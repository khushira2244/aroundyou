import type {AroundYouService,CreationForm,CreationState,Identity,IntentSource,Interpretation,UnderstandingProposal} from './contracts';
import type {PlanningOperation,PlanningState,PlanningProposal,GovernanceState} from './planning-contracts';
import type {PublicationOperation,SetupState,CanonicalProfile} from './publication-contracts';
import type {ParticipantOperation,ParticipationState,MyEvent,OrganizerParticipants,JoinEvent} from './participant-contracts';
import type {ExecutionOperation,ExecutionState} from './execution-contracts';
import type {OrganizerOperation,OrganizerDashboard} from './organizer-contracts';
import type {SponsorOperation,SponsorPortal,OrganizerSponsorState} from './sponsor-contracts';

export class HttpServiceError extends Error {constructor(public status:string,message:string){super(message)}}
export interface HttpOptions {baseUrl:string;token:()=>string|null;eventId?:()=>string|null;storage?:Storage}
export class HttpAdapter implements AroundYouService {
 readonly mode='http' as const;
 async recoveryCommand<T=unknown>(op:string,input:Record<string,unknown>):Promise<T>{const id=String(input.eventId??this.current()),base='/events/'+id+'/recovery';
 if(op==='list')return this.read(base+'/alternatives',id);
 if(op==='offers')return this.read(base+'/offers/me',id);
 const path=op==='create'?'/alternatives':op==='confirm'?'/issues/'+input.issueId+'/confirm':op==='impact'?'/impact':op==='consent'?'/alternatives/'+input.recoveryId+'/assignments/'+input.assignmentId+'/consent':'/alternatives/'+input.recoveryId+'/'+op;
 const {eventId:_,issueId:__,recoveryId:___,assignmentId:____,...body}=input;
 return this.write(base+path,'POST',body,id);}

 async insightCommand<T=unknown>(op:string,input:Record<string,unknown>):Promise<T>{const id=String(input.eventId??this.current()),base='/events/'+id;
 if(op==='configuration')return this.read(base+'/insight-configuration',id);
 if(op==='response')return this.read(base+'/insight-responses/me',id);
 if(op==='configure')return this.write(base+'/insight-configuration','PUT',{expected_revision:input.expected_revision,public_aggregates:input.public_aggregates,questions:input.questions},id);
 if(op==='respond')return this.write(base+'/insight-responses/me','PUT',{configuration_revision:input.configuration_revision,answers:input.answers,consent:input.consent},id);
 if(op==='revoke')return this.write(base+'/insight-responses/me/consent','DELETE',{},id);
 return this.unsupported();}

