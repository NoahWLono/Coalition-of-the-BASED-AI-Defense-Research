import {readdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {join,relative} from 'node:path';
const root=fileURLToPath(new URL('..',import.meta.url));
async function list(path){const entries=await readdir(path,{withFileTypes:true});const files=[];for(const e of entries){const p=join(path,e.name),rel=relative(root,p);if(['.cache','node_modules','.git'].includes(e.name)||rel==='evidence/downloads'||rel==='evidence/SHA256SUMS')continue;if(e.isDirectory())files.push(...await list(p));else if(e.isFile())files.push(p);}return files;}
const files=(await list(root)).sort();
const lines=[];for(const path of files)lines.push(`${createHash('sha256').update(await readFile(path)).digest('hex')}  ${relative(root,path)}`);
await writeFile(new URL('../evidence/SHA256SUMS',import.meta.url),lines.join('\n')+'\n');console.log(`Hashed ${files.length} deliverable files; browser cache and duplicate downloads excluded.`);
