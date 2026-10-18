"""Portable, inert decision packages and a standalone consistency verifier.

This module uses only Python's standard library. A verbatim copy is included as
verify.py so a trusted copy can validate an archive without installing CEDAR.
No package member is extracted or executed during verification.
"""
import argparse
import base64
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import re
import stat
import sys
import zipfile
import zlib

MAX_ARCHIVE = 32 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_FILES = 2048
FIXED_FILES = {'report.html', 'decision.json', 'evidence.csv', 'manifest.json', 'verify.py', 'VERIFY.txt'}
SOURCE_NAME = re.compile(r'^sources/(?:document|structured)-[0-9]{4,6}-[a-f0-9]{12}\.txt$')
SNAPSHOT_FIELDS = {'id', 'digest', 'revision', 'record', 'review', 'approval', 'current', 'status', 'history'}
RECORD_FIELDS = {'schema_version', 'application_version', 'created_at', 'revision', 'inputs', 'assumptions', 'profile', 'as_of', 'reviews', 'evaluation', 'package_id', 'decision', 'rationale', 'limitations'}
INPUT_FIELDS = {'schema_version', 'suppliers', 'packages', 'requirements', 'requirements_versions', 'requirements_version', 'documents', 'structured', 'applied_amendments', 'available_amendments', 'corpus'}
CSV_FIELDS = ['assertion_id', 'requirement_or_key', 'package_id', 'supplier_id', 'document_id', 'source_title', 'source_file', 'document_version', 'document_sha256', 'start_line', 'end_line', 'original', 'raw_value', 'unit', 'normalized_value', 'normalized_unit', 'transformation', 'evidence_type', 'valid_from', 'valid_until', 'extraction_status', 'review_status', 'superseded', 'unresolved_interpretation', 'note']


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON member: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Non-finite JSON number: ' + value)
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)


def _sources(inputs):
    """Stable safe archive names, independent of source identifiers and paths."""
    if not isinstance(inputs, dict) or set(inputs) - INPUT_FIELDS:
        raise ValueError('Unexpected snapshot input fields')
    documents = {d['id']: d for d in inputs['documents']}
    if len(documents) != len(inputs['documents']):
        raise ValueError('Duplicate document identifier')
    active = set(documents)
    for amendment in inputs.get('available_amendments', []):
        for document in amendment.get('documents', []):
            old = documents.get(document['id'])
            if old is not None and old != document:
                raise ValueError('Inconsistent amendment source identity')
            documents[document['id']] = document
    items = []
    for index, (identifier, document) in enumerate(sorted(documents.items()), 1):
        content = document['content'].encode('utf-8')
        name = f'sources/document-{index:04d}-{_sha(identifier.encode())[:12]}.txt'
        items.append((dict(kind='document', id=identifier, file=name, sha256=_sha(content), active=identifier in active), content, document))
    for index, (identifier, source) in enumerate(sorted(inputs.get('structured', {}).items()), 1):
        content = source['content'].encode('utf-8')
        name = f'sources/structured-{index:04d}-{_sha(identifier.encode())[:12]}.txt'
        items.append((dict(kind='structured', id=identifier, file=name, sha256=_sha(content), active=True), content, source))
    return items


