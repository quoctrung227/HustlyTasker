# HustlyTasker frontend foundation

HT-FE-P3-01. React SPA consuming the existing Django/DRF API; no second backend.
Status/verification evidence is maintained in HANDOVER.md. Project/AI and
Task/Review screens are outside this foundation.

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

Start the existing configured Django backend at127.0.0.1:8000 using the backend
setup in README.md and the Owner's existing private environment. Do not reset
credentials, recreate venv, rerun controlled rollout helpers or migrate an
existing database merely to run the frontend. Then, in a second terminal:

```powershell
cd D:\da\HustlyTasker\frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Use that browser origin consistently rather than
switching localhost/127.0.0.1 while testing cookies. Optional configuration:

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
| src/pages | Login, real-data overview and read-only tenant pages |
| src/styles.css | Tailwind entry, shared semantic design tokens and responsive rules |
| e2e | Real HTTP/browser tests against isolated Django/PostgreSQL |

Public routes: `/login`, `/403`, `/404`, fallback404. Protected routes:
`/dashboard`, `/profiles`, `/profiles/:profileId`,
`/profiles/:profileId/workspaces`,
`/profiles/:profileId/workspaces/:workspaceId`. `/` redirects to dashboard
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

## Profile/Workspace contracts and states

Use only the actual five read contracts: current User envelope, paginated
Profile list, Profile detail, nested paginated Workspace list and Workspace
detail. Lists use count/next/previous/results; request page numbers locally
with server-default20/page, never follow arbitrary absolute next links.
Workspace.profile_id must match nested scope; nullable legacy period and
description are supported. ACTIVE/ARCHIVED are visible read states. Dashboard
counts come from the actual accessible Profile response; no fake analytics.
No Profile/Workspace write, membership, Task, Review, Notification or AI UI is
enabled. Loading skeletons, useful empty states, generic403/404, validation,
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
