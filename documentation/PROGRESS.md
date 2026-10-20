# PROJECT PROGRESS

## Current Snapshot - 2026-10-21 (HT-TASK-P2-03)

### Current Phase

`PHASE 2.2 - API Architecture / Task and internal approval workflow`

### HT-TASK-P2-03 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

The approved backend-only Task/Deliverable/internal Review slice is implemented
in source. It keeps the existing Task ownership path (`Task -> Workspace ->
Profile`), SessionAuthentication, tenant contexts, and deny-by-default DRF
policy.

Implemented at this checkpoint:

- Additive `tasks.0002_task_workflow_foundation` and
  `reviews.0002_review_workflow_foundation` harden actor deletion with
  `PROTECT`, add status/priority checks and lookup indexes, retain one current
  active Task assignment, add positive per-Task Deliverable revisions, and
  enforce one internal Review per Deliverable. Legacy assignments become
  inactive, legacy Deliverable revisions remain `NULL`, and no current
  assignee/revision is guessed.
- Manager Task create/update/assign, assignee-only start and Deliverable
  submission, and manager-only internal approve/request-changes are provided
  through locked transactional services with atomic AuditLog events.
- The state machine is `PENDING -> ASSIGNED -> WORKING -> REVIEW`, then either
  `COMPLETED` after approval or `WORKING` after requested changes and a later
  resubmission. No arbitrary status mutation exists; `CANCELLED` is reserved
  and has no public transition.
- Profile Owner/Admin and assigned Workspace Admin manage/review Tasks in an
  active Workspace. Only an active ordinary Profile Member with effective
  Workspace `MEMBER` (Editor) capability and the current active assignment may
  start or submit. Self-review, stale revision review, repeat review, and
  cross-tenant/wrong-parent access fail closed.
- Seven nested `/api/v1/` route shapes provide Task list/create,
  detail/update, assign, start, Deliverable list/submit, approve, and
  request-changes operations. Inputs are strict, outputs omit User PII, list
  responses are bounded/paginated, unsafe methods retain session CSRF, and no
  Task/Deliverable delete or arbitrary status endpoint is exposed.
- Internal approval is explicitly separate from Client approval. Completion
  creates no Payroll/Payment row and performs no compensation calculation.
  Comments API, upload/media pipeline, Marketplace, Client Portal/Guest Review,
  Finance, Invitation, and frontend remain outside this task.
- Task, TaskAssignment, and TaskComment Django Admin surfaces are
  inspection-only. Workspace deletion through Django Admin is disabled because
  the existing Workspace -> Task FK would otherwise cascade-delete workflow
  history. Task soft delete and the wider retention/purge implementation are
  still pending a separate approved task.

Verification actually completed:

- `python -m pip check`: PASS.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, `No changes
  detected`.
- Targeted Task service/API/migration suite: PASS, **33/33** on a
  Django-created PostgreSQL test database in 7.673s; the database was
  destroyed.
- The migration rehearsal preserves legacy Task/Deliverable/Review rows,
  deliberately leaves legacy assignments inactive and Deliverable revisions
  null, and verifies the one-active-assignment constraint.
- Existing Authentication/API/Workspace regression group: PASS, **169/169** in
  87.783s.
- Final full PostgreSQL suite: PASS, **202/202** in 92.343s. The run also
  repeated dependency, Django system, and migration-drift checks; its test
  database was destroyed.
- Independent final code review: PASS; no unresolved implementation blocker.
- Documentation-scoped `git diff --check`: PASS; only existing LF-to-CRLF
  conversion warnings were emitted.

Development state is intentionally unchanged: `workspace.0003` is applied,
while `tasks.0002` and `reviews.0002` have **not** been applied. The latest
read-only post-check found `workspace.0001/0002/0003`, `tasks.0001` only and
`reviews.0001` only; 3 Users, 2 sessions, and zero Profile,
ProfileMembership, Workspace, WorkspaceMember, Task, TaskAssignment,
Deliverable, Review, or AuditLog rows. No test/rehearsal database or
`htp203` runner remains. No development or production migration is authorized
by this implementation checkpoint.

