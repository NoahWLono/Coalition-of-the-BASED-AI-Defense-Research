'use strict';

// Source documents are untrusted. Every dynamic string is escaped before markup
// insertion; full documents and original citations are always rendered as text.
const $ = (selector, parent = document) => parent.querySelector(selector);
const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = value => value == null ? 'Open' : new Intl.NumberFormat('en-CA', {style:'currency',currency:'CAD',maximumFractionDigits:2}).format(value);
const decimal = (value, digits = 1) => Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-CA', {maximumFractionDigits:digits}) : '—';
const percentWidth = value => Math.min(100, Math.max(0, Number(value) || 0));
const titleCase = value => String(value ?? '').replace(/_/g,' ').replace(/^./, x => x.toUpperCase());
const dateTime = value => value ? new Date(value).toLocaleString('en-CA', {dateStyle:'medium',timeStyle:'short'}) : 'Not recorded';
const labels = {supported:'Supported',not_satisfied:'Not satisfied',unresolved:'Unresolved',conflicting:'Conflicting',stale:'Stale',not_applicable:'Not applicable',eligible:'Eligible',conditional:'Conditional',affected:'Affected',unaffected:'Unaffected',fixed:'Fixed',accepted:'Accepted',rejected:'Rejected',unreviewed:'Unreviewed',draft:'Draft',reviewed:'Reviewed',approved:'Approved'};
const badge = (state, label) => `<span class="state-badge state-${h(state)}">${h(label || labels[state] || titleCase(state))}</span>`;
const states = ['supported','not_satisfied','unresolved','conflicting','stale','not_applicable'];
const views = {overview:'Overview',requirements:'Requirements matrix',evidence:'Evidence viewer',comparison:'Comparison',assurance:'Software assurance',changes:'Change review',decisions:'Decision package'};
const icons = {
 overview:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
 requirements:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 3v18M3 15h18M15 3v18"/>',
 evidence:'<path d="M14 3H5v18h14V8Z M14 3v5h5M8 12h8M8 16h6"/>',
 comparison:'<path d="M4 20V11M10 20V5M16 20V9M22 20V2"/>',
 assurance:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z M8 12l3 3 5-6"/>',
 changes:'<path d="M4 7h11l-3-3M15 7l-3 3M20 17H9l3 3M9 17l3-3M4 7v10M20 17V7"/>',
 decisions:'<path d="M9 4H4v17h16V4h-5M9 3h6v4H9ZM8 12h8M8 16h6"/>'
};
let state = null;
let session = {role:null,csrf:null};
let currentView = views[location.hash.slice(1)] ? location.hash.slice(1) : 'overview';
let busy = false;
let detailContext = null;
let detailRequest = 0;
const ui = {reqSearch:'',reqMode:'all',reqState:'all',reqPackage:'all',evidenceSearch:'',evidencePackage:'all',evidenceStatus:'all',evidencePage:0,comparePackage:null,assurancePackage:'all',assuranceStatus:'all',clarificationPackage:'all',clarificationPriority:'all'};
const ev = () => state.evaluation;
const packages = () => ev().packages;
const packageById = id => packages().find(p=>p.id===id);
const requirementById = id => ev().requirements.find(r=>r.id===id);
const assertionById = id => ev().assertions.find(a=>a.id===id);
const isRole = role => session.role === role;
const disabledFor = role => isRole(role) ? '' : 'disabled';
const roleNote = role => isRole(role) ? '' : `<p class="role-note">Sign in as ${h(role)} to make this change.</p>`;
const packageOptions = (selected, all = false) => `${all ? '<option value="all">All configurations</option>' : ''}${packages().map(p=>`<option value="${h(p.id)}" ${p.id===selected?'selected':''}>${h(p.id)} · ${h(p.name)}</option>`).join('')}`;
const stateOptions = selected => `<option value="all">All states</option>${states.map(s=>`<option value="${s}" ${s===selected?'selected':''}>${labels[s]}</option>`).join('')}`;
const blockers = p => p.assessments.filter(a=>requirementById(a.requirement_id)?.mode==='mandatory' && !['supported','not_applicable'].includes(a.state));
const gateText = p => `${Object.entries(p.mandatory_counts).filter(([s])=>['supported','not_applicable'].includes(s)).reduce((n,[,v])=>n+v,0)} / ${Object.values(p.mandatory_counts).reduce((n,v)=>n+v,0)}`;
const scoreText = score => score.low === score.high ? decimal(score.low) : `${decimal(score.low)}–${decimal(score.high)}`;
const eligibilityBadge = p => p.eligible ? badge('eligible','Documentary eligible') : badge('conditional','Gates remain open');
const compareButton = p => `<button type="button" class="button small" data-action="package" data-package="${h(p.id)}" aria-label="Inspect ${h(p.id)} ${h(p.name)}">Inspect</button>`;
const evidenceButton = (id, text = 'Inspect evidence') => `<button type="button" class="row-link" data-action="assertion" data-id="${h(id)}">${h(text)}</button>`;
const heading = (title, intro, action = '') => `<div class="page-heading"><div><h1>${h(title)}</h1><p>${h(intro)}</p></div>${action}</div>`;
const empty = (title, copy) => `<div class="empty-state"><strong>${h(title)}</strong>${h(copy)}</div>`;

async function api(path, options = {}) {
  const headers = {'Accept':'application/json', ...(options.body ? {'Content-Type':'application/json','X-CSRF-Token':session.csrf || ''} : {}), ...options.headers};
  const response = await fetch(path, {...options,headers,credentials:'same-origin'});
  let result;
  try { result = await response.json(); } catch { result = {}; }
  if (!response.ok) {
    const detail = typeof result.detail === 'string' ? result.detail : Array.isArray(result.detail) ? result.detail.map(x=>x.msg).join('; ') : `Request failed (${response.status}).`;
    const error = new Error(detail); error.status = response.status; throw error;
  }
  return result;
}
function showNotice(message, error = false) {
  const notice = $('#notice');
  notice.className = `notice${error?' error':''}`;
  notice.innerHTML = `<span>${h(message)}</span><button type="button" class="icon-button" data-action="dismiss-notice" aria-label="Dismiss notification">×</button>`;
  notice.hidden = false;
}
async function refresh() {
  state = await api('/api/state');
  session.role = state.role;
  if (!state.role) session.csrf = null;
  render();
}
async function mutate(path, body, message, after) {
  if (busy) return;
  busy = true;
  document.body.setAttribute('aria-busy','true');
  const submitButtons = [...document.querySelectorAll('button[type=submit]')].map(button=>({button,disabled:button.disabled}));
  submitButtons.forEach(({button})=>button.disabled=true);
  try {
    const result = await api(path,{method:'POST',body:JSON.stringify({...body,expected_revision:state.revision})});
    await refresh();
    showNotice(message);
    if (after) await after(result);
    return result;
  } catch (error) {
    if (error.status === 409) {
      await refresh();
      $('#detail-dialog').close();
      showNotice(`Inputs changed in another session. The workbench has refreshed to revision ${state.revision}. Review the new inputs and repeat your action. ${error.message}`,true);
    } else {
      showNotice(error.message,true);
      const localError = $('#detail-body .form-error');
      if (localError) {localError.textContent=error.message;localError.hidden=false;}
    }
  } finally {
    busy = false;
    document.body.removeAttribute('aria-busy');
    submitButtons.filter(({button})=>button.isConnected).forEach(({button,disabled})=>button.disabled=disabled);
  }
}
function render() {
  if (!state) return;
  const focused = document.activeElement;
  const focusId = focused?.id;
  const selection = focused && typeof focused.selectionStart === 'number' ? [focused.selectionStart,focused.selectionEnd] : null;
  $('#revision-label').textContent = `Revision ${state.revision}`;
  $('#session-button').textContent = session.role ? `${titleCase(session.role)} ▾` : 'Sign in';
  $('#session-button').setAttribute('aria-label',session.role ? `Change role: ${session.role}` : 'Sign in');
  $('#view-name').textContent = views[currentView];
  document.title = `${views[currentView]} | CEDAR`;
  document.querySelectorAll('[data-view]').forEach(button=>{
    const selected=button.dataset.view===currentView;
    if (selected) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current');
  });
  const renderers = {overview:renderOverview,requirements:renderRequirements,evidence:renderEvidence,comparison:renderComparison,assurance:renderAssurance,changes:renderChanges,decisions:renderDecisions};
  $('#main-content').innerHTML = `<section aria-label="${h(views[currentView])}">${renderers[currentView]()}</section>`;
  if (focusId) {
    const replacement = document.getElementById(focusId);
    if (replacement) {replacement.focus({preventScroll:true});if(selection && replacement.setSelectionRange) replacement.setSelectionRange(...selection);}
  }
}
function navigate(view) {
  if (!views[view]) return;
  currentView=view;
  history.replaceState(null,'',`#${view}`);
  render();
  $('#main-content').focus({preventScroll:true});
  window.scrollTo({top:0,behavior:'instant'});
}

