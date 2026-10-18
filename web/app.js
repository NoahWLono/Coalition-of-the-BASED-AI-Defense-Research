'use strict';

const $ = id => document.getElementById(id);

const palette = ['#167d80','#7663b4','#bc7b30','#426a9d','#9a567c'];

let scenes = [], scene = null, result = null, truth = null, generation = 0;

const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = x => Number(x).toLocaleString(undefined,{
  maximumFractionDigits:2
});

async function get(url){
  const r=await fetch(url);
  if(!r.ok)throw new Error(`Request failed (${r.status})`);
  return r.json();

}
function active(){
  return [...document.querySelectorAll('#observations input:checked')].map(e=>e.value);

}
function message(text,state){
  $('status').textContent=text;
  $('status').dataset.state=state;

}
function choose(){
  scene=scenes.find(s=>s.id===$('scene').value);
  truth=null;
  result=null;
  $('truth').checked=false;
  $('scene-title').textContent=scene.title;
  $('scene-description').textContent=scene.description;
  const noise = scene.noise_model?.kind;
  $('noise-description').textContent = noise === 'gaussian'
    ? 'Gaussian noise. Displayed intervals are ±1σ assumptions, not guaranteed error bounds; the true camera may be excluded.'
    : noise === 'bounded'
      ? 'Uniform bounded error. Each synthetic measurement error lies within its stated tolerance.'
      : 'No added noise. The stated measurement tolerance still defines the possible region.';
  $('explanation').textContent=scene.teaching?.explanation || 'Compare observations to see which regions survive. Cell boundaries reflect the chosen grid resolution.';
  $('observations').innerHTML='<legend class="sr-only">Active observations</legend>'+scene.observations.map(o=>`<label class="observation"><input type="checkbox" value="${escapeHTML(o.id)}" ${(scene.default_observations||scene.observations.map(v=>v.id)).includes(o.id)?'checked':''}><span><strong>${escapeHTML(o.label||o.id)}</strong><span class="measurement">${fmt(o.value_deg)}° ± ${fmt(o.tolerance_deg)}°</span><small>${o.kind==='bearing'?'World-frame bearing':'Unsigned pair angle'} · ${escapeHTML(o.landmarks.join(' / '))}</small></span></label>`).join('');
  $('additional').hidden=!scene.teaching?.additional_observation;
  refresh();

}
async function refresh(){
  const ticket=++generation;
  result=null;
  $('metrics').innerHTML='';
  $('clusters').textContent='Computing a conservative cover…';
  $('runtime').textContent='';
  message('Computing…','loading');
  draw();
  const ids=active();
  $('additional').hidden=!scene.teaching?.additional_observation||ids.includes(scene.teaching.additional_observation);
  try{
    const r=await get(`/api/solve?id=${encodeURIComponent(scene.id)}&n=${$('resolution').value}&obs=${encodeURIComponent(ids.join(','))}`);
    if(ticket!==generation)return;
    result=r;
    message(r.status==='feasible'?'Sampled witnesses found':r.status==='incompatible'?'Incompatible evidence':'Unresolved at this grid',r.status);
    $('metrics').innerHTML=`<div class="metric"><strong>${fmt(r.area_lower)}–${fmt(r.area_upper)} m²</strong><span>Numerical area lower / upper bound</span></div><div class="metric"><strong>${r.components.length} ${r.components.length===1?'cluster':'clusters'}</strong><span>Connected outer-cover clusters</span></div><div class="metric"><strong>${fmt(r.cell_diagonal)} m</strong><span>Cell diagonal / spatial resolution</span></div>`;
    $('clusters').innerHTML=r.components.map((c,i)=>`<span class="cluster" style="border-left:3px solid ${palette[i%palette.length]}">Cover ${i+1}: ${fmt(c.area_lower)}–${fmt(c.area_upper)} m² · ${c.witness_count} sampled witnesses</span>`).join('')||(r.status==='incompatible'?`Numerical exclusion within this search domain and solver padding. No formal floating-point certificate. Conflicting set: ${escapeHTML((r.conflict_observations||[]).join(', ')||'selected observations')}.`:'No sampled witness at this resolution. Refine the grid to inspect the boundary.');
    $('runtime').textContent=`${fmt(r.runtime_ms)} ms · ${r.grid.n} × ${r.grid.n} cells`;
    draw();

  }catch(e){
    if(ticket!==generation)return;
    message('Calculation failed','error');
    $('clusters').textContent=`${e.message}. Change a control to retry.`;
    draw();

  }
}
function draw(){
  if(!scene)return;
  const [xmin,ymin,xmax,ymax]=scene.bounds;
  const W=900,H=650,pad=68,scale=Math.min((W-2*pad)/(xmax-xmin),(H-2*pad)/(ymax-ymin));
  const left=(W-scale*(xmax-xmin))/2,top=(H-scale*(ymax-ymin))/2;
  const X=x=>left+(x-xmin)*scale,Y=y=>H-top-(y-ymin)*scale;
  const parts=[`<title id="map-title">${escapeHTML(scene.title)} survey map</title><desc id="map-description">Landmarks in arbitrary local metres. Solid cells are inner cells (numerical); pale cells form an unresolved boundary cover. ${result?result.components.length+' outer-cover clusters.':'Calculation pending.'}</desc>`];
  let tick=Math.pow(10,Math.floor(Math.log10(Math.max(xmax-xmin,ymax-ymin)/7)));
  if(Math.max(xmax-xmin,ymax-ymin)/tick>12)tick*=2;
  for(let x=Math.ceil(xmin/tick)*tick;
  x<=xmax+1e-8;
  x+=tick){
    parts.push(`<path d="M${X(x)} ${Y(ymin)}V${Y(ymax)}" stroke="${Math.abs(x)<1e-8?'#a4bdc7':'#dbe7eb'}" stroke-width="1"/><text x="${X(x)}" y="${Y(ymin)+24}" text-anchor="middle" font-size="12" fill="#607c88">${fmt(x)}</text>`);

  }for(let y=Math.ceil(ymin/tick)*tick;
  y<=ymax+1e-8;
  y+=tick){
    parts.push(`<path d="M${X(xmin)} ${Y(y)}H${X(xmax)}" stroke="${Math.abs(y)<1e-8?'#a4bdc7':'#dbe7eb'}" stroke-width="1"/><text x="${X(xmin)-14}" y="${Y(y)+4}" text-anchor="end" font-size="12" fill="#607c88">${fmt(y)}</text>`);

  }parts.push(`<rect x="${X(xmin)}" y="${Y(ymax)}" width="${scale*(xmax-xmin)}" height="${scale*(ymax-ymin)}" fill="none" stroke="#b4cad3"/><text x="${X(xmax)+13}" y="${Y(ymin)+4}" font-size="12" fill="#607c88">x / m</text><text x="${X(xmin)}" y="${Y(ymax)-16}" font-size="12" fill="#607c88">y / m</text>`);

if(result){
  const grouped=new Map();
  for(const [ix,iy,kind,component] of result.cells){
    const key=component+':'+kind;
    if(!grouped.has(key))grouped.set(key,[]);
    grouped.get(key).push(`M${X(xmin+ix*result.grid.dx).toFixed(2)} ${Y(ymin+(iy+1)*result.grid.dy).toFixed(2)}h${(scale*result.grid.dx).toFixed(3)}v${(scale*result.grid.dy).toFixed(3)}h${(-scale*result.grid.dx).toFixed(3)}Z`);

  }for(const [key,paths]of grouped){
    const [component,kind]=key.split(':').map(Number);
    const index=result.components.findIndex(c=>c.id===component);
    const color=palette[Math.max(0,index)%palette.length];
    parts.push(`<path d="${paths.join('')}" fill="${color}" fill-opacity="${kind?.74:.22}"/>`);

  }
}
if(truth&&$('truth').checked){
  const [cx,cy]=truth.camera;
  for(const l of scene.landmarks)parts.push(`<path d="M${X(cx)} ${Y(cy)}L${X(l.x)} ${Y(l.y)}" stroke="#a05c37" stroke-width="1.4" stroke-dasharray="5 5" opacity=".65"/>`);
  parts.push(`<circle cx="${X(cx)}" cy="${Y(cy)}" r="9" fill="white" stroke="#a05c37" stroke-width="2"/><path d="M${X(cx)-13} ${Y(cy)}h26M${X(cx)} ${Y(cy)-13}v26" stroke="#a05c37"/><text x="${X(cx)+15}" y="${Y(cy)-14}" font-size="13" fill="#834624" paint-order="stroke" stroke="#fff" stroke-width="4">Synthetic camera</text>`);

}
for(const l of scene.landmarks){
  parts.push(`<path d="M${X(l.x)} ${Y(l.y)-6}l6 6 -6 6 -6 -6Z" fill="#203e4a" stroke="white" stroke-width="1.5"/><text x="${X(l.x)+12}" y="${Y(l.y)-11}" font-size="14" font-weight="bold" fill="#203e4a" paint-order="stroke" stroke="#f8fbfc" stroke-width="4">${escapeHTML(l.label||l.id)}</text>`);

}$('map').innerHTML=parts.join('');

}
$('scene').addEventListener('change',choose);
$('observations').addEventListener('change',refresh);
$('resolution').addEventListener('change',refresh);
$('reset').addEventListener('click',choose);
$('additional').addEventListener('click',()=>{
  const id=scene.teaching.additional_observation;
  for(const e of document.querySelectorAll('#observations input'))if(e.value===id)e.checked=true;
  refresh();

});
$('truth').addEventListener('change',async()=>{
  if(!$('truth').checked){
    draw();
    return;

  }const id=scene.id;
  try{
    const t=await get(`/api/truth?id=${encodeURIComponent(id)}`);
    if(scene.id===id&&$('truth').checked){
      truth=t;
      draw();

    }
  }catch(e){
    if(scene.id===id){
      $('truth').checked=false;
      $('clusters').textContent='Ground truth could not be loaded: '+e.message;

    }
  }
});

(async()=>{
  try{
    const data=await get('/api/scenes');
    scenes=data.scenes;
    const groups=new Map();
    for(const s of scenes){
      const key=s.split||'Scenes';
      if(!groups.has(key))groups.set(key,[]);
      groups.get(key).push(s);

    }$('scene').innerHTML=[...groups].map(([name,items])=>`<optgroup label="${escapeHTML(name)}">${items.map(s=>`<option value="${escapeHTML(s.id)}">${
      escapeHTML(s.id + ': ' + s.title)
    }</option>`).join('')}</optgroup>`).join('');
    $('scene').value=scenes.some(s=>s.id==='benchmark-01')?'benchmark-01':scenes[0].id;
    choose();

  }catch(e){
    message('Unable to load scenes','error');
    $('scene-title').textContent='Laboratory unavailable';
    $('clusters').textContent=e.message;

  }
})();
