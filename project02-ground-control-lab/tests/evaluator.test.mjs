import test from 'node:test';
import assert from 'node:assert/strict';
import {compareFacts,toCSV,parseRenderedFacts} from '../src/evaluator.mjs';
const expected={owner:{value:'Operator A',status:'stale',at:0},alarmGroups:{value:'a1: link; a2: link',status:'known',at:2}};
test('oracle comparison catches incorrect ownership and a misleading grouping independently',()=>{
  const wrongOwner=structuredClone(expected);wrongOwner.owner.value='Operator B';
  assert.equal(compareFacts(wrongOwner,expected).filter(r=>!r.correct)[0].fact,'owner');
  const wrongGroup=structuredClone(expected);wrongGroup.alarmGroups.value='a1: link; a2: battery';
  assert.equal(compareFacts(wrongGroup,expected).filter(r=>!r.correct)[0].fact,'alarmGroups');
});
test('old responsibility promoted to current and omitted facts are errors',()=>{
  const actual=structuredClone(expected);actual.owner.status='known';delete actual.alarmGroups;
  assert.equal(compareFacts(actual,expected).filter(r=>!r.correct).length,2);
  assert.equal(compareFacts({},expected)[0].visibility,'omitted');
});
test('metadata parser preserves escaped values, unknown timestamps and disclosure steps',()=>{
  const html='<div data-fact="owner" data-value="A &amp; B&quot;" data-status="unknown" data-at="null" data-visibility="obscured"></div>';
  assert.deepEqual(parseRenderedFacts(html).owner,{value:'A & B"',status:'unknown',at:null,visibility:'obscured',steps:1});
});
test('correct hidden information has a separate visibility result and CSV quotes cells',()=>{
  const actual=structuredClone(expected);actual.owner.visibility='obscured';
  const r=compareFacts(actual,expected)[0];assert.equal(r.correct,true);assert.equal(r.steps,1);
  assert.equal(toCSV([{fact:'a,"b',correct:false}]),'fact,correct\n"a,""b",false\n');
});
