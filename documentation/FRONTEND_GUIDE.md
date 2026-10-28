# HustlyTasker frontend guide

Current HT-FE-P3-04: **COMPLETE / OWNER REVIEW GATE**. MVP audit, account lifecycle
consumers, cohesive isolated UI acceptance and local startup are verified within
the approved scope. See FRONTEND_MVP_ACCEPTANCE.md and
HANDOVER.md for current scope and evidence. The Owner supplied local environment
configuration; launcher validation, Django check, read-only DB connection and
non-mutating direct/proxy smoke now pass. Earlier
completed FE03/API03A checkpoints below remain historical verification.

HT-FE-P3-01 foundation, FE02 Workspace/Task and FE03 collaboration UI, including
the Owner-approved HT-API-FE-P3-03A capability extension. One React SPA consumes
the existing Django/DRF APIs. Current verification/status is in HANDOVER.md.
Source now includes Deliverable Submit, Review Approve/Request Changes, existing
Comment author actions and personal Notifications. HT-API-FE-P3-03A is COMPLETE;
HT-FE-P3-03 is IMPLEMENTATION COMPLETE. Final regression verification passes;
stop at OWNER REVIEW GATE without starting another task. The API
extension adds five read-only flags; models, migrations, authentication, RBAC
and mutation workflow services remain unchanged. Project/AI remain outside scope.

## Stack and prerequisites

Node20.17+ and npm10+; verified locally on20.17.0/10.8.2 without replacing the
Owner's Node or Python installation. Use npm and the checked-in package-lock.
React19,strict TypeScript6,Vite6.4,ReactRouter7,Tailwind4,TanStackQuery5.
Vitest/TestingLibrary cover mocked units; Playwright/axe cover real isolated
browser integration. Biome is the lint equivalent: its maintained runtime works
on the installed Node; the initial older ESLint toolchain was removed before
completion. No Zod is needed for this small surface: transport read contracts
are validated explicitly at runtime in services/api/queries.ts.

