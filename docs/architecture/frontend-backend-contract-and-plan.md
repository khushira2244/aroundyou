# AroundYou â€” frontend-driven backend contract and implementation plan

Review date: **31 October 2026, Asia/Kolkata**. Status: **proposal for review; implementation is not authorized**.

The recommended backend is a **Python/FastAPI modular monolith with PostgreSQL**, consistent with the earlier accepted architecture. The repository currently contains a React frontend and a substantial JavaScript browser/Node demo service, not a deployed FastAPI backend. The safest integration point is the existing `AroundYouService` boundary. Its browser-only assumptions must be removed deliberately; the demo engine must not simply be exposed as an authenticated HTTP server.

**Scope:** inspect and design only. No frontend behavior, visual design, fixture, business-rule implementation, migration, server, deployment or provider integration was changed in this task. AroundYou remains a general-purpose community planning, participation, governance and execution product. Canary Hill is a connected example, not the backend's domain definition.

**Review correction (31 October 2026): Event Memory is a first-class Day 1 module.** It is a derived, source-linked intelligence layer; PostgreSQL operational records and human decisions remain authoritative. Sections D, E, G, H and J below are amended by the Event Memory correction section at the end. The accepted frontend inventory and 142-contract baseline are unchanged; the memory contracts are explicitly additive design contracts, not existing frontend calls.

**Evidence labels:** **Observed** means present in the inspected repository; **Proposed** means a new design requiring approval; **Decision** identifies an unsettled product/infrastructure choice. Existing research is historical input, not a fresh claim about model availability, provider pricing, credits or API guarantees.

Supporting artifacts:

- [API catalogue](backend-api-contract-catalogue.md): each proposed method/path, request, response, validation and state effect.
- [Interaction inventory CSV](frontend-backend-interaction-inventory.csv): grouped screen/action contracts, current arguments, response needs, read/write, authority, mock status and entity.
- [Call-site inventory CSV](frontend-interaction-call-sites.csv): **183 distinct mapped frontend call-site interactions**, with source file/line and the same contract metadata.
- [Minimum database model](backend-contract-data-model.md): physical tables, logical planning entities, relationships and version/audit rules.
- [Audit coverage](../../outputs/backend-contract-audit/coverage-report.json), [raw source inventory](../../outputs/backend-contract-audit/source-inventory.json), [source hashes](../../outputs/backend-contract-audit/reviewed-source-hashes.json).

The catalogue covers **114 observed command names and 27 called service methods**, including dynamically selected commands. It has 150 grouped entries: 142 proposed HTTP contracts and eight deliberately local/test-only controls. Thirteen entries are explicitly marked new integration support (auth/media/async helpers); they are not claimed to be existing frontend API calls. This is the complete contract backlog, **not a recommendation to implement 142 endpoints before the hackathon**. Prioritize the slices in H.

## A. What was inspected

### Repository evidence

- [App routes](../../frontend/src/app/App.tsx), [provider](../../frontend/src/app/provider.tsx), [header/layout](../../frontend/src/app/layout.tsx), all 100 non-declaration TypeScript/TSX source files under `frontend/src`, and related CSS/assets.
- [AroundYouService and creation DTOs](../../frontend/src/services/contracts.ts); planning, publication, participant, organizer, sponsor and execution contracts in the same directory; [recovery DTOs](../../frontend/src/features/recovery/contracts.ts).
- [MockAdapter](../../frontend/src/services/mock-adapter.ts), [DemoService](../../demo/src/service.mjs), and the planning/publication/participation/intelligence/sponsor/organizer/execution/recovery/insights/context handlers.
- Fixture manifest and all fixture domains, five-scene replay, recovery replay, [ten-participant replay](../../demo/src/ten-participants.mjs), its explicit fictional insight responses and scenario instructions.
- Existing Node domain-test files and frontend test files; evidence IndexedDB storage, unavailable reasoning/analysis adapters, and Vite's fixture-serving middleware.
- Prior [architecture round 1](backend-architecture-proposal-round-1.md), [refinement round 2](backend-architecture-refinement-round-2.md), [AI adapter design](../research/ai-provider-adapter-design.md), and the local Meta/specialized-AI research documents. Their earlier design is retained where it matches current code; the recent frontend corrections below take precedence.

No applicable `AGENTS.md` was found in the workspace/ancestor locations checked. The working tree has project directories untracked; there is no committed application revision to cite as a release baseline. SHA-256 source hashes identify this review's inspected snapshot instead.

### Actual route/screen map

These are **client routes**, not existing backend endpoints. There are 28 concrete route patterns plus the wildcard fallback.

| Client route | Existing screen / backend demand |
|---|---|
| `/signup` | Demo identity selection and example-only form; organization/personal choice; optional fixture replay/restore. Real authentication is missing. |
| `/discover` | Category/search/map preview, create/join navigation, authorized canonical profile lookup. |
| `/create/:step` | Four steps: basics; when/where; context; review/create. Autosave, original execution explanation, sample voice text, interpreted-context review. |
| `/events/:eventId/created` | Saved unpublished event summary and next-step links. |
| `/events/:eventId/governance`, `/governance/ticket` | Advisory assessment, internal ticket, document metadata, reminder preferences. |
| `/events/:eventId/planning` | Stage proposal, edits/drag/resize, auto-arrange, assistant, apply/reject, confirm. |
| `/events/:eventId/work/:stageId?` | Stage work blocks, dependencies, quantities, effort, schedules, resource demands, proposal review and confirmation. |
| `/events/:eventId/actors` | Planned requirements, headcount/capabilities, add/review/derive/confirm. No real people assigned here. |
| `/events/:eventId/setup`, `/finalize` | Location/access, reported resources, draft invites/import, prospective partners, participation/visibility, communications, optional participant questions/tags, exact final review and publication. |
| `/events/:eventId` | Canonical **eight tabs only**: Overview, Stages, Volunteer Roles, Updates, Photos, Sponsors, Discussions, Impact. Public aggregate insights modal; owner editorial controls; join/support CTA relationship check. |
| `/join-events`, `/events/:eventId/join` | Discovery of open roles and four-step private application; review acknowledgement, submit, request/offer state. |
| `/my-events`, `/my-events/:section` | Personal cross-event workspace, relationship categories, selected event context, seven-section sidebar available before acceptance. |
| `/events/:eventId/participation/:section?` | Existing event-specific Overview, My Roles, Schedule, My Work, Updates, Meetings, Blockers. Actual work/reporting requires accepted responsibilities or explicit scoped review permission. |
| `/events/:eventId/manage/:section?` | Organizer's ten sections: Overview, Participants, Roles & Assignments, Resources, Sponsor Offers, Updates, Meetings, Blockers, Event Profile, Insights. |
| `/sponsor/register/:step` | Three-step organization draft/profile, support interests, capabilities, coverage and recognition/contact privacy. |
| `/sponsor`, `/sponsor/profile`, `/sponsor/settings` | Organization-scoped dashboard, profile/recognition, membership information. |
| `/sponsor/opportunities`, `/sponsor/opportunities/:eventId` | Filtered needs and advisory fit, details, support offer navigation. |
| `/sponsor/opportunities/:eventId/offer`, `/sponsor/offers` | Draft/submit/withdraw offer, record unverified fulfillment, review original terms. |
| `/sponsor/map`, `/sponsor/impact` | Accepted support portfolio, sourced-coordinate schematic and qualified verified outcomes. |

### Interaction coverage and controls that are not backend writes

The CSVs enumerate each current service interaction. The following controls must **not** become unnecessary backend mutations:

