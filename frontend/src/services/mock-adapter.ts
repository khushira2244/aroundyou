import {buildTenParticipantScenario} from '../../../demo/src/ten-participants.mjs';
import {buildRecoveryReplay} from '../../../demo/src/recovery-replay.mjs';
import type {ExecutionState,ExecutionOperation} from './execution-contracts';
import type {OrganizerDashboard,OrganizerOperation} from './organizer-contracts';
import type {ParticipationState,JoinEvent,MyEvent,OrganizerParticipants,ParticipantOperation} from './participant-contracts';
import type {SponsorPortal,SponsorOperation,OrganizerSponsorState} from './sponsor-contracts';
import type {SetupState,CanonicalProfile,PublicationOperation} from './publication-contracts';
import type {PlanningState,PlanningOperation,GovernanceState} from './planning-contracts';
import {DemoService,loadBrowserFixture,ORGANIZER} from '@demo';
import type {AroundYouService,CreationForm,CreationState,DemoState,DiscoveryEvent,Identity,IntentSource,Interpretation,Result,UnderstandingProposal} from './contracts';
const KEY='aroundyou.prompt1.creation.v1',SHARED='aroundyou.shared-demo.v1';
export class ServiceError extends Error {constructor(public status:string,message:string){super(message)}}
export class MockAdapter implements AroundYouService {
  private setupOpening:Promise<SetupState>|null=null;
  private opening:Promise<PlanningState>|null=null;
  private discovery:DemoService;private draft:DemoService|null=null;
  constructor(private seed:DemoState,private storage:Storage|null=typeof localStorage==='undefined'?null:localStorage){
    try{this.discovery=new DemoService(JSON.parse(this.storage?.getItem(SHARED)??'null')??seed)}catch{this.discovery=new DemoService(seed)}
    try {const saved=this.storage?.getItem(KEY);if(saved){const state=JSON.parse(saved) as DemoState;this.draft=new DemoService(state);}}
    catch{this.storage?.removeItem(KEY);}
  }
  private async run<T>(service:DemoService,op:string,input:Record<string,unknown>={}):Promise<T>{
    const r:Result<T>=await service.request<T>(op,input,{expectedRevision:service.revision});
    if(r.status!=='success'&&r.status!=='pending_approval')throw new ServiceError(r.status,r.error?.message??'The request could not be completed.');
    if(r.data===undefined)throw new ServiceError('error','Missing service response');
    if(service===this.draft)this.storage?.setItem(KEY,JSON.stringify(service.snapshot()));else if(service===this.discovery)this.storage?.setItem(SHARED,JSON.stringify(service.snapshot()));
    return r.data;
  }
  private current(){if(!this.draft)throw new ServiceError('not_found','Start an event draft first.');return this.draft;}
  async discover(category?:string){return this.run<DiscoveryEvent[]>(this.draft?.snapshot().runtime.publication==='published'?this.draft:this.discovery,'discoverEvents',{category});}
  async profile(id:string){return this.canonicalProfile(id);}
  async startCreation(){if(!this.draft){if(this.discovery.accountId!==ORGANIZER)throw new ServiceError('permission_denied','Choose the organizer personal demo to create an event.');this.draft=new DemoService(this.discovery.snapshot()).forkFlashback();}return this.creation();}
  async creation(){return this.run<CreationState>(this.current(),'readCreationState');}
  async saveDraft(step:number,form:CreationForm){
    const location={label:form.format==='online'?'Online event':`${form.venue}, ${form.city}, ${form.state}, ${form.country}`,confidence:form.format==='online'?'not_applicable':form.coordinates?'district_direction_point':'organizer_entered_unverified',coordinates:form.format==='online'?null:form.coordinates,source_id:form.format==='online'?null:form.locationSource,precise_meeting_point:null};
    await this.run(this.current(),'saveCreationDraft',{step,fields:{title:form.title,category:form.category,purpose:form.purpose,goal:form.goal,format:form.format,location,schedule:{anchor_date:form.startDate||null,end_date:form.endDate||null,start_time:form.startTime,end_time:form.endTime,timezone:form.timezone,relative_days:[1,2,3],status:form.startDate?'organizer_selected_demo_date':'unanchored_demo_relative'},context_id:'context-canary-001',creation_details:form}});
    return this.creation();
  }
  async saveIntent(text:string,source:IntentSource){await this.run(this.current(),'saveExecutionIntent',{text,source});return this.creation();}
  async sampleTranscript(){return (await this.run<{text:string}>(this.current(),'loadSampleTranscript')).text;}
  async suggestUnderstanding(message=''){return (await this.run<{proposal:UnderstandingProposal}>(this.current(),'suggestContextClarifications',{message})).proposal;}
  async reviewUnderstanding(proposalId:string,decision:'accept'|'reject',corrected?:Interpretation){await this.run(this.current(),'reviewContextInterpretation',{proposalId,decision,correctedInterpretation:corrected});return this.creation();}
  async createEvent(){await this.run(this.current(),'createUnpublishedEvent');return this.creation();}
  async openPlanning():Promise<PlanningState>{
    if(this.opening)return this.opening;
    this.opening=(async()=>{if(!this.current().snapshot().runtime.planning_progress)await this.run(this.current(),'beginPlanning');return this.readPlanning()})();
    try{return await this.opening}finally{this.opening=null}
  }
  async readPlanning(){return this.run<PlanningState>(this.current(),'readPlanningState');}
  async governanceState(){return this.run<GovernanceState>(this.current(),'readGovernanceState');}
  async planningCommand<T=unknown>(operation:PlanningOperation,input:Record<string,unknown>={}){return this.run<T>(this.current(),operation,input);}
  async openSetup():Promise<SetupState>{if(this.setupOpening)return this.setupOpening;this.setupOpening=(async()=>{if(!this.current().snapshot().runtime.event_setup)await this.run(this.current(),'beginSetup');return this.readSetup()})();try{return await this.setupOpening}finally{this.setupOpening=null}}
  async readSetup(){return this.run<SetupState>(this.current(),'readSetupState');}
  async publicationCommand<T=unknown>(operation:PublicationOperation,input:Record<string,unknown>={}){return this.run<T>(this.current(),operation,input);}
  async canonicalProfile(id:string,preview=false){const useDraft=id==='event-canary-hill-001'&&this.draft&&(preview||this.draft.snapshot().runtime.publication==='published');return this.run<CanonicalProfile>(useDraft?this.current():this.discovery,'readCanonicalProfile',{eventId:id});}
  async organizerDashboard(eventId:string){return this.run<OrganizerDashboard>(this.shared(),'readOrganizerDashboard',{eventId})}
  async organizerCommand<T=unknown>(op:OrganizerOperation,input:Record<string,unknown>={}){return this.run<T>(this.shared(),op,input)}
  async executionState(eventId:string){return this.run<ExecutionState>(this.shared(),'readExecutionState',{eventId})}
  demoAccounts():Identity[]{return Object.values((this.shared().snapshot() as DemoState).tables.accounts).filter(a=>a.kind==='personal'&&a.id!=='account-sponsor-rep-001').map(a=>({accountId:String(a.id),label:String(a.label),kind:'personal' as const}))}
  async executionCommand<T=unknown>(op:ExecutionOperation,input:Record<string,unknown>={}){if(op==='prepareTenParticipantScenario'||op==='restoreTenParticipantSession'){if(this.shared().accountId!==ORGANIZER)throw new Error('Organizer authority required for scenario setup.');const key='aroundyou.ten-participants.backup';if(op==='restoreTenParticipantSession'){const backup=JSON.parse(this.storage?.getItem(key)??'null');if(!backup)throw new Error('No preserved session available.');this.discovery=new DemoService(backup.discovery);this.draft=backup.draft?new DemoService(backup.draft):null;this.storage?.setItem(SHARED,JSON.stringify(backup.discovery));if(backup.draft)this.storage?.setItem(KEY,JSON.stringify(backup.draft));else this.storage?.removeItem(KEY);this.storage?.removeItem(key);return {restored:true} as T}const scenario=await buildTenParticipantScenario(this.seed);if(!this.storage?.getItem(key))this.storage?.setItem(key,JSON.stringify({discovery:this.discovery.snapshot(),draft:this.draft?.snapshot()??null}));this.discovery=new DemoService(scenario);this.draft=new DemoService(scenario);this.draft.switchDemoAccount(ORGANIZER);this.storage?.setItem(SHARED,JSON.stringify(scenario));this.storage?.setItem(KEY,JSON.stringify(scenario));return {prepared:true} as T}if(op==='prepareRecoveryReplay'){if(this.shared().accountId!==ORGANIZER)throw new Error('Organizer authority required for replay setup.');const backup={state:this.shared().snapshot(),wasDraft:!!this.draft};if(!this.storage?.getItem('aroundyou.recovery.backup'))this.storage?.setItem('aroundyou.recovery.backup',JSON.stringify(backup));const replay=await buildRecoveryReplay(this.seed);this.draft=new DemoService(replay);this.draft.switchDemoAccount(ORGANIZER);this.storage?.setItem(KEY,JSON.stringify(replay));return {prepared:true} as T}if(op==='restoreRecoverySession'){if(this.shared().accountId!==ORGANIZER)throw new Error('Organizer authority required to restore the replay.');const backup=JSON.parse(this.storage?.getItem('aroundyou.recovery.backup')??'null');if(!backup)throw new Error('No preserved pre-replay session available.');if(backup.wasDraft){this.draft=new DemoService(backup.state);this.storage?.setItem(KEY,JSON.stringify(backup.state))}else{this.draft=null;this.discovery=new DemoService(backup.state);this.storage?.removeItem(KEY);this.storage?.setItem(SHARED,JSON.stringify(backup.state))}this.storage?.removeItem('aroundyou.recovery.backup');return {restored:true} as T}return this.run<T>(this.shared(),op,input)}
  private shared(){return this.draft??this.discovery}
  async sponsorPortal(){return this.run<SponsorPortal>(this.shared(),'readSponsorPortal')}
  async sponsorCommand<T=unknown>(operation:SponsorOperation,input:Record<string,unknown>={}){return this.run<T>(this.shared(),operation,input)}
  async organizerSponsorOffers(eventId:string){return this.run<OrganizerSponsorState>(this.shared(),'readOrganizerSponsorOffers',{eventId})}
  async joinEvents(){return this.run<JoinEvent[]>(this.shared(),'readJoinEvents')}
  async participationState(eventId:string,applicationId?:string){return this.run<ParticipationState>(this.shared(),'readParticipationState',{eventId,applicationId})}
  async myEvents(){return this.run<MyEvent[]>(this.shared(),'readMyEvents')}
  async organizerParticipants(eventId:string){return this.run<OrganizerParticipants>(this.shared(),'readOrganizerParticipants',{eventId})}
  async participantCommand<T=unknown>(op:ParticipantOperation,input:Record<string,unknown>={}){return this.run<T>(this.shared(),op,{...input,frontend:true})}
  setIdentity(identity:Identity){const inDiscovery=!!this.discovery.snapshot().tables.accounts[identity.accountId],inDraft=!!this.draft?.snapshot().tables.accounts[identity.accountId];if(!inDiscovery&&!inDraft)throw new Error('Demo account is not loaded in this session.');if(inDiscovery)this.discovery.switchDemoAccount(identity.accountId);if(inDraft)this.draft!.switchDemoAccount(identity.accountId);}
  reset(){this.storage?.removeItem(KEY);this.storage?.removeItem(SHARED);this.discovery=new DemoService(this.seed);this.draft=null;}
}
export async function createMockAdapter(){return new MockAdapter(await loadBrowserFixture('/fixtures'));}