### Exact continuation / review gate

Stop at `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`.
The next allowed action is Owner review and, only under a separate explicit
authorization, a controlled development inventory/backup/plan/apply/smoke for
`tasks.0002` then `reviews.0002`. Do not apply either migration or start another
module from this checkpoint.

---

## Previous Snapshot - 2026-10-20 (HT-DB-P1-06)

### Current Phase

`PHASE 2.2 - API Architecture / controlled Workspace 0003 rollout`

### HT-DB-P1-06 — COMPLETE / OWNER REVIEW GATE

- Verified the existing development target as Compose container
  `hustlytasker_postgres`, PostgreSQL 16.14, database `hustlytasker_db`,
  loopback-only port 5432, and named volume `docker_postgres_data`.
- Immediately before apply, confirmed 27 migrations with `workspace.0002`
  applied and `workspace.0003` absent from both history and physical schema.
  Inventory was 3 active Users, 2 Django sessions, and zero checked business
  rows; no other PostgreSQL connection, unvalidated constraint, test database,
  or rehearsal database existed.
- Re-reviewed the tracked additive migration. `pip check`, Django system check,
  migration-drift check, global plan, and targeted plan pass; the plan contains
  only `workspace.0003`.
- Created the mandatory fresh pre-apply custom backup at
  `.local_backups/HT-DB-P1-06/hustlytasker_dev_pre_workspace_0003_20261020T073750Z.dump`
  (73,521 bytes; SHA-256
  `b004c1e102b0fedde5eea4418010d46fec76ea18788e59b937e7ef4cb63f7df4`).
  TOC listing, complete archive read, and container/host hash comparison pass.
- Full restore rehearsal passed in isolated database
  `htdb_p106_restore_20261020073818`; it reproduced the pre-migration state and
  was removed with cleanup verified.

`workspace.0003` was applied successfully to development at 2026-10-20
07:44:40 UTC. Development now has 28 migration records. All four new columns,
validated CHECK constraints, the conditional unique Profile/month index, and
lookup indexes exist and are valid/ready. Pre/post counts remain 3 active Users,
2 Django sessions, and zero checked business rows; no invalid lifecycle/period
value, duplicate period, unvalidated constraint, other session, or leftover
test/rehearsal database was found.

Post-apply verification is complete:

- `pip check`, Django system check, migration drift check, `migrate --check`,
  and Workspace `showmigrations` all PASS.
- **DEV SMOKE PASSED:** health `200`, CSRF bootstrap `200`, login without CSRF
  `403`, invalid login with valid CSRF `400`, and anonymous denial `403` across
  all current Profile/Workspace/membership read and mutation routes. No
  business row or session changed.
- **ISOLATED INTEGRATION TEST PASSED:** lifecycle/schema/concurrency 17/17 in
  13.341s; Workspace API/service/migration 140/140 in 76.602s;
  Authentication/API Foundation 29/29 in 7.327s; full PostgreSQL 169/169 in
  85.858s. Every temporary test database was destroyed.
- Final database inventory and integrity checks remain unchanged and clean;
  the disposable runner was removed. **NOT TESTED ON PERSISTENT DEVELOPMENT:**
  authenticated role/tenant/IDOR and successful lifecycle/member flows, because
  development has no business fixture; the isolated suites cover those cases.

No reverse migration, `--fake`, fixture, data deletion, source/API contract
change, or production action occurred. Stop at the Owner review gate. The next
roadmap candidate is `HT-TASK-P2-03`, but implementation requires separate
authorization and approval of Task states, reviewer authority, and payroll
trigger.

---

## Previous Snapshot - 2026-10-20 (HT-WORK-P2-02)

### Current Phase

`PHASE 2.2 - API Architecture / Workspace write foundation`

### HT-WORK-P2-02 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

