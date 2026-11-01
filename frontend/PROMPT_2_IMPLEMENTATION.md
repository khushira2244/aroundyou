# AroundYou — Frontend Prompt 2 implementation

Implemented in the existing `frontend/` React/TypeScript/Vite application. This batch stops at **Actor Requirements confirmed**. The event remains unpublished. No Event Setup, Finalize, Publish, participant, reporting, meeting, blocker or impact screen was implemented.

## Screens, routes and exact visual references

The six user-selected PNGs are retained in `outputs/ui/prompt-2/`, with `references.json` recording their mapping. Existing header, logo, bell/account controls and Prompt 1 routes remain in place. Planning uses the approved five-position progress strip, with Event Setup/Finalize disabled as later modules.

| Route / screen | Selected reference |
|---|---|
| `/events/:eventId/created` — existing success entry, now links to governance and planning | `codex-clipboard-4b24c033-ae9c-42c9-8f09-ed4fb5ff39a2.png` |
| `/events/:eventId/governance` — optional advisory assessment | `codex-clipboard-213e0cab-767d-431f-b58f-ddb34449b67f.png` |
| `/events/:eventId/governance/ticket` — internal ticket, documents and local reminder preferences | `codex-clipboard-5cabbf9c-c67a-43f3-b729-38e05cb41e41.png` |
| `/events/:eventId/planning` — stage sidebar, relative-day Gantt, assumptions, context and separate AI panel | `codex-clipboard-ddf52cd1-0da8-4970-9860-8a44700b5c7a.png` |
| `/events/:eventId/work/:stageId?` — stage-scoped work Gantt, resources, edit proposals and work AI panel | `codex-clipboard-477720bc-45b7-4037-a2f0-417621aa5af8.png` |
| `/events/:eventId/actors` — Event → Stage → Work Group → Role Requirement tree, details, confirmation | `codex-clipboard-260aa957-0d13-476a-8884-40e3f13cc912.png` |
| `/events/:eventId/setup` — accurate incomplete-state fallback only | No Event Setup screen implemented |

The initial architectural/fixture documentation in `docs/architecture/`, `demo/DEMO_DATA_GUIDE.md` and `demo/IMPLEMENTATION_REPORT.md` was reviewed. The original 39-image catalog informed design consistency; the six explicitly selected images govern this batch. Sample Riverside locations, old dates, five-stage plans, permissions and inflated staffing totals in the reference images are not operational data.

## Files created and modified

Created:

- `demo/src/planning.mjs`: bounded planning authoring, deterministic validation, proposal review, confirmations, immutable manifest snapshots, governance metadata operations.
- `demo/tests/planning.test.mjs`: 13 domain/transition tests.
- `frontend/src/services/planning-contracts.ts`: strict typed planning/governance contracts.
- `frontend/src/features/planning/`: `usePlanning.ts`, `PlanningLayout.tsx`, `Timeline.tsx`, `PlanningAssistant.tsx`, `StagePlanning.tsx`, `WorkDesign.tsx`, `ActorRequirements.tsx`, `planning.css`.
- `frontend/src/features/governance/Governance.tsx`.
- `frontend/tests/planning.test.tsx`: complete UI journey and governance document test.
- `frontend/tests/creation-flow.test.tsx`: full Prompt 1 regression including voice review and original explanation preservation.
- This report and the selected-reference manifest/copies.

Modified:

- `demo/src/service.mjs`: route new planning operations through the existing permission/version/transaction-like guard; validate planning state; expose accurate governance status in the creation read.
- `frontend/src/services/contracts.ts`, `mock-adapter.ts`: typed operations on the same persisted creation service; serialize first planning initialization; retain identity checks on restored drafts.
- `frontend/src/app/App.tsx`: replace planning fallback with actual routes; add optional governance, work and actor routes; register only a setup boundary fallback.
- `frontend/src/features/event-creation/Success.tsx`: working next actions, current governance label, preserve success entry after planning starts.
- `frontend/src/features/event-creation/Wizard.tsx`: resume an already-created/planned demo at its success screen rather than attempting draft-only writes.
- `frontend/src/main.tsx`: load planning styles.
- `frontend/vite.config.ts`, `frontend/tests/setup.ts`: serialize DOM test files and allow adequate async query time on this Windows host. No new dependency was installed for Prompt 2.

