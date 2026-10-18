#!/usr/bin/env python3
"""Regenerate declarative experiment v1, not used by runner or evaluator."""
import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def param(id,at,name,value): return dict(id=id,at_s=at,kind='parameter',name=name,value=value)
def hb(id,at,enabled):return dict(id=id,at_s=at,kind='heartbeat',enabled=enabled)
def mode(after,within=12,allowed=[9]):return dict(type='mode',after=after,within_s=within,allowed=allowed)
def text(after,contains,within):return dict(type='text',after=after,within_s=within,contains=contains,fault_evidence=True)
def field(after,message,field,op,value,within=12):return dict(type='field',after=after,within_s=within,message=message,field=field,op=op,value=value,fault_evidence=True)
def hold(after,start,duration,allowed=[9]):return dict(type='hold_mode',after=after,start_s=start,duration_s=duration,allowed=allowed)
def landed(after,within=50):return dict(type='disarmed',after=after,within_s=within)
def gcs(after='loss'):return [dict(type='heartbeat_gap',after=after,duration_s=4,fault_evidence=True),text(after,'GCS Failsafe',8),mode(after,8)]
def batt(after='low'):return [field(after,'SYS_STATUS','voltage_battery','lt',11000),text(after,'Battery 1 is low',12),mode(after,12)]
def rc(after='rc'):return [text(after,'Radio Failsafe',6),mode(after,6)]
def gps(after='stale'):return [field(after,'GPS_RAW_INT','fix_type','lt',3,10),mode(after,40)]
def save(id,title,events,assertions,duration=62,parameters=None,rationale='',starter=False,baseline=False):
    data=dict(schema_version=1,id=id,title=title,starter=starter,baseline=baseline,parameters=parameters or {},preconditions=dict(mode=4,armed=True,min_altitude_m=10.5,max_altitude_m=13.5,max_abs_vz_cm_s=30,stable_for_s=3,min_battery_mv=11500,min_gps_fix=3),events=events,max_compound_skew_s=.25,assertions=assertions,duration_s=duration,cleanup='Terminate and reap fresh simulator; never reuse eeprom; retain raw evidence',rationale=rationale)
    (root/'scenarios'/f'{id}.json').write_text(json.dumps(data,indent=2)+'\n')
