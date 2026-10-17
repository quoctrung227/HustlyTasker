# PROJECT PROGRESS

## Current Snapshot - 2026-10-17

This snapshot is the current source of truth. Older blocks below are retained as development history and may describe earlier phases.

### Current Phase

`PHASE 2.2 - API Architecture`

### Audit Result

- Git branch `main` and the local `origin/main` ref both point to `6dafc81`.
  The worktree is intentionally dirty with the uncommitted OPS/SEC/AUTH/API
  and documentation deliverables inventoried in `HANDOVER.md`; all are being
  preserved.
- Read-only PostgreSQL development inventory, reconfirmed on 2026-10-17, found
  0 business rows and 3 User
  rows. It contains the initial migrations; the new Workspace `0002` has not
  been applied there and the named volume is preserved.
- `makemigrations --check --dry-run` reports no model/migration drift relative
  to the new migration in source.
- Authentication foundation, the deny-by-default API policy, and the
  `/api/health/` liveness endpoint are implemented and verified on PostgreSQL;
  Workspace/RBAC and business APIs are not implemented.
- `HT-DATA-P2-01` architecture/design and all 11 decision groups were approved
  by the owner on 2026-10-16. `PROFILE/WORKSPACE SCHEMA FOUNDATION` is now
  complete in source and verified on disposable PostgreSQL test databases. It
  remains unchanged; development `0002` is still unapplied by design.
- `HT-RBAC-DESIGN-P0-01` has completed its design deliverables and is
  `DESIGN READY — PENDING OWNER APPROVAL`. The capability matrix,
  tenant-scoped query/service boundary, invitation contract, proposed API,
  isolation tests, and dependency order are recorded in `RBAC_DESIGN.md`.
  No API, model, migration, permission code, or database row changed.
- Root `AGENTS.md` now defines mandatory documentation/checkpoint/handover
  rules. `documentation/HANDOVER.md` is the continuation entry point.
- Frontend and production deployment/CI are not started.
- `reference/original_document/` describes the legacy Next.js/Prisma system and historical Spring migration research; it is not the active Django architecture.

Detailed status and evidence:

- `documentation/REQUIREMENT_STATUS.md`
- `documentation/PROJECT_ROADMAP.md`

### Completed In This Session

`HT-OPS-P0-01 - Backend dependency synchronization`

- Normalized `backend/requirements.txt` from malformed UTF-16/double-BOM content to UTF-8.
- Updated Django `6.1` to security patch `6.1.2`.
- Updated Django REST Framework `3.15.0` to `3.18.3`, which supports Django 6.1.
- Kept all other dependency pins unchanged.

Verification in an isolated Python 3.12 container:

- Fresh dependency install: PASS.
- `pip check`: PASS.
- Django/DRF version assertions: PASS.
- `manage.py check`: PASS.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- `manage.py migrate --check`: PASS, no unapplied migrations.
- Legacy `/api/test/` smoke test: PASS at the time of HT-OPS-P0-01; this route is later replaced by `/api/health/` in HT-API-P0-03.
- Django test discovery: executed successfully but found 0 tests; this is a coverage gap, not a test-suite pass.
- The initial `manage.py check --deploy` failure was resolved by `HT-SEC-P0-02` using an explicit production-like environment.

`HT-SEC-P0-02 - Baseline safe configuration`

- Removed the tracked Django secret and PostgreSQL credential literals from active configuration.
- Added strict environment parsing and explicit development/production behavior for Django, PostgreSQL, hosts, CSRF, HTTPS/cookies/HSTS, and Django 6.1 mailers.
- Added a clean, trackable root `.env.example`; real secret fields remain blank.
- Changed PostgreSQL Compose variables to required interpolation and loopback-only binding by default while preserving the existing named volume.
- Replaced the placeholder README setup with an explicit PowerShell onboarding flow.
- Did not add CORS, authentication, RBAC, business APIs, models, or migrations.

Verification in an isolated Python 3.12 container and the existing development PostgreSQL instance:

