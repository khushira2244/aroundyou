import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Clock3, Sparkles, Plus, ArrowRight, Info, CheckCircle2, ChevronDown } from 'lucide-react';
import { usePlanning } from './usePlanning';
import { PlanningLayout, PlanningLoading } from './PlanningLayout';
import { PlanningAssistant } from './PlanningAssistant';
import { Field } from '../../shared/ui';
import { Modal } from '../../shared/Modal';
export function ActorRequirements() {
    const { state, problem, act, busy, service } = usePlanning(), navigate = useNavigate(), [stageId, setStageId] = useState('S1'), [roleId, setRoleId] = useState('R01'), [editing, setEditing] = useState(false), [adding, setAdding] = useState(false), [title, setTitle] = useState(''), [headcount, setHeadcount] = useState(''), [skills, setSkills] = useState(''), [notice, setNotice] = useState(''), [roleExpanded, setRoleExpanded] = useState(false); if (!state) return <PlanningLoading problem={problem} />; const p = state.planning, stages = Object.values(p.stages), stage = p.stages[stageId] ?? stages[0], latest = state.proposals.filter(v => v.kind === 'actors' && (!v.stage_id || v.stage_id === stage?.id)).at(-1);
    const preview = service?.mode === 'http' && latest?.status === 'proposed' && latest.preview_plan ? latest : undefined;
    // AROUNDYOU UI CHANGE: combine saved roles and each stage's latest pending proposal.
    // Switching stages must not replace other stages' unconfirmed role previews.
    const roleMap = new Map(Object.values(p.roles).map(r => [r.id, r]));
    const latestByStage = new Map<string, typeof latest>();
    state.proposals.filter(v => v.kind === 'actors').forEach(proposal => {
        if (proposal.stage_id) latestByStage.set(proposal.stage_id, proposal);
    });
    // AROUNDYOU UI CHANGE: use only each stage's latest current candidate and its own roles.
    for (const [ownerStage, proposal] of latestByStage) {
        if (proposal?.status !== 'proposed' || !proposal.preview_plan) continue;
        for (const [id, savedRole] of roleMap) {
            if (!savedRole.stage_ids.includes(ownerStage)) continue;
            const otherStages = savedRole.stage_ids.filter(id => id !== ownerStage);
            if (!otherStages.length) roleMap.delete(id);
            else roleMap.set(id, {...savedRole, stage_ids: otherStages});
        }
        for (const proposedRole of proposal.preview_plan.roles) if (proposedRole.stage_ids.includes(ownerStage)) {
            const existing = roleMap.get(proposedRole.id);
            // AROUNDYOU UI CHANGE: one stable shared actor ID, never sum its headcounts.
            const conflict = existing && existing.proposed_headcount !== proposedRole.proposed_headcount;
            roleMap.set(proposedRole.id, existing ? {...proposedRole,
                stage_ids: [...new Set([...existing.stage_ids, ...proposedRole.stage_ids])],
                work_ids: [...new Set([...existing.work_ids, ...proposedRole.work_ids])],
                source_work_ids: [...new Set([...existing.source_work_ids, ...proposedRole.source_work_ids])],
                proposed_headcount: conflict ? null : proposedRole.proposed_headcount,
                headcount_basis: conflict ? 'Conflicting headcounts for this shared actor require review.' : proposedRole.headcount_basis
            } : proposedRole);
        }
    }
    // Handle older actor proposals without a stage_id for the selected-stage preview.
    if (preview && !preview.stage_id) {
        for (const proposedRole of preview.preview_plan?.roles ?? []) roleMap.set(proposedRole.id, proposedRole);
    }
    const roles = Array.from(roleMap.values()).map(r => { const raw = r as typeof r & { effort_person_hours?: number | null; schedule_intervals?: typeof r.commitment.schedule_intervals }; return { ...r, status: r.status ?? 'planned_requirement', delegated_permissions: r.delegated_permissions ?? [], commitment: r.commitment ?? { effort_person_hours: raw.effort_person_hours ?? null, schedule_intervals: raw.schedule_intervals ?? [] } } });
    const stageRoles = roles.filter(r => r.stage_ids.includes(stage?.id)), role = stageRoles.find(r => r.id === roleId) ?? stageRoles[0]; const ready = service?.mode === 'http' ? !!stageRoles.length && (p.work_confirmed || !!p.work_confirmed_stage_ids?.includes(stage?.id)) : !!p.derived_from && p.derived_from.stage_revision === p.stage_revision && p.derived_from.work_revision === p.work_revision && p.work_confirmed;
    // AROUNDYOU UI CHANGE: display global progress without prematurely confirming a stage.
    const actorConfirmedForStage = (id: string) => !!p.actors_confirmed || !!p.actor_confirmed_stage_ids?.includes(id);
    const allActorStagesConfirmed = stages.length > 0 && stages.every(s => actorConfirmedForStage(s.id));
    const allStagesHaveRoles = stages.length > 0 && stages.every(s => roles.some(r => r.stage_ids.includes(s.id)));
    if (!stage) return <PlanningLoading problem="Create stages and work before deriving requirements." />;
    if (!p.work_confirmed && !p.work_confirmed_stage_ids?.length) return <PlanningLoading problem="Confirm Work Design before deriving actor requirements. No stale staffing is presented as confirmed." />;
    // AROUNDYOU UI CHANGE: keep stage proposals visible and collapse details on selection.
    function chooseStage(id: string) { setStageId(id); setRoleExpanded(false); const r = roles.find(x => x.stage_ids.includes(id)); setRoleId(r?.id ?? ''); }
    function review() { if (!role) return; setHeadcount(role.proposed_headcount === null ? '' : String(role.proposed_headcount)); setSkills(role.required_capabilities.join(', ')); setEditing(true) }
    async function acceptPreview() { return !preview || (await act('approveActorProposal', { proposalId: preview.id })) !== undefined }
    // AROUNDYOU UI CHANGE: one event-wide review accepts every current stage candidate atomically.
    async function confirm() {
        const pending = [...latestByStage.values()].filter(v => v?.status === 'proposed');
        if (preview && !preview.stage_id) pending.push(preview);
        const result = await act('confirmActorRequirements', service?.mode === 'http' ? {proposalIds: [...new Set(pending.map(v => v!.id))]} : {});
        if (result) navigate(`/events/${state!.event.id}/setup`);
    }
    async function saveRole() { if (!role) return; if (!(await acceptPreview())) return; const result = await act('reviewActorRequirement', { roleId: role.id, headcount: headcount === '' ? null : Number(headcount), capabilities: skills }); if (result) setEditing(false) }
    return <PlanningLayout state={state} step={3} selectedStage={stage.id} onSelectStage={chooseStage} onSave={() => void act('savePlanningDraft').then(r => { if (r) setNotice('Actor requirements draft saved.') })}><div className="planning-title"><h1>Actor Requirements</h1><span className="demo-pill">{!preview && actorConfirmedForStage(stage.id) ? 'Confirmed' : 'In Progress'}</span><span className="actor-info"><Info size={17} />Planning structure only — no people assigned</span></div><p className="muted">Roles and capabilities derive from confirmed Work Design. One eligible person may cover compatible responsibilities.</p><div className="button-row"><button className="button secondary" disabled={busy || (service?.mode === 'http' && !p.work_confirmed && !p.work_confirmed_stage_ids?.includes(stage.id))} onClick={() => void act('deriveActorRequirements', service?.mode === 'http' ? { stageId: stage.id } : {}).then(r => { if (r) setNotice('Requirements derived from the current confirmed work revision. Review assumptions before confirming.') })}>{service?.mode === 'http' ? 'Generate Actor Requirements' : 'Derive Actor Requirements'}</button><small>Work revision {p.work_revision} · {ready ? 'Current derivation' : 'Not yet derived / reconciliation required'} · {stages.filter(s => actorConfirmedForStage(s.id)).length}/{stages.length} stages confirmed</small></div><div className="actor-layout"><div className="actor-main-column">{/* AROUNDYOU UI CHANGE: workforce contains human actors only; stages select generation in the sidebar. */}
<section className="card actor-tree actor-workforce" aria-label="Event workforce">
    <h2>Event workforce</h2>
    <p className="muted">All generated roles and teams remain visible across stages. Counts describe required people, not assignments.</p>
    <p className="workforce-capacity">Planned volunteers: <strong>{state.event.creation_details?.expectedVolunteers || 'Not supplied'}</strong> · Attendees: <strong>{state.event.creation_details?.expectedAttendees || 'Not supplied'}</strong> (not counted as workers)</p>
    <p className="field-note">Branches show stage membership, not organizational reporting. Shared actor IDs are marked across their stages; repeated nodes do not represent additional people.</p>
    {/* AROUNDYOU UI CHANGE: one root connects every saved stage to its own actor requirements. */}
    <div className="workforce-tree-scroll" tabIndex={0} aria-label="Scrollable workforce tree"><div className="workforce-tree-diagram">
        <div className="workforce-root">Event Workforce<small>Required human roles and teams</small></div>
        <ul className="workforce-branches workforce-stage-branches" aria-label="Event workforce stages">{stages.map((savedStage, index) => {
            const branchRoles = roles.filter(r => r.stage_ids.includes(savedStage.id));
            return <li key={savedStage.id} className="workforce-stage-branch">
                <div className="workforce-stage-node"><strong>Stage {index + 1}</strong><span>{savedStage.title}</span></div>
                <ul className="workforce-actor-branches" aria-label={`Actors for ${savedStage.title}`}>
                    {branchRoles.length === 0 ? <li className="workforce-branch"><div className="workforce-stage-empty"><Plus size={22} aria-hidden="true"/><small>No actors generated yet</small></div></li> : branchRoles.map(r => {
                        const pending = [...latestByStage.values()].some(v => v?.status === 'proposed' && v.preview_plan?.roles.some(candidate => candidate.id === r.id)) || !!(preview && !preview.stage_id && preview.preview_plan?.roles.some(candidate => candidate.id === r.id));
                        const confirmed = !pending && r.stage_ids.length > 0 && r.stage_ids.every(actorConfirmedForStage);
                        return <li key={r.id} className="workforce-branch"><button type="button" data-actor-id={r.id} className={'workforce-node' + (role?.id === r.id ? ' selected' : '')} aria-pressed={role?.id === r.id} onClick={() => { setRoleId(r.id); setRoleExpanded(true); if (!r.stage_ids.includes(stage.id) && r.stage_ids[0]) setStageId(r.stage_ids[0]); }}>
                            <Users size={23} aria-hidden="true"/>
                            <strong>{r.title}</strong>
                            <span className="workforce-headcount">{r.proposed_headcount === null ? 'Headcount not established' : `${r.proposed_headcount} ${r.proposed_headcount === 1 ? 'person' : 'people'} required`}</span>
                            {r.stage_ids.length > 1 && <small className="workforce-shared">Shared actor · {r.id}</small>}
                            <small className="demo-pill">{confirmed ? 'Confirmed requirement' : 'Proposed requirement'}</small>
                        </button></li>;
                    })}
                </ul>
            </li>;
        })}</ul>
    </div></div>
    {/* AROUNDYOU UI CHANGE: empty tree has one centered placeholder, never fake actors. */}
    {!roles.length && <div className="workforce-empty"><Plus size={26} aria-hidden="true"/><p>No actor requirements generated yet.</p><button className="button secondary compact" disabled={busy || !(p.work_confirmed || p.work_confirmed_stage_ids?.includes(stage.id))} onClick={() => setAdding(true)}><Plus size={16}/> Add Role</button></div>}
</section>{/* AROUNDYOU UI CHANGE: no generated roles means a compact genuine empty state. */}
{!role ? (roles.length > 0 ? <section className="card actor-empty-state" aria-label="No role requirements">
    <Plus className="actor-empty-icon" size={22} aria-hidden="true" />
    <p>No actor requirements generated yet.</p>
    <button className="button secondary compact" disabled={busy || !(p.work_confirmed || p.work_confirmed_stage_ids?.includes(stage.id))} onClick={() => setAdding(true)}><Plus size={16} /> Add Role</button>
</section> : null) : <section className="card actor-detail actor-selected-detail" aria-label="Selected role requirement">
    {/* AROUNDYOU UI CHANGE: only this role-detail card is an accordion; other sections stay unchanged. */}
    <button type="button" className="actor-detail-toggle" aria-expanded={roleExpanded} aria-controls="actor-role-detail-content" onClick={() => setRoleExpanded(x => !x)}>
        <span className="actor-detail-toggle-text"><span className="source-label">Role Requirement · {role.id}</span><strong>{role.title}</strong><small>Required: {role.proposed_headcount ?? 'Unknown'} · {actorConfirmedForStage(stage.id) && !preview ? 'Confirmed' : 'Proposed'}</small></span>
        <ChevronDown size={20} className={roleExpanded ? 'actor-detail-chevron expanded' : 'actor-detail-chevron'} aria-hidden="true" />
    </button>
    {roleExpanded && <div id="actor-role-detail-content" className="actor-detail-content"><p className="muted">Stages: {role.stage_ids.join(', ')}</p><div className="actor-numbers"><div><Users size={20} /><small>Required count</small><strong>{role.proposed_headcount ?? 'Unknown'}</strong></div><div><Clock3 size={20} /><small>Commitment effort</small><strong>{role.commitment.effort_person_hours ?? 'Unknown'}</strong><small>person-hours</small></div></div><h3>Responsibility &amp; source work</h3><ul>{role.work_ids.map(w => <li key={w}>{w} · {p.work[w]?.title}</li>)}</ul><p>{role.responsibilities?.join(' · ')}</p><p>{role.coordination_needs?.join(' · ')}</p><p>{role.resource_responsibilities?.join(' · ')}</p><h3>Key capabilities needed</h3><div className="skill-tags">{role.required_capabilities.map(c => <span key={c}>{c}</span>)}</div><h3>Timing &amp; capacity constraints</h3><ul>{role.commitment.schedule_intervals.map((s, i) => <li key={i}>Day {s.start_day}, {String(Math.floor(s.start_minute / 60)).padStart(2, '0')}:{String(s.start_minute % 60).padStart(2, '0')}–{String(Math.floor(s.end_minute / 60)).padStart(2, '0')}:{String(s.end_minute % 60).padStart(2, '0')}</li>)}</ul><p>{role.capacity_assumptions.join(' ')}</p>{role.reconciliation_note && <p className="notice">{role.reconciliation_note}</p>}<h3>Safety &amp; permission boundary</h3><p>{role.safety_considerations.join(' · ')}</p><p>Permission grants and assignments require separate human actions. None are created here.</p><div className="button-row"><button className="button secondary compact" disabled={!ready || busy} onClick={review}><Sparkles size={16} />Edit Requirement</button><button className="button secondary compact" disabled={!ready || busy} onClick={() => setAdding(true)}><Plus size={16} />Add Role</button></div></div>}
</section>}</div><aside className="card actor-ai-panel">{service?.mode === 'http' && <PlanningAssistant embedded backend mode="actors" busy={busy} history={state.proposals.filter(v => v.stage_id === stage.id)} proposal={state.proposals.filter(v => v.kind === 'planning_chat' && v.stage_id === stage.id).at(-1) ?? preview} onAsk={message => void act('askPlanningQuestion', { message, stageId: stage.id, mode: 'actors' })} onSend={message => void act('deriveActorRequirements', { message, stageId: stage.id })} onApprove={() => { }} onReject={proposalId => void act('rejectPlanningProposal', { proposalId })} />} </aside></div>{notice && <p className="notice" role="status">{notice}</p>}{allActorStagesConfirmed && !preview && <div className="notice"><CheckCircle2 size={18} />Actor Requirements confirmed for {state.active_plan_id}. The event remains unpublished.</div>}<div className="planning-bottom"><small>{state.active_plan_id} · {state.publication} · {!allStagesHaveRoles ? 'Generate or add requirements for every stage before confirming.' : 'Review all stages, then confirm the complete actor structure once.'}</small>{allActorStagesConfirmed && !preview ? <button className="button blue" onClick={() => navigate(`/events/${state.event.id}/setup`)}>Continue to Event Setup <ArrowRight size={17} /></button> : <button className="button blue" disabled={busy || !p.work_confirmed || !allStagesHaveRoles || [...latestByStage.values()].some(v => v?.status === 'proposed' && !!v.violations?.length)} onClick={() => void confirm()}>Confirm Actor Requirements <ArrowRight size={17} /></button>}</div>{editing && role && <Modal title="Review actor requirement" onClose={() => setEditing(false)}><h2>Review {role.title}</h2><p>Keep unknown quantities blank. Changing a requirement never assigns a person.</p><Field label="Proposed headcount (blank = unknown)"><input type="number" min={0} max={1000} value={headcount} onChange={e => setHeadcount(e.target.value)} /></Field><Field label="Capabilities (comma-separated)"><textarea rows={3} value={skills} onChange={e => setSkills(e.target.value)} /></Field><button className="button blue" disabled={busy} onClick={() => void saveRole()}>Save Reviewed Requirement</button></Modal>}{adding && <Modal title="Add role requirement" onClose={() => setAdding(false)}><h2>Add Role Requirement</h2><p>Source: {stage.title} → {state.work_groups.find(g => g.stage_id === stage.id)?.title}. Headcount starts unknown; no person is assigned.</p><Field label="Role requirement title"><input value={title} onChange={e => setTitle(e.target.value)} /></Field><button className="button blue" disabled={busy || !title.trim()} onClick={() => void acceptPreview().then(ok => { if (ok) return act('addActorRequirement', { stageId: stage.id, title }) }).then(r => { if (r) { setAdding(false); setTitle('') } })}>Add Proposed Requirement</button></Modal>}</PlanningLayout>;
}