 private participants=new Map<string,ParticipationState>();private organizerPeople=new Map<string,OrganizerParticipants>();private portal: SponsorPortal|null=null;
 private versions=new Map<string,number>();private planning=new Map<string,PlanningState>();private setup=new Map<string,SetupState>();
 private queue:Promise<unknown>=Promise.resolve();private draftId:string|null=null;private identity:Identity|null=null;
 constructor(private options:HttpOptions){}
 private unsupported():never {throw new HttpServiceError('unavailable','This workflow is not connected in the current backend. No demo data was substituted.');}
 async initialize(){const data=await this.read<{user:{id:string;display_name:string}}>('/me');this.identity={accountId:data.user.id,label:data.user.display_name,kind:'personal'};this.draftId=this.options.storage?.getItem('aroundyou.http.draft.'+data.user.id)??null;return this.identity;}
 private current(){const route=this.options.eventId?.()??(typeof window!=='undefined'?window.location.pathname.match(/^\/events\/([^/]+)/)?.[1]:null);const id=route??this.draftId;if(!id)throw new HttpServiceError('not_found','Start or select a backend event first.');return id;}
 private async transport<T>(path:string,method='GET',body?:unknown,eventId?:string):Promise<T>{
  const token=this.options.token();if(!token)throw new HttpServiceError('unauthenticated','A backend bearer token is required; demo identity is not authentication.');
  const headers:Record<string,string>={Authorization:`Bearer ${token}`};
  if(method!=='GET'){headers['Content-Type']='application/json';headers['Idempotency-Key']=crypto.randomUUID();if(eventId)headers['If-Match']=String(this.versions.get(eventId));}
  const response=await fetch(this.options.baseUrl.replace(/\/$/,'')+'/v1'+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body)});
  const result=await response.json();
  if(!response.ok)throw new HttpServiceError(result.error?.code??'error',result.error?.message??`HTTP ${response.status}`);
  if(eventId&&typeof result.meta?.version==='number')this.versions.set(eventId,result.meta.version);
  return result.data as T;
 }
 private read<T>(path:string,eventId?:string){return this.transport<T>(path,'GET',undefined,eventId)}
 private write<T>(path:string,method:string,body:unknown|(()=>unknown),eventId?:string):Promise<T>{
  const job=this.queue.then(async()=>{if(eventId&&!this.versions.has(eventId)){try{await this.read('/events/'+eventId,eventId)}catch(e){if(e instanceof HttpServiceError&&e.status==='not_found')await this.read('/events/'+eventId+'/participation/me',eventId);else throw e}}return this.transport<T>(path,method,typeof body==='function'?body():body,eventId)});
  this.queue=job.then(()=>undefined,()=>undefined);return job;
 }
 private async creationResult(p:Promise<CreationState>){const value=await p;this.draftId=value.event.id;this.versions.set(value.event.id,value.runtime.revision);if(this.identity)this.options.storage?.setItem('aroundyou.http.draft.'+this.identity.accountId,value.event.id);return value;}
 async startCreation(){if(this.draftId){const value=await this.read<CreationState>('/events/'+this.draftId+'/creation',this.draftId);if(value.runtime.lifecycle==='draft')return value;}return this.creationResult(this.write('/events/drafts','POST',{}));}
 creation(){const id=this.current();return this.creationResult(this.read('/events/'+id+'/creation',id))}
 saveDraft(step:number,form:CreationForm){const id=this.current();return this.creationResult(this.write('/events/'+id+'/draft','PATCH',{step,form},id))}
 saveIntent(text:string,source:IntentSource){if(source==='reviewed_demo_transcript')return Promise.reject(new HttpServiceError('invalid_source','Demo sample transcripts cannot become backend evidence.'));const id=this.current();return this.creationResult(this.write('/events/'+id+'/context-revisions','POST',{text,source},id))}
 sampleTranscript():Promise<string>{return Promise.reject(new HttpServiceError('unavailable','Live transcription is not connected. Enter original text or a reviewed transcript.'));}
 private adaptProposal(p:PlanningProposal):PlanningProposal{return {...p,status:p.status==='pending'?'proposed':p.status,kind:p.kind==='work'?'planning_work_chat':p.kind==='stages'?'planning_stage_chat':p.kind==='manual_plan'?(p.message.toLowerCase().includes('work')?'planning_work_edit':'planning_stage_edit'):p.kind}}
 private adaptPlanning(s:PlanningState){s.proposals=s.proposals.map(p=>this.adaptProposal(p));this.planning.set(s.event.id,s);return s;}
 async openPlanning(){const id=this.current();return this.adaptPlanning(await this.write<PlanningState>('/events/'+id+'/planning/draft','POST',{},id))}
 async readPlanning(){const id=this.current();return this.adaptPlanning(await this.read<PlanningState>('/events/'+id+'/planning',id))}
 async governanceState(){const id=this.current();return this.read<GovernanceState>('/events/'+id+'/governance',id)}
 private async requestAI(path:string,message='',scope:Record<string,unknown>={}){const id=this.current();const run=await this.write<{run_id:string}>(path,'POST',{message,...scope},id);for(let i=0;i<30;i++){const result=await this.read<{status:string;proposal:PlanningProposal&{interpretation?:Interpretation};error?:{code:string}}>('/ai-runs/'+run.run_id,id);if(result.status==='succeeded'&&result.proposal)return result.proposal;if(['failed','stale','cancelled'].includes(result.status))throw new HttpServiceError(result.error?.code??result.status,'AI run did not produce a current reviewable proposal.');await new Promise(resolve=>setTimeout(resolve,500));}throw new HttpServiceError('pending','AI request remains queued. Refresh later; no plan changes were applied.');}
 async clarifyContext(contextVersion:number,answers:{question:string;answer:string}[],proposalId?:string){const id=this.current();return this.creationResult(this.write('/events/'+id+'/context-clarifications','POST',{context_version:contextVersion,answers,proposal_id:proposalId},id))}
 async confirmContextManually(contextVersion:number,interpretation:Interpretation){const id=this.current();return this.creationResult(this.write('/events/'+id+'/context-interpretations','POST',{context_version:contextVersion,interpretation},id))}
 async suggestUnderstanding(message=''){return await this.requestAI('/events/'+this.current()+'/context-proposals',message) as unknown as UnderstandingProposal}
 async reviewUnderstanding(proposalId:string,decision:'accept'|'reject',corrected?:Interpretation){const id=this.current();const runProposal=await this.read<{proposal:{digest:string}}>('/events/'+id+'/context-proposals/'+proposalId,id);return this.creationResult(this.write('/events/'+id+'/context-proposals/'+proposalId+'/review','POST',{decision,reviewed_digest:runProposal.proposal.digest,corrected_interpretation:corrected},id))}
 createEvent(){const id=this.current();return this.creationResult(this.write('/events/'+id+'/confirm-creation','POST',()=>({expected_draft_version:this.versions.get(id),acknowledgements:{}}),id))}
 async planningCommand<T=unknown>(op:PlanningOperation,input:Record<string,unknown>={}):Promise<T>{
  const id=this.current(),base='/events/'+id,p=this.planning.get(id);
  const write=(path:string,body:unknown={},method='POST')=>this.write<T>(base+path,method,body,id);
  if(op==='addStage')return write('/planning/items/stages',input);
  if(op==='addWork')return write('/planning/items/work',input);
  if(op==='savePlanningDraft')return write('/planning/checkpoints',{expected_draft_version:p?.draft_version});
  if(op==='proposeStageEdit')return write('/planning/stage-edits',{stage_id:input.stageId,start_day:input.startDay,duration_days:input.durationDays});
  if(op==='proposeAutoArrange')return write('/planning/arrangements',{});
  if(['approvePlanningChat','approveStageEdit','approveWorkDesign','rejectPlanningProposal'].includes(op)){
   const proposal=p?.proposals.find(x=>x.id===input.proposalId);if(!proposal?.digest)throw new HttpServiceError('stale_proposal','Reload the exact proposal before review.');
   return write('/planning/proposals/'+input.proposalId+(op==='rejectPlanningProposal'?'/reject':'/apply'),{reviewed_digest:proposal.digest});
  }
  if(['confirmStagePlan','confirmWorkDesign','confirmActorRequirements'].includes(op))return write('/planning/'+(op==='confirmStagePlan'?'stage':op==='confirmWorkDesign'?'work':'actor')+'-confirmations',{expected_draft_version:p?.draft_version,expected_derived_from:op==='confirmActorRequirements'?p?.planning.derived_from:undefined});
  if(op==='deriveActorRequirements')return write('/planning/actor-derivations',{});
  if(op==='reviewActorRequirement')return write('/planning/actor-requirements/'+input.roleId,{headcount:input.headcount,capabilities:typeof input.capabilities==='string'?input.capabilities.split(',').map(x=>x.trim()).filter(Boolean):input.capabilities},'PATCH');
  if(op==='addActorRequirement')return write('/planning/actor-requirements',{stage_id:input.stageId,title:input.title});
  if(op==='reviseWorkDesign'){const raw=(input.patch??{}) as Record<string,unknown>;const names:Record<string,string>={durationHours:'duration_hours',startDay:'start_day',dependencyIds:'dependency_ids',resourceQuantities:'resource_quantities'};return write('/planning/work-edits',{work_id:input.workId,patch:Object.fromEntries(Object.entries(raw).map(([k,v])=>[names[k]??k,v]))});}
  if(op==='generateStageProposal'||op==='reviseStageProposal')return {proposal:await this.requestAI(base+'/planning/stage-proposals',String(input.message??''))} as T;
  if(op==='generateWorkConversation')return {proposal:await this.requestAI(base+'/planning/work-proposals',String(input.message??''))} as T;
  if(op==='generateGovernanceAdvisory')return {proposal:await this.requestAI(base+'/governance/assessments')} as T;
  if(op==='reviewGovernanceAdvisory')return write('/governance/proposals/'+input.proposalId+'/review',{decision:input.decision,reviewed_digest:input.digest});
  if(op==='updateGovernanceTicket')return write('/governance/tickets/'+input.ticketId,{status:input.status,note:input.note},'PATCH');
  if(op==='startGovernanceTicket')return write('/governance/tickets');
  if(op==='recordGovernanceDocument'||op==='updateGovernanceReminders'){
   const g=await this.governanceState();if(!g.ticket)throw new HttpServiceError('not_found','Start a governance ticket first.');
   return write('/governance/tickets/'+g.ticket.id+(op==='recordGovernanceDocument'?'/documents':'/reminders'),op==='recordGovernanceDocument'?{name:input.name,document_type:input.documentType,size:input.size,mime:input.mime}:{email_updates:input.email,remind_documents:input.remind},op==='recordGovernanceDocument'?'POST':'PATCH');
  }
  return this.unsupported();
 }
 async openSetup(){const id=this.current();const s=await this.write<SetupState>('/events/'+id+'/setup/draft','POST',{},id);this.setup.set(id,s);return s;}
 async readSetup(){const id=this.current();const s=await this.read<SetupState>('/events/'+id+'/setup',id);this.setup.set(id,s);return s;}
 async publicationCommand<T=unknown>(op:PublicationOperation,input:Record<string,unknown>={}):Promise<T>{
  const id=this.current(),base='/events/'+id,s=this.setup.get(id);const write=(path:string,body:unknown={},method='POST')=>this.write<T>(base+path,method,body,id);
  if(op==='saveSetupDraft')return write('/setup/checkpoints',{});
  if(op==='startDiscussion'||op==='replyDiscussion')return this.write('/events/'+id+'/coordination','POST',{kind:'discussion',title:input.title||'Reply',body:input.body,parent_id:input.discussionId,audience:'public',status:'published'},id);
  if(op==='saveSetupSection')return write('/setup/sections/'+input.section,{data:input.data},'PATCH');
  if(op==='saveParticipantConfiguration')return write('/setup/participant-configuration',input.configuration,'PUT');
  if(op==='addInitialInvite'){const {roleId,...rest}=input;return write('/setup/invitation-drafts',{...rest,role_id:roleId||null});}
  if(op==='removeInitialInvite')return write('/setup/invitation-drafts/'+input.inviteId,undefined,'DELETE');
  if(op==='addPartnerDraft')return write('/setup/partner-drafts',input);
  if(op==='savePublishPreferences')return write('/setup/publication-preferences',input,'PATCH');
  if(op==='finalizeEvent')return write('/finalizations',{confirm_review:input.confirmReview,expected_setup_version:s?.configuration.revision,expected_plan_id:s?.plan_id});
  if(op==='publishEvent')return write('/publications',{finalization_id:s?.finalization?.id});
  return this.unsupported();
 }
 async canonicalProfile(id:string,preview=false){return this.read<CanonicalProfile>('/events/'+id+'/profile'+(preview?'?preview=organizer':''),id)}
 profile(id:string){return this.canonicalProfile(id)}
 async discover(category?:string){return (await this.read<{items:Awaited<ReturnType<AroundYouService['discover']>>}>('/events'+(category?'?category='+encodeURIComponent(category):''))).items}
 async myEvents(){return (await this.read<{items:MyEvent[]}>('/me/events')).items}
 demoAccounts():Identity[]{return []}
 setIdentity(identity:Identity){if(this.identity&&identity.accountId!==this.identity.accountId)throw new HttpServiceError('permission_denied','Bearer identity cannot be switched to a demo account.');}
 selectEvent(eventId:string){this.draftId=eventId;if(this.identity)this.options.storage?.setItem('aroundyou.http.draft.'+this.identity.accountId,eventId);}
 reset(){this.draftId=null;if(this.identity)this.options.storage?.removeItem('aroundyou.http.draft.'+this.identity.accountId);}
 async executionState(id:string):Promise<ExecutionState>{return this.read('/events/'+id+'/execution',id)}
 async executionCommand<T=unknown>(op:ExecutionOperation,input:Record<string,unknown>={}):Promise<T>{
  const supported:ExecutionOperation[]=['readExecutionEvidence','inspectExecutionEvidence','startAssignedWork','grantExecutionReview','saveExecutionReport','attachExecutionEvidence','submitExecutionReport','beginExecutionReview','reviewExecutionReport','completeVerifiedWork','completeExecutionStage','submitWorkBlocker','reviewExecutionIssue','reconcileReportedUsage','issueReportedEquipment','returnReportedEquipment','publishVerifiedMeasurement'];if(!supported.includes(op))return this.unsupported();
  const id=String(input.eventId??this.current()),base='/events/'+id;
  if(op==='readExecutionEvidence'){
   const response=await fetch(this.options.baseUrl.replace(/\/$/,'')+'/v1'+base+'/evidence/'+input.evidenceId+'/content',{headers:{Authorization:'Bearer '+this.options.token()}});if(!response.ok)throw new HttpServiceError('unavailable','Private original evidence is unavailable');return await response.blob() as T;
  }
  const state=await this.executionState(id),r=state.reports.find(r=>r.id===input.reportId),post=(path:string,body:unknown={})=>this.write<T>(base+path,'POST',body,id);
  if(op==='startAssignedWork')return post('/execution/work/'+input.workId+'/start',{preconditions_confirmed:input.preconditionsConfirmed??false});
  if(op==='grantExecutionReview')return post('/execution/review-grants',{account_id:input.accountId,stage_id:input.stageId,confirm:input.confirm});
  if(op==='saveExecutionReport')return post('/reports/draft',{work_id:input.workId,report_id:input.reportId,report_revision:input.reportRevision,body:input.body,remaining_work:input.remainingWork,claim:input.claim,progress_percent:input.progressPercent,resource_usage:input.resourceUsage,measurements:input.measurements});
  if(op==='attachExecutionEvidence'){
   if(!r||!(input.file instanceof File))throw new HttpServiceError('validation_failed','Select the actual original file for backend upload');const file=input.file;
   const created=await this.write<{asset:{id:string}}> (base+'/evidence/uploads','POST',{report_id:r.id,report_revision:r.revision,kind:file.type.startsWith('application/')||file.type==='text/plain'?'document':file.type.split('/')[0],name:file.name,mime:file.type,size:file.size},id);
   return this.queueBinary<T>(base+'/evidence/'+created.asset.id+'/content',file,id);
  }
  if(op==='inspectExecutionEvidence'){const asset=state.evidence.find(a=>a.id===input.evidenceId);return post('/evidence/'+input.evidenceId+'/inspection',{expected_revision:asset?.revision,decision:input.decision,note:input.note});}
  if(op==='submitExecutionReport'||op==='beginExecutionReview')return post('/reports/'+input.reportId+'/'+(op==='submitExecutionReport'?'submit':'review-start'),{report_revision:input.reportRevision??r?.revision});
  if(op==='reviewExecutionReport')return post('/reports/'+input.reportId+'/review',{report_revision:r?.revision,decision:input.decision==='verify'?'accept':input.decision==='needs_correction'?'request_correction':input.decision,note:input.note,verified_percent:input.verifiedPercent,evidence_versions:Object.fromEntries(state.evidence.filter(e=>r?.evidence_ids.includes(e.id)).map(e=>[e.id,e.revision]))});
  if(op==='completeVerifiedWork'){if(!r||!input.confirm||!input.criteriaSatisfied)throw new HttpServiceError('validation_failed','Confirm the exact completion criteria');return post('/execution/work/'+r.work_ids[0]+'/complete',{reason:'Human confirmed reviewed report '+r.id+' and completion criteria'});}
  if(op==='completeExecutionStage')return post('/execution/stages/'+input.stageId+'/complete',{reason:input.reason??'Human confirmed all verified work in this stage'});
  if(op==='reviewExecutionIssue')return post('/issues/'+input.issueId+'/review',{expected_revision:state.blockers.find(x=>x.id===input.issueId)?.revision,state:input.state,condition_cleared:input.conditionCleared??false,note:input.note});
  if(op==='submitWorkBlocker')return post('/issues',{work_id:input.workId,description:input.description,severity:input.severity,occurred_at:input.occurredAt,effect:input.effect,evidence_ids:input.evidenceIds});
  if(op==='reconcileReportedUsage'||op==='issueReportedEquipment'||op==='returnReportedEquipment')return post('/resource-usage/'+(op==='reconcileReportedUsage'?'consumption':op==='issueReportedEquipment'?'checkouts':'returns'),{report_id:input.reportId,usage_id:input.usageId,reservation_id:input.reservationId,quantity:input.quantity,reference:input.clientReference,confirm:input.confirm});
  if(op==='publishVerifiedMeasurement')return post('/reports/'+input.reportId+'/measurements',{metric:input.metric,note:input.note,confirm:input.confirm});
  return this.unsupported();
 }
 private queueBinary<T>(path:string,file:File,eventId:string):Promise<T>{
  const job=this.queue.then(async()=>{const response=await fetch(this.options.baseUrl.replace(/\/$/,'')+'/v1'+path,{method:'PUT',headers:{Authorization:'Bearer '+this.options.token(),'If-Match':String(this.versions.get(eventId)),'Idempotency-Key':crypto.randomUUID(),'Content-Type':'application/octet-stream'},body:file});const result=await response.json();if(!response.ok)throw new HttpServiceError(result.error?.code??'error',result.error?.message??'Upload failed');if(typeof result.meta?.version==='number')this.versions.set(eventId,result.meta.version);return result.data as T});this.queue=job.then(()=>undefined,()=>undefined);return job;
 }
 async organizerDashboard(id:string):Promise<OrganizerDashboard>{return this.read('/events/'+id+'/organizer/dashboard',id)}
 async organizerCommand<T=unknown>(op:OrganizerOperation,input:Record<string,unknown>={}):Promise<T>{const id=String(input.eventId??this.current());const post=(body:unknown)=>this.write<T>('/events/'+id+'/coordination','POST',body,id);
 if(op==='saveOrganizerNote')return post({kind:'note',title:'Organizer note',body:input.body,audience:'internal',status:'published'});
 if(op==='saveOrganizerUpdate'){if(input.status==='scheduled_intent')return this.unsupported();return post({kind:'announcement',title:input.title,body:input.body,audience:input.audience,status:input.status});}
 if(op==='createOrganizerMeeting')return post({kind:'meeting',title:input.title,body:input.purpose,agenda:typeof input.agenda==='string'?input.agenda.split('\n').filter(Boolean):[],invited_account_ids:input.accountIds,schedule:input.schedule});
 if(op==='saveMeetingDecision')return post({kind:'action',title:input.title,parent_id:input.meetingId,status:'open'});
 if(op==='confirmMeeting'||op==='setMeetingRsvp'||op==='approveMeetingAction'){const items=await this.read<{items:{id:string;revision:number}[]}>('/events/'+id+'/coordination',id),row=items.items.find(x=>x.id===(input.meetingId??input.actionId));if(!row)throw new HttpServiceError('not_found','Coordination record unavailable');return this.write<T>('/events/'+id+'/coordination/'+row.id+'/actions','POST',{expected_revision:row.revision,action:op==='confirmMeeting'?'confirm':op==='setMeetingRsvp'?'rsvp':'approve_action',response:input.response==='declined'?'not_going':input.response,note:op==='approveMeetingAction'?'Human approved follow-up':''},id);}
 if(op==='saveResourceRequest'){const d=await this.organizerDashboard(id),r=d.resources.find(r=>r.id===input.resourceId);if(!r)throw new HttpServiceError('not_found','Resource not found');return this.write('/events/'+id+'/resource-requests','POST',{resource_id:r.id,work_id:r.work_ids[0],expected_plan_id:d.active_plan_id,quantity:input.quantity,unit:r.unit,reason:input.reason},id);}return this.unsupported();}
 async joinEvents():Promise<JoinEvent[]>{return (await this.read<{items:JoinEvent[]}>('/participation-opportunities')).items}
 async participationState(id:string,app?:string):Promise<ParticipationState>{const s=await this.read<ParticipationState>('/events/'+id+'/participation/me'+(app?'?application_id='+encodeURIComponent(app):''),id);this.participants.set(id,s);return s;}
 async organizerParticipants(id:string):Promise<OrganizerParticipants>{const s=await this.read<OrganizerParticipants>('/events/'+id+'/organizer/participants',id);this.organizerPeople.set(id,s);return s;}
 async participantCommand<T=unknown>(op:ParticipantOperation,input:Record<string,unknown>={}):Promise<T>{
  const id=String(input.eventId??this.current()),base='/events/'+id;
  if(op==='setMeetingRsvp')return this.organizerCommand<T>('setMeetingRsvp',input);
  if(op==='readMeeting'){const rows=await this.read<{items:{id:string;kind:string;parent_id?:string}[]}>(base+'/coordination',id);return {meeting:rows.items.find(x=>x.id===input.meetingId),actions:rows.items.filter(x=>x.kind==='action'&&x.parent_id===input.meetingId)} as T;}
  const write=(path:string,body:unknown={})=>this.write<T>(base+path,'POST',body,id);
  const appId=String(input.applicationId??this.participants.get(id)?.application?.id??'');
  if(op==='saveApplicationDraft')return write('/applications/draft',{application_id:input.applicationId,step:input.step,role_ids:input.roleIds,work_ids:input.workIds,intervals:input.intervals,answers:input.answers});
  if(op==='advanceApplication')return write('/applications/'+appId+'/advance',{step:input.step});
  if(op==='submitApplication')return write('/applications/'+appId+'/submit',{acknowledged:input.acknowledged});
  if(op==='withdrawApplication'||op==='queueApplicationReview'||op==='reopenParticipantReview')return write('/applications/'+appId+'/'+(op==='withdrawApplication'?'withdraw':op==='queueApplicationReview'?'begin-review':'reopen-review'));
  if(op==='reviewApplication'){const a=this.organizerPeople.get(id)?.applications.find(a=>a.id===appId);return write('/applications/'+appId+'/review',{approved_role_ids:input.approvedRoleIds,reviewed_revision:a?.revision,note:input.note??''});}
  if(op==='recordParticipantCapabilityReview')return write('/applications/'+appId+'/capability-reviews',{role_id:input.roleId,note:input.note,confirm:input.confirm});
  if(op==='requestParticipantClarification')return write('/applications/'+appId+'/clarifications',{question:input.question});
  if(op==='respondParticipantClarification')return write('/applications/'+appId+'/clarifications/'+input.clarificationId+'/answer',{answer:input.answer});
  if(op==='updateParticipantInformation')return write('/applications/'+appId+'/information-revisions',{answers:input.answers,intervals:input.intervals});
  if(['acceptAssignment','declineAssignment','withdrawAssignment'].includes(op))return write('/assignments/'+input.assignmentId+'/'+(op==='acceptAssignment'?'accept':op==='declineAssignment'?'decline':'withdraw'),op==='withdrawAssignment'?{}:{terms_key:input.termsKey,confirmed:true});
  if(op==='checkAssignment'||op==='offerAssignment'){
   const state=this.organizerPeople.get(id);const template=state?.templates.find(t=>t.id===input.templateId&&t.account_id===state.applications.find(a=>a.id===appId)?.account_id);if(!template)throw new HttpServiceError('stale_candidate','Reload published work choices before offering.');
   return write('/applications/'+appId+'/'+(op==='checkAssignment'?'assignment-checks':'assignment-offers'),{role_id:template.role_requirement_id,work_ids:template.work_ids,schedule:template.schedule,expected_plan_id:state?.plan_id});
  }
  if(op==='assessParticipantApplication')return {proposal:await this.requestAI(base+'/participation-assessments','', {application_id:appId})} as T;
  if(op==='reviewParticipationAdvisory')return write('/participation-proposals/'+input.proposalId+'/review',{decision:input.decision,reviewed_digest:input.digest});
  if(op==='readParticipantIntelligence')return this.organizerParticipants(id) as Promise<T>;
  if(op==='respondAlternativeRole')return write('/applications/'+appId+'/alternatives/'+input.requestId+'/response',{decision:input.decision==='accept'?'agree':'decline'});
  if(op==='requestAlternativeRole'||op==='offerRecommendedAssignment'){
   const s=this.organizerPeople.get(id),a=s?.applications.find(a=>a.id===appId),r=a?.intelligence?.assessment?.recommendations.find(r=>r.id===input.recommendationId);if(!r)throw new HttpServiceError('stale_proposal','Reload the reviewed recommendation.');
   if(op==='requestAlternativeRole')return write('/applications/'+appId+'/alternatives',{role_id:r.role_requirement_id,work_ids:r.work_ids,message:r.explanation});
   const work=s?.work.find(w=>w.id===input.workId);if(!work)throw new HttpServiceError('stale_work','Work not found');return write('/applications/'+appId+'/assignment-offers',{role_id:r.role_requirement_id,work_ids:[work.id],schedule:work.schedule,expected_plan_id:s?.plan_id});
  }
  return this.unsupported();
 }
 async sponsorPortal():Promise<SponsorPortal>{const p=await this.read<SponsorPortal>('/me/sponsor-portal');this.portal=p;return p;}
 async sponsorCommand<T=unknown>(op:SponsorOperation,input:Record<string,unknown>={}):Promise<T>{
  const org=this.portal?.organization.id;
  if(op==='saveOrganizationDraft'){const profile=input.profile??input.form??input;const p=profile as Record<string,unknown>;return this.write(org?'/organizations/'+org+'/registration':'/organizations/draft',org?'PATCH':'POST',{profile:p,organization_id:org||undefined,expected_version:(this.portal?.organization as unknown as {version?:number})?.version??0,step:input.step??1});}
  if(op==='completeOrganizationRegistration'){if(!org)throw new HttpServiceError('missing_organization','Save the organization request first.');return this.write('/organizations/'+org+'/registration/complete','POST',{});}
  const offer=this.portal?.offers.find(o=>o.id===input.offerId),id=String(input.eventId??offer?.event_id??this.current()),base='/events/'+id;
  const write=(path:string,body:unknown={})=>this.write<T>(path,'POST',body,id);
  if(op==='saveSponsorOffer')return write(org?'/organizations/'+org+'/offers':base+'/support-offers/draft',{event_id:org?id:undefined,offer_id:input.offerId,organization_id:org||undefined,resource_id:input.resourceId,support_type:input.supportType,description:input.description,quantity:input.quantity,unit:input.unit,estimated_value:input.estimatedValue,delivery_date:input.deliveryDate??'',delivery_method:input.deliveryMethod??'',notes:input.notes??'',submit:input.submit??false});
  if(op==='submitSponsorOffer'||op==='withdrawSponsorOffer'){if(!org)throw new HttpServiceError('missing_organization','Select the representative organization.');return write('/organizations/'+org+'/offers/'+input.offerId+'/'+(op==='submitSponsorOffer'?'submit':'withdraw'));}
  if(op==='acceptSponsorOffer'||op==='rejectSponsorOffer')return write(base+'/sponsor-offers/'+input.offerId+'/'+(op==='acceptSponsorOffer'?'accept':'reject'));
  if(op==='reportSponsorFulfillment')return write(org?'/organizations/'+org+'/offers/'+input.offerId+'/fulfillment-reports':base+'/sponsor-offers/'+input.offerId+'/fulfillments',{quantity:input.quantity,reference:input.reference,evidence_reference:input.evidenceReference??input.reference});
  if(op==='verifySponsorOfferReceipt'||op==='verifySponsorFulfillment'){
   const state=await this.organizerSponsorOffers(id);const o=state.offers.find(o=>o.id===input.offerId);if(!o)throw new HttpServiceError('missing_offer','Reload the exact accepted offer.');return write(base+'/resource-receipts',{offer_id:o.id,fulfillment_id:state.fulfillments?.find(f=>f.offer_id===o.id&&!f.verified&&f.quantity===Number(input.quantity))?.id,resource_id:o.resource_requirement_id,quantity:input.quantity,unit:o.unit,reference:input.reference,evidence_reference:input.evidenceReference??input.reference});
  }
  return this.unsupported();
 }
 async organizerSponsorOffers(id:string):Promise<OrganizerSponsorState>{return this.read('/events/'+id+'/organizer/sponsor-offers',id)}
}
