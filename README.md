# AroundYou

### From an Idea to a Community-Powered Event

**AI-assisted community planning, participation, governance and real-world execution — with people in control.**

AroundYou helps individuals and community groups turn an idea into a coordinated event: understand the goal, plan the work, recruit contributors, organize support, track execution and respond when conditions change.

The platform supports education, animal welfare, health awareness, cultural activities, environmental action and neighborhood support. Canary Hill cleanup is a demonstration scenario, not a universal event template.



## Problem and solution

People often have the willingness to create something meaningful but lack the resources, expertise and connections to make it happen. Even a small community event involves permissions, safety, practical scheduling, staffing, supplies, changing availability and accountable execution. Professional coordination can be costly, while discovery and registration alone do not solve these operational problems.

AroundYou brings these responsibilities into one connected experience. Specialized AI workflows propose plans and recommendations; deterministic services validate them; organizers and participants make the decisions that create real commitments.

**Idea → Planning → Community Support → Execution → Recovery → Reviewed Outcomes**

## Product capabilities

| Capability | Current implementation |
| --- | --- |
| Event discovery and My Events | Location-based discovery, category icons, public profiles, organizer-owned event lists and saved workflow resume. Fictional map positions are labeled as approximate demo localities. |
| Event creation | Saved multi-step forms, written or recorded execution explanations, editable transcripts and scoped event-understanding proposals. |
| Governance guidance | Contextual document and safety recommendations, human review, internal follow-up tickets and optional private PDF/image uploads. Guidance is advisory, not government or legal approval. |
| Stage and work planning | Editable Gantt timelines, dependencies, stage-specific Work Design, resource estimates and actor requirements derived from work. Missing estimates stay unknown or require review. |
| Participation | Availability and experience capture, optional role-fit suggestions, application review, specific assignment offers and participant acceptance. Approval alone never assigns work. |
| Participant workspace | Overview, My Roles, Schedule, My Work, Updates, Meetings and Blockers, scoped to the selected event and authorized responsibilities. |
| Sponsor and resource coordination | Separate organization signup and Sponsor Portal, opportunities, offers and commitments, sponsored-event map, impact/history, delivery verification, reservations, consumption and equipment returns. Funding records are not payment processing. |
| Execution and evidence | Assigned-work updates, original private attachments, progress/completion claims, optional model observations and separate human review/completion decisions. |
| Meetings and updates | Coordination records, invitee/RSVP management, follow-ups and targeted in-app recovery updates. These do not host calls or send external invitations. |
| Blocker investigation and recovery | Human investigation, affected dependency scope, local reviews, optional AI suggestions, recovery approval, participant reconfirmation and separate validated activation. |
| Outcomes and Event Memory | Source-linked records, provenance checks, correction/supersession and reviewed memory retrieval. Synthetic scenarios cannot become trusted real-event knowledge. |

Public participant insights use configured, consented aggregate responses and privacy thresholds. They do not expose private application answers or infer demographics from account personas.

## End-to-end event lifecycle

1. **Discover or create:** Sign up as a personal user or organization, explore nearby events, or save an event brief.
2. **Understand and review:** Describe intent, scope, limitations and known resources. Review AI interpretation and optional governance guidance; upload supporting documents when useful.
3. **Plan:** Generate and edit stages, work items, dependencies, resource requirements and a stage-connected workforce tree. Confirm reviewed plans.
4. **Set up and publish:** Configure access, participation, resources and communications, then finalize and publish the reviewed configuration.
5. **Recruit and commit:** Participants supply availability and experience, choose roles and submit applications. Organizers review requests and offer exact work terms; participants accept or decline.
6. **Execute and observe:** Participants start assigned work, report progress and attach original evidence. Authorized humans review claims and confirm completion separately.
7. **Investigate and recover:** Review a blocker, identify affected work and people, evaluate manual or AI-assisted changes, approve the exact proposal, obtain changed commitments and validate activation.
8. **Review and learn:** Record supported outcomes and extract source-linked candidate memories. Human review and provenance determine eligibility for future retrieval.

Confirmed plans and accepted terms are versioned. Model advice, organizer approval, participant consent, activation and verified outcomes remain distinct states.

## Meta AI integrations

