# AroundYou — minimum backend data model for the current frontend

Reviewed 31 October 2026. **Proposed logical/physical model, not implemented schema or migrations.** Read with [the contract report](frontend-backend-contract-and-plan.md) and [API catalogue](backend-api-contract-catalogue.md).

The aim is the smallest defensible model for all existing screen families, implemented incrementally. It is not a directive to create every table in the first migration. No table receives generic public CRUD merely because it is listed. Query projections (My Events, organizer dashboard, public profile, participant workspace, sponsor portfolio, aggregate charts) do not own duplicate operational records.

## Storage strategy

Use relational records for identity, permissions, accepted obligations, ledgers, reports and decisions. Use **strictly schema-validated JSON documents for bounded planning drafts and immutable confirmed plan snapshots**, matching the existing coherent-plan frontend contract. This avoids dozens of premature stage/work/requirement revision join tables while retaining stable identifiers and exact version manifests.

A confirmed `plan_versions.content` document contains separately typed stages, optional groups, work, two distinct dependency graphs, actor requirements, resource requirements, zones/exclusions and per-item revision references. Work IDs that cross into assignments/reports/ledgers additionally have relational identity rows. No arbitrary EAV dictionary or provider blob becomes authoritative content.

**Tradeoff:** PostgreSQL foreign keys cannot enforce references inside JSON. Deterministic validators must check every embedded reference, event ownership, cycle, unit, parent-child compatibility and manifest digest in the same transaction that confirms/activates the document. Lock the event aggregate during these small writes. If large-event cross-item queries/concurrent designers later justify it, normalize stage/work/requirement revision tables behind the same repository/DTO contract. Do not prematurely maintain both a JSON source of truth and separate mutable child tables.

All IDs are opaque strings at the transport boundary. Server-generated IDs should be collision-resistant; imported fixture aliases may retain existing IDs. IDs never encode permission. Do not copy the fixture validator's unnecessary requirement that IDs across unrelated tables are globally unique.

## Common column and constraint rules

- Each scoped row has `event_id` or `organization_id` and an owner-derived scope. A supplied foreign ID must belong to that same scope. Use composite uniqueness/FKs for cross-row event references where possible.
- Mutable aggregate rows have integer `version`, created/updated timestamps and authors. Original documents, confirmed plans, submitted report revisions, decisions and ledger effects are append-only. Corrections reference prior records rather than erasing them.
- `created_by`/`approved_by` come from authenticated context. Client `confirm` is evidence of intent, not authorization. Timestamps use server time; preserve original occurrence time separately from received time.
- Monetary/quantity arithmetic is decimal with explicit currency/unit. Unknown remains null; no automatic zero. Current demo restricts some inventory actions to positive whole units; support fractional units only after defining their precision and conversion rules.
- UTC instants and IANA timezone are retained alongside original relative-day terms. A provisional unanchored schedule cannot prove cross-event availability; anchoring can require renewed consent. Half-open intervals avoid boundary conflicts.
- Unique idempotency references cover creates, receipts, consumption/returns, commitment decisions and activation. Prevent duplicate effect by business identity as well as HTTP key.
- Aggregate counters are queries, not editable totals. Public chart records contain no raw individual answers.

## 1. Identity and event foundation

| Table | Purpose / key fields | Important relationships | Version / audit and creation timing |
|---|---|---|---|
| `users` | App identity: id, external_auth_subject unique, display_name, status, synthetic/demo provenance | Grants, memberships, authored/assigned records | Profile version and audit; no plaintext credentials or client-chosen identity. First read slice. |
| `organizations` | Sponsor identity/profile/registration: id, profile_json, registration_status, recognition_json, version | Memberships, offers, branding assets | Preserve reviewed profile revision/recognition basis; `verified` requires separate supported verification. Add with sponsor flow. |
| `organization_memberships` | Who can act for an organization: organization_id, user_id, permissions, status | FKs to organization/user | Unique organization+user; explicit grant/revocation audit. Sponsor authority is not participant/organizer authority. |
| `event_grants` | Event organizer and explicit scoped delegation: event_id, user_id, permission, stage_refs/work_refs, granted_by, expires_at/revoked_at | Users/events; stage refs validated against plan | Version, explicit reason/decision and revocation history. Role title alone cannot create row. First slice seeds organizer; delegation later. |
| `events` | Stable initiative identity: id, creator_id, draft_form_json, draft_step, brief_json, lifecycle, active_context_revision_id, active_plan_id, current_publication_id, version | Context, plans, releases, applications, stock, blockers | Draft and explicit created_unpublished state share durable ID. Creation is not publication. Mutable brief changes generate context/version consequences. First slice. |
| `event_context_revisions` | Original explanation and reviewed interpretation: id, event_id, sequence, original_text, source_kind, source_asset_id, interpretation_json, review_decision_id, supersedes_id, content_hash | Event/media/decision; cited by plan and AI context | Original input append-only; reviewed correction is new revision. Never replace original with generated summary. |

