"""Inert text ingestion. Only explicitly labelled observations are extracted."""
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256((value if isinstance(value, str) else canonical(value)).encode()).hexdigest()


KEY = r'(?:R\d{2}|[CA]_[A-Za-z0-9_]+)'
LABEL = re.compile(r'^('+KEY+r'): (.*?) (\S+) ; evidence=(\w+) ; valid=([\d-]+) ; until=([\d-]+) ; note=(.*)$')
BLOCK = re.compile(r'^\[('+KEY+r')\]$')
CONVERSIONS = {'hours': ('minutes', 60), 'years': ('months', 12), 'kg': ('g', 1000)}


def parse_document(document):
    body = document['content']
    lines = body.splitlines()
    observations = []
    for i, line in enumerate(lines):
        parts = None
        end = i
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) == 7 and re.fullmatch(KEY, cells[0]):
                parts = cells
        m = LABEL.fullmatch(line)
        if m:
            parts = list(m.groups())
        m = BLOCK.fullmatch(line)
        if m and i + 6 < len(lines):
            names = ['Value: ', 'Unit: ', 'Evidence: ', 'Valid: ', 'Until: ', 'Note: ']
            block = lines[i+1:i+7]
            if all(v.startswith(n) for n, v in zip(names, block)):
                parts = [m[1]]+[v[len(n):] for n,v in zip(names,block)]
                end = i+6
        if parts is None:
            continue
        key, raw, unit, evidence, start_date, until, note = parts
        issue = None
        value = raw
        normalized_unit = unit
        transform = 'Identity; verbatim text'
        try:
            num = Decimal(raw)
            if not num.is_finite() or abs(num) > Decimal('1e12'):
                raise InvalidOperation
            if unit in CONVERSIONS:
                normalized_unit, factor = CONVERSIONS[unit]
                num *= factor
                transform = f'{raw} {unit} × {factor} = {num} {normalized_unit}'
            else:
                transform = 'Decimal parsing; no unit conversion'
            value = float(num)
        except InvalidOperation:
            if raw.lower() in {'unknown','tbd','unspecified','n/a','nan','inf','infinity'}:
                value = None
                issue = 'Value is unknown or non-finite; no numeric assumption made.'
        try:
            date.fromisoformat(start_date); date.fromisoformat(until)
        except ValueError:
            issue = 'Invalid evidence validity date.'
            start_date = until = None
        dh = digest(body)
        observations.append(dict(id=digest([document['id'], dh, i+1])[:24], key=key,
            package_id=document['package_id'], supplier_id=document['supplier_id'],
            document_id=document['id'],document_hash=dh,document_version=document['version'],
            location={'start_line':i+1,'end_line':end+1},original='\n'.join(lines[i:end+1]),
            raw_value=raw,unit=unit,value=value,normalized_unit=normalized_unit,transformation=transform,
            evidence_type=evidence,extraction_status='parsed' if not issue else 'needs_interpretation',
            review_status='unreviewed',valid_from=start_date,valid_until=until,
            unresolved_interpretation=issue,note=note,superseded=False))
    return observations


def load_corpus(path, requirements_version='v1', amendments=None):
    root = Path(path).resolve()
    catalog = json.loads((root/'catalog.json').read_text())
    selected = set(amendments or [])
    known = {a['id'] for a in catalog['amendments']}
    if not selected <= known:
        raise ValueError('Unknown amendment')
    if requirements_version not in catalog['requirements']:
        raise ValueError('Unknown requirements version')
    def read_document(meta):
        path = (root/meta['path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Source path escapes corpus')
        content = path.read_bytes().decode('utf-8')
        return dict(meta, content=content, hash=digest(content))
    documents = [read_document(m) for m in catalog['documents']]
    available = []
    for amendment in catalog['amendments']:
        a = dict(amendment, documents=[read_document(m) for m in amendment['documents']])
        available.append(a)
        if a['id'] in selected:
            documents.extend(a['documents'])
    structured = {}
    paths=[root/'advisories.json',root/'assurance.json']+[root/'inventory'/f"{p['id']}.cdx.json" for p in catalog['packages']]
    for p in sorted(paths):
        if not p.exists():
            continue
        if not p.resolve().is_relative_to(root):
            raise ValueError('Structured source path escapes corpus')
        content = p.read_bytes().decode('utf-8')
        structured[p.relative_to(root).as_posix()] = {'content':content, 'hash':digest(content)}
    return dict(schema_version='1.0', suppliers=catalog['suppliers'], packages=catalog['packages'],
        requirements=catalog['requirements'][requirements_version], requirements_versions=catalog['requirements'],
        requirements_version=requirements_version, documents=sorted(documents,key=lambda d:d['id']),
        available_amendments=available, applied_amendments=sorted(selected), structured=structured,
        corpus='slice' if len(catalog['packages'])==3 else 'full')


def ledger(inputs, reviews=None):
    superseded = {x for d in inputs['documents'] for x in d.get('supersedes',[])}
    results=[]
    for d in sorted(inputs['documents'],key=lambda d:d['id']):
        for a in parse_document(d):
            a['superseded'] = d['id'] in superseded
            a['review_status'] = (reviews or {}).get(a['id'],{}).get('status','unreviewed')
            a['review'] = (reviews or {}).get(a['id'])
            results.append(a)
    return results


def current_assertions(assertions, as_of):
    return [a for a in assertions if not a['superseded'] and a['review_status']!='rejected'
            and a['valid_from'] and a['valid_from'] <= as_of <= a['valid_until']]


def undated_assertions(assertions):
    return [a for a in assertions if not a['superseded'] and a['review_status']!='rejected'
            and (not a['valid_from'] or not a['valid_until'])]
