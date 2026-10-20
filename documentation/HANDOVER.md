# HUSTLYTASKER HANDOVER

## Current checkpoint — 2026-10-20 — HT-WORK-P2-02

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `cb8e338`

Current task: **HT-WORK-P2-02 — IMPLEMENTATION COMPLETE — PENDING
DEVELOPMENT MIGRATION APPROVAL**

Read root `AGENTS.md` before any later action. Preserve every dirty file, the
development database, and the ignored HT-DB-P1-05 backup. Do not commit, push,
reset, rewrite migration history, apply `workspace.0003`, create development
business fixtures, or begin another roadmap feature without separate Owner
authorization.

### Resume classification

- `DONE before the latest token interruption`: approved schema-dependent code,
  additive migration `0003`, API/service integration, schema/API/concurrency
  tests, the full isolated PostgreSQL verification, and read-only development
  migration/inventory checks.
- `PARTIAL at interruption`: permanent documentation reconciliation. The API
  contract had just been updated; the remaining current-state documents and
  this handover still described the superseded schema approval gate.
- `DONE after resume`: all required current-state documentation reconciled with
  source/test/development evidence and the final dirty-tree checks rerun.
- `BLOCKED`: no source implementation blocker. Applying `workspace.0003` to
  development is intentionally blocked by the required Owner approval gate.

### Implementation now complete in source

- `Profile.status` supports only `ACTIVE` and `ARCHIVED`, defaults safely to
  `ACTIVE`, and has a database check plus lookup index. A current Profile Owner
  may archive/restore; Profile Admin cannot. Archived Profiles remain scoped
  and readable but block supported child and membership writes. Hard delete is
  not exposed.
- `Workspace.period` is a canonical first-of-month date. Supported new writes
  require it, later changes are rejected, and the database prevents more than
  one non-null `(profile, period)` even when the existing Workspace is archived.
  A Profile row lock and database uniqueness protect concurrent creation.
- `Workspace.status` supports `ACTIVE`/`ARCHIVED`. Profile Owner/Admin may
  archive/restore; Workspace Admin cannot. Archived Workspaces stay readable to
  callers with effective access but metadata and membership mutations fail
  closed until restore. Tenant hard delete is not exposed; existing
  platform/Admin destructive paths remain outside this task and require
  separate control.
- `WorkspaceMember.is_active` provides soft revoke. Revoke immediately removes
  effective access and roster visibility while retaining the row. Direct-add
  of the same eligible Profile member reactivates that same unique
  `(workspace, user)` row; no duplicate history row is created.
- Service boundaries lock in Profile → Workspace → membership order, recheck
  active tenant authority and role ceilings, and write lifecycle/revoke/
  reactivate AuditLog events in the same transaction. Audit failure rolls back
  the state change. Workspace Admin stays limited to `MEMBER`/`VIEWER`; legacy
  Workspace `OWNER` remains fail-closed.
- Read selectors remain tenant-scoped, include archived resources when the
  caller still has effective read access, and exclude inactive WorkspaceMember
  assignments immediately. Cross-Profile, wrong-parent, stale-context, and
  concurrent privilege-escalation paths stay fail-closed.
- Django Admin exposes lifecycle values for inspection but does not offer an
  unaudited status or WorkspaceMember activation toggle. A mapped/non-null
  monthly period is read-only.

### Schema and migration state

- New source migration:
  `workspace.0003_workspace_lifecycle_and_period`, dependent only on applied
  `workspace.0002_profile_workspace_foundation`.
- It additively adds `Profile.status`, `Workspace.period`, `Workspace.status`,
  and `WorkspaceMember.is_active`, their status/period checks, uniqueness, and
  lookup indexes. It does not edit `0001`/`0002`, delete a row, invent a tenant,
  or guess a monthly period.
- Existing rows gain `ACTIVE` status and active membership defaults. Existing
  pre-`0003` Workspaces retain `period=NULL` until an explicit verified mapping.
  `NULL` is a transitional direct-write boundary only: model/service/API paths
  reject a new Workspace without a period. Once a non-null period is assigned,
  supported model/API paths do not permit changing it.
- MigrationExecutor rehearsal from `0002` to `0003` on isolated PostgreSQL
  preserved Profile, Workspace, WorkspaceMember and the related
  `Task → Deliverable → Review` chain without synthesizing a period.

### API implemented in source

- Existing Profile/Workspace reads and Workspace create/update remain intact.
  Create now requires `period`; response objects expose lifecycle fields.
- New Profile actions:
  `POST /api/v1/profiles/{profile_id}/archive/` and `/restore/`.
- New Workspace actions:
  `POST /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/archive/` and
  `/restore/`.
- Nested member detail now accepts `DELETE` for soft revoke (`204`). A later
  collection `POST` reactivates the retained row (`200`); a new row returns
  `201`, while an already-active duplicate remains `409`.
- All unsafe routes retain SessionAuthentication and CSRF enforcement. No new
  `AllowAny`, authentication mechanism, frontend, or downstream domain was
  introduced.

### Verification actually run

- `python -m pip check`: PASS, no broken requirements.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- New lifecycle/concurrency service module: PASS, 7/7 in 6.872s.
- Entire Workspace PostgreSQL suite: PASS, 140/140 in 79.278s.
- Full PostgreSQL suite: PASS, 169/169 in 82.920s, including Authentication,
  Session/CSRF, deny-by-default, health, tenant/IDOR, lifecycle, concurrency,
  atomic audit rollback, last-active-Owner, and migration regressions.
- Django applied `workspace.0003` only inside the disposable `test_postgres`
  database and destroyed it after each run; the post-check found zero remaining
  test database.
- Development `showmigrations` shows `0001`/`0002` applied and `0003` unchecked.
  `migrate --plan` lists only the reviewed additive `0003` operations.
  `migrate --check` exits `1` as expected because `0003` is deliberately
  pending; that expected result is not reported as a failed consistency check.
- `git diff --check`: PASS after final source/documentation reconciliation;
  Git may emit only existing LF-to-CRLF conversion warnings.

### Development and production state

- The identified target remains the repository Compose PostgreSQL 16
  development container. A read-only process check on 2026-10-20 found that
  existing container stopped cleanly (`Exited (0)`); it was not restarted or
  altered in this documentation-only resume. Production was not contacted.
- Development has 27 migration rows: `workspace.0002` is applied and
  `workspace.0003` is not applied.
- Latest successful read-only database inventory, taken immediately after the
  full suite on 2026-10-19: 3 Users and zero Profile, ProfileMembership,
  Workspace, WorkspaceMember, Task, Client, Invoice, Payment, and AuditLog
  rows, with no remaining test database. No tenant, period, membership, or
  business fixture was synthesized.
- **IMPLEMENTED IN SOURCE:** yes.
- **TESTED IN ISOLATED POSTGRESQL:** yes.
- **APPLIED TO DEVELOPMENT:** no.
- **PRODUCTION TOUCHED:** no.

### Files changed in the current worktree

Backend implementation:

- `backend/apps/workspace/access.py`
- `backend/apps/workspace/admin.py`
- `backend/apps/workspace/models.py`
- `backend/apps/workspace/permissions.py`
- `backend/apps/workspace/serializers.py`
- `backend/apps/workspace/services.py`
- `backend/apps/workspace/urls.py`
- `backend/apps/workspace/views.py`
- `backend/apps/workspace/migrations/0003_workspace_lifecycle_and_period.py`

Tests:

- `backend/apps/workspace/test_api.py`
- `backend/apps/workspace/test_write_api.py`
- `backend/apps/workspace/tests.py`
- `backend/apps/workspace/test_schema_lifecycle.py`
- `backend/apps/workspace/test_lifecycle_services.py`

Current-state documentation:

- `documentation/API_DOCUMENTATION.md`
- `documentation/CHANGELOG.md`
- `documentation/DATABASE_SCHEMA.md`
- `documentation/DECISION_LOG.md`
- `documentation/HANDOVER.md`
- `documentation/PROGRESS.md`
- `documentation/PROJECT_CONTEXT.md`
- `documentation/PROJECT_ROADMAP.md`
- `documentation/RBAC_DESIGN.md`
- `documentation/REQUIREMENT_STATUS.md`

