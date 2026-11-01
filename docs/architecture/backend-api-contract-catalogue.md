# AroundYou — proposed backend API and interaction catalogue

Reviewed 31 October 2026. **Design only; none of these HTTP business endpoints exists yet.** Paths below are proposed. Current actual request expressions and source locations are in [the interaction CSV](frontend-backend-interaction-inventory.csv). The primary report defines DTOs, errors, versions, authority, priorities and open decisions.

The catalogue maps every 114 observed command name (including dynamic dispatch) and 27 called service methods. New integration-support entries are explicitly prefixed `new:`. Demo-only controls have no production endpoint. This is a contract inventory, not authorization to implement every endpoint.

Common to all writes: authenticated server actor, scoped authorization, validated typed schema, applicable expected versions (`If-Match`), and idempotency for creates/consent/ledger/activation. Recompute all validation at commit. `event_id`/resource IDs in paths replace the matching IDs in legacy camelCase arguments. No UI-provided actor ID is authority. `AsyncRunReceipt` means HTTP 202 job receipt, followed by polling; assignment offers awaiting human consent are not queued AI jobs.

Response names resolve to the existing TypeScript DTO inventory described in the main report, with production media/provider fields adapted as documented. Fields shown in braces are the proposed minimal command payload; a state refresh follows where existing hooks already refresh. Responses include common `meta` outside `data`.

**Review correction:** Event Memory is a Day 1 backend capability. The accepted API-001 through API-150 inventory is unchanged. Seven additive MEM design contracts at the end are not observed frontend calls and are not an instruction to build all 149 proposed HTTP contracts at once. Group 1 implements only the subset identified there.

## discovery

### API-001 — Load/search/filter discovery map/list

- Frontend: `discover`.
- Endpoint: **GET** `/v1/events`.
- Request: `query: category?, q?, city?, cursor?, limit?; bbox? only when valid coordinates`.
- Response `data`: `{items: DiscoveryEvent[], next_cursor: string or null}`.
- Validation: Visibility first; bounded filters/pagination; unverified coordinates remain absent.
- State effect: **None**. Entity: `event, publication`.
- Current evidence: `frontend/src/features/discovery/Discovery.tsx:12`

## publication

### API-002 — Open canonical eight-tab Event Profile or preview

- Frontend: `profile, canonicalProfile`.
- Endpoint: **GET** `/v1/events/{event_id}/profile`.
- Request: `path event_id; query preview=organizer only with owner permission`.
- Response `data`: `CanonicalProfile`.
- Validation: Published visibility or owner preview; public-safe insight/content/media projection.
- State effect: **None**. Entity: `event, publication, plan`.
- Current evidence: `frontend/src/features/discovery/Discovery.tsx:13`; `frontend/src/features/discovery/Discovery.tsx:16`; `frontend/src/features/event-profile/useProfile.ts:5`

### API-035 — Open Event Setup

- Frontend: `openSetup`.
- Endpoint: **POST** `/v1/events/{event_id}/setup/draft`.
- Request: `{}; Idempotency-Key`.
- Response `data`: `SetupState`.
- Validation: Current confirmed compatible stages/work/actors; ensure config draft idempotently.
- State effect: **Yes: initialize setup draft only**. Entity: `event_setup_revision`.
- Current evidence: `frontend/src/features/event-setup/useSetup.ts:5`

### API-036 — Read setup overview and finalization checklist

- Frontend: `readSetup`.
- Endpoint: **GET** `/v1/events/{event_id}/setup`.
- Request: `path event_id`.
- Response `data`: `SetupState`.
- Validation: Owner; return actual checklist and ledger-derived availability.
- State effect: **None**. Entity: `event_setup_revision, reservation`.
- Current evidence: `frontend/src/features/event-setup/useSetup.ts:5`

### API-037 — Save Setup Draft

- Frontend: `saveSetupDraft`.
- Endpoint: **POST** `/v1/events/{event_id}/setup/checkpoints`.
- Request: `{expected_setup_version}; If-Match`.
- Response `data`: `{saved:true,configuration_revision}`.
- Validation: Current owner draft; do not fabricate checklist completion.
- State effect: **Yes: setup checkpoint only**. Entity: `event_setup_revision`.
- Current evidence: `frontend/src/features/event-setup/EventSetup.tsx:18`; `frontend/src/features/event-setup/FinalizePublish.tsx:13`

### API-038 — Save setup location, resources, visibility/registration, communications or checklist review

- Frontend: `saveSetupSection`.
- Endpoint: **PATCH** `/v1/events/{event_id}/setup/sections/{section}`.
- Request: `section: location or resources or participation or communications or invites or sponsors; {data: typed section}; If-Match`.
- Response `data`: `{saved:true,setup_revision}`.
- Validation: Section schema; reported resource quantities never inventory; visibility review explicit; no sent invitations.
- State effect: **Yes: draft section; invalidate exact final review**. Entity: `event_setup_revision`.
- Current evidence: `frontend/src/features/event-setup/EventSetup.tsx:16`; `frontend/src/features/event-setup/EventSetup.tsx:18`; `frontend/src/features/event-setup/FinalizePublish.tsx:13`

### API-039 — Add person/group/import CSV initial invites

- Frontend: `addInitialInvite`.
- Endpoint: **POST** `/v1/events/{event_id}/setup/invitation-drafts`.
- Request: `{label,kind:individual or group or organization,email?,phone?,role_id?}; Idempotency-Key`.
- Response `data`: `{invite: InvitationDraft}`.
- Validation: Bound identifiers; valid role same plan; valid contact shape; no membership/acceptance/delivery.
- State effect: **Yes: draft entry only**. Entity: `event_setup_revision`.
- Current evidence: `frontend/src/features/event-setup/EventSetup.tsx:16`

### API-040 — Remove draft invitation

- Frontend: `removeInitialInvite`.
- Endpoint: **DELETE** `/v1/events/{event_id}/setup/invitation-drafts/{invite_id}`.
- Request: `path IDs; If-Match`.
- Response `data`: `{removed:true,setup_revision}`.
- Validation: Owner; only draft may be removed; no revocation of real access implied.
- State effect: **Yes: remove draft entry**. Entity: `event_setup_revision`.
- Current evidence: `frontend/src/features/event-setup/EventSetup.tsx:18`

### API-041 — Add prospective sponsor/partner

- Frontend: `addPartnerDraft`.
- Endpoint: **POST** `/v1/events/{event_id}/setup/partner-drafts`.
- Request: `{label,support_type,details?}; Idempotency-Key`.
- Response `data`: `{partner: PartnerDraft}`.
- Validation: No sponsor acceptance, funds or inventory credited.
- State effect: **Yes: partner discussion draft only**. Entity: `event_setup_revision`.
- Current evidence: `frontend/src/features/event-setup/EventSetup.tsx:16`

### API-043 — Manage Participant Tags & Demographics

- Frontend: `saveParticipantConfiguration`.
- Endpoint: **PUT** `/v1/events/{event_id}/setup/participant-configuration`.
- Request: `{collect_insights,public_aggregates,fields:{age_range,neighborhood,experience_level,participation_interest},custom_tags:ParticipantTag[],questions:ParticipantQuestion[]}; If-Match`.
- Response `data`: `{saved:true,individual_data_public:false,configuration_version}`.
- Validation: Stable tag/question IDs, supported answers/options, archived removal, bounded sizes; publish exact revision.
- State effect: **Yes: draft collection/visibility schema; no inferred answers/consent**. Entity: `event_setup_revision`.
- Current evidence: `frontend/src/features/event-setup/EventSetup.tsx:18`

### API-044 — Choose publish-now or save scheduled intent

- Frontend: `savePublishPreferences`.
- Endpoint: **PATCH** `/v1/events/{event_id}/setup/publication-preferences`.
- Request: `{mode:now or scheduled,date?,time?,timezone?}; If-Match`.
- Response `data`: `{saved:true,scheduler_connected:boolean,scheduled_intent?}`.
- Validation: Valid timezone/date; until scheduling exists reject actual scheduled publish as unavailable.
- State effect: **Yes: publication intent only**. Entity: `event_setup_revision`.
- Current evidence: `frontend/src/features/event-setup/FinalizePublish.tsx:13`

### API-045 — Finalize Current Configuration

- Frontend: `finalizeEvent`.
- Endpoint: **POST** `/v1/events/{event_id}/finalizations`.
- Request: `{confirm_review:true,expected_setup_version,expected_plan_id}; If-Match`.
- Response `data`: `{lifecycle:finalized,publication:unpublished,finalization_id}`.
- Validation: Only required checklist gates; exact plan/config reviewed; optional resource/governance gaps remain visible.
- State effect: **Yes: final review; does not publish**. Entity: `event, review_decision`.
- Current evidence: `frontend/src/features/event-setup/FinalizePublish.tsx:11`

### API-046 — Publish Event

- Frontend: `publishEvent`.
- Endpoint: **POST** `/v1/events/{event_id}/publications`.
- Request: `{finalization_id,expected_versions}; Idempotency-Key, If-Match`.
- Response `data`: `{publication_id,publication:published,visibility,plan_id}`.
- Validation: Current finalization digest; coherent plan/config; publish atomically with opportunities/outbox.
- State effect: **Yes: release visible profile and opportunities**. Entity: `publication, published_role`.
- Current evidence: `frontend/src/features/event-setup/FinalizePublish.tsx:12`

### API-105 — Manage public cover/visibility

- Frontend: `saveOrganizerProfile`.
- Endpoint: **PATCH** `/v1/events/{event_id}/profile`.
- Request: `{cover_asset_id? or legacy cover_data_url?,visibility?,confirm?}; If-Match`.
- Response `data`: `{saved:true,profile_revision,publication_id}`.
- Validation: Organizer; approved media; visibility requires explicit review; create publication revision, do not mutate frozen released config.
- State effect: **Yes: profile/media or explicit visibility publication revision**. Entity: `publication, content_entry, media_asset`.
- Current evidence: `frontend/src/features/organizer/OrganizerProfile.tsx:8`

### API-106 — Upload public Event Photos

- Frontend: `addApprovedPhoto`.
- Endpoint: **POST** `/v1/events/{event_id}/photos`.
- Request: `{media_asset_id,caption,approved:true}; legacy data_url translated to upload first`.
- Response `data`: `{saved:true,photo_id}`.
- Validation: Organizer; real uploaded asset; approval to display is not execution verification; honor media privacy.
- State effect: **Yes: approved gallery entry only**. Entity: `content_entry, media_asset`.
- Current evidence: `frontend/src/features/event-profile/ProfileTabs.tsx:13`

## participation

### API-003 — Load Join Events listing and filters

- Frontend: `joinEvents`.
- Endpoint: **GET** `/v1/participation-opportunities`.
- Request: `query: q?, category?, cursor?, limit?`.
- Response `data`: `{items: JoinEvent[], next_cursor}`.
- Validation: Published open opportunities; return role needs, not assigned people.
- State effect: **None**. Entity: `event, published_role`.
- Current evidence: `frontend/src/features/participation/JoinEvents.tsx:11`

### API-004 — My Events categories and current-account Join/Support gate

- Frontend: `myEvents`.
- Endpoint: **GET** `/v1/me/events`.
- Request: `query: relationship=all or requests or participating or organizing; cursor?,limit?`.
- Response `data`: `{items: MyEvent[],next_cursor}`.
- Validation: Derive account from auth; accepted commitments distinguish Participating; event-specific membership.
- State effect: **None**. Entity: `application, assignment, event_grant`.
- Current evidence: `frontend/src/features/event-profile/useEventRelationship.ts:7`; `frontend/src/features/participation/MyEvents.tsx:9`

### API-047 — Event-specific seven-section participant workspace before and after acceptance

- Frontend: `participationState`.
- Endpoint: **GET** `/v1/events/{event_id}/participation/me`.
- Request: `query application_id? (must be caller-owned)`.
- Response `data`: `ParticipationState`.
- Validation: Personal actor; event visibility; own app/answers/availability/commitments; only assigned work and permitted communications.
- State effect: **None**. Entity: `application, assignment`.
- Current evidence: `frontend/src/features/participation/useParticipation.ts:5`