- Missing secret/database password, invalid boolean/integer, production debug, wildcard production host, and conflicting SMTP TLS/SSL checks: PASS (failed fast as expected).
- `pip check` and development `manage.py check`: PASS.
- Production-like `manage.py check --deploy --fail-level WARNING`: PASS with explicit HTTPS, secure-cookie, HSTS, host, and SMTP values. The development `.env.example` is not a production config.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- `manage.py migrate --check`: PASS, no unapplied migrations.
- Development server startup and legacy `GET /api/test/`: PASS at the time of HT-SEC-P0-02; this route is later replaced by `/api/health/`.
- PostgreSQL remained on named volume `docker_postgres_data` with 8 domain migrations, 23 public tables, and no leftover test database.

`HT-AUTH-P0-01 - User Authentication Foundation`

- Audited the current `AbstractUser` model, migrations, related foreign keys,
  admin, documentation, and legacy reference material.
- Kept the User model unchanged and did not create Profile, Workspace, schema,
  or migration changes.
- Chose Django server-side sessions with DRF `SessionAuthentication`; removed
  implicit HTTP Basic authentication and set DRF permissions deny-by-default.
- Added CSRF bootstrap, register, login, logout, and current-user endpoints
  under `/api/auth/`.
- Applied Django password validation and hashing, neutral invalid-login errors,
  inactive-user blocking, input length limits, no-cache identity responses,
  current-session revocation, and scoped authentication throttles.
- Defaulted `DRF_NUM_PROXIES` to zero so client-supplied forwarding headers do
  not bypass throttle identity before a trusted proxy chain is configured.
- Fixed the existing User admin change form by making auto-managed timestamps
  readonly.
- Documented the endpoint/CSRF contract and the session architecture decision.

Verification in a Python 3.12 container against PostgreSQL 16:

- `pip check`: PASS.
- `manage.py check`: PASS, no issues.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- `manage.py migrate --check`: PASS, no unapplied migrations.
- Full Django suite: PASS, 19/19 tests.
- Development server startup and `GET /api/auth/csrf/`: PASS (`200`, CSRF cookie and token returned).
- Temporary test database and backend smoke container were removed; the existing PostgreSQL data volume was preserved.

`HT-API-P0-03 - API deny-by-default and health endpoint`

- Kept DRF globally deny-by-default with `SessionAuthentication` and
  `IsAuthenticated`.
- Added a regression guard requiring every route in the API URL tree to use a
  DRF view and limiting explicit anonymous access to the reviewed public
  allowlist.
- Replaced the legacy `/api/test/` Django view with the public
  `/api/health/` DRF liveness endpoint.
- Kept health independent of authentication, throttling and database queries;
  it returns only `{"status": "ok"}` with no-store caching.
- Limited health to `GET`, standard `HEAD`/`OPTIONS`, and `405` for mutation
  methods and `TRACE`.
- Did not add Workspace/Profile code, RBAC, a business endpoint, model or
  migration changes.

Verification in a Python 3.12 container against PostgreSQL 16:

- `pip check`: PASS.
- `manage.py check`: PASS, no issues.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- `manage.py migrate --check`: PASS, no unapplied migrations.
- Full Django suite: PASS, 29/29 tests (19 authentication and 10 API
  health/policy tests).
- Development server startup: PASS.
- `GET /api/health/`: PASS (`200`, `application/json`, exact
  `{"status":"ok"}` payload and `Cache-Control: no-store`).
- `POST /api/health/`: PASS (`405`, `Allow: GET, HEAD, OPTIONS`); legacy
  `/api/test/`: PASS (`404`).
- Authentication regression smoke: `GET /api/auth/csrf/` returned `200` with
  a CSRF cookie.
- The temporary test database and smoke container were removed; the existing
  PostgreSQL named volume was preserved and its container was returned to its
  prior stopped state.

`Documentation and permanent handover foundation`

- Added root `AGENTS.md` with mandatory startup evidence checks, dirty-worktree
  preservation, architecture/scope rules, truthful task states, verification,
  per-document update routing, and checkpoint requirements.
- Added `documentation/HANDOVER.md` as the current, chat-independent transfer
  checkpoint for developers and future Codex sessions.
- Kept existing documentation files as the domain sources of truth rather than
  creating duplicate progress, roadmap, schema, API, or decision documents.
- No secrets or private environment values were copied into documentation.

