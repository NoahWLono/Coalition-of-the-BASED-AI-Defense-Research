"""Deterministic local reports. Rendering requires no network or dependencies."""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
import csv
from decimal import Decimal
import hashlib
from html import escape
import json
from pathlib import Path

from .acquire import dump
from .adapter import adapt
from .core import normalize_lot, screen, evaluate, example_lot


_THEME_SCRIPT = '''<script>
(() => {
  const key = 'prozorro-report-theme';
  const choices = ['system', 'light', 'dark'];
  let preference = 'dark';
  try {
    const saved = localStorage.getItem(key);
    if (choices.includes(saved)) preference = saved;
  } catch (_) { /* The report remains usable when storage is unavailable. */ }
  const system = typeof matchMedia === 'function' ? matchMedia('(prefers-color-scheme: dark)') : null;
  const apply = () => {
    document.documentElement.dataset.theme = preference === 'system'
      ? (system && system.matches ? 'dark' : 'light') : preference;
  };
  apply();
  if (system) {
    if (system.addEventListener) system.addEventListener('change', apply);
    else if (system.addListener) system.addListener(apply);
  }
  document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('theme');
    picker.value = preference;
    picker.addEventListener('change', () => {
      if (!choices.includes(picker.value)) return;
      preference = picker.value;
      try { localStorage.setItem(key, preference); } catch (_) {}
      apply();
    });
  });
})();
</script>'''

_REPORT_STYLE = '''<style>
:root{color-scheme:dark;--page:#111c20;--ink:#e4edef;--surface:#1b2a30;--subtle:#21343b;--border:#5c727b;--muted:#b4c6cd;--link:#8fd8f5;--notice:#193a31;--accent:#88d4ac}
:root[data-theme="light"]{color-scheme:light;--page:#f6f5ef;--ink:#182d32;--surface:#fff;--subtle:#edf1ee;--border:#7b8d85;--muted:#526469;--link:#165e78;--notice:#e7eee8;--accent:#315d4c}
*{box-sizing:border-box}body{font-family:system-ui,sans-serif;background:var(--page);color:var(--ink);margin:0}
main{max-width:1120px;margin:auto;padding:48px 24px}h1{font:600 42px Georgia,serif;max-width:850px}p{line-height:1.6}
.toolbar{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}.kicker{letter-spacing:.15em;text-transform:uppercase;font-size:12px;color:var(--muted)}
.theme-control{display:flex;align-items:center;gap:8px;font-size:14px}.theme-control select{font:inherit;background:var(--surface);color:var(--ink);border:1px solid var(--border);border-radius:5px;min-height:44px;padding:8px 30px 8px 10px}
:focus-visible{outline:3px solid var(--link);outline-offset:4px}.notice{padding:20px;background:var(--notice);border-left:5px solid var(--accent)}
.stats{display:flex;flex-wrap:wrap;gap:15px;margin:28px 0}.stat{padding:20px;background:var(--surface);min-width:130px;border:1px solid var(--border)}.stat b{display:block;font-size:32px}
details{background:var(--surface);border:1px solid var(--border);margin:12px 0;padding:18px}summary{cursor:pointer;font-weight:600;line-height:1.5}summary::marker{color:var(--accent)}
.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:16px 0;font-size:14px;background:var(--surface)}th,td{text-align:left;border-bottom:1px solid var(--border);padding:9px;overflow-wrap:anywhere}th{background:var(--subtle)}tbody tr:nth-child(even){background:var(--subtle)}
a{color:var(--link);text-underline-offset:3px}code{overflow-wrap:anywhere;font-size:12px}small{color:var(--muted)}.fixture-lead{color:var(--accent);font-weight:600}
@media(max-width:600px){main{padding:28px 16px}h1{font-size:34px}.stat{flex:1 1 130px}th,td{padding:8px 6px}details{padding:14px}}
@media print{:root,:root[data-theme="light"]{color-scheme:light;--page:#fff;--ink:#182d32;--surface:#fff;--subtle:#edf1ee;--border:#7b8d85;--muted:#526469;--link:#165e78;--notice:#e7eee8;--accent:#315d4c}.theme-control{display:none}details{break-inside:avoid}main{padding:12px}}
</style>'''