| Control / interaction | Current behavior and backend implication |
|---|---|
| Tabs, sidebar collapse, selected card, modal open/close, zoom, timeline view options, filter reset | Local presentation/navigation. Category buttons choose a server-approved aggregate series; clicking Age is not consent or a demographic update. |
| Search/category/location/support filters | Current lists are mostly filtered in browser. Their source reads need backend filters/pagination when datasets grow; preserve zero/one/multiple-result behavior. Do not accidentally filter just the first page. |
| Stage/work drag or edit, application Next/Back, checkbox settings with Save | These do call commands; included in the CSV. Distinguish local preview movement from saved proposal/draft confirmation. |
| Share/copy ticket/link, browser back, location permission, image preview | Clipboard/browser behavior; no authoritative write. Backend supplies authorized URLs/coordinates where needed. |
| Support button on public profile | Currently an informational panel and Sponsors-tab navigation, **not** a pledge/payment/participant mutation. Keep organization sponsor offers in their own membership-scoped portal. |
| Existing request/accepted participant Join and Support gate | UI reads the current account's event relationships. Submitted/pending/approved requests and accepted commitments disable both; draft/withdrawn/rejected or another event's request do not block an otherwise open event. Server must still enforce duplicate-application/assignment invariants independently. |
| Meeting RSVP | Persists own response. It does not establish attendance, confirm meeting time or accept a work assignment. |
| Reject displayed recovery preview before a candidate exists | Currently dismisses local preview only. Rejecting an already persisted candidate is a backend decision with rationale. |
| AI buttons marked unavailable / sample voice text | Evidence analysis and live recovery reasoning have explicit unavailable adapters. Sample transcript is fixture content. Do not pretend that a model/provider call exists. |
| Notifications bell, communications channel string, governance reminders, invitation drafts | Current UI states that external delivery is not connected. Persist intention/preferences; never return `sent` until actual confirmed delivery. No unsolicited email/Slack/WhatsApp integration is assumed. |
| Participant profile Edit / Message Organizer / calendar-provider synchronization | Existing informational/limited flows do not constitute a full editable account, chat service or Google calendar integration. No invented chat, attendance or calendar-write backend is included. |
| Fixture load/reset/account switching | Development/test controls only; no public production reset/impersonation endpoint. |

## B. What already exists

### Backend and infrastructure audit

| Area | Observed state | Completion / limitation |
|---|---|---|
| Frontend | React 19.1, TypeScript, React Router, Vite 6.2.6; versions read from local package manifest | Built screens and workflows, not a remote data client. |
| Business service | Dependency-free JavaScript ES modules, `DemoService.dispatch/request`, feature handlers | Meaningful deterministic **demo** transitions/validation. It runs in the browser or Node; no FastAPI/Express/Django/HTTP business server. |
| Existing server routes | Vite `/fixtures/*.json` middleware and emitted fixture assets | Static JSON delivery only. The 29 React route definitions are not REST routes. |
| Models/entities | TypeScript interfaces, JSON records and runtime dictionaries | No database ORM models or database migrations. Full state is cloned for each demo command. |
| Persistence | `aroundyou.shared-demo.v1` and `aroundyou.prompt1.creation.v1` localStorage snapshots; sessionStorage identity/sidebar; IndexedDB original evidence files | Not multi-user persistence, authentication, remote upload or cross-device durability. |
| Database | No PostgreSQL connection/configuration, SQL schema, ORM or migration runtime found | Earlier docs propose PostgreSQL; it is not implemented. Python files under `work/` and `demo/tools/` are generation/edit utilities, not a Python backend. |
| Repositories | In-memory fixture table lookup and browser adapter | No SQL repositories/unit of work. `snapshot()` exposes the complete synthetic state for local use. Never transport this to normal clients. |
| Auth/permissions | Browser demo account switching; event grants, organization membership, assigned-work and stage-review checks inside the demo | Scope rules are useful specifications; identity is not trustworthy outside this local demo. Sponsor context is not a permanent global person role. |
| Planning/versioning | Context revisions, stage/work confirmation, actor derivation and plan snapshots; expected session revision on writes | Real domain ideas exist. IDs, session state and many assumptions are single-event/fixture specific. |
| Participation | Application submission/review, offer, explicit acceptance, withdrawal, advisory fit and renewed plan consent | Approval is distinct from acceptance. The personal shell remains accessible before acceptance. |
| Inventory/sponsorship | Pledge, acceptance, receipt, reservation, consumable verification, equipment issue/return and source-linked fulfillment | Correct demo distinctions; no database contention/real financial ledger/external stock system. |
| Execution/evidence | Original reports, metadata links, human review, explicit completion and measurement publication | Original binaries are browser-local. Claims never automatically establish stock use or completion. |
| Recovery | Enhanced blocker investigation, deterministic graph scope/options, preview/approval, notification marker, consent and activation checks | Good proof scenario; transport-specific rules, fixed event/work IDs and `plan-v2` activation prevent direct general-purpose reuse. |
| AI integration | Fixture/text-rule simulations, `model_execution:false`; unavailable evidence/recovery adapters | No configured server-side inference, transcription, vision, search grounding or SAM worker. Research docs are not integrations. |
| Worker/queue | None | No durable job lease, queue, provider retries, worker restart recovery or transactional outbox delivery. Scheduling is generally a saved intent. |
| Tests | Node `node:test` domain suites; Vitest/Testing Library/jsdom frontend tests | Useful executable specifications. They do not prove PostgreSQL locking, genuine auth, durable object upload, worker crash recovery or real model behavior. |
| Ops | Vite dev/build scripts, demo replay/validation, local output reports | No backend deployment, server observability, secret management configuration or production network policy found. |

### Current data and scenario meaning

The clean fixture validator reports **11 fictional event listings**, but only Canary Hill has the connected six-stage, twenty-work, seven-role planning/participation workflow. Four base accounts include organizer, A, B and a sponsor representative; there are no applications/accepted commitments in the clean initial fixture. Other discovery listings must not be mistaken for fully implemented event backends.

The opt-in `canary-hill-ten-participants` replay adds eight identities and replays ten original applications, ten human approvals, nine accepted assignments and Arjun's pending offer. Its updated setup enables optional aggregate fields. At nine accepted, age/neighborhood groups are 5/4 and suppressed; after Arjun's explicit consent to his work offer they become 5/5 and public charts appear. No cleanup outcome, consumption or attendance is manufactured. Its existing synthetic six-sheet receipt and four-sheet reservation remain distinct from use.

### What should be retained versus replaced

**Retain as specifications:** immutable originals; coherent version checks; separate approved application/offered assignment/accepted commitment; permission-scoped work; public aggregate privacy; ledger quantities; verified report versus completion versus public measurement; candidate approval versus activation; unresolved facts remain unknown.

**Replace as infrastructure:** client-selected actor, globally current event/draft, whole-state snapshot transport, fixture/template IDs as universal business rules, browser storage, one-time plan-v2 activation, mock provider flags, simulated notification delivery and hard-coded transport alternatives.

## C. What the frontend requires from a backend

The CSV/API catalogue is the detailed interaction contract. The backend must supply coherent read models at the same boundaries the hooks consume, plus commands with explicit effects. Avoid one REST request per displayed card or treating each component as a microservice.

| Read model / DTO | Required response content and visibility |
|---|---|
| `CreationState` | Event/draft ID, current brief/form checkpoint, original context and reviewed interpretation, lifecycle/publication and versions. Owner only. |
| `PlanningState` | Stages, work/groups, requirements/resources, dependencies and warnings, compatible revision numbers, pending proposals, active plan. Permissioned design scope. |
| `GovernanceState` | Advisory items, internal ticket, private document references/status, reminder preferences; no official approval claim. |
| `SetupState` | Exact configuration and source plan, checklist, ledger-derived availability versus reported claims, invitation/partner drafts, sponsor visibility, finalization. Owner only. |
| `CanonicalProfile` | Exactly eight public tabs, published plan/config/content, public roles/availability summaries, verified impact and consented safe aggregates. Owner preview separately authorized. Never raw applications/private organizer data. |
| `ParticipantInsights` | Safe buckets with counts/percentages, minimum group 5, explicit suppressed/disabled reasons, public accepted total; `counts` requested/approved/accepted only for organizer. No per-person answers. |
| `MyEvent[]` | Current actor's applications, accepted assignments and organizer relationships, event summary; Requests/Participating/Organizing are derived, overlapping relationships allowed. |
| `ParticipationState` | Own original application/revisions and availability, offers and terms, accepted work only, permitted updates, invitations/RSVP and relevant blockers/reports. Shell access does not imply assigned-work access. |
| `OrganizerParticipants` | Scoped private applications/experience/availability, approved requirements, assignments, deterministic candidate choices, advisory fit provenance. Not a public read model. |
| `OrganizerDashboard` | Actual service-derived counters and summaries, resources and source records, notes, updates, meetings, candidate/recovery state and audit references. Stage delegates receive narrower execution views. |
| `SponsorPortal` / `OrganizerSponsorState` | Organization membership-scoped profile/offers/needs/fit/fulfillment/portfolio, with separate organizer review view. Recognition requires both organization preference and organizer release. |
| `ExecutionState` | Work/status/plan/revision, exact report revisions and original asset links, role-scoped review flags, resource claims/reservations/loans, blockers and optional analysis availability. |
| `RecoveryState` | Direct/downstream/shared constraints, sourced facts and visibility, alternatives/preconditions, candidate exact diff/digest, notification/consent/validation state. Full cross-event or private execution snapshots are not sent to participants. |