`HT-DATA-P2-01 - Workspace architecture and ownership design`

- Audited all active Django models and initial migrations, current session/DRF
  permissions, API routes, Django Admin exposure, product requirements, and
  the relevant legacy discovery/security diagrams.
- Classified sources correctly: `ORIGINAL_REQUIREMENTS.md` is the
  capability-level requirement; `reference/original_document/00-discovery/`
  is legacy behavior evidence; the Spring material is historical research;
  current Django source remains authoritative for implementation state.
- Verified that Profile, invitation, Project, Workspace/RBAC API, and
  tenant-aware services do not exist. Current Workspace ownership has two
  unsynchronized truths (`Workspace.owner` and OWNER membership).
- Verified that Task derives Workspace scope, while Client/ShareLink,
  Invoice/Payment, and AuditLog currently lack a reliable tenant path.
- Verified that creator/assignee/commenter/uploader/reviewer membership in the
  Task Workspace is not enforced and several CASCADE relationships can erase
  business history when an actor/owner is deleted.
- Compared Workspace-root, Profile-root, and Profile-only options. Recommends
  Profile/Organization as tenant root, Workspace as operational/monthly child,
  User as global identity, Client/CRM as Profile-owned, and Task/Review as
  Workspace-owned.
- Proposed separate Profile and Workspace membership layers, internal roles
  separated from Client/Guest token principals, deny-by-scope query rules,
  actor membership invariants, last-owner transactions, and tenant-aware audit
  context.
- Produced a staged additive migration/backfill plan. Existing Workspace and
  especially Client/AuditLog rows require an owner-approved mapping; the plan
  forbids guessing tenants, editing `0001_initial.py`, or adding non-null
  constraints before reconciliation.
- Recorded the full proposal and decisions in `DECISION_LOG.md`, and current
  versus proposed schema in `DATABASE_SCHEMA.md`.
- The design task itself did not modify a model, migration,
  User/authentication mechanism, API, PostgreSQL row, Workspace permission, or
  frontend code. The separately authorized schema-foundation task below now
  implements its first additive portion.

Verification rerun on 2026-10-16 in an isolated Python 3.12 container against
PostgreSQL 16:

- `pip check`: PASS.
- `manage.py check`: PASS, no issues.
- `manage.py makemigrations --check --dry-run`: PASS, no model/migration drift.
- `manage.py migrate --check`: PASS, no unapplied migration.
- Full regression suite: PASS, 29/29 tests (19 authentication and 10 API
  health/policy tests).
- Django created and destroyed only the disposable `test_hustlytasker_db`;
  no application migration or PostgreSQL application row was changed.

Task status:

`COMPLETE / ACCEPTED — 2026-10-16`

The owner approved all 11 architecture decision groups. The intentionally
deferred details are listed below and do not authorize their future APIs or
workflows.

`PROFILE/WORKSPACE SCHEMA FOUNDATION — COMPLETE`

Implemented in source:

- Added `Profile` as company/team tenant root and `ProfileMembership` with
  protected User/Profile links, `OWNER`/`ADMIN`/`MEMBER`, active state,
  partial uniqueness for active Profile/User membership, inactive history, a
  role check, and tenant lookup indexes.
- Added transitional nullable `Workspace.profile` and changed
  `Workspace.owner` deletion from `CASCADE` to `PROTECT`. Validated new
  Workspaces require a Profile and an active Profile Owner/Admin as their
  transitional owner.
- Added persistence validation for Workspace and WorkspaceMember, prevents a
  mapped Workspace from changing Profile, and validates every legacy member
  before an explicit null-to-Profile mapping.
- Existing legacy Workspace saves lock the persisted row before accepting a
  null Profile, preventing a stale save from undoing a concurrent mapping.
- Added atomic Profile creation plus initial Owner, transactional/locked
  Profile membership updates, multiple-owner support, last-active-owner
  protection, Admin restrictions on Owner changes, a requirement to reassign
  transitional Workspace ownership before removing manager status, and
  membership AuditLog events.
- Added an audited service for Profile Owner/Admin to add an existing active
  Profile member directly to a Workspace. Generic membership reactivation is
  reserved for the future invitation-acceptance flow.
