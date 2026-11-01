import {useEffect,useState} from 'react';
import {useApp} from '../../app/provider';
/** Current-account UI projection; approval and accepted work remain service-controlled. */
export function useEventRelationship(eventId:string){
 const {service,identity}=useApp(),accountId=identity?.accountId??'';
 const [result,setResult]=useState<{eventId:string;accountId:string;accepted:boolean;requested:boolean;error:string}|null>(null),[retry,setRetry]=useState(0);
 useEffect(()=>{let live=true,version=0;setResult(null);const refresh=()=>{if(!service)return;const ticket=++version;void service.myEvents().then(events=>{if(!live||ticket!==version)return;const event=events.find(e=>e.event.id===eventId);setResult({eventId,accountId,accepted:!!event?.accepted_assignments.length,requested:!!event?.applications.some(a=>['submitted','pending_review','approved'].includes(a.status)),error:''});}).catch(()=>{if(live&&ticket===version)setResult({eventId,accountId,accepted:false,requested:false,error:'Unable to check your event participation. Retry before joining or supporting.'})});};refresh();window.addEventListener('aroundyou-participation-change',refresh);return()=>{live=false;window.removeEventListener('aroundyou-participation-change',refresh)}},[service,eventId,accountId,retry]);
 const current=result?.eventId===eventId&&result.accountId===accountId?result:null;
 return {accepted:current?.accepted??false,requested:current?.requested??false,loading:!current,error:current?.error??'',retry:()=>setRetry(n=>n+1)};
}