No file was reset, reverted, deleted, committed, or pushed.

### Exact safe continuation / review gate

Stop at the **OWNER REVIEW GATE**. Review the source diff, additive `0003`, API
contract, isolated migration rehearsal, 140-test Workspace run, and 169-test
full regression. Do not begin Invitation, Client, Project, Task/Review,
Finance, or frontend work.

If the Owner approves development rollout, open a separately controlled
migration task: repeat development identity/inventory, verify the existing
backup policy (and create a fresh pre-apply backup if required), review
`migrate --plan`, apply exactly `workspace.0003` to development, then verify
constraints, inventory, API smoke, and the full regression suite. Do not apply
it from this checkpoint.

---

## Superseded checkpoint — 2026-10-19 — HT-WORK-P2-02 schema approval gate

Historical only: the schema-free slice and schema approval gate below were
superseded after the Owner approved and Codex implemented the schema-dependent
requirements. Do not follow its continuation instruction as current work.

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `b8f1767`

Current task: `HT-WORK-P2-02 — IN PROGRESS / SCHEMA APPROVAL GATE`

Read root `AGENTS.md` before taking any later action. Preserve every dirty
file, the migrated development database, and the verified HT-DB-P1-05 backup.
Do not commit, push, reset, alter migration history, create/apply a new
migration, write development business fixtures, or begin another roadmap task.

Owner accepted `HT-DB-P1-05` and explicitly opened the limited Workspace Write
API and Membership Management task. The schema-free portion is implemented and
fully verified. The task is not `COMPLETE`, because the remaining lifecycle,
monthly-period, and membership-history requirements need an approved additive
schema and business contract.

### Completed implementation

- `POST /api/v1/profiles/{profile_id}/workspaces/` creates a Workspace for a
  Profile Owner/Admin. Profile and legacy owner fields are server-owned; the
  request cannot impersonate an owner or re-parent the Workspace.
- `PATCH /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/` changes only
  `name` and `description`. Profile Owner/Admin and the assigned Workspace
  Admin may perform this action; Editor/Viewer and an unassigned Profile Member
  are denied.
- `GET`/`POST` on the nested Workspace member collection list the effective
  roster and direct-add an active User who already has an active membership in
  the same Profile. `PATCH` on the nested member detail changes the Workspace
  role.
- Profile Owner/Admin may manage `ADMIN`, `MEMBER` (Editor), and `VIEWER`.
  Workspace Admin may manage only `MEMBER` and `VIEWER`. The legacy Workspace
  `OWNER` role fails closed and cannot be assigned or changed through this API.
- Strict input serializers reject unknown and server-owned fields. Member
  output exposes the ProfileMembership reference and assignment metadata, but
  no global User ID, username, email, or other User PII.
- Tenant path and target resolution remain scoped. The implemented mappings are
  invalid input `400`, insufficient capability `403`, unknown/wrong-parent/
  cross-tenant resource `404`, and duplicate direct-add `409`.
- Create, update, direct-add, and role-update run in locked transactions with
  AuditLog writes in the same transaction. Audit failure rolls the state change
  back.
- The final roster hardening binds the queryset to the requesting actor's
  current Profile/Workspace authority in SQL. It also rechecks that roster
  targets still have an active same-Profile membership. A manager role revoked
  after permission resolution but before lazy queryset evaluation therefore
  fails closed instead of returning a late, stale roster.

### Explicitly blocked remainder

- Workspace archive/restore is not exposed. `Workspace` has no lifecycle field,
  so archive state, default visibility, child-write behavior, restore rules,
  and actor ceiling cannot be implemented without inventing policy.
- The approved architectural description says Workspace is monthly, but the
  current model has no month/period field or approved uniqueness semantics.
- WorkspaceMember revoke/deactivate is not exposed. The model has no active or
  history field, and deactivate/rejoin/history semantics are not approved.
- Profile itself has no active/lifecycle field. Tenant lifecycle behavior must
  be decided before relying on such a state in access enforcement.
- `DELETE` remains `405 Method Not Allowed`; there is no hard-delete shortcut.

No model changed and no migration was created or applied in HT-WORK-P2-02.
Development remains at `workspace.0002_profile_workspace_foundation`; there is
no `workspace.0003`.

### Development database evidence

- Read-only verification identified the existing loopback-bound Compose
  PostgreSQL 16.14 development service. Production was not contacted.
- `django_migrations` contains 27 rows and
  `workspace.0002_profile_workspace_foundation` is applied.
- Inventory remains 3 Users and 0 Profile, ProfileMembership, Workspace,
  WorkspaceMember, Task, Client, Invoice, Payment, and AuditLog rows. No
  business fixture or tenant mapping was created, and the final read-only
  check found no `test_%` database left behind.
- There is no `workspace.0003`. HT-WORK-P2-02 performed no development schema
  or data write.

### Verification actually run

- `python -m pip check`: PASS, no broken requirements.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- `python manage.py migrate --check`: PASS.
- Workspace service/read/write/API tests: PASS, 111/111 in 62.011s.
- Authentication/API Foundation regressions (`api apps.accounts`): PASS,
  29/29 in 7.295s.
- Full PostgreSQL suite: PASS, 140/140 in 69.873s.
- The isolated Django test database was destroyed after each test run.
- `git diff --check`: PASS; Git reports only existing LF-to-CRLF conversion
  warnings for several dirty files.

These results include permissions, tenant and wrong-parent isolation, strict
inputs, duplicate handling, CSRF and anonymous denial, role ceilings,
transaction/audit rollback, existing last-active Profile Owner invariants, and
the late-revocation roster regression. They do not constitute approval for a
new schema or for the blocked endpoints.

### Files changed in the current worktree

HT-WORK-P2-02 backend implementation and tests:

- `backend/apps/workspace/access.py`
- `backend/apps/workspace/permissions.py`
- `backend/apps/workspace/serializers.py`
- `backend/apps/workspace/services.py`
- `backend/apps/workspace/urls.py`
- `backend/apps/workspace/views.py`
- `backend/apps/workspace/test_api.py`
- `backend/apps/workspace/test_write_api.py` (new)
- `backend/apps/workspace/tests.py`

Current-state documentation:

- `documentation/API_DOCUMENTATION.md`
- `documentation/CHANGELOG.md`
- `documentation/DATABASE_SCHEMA.md`
- `documentation/DECISION_LOG.md`
- `documentation/HANDOVER.md`
- `documentation/PROGRESS.md`
- `documentation/PROJECT_CONTEXT.md`
- `documentation/PROJECT_ROADMAP.md`
- `documentation/RBAC_DESIGN.md`
- `documentation/REQUIREMENT_STATUS.md`

The pre-existing `.gitignore` change and ignored HT-DB-P1-05 backup remain
preserved. No file was reset, deleted, committed, or pushed.

### Exact continuation / Owner decision required

Stop at `SCHEMA APPROVAL GATE`. Do not start a new task. Owner must approve the
small additive schema and exact contract for all of the following before any
further implementation:

1. Profile active/lifecycle representation and its access effects.
2. Workspace month/period representation and uniqueness rules.
3. Workspace archive/restore state, default visibility, child-write behavior,
   restore rules, and authorized actors.
4. WorkspaceMember revoke/deactivate representation, history retention,
   rejoin semantics, and authorized actors.

After that approval, the safe next step is a separately reviewed additive
migration/backfill plan and test plan. Do not create or apply that migration to
development from this checkpoint. Invitation, Profile Write API, downstream
business domains, and frontend remain out of scope.

---

## Superseded checkpoint — 2026-10-19 — HT-DB-P1-05

Historical only: HT-DB-P1-05 was accepted by the Owner before HT-WORK-P2-02
opened. Its evidence remains below for traceability, but its continuation
instruction is superseded by the current checkpoint above.

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `b8f1767`

Current task: `HT-DB-P1-05 — COMPLETE / OWNER REVIEW GATE`

