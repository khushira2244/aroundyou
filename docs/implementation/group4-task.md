# CODEX — AroundYou Backend Group 4
## Execution, Evidence, AI Observations, Human Verification and Coordination

### Objective

Implement Group 4 of AroundYou as a functioning, generic, backend-driven community event execution system.

This is an implementation task, not a documentation-only exercise.

Group 3 has completed its bounded core with:
- 108 backend tests on real isolated PostgreSQL
- 69 frontend tests
- 146 existing demo tests
- Successful TypeScript and production build
- Migration 0004, bringing the schema to 34 application tables

Group 4 must build on the existing FastAPI modular monolith, PostgreSQL, SQLAlchemy, Alembic, Unit of Work, versioned event plans, accepted assignments, human governance, resource accounting, audit, outbox/jobs and source-linked Event Memory.

Read the actual implementation and contracts first:

- Group 1 implementation report
- Group 2 and Group 2 Prompt 2 reports
- Group 3 implementation report
- Approved frontend/backend API catalogue and data model
- Existing execution, evidence, participant workspace, organizer dashboard, updates, discussions, meetings, communications and recovery contracts
- Existing Canary Hill and non-cleanup demo scenarios

Preserve current frontend design and existing demo fixtures.

**Implement only Group 4. Do not begin Group 5 or activate live AI services.**

---

## 1. Execution Lifecycle and Work Authorization

Implement authoritative execution records linked to actual published work and accepted assignments.

Support relevant work states, including:

- Not started
- Ready
- In progress
- Blocked
- Submitted for review
- Verified complete
- Rejected / needs correction
- Reopened, where justified

Match actual approved frontend state contracts; do not introduce conflicting status vocabularies without mapping them.

Requirements:

1. Only an eligible participant with a current accepted assignment may report their own assigned work.
2. Organizer/delegated reviewer permissions must be explicit.
3. Keep original plan versions and assignment terms immutable.
4. Record actual timestamps separately from scheduled timestamps.
5. Validate dependencies, required preconditions and assignment scope.
6. Preserve partial progress; do not collapse all work into complete/incomplete.
7. Prevent duplicate or conflicting completion transitions.
8. A submitted report does not mean the work is verified complete.
9. Historical revisions must be retained.
10. Changed or withdrawn assignments must not silently preserve execution authority.

Implement safe handling for work performed before an assignment is withdrawn, retaining legitimate historical evidence without granting future permission.

Do not create fake completed work, attendance or organizer approvals.

---

## 2. Participant Work Reports

Implement the existing participant-side reporting flow.

A participant should be able to:

- Select an assigned work item.
- Describe work performed.
- Record partial progress.
- Report what remains unfinished.
- Describe issues and missing materials.
- Attach supported evidence.
- Save a draft.
- Submit for organizer verification.
- Respond to review questions.
- Correct and resubmit without deleting original reports.

Support multiple reports for the same work item over time.

Reports must retain:

- Author/actor identity
- Event, stage, work and assignment references
- Accepted assignment terms/version
- Submission timestamps
- Original statements
- Evidence references
- Source revision identifiers
- Review and correction history

Generic event support is essential. Do not assume every work report is about physical cleanup.

---

## 3. Voice, Image, Video and Document Evidence

Implement an evidence ingestion and reference lifecycle consistent with the existing frontend contracts.

Support:

- Voice/audio files
- Images
- Short videos
- Documents
- Text statements
- Reviewed transcripts where available

Requirements:

- Preserve original media bytes when actual storage is configured.
- Store private evidence metadata and immutable references.
- Use authenticated upload authorization.
- Apply size/type validation and safe filename handling.
- Support streaming or presigned-upload design where appropriate.
- Record content hashes and upload completion state.
- Reject unauthorized and cross-event access.
- Distinguish uploaded, pending inspection, accepted for review, rejected/quarantined and deleted/retracted states as appropriate.
- Do not treat an image, video or transcript as verified merely because it was uploaded.
- Never invent a transcript when transcription is not available.
- Do not expose private evidence through public event pages.

Inspect whether local private object storage is suitable for the development environment. Use an object-storage abstraction compatible with future cloud storage.

Do not implement an unsafe arbitrary filesystem upload or publicly accessible media directory.

If file-byte storage cannot safely be completed, implement the validated boundary, report its limitations, and keep missing media functionality explicitly unavailable.

---

## 4. AI-Assisted Field Evidence Understanding

Implement the provider-neutral Group 4 AI advisory workflow for interpreting real field updates.

Inputs may include:

