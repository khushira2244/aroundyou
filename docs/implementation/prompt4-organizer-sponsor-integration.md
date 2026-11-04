# Prompt 4 — Organizer setup, publication and sponsor integration

Date: 2026-11-03. Core materials sponsorship journey verified through actual local HTTP and Docker PostgreSQL. Browser visual acceptance remains manual.

## Reused

Existing React screens, AroundYouService/HTTP adapter, FastAPI Group 2/3 services, immutable publication snapshots, event version checks, idempotency, organization membership, audit, offer revisions, fulfillment reports and receipt ledger. Existing My Events, landing page and approved layouts remain intact. Prompt 2/3 AI integrations were not changed. No Modal deployment, model calls or paid inference ran (cost: zero model calls).

## Corrections

- Organizer Request Revision now posts a persisted, authorized, audited offer revision request. It does not send an external message or create a commitment. The sponsor sees the request and can reopen the existing offer form to revise a pledged offer. Revised submission uses existing offer/version rules.
- Work/support forms use the published resource's exact unit in HTTP mode; no implicit service/funding unit conversion.
- Organizer receipt review selects the exact pending delivery report and its exact quantity. Equal-sized deliveries no longer depend on an ambiguous first-quantity-match in the adapter. Missing delivery selection blocks the HTTP form.
- Sponsor history marks a fulfillment verified only when its linked receipt has not been reversed. Receipt correction removes current verified credit from history/stats. Duplicate report references within an offer are rejected. Existing unique receipt/fulfillment constraints remain.
- Sponsor Opportunities exclude published events with no support requirements. Existing filters and cards remain. Public event/opportunity organizer labels use the creator's saved display name without exposing contact details or claiming independent verification.
- Sponsor accounts can use the Event Profile Support action to open the existing matching opportunity. Personal support remains a separate sponsor-account flow. The existing location panel reuses GoogleEventMap and persisted event coordinates in HTTP mode.
- Removed misleading synthetic/outside-this-batch messages from the connected receipt flow. Funding and volunteer verification buttons remain unavailable in HTTP because this receipt flow must not imply payment settlement or participant assignments. Their pledges/reports are not inventory.

## Real HTTP verification

Command from backend:

`.venv/Scripts/python.exe tools/verify_prompt4_http.py`

Passed over a real loopback Uvicorn server and HTTP cookie sessions, using the existing development Docker PostgreSQL database. This was not TestClient and was not browser automation. The temporary verification server shut down afterward; it did not stop or replace user runtime services.

Verified:
1. Real organizer/sponsor signup, logout and signin; organization onboarding.
2. Manual test planning, saved setup, explicit finalization/publication, public discovery and canonical Event Profile.
3. Persisted coordinates survived publication; private emergency-contact test marker was absent from the public profile.
4. Sponsor found the published resource requirement, submitted an offer, and saw the organizer's clarification request and acceptance.
5. Accepted commitment and unverified report left available inventory at zero.
6. A separate organizer receipt verified 4 of 10 test units; resource availability became 4 and remaining commitment stayed 6.
7. Sponsor Overview/Offers/Map/History data reflected partial fulfillment and the actual stored coordinates. Repeat reads restored identical offers.
8. Unrelated account could not inspect another organization portal or organizer offers.

Persisted test event: `e2353f67-69db-4157-a720-8e13ba1c238a`.
Test organization: `2657059a-859f-4410-85ea-c0ce6a0bd7c5`.
Test offer: `737e21be-aac5-46c1-84d4-5491860f858d`.

These are explicitly labeled **synthetic integration-test records**, not a real-world initiative or actual goods received. Test evidence references expressly say no actual delivery occurred. No existing data was reset/deleted. The test generated throwaway passwords in memory and did not print/store credentials. Results are in ignored `backend/.tmp/prompt4-http-results.json`.

## Tests and build

Backend (TEMP/TMP = backend/.tmp):

`.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_prompt4_sponsorship.py tests/test_group3.py tests/test_group2.py -q`

36 existing tests passed. The new test initially failed because the existing generic action route captured the new revision-request URL. Route ordering was corrected. The focused new PostgreSQL test subsequently passed, including partial receipt, full 10-unit fulfillment, completion count, correction back to 6 verified units, duplicate reports and cross-account denial:

`.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_prompt4_sponsorship.py -q`

The initial invocation without local network access could not start database tests; it was rerun after access was granted. All executed domain tests use isolated real PostgreSQL, not the development database; the separate actual HTTP verification above uses development PostgreSQL.

Frontend:

`npm test -- tests/sponsor.test.tsx tests/publication.test.tsx tests/http-group3.test.ts tests/live-navigation.test.tsx`

12 passed. Includes existing sponsor journey, setup/finalize/publish, navigation, exact fulfillment selection and revision-request HTTP mapping. The new adapter assertion initially exposed a missing organizer-command mapping, which was corrected before the final green run.

`npm run build`

Passed TypeScript and Vite production build. Existing bundle-size warning remains. `git diff --check` passed (Windows line-ending notices only). Existing Starlette/httpx deprecation warning remains.

## Endpoints

Added: `POST /v1/events/{event_id}/sponsor-offers/{offer_id}/revision-requests`, body `{body: string}`, organizer permissions, If-Match and Idempotency-Key required.

Reused: setup draft/read/section updates; finalizations/publications; events discovery/profile; organization registration and sponsor portal; organization offers/submit/withdraw; organizer sponsor offers; accept/reject; fulfillment reports; resource receipts/corrections; resources; organizer dashboard. No parallel business modules were created.

Database remains at migration `0009`; no Prompt 4 migration required. Existing JSON offer terms/revisions and receipt tables store the changes.

## Files changed for Prompt 4

- backend/app/sponsorship/service.py
- backend/app/sponsorship/projections.py
- backend/app/api/group3.py
- backend/app/publication/service.py
- frontend/src/services/http-adapter.ts
- frontend/src/features/sponsor-offers/OrganizerSponsorPanel.tsx
- frontend/src/features/sponsor-offers/SponsorOffers.tsx
- frontend/src/features/event-profile/EventProfile.tsx
- frontend/tests/http-group3.test.ts
- New: backend/tests/test_prompt4_sponsorship.py
- New: backend/tools/verify_prompt4_http.py
- New: this report

## Manual browser checks and limits

Restart the updated runtime with `./backend/tools/start_live_runtime.ps1` in normal Windows PowerShell; use its reported API URL and `http://127.0.0.1:5173`. Existing processes need the updated code loaded.

As organizer, open an event with all stage/work/actor confirmations, finish Event Setup, review participation/visibility, acknowledge and finalize, then explicitly publish. Open the existing public profile from Discovery/map. Sign into a separate sponsor account, use Sponsor Portal Opportunities, submit an offer for a listed resource, then review/revise/accept it as organizer. Report a partial delivery as sponsor; as organizer select that exact report and enter the actual evidence reference to verify. Refresh resources and all Sponsor Portal sections. Check that unverified promises do not increase availability.

Not verified: browser rendering, Google Maps visual marker placement, pointer interaction and full React-to-live-server browser journey. Component/adapter tests plus real HTTP verification are reported separately and do not count as visual acceptance.

Existing limitations retained honestly: payment processing/settled funding is unavailable; volunteer commitments are not resource receipts; automated scheduled publication is unavailable; sponsor matching is deterministic declared-needs guidance, not live AI; public sponsor recognition still requires authorized configured mentions and is not fabricated; independently verified event impact is not inferred from contributions. No new execution, participation, recovery, Modal or cloud deployment was started.