Read root `AGENTS.md` before taking any later action. Preserve the verified
backup, development database, and all dirty files. Do not commit, push, reset,
recreate PostgreSQL, create business fixtures, or begin Workspace Write,
Membership, Invitation, or frontend work without separate Owner authorization.

### Resume classification and environment

- `ALREADY DONE` before the final resume: repository/source/config audit,
  development database identity and pre-migration inventory, additive
  migration review, verified pre-migration backup, target-specific migration
  plan, safe development apply, post-migration schema/integrity checks, and
  direct HTTP smoke were complete. None was repeated destructively.
- `IN PROGRESS` at the recovered checkpoint: regression evidence and permanent
  documentation. These are now complete.
- `NOT DONE` by design: development business fixtures and a successful login
  using an existing development account. Development has no Profile/Workspace
  rows and no account credential was requested, reset, or invented; successful
  SessionAuthentication, tenant detail, cross-tenant, and IDOR paths were
  verified in Django's isolated PostgreSQL test database instead.
- `BLOCKED`: none inside HT-DB-P1-05. The task stops at Owner review by scope.
- Root/backend `.env` remains absent and was not required or created. Django
  settings do not auto-load `.env`. Commands used a development-only
  cryptographically random Django key in process memory and the existing
  PostgreSQL container runtime values, passed to disposable Python containers
  without logging or persisting secret values.
- The Owner-reported host PowerShell check returned Python 3.12.5 and a clean
  `pip check`, but the live check from Codex's managed execution context exits
  `103` and reports the referenced base interpreter path unavailable. This
  environment-visibility discrepancy was not treated as a Django/database
  failure and the venv was not modified. The approved cached
  `python:3.12-slim` fallback was used; source was mounted read-only and pinned
  requirements passed `pip check`.

### Development target, backup, and restore rehearsal

- The only target changed was the existing local Compose development service
  `hustlytasker_postgres` (PostgreSQL 16.14), loopback-bound on port 5432,
  database `hustlytasker_db`, named volume `docker_postgres_data`. Compose
  labels point to this repository. Production was not contacted and no
  PostgreSQL container or volume was recreated.
- Before apply: 26 migration rows; `workspace.0001_initial` applied;
  `workspace.0002_profile_workspace_foundation` unapplied; Profile tables and
  `workspace_workspace.profile_id` absent. Inventory was 3 active Users and 0
  Workspace, WorkspaceMember, Task, Client, Invoice, Payment, or AuditLog rows,
  with no checked orphan, unvalidated FK, or tenant mapping to infer.
- Backup artifact (Git ignored):
  `.local_backups/HT-DB-P1-05/hustlytasker_dev_pre_workspace_0002_20261018T185438Z.dump`.
  It is a 66,721-byte PostgreSQL custom archive. SHA-256 is
  `118533290c6179e63d71b7abc7b591c0882012b91c0c0e810c1d27e3965c020e`;
  host/container hashes match. `pg_restore --list` and a complete archive read
  to `/dev/null` passed.
- A full restore rehearsal also passed in a uniquely named isolated temporary
  database: 26 migrations, `workspace.0002` absent, 3 Users, 0 Workspaces, and
  the expected pre-migration schema. The exact rehearsal database was dropped;
  final checks found zero `htdb_p105_restore_%` databases.

### Migration applied and post-checked

- `python manage.py check`: PASS before apply.
- Exact plan for `workspace.0002_profile_workspace_foundation`: create
  `Profile`, create `ProfileMembership`, add nullable `Workspace.profile`, and
  alter `Workspace.owner` to the reviewed protected relationship. It matched
  the unchanged additive source and contained no data backfill or destructive
  operation.
- Applied exactly
  `python manage.py migrate workspace 0002_profile_workspace_foundation --noinput`
  on the development database: PASS (`OK`). No `--fake`, rollback, reset, or
  old-migration edit was used.
- Final state: 27 migration rows and `workspace.0002` applied. Tables
  `workspace_profile` and `workspace_profilemembership`, nullable
  `workspace_workspace.profile_id`, reviewed FKs/check/partial-unique
  constraints, and lookup indexes all exist and validate.
- Post-apply inventory remains 3 Users and zero Profile, ProfileMembership,
  Workspace, WorkspaceMember, Task, Client, Invoice, Payment, or AuditLog rows.
  There are zero unmapped Workspaces, orphan Workspace/Profile references, and
  unvalidated constraints. No tenant/backfill row was synthesized.

### Direct development HTTP smoke

- A disposable Django server started successfully against the migrated
  development database; its source mount was read-only and it was removed
  after the smoke.
- `GET /api/health/`: `200`, body status `ok`, non-cacheable response.
- Anonymous requests to all four `/api/v1/` Profile/Workspace routes: `403`;
  none returned `500`. Anonymous `GET /api/auth/me/`: `403`.
- `GET /api/auth/csrf/`: `200` with CSRF cookie. Invalid login without the
  token: `403`; the same neutral invalid credential request with the token:
  `400`. No token, cookie, password, or secret was recorded.
- `django_session` count was `1` before and after smoke. No development
  Profile/Workspace fixture or account/session data was created.

### Verification actually run

- `python -m pip check`: PASS, no broken requirements.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- `python manage.py migrate --check`: PASS.
- `showmigrations workspace --plan`: `0001` and `0002` both applied.
- Targeted `apps.workspace.test_api`: PASS, 21/21 in 0.692s.
- Authentication/API Foundation (`api apps.accounts`): PASS, 29/29 in 7.200s.
- Full PostgreSQL suite: PASS, 101/101 in 55.762s. Every Django test database
  was destroyed.
- Final read-only database check: migration/data/session counts unchanged from
  the intended post-apply state; zero `test_%` and restore-rehearsal databases.
- `git diff --check`: PASS after documentation reconciliation; Git may report
  only existing LF-to-CRLF conversion warnings.

### Files and artifacts changed

- `.gitignore` — excludes `/.local_backups/`.
- Ignored local backup artifact listed above.
- Current-state documentation: `HANDOVER.md`, `PROGRESS.md`,
  `PROJECT_ROADMAP.md`, `CHANGELOG.md`, `REQUIREMENT_STATUS.md`,
  `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md`, `PROJECT_CONTEXT.md`,
  `DECISION_LOG.md`, and `RBAC_DESIGN.md`.

No backend source, model, migration, API contract, authentication setting, or
business row was changed in HT-DB-P1-05. The only application-database schema
change was the already-reviewed existing `workspace.0002` migration on the
approved development target.

### Exact continuation

Stop at `OWNER REVIEW GATE`. Review the backup/rehearsal, migration state,
direct smoke, 101-test evidence, and documentation diff. The roadmap candidate
after approval is `HT-WORK-P2-02`, but its exact Workspace write/membership
slice must be separately authorized; Invitation remains gated by its account/
email-binding dependency. Do not implement either automatically.

---

## Superseded checkpoint — 2026-10-19 — HT-DB-P1-05 pre-migration blocker

Historical only: every status, blocker, instruction, and continuation step in
this block is superseded by the completed checkpoint above.

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `b8f1767`

Current task: `HT-DB-P1-05 — BLOCKED BEFORE MIGRATION / OWNER ACTION REQUIRED`

Read root `AGENTS.md` before taking action. Preserve the verified backup and
all dirty files. Do not commit, push, reset, recreate PostgreSQL, restore over
development, synthesize a Django secret, or start another roadmap task.

### Checkpoint recovered and verified

- `HT-API-P1-04` is committed at `b8f1767`; the worktree was clean when this
  operational task began. Its four read endpoints and 101-test historical
  evidence were not reimplemented.
- The only PostgreSQL container is the existing repository Compose service
  `hustlytasker_postgres` (`postgres:16`), bound to `127.0.0.1:5432`, with the
  existing `docker_postgres_data` named volume. Compose labels point to
  `D:\da\HustlyTasker\docker\docker-compose.yml`. No container, database, or
  volume was created, replaced, reset, or deleted.
- Read-only SQL identified `hustlytasker_db` owned/used by
  `hustlytasker_user`, PostgreSQL 16.14, database size 9,149,463 bytes. The
  local Compose identity, loopback binding, project path, and named volume are
  the evidence that this is the approved development target; production was
  not contacted.