`event_grants` and `organization_memberships` are separate because the same human can organize an event, participate in another and represent an organization. Do not create separate global ParticipantUser/SponsorUser/OrganizerUser databases.

## 2. Planning and publication

| Table | Purpose / key fields | Important relationships | Version / audit and creation timing |
|---|---|---|---|
| `planning_drafts` | Mutable authoring document: id, event_id, base_plan_id, context_revision_id, content_json, stage_revision, work_revision, actor_revision, confirmation flags, derived_from, version | Event/context; reusable typed item IDs; pending proposal references | Expected-version writes; parent scope/timing edits mark incompatible children stale. One current draft per event is sufficient initially. |
| `plan_versions` | Immutable confirmed/candidate plan document: id, event_id, parent_id, status, content_json, item_revision_map, source_versions, digest, candidate_terms_digest, approval_id, activation_at | Event active-plan pointer; context; review; assignments/reports retain historical plan FK | Candidate content freezes when reviewed; editing creates a successor/digest, invalidating approvals/consents. Confirm/activate atomically. Unlimited sequential IDs, not `plan-v2` constant. |
| `work_items` | Stable cross-flow work identity only: id, event_id, created_at, retired_at | Referenced by execution/reports/assignments/reservations; versioned title/stage/scope live in plan document | No second mutable schedule/status here. Retire, do not delete referenced work. Index event+id. |
| `work_execution` | Current operational projection: work_id, event_id, applicable_plan_id, execution_status, version, completion_decision_id, hold_reason/ref | Work identity and authorized review/blocker/plan decision | Optimistic versions and append-only decisions; changing the plan cannot erase completed work. Stage completion is an explicit review decision over required work, not a duplicated editable counter. |
| `event_setup_revisions` | Setup/question schema/visibility/communications/draft invites/partner discussions: id, event_id, source_plan_id, status, configuration_json, version, digest | Publication and application schema/version refs; asset/contact references | Draft mutable; released revision immutable. Tags/questions archive IDs; new config requires reviewed new revision. No separate table for every boolean. |
| `publications` | Exact released profile binding: id, event_id, plan_version_id, setup_revision_id, visibility, editorial_revision, status, reviewed_digest, published_at, approved_by | Event current publication pointer; public content refs | New release for visibility/config/plan changes; do not mutate the old released configuration as current demo profile editing does. Unique active release/event. |
| `published_roles` | Recruitment opportunity reference: id, event_id, publication_id, plan_version_id, role_requirement_ref, status | Role ref inside that plan; applications/candidates cite opportunity | No independent headcount or invented filled-person totals; close/suspend/archive explicitly when plan changes. |

### Planning entities inside each typed document

These are domain entities with stable IDs and explicit item revisions, **not seven additional SQL tables initially**.