function renderOverview() {
  const eligible=packages().filter(p=>p.eligible);
  const costOpen=packages().filter(p=>p.cost.upper_total===null);
  const required=ev().requirements.filter(r=>r.mode==='mandatory').length;
  const lowest=[...packages()].sort((a,b)=>a.cost.known_total-b.cost.known_total)[0];
  const cheapestBlockers=blockers(lowest);
  const priority=ev().clarifications.filter(q=>q.priority===1).slice(0,3);
  return `${heading('Civilian inspection fleet','A comparable fleet cost and a documentary shortlist, with the evidence behind each conclusion.', '<button type="button" class="button" data-view="decisions">Prepare a decision package</button>')}
    <div class="scope-line" style="margin-top:-13px;margin-bottom:22px"><span><strong>6 aircraft</strong> per configuration</span><span><strong>${h(state.assumptions.years)} years</strong> planning horizon</span><span><strong>${h(state.requirements_version.toUpperCase())}</strong> buyer requirements</span><span>Evaluated <strong>${h(state.as_of)}</strong></span></div>
    <div class="summary-strip"><div class="summary-item"><div class="metric-label">Documentary eligible</div><div class="metric-value">${eligible.length} <span>/ ${packages().length} configurations</span></div><div class="metric-foot">${required} mandatory gates per configuration</div></div><div class="summary-item"><div class="metric-label">Configurations with open gates</div><div class="metric-value">${packages().length-eligible.length}</div><div class="metric-foot">Scores cannot override these gates</div></div><div class="summary-item"><div class="metric-label">Incomplete cost totals</div><div class="metric-value">${costOpen.length}</div><div class="metric-foot">Unpriced exposure remains open</div></div><div class="summary-item"><div class="metric-label">Versioned source documents</div><div class="metric-value">${ev().documents.length}</div><div class="metric-foot">${ev().assertions.length} traceable assertions</div></div></div>
    <div class="callout amber"><span class="callout-mark" aria-hidden="true">◇</span><div><h3>The lowest known subtotal needs context</h3><p>${h(lowest.id)} ${h(lowest.name)} has a known subtotal of ${money(lowest.cost.known_total)}.${!lowest.eligible ? ` ${cheapestBlockers.length} mandatory ${cheapestBlockers.length===1?'gate remains':'gates remain'} open.` : ' Its mandatory documentary gates are supported.'}${lowest.cost.upper_total===null?' Its total has no finite upper bound until open costs are resolved.':' Its quoted cost inputs are complete under the current assumptions.'}</p></div><button type="button" class="button small" data-action="package" data-package="${h(lowest.id)}">Inspect ${h(lowest.id)}</button></div>
    <div class="panel"><div class="panel-heading"><div><h2>Commercial shortlist</h2><p>All ${packages().length} configurations. Eligibility first; preference intervals describe a separate comparison.</p></div><button type="button" class="button subtle" data-view="comparison">Cost and score detail</button></div><div class="table-wrap"><table class="commercial-table"><thead><tr><th scope="col">Configuration</th><th scope="col">Mandatory gates</th><th scope="col">Known fleet subtotal</th><th scope="col">Cost completeness</th><th scope="col">Preference / 100</th><th scope="col">Evidence</th></tr></thead><tbody>${packages().map(p=>`<tr><td><span class="package-id">${h(p.id)}</span><span class="package-name">${h(p.name)}</span><span class="package-supplier">${h(p.supplier_name)}</span></td><td>${eligibilityBadge(p)}<span class="gate-count"><small>${gateText(p)} supported or not applicable</small></span></td><td><span class="price">${money(p.cost.known_total)}</span><span class="price-caption">${state.assumptions.years}-year fleet, CAD</span></td><td>${p.cost.upper_total===null?`<span class="cost-open">${p.cost.open_exposures.length} open ${p.cost.open_exposures.length===1?'exposure':'exposures'}</span><span class="price-caption">Upper total: open</span>`:'<span class="small">Complete quoted inputs</span><span class="price-caption">Under stated assumptions</span>'}</td><td><span class="score-value">${scoreText(p.score)}</span><div class="score-track" aria-hidden="true"><span style="width:${percentWidth(p.score.low)}%"></span></div></td><td>${compareButton(p)}</td></tr>`).join('')}</tbody></table></div><div class="table-note">Eligibility means the supplied documentary evidence meets mandatory rules for further consideration. It is not purchase authorization or field-performance certification.</div></div>
    <div class="two-columns"><div class="panel"><div class="panel-heading"><div><h2>Priority clarifications</h2><p>Open mandatory evidence to resolve with suppliers.</p></div><button type="button" class="button subtle" data-view="decisions">View all</button></div><div class="panel-content">${priority.length?`<ul class="compact-list">${priority.map(q=>`<li><span class="source-pill">${h(q.package_id)}</span><div class="list-body"><strong>${h(q.requirement_id)} · ${h(q.missing)}</strong><p>${h(q.consequence)}</p></div><button type="button" class="row-link" data-action="assessment" data-package="${h(q.package_id)}" data-requirement="${h(q.requirement_id)}">Inspect</button></li>`).join('')}</ul>`:empty('Mandatory evidence is supported','Review open commercial and assurance clarifications before a decision.')}</div></div><div class="panel"><div class="panel-heading"><div><h2>Review context</h2><p>The input versions supporting this comparison.</p></div></div><div class="panel-content"><ul class="compact-list"><li><div class="list-body"><strong>Requirements ${h(state.requirements_version.toUpperCase())} / input revision ${state.revision}</strong><p>${state.applied_amendments.length?`${state.applied_amendments.length} supplier amendments applied: ${h(state.applied_amendments.join(', '))}`:'No supplier amendments applied.'}</p></div><button type="button" class="row-link" data-view="changes">Review changes</button></li><li><div class="list-body"><strong>${h(ev().profiles[state.profile].label)} preference profile</strong><p>${state.assumptions.include_optional?'Optional equipment included.':'Optional equipment excluded.'} ${h(state.assumptions.replacements_per_aircraft_per_year)} replacement batteries per aircraft per year.</p></div><button type="button" class="row-link" data-view="comparison">Assumptions</button></li><li><div class="list-body"><strong>${state.snapshots.length} decision ${state.snapshots.length===1?'snapshot':'snapshots'}</strong><p>${state.snapshots.filter(s=>!s.current).length} stale snapshots retained with their original evidence.</p></div><button type="button" class="row-link" data-view="decisions">Decisions</button></li></ul></div></div></div>`;
}