- `django_migrations` has 26 rows. `workspace.0001_initial` and the swappable
  User dependency are applied; `workspace.0002_profile_workspace_foundation`
  is not applied. `workspace_profile`, `workspace_profilemembership`, and
  `workspace_workspace.profile_id` remain absent.
- Pre-migration inventory: 3 Users, all active; 0 Workspace,
  WorkspaceMember, Task, Client, Invoice, Payment, and AuditLog rows. Profile
  and ProfileMembership counts are `TABLE ABSENT`, not zero. Orphan checks for
  Workspace owner, WorkspaceMember workspace/user, and Task workspace/creator
  returned zero; no unvalidated foreign key or leftover test database exists.
- Static review confirms existing migration `0002` is unchanged and additive:
  it creates Profile/ProfileMembership with approved indexes/constraints,
  adds nullable `Workspace.profile`, and changes `Workspace.owner` to
  `PROTECT`. It contains no `RunPython`, backfill, delete, drop, rename, or
  guessed tenant mapping. With zero Workspace rows, no mapping is required.

### Backup completed and verified

- Relative artifact:
  `.local_backups/HT-DB-P1-05/hustlytasker_dev_pre_workspace_0002_20261018T185438Z.dump`.
  The UTC filename corresponds to 2026-10-19 local time. The directory is now
  excluded by root `.gitignore`; the archive is intentionally not tracked.
- Format: PostgreSQL 16.14 custom archive; size: 66,721 bytes; source database
  metadata: `hustlytasker_db`.
- SHA-256:
  `118533290c6179e63d71b7abc7b591c0882012b91c0c0e810c1d27e3965c020e`.
  Host and container hashes match.
- `pg_restore --list` succeeded and exposed the expected migration, User, and
  Workspace schema/data entries. Streaming the entire archive through
  `pg_restore --file=/dev/null` also exited 0 without connecting to a target
  database. This verifies archive readability, not a restore rehearsal.
- The archive requires a separately created empty target database for any
  future rehearsal. Never restore it over development automatically.

### Blocking condition before plan/apply

- Root/backend `.env` files are absent. Required runtime variables are not
  loaded at Process/User/Machine scope, including a legitimate development
  `DJANGO_SECRET_KEY`; Django settings do not load `.env` automatically.
- The PostgreSQL container holds only its database variables and is not a
  source for the missing Django secret. Extracting or inventing credentials is
  prohibited.
- Host `python`, `python3`, and `py` are unavailable. The old
  `backend/venv` launcher points to a removed Python 3.12.5 installation and
  exits 103. A cached `python:3.12-slim` image exists, but it cannot make an
  unapproved secret/configuration legitimate.
- Therefore `manage.py migrate --plan`, the apply, Django system/migration
  checks, live application smoke, targeted regressions, and the full suite
  were not run in this checkpoint. `workspace.0002` remains unapplied and the
  development schema/data remain unchanged. Historical 101/101 results are
  not relabeled as current-task evidence.

### Verification actually run

- Independent Git/source/migration review and two read-only database
  inventories: PASS. The final inventory used an explicit read-only
  transaction and reconfirmed 3 Users, zero checked business rows, `0002`
  unapplied, and all three target schema objects absent.
- Backup hash comparison, `pg_restore --list`, and full archive read to
  `/dev/null`: PASS.
- `git diff --check`: PASS; Git reports only existing LF-to-CRLF conversion
  warnings. Strict UTF-8/no-BOM/no-NUL validation passes for every changed
  text file.
- Django check, migration consistency command, API smoke, targeted tests,
  Authentication/API regressions, and full PostgreSQL suite: **NOT RUN** due
  to the blocking environment condition above.

### Files and artifacts changed in this checkpoint

- `.gitignore` — ignores `/.local_backups/` so operational dumps cannot be
  committed accidentally.
- `.local_backups/HT-DB-P1-05/...dump` — verified local backup, ignored by Git.
- Current-state documentation: `HANDOVER.md`, `PROGRESS.md`,
  `PROJECT_ROADMAP.md`, `CHANGELOG.md`, `REQUIREMENT_STATUS.md`,
  `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md`, `PROJECT_CONTEXT.md`,
  `DECISION_LOG.md`, and `RBAC_DESIGN.md`.

No backend code, model, migration, authentication setting, API contract, or
database row/schema was changed.

### Exact safe continuation

Owner action is required: restore the legitimate ignored development `.env`
or load the approved development variables into the process, especially the
existing/approved `DJANGO_SECRET_KEY`. Do not paste secrets into chat, source,
logs, or documentation, and do not extract/reset PostgreSQL credentials.

After that configuration is available:

1. Reconfirm `DJANGO_ENVIRONMENT=development`, the same local Compose target,
   migration state, counts, archive presence/hash, and absence of anomalies.
2. Use the existing approved Python-container mechanism without recreating
   PostgreSQL. Run `migrate --plan` for exactly
   `workspace.0002_profile_workspace_foundation` and review the plan.
3. Only if the plan still matches the additive source, apply exactly that
   migration. Do not auto-rollback or use `--fake` if it fails.
4. Verify migration history, new tables/column/indexes/constraints, counts,
   relationships, and migration consistency.
5. Smoke health and anonymous denial directly on development without creating
   business fixtures. Because development has no Profile/Workspace and no
   approved session credentials, verify authenticated/session/CSRF/detail,
   tenant isolation, and IDOR behavior in Django's isolated PostgreSQL test
   database.
6. Run system check, migration drift check, targeted API tests,
   Authentication/API Foundation regressions, the full PostgreSQL suite, and
   `git diff --check`; then update this checkpoint with actual results.

Do not mark `HT-DB-P1-05` complete until every acceptance condition above has
current evidence. Stop at `OWNER REVIEW / CONFIGURATION GATE`; do not begin
Workspace Write, Membership, Invitation, or any other task.

---

## Superseded checkpoint — 2026-10-18 — HT-API-P1-04 (historical only)

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `eb76395`

Current task: `HT-API-P1-04 — COMPLETE / OWNER REVIEW GATE`

Read root `AGENTS.md` before taking action. Source, migrations, Git status and
current test output override historical notes. Do not commit, push, reset,
revert, clean, apply migrations or alter development data without owner
authorization.

### What was already complete before this resumed checkpoint

- `HT-RBAC-P1-03` supplied verified Profile/Workspace access contexts,
  tenant-scoped selectors, capability revalidation and scoped membership
  services. The owner authorized using that foundation for this read API task.
- Before the interruption, the complete P1-04 code and 20 API tests were already
  present. Independent review found a late membership-revocation race; it had
  already been fixed by mapping stale access during queryset evaluation to the
  same generic DRF `404` and adding an exact regression.
- Final code/test verification had already passed. The interrupted work was the
  required documentation and handover reconciliation, which this checkpoint
  completes without rewriting the valid implementation.
- Final documentation review then found that unsupported unsafe methods can be
  rejected by session CSRF before DRF reaches method dispatch. One focused API
  regression was added; the read implementation itself did not change.

### Implementation completed

- Added `/api/v1/` routing for exactly four read-only endpoints:
  - `GET /api/v1/profiles/`
  - `GET /api/v1/profiles/{profile_id}/`
  - `GET /api/v1/profiles/{profile_id}/workspaces/`
  - `GET /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/`
- Added minimal Profile and Workspace read serializers. They expose only the
  identifiers, names/descriptions and timestamps documented in
  `API_DOCUMENTATION.md`; no owner, membership, role, email, or PII is exposed.
- Added explicit DRF tenant permissions for a current active identity, active
  Profile access and effective Workspace read access. SessionAuthentication and
  global deny-by-default remain unchanged; no new `AllowAny` exists.
- Lists and lookups use only `profiles_visible_to()` and
  `workspaces_visible_to()`. Owner/Admin inheritance is same-Profile only;
  ordinary Members require an effective explicit `ADMIN`, `MEMBER` or `VIEWER`
  Workspace role. Legacy `OWNER`, transitional owner, Profile-null rows and
  staff/superuser flags fail closed.