The Owner-approved schema-dependent remainder is implemented in source and
verified on isolated PostgreSQL without applying the new migration to the
development or production database:

- Additive migration `workspace.0003_workspace_lifecycle_and_period` adds
  `Profile.status`, canonical `Workspace.period`, `Workspace.status`, and
  `WorkspaceMember.is_active`, together with status/period checks and lookup
  indexes. The `(profile, period)` uniqueness rule includes archived
  Workspaces. Existing legacy `NULL` periods are preserved for a controlled
  rollout; supported Workspace creation requires a first-of-month period.
- Profile Owner-only archive/restore and Profile Owner/Admin Workspace
  archive/restore endpoints are implemented. Archived Profile/Workspace data
  remains tenant-safe and readable, while ordinary metadata, child, and
  membership writes fail closed until restoration.
- Workspace create requires `period`; a non-first-day value is invalid and a
  duplicate monthly period, including an archived Workspace, maps to `409`.
  Period and lifecycle fields are server-controlled after creation.
- Workspace-member `DELETE` is a soft revoke that retains the assignment row
  and immediately removes effective access. A later eligible `POST` reactivates
  that same row instead of creating duplicate active/history rows. Role ceilings,
  same-Profile eligibility, row locking, and atomic AuditLog behavior remain in
  force.
- Profile and Workspace hard delete are not exposed. This task does not add
  Invitation, Profile creation, another business domain, or frontend work.

### Verification status

Final verification for the complete source implementation is current:

- `python -m pip check`: PASS.
- `python manage.py check`: PASS.
- `python manage.py makemigrations --check --dry-run`: PASS; no changes.
- Workspace PostgreSQL suite: PASS, 140/140 in 79.278s.
- Full PostgreSQL suite: PASS, 169/169 in 82.920s.
- The isolated `0002 -> 0003` migration rehearsal passed, preserving Task,
  Deliverable, and Review rows while applying lifecycle defaults without
  synthetic tenant mapping.
- `python manage.py migrate --check` exits `1` as expected because `0003` is
  intentionally pending on development. The reviewed migration plan is
  additive; this expected result is not a consistency failure.

The latest successful post-suite development inventory on 2026-10-19 recorded
the existing loopback Compose PostgreSQL 16.14 target with 27 migration rows,
`workspace.0002` applied, 3 Users, zero Profile, ProfileMembership, Workspace,
WorkspaceMember, Task, Client, Invoice, Payment, or AuditLog rows, and no
`test_%` database. A read-only container-state check on 2026-10-20 found that
existing PostgreSQL container stopped; it was not started, so no newer database
inventory is claimed. `workspace.0003` remains unapplied, no development
business/schema write occurred, and production was not contacted.

### Exact continuation / review gate

Stop at `PENDING DEVELOPMENT MIGRATION APPROVAL`. The exact next action is
Owner review of the source/migration/test evidence and, only if separately
approved, a controlled development rollout of
`workspace.0003_workspace_lifecycle_and_period` with fresh inventory, backup,
plan review, apply, and smoke verification. Do not apply `0003`, open another
feature task, or change production from this checkpoint.

---

## Previous Snapshot - 2026-10-19 (HT-DB-P1-05, superseded)

### Current Phase

`PHASE 2.2 - API Architecture / controlled development rollout`

### HT-DB-P1-05 - COMPLETE / OWNER REVIEW GATE

The condition-gated development rollout is complete without source changes,
business fixtures, data deletion, credential reset, or production access.

Completed and verified:

- Reconfirmed the existing local Compose PostgreSQL 16.14 development target,
  3 active Users, zero checked business rows, no orphan/unvalidated FK, and
  the pre-apply state of 26 migrations with `workspace.0002` unapplied.
- Revalidated the Git-ignored 66,721-byte custom backup by matching SHA-256,
  TOC listing, and full archive read. A full restore rehearsal into a uniquely
  named isolated database passed and the rehearsal database was removed.