_THEME_CONTROL = '''<div class="theme-control"><label for="theme">Theme</label>
<select id="theme" name="theme"><option value="system">System</option><option value="light">Light</option><option value="dark" selected>Dark</option></select></div>'''


def _page(title, content):
    return ('<!doctype html><html lang="en" data-theme="dark"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>'+escape(title)+'</title>'+_THEME_SCRIPT+_REPORT_STYLE+
            '</head><body><main>'+content+'</main></body></html>')


def csv_file(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore');w.writeheader()
        for row in rows:
            # Protect exported spreadsheet cells without changing JSON accounting.
            clean = {k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict,list)) else v for k,v in row.items()}
            clean = {k: ("'"+v if isinstance(v,str) and v.startswith(('=', '+', '-', '@')) else v) for k,v in clean.items()}
            w.writerow(clean)


def assumptions(records):
    variants = []
    for name in ['strict', 'assume_500_sheet_packs', 'assume_piece_means_500_sheet_pack']:
        inputs = deepcopy(records)
        changed = 0
        for r in inputs:
            if len(r['items']) != 1:
                continue
            for item in r['items']:
                if name == 'assume_500_sheet_packs' and item.get('unit') == 'pack' and not item.get('sheets_per_pack'):
                    item.update(sheets_per_pack='500',pack_size_reviewed=True);changed+=1
                if name == 'assume_piece_means_500_sheet_pack' and item.get('unit_code') == 'H87':
                    item.update(unit='pack',sheets_per_pack='500',pack_size_reviewed=True);changed+=1
        result = screen([normalize_lot(r) for r in inputs])
        variants.append({'scenario':name,'assumed_items':changed,**result['counts'],
                         'interpretation':'Stress test only. Unsupported assumptions are never used in baseline results.'})
    return {'comparability_scenarios':variants, 'currency':{'baseline':'UAH only, no conversion',
            'cross_currency_assessment':'not_applicable_no_cross_currency_comparisons',
            'common_scaling_check':'synthetic exact invariance test only; not empirical FX validation'},
            'warning':'No eligible real groups means zero leads under alternative assumptions is uninformative about economic robustness.'}


def build_report(extract_dir: Path, out: Path, labels_path: Path | None = None, reviews_path: Path | None = None):
    inputs=[]; provenance=[]
    reviews=json.loads(reviews_path.read_text()) if reviews_path else {}
    for path in sorted(extract_dir.glob('*.json')):
        raw=path.read_bytes(); extract=json.loads(raw); r=adapt(extract)
        r['extract_sha256']=hashlib.sha256(raw).hexdigest()
        key=r['tender_id']+'/'+r['lot_id']
        if key in reviews:r['review']=reviews[key]
        inputs.append(r)
        provenance.append({'key':key,'extract_file':path.name,'extract_sha256':r['extract_sha256'],**extract['provenance']})
    if set(reviews)-{r['tender_id']+'/'+r['lot_id'] for r in inputs}:raise ValueError('Review references unknown lot')
    normalized=[normalize_lot(r) for r in inputs]
    result=screen(normalized)
    labels=json.loads(labels_path.read_text()) if labels_path else []
    evaluation=evaluate(normalized,labels)
    out.mkdir(parents=True,exist_ok=True)
    dump(out/'normalized.json',result['records']);dump(out/'screening.json',result)
    dump(out/'evaluation.json',evaluation);dump(out/'provenance.json',provenance)
    dump(out/'assumption-sensitivity.json',assumptions(inputs))
    excluded=[{'key':r['key'],'tenderID':r.get('tenderID'),'source_url':r.get('source_url'),
               'reasons':r['exclusion_reasons'],'review_status':r['review_status']} for r in result['records'] if not r['comparison_eligible']]
    dump(out/'exclusions.json',excluded)
    csv_file(out/'normalized.csv',result['records'],['key','tenderID','publication_date','status','source_kind','selected_stage','amount','currency','quantity_sheets','unit_price','comparison_eligible','exclusion_reasons','source_url','attribution'])
    csv_file(out/'exclusions.csv',excluded,['key','tenderID','reasons','review_status','source_url'])
    stages=[dict(o,key=r['key'],tenderID=r.get('tenderID')) for r in result['records'] for o in r['observations']]
    csv_file(out/'stage-observations.csv',stages,['key','tenderID','id','stage','status','amount','currency','vat_included','amount_net','quantity_version','quantity_link_reviewed','amendment_reconciled'])
    dump(out/'holdout-review-template.json',[{'key':r['key'],'annotator_type':None,'evidence':[],
         'comparable':None,'unusual':None,'reviewer_id':None,'reviewed_at':None,'notes':''} for r in result['records']])
    reasons=Counter(reason for r in result['records'] for reason in r['exclusion_reasons'])
    summary={'counts':result['counts'],'stage_counts':dict(sorted(Counter(s['stage'] for s in stages).items())),
             'exclusion_reason_counts':dict(sorted(reasons.items())),
             'human_reviewed_holdout':evaluation['accepted_label_count'],
             'milestone_status':'comparability_audit_only' if not evaluation['validation_gate_met'] else 'reviewed_holdout_metrics_available',
             'reporting_period':['2025-01-01','2025-03-31'],'date_basis':'API dateCreated',
             'sampling':'search-discovered convenience sample, one lot per tender; not representative',
             'unmet_gates':['independent human reconciliation','document-supported goods/fiscal/delivery/payment comparability',
                            'empirical screening precision and false-exclusion validation'] if not evaluation['validation_gate_met'] else []}
    dump(out/'summary.json',summary)
    _html(out/'report.html',result,summary,evaluation)
    _markdown(out/'REPORT.md',summary,evaluation)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.json'}
    dump(out/'SHA256SUMS.json',hashes)
    return summary


