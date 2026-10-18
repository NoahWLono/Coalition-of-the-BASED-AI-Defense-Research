#!/usr/bin/env python3
"""Summarize sealed suite results without inventing missing runs."""
import argparse,hashlib,json,statistics,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from failsafelab.evaluate import evaluate_run
from failsafelab.controls import control_accepted

def main():
 p=argparse.ArgumentParser();p.add_argument('suite',type=Path);p.add_argument('--reevaluate',action='store_true');a=p.parse_args();suite=a.suite.resolve()
 index=json.loads((suite/'suite-results.json').read_text()); rows=[]; transitions={}; violations=[]
 for row in index['runs']:
  case=suite/row['run']; run=json.loads((case/'run.json').read_text()); spec=json.loads((case/'scenario.json').read_text());events={e['id']:e for e in map(json.loads,(case/'events.jsonl').read_text().splitlines())}
  result=evaluate_run(case) if a.reevaluate else json.loads((case/'result.json').read_text())
  if a.reevaluate:(case/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  responses=[]
  for i,assertion in enumerate(result['assertions']):
   if assertion['type']=='mode' and 'first_match_sim_s' in assertion:
    e=spec['assertions'][i]['after']
    responses.append({'after':e,'allowed':spec['assertions'][i]['allowed'],'latency_s':round(assertion['first_match_sim_s']-events[e]['sim_s'],3),'deadline_s':spec['assertions'][i]['within_s']})
  clean=run['cleanup']['completed'] and run['cleanup']['child_reaped'] and len((case/'sockets-after.txt').read_text().splitlines())==1
  entry={**row,'outcome':result['outcome'],'control_accepted':control_accepted(result,'disabled') if row['negative_control'] else None,'wall_duration_s':run['wall_duration_s'],'resources':run.get('child_resources',{}),'cleanup_confirmed':clean,'mode_responses':responses,'nonpassing':[{'id':x['id'],'outcome':x['outcome'],'detail':x['detail']} for x in result['checks']+result['assertions'] if x['outcome']!='PASS']}
  rows.append(entry)
  if not clean:violations.append(row['run'])
  if not row['negative_control'] and not row['scenario_id'].startswith('00'):
   transitions.setdefault(row['scenario_id'],{}).setdefault(row['version'],[]).append(entry)
 differences=[]
 for scenario in sorted(transitions):
  lp=suite/'4.5.6'/scenario/'schedule-0.0/params-before.json';rp=suite/'4.5.7'/scenario/'schedule-0.0/params-before.json'
  if lp.exists() and rp.exists():
   l=json.loads(lp.read_text());r=json.loads(rp.read_text());delta={k:{'4.5.6':l.get(k),'4.5.7':r.get(k)} for k in sorted(set(l)|set(r)) if l.get(k)!=r.get(k)}
   differences.append({'scenario_id':scenario,'left_count':len(l),'right_count':len(r),'differences':delta})
 replays=[]
 if len(rows)==index['expected_runs']:
  for version in ['4.5.6','4.5.7']:
   case=suite/version/'01-gcs-loss/schedule-0.0'
   if not case.exists():continue
   wrong=json.loads((case/'scenario.json').read_text())
   for assertion in wrong['assertions']:
    if assertion['type']=='mode':assertion['allowed']=[6]
   result=evaluate_run(case,wrong)
   (suite/f'{version}-planted-wrong-mode.json').write_text(json.dumps(result,indent=2)+'\n')
   replays.append({'version':version,'outcome':result['outcome'],'control_accepted':control_accepted(result,'wrong-mode'),'expected':'FAIL','input':'unchanged sealed evidence; LAND9 expectation changed to RTL6'})
  (suite/'negative-replays.json').write_text(json.dumps(replays,indent=2)+'\n')
 problems=[r for r in rows if (r['negative_control'] and r.get('control_accepted') is not True) or (not r['negative_control'] and r['outcome']!='PASS')]
 gates_resolved=len(rows)==index['expected_runs'] and not problems and len(replays)==2 and all(r['control_accepted'] for r in replays) and not violations
 payload={'schema_version':1,'expected_runs':index['expected_runs'],'completed_runs':len(rows),'complete':len(rows)==index['expected_runs'],'gates_resolved':gates_resolved,'replays':replays,'outcomes':dict(Counter(r['outcome'] for r in rows)),'runs':rows,'parameter_comparisons':differences,'cleanup_violations':violations,'evaluator_sha256':hashlib.sha256((ROOT/'src/failsafelab/evaluate.py').read_bytes()).hexdigest(),'max_rss_kib':max((r['resources'].get('max_rss_kib',0) for r in rows),default=0),'sum_case_wall_duration_s':sum(r['wall_duration_s'] for r in rows)}
 (suite/'comparison.json').write_text(json.dumps(payload,indent=2)+'\n')
 lines=['# Executed release comparison','',f"State: {'complete' if payload['complete'] else 'in progress'}; {len(rows)} of {index['expected_runs']} planned simulator runs have results.",'','This report is derived from recorded SITL evidence. It establishes only the listed assertions for this simulator, vehicle model and configuration. Assistant-authored scenarios and trace inspection are not qualified human certification.','','## Scenario results','','| Scenario | 4.5.6 outcomes | 4.5.7 outcomes | LAND response range, simulation s |','| --- | --- | --- | --- |']
 for scenario,versions in sorted(transitions.items()):
  vals=[z['latency_s'] for rs in versions.values() for r in rs for z in r['mode_responses'] if 9 in z['allowed']]
  labels=['; '.join(f"{r['schedule_offset_s']:g}s offset: {r['outcome']}" for r in versions.get(v,[])) or 'not executed' for v in ['4.5.6','4.5.7']]
  interval=f'{min(vals):.3f} to {max(vals):.3f}' if vals else 'no LAND assertion'
  lines.append(f'| {scenario} | {labels[0]} | {labels[1]} | {interval} |')
 lines+=['','Response values use the last SYSTEM_TIME sample at packet reception. Clock sampling is 0.1 s and heartbeat sampling is 0.2 s; small latency differences within those intervals do not establish a release regression. The DataFlash crosscheck uses onboard microsecond timestamps.','','## Configuration and controls','',f"Full parameter snapshots compared for {len(differences)} primary scenario pairs. Pairs with any differing value: {sum(bool(x['differences']) for x in differences)}. Exact differences, if present, remain in comparison.json.",'']
 for row in rows:
  if row['negative_control']:lines.append(f"- {row['version']} disabled GCS action: {row['outcome']}. Qualified expected mismatch: {row['control_accepted']}. This control retains the enabled-action expectation.")
 for item in json.loads((suite/'negative-replays.json').read_text()) if (suite/'negative-replays.json').exists() else []:
  lines.append(f"- {item['version']} wrong-mode replay: {item['outcome']}. Qualified targeted mismatch: {item.get('control_accepted',False)}. The original packets were unchanged.")
 lines+=['','## Resources and cleanup','',f"Sum of scenario wall times: {payload['sum_case_wall_duration_s']:.1f} s. Largest recorded child maximum RSS: {payload['max_rss_kib']/1024:.1f} MiB. Cleanup or remaining-listener violations: {len(violations)}.",'','## Unresolved outcomes','']
 if problems:
  for r in problems:
   lines.append(f"- {r['run']}: {r['outcome']}; "+'; '.join(x['detail'] for x in r['nonpassing']))
 else:lines.append('No unresolved scenario outcome among the completed runs. Missing planned runs and unqualified replay controls remain unresolved until all gates are resolved.')
 if not all(r.get('control_accepted') for r in replays) or len(replays)!=2:lines.append('Replay control acceptance is missing or unresolved.')
 lines.append(f'All full-suite gates resolved: {gates_resolved}.')
 (suite/'comparison.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({k:v for k,v in payload.items() if k not in ['runs','parameter_comparisons']},indent=2))
 return 0 if gates_resolved else 1
if __name__=='__main__':raise SystemExit(main())
