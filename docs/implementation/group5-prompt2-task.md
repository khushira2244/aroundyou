# CODEX — AroundYou Group 5 Prompt 2
## Resume and Complete Intelligent Recovery + Dynamic Participant Insights

### Mission

Resume the existing PARTIAL Group 5 implementation from:

- `docs/implementation/group5-task.md`
- `docs/implementation/group5-implementation-report.md`
- `docs/implementation/group5-checkpoint.md`, if present
- `outputs/backend-group5/verification.json`
- Existing Group 5 source code and tests

The authoritative Group 5 task is the previously approved task document. This prompt completes that task; it does not replace its requirements or authorize a new feature group.

**Do not rebuild completed components. Do not start the landing-page or My Events redesign.**

### Verified baseline

The previous checkpoint reports:

- 132 backend PostgreSQL tests passed.
- Final five focused Group 5 tests passed; these overlap the full suite.
- 146 demo tests passed.
- TypeScript and production build passed.
- Frontend full rerun: 71 passed, one timeout. The affected test subsequently passed separately.

Treat these as previous results, not fresh verification of new changes.

Group 5 currently has working blocker impact analysis/confirmation and versioned insight configuration/response/consent APIs.

The remaining work below is mandatory.

---

## 1. Complete the recovery lifecycle

Implement persistent, versioned recovery investigations and alternatives.

Connect the existing deterministic impact engine to:

1. Confirmed blocker investigation.
2. Affected-scope snapshot.
3. Recovery alternative generation or manual authoring.
4. Deterministic alternative validation.
5. Pending proposal review.
6. Exact organizer decision.
7. Participant reconfirmation, when required.
8. Atomic activation or safe deferral.
9. Source-linked recovery history and outcomes.

Do not let an issue acknowledgment substitute for confirmed blocker evidence.

Support recovery without AI through manual alternatives.

### Alternative validation

Check actual plan dependencies, resources, reservations, schedules, skills, assignment capacity, existing accepted consent, completed work, governance conditions and current versions.

Distinguish:

- Feasible under verified constraints.
- Conditional or requiring clarification.
- Invalid.
- Pending participant reconfirmation.
- No safe alternative currently available.

Never invent a vehicle, volunteer, permission, stock or completed work to make a proposal feasible.

If recovery cannot proceed, leave affected work safely blocked or held with a recorded explanation.

## 2. Human decisions and exact reconfirmation

Implement organizer review bound to the exact proposal, source digest and plan version.

Preserve rejected alternatives and review history.

For changed assignment terms:

- Reuse or extend Group 3 assignment offer and consent infrastructure.
- Generate exact revised terms.
- Require explicit participant acceptance.
- Preserve historical consent.
- Do not treat approval or silence as participant acceptance.
- Keep unaffected assignments valid.
- Handle decline, withdrawal, expiration and stale versions.

No automatic consent.

## 3. Atomic recovery activation

Only activate a revised authoritative plan after the required checks and decisions succeed.

Revalidate under the appropriate database locks:

- Current blocker state.
- Current plan/version.
- Affected dependency scope.
- Work and stage constraints.
- Resources and reservations.
- Participant consent.
- Relevant source/memory eligibility.
- Approval and proposal digest.

Activation must be transactional and idempotent.

On failure:

- Preserve the original authoritative plan.
- Record or return an appropriate deferred/conflict outcome.
- Avoid partial work reassignment or resource mutation.
- Never modify verified completed work or unrelated branches.

Test concurrency and transaction rollback.

## 4. Wire Event Memory into recovery

Reuse Group 1–4 memory services and source resolvers.

Provide current-event facts separately from retrieved historical lessons.

Retrieve applicable, authorized memory including failed attempts and uncertainty.

Validate exact source revisions and eligibility when generating, reviewing and activating alternatives.

Record source-backed recovery decisions, attempts and eventual outcomes.

A selected plan is not automatically a successful recovery.

Cross-event private memory remains disabled.

Do not use live Modal inference.

## 5. Recovery AI boundary

Extend the existing provider-neutral model port and durable job machinery for typed recovery proposals.

Use the confirmed blocker, current context, impact manifest, current resources/assignments, applicable memory and validated constraints.

Require explicit assumptions, risks, cited inputs and alternatives.

Validate outputs against current real records.

Malformed, unsupported, timed-out or stale output must fail safely.

No live Muse Spark calls, no paid worker deployment, no fabricated model responses in production.

Manual recovery must remain operational if no model is configured.

## 6. Connect the dynamic Participant Insights experience

The backend foundation for question configuration, answers and consent already exists.

