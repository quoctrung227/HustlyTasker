# HustlyTasker

HustlyTasker uses Django 6.1, Django REST Framework, and PostgreSQL 16, with a
React/TypeScript frontend consuming the existing SessionAuthentication API.

## Frontend MVP

HT-AI-P4-03C **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE** integrates the
stateless synthetic Feedback Analyzer into Task Detail. Authorized managers can
select existing Review/Comment feedback and optional focus, then view an honest
fixture result with source citations. It does not interpret feedback with live
AI, persist analysis or apply suggestions. The persistent fixture flag remains
unchanged. Fresh frontend675/675, real isolated Chromium36/36 (including six new
Analyzer enabled/disabled cases), targeted PostgreSQL AI215/215 and quality checks
pass; exits and isolated cleanup are verified. Backend source and all29 development
tables' fingerprints/schema/history are preserved. Manual Owner acceptance
remains pending. See [HANDOVER](documentation/HANDOVER.md) for files, evidence,
limits and safe isolated commands; no follow-on task/deployment is authorized.

HT-AI-P4-02C **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE** adds the scoped
Smart Task Generator fixture preview/edit/confirm integration. This is a fixed synthetic demo,
not a live AI service. Generation never creates Tasks; explicit confirmation
uses the existing atomic backend service. The persistent fixture flag is not
enabled by this task. See [Frontend Guide](documentation/FRONTEND_GUIDE.md) and
[HANDOVER](documentation/HANDOVER.md) for isolated verification and limitations.
P4-02C isolated backend676/676, frontend537/537 and real browser30/30 PASS;
typecheck/lint/build and read-only development preservation pass. No live AI
provider or persistent fixture flag is enabled by this task.

HT-AI-P4-03A **DESIGN AND FIXTURE BACKEND COMPLETE — OWNER REVIEW GATE** adds a
Task-scoped stateless Feedback Analyzer endpoint using existing internal Review
comments and nondeleted Task Comments. Output is a fixed offline fixture with
source citations, never live AI or an automatic Task/Review action. Current
isolated AI215/215 and full PostgreSQL719/719 pass; frontend/browser counts above
belong to P4-02C and were not rerun for this backend-only slice. Source/schema/data
preservation and the permanent predeployment Owner gate are in
[HANDOVER](documentation/HANDOVER.md) and [AGENTS.md](AGENTS.md).

HT-FE-P3-05 **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE** adds Create Profile
& First-Time User Onboarding. An authenticated User can choose **Tạo tổ chức**,
create a name-only Profile, become its active Owner, then create a monthly
Workspace through React. No Django Admin, manual Owner ID or automatic Workspace
creation is required. Active Profile selection continues to use its route URL.
See [HANDOVER](documentation/HANDOVER.md) for current evidence and review gate.
Historical FE05 isolated backend662/662, frontend426/426 and real browser25/25 PASS;
typecheck/lint/build and development preservation checks pass. The Owner's
manual real-website acceptance remains pending; no production readiness claim.
Invitation UI and broader membership onboarding remain separately pending;
`HT-AI-P4-02C` is the separate AI Generator preview/edit/confirm UI task above.

Historical HT-FE-P3-04 is **COMPLETE / OWNER REVIEW GATE**. Its approved MVP includes account
lifecycle and the existing Workspace/Task/Review/Comment/Notification flows.
Invitation UI, Profile Creation and broader membership onboarding remain
outside that earlier task's scope. FE05 separately approves Profile creation;
these other product goals are not removed.

Historical FE04 frontend395/395 and five real isolated browser suites22/22 PASS;
typecheck/lint/build, responsive/axe and local non-mutating startup/connectivity
checks pass. Manual Owner browser, real email delivery, remote CI and production
remain unverified. No backend/schema change or automatic next task is included.

