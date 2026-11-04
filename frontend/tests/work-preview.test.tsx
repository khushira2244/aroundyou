import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {WorkDesign,workClock} from '../src/features/planning/WorkDesign';
import type {PlanningState} from '../src/services/planning-contracts';
const mock=vi.hoisted(()=>({state:null as PlanningState|null,act:vi.fn(async(..._args:unknown[])=>({saved:true}))}));
vi.mock('../src/features/planning/usePlanning',()=>({usePlanning:()=>({...mock,busy:false,service:{mode:'http'},problem:''})}));
vi.mock('../src/features/planning/PlanningLayout',()=>({stageColor:()=> '#3684f5',PlanningLayout:({children}:{children:React.ReactNode})=><main>{children}</main>,PlanningLoading:()=>null}));
afterEach(()=>{cleanup();mock.act.mockClear()});
function open(stageScope='s',status='proposed'){
 const stage={id:'s',title:'Prepare venue',relative_start:2,relative_end:2,duration:{value:1},effort:{value:null}};
 const work={id:'w',stage_id:'s',title:'Inspect room',outcome:'Document access',scope:'Check room',work_group_id:'g',role_requirement_ids:[],resource_requirement_ids:[],skills:[],exclusion_constraints:[],conditions:[],evidence_requirements:[],volume:{value:1,unit:'room'},effort:{value:4},duration:{value:2},dependency_ids:[],schedule:{start_day:2,end_day:2,start_minute:540,end_minute:660}};
 mock.state={event:{id:'e',title:'Education',schedule:{anchor_date:'2026-11-06',timezone:'Asia/Kolkata'}},planning:{stages:{s:stage},stage_confirmed:true,work:{},resources:{},derived_from:null},proposals:[{id:'p',kind:'planning_work_chat',stage_id:stageScope,status,preview_plan:{stages:[stage],work:[work],resources:[],roles:[]},message:'Generated work',violations:[],provenance:{source:'test'}}],warnings:[]} as unknown as PlanningState;
 render(<MemoryRouter><WorkDesign/></MemoryRouter>);
}
it('shows pending work in the Gantt without applying it and places Back inside the chart',()=>{
 open();expect(screen.getByRole('button',{name:'Edit w schedule'})).toBeInTheDocument();
 const heading=screen.getByRole('heading',{name:'Work Items for Prepare venue'});
 expect(within(heading.closest('section')!).getByRole('button',{name:'Back to Stage Plan'})).toBeInTheDocument();
 expect(screen.queryByText('Proposed Plan & Key Assumptions')).not.toBeInTheDocument();
 expect(screen.queryByText('Generated work')).not.toBeInTheDocument();
 expect(mock.act).not.toHaveBeenCalled();expect(mock.state!.planning.work).toEqual({});
});
it('confirms the exact preview before selected-stage work confirmation',async()=>{
 open();fireEvent.click(screen.getByRole('button',{name:'Confirm Work Design'}));
 await waitFor(()=>expect(mock.act).toHaveBeenCalledTimes(2));
 expect(mock.act.mock.calls).toEqual([['approveWorkDesign',{proposalId:'p'}],['confirmWorkDesign',{stageId:'s'}]]);
});
it('edits and resizes pending work through its source proposal',async()=>{
 open();fireEvent.keyDown(screen.getByRole('slider',{name:'Resize w duration'}),{key:'ArrowRight'});
 await waitFor(()=>expect(mock.act).toHaveBeenCalledWith('reviseWorkDesign',{workId:'w',baseProposalId:'p',patch:{startDay:2,durationDays:2}}));
});
it.each([['other-stage','proposed'],['s','rejected']])('does not show foreign-stage or rejected work (%s, %s)',(scope,status)=>{
 open(scope,status);expect(screen.queryByRole('button',{name:'Edit w schedule'})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Confirm Work Design'})).toBeDisabled();
});

it('shows work names instead of internal IDs and formats non-hour times',()=>{
 open();expect(screen.getAllByText('Inspect room').length).toBeGreaterThan(0);
 expect(screen.queryByText('w · Inspect room')).not.toBeInTheDocument();
 expect(screen.getByText('09:00–11:00 · Document access')).toBeInTheDocument();
 expect(workClock(569)).toBe('09:29');expect(workClock(1049)).toBe('17:29');expect(workClock(1440)).toBe('24:00');
 expect(workClock(NaN)).toBe('Time unconfirmed');
});