def _csv_cell(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        value = _canonical(value).decode()
    else:
        value = str(value)
    # Include leading whitespace/control characters: spreadsheet importers differ
    # in whether they discard them before recognizing formula prefixes.
    probe = value.lstrip(' \t\r\n\ufeff')
    if probe.startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')):
        return "'" + value
    return value


def _evidence_csv(snapshot, source_items):
    documents = {d['id']: d for d in snapshot['record']['inputs']['documents']}
    source_files = {m['id']: m['file'] for m, _, _ in source_items if m['kind'] == 'document'}
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\r\n', quoting=csv.QUOTE_ALL)
    writer.writerow(CSV_FIELDS)
    for assertion in snapshot['record']['evaluation']['assertions']:
        a = assertion
        d = documents[a['document_id']]
        location = a['location']
        row = [a['id'], a['key'], a['package_id'], a['supplier_id'], a['document_id'], d.get('title', d['id']), source_files[d['id']], a['document_version'], a['document_hash'], location['start_line'], location['end_line'], a['original'], a.get('raw_value'), a.get('unit'), a.get('value'), a.get('normalized_unit'), a.get('transformation'), a.get('evidence_type'), a.get('valid_from'), a.get('valid_until'), a.get('extraction_status'), a.get('review_status'), a.get('superseded'), a.get('unresolved_interpretation'), a.get('note')]
        writer.writerow([_csv_cell(v) for v in row])
    return out.getvalue().encode('utf-8')


def _text(value):
    if value is None:
        return 'Not supplied'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _h(value):
    return html.escape(_text(value), quote=True)


def _money(value):
    return 'Not supplied' if value is None else f'CAD {float(value):,.2f}'


def _table(headers, rows):
    return '<div class="table-wrap"><table><thead><tr>' + ''.join('<th>' + _h(v) + '</th>' for v in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + value + '</td>' for value in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def _list(values):
    return '<ul>' + ''.join('<li>' + _h(v) + '</li>' for v in values) + '</ul>'


THEME_CONTROL = '<label class="theme-control" for="theme-preference">Theme <select id="theme-preference" data-theme-control aria-label="Color theme"><option value="dark">Dark</option><option value="light">Light</option><option value="system">System</option></select></label>'


def theme_script():
    """Read only while generating HTML; standalone verification needs no assets."""
    return Path(__file__).with_name('static').joinpath('theme.js').read_text(encoding='utf-8')


def _report(snapshot, source_items):
    record = snapshot['record']
    evaluation = record['evaluation']
    packages = evaluation['packages']
    selected = next(p for p in packages if p['id'] == record['package_id'])
    requirements = {r['id']: r for r in record['inputs']['requirements']}
    assertion_anchors = {a['id']: f'evidence-{i}' for i, a in enumerate(evaluation['assertions'], 1)}
    source_files = {m['id']: m['file'] for m, _, _ in source_items if m['kind'] == 'document'}
    def evidence_links(ids):
        return ' '.join('<a href="#' + assertion_anchors[i] + '">' + _h(i[:10]) + '</a>' for i in ids if i in assertion_anchors) or 'No cited observation'
    def section(title, body, extra=''):
        return '<section ' + extra + '><h2>' + _h(title) + '</h2>' + body + '</section>'
    def data_pairs(data):
        return _table(['Field', 'Recorded value'], [(_h(k.replace('_', ' ')), _h(v)) for k, v in data.items()])
    status = snapshot['status']
    theme = theme_script()
    script_hash = base64.b64encode(hashlib.sha256(theme.encode('utf-8')).digest()).decode('ascii')
    policy = "default-src 'none'; script-src 'sha256-" + script_hash + "'; style-src 'unsafe-inline'; img-src 'none'; base-uri 'none'; form-action 'none'"
    parts = ['<!doctype html><html lang="en" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="' + _h(policy) + '"><title>CEDAR decision record · ' + _h(snapshot['id']) + '</title><script>' + theme + '</script><style>' + _STYLE + '</style></head><body><main>' + THEME_CONTROL]
    parts.append('<header><div class="eyebrow">CEDAR / Decision evidence record</div><div class="tag">Synthetic demonstration · Offline package</div><h1>A decision, with its evidence.</h1><p class="deck">A frozen record of documentary assessment, explicit assumptions and recorded review.</p><div class="meta">' + _h(snapshot['id']) + ' &nbsp; / &nbsp; revision ' + _h(snapshot['revision']) + ' &nbsp; / &nbsp; as of ' + _h(record['as_of']) + '</div></header>')
    warning = 'STALE SNAPSHOT — inputs changed after this decision was recorded. Historical reviews and approvals below do not approve the current workspace.' if not snapshot['current'] else 'This snapshot was current when exported. This offline file cannot establish whether newer inputs or decisions now exist.'
    parts.append('<div class="notice"><strong>' + _h(warning) + '</strong></div>')
    parts.append('<nav aria-label="Report sections"><a href="#recommendation">Recommendation</a><a href="#alternatives">Alternatives</a><a href="#questions">Clarifications</a><a href="#evidence">Evidence index</a><a href="#sources">Original sources</a><a href="#verification">Verification</a></nav>')
    recommendation = '<div class="decision-card"><span class="badge">' + _h(status) + '</span><p class="eyebrow">Recorded recommendation · ' + _h(record['decision']) + '</p><h2>' + _h(selected['name']) + '</h2><p>' + _h(selected.get('supplier_name', selected.get('supplier_id'))) + '</p><p class="rationale">' + _h(record['rationale']) + '</p><div class="metrics"><div><span>Documentary gate</span><strong>' + ('Eligible for consideration' if selected['eligible'] else 'Mandatory blockers remain') + '</strong></div><div><span>Known cost subtotal</span><strong>' + _h(_money(selected['cost']['known_total'])) + '</strong></div><div><span>Preference interval</span><strong>' + _h(selected['score']['low']) + '–' + _h(selected['score']['high']) + '</strong></div></div><p class="fine">Conditional decisions record unresolved blockers. Neither a conditional decision nor documentary eligibility authorizes purchasing or certifies field performance.</p></div>'
    parts.append('<section id="recommendation">' + recommendation + '</section>')
    rows = []
    for p in packages:
        rows.append((_h(p['name']) + (' <span class="badge">Selected</span>' if p['id'] == selected['id'] else ''), _h(p.get('supplier_name', p['supplier_id'])), 'Eligible' if p['eligible'] else 'Blocked', _h(_money(p['cost']['known_total'])), _h(_money(p['cost']['upper_total'])) if p['cost']['upper_total'] is not None else '<strong>No finite upper bound</strong>', _h(str(p['score']['low']) + '–' + str(p['score']['high'])), _h(p['mandatory_counts'])))
    parts.append(section('Alternatives considered', '<p>Costs are undiscounted CAD and exclude taxes. An incomplete subtotal cannot establish a cheaper alternative. Score intervals preserve unresolved evidence; no midpoint ranking is implied.</p>' + _table(['Configuration', 'Supplier', 'Mandatory gates', 'Known subtotal', 'Cost upper bound', 'Score interval', 'Gate counts'], rows), 'id="alternatives"'))
    assumptions = dict(record.get('assumptions', {}))
    assumptions.update(fleet_aircraft=6, currency='CAD', discounting='None', taxes='Excluded', preference_profile=record['profile'], evaluation_date=record['as_of'])
    parts.append(section('Decision assumptions', data_pairs(assumptions) + '<p>Replacement frequency is a buyer planning assumption. Recurring price escalation is a quoted source input. All amounts and source assertions in this demonstration are synthetic.</p>'))
    for p in sorted(packages, key=lambda p: (p['id'] != selected['id'], p['id'])):
        cost = p['cost']
        body = '<h3>Requirement assessments</h3>'
        body += _table(['Requirement', 'Policy / wording', 'State', 'Reason', 'Evidence'], [(_h(a['requirement_id']), _h(requirements.get(a['requirement_id'], {}).get('wording', a['requirement_id'])), _h(a['state']), _h(a['reason']), evidence_links(a['assertions'])) for a in p['assessments']])
        body += '<h3>Cost inputs and subtotals</h3>' + _table(['Item', 'Quoted value', 'Unit', 'Evidence'], [(_h(line['label']), _h(line['quoted_value']) if line['quoted_value'] is not None else '<strong>Unknown</strong>', _h(line['unit']), evidence_links(line['assertions'])) for line in cost['lines']])
        body += data_pairs(cost.get('breakdown', {})) + '<p>' + _h(cost.get('interpretation', 'Known subtotal; unknown costs remain open.')) + '</p>'
        if cost['open_exposures']:
            body += '<h3>Open cost exposures</h3>' + _table(['Exposure', 'Reason', 'Evidence'], [(_h(x['label']), _h(x['reason']), evidence_links(x.get('assertions', []))) for x in cost['open_exposures']])
        body += '<h3>Score contributions</h3><p>' + _h(p['score'].get('method', 'Declared preference model')) + '</p>' + _table(['Criterion', 'State', 'Raw weight', 'Normalized weight', 'Score interval', 'Weighted contribution'], [(_h(x['requirement_id']), _h(x['state']), _h(x['weight']), _h(round(x['normalized_weight'], 6)), _h(str(x['low']) + '–' + str(x['high'])), _h(str(round(x['contribution_low'], 4)) + '–' + str(round(x['contribution_high'], 4)))) for x in p['score']['contributions']])
        body += '<h3>Software assurance</h3>'
        if p.get('assurance'):
            body += _table(['Finding / advisory', 'Disposition', 'Reason', 'Consequence', 'Evidence'], [(_h(x.get('title', x.get('id'))), _h(x.get('disposition')), _h(x.get('reason')), _h(x.get('consequence')), evidence_links(x.get('assertions', []))) for x in p['assurance']])
        else:
            body += '<p>No assurance rows are recorded. This does not establish absence of software risk.</p>'
        parts.append('<section><details' + (' open' if p['id'] == selected['id'] else '') + '><summary>' + _h(p['name']) + ' · assessment detail</summary>' + body + '</details></section>')
    sensitivity = evaluation.get('sensitivity', {})
    parts.append(section('Preference sensitivity and dominance', '<p>' + _h(sensitivity.get('interpretation', 'Scenario sensitivity was not supplied.')) + '</p>' + _table(['Operations / support ratio', 'Possible leaders', 'Guaranteed leaders'], [(_h(x.get('operations_to_support')), _h(x.get('possible_leaders')), _h(x.get('guaranteed_leaders'))) for x in sensitivity.get('cases', [])]) + '<p>Conservative dominance requires eligible alternatives, complete costs and criterion interval bounds. Recorded dominance relations: ' + _h(evaluation.get('dominance', [])) + '.</p>'))
    parts.append(section('Clarification questions', _table(['Priority', 'Configuration / requirement', 'Question', 'Why it matters', 'Evidence'], [(_h(q['priority']), _h(q['package_id'] + ' / ' + q['requirement_id']), _h(q['question']) + '<p class="fine">' + _h(q['missing']) + '</p>', _h(q['consequence']), evidence_links(q.get('assertions', []))) for q in evaluation.get('clarifications', [])]), 'id="questions"'))
    reviews = '<h3>Technical review</h3>' + (data_pairs(snapshot['review']) if snapshot.get('review') else '<p>Not recorded.</p>')
    reviews += '<h3>Approval</h3>' + (data_pairs(snapshot['approval']) if snapshot.get('approval') else '<p>Not recorded.</p>')
    if snapshot.get('history'):
        reviews += '<h3>Recorded review history</h3>' + _table(['Action', 'Role', 'Recorded at', 'Note', 'Record digest'], [(_h(x.get('action')), _h(x.get('role')), _h(x.get('at')), _h(x.get('note')), '<code>' + _h(x.get('digest')) + '</code>') for x in snapshot['history']])
    parts.append(section('Recorded review and approval', reviews + '<p class="fine">These are recorded application events. They are not digital signatures or independently authenticated identities.</p>'))
    limitations = list(dict.fromkeys(record.get('limitations', []) + evaluation.get('limitations', []) + ['All documents, vendors, tests and advisories in this demonstration are synthetic.', 'The offline package records snapshot status at export time; it has no connection to later workspace revisions.', 'Hashes establish internal consistency only. They do not prove authenticity, claim truth, reviewer identity or procurement authority.', 'The standalone verifier checks archive, source and citation consistency; it does not re-run the scoring or engineering assessment.']))
    parts.append(section('Limitations', _list(limitations)))
    evidence = []
    for a in evaluation['assertions']:
        loc = a['location']
        flags = 'Superseded' if a.get('superseded') else 'Not superseded'
        evidence.append('<details id="' + assertion_anchors[a['id']] + '"><summary>' + _h(a['key'] + ' · ' + a['package_id'] + ' · ' + a['document_id']) + ' <span class="badge">' + _h(flags) + '</span></summary><p><a href="' + source_files[a['document_id']] + '">Original source text</a> · version ' + _h(a['document_version']) + ' · lines ' + _h(loc['start_line']) + '–' + _h(loc['end_line']) + '</p><pre>' + _h(a['original']) + '</pre>' + data_pairs({k: a.get(k) for k in ('id', 'raw_value', 'unit', 'value', 'normalized_unit', 'transformation', 'evidence_type', 'extraction_status', 'review_status', 'valid_from', 'valid_until', 'unresolved_interpretation', 'note', 'review', 'document_hash')}) + '</details>')
    parts.append(section('Evidence index', '<p>Every extracted observation is retained, including rejected and superseded observations. Source bodies remain inert UTF-8 text. <a href="evidence.csv">Download spreadsheet-safe evidence CSV</a>.</p>' + ''.join(evidence), 'id="evidence"'))
    parts.append(section('Original sources and structured inputs', _table(['Input', 'Title / original reference', 'Scope', 'SHA-256', 'Original bytes'], [(_h(m['id']), _h(d.get('title', m['id'])), _h(m['kind'] + (' · included in evaluation' if m['active'] else ' · inactive amendment')), '<code>' + _h(m['sha256']) + '</code>', '<a href="' + m['file'] + '">Read inert text</a>') for m, _, d in source_items]), 'id="sources"'))
    parts.append(section('Selected requirements', _table(['ID', 'Mode', 'Wording', 'Comparator / target', 'Evidence types', 'Validity', 'Policy source'], [(_h(r['id']), _h(r['mode']), _h(r.get('wording', r['id'])), _h(str(r['comparator']) + ' ' + str(r['target']) + ' ' + r['unit']), _h(r['evidence_types']), _h(str(r['effective']) + ' to ' + str(r.get('expires') or 'no recorded expiry')), _h(r.get('source'))) for r in record['inputs']['requirements']])))
    parts.append(section('Verify this package', '<p><a href="decision.json">Exact snapshot envelope</a> · <a href="manifest.json">File manifest</a> · <a href="VERIFY.txt">Verification instructions</a></p><p>Use a trusted copy of the standard-library Python verifier against the ZIP. Verification does not extract or execute package members.</p><pre>python3 /trusted/path/verify_package.py decision-package.zip</pre><p class="fine">The included verify.py is portable, but a verifier supplied inside an untrusted archive can itself be replaced. Establish trust in the verifier separately. A changed archive with recomputed hashes can be internally consistent.</p><p>Record SHA-256: <code>' + _h(snapshot['digest']) + '</code></p>', 'id="verification"'))
    parts.append('<footer>CEDAR · Synthetic procurement evidence workbench · schema ' + _h(record['schema_version']) + ' · application ' + _h(record['application_version']) + ' · created ' + _h(record['created_at']) + '</footer></main></body></html>')
    return ''.join(parts).encode('utf-8')


_STYLE = '''
:root{color-scheme:light;--ink:#18382f;--muted:#53655d;--paper:#f6f4ec;--line:#d9ddd1;--accent:#cf713d}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1280px;padding:64px 48px;margin:auto}header{border-bottom:2px solid var(--ink);padding-bottom:36px;margin-bottom:24px}.eyebrow{font-size:11px;letter-spacing:.16em;text-transform:uppercase;font-weight:750}h1{font:normal clamp(38px,5vw,64px)/1.12 Georgia,serif;letter-spacing:-.04em;max-width:800px;margin:24px 0}h2{font:normal 29px/1.2 Georgia,serif;letter-spacing:-.025em}h3{font-size:17px;margin-top:28px}.deck{font-size:20px;max-width:710px;color:var(--muted)}.meta,.fine{font-size:12px;color:var(--muted)}.tag,.badge{display:inline-block;border:1px solid var(--line);padding:3px 8px;font-size:11px;border-radius:3px;font-weight:600}.tag{float:right}nav{display:flex;gap:22px;flex-wrap:wrap;padding:16px 0;border-bottom:1px solid var(--line);font-size:12px}a{color:#215d4b;text-underline-offset:3px}section{padding:26px 0;border-bottom:1px solid var(--line)}.notice{background:#f2e5ca;border-left:4px solid var(--accent);padding:16px 20px;font-size:13px}.decision-card{background:var(--ink);color:#f9f8ee;padding:32px}.decision-card h2{font-size:38px;margin:8px 0}.decision-card .badge{float:right;border-color:#799086}.decision-card .fine{color:#cad5cb}.rationale{font-size:20px;max-width:850px}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;padding:24px 0;border-top:1px solid #496056;border-bottom:1px solid #496056}.metrics span{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#cad5cb}.metrics strong{font-size:19px;font-weight:550}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;text-transform:uppercase;letter-spacing:.05em;font-size:10px;background:#e9ede2;color:var(--muted);padding:11px}td{padding:12px 11px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}td p{margin:7px 0 0}code{font:11px/1.4 ui-monospace,monospace;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#e9ede2;padding:16px;font:12px/1.7 ui-monospace,monospace;border-left:3px solid #9aaf9e}details{margin:12px 0}summary{cursor:pointer;font-size:15px;padding:12px 0;font-weight:650}details details{border-top:1px solid var(--line)}footer{padding:28px 0;font-size:11px;color:var(--muted)}@media(max-width:760px){main{padding:25px 18px}.tag{float:none;margin-top:15px}.metrics{grid-template-columns:1fr}.decision-card{padding:23px}nav{gap:12px}}@media print{body{background:white}main{padding:0}nav{display:none}section{break-inside:avoid}details{display:block}details>*{display:block}a{color:inherit}.decision-card{background:#e9ede2;color:#18382f}.decision-card .fine,.metrics span{color:#53655d}}
'''

_STYLE += '''
:root{color-scheme:dark}:root[data-theme="light"]{color-scheme:light}
.theme-control{display:flex;justify-content:flex-end;align-items:center;gap:9px;font-size:12px;font-weight:600;margin:0 0 20px;color:var(--muted)}
.theme-control select{font:inherit;padding:8px 26px 8px 10px;border:1px solid var(--line);border-radius:5px;background:var(--paper);color:var(--ink)}
a:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #78d3d0;outline-offset:4px}
:root:not([data-theme="light"]){--ink:#dfede4;--muted:#adc4b7;--paper:#101f1b;--line:#385248;--accent:#e5b470}
:root:not([data-theme="light"]) a{color:#9ad8b9}
:root:not([data-theme="light"]) .notice{background:#3a3020;color:#f0d7ac}
:root:not([data-theme="light"]) .decision-card{background:#203e31;color:#ecf5e9}
:root:not([data-theme="light"]) :is(th,pre){background:#1b322a}
:root:not([data-theme="light"]) :is(.decision-card .fine,.metrics span){color:#bdd5c5}
@media print{:root,:root:not([data-theme="light"]){--ink:#18382f;--muted:#53655d;--paper:white;--line:#d9ddd1;--accent:#cf713d;color-scheme:light}.theme-control{display:none}:root:not([data-theme="light"]) a{color:inherit}:root:not([data-theme="light"]) .notice{background:#f2e5ca;color:#18382f}:root:not([data-theme="light"]) :is(.decision-card,th,pre){background:#e9ede2;color:#18382f}:root:not([data-theme="light"]) :is(.decision-card .fine,.metrics span){color:#53655d}}
'''


VERIFY_INSTRUCTIONS = '''CEDAR portable package verification

This synthetic decision package contains an exact snapshot envelope, a static
report, a spreadsheet-safe evidence ledger, and inert UTF-8 original sources.
No server credentials, sessions or live workspace database are included.

Run from a trusted CEDAR checkout:
  python3 scripts/verify_package.py /path/to/decision-package.zip

Or inspect and establish trust in the included verify.py before running:
  python3 verify.py /path/to/decision-package.zip
Only Python 3 standard-library modules are needed. No network is used. The
verifier reads ZIP members with size limits and never extracts or executes them.
A successful check exits 0; failed checks exit 1 and list errors as JSON.

The verifier checks:
- safe unique archive paths, permitted members and expansion limits;
- the exact manifest file list, byte sizes and SHA-256 file hashes;
- canonical record SHA-256, snapshot revision, review digest references;
- the selected requirements and evaluation requirement list agree;
- all original document and structured source bodies match their stored hashes;
- citations match the cited document hash, version, line range and original text;
- assertion identifiers and assessment/clarification citation references agree;
- the evidence CSV is the safe rendering of the recorded assertion ledger.

Canonical record bytes are UTF-8 JSON using sorted keys, compact separators,
ensure_ascii=False and no non-finite numbers. The digest covers record only.
Envelope review/history/status are protected by the file manifest, not that
record digest. The manifest hashes every package file except itself.

LIMITS OF VERIFICATION
Hashes prove internal consistency, not authenticity, claim truth, reviewer
identity, digital signatures or purchasing authority. A party able to replace
files can recompute hashes. A verifier inside an untrusted package can also be
replaced; use a separately trusted copy to inspect untrusted packages. The
verifier does not recompute cost/scoring policy or certify field capability.
Snapshot status is the status recorded at export; this offline package cannot
know whether a newer workspace revision exists. A stale snapshot remains stale
and its old review or approval is historical only.

Open report.html after verification. Keep the sources directory beside it.
Original source links are text files; source markup is never rendered as HTML.
CSV cells with formula/control prefixes are quoted and prefixed by an apostrophe.
The raw values remain unchanged in decision.json and the original sources.
'''


def _semantic_errors(snapshot, manifest, files):
    errors = []
    if not isinstance(snapshot, dict) or set(snapshot) - SNAPSHOT_FIELDS:
        return ['Unexpected snapshot envelope fields']
    record = snapshot['record']
    if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
        return ['Unexpected or missing decision record fields']
    if _sha(_canonical(record)) != snapshot['digest']:
        errors.append('Canonical decision record digest mismatch')
    if manifest.get('snapshot_id') != snapshot['id'] or manifest.get('digest') != snapshot['digest']:
        errors.append('Manifest snapshot identity or digest mismatch')
    if type(snapshot['revision']) is not int or snapshot['revision'] != record['revision']:
        errors.append('Snapshot revision mismatch')
    if type(snapshot['current']) is not bool:
        errors.append('Snapshot current status must be boolean')
    expected_status = 'stale' if not snapshot['current'] else 'approved' if snapshot.get('approval') else 'reviewed' if snapshot.get('review') else 'draft'
    if snapshot['status'] != expected_status:
        errors.append('Snapshot status does not match its recorded state')
    for name in ('review', 'approval'):
        event = snapshot.get(name)
        if event is not None and event.get('digest') != snapshot['digest']:
            errors.append(name.title() + ' digest mismatch')
    if snapshot.get('approval') and not snapshot.get('review'):
        errors.append('Approval is missing a technical review')
    for event in snapshot.get('history', []):
        if event.get('digest') != snapshot['digest']:
            errors.append('Review history digest mismatch')
    inputs, evaluation = record['inputs'], record['evaluation']
    if inputs['requirements'] != evaluation['requirements']:
        errors.append('Selected requirements differ from evaluated requirements')
    versions = inputs.get('requirements_versions')
    if versions is not None and versions.get(inputs['requirements_version']) != inputs['requirements']:
        errors.append('Selected requirements version mismatch')
    for key in ('profile', 'as_of', 'assumptions'):
        if key in evaluation and record[key] != evaluation[key]:
            errors.append('Evaluation ' + key + ' mismatch')
    items = _sources(inputs)
    if manifest.get('sources') != [m for m, _, _ in items]:
        errors.append('Source index does not match snapshot source inputs')
    expected_files = FIXED_FILES | {m['file'] for m, _, _ in items}
    if set(files) != expected_files:
        errors.append('Archive source file list does not match snapshot sources')
    for metadata, content, source in items:
        if source.get('hash') != metadata['sha256']:
            errors.append('Source content hash mismatch: ' + metadata['id'])
        if files.get(metadata['file']) != content:
            errors.append('Source body does not match decision record: ' + metadata['id'])
    documents = {d['id']: d for d in inputs['documents']}
    expected_documents = [{k: v for k, v in d.items() if k != 'content'} for d in inputs['documents']]
    if evaluation.get('documents') != expected_documents:
        errors.append('Evaluation document index differs from input sources')
    assertions = evaluation['assertions']
    by_id = {a['id']: a for a in assertions}
    if len(by_id) != len(assertions):
        errors.append('Duplicate evidence assertion identifier')
    superseded = {identifier for d in inputs['documents'] for identifier in d.get('supersedes', [])}
    for a in assertions:
        d = documents.get(a['document_id'])
        if d is None:
            errors.append('Citation refers to an unknown source: ' + str(a['id']))
            continue
        digest = _sha(d['content'].encode('utf-8'))
        loc = a['location']
        start, end = loc['start_line'], loc['end_line']
        lines = d['content'].splitlines()
        valid_range = type(start) is int and type(end) is int and 1 <= start <= end <= len(lines)
        if not valid_range or a['original'] != '\n'.join(lines[start-1:end]):
            errors.append('Citation original text or line range mismatch: ' + str(a['id']))
        if a['document_hash'] != digest or a['document_version'] != d['version'] or a['package_id'] != d['package_id'] or a['supplier_id'] != d['supplier_id']:
            errors.append('Citation source identity mismatch: ' + str(a['id']))
        if type(start) is int and a['id'] != _sha(_canonical([d['id'], digest, start]))[:24]:
            errors.append('Citation assertion identifier mismatch: ' + str(a['id']))
        if a['superseded'] != (d['id'] in superseded):
            errors.append('Citation supersession mismatch: ' + str(a['id']))
        review = record['reviews'].get(a['id'])
        if a.get('review') != review or a['review_status'] != (review or {}).get('status', 'unreviewed'):
            errors.append('Citation review status mismatch: ' + str(a['id']))
    packages = evaluation['packages']
    selected = [p for p in packages if p['id'] == record['package_id']]
    if len(selected) != 1 or record['decision'] not in {'conditional', 'eligible'}:
        errors.append('Decision refers to an invalid package or decision type')
    elif record['decision'] == 'eligible' and not selected[0]['eligible']:
        errors.append('Eligible decision contradicts recorded mandatory gate')
    requirement_ids = {r['id'] for r in inputs['requirements']}
    if len(requirement_ids) != len(inputs['requirements']):
        errors.append('Duplicate selected requirement identifier')
    for p in packages:
        for assessment in p['assessments']:
            if assessment['requirement_id'] not in requirement_ids:
                errors.append('Assessment references unknown requirement')
            expected_ids = [a['id'] for a in assertions if a['key'] == assessment['requirement_id'] and a['package_id'] == p['id']]
            if assessment['assertions'] != expected_ids:
                errors.append('Assessment citation list differs from source ledger: ' + p['id'] + '/' + assessment['requirement_id'])
        references = p['cost'].get('lines', []) + p['cost'].get('open_exposures', []) + p.get('assurance', [])
        for row in references:
            for identifier in row.get('assertions', []):
                if identifier not in by_id or by_id[identifier]['package_id'] != p['id']:
                    errors.append('Package citation references missing or unrelated evidence')
    for q in evaluation.get('clarifications', []):
        for identifier in q.get('assertions', []):
            if identifier not in by_id or by_id[identifier]['package_id'] != q['package_id']:
                errors.append('Clarification citation references missing or unrelated evidence')
    if files.get('evidence.csv') != _evidence_csv(snapshot, items):
        errors.append('Evidence CSV differs from safe rendering of the assertion ledger')
    return errors


def verify_package(payload):
    """Return consistency results for ZIP bytes. Never extract or execute files."""
    errors = []
    result = {'valid': False, 'errors': errors, 'scope': 'Internal archive, source and citation consistency only; no authenticity or claim-truth guarantee.'}
    try:
        if not isinstance(payload, bytes):
            raise ValueError('Package must be bytes')
        if len(payload) > MAX_ARCHIVE:
            raise ValueError('Archive size limit exceeded')
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_FILES:
                raise ValueError('Archive member count limit exceeded')
            names = [info.filename for info in infos]
            if len(set(names)) != len(names) or len({n.casefold() for n in names}) != len(names):
                raise ValueError('Duplicate archive member names')
            total = 0
            for info in infos:
                name = info.filename
                if info.orig_filename != name or name not in FIXED_FILES and SOURCE_NAME.fullmatch(name) is None:
                    raise ValueError('Unsafe or unexpected archive member: ' + repr(name))
                kind = stat.S_IFMT(info.external_attr >> 16)
                if info.is_dir() or kind not in (0, stat.S_IFREG) or info.flag_bits & 1:
                    raise ValueError('Unsupported archive member type or encryption')
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise ValueError('Unsupported archive compression')
                if info.file_size > MAX_MEMBER or info.file_size < 0:
                    raise ValueError('Archive member expansion limit exceeded')
                total += info.file_size
                if total > MAX_EXPANDED:
                    raise ValueError('Total archive expansion limit exceeded')
            if not FIXED_FILES <= set(names):
                raise ValueError('Missing required package files')
            files = {info.filename: archive.read(info) for info in infos}
        manifest = _json(files['manifest.json'])
        if manifest.get('schema_version') != '1.0' or manifest.get('algorithm') != 'sha256':
            errors.append('Unsupported manifest format')
        entries = manifest['files']
        if set(entries) != set(files) - {'manifest.json'}:
            errors.append('Manifest file list differs from archive file list')
        for name, body in files.items():
            if name == 'manifest.json':
                continue
            entry = entries.get(name)
            if not isinstance(entry, dict) or entry.get('size') != len(body) or entry.get('sha256') != _sha(body):
                errors.append('Manifest hash or size mismatch: ' + name)
        snapshot = _json(files['decision.json'])
        errors.extend(_semantic_errors(snapshot, manifest, files))
        result.update(snapshot_id=snapshot['id'], digest=snapshot['digest'], status=snapshot['status'], files_checked=len(files)-1, sources_checked=len(manifest.get('sources', [])), citations_checked=len(snapshot['record']['evaluation']['assertions']))
    except (ValueError, TypeError, KeyError, AttributeError, IndexError, UnicodeError, RecursionError, OverflowError, zipfile.BadZipFile, zlib.error, RuntimeError, OSError) as exc:
        errors.append('Invalid package: ' + str(exc))
    result['valid'] = not errors
    return result


def build_package(snapshot):
    """Build a complete package, rejecting inconsistent or secret-bearing envelopes."""
    if not isinstance(snapshot, dict) or set(snapshot) - SNAPSHOT_FIELDS:
        raise ValueError('Unexpected snapshot envelope fields')
    record = snapshot['record']
    if set(record) != RECORD_FIELDS:
        raise ValueError('Unexpected or missing decision record fields')
    # Round-trip detached data ensures rendering cannot mutate the immutable record.
    snapshot = _json(_canonical(snapshot))
    items = _sources(snapshot['record']['inputs'])
    files = {m['file']: content for m, content, _ in items}
    files.update({'decision.json': _canonical(snapshot), 'report.html': _report(snapshot, items), 'evidence.csv': _evidence_csv(snapshot, items), 'verify.py': Path(__file__).read_bytes(), 'VERIFY.txt': VERIFY_INSTRUCTIONS.encode('utf-8')})
    manifest = dict(schema_version='1.0', algorithm='sha256', snapshot_id=snapshot['id'], digest=snapshot['digest'], files={name: {'sha256': _sha(body), 'size': len(body)} for name, body in sorted(files.items())}, sources=[m for m, _, _ in items])
    files['manifest.json'] = _canonical(manifest)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, body in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, body)
    payload = buffer.getvalue()
    checked = verify_package(payload)
    if not checked['valid']:
        raise ValueError('Cannot export inconsistent snapshot: ' + '; '.join(checked['errors']))
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description='Verify CEDAR package consistency without extracting or executing archive members. Use a separately trusted verifier.')
    parser.add_argument('package', help='Path to the decision ZIP package')
    args = parser.parse_args(argv)
    path = Path(args.package)
    try:
        if path.stat().st_size > MAX_ARCHIVE:
            raise ValueError('Archive size limit exceeded')
        result = verify_package(path.read_bytes())
    except (OSError, ValueError) as exc:
        result = {'valid': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    sys.exit(main())
