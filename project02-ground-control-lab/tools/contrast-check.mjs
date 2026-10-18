import {readFile,writeFile} from 'node:fs/promises';
const css=await readFile(new URL('../styles.css',import.meta.url),'utf8');
const tokens=selector=>{
  const start=css.indexOf(selector+'{');
  if(start===-1)throw new Error(`Missing palette: ${selector}`);
  const block=css.slice(start+selector.length+1,css.indexOf('}',start));
  return Object.fromEntries([...block.matchAll(/--([\w-]+):\s*(#[\da-f]{6})\s*;/gi)].map(([,name,value])=>[name,value]));
};
const palettes={dark:tokens(':root'),light:tokens(':root[data-theme="light"]')};
const pairs=[
  ['main text / page','ink','surface'],['main text / paper','ink','paper'],
  ['muted text / paper','muted','paper'],['muted text / rail','muted','rail-surface'],
  ['muted text / principal band','muted','principal-surface'],['muted text / handover details','muted','detail-surface'],
  ['muted text / critical alarm','muted','alarm-critical-surface'],['muted text / rejected event','muted','rejected-surface'],
  ['caution / paper','caution','paper'],['caution / ownership board','caution','board-surface'],
  ['caution / handover details','caution','detail-surface'],['critical / ownership board','critical','board-surface'],
  ['critical / alarm','critical','alarm-critical-surface'],['known / handover details','known','detail-surface'],
  ['rejected event / background','rejected-ink','rejected-surface'],['primary button','primary-ink','navy'],
  ['primary button hover','primary-ink','primary-hover'],['focus / paper','indigo','paper'],
  ['focus / page','indigo','surface'],['focus / hover','indigo','hover'],['success / rail','success','rail-surface'],
  ['control border / paper','control-line','paper',3]
];
const luminance=hex=>{const channels=hex.slice(1).match(/../g).map(h=>parseInt(h,16)/255).map(c=>c<=0.04045?c/12.92:((c+0.055)/1.055)**2.4);return channels[0]*0.2126+channels[1]*0.7152+channels[2]*0.0722;};
const results=Object.entries(palettes).flatMap(([theme,palette])=>pairs.map(([use,fg,bg,minimum=4.5])=>{
  const foreground=palette[fg],background=palette[bg];
  if(!foreground||!background)throw new Error(`Missing color token: ${theme} ${fg}/${bg}`);
  const a=luminance(foreground),b=luminance(background),contrast=(Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
  return {theme,use,foreground,background,minimum,ratio:Number(contrast.toFixed(2)),pass:contrast>=minimum};
}));
await writeFile(new URL('../evidence/contrast.json',import.meta.url),JSON.stringify({method:'sRGB relative luminance contrast ratio from current CSS tokens; selected solid-color pairs, not a rendered DOM audit. Text and focus pairs use 4.5:1; control borders use 3:1.',results},null,2)+'\n');
console.log(JSON.stringify(results,null,2));
if(results.some(r=>!r.pass))process.exitCode=1;