| Entity | Key fields / purpose | Relationships / invariant | Version consideration |
|---|---|---|---|
| Stage | id, title, purpose/outcomes, relative window, volume/effort/duration, capacity assumptions | Event phase; work belongs to a valid stage; stage dependencies are distinct from work dependencies | Editorial rename need not regenerate work; scope/window change requires compatibility checks. |
| Work Group | id, stage_id, title | Optional organizational grouping; not a team of accepted people | Store within snapshot; default group allowed; no new mandatory UI approval tier. |
| Work Block | id, stage/group IDs, scope/outcome, zones, volume/unit, effort assumptions, duration, schedule, skills, conditions, evidence requirements | Independently schedulable/reportable item; linked to requirements and dependencies | Stable ID in `work_items`; plan-specific body/revision immutable. |
| Work Dependency | predecessor_work_id, successor_work_id, kind=finish_to_start, lag | Same event/plan, resolves to real items, no self edge/cycle; cross-stage permitted | Edges stored with plan; edits require affected-scope analysis. No cross-event graph edges initially. |
| Actor Requirement | id, source work refs, skills/capabilities, planned positions nullable, peak coverage basis, timing windows, safety constraints | Demand, not person/assignment/grant; unknown capacity stays unknown | Derived_from stage/work revisions; material change revalidates offers/commitments. |
| Resource Requirement | id, work refs, resource kind, quantity/unit, timing/conditions, substitution constraints | Demand, not pledge/stock; overlapping reusable demand uses peak need | Old demand remains with its plan; revisions reconcile reservations/obligations. |
| Zone / scope exclusion | id, label, included flag, location provenance, exclusion/condition | General-purpose venue/activity scope, not hard-coded Canary Hill park rules | Retain original scope source; changes reviewed with affected work. |

Do not create a separate database row per rendered Gantt bar, summary card, graph arrow or aggregate chart.

## 3. Participation and decisions

| Table | Purpose / key fields | Important relationships | Version / audit and timing |
|---|---|---|---|
| `applications` | One active event/account request: id, event_id, user_id, status, current_revision_id, wizard_step, reviewed_steps, submitted_plan_id, approved_plan_id, approved_role_refs, version | Applicant, published roles, current revision, review decisions | Partial unique active application(event,user); draft creation is not submission. Approval creates no assignment. |
| `application_revisions` | Original private answers/availability/consent: id, application_id, sequence, original_answers_json, availability_intervals, config_revision_id, insight_consent, source/review state, hash | Application, configuration, optional clarification/alternative requests | Append-only original revisions; keep historical schema and terms. Inline current clarification/alternative entries can start as typed bounded JSON with stable IDs; split into tables only if needed. |
| `assignments` | Offered/accepted exact responsibility: id, event_id, user_id, application_id, role_ref, work_refs, plan_version_id, schedule_json, terms_digest, status, version | Source app/requirement/work; accepted consent decisions | One intended offer per exact candidate/terms; no duplicate active work offer. Acceptance rechecks locked capacity, actor availability and live work status. |
| `assignment_decisions` | Original and changed-plan consent: id, assignment_id, candidate_plan_id nullable, terms_digest, decision, user_id, created_at, idempotency_ref | Assignment and optional change candidate | Append-only and unique for subject+terms+decision semantics; refusal is valid, never auto-accept. Existing acceptance history is not overwritten by replan. |
| `review_decisions` | Explicit authorized reviews: id, event_id, target_kind/id/version/hash, decision, reviewer_id, authority_scope, note, evidence_refs, created_at | Application/capability/report/completion/measurement/proposal/follow-up targets | Immutable exact-target decision. Target kind is a closed typed union with owner validation, not an arbitrary mass-update capability. Can retain finalization review here. |

A checked assignment candidate can be represented by a pending typed proposal artifact with application/plan/work versions and digest; no fixture `assignment_templates` table is required in production. The organizer dropdown receives server-issued candidates. Candidates do not reserve capacity or authorize acceptance until the owning assignment transaction rechecks all invariants.

Availability is private original input in application revisions. A standalone availability calendar is not needed yet; actor-overlap validation loads accepted assignments across events plus the relevant declared intervals. Persist actual anchored start/end instants when available so database range constraints/locks can enforce real overlap. Do not claim cross-event date feasibility for unanchored relative commitments.

## 4. Resources and sponsorship

