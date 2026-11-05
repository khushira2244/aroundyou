import {afterEach,it,expect,vi} from 'vitest';
import {HttpAdapter} from '../src/services/http-adapter';
const response=(data:unknown,version=3)=>new Response(JSON.stringify({data,meta:{version}}),{status:200,headers:{'Content-Type':'application/json'}});
afterEach(()=>vi.unstubAllGlobals());
it('keeps report submission, original evidence versions and human verification separate',async()=>{
 const calls:{path:string;body:Record<string,unknown>}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{const path=new URL(url).pathname;calls.push({path,body:init.body?JSON.parse(String(init.body)):{}});if(path.endsWith('/execution'))return response({reports:[{id:'r',revision:4,work_ids:['w'],evidence_ids:['asset']}],evidence:[{id:'asset',revision:2}],work:[]});return response({saved:true},4)}));
 const s=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=> 'e'});
 await s.executionCommand('submitExecutionReport',{eventId:'e',reportId:'r',reportRevision:4});expect(calls.at(-1)?.path).toBe('/v1/events/e/reports/r/submit');expect(calls.some(x=>x.path.endsWith('/complete'))).toBe(false);
 await s.executionCommand('reviewExecutionReport',{eventId:'e',reportId:'r',decision:'verify',note:'Inspected original',verifiedPercent:35});expect(calls.at(-1)?.body).toMatchObject({report_revision:4,decision:'accept',verified_percent:35,evidence_versions:{asset:2}});
});
it('transmits selected file bytes rather than browser-local references',async()=>{
 const requests:{path:string;method:string;body:unknown}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{const path=new URL(url).pathname;requests.push({path,method:init.method??'GET',body:init.body});if(path.endsWith('/execution'))return response({reports:[{id:'r',revision:1}],evidence:[]});if(path.endsWith('/uploads'))return response({asset:{id:'server-asset'}},4);return response({asset:{id:'server-asset',status:'pending_inspection'}},5)}));
 const s=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=> 'e'}),file=new File(['original pdf'],'notes.pdf',{type:'application/pdf'});
 await s.executionCommand('attachExecutionEvidence',{eventId:'e',reportId:'r',file});expect(requests.at(-1)?.method).toBe('PUT');expect(requests.at(-1)?.body).toBe(file);expect(requests.at(-1)?.path).toBe('/v1/events/e/evidence/server-asset/content');
});
it('persists communications without claiming external notification or enabling Group 5',async()=>{
 const bodies:Record<string,unknown>[]=[];vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{if(init.body)bodies.push(JSON.parse(String(init.body)));if(init.method==='GET'&&url.endsWith('/coordination'))return response({items:[{id:'follow-up',revision:2}]});return response({saved:true})}));
 const s=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=> 'e'});
 await s.organizerCommand('saveOrganizerUpdate',{eventId:'e',title:'Briefing','body':'Read instructions',audience:'participants',status:'published'});expect(bodies.at(-1)).toMatchObject({kind:'announcement',audience:'participants',status:'published'});
 await s.organizerCommand('approveMeetingAction',{eventId:'e',actionId:'follow-up'});expect(bodies.at(-1)?.action).toBe('approve_action');
 await expect(s.executionCommand('activatePlanRevision',{eventId:'e'})).rejects.toThrow('not connected');
});
it('omits empty manual resources for older runtimes and sends entered resources without dropping them',async()=>{
 const bodies:Record<string,unknown>[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{
  if(url.endsWith('/execution'))return response({reports:[],evidence:[],work:[]});
  if(init.body)bodies.push(JSON.parse(String(init.body)));
  return response({report:{id:'report',revision:1}},4);
 }));
 const s=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=> 'e'});
 await s.executionCommand('saveExecutionReport',{eventId:'e',workId:'w',body:'Collected litter',resourceUsage:[],manualResourceUsage:[],measurements:[]});
 expect(bodies.at(-1)).not.toHaveProperty('manual_resource_usage');
 await s.executionCommand('saveExecutionReport',{eventId:'e',workId:'w',body:'Collected litter',resourceUsage:[],manualResourceUsage:[{name:'Gloves',quantity:12}],measurements:[]});
 expect(bodies.at(-1)?.manual_resource_usage).toEqual([{name:'Gloves',quantity:12}]);
});