Full property lists are in the seven inspected `frontend/src/services/*contracts.ts` files plus recovery/evidence analysis contracts. **These are DTO references, not SQL model definitions.** Preserve their current shape via an HTTP adapter where feasible; replace browser-only fields explicitly:

- `storage:'browser_indexeddb'`, `media_reference`, inline `data_url` â†’ authorized server asset ID + short-lived access URL; retain original bytes/hash and visible upload status.
- Literal `configured:false`, `model_execution:false`, `source:'demo_fixture'`, `synthetic:true` â†’ correctly typed provenance/availability fields capable of representing real results. Never just flip a boolean to suggest a provider ran.
- `templateId` â†’ server-issued checked assignment candidate ID tied to application/work/plan versions; never accept an arbitrary client eligibility/schedule template as authority.
- `plan-v1/plan-v2`/fixed IDs â†’ opaque stable event/item IDs and server-issued revisions; seeded legacy IDs may remain aliases for recording fixtures.
- Implicit `current()` draft â†’ explicit event/draft ID retained by the adapter from `startCreation`; every request is event scoped.
- `clientReference` â†’ scoped idempotency key with payload hash; exact consent `termsKey` â†’ server-generated canonical digest, not a browser authorization token.

### Exact important input schemas

The catalogue references the following concrete shapes. Body IDs use snake_case in the proposed HTTP API; the adapter translates existing camelCase command arguments. Path IDs replace duplicate body IDs and are revalidated.

- **`RelativeSchedule`**: `{start_day:int>=1,end_day:int>=start_day,start_minute:int[0,1439],end_minute:int[0,1440],timezone:IANA}`. Validate total end > start, valid event range and half-open intervals. Start/end on one day for current availability/meeting forms; multiday work remains explicit. Day 1 maps to the event anchor if one exists.
- **`Quantity`**: `{value:finite nonnegative decimal or null,unit:string,confidence?:string,known_subtotal?:decimal}`. Keep null as unknown. Do not sum incompatible units or replace unknown with zero.
- **`CreationForm`**: name/category/purpose/goal; format; start/end dates/times/timezone; venue/area/city/state/country/reach; coordinates/source; work scope and original execution intent/source; projected attendee/volunteer strings; target groups; known resources; constraints; outcomes; optional theme/online details; review acknowledgements. Drafts permit incomplete fields; final creation validates requirements. Projected headcount is not accepted capacity.
- **`ApplicationAnswers`**: `skills,motivation`, optional `volunteer_experience,coordination_experience,community_experience,contribution,preferred_responsibility,limitations`; `leadership_interest=unspecified|interested|open_to_discussion|not_interested`; `work_preferences[]` from fieldwork/documentation/logistics/communication/coordination/transport/other; configured `custom_answers`; `participant_insights:{consent:boolean,fields:{age_range?,neighborhood?,experience_level?,participation_interest?},tag_ids[]}`. Preserve raw originals and configuration version; no inferred demographics.
- **`ParticipantConfiguration`**: `collect_insights,public_aggregates`, booleans for the four standard fields, stable active/archived tags, versioned questions with short_answer/single_choice/multiple_choice, options and optional/required status. Current Age options: Under 18, 18â€“24, 25â€“34, 35â€“44, 45+. Experience: First time, Some experience, Experienced.
- **Setup `location`**: access instructions/facilities/emergency contact/zone IDs. **`resources`**: reported availability claims by requirement ID only. **`participation`**: visibility public/community_only/invite_only; approval_required/allow_groups/show_open_roles/registration_open booleans. **`communications`**: welcome/instructions/contact/channel strings. **`invites/sponsors`**: reviewed draft IDs and authorized public offer IDs. None are resource receipts or sent invitations.
- **`OrganizationProfile`**: name/type/description/website; logo/cover asset refs; contact name/position/email/phone/city/country; focus[], support capabilities[], coverage[]; recognition show_profile/show_logo/show_contributions/private_contact. Membership and verification are server facts, not profile inputs.
- **Sponsor offer**: exact event/resource/support type, description, positive quantity/unit, optional estimated value, delivery date/method, notes and offer revision. Support types funding/materials/equipment/services/volunteer_support/expertise. A volunteer-support quantity is not a set of personally accepted work assignments.
- **Execution report**: original body, remaining work, progress/completion claim, work/plan/report revision, declared resource usage `{resource_id,quantity,unit,kind}`, reported measurements `{metric,value,unit}`, evidence asset IDs, idempotency reference. The server derives author/stage/current permissions; no client `verified`, `completed` or reviewer identity is accepted.
- **Recovery fact**: typed key/value, reported/confirmed/unknown status, source reference, unit, evidence refs and shared/organizer-only visibility. Confirmation requires authority and a basis; a source string alone is not external verification. Candidate review includes exact diff digest, affected IDs, original base plan/work/investigation/execution versions and required consent terms.

## D. Proposed architecture and backend modules

### Runtime and ownership

One FastAPI application, one PostgreSQL database, one private object store, and an optional **separate worker process using the same application/domain code**. No microservices, distributed event bus, Redis or vector database is required for the first slice. Proposed libraries are FastAPI/Pydantic, SQLAlchemy, Alembic and a PostgreSQL driver; dependency versions are not selected or installed by this report. Use a managed identity provider or another explicitly reviewed authentication implementation; browser demo account switching is never production auth.

Request path:

```text
frontend HttpAdapter â†’ authenticated API handler â†’ application use case
  â†’ authorization + typed/domain validation â†’ unit of work / repositories
  â†’ PostgreSQL commit (state + decision + audit + outbox)
  â†’ response DTO filtered for the viewer
```

AI path:

```text
application use case â†’ load permitted authoritative versions â†’ scoped context manifest
  â†’ durable bounded AI job â†’ structured untrusted proposal â†’ schema/domain validation
  â†’ save pending proposal â†’ exact-target human review where required
  â†’ deterministic domain command â†’ atomic authoritative commit
```

Do not make the domain layer import FastAPI, provider SDKs, browser DTOs or blob storage clients. API handlers do not write ORM rows directly. Repositories implement persistence, not authorization decisions. Read-model queries can join owning records but cannot become competing sources of truth.

| Proposed package | Owns | Existing product modules preserved / dependencies |
|---|---|---|
| `access` | Authenticated users, organization membership, event grants and scoped delegation | M01; no permanent organizer/participant account segregation. |
| `events` | Durable event identity/brief, context originals and revisions | M04; M03 resume/draft progress references these records. |
| `planning` | Stage/work/actor/resource-demand draft and confirmed plan manifests; dependency validation and deterministic activation | M06â€“M08; same engine serves environmental, education and other initiatives. |
| `publication` | Setup/question/visibility revisions, finalization/publication releases, public profile presentation | M09â€“M10; public discovery projection supports M02. |
| `participation` | Applications/answers/availability, review, offers, acceptance, withdrawal and changed-term consent | M11 and assignment-owning part of M12; M03/M13 are composed views. |
| `resources` | Physical stock, verified receipts/movements, reservations, equipment custody and corrections | M14; consumes approved demand from planning and obligations from sponsorship. |
| `sponsorship` | Organizations' draft profiles/recognition, offer obligations and reported/verified fulfillment | M15 with M01 membership. No duplicate inventory ledger. |
| `execution` | Original report/evidence lineage, scoped review, work/stage progress/completion decisions | M16 + operational status part of M07. |
| `blockers` | Original issues, sourced investigation, deterministic affected scope, reviewed change candidates and issue closure | M17; calls planning activation/participation/resources through one coordinated use case. |
| `coordination` | Meetings, invitations/RSVP, proposed follow-ups, announcements/discussions/notes, notification intentions | M18; message approval never bypasses planning or work services. |
| `insights` | Verified measurement publication and privacy-preserving projections | M19; does not own a second participant or resource database. |
| `ai` | Runs/attempts/context manifests, schema-validated pending proposals, usage and capability-gated provider ports | M20; no credentials or mutation tools in browser. |
| `memory` | Source-linked, versioned event/execution intelligence; extraction candidates, authorized retrieval, correction/supersession | First-class Day 1 capability shared by planning, execution, blockers and outcomes. Derived from owning modules; no authority over their state. |
| `governance` (small feature package) | Internal tickets/documents/advisory follow-up | M05; no government/legal approval authority. |
| Shared infrastructure | Unit of work, media storage, jobs/outbox, idempotency, append-only audit, errors/observability | Technical support, not additional competing domain owners. |