def _evaluation_text(evaluation):
    text = f"Independent holdout labels accepted from supplied provenance: {evaluation['accepted_label_count']}. "
    for name, metric in evaluation.get('metrics', {}).items():
        value = 'unavailable' if metric['estimate'] is None else str(metric['estimate'])
        text += f"{name}: {value} (numerator {metric['numerator']}, denominator {metric['denominator']}, Wilson 95% interval {metric['wilson_95']}). "
    return text


def _markdown(path, summary, evaluation):
    c=summary['counts']
    text=f'''# Prozorro civilian paper comparability audit

The saved demonstration contains {c['unique_lots']} unique public lots from January through March 2025. {c['arithmetic_computable']} have a computable active-contract price under the strict stage and unit rules. {c['comparison_eligible']} pass all comparison gates, and {c['real_leads']} real screening leads are emitted.

The result is a comparability audit. It does not establish that the screening method is useful. {_evaluation_text(evaluation)} Exclusion records a limit in the available evidence. It does not establish that a purchase was wrong.

Publication-window membership uses API dateCreated and is checked against the public tender identifier. Contract and payment records are current at acquisition, potentially amended after the reporting period. The sample was found through public search and is not representative. Each tender contributes one explicit lot or one documented tender-wide `single` lot.

Amounts retain their original procurement stage. Reported amountPaid values are not independently reconciled cash payments. A terminated contract is preserved but excluded by this prototype's active-contract screening policy. Mixed item lines and unverified package conversions remain unresolved. Net and gross values, VAT flags and currencies are never inferred.

## Data-quality reasons

Counts overlap because each lot may have several unresolved gates.

| Reason | Lots |
|---|---:|
'''
    text+=''.join(f'| {k} | {v} |\n' for k,v in summary['exclusion_reason_counts'].items())
    text+='''
## Reproduction and evidence

Run `bash scripts/reproduce.sh` from the project directory. It runs the offline test suite, rebuilds this report from retained public extracts and checks exact rational arithmetic. `provenance.json` binds each row to an extract hash, source-response hash, public API URL and acquisition time. `stage-observations.csv` preserves amounts by stage. `report.html` supplies per-lot evidence panels and public document-metadata references. Source: [Prozorro](https://prozorro.gov.ua/openprocurement), reused with attribution under its observed public open-data statement.

`assumption-sensitivity.json` shows unsupported package-size stress tests separately from baseline results. Nine screening-threshold combinations are in `screening.json`. Empty lead sets cannot establish robustness when groups are ineligible. UAH is the only permitted real comparison currency; no FX rates were applied.

## Validation still required

Independent review must cover original records and contract documents, goods quality, quantity versions, fiscal treatment, delivery costs, payment terms and holdout labels. Record evidence and reviewer identity for every accepted review. Supplied review assertions remain subject to provenance verification. The evaluation function computes proportions and Wilson intervals only when the relevant denominators exist. Those intervals do not correct this sample's selection bias.

Synthetic fixtures exercise packaging, decimals, missing taxes, cancellations, amendments, duplicate stages, screening and evaluation behavior. They are separate from the fifty-lot real dataset and cannot establish real-world error rates. No procurement actor is accused of wrongdoing.
'''
    path.write_text(text,encoding='utf-8')


