"""Bounded GET-only acquisition with a field allowlist and resumable extracts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

BASE = 'https://public-api.prozorro.gov.ua/api/2.5'
START, END = '2025-01-01', '2025-03-31'
DENY = re.compile(r'військ|оборон|поліці|поліц|гварді|безпек|надзвичайн|рятув|дснс|прикордон|пенітенці|виконання покарань|слідч|територіальн.*комплект|збройн', re.I)
CIVIL = re.compile(r'ліце|гімназ|школ|освіт|університет|коледж|лікарн|медич|культур|бібліот|\bсуд\b|судов|казнач|пенсійн|соціальн|комунальн|міськ.*рад|сільськ.*рад|селищн.*рад|статистик|архів|театр|музей|державн.*адміністрац', re.I)
PAPER = re.compile(r'пап[іе]р', re.I)
A4 = re.compile(r'[аa]\s*[-]?\s*4\b', re.I)


def dump(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n'
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(body, encoding='utf-8')
    temp.replace(path)


def safe_url(url: str) -> bool:
    u = urlsplit(url)
    return (u.scheme == 'https' and u.netloc == 'public-api.prozorro.gov.ua'
            and re.fullmatch(r'/api/2\.5/(tenders|contracts)(/[a-f0-9]{32})?', u.path) is not None
            and not u.fragment)


def candidate_scope(t: dict) -> list[str]:
    reasons = []
    if t.get('config', {}).get('restricted') or t.get('restricted'):
        reasons.append('restricted_record')
    name = t.get('procuringEntity', {}).get('name', '')
    text = name + ' ' + t.get('title', '') + ' ' + t.get('procurementMethodType', '')
    if DENY.search(text) or 'defense' in text.lower(): reasons.append('excluded_buyer_scope')
    elif not CIVIL.search(name): reasons.append('civilian_buyer_unverified')
    created = t.get('dateCreated', '')
    if not created: reasons.append('missing_publication_date')
    elif not START <= created[:10] <= END: reasons.append('outside_publication_period')
    identifier_date = re.match(r'UA-(\d{4}-\d{2}-\d{2})-', t.get('tenderID', ''))
    if not identifier_date or (created and identifier_date.group(1) != created[:10]):
        reasons.append('publication_date_conflict')
    if t.get('mode'): reasons.append('test_mode')
    if len(t.get('lots', [])) > 1: reasons.append('multiple_lots_not_acquired')
    items = t.get('items', [])
    free_text = t.get('title', '') + ' ' + ' '.join(i.get('description', '') for i in items)
    if re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\+380[\s()\d-]{9,}', free_text):
        reasons.append('sensitive_free_text')
    if not any(PAPER.search(i.get('description', '')) and
               (A4.search(i.get('description', '')) or (len(items) == 1 and A4.search(t.get('title', '')))) for i in items):
        reasons.append('no_a4_paper_item')
    return reasons


def _fields(obj, names):
    return {k: obj[k] for k in names.split() if k in obj}


def _value(obj):
    return _fields(obj, 'amount amountNet currency valueAddedTaxIncluded')


def _items(items):
    result = []
    for x in items:
        y = _fields(x, 'id description quantity relatedLot')
        for k, names in [('unit', 'code name'), ('classification', 'id scheme'),
                         ('deliveryDate', 'startDate endDate')]:
            if k in x: y[k] = _fields(x[k], names)
        result.append(y)
    return result


def _documents(docs):
    return [_fields(d, 'id documentType format datePublished dateModified documentOf relatedItem confidentiality') for d in docs]


def _stage(x):
    y = _fields(x, 'id awardID lotID status date dateSigned dateModified contractID')
    for k in ('value', 'amountPaid'):
        if k in x and isinstance(x[k], dict): y[k] = _value(x[k])
    if 'items' in x: y['items'] = _items(x['items'])
    if 'documents' in x: y['documents'] = _documents(x['documents'])
    if 'changes' in x:
        y['changes'] = [_fields(c, 'id status date dateSigned rationaleTypes') for c in x['changes']]
    if 'lotValues' in x:
        y['lotValues'] = [{**_fields(v, 'relatedLot'), 'value': _value(v.get('value', {}))} for v in x['lotValues']]
    if 'implementation' in x:
        imp = x['implementation']
        y['implementation'] = {'transactions': [{**_fields(v, 'id date'), 'value': _value(v.get('value', {}))} for v in imp.get('transactions', [])]}
    return y


def sanitize(t: dict) -> dict:
    y = _fields(t, 'id tenderID title dateCreated dateModified status procurementMethodType mainProcurementCategory')
    y['restricted'] = t.get('config', {}).get('restricted', t.get('restricted'))
    for k in ('value',):
        if k in t: y[k] = _value(t[k])
    y['items'] = _items(t.get('items', []))
    for k in ('awards', 'contracts', 'bids'):
        if k in t: y[k] = [_stage(x) for x in t[k]]
    y['lots'] = [{**_fields(l, 'id title status'), 'value': _value(l.get('value', {}))} for l in t.get('lots', [])]
    y['documents'] = _documents(t.get('documents', []))
    y['cancellations'] = [_fields(c, 'id status cancellationOf relatedLot date') for c in t.get('cancellations', [])]
    return y


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect requires source-path review')


class Client:
    def __init__(self, ledger: Path, cap: int = 150):
        self.ledger, self.cap, self.count, self.last = ledger, cap, 0, 0.0
        self.opener = build_opener(NoRedirect())
        self.ledger.parent.mkdir(parents=True, exist_ok=True)

    def get(self, url):
        if not safe_url(url): raise ValueError('Not an allowed public read endpoint')
        if self.count >= self.cap: raise RuntimeError('Request budget reached')
        time.sleep(max(0, 1.05 - (time.monotonic() - self.last)))
        self.last = time.monotonic(); self.count += 1
        entry = {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'method': 'GET'}
        try:
            with self.opener.open(Request(url, headers={'User-Agent': 'civilian-comparability-audit/0.1 (bounded public research)', 'Accept': 'application/json'}), timeout=30) as r:
                body = r.read(5_000_001)
                if len(body) > 5_000_000: raise ValueError('Response size budget reached')
                entry.update(status=r.status, bytes=len(body), response_sha256=hashlib.sha256(body).hexdigest(), server_date=r.headers.get('Date'))
                data = json.loads(body, parse_float=str)
        except HTTPError as e:
            entry.update(status=e.code, error='HTTPError')
            data = None
        except Exception as e:
            entry.update(status=None, error=type(e).__name__, message=str(e))
            data = None
        with self.ledger.open('a', encoding='utf-8') as f: f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        if entry.get('status') in (401, 403, 429):
            raise RuntimeError(f"Acquisition stopped on HTTP {entry['status']}; no bypass or automatic retry")
        return data, entry


def acquire(root: Path, target: int = 50, cap: int = 150):
    if not 1 <= target <= 50: raise ValueError('Target must be between 1 and 50')
    if not 1 <= cap <= 150: raise ValueError('Request budget must be between 1 and 150')
    folder = root / 'data' / 'extracts'; folder.mkdir(parents=True, exist_ok=True)
    seeds = json.loads((root / 'data' / 'candidate-seeds.json').read_text())
    if isinstance(seeds, dict): seeds = seeds['candidates']
    client = Client(root / 'evidence' / 'acquisition.jsonl', cap)
    rejected = []
    reject_path = root / 'data' / 'acquisition-exclusions.json'
    if reject_path.exists(): rejected = json.loads(reject_path.read_text())
    checked = {r['id'] for r in rejected}
    count = len(list(folder.glob('*.json')))
    for seed in seeds:
        if count >= target: break
        ident = seed.get('id', seed.get('uuid', ''))
        if not re.fullmatch('[a-f0-9]{32}', ident): raise ValueError(f'Invalid candidate identifier: {ident!r}')
        dest = folder / (ident + '.json')
        if dest.exists() or ident in checked: continue
        payload, meta = client.get(BASE + '/tenders/' + ident)
        if payload is None:
            print('unavailable', ident, meta.get('status'), flush=True)
            continue
        tender = payload['data']
        reasons = candidate_scope(tender)
        if reasons:
            rejected.append({'id': ident, 'reasons': reasons, 'source_url': meta['url']})
            dump(reject_path, rejected)
            print('excluded', ident, ','.join(reasons), flush=True)
            continue
        extra = []
        # Full contracting state is separately linked; 404 is retained as a limitation.
        for c in tender.get('contracts', []):
            if c.get('status') != 'active' or not re.fullmatch('[a-f0-9]{32}', c.get('id', '')): continue
            detail, cm = client.get(BASE + '/contracts/' + c['id'])
            if detail and detail.get('data', {}).get('id') == c['id']:
                extra.append({'provenance': cm, 'contract': _stage(detail['data'])})
            else:
                extra.append({'provenance': cm, 'contract': None})
        extract = {'schema_version': 1, 'source_kind': 'real', 'provenance': {**meta, 'discovery_url': seed.get('discovery_url', seed.get('url')), 'attribution': 'Prozorro public procurement data', 'reuse_basis': 'https://prozorro.gov.ua/openprocurement'},
                   'scope_review': {'annotator_type': 'assistant', 'civilian_candidate': True, 'basis': 'positive civilian organization-name rule and negative sensitive-buyer rule; not independent human validation'},
                   'tender': sanitize(tender), 'contract_details': extra}
        dump(dest, extract)
        count += 1
        print('saved', count, tender.get('tenderID'), flush=True)
    summary = {'saved_unique_lots': count, 'target': target, 'requests_this_run': client.count, 'rejected_candidates': len(rejected), 'sampling': 'bounded search-discovered convenience sample; one lot per tender', 'publication_period': [START, END]}
    dump(root / 'evidence' / 'acquisition-summary.json', summary)
    return summary