- Malformed, random, cross-tenant, wrong-parent and otherwise out-of-scope IDs
  share `404 {"detail":"Not found."}`. Pagination is page-number based,
  default 20/max 100, with fixed `created_at`/`id` ordering.
- Views support only `GET`, `HEAD` and `OPTIONS` and are non-cacheable. Unsafe
  requests run auth/CSRF and tenant permissions first (`403`/`404` on failure);
  an authorized request with valid CSRF then receives `405` for unsupported
  methods. No branch implements a Profile/Workspace write, membership
  management or Invitation.

No endpoint approved for this read-only task remains missing.

### Files changed in the current worktree

Backend:

- `backend/api/urls.py`
- `backend/api/pagination.py` — new
- `backend/apps/workspace/views.py`
- `backend/apps/workspace/permissions.py` — new
- `backend/apps/workspace/serializers.py` — new
- `backend/apps/workspace/urls.py` — new
- `backend/apps/workspace/test_api.py` — new

Documentation:

- `documentation/API_DOCUMENTATION.md`
- `documentation/CHANGELOG.md`
- `documentation/DATABASE_SCHEMA.md` — runtime status wording only; no schema
  design or migration changed
- `documentation/DECISION_LOG.md` — clarified P1-03/P1-04 chronology only; no
  accepted decision changed
- `documentation/HANDOVER.md`
- `documentation/PROGRESS.md`
- `documentation/PROJECT_CONTEXT.md`
- `documentation/PROJECT_ROADMAP.md`
- `documentation/RBAC_DESIGN.md`
- `documentation/REQUIREMENT_STATUS.md`

No model, migration, settings, authentication, `access.py`, `services.py`,
Docker, dependency or development-data file changed in this task.

### Verification actually run

All Django tests below used Django-created disposable PostgreSQL databases; no
SQLite fallback or development migration was used. At resumed verification the
workspace had no `.env` and its old Windows virtualenv pointed to a removed
Python install, so the final run used the already-cached `python:3.12-slim`
image, installed the pinned manifest inside an ephemeral container, and mounted
the repository read-only. The existing PostgreSQL container was not recreated.
The initial local verification attempt therefore did not start Django tests;
only the successful isolated runs below are reported as test evidence.

- Targeted `apps.workspace.test_api`: PASS, 21/21 in 0.747s, including the new
  session-CSRF-before-`405` case.
- Authentication/API Foundation regression run (`api apps.accounts`): PASS,
  29/29, including existing session and CSRF policy coverage.
- Final full PostgreSQL suite after every code/test change: PASS, 101/101 in
  55.129s. This includes 72 Workspace, 19 Authentication and 10 API Foundation
  tests; Django destroyed the test database.
- `python -m pip check`: PASS.
- In-memory Python syntax compile for all new/modified code and tests: PASS.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- `python manage.py showmigrations workspace --plan`: development state remains
  `0001` applied and `0002` unapplied.
- Read-only PostgreSQL check after tests: zero leftover `test_%` databases.
- `git diff --check`: PASS, with only Git's existing LF-to-CRLF conversion
  warnings. Strict UTF-8/no-BOM/no-NUL, balanced-code-fence,
  trailing-whitespace and secret-assignment QA: PASS for all 17 changed/new
  source and documentation files.
- Independent code and test review found no blocking/high/medium issue. Optional
  non-blocking future assertions are page-size cap/default, explicit no-store
  header, and an additional cross-tenant Workspace-list parity case.

### Migration and data state

- Source still contains the unchanged additive
  `workspace/0002_profile_workspace_foundation.py`.
- Development PostgreSQL still has only `workspace.0001_initial` applied;
  `workspace.0002` is intentionally unapplied and Profile tables are absent.
- Final read-only inventory confirms 3 User rows, 0 Workspace rows, no Profile
  table and no leftover test database. Only the pre-existing PostgreSQL
  container remains running; every Python test container was removed. No
  development row/schema/container/volume was created, modified, deleted,
  reset, backfilled or migrated by P1-04.
- The API implementation is complete and verified on isolated PostgreSQL test
  databases, but cannot be runtime-smoked against development before the
  separately approved `0002` operational rollout.

### Remaining boundaries and exact continuation

- Direct ORM/bulk/raw/Admin bypasses, global User-deactivation/session purge,
  Workspace writes/membership lifecycle, Invitation, and all downstream
  Client/Project/Task/Review/Finance APIs remain outside this task.
- There is no implementation blocker inside the approved P1-04 scope. The
  active gate is Owner review of the API contract, diff and 101-test evidence.
- Do not apply `workspace.0002` automatically. If the owner separately
  authorizes a development rollout, first repeat read-only inventory, take the
  required backup, apply only the existing migration, then smoke all four
  endpoints and record the result.
- Do not begin Workspace write/membership or Invitation work automatically.
  After review and any operational migration approval, the next implementation
  task must be separately scoped; Invitation still depends on account/email
  verification.

Stop at `OWNER REVIEW GATE`.

---

## Superseded checkpoint — 2026-10-18 — HT-RBAC-P1-03 (historical only)

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `5e89971`

Current task: `HT-RBAC-P1-03 — COMPLETE / OWNER REVIEW GATE`

Read root `AGENTS.md` before taking action. Source, migrations, Git status and
current test output override historical notes. Do not commit, push, reset,
revert, clean, apply migrations or alter development data without owner
authorization.

### What was completed

- `HT-RBAC-DESIGN-P0-01` is `COMPLETE / ACCEPTED — APPROVED BY OWNER
  DELEGATION`. `RBAC_DESIGN.md` and `DECISION_LOG.md` record all 14 delegated
  decisions; do not ask the owner to decide them again.
- Added `backend/apps/workspace/access.py`:
  - resolver-produced immutable ID-only Profile/Workspace contexts;
  - active-User and active-ProfileMembership verification;
  - tenant-scoped Profile and Workspace selectors;
  - Profile Owner/Admin same-Profile Workspace inheritance;
  - ordinary Profile Member access only with explicit effective
    WorkspaceMember;
  - DB-revalidated read/edit/member-management capabilities;
  - generic `TenantAccessNotFound` for unknown/out-of-scope/malformed tenant
    identifiers;
  - fail-closed handling for direct construction, `dataclasses.replace()`,
    inactive/stale membership and stale Workspace role.
- Kept the existing WorkspaceMember schema vocabulary:
  - `ADMIN` = Workspace Admin;
  - `MEMBER` = Editor;
  - `VIEWER` = read-only Viewer;
  - legacy `OWNER` grants no capability through this boundary and is never
    assigned by the scoped service.
- Refactored `update_profile_membership()`:
  - signature now requires `profile_id`;
  - actor/Profile authorization precedes target lookup;
  - target is filtered inside the verified Profile;
  - Profile Admin may manage a current ordinary Member only and cannot grant
    or modify Admin/Owner;
  - Profile-first locking, last-active-owner, transitional Workspace-owner
    guard and atomic AuditLog behavior remain.
- Refactored `add_workspace_member()`:
  - signature requires `profile_id`, `workspace_id` and
    `target_profile_membership_id`; it no longer accepts a globally resolved
    User;
  - actor, Workspace, target ProfileMembership and active User are verified in
    the same Profile and rechecked under locks;
  - Profile Owner/Admin may grant `ADMIN`, `MEMBER` or `VIEWER`;
  - Workspace Admin may grant only `MEMBER` or `VIEWER` in its own Workspace;
  - Editor/Viewer cannot manage membership; no actor may grant legacy `OWNER`;
  - sequential/concurrent duplicates raise `WorkspaceMembershipConflict` and
    successful mutation writes exactly one audit event.
- Expanded Workspace tests for contexts, tenant isolation, IDOR-equivalent
  failures, stale/forged contexts, role ceilings, denied-audit behavior,
  last-owner protection and duplicate concurrency.
- Independent review found one medium context-forgery issue involving
  `dataclasses.replace()`. It was fixed with non-init provenance plus exact DB
  revalidation, regression tests were added, and follow-up review found no
  blocking/high/medium issue.