def _link(url, label):
    if isinstance(url,str) and url.startswith('https://'):
        return '<a rel="noreferrer" href="'+escape(url,quote=True)+'">'+escape(str(label))+'</a>'
    return escape(str(label))


def _html(path,result,summary,evaluation):
    c=summary['counts']; cards=''
    for r in result['records']:
        stage_rows=''.join('<tr>'+''.join('<td>'+escape(str(o.get(k,'unknown')) )+'</td>' for k in ['stage','status','amount','currency','quantity_link_reviewed'])+'</tr>' for o in r['observations'])
        item_rows=''.join('<li>'+escape(str(i.get('description','')))+'<br>Quantity '+escape(str(i.get('quantity')))+'; declared unit '+escape(str(i.get('unit_name')))+' ('+escape(str(i.get('unit_code')))+'); canonical unit '+escape(str(i.get('unit')) )+'</li>' for i in r['items'])
        docs=[]
        for d in r.get('documents',[]):
            docs.append(_link(r['source_url']+'/documents/'+d['id'],d.get('documentType','Document metadata')+' '+d['id']))
        for group in r.get('contract_documents',[]):
            for d in group['documents']:
                base=group.get('source_url')
                if base:docs.append(_link(base+'/documents/'+d['id'],d.get('documentType','Contract metadata')+' '+d['id']))
        cards+=f'''<details><summary>{escape(str(r.get('tenderID')))} · {escape(str(r.get('title','')))}</summary>
<p>{_link(r.get('source_url'),'API source')} · {_link(r.get('public_url'),'Published lot')} · Acquired {escape(str(r.get('retrieved_at')))}</p>
<p>Lot key <code>{escape(r['key'])}</code>. Review: {escape(r['review_status'])}. Status: {escape(str(r.get('status')))}.</p>
<ul>{item_rows}</ul><p>Strict active-contract price per sheet: {escape(str(r.get('unit_price')))} {escape(str(r.get('currency')))}. Comparison eligible: {r['comparison_eligible']}.</p>
<div class="table-wrap"><table><thead><tr><th scope="col">Stage</th><th scope="col">Status</th><th scope="col">Amount</th><th scope="col">Currency</th><th scope="col">Quantity linked</th></tr></thead><tbody>{stage_rows}</tbody></table></div>
<p><b>Exclusions:</b> {escape(', '.join(r['exclusion_reasons']))}</p><p>Source response SHA-256: <code>{escape(str(r.get('response_sha256')))}</code><br>Extract SHA-256: <code>{escape(str(r.get('extract_sha256')))}</code></p>
<p>Documents are metadata references. Content has not been reviewed: {' · '.join(docs) or 'No retained public document metadata.'}</p></details>'''
    reasons=''.join('<tr><td>'+escape(k)+'</td><td>'+str(v)+'</td></tr>' for k,v in summary['exclusion_reason_counts'].items())
    html=_page('Prozorro · Civilian paper comparability audit', f'''
<div class="toolbar"><div class="kicker">Project 31 · public-source audit · January–March 2025</div>{_THEME_CONTROL}</div><h1>Which paper purchases can actually be compared?</h1>
<div class="notice"><strong>Comparability audit. Screening usefulness has not been established.</strong><p>Unknown terms stay unresolved. Independent holdout labels accepted: {evaluation['accepted_label_count']}. An unusual price alone would not establish misconduct.</p></div>
<div class="stats"><div class="stat"><b>{c['unique_lots']}</b>unique real lots</div><div class="stat"><b>{c['arithmetic_computable']}</b>strict prices computable</div><div class="stat"><b>{c['comparison_eligible']}</b>comparison eligible</div><div class="stat"><b>{c['real_leads']}</b>real leads emitted</div></div>
<p>This convenience sample covers civilian A4 paper candidates. Each lot keeps estimates, bids, awards, current or amended contracts and reported payments separate. The acquisition timestamp describes current source state, including later changes. Source: {_link('https://prozorro.gov.ua/openprocurement','Prozorro public procurement data')}.</p>
<h2>Why comparisons are withheld</h2><p>Reason counts overlap. These are evidence limitations, not accusations or measured false exclusions.</p><table><thead><tr><th scope="col">Unresolved gate</th><th scope="col">Lots</th></tr></thead><tbody>{reasons}</tbody></table>
<h2>Evaluation</h2><p>{escape(_evaluation_text(evaluation))} Zero emitted leads does not imply zero false-flag risk. Review evidence and holdout labels require independent verification before making usefulness claims.</p>
<h2>Evidence by lot</h2><p>Open each panel for quantities, accounting stages, exclusions and source references. Personal contacts and delivery locations are omitted.</p>{cards}
<p><small>Each record carries its annotator provenance. The program checks evidence fields but cannot certify reviewer independence or document meaning. No FX conversion, deployment or remote publication is performed by report generation.</small></p>''')
    path.write_text(html,encoding='utf-8')