function renderRequirements() {
  const selectedPackages=ui.reqPackage==='all'?packages():packages().filter(p=>p.id===ui.reqPackage);
  const search=ui.reqSearch.trim().toLowerCase();
  const requirements=ev().requirements.filter(r=>(ui.reqMode==='all'||r.mode===ui.reqMode) && (!search||`${r.id} ${r.wording} ${r.category}`.toLowerCase().includes(search)) && (ui.reqState==='all'||selectedPackages.some(p=>p.assessments.find(a=>a.requirement_id===r.id)?.state===ui.reqState)));
  return `${heading('Requirements matrix','Inspect the state of every configuration against each buyer requirement. Select a state to see its rule, reasoning, and original sources.')}
    <div class="panel"><div class="toolbar"><div class="field grow"><label for="requirement-search">Search requirements</label><input id="requirement-search" data-filter="reqSearch" type="search" value="${h(ui.reqSearch)}" placeholder="Requirement ID, wording or category"></div><div class="field"><label for="requirement-mode">Requirement type</label><select id="requirement-mode" data-filter="reqMode"><option value="all">All types</option>${['mandatory','scored','informational'].map(m=>`<option value="${m}" ${ui.reqMode===m?'selected':''}>${titleCase(m)}</option>`).join('')}</select></div><div class="field"><label for="requirement-state">Assessment state</label><select id="requirement-state" data-filter="reqState">${stateOptions(ui.reqState)}</select></div><div class="field"><label for="requirement-package">Configuration</label><select id="requirement-package" data-filter="reqPackage">${packageOptions(ui.reqPackage,true)}</select></div></div><div class="legend" aria-label="Assessment state legend">${states.map(s=>badge(s)).join('')}</div><p class="filters-caption">${requirements.length} of ${ev().requirements.length} requirements · ${selectedPackages.length} configurations. Scroll horizontally to compare. State filtering keeps rows with at least one matching configuration.</p>
    <div class="matrix-wrap" tabindex="0" role="region" aria-label="Scrollable requirements matrix">${requirements.length?`<table class="matrix"><thead><tr><th scope="col">Buyer requirement ${h(state.requirements_version.toUpperCase())}</th>${selectedPackages.map(p=>`<th scope="col">${h(p.id)}<span class="matrix-name">${h(p.name)}</span></th>`).join('')}</tr></thead><tbody>${requirements.map(r=>`<tr><td><span class="requirement-id">${h(r.id)}</span><span class="requirement-mode">${titleCase(r.mode)} / ${h(r.category)}</span><div class="requirement-title">${h(r.wording)}</div></td>${selectedPackages.map(p=>{const a=p.assessments.find(a=>a.requirement_id===r.id);return `<td><button type="button" class="state-button" data-action="assessment" data-package="${h(p.id)}" data-requirement="${h(r.id)}" aria-label="${h(p.id)} ${h(r.id)} ${h(labels[a.state])}; inspect evidence">${badge(a.state)}<span class="state-value">${a.value!=null?`${h(a.value)} ${h(r.unit)}`:`${a.assertions.length} source ${a.assertions.length===1?'assertion':'assertions'}`}</span></button></td>`;}).join('')}</tr>`).join('')}</tbody></table>`:empty('No matching requirements','Adjust the search or assessment filters to see more requirements.')}</div></div>`;
}

function renderEvidence() {
  const search=ui.evidenceSearch.trim().toLowerCase();
  const assertions=ev().assertions.filter(a=>(ui.evidencePackage==='all'||a.package_id===ui.evidencePackage) && (ui.evidenceStatus==='all'|| (ui.evidenceStatus==='superseded'?a.superseded:ui.evidenceStatus==='needs_interpretation'?a.extraction_status==='needs_interpretation':a.review_status===ui.evidenceStatus)) && (!search||`${a.key} ${a.document_id} ${a.original} ${a.note}`.toLowerCase().includes(search)));
  const pageSize=75, pageCount=Math.max(1,Math.ceil(assertions.length/pageSize));
  ui.evidencePage=Math.min(ui.evidencePage,pageCount-1);
  const page=assertions.slice(ui.evidencePage*pageSize,(ui.evidencePage+1)*pageSize);
  return `${heading('Evidence viewer','A source-bound ledger of extracted assertions. Original wording, source hashes, normalization, and human interpretation review remain separate.')}
    <div class="panel"><div class="toolbar"><div class="field grow"><label for="evidence-search">Search evidence</label><input id="evidence-search" data-filter="evidenceSearch" type="search" value="${h(ui.evidenceSearch)}" placeholder="Source ID, requirement, cost key or original text"></div><div class="field"><label for="evidence-package">Configuration</label><select id="evidence-package" data-filter="evidencePackage">${packageOptions(ui.evidencePackage,true)}</select></div><div class="field"><label for="evidence-status">Ledger status</label><select id="evidence-status" data-filter="evidenceStatus">${[['all','All assertions'],['unreviewed','Unreviewed'],['accepted','Accepted'],['rejected','Rejected'],['superseded','Superseded source'],['needs_interpretation','Needs interpretation']].map(([v,l])=>`<option value="${v}" ${ui.evidenceStatus===v?'selected':''}>${l}</option>`).join('')}</select></div></div><div class="table-wrap"><table class="evidence-table"><thead><tr><th scope="col">Configuration / key</th><th scope="col">Extracted value</th><th scope="col">Source and original passage</th><th scope="col">Evidence type</th><th scope="col">Review</th><th scope="col">Inspect</th></tr></thead><tbody>${page.map(a=>`<tr><td><strong>${h(a.package_id)}</strong><span class="package-supplier">${h(a.key)}</span></td><td><strong>${a.value===null?'Unresolved':h(a.value)}</strong> ${h(a.normalized_unit)}<span class="package-supplier">${h(a.extraction_status.replace(/_/g,' '))}${a.superseded?' / superseded':''}</span></td><td><span class="source-title">${h(a.document_id)}</span><span class="package-supplier">Version ${h(a.document_version)} · lines ${h(a.location.start_line)}–${h(a.location.end_line)}</span><div class="evidence-excerpt" title="${h(a.original)}">${h(a.original)}</div></td><td><span class="tag">${h(a.evidence_type.replace(/_/g,' '))}</span></td><td>${badge(a.review_status)}</td><td>${evidenceButton(a.id,'Open source')}</td></tr>`).join('')}</tbody></table>${page.length?'':empty('No matching assertions','Clear a filter or import a labelled source document.')}</div><div class="table-note button-row"><span>${assertions.length} matching assertions · page ${ui.evidencePage+1} of ${pageCount}</span><span class="row-end button-row"><button type="button" class="button small" data-action="evidence-page" data-delta="-1" ${ui.evidencePage===0?'disabled':''}>Previous</button><button type="button" class="button small" data-action="evidence-page" data-delta="1" ${ui.evidencePage>=pageCount-1?'disabled':''}>Next</button></span></div>
    <details class="source-import"><summary>Import an additional source document</summary><p class="field-hint">UTF-8 .txt or .md, up to 100 KiB. Text stays inert. No archives, active content, OCR, or PDF extraction. Importing changes the input revision and stales existing decisions.</p><form id="upload-form" class="form-grid"><div class="field"><label for="upload-package">Source configuration</label><select id="upload-package" name="package_id" ${disabledFor('analyst')}>${packageOptions(packages()[0].id)}</select></div><div class="field"><label for="upload-title">Source title</label><input id="upload-title" name="title" required maxlength="200" ${disabledFor('analyst')}></div><div class="field full"><label for="upload-file">Text or Markdown source</label><input id="upload-file" name="source" type="file" accept=".txt,.md,text/plain,text/markdown" required ${disabledFor('analyst')}></div><div class="full button-row"><button type="submit" class="button primary" ${disabledFor('analyst')}>Import source</button>${roleNote('analyst')}</div></form></details></div>
    <div class="callout"><div><h3>Traceability does not establish supplier truth</h3><p>Document hashes identify the bytes used in this evaluation. “Independent test” is an evidence type in the fictional corpus; no real-world independent testing is asserted. Reviewer acceptance concerns the interpretation of a passage.</p></div></div>`;
}

