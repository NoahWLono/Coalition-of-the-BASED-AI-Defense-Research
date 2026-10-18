// No imports from the replay engine: expectations come exclusively from literal oracle records.
export function compareFacts(actual,expected) {
  return Object.entries(expected).map(([fact,want])=>{
    const got=actual[fact];
    const errors=[];
    if(!got)errors.push('missing fact');
    else for(const key of ['value','status','at'])if(got[key]!==want[key])errors.push(`${key}: expected ${JSON.stringify(want[key])}, got ${JSON.stringify(got[key])}`);
    const visibility=got?.visibility??(got?'visible':'omitted');
    return {fact,expected:want,actual:got??null,correct:errors.length===0,reason:errors.join('; '),visibility,steps:visibility==='omitted'?null:visibility==='obscured'?1:0};
  });
}
export function toCSV(rows) {
  if(!rows.length)return '';
  const keys=Object.keys(rows[0]);
  const cell=v=>{const s=v===null||v===undefined?'':typeof v==='object'?JSON.stringify(v):String(v);return /[",\n\r]/.test(s)?'"'+s.replaceAll('"','""')+'"':s;};
  return [keys.join(','),...rows.map(row=>keys.map(k=>cell(row[k])).join(','))].join('\n')+'\n';
}
function decode(value) {
  return value.replace(/&(?:amp|quot|lt|gt|#39|apos);/g,e=>({'&amp;':'&','&quot;':'"','&lt;':'<','&gt;':'>','&#39;':"'",'&apos;':"'"}[e]));
}
export function parseRenderedFacts(html) {
  const result={};
  for(const match of html.matchAll(/<[^>]+\bdata-fact="[^"]+"[^>]*>/g)) {
    const attr=Object.fromEntries([...match[0].matchAll(/data-([\w-]+)="([^"]*)"/g)].map(x=>[x[1],decode(x[2])]));
    if(result[attr.fact])throw new Error(`Duplicate rendered fact: ${attr.fact}`);
    result[attr.fact]={value:attr.value,status:attr.status,at:attr.at==='null'?null:Number(attr.at),visibility:attr.visibility,steps:attr.visibility==='obscured'?1:0};
  }
  return result;
}