- Used a process-only development configuration in disposable Python 3.12
  containers. No `.env` or secret file was created; no secret was printed or
  documented. Although the Owner's host shell reported a working venv, the
  Codex managed context exits 103 and reports its base path unavailable; the
  venv was not modified or replaced.
- Reviewed the exact additive migration plan and applied only
  `workspace.0002_profile_workspace_foundation` to development. Final state is
  27 migration rows with Profile/ProfileMembership tables and nullable
  `Workspace.profile_id`; constraints/indexes validate and all business counts
  remain zero. No tenant mapping was synthesized.
- Direct development smoke passed: health `200`; all four tenant routes and
  `/api/auth/me/` anonymous `403`; CSRF bootstrap `200`; invalid login without
  CSRF `403` and with valid CSRF `400`; no `500` and no new Django session.
- Current verification passed: `pip check`; Django system check;
  `makemigrations --check --dry-run`; `migrate --check`; targeted read API
  21/21; Authentication/API Foundation 29/29; full PostgreSQL suite 101/101.
  Final checks found no test/rehearsal databases or temporary containers.

Development after migration: 3 Users; 0 Profile, ProfileMembership, Workspace,
WorkspaceMember, Task, Client, Invoice, Payment, and AuditLog rows; 1 existing
Django session; zero unmapped Workspace/orphan/unvalidated constraints.

### Review Gate

Stop for Owner review. Do not begin Workspace Write, Membership, Invitation,
or frontend work. `HT-WORK-P2-02` is only the roadmap candidate after an
explicitly approved implementation scope; Invitation retains its account/email
binding dependency.

---

## Superseded Snapshot - 2026-10-19 (pre-migration blocker)

Historical only. The status and continuation instructions below were valid
before the Owner-authorized runtime recovery, migration apply, and verification.

### Current Phase

`PHASE 2.2 - API Architecture / controlled development rollout`

### HT-DB-P1-05 - BLOCKED BEFORE MIGRATION / OWNER ACTION REQUIRED

The owner conditionally authorized applying the existing
`workspace.0002_profile_workspace_foundation` migration to the development
database only, after identity, inventory, backup, plan, and risk gates.

Completed and verified at this checkpoint:

- Recovered a clean `main` worktree at `b8f1767`; did not redo P1-04.
- Independently identified the existing local Compose PostgreSQL target:
  `hustlytasker_postgres`, PostgreSQL 16.14, loopback port 5432, database
  `hustlytasker_db`, and preserved named volume `docker_postgres_data`.
- Confirmed 26 applied migration rows: `workspace.0001` is applied and
  `workspace.0002` is not. Profile/ProfileMembership tables and
  `Workspace.profile_id` are absent.
- Inventoried 3 active Users and zero Workspace, WorkspaceMember, Task,
  Client, Invoice, Payment, or AuditLog rows. Profile counts are not reported
  as zero because their tables do not yet exist. No checked orphan,
  unvalidated FK, or leftover test database was found.
- Re-reviewed unchanged `0002`: additive create/add/alter-to-`PROTECT` only,
  with no data migration, deletion, guessed mapping, or destructive operation.
- Created a Git-ignored PostgreSQL custom archive under
  `.local_backups/HT-DB-P1-05/`. Host/container SHA-256 matches; TOC listing
  and a complete `pg_restore` stream to `/dev/null` both pass. No restore was
  attempted.

Blocking condition:

- No ignored `.env` or complete approved runtime environment is available to
  the Django management-command runner, including a legitimate development
  `DJANGO_SECRET_KEY` and its database connection variables. The PostgreSQL
  service retains its own internal variables, but settings deliberately fail
  fast and do not auto-load `.env`.
- Host Python is unavailable and the old virtualenv points to a removed
  Python 3.12.5 installation. The cached Python image is usable only after the
  approved development configuration is restored.
