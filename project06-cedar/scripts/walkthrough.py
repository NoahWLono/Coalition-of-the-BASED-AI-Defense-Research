"""Executable API walkthrough; no browser or external service required."""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from cedar.app import create_app
from cedar.ingest import load_corpus,digest
from cedar.store import Store
from cedar.export import verify_package


def run(scope='full',output=Path('artifacts')):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    inputs=load_corpus('data/'+scope)
    steps=[]
    with tempfile.TemporaryDirectory(prefix='cedar-walkthrough-') as tmp:
        client=TestClient(create_app(Store(Path(tmp)/'demo.sqlite',inputs),test_mode=True))
        def sign(role):
            r=client.post('/api/login',json={'role':role,'password':'cedar-'+role});r.raise_for_status()
            return {'X-CSRF-Token':r.json()['csrf']}
        def post(path,body,h):
            r=client.post(path,json=body,headers=h);r.raise_for_status();return r.json()
        initial=client.get('/api/state').json();revision=initial['revision']
        cheap=min(initial['evaluation']['packages'],key=lambda p:p['cost']['known_total'])
        assert not cheap['eligible'] and cheap['cost']['upper_total'] is None
        steps.append({'step':'import and inspect cheapest bid','package_id':cheap['id'],'known_subtotal':cheap['cost']['known_total'],'eligible':cheap['eligible'],'open_costs':cheap['cost']['open_exposures']})
        h=sign('analyst')
        changed=post('/api/settings',{'expected_revision':revision,'assumptions':{'replacements_per_aircraft_per_year':2}},h)
        revision=changed['revision']
        steps.append({'step':'change replacement assumption','revision':revision,'P03_total':next(p['cost']['known_total'] for p in changed['evaluation']['packages'] if p['id']=='P03')})
        first=post('/api/snapshots',{'expected_revision':revision,'package_id':'P03','decision':'eligible','rationale':'Retain Birch Inspect Standard for documentary consideration under the selected evidence and replacement assumptions. All products and evidence are synthetic.'},h)
        denied=client.post('/api/snapshots/'+first['id']+'/approve',headers=h,json={'expected_revision':revision,'note':'Analyst must be refused'})
        assert denied.status_code==403
        post('/api/snapshots/'+first['id']+'/review',{'expected_revision':revision,'note':'Demonstration technical review: source references, documentary gates and cost assumptions checked.'},sign('reviewer'))
        post('/api/snapshots/'+first['id']+'/approve',{'expected_revision':revision,'note':'Demonstration approval for consideration only; no purchase authorized.'},sign('approver'))
        approved=client.get('/api/state').json()['snapshots'][0];assert approved['status']=='approved'
        steps.append({'step':'separate review and approval','snapshot':first['id'],'status':'approved','analyst_approval_http':denied.status_code})
        amended=post('/api/amendments',{'expected_revision':revision,'id':'AMD01'},sign('analyst'));revision=amended['revision']
        assert amended['snapshots'][0]['status']=='stale'
        assert not next(p for p in amended['evaluation']['packages'] if p['id']=='P03')['eligible']
        steps.append({'step':'amendment and invalidation','revision':revision,'old_snapshot_status':'stale','changes':amended['changes'][-1]})
        stale_bytes=client.get('/api/export/'+first['id']).content
        assert verify_package(stale_bytes)['valid']
        (output/(scope+'-stale-decision.zip')).write_bytes(stale_bytes)
        h=sign('analyst')
        second=post('/api/snapshots',{'expected_revision':revision,'package_id':'P03','decision':'conditional','rationale':'Hold this alternative pending a support commitment meeting the buyer requirement. The amendment reduced documented support from 36 to 24 months. Compare the remaining documentary-eligible alternatives; do not treat this conditional record as an unconditional recommendation.'},h)
        post('/api/snapshots/'+second['id']+'/review',{'expected_revision':revision,'note':'Reviewed the changed support passage, outstanding questions and conditional limitation.'},sign('reviewer'))
        post('/api/snapshots/'+second['id']+'/approve',{'expected_revision':revision,'note':'Approve the recorded hold-for-clarification decision only.'},sign('approver'))
        final=client.get('/api/state').json()
        payload=client.get('/api/export/'+second['id']).content
        result=verify_package(payload);assert result['valid'],result
        package_path=output/(scope+'-decision.zip');package_path.write_bytes(payload)
        steps.append({'step':'review new conditional snapshot and export','snapshot':second['id'],'status':final['snapshots'][0]['status'],'package_sha256':hashlib.sha256(payload).hexdigest(),'verification':result})
    report={'scope':scope,'executed_at':datetime.now(timezone.utc).isoformat(),'packages':len(inputs['packages']),'requirements':len(inputs['requirements']),
        'base_documents':len(inputs['documents']),'steps':steps,'passed':True,'limits':'API replay using synthetic fixtures and public demonstration roles; no human review or customer validation.'}
    (output/('milestone-a.json' if scope=='slice' else 'walkthrough.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps({'passed':True,'scope':scope,'package':str(package_path),'steps':len(steps)}))
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=['slice','full'],default='full');ap.add_argument('--output',type=Path,default=Path('artifacts'))
    args=ap.parse_args();run(args.scope,args.output)
