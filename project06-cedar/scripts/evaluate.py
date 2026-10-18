"""Evaluation-only answer-key consumer. Never imported by the workbench."""
import json
import sys
import time
import resource
import platform
from collections import Counter,defaultdict
from decimal import Decimal
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cedar.ingest import load_corpus,digest
from cedar.engine import evaluate


def run(output='artifacts/evaluation.json'):
    started=time.perf_counter();truth=json.load(open('evaluation/ground_truth.json'));extract=json.load(open('evaluation/extraction_truth.json'))
    report={'executed_at':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'platform':platform.platform(),
        'annotation_provenance':truth['metadata']['authorship'],'scopes':{},'errors':[]}
    for scope in ['slice','full']:
        expected=truth['scopes'][scope];inputs=load_corpus('data/'+scope);e=evaluate(inputs)
        fieldnames=['key','raw_value','unit','evidence_type','valid_from','valid_until']
        expected_rows={};actual_rows={};layouts={}
        for d in extract['scopes'][scope]['documents']:
            if d['stage']!='base':continue
            layouts[d['document_id']]=d['layout']
            for a in d['assertions']:
                expected_rows[(d['document_id'],a['key'],a['occurrence'])]=tuple(a[k] for k in fieldnames)
        seen=Counter()
        for a in e['assertions']:
            seen[(a['document_id'],a['key'])]+=1
            actual_rows[(a['document_id'],a['key'],seen[(a['document_id'],a['key'])])]=tuple(a[k] for k in fieldnames)
        per_layout={}
        for layout in ['table','labels','blocks']:
            ex={k:v for k,v in expected_rows.items() if layouts[k[0]]==layout}
            ac={k:v for k,v in actual_rows.items() if layouts[k[0]]==layout}
            correct=sum(ac.get(k)==v for k,v in ex.items())
            per_layout[layout]={'expected_assertions':len(ex),'extracted_assertions':len(ac),'exact_matches':correct,
                'precision':correct/len(ac) if ac else 0,'recall':correct/len(ex) if ex else 0}
            if correct!=len(ex) or correct!=len(ac):report['errors'].append([scope,'extraction',layout])
        docs={d['id']:d for d in inputs['documents']};bad_citations=[]
        for a in e['assertions']:
            d=docs[a['document_id']];l=a['location']
            if digest(d['content'])!=a['document_hash'] or '\n'.join(d['content'].splitlines()[l['start_line']-1:l['end_line']])!=a['original']:
                bad_citations.append(a['id'])
        assessments=0;assessment_errors=[];false_support=0;cost_checks=0;eligibility_checks=0
        scenarios=[('baseline','v1',[]),('buyer-v2','v2',[])]+[(a['id'],'v1',[a['id']]) for a in inputs['available_amendments']]
        if len(inputs['available_amendments'])>1:scenarios.append(('all-amendments','v1',[a['id'] for a in inputs['available_amendments']]))
        for label,version,amendments in scenarios:
            ii=load_corpus('data/'+scope,version,amendments);ee=evaluate(ii)
            mandatory={r['id'] for r in ii['requirements'] if r['mode']=='mandatory'}
            for p in ee['packages']:
                x=expected['v1']['packages'][p['id']];states=dict(x['states'])
                if version=='v2':states.update(expected.get('v2_state_overrides',{}).get(p['id'],{}))
                for aid in amendments:
                    a=expected['amendments'][aid]
                    if a['package_id']==p['id']:states.update({k:v['after'] for k,v in a['changed_states'].items()})
                for a in p['assessments']:
                    assessments+=1
                    if a['state']!=states[a['requirement_id']]:
                        assessment_errors.append([label,p['id'],a['requirement_id'],a['state'],states[a['requirement_id']]])
                        if a['requirement_id'] in mandatory and a['state']=='supported':false_support+=1
                intended=all(states[r] in {'supported','not_applicable'} for r in mandatory)
                eligibility_checks+=1
                if p['eligible']!=intended:report['errors'].append([scope,label,'eligibility',p['id']])
                cost_checks+=1
                if Decimal(str(p['cost']['known_total']))!=Decimal(x['known_total']):report['errors'].append([scope,label,'cost',p['id']])
        if assessment_errors:report['errors'].extend([[scope]+x for x in assessment_errors])
        if bad_citations:report['errors'].append([scope,'citations',bad_citations])
        reverse=dict(inputs,documents=list(reversed(inputs['documents'])))
        if evaluate(reverse)!=e:report['errors'].append([scope,'document_order'])
        report['scopes'][scope]={'counts':expected['counts'],'baseline_assessments':len(e['packages'])*len(e['requirements']),
            'baseline_eligible':[p['id'] for p in e['packages'] if p['eligible']],
            'baseline_state_counts':dict(Counter(a['state'] for p in e['packages'] for a in p['assessments'])),
            'extraction_by_layout':per_layout,'citation_checks':len(e['assertions']),'unsupported_citations':len(bad_citations),
            'scenarios':[x[0] for x in scenarios],'assessment_checks':assessments,'assessment_errors':len(assessment_errors),
            'false_supported_mandatory':false_support,'cost_checks':cost_checks,'eligibility_checks':eligibility_checks,
            'sensitivity':e['sensitivity'],'dominance':e['dominance']}
    report['runtime_seconds']=round(time.perf_counter()-started,4)
    report['peak_process_rss_mib']=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2)
    report['passed']=not report['errors']
    report['scope_limits']=['Exact-labelled, assistant-generated synthetic layouts; all three were designed for this parser.','No held-out unseen customer corpus, human annotation study, live LLM evaluation or measured user time savings.','Runtime is one local evaluation process; peak RSS includes Python, schema validator and evaluation code.','Independent arithmetic means separately derived calculations; review agents are not independent empirical confirmation.']
    Path(output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'output':output,'assessment_checks':sum(x['assessment_checks'] for x in report['scopes'].values()),'errors':report['errors'],'seconds':report['runtime_seconds'],'rss_mib':report['peak_process_rss_mib']}))
    return report

if __name__=='__main__':sys.exit(0 if run()['passed'] else 1)