- Per owner instruction, no secret/credential was generated, extracted,
  reset, or substituted. Consequently `migrate --plan`, migration apply,
  live API smoke, Django checks, and current regression suites have not run.
  Development remains on `workspace.0001`; schema and rows are unchanged.

### Review / Configuration Gate

Owner must restore the legitimate local development environment variables
without placing secrets in source, documentation, logs, or chat. Then resume
at `migrate --plan`, apply only `workspace.0002` if the plan still matches,
perform post-migration integrity checks, separate direct-development smoke
from isolated-test verification, and run all required regressions.

Do not begin Workspace Write, Membership, Invitation, or another task.

---

## Previous Snapshot - 2026-10-18 (HT-API-P1-04, superseded)

This historical snapshot records the completed P1-04 state before the owner
opened HT-DB-P1-05. Use the current snapshot above.

### Current Phase

`PHASE 2.2 - API Architecture`

### HT-API-P1-04 - COMPLETE / OWNER REVIEW GATE

The owner authorized the minimal Profile/Workspace read API after
`HT-RBAC-P1-03`. The implementation reuses its access contexts and selectors;
it does not create a parallel authorization system.

Completed in this task:

- Added four read-only tenant routes under `/api/v1/`: Profile list/detail and
  nested Workspace list/detail.
- Added minimal read serializers. Profile responses expose only `id`, `name`,
  `created_at`, and `updated_at`; Workspace responses add `profile_id`,
  `description`, and no owner/member/role/PII field.
- Added DRF permission adapters for an active authenticated identity, active
  Profile access, and effective Workspace read access. No new endpoint uses
  `AllowAny`; SessionAuthentication and global deny-by-default remain intact.
- Every list and object lookup starts from `profiles_visible_to()` or
  `workspaces_visible_to()`. Cross-Profile, wrong-parent, sibling,
  malformed, random, revoked, inactive, legacy-role, Profile-null, and
  transitional-owner cases fail closed without disclosing existence.
- Added bounded page-number pagination: default 20, client maximum 100, stable
  `created_at`/`id` ordering, and no client-controlled search/filter/order.
- Limited all four views to `GET`, `HEAD`, and `OPTIONS` and marked responses
  non-cacheable. Unsupported unsafe requests enforce SessionAuthentication/
  CSRF and tenant permissions first (`403`/`404` when those checks fail), then
  return `405` for an authorized request with valid auth/CSRF; no path changes
  Profile, Workspace, membership, or AuditLog data.
- Independent review identified a late membership-revocation race between DRF
  permission resolution and queryset evaluation. The shared view mixin now
  maps that stale access exception to the same generic JSON `404`, with a
  regression test for both Workspace list and detail.
- No authentication mechanism, model, schema, migration, service business
  rule, development row, or Docker resource changed.

Verification actually run against Django-created disposable PostgreSQL test
databases:

- Targeted `apps.workspace.test_api`: PASS, 21/21, including an explicit
  session-CSRF-before-`405` regression.
- Authentication and API Foundation regressions (`api apps.accounts`): PASS,
  29/29, including the existing SessionAuthentication/CSRF policy coverage.
- Final full PostgreSQL suite after all code/test changes: PASS, 101/101 in
  55.129s inside a disposable Python 3.12 container with the source mounted
  read-only; Django destroyed the disposable test database.
- `python -m pip check`: PASS.
- In-memory Python syntax compile for the new modules/tests: PASS.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- Read-only migration plan still shows `workspace.0001_initial` applied and
  `workspace.0002_profile_workspace_foundation` unapplied in development.
- Post-test read-only verification found no leftover `test_%` database.
- Current local `.env` is absent and the historical Windows virtualenv points
  to a removed Python installation; verification was safely restored with the
  cached ephemeral Python image, without recreating PostgreSQL infrastructure.
- `git diff --check`: PASS (only existing LF-to-CRLF conversion warnings).
  Strict UTF-8/no-BOM/no-NUL/code-fence/trailing-whitespace QA and
  secret-assignment scan: PASS for all 17 changed/new code/documentation files.