All **20 previously specified capabilities** remain represented. Organizer Dashboard, Participant Workspace, My Events and Sponsor Portal are query/application faÃ§ades over these owners, not separate databases or deployment units. Do not create twenty services or CRUD routers for every table.

### Authorization and concurrency defaults

- Actor comes from verified server session/token. Organization/event/work scope is checked on every use case, including file access and AI context retrieval. `accountId`, `role`, `can_review`, `confirm:true` and `reviewedTerms` sent by the browser are not permission grants.
- A role title never grants stage authority. Stage review cannot approve inventory, event-wide planning or unrelated work. Sponsors need membership in the path organization, not a global sponsor boolean.
- All writes carry expected affected entity versions. Plan edits/AI include base plan/context/work/requirement versions. Replace the demo's single global revision with per-aggregate versions and a coherent plan manifest.
- Lock the event/candidate/affected assignment and stock/capacity records in a consistent order for short transactions. Use unique/idempotency constraints and real database contention tests. Do not hold locks across user review, uploads or model calls.
- Accepted assignment scheduling needs actor-level protection across events, not only within the edited event. Role capacity and stock reservation races require locked shared predicates, not just optimistic edits to two independent assignment rows.
- No frontend request/support disabled state is a security check. Enforce unique active application, current offered terms and actual accepted coverage server-side. Support currently opens information only; any rule forbidding a joined person from representing a sponsor in that same event needs an explicit product decision rather than a global account-role restriction.

## E. Proposed database entities

The field-by-field model, relationships, constraints and audit/version rules are in [backend-contract-data-model.md](backend-contract-data-model.md). It describes the frontend's full present breadth, **not a request to implement 42 tables immediately**.

The smallest coherent persistence design is:

- **Identity and access:** users, organizations, organization memberships and explicit event grants. An authenticated user can organize one event, participate in another and represent an organization with permission.
- **Versioned planning and publication:** events, immutable event-context revisions, an editable coherent planning draft, immutable plan versions, stable work-item identities, operational work state, setup revisions, publications and published role opportunities. Stage/work/dependency/group/actor/resource-demand objects initially live in a validated plan manifest; their stable IDs resolve to the same event and plan. Do not duplicate current planning fields in several authoritative tables.
- **Participation:** applications and immutable answer revisions, exact assignment offers, assignment decisions and typed review decisions. Application approval never inserts an accepted assignment. Changed terms preserve the original acceptance and require renewed consent when material.
- **Supply and execution:** inventory lots, append-only resource movements, reservations, equipment loans, sponsor offers and fulfillment reports; original execution reports and immutable report revisions; media metadata in PostgreSQL and original bytes in object storage. Sponsor promises do not increase usable inventory.
- **Recovery and coordination:** blockers and append-only investigation entries; meetings/invitees/follow-ups; typed content entries and event follows; internal governance tickets; verified impact measurements.
- **AI and infrastructure:** bounded AI runs, immutable proposals with source manifests, durable jobs, transactional outbox, audit and idempotency records.

JSON manifests are a deliberate hackathon tradeoff: simpler atomic coherent versions and fewer revision tables, at the cost of application-enforced internal references and less convenient SQL reporting. Database foreign keys still protect event/work/application/assignment/media ownership. All graph references must be validated before the transaction commits. If collaborative editing or cross-plan analytics demands row-level edits, normalize versioned plan items later; do not maintain a JSON and normalized graph as independent truths.

Unknown effort, quantity, headcount and availability remain `null` with an explicit reason. Zero means a known zero. Physical quantities use decimal values and typed units; money is a separate typed amount/currency and is never converted into physical stock. No stored dashboard totals, fake attendance, model-derived completion or inferred demographic answers are needed.

## F. Proposed API contract

[The API catalogue](backend-api-contract-catalogue.md) contains each proposed method/path, request, response, validation, state effect, domain and source call sites. [The interaction CSV](frontend-interaction-call-sites.csv) gives one row per observed source interaction with current request expressions and its proposed contract mapping. These are an integration backlog, not an instruction to build broad CRUD.

### Shared wire conventions

All application paths use `/v1`. Authentication is established by a verified server session or bearer token from a selected identity provider. Choose one browser-session/CSRF/CORS strategy before implementation; do not accept an `actor_id` argument as authentication. Organization and event IDs in paths are authorization scopes, not grants.

- JSON uses snake_case. An HTTP adapter translates to existing frontend DTOs; any production-only union changes must be reviewed explicitly. Read projections retain the screen-oriented shapes in the current seven contract files, with private fields removed by audience.
- Mutable aggregates expose `version` and an ETag. `If-Match` is required for existing-state writes; proposal commands also send the exact source-version manifest they reviewed. Creation commands use an idempotency key. Irreversible/effect-producing commands also use an idempotency key even when version guarded.
- An idempotency key is scoped by authenticated actor, method/path and operation; replaying the same body returns the original result. Reuse with a different payload is `409`. It is not a replacement for receipt/consumption uniqueness constraints.
- Paginated reads return `{items, next_cursor}` with a stable server ordering. Apply search/category/location/support filters before pagination. Never return a browser-session snapshot or all private applications so the browser can filter them.
- Synchronous command results contain the affected IDs, current versions and outcome, plus only the authorized projection needed next. An operation declared `{applied:true}` means the specific documented draft/record effect; it does not imply publication, activation, inventory availability or verified completion.
- Errors use `{error:{code,message,field_errors?,current_versions?,retryable,request_id}}`. Use `401` unauthenticated, `403` forbidden, `404` inaccessible/missing scoped record, `409` stale/incompatible/business conflict, `422` invalid input, `429` throttled, and `503` temporarily unavailable. Do not expose private conflicting participant details in a conflict explanation.
- Read access to a pending AI run uses the run ID and the same event/audience policy. An unavailable provider returns a clear capability/unavailable error or failed run, never a fabricated successful proposal.

The catalogue's named responses refer to existing screen DTOs as documented in section C, plus these new infrastructure contracts:

```typescript
// Proposed transport shapes; these are documentation, not implemented code.
type SourceVersions = {
  event_version: number; context_revision: string;
  draft_version?: number; active_plan_id?: string;
  publication_id?: string;
  entity_versions?: Record<string, number>;
};
type AsyncRunReceipt = {
  run_id: string;
  status: 'queued' | 'running';
  status_url: string;
  source_versions: SourceVersions;
};
type RunResult = {
  run_id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled' | 'stale';
  proposal_id?: string;
  error?: { code: string; message: string; retryable: boolean };
};
type ProposalEnvelope = {
  proposal_id: string; event_id: string;
  kind: string; schema_version: string;
  status: 'pending' | 'approved' | 'rejected' | 'stale';
  source_versions: SourceVersions;
  source_manifest_hash: string;
  proposed_changes: unknown; // validated by a specific closed schema per kind
  assumptions: string[]; unknowns: string[];
  validation: { errors: string[]; warnings: string[] };
  digest: string;
};
type CommandReceipt = {
  operation_id: string; outcome: string;
  entity_ids: string[]; versions: Record<string, number>;
};
type Quantity = { value: string | null; unit: string; unknown_reason?: string };
```

`unknown` above is only shorthand for the union of registered proposal schemas in this design document: the server must never accept an arbitrary patch, SQL, executable function or arbitrary tool name. Each endpoint uses its own allowlisted fields. Review decisions store the reviewed digest and schema version. `PlanningProposal`, `RecoveryCandidate` and understanding/role-fit/advisory results use this envelope with their typed existing payload; the adapter must handle queued/running/failed/stale states instead of pretending a model call is synchronous.

`MediaAsset` minimally returns `{asset_id,event_id,kind,mime_type,byte_size,sha256,status,created_by}`; upload initiation adds a short-lived scoped upload URL/headers and expiry. Upload completion verifies bytes, size, type and ownership before marking usable. Read access returns a short-lived authorized URL. Neither public profile URLs nor arbitrary client URLs are trusted as original evidence.

### Critical contract examples and effects

