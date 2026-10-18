import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {chromium} from './browser-runtime.mjs';
import {createServer} from './serve.mjs';
import {inspectDocument,checkGroups} from './dom-audit.mjs';
const server=createServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await chromium.launch({headless:true}),page=await browser.newPage();
const results=[];
try{
  const oracle=JSON.parse(await readFile(new URL('../data/oracle.json',import.meta.url)));
  const expected=oracle.find(o=>o.scenarioId==='interrupted'&&o.at===3).expected;
  await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForFunction(()=>window.lab?.state);
  await page.locator('#checkpoint').selectOption('3');await page.locator('#variant').selectOption('grouped');
  await page.locator('[data-fact="owner"] .fact-value').evaluate(el=>el.style.display='none');
  results.push({mutation:'hidden owner value',detected:(await page.evaluate(inspectDocument)).issues.length>0});
  await page.locator('#variant').selectOption('chronological');await page.locator('#variant').selectOption('grouped');
  await page.locator('[data-alarm-group] h3').evaluate(el=>el.textContent='battery 1 alarm');
  let detected=false;try{checkGroups(await page.evaluate(inspectDocument),expected,'grouped');}catch{detected=true;}
  results.push({mutation:'misleading visible heading only',detected});
  console.log(JSON.stringify(results,null,2));
  assert.ok(results.every(r=>r.detected),'DOM-only semantic faults must be detected');
  await writeFile(new URL('../evidence/audit-regressions.json',import.meta.url),JSON.stringify(results,null,2)+'\n');
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