Connected JSON fixtures and architecture documents were not regenerated or overwritten. Proposed edits live inside the mock service session; immutable confirmed version snapshots preserve prior state. The same browser-local persistence used in Prompt 1 is retained.

## Operations integrated

Existing operations are reused, with bounded Prompt 2 behavior when a planning authoring session is open:

`generateGovernanceAdvisory`, `generateStageProposal`, `reviseStageProposal`, `approvePlanningChat`, `confirmStagePlan`, `readStageWork`, `reviseWorkDesign`, `approveWorkDesign`, `deriveActorRequirements`.

Needed missing mock contracts were added rather than returning fake success:

- `beginPlanning`, `readPlanningState`, `savePlanningDraft`.
- `readGovernanceState`, `startGovernanceTicket`, `recordGovernanceDocument`, `updateGovernanceReminders`.
- `proposeStageEdit`, `proposeAutoArrange`, `approveStageEdit`, `rejectPlanningProposal`.
- `generateWorkConversation`, `confirmWorkDesign`.
- `reviewActorRequirement`, `addActorRequirement`, `confirmActorRequirements`.

Every mutating call still requires an expected session revision. AI proposals additionally capture context, stage and work revisions. Permission checks run before reading or writing organizer planning. A rejected/conflicting/invalid mutation does not replace session state. These guarantees apply to one in-memory mock service, not real PostgreSQL locking.

## Connected behavior and invariants

1. Entry uses the event and context already created in Prompt 1: `event-canary-hill-001`. Raw written/reviewed-transcript explanation and accepted exclusions remain readable.
2. Governance starts at Not Assessed and is optional. Advisory generation creates no legal approval. `GOV-DEMO-001` is an internal demo ticket. Uploaded files are represented by local metadata only and always say Submitted — Not Verified; no file contents are stored remotely or sent to government.
3. The six existing stages S1–S6 and twenty existing blocks W01–W20 remain linked. The maintained front park has no cleanup work. Stage duration, workload, effort, capacity and unknown waste mass remain separate.
4. Gantt bars support native drag to another relative day; stage arrow keys move, Shift+arrows propose duration changes; clicking opens explicit numeric controls. Work duration uses numeric working-hour controls. Dependencies and stage-window violations are shown/rejected. Auto Arrange is a conservative precedence-only proposal, never an optimization or staffing feasibility claim.
5. The stage conversation checks the existing R02 liaison, proposes accountable stage responsibilities without six extra people, and leaves carrying/transport demand unknown. Explicit Apply Changes is required. No actual grants or assignments are created.
6. Stage confirmation is separate from work confirmation and actor confirmation. Confirmed snapshots remain immutable. The initial `plan-v1` is followed by compatible, linked `plan-work-*`, `plan-stages-*` or `plan-actors-*` revision IDs as necessary; stable event/stage/work/role identities are retained. A stage-only confirmation does not claim detailed work or staffing is confirmed.
7. Work edits propose title/outcome, explicit workload/unit, effort, relative day, working-hour duration, dependencies and linked resource quantities. Existing scope/exclusion relationships are retained. A resource quantity is demand, not inventory. Applying work changes invalidates actor derivation/confirmation. Historical manifests are not rewritten.
8. The work conversation targets existing W08/W15/W16 carrying and handover concerns. Bags, trips, safe load, vehicle, pickup, budget and extra headcount remain unknown until supported.
9. Actor derivation requires current confirmed work. Seven original requirement types are reused; their stage/work timing references refresh from current work. After changed work, uncertain headcount assumptions are reset to unknown rather than carried forward as confirmed staffing. R02 remains the explicit one-person liaison responsibility. Organizers can review counts/capabilities or add a proposed, work-linked role.
10. The actor hierarchy exposes each real stage/work group. A role spanning stages is the same requirement, not extra people. Summary counts show requirement types, unknowns and zero assigned people; they do not sum positions into unique participants. Actual permission grants, applications and commitments remain outside this batch.
11. The final confirmation saves the reviewed requirement snapshot and exposes Continue to Event Setup. Its route accurately states that Setup is not implemented. No publication occurs.

