import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium} from './browser-runtime.mjs';
import {createServer} from './serve.mjs';
import {compareFacts,toCSV} from '../src/evaluator.mjs';
import {inspectDocument,checkGroups} from './dom-audit.mjs';
const scenarios=JSON.parse(await readFile(new URL('../data/scenarios.json',import.meta.url)));
const oracle=JSON.parse(await readFile(new URL('../data/oracle.json',import.meta.url)));
const server=createServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1080},reducedMotion:'reduce',acceptDownloads:true});
const page=await context.newPage();page.setDefaultTimeout(8000);
const consoleErrors=[],externalRequests=[],rows=[],mutations=[],keyboard=[],orderHashes=[],downloads=[];
page.on('pageerror',e=>consoleErrors.push(e.message));
page.on('request',r=>{if(!r.url().startsWith(origin)&&!r.url().startsWith('blob:'))externalRequests.push(r.url());});
await mkdir(new URL('../screenshots/',import.meta.url),{recursive:true});
await mkdir(new URL('../evidence/downloads/',import.meta.url),{recursive:true});
async function inspect(){return page.evaluate(inspectDocument);}
async function tabTo(id){let presses=0;while(await page.evaluate(()=>document.activeElement?.id)!==id){await page.keyboard.press('Tab');if(++presses>80)throw new Error(`Cannot reach ${id} by Tab`);}return presses;}
try{
  await page.goto(origin);await page.waitForFunction(()=>window.lab?.state);
  for(const s of scenarios){
    await page.locator('#scenario').selectOption(s.id);
    for(const at of s.checkpoints){
      await page.locator('#checkpoint').selectOption(String(at));
      let hash=null;
      for(const variant of ['chronological','grouped','handover']){
        await page.locator('#variant').selectOption(variant);
        await page.locator('#view details').evaluateAll(nodes=>nodes.forEach(n=>n.open=false));
        const result=await inspect(),expected=oracle.find(o=>o.scenarioId===s.id&&o.at===at).expected;
        assert.deepEqual(result.issues,[]);assert.equal(Object.keys(result.actual).length,11);
        const compared=compareFacts(result.actual,expected);
        assert.deepEqual(compared.filter(r=>!r.correct),[],`${s.id}/${at}/${variant}`);checkGroups(result,expected,variant);
        for(const alarm of result.alarms){
          const source=s.events.find(e=>e.type==='alarm'&&e.id===alarm.id&&e.at<=at);
          assert.ok(source);assert.equal(alarm.label,source.label);assert.ok(alarm.severity.endsWith(source.severity));assert.equal(alarm.time,`knownt=${source.at} s`);
        }
        await page.locator('#view details').evaluateAll(nodes=>nodes.forEach(n=>n.open=true));
        const expanded=await inspect();assert.deepEqual(expanded.issues,[],`${s.id}/${at}/${variant}: expanded evidence must be readable`);
        for(const fact of Object.values(expanded.actual))assert.equal(fact.visibility,'visible');
        await page.locator('#view details').evaluateAll(nodes=>nodes.forEach(n=>n.open=false));
        const currentHash=createHash('sha256').update(JSON.stringify(result.history)).digest('hex');
        if(hash!==null)assert.equal(currentHash,hash,'view changed event order/time');hash=currentHash;
        for(const r of compared)rows.push({scenario:s.id,second:at,variant,fact:r.fact,value:r.actual.value,status:r.actual.status,timestamp:r.actual.at,visibility:r.visibility,disclosure_steps:r.steps,correct:r.correct});
      }
      orderHashes.push({scenario:s.id,at,sha256:hash});
    }
  }
  for(const variant of ['chronological','grouped','handover']){
    await page.locator('#scenario').selectOption('interrupted');await page.locator('#checkpoint').selectOption('3');await page.locator('#variant').selectOption(variant);
    const expected=oracle.find(o=>o.scenarioId==='interrupted'&&o.at===3).expected;
    for(const [name,key] of [['wrong ownership','owner'],['misleading grouping','alarmGroups']]){
      await page.evaluate(async({name,variant})=>{const {renderView}=await import('./src/views.mjs');const s=structuredClone(window.lab.state);if(name==='wrong ownership')s.owner.value='Operator B';else s.alarms[0].group='battery';document.querySelector('#view').innerHTML=renderView(s,variant);},{name,variant});
      const result=await inspect();const failures=compareFacts(result.actual,expected).filter(r=>!r.correct);
      assert.ok(failures.some(r=>r.fact===key),`missed ${name}`);mutations.push({name,variant,detected:true,failedFacts:failures.map(r=>r.fact)});
    }
  }
  const stale=oracle.find(o=>o.expected.owner.status==='stale');
  await page.locator('#scenario').selectOption(stale.scenarioId);await page.locator('#checkpoint').selectOption(String(stale.at));
  await page.evaluate(()=>{const el=document.querySelector('[data-fact="owner"]');el.dataset.status='known';el.querySelector('.fact-meta').textContent=el.querySelector('.fact-meta').textContent.replace('stale','known');});
  assert.ok(compareFacts((await inspect()).actual,stale.expected).some(r=>r.fact==='owner'&&!r.correct));mutations.push({name:'stale owner displayed current',detected:true});
  // Fresh load, then only Tab/arrow/Enter/Space for the core task sequence.
  await page.goto(origin);await page.waitForFunction(()=>window.lab?.state);
  await tabTo('scenario');await page.keyboard.press('Home');await page.keyboard.press('Enter');
  await tabTo('checkpoint');await page.keyboard.press('Home');for(let i=0;i<3;i++)await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>window.lab.state.time),5);
  for(const [index,variant] of ['chronological','grouped','handover'].entries()){
    await tabTo('variant');await page.keyboard.press('Home');for(let i=0;i<index;i++)await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(()=>window.lab.variant),variant);
    const before=await inspect();const expected=oracle.find(o=>o.scenarioId==='interrupted'&&o.at===5).expected;
    const taskKeys=['owner','nextActor','principal','lastReliable'];
    const hidden=taskKeys.filter(k=>before.actual[k].visibility==='obscured');
    let tabs=0;if(hidden.length){tabs=await tabTo(`${variant}-evidence-toggle`);await page.keyboard.press('Enter');}
    const after=await inspect();for(const k of taskKeys){assert.equal(after.actual[k].visibility,'visible');assert.equal(after.actual[k].value,expected[k].value);}
    keyboard.push({variant,scenario:'interrupted',at:5,taskFacts:taskKeys,hiddenBefore:hidden,disclosureActivations:hidden.length?1:0,tabsToDisclosure:tabs,passed:true});
    const active=await page.evaluate(()=>{const el=document.activeElement,s=getComputedStyle(el);return {id:el.id,outlineStyle:s.outlineStyle,outlineWidth:s.outlineWidth};});
    assert.notEqual(active.outlineStyle,'none');assert.ok(parseFloat(active.outlineWidth)>=2);keyboard.at(-1).focus=active;
  }
  await tabTo('play');await page.keyboard.press('Enter');
  await page.waitForFunction(()=>window.lab.state.time>5);
  assert.equal(await page.evaluate(()=>document.activeElement.id),'play');
  await tabTo('reset');await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>window.lab.state.time),0);
  await page.waitForTimeout(1150);assert.equal(await page.evaluate(()=>window.lab.state.time),0);
  await tabTo('forward');await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>window.lab.state.time),1);
  await tabTo('back');await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>window.lab.state.time),0);
  const inputs=await page.locator('button,select,input,summary').evaluateAll(nodes=>nodes.map(el=>({id:el.id,name:el.getAttribute('aria-label')||[...el.labels??[]].map(l=>l.textContent.trim()).join(' ')||el.textContent.trim(),tabindex:el.tabIndex})));
  assert.ok(inputs.every(i=>i.name),'unnamed interactive control');assert.ok(inputs.every(i=>i.tabindex>=0),'unreachable control');
  await writeFile(new URL('../evidence/accessibility-tree.txt',import.meta.url),await page.locator('body').ariaSnapshot());
  // Persisted regressions for disclosure reset and exact status parsing in the on-screen checker.
  await page.locator('#variant').selectOption('grouped');
  await page.locator('[data-fact="owner"] .fact-meta').evaluate(el=>el.textContent=el.textContent.replace('known','unknown'));
  await page.locator('#grouped-evidence-toggle').click();
  await page.waitForFunction(()=>document.querySelector('#oracle-result').textContent.startsWith('10 of 11'));
  assert.match(await page.locator('#oracle-result').textContent(),/^10 of 11/);
  await page.locator('#scenario').selectOption('stale_evidence');
  assert.equal(await page.locator('#grouped-evidence').getAttribute('open'),null);
  await page.locator('#scenario').selectOption('interrupted');await page.locator('#checkpoint').selectOption('5');
  for(const kind of ['scenario','state','trace','matrix']){
    const [download]=await Promise.all([page.waitForEvent('download'),page.locator(`#export-${kind}`).click()]);
    const path=fileURLToPath(new URL(`../evidence/downloads/${download.suggestedFilename()}`,import.meta.url));await download.saveAs(path);
    const text=await readFile(path,'utf8');
    if(kind==='matrix')assert.equal(text,await readFile(new URL('../evidence/correctness-matrix.csv',import.meta.url),'utf8'));
    else {const payload=JSON.parse(text);assert.equal(payload.synthetic,true);
      if(kind==='scenario'){assert.deepEqual(payload.events,scenarios[0].events);assert.deepEqual(payload.checkpoints,scenarios[0].checkpoints);}
      if(kind==='state')assert.deepEqual(payload.state,await page.evaluate(()=>window.lab.state));
      if(kind==='trace')assert.deepEqual(payload.history,await page.evaluate(()=>window.lab.state.history));
    }
    downloads.push({kind,file:download.suggestedFilename(),bytes:Buffer.byteLength(text),payloadVerified:true});
  }
  // Capture equal-checkpoint views, plus flood, grayscale and narrow viewport evidence.
  await page.locator('#checkpoint').selectOption('5');
  await page.locator('h1').click();await page.evaluate(()=>scrollTo(0,0));
  for(const variant of ['chronological','grouped','handover']){
    await page.locator('#variant').selectOption(variant);await page.locator('#view details').evaluateAll(nodes=>nodes.forEach(n=>n.open=false));
    await page.locator('#variant').focus();await page.evaluate(()=>scrollTo(0,0));
    await page.screenshot({path:fileURLToPath(new URL(`../screenshots/${variant}.png`,import.meta.url)),fullPage:true});
  }
  await page.locator('#grayscale').check();
  assert.ok(await page.evaluate(()=>getComputedStyle(document.body).filter.includes('grayscale')||getComputedStyle(document.documentElement).filter.includes('grayscale')));
  const gray=await inspect();assert.equal(gray.actual.owner.value,'Unresolved');assert.equal(gray.actual.owner.status,'unknown');
  await page.locator('#variant').focus();await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:fileURLToPath(new URL('../screenshots/grayscale.png',import.meta.url)),fullPage:true});await page.locator('#grayscale').uncheck();
  await page.locator('#scenario').selectOption('alarm_cascade');await page.locator('#checkpoint').selectOption('5');await page.locator('#variant').selectOption('grouped');
  await page.locator('#variant').focus();await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:fileURLToPath(new URL('../screenshots/alarm-flood.png',import.meta.url)),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.locator('h1').click();await page.evaluate(()=>scrollTo(0,0));
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'horizontal overflow');
  await page.locator('#variant').focus();await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:fileURLToPath(new URL('../screenshots/mobile.png',import.meta.url)),fullPage:true});
  assert.ok(await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches));
  assert.deepEqual(consoleErrors,[]);assert.deepEqual(externalRequests,[]);
  await writeFile(new URL('../evidence/browser-correctness-matrix.csv',import.meta.url),toCSV(rows));
  const report={browser:await browser.version(),scenarios:scenarios.length,checkpoints:oracle.length,renderedChecks:rows.length,passed:true,mutations,keyboard,downloads,controls:inputs,identicalOrderChecks:orderHashes,consoleErrors,externalRequests,checks:['actual text and visible timestamps match oracle','all initially obscured values become readable when expanded','visible group headings, counts and containers match oracle','keyboard core tasks in all variants','visible focus and playback focus retention','reset cancels advancing timer','keyboard step and rewind','scenario change closes disclosures','on-screen checker parses exact status words','all four exported payloads verified','reduced-motion preference','grayscale retains state words','390 px viewport has no horizontal overflow'],limitations:['No human participants','No assistive-technology user session','Single Chromium engine','Grayscale is not a full color-vision-deficiency study']};
  await writeFile(new URL('../evidence/browser-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:true,browser:report.browser,renderedChecks:rows.length,mutations:mutations.length,keyboardVariants:keyboard.length,consoleErrors,externalRequests},null,2));
}catch(error){await writeFile(new URL('../evidence/browser-failure.txt',import.meta.url),error.stack+'\n');throw error;}
finally{await context.close();await browser.close();await new Promise(resolve=>server.close(resolve));}