### API-048 — Organizer Participants and Roles & Assignments / candidate choices

- Frontend: `organizerParticipants`.
- Endpoint: **GET** `/v1/events/{event_id}/organizer/participants`.
- Request: `query cursor?,limit?,status?,role_id?,q?`.
- Response `data`: `{event,applications:ParticipantApplication[],assignments:ParticipantAssignment[],roles,work,templates,configuration,next_cursor}`.
- Validation: Event organizer; scoped delegates receive separate narrowed view; private answers never public.
- State effect: **None**. Entity: `application, assignment, actor_requirement`.
- Current evidence: `frontend/src/features/organizer/OrganizerRoles.tsx:10`; `frontend/src/features/participation/ParticipantReviewPanel.tsx:9`

### API-049 — Four-step application create/autosave/back/edit

- Frontend: `saveApplicationDraft`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/draft`.
- Request: `{application_id?,step?:1..4,role_ids?,intervals?:RelativeSchedule[],answers?:ApplicationAnswers}; If-Match when existing`.
- Response `data`: `{application: ParticipantApplication}`.
- Validation: Authenticated owner; ensure one active application/event/account; configured questions; valid published roles; version answer schema.
- State effect: **Yes: private draft/checkpoint only**. Entity: `application, application_revision`.
- Current evidence: `frontend/src/features/participation/JoinApplication.tsx:13`; `frontend/src/features/participation/JoinApplication.tsx:15`; `frontend/src/features/participation/JoinApplication.tsx:17`

### API-050 — Next application step

- Frontend: `advanceApplication`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/steps/{step}/review`.
- Request: `{expected_application_version}; If-Match`.
- Response `data`: `{application: ParticipantApplication}`.
- Validation: Owner; advance only next step; roles/availability/required answers validate before marking reviewed.
- State effect: **Yes: reviewed wizard checkpoint only**. Entity: `application`.
- Current evidence: `frontend/src/features/participation/JoinApplication.tsx:16`

### API-051 — Submit Join Request and navigate My Events

- Frontend: `submitApplication`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/submit`.
- Request: `{acknowledged:true,availability_acknowledged:true,expected_plan_id,configuration_version}; If-Match`.
- Response `data`: `{application: ParticipantApplication,assignments_created:0}`.
- Validation: Four steps reviewed, recruitment open, current plan/config, original availability consistent, explicit acknowledgements.
- State effect: **Yes: submitted request only; no assignment**. Entity: `application, application_revision`.
- Current evidence: `frontend/src/features/participation/JoinApplication.tsx:18`

### API-052 — Withdraw request

- Frontend: `withdrawApplication`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/withdraw`.
- Request: `{reason?}; If-Match`.
- Response `data`: `{application: ParticipantApplication}`.
- Validation: Owner; decline/withdraw live offers/commitments first; no silent acceptance cancellation.
- State effect: **Yes: request withdrawn**. Entity: `application`.
- Current evidence: `frontend/src/features/participation/ApplicationStatus.tsx:9`

### API-053 — Start Human Review

- Frontend: `queueApplicationReview`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/begin-review`.
- Request: `{expected_application_version}; If-Match`.
- Response `data`: `{application: ParticipantApplication}`.
- Validation: Organizer; submitted current application; no implied approval.
- State effect: **Yes: pending human review**. Entity: `application`.
- Current evidence: `frontend/src/features/participation/ParticipantReviewPanel.tsx:9`

### API-054 — Approve selected roles / decline request

- Frontend: `reviewApplication`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/review`.
- Request: `{approved_role_ids:string[],reviewed_revision,note?}; If-Match`.
- Response `data`: `{application,decision,assignment_created:false}`.
- Validation: Organizer; only requested current roles; partial approval/rejection separate from assignment.
- State effect: **Yes: application approval/rejection only**. Entity: `review_decision, application`.
- Current evidence: `frontend/src/features/participation/ParticipantReviewPanel.tsx:9`

### API-055 — Check specific work-linked assignment

- Frontend: `checkAssignment`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/assignment-checks`.
- Request: `{candidate_id,expected_plan_id}; legacy templateId maps to server-issued candidate ID`.
- Response `data`: `{candidate,conflicts:string[],explanation,model_execution:false}`.
- Validation: Current candidate membership, skills, preference, availability, concurrent role capacity, no overlap; read calculation only.
- State effect: **None: deterministic validation; no reservation/offer**. Entity: `assignment_candidate`.
- Current evidence: `frontend/src/features/participation/ParticipantReviewPanel.tsx:9`

### API-056 — Offer Specific Assignment

- Frontend: `offerAssignment`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/assignment-offers`.
- Request: `{candidate_id,reviewed_terms_digest,expected_plan_id}; If-Match`.
- Response `data`: `{assignment: ParticipantAssignment}`.
- Validation: Approved requested role; repeat conflict/capacity/version checks; source candidate not arbitrary browser template.
- State effect: **Yes: assignment_offered; no accepted commitment**. Entity: `assignment`.
- Current evidence: `frontend/src/features/participation/ParticipantReviewPanel.tsx:9`

### API-057 — Accept Assignment

- Frontend: `acceptAssignment`.
- Endpoint: **POST** `/v1/events/{event_id}/assignments/{assignment_id}/accept`.
- Request: `{terms_key,expected_assignment_version}; If-Match, Idempotency-Key`.
- Response `data`: `{assignment: ParticipantAssignment,commitment_id}`.
- Validation: Assignee only; exact current terms/plan; lock and revalidate availability, overlap, capacity, work status.
- State effect: **Yes: accepted commitment; enables scoped work only**. Entity: `assignment, assignment_decision`.
- Current evidence: `frontend/src/features/participation/ApplicationStatus.tsx:9`

### API-058 — Decline assignment offer

- Frontend: `declineAssignment`.
- Endpoint: **POST** `/v1/events/{event_id}/assignments/{assignment_id}/decline`.
- Request: `{terms_key,reason?}; If-Match`.
- Response `data`: `{assignment: ParticipantAssignment}`.
- Validation: Assignee only; offered/current terms; no forced acceptance.
- State effect: **Yes: declined offer**. Entity: `assignment, assignment_decision`.
- Current evidence: `frontend/src/features/participation/ApplicationStatus.tsx:9`

### API-059 — Withdraw accepted commitment

- Frontend: `withdrawAssignment`.
- Endpoint: **POST** `/v1/events/{event_id}/assignments/{assignment_id}/withdraw`.
- Request: `{reason?}; If-Match`.
- Response `data`: `{assignment,staffing_gap:true}`.
- Validation: Assignee; accepted only; preserve historical work/evidence; expose gap and affected obligations.
- State effect: **Yes: withdraw future commitment; no deletion of history**. Entity: `assignment, assignment_decision`.
- Current evidence: `frontend/src/features/participation/ApplicationStatus.tsx:9`

### API-060 — Update personal experience/preferences/availability

- Frontend: `updateParticipantInformation`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/information-revisions`.
- Request: `{answers?:ApplicationAnswers,intervals?:RelativeSchedule[]}; If-Match`.
- Response `data`: `{saved:true,reassessment_required:true,application_version}`.
- Validation: Owner; accepted commitments remain covered; preserve original; approved app reopens and pending offers become stale.
- State effect: **Yes: new original response revision; no auto reassignment**. Entity: `application_revision, application`.
- Current evidence: `frontend/src/features/participation/ParticipantIntelligenceResponses.tsx:6`

### API-062 — Reassess current participant information

- Frontend: `reopenParticipantReview`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/reopen-review`.
- Request: `{reason?,expected_application_version}; If-Match`.
- Response `data`: `{application,reassessment_required:true}`.
- Validation: Organizer; retain original answers and accepted terms; invalidate relevant pending offers.
- State effect: **Yes: pending review; no silent commitment change**. Entity: `application`.
- Current evidence: `frontend/src/features/participation/ParticipantIntelligencePanel.tsx:6`

### API-063 — Record Human Capability Review

- Frontend: `recordParticipantCapabilityReview`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/capability-reviews`.
- Request: `{role_id,note,confirm:true,evidence_ids?}; If-Match`.
- Response `data`: `{saved:true,permissions_granted:false,review_id}`.
- Validation: Authorized reviewer; specific requirement and basis; self-report is not verified qualification; no role-title grants.
- State effect: **Yes: requirement-specific human capability attestation only**. Entity: `review_decision`.
- Current evidence: `frontend/src/features/participation/ParticipantIntelligencePanel.tsx:5`

### API-064 — Ask participant about alternative responsibility

- Frontend: `requestAlternativeRole`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/alternative-role-requests`.
- Request: `{assessment_id,recommendation_id}; If-Match`.
- Response `data`: `{request,assignment_created:false}`.
- Validation: Organizer; current assessment and permitted alternative; participant agreement still needed.
- State effect: **Yes: invitation to consider alternative only**. Entity: `ai_proposal, application`.
- Current evidence: `frontend/src/features/participation/ParticipantIntelligencePanel.tsx:5`

### API-065 — Accept/decline advisory alternative

- Frontend: `respondAlternativeRole`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/alternative-role-requests/{request_id}/respond`.
- Request: `{decision:accept or decline}; If-Match`.
- Response `data`: `{request,assignment_created:false}`.
- Validation: Own application; current source; agreeing does not accept work or create assignment.
- State effect: **Yes: alternative-role preference response**. Entity: `application_revision`.
- Current evidence: `frontend/src/features/participation/ParticipantIntelligenceResponses.tsx:6`

### API-066 — Ask participant for clarification

- Frontend: `requestParticipantClarification`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/clarifications`.
- Request: `{question}; If-Match`.
- Response `data`: `{clarification,saved:true,delivery_state}`.
- Validation: Organizer; private bounded question; no external message claim before outbox delivery.
- State effect: **Yes: clarification request**. Entity: `application`.
- Current evidence: `frontend/src/features/participation/ParticipantIntelligencePanel.tsx:6`

### API-067 — Answer organizer clarification

- Frontend: `respondParticipantClarification`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/clarifications/{clarification_id}/answer`.
- Request: `{answer}; If-Match`.
- Response `data`: `{saved:true,application_version}`.
- Validation: Owner; preserve original answer history; re-assess advisory source versions.
- State effect: **Yes: original answer revision**. Entity: `application_revision`.
- Current evidence: `frontend/src/features/participation/ParticipantIntelligenceResponses.tsx:6`

### API-068 — Human-selected recommended work offer

- Frontend: `offerRecommendedAssignment`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/recommended-assignment-offers`.
- Request: `{assessment_id,recommendation_id,work_id,reviewed_digest}; If-Match`.
- Response `data`: `{assignment: ParticipantAssignment}`.
- Validation: Organizer; participant agreed/requested role and approved role; recommendation/current sources; deterministic full recheck.
- State effect: **Yes: offered terms only; AI cannot offer independently**. Entity: `assignment`.
- Current evidence: `frontend/src/features/participation/ParticipantIntelligencePanel.tsx:5`

### API-094 — Accept/decline changed commitment from workspace or blocker view

- Frontend: `acceptPlanChange, declinePlanChange`.
- Endpoint: **POST** `/v1/events/{event_id}/assignments/{assignment_id}/plan-change-decisions`.
- Request: `{candidate_id,terms_key,decision:accept or decline}; If-Match, Idempotency-Key`.
- Response `data`: `{decision,unmet_capacity,active_plan_unchanged:true}`.
- Validation: Assignee; notified exact current candidate terms; no coerced acceptance; changes invalidate decisions.
- State effect: **Yes: consent/decline record only; not activation**. Entity: `assignment_decision`.
- Current evidence: `frontend/src/features/participation/PlanChangeConsent.tsx:4`; `frontend/src/features/recovery/RecoveryPanel.tsx:9`

## events

### API-005 — Create Event / start durable draft

- Frontend: `startCreation`.
- Endpoint: **POST** `/v1/events/drafts`.
- Request: `{format?: in_person or online or hybrid}; Idempotency-Key`.
- Response `data`: `CreationState`.
- Validation: Authenticated personal actor; create one new durable event/draft ID, not a Canary Hill fork.
- State effect: **Yes: new draft event; not created/published**. Entity: `event`.
- Current evidence: `frontend/src/app/provider.tsx:13`

