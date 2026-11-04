import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {ActorRequirements} from '../src/features/planning/ActorRequirements';
import type {PlanningState} from '../src/services/planning-contracts';
const mock=vi.hoisted(()=>({state:null as PlanningState|null,act:vi.fn(async(..._args:unknown[])=>({saved:true}))}));
vi.mock('../src/features/planning/usePlanning',()=>({usePlanning:()=>({...mock,busy:false,service:{mode:'http'},problem:''})}));
vi.mock('../src/features/planning/PlanningLayout',()=>({stageColor:()=> '#3684f5',PlanningLayout:({children,state,onSelectStage}:{children:React.ReactNode;state:PlanningState;onSelectStage:(id:string)=>void})=><><nav aria-label="Stage selection">{Object.values(state.planning.stages).map(s=><button key={s.id} onClick={()=>onSelectStage(s.id)}>Select stage {s.title}</button>)}</nav><main>{children}</main></>,PlanningLoading:()=>null}));
afterEach(()=>{cleanup();mock.act.mockClear()});
function open(status='proposed',hasProposal=true,multi=false,shared=false){
 const stage={id:'s',title:'Teaching',duration:{value:1}};
 const role={id:'r',title:'Workshop facilitator',stage_ids:['s'],work_ids:['w'],source_work_ids:['w'],required_capabilities:['Teaching'],proposed_headcount:2,headcount_basis:'Demand estimate',effort_person_hours:4,schedule_intervals:[],capacity_assumptions:[],safety_considerations:[]};
 mock.state={event:{id:'e',title:'Reading workshop'},planning:{stages:{s:stage},work:{w:{id:'w',title:'Teach reading',work_group_id:'g'}},roles:{},work_confirmed:true,actors_confirmed:false,work_revision:2},proposals:hasProposal?[{id:'p',kind:'actors',stage_id:'s',status,preview_plan:{stages:[stage],roles:[role],work:[]},message:'Saved actor candidate',violations:[],provenance:{source:'test'}}]:[],work_groups:[{id:'g',stage_id:'s',title:'Teaching group'}],warnings:[]} as unknown as PlanningState;
 if(multi){
  mock.state!.planning.stages.s2={...mock.state!.planning.stages.s,id:'s2',title:'Feedback'};
  mock.state!.planning.work.w2={...mock.state!.planning.work.w,id:'w2',title:'Collect feedback',work_group_id:'g2'};
  mock.state!.work_groups.push({id:'g2',stage_id:'s2',title:'Feedback group'});
  mock.state!.proposals.push({...mock.state!.proposals[0],id:'p2',stage_id:'s2',preview_plan:{stages:[],work:[],roles:[{...role,id:'r2',title:'Feedback facilitator',stage_ids:['s2'],work_ids:['w2'],source_work_ids:['w2']} as unknown as import('../src/services/planning-contracts').ActorRequirement]}});
 }
 if(shared){const candidate=mock.state!.proposals[1].preview_plan!.roles[0];candidate.id='r';candidate.title='Workshop facilitator';candidate.stage_ids=['s','s2'];}
 mock.state!.event.creation_details={expectedVolunteers:'20',expectedAttendees:'30'} as import('../src/services/contracts').CreationForm;
 render(<MemoryRouter><ActorRequirements/></MemoryRouter>);
}
it('does not generate actors automatically when the page opens',()=>{
 open('proposed',false);expect(screen.getByText('No actor requirements generated yet.')).toBeInTheDocument();
 expect(mock.act).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Confirm Actor Requirements'})).toBeDisabled();
});
it('restores pending roles directly into the structure with normalized provider fields',()=>{
 open();expect(screen.getAllByRole('button',{name:/Workshop facilitator/})).toHaveLength(2);
 expect(screen.queryByText('No actor requirements generated yet.')).not.toBeInTheDocument();
 expect(screen.queryByText('Review all proposed requirements')).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Apply Actor Proposal'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Reject Actor Proposal'})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Request Changes'})).toBeInTheDocument();
 expect(mock.act).not.toHaveBeenCalled();expect(mock.state!.planning.roles).toEqual({});
});
it('confirms the complete actor structure in one command',async()=>{
 open();fireEvent.click(screen.getByRole('button',{name:'Confirm Actor Requirements'}));
 await waitFor(()=>expect(mock.act).toHaveBeenCalledTimes(1));
 expect(mock.act.mock.calls).toEqual([['confirmActorRequirements',{proposalIds:['p']}]]);
});
it('sends requested actor changes with stage scope and the organizer message',async()=>{
 open();fireEvent.change(screen.getByRole('textbox'),{target:{value:'Use one facilitator where feasible'}});
 fireEvent.click(screen.getByRole('button',{name:'Request Changes'}));
 await waitFor(()=>expect(mock.act).toHaveBeenCalledWith('deriveActorRequirements',{message:'Use one facilitator where feasible',stageId:'s'}));
});
it('does not restore stale actor candidates as current roles',()=>{
 open('stale');expect(screen.getByText('No actor requirements generated yet.')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Confirm Actor Requirements'})).toBeDisabled();
});
// AROUNDYOU UI CHANGE: verify only the real role-detail card expands.
it('opens the role accordion to reveal original details and editing actions',()=>{
 open();const header=screen.getByRole('button',{name:/Role Requirement/});
 expect(header).toHaveAttribute('aria-expanded','false');
 expect(screen.queryByText('Responsibility & source work')).not.toBeInTheDocument();
 fireEvent.click(header);
 expect(header).toHaveAttribute('aria-expanded','true');
 expect(screen.getByText('Responsibility & source work')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Edit Requirement'})).toBeInTheDocument();
 fireEvent.click(header);expect(header).toHaveAttribute('aria-expanded','false');
});
it('shows a compact empty state with manual creation and no fake role detail',()=>{
 open('proposed',false);
 expect(screen.queryByRole('button',{name:/Role Requirement/})).not.toBeInTheDocument();
 expect(screen.queryByText('Required count')).not.toBeInTheDocument();
 expect(screen.queryByText('Unknown')).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Generate Actor Requirements'})).toBeEnabled();
 fireEvent.click(screen.getByRole('button',{name:'Add Role'}));
 expect(screen.getByRole('heading',{name:'Add Role Requirement'})).toBeInTheDocument();
 expect(mock.act).not.toHaveBeenCalled();
});
it('retains separate unconfirmed proposal roles when switching stage tabs',()=>{
 open('proposed',true,true);
 expect(screen.getByRole('button',{name:/Role Requirement/})).toHaveTextContent('Workshop facilitator');
 fireEvent.click(screen.getByRole('button',{name:'Select stage Feedback'}));
 expect(screen.getByRole('button',{name:/Role Requirement/})).toHaveTextContent('Feedback facilitator');
 fireEvent.click(screen.getByRole('button',{name:'Select stage Teaching'}));
 expect(screen.getByRole('button',{name:/Role Requirement/})).toHaveTextContent('Workshop facilitator');
 expect(mock.act).not.toHaveBeenCalled();expect(mock.state!.planning.roles).toEqual({});
});
it('shows each saved stage with its own actors in one workforce tree',()=>{
 open('proposed',true,true);
 const workforce=screen.getByRole('region',{name:'Event workforce'});
 expect(within(workforce).getByRole('button',{name:/Workshop facilitator/})).toHaveTextContent('2 people required');
 expect(within(workforce).getByRole('button',{name:/Feedback facilitator/})).toHaveTextContent('2 people required');
 expect(within(workforce).getByText('Teaching')).toBeInTheDocument();
 expect(within(workforce).getByText('Feedback')).toBeInTheDocument();
 expect(within(workforce).queryByText('Teaching group')).not.toBeInTheDocument();
 expect(within(workforce).getByText(/not counted as workers/)).toHaveTextContent('Planned volunteers: 20 · Attendees: 30');
 fireEvent.click(screen.getByRole('button',{name:'Select stage Feedback'}));
 expect(within(workforce).getAllByRole('button')).toHaveLength(2);
 expect(mock.act).not.toHaveBeenCalled();
});
it('marks shared actor references across stages without adding people',()=>{
 open('proposed',true,true,true);
 const workforce=screen.getByRole('region',{name:'Event workforce'});
 expect(within(workforce).getAllByRole('button')).toHaveLength(2);
 for(const node of within(workforce).getAllByRole('button')){expect(node).toHaveAttribute('data-actor-id','r');expect(node).toHaveTextContent('2 people required');expect(node).toHaveTextContent('Shared actor');}
 expect(within(workforce).queryByText('4 people required')).not.toBeInTheDocument();
 for(const node of within(workforce).getAllByRole('button'))expect(node).toHaveTextContent('Proposed requirement');
});
// AROUNDYOU UI CHANGE: stage branches are membership, not invented management.
it('connects stages and actors under one root and opens existing details on click',()=>{
 open('proposed',true,true);
 const workforce=screen.getByRole('region',{name:'Event workforce'});
 expect(within(workforce).getByText('Event Workforce')).toHaveClass('workforce-root');
 const branches=within(workforce).getByRole('list',{name:'Event workforce stages'});
 expect(branches.children).toHaveLength(2);
 expect(within(branches.children[0] as HTMLElement).getByRole('button',{name:/Workshop facilitator/})).toBeInTheDocument();
 expect(within(branches.children[1] as HTMLElement).getByRole('button',{name:/Feedback facilitator/})).toBeInTheDocument();
 expect(workforce.querySelectorAll('.workforce-root')).toHaveLength(1);
 expect(workforce.querySelector('.workforce-nodes')).toBeNull();
 fireEvent.click(within(branches).getByRole('button',{name:/Feedback facilitator/}));
 expect(screen.getByRole('button',{name:/Role Requirement/})).toHaveAttribute('aria-expanded','true');
 expect(screen.getByText('Responsibility & source work')).toBeInTheDocument();
 expect(mock.act).not.toHaveBeenCalled();
});
it('keeps the saved stage branch and plus placeholder before generation',()=>{
 open('proposed',false);
 const workforce=screen.getByRole('region',{name:'Event workforce'});
 expect(workforce.querySelectorAll('.workforce-root')).toHaveLength(1);
 expect(within(workforce).getByText('Teaching')).toBeInTheDocument();
 expect(workforce.querySelectorAll('.workforce-stage-empty')).toHaveLength(1);
 expect(within(workforce).getByText('No actors generated yet')).toBeInTheDocument();
 expect(workforce.querySelectorAll('[data-actor-id]')).toHaveLength(0);
 expect(mock.act).not.toHaveBeenCalled();
});
it('sends every generated stage candidate through the single event confirmation',async()=>{
 open('proposed',true,true);
 fireEvent.click(screen.getByRole('button',{name:'Confirm Actor Requirements'}));
 await waitFor(()=>expect(mock.act).toHaveBeenCalledWith('confirmActorRequirements',{proposalIds:['p','p2']}));
 expect(mock.act).toHaveBeenCalledTimes(1);
 expect(screen.queryByRole('button',{name:'Confirm This Stage'})).not.toBeInTheDocument();
});
