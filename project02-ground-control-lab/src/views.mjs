import { facts } from './engine.mjs';

export const viewDefinitions = {
  chronological: {name:'Chronological alarms', title:'Follow the alarm sequence', description:'Alarms in arrival order, with additional context behind one disclosure.', hidden:['principal','alarmGroups','nextActor','lastReliable'], disclosure:'Issue context and historical evidence'},
  grouped: {name:'Incident groups', title:'Read the issue and its related alarms', description:'Alarms share only the issue identifiers declared in the script. Grouping is not a causal diagnosis.', hidden:['handover','target','nextActor'], disclosure:'Handover details'},
  handover: {name:'Handover state', title:'Establish who acts next', description:'Ownership, transfer state and the next responsible actor stay together. Alarm detail is one disclosure away.', hidden:['acknowledgments','alarmGroups'], disclosure:'Alarm details and receipts'}
};
const labels = {principal:'Principal issue',mode:'Control mode',owner:'Responsibility',handover:'Handover state',target:'Handover target',nextActor:'Responsible for next action',telemetry:'Latest telemetry observation',lastReliable:'Last reliable observation (historical)',acknowledgments:'Alarm acknowledgments',alarmGroups:'Declared alarm groups',completion:'Scenario completion'};
export const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stamp = at => at === null ? 'no timestamp' : `t=${at} s`;

