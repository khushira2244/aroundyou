import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {StagePlanning} from '../src/features/planning/StagePlanning';
import type {PlanningState} from '../src/services/planning-contracts';

const mock=vi.hoisted(()=>({state:null as PlanningState|null,act:vi.fn(async(..._args:unknown[])=>({saved:true}))}));
vi.mock('../src/features/planning/usePlanning',()=>({usePlanning:()=>({...mock,busy:false,service:{mode:'http'},problem:''})}));
vi.mock('../src/features/planning/PlanningLayout',()=>({stageColor:()=> '#3684f5',PlanningLayout:({children}:{children:React.ReactNode})=><main>{children}</main>,PlanningLoading:()=>null}));
afterEach(()=>{cleanup();mock.act.mockClear()});

function open(status='proposed',effort:number|null=null,end=2) {
 const stage={id:'prepare',title:'Prepare the venue',purpose:'Check access',intended_outcomes:[],relative_start:1,relative_end:end,dependency_ids:[],volume:{value:null,unit:'sites'},effort:{value:effort,unit:'person_hours'},duration:{value:end,unit:'days'},staffing_assumptions:[],resource_constraints:[]};
 mock.state={event:{id:'e',title:'Workshop',schedule:{anchor_date:'2026-11-06'}},context:{version:8},planning:{stages:{},work:{},stage_confirmed:false},proposals:[{id:'p',kind:'planning_stage_chat',status,preview_plan:{stages:[stage],work:[],roles:[]},message:'Prepare before teaching',changes:['prepare: Day 1â€“2'],provenance:{source:'test'},violations:[]}],warnings:[]} as unknown as PlanningState;
 render(<MemoryRouter><StagePlanning/></MemoryRouter>);
}
it('renders saved pending stages as editable Gantt bars without automatically applying them',async()=>{
 open();expect(screen.getByRole('button',{name:'Edit prepare schedule'})).toBeInTheDocument();
 expect(screen.queryByText('Prepare before teaching')).not.toBeInTheDocument();expect(screen.queryByText('Review proposed stages, work and requirements')).not.toBeInTheDocument();expect(screen.queryByText(/Est. Effort/)).not.toBeInTheDocument();expect(screen.getByText('Day 3')).toBeInTheDocument();expect(screen.queryByText('Day 4')).not.toBeInTheDocument();expect(mock.act).not.toHaveBeenCalled();
 fireEvent.keyDown(screen.getByRole('button',{name:'Edit prepare schedule'}),{key:'ArrowRight'});
 await waitFor(()=>expect(mock.act).toHaveBeenCalledWith('proposeStageEdit',{stageId:'prepare',startDay:2,durationDays:2,baseProposalId:'p'}));
});
it('explicit confirmation applies the exact pending proposal before confirming the stage plan',async()=>{
 open();fireEvent.click(screen.getByRole('button',{name:'Confirm Stage Plan'}));
 await waitFor(()=>expect(mock.act).toHaveBeenCalledTimes(2));
 expect(mock.act.mock.calls[0]).toEqual(['approvePlanningChat',{proposalId:'p'}]);
 expect(mock.act.mock.calls[1]).toEqual(['confirmStagePlan',{proposalId:undefined}]);
});
it('does not display rejected proposal stages as the current Gantt',()=>{
 open('rejected');expect(screen.queryByRole('button',{name:'Edit prepare schedule'})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Confirm Stage Plan'})).toBeDisabled();
});
it('shows exactly one spare day for a three-day proposal and hides zero effort',()=>{
 open('proposed',0,3);
 expect(screen.getByText('Day 4')).toBeInTheDocument();
 expect(screen.queryByText('Day 5')).not.toBeInTheDocument();
 expect(screen.queryByText(/Est. Effort/)).not.toBeInTheDocument();
 expect(screen.queryByText('Linked work blocks')).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Apply Changes'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Reject'})).not.toBeInTheDocument();
});
it('retains a supplied positive effort estimate',()=>{
 open('proposed',8,3);
 expect(screen.getByText(/Est. Effort/)).toBeInTheDocument();
 expect(screen.getByText('8')).toBeInTheDocument();
});