| Technology | Role and verified boundaries |
| --- | --- |
| **Muse Spark — `muse-spark-1.3`** | Server-side understanding, governance, stage/work/actor proposals, participation advice, evidence interpretation and scoped recovery. Responses are schema- and source-validated before becoming pending proposals. Live checks are recorded in implementation reports; failed or questions-only responses are not presented as completed plans. |
| **Muse Voice Transcribe — `muse-voice-transcribe-1.0`** | Transcribes captured/uploaded explanations and execution audio. Originals, machine transcripts and reviewed corrections remain distinct. FFmpeg/ffprobe normalize audio; the implemented limit is 60 seconds. |
| **SAM 3.1 — `sam-3.1`** | Concept-based segmentation using actual evidence images. A dedicated garbage-photo check returned three bag regions, three mask records and three normalized boxes. Mask wire records are preserved; raster-mask rendering is not implemented. Geometry alone cannot prove an area is clean or work is complete. |
| **Modal-hosted Event Memory extractor** | Uses **Qwen/Qwen2.5-1.5B-Instruct**, pinned to revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Qwen is not a Meta model. The constrained extractor selects exact source-linked factual excerpts, not independently verified outcomes or unrestricted generalized lessons. A bounded live test persisted a pending synthetic candidate, which was blocked from trusted publication. |

Modal is an internal extraction provider: T4, zero minimum/warm containers, maximum one container and one input, 30-second scale-down, 120-second timeout and zero automatic retries in the prepared deployment. The adapter is disabled by default. A separately verified extractor deployment does **not** mean the overall product is publicly deployed.

Image analysis currently enforces a 2 MB / 2048-pixel-per-dimension input limit. Larger original uploads do not automatically become valid analysis inputs. Full video interpretation is not implemented.

See the [SAM verification](docs/implementation/sam-garbage-verification.md), [voice and evidence integration](docs/implementation/prompts5-6-participation-execution.md), [Modal structured extraction](docs/implementation/modal-structured-extraction-fix.md) and [live recovery verification](docs/implementation/final-spark-recovery.md) reports for tested boundaries.

### Eight specialized agents

These are specialized application workflows within one backend, not eight independently deployed services or unrestricted autonomous workers.

| Agent | Responsibility |
| --- | --- |
| **Event Understanding** | Interpret intentions, goals, scope, constraints and unresolved questions. |
| **Governance Advisor** | Propose applicable document, coordination and safety considerations for organizer review. |
| **Stage Planning** | Propose stages, sequence, timelines and dependencies. |
| **Work & Actor Planning** | Derive work, resource estimates, skills, roles and required headcounts, one selected stage at a time. |
| **Participation & Resource** | Support role suitability and contributor/resource coordination without approving applicants, assigning people or verifying stock. |
| **Execution Intelligence** | Interpret reports, transcripts and image observations against work requirements; return advisory observations. |
| **Recovery** | Propose bounded alternatives for the affected dependency scope, preserving unrelated work and requiring reviewed changes. |
| **Event Memory** | Project, extract and retrieve applicable source-linked knowledge, preserving privacy, provenance and outcome distinctions. |

Provider coverage differs by workflow. Sponsor/resource views also use deterministic matching and accounting; not every recommendation invokes AI. Memory extraction currently uses the bounded Qwen path described above.

### Agent orchestration

**Understand → Plan → Validate → Human Decision → Coordinate → Observe → Recover → Learn**

A frontend action passes through `AroundYouService` to an authenticated application service. The service loads permitted, versioned state and applicable memory, builds scoped context, requests model output and validates it before saving a pending proposal.

Human confirmation invokes deterministic domain services to commit changes. Stale plans, unsupported references, invented evidence, invalid quantities and unauthorized edits are rejected. AI never directly changes plans, permissions, participant consent, inventory or verified outcomes.

For recovery, the backend computes the affected dependency subgraph before requesting scoped advice. Local review, overall approval, revised participant consent and activation are separate operations. A no-change review can be saved, but the current API requires changed fields or an explicit hold before creating an approvable recovery alternative.

## System architecture

One **FastAPI modular monolith** owns operational rules and PostgreSQL persistence. The React service boundary selects HTTP integration or the separate replay implementation.

