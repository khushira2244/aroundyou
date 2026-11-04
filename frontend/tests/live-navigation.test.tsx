import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {MemoryRouter,Route,Routes} from 'react-router-dom';
import {AppProvider} from '../src/app/provider';
import {Signup} from '../src/features/auth/Signup';
import {Header} from '../src/app/layout';
import {OrganizerEvents} from '../src/features/organizer/OrganizerEvents';
import {validMapCoordinate} from '../src/shared/GoogleEventMap';
import type {AroundYouService,EventLocation} from '../src/services/contracts';
import {SponsorShell} from '../src/features/sponsor-dashboard/SponsorShell';
import type {SponsorPortal} from '../src/services/sponsor-contracts';
afterEach(()=>vi.unstubAllEnvs());
const service=(extra:object={})=>({mode:'http',setIdentity:vi.fn(),...extra} as unknown as AroundYouService);
it('live signup removes demo pickers and routes authoritative sponsor identity to existing onboarding',async()=>{
 vi.stubEnv('VITE_AROUNDYOU_MODE','http');const authCommand=vi.fn(async()=>({accountId:'real-sponsor',label:'Representative',kind:'sponsor'}));
 render(<MemoryRouter initialEntries={['/signup']}><AppProvider providedService={service({authCommand})}><Routes><Route path="/signup" element={<Signup/>}/><Route path="/sponsor/register/1" element={<p>Existing organization onboarding</p>}/></Routes></AppProvider></MemoryRouter>);
 expect(screen.queryByLabelText('Demo personal identity')).toBeNull();expect(screen.queryByRole('button',{name:/Load canary/})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:/Sponsor \/ Organization/}));fireEvent.change(screen.getByLabelText('Full name'),{target:{value:'Representative'}});fireEvent.change(screen.getByLabelText('Email'),{target:{value:'rep@example.org'}});fireEvent.change(screen.getByLabelText('Password (optional)'),{target:{value:'a-long-test-password'}});fireEvent.submit(screen.getByRole('button',{name:'Create Sponsor Account'}).closest('form')!);
 await screen.findByText('Existing organization onboarding');expect(authCommand).toHaveBeenCalledWith('signup',expect.objectContaining({kind:'sponsor',email:'rep@example.org'}));
});
it('sponsor header hides personal My Events and uses real logout',async()=>{
 vi.stubEnv('VITE_AROUNDYOU_MODE','http');sessionStorage.setItem('aroundyou.demo.identity',JSON.stringify({accountId:'s',label:'Sponsor rep',kind:'sponsor'}));const authCommand=vi.fn(async()=>null);
 render(<MemoryRouter><AppProvider providedService={service({authCommand})}><Header/></AppProvider></MemoryRouter>);
 expect(screen.queryByText('My Events')).toBeNull();fireEvent.click(screen.getByRole('button',{name:/Sponsor rep/}));expect(screen.queryByText(/Switch to/)).toBeNull();fireEvent.click(screen.getByRole('button',{name:'Sign out'}));await waitFor(()=>expect(authCommand).toHaveBeenCalledWith('logout'));
});
it('organizer list filters owned events and resumes the server-selected exact creation step',async()=>{
 const event={id:'owned',title:'Reading workshop',lifecycle:'draft',location:{label:'Local library'},schedule:{timezone:'Asia/Kolkata',anchor_date:null}};const selectEvent=vi.fn();
 const rows=[{event,organizer:true,resume_path:'/create/3',applications:[],accepted_assignments:[]},{event:{...event,id:'other',title:'Another organizer'},organizer:false,applications:[],accepted_assignments:[]}];
 render(<MemoryRouter><AppProvider providedService={service({myEvents:async()=>rows,selectEvent})}><Routes><Route path="/" element={<OrganizerEvents/>}/><Route path="/create/3" element={<p>Saved context step</p>}/></Routes></AppProvider></MemoryRouter>);
 await screen.findByText('Reading workshop');expect(screen.queryByText('Another organizer')).toBeNull();expect(screen.queryByRole('navigation',{name:'Organized events'})).toBeNull();fireEvent.click(screen.getByRole('button',{name:'Resume Draft'}));await screen.findByText('Saved context step');expect(selectEvent).toHaveBeenCalledWith('owned');
});
it('registered but unverified HTTP organizations enter the existing sponsor portal',()=>{
 const portal={organization:{registration_status:'registered_unverified',id:'org'}} as SponsorPortal;
 render(<MemoryRouter><AppProvider providedService={service()}><SponsorShell portal={portal}><h1>Sponsor overview</h1></SponsorShell></AppProvider></MemoryRouter>);
 expect(screen.getByRole('heading',{name:'Sponsor overview'})).toBeInTheDocument();expect(screen.getAllByRole('navigation',{name:'Sponsor Portal'})[0].querySelectorAll('a')).toHaveLength(6);
});
it('maps never invent coordinates for missing, nonfinite or out-of-range locations',()=>{
 const location=(coordinates:unknown)=>({coordinates} as EventLocation);
 expect(validMapCoordinate(location(null))).toBe(false);expect(validMapCoordinate(location({lat:NaN,lng:10}))).toBe(false);expect(validMapCoordinate(location({lat:91,lng:10}))).toBe(false);expect(validMapCoordinate(location({lat:23.99,lng:85.36}))).toBe(true);
});
