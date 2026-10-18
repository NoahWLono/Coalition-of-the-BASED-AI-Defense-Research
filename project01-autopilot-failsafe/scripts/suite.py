#!/usr/bin/env python3
"""Serial experiment orchestration; evaluator outcomes never alter expectations."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from failsafelab.evaluate import evaluate_run
from failsafelab.controls import control_accepted

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--stage',choices=['starter','full'],default='full');p.add_argument('--resume',action='store_true');a=p.parse_args()
 out=a.output.resolve();
 if not out.is_relative_to(ROOT/'evidence') or out==ROOT/'evidence':raise SystemExit('Output must be inside project evidence/')
 out.mkdir(parents=True,exist_ok=True)
 plan=[]
 def add(v,i,offset=0):
  path=next((ROOT/'scenarios').glob(f'{i:02d}-*.json'))
  plan.append((v,path,offset))
 add('4.5.6',0)
 for i in range(1,4):add('4.5.6',i)
 if a.stage=='full':
  for i in range(4,13):add('4.5.6',i)
  for i in range(13):add('4.5.7',i)
  for v in ['4.5.6','4.5.7']:
   for i in range(1,13):add(v,i,.7)
   for i in [1,2,9]:add(v,i,1.4)
   add(v,90)
 rows=[]; started=time.monotonic()
 for index,(version,scenario,offset) in enumerate(plan):
  if time.monotonic()-started>3600:raise SystemExit('one-hour suite wall budget exhausted')
  name=f'{version}/{scenario.stem}/schedule-{offset:.1f}'
  case=out/name
  cmd=['bash',str(ROOT/'scripts/isolated-case.sh'),'--scenario',str(scenario),'--version',version,'--output',str(case),'--offset',str(offset)]
  if not(case.exists() and a.resume):
   case.parent.mkdir(parents=True,exist_ok=True)
   with (case.parent/f'{case.name}.console.log').open('w') as log:
    result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=195)
  result=evaluate_run(case)
  (case/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  row={'run':name,'version':version,'scenario_id':scenario.stem,'schedule_offset_s':offset,'outcome':result['outcome'],'negative_control':scenario.stem.startswith('90-'),'command':cmd,'control_accepted':control_accepted(result,'disabled') if scenario.stem.startswith('90-') else None}
  rows.append(row)
  (out/'suite-results.json').write_text(json.dumps({'schema_version':1,'stage':a.stage,'expected_runs':len(plan),'completed_runs':len(rows),'wall_duration_s':time.monotonic()-started,'runs':rows},indent=2)+'\n')
  print(f'{index+1}/{len(plan)} {name}: {result["outcome"]}',flush=True)
  if scenario.stem=='00-baseline' and result['outcome']!='PASS':raise SystemExit('baseline gate failed; evidence preserved')
  if a.stage=='starter' and result['outcome']!='PASS':raise SystemExit('starter gate failed; evidence preserved')
 # Replay actual successful GCS evidence with an intentionally wrong expected mode.
 demos=[]
 for v in (['4.5.6'] if a.stage=='starter' else ['4.5.6','4.5.7']):
  case=out/v/'01-gcs-loss'/'schedule-0.0';wrong=json.loads((case/'scenario.json').read_text())
  for assertion in wrong['assertions']:
   if assertion['type']=='mode':assertion['allowed']=[6]
  result=evaluate_run(case,scenario_override=wrong)
  target=out/f'{v}-planted-wrong-mode.json';target.write_text(json.dumps(result,indent=2)+'\n')
  demos.append({'version':v,'outcome':result['outcome'],'expected':'FAIL','control_accepted':control_accepted(result,'wrong-mode'),'input':'original immutable RX/TX evidence; assertion alone changed LAND9 to RTL6'})
 (out/'negative-replays.json').write_text(json.dumps(demos,indent=2)+'\n')
 clean=all((r.get('control_accepted') is True if r['negative_control'] else r['outcome']=='PASS') for r in rows) and all(r.get('control_accepted') is True for r in demos)
 print('ALL GATES RESOLVED' if clean else 'UNRESOLVED GATES: inspect suite-results.json',flush=True)
 return 0 if clean else 1
if __name__=='__main__':raise SystemExit(main())
