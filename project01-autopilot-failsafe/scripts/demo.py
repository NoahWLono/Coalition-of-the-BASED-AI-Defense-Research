#!/usr/bin/env python3
"""Show an actual passing trace and a deliberately rejected wrong assertion."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from failsafelab.evaluate import evaluate_run
from failsafelab.controls import control_accepted
p=argparse.ArgumentParser();p.add_argument('run',nargs='?',type=Path,default=ROOT/'evidence/full/4.5.6/01-gcs-loss/schedule-0.0');a=p.parse_args()
original=evaluate_run(a.run)
wrong=json.loads((a.run/'scenario.json').read_text())
for assertion in wrong['assertions']:
 if assertion['type']=='mode':assertion['allowed']=[6]
regression=evaluate_run(a.run,wrong)
print('Actual SITL trace:',a.run)
print('Configured assertion: GCS heartbeat interruption -> LAND (mode 9)')
print('Original evidence:',original['outcome'])
for assertion in original['assertions']:
 if assertion['type'] in ['heartbeat_gap','text','mode','disarmed']:
  print(' ',assertion['type'],assertion['outcome'],assertion.get('first_match_sim_s',assertion.get('window_sim_s')))
print('Planted oracle regression: require RTL (mode 6) for that same immutable trace')
print('Wrong expectation:',regression['outcome'])
print('This is a detector demonstration, not an observed autopilot release regression.')
raise SystemExit(0 if original['outcome']=='PASS' and control_accepted(regression,'wrong-mode') else 1)
