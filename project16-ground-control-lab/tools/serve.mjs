import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve,extname,sep } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
const types={'.html':'text/html','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.csv':'text/csv','.png':'image/png','.md':'text/plain','.txt':'text/plain'};
export function createServer(){return http.createServer(async(req,res)=>{
  try{
    if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);res.end();return;}
    const url=new URL(req.url,'http://127.0.0.1');
    const path=resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname));
    if(!path.startsWith(root+sep)||!types[extname(path)]){res.writeHead(404);res.end('Not found');return;}
    const body=await readFile(path);
    res.writeHead(200,{'Content-Type':types[extname(path)]+'; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"});
    res.end(req.method==='HEAD'?undefined:body);
  }catch{res.writeHead(404);res.end('Not found');}
});}
if(process.argv[1]===fileURLToPath(import.meta.url))createServer().listen(Number(process.env.PORT??4160),'127.0.0.1',()=>console.log('Ground-control lab: http://127.0.0.1:'+(process.env.PORT??4160)));
