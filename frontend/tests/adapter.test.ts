import {describe,it,expect} from 'vitest';
import {MockAdapter} from '../src/services/mock-adapter';
import {DEFAULT_FORM,validateStep} from '../src/features/event-creation/model';
import {testSeed} from './seed';
const identity={accountId:'account-organizer-001',label:'Demo Organizer',kind:'personal' as const};
describe('typed adapter and validation',()=>{
  it('reads eleven fixtures and filters without component-local event arrays',async()=>{const a=new MockAdapter(await testSeed());expect(await a.discover()).toHaveLength(11);expect(await a.discover('Education')).toHaveLength(1);expect((await a.profile('event-canary-hill-001')).tabs).toHaveLength(8)});
  it('persists edited drafts through service and reloads the same event identity',async()=>{const seed=await testSeed(),a=new MockAdapter(seed);a.setIdentity(identity);await a.startCreation();await a.saveDraft(1,{...DEFAULT_FORM,title:'Edited title'});const b=new MockAdapter(seed);expect((await b.startCreation()).runtime.draft.title).toBe('Edited title');expect((await b.creation()).event.id).toBe('event-canary-hill-001')});
  it('keeps online events unpinned even if a previous location was selected',async()=>{const a=new MockAdapter(await testSeed());await a.startCreation();await a.saveDraft(1,{...DEFAULT_FORM,format:'online',coordinates:{lat:24,lng:85}});const s=await a.creation();expect((s.runtime.draft.location as {coordinates:unknown}).coordinates).toBeNull()});
  it('requires basics, chronological schedule and final acknowledgments',()=>{expect(validateStep(1,DEFAULT_FORM)).toHaveProperty('title');expect(validateStep(2,{...DEFAULT_FORM,startDate:'2026-11-10',endDate:'2026-11-09'})).toHaveProperty('endDate');expect(validateStep(4,DEFAULT_FORM)).toHaveProperty('confirmAccuracy')});
  it('accepts context without resolving unknown quantities or generating plans',async()=>{const a=new MockAdapter(await testSeed());const s=await a.startCreation();await a.saveIntent(s.sample_intent,'written');const p=await a.suggestUnderstanding();expect(p.provenance.model_execution).toBe(false);await a.reviewUnderstanding(p.id,'accept');expect((await a.creation()).context.approved_interpretation?.unknowns.length).toBeGreaterThan(0)});
});
