import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {replay,facts} from '../src/engine.mjs';
import {renderView} from '../src/views.mjs';
import {compareFacts,parseRenderedFacts,toCSV} from '../src/evaluator.mjs';
const read=async path=>JSON.parse(await readFile(new URL(path,import.meta.url),'utf8'));
const scenarios=await read('../data/scenarios.json'),oracle=await read('../data/oracle.json');
const variants=['chronological','grouped','handover'];
const rows=[],failures=[],determinism=[],mutations=[];
for(const s of scenarios){
  for(let t=0;t<=s.duration;t++){
    const first=JSON.stringify(replay(s,t)),again=JSON.stringify(replay(s,t));
    if(first!==again)failures.push({scenario:s.id,t,reason:'nondeterministic'});
  }
  determinism.push({scenario:s.id,seconds:s.duration+1,sha256:createHash('sha256').update(JSON.stringify(replay(s,s.duration))).digest('hex')});
  for(const at of s.checkpoints){
    const checkpoints=oracle.filter(o=>o.scenarioId===s.id&&o.at===at);
    if(checkpoints.length!==1)throw new Error(`Need one oracle: ${s.id} ${at}`);
    const expected=checkpoints[0].expected,state=replay(s,at);
    for(const row of compareFacts(facts(state),expected))if(!row.correct)failures.push({scenario:s.id,at,layer:'model',...row});
    for(const variant of variants){
      const rendered=parseRenderedFacts(renderView(state,variant));
      for(const row of compareFacts(rendered,expected)){
        rows.push({scenario:s.id,second:at,variant,fact:row.fact,expected_value:row.expected.value,expected_status:row.expected.status,expected_at:row.expected.at,actual_value:row.actual?.value,actual_status:row.actual?.status,actual_at:row.actual?.at,visibility:row.visibility,disclosure_steps:row.steps,correct:row.correct,reason:row.reason});
        if(!row.correct)failures.push({scenario:s.id,at,variant,layer:'render-contract',...row});
      }
    }
  }
}
for(const [name,scenarioId,at,mutate,key] of [
  ['wrong ownership','interrupted',3,s=>{s.owner.value='Operator B';},'owner'],
  ['misleading grouping','interrupted',3,s=>{s.alarms[0].group='battery';},'alarmGroups']
]){
  const s=scenarios.find(s=>s.id===scenarioId),o=oracle.find(o=>o.scenarioId===scenarioId&&o.at===at);
  const state=replay(s,at);mutate(state);
  for(const variant of variants){const mismatches=compareFacts(parseRenderedFacts(renderView(state,variant)),o.expected).filter(r=>!r.correct);const detected=mismatches.some(r=>r.fact===key);mutations.push({name,variant,detected,mismatches});if(!detected)failures.push({name,variant,reason:'undetected mutation'});}
}
const staleOracle=oracle.find(o=>o.expected.owner.status==='stale');
if(!staleOracle)throw new Error('Missing stale-owner checkpoint');
const staleActual=structuredClone(staleOracle.expected);staleActual.owner.status='known';
mutations.push({name:'stale responsibility promoted to current',detected:compareFacts(staleActual,staleOracle.expected).some(r=>!r.correct&&r.fact==='owner')});
await mkdir(new URL('../evidence/',import.meta.url),{recursive:true});
await writeFile(new URL('../evidence/correctness-matrix.csv',import.meta.url),toCSV(rows));
const report={annotationProducer:'Assistant-authored literal oracle, independently derived from narratives and declared model; no human annotations',scenarios:scenarios.length,checkpoints:oracle.length,variants:variants.length,rows:rows.length,failures,determinism,mutations,visibility:Object.fromEntries(variants.map(v=>[v,{visible:rows.filter(r=>r.variant===v&&r.visibility==='visible').length,obscured:rows.filter(r=>r.variant===v&&r.visibility==='obscured').length,omitted:rows.filter(r=>r.variant===v&&r.visibility==='omitted').length}]))};
await writeFile(new URL('../evidence/evaluation.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({scenarios:report.scenarios,checkpoints:report.checkpoints,rows:rows.length,failures:failures.length,mutations:mutations.map(m=>({name:m.name,variant:m.variant,detected:m.detected})),visibility:report.visibility},null,2));
if(failures.length||mutations.some(m=>!m.detected))process.exitCode=1;
