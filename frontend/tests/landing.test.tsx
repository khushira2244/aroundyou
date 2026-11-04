import {it,expect} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {MemoryRouter,useLocation} from 'react-router-dom';
import {Landing} from '../src/features/landing/Landing';
import {App} from '../src/app/App';
import {AppProvider} from '../src/app/provider';
import type {AroundYouService} from '../src/services/contracts';

function CurrentRoute(){return <output aria-label="Current route">{useLocation().pathname}</output>}
it('shows the approved landing sections and working section anchors',()=>{
 render(<MemoryRouter><Landing/></MemoryRouter>);
 expect(screen.getByRole('heading',{level:1})).toHaveTextContent('Discover. Join. Organize.Support. Together.');
 for(const [label,id] of [['How it Works','how-it-works'],['Features','features'],['Communities','communities'],['About','about']]){
  expect(screen.getByRole('link',{name:label})).toHaveAttribute('href','#'+id);
  expect(document.getElementById(id)).not.toBeNull();
 }
 expect(screen.getByRole('link',{name:'Get in touch'})).toHaveAttribute('href','mailto:khushboorani@gmail.com');
});
it.each([['Sign Up','/signup'],['Sign In','/signin'],['Get Started','/signup'],['Explore Events','/discover']])('connects %s to its existing route', (label,path)=>{
 render(<MemoryRouter><Landing/><CurrentRoute/></MemoryRouter>);
 fireEvent.click(screen.getByRole('link',{name:label}));
 expect(screen.getByLabelText('Current route')).toHaveTextContent(path);
});
it('root route renders the landing page and signup retains both existing account choices',async()=>{
 const service={mode:'demo',demoAccounts:()=>[],setIdentity:()=>{}} as unknown as AroundYouService;
 render(<MemoryRouter initialEntries={['/']}><AppProvider providedService={service}><App/></AppProvider></MemoryRouter>);
 expect(screen.getByRole('heading',{level:1})).toHaveTextContent('Discover. Join. Organize.');
 fireEvent.click(screen.getByRole('link',{name:'Sign Up'}));
 expect(await screen.findByRole('button',{name:/Personal Account/})).toBeInTheDocument();
 expect(screen.getByRole('button',{name:/Sponsor \/ Organization/})).toBeInTheDocument();
});

it('How It Works cards change the explanation without leaving the landing page',()=>{
 render(<MemoryRouter><Landing/><CurrentRoute/></MemoryRouter>);
 const names=['Discover or create an event','Define roles, stages and support needs','Join, volunteer, or support','Coordinate execution and updates','Review outcomes and learn'];
 for(const name of names){const button=screen.getByRole('button',{name:new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))});fireEvent.click(button);expect(button).toHaveAttribute('aria-pressed','true');expect(document.getElementById('landing-step-detail')?.querySelector('h3')).toHaveTextContent(name);expect(screen.getByLabelText('Current route')).toHaveTextContent('/')}
});
