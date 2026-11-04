import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import type {ParticipationState} from '../src/services/participant-contracts';
import {JoinApplication} from '../src/features/participation/JoinApplication';
const mock=vi.hoisted(()=>({state:null as ParticipationState|null,act:vi.fn()}));
vi.mock('../src/features/participation/useParticipation',()=>({useParticipation:()=>({...mock,problem:'',busy:false})}));
vi.mock('../src/app/layout',()=>({Layout:({children}:{children:React.ReactNode})=><main>{children}</main>}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
function open(fail=false){
 mock.state={event:{id:'reading',title:'Reading workshop',location:{label:'Hazaribagh'},schedule:{timezone:'Asia/Kolkata'}},account:{id:'participant'},roles:[{id:'photo',title:'Photo Support',required_capabilities:['Photography'],work_ids:['work'],open_positions:2,commitment:{schedule_intervals:[]}}],day_count:3,availability:[],application:{id:'application',status:'application_draft',wizard_step:3,role_requirement_ids:[],availability_snapshot:[],answers:{skills:'I can take photos',motivation:'',custom_answers:{},participant_insights:{fields:{},tag_ids:[],consent:false}}}} as unknown as ParticipationState;
 mock.act.mockImplementation(async(op:string)=>op==='suggestApplicantRoles'?fail?{status:'failed',recommendations:[],message:'AI unavailable; choose manually.',model_execution:false}:{status:'available',recommendations:[{role_id:'photo',explanation:'Photography experience matches this role.',missing_information:[],trade_offs:[]}],model_execution:true}:{saved:true});
 render(<MemoryRouter><JoinApplication/></MemoryRouter>);
}
it('renders real service suggestions without selecting roles or submitting',async()=>{
 open();fireEvent.click(screen.getByRole('button',{name:'Suggest Roles with AI'}));
 await screen.findByText('Photography experience matches this role.');
 expect(mock.act.mock.calls.map(c=>c[0])).toEqual(['saveApplicationDraft','suggestApplicantRoles']);
 expect(screen.getByRole('checkbox',{name:/Photo Support/})).not.toBeChecked();
 fireEvent.click(screen.getByRole('button',{name:'Next: Review'}));
 await screen.findByText('Select at least one published role.');
 expect(mock.act).not.toHaveBeenCalledWith('submitApplication',expect.anything());
});
it('retains manual role selection on AI failure',async()=>{
 open(true);fireEvent.click(screen.getByRole('button',{name:'Suggest Roles with AI'}));
 await screen.findByRole('alert');
 fireEvent.click(screen.getByRole('checkbox',{name:/Photo Support/}));
 fireEvent.click(screen.getByRole('button',{name:'Next: Review'}));
 await waitFor(()=>expect(mock.act).toHaveBeenCalledWith('advanceApplication',{applicationId:'application',step:4,stepOrder:'availability_first'}));
});
