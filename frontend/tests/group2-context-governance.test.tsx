import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {AppProvider} from '../src/app/provider';
import {App} from '../src/app/App';
import {EventContext} from '../src/features/event-creation/EventContext';
import {DEFAULT_FORM} from '../src/features/event-creation/model';
import type {AroundYouService} from '../src/services/contracts';

it('offers manual organizer context confirmation in HTTP mode without calling a model',async()=>{
 sessionStorage.setItem('aroundyou.demo.identity',JSON.stringify({accountId:'u',label:'Organizer',kind:'personal'}));
 const form={...DEFAULT_FORM,executionIntent:'My exact original explanation'};
 const saved={event:{id:'e'},context:{version:2,original_text:form.executionIntent},runtime:{revision:2}};
 const confirm=vi.fn(async()=>saved);const suggest=vi.fn();
 const service={mode:'http',setIdentity:()=>{},saveIntent:async()=>saved,confirmContextManually:confirm,suggestUnderstanding:suggest} as unknown as AroundYouService;
 render(<MemoryRouter><AppProvider providedService={service}><EventContext form={form} update={()=>{}} errors={{}}/></AppProvider></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'Complete context manually'}));
 fireEvent.change(await screen.findByLabelText('Work scope'),{target:{value:'Reading sessions'}});
 fireEvent.click(screen.getByRole('button',{name:'Accept interpretation'}));
 await waitFor(()=>expect(confirm).toHaveBeenCalledWith(2,expect.objectContaining({scope:['Reading sessions']})));
 expect(suggest).not.toHaveBeenCalled();expect(screen.queryByRole('button',{name:'Try voice demo'})).not.toBeInTheDocument();
});

it('displays and reviews pending governance advice in HTTP mode',async()=>{
 sessionStorage.setItem('aroundyou.demo.identity',JSON.stringify({accountId:'u',label:'Organizer',kind:'personal'}));
 const state={event:{id:'e',title:'Reading workshop',category:'Education',format:'in_person',location:{label:'Library'},schedule:{timezone:'Asia/Kolkata'}},context:{version:1,original_text:'Reading sessions'},planning:{stages:{},work:{},roles:{},resources:{}},proposals:[],work_groups:[],warnings:[],revision:1};
 const governance={guidance:{status:'not_assessed'},items:[],ticket:null,proposals:[{id:'p',digest:'abc',status:'pending',items:[{id:'venue',title:'Check library access',detail:'Ask the venue owner',classification:'conditional_recommendation',uncertainty:['Local rules unverified']}]}]};
 const command=vi.fn(async()=>({saved:true}));
 const service={mode:'http',setIdentity:()=>{},openPlanning:async()=>state,readPlanning:async()=>state,governanceState:async()=>governance,planningCommand:command} as unknown as AroundYouService;
 render(<MemoryRouter initialEntries={['/events/e/governance']}><AppProvider providedService={service}><App/></AppProvider></MemoryRouter>);
 expect(await screen.findByText('Check library access')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Accept advisory assessment'}));
 await waitFor(()=>expect(command).toHaveBeenCalledWith('reviewGovernanceAdvisory',{proposalId:'p',digest:'abc',decision:'accept'}));
 expect(screen.getByText('Verified rule source: none verified in this integration.')).toBeInTheDocument();
});
