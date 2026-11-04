// Real HTTP adapter smoke check. Credentials read from ignored local runtime storage.
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {build} from 'esbuild';
const out=resolve('../backend/.tmp/http-adapter-check.mjs');
await build({entryPoints:['src/services/http-adapter.ts'],bundle:true,platform:'node',format:'esm',outfile:out,logLevel:'silent'});
const {HttpAdapter}=await import(pathToFileURL(out));
const session=JSON.parse(await readFile('../backend/.tmp/development-session.json','utf8'));
const values=new Map();const storage={getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};
const client=new HttpAdapter({baseUrl:session.base_url,token:()=>session.token,storage});
await client.initialize();const draft=await client.startCreation();
const form={title:'Connection check — community reading workshop',category:'Education',purpose:'Verify the AroundYou local database connection',goal:'Technical persistence check only; no actual event or participant commitments.',format:'in_person',startDate:'2026-11-07',endDate:'2026-11-07',startTime:'09:00',endTime:'11:00',timezone:'Asia/Kolkata',venue:'Venue unconfirmed',area:'Hazaribagh',city:'Hazaribagh',state:'Jharkhand',country:'India',reach:'Local area',coordinates:null,locationSource:null,workScope:'Check event creation and persistence. No community work is scheduled by this verification.',executionIntent:'This is a local integration connection check, not an approved real-world event.',intentSource:'written',expectedAttendees:'',expectedVolunteers:'',targetGroups:['Local community'],knownResources:'None verified',constraints:'Do not treat this technical check as an actual community commitment.',outcomes:'An event record that survives a new HTTP read',theme:'Standard',onlineDetails:'',confirmAccuracy:true,confirmPlanning:true,confirmContinue:true};
await client.saveDraft(4,form);const created=await client.createEvent();
const independent=new HttpAdapter({baseUrl:session.base_url,token:()=>session.token,storage,eventId:()=>created.event.id});await independent.initialize();const read=await independent.creation();
if(read.event.id!==created.event.id||read.event.title!==form.title||read.runtime.lifecycle!=='created_unpublished')throw new Error('Persistence check failed');
console.log(JSON.stringify({event_id:created.event.id,title:read.event.title,lifecycle:read.runtime.lifecycle,http_adapter_verified:true,fresh_client_read_verified:true,ai_calls:0}));