function renderComparison() {
  const p=packageById(ui.comparePackage)||packages()[0];ui.comparePackage=p.id;
  const c=p.cost;
  return `${heading('Comparison','Review quoted costs, declared planning assumptions, criterion contributions, and changes under explicit preference scenarios.')}
    <div class="panel"><div class="panel-heading"><div><h2>Evaluation assumptions</h2><p>Changing an assumption or preference profile creates a new input revision.</p></div><span class="tag">${h(state.profile)} profile</span></div><form id="settings-form" class="panel-content"><div class="settings-grid"><div class="field"><label for="preference-profile">Preference profile</label><select id="preference-profile" name="profile" ${disabledFor('analyst')}>${Object.entries(ev().profiles).map(([id,v])=>`<option value="${h(id)}" ${state.profile===id?'selected':''}>${h(v.label)} (${v.operations}:${v.support})</option>`).join('')}</select><span class="field-hint">Operational : support criterion weights</span></div><div class="field"><label for="planning-years">Planning horizon (years)</label><input id="planning-years" name="years" type="number" min="1" max="10" step="1" required value="${h(state.assumptions.years)}" ${disabledFor('analyst')}></div><div class="field"><label for="replacement-rate">Replacement batteries / aircraft / year</label><input id="replacement-rate" name="replacements" type="number" min="0" max="10" step="any" required value="${h(state.assumptions.replacements_per_aircraft_per_year)}" ${disabledFor('analyst')}></div></div><div class="checkbox-field"><input id="include-optional" name="include_optional" type="checkbox" ${state.assumptions.include_optional?'checked':''} ${disabledFor('analyst')}><label for="include-optional">Include quoted optional equipment</label></div><div class="settings-actions"><p>Fleet quantity is six. CAD only; undiscounted, pre-tax. Quoted escalation applies to recurring software and support. Replacement frequency is a buyer planning assumption.</p><div class="button-row">${roleNote('analyst')}<button type="submit" class="button primary" ${disabledFor('analyst')}>Save assumptions</button></div></div></form></div>
    <div class="panel"><div class="panel-heading"><div><h2>Cost and criterion detail</h2><p>The displayed values are calculated from the current evidence and assumptions.</p></div><div class="field"><label for="compare-package">Inspect configuration</label><select id="compare-package" data-filter="comparePackage">${packageOptions(p.id)}</select></div></div><div class="panel-content"><div class="button-row">${eligibilityBadge(p)}<span class="price">${money(c.known_total)} known subtotal</span>${c.upper_total===null?'<span class="cost-open">Upper total: open</span>':'<span class="small muted">Complete quoted inputs</span>'}<button type="button" class="row-link row-end" data-action="package" data-package="${h(p.id)}">Inspect mandatory gates</button></div></div><div class="cost-breakdown"><div><span>Initial fleet and required items</span><strong>${money(c.breakdown.initial)}</strong></div><div><span>Recurring software and support</span><strong>${money(c.breakdown.recurring_by_year.reduce((a,b)=>a+b,0))}</strong></div><div><span>Planned battery replacements</span><strong>${money(c.breakdown.replacement_assumption)}</strong></div><div><span>Optional equipment included</span><strong>${money(c.breakdown.optional)}</strong></div></div><div class="table-wrap"><table><thead><tr><th scope="col">Quoted cost input</th><th scope="col">Quoted unit amount</th><th scope="col">Application to fleet total</th><th scope="col">Source</th></tr></thead><tbody>${c.lines.map(line=>`<tr><td>${h(line.label)}</td><td class="number">${line.quoted_value===null?'<span class="cost-open">Not priced / unresolved</span>':line.unit==='pct'?`${decimal(line.quoted_value)}%`:money(line.quoted_value)}</td><td class="small muted">${h(costApplication(line.key))}</td><td>${line.assertions.length?evidenceButton(line.assertions[0],`${line.assertions.length} ${line.assertions.length===1?'assertion':'assertions'}`):'<span class="muted">No current quoted evidence</span>'}</td></tr>`).join('')}</tbody></table></div><div class="table-note">${h(c.interpretation)}</div>${c.open_exposures.length?`<div class="panel-content padded"><div class="callout amber" style="margin-bottom:0"><div><h3>${c.open_exposures.length} unpriced ${c.open_exposures.length===1?'exposure':'exposures'}</h3><p>${c.open_exposures.map(x=>h(x.label)).join('; ')}. The known subtotal is incomplete. Missing amounts are not assumed to be zero.</p></div></div></div>`:''}</div>
    <div class="panel"><div class="panel-heading"><div><h2>Preference contributions: ${h(p.id)}</h2><p>${h(ev().profiles[state.profile].label)} · aggregate interval ${scoreText(p.score)} / 100</p></div><span class="tag">Eligibility is a separate gate</span></div><div class="table-wrap"><table><thead><tr><th scope="col">Scored requirement</th><th scope="col">Evidence state</th><th scope="col">Normalized score</th><th scope="col">Weight</th><th scope="col">Weighted contribution</th></tr></thead><tbody>${p.score.contributions.map(x=>`<tr><td><button type="button" class="row-link" data-action="assessment" data-package="${h(p.id)}" data-requirement="${h(x.requirement_id)}">${h(x.requirement_id)}</button><span class="package-supplier">${h(requirementById(x.requirement_id)?.wording)}</span></td><td>${badge(x.state)}</td><td class="number">${scoreText(x)} / 100</td><td class="number">${decimal(x.normalized_weight*100,2)}%</td><td class="number">${decimal(x.contribution_low,2)}${x.contribution_low!==x.contribution_high?`–${decimal(x.contribution_high,2)}`:''}</td></tr>`).join('')}</tbody></table></div><div class="table-note">${h(p.score.method)}</div></div>
    <div class="two-columns"><div class="panel"><div class="panel-heading"><div><h2>Weight sensitivity</h2><p>Eligible configurations across five declared scenarios.</p></div></div><div class="table-wrap"><table><thead><tr><th scope="col">Operations : support</th><th scope="col">Possible leaders</th><th scope="col">Guaranteed leader</th></tr></thead><tbody>${ev().sensitivity.cases.map(x=>`<tr><td class="number">${h(x.operations_to_support)} : 1</td><td>${h(x.possible_leaders.join(', ')||'None')}</td><td>${h(x.guaranteed_leaders.join(', ')||'None established')}</td></tr>`).join('')}</tbody></table></div><div class="table-note">${h(ev().sensitivity.interpretation)} Possible leaders have an upper score at least as high as the best lower score; a guaranteed leader exceeds every alternative’s upper score.</div></div><div class="panel"><div class="panel-heading"><div><h2>Conservative dominance</h2><p>Complete costs and criterion bounds are required.</p></div></div><div class="panel-content">${ev().dominance.length?`<ul class="compact-list">${ev().dominance.map(d=>`<li><div class="list-body"><strong>${h(d.dominant)} conservatively dominates ${h(d.dominated)}</strong><p>No higher complete cost, no worse criterion bounds, and at least one strict advantage.</p></div></li>`).join('')}</ul>`:empty('No dominance relation established','This does not establish equivalence. Open costs, overlapping criterion intervals, or trade-offs can prevent a dominance finding.')}<p class="inline-note">Only documentary-eligible alternatives with complete costs are tested. No midpoint is invented for unresolved evidence, and sensitivity results are not purchase-success probabilities.</p></div></div></div>`;
}
function costApplication(key) {
  const n=state.assumptions.years,r=state.assumptions.replacements_per_aircraft_per_year;
  return ({C_aircraft:'Quoted per aircraft × 6',C_ground:'One shared fleet allocation',C_software:`Annual fleet amount, escalated across ${n} years`,C_training:'One initial training allocation',C_support:`Annual fleet amount, escalated across ${n} years`,C_battery:`6 aircraft × ${n} years × ${r} replacements`,C_optional:state.assumptions.include_optional?'One optional allocation included':'Excluded by current assumption',C_escalation:'Applied to recurring software and support each year',C_required:'One mandatory additional allocation'})[key]||'See quotation';
}