def synthetic_demo(out:Path):
    values=['9800','9900','10000','10100','10200','20000']
    inputs=[]
    for n,v in enumerate(values):
        r=example_lot();r['tender_id']=f'synthetic-{n:02}';r['observations'][0]['amount']=v;inputs.append(r)
    result=screen([normalize_lot(r) for r in inputs]);out.mkdir(parents=True,exist_ok=True)
    dump(out/'inputs.json',inputs);dump(out/'screening.json',result)
    scaled=deepcopy(inputs)
    for r in scaled:r['observations'][0]['amount']=str(Decimal(r['observations'][0]['amount'])*Decimal('1.2'))
    scaled_result=screen([normalize_lot(r) for r in scaled])
    dump(out/'checks.json',{'source_kind':'synthetic','author':'assistant_fixture_author','seed':'none; enumerated constants',
          'expected_lead_keys':['synthetic-05/single'],'actual_lead_keys':[r['key'] for r in result['leads']],
          'common_currency_scaling_preserves_leads':[r['key'] for r in result['leads']]==[r['key'] for r in scaled_result['leads']],
          'real_world_validation':False})
    _synthetic_html(out/'report.html', result)
    return result['counts']


def _synthetic_html(path, result):
    leads = {r['key'] for r in result['leads']}
    rows = ''
    for record in result['records']:
        status = '<span class="fixture-lead">Synthetic review lead</span>' if record['key'] in leads else 'No synthetic lead'
        rows += ('<tr><td>'+escape(record['key'])+'</td><td>'+escape(str(record['amount']))+
                 '</td><td>'+escape(str(record['quantity_sheets']))+'</td><td>'+escape(str(record['unit_price']))+
                 '</td><td>'+status+'</td></tr>')
    c = result['counts']
    content = f'''<div class="toolbar"><div class="kicker">Project 31 · synthetic algorithm fixture</div>{_THEME_CONTROL}</div>
<h1>Synthetic screening exercise</h1>
<div class="notice"><strong>All records on this page are synthetic.</strong><p>These assistant-authored constants exercise the algorithm. They do not establish real-world error rates or independent human validation. The real dataset remains a comparability audit with no real screening leads.</p></div>
<div class="stats"><div class="stat"><b>{c['unique_lots']}</b>synthetic lots</div><div class="stat"><b>{c['synthetic_leads']}</b>synthetic review leads</div><div class="stat"><b>{c['real_leads']}</b>real leads</div></div>
<p>The fixture uses six comparable 50,000-sheet purchases in UAH. Its known high-price example checks the screening path. A separate check applies a common currency scaling factor; this is not empirical FX validation.</p>
<div class="table-wrap"><table><thead><tr><th scope="col">Fixture key</th><th scope="col">Amount (UAH)</th><th scope="col">Sheets</th><th scope="col">UAH per sheet</th><th scope="col">Screening status</th></tr></thead><tbody>{rows}</tbody></table></div>
<p><a href="checks.json">Fixture expectations and checks</a> · <a href="screening.json">Full synthetic screening output</a> · <a href="../real/report.html">Real comparability audit</a></p>
<p><small>No source procurement records or actors appear in this fixture. Review leads do not establish misconduct. Report generation makes no network requests.</small></p>'''
    path.write_text(_page('Prozorro · Synthetic screening exercise', content), encoding='utf-8')