With the configured Django backend running at127.0.0.1:8000:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. First-time Profile creation, authorized Workspace/Task
management, assignment and current-assignee Start are implemented. Existing
Profile metadata edit/delete remains unavailable outside explicit lifecycle APIs.
Task detail shows revision/Review history, capability-based Deliverable Submit
and Review decisions, and authorized existing Comment edit/soft-delete actions;
personal Notifications support feed/count/mark-read. The approved API extension
keeps mutation services authoritative. Registration, password recovery and the
protected current-account email-verification page consume existing APIs without
automatic login or new backend/schema/authentication changes. Historical
HT-API-FE-P3-03A and HT-FE-P3-03 are complete; current FE04 evidence and its final
Owner review gate are in HANDOVER. No AI or next task starts automatically.
Same-origin Vite
proxy preserves Django session cookies and CSRF; no JWT or parallel backend.
See [Frontend Guide](documentation/FRONTEND_GUIDE.md) for Node/dependencies,
routes, configuration, unit/build checks and isolated real browser integration.
See [design system](documentation/design-system/hustlytasker/MASTER.md) before
UI changes and [HANDOVER](documentation/HANDOVER.md) for actual verification.

## Backend tests and CI

From the repository root, use PowerShell 5.1 or 7 with Docker Desktop/Engine
and Compose v2. The launcher supplies Python 3.12 and PostgreSQL 16; it does
not need `.env`, development credentials, or changes to the Owner's venv.

```powershell
# Full PostgreSQL regression suite and required checks
.\scripts\test-backend.ps1

# Targeted modules/classes/test methods use dotted Django labels
.\scripts\test-backend.ps1 -TestLabel apps.accounts.tests,api.tests
```

The first run builds a dependency-only test image from the pinned
`backend/requirements.txt`. Later runs can reuse that image/build cache while
mounting the current source read-only. The Docker build context excludes
private environment files and local backups.

Each invocation creates a new labelled Compose project, internal network,
and PostgreSQL cluster with tmpfs data, no published DB port, and no persistent
data volume. The shared `scripts/test_backend.py` command runs `pip check`,
Django system checks, model/migration drift and graph/history checks, builds
the current migration chain on a uniquely named owned test database, and runs
the selected tests serially. Application password hashing/validation,
SessionAuthentication, permissions, and CSRF remain enabled. Mail is locmem.

Test settings read only the explicit test endpoint/run identity and ignore
inherited `POSTGRES_*`, Django deployment settings, and PostgreSQL connection
environment. They never read `.env` or select the development database.
The core refuses a non-fresh cluster or an existing database rather than
autoclobbering it. Its internal reuse is limited to the database it just
created and marked; CLI settings/runner/keepdb/parallel overrides are rejected.
The approved development schema already includes `accounts.0002` through
HT-DB-P1-09; running tests does not apply migrations to that database.

Normal completion and Ctrl+C attempt cleanup. After a hard interruption or
Docker daemon outage, use the printed run ID from the same checkout:

```powershell
.\scripts\test-backend.ps1 -CleanupRunId '<printed 32-character run ID>'
```

Cleanup verifies exact repository/run/project labels and resource identity
before removing only that run's containers/network. The core additionally
checks PostgreSQL cluster, role, and database marker before dropping its
owned database. Ownership mismatches fail; do not replace this with broad
Docker prune/down-volume commands. The reusable dependency image may remain
cached, but it contains no database state.

With Python 3.12 and the pinned backend requirements installed, the harness
guard unit tests are:

```text
python -m unittest discover -s scripts -p test_test_backend.py
```

`.github/workflows/backend-ci.yml` runs on pull requests and pushes to `main`.
It uses Python 3.12 and a fresh PostgreSQL 16 service on a random job-local
port, installs the pinned requirements, runs the guard tests, then invokes
`python scripts/test_backend.py`. This uses the same core without Docker-in-
Docker. The workflow has read-only repository permission, no deployment step,
no production secrets, and no `continue-on-error` for required gates. Failures
propagate as nonzero exit codes. In GitHub's Actions tab, open **Backend
PostgreSQL checks** and inspect the failed step/log; a local run is not proof
that GitHub accepted or executed the workflow.

