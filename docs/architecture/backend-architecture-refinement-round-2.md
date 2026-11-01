# AroundYou V1 — Backend Architecture Refinement, Round 2

Prepared 27 October 2026. **Design proposal only. No implementation authorization.**

This refines the accepted FastAPI modular-monolith/PostgreSQL baseline. It preserves AroundYou as a general-purpose community planning, participation, governance and execution platform. Environmental and education examples illustrate the same domain; neither defines the product boundary.

**Reading labels:** “Required” denotes a supplied product constraint. “Proposed” denotes an engineering choice awaiting review. “Mathematical” denotes a consequence of stated inputs, not a product policy. “Open” denotes a human decision. Numerical examples are hypothetical; estimates, provider behavior and results have not been experimentally validated.

Inputs reviewed: the supplied four product-understanding rounds, approved UI references, [Round 1 architecture](backend-architecture-proposal-round-1.md), [Meta technical study](../research/meta-ai-technical-study.md), and [provider adapter study](../research/ai-provider-adapter-design.md). Review date: 27 October 2026. This refinement makes no new claims about live model availability, credits, pricing or provider schema guarantees. November 4 is the user-supplied deadline; its official closing time remains unverified.

## 1. Canonical planning domain

### Proposed design and rationale

The event is the durable operational identity. Its current plan is a coherent set of immutable confirmed revisions. Execution facts, commitments and evidence refer to that identity and the particular plan/work versions they concern; replacing a plan must not rewrite historical facts.

| Concept | Exact meaning and relationships | Must not be confused with |
|---|---|---|
| Event | Community initiative with purpose, ownership, location/time context and lifecycle. Owns stages and the plan lineage. | A published listing, one meeting, or a model conversation. |
| Stage | A meaningful phase/outcome boundary within one event. Holds scope, intended outputs and timing constraints; contains work groups. May overlap another stage when feasible. | An automatically sequential calendar bucket or management position. |
| Work Group | Organizational grouping of related work inside a stage. Proposed: grouping has no independent staffing or resource arithmetic; totals derive from its blocks. | A team of actual people or another mandatory approval tier. |
| Work Block | Proposed smallest independently schedulable and reportable unit, with stable identity, measurable scope, dependencies, effort assumptions and requirements. | A person, checklist description, or AI response. |
| Work Dependency | Explicit directed relation between work blocks. Initial proposal supports finish-to-start with nonnegative lag. Cross-stage edges are allowed within the event. | A mere display order or implicit dependency between every pair of stages. |
| Work Volume | Quantity of output to perform, with unit and measurement definition: 12 sites inspected, 60 learners assessed. | Worker-hours or elapsed time. |
| Effort | Labor required, separated by skill/activity where relevant, in person-hours. Derived only when an approved productivity assumption supports it; otherwise an explicit estimate. | Duration. Two people do not always halve it or duration. |
| Duration | Elapsed scheduled working/calendar interval under a stated calendar and execution method, including unavoidable fixed waiting when applicable. | Effort divided by any arbitrary headcount. |
| Capacity | Time-indexed ability of eligible actors/equipment/facilities to perform work. Includes availability, skills, concurrency and physical limits. | Total registered volunteers or total event headcount. |
| Resource Requirement | Typed demand attached to work: consumable quantity, reusable asset/time interval, service units/slot, or funding need. Includes unit, timing and substitution rules. | A pledge, inventory receipt or reservation. |
| Actor Requirement | Required responsibility/skill and coverage for work, with timing/effort and number of positions or simultaneous people distinguished. A published role references one or more such requirements. | A named assignee, application, or accepted commitment. |
| Confirmed Plan Revision | An immutable, human-approved coherent planning snapshot, identified by a manifest referencing exact compatible stage, work and actor-requirement revisions. One active revision per event. | The latest draft, a mutable stage row, or an AI-generated plan. |

A Work Group should be optional in authoring: a stage can use a default group internally without requiring another UI step. Whether blocks can contain independently tracked sub-blocks is open; do not introduce a recursive work hierarchy for V1 without a demonstrated need.

Requirements attach to blocks, with group/stage summaries derived. A reusable item used by two sequential blocks is not necessarily two items. The same actor can satisfy sequential requirements if qualified and available. Group totals must retain both summed effort and peak concurrent demand; one number cannot represent both.

A stage's displayed start/finish can derive from its blocks. Explicit stage windows are constraints, not a competing schedule. Proposed rule: a block must fit its stage's allowed window, and the stage summary encloses its blocks. A stage can have no work while being designed, but cannot be represented as execution-ready merely because its title is confirmed.

### Contrasting examples

**Environmental initiative: neighborhood habitat restoration.** Event goal: restore and document 12 planting sites. Stages: assess sites, restore habitat, monitor survival. Restoration group: prepare sites. Block A: prepare 12 sites at an approved estimate of 2 person-hours/site = 24 person-hours. Block B: plant 36 native plants after preparation, with its own estimate and skill mix. Requirements include plants and mulch as consumables, borrowed tools as reusable assets, and safe-tool supervision as actor coverage. A later survival survey measures living plants; planting completion alone does not prove ecological impact.

**Community education initiative: neighborhood digital-literacy program.** Event goal: deliver a learning program to 60 residents. Stages: assess learning needs, prepare curriculum, deliver sessions, evaluate learning. Delivery group: three cohorts of 20 learners. A block can be one two-hour cohort session requiring one instructor and one assistant, 20 usable device seats and an accessible room. Its direct delivery effort is 4 person-hours, duration 2 hours, and volume 20 learner-session places. Preparation is separate effort. Sixty places do not prove attendance or learning; attendance records and an agreed assessment supply distinct evidence. Device seats and instructors may prevent all three cohorts running together.

