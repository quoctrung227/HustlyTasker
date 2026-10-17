# HustlyTasker

HustlyTasker uses Django 6.1, Django REST Framework, and PostgreSQL 16. The
frontend is planned but is not implemented yet.

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