## How to test manually

Start the existing local frontend with `cd frontend` then `npm run dev`. Refresh the page after updating source.

- If you already created Canary Hill, use its success page and Continue to Stage Planning. Otherwise complete Prompt 1. Use the existing account dropdown reset only when you want a fresh replay.
- Optional path: Check Governance Requirements → Generate Advisory Guidance → Start Governance Ticket → choose a document type/file → see Submitted — Not Verified. Continue without completing outstanding items.
- Direct path: Continue to Stage Planning → inspect Event Context → Generate Stage Proposal.
- Click S1's Gantt bar, change its duration from one to two relative days, propose and Apply Changes. Volume/effort remain unchanged. Generate a current Stage Proposal after timing edits before confirming.
- Submit the predefined stage message, review its proposal, Apply Changes, then Confirm Stage Plan.
- In Work Design, select stages to inspect W01–W20. Edit W01 duration from two working hours to one, propose and Apply Changes. This preserves its four-section volume and effort while requiring capacity review. Invalid overlaps/dependencies are rejected.
- Submit the work carrying request, review and apply its capacity flags. Confirm Work Design across the linked plan, then Continue to Actor Requirements.
- Derive Actor Requirements → inspect stage/group/role relationships → review a count/capability if appropriate → Confirm Actor Structure.
- Check that Continue to Event Setup opens an accurate boundary message, that publication remains Unpublished, and no person is assigned.

## Verification and limitations

Automated evidence is saved alongside this report: `mock-tests.tap`, `frontend-tests.json`, `build-log.txt`. The frontend tests exercise actual React controls against the real mock adapter, not a second fake UI state store. The Prompt 1 regression covers signup, required-field validation, forward/back navigation, date retention, voice sample editing, rejecting/accepting interpretation, source preservation, review acknowledgments and unpublished creation. Planning tests cover timing edits, stale outputs, dependency failures, work/resource proposals, rederivation, immutable snapshots, role confirmation and optional governance documents.

Provider limitations: AI is fixture-scripted, not arbitrary reasoning; no Meta/Modal request, ASR, media inference, municipal search, legal verification, real document upload, remote notifications or production authentication is present. Backend persistence, distributed concurrency and actual resource-constrained scheduling remain future work. Original fixture quantities remain synthetic estimates.

Visual limitations: the selected images were reviewed and their layouts, blue planning controls, sidebar/Gantt/AI panels and actor hierarchy were implemented. Browser screenshot comparison was not completed: prior local browser verification encountered loopback access restrictions and the Windows Computer Use URL guard. This batch does not claim pixel-perfect or screenshot-verified fidelity. Responsive styles are included; rendered desktop/mobile review remains outstanding. Detailed Gantt links are shown as labeled predecessor IDs rather than the exact curved connector paths from the image. Work editing is bounded to existing blocks; arbitrary split/merge/new-block authoring and unrestricted natural-language AI editing are not claimed. Governance uploads persist metadata only; permission documents are never automatically verified.

STOP: Actor Requirements confirmed. No subsequent product module was built.

### Final verification result

- **62 mock/domain tests passed**, including the original 39 and 10 context tests plus 13 planning tests.
- **10 frontend tests passed**, including the full Prompt 1 regression and both Prompt 2 UI journeys.
- **72 total tests passed; zero failures.** Strict TypeScript check and Vite production build passed.
- The final run uses cached, concurrently read fixture input in the test harness and serial DOM test files; source fixture data remains unchanged. This addresses Windows test-host timing without changing product behavior.
- Additional supporting changes: `frontend/tests/seed.ts` caches and clones immutable test input; `frontend/.gitignore` excludes dependencies, build output and TypeScript build metadata.
