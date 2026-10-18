import assert from 'node:assert/strict';
export function inspectDocument(){
  const actual={},issues=[];
  for(const el of document.querySelectorAll('#view [data-fact]')){
    const key=el.dataset.fact;if(actual[key])issues.push(`Duplicate ${key}`);
    const value=el.querySelector('.fact-value')?.textContent.trim();
    const meta=el.querySelector('.fact-meta')?.textContent??'';
    const status=meta.match(/\b(known|stale|unknown)\b/)?.[1];
    const match=meta.match(/t=(\d+) s/),at=match?Number(match[1]):null;
    if(!match&&!meta.includes('no timestamp'))issues.push(`${key}: missing visible timestamp`);
    if(value!==el.dataset.value||status!==el.dataset.status||String(at)!==el.dataset.at)issues.push(`${key}: text and metadata disagree`);
    let closed=false;for(let p=el.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS'&&!p.open)closed=true;
    const visibility=closed?'obscured':'visible';
    if(!closed)for(const node of [el,el.querySelector('.fact-value'),el.querySelector('.fact-meta'),el.querySelector('.fact-label')]){
      if(!node?.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}))issues.push(`${key}: answer or evidence label unexpectedly hidden`);
    }
    actual[key]={value,status,at,visibility};
  }
  const alarms=[...document.querySelectorAll('#view [data-alarm]')].map(el=>{
    const closed=el.closest('details:not([open])');
    if(!closed)for(const selector of ['.alarm-label','.alarm-group','.severity','.alarm-time'])if(!el.querySelector(selector)?.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}))issues.push(`${el.dataset.alarm}: ${selector} hidden`);
    return {id:el.dataset.alarm,group:el.querySelector('.alarm-group')?.textContent.trim(),metadata:el.dataset.group,container:el.closest('[data-alarm-group]')?.dataset.alarmGroup??null,label:el.querySelector('.alarm-label')?.textContent.trim(),severity:el.querySelector('.severity')?.textContent.trim(),time:el.querySelector('.alarm-time')?.textContent.trim()};
  });
  const groups=[...document.querySelectorAll('#view [data-alarm-group]')].map(el=>({
    id:el.dataset.alarmGroup,label:el.querySelector('.group-label')?.textContent.trim(),
    labelVisible:el.querySelector('.group-label')?.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})??false,
    count:el.querySelector('.count')?.textContent.trim()
  }));
  return {actual,issues,alarms,groups,history:window.lab.state.history};
}
export function checkGroups(result,expected,variant){
  const mapping=expected.alarmGroups.value==='None'?[]:expected.alarmGroups.value.split('; ').map(p=>{const split=p.indexOf(': ');return {id:p.slice(0,split),group:p.slice(split+2)};});
  assert.equal(result.alarms.length,mapping.length,'active alarm count differs');
  for(const item of mapping){const a=result.alarms.find(a=>a.id===item.id);assert.ok(a,`missing alarm ${item.id}`);assert.equal(a.group,item.group);assert.equal(a.metadata,item.group);if(variant==='grouped')assert.equal(a.container,item.group);}
  if(variant==='grouped'){
    const groups=[...new Set(mapping.map(m=>m.group))];assert.equal(result.groups.length,groups.length);
    for(const group of groups){const actual=result.groups.find(g=>g.id===group);assert.ok(actual);assert.equal(actual.label,group,'visible group heading differs');assert.equal(actual.labelVisible,true);const count=mapping.filter(m=>m.group===group).length;assert.equal(actual.count,`${count} ${count===1?'alarm':'alarms'}`);}
  }
}
