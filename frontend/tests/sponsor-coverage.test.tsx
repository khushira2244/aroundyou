import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {SponsorRegistration} from '../src/features/sponsor-registration/SponsorRegistration';
const mock=vi.hoisted(()=>({act:vi.fn(async()=>({saved:true}))}));
vi.mock('../src/app/provider',()=>({useApp:()=>({service:{mode:'http'}})}));
vi.mock('../src/features/sponsor-dashboard/useSponsor',()=>({useSponsor:()=>({act:mock.act,busy:false,problem:'',portal:{organization:{id:'org'},registration:{draft:{name:'Community partner',type:'Business',description:'Local support',contact_name:'Contact',position:'Coordinator',email:'contact@example.com',phone:'1234567890',city:'Hazaribagh',country:'India',focus:['Environment'],capabilities:['funding'],coverage:[],recognition:{show_profile:false,show_logo:false,show_contributions:false,private_contact:true}}}}})}));
vi.mock('../src/features/sponsor-dashboard/SponsorShell',()=>({SponsorShell:({children}:{children:React.ReactNode})=><main>{children}</main>,SponsorLoading:()=>null}));
it('Next saves a typed locality without Add location and removes the synthetic organization label',async()=>{
 render(<MemoryRouter initialEntries={['/sponsor/register/2']}><Routes><Route path='/sponsor/register/:step' element={<SponsorRegistration/>}/></Routes></MemoryRouter>);
 expect(screen.queryByText(/Synthetic organization/)).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Add city or region'),{target:{value:'  Hazaribag  '}});
 fireEvent.click(screen.getByRole('button',{name:'Next: Review & Create'}));
 await waitFor(()=>expect(mock.act).toHaveBeenCalledWith('saveOrganizationDraft',{profile:expect.objectContaining({coverage:['Hazaribag'],focus:['Environment'],capabilities:['funding']}),step:3}));
 await screen.findByRole('heading',{name:'Review & Create',level:1});
 expect(screen.queryByRole('alert')).not.toBeInTheDocument();
 expect(screen.getByText('Hazaribag')).toBeInTheDocument();
});
