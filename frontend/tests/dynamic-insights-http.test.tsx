import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {DynamicInsightFields} from '../src/features/participation/DynamicInsightFields';
import {DynamicInsightSettings} from '../src/features/event-setup/DynamicInsightSettings';
const {command}=vi.hoisted(()=>({command:vi.fn()}));
vi.mock('../src/app/provider',()=>({useApp:()=>({service:{mode:'http',insightCommand:command}}),useOptionalApp:()=>({service:{mode:'http',insightCommand:command}})}));
afterEach(()=>{cleanup();command.mockReset()});
const config={revision:7,public_aggregates:true,questions:[{id:'age',label:'Age range',description:'Optional age band',dimension:'age_range',choices:['18-24','25-34'],required:false,enabled:true,aggregate:true},{id:'club',label:'Reading club',description:'',dimension:'tags',choices:['Tutor','Reader'],required:true,enabled:true,aggregate:true},{id:'disabled',label:'Hidden question',choices:['No'],enabled:false}]};
function mount(node:React.ReactNode){render(<MemoryRouter initialEntries={['/events/e/join']}><Routes><Route path="/events/:eventId/join" element={node}/></Routes></MemoryRouter>)}
it('loads current bounded questions, saves exact version and independent consent, then revokes',async()=>{
 command.mockImplementation(async(op:string)=>op==='configuration'?config:op==='response'?{response:null}:{});mount(<DynamicInsightFields/>);
 await screen.findByLabelText('Reading club');expect(screen.queryByLabelText('Hidden question')).toBeNull();
 fireEvent.change(screen.getByLabelText('Reading club'),{target:{value:'Tutor'}});fireEvent.click(screen.getByText('Save private responses'));
 await waitFor(()=>expect(command).toHaveBeenCalledWith('respond',expect.objectContaining({configuration_revision:7,answers:{club:'Tutor'},consent:false})));
 fireEvent.click(screen.getByText('Revoke aggregate consent'));await waitFor(()=>expect(command).toHaveBeenCalledWith('revoke',expect.anything()));
});
it('organizer edits structured Tag choices and saves the reviewed configuration version',async()=>{
 command.mockResolvedValue(config);mount(<DynamicInsightSettings/>);await screen.findByDisplayValue('Reading club');
 fireEvent.change(screen.getAllByLabelText('Choices (one per line)')[1],{target:{value:'Tutor\nReader\nCoordinator'}});fireEvent.click(screen.getByText('Save event questions'));
 await waitFor(()=>expect(command).toHaveBeenCalledWith('configure',expect.objectContaining({expected_revision:7,questions:expect.arrayContaining([expect.objectContaining({id:'club',choices:['Tutor','Reader','Coordinator']})])})));
});
