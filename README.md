# HustlyTasker

HustlyTasker uses Django 6.1, Django REST Framework, and PostgreSQL 16, with a
React/TypeScript frontend consuming the existing SessionAuthentication API.

## Frontend foundation

With the configured Django backend running at127.0.0.1:8000:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Profile/Workspace UI is read-only. Same-origin Vite
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

Prerequisites: Docker Desktop and Python 3.12 with the Windows Python Launcher
(`py`). Run the commands below from the repository root.

1. Create a private environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

   Fill `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` in `.env`. Generate two
   different URL-safe values without storing them in source control:

   ```powershell
   py -3.12 -c "import secrets; print(secrets.token_urlsafe(64))"
   py -3.12 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Paste the first output as `DJANGO_SECRET_KEY` and the second as
   `POSTGRES_PASSWORD`. Keep `.env` as plain, unquoted `KEY=value` lines. Do
   not add inline comments or whitespace to values; this keeps PowerShell and
   Docker Compose parsing identical.

   If an existing `postgres_data` Docker volume is in use, keep its current
   database name, user, and password. Changing Compose variables does not
   change credentials already initialized inside that volume.

2. Load `.env` into the current PowerShell process before invoking either
   Docker Compose or Django. This also replaces stale variables inherited by
   the shell with the values from the selected file.

   ```powershell
   Get-Content .env | ForEach-Object {
       $line = $_
       if (-not [string]::IsNullOrWhiteSpace($line) -and -not $line.TrimStart().StartsWith('#')) {
           if ($line -notmatch '^([A-Za-z_][A-Za-z0-9_]*)=(\S*)$') {
               throw 'Use plain, unquoted KEY=value lines without whitespace.'
           }
           $value = $matches[2]
           if ($value.Contains('"') -or $value.Contains("'") -or $value.Contains('#')) {
               throw 'Do not quote values or add inline comments in .env.'
           }
           [Environment]::SetEnvironmentVariable($matches[1], $value, 'Process')
       }
   }
   ```

3. Validate and start PostgreSQL:

   ```powershell
   docker compose --env-file .env -f docker/docker-compose.yml config --quiet
   docker compose --env-file .env -f docker/docker-compose.yml up -d postgres
   ```

4. Create and activate a Python 3.12 virtual environment, then install the
   pinned dependencies:

   ```powershell
   py -3.12 -m venv backend/venv
   .\backend\venv\Scripts\Activate.ps1
   python -m pip install -r backend/requirements.txt
   ```

5. Check the backend and start the development server:

   ```powershell
   Set-Location backend
   python manage.py check
   python manage.py migrate
   python manage.py runserver
   ```

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