### API-006 — Resume creation or success summary

- Frontend: `creation`.
- Endpoint: **GET** `/v1/events/{event_id}/creation`.
- Request: `path event_id`.
- Response `data`: `CreationState`.
- Validation: Owner; event/draft belongs to route; no implicit global current draft.
- State effect: **None**. Entity: `event, context_revision`.
- Current evidence: `frontend/src/features/event-creation/Success.tsx:8`

### API-007 — Autosave four creation steps / Save & Exit

- Frontend: `saveDraft`.
- Endpoint: **PATCH** `/v1/events/{event_id}/draft`.
- Request: `{step:1..4, form: CreationForm}; If-Match`.
- Response `data`: `CreationState`.
- Validation: Bound text; dates/timezone/location format; preserve partial drafts; final validation at confirm.
- State effect: **Yes: editable event brief draft only**. Entity: `event`.
- Current evidence: `frontend/src/features/event-creation/Wizard.tsx:17`; `frontend/src/features/event-creation/Wizard.tsx:20`

### API-008 — Save original execution explanation / corrected voice text

- Frontend: `saveIntent`.
- Endpoint: **POST** `/v1/events/{event_id}/context-revisions`.
- Request: `{text, source: written or reviewed_transcript, source_media_id?}; If-Match`.
- Response `data`: `CreationState with updated ContextRecord`.
- Validation: Keep original text/transcript provenance; bump context version; mark dependent proposals stale.
- State effect: **Yes: new original context revision; no confirmed plan edit**. Entity: `context_revision`.
- Current evidence: `frontend/src/features/event-creation/EventContext.tsx:10`; `frontend/src/features/event-creation/Wizard.tsx:20`

### API-010 — Accept/correct/reject interpreted context

- Frontend: `reviewUnderstanding`.
- Endpoint: **POST** `/v1/events/{event_id}/context-proposals/{proposal_id}/review`.
- Request: `{decision: accept or reject, corrected_interpretation?: Interpretation, source_version, reviewed_digest}; If-Match`.
- Response `data`: `CreationState`.
- Validation: Owner; exact proposal/current source; corrected fields schema validated; retain original.
- State effect: **Yes: reviewed interpretation; not event creation/plan activation**. Entity: `context_revision, review_decision`.
- Current evidence: `frontend/src/features/event-creation/EventContext.tsx:11`

### API-011 — Review & Create event

- Frontend: `createEvent`.
- Endpoint: **POST** `/v1/events/{event_id}/confirm-creation`.
- Request: `{expected_draft_version, acknowledgements}; If-Match`.
- Response `data`: `CreationState`.
- Validation: Required four-step brief, valid date/format/location, reviewed latest context.
- State effect: **Yes: draft to created_unpublished; same event ID**. Entity: `event`.
- Current evidence: `frontend/src/features/event-creation/Wizard.tsx:21`

## ai

### API-009 — Generate/refine understanding

- Frontend: `suggestUnderstanding`.
- Endpoint: **POST** `/v1/events/{event_id}/context-proposals`.
- Request: `{message?, context_revision}; expected versions`.
- Response `data`: `AsyncRunReceipt then {proposal: UnderstandingProposal}`.
- Validation: Permitted event context only; bounded call; untrusted structured interpretation; no approval.
- State effect: **Yes: pending interpretation artifact only**. Entity: `ai_run, ai_proposal`.
- Current evidence: `frontend/src/features/event-creation/EventContext.tsx:10`

### API-015 — Generate Stage Proposal

- Frontend: `generateStageProposal`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/stage-proposals`.
- Request: `{context_revision, draft_version}; expected versions`.
- Response `data`: `AsyncRunReceipt then {proposal: PlanningProposal}`.
- Validation: Scoped current brief; stage schema, stable IDs, bounded sizes; no direct plan write.
- State effect: **Yes: pending stage proposal only**. Entity: `ai_proposal`.
- Current evidence: `frontend/src/features/planning/StagePlanning.tsx:16`

### API-016 — Stage Planning assistant revision

- Frontend: `reviseStageProposal`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/stage-proposals/revisions`.
- Request: `{message, base_proposal_id?, context_revision, draft_version}`.
- Response `data`: `AsyncRunReceipt then {proposal: PlanningProposal}`.
- Validation: Reject arbitrary authority fields; record assumptions, source manifests, unknowns.
- State effect: **Yes: new pending chat/stage artifact only**. Entity: `ai_proposal`.
- Current evidence: `frontend/src/features/planning/StagePlanning.tsx:16`

### API-023 — Work Design AI assistant

- Frontend: `generateWorkConversation`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/work-proposals`.
- Request: `{message,stage_id?,work_ids?,draft_version}`.
- Response `data`: `AsyncRunReceipt then {proposal: PlanningProposal}`.
- Validation: Bound permitted stage/work scope; no silently changed unrelated work or resource stock.
- State effect: **Yes: pending work proposal only**. Entity: `ai_proposal`.
- Current evidence: `frontend/src/features/planning/WorkDesign.tsx:16`

### API-031 — Generate governance guidance

- Frontend: `generateGovernanceAdvisory`.
- Endpoint: **POST** `/v1/events/{event_id}/governance/assessments`.
- Request: `{context_revision,source_ids?}`.
- Response `data`: `AsyncRunReceipt then GovernanceState`.
- Validation: Only verified references may support claims; distinguish guidance from permits; no external filing.
- State effect: **Yes: advisory artifact only; no official approval**. Entity: `ai_run, ai_proposal`.
- Current evidence: `frontend/src/features/governance/Governance.tsx:17`

### API-061 — Assess fit / refresh simulated recommendation with a real bounded provider later

- Frontend: `assessParticipantApplication`.
- Endpoint: **POST** `/v1/events/{event_id}/applications/{application_id}/assessments`.
- Request: `{application_revision,expected_plan_id}; expected versions`.
- Response `data`: `AsyncRunReceipt then ParticipantIntelligence`.
- Validation: Organizer; permitted capability/availability context only; advisory categories and unknowns; no competence/grants invented.
- State effect: **Yes: advisory assessment only**. Entity: `ai_run, ai_proposal`.
- Current evidence: `frontend/src/features/organizer/OrganizerRoles.tsx:10`; `frontend/src/features/participation/ParticipantIntelligencePanel.tsx:6`

### API-110 — AI Meeting Assistant / Generate Meeting Plan

- Frontend: `createMeetingProposal`.
- Endpoint: **POST** `/v1/events/{event_id}/meeting-proposals`.
- Request: `{purpose?,stage_ids?,work_ids?,time_hints?,attendee_ids?}`.
- Response `data`: `AsyncRunReceipt then {meeting: ManagedMeeting}`.
- Validation: Permitted real participants/grants only; unavailable inputs left unknown; proposal not invited or scheduled.
- State effect: **Yes: proposed meeting only**. Entity: `ai_proposal, meeting`.
- Current evidence: `frontend/src/features/organizer/OrganizerMeetings.tsx:7`

### API-145 — Async proposal/analysis polling through HttpAdapter

- Frontend: `new:aiRunRead`.
- Endpoint: **GET** `/v1/ai-runs/{run_id}`.
- Request: `path run_id`.
- Response `data`: `{id,status,progress,result_ref?,failure?,usage?,source_versions}`.
- Validation: Run owner/authorized scope; sanitized trace, no provider secret/hidden reasoning.
- State effect: **None**. Entity: `ai_run`.
- Current evidence: New support contract; no existing HTTP implementation.

### API-146 — Enable currently unavailable evidence analysis later

- Frontend: `new:evidenceAnalysis`.
- Endpoint: **POST** `/v1/events/{event_id}/evidence/{asset_id}/analysis-runs`.
- Request: `{report_id,task,expected_report_revision}; Idempotency-Key`.
- Response `data`: `AsyncRunReceipt then EvidenceAnalysisResult`.
- Validation: Original authorized asset; capability-tested provider, consent/budget; observations only; report/asset hash binding.
- State effect: **Yes: advisory observation only; no report verification/completion**. Entity: `ai_run, ai_proposal`.
- Current evidence: New support contract; no existing HTTP implementation.

### API-147 — Replace canned audio context/evidence transcription when approved

- Frontend: `new:transcription`.
- Endpoint: **POST** `/v1/events/{event_id}/media/{asset_id}/transcription-runs`.
- Request: `{purpose,language_hints?,expected_source_version}; Idempotency-Key`.
- Response `data`: `AsyncRunReceipt then {transcript_id,original_text,segments?,timing_kind,status}`.
- Validation: Authorized audio; original preserved, retention/consent; machine output unreviewed; no invented word timestamps.
- State effect: **Yes: unreviewed transcript artifact only**. Entity: `ai_run, media_asset`.
- Current evidence: New support contract; no existing HTTP implementation.

## planning

### API-012 — Open planning workspace

- Frontend: `openPlanning`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/draft`.
- Request: `{}; Idempotency-Key`.
- Response `data`: `PlanningState`.
- Validation: Owner; created event; ensure draft idempotently; no GET side effect.
- State effect: **Yes: initialize planning draft only**. Entity: `planning_draft`.
- Current evidence: `frontend/src/features/planning/usePlanning.ts:6`

### API-013 — Load stages, work, roles, warnings and proposals

- Frontend: `readPlanning`.
- Endpoint: **GET** `/v1/events/{event_id}/planning`.
- Request: `path event_id`.
- Response `data`: `PlanningState`.
- Validation: Owner or explicitly authorized design scope; coherent source versions.
- State effect: **None**. Entity: `planning_draft, plan_version`.
- Current evidence: `frontend/src/features/planning/usePlanning.ts:7`

### API-014 — Save planning draft

- Frontend: `savePlanningDraft`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/checkpoints`.
- Request: `{expected_draft_version}; If-Match`.
- Response `data`: `{saved:true, draft_version, checkpoint_id}`.
- Validation: Persist current draft checkpoint; unchanged content need not create plan.
- State effect: **Yes: checkpoint only**. Entity: `planning_draft`.
- Current evidence: `frontend/src/features/planning/ActorRequirements.tsx:12`; `frontend/src/features/planning/StagePlanning.tsx:16`; `frontend/src/features/planning/WorkDesign.tsx:16`

### API-017 — Drag/resize/edit stage timing

- Frontend: `proposeStageEdit`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/stage-edits`.
- Request: `{stage_id,start_day,duration_days}; If-Match`.
- Response `data`: `{proposal: PlanningProposal}`.
- Validation: Positive relative days, stage membership, dependency/child compatibility checks.
- State effect: **Yes: manual pending change set; active plan unchanged**. Entity: `planning_draft, ai_proposal`.
- Current evidence: `frontend/src/features/planning/StagePlanning.tsx:13`

### API-018 — Auto Arrange stages

- Frontend: `proposeAutoArrange`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/arrangements`.
- Request: `{expected_draft_version}; If-Match`.
- Response `data`: `{proposal: PlanningProposal, feasibility, violations}`.
- Validation: Deterministic precedence/calendar/capacity check; unknown resources not feasible by default.
- State effect: **Yes: pending arrangement only**. Entity: `planning_draft`.
- Current evidence: `frontend/src/features/planning/StagePlanning.tsx:16`

### API-019 — Apply reviewed stage/chat changes

- Frontend: `approvePlanningChat, approveStageEdit`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/proposals/{proposal_id}/apply`.
- Request: `{reviewed_digest, expected_source_versions}; If-Match`.
- Response `data`: `{applied:true,draft_version}`.
- Validation: Owner; current proposal/schema; dependency and child compatibility; edit draft only.
- State effect: **Yes: approved proposal applied to draft; not active confirmed plan**. Entity: `planning_draft, review_decision`.
- Current evidence: `frontend/src/features/planning/StagePlanning.tsx:14`

### API-020 — Reject stage or work proposal