| Table | Purpose / key fields | Important relationships | Version / audit and timing |
|---|---|---|---|
| `inventory_lots` | Physical usable stock identity: id, owner/event scope, requirement_ref or resource_type, kind consumable/reusable, unit, opening_quantity, version | Movements/reservations; sponsor physical receipt references | Opening balances have source/basis. No pledge or sponsor-reported delivery increments usable stock. Lock during ledger/reservation writes. |
| `resource_movements` | Append-only receipt/consumption/correction/custody effects: id, lot_id, event_id, kind, quantity, signed stock delta, unit, source_offer/report/decision IDs, canonical_reference, correction_of | Lot; verified original receipt/report; optional equipment loan | Unique receipt/effect identity and payload hash; corrections reverse/reference prior entry. Do not credit the same physical delivery in two ledgers. |
| `reservations` | Allocation against work/time: id, event_id, lot_id or verified non-stock capacity reference, work_refs, plan_version_id, quantity, remaining, interval?, status, version | Plan demand and authoritative source | Prevent free stock <0 and overlapping reusable capacity over-allocation. Changes release/retain/revise explicitly on activation. Non-stock booking only when real capacity exists. |
| `equipment_loans` | Custody/issue-return: id, reservation_id, assignee/report ref, quantity, returned_quantity, issue/return decisions | Reusable lot/reservation/movements | Issued is not consumed. Return <= outstanding; maintain partial returns and idempotent reference. |
| `sponsor_offers` | Organization obligation: id, organization_id, representative_id, event_id, resource_ref, support_type, offered_terms_json, quantity/unit, status, version | Membership; need in plan; acceptance decision | Draft/submitted/accepted/withdrawn/rejected separate; accepted changes need an amendment, not silent overwrite. |
| `sponsor_fulfillment_reports` | Reported delivery/service/funding and review: id, offer_id, quantity/unit, reference, original_note, evidence_refs, status, verification_decision_id | Offer, media, human decision, optional physical receipt movement | A reported fulfillment never makes stock available. Physical verification points to one receipt; services/funding/expertise use separate non-stock verification, not fake inventory or cash transactions. |

Resource requests visible in Organizer Resources can initially be typed `content_entries(kind=resource_request)` with requirement ref/quantity/unit/reason/status; they are requests, not a procurement or accounting subsystem. A separate `resource_requests` table is optional when that workflow grows.

Services/facilities are quantities/availability windows only when sourced and verified. Funding amounts/estimated values do not constitute payment processing. Do not add bank accounts, donations, purchase orders, invoices or a general ledger without a corresponding approved workflow. If real non-stock interval capacity/reservation is needed for the first vertical slice, add a typed capacity record then; the current frontend mainly records offers/verified fulfillment.

## 5. Execution, evidence and blocker recovery

| Table | Purpose / key fields | Important relationships | Version / audit and timing |
|---|---|---|---|
| `execution_reports` | Report identity/current workflow: id, event_id, author_id, work_refs, stage_ref, plan_version_id, current_revision_id, review_status, version | Work identities, report revisions and reviewer decisions | Submission/review/completion are separate; app does not equate reporting with completed work. |
| `execution_report_revisions` | Original body/claim/remaining work/declared usage/measurements: id, report_id, sequence, body, claim, typed payloads, asset_refs, source_hash, submitted_at | Report and immutable media | Draft editing may create checkpoints; submitted content immutable. Corrections produce new revisions and supersede only with explicit review. |
| `media_assets` | Original binary metadata/storage: id, owner_id, event/org scope, purpose, object_key, mime, bytes, sha256, upload_state, scan_state, retention_state, version | Report/governance/gallery/branding uses; signed access policy | Object storage keeps immutable original. Data URL or claimed byte count is not successful upload. Upload/link retries and orphan cleanup are explicit. Derived thumbnails/analysis point back to source hash. |
| `blockers` | Original issue and state: id, event_id, reporter_id, work_refs, primary_work_refs, original_description, occurred_at, received_at, effect, evidence_refs, severity, investigation_version, resolution/closure status, version | Work, authorized users, entries, proposal/candidate | Reported problem and confirmed facts distinct. Resolution, documented closure, suspension and completion are different outcomes. |
| `blocker_entries` | Append-only fact/question/update with a closed type: id, blocker_id, kind, typed payload, unit?, provenance/source, status, visibility, author_id, supersedes_id | Blocker; evidence; reviewer authority | Confirmed fact revisions invalidate dependent previews; organizer-only budgets/notes do not leak through shared recovery state or AI context. |

No separate `affected_subgraph` table is necessary initially. Compute against the specified plan, work-execution versions and sourced facts; persist the analysis/source manifest and exact proposed diff on the proposal/candidate for review and staleness checks. Recompute at activation. Completed work's historical body/status cannot be rewritten by applying a candidate.

## 6. Coordination, governance, public content and outcomes