### Invariants when a stage changes

Stable event/stage/work identities and evidence lineage survive version changes. Every active block still belongs to one active group/stage in the same event; moving work requires an explicit mapping. Dependencies still resolve to active compatible blocks, remain acyclic, and satisfy timing constraints. No edge silently disappears because its source stage was renamed or replaced.

Actor/resource requirements must match the new scope and timing. Active reservations, published roles and assignments must reference compatible work and requirements. Completed work remains historically linked to its original revision; removed unfinished work needs explicit cancellation or replacement disposition. Stage summaries, public representations and impact denominators must not combine incompatible revisions.

**Failure scenarios:** renaming treated as deletion loses reports; moving a block drops a cross-stage predecessor; summing reusable requirements overstates procurement; “60 learners” becomes “60 volunteers”; a stage window shrinks while assigned blocks remain outside it.

**Open human decisions:** block granularity; stage window strictness; permitted overlap; units/productivity ownership; treatment of partially completed work when scope changes; whether any cross-event dependency is needed later. Initial recommendation excludes cross-event dependency edges while tracking shared actors/resources separately.

## 2. Confirmed planning revision protocol

### Proposed design

Separate three objects: the **active confirmed manifest**, an editable **candidate change set**, and an immutable **review package** containing the exact proposed diff, dependency analysis and approval/consent evidence. An AI proposal can populate a candidate but cannot confirm it.

1. **Capture the base.** Record event, active manifest, expected versions for relevant stage/work/requirements, permissions and source facts. Editing drafts does not mutate active content.
2. **Express the change.** Preserve stable IDs for retained entities; list additions, removals, moves and replacements explicitly. Candidate children name the candidate parent context they were designed against.
3. **Compute affected scope.** Include changed blocks, downstream dependency closure, parent summaries, shared-actor/resource conflicts, role requirements, reservations, published opportunities, pending applications, accepted commitments, meetings and evidence/impact references. Upstream blocks need reassessment when their outputs are newly insufficient, even if their schedule is unchanged.
4. **Build a compatible manifest.** Reuse unchanged revisions only after validation against the new parent constraints. A parent's editorial rename need not regenerate all children. A scope/window change requires affected children to be explicitly revalidated or revised. Compatibility is a recorded validation result, not an assumption based on matching IDs.
5. **Prepare dispositions.** For every affected reservation, opportunity and responsibility, state retain, modify, release, suspend or cancel, with reasons. Preserve application answers and historical acceptances. Compute resource and staffing feasibility using current authoritative facts.
6. **Human review.** Present the exact diff and consequences within the existing planning/change-review experience. The organizer may approve their manual change in that same action; AI authorship does not replace review. Scope-specific authority is checked again at activation.
7. **Obtain renewed consent where required.** Material changes to a participant's accepted responsibility require acceptance of the exact new terms. Sponsor/resource-provider obligations similarly cannot be rewritten by an organizer. A pending acceptance names a candidate digest; further relevant edits invalidate it.
8. **Activate atomically.** In one short transaction, recheck expected versions, active manifest, permissions, consent, hard constraints, resource availability and assignment conflicts. Switch the active manifest, apply reservation/assignment/opportunity dispositions, append audit and durable notifications together. Failure leaves the previous confirmed version intact.
9. **Notify and project.** Deliver notifications and refresh public/workspace projections durably after commit. Operational writes and reads consult authoritative versions; a lagging projection cannot authorize outdated work or applications.

Expected-version checks are necessary but insufficient. Two different assignments can race for the same person or asset without editing the same row. Activation must also serialize/check shared capacity and ledger invariants. No database lock is held while a human reviews or a model runs.

### Safe deferred activation

Proposed default: material changes remain candidates until compatible requirements, reservations and required consent are ready. The existing confirmed plan stays historically authoritative. However, a new real-world fact—venue unavailable, unsafe conditions, participant withdrawal—can independently make old work infeasible. Record that fact and mark/block affected execution immediately through the authorized operational process. “Old plan remains active” must never mean “old plan is safe and feasible.”

Reserve candidate demand as an **intent**, not a second active allocation. Recheck availability at activation. Optional expiring tentative holds would need a separate approved policy and must reduce free capacity visibly; omit them initially. If resources disappear before activation, return the candidate for review rather than partially activating it.

For material changes affecting published opportunities, proposed policy is to suspend affected new applications while the candidate is reviewed, leaving unrelated roles open. Existing applications retain their submitted role/version and answers. On activation, publish compatible role revisions or keep them suspended; never silently reinterpret old applications. Publication of private detail still requires its own allowed disclosure boundary. Whether suspension happens at candidate creation or only after organizer review is an open product policy.

A committed participant's original acceptance remains evidence. An updated assignment is pending consent until accepted; it cannot appear as an accepted replacement. If the participant declines, the organizer must revise coverage or explicitly remove that responsibility through the agreed change process. Historical completed work cannot be reassigned retroactively.

### Organizer changes a stage while AI is running

Example: request R starts from active manifest P17, stage S4, work W8 and role R3. It asks for work design. The organizer changes the stage window and activates P18/S5 while inference continues. The AI response carries its original version vector and returns later.

