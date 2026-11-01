import {afterEach,expect,it,vi} from 'vitest';
import {HttpAdapter} from '../src/services/http-adapter';
import {DEFAULT_FORM} from '../src/features/event-creation/model';
const response=(data:unknown,version?:number)=>new Response(JSON.stringify({data,meta:version===undefined?{}:{version}}),{status:200,headers:{'Content-Type':'application/json'}});
afterEach(()=>vi.unstubAllGlobals());
it('uses bearer identity and event-scoped server draft persistence, never fixture identity',async()=>{
 const requests:{path:string;init:RequestInit}[]=[];let version=1;let title='';
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{const path=new URL(url).pathname;requests.push({path,init});if(path.endsWith('/me'))return response({user:{id:'real-user',display_name:'Organizer'}});if(path.endsWith('/draft')){title=JSON.parse(init.body as string).form.title;version++;}return response({event:{id:'server-event',title},context:{original_text:''},runtime:{revision:version,lifecycle:'draft',draft:{creation_details:{title}},wizard_step:1}},version)}));
 const service=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 'signed-token',storage:sessionStorage,eventId:()=>null});
 const identity=await service.initialize();expect(identity.accountId).toBe('real-user');expect(service.demoAccounts()).toEqual([]);
 const created=await service.startCreation();expect(created.event.id).toBe('server-event');await service.saveDraft(1,{...DEFAULT_FORM,title:'Reading club'});
 expect(requests.at(-1)?.path).toBe('/v1/events/server-event/draft');expect((requests.at(-1)?.init.headers as Record<string,string>)['If-Match']).toBe('1');expect((requests.at(-1)?.init.headers as Record<string,string>).Authorization).toBe('Bearer signed-token');
 expect(()=>service.setIdentity({accountId:'fixture-user',label:'Fake',kind:'personal'})).toThrow();
 await service.executionState('server-event');expect(requests.at(-1)?.path).toBe('/v1/events/server-event/execution');
 service.selectEvent('server-event');
 const reloaded=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 'signed-token',storage:sessionStorage,eventId:()=>null});await reloaded.initialize();expect((await reloaded.creation()).event.title).toBe('Reading club');
});
it('binds calls to route event and never falls back to demo on an HTTP failure',async()=>{
 let id='event-a';const paths:string[]=[];vi.stubGlobal('fetch',vi.fn(async(url:string)=>{paths.push(url);return response({version:4},4)}));
 const service=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=>id});await service.readSetup();id='event-b';
 // Use setup read to avoid fake PlanningState projection in this transport-only test.
 await service.readSetup();expect(paths.at(-1)).toContain('/events/event-b/setup');
 vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({error:{code:'stale_version',message:'Reload exact version'}}),{status:409})));
 await expect(service.readSetup()).rejects.toMatchObject({status:'stale_version'});
});
it('does not submit fixture transcripts or request without a token',async()=>{
 const fetchMock=vi.fn();vi.stubGlobal('fetch',fetchMock);
 const service=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=>null});await expect(service.initialize()).rejects.toMatchObject({status:'unauthenticated'});expect(fetchMock).not.toHaveBeenCalled();
 await expect(service.saveIntent('canned','reviewed_demo_transcript')).rejects.toMatchObject({status:'invalid_source'});await expect(service.sampleTranscript()).rejects.toThrow(/not connected/);
});
it('serializes writes so the second request uses the committed event version',async()=>{
 let current=1;const headers:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async(_url:string,init:RequestInit)=>{if(init.method==='GET')return response({version:current},current);headers.push((init.headers as Record<string,string>)['If-Match']);await new Promise(r=>setTimeout(r,2));current++;return response({event:{id:'e'},runtime:{revision:current,lifecycle:'draft',draft:{}}},current)}));
 const service=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=> 'e'});
 await Promise.all([service.saveDraft(1,DEFAULT_FORM),service.saveDraft(2,DEFAULT_FORM)]);expect(headers).toEqual(['1','2']);
});

it('persists structured clarifications, manual confirmation and governance review/ticket edits through HTTP',async()=>{
 const requests:{path:string;method:string;body:Record<string,unknown>}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{const path=new URL(url).pathname;requests.push({path,method:String(init.method),body:init.body?JSON.parse(String(init.body)):{}});return response(init.method==='GET'?{version:2}:{event:{id:'e'},context:{version:3},runtime:{revision:3}},3)}));
 const service=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=> 'e'});
 await service.clarifyContext(2,[{question:'Which venue?',answer:'Library'}]);await service.confirmContextManually(3,{reported_facts:['Library'],scope:[],exclusions:[],instructions:[],constraints:[],unknowns:[],clarifications:[]});
 await service.planningCommand('reviewGovernanceAdvisory',{proposalId:'p',digest:'a'.repeat(64),decision:'reject'});await service.planningCommand('updateGovernanceTicket',{ticketId:'t',status:'closed',note:'Internal review done'});
 expect(requests.find(r=>r.path.endsWith('/context-clarifications'))?.body).toEqual({context_version:2,answers:[{question:'Which venue?',answer:'Library'}]});
 expect(requests.at(-1)).toMatchObject({path:'/v1/events/e/governance/tickets/t',method:'PATCH',body:{status:'closed'}});
 expect(requests.some(r=>r.path.endsWith('/governance/proposals/p/review'))).toBe(true);
});