function renderAssurance() {
  const rows=packages().flatMap(p=>p.assurance.map(issue=>({...issue,package:p})));
  const filtered=rows.filter(i=>(ui.assurancePackage==='all'||i.package.id===ui.assurancePackage)&&(ui.assuranceStatus==='all'||i.disposition===ui.assuranceStatus));
  return `${heading('Software assurance','Offline component matching with supplier exposure declarations. A matched component is not proof of application exploitability or deployed-build exposure.')}
    <div class="callout"><div><h3>Synthetic advisories and declared inventories</h3><p>CycloneDX 1.6 inventories are schema-validated. Matching is limited to top-level components, generic package URLs (PURLs), and exact affected or fixed version lists in the local fictional advisory set. Dependency trees and version ranges are not inferred. Inventory completeness, shipped binaries, and real-world vulnerabilities are not independently verified.</p></div></div>
    <div class="panel"><div class="toolbar"><div class="field grow"><label for="assurance-package">Configuration</label><select id="assurance-package" data-filter="assurancePackage">${packageOptions(ui.assurancePackage,true)}</select></div><div class="field"><label for="assurance-status">Disposition</label><select id="assurance-status" data-filter="assuranceStatus"><option value="all">All dispositions</option>${['affected','unaffected','fixed','unresolved'].map(s=>`<option value="${s}" ${ui.assuranceStatus===s?'selected':''}>${titleCase(s)}</option>`).join('')}</select></div><span class="list-filter-count">${filtered.length} component findings</span></div>${filtered.map(issue=>`<article class="assurance-item"><div class="assurance-header"><div><h3>${h(issue.title||issue.id)}</h3><p>${h(issue.package.id)} ${h(issue.package.name)} / ${h(issue.id)}</p></div>${badge(issue.disposition)}</div><div class="assurance-detail"><div><strong>Declared component identity</strong><p>${h(issue.component||'Inventory unavailable')} ${h(issue.version||'Version unresolved')}<br><code>${h(issue.purl||'Package identity not supplied')}</code></p><strong>Disposition rationale</strong><p>${h(issue.reason)}</p></div><div><strong>Procurement consequence</strong><p>${h(issue.consequence)}</p><strong>Advisory provenance</strong><p>Published: ${h(issue.published||'Not supplied')}<br>Stated source: ${h(issue.source||'Not supplied; inventory-only finding')}</p><strong>Application exposure evidence</strong>${issue.assertions?.length?issue.assertions.map(id=>evidenceButton(id,'Inspect exposure declaration')).join(' '):'<p>No current source-bound application declaration is available.</p>'}<p class="small muted">${h(issue.limitation||'Synthetic inventory; deployed components have not been independently verified.')}</p></div></div><div class="assurance-hashes"><span>Inventory: ${h(issue.inventory_source||'not supplied')}<br><code>${h(issue.inventory_hash||'No inventory hash')}</code></span>${issue.advisory_hash?`<span>Advisory-set SHA-256<br><code>${h(issue.advisory_hash)}</code></span>`:''}</div></article>`).join('')}${filtered.length?'':empty('No findings match the filters','Change the configuration or disposition filter. No match does not prove a configuration is unaffected.')}</div>`;
}

function renderChanges() {
  const stale=state.snapshots.filter(s=>!s.current);
  return `${heading('Change review','Apply supplier amendments or a buyer policy revision, then inspect exactly which assessments changed and which decisions need review.')}
    <div class="two-columns"><div class="panel"><div class="panel-heading"><div><h2>Buyer requirements</h2><p>Current policy: ${h(state.requirements_version.toUpperCase())}</p></div></div><form id="policy-form" class="panel-content"><div class="field"><label for="requirements-version">Requirements version</label><select id="requirements-version" name="requirements_version" ${disabledFor('analyst')}><option value="v1" ${state.requirements_version==='v1'?'selected':''}>V1 — original buyer schedule</option><option value="v2" ${state.requirements_version==='v2'?'selected':''}>V2 — revised buyer schedule</option></select></div><p class="field-hint">Changing the buyer schedule re-evaluates all configurations. The resulting history records affected requirement states and conservatively stales existing snapshots.</p><div class="button-row"><button type="submit" class="button primary" ${disabledFor('analyst')}>Apply policy version</button>${roleNote('analyst')}</div></form></div><div class="panel"><div class="panel-heading"><div><h2>Decision currency</h2><p>Current input revision ${state.revision}</p></div></div><div class="panel-content"><div class="metric-value">${stale.length} <span>stale decision ${stale.length===1?'snapshot':'snapshots'}</span></div><p class="inline-note">Every input change invalidates the currency of previous reviews and approvals. Their original records remain exportable.</p><button type="button" class="button" data-view="decisions">Inspect decision history</button></div></div></div>
    <div class="panel"><div class="panel-heading"><div><h2>Supplier amendments</h2><p>Versioned additions retain superseded sources in the evidence ledger.</p></div></div>${state.available_amendments.map(a=>`<div class="amendment"><span class="amendment-id">${h(a.id)}</span><div class="list-body"><strong>${h(a.title)}</strong><p>${h(a.description)}</p></div>${state.applied_amendments.includes(a.id)?badge('supported','Applied'):`<button type="button" class="button" data-action="apply-amendment" data-id="${h(a.id)}" ${disabledFor('analyst')}>Apply ${h(a.id)}</button>`}</div>`).join('')}<div class="table-note">${isRole('analyst')?'Applying an amendment immediately creates a new revision.':'Sign in as analyst to apply supplier amendments.'} All earlier snapshots become stale and require a new snapshot and review.</div></div>
    <div class="panel"><div class="panel-heading"><div><h2>Assessment change history</h2><p>Before and after states, including cost and preference changes.</p></div><span class="tag">${state.changes.length} input ${state.changes.length===1?'change':'changes'}</span></div>${state.changes.length?[...state.changes].reverse().map((change,index)=>`<details class="change-record" ${index===0?'open':''}><summary><span><strong>Revision ${change.revision}: ${h(change.reason)}</strong><small>${h(dateTime(change.at))} · ${change.diffs.length} affected assessment or calculation rows</small></span></summary><div class="change-body"><div class="callout amber"><div><p>${h(change.approval_effect)}</p></div></div>${change.diffs.length?`<div class="table-wrap"><table><thead><tr><th scope="col">Configuration / item</th><th scope="col">Previous</th><th scope="col">Current</th><th scope="col">Reason</th></tr></thead><tbody>${change.diffs.map(d=>`<tr><td><strong>${h(d.package_id)}</strong> ${h(d.requirement_id)}${requirementById(d.requirement_id)?`<br><button type="button" class="row-link" data-action="assessment" data-package="${h(d.package_id)}" data-requirement="${h(d.requirement_id)}">Inspect current evidence</button>`:''}</td><td>${states.includes(d.before)?badge(d.before):h(d.before)}</td><td>${states.includes(d.after)?badge(d.after):h(d.after)}</td><td class="small">${h(d.reason)}</td></tr>`).join('')}</tbody></table></div>`:empty('No assessment values changed','The changed input revision still requires fresh decision review.')}</div></details>`).join(''):empty('The original input set is current','Apply an amendment or policy revision to see its recorded effect here.')}</div>`;
}

