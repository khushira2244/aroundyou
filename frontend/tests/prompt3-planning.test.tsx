import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {Timeline} from '../src/features/planning/Timeline';
import {PlanningAssistant} from '../src/features/planning/PlanningAssistant';
import {AppProvider} from '../src/app/provider';
import {App} from '../src/app/App';
import type {AroundYouService} from '../src/services/contracts';
import type {PlanningProposal} from '../src/services/planning-contracts';
afterEach(cleanup);

it('moves and resizes only through explicit timeline gestures and renders anchored dates',()=>{
 const move=vi.fn(),edit=vi.fn();render(<Timeline anchorDate="2026-11-05" horizon={5} rows={[{id:'s',title:'Prepare reading room',subtitle:'Review venue',volume:'1 room',effort:'4',start:1,finish:2,dependencies:[],colorIndex:0}]} onMove={move} onEdit={edit}/>);
 expect(move).not.toHaveBeenCalled();expect(screen.getByText('2026-11-05')).toBeInTheDocument();
 fireEvent.keyDown(screen.getByRole('button',{name:'Edit s schedule'}),{key:'ArrowRight'});expect(move).toHaveBeenLastCalledWith('s',2,2);
 fireEvent.keyDown(screen.getByRole('slider',{name:'Resize s duration'}),{key:'ArrowRight'});expect(move).toHaveBeenLastCalledWith('s',1,3);expect(move).toHaveBeenCalledTimes(2);
 fireEvent.drop(screen.getByLabelText('s Day 4'),{dataTransfer:{getData:()=> 's'}});expect(move).toHaveBeenLastCalledWith('s',4,2);
});
it('separates advisory questions from explicit recalculation and does not apply advisory text',()=>{
 const ask=vi.fn(),send=vi.fn(),apply=vi.fn();const p={id:'p',kind:'planning_chat',status:'proposed',message:'The venue must be prepared before teaching.',advisory_only:true,context_version:2,base_stage_revision:1,base_work_revision:1,provenance:{source:'muse-spark-1.3',model_execution:true}} as PlanningProposal;
 render(<PlanningAssistant backend mode="stage" busy={false} proposal={p} history={[]} onAsk={ask} onSend={send} onApprove={apply} onReject={()=>{}}/>);
 expect(ask).not.toHaveBeenCalled();expect(screen.getByText('Muse Spark · human review required')).toBeInTheDocument();expect(screen.queryByText('Fixture simulation · no live AI')).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Apply Changes'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Ask AI · advisory answer'}));expect(ask).toHaveBeenCalledOnce();expect(send).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Request Changes'}));expect(send).toHaveBeenCalledOnce();expect(apply).not.toHaveBeenCalled();
});
it('opens an empty HTTP actor screen safely and offers genuine generation without automatic inference',async()=>{
 sessionStorage.setItem('aroundyou.demo.identity',JSON.stringify({accountId:'u',label:'Organizer',kind:'personal'}));
 const state={event:{id:'e',title:'Reading workshop',schedule:{timezone:'Asia/Kolkata'}},context:{version:1},planning:{stages:{s:{id:'s',title:'Teaching',relative_start:1,relative_end:1,duration:{value:1,unit:'days'}},s2:{id:'s2',title:'Feedback',relative_start:2,relative_end:2,duration:{value:1,unit:'days'}}},work:{},roles:{},resources:{},work_confirmed:true,actors_confirmed:false,derived_from:null},proposals:[],work_groups:[],warnings:[],revision:1};
 const command=vi.fn(async()=>({queued:true}));const service={mode:'http',setIdentity:()=>{},openPlanning:async()=>state,readPlanning:async()=>state,planningCommand:command} as unknown as AroundYouService;
 render(<MemoryRouter initialEntries={['/events/e/actors']}><AppProvider providedService={service}><App/></AppProvider></MemoryRouter>);
 expect(await screen.findByText('No actor requirements generated yet.')).toBeInTheDocument();expect(command).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Generate Actor Requirements'}));await waitFor(()=>expect(command).toHaveBeenCalledWith('deriveActorRequirements',{stageId:'s'}));
 fireEvent.click(screen.getByRole('button',{name:/Feedback/}));expect(screen.getByRole('button',{name:/Feedback/})).toHaveClass('selected');
 fireEvent.click(screen.getByRole('button',{name:'Generate Actor Requirements'}));await waitFor(()=>expect(command).toHaveBeenLastCalledWith('deriveActorRequirements',{stageId:'s2'}));
});

