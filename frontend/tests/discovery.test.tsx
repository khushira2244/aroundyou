import {it,expect} from 'vitest';
import {render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {MemoryRouter} from 'react-router-dom';
import {AppProvider} from '../src/app/provider';
import {App} from '../src/app/App';
import {MockAdapter} from '../src/services/mock-adapter';
import {testSeed} from './seed';
async function openDiscovery(){sessionStorage.setItem('aroundyou.demo.identity',JSON.stringify({accountId:'account-organizer-001',label:'Demo Organizer',kind:'personal'}));const service=new MockAdapter(await testSeed());render(<MemoryRouter initialEntries={['/discover']}><AppProvider providedService={service}><App/></AppProvider></MemoryRouter>);await screen.findByRole('button',{name:'Preview Canary Hill Plastic Cleanup'});return service;}
it('shows eleven category markers without inventing geographic coordinates',async()=>{
  const service=await openDiscovery();const layer=screen.getByLabelText('Hazaribagh initiative markers');expect(within(layer).getAllByRole('button')).toHaveLength(11);
  expect(within(layer).getByRole('img',{name:'Pets icon'})).toBeInTheDocument();expect(within(layer).getAllByRole('img',{name:'Environment icon'})).toHaveLength(3);
  expect(within(layer).getByRole('img',{name:'Education icon'})).toBeInTheDocument();expect(within(layer).getByRole('img',{name:'Health icon'})).toBeInTheDocument();
  const events=await service.discover();expect(events.every(e=>e.location.label.includes('Hazaribagh'))).toBe(true);expect(events.filter(e=>e.location.coordinates!==null)).toHaveLength(1);
});
it('category filters update markers and marker clicks open the correct canonical preview',async()=>{
  await openDiscovery();const user=userEvent.setup();await user.click(screen.getByRole('button',{name:'Pets'}));const layer=screen.getByLabelText('Hazaribagh initiative markers');
  const pet=await within(layer).findByRole('button',{name:'Preview Street Animal Feeding & Care Drive'});expect(within(layer).getAllByRole('button')).toHaveLength(1);await user.click(pet);
  expect(await screen.findByRole('dialog',{name:'Street Animal Feeding & Care Drive'})).toBeInTheDocument();
});