| Table | Purpose / key fields | Important relationships | Version / audit and timing |
|---|---|---|---|
| `meetings` | Proposed/confirmed meeting: id, event_id, organizer_id, title/purpose, proposed/confirmed intervals, location/join URL, agenda_json, work/stage refs, conducted status, version | Invited users and proposed actions | Confirmation rechecks availability. No automatic Zoom/Meet link or attendance from RSVP. Provider calendar sync is not modeled yet. |
| `meeting_invitees` | Invitation/own RSVP: meeting_id, user_id, invitation_status, RSVP, delivery_state, version | Meeting/user | Unique invitee; actual record required for viewing. Invitation, delivery, RSVP and attendance are separate. |
| `meeting_actions` | Suggested/approved follow-up: id, meeting_id, title/notes, work_refs, status, human_approval_status, review_decision_id | Meeting, owning domain target where relevant | Approval of notes cannot directly rewrite work/plan/stock; consequential commands go through owner validation. |
| `content_entries` | Closed typed editorial records: id, event_id, kind announcement/update/discussion/reply/internal_note/photo/resource_request, parent_id?, title/body, audience, asset_refs, status, pinned, scheduled_at?, author_id, version | Event/media/parent entry; optional referenced requirement | Safe rendering and audience filtering. Publication/edits audited; scheduled intent is not delivery. Use typed columns/payload variants, not arbitrary executable instructions. |
| `event_follows` | Follow/watch preference: event_id,user_id,created_at | Event/user | Unique pair. Use explicit desired state (`following:true/false`), not a retry-unsafe toggle. |
| `governance_tickets` | Internal follow-up: id,event_id,status,items_json,document_asset_refs,reminder_preferences,version | Context/media/optional advisory proposal | No external filing/permit/legal approval inferred. Add separate document rows only if per-document review/history becomes needed. |
| `impact_measurements` | Human-verified published metric: id,event_id,report_revision_id,work_refs,metric,value,unit,measurement_method,qualification,decision_id,status,supersedes_id | Verified original report/evidence and decision | Prevent duplicate output credit for same work/metric; corrections explicit append-only. Unknown totals remain null; weight/area/attendance never inferred from photos or roles. |

No independent Participants, Insights, OrganizerDashboard, PublicProfileParticipants or SponsorImpact truth tables. Derive views from source records. Public aggregate caching is optional and rebuildable; cache keys include event/config/data versions and visibility, with no private answer payload.

## 7. AI provenance and operational reliability

| Table | Purpose / key fields | Important relationships | Version / audit and timing |
|---|---|---|---|
| `ai_runs` | Bounded run/attempt metadata: id,event/org scope,requester_id,task/schema version,context_manifest_json,provider/model profile,status,budget/deadline,attempts_json,usage_json,failure | Job, input record/media hashes, pending proposals | No secrets or hidden chain-of-thought. Source versions/scope rechecked before exposing/applying output. Attempt identity and unknown usage not zero. |
| `ai_proposals` | Structured advisory/candidate artifact: id,run_id?,event_id,kind,base_plan_id,source_versions,diff/payload_json,validation_report,digest,status,review_decision_id | Runs, domain objects, plan candidate and review | Manual/deterministic proposals may have no AI run and accurate provenance. AI cannot mark approved or activate. Source changes mark stale; store rejection/cancellation. |
| `job_tasks` | Durable leased processing: id,kind,payload_ref,status,attempt_count,max_attempts,available_at,lease_owner,lease_until,fencing_token,last_error | Run/media/outbox task; authenticated enqueue context | Process outside transaction; short claim locks; retries bounded; stale lease cannot publish results. Same Python codebase worker, no Redis required initially. |
| `outbox_events` | Durable post-commit notification/projection intentions: id,event_id,kind,target_refs,payload_ref,delivery_status,attempts,next_attempt_at | Owning transaction/recipient/in-app view | Insert in same transaction as state change; delivery idempotent. Recorded/sent/read are distinct. Minimal in-app notification delivery can use this table; no extra notification service required. |
| `audit_events` | Append-only authorized action history: id,event/org scope,actor,operation,target IDs/versions,before/after hashes,decision_id,request_id,time | Changed domain records and trace | No raw tokens/private transcripts in generic logs. Private audit views scoped; cannot be edited as ordinary content. |
| `idempotency_records` | Retry/outcome binding: actor_id,scope,operation,key,payload_hash,status,response_ref,created/expires_at | Owning transaction and business effect IDs | Unique composite key; same key different body conflicts. Resolve unknown client outcome without replaying ledger/consent side effects. |

