import test from 'node:test';
import assert from 'node:assert/strict';
import { replay } from '../src/engine.mjs';
import { first } from './first-fixture.mjs';
import { renderView } from '../src/views.mjs';

const variants = ['chronological', 'grouped', 'handover'];
const keys = ['principal','mode','owner','handover','target','nextActor','telemetry','lastReliable','acknowledgments','alarmGroups','completion'];

// Removing a required fact or rendering a duplicate must fail this contract check.
test('every variant renders each required fact exactly once with semantic metadata', () => {
  for (const variant of variants) {
    const html = renderView(replay(first, 5), variant);
    assert.equal((html.match(/data-fact=/g) || []).length, 11);
    for (const key of keys) {
      assert.equal((html.match(new RegExp(`data-fact="${key}"`, 'g')) || []).length, 1, `${variant}: ${key}`);
      assert.match(html, new RegExp(`data-fact="${key}"[^>]+data-value="[^"]*"[^>]+data-status="(?:known|stale|unknown)"[^>]+data-at="(?:null|\\d+)"[^>]+data-visibility="(?:visible|obscured)"`));
    }
    assert.match(html, /data-fact="owner" data-value="Unresolved" data-status="unknown" data-at="5"/);
    assert.match(html, /class="fact-value">Unresolved</);
  }
});

test('stale ownership stays explicit and last reliable evidence is labeled historical', () => {
  const stale = replay({duration:8,events:[{at:0,type:'owner',actor:'Operator A',ttl:2},{at:0,type:'observe',field:'telemetry',value:'40 metres',ttl:1}]}, 4);
  for (const variant of variants) {
    const html = renderView(stale, variant);
    assert.match(html, /data-fact="owner" data-value="Operator A" data-status="stale" data-at="0"/);
    assert.match(html, /Previous known owner; current responsibility is unverified/);
    assert.match(html, /Last reliable observation \(historical\)/);
    assert.match(html, /data-fact="telemetry" data-value="40 metres" data-status="stale"/);
  }
});

test('fact values, actor labels, alarm groups and event details cannot inject markup', () => {
  const value = '<img src=x onerror="alert(1)">&';
  const state = replay({duration:1,events:[{at:0,type:'owner',actor:value},{at:0,type:'observe',field:'principal',value},{at:0,type:'alarm',id:'x',label:value,group:value,severity:'critical'}]}, 0);
  for (const variant of variants) {
    const html = renderView(state, variant);
    assert.ok(!html.includes('<img'), variant);
    assert.ok(html.includes('&lt;img src=x onerror=&quot;alert(1)&quot;&gt;&amp;'));
    assert.match(html, /data-alarm="x"/);
  }
});

test('declared visibility differs by design and all alarms retain their authored group', () => {
  const state = replay(first, 3);
  for (const [variant, hidden] of [['chronological',4],['grouped',3],['handover',2]]) {
    const html = renderView(state, variant);
    assert.equal((html.match(/data-visibility="obscured"/g) || []).length, hidden);
    assert.match(html, /data-alarm="a1" data-group="link"/);
    assert.match(html, /class="alarm-group">link</);
    assert.match(html, /class="alarm-label">Control link degraded</);
    assert.match(html, /known historical event/);
  }
  assert.match(renderView(state, 'grouped'), /data-alarm-group="link"/);
  assert.match(renderView(state, 'grouped'), /class="group-label">link<\/span>/);
  assert.throws(() => renderView(state, 'invalid'), /Unknown view/);
});
