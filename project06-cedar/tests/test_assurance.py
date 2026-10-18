import json
from copy import deepcopy
from cedar.ingest import load_corpus,ledger,digest
from cedar.assurance import software_assurance,inventory_errors


def test_unidentified_component_is_unresolved():
    i=load_corpus('data/slice'); r=software_assurance(i,'P01',ledger(i),'2026-10-17')
    assert r and r[0]['disposition']=='unresolved'
    assert 'identity' in r[0]['reason'].lower()


def test_fixed_exact_version_and_purl_consistency():
    i=load_corpus('data/slice'); source=i['structured']['inventory/P03.cdx.json']
    inv=json.loads(source['content']); c=inv['components'][0]
    c['version']='1.1.0';c['purl']='pkg:generic/cedar-report-cache@1.1.0'
    source['content']=json.dumps(inv);source['hash']=digest(source['content'])
    assert software_assurance(i,'P03',ledger(i),'2026-10-17')[0]['disposition']=='fixed'
    c['purl']='pkg:generic/cedar-report-cache@1.0.0'
    source['content']=json.dumps(inv)
    assert software_assurance(i,'P03',ledger(i),'2026-10-17')[0]['disposition']=='unresolved'


def test_invalid_schema_and_expired_application_exposure():
    assert inventory_errors({'bomFormat':'NotCycloneDX'})
    i=load_corpus('data/slice'); aa=ledger(i)
    assert software_assurance(i,'P03',aa,'2035-01-01')[0]['disposition']=='unresolved'


def test_undated_exposure_cannot_preserve_unaffected_until_rejected():
    i=load_corpus('data/slice')
    aa=[a for a in ledger(i) if a['package_id']=='P03']
    assert software_assurance(i,'P03',aa,'2026-10-17')[0]['disposition']=='unaffected'
    document=dict(id='P03-undated-exposure',package_id='P03',supplier_id='S02',version=1,
        supersedes=[],content='| A_01 | affected | text | declaration | 2026-99-01 | 2027-10-01 | Contradictory synthetic exposure with unknown validity. |')
    i['documents'].append(document)
    aa=[a for a in ledger(i) if a['package_id']=='P03']
    ambiguous=next(a for a in aa if a['document_id']==document['id'])
    result=software_assurance(i,'P03',aa,'2026-10-17')[0]
    assert result['disposition']=='unresolved'
    assert ambiguous['id'] in result['assertions']
    ambiguous['review_status']='rejected'
    assert software_assurance(i,'P03',aa,'2026-10-17')[0]['disposition']=='unaffected'