Auth provider sessions may be external; do not add password-reset/MFA/token tables speculatively. If self-managed sessions are chosen, the session store and revocation design must be approved explicitly.

## First migration boundary and growth policy

The full physical model describes the frontend backlog, not the first migration. **Review correction: the first slice now includes Event Memory**, minimal authenticated event/immutable-source persistence, review decisions, audit/idempotency and durable outbox/job infrastructure. Publication/setup/roles/applications/assignments are added when their read/write slice needs them. See section 8 and the updated Group 1 in the main report; the previous broader read-model migration is superseded.

Do not store secrets, whole browser snapshots, provider raw kwargs or arbitrary JSON operations as business tables. Do not create replicas of the source graph in multiple modules. Review and test the JSON-manifest tradeoff before approving SQL migrations; a fully normalized item-revision model is a valid later decision if query/concurrency requirements demand it.


## 8. Event Memory — derived intelligence (Day 1)

Added by the 31 October contract-review correction. **Proposed; no tables implemented.** The `memory` module shares PostgreSQL and the FastAPI deployment. It is a rebuildable intelligence layer over operational events, immutable plans, original evidence and human decisions, not their replacement. It is present in the foundation migration, without requiring a live model or vector index.

### Minimal physical entities

| Table | Purpose and key fields | Relationships / constraints | Versioning, privacy and audit |
|---|---|---|---|
| `memory_entries` | Immutable derived revision: `id`, `logical_memory_id`, `revision`, `event_id`, `kind`, `title`, `assertions_json`, `applicability_json`, `origin`, `schema_version`, `extractor_version`, `model_profile?`, `run_id?`, `lifecycle`, `visibility`, `sharing_policy_version`, `review_decision_id?`, `supersedes_id?`, `correction_reason?`, `digest`, `created_at`, `created_by` | Event FK; prior revision FK must share logical memory/event; unique logical ID/revision; run/review links. Asserted source references must resolve to `memory_sources` rows for THIS revision. Kinds: event/context, plan, decision, execution_attempt, blocker, recovery, outcome/lesson. Default visibility event-scoped; explicit sanitized cross-event reuse only. | Original content/references immutable; review/lifecycle transitions authorized and append audited. Corrections append a revision; lifecycle transition retires old retrieval eligibility. Published is retrieval-ready, not public or verified. A digest binds exact review content. No private raw application answers or evidence bytes in text. |
| `memory_sources` | Normalized source lineage per memory revision/assertion: `id`, `memory_entry_id`, `assertion_id`, `source_event_id`, `source_kind`, `source_id`, `source_revision`, `source_digest`, `source_state_at_capture`, `source_decision_id?`, `relation` (supports/contradicts/qualifies), `locator_json`, `access_class`, `sharing_basis?` | Memory FK + event FK + review-decision FK where applicable. A typed source resolver validates kind/ID/revision/event/digest against real owning records; a polymorphic ID alone is not a database FK guarantee. Unique assertion/source/relation. Do not duplicate whole operational payload. | Captured source revision is immutable; current supersession/visibility is checked at retrieval. Locator is a safe structured reference (e.g. work ID or evidence span), not arbitrary URL/executable query. Protected source metadata and signed URLs never leak through public citations. |
| `memory_runs` | Extraction/retrieval trace: `id`, `kind`, `event_id`, `requester_id`, `purpose`, `policy_version`, `schema_version`, `source_manifest_json`, `source_manifest_digest`, `input_digest`, `status`, `job_id?`, `ai_run_id?`, `output_entry_ids`, `retrieved_revisions_json`, `budget_json`, `attempts_json`, `failure_code?`, `created_at`, `finished_at?` | Event/user/job/AI-run references; extraction deduplication key includes source revisions + extractor/schema + policy. AI provider attempts/usage belong to `ai_runs`; link them, do not duplicate independent run truth. Retrieval stores selected immutable IDs and reasons for context audit. | Scoped metadata; no secrets/hidden reasoning/raw protected prompts. Durable extraction status queued/running/succeeded/failed/cancelled/stale, fenced finalization; succeeded means candidates/projections saved, not outcome verified. Retrieval logging may be audit metadata rather than blocking source access. |