This logical overview adapts the existing [architecture diagram](docs/architecture/backend-architecture-proposal-round-1.md#11-runtime-shape) to current code. It is **not production infrastructure**; proposed external notification adapters are omitted.

```mermaid
flowchart TD
    UI[React frontend] --> SERVICE[AroundYouService / HTTP adapter]
    SERVICE --> API[FastAPI authentication and event authorization]
    API --> APP[Application services and deterministic validation]
    APP --> DB[(PostgreSQL: operational state and audit)]
    APP --> FILES[Private original evidence storage]
    APP --> JOBS[Durable AI runs, jobs and outbox]
    JOBS --> CONTEXT[Scoped context and authorized Event Memory]
    CONTEXT --> META[Muse Spark / Muse Voice / SAM adapters]
    META --> PROPOSAL[Validated pending proposals and observations]
    PROPOSAL --> HUMAN[Authorized human review]
    HUMAN --> APP
    JOBS --> MEMORY[Derived memory projection and extraction]
    MEMORY --> MODAL[Optional Modal Qwen extractor]
    MODAL --> CANDIDATE[Source-linked candidate memory]
    CANDIDATE --> DB
```

Event Memory is a derived intelligence layer in the same PostgreSQL database, not a competing operational source of truth. Original evidence stays private; citations, source revisions, permissions and correction history control reuse.

## Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, React Router, Lucide icons, existing CSS |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, psycopg |
| Database | PostgreSQL 16; persistent local Docker volume |
| Model providers | Meta Model API; optional Modal-hosted pinned Qwen extractor |
| Media | Browser MediaRecorder, FFmpeg/ffprobe, Pillow, authenticated private storage |
| Discovery | Google Maps JavaScript API / Places and stored event coordinates |
| Reliability | Transactional unit of work, expected versions, idempotency, durable jobs/outbox and audit |
| Tests | pytest, PostgreSQL integration tests, Vitest, Testing Library and Node replay tests |

## Local setup and run

### Prerequisites and checkout limitations

- Python **3.12+**, Node.js **22+** and npm.
- Docker Desktop running with PostgreSQL **16**, or an existing intended PostgreSQL database.
- FFmpeg and ffprobe on `PATH` for voice conversion; manual text remains usable without them.
- Provider credentials only for features you explicitly intend to invoke.

**Current packaging limitation:** `.gitignore` excludes `demo/` and fixture JSON. The frontend still imports replay modules from that directory, and Vite reads `demo/fixtures` even in HTTP mode. A fresh GitHub checkout without those files cannot yet build or run the full frontend test suite. Obtain the existing demo source/fixtures from the maintainer; no download or generation command is supplied here. This README does not change that exclusion or upload demo data.

Commands below use **Windows PowerShell**, from the repository root unless stated otherwise. Preserve existing local environment files.

### 1. Install backend dependencies

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

The editable installation also installs dependencies declared in `pyproject.toml`, including image support. The optional Modal SDK is not needed for basic application startup.

### 2. Configure private backend settings

Create `backend/.env` locally. Replace placeholders; never commit actual values.

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/aroundyou
SESSION_SECRET=REPLACE_WITH_A_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS
META_AI_ENABLED=false
META_MODEL_ID=muse-spark-1.3
MODAL_MEMORY_ENABLED=false
```

Generate a session secret without printing it, from `backend`. Do this once for a new setup; rotation invalidates existing signed tokens.

```powershell
.\.venv\Scripts\python.exe -c "import secrets; from dotenv import set_key; set_key('.env', 'SESSION_SECRET', secrets.token_urlsafe(48))"
```

| Optional setting | Purpose |
| --- | --- |
| `META_API_KEY`, `META_AI_ENABLED=true` | Enable the server-side Meta provider for explicit inference actions, which may incur charges. |
| `EVIDENCE_DIRECTORY` | Absolute private directory outside web roots, such as `C:/AroundYouPrivate/evidence`; required for original execution/governance uploads. |
| `VOICE_DIRECTORY` | Private voice storage; defaults to the backend's ignored `.private/voice` directory. |
| `MODAL_MEMORY_ENDPOINT` | Authenticated extractor endpoint; keep the actual value private. |
| `MODAL_MEMORY_PROXY_KEY`, `MODAL_MEMORY_PROXY_SECRET` | Endpoint proxy authentication, distinct from CLI management credentials. |
| `MODAL_MEMORY_ENABLED=true` | Opt in to configured extraction. Leave false until intentionally enabled. |

Modal CLI credentials may stay in the CLI credential store. Never put Meta keys, Modal secrets, database credentials or private storage paths in frontend variables. Provider configuration does not grant business-state authority.

### 3. Prepare PostgreSQL and migrations

Inspect Docker before creating anything:

```powershell
docker version
docker ps -a
docker volume ls
```

For a **new** setup with placeholder database credentials and no existing AroundYou container/volume, run the helper from `backend`:

```powershell
.\.venv\Scripts\python.exe tools/setup_docker_development.py
```

It creates `aroundyou-postgres-dev`, persistent volume `aroundyou-postgres-dev-data`, database `aroundyou` and dedicated role `aroundyou_app`. It generates private credentials, updates only `DATABASE_URL` and selects an available loopback port from 5432–5434. Existing AroundYou containers, volumes or non-placeholder database settings cause it to stop rather than overwrite data.

For existing installations, inspect and reuse the intended database. Start the existing container if stopped; do not rerun setup to reset it. The helper does **not** apply migrations.

After verifying the intended development `DATABASE_URL`:

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Migrations run from `0001` through `0010_memory_data_class`. Startup does not apply them automatically. Do not downgrade or reset an application database.

### 4. Start FastAPI

In `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001
```

For durable memory/outbox processing, use a separate terminal in `backend`:

```powershell
.\.venv\Scripts\python.exe -m app.cli worker
```

The CLI worker processes outbox/memory jobs; explicit Meta routes use the existing background-run workflow. Starting it does not deploy Modal or run verification harnesses. Leave provider flags disabled when inference is not intended.

### 5. Configure and start React

Create `frontend/.env.local`:

```dotenv
VITE_AROUNDYOU_MODE=http
VITE_AROUNDYOU_API_URL=http://127.0.0.1:8001
```

Optional Maps settings are `VITE_GOOGLE_MAPS_API_KEY` and `VITE_GOOGLE_MAPS_MAP_ID`. Browser Maps keys are exposed by design; restrict their APIs and development referrers. Without configuration, do not expect a functioning live Google map.

In a separate terminal, from the repository root:

```powershell
cd frontend
npm ci
npm run dev -- --port 5173 --strictPort
```

Use `127.0.0.1` consistently for frontend and API so browser session cookies remain same-site. Inspect existing services before starting another instance on an occupied port. Restart Vite after environment changes.

| Local page | URL |
| --- | --- |
| Landing page | <http://127.0.0.1:5173/> |
| Personal / organization signup | <http://127.0.0.1:5173/signup> |
| Sign in | <http://127.0.0.1:5173/signin> |
| FastAPI contracts | <http://127.0.0.1:8001/docs> |
| OpenAPI JSON | <http://127.0.0.1:8001/openapi.json> |
| Process health | <http://127.0.0.1:8001/health> |

`/health` indicates process availability, not database/provider connectivity. Live signup uses password-backed browser sessions; replay identities are not production authentication.

The existing Windows launcher `backend/tools/start_live_runtime.ps1` can start a free API port between 8001–8010, update the frontend API URL and open signup after dependency/database setup. It is an alternative to manual startup, not a deployment command. The older `start_local_runtime.ps1` provisions development identities and creates verification data; it is not recommended for a clean walkthrough.

## Testing

These are reproducible commands, **not a claim that full suites were rerun for this README**. Tests use model fakes; separate live-verification tools can spend credits and are not ordinary tests.

### Frontend

From `frontend`, with required replay files present:

```powershell
npm run typecheck
npm test
npm run build
# Focused investigation and recovery checks:
npm test -- tests/blocker-investigation.test.tsx tests/prompt7-workspace.test.tsx tests/recovery.test.tsx
```

The production build currently reports a non-failing large-bundle warning. Automated UI tests are not browser screenshot acceptance.

### Backend

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Database-dependent tests skip when test database settings are absent. A skip is not a pass. Integration fixtures downgrade/rebuild and truncate their **disposable test databases**.

For the isolated runner, install PostgreSQL 16 server/command-line binaries in addition to Docker:

```powershell
$env:PG_BIN = 'C:/Program Files/PostgreSQL/16/bin'
.\.venv\Scripts\python.exe tools/run_postgres_tests.py -q --tb=short
```

Alternatively, supply `TEST_DATABASE_URL` and `TEST_MIGRATION_DATABASE_URL` for two dedicated disposable PostgreSQL databases whose names end in `_test`, then run pytest. **Never use `aroundyou` or any database containing project/personal data for those settings.** `AROUNDYOU_MIGRATION_DATABASE_URL` is an explicit migration override; ensure it is not accidentally pointing elsewhere during normal setup.

### Replay/domain regressions

If the locally excluded `demo/` directory is available, from the repository root:

```powershell
cd demo
npm test
npm run validate
```

Replay data is fictional. Model detections, attendance, commitments and verified outcomes must not be inferred from a fixture or account's existence.

## Demo and screenshots

| Deliverable | Status |
| --- | --- |
| Live frontend URL | **TODO — deployment not completed** |
| Backend / API deployment URL | **TODO — deployment not completed** |
| Demo video URL | **TODO — add final recording** |
| Product screenshots | **TODO — add reviewed, privacy-safe images** |
| Production architecture/deployment details | **TODO — document after infrastructure is selected and deployed** |

Suggested recording: create an event → review understanding/governance → edit Gantt and Work Design → confirm workforce → publish → participant application and exact offer acceptance → work report/blocker → impact investigation → recovery review → participant reconfirmation. Demonstrate only states and provider results actually reached.

The ten-participant and blocker-recovery replays remain separate from genuine operational records. Approximate demo map points retain their labels; they are not verified venues.

## Documentation

Implementation reports are dated verification records. Earlier proposals and the backend README contain historical limitations superseded by later work; current code and installed OpenAPI remain the API reference.

| Document | Purpose |
| --- | --- |
| [Original README draft](readmepractise.md) | Product vision and eight-agent reference |
| [Frontend/backend inventory](docs/architecture/frontend-backend-contract-and-plan.md) | Screen interactions, service boundary and integration plan |
| [API catalogue](docs/architecture/backend-api-contract-catalogue.md) | Proposed contracts; not every proposed endpoint is implemented |
| [Data model](docs/architecture/backend-contract-data-model.md) | Operational and memory entities |
| [Architecture refinement](docs/architecture/backend-architecture-refinement-round-2.md) | Planning, participation, resources and deterministic boundaries |
| [Meta technical study](docs/research/meta-ai-technical-study.md) | Reviewed capabilities and limitations |
| [AI adapter design](docs/research/ai-provider-adapter-design.md) | Provider boundaries and scoped context |
| [Accounts and Maps](docs/implementation/prompt1-live-accounts-maps.md) | Browser authentication and navigation |
| [Planning integration](docs/implementation/prompt3-meta-planning-report.md) | Stage, work and actor proposal integration |
| [Execution and media](docs/implementation/prompts5-6-participation-execution.md) | Participation, evidence, voice/image processing and limitations |
| [SAM verification](docs/implementation/sam-garbage-verification.md) | Actual geometry, parsing and source linkage |
| [Recovery and memory](docs/implementation/prompt7-recovery-memory.md) | Selective recovery and human decisions |
| [Live Spark recovery](docs/implementation/final-spark-recovery.md) | Genuine provider result and verification limits |
| [Modal structured extraction](docs/implementation/modal-structured-extraction-fix.md) | Constrained extraction and synthetic provenance guard |
| [Backend historical notes](backend/README.md) | Original group-by-group implementation records |
| [Demo data guide](DEMO_DATA_GUIDE.md) | Local connected scenarios |

**Planned consolidated guides — not yet present:** `docs/JUDGES_GUIDE.md`, `docs/PRODUCT_CAPABILITIES.md`, `docs/AGENT_ARCHITECTURE.md`, `docs/SYSTEM_ARCHITECTURE.md`, `docs/EXECUTION_AND_RECOVERY.md` and `docs/TESTING_AND_EVALUATION.md`. These are not linked to missing files. A production deployment guide remains to be written after deployment decisions.

## Future Roadmap

- Improve participant evidence capture, previews, upload feedback and mobile accessibility.
- Refine AI-assisted blocker coordination and less technical local-change editing.
- Improve resource estimation, reusable-equipment overlap analysis and uncertainty handling.
- Extend approved integrations for notifications, meetings and organization support.
- Package replay/build dependencies for a reproducible public checkout without private demo files.
- Complete production hosting, private object storage, monitoring, security/retention hardening and deployment documentation.

These are planned improvements, not implemented production capabilities. Richer memory generalization must retain authorization and outcome verification.

## Hackathon

AroundYou was built for the **Meta Global AI Developer Hackathon 2026**, exploring how Meta AI and community participation can make practical event organization more accessible.

Education, community support and environmental scenarios demonstrate human-guided planning and execution. The [submission narrative](hackathon_submission.md) is a draft, not proof of submission, acceptance or an award. Live deployment and the final video remain placeholders above. No credits, model availability or billing guarantees are implied.

## License

**A project license has not yet been added.** The owner must choose terms and add a `LICENSE` file; no open-source license is asserted here.

The pinned Qwen model's Apache-2.0 license is recorded in the [Modal verification report](docs/implementation/modal-live-verification.md). That model license does not license AroundYou, provider services, photographs or other third-party assets. Their respective terms and permissions apply.