save('00-baseline','Fault-free hover and commanded landing',[dict(id='land',at_s=12,kind='mode',mode='LAND')],[hold('baseline_ready',0,10,[4]),mode('land',3),landed('land',45)],60,baseline=True,rationale='Demonstrate stable hover and commanded landing before injecting failures.')
save('01-gcs-loss','GCS heartbeat interruption requests LAND',[hb('loss',5,False)],gcs()+[landed('loss')],starter=True,rationale='FS_GCS_ENABLE5, timeout3, options0; require 4s TX silence and failsafe status. Deadline8s includes scheduler and 0.1s clock resolution.')
save('02-battery-low','Low voltage threshold requests LAND',[param('low',5,'SIM_BATT_VOLTAGE',10.5)],batt()+[landed('low')],starter=True,rationale='Raw threshold11V, timer3s, low action1. Deadline12s permits filtering and scheduler latency. Capacity trigger disabled.')
save('03-rc-loss','RC pulse interruption requests LAND',[param('rc',5,'SIM_RC_FAIL',1)],rc()+[landed('rc')],starter=True,rationale='SIM_RC_FAIL1 removes pulse updates; FS_THR_ENABLE3 and RC_FS_TIMEOUT1. Status confirms detector; no MAVLink RC overrides are used.')
save('04-gcs-recovery','GCS recovery remains LAND',[hb('loss',5,False),hb('restore',13,True)],gcs()+[dict(type='heartbeat_resumed',after='restore',within_s=2),text('restore','GCS Failsafe Cleared',5),hold('restore',1,10),landed('loss')],rationale='Restoring the link clears detection without automatically restoring GUIDED. LAND must persist for10s after heartbeat resumes.')
save('05-rc-recovery','RC recovery remains LAND',[param('rc',5,'SIM_RC_FAIL',1),param('restore',12,'SIM_RC_FAIL',0)],rc()+[text('restore','Radio Failsafe Cleared',5),hold('restore',1,10),landed('rc')],rationale='Restored pulses clear radio failsafe but mode stays LAND. No pilot mode change is injected.')
save('06-battery-recovery','Restored battery voltage leaves LAND latched',[param('low',5,'SIM_BATT_VOLTAGE',10.5),param('restore',16,'SIM_BATT_VOLTAGE',12.6)],batt()+[field('restore','SYS_STATUS','voltage_battery','gt',11500,8),hold('restore',5,10),landed('low')],rationale='Battery failsafe is latched; raising simulated voltage does not restart the mission. Recovery voltage confirmation is independent of parameter echo.')
save('07-gcs-transient','Short heartbeat dropout does not trigger LAND',[hb('brief',5,False),hb('restore',6.2,True),dict(id='land',at_s=18,kind='mode',mode='LAND')],[dict(type='heartbeat_gap',after='brief',duration_s=1,fault_evidence=True),dict(type='heartbeat_resumed',after='restore',within_s=1),hold('brief',0,12,[4]),landed('land',45)],65,rationale='1.2s planned outage is below3s timeout even with heartbeat phase. Require observed silence and GUIDED through17s.')
save('08-battery-transient','Brief low-voltage dip does not trigger LAND',[param('dip',5,'SIM_BATT_VOLTAGE',10.5),param('restore',6,'SIM_BATT_VOLTAGE',12.6),dict(id='land',at_s=20,kind='mode',mode='LAND')],[field('dip','SYS_STATUS','voltage_battery','lt',11000,2),field('restore','SYS_STATUS','voltage_battery','gt',11500,6),hold('dip',0,14,[4]),landed('land',45)],67,rationale='1s voltage dip shorter than3s battery timer; require actual observed low reading. If filtering prevents the dip, case is not accepted as a pass.')
save('09-gps-stale','GPS byte starvation requests LAND',[param('stale',5,'SIM_GPS_BYTELOSS',100)],gps()+[landed('stale',70)],78,rationale='100 percent byte loss stops fresh GPS receiver input. GPS_TYPE2=0 prevents receiver substitution. GPS driver timeout4s; LAND within40s is an experimental bound for this EKF/configuration, not a documented universal guarantee. FS_DR_ENABLE0 isolates EKF behavior.')
save('10-gcs-rc-compound','Simultaneous GCS and RC loss',[hb('loss',5,False),param('rc',5,'SIM_RC_FAIL',1)],gcs()+rc()+[hold('rc',9,10),landed('rc')],rationale='Both faults within one controller scheduling tick; both detectors must be visible. Both actions LAND. Status text, heartbeat gap and sustained mode guard masking.')
compound_gcs=gcs();compound_gcs[1].pop('contains');compound_gcs[1]['contains_any']=['GCS Failsafe','GCS + Battery Failsafe - Continuing Landing']
save('11-gcs-battery-compound','Simultaneous GCS loss and battery low',[hb('loss',5,False),param('low',5,'SIM_BATT_VOLTAGE',10.5)],compound_gcs+batt()+[hold('low',14,8),landed('low')],rationale='Both fault events at5s, both detectors must occur. Both configured actions LAND; this does not test conflicting action priorities.')
save('12-gps-rc-compound','Simultaneous GPS starvation and RC loss',[param('stale',5,'SIM_GPS_BYTELOSS',100),param('rc',5,'SIM_RC_FAIL',1)],gps()+rc()+[hold('rc',10,10),landed('rc',70)],78,rationale='Require actual GPS fix degradation plus radio failsafe. RC LAND may precede EKF action; this checks resulting LAND and fault visibility, not independent proof of two LAND causes.')
control=json.loads((root/'scenarios/01-gcs-loss.json').read_text());control['id']='90-disabled-gcs-control';control['title']='Negative control: GCS failsafe disabled';control['parameters']={'FS_GCS_ENABLE':0};control['negative_control']=True
(root/'scenarios/90-disabled-gcs-control.json').write_text(json.dumps(control,indent=2)+'\n')

manifest_path=root/"scenarios/manifest.json"
manifest=json.loads(manifest_path.read_text())
for row in manifest["files"]:row["sha256"]=hashlib.sha256((root/row["path"]).read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