### Files changed in the worktree

Backend:

- `backend/apps/workspace/access.py` — new, untracked until the owner chooses to
  commit.
- `backend/apps/workspace/services.py`
- `backend/apps/workspace/tests.py`

Documentation:

- `documentation/CHANGELOG.md`
- `documentation/DATABASE_SCHEMA.md`
- `documentation/DECISION_LOG.md`
- `documentation/HANDOVER.md`
- `documentation/PROGRESS.md`
- `documentation/PROJECT_CONTEXT.md`
- `documentation/PROJECT_ROADMAP.md`
- `documentation/RBAC_DESIGN.md`
- `documentation/REQUIREMENT_STATUS.md`

`API_DOCUMENTATION.md` is unchanged because no HTTP route or API contract was
added. No model or migration file changed.

### Verification actually run

Environment:

- Existing PostgreSQL 16 container `hustlytasker_postgres`; no container was
  created, replaced, stopped or reset.
- Existing local Python 3.12.5 virtualenv synchronized to pinned Django 6.1.2
  and DRF 3.18.3; no requirement file changed.

Final acceptance evidence after the independent-review fix:

- `python -m pip check`: PASS.
- Version assertion: Django 6.1.2 / DRF 3.18.3: PASS.
- Python compile for access/services/tests: PASS.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- `python manage.py test apps.workspace --noinput -v 1`: PASS, 51/51.
- `python manage.py test --noinput -v 1`: PASS, 80/80. This includes all 19
  Authentication and 10 API Foundation regressions.
- `git diff --check`: PASS (only existing LF-to-CRLF conversion warnings).
- Strict UTF-8/no-NUL/code-fence QA and secret-assignment scan: PASS for all
  changed code/documentation files.

Pre-fix diagnostic runs also passed 49/49 targeted and 78/78 full. They are
historical within this task and are not the final acceptance evidence.

Django created and destroyed only disposable `test_hustlytasker_db` databases.
It did not migrate the development database.

### Migration and data state

- Source still contains additive
  `workspace/0002_profile_workspace_foundation.py`; no migration was created or
  edited by HT-RBAC-P1-03.
- Read-only development PostgreSQL inventory on 2026-10-18 confirmed only
  `workspace.0001_initial` is applied. `workspace.0002` is unapplied.
- Development inventory: 3 User rows; 0 Workspace, WorkspaceMember, Task,
  Client, Invoice, Payment and AuditLog business rows. Profile tables do not
  exist in development because `0002` is unapplied.
- No development row was created, changed, deleted, reset or backfilled. The
  named volume was preserved.

### Security boundaries that still exist

- Direct ORM `.save()`/`.update()`, bulk operations, raw SQL and unsafe Django
  Admin paths can bypass the reviewed membership services. This task does not
  claim database-wide enforcement against privileged code.
- Django Admin remains a platform-operations surface. Tenant-wide business
  model access is for platform superusers only until tenant-scoped Admin exists.
- Direct `User.is_active` changes can bypass cross-Profile last-owner and
  session-revocation requirements. The approved account-deactivation service
  and established-session purge are not implemented.
- No Workspace/Profile API or DRF tenant permission class exists. The new
  exception is a service boundary that a future API must map without revealing
  object existence.
- No Invitation model/migration/service/API exists. Verified email/account
  binding is required before production Invitation; token hashing alone is not
  identity verification.
- No Client, Project, Finance, Audit, Task or Review tenant selector/API was
  added. Concrete Review role/states and the payroll trigger remain deferred.
- WorkspaceMember has no active flag and legacy membership/history semantics
  remain for later lifecycle work. Soft delete is not implemented.

### Blockers and exact continuation

There is no implementation blocker for the completed scope. The active gate is
owner review.

1. Review the three backend files, the delegated decisions and the 51/80-test
   evidence. Do not reopen the 14 accepted decisions unless the owner explicitly
   changes them.
2. Do not apply `workspace.0002` as part of this task. A future operational
   apply requires target-specific inventory, retention-appropriate backup and
   explicit authorization even though current development has no business rows.
3. Do not open Workspace or Invitation APIs in this worktree yet.
4. After owner approval, define a separately authorized next task. The expected
   next implementation slice is minimal Profile/Workspace read/API permission
   integration using this foundation, scheduled with the account-verification
   dependency; Invitation remains later.

Stop at `OWNER REVIEW GATE`. Do not start the next task automatically.

---

## Superseded checkpoint — 2026-10-17 (historical only)

Checkpoint: 2026-10-17

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `5e89971`
Current task: `HT-RBAC-DESIGN-P0-01 — DESIGN READY / OWNER REVIEW GATE`

This historical checkpoint is retained only for traceability. Continue from
the current checkpoint above.
Read root `AGENTS.md` before taking action. Source code, migrations, Git status,
and current test results override any stale historical note.

## 1. Project and stack

HustlyTasker is a backend-first workflow system for content-production teams
and agencies.

- Backend: Python 3.12, Django 6.1.2
- API: Django REST Framework 3.18.3
- Database: PostgreSQL 16
- ORM: Django ORM
- Local database workflow: Docker Compose with named volume
  `docker_postgres_data`
- Authentication foundation: Django server-side sessions, CSRF, DRF
  `SessionAuthentication`
- Default API access: DRF `IsAuthenticated`; public endpoints must explicitly
  use reviewed `AllowAny`
- Frontend: planned React/Next.js, no frontend source implemented

Do not replace this stack, start frontend, or introduce another framework
without explicit owner approval.

## 2. Current implementation status

### Backend implemented

- Modular Django apps for accounts, workspace, tasks, reviews, clients,
  finance, notifications, and audit.
- Fourteen concrete initial domain models and eight domain
  `0001_initial.py` migrations.
- Environment-based Django/PostgreSQL/security/mailer configuration and a safe
  `.env.example`.
- PostgreSQL Compose workflow preserving the named volume.
- Session authentication API:
  `/api/auth/csrf/`, `register/`, `login/`, `logout/`, and `me/`.
- DRF deny-by-default policy and reviewed public allowlist.
- Public JSON-only `/api/health/` liveness endpoint; legacy `/api/test/` is
  removed.
- Accepted Profile/Workspace architecture: Profile is the company/team tenant
  root; Workspace is the monthly operational scope; User remains global.
- `Profile` and `ProfileMembership` foundation with Profile roles, uniqueness,
  indexes, multi-owner/last-owner services and membership audit events.
- Transitional nullable `Workspace.profile`, protected Workspace owner
  deletion, and same-Profile validation for validated Workspace writes.
- Additive `workspace/0002_profile_workspace_foundation.py` in source; it has
  run only on disposable PostgreSQL test databases.
- Reviewable `documentation/RBAC_DESIGN.md` with the proposed capability
  matrix, tenant-scoped request/query/service boundary, Profile Invitation
  contract, planned routes, negative/concurrency tests, open decisions, and
  dependency-ordered implementation plan. It is not runtime behavior.

### Not implemented

- Applying Workspace `0002` to the development database
- Workspace lifecycle/invitation API
- Workspace/Profile RBAC and object-scoped querysets
- Owner approval of the seven residual RBAC groups covering Workspace roles,
  Profile Admin/lifecycle, Task visibility/contributor membership, account/
  membership lifecycle, Invitation identity/operations, and error/operator policy
- Project model/API
- Client/Profile, Workspace-scoped Invoice, public-link and soft-delete schema
  migrations
- Task, Review, Client, Finance, Notification, or Audit business APIs
- Account activation/OTP, password recovery, and logout-all
- Frontend
- Backend container image, production deployment, or CI pipeline

Most business app `views.py` files remain scaffolds. Workspace now has focused
foundation tests, but global DRF authentication still proves identity only; it
does not provide tenant authorization.

## 3. Completed tasks and verification evidence

