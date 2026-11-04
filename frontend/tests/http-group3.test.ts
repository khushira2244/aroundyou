import {afterEach,it,expect,vi} from 'vitest';
import {HttpAdapter} from '../src/services/http-adapter';
const response=(data:unknown,version=1,status=200)=>new Response(JSON.stringify(status<400?{data,meta:{version}}:{error:{code:'not_found',message:'Inaccessible'}}),{status,headers:{'Content-Type':'application/json'}});
afterEach(()=>vi.unstubAllGlobals());
it('uses the real personal application and separate consent contracts, not organizer approval as acceptance',async()=>{
 const requests:{path:string;body:Record<string,unknown>;headers:Record<string,string>}[]=[];let version=1;
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{const path=new URL(url).pathname;requests.push({path,body:init.body?JSON.parse(String(init.body)):{},headers:init.headers as Record<string,string>});if(init.method==='GET'&&path.endsWith('/participation/me'))return response({event:{id:'e'},account:{id:'person'},application:null,assignments:[]},version);return response({saved:true},++version)}));
 const s=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 'bearer',eventId:()=> 'e'});await s.participationState('e');
 await s.participantCommand('saveApplicationDraft',{eventId:'e',roleIds:['r1','r2'],intervals:[],answers:{skills:'Original statement'}});
 await s.participantCommand('submitApplication',{eventId:'e',applicationId:'a',acknowledged:true});
 expect(requests.at(-1)?.path).toBe('/v1/events/e/applications/a/submit');expect(requests.some(r=>r.path.endsWith('/accept'))).toBe(false);
 await s.participantCommand('acceptAssignment',{eventId:'e',assignmentId:'assignment',termsKey:'digest'});
 expect(requests.at(-1)?.body).toEqual({terms_key:'digest',confirmed:true});expect(requests.at(-1)?.headers.Authorization).toBe('Bearer bearer');expect(requests.at(-1)?.headers['Idempotency-Key']).toBeTruthy();
});
it('maps server work candidates and exact reviewed application revision before issuing an offer',async()=>{
 const calls:{path:string;body:Record<string,unknown>}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{const path=new URL(url).pathname;calls.push({path,body:init.body?JSON.parse(String(init.body)):{}});if(path.endsWith('/organizer/participants'))return response({event:{id:'e'},plan_id:'plan-current',applications:[{id:'a',account_id:'p',revision:7}],templates:[{id:'candidate',account_id:'p',role_requirement_id:'role',work_ids:['work'],schedule:{start_day:1,end_day:1,start_minute:540,end_minute:660,timezone:'Asia/Kolkata'}}]});return response({saved:true},2)}));
 const s=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=> 'e'});await s.organizerParticipants('e');
 await s.participantCommand('reviewApplication',{eventId:'e',applicationId:'a',approvedRoleIds:['role']});expect(calls.at(-1)?.body.reviewed_revision).toBe(7);
 await s.participantCommand('checkAssignment',{eventId:'e',applicationId:'a',templateId:'candidate'});expect(calls.at(-1)?.path).toContain('/assignment-checks');
 await s.participantCommand('offerAssignment',{eventId:'e',applicationId:'a',templateId:'candidate'});expect(calls.at(-1)?.body).toMatchObject({expected_plan_id:'plan-current',role_id:'role',work_ids:['work']});
});
it('keeps sponsor membership/version and exact fulfillment linkage in HTTP commands',async()=>{
 const calls:{path:string;body:Record<string,unknown>}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{const path=new URL(url).pathname;calls.push({path,body:init.body?JSON.parse(String(init.body)):{}});if(path.endsWith('/me/sponsor-portal'))return response({organization:{id:'org',version:3},offers:[{id:'o',event_id:'e'}]});if(path.endsWith('/organizer/sponsor-offers'))return response({event_id:'e',offers:[{id:'o',resource_requirement_id:'r',unit:'books'}],fulfillments:[{id:'f',offer_id:'o',quantity:5,verified:false}]});return response({saved:true},4)}));
 const s=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=> 'e'});await s.sponsorPortal();await s.sponsorCommand('saveOrganizationDraft',{profile:{name:'Books association'},step:2});expect(calls.at(-1)?.body.expected_version).toBe(3);
 await s.sponsorCommand('saveSponsorOffer',{eventId:'e',resourceId:'r',supportType:'materials',description:'Books',quantity:5,unit:'books',submit:true});expect(calls.at(-1)?.path).toBe('/v1/organizations/org/offers');
 await s.sponsorCommand('verifySponsorOfferReceipt',{eventId:'e',offerId:'o',quantity:5,reference:'delivery-note'});expect(calls.at(-1)?.body.fulfillment_id).toBe('f');
});

it('saves organizer revision requests and verifies the exact selected delivery report',async()=>{
 const calls:{path:string;body:Record<string,unknown>}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{const path=new URL(url).pathname;calls.push({path,body:init.body?JSON.parse(String(init.body)):{}});if(path.endsWith('/organizer/sponsor-offers'))return response({offers:[{id:'o',resource_requirement_id:'r',unit:'books'}],fulfillments:[{id:'f1',offer_id:'o',quantity:4,verified:false},{id:'f2',offer_id:'o',quantity:4,verified:false}]});return response({saved:true},2)}));
 const s=new HttpAdapter({baseUrl:'http://localhost:8000',token:()=> 't',eventId:()=> 'e'});
 await s.organizerCommand('requestSponsorRevision',{eventId:'e',offerId:'o',body:'Clarify delivery'});
 expect(calls.at(-1)).toEqual({path:'/v1/events/e/sponsor-offers/o/revision-requests',body:{body:'Clarify delivery'}});
 await s.sponsorCommand('verifySponsorOfferReceipt',{eventId:'e',offerId:'o',fulfillmentId:'f2',quantity:4,reference:'receipt'});
 expect(calls.at(-1)?.body.fulfillment_id).toBe('f2');expect(calls.at(-1)?.body.unit).toBe('books');
});
