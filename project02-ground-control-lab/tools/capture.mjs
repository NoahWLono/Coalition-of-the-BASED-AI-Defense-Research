import {fileURLToPath} from 'node:url';
import {chromium} from './browser-runtime.mjs';
import {createServer} from './serve.mjs';
const server=createServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:1440,height:1080},reducedMotion:'reduce'});
async function capture(name){await page.locator('#variant').focus();await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:fileURLToPath(new URL(`../screenshots/${name}.png`,import.meta.url)),fullPage:true});}
try{
  await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForFunction(()=>window.lab?.state);
  await page.locator('#checkpoint').selectOption('5');
  for(const variant of ['chronological','grouped','handover']){await page.locator('#variant').selectOption(variant);await capture(variant);}
  await page.locator('#grayscale').check();await capture('grayscale');await page.locator('#grayscale').uncheck();
  await page.locator('#scenario').selectOption('alarm_cascade');await page.locator('#checkpoint').selectOption('5');await page.locator('#variant').selectOption('grouped');await capture('alarm-flood');
  await page.setViewportSize({width:390,height:844});await capture('mobile');
  console.log('Saved six final screenshots; design control focused and page at top.');
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