- Original participant text or reviewed transcript
- Image/video evidence metadata and content only when authorized and supported
- Current event context
- Stage/work definitions
- Actual assignment scope
- Previous verified work history
- Reported resource problems
- Relevant source-linked Event Memory

The model may propose:

1. What the participant appears to be reporting.
2. Possible progress interpretation.
3. Missing or contradictory evidence.
4. Risks and unresolved questions.
5. Whether further human clarification is required.
6. Potential issue/blocker signals.
7. Suggested next actions for organizer review.

The AI must clearly separate:

- Reported fact
- Source-supported observation
- Inference
- Uncertainty
- Missing evidence
- Recommendation

A model must not mark work as complete, verify attendance, confirm resource usage or authorize an operational transition.

Do not claim image/video analysis when the model received only filenames or metadata.

Validate model output against authorized evidence references and current source versions.

### Muse Spark boundary

Reuse the existing typed AI port, context builder, durable runs, bounded retry/error handling and human-review controls.

Prepare compatible task-specific interfaces for execution interpretation and evidence assessment.

No live Muse Spark or Modal calls.

No network inference and no AI credit consumption.

Test with explicitly labeled non-live adapters.

---

## 5. Human Evidence Review and Verification

Implement organizer/delegated-reviewer actions:

- View original report and evidence.
- Inspect AI observations when available.
- Ask for clarification.
- Accept verified portions.
- Reject unsupported claims.
- Request correction.
- Mark exact work or measurable portions as verified.
- Reopen work with a recorded reason when appropriate.

Review decisions must be version-bound, auditable and attached to exact report/evidence revisions.

Distinguish:

- Participant-reported progress
- AI-estimated progress
- Human-verified progress

Public impact and organizer dashboards must use only the appropriate verified state.

Do not infer actual environmental/social impact automatically from completed task count.

If an external impact metric has not been measured, mark it as unverified or unavailable.

---

## 6. Attendance and Participation Evidence

Implement explicit event participation/check-in and attendance records only where supported by existing workflows.

Keep separate:

- Accepted assignment
- Scheduled presence
- Self-reported attendance
- Organizer-verified attendance

Do not mark participants as present because they accepted assignments.

Use authorized timestamps and, when applicable, verified location evidence without assuming device GPS is trustworthy proof.

Preserve private location and personal data appropriately.

---

## 7. Resource Consumption, Equipment Custody and Returns

Extend Group 3's verified receipt and reservation ledger.

Implement authorized transitions for:

- Resource allocation/issue
- Actual consumption reporting
- Consumption verification
- Equipment check-out
- Equipment return
- Shortage/damage/loss report
- Corrections/reversals

Respect the difference between consumable supplies and reusable equipment.

Preserve ledger consistency and source history.

Prevent:

- Consuming pledged but unreceived resources
- Negative stock
- Duplicate consumption
- Reusing equipment already checked out
- Missing or double returns
- Invalid unit conversions
- Silent correction of operational history

A participant's self-reported usage must not automatically become verified inventory usage.

Resource changes must be traceable to actual authorized operations and work where applicable.

---

## 8. Live Updates and Coordination

Implement useful operational communication features using the existing frontend contracts:

- Participant status updates
- Organizer announcements
- Work-linked notes and discussions
- Clarification threads
- Relevant activity timeline
- Internal coordination messages
- Visibility/permission rules
- Meeting metadata, agenda, participant associations and decisions
- Work/action items arising from meetings

Preserve the distinction between saved communication and externally delivered notification.

Do not claim email, WhatsApp, SMS, push delivery or real-time calls unless actual integrations exist.

Use persistence-first APIs. Polling is acceptable for the hackathon; WebSockets are optional only if necessary.

Do not create a second communication product or redesign existing screens.

---

## 9. Issue and Blocker Detection — Group 4 Boundary

Group 4 may record:

- Reported blockers
- Missing resources
- Schedule conflicts
- Delayed work
- Unavailable dependencies
- Suspected safety issues
- Organizer clarification requests

Create typed, source-linked issue records with severity, affected work references, evidence and investigation state.

Support issue lifecycle:

Reported → Acknowledged → Investigating → Resolved/Closed, with exact transitions as compatible with existing contracts.

Keep **handling state** separate from **whether the underlying blocking condition is actually cleared**.

An acknowledged issue is not a resolved blocker.

AI may suggest that a report indicates a blocker, but it cannot create a verified incident or activate a new plan without human review.

### Group 5 ownership

Do not implement full affected-subgraph recovery, alternative plan activation, assignment reconfirmation or AI-driven replanning yet.

Group 4 only produces reliable operational evidence and issue records that Group 5 can consume.

---

## 10. Dependency and Progress Validation

Build deterministic progress calculations using the current published plan and actual verified operational records.

