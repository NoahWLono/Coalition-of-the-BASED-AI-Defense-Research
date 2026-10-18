"""Bounded SITL controller. Assertions are evaluated separately after teardown."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import resource
import signal
import shutil
import socket
import struct
import subprocess
import time
import traceback
from pymavlink import mavutil

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_FAULT_PARAMS = {'SIM_BATT_VOLTAGE', 'SIM_RC_FAIL', 'SIM_GPS_BYTELOSS'}
MODES = {'GUIDED': 4, 'LAND': 9, 'LOITER': 5, 'ALT_HOLD': 2}

def validate_scenario(s):
    last = -1
    ids = set()
    for e in s['events']:
        if e['id'] in ids or e['at_s'] < last or not 0 <= e['at_s'] < s['duration_s']:
            raise ValueError('duplicate id or unsorted/out-of-range event')
        ids.add(e['id']); last = e['at_s']
        if e['kind'] == 'parameter':
            if e['name'] not in ALLOWED_FAULT_PARAMS:
                raise ValueError('unsupported fault parameter')
            limits = {'SIM_BATT_VOLTAGE': (9.8,13), 'SIM_RC_FAIL':(0,2), 'SIM_GPS_BYTELOSS':(0,100)}
            low, high = limits[e['name']]
            if not low <= e['value'] <= high:
                raise ValueError('fault value outside experimental bounds')
        elif e['kind'] == 'heartbeat':
            if type(e['enabled']) is not bool: raise ValueError('heartbeat value must be boolean')
        elif e['kind'] == 'mode':
            if e['mode'] not in MODES: raise ValueError('unsupported mode')
        else:
            raise ValueError('unsupported event kind')

def isolation_ok(interfaces, current_ns, host_ns):
    return set(interfaces) == {'lo'} and current_ns != host_ns

def validated_output(path):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT/'evidence') or path==ROOT/'evidence':
        raise ValueError('Output must be a subdirectory of project evidence/')
    return path

def json_write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

def file_hash(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()

def seal(directory):
    lines=[]
    for p in sorted(directory.rglob('*')):
        if p.is_file() and p.name not in {'SHA256SUMS','result.json'}:
            lines.append(f'{file_hash(p)}  {p.relative_to(directory)}')
    (directory/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
    for p in directory.rglob('*'):
        if p.is_file() and p.name!='result.json': p.chmod(0o444)

class Controller:
    def __init__(self, output):
        self.output = output
        self.sim_s = 0.0
        self.latest = {}
        self.params = {}
        self.rxseq = 0
        self.heartbeats = True
        self.last_heartbeat_sim = -100
        self.last_heartbeat_wall = 0
        self.start_wall = time.monotonic()
        self.conn = mavutil.mavlink_connection('tcpin:127.0.0.1:5760', source_system=255, source_component=190)
        self.rx = (output/'rx.tlog').open('wb')
        self.tx = (output/'tx.tlog').open('wb')
        self.times = (output/'timing.jsonl').open('w')
        self.events = (output/'events.jsonl').open('w')
        self.conn.mav.set_send_callback(self.sent)
        self.rc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rc.bind(('127.0.0.1',0))
        self.last_rc_wall = 0
        self.process = None
        self.rc_throttle = 1000
    def sent(self, msg):
        self.tx.write(struct.pack('>Q',time.time_ns()//1000)+msg.get_msgbuf())
    def event(self, id, kind, **details):
        e = dict(id=id,kind=kind,sim_s=self.sim_s,host_monotonic_ns=time.monotonic_ns(),host_unix_us=time.time_ns()//1000,**details)
        self.events.write(json.dumps(e)+'\n'); self.events.flush()
        print(json.dumps(e), flush=True)
        return e
    def pump(self):
        if self.process is not None and self.process.poll() is not None:
            raise RuntimeError(f'Simulator exited unexpectedly: {self.process.returncode}')
        if time.monotonic()-self.start_wall > 170:
            raise TimeoutError('170 second controller wall budget exceeded')
        for _ in range(1000):
            m = self.conn.recv_match(blocking=False)
            if m is None: break
            if m.get_type() == 'BAD_DATA': continue
            self.rx.write(struct.pack('>Q',time.time_ns()//1000)+m.get_msgbuf())
            if m.get_type() == 'SYSTEM_TIME': self.sim_s=m.time_boot_ms/1000
            self.latest[m.get_type()]=m
            if m.get_type() == 'PARAM_VALUE': self.params[m.param_id]=m.param_value
            self.times.write(json.dumps({'rx_sequence':self.rxseq,'host_monotonic_ns':time.monotonic_ns(),'sim_s':self.sim_s})+'\n')
            self.rxseq+=1
        now=time.monotonic()
        if self.heartbeats and (self.sim_s-self.last_heartbeat_sim >= .5 or (self.sim_s == 0 and now-self.last_heartbeat_wall > .2)):
            self.conn.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,mavutil.mavlink.MAV_AUTOPILOT_INVALID,0,0,0)
            self.last_heartbeat_sim=self.sim_s; self.last_heartbeat_wall=now
        if now-self.last_rc_wall >= .05:
            channels=[1500,1500,self.rc_throttle,1500,1800,1500,1500,1500]+[1500]*8
            self.rc.sendto(struct.pack('<16H',*channels),('127.0.0.1',5501))
            self.last_rc_wall=now
        time.sleep(.002)
    def until(self, condition, sim_timeout=30, wall_timeout=30):
        ss=self.sim_s; ww=time.monotonic()
        while not condition():
            self.pump()
            if self.sim_s-ss > sim_timeout or time.monotonic()-ww > wall_timeout:
                texts=[str(self.latest.get(n,'')) for n in ['HEARTBEAT','STATUSTEXT','EKF_STATUS_REPORT','GLOBAL_POSITION_INT']]
                raise TimeoutError('condition timed out: '+' | '.join(texts))
    def delay(self, seconds):
        start=self.sim_s
        self.until(lambda:self.sim_s >= start+seconds,seconds+2,30)
    def command(self, command,*values):
        p=list(values)+[0]*7
        self.conn.mav.command_long_send(1,1,command,0,*p[:7])
    def mode(self, mode):
        self.conn.mav.set_mode_send(1,mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,MODES[mode])
    def set_param(self, name, value):
        self.params.pop(name,None)
        self.conn.mav.param_set_send(1,1,name.encode(),float(value),mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        self.until(lambda:name in self.params and abs(self.params[name]-value)<.001,5,10)
    def snapshot(self):
        self.params={}
        self.conn.mav.param_request_list_send(1,1)
        self.until(lambda:'PARAM_VALUE' in self.latest and len(self.params)>=self.latest['PARAM_VALUE'].param_count,35,25)
        return dict(self.params)
    def close(self):
        for f in [self.rx,self.tx,self.times,self.events]: f.close()
        self.conn.close(); self.rc.close()

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(1536*1024**2,1536*1024**2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    cpus=sorted(os.sched_getaffinity(0))[:2]
    os.sched_setaffinity(0,cpus)

def run_case(scenario_path, version, output, offset=0.0):
    s=json.loads(scenario_path.read_text()); validate_scenario(s)
    output=validated_output(output)
    output.mkdir(parents=True,exist_ok=False)
    json_write(output/'scenario.json',s)
    shutil.copyfile(Path(__file__),output/'runner-source.py')
    (output/'config').mkdir()
    for p in (ROOT/'config').glob('*.parm'): shutil.copyfile(p,output/'config'/p.name)
    current_ns=os.readlink('/proc/self/ns/net'); host_ns=os.environ.get('LAB_HOST_NETNS',current_ns)
    interfaces=list(os.listdir('/sys/class/net'))
    # /sys may represent the host mount; ip reports the actual network namespace.
    ip=json.loads(subprocess.check_output(['ip','-j','addr']))
    interfaces=[i['ifname'] for i in ip]
    if not isolation_ok(interfaces,current_ns,host_ns): raise RuntimeError('private loopback-only namespace required')
    json_write(output/'network-before.json',{'interfaces':ip,'routes':subprocess.check_output(['ip','route'],text=True),'namespace':current_ns,'host_namespace':host_ns,'devices':os.listdir('/dev')})
    overrides=''.join(f'{k} {v}\n' for k,v in sorted(s.get('parameters',{}).items()))
    (output/'overrides.parm').write_text(overrides)
    binary=ROOT/'vendor'/version/'arducopter'
    command=[str(binary),'--model','quad','--speedup','4','--synthetic-clock','--home','0.01,0.01,0,0','--start-time','1700000000','--wipe','--defaults',','.join(map(str,[ROOT/'config/base-copter.parm',ROOT/'config/lab.parm',output/'overrides.parm'])),'--serial0','tcpclient:127.0.0.1:5760','--serial1','none','--serial2','none','--serial4','none','--serial5','none','--serial6','none','--serial7','none','--serial8','none']
    # SERIAL3 remains the built-in simulated GPS, never a host UART.
    run={'schema_version':1,'scenario_id':s['id'],'version':version,'binary_sha256':file_hash(binary),'command':command,'schedule_offset_s':offset,'error':None,'returncode':1,'cleanup':{'completed':False,'child_reaped':False},'synthetic':False,'host':{'uname':list(os.uname()),'python':os.sys.version},'timing_model':'SITL synthetic clock; speedup 4; assertion clock SYSTEM_TIME.time_boot_ms'}
    start=time.monotonic(); proc=None; c=None
    out=(output/'sitl.stdout').open('wb')
    try:
        c=Controller(output)
        proc=subprocess.Popen(command,cwd=output,stdout=out,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
        run['pid']=proc.pid
        c.process=proc
        c.until(lambda:'HEARTBEAT' in c.latest,30,20)
        c.conn.mav.request_data_stream_send(1,1,mavutil.mavlink.MAV_DATA_STREAM_ALL,10,1)
        for msgid, interval in [(2,100000),(0,200000),(33,100000),(24,200000),(1,200000),(147,200000),(65,200000),(193,200000)]:
            c.command(mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,msgid,interval)
        c.command(mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,148)
        c.until(lambda:c.sim_s>=25 and 'GPS_RAW_INT' in c.latest and c.latest['GPS_RAW_INT'].fix_type>=3 and 'EKF_STATUS_REPORT' in c.latest and c.latest['EKF_STATUS_REPORT'].flags & 16,70,35)
        before=c.snapshot(); json_write(output/'params-before.json',before)
        expected={}
        for paramfile in [ROOT/'config/base-copter.parm',ROOT/'config/lab.parm',output/'overrides.parm']:
            for line in paramfile.read_text().splitlines():
                line=line.split('#')[0].strip()
                if line:
                    name,value=line.split(); expected[name]=float(value)
        mismatches={k:{'expected':v,'actual':before.get(k)} for k,v in expected.items() if k not in before or abs(before[k]-v)>max(.001,abs(v)*1e-5)}
        json_write(output/'parameter-check.json',mismatches)
        if mismatches: raise RuntimeError('parameter snapshot differs: '+str(mismatches))
        (output/'sockets.txt').write_text(subprocess.check_output(['ss','-lntup'],text=True))
        json_write(output/'simulator-fds.json',{p.name:os.readlink(p) for p in Path(f'/proc/{proc.pid}/fd').iterdir()})
        c.mode('GUIDED'); c.until(lambda:c.latest['HEARTBEAT'].custom_mode==4,10,10)
        c.command(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,1)
        c.until(lambda:c.latest['HEARTBEAT'].base_mode & 128,30,20)
        c.rc_throttle=1500
        c.command(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,0,0,0,0,0,0,12)
        c.until(lambda:'GLOBAL_POSITION_INT' in c.latest and c.latest['GLOBAL_POSITION_INT'].relative_alt>=10500,40,25)
        stable_since=[None]
        def stable_hover():
            pos=c.latest['GLOBAL_POSITION_INT']; hb=c.latest['HEARTBEAT']
            healthy=(10500<=pos.relative_alt<=13500 and abs(pos.vz)<=30 and hb.custom_mode==4 and hb.base_mode&128 and c.latest['GPS_RAW_INT'].fix_type>=3 and c.latest.get('SYS_STATUS') and c.latest['SYS_STATUS'].voltage_battery>11500)
            if not healthy: stable_since[0]=None
            elif stable_since[0] is None: stable_since[0]=c.sim_s
            return stable_since[0] is not None and c.sim_s-stable_since[0]>=3.2
        c.until(stable_hover,35,20)
        base=c.event('baseline_ready','baseline',altitude_m=c.latest['GLOBAL_POSITION_INT'].relative_alt/1000,mode=4,armed=True)
        for at_s, grouped in itertools.groupby(s['events'],key=lambda e:e['at_s']):
            group=list(grouped)
            c.until(lambda:c.sim_s>=base['sim_s']+at_s+offset,s['duration_s']+5,100)
            pending={}
            for event in group:
                c.event(event['id'],event['kind'],**{k:v for k,v in event.items() if k not in {'id','kind'}})
                if event['kind']=='heartbeat': c.heartbeats=event['enabled']
                elif event['kind']=='parameter':
                    name=event['name']; value=event['value']; pending[name]=value
                    c.params.pop(name,None)
                    c.conn.mav.param_set_send(1,1,name.encode(),float(value),mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
                elif event['kind']=='mode': c.mode(event['mode'])
            if pending:
                c.until(lambda:all(k in c.params and abs(c.params[k]-v)<.001 for k,v in pending.items()),5,10)
        c.until(lambda:c.sim_s>=base['sim_s']+s['duration_s']+offset,s['duration_s']+5,100)
        c.event('scenario_end','end')
        json_write(output/'params-after.json',c.snapshot())
        run['returncode']=0
    except BaseException as e:
        run['error']=f'{type(e).__name__}: {e}'
        (output/'error.txt').write_text(traceback.format_exc())
        print(run['error'],flush=True)
    finally:
        if proc is not None:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL); proc.wait(timeout=5)
            run['simulator_returncode']=proc.returncode
            run['cleanup']['child_reaped']=proc.poll() is not None
        else: run['cleanup']['child_reaped']=True
        if c is not None: c.close()
        out.close()
        run['wall_duration_s']=time.monotonic()-start
        usage=resource.getrusage(resource.RUSAGE_CHILDREN)
        run['child_resources']={'max_rss_kib':usage.ru_maxrss,'user_cpu_s':usage.ru_utime,'system_cpu_s':usage.ru_stime}
        run['cleanup']['completed']=True
        (output/'sockets-after.txt').write_text(subprocess.check_output(['ss','-lntup'],text=True))
        json_write(output/'run.json',run)
        seal(output)
    return run['returncode']

def main():
    p=argparse.ArgumentParser(); p.add_argument('--scenario',type=Path,required=True); p.add_argument('--version',choices=['4.5.6','4.5.7'],required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--offset',type=float,default=0)
    a=p.parse_args()
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt('terminated')))
    raise SystemExit(run_case(a.scenario.resolve(),a.version,a.output.resolve(),a.offset))
if __name__=='__main__':main()