function renderDecisions() {
  const qs=ev().clarifications.filter(q=>(ui.clarificationPackage==='all'||q.package_id===ui.clarificationPackage)&&(ui.clarificationPriority==='all'||String(q.priority)===ui.clarificationPriority));
  return `${heading('Decision package','Freeze a reproducible evidence snapshot, obtain a separate technical review and approval, and export the original decision record.')}
    <div class="callout"><div><h3>A conditional decision records the unresolved work</h3><p>Documentary eligibility supports further consideration only. A conditional decision retains the blockers and is never purchasing authorization. Input changes make all previous decisions stale.</p></div></div>
    <div class="panel"><div class="panel-heading"><div><h2>Create a decision snapshot</h2><p>Snapshot revision ${state.revision}, requirements ${h(state.requirements_version.toUpperCase())}, and ${h(ev().profiles[state.profile].label.toLowerCase())}.</p></div><span class="tag">Analyst action</span></div><form id="snapshot-form" class="panel-content decision-form"><div class="field"><label for="decision-package">Decision configuration</label><select id="decision-package" name="package_id" ${disabledFor('analyst')}>${packageOptions(ui.comparePackage||packages()[0].id)}</select></div><div class="field"><label for="decision-kind">Decision type</label><select id="decision-kind" name="decision" ${disabledFor('analyst')}><option value="conditional">Conditional — record open blockers</option><option value="eligible">Documentary eligible — further consideration</option></select></div><div class="field full"><label for="decision-rationale">Decision rationale</label><textarea id="decision-rationale" name="rationale" maxlength="4000" required placeholder="Explain the evidence, trade-offs, outstanding work, and reason for this decision." ${disabledFor('analyst')}></textarea></div><div class="full button-row"><button type="submit" class="button primary" ${disabledFor('analyst')}>Create snapshot</button>${roleNote('analyst')}</div></form></div>
    <div class="panel"><div class="panel-heading"><div><h2>Decision history</h2><p>Review and approval are bound to the frozen record’s digest.</p></div><span class="tag">${state.snapshots.length} snapshots</span></div>${state.snapshots.length?state.snapshots.map(snapshotMarkup).join(''):empty('No decision snapshot yet','An analyst can create a snapshot from the current evidence. A reviewer and approver then act on that same record.')}</div>
    <div class="panel"><div class="panel-heading"><div><h2>Supplier clarification register</h2><p>Locally generated questions for open evidence, cost, and software assurance. No messages are sent.</p></div></div><div class="toolbar"><div class="field grow"><label for="clarification-package">Clarification configuration</label><select id="clarification-package" data-filter="clarificationPackage">${packageOptions(ui.clarificationPackage,true)}</select></div><div class="field"><label for="clarification-priority">Clarification priority</label><select id="clarification-priority" data-filter="clarificationPriority">${[['all','All priorities'],['1','1 — mandatory eligibility'],['2','2 — cost or assurance'],['3','3 — preference or information']].map(([v,l])=>`<option value="${v}" ${ui.clarificationPriority===v?'selected':''}>${l}</option>`).join('')}</select></div><span class="list-filter-count">${qs.length} open clarifications</span></div><div class="table-wrap"><table><thead><tr><th scope="col">Priority / configuration</th><th scope="col">Clarification request</th><th scope="col">Decision consequence</th><th scope="col">Evidence</th></tr></thead><tbody>${qs.map(q=>`<tr><td class="no-wrap">${h(q.priority)} / <strong>${h(q.package_id)}</strong><span class="package-supplier">${h(q.requirement_id)}</span></td><td><strong class="small">${h(q.question)}</strong><span class="package-supplier">${h(q.missing)}</span></td><td class="small">${h(q.consequence)}</td><td>${requirementById(q.requirement_id)?`<button type="button" class="row-link" data-action="assessment" data-package="${h(q.package_id)}" data-requirement="${h(q.requirement_id)}">Inspect</button>`:q.assertions.length?evidenceButton(q.assertions[0],'Inspect'):'<span class="small muted">Evidence requested</span>'}</td></tr>`).join('')}</tbody></table>${qs.length?'':empty('No clarifications match the filters','Choose another configuration or priority.')}</div></div>`;
}
function snapshotMarkup(s) {
  const p=s.record.evaluation.packages.find(p=>p.id===s.record.package_id);
  return `<article class="snapshot"><div class="snapshot-heading"><div><h3>${h(s.id)} / ${h(p.name)}</h3><p>${h(s.record.package_id)} · created ${h(dateTime(s.record.created_at))} · input revision ${s.revision}</p></div>${badge(s.status)}</div><div class="snapshot-rationale">${h(s.record.rationale)}</div><div class="snapshot-meta"><div><strong>Decision</strong>${s.record.decision==='eligible'?'Documentary eligible for consideration':'Conditional; blockers recorded'}</div><div><strong>Mandatory eligibility at snapshot</strong>${p.eligible?'Supported by supplied evidence':'Open mandatory gates'}</div><div><strong>Frozen known fleet subtotal</strong>${money(p.cost.known_total)}${p.cost.upper_total===null?' / upper total open':''}</div></div><div class="workflow" aria-label="Decision workflow"><span class="complete">Snapshot created</span><span aria-hidden="true">›</span><span class="${s.review?'complete':'current'}">${s.review?'Technically reviewed':'Technical review required'}</span><span aria-hidden="true">›</span><span class="${s.approval?'complete':''}">${s.approval?'Approval recorded':'Approval required'}</span>${!s.current?'<span class="cost-open">Previous review / approval is stale</span>':''}</div><div class="snapshot-hash">Record SHA-256 <code>${h(s.digest)}</code></div>${s.review?`<div class="snapshot-review"><strong>Technical reviewer / ${h(dateTime(s.review.at))}</strong><p class="review-note">${h(s.review.note)}</p></div>`:''}${s.approval?`<div class="snapshot-review"><strong>Approver / ${h(dateTime(s.approval.at))}</strong><p class="review-note">${h(s.approval.note)}</p></div>`:''}<div class="button-row" style="margin-top:16px"><button type="button" class="button" data-action="snapshot-detail" data-id="${h(s.id)}">Inspect frozen record</button><a class="button" href="/api/export/${encodeURIComponent(s.id)}" download>Export ${s.current?'decision':'stale record'} ZIP</a>${s.current&&isRole('reviewer')?`<button type="button" class="button primary" data-action="snapshot-review" data-id="${h(s.id)}">Record technical review</button>`:''}${s.current&&isRole('approver')?`<button type="button" class="button primary" data-action="snapshot-approve" data-id="${h(s.id)}" ${s.review?'':'disabled'}>Approve decision</button>`:''}</div>${!s.current?'<p class="inline-note">Create a new snapshot from the current input revision before review or approval. This ZIP preserves the original evidence and marks its stale status.</p>':isRole('approver')&&!s.review?'<p class="inline-note">A current technical review is required before approval.</p>':''}</article>`;
}