The system saves the response as **stale, not applicable** and records why. It does not overwrite S5, activate a plan, reserve resources or show the result as current. Cancellation is best-effort and may not prevent provider cost. A fresh request uses P18 and the new constraints. An organizer may deliberately reuse text as a new candidate, but that candidate gets new provenance, validation and review. Automatic “rebase” is excluded initially.

If an unrelated profile typo changed, a precisely scoped dependency vector can show the response is still applicable; do not invalidate every run for every event edit. When scope cannot be proven, reject application conservatively. A candidate-stage edit during inference likewise invalidates outputs based on the previous candidate digest, even without an active-plan change.

**Rationale:** immutable snapshots make approvals meaningful; a short activation transaction gives coherent operational state; a version vector avoids both stale overwrites and needless invalidation.

**Invariants:** one active manifest; no incompatible active parent/child pair; consent refers to exact terms; no capacity overcommit during activation; no partial reservation/assignment switch; preserved history; notifications never substitute for consent.

**Failure scenarios:** simultaneous organizers; acknowledgment followed by another edit; job retry after activation; crash after commit before notification; resource receipt corrected during review; public cache still showing old roles. Recover by conflict/review, idempotent activation, durable outbox retry and authoritative version checks—not by last-write-wins.

**Open human decisions:** materiality thresholds; who can reconfirm which scope; application suspension timing; acknowledgment expiry; cancellation/reassignment rules; emergency authority. No emergency bypass is assumed.

## 3. Scheduling and capacity

### Proposed design and numerical examples

Use a deterministic constraint evaluator first. It validates a proposed schedule and can produce a bounded, labeled heuristic schedule. Do not claim that dependency traversal solves resource-constrained project scheduling or that a heuristic failure proves global infeasibility.

**Example inputs:** hypothetical event Day 1 = 10 November 2026, 09:00 Asia/Kolkata. Working calendar: 09:00–13:00 each day. No travel, setup, breaks or holidays in this simplified example; these would need explicit inputs. Work intervals are half-open: an interval ending at 13:00 does not overlap one starting at 13:00. Relative Day 1 is offset zero from the approved anchor; it is not the creation/publication date. Changing the anchor proposes new actual times and triggers commitment/resource review.

| Block | Inputs | Earliest feasible example |
|---|---|---|
| A: site preparation | 12 sites × 2 person-hours/site = 24 person-hours; 2 qualified workers × 4 hours/day; perfectly divisible work assumed | Days 1–3, 09:00–13:00 each day; finishes Day 3 at 13:00 |
| B: planting | 16 person-hours; same 2 workers; finish-to-start after A, zero lag | Days 4–5; finishes Day 5 at 13:00 |
| C: outreach preparation | 8 person-hours; separate eligible worker available 4 hours/day; independent of A | Days 1–2, parallel with A |

A and B require 40 person-hours and, with the same two workers and this calendar, five working days. C does not lengthen that chain because it has separate capacity and no predecessor on A. If C instead uses the same two workers, its 8 hours cannot be scheduled concurrently when A consumes their entire capacity. Total 48 person-hours then requires at least six working days at 8 person-hours/day. Resource constraints add precedence or delay even when the dependency graph permits overlap.

Finish-to-start rule: start(B) ≥ finish(A) + lag, interpreted on an explicitly defined calendar. Here A finishes at closing time, so B starts the next opening. A 24-hour curing lag differs from one working-day lag; the lag's time basis must be stored. Initial recommendation: zero-lag finish-to-start only unless a required example justifies calendar-aware lags.

**Effort versus duration:** A has 24 person-hours of effort and occupies three four-hour working days with two workers. Its wall-clock span includes nights; displaying “3 days” must identify working days. A fixed two-hour teaching session with instructor and assistant has 4 person-hours of effort and 2 hours of duration. Adding instructors cannot shorten a promised two-hour session. Productivity, coordination and minimum crew constraints can defeat linear scaling.

**Skill constraint:** education session E requires an instructor and assistant simultaneously, 09:00–11:00. Two assistants available then provide 4 person-hours but zero instructor coverage. E is infeasible in that slot. An instructor available only 11:00–13:00 does not fix it unless the session and assistant can move with required consent. Aggregate person-hours are a necessary capacity check, not a sufficient staffing proof.

**Workload change:** increasing A from 12 to 18 sites at the same approved productivity raises effort from 24 to 36 person-hours. At 8 person-hours/day, the lower bound is 4.5 working days. A can finish Day 5 at 11:00 under divisible-work assumptions. B can use the remaining 2 hours per worker on Day 5 (4 person-hours), then Day 6 (8), then Day 7 until 11:00 (4). The new chain finishes Day 7. If the deadline is Day 5 at 13:00, available capacity is 40 person-hours against 52 required: at least 12 person-hours short, independently proving infeasibility under these inputs.

**Resource constraint:** three two-hour cohorts each require one instructor, one assistant and 20 devices. With only 20 devices, at most one cohort runs at once even if three teaching teams are available. With 40 devices but one instructor, still at most one. Room capacity, accessibility, equipment availability and maintenance can constrain separately.

The evaluator should return explainable violations and assumption provenance: missing skill coverage, deadline lower-bound failure, overlap, unmet predecessor, unavailable asset or missing estimate. “Unknown” is distinct from feasible. Exhaustive/optimization scheduling can be evaluated later when measured cases show the heuristic insufficient.

**Mathematical invariants:** no worker allocated beyond availability/concurrency; eligible skill coverage in every required interval; no overlapping exclusive asset bookings; predecessors respected; units consistent; duration nonnegative; workload and productivity assumptions explicit. Effort totals and peak concurrency are different aggregates.

