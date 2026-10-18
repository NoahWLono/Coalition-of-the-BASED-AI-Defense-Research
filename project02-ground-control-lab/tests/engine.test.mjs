import test from 'node:test';
import assert from 'node:assert/strict';
import { replay, facts, ReplayController } from '../src/engine.mjs';
import { first } from './first-fixture.mjs';

test('receipt never accepts responsibility; accepted/interrupted ownership is unresolved',()=>{
  assert.deepEqual(facts(replay(first,3)).owner,{value:'Operator A',status:'known',at:0});
  assert.deepEqual(facts(replay(first,4)).owner,{value:'Unresolved',status:'unknown',at:4});
  assert.deepEqual(facts(replay(first,5)).owner,{value:'Unresolved',status:'unknown',at:5});
  assert.deepEqual(facts(replay(first,5)).nextActor,{value:'Supervisor',status:'known',at:5});
  assert.deepEqual(facts(replay(first,7)).owner,{value:'Operator A',status:'known',at:7});
  assert.equal(facts(replay(first,8)).completion.value,'complete');
});
test('freshness boundary and historical evidence are distinct',()=>{
  assert.equal(facts(replay(first,5)).telemetry.status,'known');
  assert.equal(facts(replay(first,6)).telemetry.status,'stale');
  assert.deepEqual(facts(replay(first,12)).lastReliable,{value:'Link margin 82 percent',status:'known',at:0});
  assert.equal(facts(replay({...first,events:[]},3)).telemetry.status,'unknown');
});
test('timeout wins simultaneous acceptance and delayed confirm cannot assign owner',()=>{
  const s={duration:15,events:[...first.events.slice(0,6),{at:10,type:'accept',id:'h1',actor:'Operator B'},{at:11,type:'confirm',id:'h1',actor:'Supervisor'}]};
  const state=replay(s,12);
  assert.equal(state.handover.phase,'timed-out'); assert.equal(state.rejected.length,2);
  assert.equal(facts(state).owner.value,'Operator A');
  assert.equal(facts(state).nextActor.value,'Supervisor');
});
test('accepted timeout retains unresolved owner and invalid cancellation cannot undo acceptance',()=>{
  const s={duration:15,events:[...first.events.slice(0,8),{at:5,type:'cancel',id:'h1',actor:'Operator A'}]};
  assert.equal(replay(s,6).rejected.length,1);
  assert.equal(facts(replay(s,10)).owner.status,'unknown');
  assert.equal(replay(s,10).handover.phase,'timed-out');
});
test('rewind/reset during replay pauses and removes future state',()=>{
  const c=new ReplayController(first);c.play();for(let i=0;i<6;i++)c.tick();
  assert.equal(c.state.time,6);c.reset();c.tick();
  assert.equal(c.state.time,0);assert.equal(c.playing,false);assert.equal(c.state.alarms.length,0);
  c.seek(7);c.play();c.tick();assert.equal(c.state.completed,true);
  c.seek(3);assert.equal(c.state.completed,false);assert.equal(c.state.handover.phase,'requested');
});
test('stale ownership cannot authorize a request and unknown observations never invent a value',()=>{
  const s={duration:10,events:[{at:0,type:'owner',actor:'Operator A',ttl:2},{at:0,type:'observe',field:'telemetry',value:'42 m'},{at:3,type:'request',id:'h',from:'Operator A',to:'Operator B',deadline:8},{at:4,type:'observe',field:'telemetry',value:null}]};
  const f=facts(replay(s,5));assert.equal(f.owner.status,'stale');assert.equal(f.nextActor.status,'stale');
  assert.equal(replay(s,5).rejected.length,1);assert.deepEqual(f.telemetry,{value:'Unknown',status:'unknown',at:4});
  assert.deepEqual(f.lastReliable,{value:'42 m',status:'known',at:0});
});
test('replays are deterministic for every second and do not mutate scripts',()=>{
  const before=JSON.stringify(first);
  for(let t=0;t<=first.duration;t++)assert.deepEqual(replay(first,t),replay(first,t));
  assert.equal(JSON.stringify(first),before);
});