Complete the actual existing UI/API integration:

**Organizer Event Profile Settings → enabled insight questions → participant Join Event form → private persisted answers → separate insight consent → accepted participant eligibility → existing six-tab Insights modal.**

Keep these six existing tabs:

- Overview
- Age
- Neighbourhood
- Experience
- Interests
- Tags

Do not recreate the UI or create a second insights module.

### Required behaviors

- Organizer adds/enables structured questions and predefined custom Tag options.
- Participants see only relevant enabled questions.
- Questions and answers use stable IDs and exact configuration versions.
- Required fields validate correctly.
- Consent is distinct from application submission and assignment acceptance.
- The participant can revoke aggregate-consent permission.
- Old answers retain their original meaning when configuration changes.
- HTTP mode uses actual backend projections, not fixture-based counts.
- Existing demo mode remains unchanged.

### Privacy

Preserve the existing minimum-five eligibility threshold and per-bucket suppression.

Do not reveal raw private answers through aggregate APIs.

Test combined filters and complementary counts for disclosure risks. If safe release cannot be established, suppress the result.

Review repeated-query and longitudinal-differencing exposure. Avoid claiming full privacy protection when this remains unverified.

Count accepted participants from actual Group 3 assignment records.

## 7. Group 5 frontend wiring

Wire the existing recovery UI to the actual Group 5 APIs:

- Confirm issue.
- View impact.
- View/create alternatives.
- Review feasibility and trade-offs.
- Organizer selection.
- Participant revised offers and acceptance.
- Pending/hold states.
- Activation or rejection.
- Source-linked recovery history.

Preserve the existing screen layout, route structure and styling.

This Group 5 functional wiring is REQUIRED and must not be deferred as mere tomorrow polish.

Do not start the separate public landing page or organizer-only My Events redesign.

## 8. Verification

Add integration tests covering complete successful and safely deferred recovery paths.

At minimum test:

- Confirmed issue → affected graph → manual alternative → feasibility → approval → activation.
- Conditional or impossible recovery remaining deferred.
- A recovery requiring changed participant consent.
- Participant decline.
- Stale plan and stale proposal.
- Simultaneous activation attempts.
- Resource/assignment conflict.
- Verified completed work preservation.
- Event Memory retrieval, retraction and source invalidation.
- Failed/inconclusive recovery history without fabricated success.
- Canary Hill unavailable-vehicle case.
- A separate non-cleanup event.
- Organizer custom question appearing in Join Event form.
- Answer persistence and independent consent.
- Insights updating after actual participant acceptance.
- Five-person privacy threshold and suppressed buckets.
- Combined-filter and longitudinal privacy safeguards.
- Cross-event access denial.
- Previously completed Group 1–4 behavior.

Run the entire backend suite against real isolated PostgreSQL, full frontend test suite, all 146 demo tests, TypeScript check, production build, compileall and dependency checks.

Investigate the previously timed-out full frontend suite. Do not call it passing merely because the affected test passed in isolation.

If there is a reproducible issue, fix the actual cause rather than hiding it by excluding tests.

## 9. Configuration and safety

Do not print or change any existing secrets.

Do not overwrite `DATABASE_URL`, assume placeholder credentials are valid, or migrate an uncertain application database.

Do not make live Meta/Muse Spark/Modal calls.

Do not start GPU resources or external notifications.

Use isolated PostgreSQL and explicit non-live AI adapters for tests.

Preserve existing backend/frontend fixtures, immutable source history and established authorization checks.

## 10. Final deliverables

Update:

- `docs/implementation/group5-implementation-report.md`
- Group 5 checkpoint/status document
- `outputs/backend-group5/files-changed.txt`
- `outputs/backend-group5/file-manifest.json`
- `outputs/backend-group5/verification.json`

Preserve historical failed verification artifacts rather than rewriting them as passes.

Report:

1. Precisely what was present before Prompt 2.
2. Every implemented recovery transition and API.
3. AI model interface versus actual execution.
4. Deterministic feasibility and atomic activation details.
5. Exact assignment reconfirmation behavior.
6. Event Memory retrieval and recovery source history.
7. Dynamic insight settings, form, consent and aggregation.
8. Existing UI/API integration and remaining gaps.
9. Actual migrations and table totals.
10. Exact backend/frontend/demo verification results.
11. Real browser, application database and provider limitations.
12. Anything still incomplete.

**Stop after Group 5. Do not start the separate tomorrow frontend redesign, production deployment or live provider integration.**

Do not declare Group 5 complete unless both full recovery and dynamic insights workstreams are implemented and meaningfully tested. If anything remains partial, report it explicitly.