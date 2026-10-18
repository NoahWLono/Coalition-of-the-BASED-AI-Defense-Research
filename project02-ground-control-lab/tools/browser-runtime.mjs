import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {homedir} from 'node:os';
const require=createRequire(import.meta.url);
process.env.PLAYWRIGHT_BROWSERS_PATH??=resolve('.cache/ms-playwright');
let playwright;
try{playwright=require('playwright');}catch{playwright=require(process.env.PLAYWRIGHT_MODULE??resolve(homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));}
export const chromium=playwright.chromium;