| Method/path | Required input | Required output | Validation and authoritative effect |
|---|---|---|---|
| `GET /v1/me/events` | Relationship and optional cursor/limit | Compact `MyEvent[]`, statuses, next action and event/workspace links | Session user only; Requests vs Participating derived from actual accepted current assignments; no write. |
| `GET /v1/events/{event_id}/participation/me` | Route event; current session | Existing participation state, own application/offers, accepted roles, schedule/work, permitted actions | Never another participant's private answers. Workspace shell may exist before acceptance; accepted assignments govern work access. No write. |
| `POST /v1/events/{event_id}/applications/{application_id}/submit` | Published role IDs, own availability, optional skills/motivation/consented answers, acknowledgement and source versions | Application ID/status/version plus own application projection | Active unique event/user application; only published current roles; approval is a later human command. Existing combined acknowledgement must map to its exact reviewed meaning, not invent additional user acknowledgements. |
| `POST /v1/events/{event_id}/assignments/{assignment_id}/accept` | Exact offered version, terms digest and consent; idempotency key | Accepted assignment, commitment/schedule and updated own relationship | Offer belongs to user; current compatible plan/role/capacity/overlap/capability conditions. Atomic acceptance only; no completion. |
| `POST /v1/events/{event_id}/reports/{report_id}/submit` | Existing report ID and exact draft revision; original note/claims/assets were saved to the draft | Report/revision ID, submitted status and pending-review projection | Original preserved; reporting is not human verification or stock consumption. Review and reconciliation are separate commands. |
| `GET /v1/events/{event_id}/blockers/{blocker_id}/affected-scope` | Scoped blocker | Versioned roots, downstream edges, affected work/resources/commitments and unknowns | Deterministic permitted graph; no model call or state mutation. |
| `POST /v1/events/{event_id}/blockers/{blocker_id}/replanning-runs` | Confirmed fact references, selected affected scope and exact base versions | Async run receipt; later immutable recovery proposal | Persist pending artifact only; model cannot modify plan, stock, commitments or completion. |
| `POST /v1/events/{event_id}/plan-candidates/{candidate_id}/activate` | Exact candidate digest, expected versions and required review/consent references | New active plan version or explicitly deferred outcome with blockers | Revalidate affected graph, commitments and inventory under transaction locks. Incompatible/stale inputs conflict; approval alone is not activation. |
| `GET /v1/events/{event_id}/profile` (insights projection) | Authorized event viewer; selected dimension is a local UI choice | Safe aggregate buckets/suppression reason; public accepted count; organizer-only workflow counts | Same privacy projection for prospective/pending/accepted viewers. No individual answers; no mutation to enable settings. |

Paths above are cross-flow examples from the catalogue. Submit commands reference an existing server-created draft/report ID; creation/upload commands are listed separately in the catalogue. Avoid implementing parallel aliases. The browser can render permitted actions but the server recomputes permission and state validity on every command.

Retries: clients may retry idempotent reads and keyed writes with bounded backoff/jitter for transient errors; never retry validation/permission/stale conflicts blindly. A timeout after commit must resolve by idempotency replay or operation lookup. Do not retry a full multi-step sponsorship/execution workflow as one unkeyed write.

## G. AI/orchestration and execution boundaries

### End-to-end recovery protocol

1. **Load the active plan manifest and permitted operational records.** Work identities remain stable while plan versions are immutable. Keep original execution evidence, reported facts and human decisions separately addressable.
2. **Record the blocker/change as an original.** A participant can report an issue in their permitted scope; they cannot confirm a resource shortage, grant access or verify another person's work merely by stating it. Organizer/stage authority and source references determine which facts are confirmed. Preserve contradictory observations.
3. **Compute affected scope deterministically.** Build dependency edges from the selected plan, validate no dangling/cross-event references or cycles, start at explicitly linked impacted work, then traverse downstream dependencies. Separate already-completed work, work in progress, future work and historical evidence. Include shared resource/capacity/actor constraints as additional affected relationships; a dependency DAG alone is not a resource-constrained scheduler. Unknown impact returns `needs_investigation`, not an invented vehicle or staffing number.
4. **Capture an immutable source manifest.** Include event/context/plan versions, exact relevant work/dependency/resource/assignment versions, known facts/evidence references, units/timezone, exclusions, authority scope and unresolved questions. Record hashes and provenance. Retrieve only approved historical knowledge with source IDs, access policy and supersession status. There is no Event Memory implementation today. Build the Day 1 memory persistence/retrieval boundary described below; begin with source-linked PostgreSQL retrieval, without requiring embeddings or a live model.
5. **Run a bounded proposal workflow outside the transaction.** Start with one structured call for stage/work/role suggestions and scoped recovery. Use a fixed multimodal pipeline for evidence transcription/analysis, with deterministic pre/post validation. Add tool loops only if measured failures require retrieval or iterative clarification. Bound time, attempts, calls, tokens and allowed retrieval tools; no authoritative mutation tool or arbitrary external URL fetch. Database content, media and transcripts are untrusted instructions.
6. **Validate the proposal.** Enforce the registered schema, scoped IDs, allowed change kinds, units, nonnegative quantities, dependency validity, stage windows, skill/capacity/calendar rules and explicit unknowns. Recompute arithmetic server-side. A syntactically valid model response is not a feasible schedule, proof of inventory or permission approval.
7. **Save pending proposal and review package.** Show the exact diff, assumptions, source references, affected opportunities/reservations/accepted commitments, risks and unresolved checks. Applying a suggestion to a draft is distinct from confirming a plan. Human approval references a specific digest; it cannot approve all future revisions of a proposal.
8. **Build a candidate version deterministically.** Preserve the current active version. Reconcile changed stage/work/actor requirements, publication opportunities, resource reservations and assignment compatibility. Material changes require exact renewed participant consent; no silent acceptance migration. Human approvers cannot fabricate a sponsor receipt or inventory balance to make a plan feasible.
9. **Activate atomically or defer safely.** Within a short transaction recheck base pointers/versions, relevant capacities and permissions, then commit the candidate plan pointer, compatible dependent records, audit and outbox together. If consent or verified inputs are missing, keep the current version active and candidate explicitly deferred. If work must pause immediately, an authorized separate hold/suspension command records it; pending AI cannot silently suspend work. Never half-activate changed parents with old incompatible children.
10. **Expose traceability and recovery.** Read models identify current active and proposed versions. Audit original report â†’ blocker â†’ affected-scope manifest â†’ AI run/attempt â†’ proposal â†’ decision â†’ candidate â†’ activation. Rejected/stale/failed proposals remain inspectable by permitted reviewers and cannot be re-applied as fresh.

### Organizer changes a stage during an AI run

Run R starts from context C2 / active P3 / draft D7. Organizer changes the stage, producing D8 and invalidating incompatible child derivations. R may finish successfully as model output, but the server compares its source manifest before review/apply and marks it stale. An old approval digest cannot force it into D8. Return a conflict with current version identifiers and offer a new scoped request; retain R and its original context for audit. The same check runs again at activation, because state can change after human review.

### Operational boundaries

- PostgreSQL owns business state; object storage owns bytes, with database metadata/authorization; jobs own durable execution intent. A small PostgreSQL-backed lease queue and outbox are sufficient initially. An in-process FastAPI background task alone is not durable recovery.
- Jobs use bounded attempts, leases and fencing tokens; a late worker cannot overwrite a newer result. Provider retries create attempts under the same run; deduplicate final proposal persistence. Handle cancellation, unavailable credentials, malformed responses, refusal, truncation and timeouts explicitly.
- Provider adapters declare **tested** capabilities (text, schema format, tools, vision, audio/video, streaming) per model/provider. Do not assume Meta and Modal share endpoints or schema enforcement. The October 27 research is reference material, not proof of current access, credits or hosted availability. Confirm those in a separate provider proof of concept before enabling a real call.
- Store usage/latency/error metadata and redacted diagnostic references; do not store hidden chain-of-thought, credentials or unrestricted private prompts in audit. Cost budgets/rate limits are per run/event/user; price configuration is external and unverified here.
- Audio transcription preserves original audio plus an editable reviewed transcript. Evidence analysis is an advisory observation; neither transcription nor segmentation verifies completion, physical quantities, receipt, safety or municipal permission. Publish impact only from reviewed measurements with original evidence lineage and correction history.
- Streaming is presentation/progress only. A partial streamed proposal cannot be applied. Recovery from a disconnected client reads the durable run, not a duplicate unkeyed request.

## H. Recommended implementation and mock replacement order