- Added additive `workspace/0002_profile_workspace_foundation.py`; no existing
  `0001_initial.py` was modified.
- Added model/service/concurrency tests and a populated migration test that
  preserves Workspace → Task → Deliverable → Review relationships without
  guessing a Profile for legacy rows.
- Added cross-Profile negative service tests proving that Profile manager
  authority never transfers to another Profile.

Data and migration evidence:

- Read-only development PostgreSQL inventory: 0 business rows, 3 User rows.
- No Profile/backfill row was synthesized.
- `0002` ran only on disposable PostgreSQL test databases, including empty and
  populated cases. It has not been applied to the development database.

Current verification (rerun on 2026-10-17):

- Targeted `apps.workspace`: PASS, 32/32.
- `manage.py check`: PASS.
- `manage.py makemigrations --check --dry-run`: PASS.
- `pip check`: PASS.
- Full PostgreSQL suite after this schema change: PASS, 61/61. This includes
  all 19 Authentication and 10 API Foundation regression tests.

Known service boundary, not hidden as a database guarantee:

- Normal Workspace/WorkspaceMember writes and membership services share
  Profile-first locking, including concurrent legacy mapping and manager-role
  transitions. Bulk/raw writes can bypass this boundary.
- Direct `User.is_active` changes and direct ProfileMembership ORM mutation can
  still bypass the usable-last-Owner service invariant. No account lifecycle
  change was made in this task; this must be closed before a global invariant
  is claimed.
- Inactive Profile membership does not erase WorkspaceMember history. Future
  permission code must check both layers, and invitation/rejoin policy must
  decide whether old Workspace access is restored.

Approved target not implemented in this task: Invitation/API, Project,
Client/Profile and Finance migrations, public-link replacements, soft delete,
tenant query scoping/full RBAC, detailed Task/Review workflow, and frontend.

`HT-RBAC-DESIGN-P0-01 — DESIGN READY / PENDING OWNER APPROVAL`

Completed as design evidence:

- Classified outsource requirements, the 11 approved decisions, current
  Django source, legacy reference evidence, proposals, and open decisions so
  proposed permissions cannot be mistaken for accepted policy.
- Produced an action-level matrix for Profile Owner/Admin/Member and proposed
  Workspace Admin/Member/Viewer behavior. Existing Workspace `OWNER` and
  `VIEWER` enum values are not treated as approved capabilities.
- Defined fail-closed request context, scoped querysets, same-tenant input
  validation, `404`/`403`/generic `400` IDOR behavior, transaction/lock order,
  and controls for ORM, bulk, jobs, and Django Admin bypass paths.
- Found that `update_profile_membership()` globally resolves membership ID,
  while `add_workspace_member()` globally resolves Workspace ID and accepts an
  already-resolved unscoped target User before actor scope. No route exposes
  them today; both boundaries must be refactored before an API is opened.
- Defined a Profile-only invitation lifecycle with authenticated recipient
  binding, CSRF, hashed one-time token, terminal states, concurrency/audit
  rules, planned routes, and negative tests. Workspace direct-add remains a
  separate operation available only after active Profile membership.
- Reconfirmed development PostgreSQL read-only: only `workspace.0001` is
  applied; 3 Users and 0 business rows; `workspace.0002` was not applied and
  Docker was returned to its prior stopped state.
- Documentation QA: required design sections/status labels PASS; UTF-8/no-NUL
  check PASS for all affected documentation; secret-pattern scan found no
  matches; `git diff --check` PASS with only existing LF→CRLF warnings.
- No backend implementation test was rerun for this documentation-only task.
  The local venv points to a missing Python 3.12 installation and neither
  `py` nor `python` is installed on PATH. No replacement environment or new
  container was created. The latest actual source evidence remains targeted
  32/32 and full PostgreSQL 61/61 from the schema-foundation checkpoint.

Implementation deliberately not performed: no source model/service/API or
migration was edited, no migration was applied, and no data was written. The
current runtime API documentation therefore remains unchanged.

### Review Gate

`HT-AUTH-P0-01`, `HT-API-P0-03`, and the `HT-DATA-P2-01` architecture decision
are complete. The schema foundation implementation and verification are also
complete. The owner then authorized this design task only.