Historical HT-TEST-P1-01 checkpoint: **COMPLETE / OWNER REVIEW GATE — LOCAL TEST HARNESS VERIFIED**.
Actual local results: 14/14 guard tests (0.513s), targeted API 10/10 (0.044s),
and full PostgreSQL 286/286 (166.382s), with dependency/system/migration-chain
checks and cleanup PASS. A deliberate nonexistent test label returns exit 1
and still cleans its resources. Run-ID cleanup removes owned interruption
fixtures and refuses a wrong-repository fixture. PowerShell parser, Compose
configuration, actionlint, and diff checks PASS. The original development
Users/Sessions were compared in memory before/after and remain unchanged;
development stays at 32 migrations, 3 Users, 2 Sessions, and zero token rows.
**CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED.**

## Local setup

Use the existing PostgreSQL development service and backend/venv. From
D:\da\HustlyTasker, terminal1:

```powershell
.\scripts\start-backend-dev.ps1 -ValidateOnly
.\scripts\start-backend-dev.ps1 -Check
.\scripts\start-backend-dev.ps1
```

The launcher reads the Git-ignored root .env as literal KEY=value data and
passes it only to the Python child. It validates all nine required variable
names without displaying values, refuses production/remote DB, and never
generates credentials, applies migrations or seeds fixtures. It uses
backend/venv/Scripts/python.exe and serves loopback8000 with --noreload;
restart manually after code changes. No repeated27-variable shell setup.

The Owner's private .env is now configured. Keep its SECRET_KEY stable and
retain the existing PostgreSQL credentials. Do not overwrite it, recreate the
venv/database or change a Docker volume to start development. For a genuinely
new checkout without a private file, copy .env.example to .env once and fill
existing local values privately; provisioning a new database is a separate
explicit setup action. Never put secrets into .env.example or terminal logs.

Terminal2:

```powershell
cd D:\da\HustlyTasker\frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Use .\scripts\test-backend-dev.ps1 for the isolated
launcher guard tests; it does not connect to the database. Full two-terminal
options, literal file grammar and current connectivity evidence are in
[FRONTEND_GUIDE.md](documentation/FRONTEND_GUIDE.md). The automated local smoke
used Django8000 and a temporary Vite5174 to avoid integration-test port5173;
manual Owner browser verification is still pending. Production, real email
delivery and remote CI remain unverified.

The public API liveness endpoint is
`http://127.0.0.1:8000/api/health/`. A successful `GET` returns
`{"status":"ok"}` without checking PostgreSQL. The legacy `/api/test/`
endpoint has been removed and returns `404 Not Found`.

## Environment policy

- `.env` is ignored by Git; `.env.example` contains names and safe development
  values only.
- `DJANGO_ENVIRONMENT` accepts `development` or `production`. Production
  rejects `DJANGO_DEBUG=true`, wildcard hosts, and development mail backends.
- `DRF_NUM_PROXIES=0` makes authentication throttles ignore client-supplied
  proxy headers. Set it to the exact trusted reverse-proxy count only after the
  deployment proxy chain is fixed and strips untrusted forwarding headers.
- Production HTTPS, cookie, HSTS, allowed-host, CSRF-origin, SMTP, and database
  values must be reviewed for the deployment environment. Do not enable HSTS
  include-subdomains or preload before confirming the policy for every domain.
- Production SMTP requires explicit host, port, TLS/SSL choices, and matching
  username/password values when authentication is used.
- `SECURE_PROXY_SSL_HEADER` is intentionally unset until a trusted reverse
  proxy boundary is designed; configure it only in the deployment task.
- There is no cross-origin frontend contract yet, so CORS is intentionally not
  enabled in this phase.

Before continuing development, read root `AGENTS.md` and the current
`documentation/HANDOVER.md` checkpoint. See `documentation/` for the audit,
roadmap, schema, API contract, and architecture decisions.