1. **Approve contracts and policy decisions.** Resolve identity/session strategy, plan/version lifecycle, accepted commitment/calendar semantics and privacy/publication rules. Keep the existing fixtures/tests as explicit demo specifications.
2. **Persistence/auth/read-model foundation (first proposed coding step).** FastAPI modular-monolith skeleton, PostgreSQL migrations/UoW, verified session boundary, explicit event grants, versioned event/plan/publication/participation source records, `GET /me`, `GET /me/events` and canonical profile reads. Use test fixtures in tests, not automatic production seeding. Verify visibility, own-data access and relationship derivation before wiring the UI.
3. **Generic event creation/context â†’ planning â†’ publication.** Replace global creation/current-event state with route IDs. Preserve original context and exact confirmations. Implement deterministic plan validation and manual reviewed proposals before a live model. Add scoped HTTP adapter integration only after the read contracts pass. New events cannot inherit Canary Hill work or categories automatically.
4. **Application â†’ human review â†’ exact assignment offer â†’ acceptance â†’ same participant workspace.** Replace participation mocks next: this proves actual data ownership, capacity/version checks and the most visible navigation distinction. Exercise approved-without-offer, pending offer, accepted, rejected, withdrawn, conflicting roles and material changes.
5. **Resource/sponsor receipt and reservation â†’ execution report/evidence â†’ human review.** Introduce durable media first; connect physical accounting and report reconciliation with idempotent effects. Reported usage/completion stays separate until authorized review. This is the first useful operational vertical slice.
6. **Blocker impact â†’ scoped pending proposal â†’ human candidate review â†’ new active version.** Use the same graph and assignments/resources as step 5; replace fixed recovery IDs/options with versioned proposals. Verify stale outputs and deferred activation/renewed consent. This is the core differentiating demo; no broad CRUD is needed to prove it.
7. **Meaningful extensions:** meetings/RSVP/follow-ups, content/governance, privacy aggregates/verified impact, sponsor profile/offer refinements. These modules remain in the architecture even when implemented later.
8. **Optional experiments:** real transcription/vision/segmentation, semantic indexing and expanded retrieval tools after provider/quality/latency evaluation. Event Memory source capture, provenance and authorized retrieval are part of the foundation, not an optional later RAG experiment. Keep their availability explicit; none is necessary to grant business authority to AI.

Replace read mocks first where source records are trustworthy; do not populate production dashboards with aggregate fixture numbers. Retain `MockAdapter` and explicit replay fixtures for development/video tests under a clear demo mode. The future `HttpAdapter` selects the server through configuration and sends commands to real endpoints; **removing JSON completely should mean removing JSON fixtures as authoritative runtime storage, not removing JSON HTTP payloads or test fixtures**. Avoid mixing local writes and server reads for the same event; that creates split state and misleading counts.

## I. Mismatches, risks and human decisions

### Five decisions to settle first

1. **Authentication and organization representation:** identity provider/session transport, local development login, organization invitation/membership management, and explicit stage delegation.
2. **Plan lifecycle:** approve coherent immutable manifests/JSON tradeoff, milestone confirmation versus active operational version, publication release linkage, and immediate hold versus deferred candidate activation.
3. **Commitment/calendar policy:** which changes are material, who may approve assignments, skill-review basis, capacity/overlap rules, and whether unanchored relative sessions can be accepted before dates are known.
4. **Insights/consent policy:** public-safe aggregate access, threshold/denominator rules, optional unanswered fields, question/configuration revisions, under-18 participation and retention. Enabling Age later cannot invent answers or retroactively grant consent.
5. **First demonstrable scope and providers:** approve the read/auth slice followed by one end-to-end execution/recovery slice, and separately verify model/storage availability before promising integrations. Keep all event categories supported.

### Concrete frontend/backend gaps

| Finding | Required resolution / risk |
|---|---|
| Browser-selected demo identity and capability flags | Replace with verified session plus database grants; do not treat persona IDs as authorization. Signup is currently demo entry, not a production credential flow. |
| One global draft/current session and Canary Hill context/template IDs | Introduce persistent event-specific drafts/read models; other ten discovery listings have no full connected operational graph. Do not claim all eleven events support the same scenario. |
| No real backend, transactions, database or workers | Existing Node validations are valuable executable examples but cannot prove database races, secure media access, durable jobs or production authentication. |
| Literal `false`/`demo_fixture`/`synthetic:true`/IndexedDB provenance in contracts | Introduce truthful production variants and adapter mapping deliberately. Do not falsely label real evidence synthetic or server files as local. |
| Modern recovery impact plus legacy W16/S4/vehicle logic, fixed `plan-v2` | Generalize graph-driven affected scope and arbitrary version lineage; preserve exclusions/completed work and unknowns. One transport scenario is not a general replanner. |
| Global expected revision | Replace with aggregate versions and shared predicate locking for role capacity, stock and cross-event actor time conflicts. |
| Qualification/overlap heuristics and template IDs | Fixture allowlists/regex and browser template choice are not verified skills. Store structured review basis, exact terms and genuine schedule conflicts. |
| Post-publication edit inconsistency | Some setup commands reject changes while Organizer Profile can change release visibility/configuration. Use one versioned publication change protocol and decide consent/visibility effects explicitly. |
| Public insights access and synthetic-only eligibility | Public safe aggregates must work for authorized joiners, not only organizers. Do not port the demo's `synthetic === true` eligibility filter to real users. Consent/accepted status/configuration/threshold still apply. |
| Age/neighborhood empty or suppressed | Current configuration and actual optional answers govern data. At nine synthetic accepted users the 5/4 categories are suppressed; at ten 5/5 may display. Enabling a question alone cannot produce a chart. Never lower privacy silently for video. |
| Private application counts versus public aggregate | Organizer workflow totals and private answers require separate projection. Accepted public totals can be visible without exposing application-review counts. |
| Governance metadata-only input, local evidence, inline image data | Durable original upload/storage/access/retention needed; metadata or a client URL is not verified bytes. |
| Scheduling and notifications are intent/placeholder | Durable scheduling/outbox and actual delivery state needed before claiming sends. Draft invites do not grant access; RSVP is not attendance; suggested meeting follow-ups do not commit plan changes. |
| Generic blank-event planning fallback | Current controls primarily edit existing plan nodes; no verified generic add-stage/add-work workflow was found. Decide manual fallback/import or provider-assisted drafting before a new arbitrary event must progress during model outage; do not silently seed cleanup work. |
| Join/Support enabled-state rule | Preserve the current same-event UI behavior, but enforce uniqueness/permissions server-side. Support currently opens information; it is not a payment/pledge. Whether a joined person may represent an organization is a separate policy. |
| Partial resource effects/retries | A receipt or consumption correction needs unique effect identity and original lineage. Reused references across partial effects cannot grant duplicate stock or reject legitimate separate actions accidentally. |
| Service/facility/funding support | Do not treat an accepted pledge as delivered stock, money as units, or a proposed facility as a verified time booking. Add capacity booking/payment integrations only with an actual approved flow. |
| Maps/AI/media capabilities | No live geocoding, model, transcription, SAM or historical RAG integration exists. Do not fabricate coordinates, measured quantities, provider success or meeting URLs. |

The five highest-risk cross-module inconsistencies are: plan/publication/assignment version mismatch; approval confused with accepted capacity; sponsor pledge confused with available inventory; report/AI analysis confused with verified execution and ledger effects; and private participant answers leaked through public insight/read projections. Integration tests must exercise each boundary negatively as well as positively.

## J. Exact next-step files, verification and stop boundary

### Proposed first implementation change â€” only after review

These paths are **not created by this research task**. The proposed first coding PR establishes persistence/auth boundaries and read projections only, not broad commands, AI integrations or a complete backend:

```text
backend/pyproject.toml
backend/alembic.ini
backend/.env.example
backend/README.md
backend/app/__init__.py
backend/app/main.py
backend/app/settings.py
backend/app/api/__init__.py
backend/app/api/dependencies.py
backend/app/api/errors.py
backend/app/access/__init__.py
backend/app/access/authentication.py
backend/app/access/authorization.py
backend/app/access/models.py
backend/app/access/router.py
backend/app/events/__init__.py
backend/app/events/models.py
backend/app/planning/__init__.py
backend/app/planning/models.py
backend/app/publication/__init__.py
backend/app/publication/models.py
backend/app/publication/queries.py
backend/app/publication/schemas.py
backend/app/publication/router.py
backend/app/participation/__init__.py
backend/app/participation/models.py
backend/app/participation/queries.py
backend/app/participation/schemas.py
backend/app/participation/router.py
backend/app/shared/__init__.py
backend/app/shared/database.py
backend/app/shared/unit_of_work.py
backend/app/shared/audit.py
backend/app/shared/idempotency.py
backend/migrations/env.py
backend/migrations/script.py.mako
backend/migrations/versions/0001_read_model_foundation.py
backend/tests/conftest.py
backend/tests/test_authentication.py
backend/tests/test_event_visibility.py
backend/tests/test_my_events_relationships.py
backend/tests/test_public_profile_projection.py
backend/tests/test_database_constraints.py
```