- Frontend: `rejectPlanningProposal`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/proposals/{proposal_id}/reject`.
- Request: `{reason?, reviewed_digest}; If-Match`.
- Response `data`: `{status: rejected}`.
- Validation: Owner; proposal still pending; append decision; preserve artifact.
- State effect: **Yes: proposal decision only**. Entity: `ai_proposal, review_decision`.
- Current evidence: `frontend/src/features/planning/StagePlanning.tsx:16`; `frontend/src/features/planning/WorkDesign.tsx:16`

### API-021 — Confirm Stage Plan

- Frontend: `confirmStagePlan`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/stage-confirmations`.
- Request: `{proposal_id,expected_draft_version}; If-Match`.
- Response `data`: `{stage_confirmed:true,plan_id,draft_version}`.
- Validation: Current proposal, event/context, acyclic stage graph, child stale markers.
- State effect: **Yes: confirmed planning milestone; invalidate incompatible children**. Entity: `plan_version, planning_draft`.
- Current evidence: `frontend/src/features/planning/StagePlanning.tsx:15`

### API-022 — Edit work intent, dependencies, volume, effort, resource demand or timeline

- Frontend: `reviseWorkDesign`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/work-edits`.
- Request: `{work_id,patch:{title?,outcome?,duration_hours?,start_day?,effort?,dependency_ids?,volume?:Quantity,resource_quantities?}}; If-Match`.
- Response `data`: `{proposal: PlanningProposal}`.
- Validation: Same event; units/nonnegative finite quantities; DAG and schedule feasibility; preserve original revision.
- State effect: **Yes: pending manual work edit only**. Entity: `planning_draft`.
- Current evidence: `frontend/src/features/planning/WorkDesign.tsx:14`; `frontend/src/features/planning/WorkDesign.tsx:16`

### API-024 — Apply reviewed work proposal

- Frontend: `approveWorkDesign`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/work-proposals/{proposal_id}/apply`.
- Request: `{reviewed_digest,expected_source_versions}; If-Match`.
- Response `data`: `{applied:true,draft_version}`.
- Validation: Owner; validate exact diff, quantities, dependencies and stage windows.
- State effect: **Yes: draft work revisions; actor derivation becomes stale**. Entity: `planning_draft, review_decision`.
- Current evidence: `frontend/src/features/planning/WorkDesign.tsx:15`

### API-025 — Confirm work design

- Frontend: `confirmWorkDesign`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/work-confirmations`.
- Request: `{expected_draft_version}; If-Match`.
- Response `data`: `{work_confirmed:true,plan_id}`.
- Validation: Confirmed compatible stages; valid graph, units, schedules; mark actors stale.
- State effect: **Yes: confirmed work milestone**. Entity: `plan_version, planning_draft`.
- Current evidence: `frontend/src/features/planning/WorkDesign.tsx:16`

### API-026 — Derive planned actor structure

- Frontend: `deriveActorRequirements`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/actor-derivations`.
- Request: `{expected_work_revision}; If-Match`.
- Response `data`: `{requirements: ActorRequirement[],derived_from}`.
- Validation: Derive deterministic coverage from confirmed work; optional AI explanations cannot create people.
- State effect: **Yes: planned requirements only; no assignments/grants**. Entity: `planning_draft`.
- Current evidence: `frontend/src/features/planning/ActorRequirements.tsx:12`

### API-027 — Edit role count and capabilities

- Frontend: `reviewActorRequirement`.
- Endpoint: **PATCH** `/v1/events/{event_id}/planning/actor-requirements/{role_id}`.
- Request: `{headcount:number or null,capabilities:string[]}; If-Match`.
- Response `data`: `{requirement: ActorRequirement,draft_version}`.
- Validation: Explicit null for unknown headcount; skills, peak coverage, referenced work valid.
- State effect: **Yes: reviewed requirement draft only**. Entity: `planning_draft`.
- Current evidence: `frontend/src/features/planning/ActorRequirements.tsx:12`

### API-028 — Add Role

