# Prompt 1 — live account and navigation integration

Reviewed and implemented: 2026-11-02. Local development only; no deployment or AI calls.

## Implemented

- Password-backed personal/sponsor signup and signin. Normalized unique email, scrypt password hashes, account lockout after repeated invalid attempts, opaque HttpOnly SameSite cookies, eight-hour sessions, server-side revocation and page-refresh restoration. Cookie writes validate the frontend Origin. Existing signed-bearer integration remains available; the HTTP UI offers no identity picker.
- The optional password field remains visible. **Email-only signup/login is rejected** because email verification is not configured. There is no public email-string login bypass. Password reset, email delivery/verification and production signup throttling are outside this local implementation.
- Account kind comes from stored credentials. Sponsor signup continues through the existing organization form; organization access requires stored representative membership. A sponsor does not automatically gain event creation permissions. Personal accounts cannot create organizations through the new live-account path. Repeated creation of another organization by the same representative is rejected; retrying an idempotent request remains supported.
- Existing users, grants, plans, evidence, demo fixtures and participant state transitions remain intact. Organization names are not proof of identity: matching names never grant membership automatically. Joining/merging independently registered organizations requires a later verified invitation/review flow.
- Organizer `/my-events`: All, Drafts, Organizing, Completed. Backend `/me/events` supplies an authorized `resume_path` based on saved wizard step and confirmed planning/setup state. Published events open the existing organizer dashboard. Completed is empty until an authoritative completion state exists; dates do not imply completion.
- Existing participant listing/workspace is available through `/my-participation` and all seven event-specific participation routes. Legacy `/my-events?tab=requests` and other tab-qualified links still resolve to the existing participant listing. Application approval does not become accepted participation.
- The personal header exposes Organizing and My Participation under its existing My Events control. Sponsor headers omit the personal control and retain the existing six-section sponsor sidebar. `registered_unverified` organizations can enter that portal without receiving a verification badge.
- One Google Maps/Places component powers live discovery, the creation location picker and sponsored-event maps. Demo mode retains its original schematic views. Maps use stored finite, bounded coordinates only. Places selection saves its ID in the existing `locationSource` field (`google-place:<id>`), with address and coordinates in the existing creation JSON. No new location table, per-marker geocoding or fabricated venue coordinate was added.
- Discovery map and list share category/search results from the existing public publication projection. Drafts/private publications remain excluded. Sponsor supported events still derive from accepted support; fulfillment is separately verified.

## HTTP additions

All responses use the existing `data` envelope. Auth writes require an approved local Origin and `credentials: include` in the browser.

| Method/path | Request | Result |
| --- | --- | --- |
| POST `/v1/auth/signup` | `{name,email,password,kind: personal\|sponsor}` | 201, `{identity:{accountId,label,kind}}`, session cookie |
| POST `/v1/auth/signin` | `{email,password}` | 200, stored identity and new session cookie |
| POST `/v1/auth/logout` | `{}` | Revokes current cookie session and clears cookie |
| GET `/v1/me` | Cookie or existing signed bearer | Existing user projection plus authoritative identity |
| GET `/v1/me/events` | Authenticated | Existing relationships plus organizer-only `resume_path` |

No broad CRUD or alternate domain service was introduced. Existing mutation idempotency, expected-version checks and event authorization still apply.

## Database

Docker database `aroundyou`, user `aroundyou_app`, PostgreSQL 16, remains authoritative. Migration `0006` adds only `account_credentials` and `browser_sessions`; it does not replace or reinterpret existing users. Migration `0006` is applied to the confirmed development database.

Initial inspection found one existing user and no organizations. No ten-participant scenario was present in this database; none was imported or deleted. The unchanged local demo fixtures retain that scenario.

The non-destructive Docker smoke check retained one additional **Integration check personal** account and one **Technical integration check — private draft**. Its generated password was held in memory, never printed or written as plaintext. Existing records were preserved.

## Verification

Commands run from the indicated directories:

