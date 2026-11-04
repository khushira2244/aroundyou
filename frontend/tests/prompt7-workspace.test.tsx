import {afterEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {RecoveryWorkspace} from '../src/features/recovery/RecoveryWorkspace';
import {Header} from '../src/app/layout';
import {HttpAdapter} from '../src/services/http-adapter';
const mock=vi.hoisted(()=>({useApp:vi.fn()}));vi.mock('../src/app/provider',()=>({useApp:mock.useApp}));
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.unstubAllEnvs()});
it('restores exact blocker workspace and keeps local review distinct from activation',async()=>{
 let hub={id:'hub',revision:2,base_plan_id:'plan',status:'recovery_planning',stale:false,nodes:[{key:'work:w',original:{id:'w',scope:'Original'},patch:{},status:'needs_review'}],people:[],alternative_id:null,communication:null};
 const command=vi.fn(async(op:string,body:Record<string,unknown>)=>{if(op==='local-review'){hub={...hub,revision:3,nodes:[{...hub.nodes[0],status:'confirmed_local_change',patch:body.patch as object}]};return hub}return hub});
 mock.useApp.mockReturnValue({service:{recoveryCommand:command}});
 render(<MemoryRouter initialEntries={['/events/e/manage/blockers?workspace=hub&issue=i&node=work:w']}><RecoveryWorkspace eventId="e" issueId="i" planId="plan"/></MemoryRouter>);
 await screen.findByText('work:w');expect(command).toHaveBeenCalledWith('workspace',{eventId:'e',workspaceId:'hub'});
 fireEvent.change(screen.getByLabelText('Proposed fields only (JSON)'),{target:{value:'{"scope":"Proposed only"}'}});fireEvent.change(screen.getByLabelText('Operational review note'),{target:{value:'Human local review'}});fireEvent.click(screen.getByRole('button',{name:'confirmed local change'}));
 await waitFor(()=>expect(command).toHaveBeenCalledWith('local-review',expect.objectContaining({eventId:'e',workspaceId:'hub',expected_revision:2,node_key:'work:w',patch:{scope:'Proposed only'}})));
 expect(command.mock.calls.some(([op])=>['activate','ai'].includes(op))).toBe(false);fireEvent.click(screen.getByText('Return to Blocker'));expect(screen.getByText('Submit Local Reviews for Overall Approval')).toBeTruthy();
});
it('sponsor header omits personal My Events in both live and demo modes',()=>{
 mock.useApp.mockReturnValue({identity:{kind:'sponsor',label:'Sponsor'},service:{demoAccounts:()=>[]},logout:vi.fn()});
 vi.stubEnv('VITE_AROUNDYOU_MODE','http');const view=render(<MemoryRouter><Header/></MemoryRouter>);expect(screen.queryByText('My Events')).toBeNull();view.unmount();vi.stubEnv('VITE_AROUNDYOU_MODE','demo');render(<MemoryRouter><Header/></MemoryRouter>);expect(screen.queryByText('My Events')).toBeNull();
});
it('memory review sends memory version rather than event version; targeted notices use authenticated reads',async()=>{
 const calls:{path:string;init:RequestInit}[]=[];vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{calls.push({path:new URL(url).pathname,init});return new Response(JSON.stringify({data:{items:[]}}),{status:200})}));
 const adapter=new HttpAdapter({baseUrl:'http://localhost:8001',token:()=>null,eventId:()=> 'e'});
 await adapter.recoveryCommand('reviewMemory',{eventId:'e',memoryId:'m',version:7,expected_revision:2,reviewed_digest:'a'.repeat(64),decision:'publish'});expect((calls[0].init.headers as Record<string,string>)['If-Match']).toBe('7');expect(calls[0].path).toBe('/v1/events/e/memory/m/review');
 await adapter.readNotifications();expect(calls.at(-1)?.path).toBe('/v1/notifications');expect(calls.at(-1)?.init.credentials).toBe('include');
});
