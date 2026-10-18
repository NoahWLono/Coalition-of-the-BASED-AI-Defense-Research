"""Runtime reproductions of the fresh-context source review, plus adjacent bounds."""
import json
import hashlib
from pathlib import Path
import pytest
from cedar.engine import evaluate,assess
from cedar.ingest import load_corpus,parse_document,digest
from cedar.costs import calculate_cost
from cedar.store import Store
from test_engine import doc,row,req


def test_matching_purl_cannot_disappear_due_to_display_name():
    inputs=load_corpus('data/slice');s=inputs['structured']['inventory/P05.cdx.json']
    inv=json.loads(s['content']);inv['components'][0]['name']='Report cache library'
    s['content']=json.dumps(inv);s['hash']=digest(s['content'])
    p=next(p for p in evaluate(inputs)['packages'] if p['id']=='P05')
    assert any(x['id']=='SYNTH-CEDAR-001' and x['disposition']=='affected' for x in p['assurance'])


def test_undated_evidence_prevents_false_support_and_closed_cost():
    aa=parse_document(doc(row()))+parse_document(doc(row(value='unknown').replace('2026-10-01','2026-99-01'),'d2'))
    assert assess(req(),aa,'p1','2026-10-17')['state']=='unresolved'
    aa=parse_document(doc(row('C_support','400','CAD','quotation')))+parse_document(doc(row('C_support','unknown','CAD','quotation').replace('2026-10-01','2026-99-01'),'d2'))
    c=calculate_cost(aa,{},'2026-10-17')
    assert any(x['key']=='C_support' for x in c['open_exposures'])


def test_amendment_logs_software_assurance_changes(tmp_path):
    s=Store(tmp_path/'db',load_corpus('data/slice'));out=s.amend('analyst',0,'AMD01')
    assert any(d['requirement_id']=='assurance:SYNTH-CEDAR-001' and d['before']=='unaffected' and d['after']=='unresolved' for d in out['changes'][-1]['diffs'])


def test_conflicting_exposure_declarations_remain_unresolved():
    inputs=load_corpus('data/slice');d=doc(row('A_01','affected','text','declaration'),'upload')
    d.update(package_id='P03',supplier_id='S02',title='Contradiction',hash=digest(d['content']))
    inputs['documents'].append(d)
    p=next(p for p in evaluate(inputs)['packages'] if p['id']=='P03')
    assert p['assurance'][0]['disposition']=='unresolved'


def test_corpus_hashes_exact_utf8_bytes_and_ignores_undeclared_json(tmp_path):
    import shutil
    root=tmp_path/'corpus';shutil.copytree('data/slice',root)
    p=root/'documents/P01-spec-v1.md';p.write_bytes(p.read_bytes().replace(b'\n',b'\r\n'))
    (root/'not-a-declared-input.json').write_text('{"internal_note":"should not export"}')
    x=load_corpus(root);d=next(d for d in x['documents'] if d['id']=='P01-spec-v1')
    assert d['hash']==hashlib.sha256(p.read_bytes()).hexdigest()
    assert 'not-a-declared-input.json' not in x['structured']


def test_structured_symlink_cannot_leave_corpus(tmp_path):
    import shutil
    root=tmp_path/'corpus';shutil.copytree('data/slice',root)
    outside=tmp_path/'external.json';outside.write_text('[]')
    (root/'advisories.json').unlink();(root/'advisories.json').symlink_to(outside)
    with pytest.raises(ValueError,match='escapes'):
        load_corpus(root)