| Task | Status | Evidence |
|---|---|---|
| HT-OPS-P0-01 dependency synchronization | COMPLETE | Clean Python 3.12 install, `pip check`, Django check, dependency versions verified on 2026-10-13. |
| HT-SEC-P0-02 environment hardening | COMPLETE | Development and production-like checks, fail-fast env cases, migration checks, PostgreSQL smoke on 2026-10-13. |
| HT-AUTH-P0-01 authentication foundation | COMPLETE | 19 authentication/session/CSRF/throttle/admin tests and API smoke passed on 2026-10-14. |
| HT-API-P0-03 DRF/health foundation | COMPLETE | Full suite 29/29 (19 auth + 10 API), checks, migration consistency, runserver health/auth smoke passed on 2026-10-15. The same suite and non-server checks passed again on 2026-10-16. |
| Permanent documentation/handover foundation | COMPLETE | Root `AGENTS.md` and this handover checkpoint created on 2026-10-16. |
| HT-DATA-P2-01 Workspace architecture design | COMPLETE / ACCEPTED | Source/reference audit, alternatives, ownership matrix, invariants and migration plan completed; owner approved all 11 decision groups on 2026-10-16. |
| PROFILE/WORKSPACE SCHEMA FOUNDATION | COMPLETE | Foundation implemented and verified: targeted Workspace tests 32/32 and full PostgreSQL suite 61/61 pass; `pip check`, system check and migration drift check pass. Owner authorized the subsequent design task; `0002` intentionally remains unapplied to development. |
| HT-RBAC-DESIGN-P0-01 capability/scoping/invitation design | DESIGN READY / OWNER REVIEW GATE | Full evidence-labeled design in `RBAC_DESIGN.md`; reconciled against all 11 approved groups (all now `MATCH`); seven residual review groups only; source/migration/database unchanged; current PostgreSQL migration/data state reconfirmed read-only on 2026-10-17. |

Latest foundation verification on 2026-10-17: targeted `apps.workspace` tests
passed 32/32 and the complete PostgreSQL suite passed 61/61. The full run
includes 19 Authentication and 10 API Foundation regression tests. `pip check`,
Django system check, and `makemigrations --check --dry-run` passed. See
`PROGRESS.md` for dated evidence.

For `HT-RBAC-DESIGN-P0-01` on 2026-10-17, the final reconciliation QA passed:
the 11-row table and seven open-group structure are present; all nine affected
files pass strict UTF-8/no-NUL/code-fence and secret-pattern checks; and
`git diff --check` passes with only line-ending conversion warnings. No backend
code changed, so the 32/32 and 61/61 results above were not relabeled as a new
run. The local venv references a missing Python 3.12 installation and no
`py`/`python` exists on PATH; no replacement environment or new container was
created for this design-only checkpoint.

## 4. Active task checkpoint

`HT-RBAC-DESIGN-P0-01` has all requested design deliverables and is
`DESIGN READY — PENDING OWNER APPROVAL`. Stop here; this status is not approval
to implement RBAC, Workspace, Invitation, or another business API.

Work completed:

- Re-read requirements, accepted decisions, current models/services/admin,
  migrations, API routing/settings/tests, and relevant legacy discovery. The
  design marks each rule as requirement, approved, current, proposed, or open.
- Added `documentation/RBAC_DESIGN.md` with a full Profile/Workspace capability
  matrix. It preserves approved Owner/Admin inheritance and ordinary-Member
  explicit Workspace access while treating Workspace Admin/Viewer/Owner action
  semantics as proposals pending approval.
- Reconciled the complete RBAC design against all 11 owner-approved
  architecture groups. The original findings were 1–3/5/10 `MATCH`, group 4 a
  labeling `CONFLICT`, and groups 6–9/11 `NOT DOCUMENTED` in part or whole.
  The conflict was corrected back to “at least one active Owner membership”;
  every missing approved boundary was added. All 11 now read as `MATCH` without
  asking the owner to approve them again.
- Defined a fail-closed per-request Profile context, scoped Workspace and
  child-resource querysets, same-tenant request-body resolution, and proposed
  non-enumerating `404`/`403`/generic `400` behavior.
- Defined service/transaction enforcement, Profile-first lock order, database
  versus service responsibilities, and controls for direct ORM, bulk writes,
  jobs, Django Admin, User deactivation, and platform-operator access.
- Identified a concrete pre-API issue: `update_profile_membership()` globally
  resolves membership ID; `add_workspace_member()` globally resolves Workspace
  ID and accepts an already-resolved unscoped target User before actor scope.
  They have no HTTP route today, but implementation must refactor both
  boundaries before exposure to avoid an IDOR existence oracle.
- Defined the Profile Invitation aggregate, recipient/authority boundary,
  `PENDING` terminal transitions, 256-bit token/hash-at-rest rules, CSRF and
  account binding, duplicate/replay/concurrency behavior, audit events,
  proposed routes, and negative tests. Invitation acceptance never creates a
  Workspace membership automatically.
- Defined dependency order from owner approval through safe `0002` apply,
  access primitives, membership-service refactor, minimal endpoints, future
  additive Invitation migration/API, and later business domains.
- Reconfirmed PostgreSQL through read-only SQL on 2026-10-17: only
  `workspace.0001_initial` is applied; 3 Users and 0 Profile, membership,
  Workspace, Task, Client, Invoice, Payment, or AuditLog business rows;
  `workspace.0002` remains unapplied. Existing Docker/PostgreSQL state was
  returned to stopped; no migration or data write occurred.

Work pending at this checkpoint:

- Owner review/edits of the seven genuinely open groups in
  `RBAC_DESIGN.md`: Workspace role/action ceiling; Profile Admin/lifecycle
  authority; Task visibility/contributor attribution; Profile/account/
  membership lifecycle; Invitation identity/role ceiling; Invitation
  operations/retention; and API error/operator policy.
- Development database migration apply is still a separate operational gate.
  Do not apply `0002` merely because the current inventory has no business rows.
- There is no blocker to reviewing the design. The unresolved owner decisions
  intentionally block implementation, not completion of this review package.

Deliberately not implemented in this design task:

- No access context, queryset selector, permission class, RBAC, or Workspace API.
- No Invitation model/migration/service/API or email delivery flow.
- No Client/Profile, Finance, public-link, AuditLog-tenant or soft-delete schema
  was added.
- No User/authentication mechanism, model, migration, database row, frontend,
  or runtime API contract was changed.

## 5. Current ownership facts and gaps

| Entity | Current source truth | Gap before business API |
|---|---|---|
| User | Global Django identity | Profile access is separate; no auth-model change. |
| Profile | Company/team tenant root exists in source | No soft-delete lifecycle or API. |
| ProfileMembership | Partial unique active Profile/User; inactive history; OWNER/ADMIN/MEMBER | Invitation lifecycle/API absent; aggregate last-owner invariant depends on service use; direct User deactivation/ORM mutation can bypass it. |
| Workspace | Nullable protected Profile FK plus transitional protected owner User | Development migration unapplied; FK remains nullable for safe legacy transition; old Workspace role/owner representation remains. |
| WorkspaceMember | Unique Workspace/User with OWNER/ADMIN/MEMBER/VIEWER; persistence validation plus audited direct-add service | No invitation lifecycle/API; bulk/raw writes remain outside the service boundary; inactive Profile membership does not erase historical WorkspaceMember rows. |
| Task | Required Workspace and creator User | Creator/member relationship is not enforced. |
| Assignment/Comment | Derive Workspace through Task | Actor membership is not enforced. |
| Deliverable/Review | Derive Workspace through Task | Uploader/reviewer membership is not enforced. |
| Client | No tenant FK | Cannot be safely tenant-filtered. |
| ShareLink | Client only; raw unique token | Client is global; no hash/revoke/capability/creator contract. |
| Invoice/Payment | Current schema still derives through global Client | Approved target is Invoice→Workspace plus same-Profile Client, but migration is not implemented. |
| Notification | User recipient | No structured tenant/resource context. |
| AuditLog | Optional User + generic entity ID | No reliable tenant path or target integrity. |

There is no current Workspace/business API, so the new foundation does not
claim complete tenant authorization. Django Admin currently uses global model
querysets and must be treated as a platform-operations surface, not a tenant
admin UI.

## 6. Accepted architecture decisions

