#!/usr/bin/env python3
"""Audit provenance and isolation records after the suite, without launching SITL."""
import argparse,hashlib,json,os,sys
from pathlib import Path
from pymavlink import mavutil
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('suite',type=Path);a=p.parse_args();suite=a.suite.resolve()
 summary=json.loads((suite/'comparison.json').read_text());manifest=json.loads((ROOT/'manifest.json').read_text())
 pins={r['version']:r for r in manifest['releases']};files={r['path']:r for r in manifest['files']};audits=[]
 for row in summary['runs']:
  case=suite/row['run'];r=json.loads((case/'run.json').read_text()); net=json.loads((case/'network-before.json').read_text());fds=json.loads((case/'simulator-fds.json').read_text());events={e['id']:e for e in map(json.loads,(case/'events.jsonl').read_text().splitlines())}
  v=r['version'];binary=files[f'vendor/{v}/arducopter'];m=mavutil.mavlink_connection(str(case/'rx.tlog'));av=m.recv_match(type='AUTOPILOT_VERSION');m.close()
  live_git=bytes(av.flight_custom_version).decode('ascii') if av else None
  config_ok=all(digest(case/'config'/Path(f).name)==info['sha256'] for f,info in files.items() if f.startswith('config/'))
  previous=-1;clock_previous=-1;seq_previous=-1;timing_ok=True
  with (case/'timing.jsonl').open() as stream:
   for line in stream:
    x=json.loads(line)
    timing_ok &= x['host_monotonic_ns']>=previous and x['sim_s']>=clock_previous and x['rx_sequence']==seq_previous+1
    previous=x['host_monotonic_ns'];clock_previous=x['sim_s'];seq_previous=x['rx_sequence']
  start=events['baseline_ready'];end=events['scenario_end'];observed_speed=(end['sim_s']-start['sim_s'])/((end['host_monotonic_ns']-start['host_monotonic_ns'])/1e9)
  checks={'binary_pin':r['binary_sha256']==binary['sha256'],'live_firmware_commit':live_git==pins[v]['commit'][:8], 'config_pins':config_ok,'parameter_readback':json.loads((case/'parameter-check.json').read_text())=={},'private_network':net['namespace']!=net['host_namespace'] and [i['ifname'] for i in net['interfaces']]==['lo'] and not net['routes'].strip(),'no_hardware_fd':all(not value.startswith('/dev/') or value in ['/dev/null','/dev/urandom','/dev/random','/dev/zero'] for value in fds.values()),'no_hardware_uart':not any(str(arg).startswith('uart:') for arg in r['command']),'monotonic_timing':bool(timing_ok),'cleanup':row['cleanup_confirmed']}
  audits.append({'run':row['run'],'checks':checks,'live_firmware_commit':live_git,'runner_sha256':digest(case/'runner-source.py'),'observed_speedup':observed_speed,'namespace_socket_snapshot':(case/'sockets.txt').read_text()})
 unresolved=[{'run':r['run'],'failed':[k for k,v in r['checks'].items() if not v]} for r in audits if not all(r['checks'].values())]
 # Inspect actual host processes by executable path, without matching this checker command line.
 running=[]
 for entry in Path('/proc').iterdir():
  if not entry.name.isdigit():continue
  try:
   target=Path(os.readlink(entry/'exe'))
   if target.name=='arducopter' and target.is_relative_to(ROOT):running.append(int(entry.name))
  except (OSError,ValueError):pass
 result={'schema_version':1,'runs_audited':len(audits),'checks_per_run':9,'checks_evaluated':sum(len(r['checks']) for r in audits),'scenario_gates_resolved':summary['gates_resolved'],'unresolved':unresolved,'remaining_project_simulator_pids':running,'all_checks_passed':len(audits)==58 and not unresolved and not running,'runner_source_hashes':sorted({r['runner_sha256'] for r in audits}),'observed_speedup_range':[min(r['observed_speedup'] for r in audits),max(r['observed_speedup'] for r in audits)],'runs':audits}
 (suite/'provenance-isolation-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='runs'},indent=2))
 return 0 if result['all_checks_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