**Failure scenarios:** timezone anchoring shifts accepted dates; a day label conceals overnight waiting; two workers counted twice across events; missing productivity treated as zero effort; heuristic labels an unsolved problem impossible; completed work is rescheduled as if unfinished.

**Open human policies:** anchor ownership and edit rules; working calendars; minimum shift lengths; overtime/travel; whether people may hold concurrent light duties; substitution qualifications; indivisible work; deadlines that may move; acceptable estimation uncertainty. These policies cannot be inferred from arithmetic.

## 4. Participation and assignments

### Proposed smallest coherent lifecycle

| Business fact | Meaning and owner | Existing UI surface |
|---|---|---|
| Published role | Versioned opportunity derived from confirmed actor requirements, with scope, capacity, timing and terms; M08 requirements, M09 publication | Volunteer Roles tab and Choose Roles |
| Application | Participant's selected roles, availability, answers and submitted terms/version; M11 | Four-step joining flow; Requested state |
| Human approval | Authorized organizer decision on all or specified parts of the application; M11 | Organizer participant/application review |
| Actual responsibility | Named person connected to specific approved role/work coverage, with scope and dates; M12 | Organizer operations and participant role/work views |
| Accepted commitment | Participant consent to those exact responsibilities and material terms; M11 acceptance linked to M12 assignment | Existing review/confirmation or Participant Workspace action |
| Participant Workspace | Permission-controlled view of participation, responsibilities, schedule, evidence and coordination; M13 | Approved workspace, with pending versus accepted status explicit |

Approval is eligibility/selection, assignment is actual responsibility, and acceptance is consent. They can occur close together without becoming the same fact.

**One organizer action:** “Approve and offer these responsibilities” may record approval and create exact assignments awaiting participant acceptance in one transaction. It must perform capacity, scope and authority checks. If the application already contained explicit, specific consent to exactly those assignments and terms, approval may also establish acceptance in that transaction. Selecting a broad role or stating availability alone is insufficient evidence of consent to later undisclosed work.

**One participant action:** reviewing an offered assignment and accepting it can create the accepted commitment and activate its workspace responsibility together. Several displayed assignments can be accepted together when the exact selection and conflicts are clear. No additional frontend screen is required: proposed accept/decline controls and status in existing review/workspace surfaces suffice. These are future interaction recommendations, not authorized UI changes.

An approved participant can enter a limited workspace showing pending offers and event information while having no accepted work. Only accepted responsibilities count as committed staffing; access is independently permissioned, so workspace access itself proves neither assignment nor consent.

### Conflicts and changes

- **Multiple roles:** apply for multiple published roles, but evaluate actual time, skill, exclusivity and workload across accepted assignments before commitment. One person holding two role labels does not supply two simultaneous people. Cross-event checks should disclose a conflict/busy interval without leaking another event's private details.
- **Partial approval:** approve role A and decline or leave role B pending, recording a separate decision for each submitted selection. Offer only the approved responsibilities. Do not rewrite the original application as if only A was requested. The participant can accept or decline the offered subset.
- **Partial acceptance:** acceptance of one independently executable assignment need not accept all offers. If two assignments are an explicitly disclosed indivisible package, enforce that package and explain it before consent. Package policy is open.
- **Withdrawal:** preserve the acceptance history, end future commitment coverage, flag staffing gaps and notify authorized coordinators. Do not delete past work/evidence. Distinguish withdrawal from an offer, application withdrawal, and withdrawal from accepted work. Resource custody/return obligations need their own resolution.
- **Material change:** moving a session, extending hours, changing work/location, adding risk or expanding responsibility creates a new offer requiring renewed consent. An editorial typo can be nonmaterial under an approved policy. Silence or a notification read receipt is not acceptance.
- **Capacity race:** accepting two offers simultaneously must not exceed a role's positions or the person's permitted workload. Record one successful commitment and return the conflicting one for review; never overfill and fix it later.

**Rationale:** this is the smallest lifecycle that preserves the joining UI, organizer discretion and participant agency without inventing a new approval bureaucracy.

**Invariants:** application history survives decisions; approval never creates undisclosed responsibility; accepted terms identify versions; only accepted coverage counts as committed; role capacity counts positions/time coverage, not merely applications; permissions remain event-scoped.

**Failure scenarios:** partial approval silently becomes full consent; organizer marks someone accepted; withdrawal leaves them counted as staffed; a stage edit changes accepted dates without consent; public “filled” counts approvals while the workspace counts commitments.

**Open human decisions:** prospective consent wording; acceptance deadlines; role hold/offer expiry; whether approval temporarily holds a position; withdrawal notice expectations; indivisible packages; materiality rules; which pending participants can see which workspace content. Initial recommendation: no invisible indefinite holds and no automatic acceptance.

## 5. Resource accounting

### Proposed design and shared invariants

Keep requirements, offers/pledges, accepted obligations, verified fulfillment, custody/stock, reservations and usage as distinct facts. Use append-only movements with authorized correction/reversal linked to originals; do not overwrite history. An item's resource type determines its accounting strategy.

A delivery claim is evidence awaiting verification. Only authorized verified receipt credits usable stock, subject to quality/quarantine checks. Acceptance of a pledge changes forecast coverage, never on-hand inventory. Quantities use explicit compatible units and exact arithmetic. A commitment to fund a purchase is not itself both cash received and goods received.

For consumables in these examples: **free usable stock = usable on-hand − active reservations**. Quarantined stock is excluded from usable on-hand. Consumption against a reservation reduces both stock and that reservation. Reservations are subsets of stock, not additional stock movements. Conservation must reconcile opening stock + verified receipts + corrections − verified consumption − outbound movements with closing stock.