- Frontend: `addActorRequirement`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/actor-requirements`.
- Request: `{stage_id,title}; If-Match`.
- Response `data`: `{requirement: ActorRequirement}`.
- Validation: Stage in current draft; server ID; no actor permission generated.
- State effect: **Yes: additional planned role requirement**. Entity: `planning_draft`.
- Current evidence: `frontend/src/features/planning/ActorRequirements.tsx:12`

### API-029 — Confirm Actor Structure

- Frontend: `confirmActorRequirements`.
- Endpoint: **POST** `/v1/events/{event_id}/planning/actor-confirmations`.
- Request: `{expected_draft_version,expected_derived_from}; If-Match`.
- Response `data`: `{actors_confirmed:true,plan_id}`.
- Validation: Parent stage/work versions match; references and requirements coherent.
- State effect: **Yes: coherent planning confirmation; not participants or execution**. Entity: `plan_version`.
- Current evidence: `frontend/src/features/planning/ActorRequirements.tsx:12`

### API-096 — Activate Validated Revision

- Frontend: `activatePlanRevision`.
- Endpoint: **POST** `/v1/events/{event_id}/plan-candidates/{candidate_id}/activate`.
- Request: `{expected_active_plan_id,expected_candidate_version}; If-Match, Idempotency-Key`.
- Response `data`: `{active_plan_id,previous_plan_id,activation_id,versions}`.
- Validation: Organizer; atomic revalidation/locking, all consents, valid graph and resources; never fixed plan-v2 ID.
- State effect: **Yes: atomic active-plan switch plus approved dispositions and outbox**. Entity: `plan_version, assignment, reservation, audit`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

## governance

### API-030 — Read advisory assessment/ticket/document status

- Frontend: `governanceState`.
- Endpoint: **GET** `/v1/events/{event_id}/governance`.
- Request: `path event_id`.
- Response `data`: `GovernanceState`.
- Validation: Owner; protect document metadata; governance incomplete is not blanket planning gate.
- State effect: **None**. Entity: `governance_ticket`.
- Current evidence: `frontend/src/features/governance/Governance.tsx:12`; `frontend/src/features/governance/Governance.tsx:13`

### API-032 — Start Governance Ticket

- Frontend: `startGovernanceTicket`.
- Endpoint: **POST** `/v1/events/{event_id}/governance/tickets`.
- Request: `{}; Idempotency-Key`.
- Response `data`: `{ticket: GovernanceTicket}`.
- Validation: Owner; unique active internal ticket; no government submission implied.
- State effect: **Yes: internal follow-up record**. Entity: `governance_ticket`.
- Current evidence: `frontend/src/features/governance/Governance.tsx:15`

### API-033 — Upload governance supporting document

- Frontend: `recordGovernanceDocument`.
- Endpoint: **POST** `/v1/events/{event_id}/governance/tickets/{ticket_id}/documents`.
- Request: `{media_asset_id,document_type,name}; legacy metadata {size,mime} mapped by adapter`.
- Response `data`: `{document: GovernanceDocument}`.
- Validation: Verified completed upload and authorized asset link; metadata alone is not a durable document.
- State effect: **Yes: supporting document reference; submitted_not_verified**. Entity: `governance_ticket, media_asset`.
- Current evidence: `frontend/src/features/governance/Governance.tsx:16`

### API-034 — Toggle governance updates/reminders

- Frontend: `updateGovernanceReminders`.
- Endpoint: **PATCH** `/v1/events/{event_id}/governance/tickets/{ticket_id}/reminders`.
- Request: `{email_updates:boolean,remind_documents:boolean}; If-Match`.
- Response `data`: `{saved:true,delivery_state}`.
- Validation: Owner/contact consent; schedule outbox only if provider configured; do not claim email sent.
- State effect: **Yes: preferences/notification intent**. Entity: `governance_ticket, outbox_event`.
- Current evidence: `frontend/src/features/governance/Governance.tsx:17`

## sponsorship

### API-042 — Accept sponsor offer from setup or organizer panel

- Frontend: `acceptSetupSponsorOffer, acceptSponsorOffer`.
- Endpoint: **POST** `/v1/events/{event_id}/sponsor-offers/{offer_id}/accept`.
- Request: `{expected_offer_version,reviewed_terms}; If-Match`.
- Response `data`: `{offer: SponsorOffer,inventory_credited:0}`.
- Validation: Organizer; current submitted/pledged offer; membership and event scope; no delivery credit.
- State effect: **Yes: accepted sponsor obligation; not inventory**. Entity: `sponsor_offer, review_decision`.
- Current evidence: `frontend/src/features/event-setup/EventSetup.tsx:18`; `frontend/src/features/sponsor-offers/OrganizerSponsorPanel.tsx:8`

### API-118 — Sponsor dashboard, opportunities, profile/settings, offers, map and impact

- Frontend: `sponsorPortal`.
- Endpoint: **GET** `/v1/organizations/{organization_id}/sponsor-portal`.
- Request: `path organization_id; optional opportunities filters/cursor`.
- Response `data`: `SponsorPortal`.
- Validation: Authenticated organization member; only that organization offers/contact/portfolio; other events require visibility.
- State effect: **None**. Entity: `organization, membership, sponsor_offer`.
- Current evidence: `frontend/src/features/sponsor-dashboard/useSponsor.ts:4`

### API-119 — Review sponsor offers and fulfillment

- Frontend: `organizerSponsorOffers`.
- Endpoint: **GET** `/v1/events/{event_id}/organizer/sponsor-offers`.
- Request: `query status?,support_type?,q?,cursor?,limit?`.
- Response `data`: `OrganizerSponsorState`.
- Validation: Organizer; event needs/offers; derive accepted/reported/verified separately.
- State effect: **None**. Entity: `sponsor_offer, resource_requirement`.
- Current evidence: `frontend/src/features/sponsor-offers/OrganizerSponsorPanel.tsx:8`

### API-120 — Registration steps / Edit Organization Profile & Settings

- Frontend: `saveOrganizationDraft`.
- Endpoint: **PATCH** `/v1/organizations/{organization_id}/registration`.
- Request: `{profile:OrganizationProfile,step:1..3}; If-Match`.
- Response `data`: `{organization,registration}`.
- Validation: Authorized representative; contact/privacy/preferences; owned uploaded logo/cover assets replace data URLs.
- State effect: **Yes: organization draft/profile revision only**. Entity: `organization`.
- Current evidence: `frontend/src/features/sponsor-registration/SponsorRegistration.tsx:13`; `frontend/src/features/sponsor-registration/SponsorRegistration.tsx:15`

### API-121 — Review & Create organization

- Frontend: `completeOrganizationRegistration`.
- Endpoint: **POST** `/v1/organizations/{organization_id}/registration/complete`.
- Request: `{profile:OrganizationProfile,step:3,reviewed_version}; If-Match`.
- Response `data`: `{organization,registration_status:complete}`.
- Validation: Required identity/contact fields and scoped membership; no automatic verified badge.
- State effect: **Yes: reviewed organization profile; not external verification**. Entity: `organization`.
- Current evidence: `frontend/src/features/sponsor-registration/SponsorRegistration.tsx:15`

### API-122 — Create/Edit Sponsorship Offer

- Frontend: `saveSponsorOffer`.
- Endpoint: **POST** `/v1/organizations/{organization_id}/offers`.
- Request: `{offer_id?,event_id,resource_id,support_type,description,quantity,unit,estimated_value?,delivery_date,delivery_method,notes,submit:boolean}; If-Match when editing`.
- Response `data`: `{offer: SponsorOffer}`.
- Validation: Representative membership; published matching need; correct support-kind/unit; positive finite quantity; edit draft or revision only; no stock credit.
- State effect: **Yes: draft/submitted pledge; not resource availability**. Entity: `sponsor_offer`.
- Current evidence: `frontend/src/features/sponsor-offers/SponsorOffers.tsx:9`

### API-123 — Submit saved sponsor offer

- Frontend: `submitSponsorOffer`.
- Endpoint: **POST** `/v1/organizations/{organization_id}/offers/{offer_id}/submit`.
- Request: `{reviewed_offer_version}; If-Match`.
- Response `data`: `{offer: SponsorOffer}`.
- Validation: Owner organization; valid current draft/need; immutable offered terms/version.
- State effect: **Yes: submitted pledge**. Entity: `sponsor_offer`.
- Current evidence: `frontend/src/features/sponsor-offers/SponsorOffers.tsx:12`

### API-124 — Withdraw offer

- Frontend: `withdrawSponsorOffer`.
- Endpoint: **POST** `/v1/organizations/{organization_id}/offers/{offer_id}/withdraw`.
- Request: `{reason?}; If-Match`.
- Response `data`: `{offer: SponsorOffer}`.
- Validation: Only own unaccepted offer; accepted obligations require explicit change workflow.
- State effect: **Yes: withdraw pending pledge only**. Entity: `sponsor_offer`.
- Current evidence: `frontend/src/features/sponsor-offers/SponsorOffers.tsx:12`

### API-125 — Reject sponsor offer

- Frontend: `rejectSponsorOffer`.
- Endpoint: **POST** `/v1/events/{event_id}/sponsor-offers/{offer_id}/reject`.
- Request: `{reason?}; If-Match`.
- Response `data`: `{offer: SponsorOffer}`.
- Validation: Organizer; current pending event offer; preserve original offer/version.
- State effect: **Yes: rejected pledge**. Entity: `sponsor_offer, review_decision`.
- Current evidence: `frontend/src/features/sponsor-offers/OrganizerSponsorPanel.tsx:8`

### API-126 — Ask sponsor for revision

- Frontend: `requestSponsorRevision`.
- Endpoint: **POST** `/v1/events/{event_id}/sponsor-offers/{offer_id}/revision-requests`.
- Request: `{body}; If-Match`.
- Response `data`: `{saved:true,revision_request,delivery_state}`.
- Validation: Organizer; pending offer; message is not acceptance or fulfillment.
- State effect: **Yes: revision request only**. Entity: `sponsor_offer, outbox_event`.
- Current evidence: `frontend/src/features/sponsor-offers/OrganizerSponsorPanel.tsx:8`

### API-127 — Report sponsor delivery/availability

- Frontend: `reportSponsorFulfillment`.
- Endpoint: **POST** `/v1/organizations/{organization_id}/offers/{offer_id}/fulfillment-reports`.
- Request: `{quantity,reference,evidence_ids?}; Idempotency-Key`.
- Response `data`: `{fulfillment,reported:number,verified:number}`.
- Validation: Representative; accepted matching offer; quantity/unit/ref; sponsor report unverified; duplicate report detection.
- State effect: **Yes: unverified claimed delivery; no inventory**. Entity: `sponsor_fulfillment_report`.
- Current evidence: `frontend/src/features/sponsor-offers/SponsorOffers.tsx:12`

### API-129 — Verify non-stock sponsor support

- Frontend: `verifySponsorFulfillment`.
- Endpoint: **POST** `/v1/events/{event_id}/sponsor-offers/{offer_id}/fulfillment-verifications`.
- Request: `{quantity,reference,evidence_ids?,note?}; If-Match, Idempotency-Key`.
- Response `data`: `{verification_id,offer,verified_quantity}`.
- Validation: Organizer; non-stock funding/service/expertise type; unique evidence/ref; no fictitious cash payment, inventory or actual volunteer assignments.
- State effect: **Yes: verified non-stock contribution; not stock or participant registration**. Entity: `sponsor_fulfillment_report, review_decision`.
- Current evidence: `frontend/src/features/sponsor-offers/OrganizerSponsorPanel.tsx:8`

### API-150 — Replace the fixed seeded organization when registering a new sponsor

- Frontend: `new:organizationDraft`.
- Endpoint: **POST** `/v1/organizations/drafts`.
- Request: `{profile?:OrganizationProfile}; Idempotency-Key`.
- Response `data`: `{organization_id,membership,registration}`.
- Validation: Authenticated personal actor; explicit create-organization permission/policy; never grant event organizer authority.
- State effect: **Yes: organization draft and scoped creator membership**. Entity: `organization, membership`.
- Current evidence: New support contract; no existing HTTP implementation.

## execution

### API-069 — My Work / authorized report review / stage status

- Frontend: `executionState`.
- Endpoint: **GET** `/v1/events/{event_id}/execution`.
- Request: `path event_id; query work_id?,stage_id?`.
- Response `data`: `ExecutionState`.
- Validation: Assigned work or scoped stage grant/organizer; narrow reports/evidence; no global state snapshot.
- State effect: **None**. Entity: `work_execution, execution_report`.
- Current evidence: `frontend/src/features/execution/useExecution.ts:4`

### API-070 — Start assigned work

- Frontend: `startAssignedWork`.
- Endpoint: **POST** `/v1/events/{event_id}/work/{work_id}/start`.
- Request: `{expected_plan_id,expected_work_version}; If-Match`.
- Response `data`: `{work_id,execution_status:in_progress}`.
- Validation: Current accepted assignment or authorized scope; prerequisites/holds/safety constraints checked.
- State effect: **Yes: work started; not completed**. Entity: `work_execution`.
- Current evidence: `frontend/src/features/execution/WorkExecutionDetail.tsx:8`

### API-071 — Save original progress/completion report

- Frontend: `saveExecutionReport`.
- Endpoint: **POST** `/v1/events/{event_id}/work/{work_id}/report-drafts`.
- Request: `{report_id?,report_revision?,client_reference,body,remaining_work,claim:progress or completion,resource_usage:ResourceUsage[],measurements:Measurement[]}; If-Match`.
- Response `data`: `{report: ExecutionReport}`.
- Validation: Assignee/scoped reviewer; current work/plan; immutable submitted original; finite quantities/known units; idempotent reference.
- State effect: **Yes: original draft/claim only; no ledger/completion/impact**. Entity: `execution_report, execution_report_revision`.
- Current evidence: `frontend/src/features/execution/WorkExecutionDetail.tsx:8`

### API-072 — Attach photo, video or voice recording

- Frontend: `attachExecutionEvidence`.
- Endpoint: **POST** `/v1/events/{event_id}/reports/{report_id}/evidence`.
- Request: `{media_asset_id,expected_report_revision}; legacy LocalEvidence metadata maps after real upload`.
- Response `data`: `{evidence: EvidenceAsset,report_revision}`.
- Validation: Actor can edit report; asset uploaded/scanned, MIME/hash/size checked; owner/event/work linkage; no fake remote receipt.
- State effect: **Yes: durable original evidence link; not verification**. Entity: `media_asset, execution_report_revision`.
- Current evidence: `frontend/src/features/execution/EvidenceAttachments.tsx:6`

### API-073 — Submit Report for Review

- Frontend: `submitExecutionReport`.
- Endpoint: **POST** `/v1/events/{event_id}/reports/{report_id}/submit`.
- Request: `{report_revision}; If-Match, Idempotency-Key`.
- Response `data`: `{report: ExecutionReport}`.
- Validation: Own editable report; exact saved revision; asset availability; freeze original; create outbox/job atomically.
- State effect: **Yes: submitted claim awaiting review**. Entity: `execution_report_revision`.
- Current evidence: `frontend/src/features/execution/WorkExecutionDetail.tsx:8`

### API-074 — Begin Evidence Review

- Frontend: `beginExecutionReview`.
- Endpoint: **POST** `/v1/events/{event_id}/reports/{report_id}/begin-review`.
- Request: `{report_revision}; If-Match`.
- Response `data`: `{report: ExecutionReport}`.
- Validation: Organizer or explicit permitted stage reviewer; submitted report; immutable evidence revision.
- State effect: **Yes: review started**. Entity: `execution_report, review_decision`.
- Current evidence: `frontend/src/features/execution/ReportReviewControls.tsx:6`

### API-075 — Verify / Request Corrections / Reject report

- Frontend: `reviewExecutionReport`.
- Endpoint: **POST** `/v1/events/{event_id}/reports/{report_id}/review`.
- Request: `{decision:verify or needs_correction or reject,note,confirm:true,criteria_satisfied,report_revision}; If-Match`.
- Response `data`: `{report: ExecutionReport,review_decision_id}`.
- Validation: Scoped human reviewer; exact report/evidence hashes; cannot silently overwrite original; completion criteria for completion claims.
- State effect: **Yes: report review outcome only; no consumption/completion/impact**. Entity: `review_decision`.
- Current evidence: `frontend/src/features/execution/ReportReviewControls.tsx:6`

### API-076 — Approve Work Completion

- Frontend: `completeVerifiedWork`.
- Endpoint: **POST** `/v1/events/{event_id}/work/{work_id}/complete`.
- Request: `{report_id,report_revision,confirm:true,criteria_satisfied:true}; If-Match`.
- Response `data`: `{work_id,execution_status:completed,completion_decision_id}`.
- Validation: Human scope; verified exact report; required predecessors complete and no active hold; stable plan refs.
- State effect: **Yes: authoritative work completion; preserve historical plan version**. Entity: `work_execution, review_decision`.
- Current evidence: `frontend/src/features/execution/ReportReviewControls.tsx:6`

### API-077 — Approve stage completion

- Frontend: `completeExecutionStage`.
- Endpoint: **POST** `/v1/events/{event_id}/stages/{stage_id}/complete`.
- Request: `{expected_plan_id,confirm:true}; If-Match`.
- Response `data`: `{stage_completed:true,stage_id}`.
- Validation: Explicit authorized reviewer; all required stage work complete; no AI-completion shortcut.
- State effect: **Yes: stage completion**. Entity: `work_execution, review_decision`.
- Current evidence: `frontend/src/features/execution/ExecutionReviewPanel.tsx:11`

## access

### API-078 — Grant stage-level execution review

- Frontend: `grantExecutionReview`.
- Endpoint: **POST** `/v1/events/{event_id}/review-grants`.
- Request: `{account_id,stage_id,confirm:true,scope:review_execution}; If-Match`.
- Response `data`: `{grant_id,stage_id,permissions}`.
- Validation: Organizer; target has appropriate accepted responsibility; no global organizer/inventory powers; audit/revocation supported.
- State effect: **Yes: explicit scoped review grant**. Entity: `event_grant`.
- Current evidence: `frontend/src/features/execution/ExecutionReviewGrant.tsx:5`

### API-138 — Replace demo login with genuine authenticated session

- Frontend: `new:authLogin`.
- Endpoint: **GET** `/v1/auth/login`.
- Request: `query return_to (same-origin allowlist)`.
- Response `data`: `Redirect to selected identity provider`.
- Validation: Auth provider choice pending; state/nonce/PKCE; no browser account ID as identity.
- State effect: **No business-state change; begin authentication**. Entity: `session`.
- Current evidence: New support contract; no existing HTTP implementation.

### API-139 — Complete login

- Frontend: `new:authCallback`.
- Endpoint: **GET** `/v1/auth/callback`.
- Request: `query code,state`.
- Response `data`: `Redirect + secure session cookie`.
- Validation: Provider validation, state/nonce, same-origin redirects; no trusted demo labels.
- State effect: **Yes: authenticated session/user identity record only**. Entity: `user, session`.
- Current evidence: New support contract; no existing HTTP implementation.

### API-140 — Header current identity and route auth guard

- Frontend: `new:authMe`.
- Endpoint: **GET** `/v1/auth/me`.
- Request: `no body`.
- Response `data`: `{user:{id,display_name},organizations:[{id,permissions}],capabilities}`.
- Validation: Server identity; minimal scoped membership; no global actor-role conflation.
- State effect: **None**. Entity: `user, membership`.
- Current evidence: New support contract; no existing HTTP implementation.

### API-141 — Sign out

- Frontend: `new:logout`.
- Endpoint: **POST** `/v1/auth/logout`.
- Request: `{}; CSRF protection`.
- Response `data`: `{signed_out:true}`.
- Validation: Revoke/clear session; no deletion of accounts or events.
- State effect: **Yes: session ended only**. Entity: `session`.
- Current evidence: New support contract; no existing HTTP implementation.

### API-149 — Persist personal display name when genuine auth replaces identity picker

- Frontend: `new:profileUpdate`.
- Endpoint: **PATCH** `/v1/me/profile`.
- Request: `{display_name}; If-Match`.
- Response `data`: `{user:{id,display_name,version}}`.
- Validation: Authenticated owner; validated bounded name; verified email/credentials managed through selected auth provider, not copied from demo form.
- State effect: **Yes: own display profile only**. Entity: `user`.
- Current evidence: New support contract; no existing HTTP implementation.

## resources

### API-079 — Confirm Consumption in Ledger

- Frontend: `reconcileReportedUsage`.
- Endpoint: **POST** `/v1/events/{event_id}/reports/{report_id}/usage/{usage_id}/consumption-confirmations`.
- Request: `{reservation_id,quantity,confirm:true,client_reference}; Idempotency-Key, If-Match`.
- Response `data`: `{action,transaction_id,replayed:boolean}`.
- Validation: Organizer; verified report, consumable kind, matching reservation/work/unit; no overreported or overreserved quantity; locked ledger.
- State effect: **Yes: verified consumption debit; separate from report claim**. Entity: `resource_movement, reservation`.
- Current evidence: `frontend/src/features/execution/ReportReviewControls.tsx:5`

### API-080 — Confirm Equipment Issued

- Frontend: `issueReportedEquipment`.
- Endpoint: **POST** `/v1/events/{event_id}/reports/{report_id}/usage/{usage_id}/equipment-issues`.
- Request: `{reservation_id,quantity,confirm:true,client_reference}; Idempotency-Key, If-Match`.
- Response `data`: `{action,loan_id,replayed:boolean}`.
- Validation: Organizer; verified report; reusable kind; issue <= approved claim and reserved free equipment.
- State effect: **Yes: equipment custody issued, not consumed**. Entity: `equipment_loan, resource_movement`.
- Current evidence: `frontend/src/features/execution/ReportReviewControls.tsx:5`

### API-081 — Confirm Equipment Returned

- Frontend: `returnReportedEquipment`.
- Endpoint: **POST** `/v1/events/{event_id}/reports/{report_id}/usage/{usage_id}/equipment-returns`.
- Request: `{reservation_id,quantity,confirm:true,client_reference}; Idempotency-Key, If-Match`.
- Response `data`: `{action,loan_id,replayed:boolean}`.
- Validation: Organizer; actual outstanding loan; no duplicate/excess return; release compatible reservation amount.
- State effect: **Yes: equipment returned/released**. Entity: `equipment_loan, reservation, resource_movement`.
- Current evidence: `frontend/src/features/execution/ReportReviewControls.tsx:5`

### API-102 — Add resource request

- Frontend: `saveResourceRequest`.
- Endpoint: **POST** `/v1/events/{event_id}/resource-requests`.
- Request: `{resource_id,quantity,reason}; Idempotency-Key`.
- Response `data`: `{request,saved:true,inventory_credited:0}`.
- Validation: Organizer; requirement belongs to event; positive quantity/matching unit; request is not supply.
- State effect: **Yes: support/procurement request only**. Entity: `resource_request`.
- Current evidence: `frontend/src/features/organizer/OrganizerResources.tsx:7`

### API-128 — Verify material/equipment delivery

- Frontend: `verifySponsorOfferReceipt`.
- Endpoint: **POST** `/v1/events/{event_id}/sponsor-offers/{offer_id}/receipts`.
- Request: `{quantity,reference,evidence_ids?}; If-Match, Idempotency-Key`.
- Response `data`: `{receipt_id,stock_id,offer_id,balance,verified_quantity}`.
- Validation: Organizer; physical consumable/reusable unit; accepted offer; unique real receipt effect; cannot exceed obligation without explicit amendment.
- State effect: **Yes: verified physical inventory receipt only**. Entity: `resource_movement, inventory_lot`.
- Current evidence: `frontend/src/features/sponsor-offers/OrganizerSponsorPanel.tsx:8`

## insights

### API-082 — Publish Human-Verified Measurement

- Frontend: `publishVerifiedMeasurement`.
- Endpoint: **POST** `/v1/events/{event_id}/reports/{report_id}/measurement-verifications`.
- Request: `{metric,note,confirm:true,report_revision}; If-Match`.
- Response `data`: `{impact: VerifiedMeasurement}`.
- Validation: Organizer; human-confirmed value in verified exact report; unit/method/evidence; no duplicate work+metric publication; correction is append-only.
- State effect: **Yes: publish verified metric; never derive weight from photos**. Entity: `impact_measurement, review_decision`.
- Current evidence: `frontend/src/features/execution/ReportReviewControls.tsx:6`

## blockers

### API-083 — Report blocker from assigned work

- Frontend: `submitWorkBlocker`.
- Endpoint: **POST** `/v1/events/{event_id}/work/{work_id}/blockers`.
- Request: `{description,severity:delayed or impossible or unsafe,immediate_help,occurred_at,effect,evidence_ids,client_reference}; Idempotency-Key`.
- Response `data`: `{blocker: RecoveryBlocker,plan_changed:false}`.
- Validation: Assignment/scoped reporting; meaningful original report; authorized same-work evidence; safety hold policy explicit.
- State effect: **Yes: reported blocker only; no implicit plan rewrite**. Entity: `blocker`.
- Current evidence: `frontend/src/features/execution/WorkExecutionDetail.tsx:8`

### API-084 — Organizer and participant blocker views / candidate consent status

- Frontend: `readRecoveryState`.
- Endpoint: **GET** `/v1/events/{event_id}/recovery`.
- Request: `query blocker_id?`.
- Response `data`: `RecoveryState`.
- Validation: Organizer, delegated stage or affected/own work only; organizer-only facts/budgets and full snapshots filtered.
- State effect: **None**. Entity: `blocker, plan_version`.
- Current evidence: `frontend/src/features/recovery/useRecovery.ts:5`

### API-085 — Assign reviewer / confirm primary blocked work / severity

- Frontend: `updateBlockerInvestigation`.
- Endpoint: **PATCH** `/v1/events/{event_id}/blockers/{blocker_id}/investigation`.
- Request: `{severity,urgency,reviewer_id?,primary_work_id?}; If-Match`.
- Response `data`: `{blocker,investigation_version}`.
- Validation: Reviewer in authorized event scope; primary work linked; changing facts invalidates previews/candidates.
- State effect: **Yes: investigation metadata, not active plan**. Entity: `blocker`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-086 — Record Sourced Fact

- Frontend: `recordBlockerFact`.
- Endpoint: **POST** `/v1/events/{event_id}/blockers/{blocker_id}/facts`.
- Request: `{key,value,status:reported or confirmed or unknown,source,visibility:shared or organizer_only,unit?,evidence_ids?}; If-Match`.
- Response `data`: `{fact,investigation_version}`.
- Validation: Scope and confirmation authority; finite quantity/unit compatible; source/evidence recorded; report is not confirmation.
- State effect: **Yes: sourced investigation fact only**. Entity: `blocker_entry`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-087 — Ask blocker question

- Frontend: `askBlockerQuestion`.
- Endpoint: **POST** `/v1/events/{event_id}/blockers/{blocker_id}/questions`.
- Request: `{body,visibility}; If-Match`.
- Response `data`: `{question,investigation_version}`.
- Validation: Allowed reader/manager; bounded text; private visibility protected.
- State effect: **Yes: investigation question**. Entity: `blocker_entry`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-088 — Post investigation update or local mitigation suggestion

- Frontend: `addBlockerUpdate`.
- Endpoint: **POST** `/v1/events/{event_id}/blockers/{blocker_id}/updates`.
- Request: `{body,kind,visibility}; If-Match`.
- Response `data`: `{update,investigation_version}`.
- Validation: Reporter/affected actor or scoped manager; no participant private-authority escalation; unverified suggestions remain unverified.
- State effect: **Yes: update/participant response only**. Entity: `blocker_entry`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-089 — Link permitted original evidence

- Frontend: `linkBlockerEvidence`.
- Endpoint: **POST** `/v1/events/{event_id}/blockers/{blocker_id}/evidence`.
- Request: `{evidence_id}; If-Match`.
- Response `data`: `{blocker,investigation_version}`.
- Validation: Asset readable and relevant to affected work; consent/retention rules; no evidence-based automatic resolution.
- State effect: **Yes: evidence linkage**. Entity: `blocker, media_asset`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-090 — Investigate records and generate recovery alternatives

- Frontend: `evaluateMitigationAlternatives`.
- Endpoint: **POST** `/v1/events/{event_id}/blockers/{blocker_id}/replanning-runs`.
- Request: `{expected_plan_id,investigation_version}; Idempotency-Key`.
- Response `data`: `AsyncRunReceipt then {alternatives: RecoveryOption[],impact,source_versions}`.
- Validation: Compute affected scope deterministically before optional bounded AI; confirmed vs unknown facts; no fabricated provider/budget availability.
- State effect: **Yes: pending alternatives only; active plan unchanged**. Entity: `ai_run, ai_proposal`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-091 — Review Plan Difference

- Frontend: `previewRecoveryCandidate`.
- Endpoint: **POST** `/v1/events/{event_id}/blockers/{blocker_id}/change-previews`.
- Request: `{proposal_id,reason,delay_days?,expected_plan_id,investigation_version}`.
- Response `data`: `{diff:RecoveryDiff[],terms_key,required_assignment_ids,consequences,violations}`.
- Validation: Organizer/event-wide authority; validate allowed affected unfinished scope, completed preservation, source versions and exact diff digest.
- State effect: **None: compute immutable review preview; no active change**. Entity: `ai_proposal, plan_version`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-092 — Approve Candidate Revision

- Frontend: `approveChangeProposal`.
- Endpoint: **POST** `/v1/events/{event_id}/blockers/{blocker_id}/change-candidates`.
- Request: `{proposal_id,reason,delay_days?,reviewed_terms,confirm:true}; If-Match`.
- Response `data`: `{candidate: RecoveryCandidate}`.
- Validation: Human organizer; exact reviewed preview, current investigation/plan/execution; no arbitrary unreviewed diff.
- State effect: **Yes: approved candidate awaiting required consents; active plan unchanged**. Entity: `plan_version, review_decision`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-095 — Validate Activation

- Frontend: `validateParticipantReconfirmation`.
- Endpoint: **POST** `/v1/events/{event_id}/plan-candidates/{candidate_id}/validate`.
- Request: `{expected_candidate_version}`.
- Response `data`: `{valid:boolean,violations:string[],active_plan_id,candidate_plan_id}`.
- Validation: Deterministic recheck plan/work/execution/facts/consents/capacity/reservations/deadline; read-only calculation.
- State effect: **None: preflight is not authority to skip checks at commit**. Entity: `plan_version`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-097 — Reject Candidate with Rationale

- Frontend: `rejectRecoveryCandidate`.
- Endpoint: **POST** `/v1/events/{event_id}/plan-candidates/{candidate_id}/reject`.
- Request: `{reason}; If-Match`.
- Response `data`: `{candidate,status:rejected,active_plan_unchanged:true}`.
- Validation: Organizer; preserve artifact and prior consent history; do not delete active historical plan.
- State effect: **Yes: candidate rejection only**. Entity: `plan_version, review_decision`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-098 — Record Evidence-Backed Resolution

- Frontend: `resolveBlocker`.
- Endpoint: **POST** `/v1/events/{event_id}/blockers/{blocker_id}/resolve`.
- Request: `{reason,evidence_ids,expected_investigation_version}; If-Match`.
- Response `data`: `{blocker,resolution_status:resolved}`.
- Validation: Organizer or explicitly delegated resolver; issue-specific verified facts/evidence; suspension does not prove resolution.
- State effect: **Yes: evidence-backed resolution, not completed work**. Entity: `blocker, review_decision`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-099 — Close blocker with documented reason

- Frontend: `closeRecoveryBlocker`.
- Endpoint: **POST** `/v1/events/{event_id}/blockers/{blocker_id}/close`.
- Request: `{reason,evidence_ids}; If-Match`.
- Response `data`: `{blocker,closure_kind,unresolved_facts}`.
- Validation: Authorized human; documented closure distinct from issue resolved and from plan activation.
- State effect: **Yes: documented closure only**. Entity: `blocker, review_decision`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-148 — Deterministic input to scoped replanning; current recovery DTO already embeds this

- Frontend: `new:affectedScope`.
- Endpoint: **GET** `/v1/events/{event_id}/blockers/{blocker_id}/affected-scope`.
- Request: `path IDs; query base_plan_id?`.
- Response `data`: `{direct,downstream,resource_constrained,requiring_investigation,unaffected,completed,affected_work_ids,source_versions}`.
- Validation: Permissioned graph; actual dependencies plus shared resource/actor conflicts; completed historical scope protected.
- State effect: **None**. Entity: `blocker, plan_version`.
- Current evidence: New support contract; no existing HTTP implementation.

## coordination

### API-093 — Notify affected participants in app

- Frontend: `notifyRecoveryParticipants`.
- Endpoint: **POST** `/v1/events/{event_id}/plan-candidates/{candidate_id}/notifications`.
- Request: `{expected_candidate_version}; Idempotency-Key`.
- Response `data`: `{notified_assignment_ids,delivery_state,external_messages_sent:false until confirmed delivery}`.
- Validation: Organizer; affected assignees only; durable in-app intent and outbox; delivery is not consent.
- State effect: **Yes: durable notification intent/status**. Entity: `outbox_event`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-101 — Add organizer note

- Frontend: `saveOrganizerNote`.
- Endpoint: **POST** `/v1/events/{event_id}/organizer/notes`.
- Request: `{body}; Idempotency-Key`.
- Response `data`: `{saved:true,note}`.
- Validation: Organizer; private bounded text; no plan or execution effect.
- State effect: **Yes: internal note only**. Entity: `content_entry`.
- Current evidence: `frontend/src/features/organizer/OrganizerOverview.tsx:8`

### API-103 — Write/publish/pin internal or public update

- Frontend: `saveOrganizerUpdate`.
- Endpoint: **POST** `/v1/events/{event_id}/updates`.
- Request: `{title,body,audience:public or participants or internal,status:draft or published or scheduled_intent,date?,time?,timezone?,pinned,confirm}; If-Match`.
- Response `data`: `{update,saved:true,scheduler_connected:boolean}`.
- Validation: Organizer; audience; explicit publish review; private message filtering; scheduled intent not sent without scheduler.
- State effect: **Yes: draft/published message or scheduling intent; no operational plan change**. Entity: `content_entry, outbox_event`.
- Current evidence: `frontend/src/features/organizer/OrganizerUpdates.tsx:5`

### API-104 — Public Event Profile Updates editor

- Frontend: `saveAnnouncement`.
- Endpoint: **POST** `/v1/events/{event_id}/announcements`.
- Request: `{title,body,status:draft or published,confirm_publish?}; If-Match`.
- Response `data`: `{saved:true,status,update_id}`.
- Validation: Organizer; public editorial operation; maps into same update store as organizer updates.
- State effect: **Yes: editorial announcement only**. Entity: `content_entry`.
- Current evidence: `frontend/src/features/event-profile/ProfileTabs.tsx:12`

### API-107 — Follow event organizer/event

- Frontend: `toggleEventFollow`.
- Endpoint: **PUT** `/v1/events/{event_id}/following`.
- Request: `{following:boolean}; expected state, not retry-unsafe toggle`.
- Response `data`: `{following:boolean}`.
- Validation: Current authenticated actor; event visible; no organization membership or participant approval implied.
- State effect: **Yes: follow preference only**. Entity: `event_follow`.
- Current evidence: `frontend/src/features/event-profile/EventProfile.tsx:16`

### API-108 — Start Discussion

- Frontend: `startDiscussion`.
- Endpoint: **POST** `/v1/events/{event_id}/discussions`.
- Request: `{title,body}; Idempotency-Key`.
- Response `data`: `{discussion_id,saved:true}`.
- Validation: Authenticated permitted viewer; bounded text/safe rendering; no PII/authority auto-grants.
- State effect: **Yes: public/permitted discussion post**. Entity: `content_entry`.
- Current evidence: `frontend/src/features/event-profile/ProfileTabs.tsx:16`

### API-109 — Reply to discussion

- Frontend: `replyDiscussion`.
- Endpoint: **POST** `/v1/events/{event_id}/discussions/{discussion_id}/replies`.
- Request: `{body}; Idempotency-Key`.
- Response `data`: `{reply_id,saved:true}`.
- Validation: Parent belongs to visible event; bounded content; author from auth.
- State effect: **Yes: discussion reply only**. Entity: `content_entry`.
- Current evidence: `frontend/src/features/event-profile/ProfileTabs.tsx:16`

### API-111 — Schedule/Create Meeting manually

- Frontend: `createOrganizerMeeting`.
- Endpoint: **POST** `/v1/events/{event_id}/meetings`.
- Request: `{title,purpose,agenda:string or string[],account_ids,schedule:RelativeSchedule}; Idempotency-Key`.
- Response `data`: `{meeting: ManagedMeeting}`.
- Validation: Organizer; valid interval/timezone, allowed invitees/event links; creates proposed time, not auto-confirmation.
- State effect: **Yes: proposed coordination meeting**. Entity: `meeting, meeting_invitee`.
- Current evidence: `frontend/src/features/organizer/OrganizerMeetings.tsx:7`

### API-112 — Edit meeting attendees

- Frontend: `reviseMeetingInvitees`.
- Endpoint: **PUT** `/v1/events/{event_id}/meetings/{meeting_id}/invitees`.
- Request: `{account_ids:string[]}; If-Match`.
- Response `data`: `{meeting: ManagedMeeting}`.
- Validation: Organizer; explicit invite grant; availability recheck on confirmation; no draft invite equals access.
- State effect: **Yes: invitation membership/plan only**. Entity: `meeting_invitee`.
- Current evidence: `frontend/src/features/organizer/OrganizerMeetings.tsx:7`

### API-113 — Confirm meeting time

- Frontend: `confirmMeeting`.
- Endpoint: **POST** `/v1/events/{event_id}/meetings/{meeting_id}/confirm`.
- Request: `{reviewed_meeting_version}; If-Match`.
- Response `data`: `{meeting,delivery_state}`.
- Validation: Organizer; compatible actual invitee schedules and valid event time; outbox delivery separate.
- State effect: **Yes: confirmed meeting schedule; not attendance or work acceptance**. Entity: `meeting, outbox_event`.
- Current evidence: `frontend/src/features/organizer/OrganizerMeetings.tsx:7`

### API-114 — Participant Meeting Details and follow-ups

- Frontend: `readMeeting`.
- Endpoint: **GET** `/v1/events/{event_id}/meetings/{meeting_id}`.
- Request: `path IDs`.
- Response `data`: `{meeting: ParticipantMeeting,actions: MeetingAction[]}`.
- Validation: Invitee/organizer or delegated scope; only permitted agenda/actions; join URL must be safe and real.
- State effect: **None**. Entity: `meeting, meeting_action`.
- Current evidence: `frontend/src/features/participation/ParticipantMeetings.tsx:9`

### API-115 — Change My RSVP from organizer or participant view

- Frontend: `setMeetingRsvp`.
- Endpoint: **PUT** `/v1/events/{event_id}/meetings/{meeting_id}/my-rsvp`.
- Request: `{response:going or maybe or declined}; If-Match`.
- Response `data`: `{meeting_id,response}`.
- Validation: Current invited account only; no attendance/schedule confirmation from RSVP.
- State effect: **Yes: own RSVP only**. Entity: `meeting_invitee`.
- Current evidence: `frontend/src/features/organizer/OrganizerMeetings.tsx:7`; `frontend/src/features/participation/ParticipantMeetings.tsx:9`

### API-116 — Add decision/follow-up

- Frontend: `saveMeetingDecision`.
- Endpoint: **POST** `/v1/events/{event_id}/meetings/{meeting_id}/actions`.
- Request: `{title,notes?}; Idempotency-Key`.
- Response `data`: `{action:{status:suggested,human_approval_status:pending,...}}`.
- Validation: Organizer; proposed follow-up, no hidden work/status effects.
- State effect: **Yes: suggested action only**. Entity: `meeting_action`.
- Current evidence: `frontend/src/features/organizer/OrganizerMeetings.tsx:7`

### API-117 — Approve meeting follow-up

- Frontend: `approveMeetingAction`.
- Endpoint: **POST** `/v1/events/{event_id}/meeting-actions/{action_id}/approve`.
- Request: `{reviewed_action_version,confirm:true}; If-Match`.
- Response `data`: `{action,approval_status}`.
- Validation: Organizer/scoped authority; if action changes work route through normal change proposal, not meeting record write.
- State effect: **Yes: approve follow-up; operational effects require owning command**. Entity: `meeting_action, review_decision`.
- Current evidence: `frontend/src/features/organizer/OrganizerMeetings.tsx:7`

## operations

### API-100 — Organizer Overview/Resources/Meetings/Updates/Profile/Insights summaries

- Frontend: `organizerDashboard`.
- Endpoint: **GET** `/v1/events/{event_id}/organizer/dashboard`.
- Request: `path event_id; optional include flags for composed panels`.
- Response `data`: `OrganizerDashboard`.
- Validation: Organizer only; current plan plus current ledgers; no fabricated counters/provider facts; stage delegate uses narrowed execution view.
- State effect: **None**. Entity: `event, assignment, inventory, blocker`.
- Current evidence: `frontend/src/features/organizer/OrganizerShared.tsx:8`

## demo-only

### API-130 — List/switch synthetic identities

- Frontend: `demoAccounts`.
- Endpoint: **DEMO** `No production endpoint`.
- Request: `{} or synthetic identity ID; local/test only`.
- Response `data`: `Local demo state / Identity[] / sample text`.
- Validation: Never ship arbitrary account switching, data reset or replay setup to public production APIs.
- State effect: **No production effect; mutates only explicitly selected synthetic demo storage**. Entity: `demo_fixture`.
- Current evidence: `frontend/src/app/layout.tsx:6`; `frontend/src/features/auth/Signup.tsx:7`; `frontend/src/features/auth/Signup.tsx:8`

### API-131 — Browser-selected demo identity

- Frontend: `setIdentity`.
- Endpoint: **DEMO** `No production endpoint`.
- Request: `{} or synthetic identity ID; local/test only`.
- Response `data`: `Local demo state / Identity[] / sample text`.
- Validation: Never ship arbitrary account switching, data reset or replay setup to public production APIs.
- State effect: **No production effect; mutates only explicitly selected synthetic demo storage**. Entity: `demo_fixture`.
- Current evidence: `frontend/src/app/provider.tsx:10`; `frontend/src/app/provider.tsx:11`

### API-132 — Reset browser-local demo state

- Frontend: `reset`.
- Endpoint: **DEMO** `No production endpoint`.
- Request: `{} or synthetic identity ID; local/test only`.
- Response `data`: `Local demo state / Identity[] / sample text`.
- Validation: Never ship arbitrary account switching, data reset or replay setup to public production APIs.
- State effect: **No production effect; mutates only explicitly selected synthetic demo storage**. Entity: `demo_fixture`.
- Current evidence: `frontend/src/app/provider.tsx:15`

### API-133 — Load canned reviewed sample transcript

- Frontend: `sampleTranscript`.
- Endpoint: **DEMO** `No production endpoint`.
- Request: `{} or synthetic identity ID; local/test only`.
- Response `data`: `Local demo state / Identity[] / sample text`.
- Validation: Never ship arbitrary account switching, data reset or replay setup to public production APIs.
- State effect: **No production effect; mutates only explicitly selected synthetic demo storage**. Entity: `demo_fixture`.
- Current evidence: `frontend/src/features/event-creation/EventContext.tsx:13`

### API-134 — Load ten-person recording scenario

- Frontend: `prepareTenParticipantScenario`.
- Endpoint: **DEMO** `No production endpoint`.
- Request: `{} or synthetic identity ID; local/test only`.
- Response `data`: `Local demo state / Identity[] / sample text`.
- Validation: Never ship arbitrary account switching, data reset or replay setup to public production APIs.
- State effect: **No production effect; mutates only explicitly selected synthetic demo storage**. Entity: `demo_fixture`.
- Current evidence: `frontend/src/features/auth/Signup.tsx:8`

### API-135 — Restore pre-scenario browser snapshot

- Frontend: `restoreTenParticipantSession`.
- Endpoint: **DEMO** `No production endpoint`.
- Request: `{} or synthetic identity ID; local/test only`.
- Response `data`: `Local demo state / Identity[] / sample text`.
- Validation: Never ship arbitrary account switching, data reset or replay setup to public production APIs.
- State effect: **No production effect; mutates only explicitly selected synthetic demo storage**. Entity: `demo_fixture`.
- Current evidence: `frontend/src/features/auth/Signup.tsx:8`

### API-136 — Load recovery fixture replay

- Frontend: `prepareRecoveryReplay`.
- Endpoint: **DEMO** `No production endpoint`.
- Request: `{} or synthetic identity ID; local/test only`.
- Response `data`: `Local demo state / Identity[] / sample text`.
- Validation: Never ship arbitrary account switching, data reset or replay setup to public production APIs.
- State effect: **No production effect; mutates only explicitly selected synthetic demo storage**. Entity: `demo_fixture`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

### API-137 — Restore pre-recovery browser snapshot

- Frontend: `restoreRecoverySession`.
- Endpoint: **DEMO** `No production endpoint`.
- Request: `{} or synthetic identity ID; local/test only`.
- Response `data`: `Local demo state / Identity[] / sample text`.
- Validation: Never ship arbitrary account switching, data reset or replay setup to public production APIs.
- State effect: **No production effect; mutates only explicitly selected synthetic demo storage**. Entity: `demo_fixture`.
- Current evidence: `frontend/src/features/recovery/RecoveryPanel.tsx:9`

## media

### API-142 — Replace IndexedDB/data URL/file-metadata storage with durable upload

- Frontend: `new:uploadStart`.
- Endpoint: **POST** `/v1/media/uploads`.
- Request: `{event_id,purpose:report_evidence or governance_document or public_photo or org_branding,kind,name,mime,size,sha256,report_id?,organization_id?}; Idempotency-Key`.
- Response `data`: `{asset_id,upload_url,method,required_headers,expires_at}`.
- Validation: Scoped owner/use permission; strict limits; opaque object key; signed URL never auth substitute.
- State effect: **Yes: pending upload reservation only**. Entity: `media_asset`.
- Current evidence: New support contract; no existing HTTP implementation.

### API-143 — Finalize upload before linking report/governance/gallery

- Frontend: `new:uploadComplete`.
- Endpoint: **POST** `/v1/media/uploads/{asset_id}/complete`.
- Request: `{sha256,byte_length,storage_etag?}; Idempotency-Key`.
- Response `data`: `{asset_id,status:processing or ready or rejected}`.
- Validation: Server verifies object/MIME/signature/size/hash; scan result; immutable original; do not trust browser completion claim.
- State effect: **Yes: upload finalize/job; not evidence verification**. Entity: `media_asset, job_task`.
- Current evidence: New support contract; no existing HTTP implementation.

### API-144 — Open original evidence/download preview

- Frontend: `new:mediaRead`.
- Endpoint: **GET** `/v1/media/{asset_id}/access`.
- Request: `path asset_id`.
- Response `data`: `{download_url,expires_at,metadata}`.
- Validation: Every access rechecks event/report/content permissions; short-lived signed URL; retention/privacy applied.
- State effect: **None**. Entity: `media_asset`.
- Current evidence: New support contract; no existing HTTP implementation.


## Event Memory — Day 1 design addendum

These **seven new proposed support contracts** do not alter the accepted 142 HTTP contracts/183 frontend call-site reference. The original audit coverage files describe that baseline, not these new requirements. No `AroundYouService` change or frontend screen is needed for the foundation; memory is consumed through backend planning/recovery context ports. All paths below are application APIs, **not claimed Modal or Meta provider endpoints**.

Common rules: actor from verified authentication; event and source scope checked server-side; closed schemas; finite bounds; exact immutable source revisions; `If-Match`/digest for decisions and idempotency keys for commands. Responses use the existing common `data/meta` and error envelope. Unauthorized records do not leak IDs/titles/existence; cross-event reuse requires policy-approved sanitized memories. Source linkage/confidence is never outcome authority.

### Memory wire shapes

```text
SourceRef = { source_kind, source_id, source_revision, source_digest }
ExtractionRequest = { source_refs: SourceRef[], extractor: deterministic | open_weight,
                      schema_version, purpose }