function openDetail(title, label, html, context) {
  detailContext=context;
  $('#detail-title').textContent=title;
  $('#detail-label').textContent=label;
  $('#detail-body').innerHTML=html;
  const dialog=$('#detail-dialog');
  if (!dialog.open) dialog.showModal();
  dialog.scrollTop=0;
}
function assertionCards(ids) {
  return ids.map(id=>assertionById(id)).filter(Boolean).map(a=>`<button type="button" class="assertion-card" data-action="assertion" data-id="${h(a.id)}"><span class="assertion-top"><span>${h(a.document_id)} · lines ${a.location.start_line}–${a.location.end_line}</span>${badge(a.review_status)}</span><span class="assertion-value">${a.value===null?'Unresolved value':h(a.value)} ${h(a.normalized_unit)}</span><span class="assertion-source">${h(a.evidence_type.replace(/_/g,' '))} · ${a.superseded?'Superseded source':`Valid ${h(a.valid_from)} to ${h(a.valid_until)}`} · Open original passage</span></button>`).join('');
}
function showAssessment(packageId, requirementId) {
  const p=packageById(packageId),r=requirementById(requirementId),a=p?.assessments.find(a=>a.requirement_id===requirementId);
  if (!p||!r||!a) return;
  const comparison=({gte:'at least',lte:'at most',eq:'equal to',present:'present'})[r.comparator];
  const rule=r.comparator==='present'?'A stated value must be present.':`The normalized value must be ${comparison} ${r.target} ${r.unit}.`;
  openDetail(`${p.id} / ${r.id}`,`${p.name} · requirement assessment`,`${badge(a.state)}<h3>${h(r.wording)}</h3><p class="muted">${h(a.reason)}</p><div class="policy-reference"><strong>Buyer rule ${h(state.requirements_version.toUpperCase())} / ${h(titleCase(r.mode))}</strong><p>${h(rule)} Accepted evidence: ${h(r.evidence_types.map(x=>x.replace(/_/g,' ')).join(', '))}.</p></div><dl class="detail-grid"><div><dt>Documented normalized value</dt><dd>${a.value==null?'Not established':`${h(a.value)} ${h(r.unit)}`}</dd></div><div><dt>Applicability</dt><dd>${h(r.applies_to.includes('*')?'All configurations':r.applies_to.join(', '))}</dd></div><div><dt>Policy effective date</dt><dd>${h(r.effective)}</dd></div><div><dt>Policy expiry</dt><dd>${h(r.expires||'No expiry specified')}</dd></div><div class="full"><dt>Policy source</dt><dd>${h(r.source)}</dd></div>${r.scoring?`<div class="full"><dt>Score normalization</dt><dd>Declared range ${h(r.scoring.low)} to ${h(r.scoring.high)} ${h(r.unit)}; ${h(r.scoring.direction)} is preferred. Current score interval: ${decimal(a.score_low)}–${decimal(a.score_high)} / 100.</dd></div>`:''}</dl><h3>Source assertions (${a.assertions.length})</h3>${a.assertions.length?assertionCards(a.assertions):empty('No matching evidence supplied','This requirement stays unresolved until suitable, current evidence is provided.')}<p class="inline-note">Superseded, expired, conflicting, and rejected assertions remain visible. Their presence in the ledger does not mean they support the current assessment.</p>`,{kind:'assessment',packageId,requirementId});
}
function showPackage(packageId) {
  const p=packageById(packageId);if(!p)return;
  const open=blockers(p);
  openDetail(p.name,`${p.id} · configuration review`,`${eligibilityBadge(p)}<p class="inline-note">${h(p.supplier_name)} · ${gateText(p)} mandatory gates supported or not applicable</p><dl class="detail-grid"><div><dt>Known fleet subtotal</dt><dd class="price">${money(p.cost.known_total)}</dd></div><div><dt>Upper fleet total</dt><dd>${p.cost.upper_total===null?'Open — no finite upper bound':money(p.cost.upper_total)}</dd></div><div><dt>Preference score interval</dt><dd>${scoreText(p.score)} / 100</dd></div><div><dt>Profile</dt><dd>${h(ev().profiles[state.profile].label)}</dd></div></dl><div class="button-row"><button type="button" class="button" data-action="compare-package" data-package="${h(p.id)}">Inspect cost and score detail</button><button type="button" class="button" data-action="matrix-package" data-package="${h(p.id)}">All requirements</button></div><h3>Open mandatory gates (${open.length})</h3>${open.length?open.map(a=>`<button type="button" class="assertion-card" data-action="assessment" data-package="${h(p.id)}" data-requirement="${h(a.requirement_id)}"><span class="assertion-top"><strong>${h(a.requirement_id)}</strong>${badge(a.state)}</span><span class="assertion-value">${h(requirementById(a.requirement_id).wording)}</span><span class="assertion-source">${h(a.reason)}</span></button>`).join(''):'<div class="callout"><div><h3>Mandatory documentary gates are supported</h3><p>This means eligibility for further consideration. It does not establish field capability or purchasing authorization.</p></div></div>'}<h3>Open cost exposures (${p.cost.open_exposures.length})</h3>${p.cost.open_exposures.length?p.cost.open_exposures.map(x=>`<div class="policy-reference" style="margin-bottom:10px"><strong>${h(x.label)}</strong><p>${h(x.reason)}</p>${x.assertions.map(id=>evidenceButton(id)).join(' ')}</div>`).join(''):'<p class="small muted">The current quoted inputs are complete under the selected planning assumptions.</p>'}<h3>Software assurance dispositions</h3><div class="all-dispositions">${p.assurance.map(a=>badge(a.disposition,`${a.component||a.id}: ${labels[a.disposition]}`)).join('')}</div><button type="button" class="button subtle" data-action="assurance-package" data-package="${h(p.id)}">Inspect software assurance</button>`,{kind:'package',packageId});
}
async function showAssertion(id) {
  const a=assertionById(id);if(!a)return;
  const request=++detailRequest;
  openDetail(`${a.package_id} / ${a.key}`,'Source-bound assertion', '<p class="muted">Loading the original source version…</p>',{kind:'assertion',id});
  try {
    const doc=await api(`/api/documents/${encodeURIComponent(a.document_id)}`);
    if(request!==detailRequest)return;
    const sourceLines=doc.content.split('\n').map((line,index)=>`<li class="${index+1>=a.location.start_line&&index+1<=a.location.end_line?'highlighted':''}"><span class="line-number" aria-label="Line ${index+1}">${index+1}</span><span class="line-text">${h(line)||' '}</span></li>`).join('');
    const html=`<div class="button-row">${badge(a.review_status)}${a.superseded?badge('stale','Superseded source'):''}<span class="tag">${h(a.extraction_status.replace(/_/g,' '))}</span></div><h3>Exact original passage</h3><p class="small muted">${h(doc.title)} · version ${h(a.document_version)} · lines ${a.location.start_line}–${a.location.end_line}</p><pre class="citation">${h(a.original)}</pre><dl class="detail-grid"><div><dt>Raw value and unit</dt><dd>${h(a.raw_value)} ${h(a.unit)}</dd></div><div><dt>Normalized value and unit</dt><dd>${a.value===null?'Unresolved':h(a.value)} ${h(a.normalized_unit)}</dd></div><div><dt>Transformation</dt><dd>${h(a.transformation||'No unit conversion')}</dd></div><div><dt>Evidence type</dt><dd>${h(a.evidence_type.replace(/_/g,' '))}</dd></div><div><dt>Valid from</dt><dd>${h(a.valid_from||'Unresolved')}</dd></div><div><dt>Valid until</dt><dd>${h(a.valid_until||'Unresolved')}</dd></div><div><dt>Source issued</dt><dd>${h(doc.issued)}</dd></div><div><dt>Evaluation date</dt><dd>${h(state.as_of)}</dd></div><div class="full"><dt>Source SHA-256</dt><dd class="hash"><code>${h(a.document_hash)}</code></dd></div><div class="full"><dt>Assertion ID</dt><dd class="hash"><code>${h(a.id)}</code></dd></div>${a.note?`<div class="full"><dt>Source note</dt><dd>${h(a.note)}</dd></div>`:''}</dl>${a.unresolved_interpretation?`<div class="callout amber"><div><h3>Unresolved interpretation</h3><p>${h(a.unresolved_interpretation)}</p></div></div>`:''}${a.review?`<div class="policy-reference"><strong>Interpretation ${h(a.review.status)} by ${h(a.review.role)} / ${h(dateTime(a.review.at))}</strong><p class="review-note">${h(a.review.note)}</p></div>`:''}<details class="source-detail" open><summary>Full original source document (${doc.content.split('\n').length} lines)</summary><ol class="source-lines" aria-label="Original source with line numbers">${sourceLines}</ol><p class="inline-note">Text is shown verbatim and inert. Instructions within a supplier document do not control policy, permissions, or evaluation.</p></details><form id="assertion-review-form" class="review-form" data-id="${h(a.id)}"><h3>Review the interpretation</h3><p class="field-hint">Acceptance records a reviewer’s interpretation of this passage; it does not certify the supplier’s claim. Rejection excludes the assertion from current support. Either action creates a new revision and stales decision snapshots.</p><label for="assertion-review-status">Interpretation disposition</label><select id="assertion-review-status" name="status" ${disabledFor('reviewer')}><option value="accepted">Accept interpretation</option><option value="rejected">Reject interpretation</option></select><label for="assertion-review-note">Interpretation review note</label><textarea id="assertion-review-note" name="note" required maxlength="4000" ${disabledFor('reviewer')}></textarea><p class="form-error" hidden role="alert"></p><div class="button-row"><button type="submit" class="button primary" ${disabledFor('reviewer')}>Record interpretation review</button>${roleNote('reviewer')}</div></form>`;
    openDetail(`${a.package_id} / ${a.key}`,'Source-bound assertion',html,{kind:'assertion',id});
  }catch(error){openDetail('Source could not be loaded','Evidence inspection',`<div class="callout amber"><p>${h(error.message)}</p></div>`,{kind:'assertion',id});}
}
function showSnapshot(id, action) {
  const s=state.snapshots.find(s=>s.id===id);if(!s)return;
  const p=s.record.evaluation.packages.find(p=>p.id===s.record.package_id);
  const record=s.record;
  openDetail(s.id,'Frozen decision record',`${badge(s.status)}<h3>${h(p.id)} ${h(p.name)}</h3><p class="review-note">${h(record.rationale)}</p><dl class="detail-grid"><div><dt>Input revision</dt><dd>${s.revision}${s.current?' (current)':' (stale)'}</dd></div><div><dt>Buyer requirements</dt><dd>${h(record.inputs.requirements_version.toUpperCase())}</dd></div><div><dt>Decision type</dt><dd>${h(record.decision==='eligible'?'Documentary eligible for consideration':'Conditional; blockers retained')}</dd></div><div><dt>As-of date</dt><dd>${h(record.as_of)}</dd></div><div><dt>Known cost / upper total</dt><dd>${money(p.cost.known_total)} / ${p.cost.upper_total===null?'open':money(p.cost.upper_total)}</dd></div><div><dt>Frozen preference interval</dt><dd>${scoreText(p.score)} / 100 (${h(record.profile)})</dd></div><div><dt>Bound source documents</dt><dd>${record.inputs.documents.length}</dd></div><div><dt>Bound structured inputs</dt><dd>${Object.keys(record.inputs.structured||{}).length}</dd></div><div class="full"><dt>Frozen assumptions</dt><dd>${h(record.assumptions.years)} years; ${h(record.assumptions.replacements_per_aircraft_per_year)} replacement batteries / aircraft / year; optional equipment ${record.assumptions.include_optional?'included':'excluded'}.</dd></div><div class="full"><dt>Record SHA-256</dt><dd class="hash"><code>${h(s.digest)}</code></dd></div></dl><h3>Mandatory states in this snapshot</h3><div class="all-dispositions">${p.assessments.filter(a=>record.evaluation.requirements.find(r=>r.id===a.requirement_id)?.mode==='mandatory').map(a=>badge(a.state,`${a.requirement_id}: ${labels[a.state]}`)).join('')}</div><h3>Snapshot limitations</h3><ul class="small muted">${record.limitations.map(l=>`<li>${h(l)}</li>`).join('')}</ul>${s.review?`<div class="snapshot-review"><strong>Technical review / ${h(dateTime(s.review.at))}</strong><p class="review-note">${h(s.review.note)}</p></div>`:''}${s.approval?`<div class="snapshot-review"><strong>Approval / ${h(dateTime(s.approval.at))}</strong><p class="review-note">${h(s.approval.note)}</p></div>`:''}${action?`<form id="snapshot-action-form" class="review-form" data-id="${h(s.id)}" data-kind="${h(action)}"><h3>${action==='review'?'Record technical review':'Approve this decision'}</h3><p class="field-hint">This action binds your ${action==='review'?'review':'approval'} to the displayed snapshot digest. ${record.decision==='conditional'?'The decision remains conditional and is not purchasing authorization.':'This is documentary eligibility for further consideration only.'}</p><label for="snapshot-action-note">${action==='review'?'Technical review':'Approval'} note</label><textarea id="snapshot-action-note" name="note" required maxlength="4000"></textarea><p class="form-error" hidden role="alert"></p><button type="submit" class="button primary">${action==='review'?'Record technical review':'Approve decision'}</button></form>`:''}<div class="section-split"><a class="button" href="/api/export/${encodeURIComponent(s.id)}" download>Export ${s.current?'decision package':'stale decision record'}</a><p class="inline-note">ZIP includes the readable report, frozen decision JSON, source bytes, manifest, CSV tables, and an offline integrity verifier. Hash integrity binds content; it does not establish that the underlying supplier claims are true.</p></div>`,{kind:'snapshot',id});
}

