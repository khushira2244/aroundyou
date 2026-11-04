/* AROUNDYOU UI CHANGE: verify organizer investigation actions without live inference or database writes. */
import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {HttpRecoveryPanel} from '../src/features/recovery/HttpRecoveryPanel';
const mock=vi.hoisted(()=>({service:null as unknown}));
vi.mock('../src/app/provider',()=>({useApp:()=>({service:mock.service})}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
function setup(options:{failure?:boolean;resume?:boolean}={}){
 const schedule={start_day:2,end_day:2,start_minute:540,end_minute:720,timezone:'Asia/Kolkata'};
 const work={id:'work-private-id',title:'Supervised litter collection',stage_id:'stage-private-id',scope:'Collect light litter in safe areas.',outcome:'Litter bagged safely',resource_requirement_ids:['resource-private-id'],schedule};
 const scope={affected_work_ids:[work.id],affected_resource_ids:['resource-private-id'],work:[{work_id:work.id,classification:'directly_blocked'}]};
 let hub={id:'workspace-private-id',revision:1,base_plan_id:'plan',status:'recovery_planning',stale:false,scope,nodes:[{key:'work:'+work.id,original:work,patch:{} as object,status:'needs_review'}],people:[{account_id:'account-private-id',classification:'affected_participant'}],alternative_id:null as string|null,communication:null as {mode:string;meeting_ids:string[]}|null,reviews:{} as Record<string,{note:string}>};
 let items:unknown[]=[],confirmed=!!options.resume;
 const command=vi.fn(async(op:string,body:Record<string,unknown>)=>{
  if(op==='list')return {items};
  if(op==='confirm'){if(options.failure)throw new Error('Review current issue and plan');confirmed=true;return {condition_confirmed:true}}
  if(op==='impact'){if(!confirmed)throw Object.assign(new Error('Requires a human-reviewed uncleared condition'),{status:'unconfirmed_blocker'});return {scope}}
  if(op==='workspace'||op==='openWorkspace')return structuredClone(hub);
  if(op==='local-review'){hub={...hub,revision:hub.revision+1,nodes:[{...hub.nodes[0],patch:body.patch as object,status:String(body.status)}],reviews:{[String(body.node_key)]:{note:String(body.note)}}};return structuredClone(hub)}
  if(op==='submit'){const alternative={id:'alternative',revision:1,title:'Reviewed selective recovery',proposal_digest:'digest',status:'pending',validation:{status:'conditional',errors:[],conditions:['participant_reconfirmation_required']},changed_work_ids:[work.id],plan:{work:[work]},outcome:'inconclusive'};items=[alternative];hub={...hub,alternative_id:alternative.id};return {workspace:structuredClone(hub),alternative}}
  if(op==='review'){items=(items as {status:string}[]).map(p=>({...p,status:'conditionally_approved'}));return {status:'conditionally_approved'}}
  if(op==='communication'){hub={...hub,revision:hub.revision+1,communication:{mode:String(body.mode),meeting_ids:body.mode==='meeting'?['meeting']:[]}};return structuredClone(hub)}
  if(op==='ai')return {advisory:{alternatives:[]}};
  throw new Error('Unexpected operation '+op);
 });
 mock.service={executionState:vi.fn(async()=>({plan_id:'plan',blockers:[{id:'issue-private-id',description:'I will arrive one hour late.',revision:1,work_ids:[work.id],evidence_ids:[],possible_effect:'Morning coverage may be delayed.'}],work:[work],stages:[{id:'stage-private-id',title:'Cleanup'}],resources:[{id:'resource-private-id',title:'Protective gloves',quantity:20,unit:'pairs'}],evidence:[]})),organizerParticipants:vi.fn(async()=>({applications:[{account_id:'account-private-id',applicant_label:'Khushi'}],roles:[],event:{schedule:{timezone:'Asia/Kolkata'}}})),recoveryCommand:command};
 render(<MemoryRouter initialEntries={[options.resume?'/events/event/manage/blockers?issue=issue-private-id&workspace=workspace-private-id&node=work:work-private-id':'/events/event/manage/blockers']}><HttpRecoveryPanel eventId="event"/></MemoryRouter>);
 return command;
}
async function analyze(){await screen.findByRole('heading',{name:'Blocker Investigation'});fireEvent.change(screen.getByLabelText('Review rationale'),{target:{value:'Review the operational impact of the reported delay.'}});fireEvent.click(screen.getByRole('button',{name:'Analyze Impact'}));await screen.findByText('Impact analyzed. Current work and assignments remain unchanged.');}
it('analyzes real service scope, resolves names, and saves no-change reviews without fake approval',async()=>{
 const command=setup();await analyze();expect(command.mock.calls.map(c=>c[0])).toEqual(expect.arrayContaining(['confirm','impact','openWorkspace']));expect(screen.getByText('Supervised litter collection')).toBeTruthy();expect(screen.getAllByText('Khushi').length).toBeGreaterThan(0);expect(screen.getByText(/Protective gloves/)).toBeTruthy();expect(screen.queryByText(/work-private-id/)).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:/No plan change needed/}));fireEvent.click(screen.getByRole('button',{name:'Save Review'}));await screen.findByText(/Review saved/);expect(command).toHaveBeenCalledWith('local-review',expect.objectContaining({patch:{},status:'reviewed_no_change'}));expect(screen.getByRole('button',{name:'Approve Recovery Decision'})).toBeDisabled();expect(screen.getByText(/cannot approve an empty plan revision/)).toBeTruthy();expect(command.mock.calls.some(c=>['ai','activate','submit'].includes(c[0]))).toBe(false);
});
it('saves a scoped work patch and approves its exact decision without activating',async()=>{
 const command=setup();await analyze();fireEvent.click(screen.getByRole('button',{name:/Review Work Design changes/}));expect(screen.getByRole('link',{name:'Open affected Work Design'})).toHaveAttribute('target','_blank');expect(screen.getByRole('link',{name:'Return to this blocker'}).getAttribute('href')).toContain('workspace=workspace-private-id');
 fireEvent.change(screen.getByLabelText('Local review decision'),{target:{value:'confirmed_local_change'}});fireEvent.change(screen.getByLabelText('Proposed fields (JSON)'),{target:{value:'{"scope":"Supervised safe-area collection with revised coverage."}'}});expect(screen.getByRole('button',{name:'Approve Recovery Decision'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Save Review'}));await screen.findByText(/Review saved/);await waitFor(()=>expect(screen.getByRole('button',{name:'Approve Recovery Decision'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Approve Recovery Decision'}));await screen.findByText(/Recovery decision approved. No plan was activated/);expect(command).toHaveBeenCalledWith('review',expect.objectContaining({recoveryId:'alternative',proposal_digest:'digest',expected_revision:1,decision:'approve'}));expect(command.mock.calls.some(c=>c[0]==='activate')).toBe(false);
});
it('coordinates selected actual recipients and requires meeting times',async()=>{
 const command=setup();await analyze();fireEvent.click(screen.getByRole('checkbox',{name:/Khushi/}));fireEvent.click(screen.getByRole('button',{name:'Send targeted update'}));await screen.findByText(/Targeted in-app update recorded/);expect(command).toHaveBeenCalledWith('communication',expect.objectContaining({mode:'targeted',invited_account_ids:['account-private-id']}));fireEvent.click(screen.getByRole('button',{name:'Propose meeting'}));fireEvent.change(screen.getByLabelText('Relative meeting day'),{target:{value:'2'}});fireEvent.click(screen.getByRole('button',{name:'Confirm meeting proposal'}));await screen.findByText('Linked coordination meeting proposed.');expect(command).toHaveBeenCalledWith('communication',expect.objectContaining({mode:'meeting',schedule:expect.objectContaining({start_day:2,timezone:'Asia/Kolkata'})}));
});
it('AI remains optional and opening the suggestions panel makes no model request',async()=>{
 const command=setup();await analyze();fireEvent.click(screen.getByRole('button',{name:/Open AI Recovery Suggestions/}));expect(screen.getByRole('button',{name:'Request AI Recovery Suggestions'})).toBeTruthy();expect(command.mock.calls.some(c=>c[0]==='ai')).toBe(false);
});
it('shows backend prerequisites and stops after condition confirmation fails',async()=>{
 const command=setup({failure:true});await screen.findByLabelText('Review rationale');fireEvent.change(screen.getByLabelText('Review rationale'),{target:{value:'Investigate delay'}});fireEvent.click(screen.getByRole('button',{name:'Analyze Impact'}));await screen.findByRole('alert');expect(command.mock.calls.some(c=>['openWorkspace','activate'].includes(c[0]))).toBe(false);
});
it('restores the saved event-specific blocker and node from the URL without writes',async()=>{
 const command=setup({resume:true});await screen.findByLabelText('Local review decision');expect(command).toHaveBeenCalledWith('workspace',{eventId:'event',workspaceId:'workspace-private-id'});expect(command.mock.calls.some(c=>['confirm','ai','local-review','activate'].includes(c[0]))).toBe(false);
});