function fact(key, record, obscured=false) {
  const note = key === 'owner' && record.status === 'stale' ? '<p class="fact-note">Previous known owner; current responsibility is unverified.</p>' : key === 'owner' && record.status === 'unknown' ? '<p class="fact-note">No actor is established as the current owner.</p>' : key === 'acknowledgments' ? '<p class="fact-note">Receipt does not accept responsibility.</p>' : key === 'lastReliable' ? '<p class="fact-note">Historical evidence; do not treat this as current telemetry.</p>' : '';
  return `<div class="fact fact-${key} state-${record.status}" data-fact="${key}" data-value="${escapeHTML(record.value)}" data-status="${record.status}" data-at="${record.at}" data-visibility="${obscured?'obscured':'visible'}"><p class="fact-label">${labels[key]}</p><p class="fact-value">${escapeHTML(record.value)}</p><p class="fact-meta"><span class="state-mark" aria-hidden="true">${record.status==='known'?'●':record.status==='stale'?'◷':'?'}</span> ${record.status} · ${stamp(record.at)}${key==='lastReliable'?' · historical':''}</p>${note}</div>`;
}
function alarmRow(a) {
  const receipts = a.acks.length ? a.acks.map(r=>`${escapeHTML(r.actor)} at ${stamp(r.at)}`).join('; ') : 'No receipt recorded';
  return `<li class="alarm severity-${a.severity}" data-alarm="${escapeHTML(a.id)}" data-group="${escapeHTML(a.group)}"><span class="severity">${a.severity==='critical'?'◆':a.severity==='warning'?'▲':'■'} ${a.severity}</span><div class="alarm-main"><p class="alarm-label">${escapeHTML(a.label)}</p><p class="alarm-meta">${escapeHTML(a.id)} <span aria-hidden="true">/</span> declared group: <span class="alarm-group">${escapeHTML(a.group)}</span></p><p class="alarm-receipts">${receipts}</p></div><p class="alarm-time">known<br>${stamp(a.at)}</p></li>`;
}
function alarms(s, grouped=false) {
  if (!s.alarms.length) return '<div class="empty-state"><span aria-hidden="true">✓</span><p>No active alarms</p><p>Cleared and rejected events remain in the event history.</p></div>';
  if (!grouped) return `<ol class="alarm-list">${s.alarms.map(alarmRow).join('')}</ol>`;
  const groups = new Map();
  for (const a of s.alarms) { if (!groups.has(a.group)) groups.set(a.group,[]); groups.get(a.group).push(a); }
  return [...groups].map(([group,items])=>`<section class="alarm-cluster" data-alarm-group="${escapeHTML(group)}"><h3><span class="group-symbol" aria-hidden="true">▤</span> <span class="group-label">${escapeHTML(group)}</span> <span class="count">${items.length} ${items.length===1?'alarm':'alarms'}</span></h3><ol class="alarm-list">${items.map(alarmRow).join('')}</ol></section>`).join('');
}
function eventDescription(e) {
  const pieces = [];
  for (const [key,value] of Object.entries(e)) {
    if (['at','type','sequence','accepted'].includes(key)) continue;
    pieces.push(`${key}: ${Array.isArray(value)?value.join('; '):value===null?'unknown':value}`);
  }
  return pieces.length ? escapeHTML(pieces.join(' / ')) : 'No additional fields';
}
function history(s) {
  return `<details class="history-disclosure" id="event-history"><summary id="event-history-toggle">Event history <span>${s.history.length} events; ${s.rejected.length} rejected</span></summary><div class="disclosure-content"><p class="section-note">Historical record in deterministic script order. At a deadline, timeout precedes scripted events. A rejected event has no state effect.</p><ol class="event-list">${s.history.map(e=>`<li class="event ${e.accepted?'':'event-rejected'}"><span class="event-time">${stamp(e.at)}</span><div><p><strong>${escapeHTML(e.type)}</strong> <span class="event-result">${e.accepted?'known historical event':'rejected historical event'}</span></p><p>${eventDescription(e)}</p></div><span class="event-order">${typeof e.sequence==='number'?`#${e.sequence+1}`:'deadline'}</span></li>`).join('') || '<li>No events have occurred.</li>'}</ol></div></details>`;
}
function disclosure(s, f, variant) {
  const d = viewDefinitions[variant];
  return `<details class="evidence-disclosure" id="${variant}-evidence"><summary id="${variant}-evidence-toggle">${d.disclosure}<span>${d.hidden.length} facts behind this disclosure</span></summary><div class="disclosure-content">${variant==='handover'?alarms(s):''}<div class="fact-grid">${d.hidden.map(k=>fact(k,f[k],true)).join('')}</div></div></details>`;
}
export function renderView(s, variant='handover') {
  if (!viewDefinitions[variant]) throw new Error(`Unknown view: ${variant}`);
  const f=facts(s), d=viewDefinitions[variant], show=k=>fact(k,f[k]);
  let content;
  if (variant==='chronological') content=`<div class="status-grid">${['owner','mode','handover','target','completion'].map(show).join('')}</div><section class="alarm-section"><div class="section-heading"><h3>Active alarms</h3><span>Oldest first; ${s.alarms.length} active</span></div>${alarms(s)}</section><div class="fact-grid">${show('telemetry')}${show('acknowledgments')}</div>${disclosure(s,f,variant)}`;
  if (variant==='grouped') content=`<div class="principal-band">${show('principal')}</div><div class="status-grid">${['owner','mode','completion'].map(show).join('')}</div><section class="alarm-section"><div class="section-heading"><h3>Declared issue groups</h3><span>${s.alarms.length} active alarms</span></div>${alarms(s,true)}</section><div class="fact-grid">${['alarmGroups','acknowledgments','telemetry','lastReliable'].map(show).join('')}</div>${disclosure(s,f,variant)}`;
  if (variant==='handover') content=`<div class="handover-board"><div class="ownership-pair">${show('owner')}<span class="ownership-divider" aria-hidden="true">⇢</span>${show('nextActor')}</div><div class="handover-detail">${show('handover')}${show('target')}</div><p class="handover-explanation">${s.handover.phase==='accepted'?'Acceptance recorded. Responsibility stays unresolved until supervisory confirmation.':s.handover.phase==='interrupted'||s.handover.phase==='conflicted'?'Recovery required. A supervisor must reconcile responsibility.':s.handover.phase==='timed-out'?'Deadline elapsed. A supervisor must resolve the transfer.':s.handover.phase==='requested'?'Transfer requested. The existing owner remains responsible until acceptance.':'Alarm receipt and control mode do not establish a responsibility transfer.'}${s.handover.deadline!==null?` <span>Scripted deadline: ${stamp(s.handover.deadline)}.</span>`:''}</p></div><div class="principal-band">${show('principal')}</div><div class="fact-grid">${['mode','completion','telemetry','lastReliable'].map(show).join('')}</div>${disclosure(s,f,variant)}`;
  return `<article class="variant-view variant-${variant}" aria-labelledby="view-heading"><div class="view-heading"><h2 id="view-heading">${d.title}</h2><p>${d.description}</p></div>${content}${history(s)}</article>`;
}