Known boundary: the source migration was exercised on disposable test
databases that Django destroyed, but development still has only
`workspace.0001` and no Profile table.
The new routes must not be exercised there until the owner separately approves
inventory, backup, the existing `0002` rollout, and a development smoke test.
No endpoint required by this read-only task remains missing; Workspace writes,
membership management, Invitation, and downstream business APIs are explicitly
outside scope.

### Review Gate

Stop at the `HT-API-P1-04` owner review gate. Do not apply `workspace.0002`,
open write/Invitation APIs, or begin another roadmap task automatically.

---

## Previous Snapshot - 2026-10-18 (HT-RBAC-P1-03, superseded)

This historical snapshot describes the completed access/service foundation
before the owner authorized HT-API-P1-04. Use the current snapshot above.

### Current Phase

`PHASE 2.2 - API Architecture`

### HT-RBAC-P1-03 - COMPLETE / OWNER REVIEW GATE

The owner delegated the remaining RBAC design decisions to the Technical
Advisor. `HT-RBAC-DESIGN-P0-01` is therefore `COMPLETE / ACCEPTED - APPROVED BY
OWNER DELEGATION`; its 14 delegated decisions are recorded in
`RBAC_DESIGN.md` and `DECISION_LOG.md`.

Implemented in this task:

- Added `backend/apps/workspace/access.py` with immutable, resolver-produced
  Profile/Workspace contexts, tenant-scoped Profile/Workspace selectors, and
  fail-closed read/edit/member-management capability checks.
- Context resolution requires a current active User and active
  ProfileMembership. Profile Owner/Admin see mapped Workspaces in their own
  Profile; ordinary Profile Members see only Workspaces with an effective
  explicit WorkspaceMember role.
- Kept the existing schema vocabulary with the approved compatibility map:
  WorkspaceMember `ADMIN` = Workspace Admin, `MEMBER` = Editor, `VIEWER` =
  read-only Viewer. Legacy `OWNER` is not assignable and grants no capability
  through the new boundary.
- Hardened contexts against direct construction, `dataclasses.replace()` role
  escalation, stale account/Profile membership, and stale Workspace role.
- Refactored `update_profile_membership()` to authorize Profile scope before
  resolving the target. Profile Admin may manage current ordinary Members only;
  Owner changes and the last-active-owner invariant remain locked and audited.
- Refactored `add_workspace_member()` to accept a scoped
  `target_profile_membership_id`, revalidate authority under locks, require an
  active same-Profile membership and active User, enforce role ceilings, and
  translate duplicate/concurrent adds to a stable domain conflict. Audit is
  written only after a successful mutation.
- No API route, authentication mechanism, model, schema, or migration changed.
  Workspace/Invitation APIs remain unopened.

Verification on PostgreSQL 16 using Django-created disposable test databases:

- Local Python 3.12 environment synchronized to Django 6.1.2 and DRF 3.18.3;
  `pip check`: PASS.
- Python compile check for access/services/tests: PASS.
- `manage.py check`: PASS, no issues.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- Final targeted `apps.workspace` suite after independent-review hardening:
  PASS, 51/51.
- Final full suite: PASS, 80/80, including all 19 Authentication and 10 API
  Foundation regressions.
- The earlier pre-hardening runs also passed 49/49 targeted and 78/78 full;
  they are not used as the final acceptance evidence.
- Read-only development inventory reconfirmed 3 Users and 0 business rows.
  Only `workspace.0001_initial` is applied; `workspace.0002` remains unapplied.
- Post-test read-only verification found no leftover `test_hustlytasker_db` and
  the Profile table remains absent from development, as expected before `0002`.
- `git diff --check`: PASS (only existing LF-to-CRLF conversion warnings).
  Strict UTF-8/no-NUL/code-fence QA and secret-assignment scan: PASS for all
  changed code/documentation files.

Known boundaries:

- Direct ORM, bulk, raw-SQL, or unsafe Django Admin writes can bypass service
  invariants. Tenant managers must use reviewed services; Django Admin remains
  a platform-superuser surface until a tenant-scoped Admin exists.
- Direct `User.is_active` mutation still lacks the approved cross-Profile
  last-owner/session-revocation lifecycle service. This task rechecks inactive
  accounts but does not implement global account deactivation or session purge.
- There are no Client, Finance, Audit, Task, Review, Invitation, or Workspace
  API selectors yet. Concrete reviewer role/workflow states remain deferred.
- `workspace.0002` is intentionally not applied to development. No development
  row was created, changed, deleted, or backfilled.

### Review Gate

Stop at the `HT-RBAC-P1-03` owner review gate. Do not apply `workspace.0002`,
open Workspace/Invitation APIs, or begin the next task in this worktree without
owner review.

---

## Previous Snapshot - 2026-10-17 (superseded)

This superseded snapshot is retained only as development history and may
describe earlier phases. Use the current 2026-10-18 snapshot above.

### Current Phase

`PHASE 2.2 - API Architecture`

### Audit Result

- Git branch `main` and the local `origin/main` ref both point to `5e89971`.
  The current worktree contains only the nine modified documentation files for
  this reconciliation, as inventoried in `HANDOVER.md`; all are being preserved.
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
  isolation tests, dependency order, and 11-group reconciliation table are
  recorded in `RBAC_DESIGN.md`. All 11 approved groups now match; only seven
  grouped decisions remain for owner review. No API, model, migration,
  permission code, or database row changed.
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
  still bypass the foundation service's stronger effective-Owner check. The
  approved invariant is at least one active Owner membership; account activity,
  deletion, and session mechanics remain open. No account lifecycle change was
  made in this task.
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
- Reconciled the full design against all 11 approved decision groups. Initial
  findings: groups 1–3/5/10 `MATCH`; group 4 `CONFLICT` because “usable Owner”
  had been over-labeled as approved; groups 6–9/11 `NOT DOCUMENTED` in part or
  whole. Corrected the label and added every missing approved boundary; all 11
  now read as `MATCH`. The review gate is reduced from 16 granular questions
  to seven genuinely open decision groups.
- Reconfirmed development PostgreSQL read-only: only `workspace.0001` is
  applied; 3 Users and 0 business rows; `workspace.0002` was not applied and
  Docker was returned to its prior stopped state.
- Documentation QA after reconciliation: required 11-row comparison and seven
  open-group structure PASS; UTF-8/no-NUL/code-fence checks PASS for all nine
  affected files; secret-pattern scan found no matches; `git diff --check`
  PASS with only line-ending conversion warnings.
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

### Decisions Required Before RBAC Implementation

The 11 approved architecture groups are reconciled and must not be reviewed
again. Owner review is limited to these seven groups:

1. Workspace role vocabulary and action ceiling.
2. Profile Admin and Profile/Workspace lifecycle authority.
3. Workspace Member Task visibility and contributor-membership requirement.
4. Profile/account/membership lifecycle: self-service eligibility/limits,
   leave/rejoin/history, and deactivate/delete/session mechanics. Atomic
   initial-Owner creation already exists and is not an open decision.
5. Invitation identity/onboarding and role/management ceiling, including
   whether an invitation can ever request `OWNER` (proposal: no).
6. Invitation TTL/reinvite/throttle/delivery, inviter revalidation, record/PII
   retention, and optional combined UX that preserves acceptance then direct-add.
7. Non-enumerating error/`409` and platform-operator/Django Admin policy.

Other genuine decisions remain scoped to their later tasks: authentication
activation method; Invoice numbering/billing; Client Portal/Guest Review exact
capabilities/account linking/default expiry; retention/legal hold/purge; and
exact Task/Review states, approvers, and payroll trigger. A tenant row that
cannot be mapped becomes an evidence-specific migration blocker if encountered;
the already-approved rule is not to guess.

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