Stop at `HT-RBAC-DESIGN-P0-01` owner review. Do not begin Workspace API, RBAC
implementation, Invitation migration/API, Project/Client/Finance migration,
Task workflow, or another business API. Do not apply `0002` without a separate
approved operational step, repeated inventory, and backup policy appropriate
to the target environment.

### Decisions Required Before Business APIs

- Authentication activation method (email link or OTP); session is the selected foundation contract for the current same-origin architecture.
- Workspace role vocabulary: keep Workspace Admin; deprecate Workspace Owner;
  enable/disable Viewer and approve its exact read/download scope.
- Profile Admin authority over other Admins, Workspace membership management,
  and soft-delete/restore operations.
- Profile creation self-service eligibility/limits and the initial-Owner
  bootstrap; voluntary leave/rejoin and historical Workspace access behavior.
- Task visibility for Members and whether inherited Profile managers need an
  explicit Workspace membership for contributor actions.
- Invitation role ceiling, registered/unregistered recipient onboarding,
  existing-account email verification, TTL/reinvite/throttle, issuer revalidation,
  optional Workspace orchestration, and invitation retention.
- Proposed non-enumerating `404`/`403`/generic `400` behavior, `409` conflict
  envelope, platform-operator/Admin bypass, and User deactivate/delete/session
  policy protecting the last usable Owner.
- Invoice numbering and detailed billing workflow.
- Client Portal/Guest Review exact fields/actions, account-linking flow and
  default expiry/rotation details.
- Retention duration, legal hold/purge schedule and hard-delete authority.
- Canonical Task/Review states, approver permissions and payroll trigger.
- Explicit mapping for any existing row that a later environment inventory
  cannot map safely; unknown rows remain blockers rather than guessed tenants.

---

## Historical Log - Superseded Snapshots

The remaining sections are preserved from earlier development phases. They are
not current tasks or instructions; use the snapshot and review gate above as
the source of truth.

### Historical Current Phase

PHASE 2.2 - API Architecture


### Historical Latest Completed Phase

PHASE 2.1 - Django REST Framework Foundation


Completed:

- Added Django REST Framework.
- Created API routing.
- Created the legacy `/api/test/` endpoint (later replaced by `/api/health/`).
- Verified API response.


### Historical Next Step

PHASE 2.2

Tasks:

- Design API structure.
- Define serializers.
- Define authentication flow.
- Define permission system.
- Prepare API documentation.


### Historical Overall Progress

10%


---

# Completed


## Documentation

[x] Imported original system documents

[x] Created requirement documentation

[x] Created developer profile

[x] Created architecture documentation

[x] Created technology decision document


## Project Management

[x] Created project folder structure

[x] Initialized Git repository

[x] Connected GitHub repository

[x] Created first commit


---

# Current Status

The project is ready for development.


---

# Next Phase

## Phase 1 - Development Environment Setup


Tasks:

- Setup Python environment.
- Install Django.
- Create Django project.
- Setup PostgreSQL.
- Connect Django with PostgreSQL.
- Create Docker environment.


---

# Known Issues

# PROJECT PROGRESS


## Current Phase

Phase 1.6 - Database Schema Design


## Completed Today

[x] Setup Django environment

[x] Setup PostgreSQL using Docker

[x] Connect Django with PostgreSQL

[x] Create modular Django app structure

[x] Fix Django app namespace configuration

[x] Create initial database schema

[x] Improve DATABASE_SCHEMA.md


## Current Status

Backend foundation completed.

Database design is currently being reviewed before creating Django Models.


## Current Working Files

Modified:

- documentation/DATABASE_SCHEMA.md
- documentation/PROGRESS.md


Created:

- backend/apps/
- backend/common/


## Next Step

PHASE 1.6.3:

Create Entity Relationship Diagram (ERD)

Then:

PHASE 1.7:

Create Django Models


## Known Issues

## Phase 1.8 Completed

Completed:
- Django models created
- Initial migrations generated
- PostgreSQL schema created
- Custom User Model verified
- Database relationships verified

Next:
PHASE 1.9 Django Admin + CRUD Testing

PHASE 2.1 completed.

DRF foundation created.
