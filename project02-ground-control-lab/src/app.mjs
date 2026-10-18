import { ReplayController, facts } from './engine.mjs';
import { renderView, viewDefinitions } from './views.mjs';
import { compareFacts } from './evaluator.mjs';

const $ = id => document.getElementById(id);
const view = $('view');
let scenarios = [], oracle = [], controller = null;
let variant = $('variant').value;
const disclosureMemory = new Map();
const formatTime = seconds => `${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;
const announce = text => { $('announcer').textContent = text; };
Object.defineProperty(window, 'lab', {value: Object.freeze({
  get state() { return controller ? structuredClone(controller.state) : null; },
  get variant() { return variant; },
  get scenario() { return controller ? structuredClone(controller.scenario) : null; }
}), writable:false, configurable:false});

function saveDisclosures() {
  for (const detail of view.querySelectorAll('details')) disclosureMemory.set(detail.id, detail.open);
}
function updateVisibility() {
  for (const node of view.querySelectorAll('[data-fact]')) {
    const parent = node.closest('details');
    node.dataset.visibility = parent && !parent.open ? 'obscured' : 'visible';
  }
}
function readDisplayedFacts() {
  return Object.fromEntries([...view.querySelectorAll('[data-fact]')].map(node => {
    const meta = node.querySelector('.fact-meta').textContent;
    const status = meta.match(/\b(known|stale|unknown)\b/)?.[1];
    const timeMatch = meta.match(/t=(\d+) s/);
    const at = timeMatch ? Number(timeMatch[1]) : null;
    const value = node.querySelector('.fact-value').textContent;
    const metadataMatches = value === node.dataset.value && status === node.dataset.status && String(at) === node.dataset.at && (timeMatch || meta.includes('no timestamp'));
    return [node.dataset.fact, {value, status:metadataMatches ? status : 'invalid display metadata',at,visibility:node.dataset.visibility}];
  }));
}
function checkOracle() {
  const checkpoint=oracle.find(row=>row.scenarioId===controller.scenario.id && row.at===controller.state.time);
  if (!checkpoint) {
    $('oracle-result').textContent='Between checkpoints';
    $('oracle-result').className='oracle-neutral';
    $('oracle-rationale').textContent='Select an oracle checkpoint to compare this screen with a literal truth-table row.';
    return;
  }
  const rows=compareFacts(readDisplayedFacts(),checkpoint.expected);
  const correct=rows.filter(row=>row.correct).length;
  $('oracle-result').textContent=`${correct} of ${rows.length} facts match the oracle`;
  $('oracle-result').className=correct===rows.length?'oracle-pass':'oracle-fail';
  $('oracle-rationale').textContent=correct===rows.length?checkpoint.rationale:rows.filter(row=>!row.correct).map(row=>`${row.fact}: ${row.reason}`).join('; ');
}
function render() {
  saveDisclosures();
  const focusId = view.contains(document.activeElement) ? document.activeElement.id : null;
  view.innerHTML=renderView(controller.state,variant);
  for (const detail of view.querySelectorAll('details')) detail.open=disclosureMemory.get(detail.id)??false;
  updateVisibility();
  if(focusId) document.getElementById(focusId)?.focus({preventScroll:true});
  const {time}=controller.state, {duration,checkpoints}=controller.scenario;
  $('timeline').value=time;
  $('timeline').setAttribute('aria-valuetext',`${time} of ${duration} seconds`);
  $('time').value=formatTime(time);
  $('play').textContent=controller.playing?'Pause':'Play';
  $('play').setAttribute('aria-pressed',String(controller.playing));
  $('play').disabled=time===duration && !controller.playing;
  $('playback-state').textContent=controller.playing?'Playing':time===duration?'Replay ended':'Paused';
  $('back').disabled=time===0;
  $('forward').disabled=time===duration;
  $('checkpoint').value=checkpoints.includes(time)?String(time):'';
  checkOracle();
}
function updateDesignDecision() {
  const definition=viewDefinitions[variant];
  const choices={chronological:'Arrival order is prominent. Principal issue, declared groups, next actor and historical telemetry require opening the evidence disclosure.',grouped:'Declared issue groups are prominent. Handover phase, target and next actor require opening the handover disclosure.',handover:'Responsibility and transfer state are prominent. Detailed alarms, receipts and group mappings require opening the alarm disclosure.'};
  $('visibility-decision').textContent=choices[variant];
  $('visible-count').textContent=`${11-definition.hidden.length} facts`;
  $('obscured-count').textContent=`${definition.hidden.length} facts`;
}
function chooseScenario(id) {
  controller?.pause();
  const scenario=scenarios.find(item=>item.id===id);
  controller=new ReplayController(scenario);
  view.replaceChildren();
  disclosureMemory.clear();
  $('scenario-context').textContent=`${scenario.vehicle} / ${scenario.location}`;
  $('scenario-title').textContent=scenario.title;
  $('scenario-description').textContent=scenario.description;
  $('completion-condition').textContent=scenario.completionCondition;
  $('timeline').max=scenario.duration;
  $('duration-label').textContent=`${scenario.duration} seconds`;
  $('checkpoint').replaceChildren(new Option('Between checkpoints',''),...scenario.checkpoints.map(at=>new Option(`t=${at} s`,String(at))));
  $('checkpoint').options[0].disabled=true;
  render();
}
function download(name,contents,type) {
  const url=URL.createObjectURL(new Blob([contents],{type}));
  const link=document.createElement('a');link.href=url;link.download=name;link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
  $('export-result').textContent=`Downloaded ${name}.`;
}
function exportJSON(kind) {
  const payload=kind==='scenario'?controller.scenario:kind==='state'?{scenarioId:controller.scenario.id,variant,time:controller.state.time,facts:facts(controller.state),state:controller.state}:{scenarioId:controller.scenario.id,time:controller.state.time,eventOrder:'script order; deadline timeout before same-time events',history:controller.state.history};
  download(`${controller.scenario.id}-${kind}${kind==='scenario'?'':`-t${controller.state.time}`}.json`,JSON.stringify({synthetic:true,...payload},null,2)+'\n','application/json');
}
$('scenario').addEventListener('change',()=>{chooseScenario($('scenario').value);announce('Scenario changed. Replay paused at zero seconds.');});
$('variant').addEventListener('change',()=>{variant=$('variant').value;updateDesignDecision();if(controller)render();announce(`${viewDefinitions[variant].name}. Replay time and playback state preserved.`);});
$('checkpoint').addEventListener('change',()=>{controller.seek(Number($('checkpoint').value));render();announce(`Checkpoint ${controller.state.time} seconds. Playback paused.`);});
$('timeline').addEventListener('input',()=>{controller.seek(Number($('timeline').value));render();});
$('play').addEventListener('click',()=>{controller.playing?controller.pause():controller.play();render();announce(controller.playing?'Replay playing.':'Replay paused.');});
$('reset').addEventListener('click',()=>{controller.reset();render();announce('Replay reset to zero seconds and paused.');});
$('back').addEventListener('click',()=>{controller.step(-1);render();announce(`Rewound to ${controller.state.time} seconds. Playback paused.`);});
$('forward').addEventListener('click',()=>{controller.step(1);render();announce(`Advanced to ${controller.state.time} seconds. Playback paused.`);});
$('grayscale').addEventListener('change',()=>document.documentElement.classList.toggle('grayscale',$('grayscale').checked));
view.addEventListener('toggle',event=>{if(event.target.matches('details')){disclosureMemory.set(event.target.id,event.target.open);updateVisibility();if(controller)checkOracle();}},true);
for(const kind of ['scenario','state','trace']) $('export-'+kind).addEventListener('click',()=>exportJSON(kind));
$('export-matrix').addEventListener('click',async()=>{
  try {
    const response=await fetch('./evidence/correctness-matrix.csv');
    if(!response.ok)throw new Error('The generated CSV is unavailable. Run npm run evaluate in the project directory, then retry.');
    download('correctness-matrix.csv',await response.text(),'text/csv');
  } catch(error) { $('export-result').textContent=error.message; }
});
setInterval(()=>{
  if(!controller?.playing)return;
  const previous=controller.state.handover.phase;
  controller.tick();render();
  if(previous!==controller.state.handover.phase)announce(`At ${controller.state.time} seconds, handover is ${controller.state.handover.phase}. Responsibility: ${facts(controller.state).owner.value}, ${facts(controller.state).owner.status}.`);
},1000);

try {
  [scenarios,oracle]=await Promise.all(['./data/scenarios.json','./data/oracle.json'].map(async url=>{const response=await fetch(url);if(!response.ok)throw new Error(`Could not load ${url}. Start the local server from the project directory and reload.`);return response.json();}));
  if(!Array.isArray(scenarios)||!scenarios.length||!Array.isArray(oracle))throw new Error('Scenario or oracle data is missing. Restore the project data files and reload.');
  $('scenario').replaceChildren(...scenarios.map((scenario,index)=>new Option(`${String(index+1).padStart(2,'0')} / ${scenario.title}`,scenario.id)));
  for(const id of ['scenario','checkpoint','play','back','forward','reset','timeline','export-scenario','export-state','export-trace','export-matrix'])$(id).disabled=false;
  $('scenario').value=scenarios.some(s=>s.id==='interrupted')?'interrupted':scenarios[0].id;
  chooseScenario($('scenario').value);updateDesignDecision();view.setAttribute('aria-busy','false');
} catch(error) {
  view.replaceChildren(Object.assign(document.createElement('p'),{className:'error',textContent:error.message}));
  view.setAttribute('aria-busy','false');$('oracle-result').textContent='Unable to evaluate: data did not load.';
}