| Command | Result |
| --- | --- |
| backend: `.venv/Scripts/python.exe tools/run_postgres_tests.py -q` | 145 passed, isolated real PostgreSQL; includes upgrade/downgrade and metadata comparison |
| backend: `.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_browser_accounts.py -q` | 6 passed, including password-whitespace preservation, organization membership, duplicate prevention and cross-account denial |
| backend: `.venv/Scripts/python.exe -m alembic upgrade head` | Applied additive `0006` to Docker development DB; subsequent query confirmed revision |
| backend: `.venv/Scripts/python.exe -m tools.verify_browser_account_persistence` | Passed against Docker DB using actual FastAPI TestClient, including fresh-app restoration and independent persisted read |
| root: `npm --prefix frontend test -- --reporter=dot` | 79 passed after rerunning separately; initial concurrent runs had timeouts |
| root: `npm --prefix frontend run build` | Passed TypeScript and Vite production build; existing large-bundle advisory remains |
| root: `npm --prefix demo test` | 146 passed; fixtures unchanged |
| root: `git diff --check` | Passed |

**Not verified:** host-browser signup/signin rendering, actual Google map rendering, Places selection, Maps billing/referrer authorization and visual screenshot comparison. In-app browser navigation timed out; Windows Computer Use was stopped by automatic review because Chrome's current URL could not be determined reliably. No specific Google key restriction failure was observed or inferred.

The server already running on host port 8000 was identified as older code without the new auth routes. It was not stopped. A new-code process starts inside the tool environment on 8001 but is not reachable from host clients. TestClient verification is explicitly not a host HTTP/browser test.

## Start the live code for browser testing

From the project root in normal Windows PowerShell:

```powershell
.\backend\tools\start_live_runtime.ps1
```

This starts the new FastAPI code on port 8001 without stopping port 8000, verifies its signup route, updates only frontend mode/API URL in ignored `.env.local`, and starts/reuses Vite on 5173. It preserves the Google key and all backend/provider secrets. Vite reloads after its environment file changes.

- Signup: `http://127.0.0.1:5173/signup`
- Signin: `http://127.0.0.1:5173/signin`
- New API: `http://127.0.0.1:8001/docs`

Use `127.0.0.1` consistently for frontend and API; mixing localhost and 127.0.0.1 changes browser cookie site behavior. If 8001 is already occupied by unrelated/older code, the helper stops with an error and does not terminate it. No account is automatically selected or minted by this helper.

## Changed implementation files

Backend: `app/access/accounts.py`, `app/access/router.py`, `app/api/dependencies.py`, `app/main.py`, `app/models.py`, `app/events/creation_service.py`, `app/participation/projections.py`, `app/sponsorship/service.py`, `migrations/versions/0006_browser_accounts.py`, `tests/test_browser_accounts.py`, `tools/start_live_runtime.ps1`, `tools/verify_browser_account_persistence.py`.

Frontend: `app/App.tsx`, `app/layout.tsx`, `app/provider.tsx`, `features/auth/Signup.tsx`, `features/auth/LiveSignup.tsx`, `features/discovery/Discovery.tsx`, `features/event-creation/BasicSteps.tsx`, `features/organizer/OrganizerEvents.tsx`, `features/participation/ParticipantShell.tsx`, `features/sponsor-dashboard/SponsorShell.tsx`, `features/sponsor-impact/SponsorImpact.tsx`, `features/sponsor-registration/SponsorRegistration.tsx`, `services/contracts.ts`, `services/http-adapter.ts`, `services/participant-contracts.ts`, `shared/GoogleEventMap.tsx`, `tests/http-adapter.test.ts`, `tests/live-navigation.test.tsx`, `vite.config.ts`.

Pre-existing local runtime helper/main bootstrap changes from the previous task remain; they were not removed or used to substitute demo auth for this workflow.

Google API references reviewed: [JavaScript loading](https://developers.google.com/maps/documentation/javascript/load-maps-js-api), [Place Autocomplete (New)](https://developers.google.com/maps/documentation/javascript/place-autocomplete-new). API keys remain in ignored local configuration and were not printed.