The following are accepted and implemented:

- Modular Django architecture under `backend/apps/`.
- PostgreSQL with the existing Docker workflow.
- Django server-side session authentication for the current same-origin API.
- DRF session authentication plus global `IsAuthenticated` deny-by-default.
- Explicit reviewed `AllowAny` for health, CSRF bootstrap, registration, and
  login only.
- `/api/health/` is process liveness, not database readiness.

The owner also accepted these tenancy/business boundaries on 2026-10-16:

- Profile represents a company/team and is the tenant root; Workspace is its
  monthly operational scope.
- User may join multiple Profiles. Switching selected Profile is navigation,
  not authorization.
- Profile roles are OWNER/ADMIN/MEMBER. Profile Owner/Admin administer all
  Workspaces in that Profile; ordinary Members need explicit Workspace access;
  nothing is inherited across Profiles.
- Profiles support multiple equal Owners and always retain at least one active
  Owner; Owner changes are transactional and Admin cannot change Owners.
- Joining Profile requires invitation acceptance. Direct Workspace add is
  allowed only for an already-active Profile member; material changes are
  audited and active memberships do not duplicate.
- Client belongs to Profile; a Client has Projects; a Project may span monthly
  Workspaces through Tasks. Task remains in one Workspace and all referenced
  Client/Project/Workspace records must share one Profile.
- Invoice belongs to one Workspace and same-Profile Client; Payment belongs to
  Invoice. Numbering and detailed billing are deferred.
- Client Portal supports account and secure-link access; its link and Guest
  Review link are separate hashed, scoped, expiring and revocable principals.
  Client accounts receive no internal membership automatically.
- Soft delete is the target default for Profile, Workspace, Client, Project
  and Task; hard delete is controlled, finance/audit history is protected, and
  User departure does not cascade-delete business data. Retention duration and
  purge remain deferred.
- Migration requires inventory, no guessed mapping, backup/rehearsal for risky
  data, and new migrations only.
- High-level Task workflow is assignment → work → Deliverable → Review →
  approval/completion or revision/resubmission. Task completes only after its
  Deliverable is approved. Exact states, approvers and payroll trigger are
  deferred.

## 7. Approved target and remaining decisions

Accepted target:

```text
User (global identity)
  ↕ ProfileMembership
Profile / Organization (tenant root)
  ├─ Workspace (operational/monthly scope)
  │    └─ Task → Deliverable/Review
  ├─ Client / CRM → Project (may span monthly Workspaces through Tasks)
  ├─ Workspace → Invoice → Payment (Client must share Profile)
  └─ tenant AuditLog
```

Client Portal and Guest Review remain separate principals/link aggregates and
are not Workspace roles.

Still requires later task decisions:

RBAC owner-review gate (seven groups):

1. Workspace role vocabulary and action ceiling.
2. Profile Admin and Profile/Workspace lifecycle authority.
3. Task visibility and contributor-membership requirement.
4. Profile/account/membership lifecycle, including self-service eligibility,
   leave/rejoin, history, and account/session mechanics. Initial-Owner creation
   already exists and is not pending re-approval.
5. Invitation identity, onboarding, grant/management role ceiling, including
   whether invitations can ever request `OWNER` (proposal: no).
6. Invitation TTL/reinvite/throttle/delivery, inviter revalidation, optional
   combined UX that preserves the two fixed transitions, and record retention.
7. Non-enumerating error/`409` and platform-operator/Django Admin policy.

Separate downstream decisions: Invoice numbering/billing; Client Portal/Guest
Review exact capabilities/account linking/default expiry; retention/legal hold/
purge; and exact Task/Review states, approvers, and payroll trigger. An unknown
tenant mapping becomes a target-environment blocker only when inventory finds
such a row; the approved policy is already to never guess it.

Detailed proposal and owner-review checklist: `documentation/RBAC_DESIGN.md`.
Accepted rationale and proposal status: `documentation/DECISION_LOG.md`.

Current source/development state versus accepted target:
`documentation/DATABASE_SCHEMA.md`.

## 8. Git and uncommitted work to preserve

Repository evidence on 2026-10-17:

- Branch, `HEAD`, and local `origin/main` are `main` / `5e89971`. That existing
  owner commit contains the previously completed environment, authentication,
  API, schema-foundation, and initial RBAC-design work.
- This reconciliation did not commit, push, reset, rewrite history, edit
  backend source, or touch the database.
- `git status --short --untracked-files=all` currently reports exactly nine
  modified tracked documentation files and no untracked files:
  `CHANGELOG.md`, `DATABASE_SCHEMA.md`, `DECISION_LOG.md`, `HANDOVER.md`,
  `PROGRESS.md`, `PROJECT_CONTEXT.md`, `PROJECT_ROADMAP.md`, `RBAC_DESIGN.md`,
  and `REQUIREMENT_STATUS.md` under `documentation/`.
- `API_DOCUMENTATION.md` is unchanged because no runtime API contract changed.

Preserve all nine documentation changes. Before any future edit, rerun
`git status --short --untracked-files=all`; do not use reset/checkout/clean to
make the tree appear clean.

## 9. Environment setup and test commands

The complete Windows/PowerShell onboarding flow is in root `README.md`.

At this checkpoint on 2026-10-17, the development database was queried read-only and
contained 0 business rows and 3 User rows. The named volume was preserved.
Migration `workspace.0002_profile_workspace_foundation` was applied only in
disposable Django test databases and not in development. Future sessions must
inspect Docker and migration state rather than assume either is unchanged.

1. Copy `.env.example` to the ignored `.env` and fill only local values. Never
   paste real values into documentation or Git.
2. Load `.env` into the current PowerShell process using the validated loader
   block in `README.md`.
3. Start PostgreSQL without replacing its named volume:

   ```powershell
   docker compose --env-file .env -f docker/docker-compose.yml config --quiet
   docker compose --env-file .env -f docker/docker-compose.yml up -d postgres
   ```

4. Create/activate a fresh Python 3.12 virtual environment if the existing
   local venv is broken, then install:

   ```powershell
   py -3.12 -m venv backend/venv
   .\backend\venv\Scripts\Activate.ps1
   python -m pip install -r backend/requirements.txt
   ```

5. With environment variables loaded:

   ```powershell
   Set-Location backend
   python -m pip check
   python manage.py check
   python manage.py makemigrations --check --dry-run
   python manage.py test -v 2
   ```

`migrate --check` is expected to report the unapplied Workspace `0002` until an
approved development apply occurs. Do not run `migrate` against an unknown
database, reset the named volume, or reuse production credentials for tests.
Django tests must use a disposable test database.

## 10. Exact safe continuation

Current review gate: `HT-RBAC-DESIGN-P0-01` deliverables are ready. Stop before
Workspace API/RBAC/Invitation implementation until the owner approves or edits
the proposal in `RBAC_DESIGN.md`.

1. Owner reviews only the seven open decision groups in `RBAC_DESIGN.md`. Do
   not request re-approval of the reconciled 11 architecture groups; all now
   match the authoritative accepted decision.
2. Record accepted answers in `DECISION_LOG.md`; proposals remain proposals
   until then. Do not silently select defaults from legacy reference material.
3. If implementation is authorized, repeat Git/source/database inventory.
   Treat the prior 32/32 targeted and 61/61 full PostgreSQL runs as historical
   evidence and rerun checks after any source change.
4. Apply `workspace.0002` only as a separately approved operational step after
   target-specific inventory and backup policy. Preserve nullable legacy rows
   and never synthesize a Profile for unknown data.
5. Proposed first implementation slice of existing `HT-RBAC-P1-03` after
   approval: Tenant Access Context and Scoped Service Foundation. Implement
   scoped selectors/error mapping, refactor the two unsafe membership service
   boundaries, and add IDOR/concurrency tests before opening broad Workspace
   CRUD. Invitation schema/API follows only after its open decisions.

Do not implement Workspace API/RBAC, Invitation, Project/Client/Finance
migration, public-link flows, soft delete, Task workflow, or frontend in this
task. Do not commit, push, reset, rewrite history, or migrate development.
