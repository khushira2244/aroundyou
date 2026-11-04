import {afterEach,it,expect,vi} from 'vitest';
import {HttpAdapter} from '../src/services/http-adapter';
afterEach(()=>vi.unstubAllGlobals());
it('uses cookie sessions for private binary evidence and explicit scoped inference',async()=>{
 const calls:{path:string;init:RequestInit}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{const path=new URL(url).pathname;calls.push({path,init});const data=path.endsWith('/execution')?{reports:[{id:'r',revision:2}],evidence:[{id:'a',revision:3}]}:path.endsWith('/uploads')?{asset:{id:'a'}}:{status:'succeeded'};return new Response(JSON.stringify({data,meta:{version:4}}),{status:200})}));
 const service=new HttpAdapter({baseUrl:'http://localhost:8001',token:()=>null,eventId:()=> 'e'});
 await service.executionCommand('attachExecutionEvidence',{reportId:'r',file:new File(['audio'],'voice.wav',{type:'audio/wav'})});
 expect(calls.at(-1)?.init.credentials).toBe('include');expect(calls.at(-1)?.init.headers).not.toHaveProperty('Authorization');
 await service.executionCommand('readExecutionEvidence',{evidenceId:'a'});expect(calls.at(-1)?.init.credentials).toBe('include');
 await service.executionCommand('reviewReportTranscript',{evidenceId:'a',text:'Corrected participant text'});expect(JSON.parse(String(calls.at(-1)?.init.body))).toEqual({expected_revision:3,text:'Corrected participant text'});
 await service.executionCommand('analyzeReportImage',{evidenceId:'a',concept:'tables'});expect(calls.at(-1)?.path).toBe('/v1/events/e/media/a/segmentation-runs');expect(JSON.parse(String(calls.at(-1)?.init.body))).toEqual({concept:'tables'});
 expect(calls.filter(c=>c.path.endsWith('/segmentation-runs'))).toHaveLength(1);
});