The identity-provider choice may add its dedicated adapter/config file after decision 1; do not implement password storage speculatively. A minimal `/health` route and test may live in `main.py`/foundation tests. Existing `.gitignore` should be modified only to exclude backend environment/cache artifacts; dependency lockfile generated by the chosen Python package manager must be committed with the approved implementation.

**Later frontend integration files, not part of that initial backend foundation:** create `frontend/src/services/http-adapter.ts`; modify `frontend/src/app/provider.tsx`, `frontend/src/services/contracts.ts`, `frontend/src/features/event-creation/model.ts` and the scoped feature contracts only for reviewed transport/source variants. Verify actual filenames again at implementation. No frontend change is authorized by this report. Do not create a second participant workspace or organizer dashboard.

### Research verification performed

- Parsed the frontend with its installed TypeScript compiler API; inventoried 100 source files, 29 routes, observed controls and service call expressions.
- Reconciled 114 observed command names and 27 service methods against the catalogue: **zero unmapped names**. The 183 source-interaction rows retain call-site references/current arguments; 13 infrastructure-support entries are explicitly additions and eight operations are demo-only.
- Ran `node demo/src/validate.mjs`: **valid**, no errors. This validates clean fixture references/invariants, not production SQL/API behavior.
- Recorded hashes of reviewed frontend/demo sources to check that the audit did not change application code.
- Reviewed existing tests and architecture/research documentation. No backend tests exist. No TypeScript build or frontend/domain test suite was rerun for these documentation-only changes; previous logs are not claimed as fresh passes. No browser/screenshot/visual verification was performed or claimed.

Generated audit scripts and coverage artifacts are under `outputs/backend-contract-audit/`; they are analysis tools, not application runtime code. The only deliverables are this report, its API/data-model companions and interaction inventories. **Stop here for review. No backend business logic, migrations, deployment, frontend behavior or demo data has been implemented or changed.**


## Review correction: Event Memory from Day 1

