import json
from decimal import Decimal
from copy import deepcopy
from cedar.ingest import load_corpus,ledger,digest
from cedar.engine import evaluate
from cedar.assurance import inventory_errors


def test_slice_independently_authored_expectations_and_citations():
    expected=json.load(open('evaluation/ground_truth.json'))['scopes']['slice']['v1']['packages']
    inputs=load_corpus('data/slice');e=evaluate(inputs)
    assert len(e['requirements'])==8 and len(e['packages'])==3
    for p in e['packages']:
        x=expected[p['id']]
        assert p['eligible']==x['eligible']
        assert Decimal(str(p['cost']['known_total']))==Decimal(x['known_total'])
        assert {a['requirement_id']:a['state'] for a in p['assessments']}==x['states']
    sources={d['id']:d for d in inputs['documents']}
    for a in e['assertions']:
        d=sources[a['document_id']];loc=a['location']
        assert '\n'.join(d['content'].splitlines()[loc['start_line']-1:loc['end_line']])==a['original']
        assert digest(d['content'])==a['document_hash']
    inputs['documents'].reverse()
    assert evaluate(inputs)==e


def test_every_unconditional_eligibility_has_all_required_evidence():
    for scope in ['slice','full']:
        from pathlib import Path
        if not Path('data',scope,'catalog.json').exists():continue
        e=evaluate(load_corpus('data/'+scope))
        required={r['id'] for r in e['requirements'] if r['mode']=='mandatory'}
        for p in e['packages']:
            if p['eligible']:
                assert all(a['state'] in {'supported','not_applicable'} for a in p['assessments'] if a['requirement_id'] in required)
            else:
                assert any(a['state'] not in {'supported','not_applicable'} for a in p['assessments'] if a['requirement_id'] in required)


def test_supersession_preserves_source_but_changes_support():
    e=evaluate(load_corpus('data/slice',amendments=['AMD01']))
    p=next(p for p in e['packages'] if p['id']=='P03')
    assert not p['eligible']
    a=next(a for a in p['assessments'] if a['requirement_id']=='R03')
    assert a['state']=='not_satisfied'
    assert any(a['document_id']=='P03-terms-v1' and a['superseded'] for a in e['assertions'])


def test_independent_cost_scenarios_and_unknown_score_interval():
    i=load_corpus('data/slice')
    for assumptions,total in [({'years':2},143016),({'replacements_per_aircraft_per_year':2},162654.48),({'include_optional':True},156654.48)]:
        p=next(p for p in evaluate(i,assumptions)['packages'] if p['id']=='P03')
        assert p['cost']['known_total']==total
    e=evaluate(i)
    p=next(p for p in e['packages'] if p['id']=='P05')
    a=next(a for a in p['assessments'] if a['requirement_id']=='R19')
    assert [a['score_low'],a['score_high']]==[0,100]


def test_full_480_expected_assessments_and_answer_key_isolation(monkeypatch):
    from pathlib import Path
    expected=json.loads(Path('evaluation/ground_truth.json').read_text())['scopes']['full']['v1']['packages']
    original=Path.read_text;original_bytes=Path.read_bytes
    def forbid(path,*a,**kw):
        assert 'evaluation' not in path.parts, 'Runtime must not read an answer key'
        return original(path,*a,**kw)
    def forbid_bytes(path,*a,**kw):
        assert 'evaluation' not in path.parts, 'Runtime must not read an answer key'
        return original_bytes(path,*a,**kw)
    monkeypatch.setattr(Path,'read_text',forbid);monkeypatch.setattr(Path,'read_bytes',forbid_bytes)
    e=evaluate(load_corpus('data/full'))
    assert len(e['requirements'])==40 and len(e['packages'])==12
    for p in e['packages']:
        assert {a['requirement_id']:a['state'] for a in p['assessments']}==expected[p['id']]['states']
    assert {'dominant':'P11','dominated':'P12'} in e['dominance']
    cases=e['sensitivity']['cases']
    assert cases[0]['guaranteed_leaders']==['P11'] and cases[-1]['guaranteed_leaders']==['P07']