### 5.1 Consumable materials

Hypothetical planting requirement: 100 identical plants; opening usable stock 40. One supplier pledges 60.

| Action | Pledged / accepted obligation | Usable on-hand | Reserved | Free | Verified consumption |
|---|---|---:|---:|---:|---:|
| Before pledge | 0 / 0 | 40 | 0 | 40 | 0 |
| Pledge 60 | 60 / 0 | 40 | 0 | 40 | 0 |
| Accept pledge 60 | 60 / 60 | 40 | 0 | 40 | 0 |
| Supplier claims delivery 60, unverified | 60 / 60 | 40 | 0 | 40 | 0 |
| Verify receipt of 60 usable plants | 60 / 60, fulfilled 60 | 100 | 0 | 100 | 0 |
| Reserve 80 for block A | Same | 100 | 80 | 20 | 0 |
| Verify consumption of 70 against A | Same | 30 | 10 | 20 | 70 |
| Authorized correction: actual consumption was 75 | Same | 25 | 5 | 20 | 75 |

The correction adds a linked consumption adjustment of 5, supported by review; it does not edit the original 70 away. Remaining requirement is 25 if original scope remains 100; A has 5 reserved and 20 free stock remains available for reservation. Correcting a requirement is a planning revision, separate from correcting observed consumption.

If two actors simultaneously try to reserve 15 each from the free 20, at most one can succeed. The second must fail/review against the authoritative balance. An earlier UI balance is not permission to over-reserve.

### 5.2 Reusable equipment

Example: opening custody contains four ready laptops. A partner pledges two more; acceptance changes only forecast. A delivery claim changes no ready capacity. Verification adds two uniquely tracked, usable laptops: six ready assets.

Reserve four for a specified session interval: four reserved, two free in that interval. Another request for three overlapping laptops fails. An identical request for a later non-overlapping interval may succeed. Issuing/using four changes custody/use status, not ownership stock through “consumption.” At session close, three return ready and one returns damaged. Release the completed reservation: five ready, one quarantined, no remaining booking for that interval. A reviewed correction establishing that the sixth passed inspection releases quarantine: six ready. Keep the inspection/correction trail.

A missing return is not an automatic loss write-off. An asset under unresolved custody cannot be promised to another session just because its scheduled booking ended. Borrowed partner assets retain their owner and return obligation. Counts summarize asset-level states; delivered, issued and returned counts cannot be added as new equipment.

### 5.3 Services and facilities

Example: a community center offers one room for a two-hour session. Accepting the offer records an obligation/permission, not two hours of stock. Verified provider confirmation establishes bookable room capacity for the precise slot under the chosen policy. Reserve the one room for 09:00–11:00; another exclusive booking in that interval is rejected.

The session occurs; evidence initially claims 1.5 hours of service delivered. Authorized verification records 1.5 fulfilled service-hours and releases the finished booking. A reviewed correction adds 0.25 hour: verified fulfillment becomes 1.75 hours. The unused 0.25 hour is neither inventory nor time that can be sold/reserved in the past. Cancellation terms determine whether any future replacement entitlement exists.

Here reservation precedes actual service delivery. Forcing every resource through “receive stock, then consume” is incorrect. A room's physical availability, a provider's confirmed entitlement and actual fulfilled service are three distinct concepts. A two-hour appointment may need the full slot reserved even when measured teaching lasts 1.75 hours.

### 5.4 Sponsor-funded or sponsor-supplied resources

**Supplied goods:** a sponsor pledges 100 notebooks; organizer accepts 80; sponsor claims 80 delivered; verification finds 75 usable and 5 damaged. Credit 75 usable, quarantine 5, and retain the unfulfilled/quality disposition against the accepted obligation. Reserve 60, leaving 15 free. Verify distribution/consumption of 50: usable on-hand 25, reserved 10, free 15. Correct actual distribution to 55: usable 20, reserved 5, free 15. A receipt can fulfill a sponsorship obligation and create an inventory movement through one linked action; it must not create two receipts.

**Funding:** proposed external-funding tracking only, subject to approval; no wallet, escrow or payment execution. Sponsor offers INR 5,000; organizer accepts INR 3,000. No received balance exists yet. A payment claim of INR 3,000 remains unverified. Verified external receipts totaling INR 2,000 create a tracked received balance of INR 2,000, with INR 1,000 accepted but outstanding.

Earmark INR 1,500 for a purchase: tracked balance 2,000, outstanding earmark 1,500, unearmarked 500. Verify a supported payment of INR 1,200 against it: balance 800, remaining earmark 300, unearmarked 500. A reviewed correction establishes payment was INR 1,300: balance 700, remaining earmark 200, unearmarked 500. Do not call this tracked balance a bank reconciliation or spendable wallet balance. Funding restrictions, refunds and currency treatment require approved policy.

When that purchase delivers goods, credit those goods only on verified receipt. Link purchase, sponsor funding and receipt for provenance, but do not present the same contribution's money value plus goods value as two independent sponsor contributions. Funding verification does not verify quantity or community impact.

### Prevention and recovery

Use a canonical fulfillment/receipt identity and source-document reference within the relevant obligation. Retried verification returns its existing result rather than crediting again. Independently uploaded evidence can still describe the same physical delivery; flag matching supplier, obligation, quantities, date and source reference for review. File hash alone is neither a complete duplicate detector nor proof of a new delivery.

