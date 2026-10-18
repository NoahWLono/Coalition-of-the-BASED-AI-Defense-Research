const observation = (value=null,at=null,ttl=null)=>({value,at,ttl});
const known = (value,at)=>({value,status:'known',at});
function observed(o,time,fallback='Unknown') {
  return {value:o.value??fallback,status:o.value===null?'unknown':o.ttl!==null&&time-o.at>o.ttl?'stale':'known',at:o.at};
}
function initial() {
  return {time:0,observations:{principal:observation(),mode:observation(),telemetry:observation()},
    lastReliable:observation(),owner:observation(),handover:{phase:'idle',id:null,from:null,to:null,deadline:null,at:0,targetAt:0},
    alarms:[],ackAt:0,groupsAt:0,history:[],rejected:[],completed:false,completedAt:0};
}
function advance(s,time) {
  const h=s.handover;
  if(['requested','accepted'].includes(h.phase)&&time>=h.deadline) {
    const wasAccepted=h.phase==='accepted';h.phase='timed-out';h.at=h.deadline;
    if(wasAccepted)s.owner=observation(null,h.deadline);
    s.history.push({at:h.deadline,type:'timeout',id:h.id,accepted:true,sequence:'deadline'});
  }
  s.time=time;
}
function apply(s,e) {
  const h=s.handover;
  const a=s.alarms.find(a=>a.id===e.id);
  const match=e.id===h.id;
  const actor=v=>typeof v==='string'&&v.trim().length>0;
  const phase=p=>{h.phase=p;h.at=e.at;};
  const clearTarget=()=>{h.to=null;h.targetAt=e.at;};
  switch(e.type) {
    case 'observe':
      if(!(e.field in s.observations)||!(e.value===null||typeof e.value==='string'))return false;
      s.observations[e.field]=observation(e.value,e.at,e.ttl??({mode:10,telemetry:5}[e.field]??null));
      if(e.field==='telemetry'&&e.value!==null)s.lastReliable=observation(e.value,e.at);
      break;
    case 'owner':
      if(h.phase!=='idle'||s.owner.at!==null||!actor(e.actor))return false;
      s.owner=observation(e.actor,e.at,e.ttl??30);break;
    case 'alarm':
      if(a||!actor(e.id)||!actor(e.group)||!actor(e.label)||!['critical','warning','advisory'].includes(e.severity))return false;
      s.alarms.push({id:e.id,label:e.label,group:e.group,severity:e.severity,at:e.at,acks:[]});s.groupsAt=e.at;break;
    case 'clear':
      if(!a)return false;
      if(a.acks.length)s.ackAt=e.at;
      s.alarms=s.alarms.filter(a=>a.id!==e.id);s.groupsAt=e.at;break;
    case 'ack':
      if(!a||!actor(e.actor))return false;
      if(!a.acks.some(x=>x.actor===e.actor))a.acks.push({actor:e.actor,at:e.at});
      s.ackAt=e.at;break;
    case 'request':
      if(!['idle','completed','cancelled','timed-out'].includes(h.phase)||observed(s.owner,s.time).status!=='known'||e.from!==s.owner.value||!actor(e.to)||e.to===e.from||!actor(e.id)||!Number.isInteger(e.deadline)||e.deadline<=e.at)return false;
      Object.assign(h,{phase:'requested',id:e.id,from:e.from,to:e.to,deadline:e.deadline,at:e.at,targetAt:e.at});break;
    case 'accept':
      if(h.phase!=='requested'||!match||e.actor!==h.to)return false;
      phase('accepted');s.owner=observation(null,e.at);break;
    case 'confirm':
      if(h.phase!=='accepted'||!match||e.actor!=='Supervisor')return false;
      s.owner=observation(h.to,e.at,30);phase('completed');clearTarget();break;
    case 'cancel':
      if(h.phase!=='requested'||!match||![h.from,'Supervisor'].includes(e.actor))return false;
      phase('cancelled');clearTarget();break;
    case 'interrupt':
      if(!['requested','accepted'].includes(h.phase)||!match)return false;
      phase('interrupted');s.owner=observation(null,e.at);break;
    case 'conflict':
      if(!Array.isArray(e.reports)||e.reports.length<2||!e.reports.every(actor))return false;
      phase('conflicted');s.owner=observation(null,e.at);break;
    case 'reconcile':
      if(!['interrupted','conflicted','timed-out'].includes(h.phase)||e.actor!=='Supervisor'||!actor(e.owner))return false;
      s.owner=observation(e.owner,e.at,30);phase('completed');clearTarget();break;
    case 'complete':
      if(s.alarms.length||observed(s.owner,s.time).status!=='known'||!['idle','completed','cancelled'].includes(h.phase))return false;
      s.completed=true;s.completedAt=e.at;break;
    default:return false;
  }
  return true;
}

export function replay(scenario,second=0) {
  if(!Number.isFinite(second)||!Number.isInteger(scenario.duration)||scenario.duration<0)throw new Error('Invalid replay time or duration');
  const time=Math.max(0,Math.min(scenario.duration,Math.floor(second)));
  const s=initial();
  let previous=-1;
  for(const [sequence,event] of scenario.events.entries()) {
    if(!Number.isInteger(event.at)||event.at<previous||event.at>scenario.duration)throw new Error('Events must be ordered integer seconds within duration');
    previous=event.at;
    if(event.at>time)continue;
    advance(s,event.at);
    const accepted=apply(s,event);
    const entry={...structuredClone(event),sequence,accepted};
    s.history.push(entry);if(!accepted)s.rejected.push(entry);
  }
  advance(s,time);return s;
}

export function facts(s) {
  const h=s.handover,owner=observed(s.owner,s.time,'Unresolved');
  const next=h.phase==='requested'?known(h.to,h.at):['accepted','interrupted','conflicted','timed-out'].includes(h.phase)?known('Supervisor',h.at):{...owner};
  const sorted=[...s.alarms].sort((a,b)=>a.id.localeCompare(b.id));
  return {
    principal:observed(s.observations.principal,s.time),mode:observed(s.observations.mode,s.time),owner,
    handover:known(h.phase,h.at),target:known(h.to??'None',h.targetAt),nextActor:next,
    telemetry:observed(s.observations.telemetry,s.time),lastReliable:observed(s.lastReliable,s.time),
    acknowledgments:known(sorted.flatMap(a=>[...a.acks].sort((a,b)=>a.actor.localeCompare(b.actor)).map(r=>`${a.id}: ${r.actor}`)).join('; ')||'None',s.ackAt),
    alarmGroups:known(sorted.map(a=>`${a.id}: ${a.group}`).join('; ')||'None',s.groupsAt),
    completion:known(s.completed?'complete':'incomplete',s.completedAt)
  };
}

export class ReplayController {
  constructor(scenario) {this.scenario=scenario;this.playing=false;this.state=replay(scenario,0);}
  seek(second) {this.pause();this.state=replay(this.scenario,second);return this.state;}
  reset() {return this.seek(0);}
  step(delta=1) {return this.seek(this.state.time+delta);}
  play() {this.playing=this.state.time<this.scenario.duration;}
  pause() {this.playing=false;}
  tick() {
    if(this.playing) {this.state=replay(this.scenario,this.state.time+1);if(this.state.time===this.scenario.duration)this.pause();}
    return this.state;
  }
}