No separate memory database, memory service, truth-score table, copied participant/inventory state or mandatory embedding table. If semantic retrieval is introduced later, store versioned vectors as rebuildable indexes linked to memory revision/model; reauthorize the underlying record after every hit. No new frontend memory screen is required.

### Assertion and applicability schema

Each `assertions_json` item is a closed typed value:

```text
assertion_id, claim_kind, text,
evidence_stage: proposed | attempted | verified,
outcome: unknown | successful | failed | mixed | inconclusive,
evaluation_scope?, evaluation_criteria?, source_link_ids[],
authoritative_source_decision_id?,
uncertainty_reasons[], model_confidence?: number|null,
confidence_basis: source_record | reviewed_synthesis | model_estimate
```

Reject unknown keys, oversized batches/text and nonexistent/cross-scope source links. Confidence values, when supplied, must be finite in [0,1], labeled uncalibrated unless an evaluation exists, and never authorize a state change. The backend derives/validates evidence stage and eligible outcome from the permitted source chain. A model's output is only a suggested assertion payload; its `verified`/`successful` flags cannot be committed as authoritative verification. Preserve the raw suggestion in the restricted run artifact if useful; store validated claim classifications separately.

`applicability_json`: category/tags, goal/work pattern, scale with unit, environmental/location factors when relevant, skill/capacity/calendar/resource assumptions, exclusions, policy references, unknowns, and suggested transfer conditions. Shared lessons do not require identical categories, but conditions must be compared explicitly. The applicability score is separate from confidence and verification.

### Lifecycle and outcome invariants

1. A source-backed plan proposal can produce **proposed** memory. Approval/activation is a decision source, not execution success. A recorded execution action can produce **attempted** memory even before its outcome is known.
2. A **verified** observation needs the owning module's authorized decision about that exact report/attempt/measurement revision. A **successful/failed** outcome also needs source-backed evaluation criteria/scope and an authorized determination; model confidence, event closure or publication alone is insufficient. A deterministic source projection may copy such an existing decision exactly, without making one.
3. Human memory review authorizes publication of the derived synthesis/lesson and its sharing scope. It does not create a missing operational verification. If the source does not support a claim, reject or downgrade the claim; do not bless it with a memory review.
4. `candidate -> published` after schema, source, privacy and review policy; `published -> superseded/retracted` by authorized deterministic transition. A new correction revision gets its own review/digest. Audit status transitions; content is never edited in place.
5. Source correction immediately makes unsupported old assertions ineligible at read time. Outbox-driven invalidation/index rebuilding follows idempotently. Re-check source authorizations and current logical revision, rather than trust the captured source state forever.
6. Cross-event sharing requires explicit sanctioned reusable visibility and sanitized fields. Do not make the original private source accessible just because the memory is reusable. If source lineage can no longer be safely resolved, exclude the claim rather than return a misleading citation.
7. Revocation/deletion removes protected derived text/index data according to the approved retention policy. Retain only non-sensitive tombstone metadata if permitted; do not retain erased personal text under immutable-history wording.

### Day 1 atomic capture and retrieval

An operational source commit inserts a source-version outbox intention in the same transaction. The memory worker resolves that genuine source, checks access/policy, and creates a deterministic fact projection or a model candidate. Deduplicate by immutable source manifest/extractor policy; stale workers cannot publish after correction. Business commands do not call the model inside their transaction. Model failures never invalidate the operational commit.

Day 1 migration includes the three memory tables, minimal users/events/grants/context/plan/review source records and shared durable jobs/outbox/audit/idempotency. Existing media/execution/participation/resource models arrive with their actual flow. The source resolver supports typed ports for later kinds without fake source rows. Source hashes and registry locators do not replace original evidence.

Retrieval filters actor/event/purpose/sharing policy, eligible source revisions and lifecycle before applicability ranking; bound input/results and return exact cited revisions. Recheck before delivering a bundle and before applying a plan that used it. Store the selected bundle manifest in the planning/recovery AI run. No operational source fields are updated by retrieving, extracting, reviewing or correcting memory.