for (const button of document.querySelectorAll('#navigation [data-view]')) {
  button.innerHTML=`<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[button.dataset.view]}</svg><span>${h(views[button.dataset.view])}</span>`;
}
document.addEventListener('click', async event=>{
  const target=event.target.closest('button, a[data-action]');if(!target)return;
  if(target.dataset.view){navigate(target.dataset.view);return;}
  const action=target.dataset.action;
  try {
    switch(action){
      case 'dismiss-notice':$('#notice').hidden=true;break;
      case 'close-detail':detailRequest++;$('#detail-dialog').close();break;
      case 'close-login':$('#login-dialog').close();break;
      case 'package':showPackage(target.dataset.package);break;
      case 'assessment':showAssessment(target.dataset.package,target.dataset.requirement);break;
      case 'assertion':await showAssertion(target.dataset.id);break;
      case 'compare-package':ui.comparePackage=target.dataset.package;$('#detail-dialog').close();navigate('comparison');break;
      case 'matrix-package':ui.reqPackage=target.dataset.package;ui.reqMode='all';ui.reqState='all';$('#detail-dialog').close();navigate('requirements');break;
      case 'assurance-package':ui.assurancePackage=target.dataset.package;$('#detail-dialog').close();navigate('assurance');break;
      case 'evidence-page':ui.evidencePage+=Number(target.dataset.delta);render();break;
      case 'apply-amendment':await mutate('/api/amendments',{id:target.dataset.id},`${target.dataset.id} applied. Inspect the assessment changes and stale decision status below.`);break;
      case 'snapshot-detail':showSnapshot(target.dataset.id);break;
      case 'snapshot-review':showSnapshot(target.dataset.id,'review');break;
      case 'snapshot-approve':showSnapshot(target.dataset.id,'approve');break;
    }
  }catch(error){showNotice(error.message,true);}
});
function filterChanged(target){
  if(!target.dataset.filter)return;
  ui[target.dataset.filter]=target.value;
  if(target.dataset.filter.startsWith('evidence'))ui.evidencePage=0;
  render();
}
document.addEventListener('input',event=>{if(event.target.matches('input[data-filter]'))filterChanged(event.target);});
document.addEventListener('change',event=>{if(event.target.matches('select[data-filter]'))filterChanged(event.target);});
$('#session-button').addEventListener('click',()=>{
  $('#login-error').hidden=true;
  $('#login-password').value='';
  $('#login-dialog').showModal();
  $('#login-role').focus();
});
$('#login-role').addEventListener('change',()=>{
  $('#password-hint').innerHTML=`For this role, enter <code>cedar-${h($('#login-role').value)}</code>.`;
  $('#login-password').value='';
});
$('#refresh-button').addEventListener('click',async()=>{
  try{await refresh();showNotice(`Workbench refreshed to revision ${state.revision}.`);}catch(error){showNotice(error.message,true);}
});
$('#detail-dialog').addEventListener('close',()=>{detailContext=null;detailRequest++;});
window.addEventListener('hashchange',()=>{const view=location.hash.slice(1);if(views[view])navigate(view);});
document.addEventListener('submit',async event=>{
  event.preventDefault();
  const form=event.target, data=new FormData(form);
  if(form.id==='login-form'){
    try{
      const result=await api('/api/login',{method:'POST',body:JSON.stringify({role:data.get('role'),password:data.get('password')})});
      session=result;
      $('#login-dialog').close();
      await refresh();
      showNotice(`Signed in as ${session.role}. Role permissions are enforced by the server.`);
    }catch(error){$('#login-error').textContent=error.message;$('#login-error').hidden=false;}
    return;
  }
  switch(form.id){
    case 'settings-form':await mutate('/api/settings',{profile:data.get('profile'),assumptions:{years:Number(data.get('years')),replacements_per_aircraft_per_year:Number(data.get('replacements')),include_optional:data.has('include_optional')}},'Assumptions saved. Existing snapshots are stale; compare the updated totals and preference contributions.');break;
    case 'policy-form':await mutate('/api/settings',{requirements_version:data.get('requirements_version')},'Buyer requirements updated. Inspect the resulting assessment differences below.');break;
    case 'snapshot-form':await mutate('/api/snapshots',{package_id:data.get('package_id'),decision:data.get('decision'),rationale:data.get('rationale')},'Decision snapshot created. A separate technical reviewer can now review this frozen record.');break;
    case 'assertion-review-form':await mutate(`/api/assertions/${encodeURIComponent(form.dataset.id)}/review`,{status:data.get('status'),note:data.get('note')},'Interpretation review recorded. The evaluation was refreshed and previous decision snapshots are stale.',()=>showAssertion(form.dataset.id));break;
    case 'snapshot-action-form':await mutate(`/api/snapshots/${encodeURIComponent(form.dataset.id)}/${form.dataset.kind}`,{note:data.get('note')},form.dataset.kind==='review'?'Technical review recorded against the current snapshot digest.':'Approval recorded against the current reviewed snapshot digest.',()=>$('#detail-dialog').close());break;
    case 'upload-form':{
      const file=data.get('source');
      if(!file||!file.size){showNotice('Choose a nonempty UTF-8 .txt or .md document.',true);break;}
      if(file.size>102400){showNotice('Source exceeds the 100 KiB limit. Choose a smaller text document.',true);break;}
      if(!/\.(txt|md)$/.test(file.name)){showNotice('Only .txt and .md source documents are accepted. Archives are not supported.',true);break;}
      let content;
      try{content=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());}catch{showNotice('The source is not valid UTF-8 text. Save it as UTF-8 and try again.',true);break;}
      await mutate('/api/uploads',{filename:file.name,content,package_id:data.get('package_id'),title:data.get('title')},'Source imported as inert text. Review the extracted assertions before relying on the updated evaluation.');
      break;
    }
  }
});
async function start(){
  try{session=await api('/api/session');}catch(error){if(error.status!==401)showNotice(`Session could not be restored: ${error.message}`,true);}
  try{await refresh();}catch(error){$('#main-content').innerHTML=empty('The local workbench could not be loaded',`${error.message} Use Refresh workbench after the local server is available.`);}
}
start();