Reservations commit under concurrency protection over the shared stock pool or asset/time capacity. Corrections that would make stock negative, invalidate reservations or overstate an obligation cannot silently succeed; require reconciliation and affected-work review. A physical shortage is recorded immediately with an exception, while authorized adjustments and reservation dispositions restore a coherent ledger. Never falsify consumption to force balances to fit.

**Rationale:** one uniform vocabulary with type-specific accounting avoids treating consumables, time slots, reusable custody and money as interchangeable quantities.

**Invariants:** promises are not stock; no negative free capacity; one receipt credit per verified fulfillment; reservations and consumption are not double deductions; units/currency stay explicit; every correction is attributable; sponsor attribution cannot duplicate physical supply or impact.

**Failure scenarios:** two deliveries credited from the same receipt; damaged goods counted usable; a borrowed laptop counted consumed; facility hours stored indefinitely; two events reserve the same shared asset; funding counted on acceptance; a correction leaves more reservations than usable stock.

**Open human decisions:** who verifies receipt/usage/corrections; shared versus event-local stock; condition/expiry rules; units and substitutions; acceptable service confirmation; custody escalation; financial evidence/restrictions; monetary valuation in public reporting. Initial slice should use event-local consumables, avoiding an unapproved cross-event warehouse or financial subsystem.

## 6. AI workflow decisions

### Proposed comparison and initial choices

A structured call means one bounded request producing a candidate schema, followed by deterministic validation. A tool-using agent means a bounded loop with permission-controlled reads/calculations; tool requests have no authority to execute consequential mutations. A fixed pipeline means prescribed steps with independent statuses/retries, possibly including model analysis of media.

| Workflow | One structured call | Bounded tool-using agent | Fixed pipeline | Initial recommendation and evidence to increase complexity |
|---|---|---|---|---|
| Stage Planning | Good fit for proposing a small stage outline from a complete brief. | Useful if verified historical examples must be searched iteratively; more latency and failure paths. | Validate scope, units, dependencies and timing after generation; pure rules cannot invent useful outcome descriptions. | One call plus fixed validation/review. Add retrieval tools only if an evaluation shows missing context is the dominant error and retrieval improves accepted suggestions. |
| Work Design | Good when a confirmed stage and bounded context fit one request. | Can inspect neighboring work, calculate candidate capacity and retrieve precedents selectively. | Deterministic requirement checks and scheduling evaluation remain mandatory. | One call for one stage plus validator. Move to a bounded read/calculation loop only when measured multi-step cases consistently need it. |
| Actor Requirements | Can propose descriptions/skills, but must not supply authoritative people counts without assumptions. | Usually excess complexity initially; may help reconcile heterogeneous skills later. | Derive coverage from work effort, schedule, required skills and approved staffing rules; flag missing assumptions. | Deterministic derivation first, optional single call for wording/uncertain suggestions. Increase only if complex skill mapping measurably benefits and human-reviewed tests pass. |
| Blocker mitigation | Can propose a few alternatives given deterministic affected scope and facts. | Useful for constrained alternatives requiring repeated context/feasibility checks. | First calculate dependency/resource/commitment impact; validate each candidate before review. | Fixed impact analysis + one targeted call. Add a bounded tool loop when one-call alternatives repeatedly fail constraints and iteration improves feasible proposals within budget. |
| Evidence analysis | One call can extract observations from a supported image or text. | Free-form agency adds little to straightforward extraction and creates disclosure risks. | Preserve original → validate media → optional transcribe/sample → model observations → deterministic checks → human review. | Fixed multimodal pipeline. Add individual specialized stages only when labeled evaluation proves benefit; no autonomous verification or work closure. |

Every initial flow should still work with manual input if the provider is unavailable. A valid JSON shape is not a correct plan, safe instruction, verified quantity or permission. Capability negotiation determines whether native schema enforcement is available. If not, parse/validate a candidate response and reject invalid results; do not claim equivalent guarantees. Repaired outputs are new attempts with visible provenance, bounded retries and fresh stale checks.

A provider adapter must expose supported input types, schema behavior, tool behavior, cancellation, usage and error classification based on verified documentation plus contract tests. Meta API and Modal implementations can differ. Do not hardcode a model name or assume provider credits, model access, identical reasoning controls, hidden-state portability or replay parity. Thinking-token budgets and latency need measurement before choosing configurations.

For any later agent: an explicit task scope, allowlisted tools, finite turn/tool/time/cost limits, cancellation, permissions on every read, source versions and trace records are required. Numeric limits should be chosen from evaluation; a “six-turn agent” is not inherently reliable. No tool may publish, approve people, verify stock, change authoritative work or close blockers on the model's own decision.

Historical retrieval should return authorized, source-linked records distinguishing original reports, reviewed observations and verified outcomes. Apply event/privacy filters before retrieval and check them again when presenting evidence. A similar past event is an analogy, not a validated productivity rate for the current event. Untrusted retrieved text and media are data, not instructions.

**Rationale:** complexity follows demonstrated information needs. Deterministic checks govern authority regardless of which generation pattern is used.

**Invariants:** AI never owns confirmation; every proposal names source versions; unsupported capability fails explicitly; no unbounded retries/tools; original evidence survives analysis failure; failure does not lose a submitted report; human review targets the exact source and proposal.

**Failure scenarios:** schema-valid invented quantities; stale output; unsupported media/provider features; prompt injection; retry cost escalation; transcription edits mistaken for original speech; mask area mistaken for material weight; model's “verified” label bypasses human review.