This section supersedes any earlier implication that reusable event knowledge begins only as a later RAG experiment. It updates the module, database, API, orchestration and implementation boundaries while retaining all accepted frontend interactions. Detailed memory schemas and endpoints are in [the data model](backend-contract-data-model.md#8-event-memory--derived-intelligence-day-1) and [the API addendum](backend-api-contract-catalogue.md#event-memory--day-1-design-addendum).

### D/E amendment — memory ownership and semantics

`memory` is a package inside the **same FastAPI modular monolith**, using PostgreSQL and the shared UoW/jobs/audit facilities. It owns derived memory versions, source links, extraction attempts and retrieval manifests. Planning, participation, resources, execution and blockers retain their operational ownership. A memory entry can explain why a choice worked under particular conditions; it cannot establish current inventory, current assignments, legal permission, work completion or a new active plan.

Support these source-linked kinds: event/context; plan/work/dependency pattern; decision/rationale; execution attempt; blocker; recovery attempt; and outcome/lesson. Kinds are general-purpose, not waste-specific. For example, a projector shortage in a literacy workshop and transport limitations in an environmental initiative can share a resource-capacity lesson only when their applicability conditions match. A failed attempt is retained with the conditions and evidence that establish failure; do not retrieve only positive stories.

**Separate three axes:**

- Memory lifecycle: `candidate`, `published`, `superseded`, `retracted`. Published means eligible for authorized retrieval, not publicly visible or operationally verified.
- Evidence progression: `proposed`, `attempted`, `verified`. A proposed plan/recovery idea is not an attempted action; an attempt requires an execution/attempt source; verified requires an authorized source decision about the stated observation.
- Outcome: `unknown`, `successful`, `failed`, `mixed`, `inconclusive`. A source-supported success/failure requires explicit scope, evaluation criteria and an authoritative human review or recorded deterministic operational decision. A model may suggest a classification in its candidate payload, but cannot promote it to a verified assertion. Human review of prose alone cannot upgrade unverified source evidence.

A human can explicitly record a bounded observation as verified while its broader outcome remains inconclusive. An accepted assignment does not imply attendance; a reserved item does not imply delivery or consumption; a proposed/activated recovery does not imply it succeeded. Source state and source version are mandatory for each assertion, including negative outcomes. Preserve original evidence and decision histories rather than replacing them with summaries.

**Applicability** is structured: event category/tags, goal, work pattern, scale and units, location/environment where relevant, time/calendar constraints, required skills, participant capacity, resource assumptions, exclusions, relevant policy versions and explicit unknowns. Conditions are optional only when genuinely irrelevant; unknown conditions remain unknown and lower applicability. Do not infer demographics or compatibility from persona/category alone. Store facts separately from hypotheses and generalized recommendations.

**Confidence/provenance** distinguish source-supported verification from model-reported confidence and retrieval relevance. Store origin (deterministic projection, human-authored or model-extracted), source IDs/versions/hashes, reviewer/decision, model profile and schema/prompt versions, uncertainty and applicability reasons. An optional model confidence is uncalibrated until tested; it is not an authorization or success threshold. An unavailable confidence stays null. Retrieval scores rank relevance, not truth.

### G amendment — extraction, retrieval and model ports

**Extraction path:** owning domain transaction commits original/versioned source and an outbox intention → memory worker loads permitted immutable source revisions → deterministic source projection or bounded open-weight extraction → strict candidate schema and reference validation → pending memory candidate → authorized review where synthesis/generalization is involved → publish eligible derived version. Deterministic projections may publish automatically only when they faithfully copy already-authorized source facts under a registered projection policy. They cannot add success labels, permissions or inferred lessons. Day 1 uses this projection path with a fake extraction port for tests; the live model is not a dependency of business commits.

A source transaction must not wait for Modal or Muse Spark. Outbox uniqueness by source revision/extractor schema prevents duplicate captures. Extraction retries retain attempts and use bounded leases/fencing; no permission to run business commands is passed to the extractor. Missing/deleted/corrected sources invalidate eligibility even if the worker has not yet processed an invalidation event. A memory extraction failure does not roll back the operational event; it remains a retryable, visible intelligence-layer failure.

**Retrieval path:** application service derives actor, event, purpose and permitted scope → memory query enforces access and current source eligibility before ranking → structured applicability filtering and bounded lexical ranking → return citations, evidence/outcome states, conditions, caveats and retrieval manifest → planning/recovery context builder combines these with the current authoritative graph. No raw SQL, unrestricted event list or model-selected actor identity is accepted as a retrieval tool argument. Cache keys include actor/scope/permission epoch, purpose, source/version manifest and query; never share a private retrieval cache across viewers.

Initial PostgreSQL filters/text search are sufficient. Embeddings, if later useful, are rebuildable indexes of approved memory text and never the authority. A vector hit must be reauthorized and checked against current memory/source versions before returning. Retrieval must work without a model. Zero eligible memories returns an empty result with reasons, never invented precedent.

Three internal integration ports:

1. `MemoryExtractionPort.extract(ExtractionInput) -> MemoryCandidateBatch`: designed for an explicitly selected **open-weight model hosted on Modal**. Input contains only authorized, minimized source excerpts and immutable references, extraction schema version and budget. Output is bounded candidate assertions with exact source references, applicability, uncertainty and proposed classifications. No operational mutation tools. Implementations must disclose model/checkpoint/runtime identity and tested capabilities; URL, authentication, model choice and provider-specific request parameters remain configuration/proof-of-concept decisions, not invented APIs.
2. `MemoryRetrievalPort.retrieve(RetrievalQuery, AccessScope) -> MemoryBundle`: PostgreSQL implementation first, model-independent, with deterministic eligibility and bounded results. The caller cannot broaden `AccessScope` through a prompt.
3. `PlanningContextPort.build(CurrentState, MemoryBundle) -> ScopedPlanningContext`: used by Muse Spark stage/work planning and blocker recovery through the existing AI provider boundary. Current authoritative inputs and historical derived memory are separate labeled sections. Record chosen/rejected memory IDs/revisions, retrieval reasons and citations in the AI run context manifest; keep source-linked attribution in proposals.

A shared provider transport may be reused by memory extraction and existing AI adapters, but the ports/permissions differ. No claim is made that Modal and Meta share model APIs, tool behavior or schema guarantees. A live Modal extraction adapter and Muse Spark consumer must pass contract/latency/privacy evaluations before enabling them. No deployment, model endpoint or credentials are created in this design task.

**Muse Spark cannot use retrieved memory as authority.** A historical successful recovery is only a candidate idea under matched conditions; revalidate current graph, skills, quantities, reservations and consent. A failure memory should flag conditions to avoid, not force a plan change. A stale memory used in an already-running proposal marks that proposal/context stale or requires regeneration before apply; recheck both current operational source versions and retrieved memory eligibility at human review/activation. Do not reactivate/rewrite an old plan through memory.

### Privacy, scope and correction invariants

- Default retrieval is the current event's permitted records. Joining an event does not grant its private applications, notes or original evidence. Reviewers need explicit scopes; stage leads see only granted work/stage sources.
- Cross-event reuse requires an explicit reusable visibility policy and sanitized published memory. Event ownership alone does not authorize another event's private evidence. Return only share-approved excerpts/citations; a citation's existence/title can itself leak information. Private source links stay protected even behind a reusable summary.
- Public insights retain existing consent/aggregation thresholds. Do not store raw participant answers, faces, contact details, access tokens or sensitive audio as reusable memory text. A sanitized lesson can cite an opaque authorized source reference; it cannot expose personal evidence via retrieval URLs.
- Distinguish event-view access, source access and permission to extract/review/share memory. Backend derives actor from authentication; model output cannot choose visibility or grants.
- Corrections create a new derived revision linked by `supersedes_id`, plus a reason and correcting source/decision. Preserve immutable history subject to retention/deletion policy. Default retrieval excludes superseded/retracted entries and any unsupported stale assertion. Source corrections/revoked sharing take effect at read-time checks immediately, not only eventual index refresh.
- Deletion/retention can erase protected text and derived indexes while retaining a minimal non-sensitive tombstone/hash/audit where lawful. Decide retention explicitly; append-only audit is not a blanket reason to retain personal content forever.

### H amendment — five implementation groups, small vertical slices

The repository report did not contain named definitions for the user's **five approved backend groups**. The following are working alignment labels for the existing sequence, not a claim that new names/boundaries were approved. If those group names differ, map these slices to them before coding; this correction does not expand into five services or reorder domain authority.

| Group / working alignment | Small tested vertical slices | Memory integration from the first relevant source |
|---|---|---|
| 1. Foundation, access and Event Memory | Database/UoW + authenticated scoped reads; source-version capture → deterministic memory projection → authorized retrieval | First-class schemas/ports, source lineage, proposed plan/decision memories, source correction/invalidation; no live model required. |
| 2. Event planning and publication | Generic context → draft plan/requirements → confirmation → coherent publication | Capture exact confirmed/proposed plan and decision sources; supply scoped historical context to pending planning proposals. |
| 3. Participation and resource commitments | Application → human review → exact offer → acceptance; sponsor pledge → reviewed receipt → reservation | Capture only source-backed transitions/conditions, not inferred attendance or inventory. Preserve ten-participant scenario semantics. |
| 4. Execution, evidence and coordination | Original report/upload → authorized review → deterministic work/resource effects; meetings/follow-ups as separate slices | Attempt/verification/outcome lineage, corrections, privacy-safe extraction. Completion and consumption remain separate. |
| 5. Blocker recovery and intelligence | Actual dependency impact → scoped pending proposal → review/renewed consent → atomic or deferred new plan version | Retrieve successes AND failures with applicability; capture attempts and subsequently reviewed outcomes. Preserve blocker-recovery replay and stale-output checks. |

No group requires implementing all of its tables/routes at once. The 142 accepted proposed HTTP contracts remain a backlog, not a first milestone. New memory endpoints below are separate additive support contracts; no frontend route/component or `AroundYouService` method needs changing in Group 1.

### Updated Group 1 — smallest coherent foundation implementation (next, after review)

**Demonstrable path:** authenticated actor reads one permitted event's versioned plan/decision source → deterministic memory projection records source-linked facts (usually proposed/confirmed-plan facts, not execution success) → authorized retrieval returns conditions, provenance and exact citations → source correction/supersession removes the old version from default retrieval. A forbidden actor gets no existence/title/text leak. No full planning/execution mutation workflow is required to prove this foundation.

Minimal source persistence: users/session boundary, events + event grants, immutable event context and plan versions, typed review decisions, and minimal audit/idempotency/outbox/job records. Persist no application/assignment/source table solely to fill the schema: use test source adapters for future kinds and add real domain tables with their slice. Stable source registration must point to genuine persisted versions; a generic source registry is a locator, not an operational record store. Original evidence references use a source resolver port now; real media upload/execution tables arrive with Group 4, and cannot be fabricated by this module.

Minimal memory persistence: `memory_entries`, `memory_sources` and `memory_runs` as specified in the data-model addendum. Store immutable assertion/retrieval schema versions, lifecycle and source-linked state. Persist extraction/retrieval run manifests for traceability; do not persist a second mutable summary of operational state. PostgreSQL lexical queries only; no vector database, separate service or model infrastructure.

Initial exposed contracts: `GET /v1/me`, `GET /v1/events/{event_id}/memory`, `GET /v1/events/{event_id}/memory/{memory_id}`; authorized `POST .../memory/extractions` and extraction status lookup to exercise durable projection; the correction/review service must be tested internally, with its HTTP endpoints delivered only if required to demonstrate that slice. Public profile/My Events read adapters may follow as a separately tested Group 1 slice when their authoritative source tables are included; the earlier broader first migration is narrowed accordingly. Do not ship accepted-assignment read claims without the actual assignment/consent records.

**Group 1 acceptance tests:** PostgreSQL migration and FK/scope constraints; auth allow/deny; allowed current source projected once despite duplicate outbox delivery; crash/retry/fencing; candidate schema rejection (invented source IDs, visibility, outcome promotion); proposed vs attempted vs verified separation; success/failure requires proper source decision; exact source correction and stale-source read exclusion; cross-event and private citation denial; minimized cross-event reusable lesson policy; empty retrieval; deterministic ranking/limit; fake Modal port records provenance but cannot mutate any operational table; Muse Spark context-builder contract keeps historical memory separate from current facts. Use ordinary PostgreSQL integration tests, not only mocks. Run the existing ten-participant and recovery replay tests unchanged as regression checks; no seed/scenario rewrite.

**Exact Group 1 file amendment to J (proposed files only):** retain the selected foundation `backend/pyproject.toml`, settings/main/API dependencies/errors, access authentication/authorization/models/router and shared database/UoW/audit/idempotency files from J. Replace the broad `0001_read_model_foundation.py` plan with `backend/migrations/versions/0001_access_event_memory_foundation.py`. Add:

```text
backend/app/events/source_revisions.py
backend/app/planning/models.py
backend/app/shared/source_resolver.py
backend/app/shared/outbox.py
backend/app/shared/jobs.py
backend/app/memory/__init__.py
backend/app/memory/models.py
backend/app/memory/schemas.py
backend/app/memory/ports.py
backend/app/memory/authorization.py
backend/app/memory/service.py
backend/app/memory/repository.py
backend/app/memory/projections.py
backend/app/memory/retrieval.py
backend/app/memory/router.py
backend/app/memory/worker.py
backend/app/ai/context_builder.py
backend/tests/test_memory_source_projection.py
backend/tests/test_memory_authorization.py
backend/tests/test_memory_outcomes.py
backend/tests/test_memory_supersession.py
backend/tests/test_memory_jobs.py
backend/tests/test_memory_provider_ports.py
backend/tests/test_memory_planning_context.py
```

`ports.py` defines the Modal-oriented extraction interface; tests use a fake. **No live Modal/Muse Spark adapter, provider SDK, endpoint, embeddings, upload service, frontend edit, operational CRUD or model deployment is in Group 1.** Add empty package initializers only where required by the selected packaging layout, not empty modules for every future feature. Publication/participation query/model/router files from the earlier J list are deferred to the appropriate read slice rather than created speculatively.

All changes in this review correction are documentation only. The existing AroundYouService, modular backend choice, all event categories, original evidence/versioned plans, human approval, actual participant/resource transitions and both demo scenarios are preserved. Stop for review of Group 1 before implementation.
