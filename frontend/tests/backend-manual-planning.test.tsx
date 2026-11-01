import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {AppProvider} from '../src/app/provider';
import {App} from '../src/app/App';
import type {AroundYouService} from '../src/services/contracts';
import type {PlanningState,Stage} from '../src/services/planning-contracts';

it('renders an empty backend plan and creates a manual stage using server-issued IDs',async()=>{
 sessionStorage.setItem('aroundyou.demo.identity',JSON.stringify({accountId:'user',label:'Organizer',kind:'personal'}));
 const state={event:{id:'real-event',title:'Reading workshop',schedule:{timezone:'Asia/Kolkata'}},context:{version:1,original_text:'Reading practice'},planning:{stages:{},work:{},roles:{},resources:{},stage_revision:1,work_revision:1,stage_confirmed:false,work_confirmed:false,actors_confirmed:false,derived_from:null},proposals:[],active_plan_id:null,publication:'unpublished',work_groups:[],warnings:[],revision:1} as unknown as PlanningState;
 const command=vi.fn(async(op:string,input:Record<string,unknown>)=>{if(op==='addStage'){const stage={id:'server-stage-uuid',title:String(input.title),purpose:'',intended_outcomes:[],relative_start:1,relative_end:1,dependency_ids:[],volume:{value:null,unit:'work_blocks'},effort:{value:null,unit:'person_hours'},duration:{value:null,unit:'days'},capacity:{confirmed_people:0,feasibility:'unverified'},staffing_assumptions:[],resource_constraints:[],responsible_role_requirement_id:''} as Stage;state.planning.stages[stage.id]=stage;}return {saved:true}});
 const service={mode:'http',setIdentity:()=>{},openPlanning:async()=>structuredClone(state),readPlanning:async()=>structuredClone(state),planningCommand:command} as unknown as AroundYouService;
 render(<MemoryRouter initialEntries={['/events/real-event/planning']}><AppProvider providedService={service}><App/></AppProvider></MemoryRouter>);
 await screen.findByRole('heading',{name:'Stage Planning'});expect(screen.getByRole('button',{name:'Confirm Stage Plan'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Add Stage'}));const modal=screen.getByRole('dialog',{name:'Add Stage'});fireEvent.change(within(modal).getByLabelText('Stage title'),{target:{value:'Reading session'}});fireEvent.click(within(modal).getByRole('button',{name:'Save Stage'}));
 await waitFor(()=>expect(command).toHaveBeenCalledWith('addStage',expect.objectContaining({title:'Reading session'})));await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm Stage Plan'})).toBeEnabled());
 expect(screen.queryByText(/Six connected stages/)).not.toBeInTheDocument();
});


it('resumes the selected backend draft from My Events instead of a fixture/global event',async()=>{
 sessionStorage.setItem('aroundyou.demo.identity',JSON.stringify({accountId:'user',label:'Organizer',kind:'personal'}));
 const {DEFAULT_FORM}=await import('../src/features/event-creation/model');
 const event={id:'selected-server-draft',title:'Saved reading draft',lifecycle:'draft',location:{label:'Town library'},schedule:{anchor_date:null,timezone:'Asia/Kolkata'}};
 const selected=vi.fn();const creation={event,context:{id:'context',version:1,original_text:''},runtime:{revision:1,lifecycle:'draft',publication:'unpublished',wizard_step:1,draft:{creation_details:{...DEFAULT_FORM,title:event.title}},context_version:1},sample_intent:''};
 const service={mode:'http',setIdentity:()=>{},selectEvent:selected,myEvents:async()=>[{event,organizer:true,applications:[],accepted_assignments:[]}],startCreation:async()=>creation,saveDraft:async()=>creation,demoAccounts:()=>[]} as unknown as AroundYouService;
 render(<MemoryRouter initialEntries={['/my-events?tab=organizing']}><AppProvider providedService={service}><App/></AppProvider></MemoryRouter>);
 fireEvent.click(await screen.findByRole('button',{name:'Resume Draft'}));await waitFor(()=>expect(selected).toHaveBeenCalledWith('selected-server-draft'));
 expect(await screen.findByRole('heading',{name:'Create Event'})).toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Use Canary Hill demo example'})).not.toBeInTheDocument();
});