**Open human decisions:** permitted providers/data regions, budget and latency targets, acceptable media/privacy policy, evidence-review roles, historical knowledge reuse boundaries and evaluation thresholds. No live provider experiment is claimed in this proposal.

## 7. Implementation realism and differentiated vertical slice

### Proposed end-to-end slice

Demonstrate a small community education initiative with a planning change during execution. The differentiator is the traceable connection between confirmed planning, real participation, constrained resources, evidence and human-controlled change—not the number of model calls.

1. Organizer creates an unpublished event through the approved creation flow, with draft recovery.
2. A single AI call suggests stages; the organizer reviews and confirms. Work and actor requirements are produced/entered, deterministically checked and confirmed as one coherent manifest.
3. Organizer publishes a role linked to an instructor/assistant requirement. A participant submits the existing four-step application; organizer approves and offers a specific responsibility; participant accepts.
4. Organizer verifies an event-local consumable receipt and reserves supplies for the work. Pledged but undelivered supplies remain forecast only.
5. Participant submits an original progress report with evidence. Optional asynchronous AI observations are labeled pending/reviewed separately; authorized review records actual progress/consumption.
6. A blocker makes the proposed session time infeasible. The engine identifies affected work, people, resource bookings and published roles. AI suggests alternatives, while the organizer reviews a versioned change and the participant accepts material changes.
7. A coherent replacement manifest activates. Old evidence/consent remain linked to their versions. Impact shows only a clearly defined verified output, such as reviewed attendance, and does not claim measured learning gains without assessment.

Use one event, a few blocks, one consumable type and a small number of roles. A separate environmental fixture validates that names, units and workflows are not hardcoded to education. The demo does not require a second polished event journey.

### Scope tiers

**Essential demonstrable functionality:** persistent event and draft recovery; event-scoped identity/permissions; immutable coherent planning; deterministic basic dependency/capacity checks; one bounded AI proposal path or explicit provider-unavailable fallback; publication and real application/approval/assignment/acceptance distinctions; participant report durability; one receipt/reservation/consumption flow; one targeted blocker/revision with renewed consent; audit and retry behavior. Use manual evidence review if multimodal analysis is not ready.

**Meaningful extensions:** asynchronous image/audio analysis with source review; sponsor-supplied goods linked to the same receipt; reusable-equipment booking; meeting availability; richer map discovery; verified historical retrieval. Choose only after the essential chain is reliable.

**Optional experiments:** iterative tool agents, optimization scheduling, video/SAM processing, multiple inference providers, automated historical recommendation ranking, sophisticated sponsor analytics. These are evaluated independently and cannot become dependencies of basic participation or reporting.

### Preserve all twenty module boundaries

“Architectural place” is not a promise that every module is production-complete before November 4. The following keeps every approved module without requiring twenty deployables or twenty agents.

| Module | Ownership preserved | Demonstration depth |
|---|---|---|
| M01 Identity & Accounts | Account, organization membership, event grants | Essential account/event authorization; advanced org administration later |
| M02 Discovery & Maps | Discovery projection and location search | Basic published-event retrieval; rich map extension |
| M03 My Events & Recovery | Watch/resume and contextual event entry | Draft/responsibility recovery essential |
| M04 Event Creation/Core | Event identity, creation, lifecycle | Essential |
| M05 Governance | Optional assessment and internal guidance/ticket | Architectural boundary; manual status or defer assessment |
| M06 Stage Planning | Stage revisions and coherent plan activation | Essential |
| M07 Work Design | Work structure, dependencies and demand | Essential small graph |
| M08 Actor Requirements | Required skills/responsibility coverage | Essential bounded requirements |
| M09 Setup & Publishing | Participation settings and release/visibility | Essential minimal release; richer settings later |
| M10 Public Event Profile | Authorized public editorial/read projection | Existing canonical profile; only supported data, no invented ninth tab |
| M11 Join & Participation | Applications, decisions and consent | Essential |
| M12 Organizer Operations | Named responsibility and operational coordination | Essential review/assignment/change views |
| M13 Participant Workspace | Authorized participant operational projection | Essential own assignments/report/blocker path |
| M14 Resources & Inventory | Supply, custody, reservations and movements | Essential one consumable; other types extension |
| M15 Sponsorship | Offers, accepted obligations and fulfillment attribution | Linked supplied goods extension; no wallet |
| M16 Reporting & Evidence | Original media/report, analysis and verification | Essential original/manual review; AI analysis extension |
| M17 Blockers & Change Control | Blocker facts, affected scope and change workflow | Essential one controlled change |
| M18 Meetings & Communications | Meeting/RSVP/message facts | Notifications essential where required; full coordination extension |
| M19 Impact & Insights | Qualified measurements and public aggregation | One honest verified output; advanced impact later |
| M20 AI & Execution Intelligence | Runs, provenance, proposals and adapter contracts | Essential bounded proposal path; agents optional |

M18 notifications rely on a durable delivery mechanism but do not require implementing chat. M10/M12/M13 compose owner data; they must not become alternative stores for application, stock or work status. Modules not demonstrated retain explicit contracts and ownership in the design, not fake completed behavior.

**Rationale:** a narrow end-to-end chain exercises AroundYou's core cross-module invariants. Implementing isolated attractive screens or many disconnected agents would not prove those invariants.

**Invariants:** no architectural deletion of modules; no unsupported status presented as working functionality; no hardcoded cleanup metrics; demo data clearly identified; no AI/provider dependency for saving user work; approved UI preserved.

