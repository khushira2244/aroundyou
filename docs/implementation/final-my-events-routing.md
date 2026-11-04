# Final My Events data binding and navigation

Date: 2026-11-03.

The approved landing component/styles and Sponsor Portal screens/routes were preserved. No Modal deployment or inference ran; Modal remains the intended internal open-weight Event Memory extraction integration.

Changes:
- The existing organizer event list reads authenticated `/v1/me/events`, filters organizer relationships, and no longer adds All/Drafts/Organizing/Completed tabs. Event titles and actions open the existing Organizer Dashboard. Creation drafts select their event in the service and resume the PostgreSQL `draft_step`.
- Backend list navigation uses `/create/{draft_step}` only for creation drafts; created events use `/events/{id}/manage/overview`. Authorization still determines organizer membership; events owned by unrelated users are not included as organizer relationships.
- Existing participant My Events continues using the same backend records, Requests/Participating/Organizing distinctions and assignment consent flow. Approved applications remain Requests until an assignment is accepted. Organizer actions within that existing list use the same dashboard and saved-step targets.
- Sponsor accounts visiting personal My Events routes return to the existing Sponsor Portal. Opportunities, Offers & Commitments, Map and Impact & History were not replaced or redesigned.
- Existing organizer preview now supports a created event without a planning draft, without creating a draft on GET. The existing dashboard data endpoint supports this pre-publication state, returns actual event/audit data and no fabricated operational activity, and marks publication-required modules unavailable. A Continue Planning link opens the existing planning workflow. Operational features that require publication retain their existing guards.

Files for this task:
- backend/app/participation/projections.py
- backend/app/publication/service.py
- backend/app/api/group3.py
- backend/tests/test_browser_accounts.py
- frontend/src/app/App.tsx
- frontend/src/features/organizer/OrganizerEvents.tsx
- frontend/src/features/organizer/OrganizerOverview.tsx
- frontend/src/features/participation/MyEvents.tsx
- frontend/tests/live-navigation.test.tsx
- this report

Verification commands:

From backend (TEMP/TMP set to backend/.tmp):
`.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_browser_accounts.py tests/test_group3.py -q`

From frontend:
`npm test -- tests/live-navigation.test.tsx tests/landing.test.tsx tests/personal-workspace-routing.test.tsx tests/http-adapter.test.ts`
`npm run build`

Frontend: 20 tests passed, including approved/offered/accepted participant navigation, seven workspace sections, event-context isolation across remount/back, existing sponsor navigation, landing navigation and HTTP adapter contracts. Final production build (including TypeScript) passed after all changes. Final backend suite: 13 passed against isolated real PostgreSQL, including the new unpublished-event dashboard regression. The regression initially exposed a publication-only projection; it passed after that correction.

No live browser screenshot comparison was performed. Runtime processes must load updated code before manual testing. Existing bundle-size and Starlette/httpx deprecation warnings may remain. No schema migration, data reset, credentials change, AI call or deployment was required.