Support:

- Work readiness based on dependencies.
- Blocked vs unblocked work.
- Stage progress derived from work.
- Event progress derived from stage/work status.
- Overdue and at-risk indicators when supported by actual time references.
- Verified versus reported progress separation.

Do not falsely assume that every task has the same effort or weight if the approved plan specifies otherwise.

Avoid forcing every event type into the same impact metric.

If prerequisites are missing or unresolved, surface the uncertainty.

---

## 11. Event Memory and Provenance

Integrate genuine execution and evidence records into the existing Event Memory architecture.

Sources should include appropriate:

- Work attempts
- Field reports
- Human verification decisions
- Resource usage and corrections
- Blocker observations
- Meeting decisions when they are source-supported
- Verified and failed attempts where evidence supports them

Maintain separate dimensions:

- Evidence stage: proposed / attempted / verified
- Outcome: unknown / successful / failed / mixed / inconclusive
- Memory lifecycle: candidate / published / superseded / retracted

Do not automatically describe every work-completion record as a generalizable success lesson.

Preserve exact source lineage and access permissions.

Ensure source correction/retraction immediately invalidates stale derived memory.

Do not enable private cross-event reuse.

---

## 12. Frontend HTTP Integration

Extend the existing opt-in HTTP adapter and AroundYouService contracts for the verified Group 4 operations.

Support the existing participant and organizer UI for:

- Assigned work
- Work reports
- Evidence references
- Organizer verification
- Resource usage and custody
- Activity timeline
- Discussions
- Meeting records
- Issues/blockers
- Progress and impact views

Preserve existing React screens, navigation, styles and fixture-based demo mode.

Do not silently return demo values for missing backend execution APIs.

If an existing screen is not backed by a working HTTP endpoint, show an explicit unavailable/empty state and document it.

No second organizer dashboard, duplicate participant workspace or fake live collaboration.

---

## 13. PostgreSQL and Configuration

Use additive Alembic migrations after 0004.

Preserve all prior tables, immutable triggers, source references and version invariants.

Use real isolated PostgreSQL for integration testing.

The configured application DATABASE_URL previously contained placeholder credentials.

Do not invent credentials, print secrets, reset databases or migrate an uncertain target.

Report application database setup as a separate blocker until correctly configured.

Do not modify Meta API keys or Modal authentication.

---

## 14. Required Integration Tests

Test at least:

- Accepted participant reporting assigned work
- Unauthorized participant reporting another person's work
- Withdrawn or changed assignment authority
- Partial progress and multiple report revisions
- Evidence upload/metadata validation and private access
- Unsupported/missing media or transcription behavior
- Malformed/stale/timeout AI observations
- Organizer clarification and correction loop
- Report submission versus verified completion
- Verification reversal or reopening
- Attendance claims versus verified presence
- Consumption and reusable-equipment return
- Concurrent resource allocation
- Reported blocker versus verified blocker state
- Dependency-based progress/readiness
- Meeting/discussion scope and permissions
- Source correction and memory invalidation
- Cross-event access denial
- A non-cleanup event execution workflow
- Existing ten-participant Canary Hill scenario

Run full regression checks:

- Group 1–3 backend PostgreSQL tests
- All frontend tests
- All 146 existing demo tests
- TypeScript typecheck
- Production build
- Dependency/compilation checks

Record exact results and distinguish passing tests from unverified browser/runtime claims.

---

## 15. Required Group 4 Implementation Report

After completing the implementation, provide:

1. Exact working features and state transitions.
2. Database migration and new tables.
3. Exact API endpoints implemented.
4. File evidence storage status, including real bytes versus metadata-only.
5. AI advisory interfaces and actual execution status.
6. Human verification and progress-calculation behavior.
7. Resource consumption/custody invariants.
8. Coordination, meetings and communication limitations.
9. Issue and blocker boundary for Group 5.
10. Event Memory source lineage and eligibility.
11. Frontend HTTP adapter integration status.
12. Real PostgreSQL/backend/frontend/demo verification totals.
13. Exact files created/modified.
14. Remaining configuration and deployment blockers.
15. Group 5 dependencies and deferred work.

Save the implementation report under `docs/implementation/` and evidence/file manifests under `outputs/backend-group4/`.

After implementing and testing Group 4, **STOP**.

Do not begin Group 5.
Do not deploy models or call Muse Spark/Modal.
Do not make unapproved external service requests.
Do not modify demo fixtures to force tests to pass.
Do not claim verified evidence, attendance, resource usage, communication delivery or work completion unless supported by genuine authorized records.

Report what is implemented, what is tested and what remains incomplete.