MemoryAssertion = { assertion_id, text, claim_kind, evidence_stage, outcome,
                    evaluation_scope?, evaluation_criteria?, citations: Citation[],
                    uncertainty_reasons[], confidence_basis, model_confidence? }
Citation = { memory_source_id, permitted_source_reference, revision, digest,
             relation: supports | contradicts | qualifies }
MemoryItem = { memory_id, logical_memory_id, revision, event_id, kind, lifecycle,
               visibility, assertions: MemoryAssertion[], applicability,
               provenance: { origin, schema_version, extractor_version, model_profile?,
                             run_id?, review_decision_id? }, digest, supersedes_id? }
MemoryBundle = { items: MemoryItem[], retrieval_id, query_digest, policy_version,
                 selected_revision_manifest, applicability_reasons,
                 limitations[], next_cursor? }
MemoryRun = { run_id, kind, status, source_manifest_digest, candidate_ids[],
              error?: { code, retryable }, status_url }
```

Concrete schemas must bound text/count/limits and enumerate source/purpose kinds. `permitted_source_reference` is a sanitized reference, not an unrestricted URL or private title; retrieving original evidence requires its own permission. Expose only caller-permitted provenance. Model confidence nullable/uncalibrated; relevance and outcome verification are separate. Per-assertion source citations are mandatory, including contradictory evidence. Full field/constraint semantics are in [data model section 8](backend-contract-data-model.md#8-event-memory--derived-intelligence-day-1).

### MEM-001 — Request source-linked extraction

- **POST** `/v1/events/{event_id}/memory/extractions`.
- Request: `ExtractionRequest`; idempotency key. Server bounds source set/budget and derives actor/policy/provider configuration. No arbitrary prompt, provider URL, actor ID or visibility grant.
- Response: **202** `{run: MemoryRun}`. Poll MEM-002. Duplicate identical keyed request returns its original run; same key/different payload conflicts.
- Validation: explicit extract permission plus access to every source revision; same-event source capture unless an explicit approved reusable source policy applies. Resolve hashes and current corrections. Reject invented IDs, unsupported kinds and unsupported extractor capability; open-weight unavailable is explicit `503` or a failed run, never fake success.
- Read/write: **write derived run/job/candidate only**, no authoritative operational state change. Deterministic source projections may publish only under registered fact-copy policy; model extraction always yields candidates. Main domain transaction is already committed.
- Group 1: deterministic implementation plus fake open-weight extraction port in tests; no real Modal call.

### MEM-002 — Read extraction status

- **GET** `/v1/events/{event_id}/memory/extractions/{run_id}`.
- Request: scoped run ID. Response: `{run: MemoryRun}` plus permitted candidate IDs; no private source payload or raw model output by default.
- Validation: requester or authorized event memory reviewer; recheck source confidentiality. Bounded operational failure details, not credentials/provider internals.
- Read only; succeeded means extraction artifacts saved, not verified success of the event/recovery. Group 1 included.

### MEM-003 — Retrieve applicable event memory

- **GET** `/v1/events/{event_id}/memory`.
- Request query: `q?`, `purpose=planning|blocker_recovery|event_review`, `kind?`, `evidence_stage?`, `outcome?`, `limit?`, `cursor?`, `include_reusable=false` by default. Purpose must be allowed for the actor; it does not grant permission. Server context supplies the actual work/conditions where called internally.
- Response: `MemoryBundle` with source-linked results, applicability explanations and limitations; empty `items` is valid. Include successful AND failed records when relevant; do not silently exclude negative outcomes.
- Validation: event/source authorization, current eligible revision, lifecycle, sharing policy, privacy minimization before ranking/pagination; limit capped (initial design cap 20). `include_reusable=true` requests only separately authorized sanitized cross-event lessons, never all events.
- Read only operationally; record retrieval provenance for AI consumption without storing raw private query text in generic logs. Group 1 included with structured PostgreSQL filters/lexical ranking; no model needed.

### MEM-004 — Read exact memory revision

- **GET** `/v1/events/{event_id}/memory/{memory_id}`.
- Request: revision ID; optional explicit historical view is reviewer-only. Response: `{memory: MemoryItem}` or inaccessible/not-found. Historical correction lineage metadata is minimized by access policy.
- Validation: exact event ownership, memory/source access, current eligibility; default consumers cannot bypass supersession by requesting an old ID. Reviewer audit access does not make an old version eligible for planning retrieval.
- Read only; Group 1 included.

### MEM-005 — Review derived candidate

- **POST** `/v1/events/{event_id}/memory/{memory_id}/review`.
- Request: `{decision: publish|reject, reviewed_digest, expected_revision, note?}`; If-Match and idempotency key. Sharing expansion is not implicit in publish.
- Response: `{memory: MemoryItem, decision_id}` or recorded rejection status.
- Validation: authorized memory reviewer; exact candidate/current source digests, valid source-backed assertions, privacy policy. Reject requested outcome promotion not supported by an authoritative source decision; review only publishes a derived synthesis, never confirms execution or changes plans.
- Write derived lifecycle/review/audit only. Internal service and tests required Group 1; expose route only when delivering the review sub-slice.

### MEM-006 — Correct or supersede memory

- **POST** `/v1/events/{event_id}/memory/{memory_id}/corrections`.
- Request: `{reason, correcting_source_refs: SourceRef[], reviewed_digest, expected_revision}`; If-Match/idempotency key. Human text annotations, if allowed, are separately provenance-labeled and cannot be source verification.
- Response: `{replacement_candidate: MemoryItem, supersedes_id, old_eligibility}`. Unsupported old assertions are excluded immediately; valid replacement may remain candidate until reviewed. Do not continue serving a known wrong original while waiting for replacement approval.
- Validation: authorized correcting scope, real source lineage, no cross-event chain/cycles, concurrency/source-version checks. Original sources and immutable memory content retained subject to deletion policy; new revision plus audit, not overwrite.
- Write derived revision/eligibility only; no operational correction via memory. Owning domain corrects operational records first. Internal service/tests Group 1, HTTP later if needed.

### MEM-007 — Retract derived memory

- **POST** `/v1/events/{event_id}/memory/{memory_id}/retract`.
- Request: `{reason, reviewed_digest, expected_revision}`; If-Match/idempotency key. Response: `{memory_id, lifecycle: retracted, decision_id}`.
- Validation: authorized reviewer/sharing administrator, exact target; event-scoped permission cannot erase unrelated events' records. Invalidate cached/indexed results immediately by eligibility checks; retention deletion is a separate protected process.
- Write derived lifecycle/audit only; does not retract the original report, undo an accepted assignment or roll back an active plan. Internal invalidation service is Group 1; standalone route can follow.

### Internal integration contracts (not additional HTTP endpoints)

- `MemoryExtractionPort.extract(input) -> MemoryCandidateBatch`: Modal-hosted open-weight adapter port, source-minimized bounded payload, strict schema, immutable source citations and proposed classifications only. No tools for plan/stock/outcome confirmation. Fake in Group 1; live endpoint/model/auth/runtime remain unverified configuration decisions.
- `MemoryRetrievalPort.retrieve(query, access_scope) -> MemoryBundle`: PostgreSQL implementation; server-derived access scope, no model-selected grant/event list.
- `PlanningContextPort.build(current_state, memory_bundle) -> ScopedPlanningContext`: Muse Spark planning/recovery consumer, labeled authoritative-current vs derived-historical context, per-memory citations and applicability/unknowns. Run manifest records memory revisions and source versions. Revalidate eligibility before proposal application/activation.

Foundation test path: genuine versioned source → durable deterministic extraction → authorized retrieval → source correction/retraction excludes stale result. No broad operational CRUD, embeddings, live model deployment or fixture rewriting is authorized by this addendum.
