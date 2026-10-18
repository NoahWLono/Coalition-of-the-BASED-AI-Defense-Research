import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {replay,facts,ReplayController} from '../src/engine.mjs';
import {compareFacts} from '../src/evaluator.mjs';
const scenarios=JSON.parse(readFileSync(new URL('../data/scenarios.json',import.meta.url)));
const oracle=JSON.parse(readFileSync(new URL('../data/oracle.json',import.meta.url)));
for(const s of scenarios)test(`${s.id}: all checkpoints match literal truth and reset removes future events`,()=>{
  for(const at of s.checkpoints){
    const matches=oracle.filter(o=>o.scenarioId===s.id&&o.at===at);assert.equal(matches.length,1);
    const actual=facts(replay(s,at));assert.deepEqual(Object.keys(matches[0].expected).sort(),Object.keys(actual).sort());
    assert.deepEqual(compareFacts(actual,matches[0].expected).filter(r=>!r.correct),[]);
  }
  const c=new ReplayController(s);c.play();while(c.playing)c.tick();
  assert.equal(c.state.completed,true);c.reset();c.tick();assert.deepEqual(c.state,replay(s,0));
  for(let t=0;t<=s.duration;t++)assert.deepEqual(c.seek(t),replay(s,t));
});
test('every scenario has declared completion, at least three checkpoint tasks and no unmatched oracle records',()=>{
  assert.equal(scenarios.length,10);assert.equal(new Set(scenarios.map(s=>s.id)).size,10);
  for(const s of scenarios){assert.ok(s.completionCondition);assert.ok(s.checkpoints.length>=3);}
  assert.equal(oracle.length,scenarios.reduce((n,s)=>n+s.checkpoints.length,0));
});