**Failure scenarios:** scope grows to every module; inaccessible model blocks the entire demo; missing frontend source prevents real integration; fake participant states hide missing consent; stock and evidence paths are mocked while claiming transactional proof.

**Open human decisions:** demo event and roles, approved frontend source/contracts, identity/provider accounts, available team time, acceptable manual steps, exact deadline/timezone, and which one extension matters most. Freeze essential scope before optional experiments; this document does not authorize building it.

## 8. Five highest-priority decisions to settle first

1. **Canonical work and schedule semantics.** Approve Work Block granularity, stage-window behavior, Day 1 anchoring/calendar, initial dependency types and who approves productivity assumptions. These determine planning, roles and capacity contracts.
2. **Consent and material-change policy.** Define what an application consents to, when a responsibility becomes accepted, material changes, partial approvals and withdrawal. This determines truthful staffing and workspace state.
3. **Revision activation and disruption policy.** Approve coherent manifest activation, affected-role suspension, required acknowledgments and handling known infeasibility while a candidate waits. Name authorized reviewers and avoid an implicit emergency bypass.
4. **Resource/verification authority.** Decide event-local scope, who verifies receipts/usage/corrections, which quantities count available, and whether sponsor funding tracking is in scope. Initial recommendation is event-local consumables with no financial subsystem.
5. **Executable demo boundary and access.** Choose the essential journey, provide actual approved frontend source/contracts, verify identity/model access without assuming credits, and confirm the deadline. Architectural completeness and demonstrated breadth must be separate acceptance criteria.

## 9. Five highest-risk cross-module inconsistencies

| Risk | Modules | Required consistency boundary |
|---|---|---|
| New stage paired with old work/roles | M06–M09, M12–M14 | One compatible active manifest plus atomic downstream dispositions; no piecemeal activation |
| “Filled role” counts approval while schedule assumes accepted staffing | M08, M10–M13 | Explicit counts for applications, approvals, offers and accepted coverage; only compatible accepted coverage staffs work |
| Sponsor fulfillment, receipt and consumption each count as extra supply/impact | M14–M16, M19 | One linked fulfillment/receipt trail, type-specific ledger and distinct output/impact measures |
| Old public opportunities accept participants after private planning changed | M06–M11 | Published version references, authoritative application checks and explicit suspension/republication policy |
| AI/evidence analysis or delayed worker silently changes authority | M16, M17, M19, M20 | Source-version checks, distinct analysis/review/verification states, idempotent effects and human-authorized changes |

Cross-event shared resources and actors add another serious concern: event-scoped permission does not imply event-isolated capacity. Start with clearly event-local inventory and privacy-preserving participant conflict checks; introduce shared inventory only with explicit ownership and concurrency rules.

## 10. Smallest practical architecture proof-of-concept

This is a **proposed future experiment**, requiring implementation approval. It is smaller than the demo slice and needs no new frontend or real paid model request.

Use real PostgreSQL transaction behavior and two simulated users to exercise one event with two dependent blocks, one role, one participant, one consumable pool, two plan versions and a durable job/outbox. A deterministic fake provider can delay or fail responses; this proves orchestration behavior, not model capability.

Acceptance evidence:

- Two simultaneous edits from the same base: one activates, the other receives a conflict; no incompatible children remain active.
- A delayed AI result from the prior stage revision is retained as stale and cannot mutate current state.
- Two concurrent reservations cannot exceed stock. Replaying receipt verification credits once. Consumption and a linked correction reconcile exactly.
- Approval without consent produces no accepted coverage. A material schedule change waits for exact renewed acceptance, and a conflicting acceptance is rejected atomically.
- Worker interruption after authoritative commit but before notification is recoverable: durable retry delivers a consistent notification without repeating the domain effect. Submitted original evidence survives analysis failure.
- An unauthorized participant cannot read another event's report or invoke a tool to bypass event scope. Logs retain provenance without leaking private content.

If these fail, adding agents, optimization or additional infrastructure will not repair the domain model. After this proof passes, separately test the selected live provider's actual schema/tool/media behavior with approved access and a bounded budget. Fake-provider success cannot substantiate any provider capability claim.

## 11. Disagreements and qualifications

There is **no disagreement with the accepted baseline**. The following qualify interpretations that would otherwise produce unsafe or unnecessarily broad implementation:

- **A DAG is necessary but insufficient for scheduling.** Resource, calendar, skill and consent constraints can delay work even without a dependency edge. A topological order proves neither feasibility nor optimality.
- **Keeping the old confirmed plan is not enough during change.** Independent operational facts may require affected work to stop while the replacement awaits consent. Confirmation history and current feasibility are different dimensions.
- **Human approval does not require a separate click for every fact.** One explicit action may approve an application and offer exact responsibilities; prior sufficiently specific consent may permit recording acceptance too. Preserve the business facts and evidence rather than multiplying screens.
- **“Delivery then consumption” is not a universal resource lifecycle.** Reusable custody, room bookings, services and funding require different accounting semantics. A common ledger interface must not erase those differences.
- **Multi-agent branding does not require multi-agent execution everywhere.** Fixed validation/pipelines and single model calls are appropriate initial choices. Tool loops require measurable benefit, not architectural enthusiasm.
- **Preserving twenty modules does not mean implementing twenty complete modules before the deadline.** Ownership and compatible contracts should remain complete while the demonstrable path stays bounded.

These are technical refinements, not requests to redesign the product. No code, migrations, API implementations, infrastructure deployment or frontend changes were made. Stop here for review and wait for explicit implementation approval.
