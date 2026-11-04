import type {SetupState,ResourceStatus} from '../../services/publication-contracts';
// AROUNDYOU UI CHANGE: consolidate demand without inventing stock or reuse assumptions.
export function resourceRows(state:SetupState){
 const groups=new Map<string,ResourceStatus[]>();
 for(const r of state.resources){const key=[r.title.trim().toLocaleLowerCase(),r.kind,r.unit.trim().toLocaleLowerCase()].join('|');groups.set(key,[...(groups.get(key)??[]),r])}
 return [...groups.values()].map(items=>{
  const source=(r:ResourceStatus)=>Object.values(state.planning.work).filter(w=>state.planning.resources[r.id]?.work_ids?.includes(w.id)||w.resource_requirement_ids.includes(r.id));
  const known=(n:unknown):n is number=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
  let required:number|null=null,review=false;
  if(items.every(r=>known(r.required))){
   if(items.length===1)required=items[0].required;
   else if(items[0].kind==='consumable'){
    const ids=items.flatMap(r=>source(r).map(w=>w.id));
    if(items.some(r=>!source(r).length)||new Set(ids).size!==ids.length)review=true;
    else required=items.reduce((n,r)=>n+r.required!,0);
   }else if(items[0].kind==='equipment'){
    const spans=items.map(r=>{const work=source(r);const t=work[0]?.schedule;return work.length===1&&t?{start:(t.start_day-1)*1440+t.start_minute,end:(t.end_day-1)*1440+t.end_minute,quantity:r.required!}:null});
    const workIds=items.flatMap(r=>source(r).map(w=>w.id));
    const zones=new Set(items.flatMap(r=>source(r).map(w=>w.schedule?.timezone??'')));
    if(spans.some(s=>!s||!Number.isFinite(s.start)||!Number.isFinite(s.end)||s.end<=s.start)||new Set(workIds).size!==workIds.length||zones.size>1)review=true;
    else{const edges=spans.flatMap(s=>[{time:s!.start,delta:s!.quantity},{time:s!.end,delta:-s!.quantity}]).sort((a,b)=>a.time-b.time||a.delta-b.delta);let active=0;required=0;for(const e of edges){active+=e.delta;required=Math.max(required,active)}}
   }else review=true;
  }
  const reported=items.some(r=>known(r.reported_available));
  const values=items.map(r=>known(r.reported_available)?r.reported_available:r.available);
  const availableReview=items.length>1&&items[0].kind!=='consumable'&&reported;
  const available=!availableReview&&values.every(known)?values.reduce((a,b)=>a+b,0):null;
  return {id:items[0].id,title:items[0].title,unit:items[0].unit,items,source,required,review,available,availableReview,reported,gap:!review&&known(required)&&known(available)?Math.max(required-available,0):null};
 });
}