Vite6.4 was selected for installed Node compatibility and its security-supported
branch, instead of bypassing newer tools' Node engine checks. See official
[Vite support policy](https://main.vite.dev/releases) and
[Node requirement change](https://v7.vite.dev/guide/migration).
Routes use ReactRouter's [declarative SPA mode](https://reactrouter.com/start/declarative/installation);
Tailwind uses its [Vite plugin](https://tailwindcss.com/docs/installation/using-vite).
Versions resolved by package-lock are authoritative. Future engine upgrades
belong to a deliberate dependency task, not an implicit backend upgrade.

## Local development

HT-FE-P3-04 adds a repeatable Windows launcher; Django settings still intentionally
read process environment, not a .env file automatically. Running bare
`python manage.py runserver` in a fresh PowerShell therefore reports missing
variables. Load the selected private file through the launcher instead.

Configure once, from the repository root, only if .env does not already exist:

```powershell
Copy-Item .env.example .env
```

Privately edit .env: supply a stable DJANGO_SECRET_KEY and the EXISTING
POSTGRES_PASSWORD, retaining the known development database/user/loopback values.
If either existing value is unknown, stop and recover it through the Owner's
normal private configuration process. Do not extract passwords from Docker
inspect, reset credentials, recreate venv/DB, run rollout helpers or migrate just
to start the website. Never repeat Copy-Item over an existing private .env.

The launcher accepts literal single-line KEY=value matching the sample. Only
whole-line # comments and blank lines are skipped. Values do not interpolate;
#, $, quotes and backticks inside values are literal. Do not add surrounding
quotes as shell syntax, export prefixes, inline comments or multiline values.
The file must be regular, repository-local and Git-ignored. All nine mandatory
Django/PostgreSQL names are validated together without displaying their values;
optional settings retain Django defaults. No need to enter27 variables each run.

Terminal1, from D:\da\HustlyTasker:

```powershell
.\scripts\start-backend-dev.ps1 -ValidateOnly
.\scripts\start-backend-dev.ps1 -Check
.\scripts\start-backend-dev.ps1
```

ValidateOnly checks file/required names/development endpoint, not Django or DB.
Check runs the existing backend/venv/Scripts/python.exe manage.py check; it does
not prove DB connectivity. Default starts Django at http://127.0.0.1:8000 with
--noreload; Ctrl+C stops it and code changes require a manual restart. Environment
is passed only to the child; parent PowerShell and security policy are not
modified. There are no automatic migrations, fixtures or credential generation.
Optional -EnvFile selects another ignored repository-local file; -Port changes
only the loopback HTTP listener. If changing port, match DJANGO_API_TARGET below.

Terminal2:

```powershell
cd D:\da\HustlyTasker\frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Non-mutating connectivity checks from a third terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/
Invoke-RestMethod http://127.0.0.1:5173/api/health/
```

Both should return status=ok; liveness does not prove DB readiness. Do not print
CSRF bootstrap response bodies or cookies into logs. Use browser login only with
the Owner's own authorized account; automated mutation tests use disposable
PostgreSQL through the integration runner, never persistent development.
At FE04 preflight no private .env existed. The Owner subsequently supplied the
configuration; the two configured fields were preserved exactly in the ignored
root .env and blanked in the tracked example. No credential was regenerated.
Current automated local verification: ValidateOnly0, existing-venv Django check0,
read-only PostgreSQL16.14/hustlytasker_db with35 migrations/no pending migrations,
3 Users/2 Sessions/0 business rows. Django8000 and temporary Vite5174 returned
health200 direct/proxy, CSRF bootstrap200 without token logging, anonymous me403
direct/proxy, scoped Profile403 and public registration OPTIONS200. No persistent
login or business mutation was performed. The smoke helper returned0; intentional
server termination returned native-1, not a claimed graceful server exit0.
Default developer frontend port remains5173. Manual Owner browser verification,
production, real email delivery and remote CI remain unverified.

Use the frontend origin consistently rather than switching localhost/127.0.0.1
while testing cookies. Optional Vite-only configuration, inside frontend/:

```powershell
Copy-Item .env.example .env.local
```

`DJANGO_API_TARGET=http://127.0.0.1:8000` is the only frontend setting. It is
read by Vite on the server and must be an HTTP loopback origin without path,
credentials, query or fragment. It is NOT a VITE_* public bundle variable.
There are no browser database credentials, authentication keys or LLM keys.
Do not add private credentials to frontend environment variables.

Development proxy sends `/api/` to Django and preserves Host (`changeOrigin:
false`), so Origin/Host and browser cookies stay same-origin without CORS,
wildcard credentials, trusted-origin expansion or CSRF settings changes.
Vite `server.cors=false` lets same-origin OPTIONS reach DRF instead of its own
CORS middleware returning a synthetic204. Django settings remain unchanged.
Static production deployment is not part of this task. A future deployment
must serve SPA files with navigation fallback and route `/api/` to Django
before that fallback, retaining secure cookie/HTTPS/proxy configuration.
The Vite dev/preview server is not a production deployment.

## Source map and routes

| Area | Responsibility |
|---|---|
| src/app | One route tree, protected routes, fatal UI fallback |
| src/features/auth | Single identity state machine, revalidation, cache cleanup |
| src/services/api | Fixed same-origin client, CSRF, safe errors, typed read contracts |
| src/layouts | Responsive sidebar/topbar, navigation, own account/logout |
| src/components | Shared semantic controls, native dialog, states, pagination |
| src/pages | Login/register/recovery/current-account verification, real-data overview, tenant and scoped Task pages |
| src/features/workspaces | Capability hints, Workspace forms/lifecycle and sanitized roster |
| src/features/tasks | Task metadata/child forms, deadline conversion and assignment |
| src/features/collaboration | Deliverable/Review reads and mutations, scoped Comment thread/forms |
| src/features/notifications | Personal feed, preview/count and confirmed mark-read |
| src/styles.css | Tailwind entry, shared semantic design tokens and responsive rules |
| e2e | Real HTTP/browser tests against isolated Django/PostgreSQL |

Public routes: `/login`, `/register`, `/forgot-password`, `/reset-password`,
`/403`, `/404`, fallback404. Protected routes include `/account`,
`/dashboard`, `/notifications`, `/profiles`, `/profiles/:profileId`,
`/profiles/:profileId/workspaces`,
`/profiles/:profileId/workspaces/:workspaceId`, and that Workspace's
`/tasks` and `/tasks/:taskId`. `/` redirects to dashboard
through the same auth guard. Return-to paths are local; external redirect
destinations are rejected. Only implemented navigation is enabled.

## Authentication, privacy and access

The shared client always sends credentials same-origin and no-store. It gets
a masked token from GET`/api/auth/csrf/`, holds it only in memory and sends
X-CSRFToken on unsafe requests. POSTlogin uses email/password; login success
invalidates the old token because Django rotates it. POSTlogout fetches fresh
CSRF when necessary. Mutations are never silently replayed after failure.
Browser-managed HttpOnly session cookies are not read by JavaScript, and no
password/session/token/private Query cache is persisted to localStorage or
sessionStorage. UI errors use controlled local text, not raw HTML/stack traces.

GET`/api/auth/me/` resolves initial identity before any private page/query mounts.
Focus, return to a visible document and a60-second visible-page interval
revalidate identity; private UI is hidden during that check. Expiry/uncertain
network identity cancels and clears private queries. Logout clears immediately
and only claims server-confirmed success when its request succeeds; failure
shows an unavailable state. Identity generation/abort guards reject stale
responses from previous sessions. Query caching is in-memory,staleTime0,gcTime0,
no retry, no persisted state; central auth handles focus revalidation.

DRF SessionAuthentication can return403 for anonymous users. A tenant403 probes
`/me` quietly: valid same-user session retains a stable permission error rather
than remounting/refetching forever; invalid/uncertain identity clears private
state. Tenant-safe404 is kept generic and does not reveal object existence.
Current backend permission/membership checks remain authoritative. Knowing an
ID or switching the UI context grants no access.

### Account lifecycle — HT-FE-P3-04

Registration sends email/username/password/password_confirm with optional names
to the existing POST /api/auth/register/. It neither logs in nor creates Profile
membership. Login links expose registration and recovery; the shared authenticated
navigation exposes /account for the current User only.

/forgot-password sends POST /api/auth/password-reset/request/ with email. The
neutral202 message explicitly does not confirm that an account exists or that
email delivery succeeded. /reset-password accepts a manually pasted masked token
and matching new passwords, sends the existing confirm contract, clears inputs/
stale CSRF after204 and revalidates identity to clear invalidated session data.
It does not auto-login; the user must sign in explicitly with the new password.

/account displays only /me identity and email_verified. Verification request
sends an empty object for the current session; confirmation sends only token.
A request202 never marks the email verified. Successful confirmation refreshes
server identity; legacy unverified Users keep existing permissions. Neither
verification nor recovery accepts an Invitation or grants tenant membership.

All forms reuse shared teal/neutral components, visible labels, focused linked
error summaries, static safe field errors, pending/duplicate guards and abort on
unmount. Password-manager autofill/paste is allowed. Tokens are password-type
inputs kept only in mounted form memory and POST bodies, not URLs/query keys,
browser storage or logs. No fake email link contract or real provider is added.
The current console backend intentionally cannot deliver security credentials;
real email requires a separately configured safe provider. Browser success tests
use only the isolated locmem adapter/mailbox, never production email.

Owner retains the MVP scope above. Invitation UI, Profile Creation and membership
candidate/onboarding management are OUT OF CURRENT TASK SCOPE / PENDING OWNER
REVIEW; their target product requirements remain. See FRONTEND_MVP_ACCEPTANCE.md
for exact API gaps and AI readiness proposals. No new backend/schema/RBAC rule.

Current frontend unit/contract395/395 PASS (14files,15.94s), typecheck0,
Biome52files0 and build6.65s0 (JS479.99kB/gzip139.09,CSS39.06kB/gzip11.00).
Initial typecheck found two unsupported ByRoleOptions in App tests; those test
selectors were corrected and the full checks rerun. All current real isolated
Django/PostgreSQL/Chrome suites pass:

| Suite | Result | Run ID |
|---|---|---|
| Cohesive business UI acceptance | 1/1 PASS43.6s | 6a1ec11fb62741aabcc330571015c828 |
| Account lifecycle/email adapter | 1/1 PASS22.4s | 77a73580faf34927b8970208eca6f658 |
| Collaboration | 7/7 PASS1.2m | 8a940dabeedc41ceaf63b8669f461b28 |
| Workspace/Task/Start | 7/7 PASS1.0m | e1470330e0904f9d92e5254324892455 |
| Auth/CSRF/tenant foundation | 6/6 PASS36.3s | 5d6f2f14dbbf4829ad54c0d054584d81 |

All22 browser tests have actual native launcher/Playwright/backend exits0 and
owned DB/container/network cleanup evidence. The cohesive case creates a Task
and Subtask, then assigns/starts/submits/reviews the parent through React;
the child remains PENDING, proving no status cascade. Comment CRUD, Notification
read and same-browser User switching are also performed through React.
Account registration/verification/reset use React plus the isolated delivered-mail
adapter; fixture setup and negative direct API probes are labeled separately.
No real email-provider success is inferred.

Responsive375/768/1440/812x375 landscape, native dialog focus/keyboard, overflow
and axe WCAG2/2.1AA checks pass with0 violations. Empty registration375, reset812
landscape and completed Task1440 screenshots were visually inspected. No manual
interactive Owner browser claim follows. Backend485/485 remains historical and
was not rerun because all144 protected backend/config/harness/dependency assets
are unchanged; no schema/migration or production action. FE04 is COMPLETE within
the retained MVP scope. Stop at Owner review without starting AI or onboarding.

Run each suite separately against fresh owned PostgreSQL fixtures:

```powershell
.\scripts\test-frontend-integration.ps1 -Suite acceptance
.\scripts\test-frontend-integration.ps1 -Suite account-security
.\scripts\test-frontend-integration.ps1 -Suite collaboration
.\scripts\test-frontend-integration.ps1 -Suite work-management
.\scripts\test-frontend-integration.ps1 -Suite foundation
```

New acceptance/account screenshots and paired evidence are Git-ignored under
.local_backups/HT-FE-P3-04/. Browser actions versus API fixture/negative probes,
final responsive/axe results, exit codes and cleanup are recorded in HANDOVER.

## Profile/Workspace contracts and states

The foundation uses five read contracts: current User envelope, paginated
Profile list, Profile detail, nested paginated Workspace list and Workspace
detail. Lists use count/next/previous/results; request page numbers locally
with server-default20/page, never follow arbitrary absolute next links.
Workspace.profile_id must match nested scope; nullable legacy period and
description are supported. ACTIVE/ARCHIVED are visible read states. Dashboard
counts come from the actual accessible Profile response; no fake analytics.
FE02 adds authorized Workspace/Task writes as detailed below. FE03 and API03A
add the bounded collaboration and personal Notification surfaces described
below. Profile writes, membership mutation and AI UI remain outside scope.
Loading skeletons, useful empty states, generic403/404, validation,
CSRF,409,429,5xx and network failures have explicit feedback/retry behavior.

## Design reference

Read [the shared master](design-system/hustlytasker/MASTER.md) and current
tokens before UI changes. ui-ux-pro-max was fully read and its CLI used for
design-system/focused UX/React/color/typography searches; unsuitable landing,
motion and native-only recommendations were not applied. Deep teal/warm
neutral/lime, self-hosted Vietnamese PlusJakartaSans, consistent spacing,
component states, native dialog and responsive rules are shared across pages.
Primary semantic control/keyboard/focus/contrast/reduced-motion checks are
applied and recorded in the verification checkpoint, not inferred from styling.

## Checks and real isolated integration

```powershell
cd D:\da\HustlyTasker\frontend
npm run typecheck
npm run lint
npm test
npm run build
```

`npm test` is explicitly MOCK FRONTEND/API CONTRACT testing; it does not prove
a real Django login. The actual HTTP/browser suite is run from repository root:

```powershell
.\scripts\test-frontend-integration.ps1
```

Requires Docker, existing dependency image hustlytasker-backend-tests:local
(built by the shared backend test launcher) and installed Chrome/Edge or a
Playwright-supported Chromium installation. The runner selects an installed
Chrome/Edge without modifying it. It creates a fresh unpublished PostgreSQL16
tmpfs service/internal database network, gates cluster+role+owned UUID database, applies
the existing migration chain only there and creates synthetic fixtures. Django
HTTP is published only on127.0.0.1:8001 via a second owned HTTP bridge attached
only to the backend; PostgreSQL stays internal and unpublished. This is needed
for host port publication on the verified Docker Desktop runtime. Neither
network is the development network. Vite runs on5173 with that proxy target.
Generated fixture credentials stay in process memory/env, never docs/logs.

Real tests exercise CSRF rejection/rotation, login/logout/me, private route
boundaries, nested tenant denial, current membership, session expiry and
read-only pages, plus responsive/axe/keyboard/native-dialog checks. Screenshots
of synthetic fixtures are retained ignored in .local_backups/HT-FE-P3-01/.
Cleanup gates exact UUID/repository/image/network/mount ownership and verifies
backend exit and owned DB removal before removing only test resources.
No persistent development credentials/network or Owner accounts are selected.
After hard interruption inspect exact labelled run resources; never use broad
Docker prune/down-volume or substitute development as a test target.

Current PASS/failure counts and visual inspection status belong in HANDOVER.md.
No manual authenticated E2E on persistent development, production deployment,
real email delivery or remote CI verification is implied by local isolated tests.

## Workspace and Task management — HT-FE-P3-02

Protected routes add `/profiles/:profileId/workspaces/:workspaceId/tasks` and
the nested `/:taskId` detail. Workspace list creates an authorized monthly
Workspace; detail edits metadata, confirms archive/restore and shows the
manager-only sanitized member roster. Period is chosen as month and sent as
YYYY-MM-01 at creation, not edited later. No Profile creation or membership
mutation UI is included.

Task list renders real title/description/status/priority/deadline, assignment
membership code and update time. Filters/sort/page go to the server. Local
"Tìm trong trang" searches only current-page titles. Root-only is a server
filter; detail's direct-child link selects parent_id. Filter dates use UTC day
bounds. No global search or aggregate Task dashboard is invented.

Detail requests one Task, paginated direct children and at most3 ancestors.
Breadcrumb shows root0/child1–3; a fourth child level is unavailable. Create
child fixes parent_id from current context. Each Task keeps its own workflow;
there is no completion/priority/deadline cascade or arbitrary status PATCH.
Metadata edit sends changed fields only; assignment is a separate action.
Empty deadline sends null; browser-local datetime is validated and converted
to UTC. Overdue is an indicator, not a new state. Collaboration UI is tracked
in the separately approved HT-FE-P3-03 section below.

Workspace/Task metadata form hints come from DRF OPTIONS.actions.POST, never
static Allow. Object-specific Start/Submit/Review/Comment actions instead use
the corresponding read-only flags described below. Hints default closed and
discard stale data after failed refetch. Backend always
revalidates writes. Queries/invalidation include Profile/Workspace. Forms keep
drafts on recoverable errors, prevent duplicate submit and abort UI requests
on unmount/scope switch. HTTP abort cannot undo a committed transaction;
unsafe requests never automatically replay.

### Identity/Start/assignment extension — HT-API-FE-P3-02A

The Owner approved resolving the two original FE02 API gaps. Task responses now
include a required boolean can_start, computed by Django from the authenticated
request, live tenant capability, current active User assignment and ASSIGNED
state. The client never compares global User.id with a ProfileMembership ID.
Start appears only with that hint in an active matching Workspace. It uses the
existing POST Start service with CSRF, pending/duplicate guards and safe errors;
no optimistic transition or automatic retry. Success invalidates the current
Task/list/child scope;403/404/409 refresh current scope and suppress stale action.
Backend revalidates every mutation regardless of the displayed hint.

Manager-only roster adds display_label and is_assignable without a new endpoint.
The selector uses the server eligibility flag and excludes the current assignee,
renders friendly labels, and submits the original ProfileMembership ID. Duplicate
labels receive a short membership suffix for disambiguation. Full-name labels
fall back to a safe membership code, never username or email. No global User ID,
phone or credential is added. Workspace member list uses the same labels with
existing role/activity information; the selector omits ineligible rows. Names
do not confer authority.

Type guards reject missing/invalid hint/label fields. Query/cache keys stay tenant
scoped; failed requests keep safe feedback, not a success status. Current results
and FE02 completion reconciliation are in HANDOVER.md. No schema, new role,
workflow change or dependency upgrade. Existing legacy CANCELLED is a status
display only; no cancellation action is introduced. Task dashboard analytics
are still unavailable and are not a blocker or an invented aggregate.

Both gaps are resolved and HT-FE-P3-02 is IMPLEMENTATION COMPLETE through the
approved HT-API-FE-P3-02A extension. Historical backend448/frontend224/browser7+6,
type/lint/build and responsive/axe checks passed; exact runs are in HANDOVER.
That historical extension stopped at Owner review before FE03 was authorized.
UI work reused ui-ux-pro-max's full
instructions and the existing master; the actual focused React async-error
search informed safe feedback/pending behavior. No theme/component redesign.

Run separate fresh isolated suites to retain existing login throttles:

```powershell
.\scripts\test-frontend-integration.ps1 -Suite foundation
.\scripts\test-frontend-integration.ps1 -Suite work-management
```

Default remains foundation. Work screenshots live ignored under
`.local_backups/HT-FE-P3-02/screenshots/<run-id>/`. Foundation retains FE01 path.
All mutation flows use disposable synthetic fixtures, never development users.
If a personal Django terminal lacks DJANGO_ENVIRONMENT/SECRET_KEY/DEBUG/
ALLOWED_HOSTS/POSTGRES_DB, follow README's private environment setup. This is a
separate development setup issue; do not regenerate credentials, recreate venv,
relax backend security or reset/migrate development to run frontend tests.

## Collaboration — HT-FE-P3-03

Task/Subtask detail reuses existing overview, assignment, Start and hierarchy.
It now includes `#deliverables` and `#comments` sections, with per-Task paginated
revision cards, nested Review status/feedback and comment thread/composer.
Review detail is shown from the existing Deliverable row; no fake detail route.
Safe absolute HTTP(S) product URLs open with noopener/noreferrer/no-referrer;
other supplied content remains escaped text, never executable HTML or links.
No storage/upload, rich text, mention or attachment system is added.

Comment text validates4,000 Unicode code points, rejects NUL/unpaired surrogates,
shows counter/inline errors/focused summary and preserves drafts on recoverable
failures. POST OPTIONS verifies current commenter role; writes still require CSRF.
Each Comment response now supplies required `can_edit`/`can_delete` booleans
computed by the backend for the current request. These support existing comments
after reload, pagination or navigation; temporary POST-response ownership proof
has been removed. The UI never maps global User IDs to membership IDs or infers
authorship from a display name. Current authorized authors may edit; an authorized
author or manager may delete. Managers cannot edit another author's text and
tombstones expose neither action. Delete requires confirmation. Confirmed edit/delete
cancels older Comment GETs and updates/redacts all matching cached copies before
refetch; deleted retained content is never rendered. No optimistic success.

`/notifications` is a protected personal feed, with all/read/unread filter,
server pagination, explicit refresh and mark-read. Topbar bell opens a native
modal preview of at most5 rows from the first server page. Badge count is the
server's own readable-target unread count; contextual atomic status text avoids
announcing a bare number. Feed is User-keyed and spans the User's currently
authorized Profiles, not a fabricated current-Workspace aggregate. Header/page
queries refresh on mount and mutations, with the existing auth focus/visibility
revalidation; no new polling/WebSocket/worker infrastructure.

Mark-read changes only after server confirmation. On denied target, cached rows
for that Workspace are redacted and feed/count revalidated. Failed refresh hides
stale private rows/count. Navigation is a SPA Task path derived from validated
Profile/Workspace/Task UUIDs; raw server target_url is never followed. Opening
the target rechecks current scoped read access. No read-all or mark-unread API
is invented. Logout/expiry uses the existing AuthProvider cancel+cache clear.

All collaboration keys include User/Profile/Workspace/Task; notification keys
include authenticated User. Unsafe requests reuse the single memory-CSRF client
with no automatic replay. Existing tenant403 quiet identity probe stays finite.

### Collaboration mutation extension — HT-API-FE-P3-03A

Verified contracts and the historical gap matrix are in
[FE03_CONTRACT_MATRIX.md](FE03_CONTRACT_MATRIX.md). The separately approved
extension resolves all three gaps in source without a new endpoint:

- Task `can_submit`: current assigned active Editor in an active authorized
  scope, Task WORKING and no unresolved PENDING/SUBMITTED Deliverable.
- Deliverable `can_approve`/`can_request_changes`: current reviewer/manager
  authority, Task REVIEW, this submission SUBMITTED and latest by created_at/id,
  non-self uploader and no existing Review row.
- Comment `can_edit`/`can_delete`: current commenter authority, nondeleted row,
  author for edit and author-or-manager for delete.

Every flag is a required runtime-validated boolean bound to authenticated request
and verified tenant context. Missing or malformed fields fail closed. Hints do
not grant durable authority: the existing locked mutation service checks live
membership, assignment and state again at POST/PATCH/DELETE time. OPTIONS alone
is not used as proof for Submit, Review decisions or existing Comment authorship.

`CollaborationActions` reuses native Dialog and the established work-form/error
patterns. Submit sends `{file_url}` as text or URL (maximum500 Unicode code
points), not a file upload. Approve sends optional `{comment}`; Request Changes
requires nonblank `{comment}`. Forms reject NUL/unpaired Unicode, retain drafts
and focused linked errors on failure, prevent duplicate submission, abort on
unmount and disable dismissal while pending. No success or Task status is shown
optimistically. Safe400/403/404/409 responses remain visible; unsafe requests do
not automatically retry. A stale hint never overrides the server's decision.

Confirmed success invalidates the current Profile/Workspace Task scope, the
User/Profile/Workspace/Task collaboration scope and that User's Notification
prefix. Failed authorization refreshes the scope without displaying stale
private content. Comment deletion still cancels older reads and redacts cached
pages before refetch. Logout/expiry retains the single AuthProvider's cache clear.

No Deliverable update/delete/upload endpoint is invented; new submissions after
Request Changes use the existing revision-creation workflow. No self-review,
revision, RBAC, AuditLog or Notification transaction policy changes. There is no
schema/migration change. Project remains PENDING OWNER DECISION.

Historical API03A resume checks: frontend356/356 (12files,41.49s), strict typecheck exit0,
Biome46files exit0 and productionbuild6.69s exit0 (JS465.75kB/gzip135.48kB,
CSS39.06kB/gzip11.00kB). These local unit/contract/build checks are separate from
the current real PostgreSQL/Django/Chrome collaboration7/7 PASS (1.3m,
runff6abc6459954d6d83f47ec94c426a62). Native launcher, Playwright and backend
exits0 and owned database/container/network cleanup are evidenced. Actual React
Submit/Request Changes/resubmit/Approve and a separate fresh Submit/Approve
flow pass, as do existing Comment edit after reload/navigation, moderation,
Notification actions, revocation and expiry. Full isolated PostgreSQL485/485
PASS (231.054s, run3b2abcd913324644b6240bfc49ca1c18), work-management7/7
PASS (1.1m, run3074e74939f84f3b8039665dab7196ba) and foundation Auth/CSRF/tenant6/6
PASS (43s, runc125145b536b480badeccfba582f4c90) complete the regressions. Actual
native/Python/Playwright/backend exit0 and owned cleanup are verified for their
respective runners. Final E2E-spec typecheck/lint also return0. All three gaps
are closed and FE03 is IMPLEMENTATION COMPLETE; HANDOVER.md is the authoritative
final evidence and OWNER REVIEW GATE. No next task is started automatically.

UI UX Pro Max's full instructions and the unchanged master were read. Actual
focused `error summary validation --domain ux` and `async form error --stack react`
searches informed linked focused errors, inline messages, caught asynchronous
failures and pending feedback. Recommendations did not introduce a new theme or
replace existing mutation/state handling with a framework-wide refactor.

```powershell
.\scripts\test-frontend-integration.ps1 -Suite collaboration
```

Run foundation/work-management/collaboration separately on fresh owned isolated
PostgreSQL instances; each preserves existing login throttles. Collaboration
tests distinguish fixture/API setup from mutations actually performed through
React. The earlier FE03 API-driven Submit/Review run is historical and does not
prove the newly added mutation UI. The current API03A run exercises actual Submit,
Request Changes and Approve dialogs, with axe WCAG2/2.1 AA0 violations, native
keyboard/focus checks and no overflow at375/768/1440 and812x375 landscape.
24 screenshots are retained; Submit375, RequestChanges812 landscape and
Approve1440 were visually inspected. Screenshots remain ignored under
`.local_backups/HT-FE-P3-03/`; current API03A logs/exit evidence are under
`.local_backups/HT-API-FE-P3-03A/`. Exact final
counts, exits, cleanup and preservation evidence are in HANDOVER.md.
