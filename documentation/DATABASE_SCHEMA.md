# DATABASE_SCHEMA.md

# HustlyTasker Database Design

Version: 0.5

Status:

Profile/Workspace lifecycle and monthly-period foundation implemented and
verified; `workspace.0003` is applied to the approved development PostgreSQL
database. Task/Deliverable/internal Review workflow hardening is implemented
in source through additive `tasks.0002` and `reviews.0002`, verified by the
final 202-test PostgreSQL gate, and not yet applied to development. Remaining
tenant domains are approved targets not yet implemented.

Initial schema implementation phase (historical):

PHASE 1.8 - Django Models and Migration

Accuracy note:

Sections 1-12 are the historical/conceptual initial design and use logical
table labels such as `users` or `workspaces`. The implemented models do not set
`Meta.db_table`; actual PostgreSQL table names follow Django defaults, for
example `accounts_user`, `workspace_workspace`,
`workspace_workspacemember`, `tasks_task`, and corresponding
`<app_label>_<model_name>` names. Active models and migrations are
authoritative. Sections 13-14 distinguish source/development migration state
from the accepted but not-yet-implemented tenant-domain target.


---

# 1. Database Overview


## Database Technology

PostgreSQL


## ORM

Django ORM


## Primary Key Strategy

All main entities use:

UUID


## Common Fields

All business tables should inherit:

BaseModel


Common fields:

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| created_at | timestamp | Creation time |
| updated_at | timestamp | Last update time |



---

# 2. Accounts Domain


Application:

apps/accounts


## User


Purpose:

Store system users.


Table:

users


Fields:


| Field | Type | Constraint | Description |
|-|-|-|-|
| id | UUID | PK | User identifier |
| email | varchar | Unique | Login email |
| username | varchar | Unique | Required public username inherited from Django `AbstractUser` |
| password | varchar | Required | Hashed password |
| first_name | varchar | Optional | First name |
| last_name | varchar | Optional | Last name |
| is_active | boolean | Default true | Account status |
| is_staff | boolean | Default false | Admin permission |
| created_at | timestamp | | Creation time |
| updated_at | timestamp | | Update time |


Relationships:


User 1 --- N Workspace (Owner)


User N --- N Workspace

through WorkspaceMember


User N --- N Task

through TaskAssignment



---

# 3. Workspace Domain


Application:

apps/workspace



# Workspace


Purpose:

Represent a working environment/team/project space.


Table:

workspaces


Fields:


| Field | Type | Constraint |
|-|-|-|
| id | UUID | PK |
| name | varchar | Required |
| description | text | Optional |
| owner_id | FK User | Required |
| created_at | timestamp | |
| updated_at | timestamp | |



Relationships:


User 1 --- N Workspace


Workspace 1 --- N WorkspaceMember


Workspace 1 --- N Task



---


# WorkspaceMember


Purpose:

Manage users belonging to workspace.


Table:

workspace_members


Fields:


| Field | Type | Constraint |
|-|-|-|
| id | UUID | PK |
| workspace_id | FK | Required |
| user_id | FK | Required |
| role | enum | Required |
| joined_at | timestamp | |



Role:


OWNER

ADMIN

MEMBER

VIEWER



Relationships:


User N --- N Workspace


through WorkspaceMember



---

# 4. Task Domain


Application:

apps/tasks



# Task


Purpose:

Store work items.


Table:

tasks


Fields:


| Field | Type | Constraint |
|-|-|-|
| id | UUID | PK |
| workspace_id | FK | Required |
| title | varchar | Required |
| description | text | Optional |
| status | enum | Required |
| priority | enum | Required |
| deadline | datetime | Optional |
| created_by | FK User (`PROTECT`) | Required |
| created_at | timestamp | |
| updated_at | timestamp | |



Status:


PENDING

ASSIGNED

WORKING

REVIEW

COMPLETED

CANCELLED



Priority:


LOW

MEDIUM

HIGH

URGENT



Relationships:


Workspace 1 --- N Task


Task N --- N User

through TaskAssignment

Current source constraints/indexes (`tasks.0002`, pending development apply):

- `task_valid_status` limits stored status to the six values above.
- `task_valid_priority` limits priority to the four values above.
- `task_ws_status_created_idx` supports scoped status/history reads.
- Supported services derive Workspace/Profile from the nested authorized path;
  a Task cannot be moved to another Workspace/Profile.
- Task completion is service-controlled and occurs only after approval of the
  latest submitted Deliverable. `CANCELLED` remains a storage choice without a
  public transition in this slice.



---


# TaskAssignment


Purpose:

Store task members.


Table:

task_assignments


Fields:


| Field | Type |
|-|-|
| id | UUID |
| task_id | FK |
| user_id | FK (`PROTECT`) |
| is_active | boolean; default true for new rows |
| assigned_at | timestamp |



Relationships:


Task N --- N User

Current source behavior (`tasks.0002`, pending development apply):

- At most one assignment per `(task, user)` remains from the initial schema.
- Partial unique constraint `uniq_active_task_assignment` permits at most one
  current active assignment for a Task.
- Migration adds `is_active` as false for every legacy row before changing the
  model default to true. It deliberately does not guess which legacy assignee
  is current.
- `task_active_assigned_idx` supports current-assignment lookup and history.



---


# TaskComment


Purpose:

Store discussion inside task.


Table:

task_comments


Fields:


| Field | Type |
|-|-|
| id | UUID |
| task_id | FK |
| user_id | FK (`PROTECT`) |
| content | text |
| created_at | timestamp |



Relationships:


Task 1 --- N Comment



---

# 5. Review Domain


Application:

apps/reviews



# Deliverable


Purpose:

Store submitted files/results.


Table:

deliverables


Fields:


| Field | Type |
|-|-|
| id | UUID |
| task_id | FK |
| file_url | varchar |
| uploaded_by | FK User (`PROTECT`) |
| revision | positive integer, nullable only for legacy/unmapped rows |
| status | enum |
| created_at | timestamp |
| updated_at | timestamp |



Status:


PENDING

SUBMITTED

APPROVED

REJECTED



Relationships:


Task 1 --- N Deliverable

Current source constraints/indexes (`reviews.0002`, pending development apply):

- `deliverable_valid_status` restricts status to the values above.
- `deliverable_revision_positive` permits `NULL` legacy revisions or values
  greater than or equal to 1.
- `uniq_task_deliv_revision` makes every non-null `(task, revision)` unique.
- `deliv_task_status_created_idx` supports revision/status history reads.
- Supported submissions allocate revisions sequentially under a Task lock;
  migration never invents revisions for existing rows.



---


# Review


Table:

reviews


Fields:


| Field | Type |
|-|-|
| id | UUID |
| deliverable_id | FK |
| reviewer_id | FK User (`PROTECT`) |
| status | enum |
| comment | text |
| created_at | timestamp |



Status:


PENDING

APPROVED

REQUEST_CHANGE



Relationships:


Deliverable 1 --- 0..1 Review

Current source constraints (`reviews.0002`, pending development apply):

- `review_valid_status` restricts status to the values above.
- `uniq_deliverable_review` enforces one internal Review record per
  Deliverable.
- The workflow service rejects self-review, stale/non-latest revision review,
  repeat review, and review outside the Task's active tenant scope.



---

# 6. Client Domain


Application:

apps/clients



# Client


Purpose:

Store external customers.


Table:

clients


Fields:


| Field | Type |
|-|-|
| id | UUID |
| name | varchar |
| email | varchar |
| company | varchar |
| phone | varchar |
| created_at | timestamp |
| updated_at | timestamp |



Relationships:


Client 1 --- N Invoice



---


# ShareLink


Purpose:

Allow external access.


Table:

share_links


Fields:


| Field | Type |
|-|-|
| id | UUID |
| client_id | FK |
| token | varchar |
| expired_at | timestamp |
| created_at | timestamp |



---

# 7. Finance Domain


Application:

apps/finance



# Invoice


Purpose:

Store billing information.


Table:

invoices


Fields:


| Field | Type |
|-|-|
| id | UUID |
| client_id | FK |
| invoice_number | varchar |
| amount | decimal |
| status | enum |
| due_date | date |
| paid_at | timestamp |
| created_at | timestamp |



Status:


DRAFT

SENT

PAID

OVERDUE

CANCELLED



Relationships:


Client 1 --- N Invoice


Invoice 1 --- N Payment



---


# Payment


Table:

payments


Fields:


| Field | Type |
|-|-|
| id | UUID |
| invoice_id | FK |
| amount | decimal |
| payment_method | varchar |
| paid_at | timestamp |



---

# 8. Notification Domain


Application:

apps/notifications



# Notification


Table:

notifications


Fields:


| Field | Type |
|-|-|
| id | UUID |
| user_id | FK |
| title | varchar |
| message | text |
| is_read | boolean |
| created_at | timestamp |



Relationships:


User 1 --- N Notification



---

# 9. Audit Log Domain


Purpose:

Track important system activities.


Table:

audit_logs


Fields:


| Field | Type |
|-|-|
| id | UUID |
| user_id | FK |
| action | varchar |
| entity_name | varchar |
| entity_id | UUID |
| metadata | JSON |
| created_at | timestamp |



Example:


User updated Task status

User deleted Workspace member



---

# 10. Entity Relationship Overview


User

|

| N:N

|

WorkspaceMember

|

|

Workspace


Workspace

|

| 1:N

|

Task


Task

|

| 1:N

|

Deliverable


Deliverable

|

| 1:N

|

Review



Task

|

| N:N

|

User

through TaskAssignment



Client

|

| 1:N

|

Invoice

|

| 1:N

|

Payment



---

# 11. Database Constraints


## Unique Constraints


User.email unique


Invoice.invoice_number unique


ShareLink.token unique



## Index Strategy


Create indexes for:


- User email
- Task status
- Task deadline
- Workspace owner
- Notification unread status


---

# 12. Future Extension


Possible future modules:


- Calendar
- Chat
- Analytics Dashboard
- Automation Workflow
- AI Assistant


Historical note: the initial schema above was reviewed before the current
Django models were created. It does not describe the accepted tenancy
foundation and remaining gaps in sections 13-14.

---

# Initial Schema Implementation Status (Historical Baseline)

The initial schema represented by the models listed below has been implemented
using Django ORM. Section 14 records the later Profile/Workspace foundation
and clearly separates it from approved target domains not yet implemented.

Completed:

- Custom User Model
- Workspace Models
- Task Models
- Review Models
- Client Models
- Finance Models
- Notification Models
- Audit Models

Migration status:

Initial migrations completed successfully.

Database:

PostgreSQL


---

# 13. Current Ownership Audit — verified 2026-10-21

This section describes the active Django source. The original sections above
document the initial schema; their “future” indexes or relationships must not
be treated as implemented unless they also exist in models/migrations.

| Entity | Current ownership path | Verified gap |
|---|---|---|
| User | Global identity | Profile access now uses separate ProfileMembership; User remains unchanged. |
| Profile/ProfileMembership | Tenant root + User membership | Profile now has an `ACTIVE`/`ARCHIVED` lifecycle in source; Invitation and general Profile CRUD remain absent. |
| Workspace | `profile → Profile` plus transitional `owner → User` | Profile FK remains nullable for safe transition; supported new writes require a canonical non-null monthly period, while schema nullability preserves unresolved legacy rows. Lifecycle state is implemented in source, and owner remains a transitional second ownership representation. |
| WorkspaceMember | `workspace + user` | One historical row per pair is retained; `is_active` distinguishes effective assignment from soft revocation, and validated activation requires active membership in the Workspace Profile. |
| Task | `workspace → Workspace → Profile` | Supported create/update/assignment transitions enforce an active tenant and manager capability; the creator is retained with `PROTECT`. Direct ORM/bulk writes remain outside that guarantee. |
| TaskAssignment/TaskComment | `task → workspace → profile` | Supported assignment targets an active ordinary Profile Member with effective Workspace Editor access and retains one active assignee. TaskComment has no public workflow API yet. |
| Deliverable/Review | `task → workspace → profile` | Supported submit/review paths enforce current assignee or internal manager capability, prevent self-review, and retain actor references with `PROTECT`; Client/Guest review is separate and absent. |
| Client | None | Global row cannot be tenant-filtered safely. |
| ShareLink | `client`, but Client is global | Raw token, no tenant, creator, capabilities, revoke state, or token hash. |
| Invoice/Payment | `invoice → client`, but Client is global | No tenant boundary; invoice number is globally unique. |
| Notification | Recipient User | No structured Profile/Workspace context. |
| AuditLog | Optional User + generic entity ID | No reliable tenant path or enforced target reference. |

The schema foundation adds explicit ProfileMembership uniqueness and role
checks, membership lookup indexes, Workspace/Profile model validation, and
transactional membership services. `HT-RBAC-P1-03` now adds Profile/Workspace
scoped selectors and verified access contexts without a schema change.
`HT-API-P1-04` adds four read-only DRF endpoints and tenant permissions, also
without a schema change. `HT-WORK-P2-02` now includes the original Workspace
create/metadata-update and member-manager slice plus the approved
schema-dependent monthly-period, archive/restore, soft-revoke, and reactivation
behavior. `HT-TASK-P2-03` now adds the scoped Task/Deliverable/internal Review
service/API boundary and additive schema hardening described below. Cross-domain
Client/Project constraints, external review, Task soft delete, and the broader
retention/purge policy are not implemented.

Five non-Workspace domain apps remain at their existing `0001_initial.py`
migrations. Tasks and Reviews now also have additive source migrations
`0002_task_workflow_foundation` and `0002_review_workflow_foundation`, while
development remains at their `0001` state. The additive
`workspace/0002_profile_workspace_foundation.py` exists unchanged in source,
has run on disposable PostgreSQL test databases, and was applied to the
approved development database on 2026-10-19 after inventory, backup, restore
rehearsal, and plan review. This does not imply rollout to another environment.


---

# 14. Approved Tenancy Architecture and Foundation Status

Architecture status: `ACCEPTED — 2026-10-16`

Foundation `workspace.0002` status:
`COMPLETE IN SOURCE; APPLIED TO DEVELOPMENT ON 2026-10-19`

RBAC/Invitation design status:
`COMPLETE / ACCEPTED BY OWNER DELEGATION; INVITATION SCHEMA NOT IMPLEMENTED`

Tenant access/service status:
`HT-RBAC-P1-03 COMPLETE; NO MODEL OR MIGRATION CHANGE`

Workspace API status:
`HT-WORK-P2-02 COMPLETE; DEVELOPMENT ROLLOUT VERIFIED BY HT-DB-P1-06`

Task workflow status:
`HT-TASK-P2-03 IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`

The authoritative decisions and remaining detailed questions are in
`documentation/DECISION_LOG.md`. This section distinguishes current schema
from later approved target work.

## Aggregate target

```text
User (global identity)
  └─ ProfileMembership ── Profile (company/team tenant root)
                           ├─ Workspace (monthly operational scope)
                           │    ├─ WorkspaceMember
                           │    ├─ Task → Assignment / Comment
                           │    │         └─ Deliverable → Review
                           │    └─ Invoice → Payment
                           ├─ Client
                           │    ├─ Project ── Task references across Workspaces
                           │    └─ ClientPortalLink / account access
                           ├─ GuestReviewLink (separate credential aggregate)
                           └─ tenant AuditLog
```

Task remains owned by one Workspace. If a Task references Client or Project,
all three objects must resolve to the same Profile. A Project may span several
monthly Workspaces. Invoice belongs to one Workspace and references a Client
from the same Profile; Payment belongs to Invoice.

## Implemented now in source

| Model/change | Current implementation |
|---|---|
| `Profile` | UUID/timestamps inherited from `BaseModel`; required `name`; `status` constrained to `ACTIVE`/`ARCHIVED`, default `ACTIVE`, with a status index. Represents the company/team tenant root. |
| `ProfileMembership` | Protected Profile and User FKs; `OWNER`, `ADMIN`, `MEMBER`; `is_active`; `joined_at`; inactive history is permitted but only one active row may exist per `(profile, user)`. |
| Membership constraints | Partial unique `uniq_active_profile_user`, role check `profmem_valid_role`; indexes `profmem_user_active_idx` and `profmem_prof_active_role_idx`. |
| `Workspace.profile` | Transitional nullable protected FK. New saves require Profile; a mapped Workspace cannot be re-parented through model/admin writes; an explicit null-to-Profile mapping validates the owner and every existing Workspace member. Mapped saves lock Profile then Workspace; existing legacy null saves lock their Workspace row before validation, preventing concurrent mapping/re-parent and stale null write-back races. Null remains allowed at database level so unknown legacy rows are preserved without guessed backfill. |
| `Workspace.period` | Nullable date for migration compatibility; supported creation requires the first day of a month. A DB check permits only null or day 1, and a conditional unique constraint allows at most one non-null `(profile, period)` across active and archived rows. A non-null period is immutable through supported model/service/API paths. Null is reserved for unresolved legacy rows and is never guessed. |
| `Workspace.status` | Constrained `ACTIVE`/`ARCHIVED`, default `ACTIVE`; indexed together with Profile and period. Archived rows remain scoped/readable and continue to reserve their monthly period. |
| `Workspace.owner` | Existing transitional FK retained; deletion changed from `CASCADE` to `PROTECT`. Validated writes require that owner to be an active Profile Owner or Admin. |
| `WorkspaceMember` lifecycle/validation | `is_active` defaults true. Existing one-row-per-Workspace/User uniqueness is retained so revoke/reactivate reuse the same row. An active row validates active same-Profile membership and account; an inactive historical row remains preservable. The `(workspace, is_active, role)` index supports effective-roster lookup, and Django Admin membership mutation remains read-only. |
| Foundation services | Create Profile plus initial active Owner atomically; tenant-scope Profile membership updates before target lookup; lock Profile during role/active changes; support multiple Owners; block removal/demotion of the last usable active Owner; restrict Profile Admin to current ordinary Members; directly add only an active same-Profile member with Profile/Workspace role ceilings; translate duplicate adds to a stable conflict; write membership AuditLog events atomically. |
| Access contexts/selectors (no schema change) | Resolver-produced immutable Profile/Workspace contexts require active User and ProfileMembership; Profile/Workspace selectors fail closed across tenants; capability checks revalidate current role and reject forged/stale contexts. Existing WorkspaceMember values map `ADMIN` to Workspace Admin, `MEMBER` to Editor and `VIEWER` to read-only Viewer; legacy `OWNER` grants no capability and cannot be assigned by the service. |
| Profile lifecycle service/API | Profile Owner alone may archive/restore the Profile. Profile Admin cannot. Transitions are locked, idempotent, audited atomically, keep rows tenant-scoped/readable, and block normal child/membership writes while archived. Hard delete is not exposed. |
| Workspace write/lifecycle services/API | Profile Owner/Admin create a Workspace for a required canonical period; Profile Owner/Admin and assigned Workspace Admin may update only `name`/`description` while active. Profile Owner/Admin may archive/restore a Workspace; Workspace Admin cannot. Lifecycle is locked, idempotent, audited, readable while archived, and blocks normal metadata/member mutations. Profile, transitional owner, period, and status cannot be mass-assigned or re-parented by update input. |
| Workspace-member manager API | Profile Owner/Admin and assigned Workspace Admin may list effective assignments, direct-add or reactivate an active same-Profile member, update a supported role, and soft-revoke within their role ceiling. Revocation immediately removes effective access but retains the row; reactivation reuses it. The roster query retains actor authority in SQL, excludes inactive/legacy/ineffective assignments, emits no User PII, and mutations revalidate under locks with atomic audit. |
| Task/assignment workflow | Task remains owned by exactly one Workspace and cannot be re-parented through supported APIs. Profile Owner/Admin or Workspace Admin create/update/assign. One active assignment is enforced; eligible targets are active Profile Members with effective Workspace `MEMBER` (Editor) access. The assigned Editor alone may start. Status/priority checks and scoped lookup index are provided by `tasks.0002`. |
| Deliverable/internal Review workflow | The assigned Editor submits a URL-based, sequential positive revision from `WORKING`; Task enters `REVIEW`. A different Profile Owner/Admin or Workspace Admin may approve the latest submitted revision (Task becomes `COMPLETED`) or request changes (Task returns to `WORKING`). One Review per Deliverable, no self-review, stale/repeat protection, atomic audit, and status/revision constraints are provided. Client/Guest approval and Payroll/Payment are not coupled to this internal decision. |
| Workflow actor retention/Admin boundary | Task creator, assignee, commenter, uploader, and reviewer FKs use `PROTECT`. Task/Assignment/Comment Admin is inspection-only, and Workspace Admin hard delete is disabled to avoid the existing aggregate CASCADE path. Task soft-delete fields/services and a full retention/purge mechanism remain unimplemented. |

`Workspace.save()` and `WorkspaceMember.save()` call `full_clean()`, but bulk
updates, raw SQL, and direct ORM mutations can bypass service invariants.
In particular, database nullability intentionally preserves unresolved legacy
`Workspace.period` rows; raw/bulk/direct paths can still write null and are not
supported creation paths. Direct User deactivation can also make an Owner
account unusable without going through the owner service.
Profile/ProfileMembership are not exposed in Admin; lifecycle state and mapped
period fields are read-only in Workspace Admin as applicable; WorkspaceMember
Admin is read-only. Supported lifecycle, metadata, and membership mutations use
reviewed services. The DRF layer uses scoped access contexts/selectors, but
this remains neither a complete cross-domain authorization layer nor a
database-wide guarantee of the aggregate last-owner invariant.

## Migration and inventory evidence

- Additive migrations:
  `workspace/0002_profile_workspace_foundation.py` and, in current source,
  `workspace/0003_workspace_lifecycle_and_period.py`,
  `tasks/0002_task_workflow_foundation.py`, and
  `reviews/0002_review_workflow_foundation.py`.
- No applied `0001_initial.py` was edited.
- Read-only PostgreSQL development inventory before migration: 0 business
  rows and 3 active User rows; independently reconfirmed on 2026-10-19.
- No synthetic Profile or tenant mapping was created.
- `0002` was exercised on disposable PostgreSQL test databases, including an
  empty test schema and a populated migration fixture retaining Workspace,
  WorkspaceMember, Task, Deliverable, and Review relationships while leaving
  unknown `Workspace.profile` as null.
- `0002` was applied to the approved development database on 2026-10-19 after
  the controlled HT-DB-P1-05 gates passed. A different environment must still
  be inventoried, backed up, rehearsed as appropriate, and separately
  authorized before apply.
- `0003` first passed isolated PostgreSQL migration tests, then completed the
  Owner-approved controlled development rollout in `HT-DB-P1-06` on
  2026-10-20. Production and every other persistent target remain untouched and
  require their own explicit authorization and safety gates.
- `tasks.0002` depends on `workspace.0003`; `reviews.0002` depends on
  `tasks.0002`. Both workflow migrations have run only on Django-created
  isolated PostgreSQL test databases. They are not applied to development or
  production, and this implementation task grants no permission to apply them.
- Current migration rehearsal preserves existing Task/Assignment/Deliverable/
  Review relations, sets every legacy assignment inactive, and leaves each
  legacy Deliverable revision null. It never selects a current assignee or
  invents a revision.

### HT-DB-P1-05 development rollout checkpoint — 2026-10-19

- Target evidence identifies the existing local Compose PostgreSQL 16.14
  service, loopback-bound on port 5432 with named volume
  `docker_postgres_data`, database `hustlytasker_db`. Production was not
  contacted.
- Before apply, `django_migrations` contained 26 rows: `workspace.0001` and the
  swappable User dependency were applied; `workspace.0002`, Profile tables,
  and `workspace_workspace.profile_id` were absent.
- Counts before migration: User 3 (all active); Workspace, WorkspaceMember,
  Task, Client, Invoice, Payment, and AuditLog 0. Profile and
  ProfileMembership were `TABLE ABSENT`, not count zero. Checked ownership
  relationships had no orphan and PostgreSQL reported no unvalidated FK.
- The existing `0002` remains additive and unchanged. With zero Workspace rows
  there is no tenant mapping or backfill to infer.
- A PostgreSQL custom-format backup is stored under the Git-ignored
  `.local_backups/HT-DB-P1-05/`. Its 66,721-byte host copy matches the
  container SHA-256, `pg_restore --list` succeeds, and a full archive stream to
  `/dev/null` exits 0. A full isolated restore rehearsal reproduced 26
  migrations, 3 Users, zero Workspaces, and the expected pre-`0002` schema;
  the temporary rehearsal database was removed.
- A process-only development runtime was used without creating `.env` or
  persisting/logging secrets. The reviewed plan matched the additive source,
  then exactly `workspace.0002_profile_workspace_foundation` was applied.
- Final state has 27 migration rows; `workspace_profile`,
  `workspace_profilemembership`, nullable `workspace_workspace.profile_id`,
  reviewed FKs/check/partial-unique constraints and indexes exist and validate.
  Counts remain 3 Users and zero Profile, ProfileMembership, Workspace,
  WorkspaceMember, Task, Client, Invoice, Payment, and AuditLog rows. There are
  zero unmapped Workspaces, orphan Workspace/Profile references, unvalidated
  constraints, test databases, or restore-rehearsal databases.

### Historical HT-WORK-P2-02 schema-free checkpoint — 2026-10-19

This checkpoint records the earlier completed slice and is **superseded for
current source behavior** by the schema-dependent checkpoint below.

- The initially authorized Workspace write/membership slice required no model
  change and created no migration. At that historical checkpoint,
  `workspace.0002_profile_workspace_foundation` was the latest Workspace
  migration in source and development, and no `0003` existed.
- At that checkpoint, `Profile` had no active/archive lifecycle field,
  `Workspace` had no archive state or canonical month/period field, and
  `WorkspaceMember` had no active/revoked state.
- Consequently, archive/restore and Workspace-member revoke/deactivate were
  unavailable in that slice. The later approved schema-dependent portion now
  implements the bounded lifecycle behavior below; it does not infer broader
  retention, purge, self-leave, or Profile-membership rejoin policy.
- Verification passed 111/111 targeted Workspace tests, 29/29
  Authentication/API Foundation regressions, and 140/140 full PostgreSQL tests,
  plus Django system and migration consistency checks.

### Historical HT-WORK-P2-02 schema-dependent source checkpoint — 2026-10-19

Status at that checkpoint: `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`

- Additive `workspace.0003_workspace_lifecycle_and_period` adds
  `Profile.status`, `Workspace.period`, `Workspace.status`, and
  `WorkspaceMember.is_active`, together with the status/period checks,
  conditional Profile/month uniqueness, and lookup indexes described above.
  It edits no applied migration and performs no guessed data mapping.
- An isolated PostgreSQL `0002 → 0003` rehearsal verified legacy defaults and
  preserved Workspace/WorkspaceMember plus Task → Deliverable → Review
  relationships. Existing Workspaces retain null period until explicitly
  reconciled; the migration does not synthesize a month.
- Profile Owner-only archive/restore, Profile Owner/Admin Workspace
  archive/restore, mandatory immutable canonical period creation, and
  Workspace-member soft-revoke/reactivation are implemented through locked,
  transactional, audited services and tenant-scoped DRF endpoints. Archived
  rows remain readable and normal writes are blocked. Hard delete is not
  exposed by the tenant API/service contract; existing platform/Admin
  destructive paths remain outside this task and require separate control.
- Verification passed `pip check`, Django system check,
  `makemigrations --check --dry-run`, 140/140 Workspace tests in 79.278s, and
  169/169 full PostgreSQL tests in 82.920s.
- The latest successful post-suite development inventory on 2026-10-19 found
  27 migrations with `workspace.0002` applied and `workspace.0003` absent;
  3 Users and zero Profile, ProfileMembership, Workspace, WorkspaceMember,
  Task, Client, Invoice, Payment, or AuditLog rows; no test database. A
  read-only check on 2026-10-20 found the existing development PostgreSQL
  container stopped; it was not started or changed. `0003` was not applied to
  development, and production was not touched.

### Current HT-DB-P1-06 development rollout checkpoint — 2026-10-20

Status: `COMPLETE / OWNER REVIEW GATE`

- The approved target is the existing Compose-labeled PostgreSQL 16.14
  development container, database `hustlytasker_db`, loopback-bound at port
  5432 with named volume `docker_postgres_data`. Production was not contacted.
- Immediately before apply, migration history and physical schema agreed at 27
  records with `workspace.0002` applied and `workspace.0003` absent. Inventory
  was 3 active Users, 2 existing sessions, and zero checked business rows.
- A fresh ignored custom-format backup was verified by matching host/container
  SHA-256, readable 188-line TOC, and full archive read. A full restore rehearsal
  reproduced the pre-apply 27-migration/3-User state in an isolated database,
  which was then removed.
- Exact plan review contained only the 11 additive `workspace.0003` operations.
  Apply completed at 2026-10-20 07:44:40 UTC without `--fake`, reverse,
  backfill, data deletion, or guessed tenant/month mapping.
- Development now has 28 migration records. `Profile.status` and
  `Workspace.status` are non-null varchar, `Workspace.period` is nullable date,
  and `WorkspaceMember.is_active` is non-null boolean; none retains a permanent
  database default. All three CHECK constraints are validated. The conditional
  unique `(profile_id, period)` index and all three lookup indexes are valid and
  ready.
- Final inventory remains 3 active Users, 2 sessions, and zero rows across
  Profile/ProfileMembership/Workspace/WorkspaceMember, Task and related review
  records, Client/ShareLink, Invoice/Payment, Notification, and AuditLog. There
  is no invalid lifecycle/period value, duplicate Profile/month, unvalidated
  constraint, other live PostgreSQL connection, or temporary test/rehearsal
  database.
- Direct development request-stack smoke changed no data. Fixture-dependent
  role, tenant isolation, IDOR, lifecycle, membership, concurrency, and
  migration cases passed only in isolated PostgreSQL test databases: targeted
  lifecycle/schema 17/17, Workspace 140/140, auth/API 29/29, and full suite
  169/169. This evidence does not authorize another environment.

### Current HT-TASK-P2-03 source checkpoint — 2026-10-21

Status: `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`

- `tasks.0002_task_workflow_foundation` adds the assignment lifecycle flag,
  Task status/priority checks, one-active-assignment constraint and lookup
  indexes, while changing Task creator/assignee/commenter FKs to `PROTECT`.
- `reviews.0002_review_workflow_foundation` adds nullable legacy-safe
  Deliverable revisions, revision/status constraints and index, one Review per
  Deliverable, and protected uploader/reviewer FKs.
- The migration order is `workspace.0003 -> tasks.0002 -> reviews.0002`.
  Existing assignments are intentionally inactive after migration and existing
  Deliverable revisions intentionally remain `NULL`; application-created rows
  use active assignments and positive revisions.
- Before any persistent rollout, inventory every status/priority value,
  duplicate Review per Deliverable, legacy assignment set, and revision state.
  Invalid enum values or duplicate Reviews will block constraint creation and
  require an explicit owner-reviewed reconciliation. Do not auto-delete,
  deduplicate, select a current assignee, or synthesize revisions.
- The final read-only development post-check reports 3 Users, 2 sessions, zero
  checked business/workflow rows, `workspace.0001/0002/0003`, `tasks.0001`
  only, and `reviews.0001` only. Both new migrations remain unapplied. No
  test/rehearsal database or disposable runner remains.
- Read-only `migrate --plan` succeeds and lists only additive `tasks.0002`
  followed by `reviews.0002`. No migration was applied by this task.
- Isolated PostgreSQL verification passes targeted service/API/migration
  33/33 in 7.673s, existing Authentication/API/Workspace regressions 169/169
  in 87.783s, and the final full suite 202/202 in 92.343s. Dependency, Django
  system and migration-drift checks pass, test databases are destroyed, and
  independent final code review passes.

## Approved target — implementation status

| Domain | Approved boundary/behavior still awaiting its own task |
|---|---|
| Invitation | Joining Profile requires accepted invitation; direct Workspace add is limited to an already-active Profile member. A proposed ProfileInvitation record/token/state contract is documented below and in `RBAC_DESIGN.md`; no model, migration, service, or API exists. |
| Project/Client | Client belongs to Profile; Project belongs to Client/Profile and may span Workspaces. Current models have not been migrated. |
| Finance | Invoice belongs to Workspace and same-Profile Client; Payment belongs to Invoice. Current finance schema has not been migrated and numbering/billing details remain undecided. |
| Public access | Client Portal account and secure link are supported targets; ClientPortalLink and GuestReviewLink are separate, hashed, expiring, revocable, capability-scoped principals. Replacements are absent. |
| Soft delete/retention | Soft delete remains the target default for Profile, Workspace, Client, Project, and Task; hard delete is controlled; Invoice/Payment/AuditLog are protected under the eventual retention policy; User departure must not cascade-delete business data. Bounded Profile/Workspace archive, Workspace-member soft revoke, protected workflow actor FKs, inspection-only Task Admin, and disabled Workspace Admin delete are implemented. Client/Project/Task soft delete fields, legal retention periods, purge, self-leave, and full Profile-membership rejoin policy remain undecided or unimplemented. |
| Tenant authorization | Profile Owner/Admin Workspace-content inheritance and ordinary-Member explicit assignment are approved. Profile/Workspace contexts, scoped selectors, Workspace routes and Task/Deliverable/internal Review scoping now exist with IDOR/concurrency/audit tests. General Profile CRUD/membership APIs and Client/Finance/Audit/external-review scoping remain absent. |
| Task/Review workflow | The approved internal flow is implemented in source: manager create/assign, assigned Editor execute/submit, distinct manager approve or request changes, and completion only after valid approval. Client/Guest approval, arbitrary cancellation, comments, file storage/media handling, Task soft delete, and Payroll/Payment pricing/trigger remain separate and unimplemented. |

## Approved ProfileInvitation contract — schema not implemented

This subsection is approved design information only. It does not describe
current models, does not reserve a migration number, and is not authorization
to implement Invitation in `HT-RBAC-P1-03`. Verified email identity is a
production dependency; a hashed token alone is not sufficient identity proof.

Proposed aggregate:

- required Profile FK as tenant boundary;
- normalized recipient-email snapshot and optional unambiguously bound User;
- requested Profile role with an approved grant ceiling;
- inviter and terminal actor/reason metadata subject to retention policy;
- `PENDING`, `ACCEPTED`, `DECLINED`, `EXPIRED`, `REVOKED` state;
- required expiry and a unique SHA-256 token digest; the raw token is never
  persisted, serialized, audited, or logged;
- at most one `PENDING` record for a Profile/normalized email and, when bound,
  per Profile/recipient User. A stale expired pending row is terminalized
  inside the locked service before a replacement is created;
- Profile/status/expiry and safe recipient-inbox indexes; and
- immutable terminal records, with reinvite/resend represented by a new
  credential/record rather than reusing a consumed token.

Acceptance is a transactional Profile-level operation and never creates a
WorkspaceMember automatically. Lock order is Profile → Invitation → relevant
ProfileMembership rows. Constraints provide duplicate/replay defense while
the service enforces recipient binding, expiry, role ceiling, one terminal
winner, same-Profile scope, and atomic audit.

Later schema/implementation work must still define unregistered-recipient
onboarding, reactivate-versus-new membership history, historical WorkspaceMember
behavior on rejoin, FK deletion behavior and inviter-authority revalidation.
The approved initial TTL is 7 days; resend invalidates the prior credential;
terminal metadata is retained at least 12 months; automated purge is out of
scope.

## Foundation invariants and remaining rollout work

- Multiple active Profile Owners are permitted; service operations preserve at
  least one active Owner with transaction locking. This is intentionally not an
  at-most-one-owner constraint.
- Deactivating a ProfileMembership does not delete its WorkspaceMember history.
  Future authorization must require both active Profile membership and the
  applicable Workspace access; invitation/rejoin work must decide whether old
  Workspace access is restored or explicitly granted again.
- A selected Profile or Workspace is navigation context only, never evidence
  of authorization.
- Tenant FKs become non-null only after target-specific inventory, explicit
  reconciliation, rehearsal, and validation.
- No Workspace mapping may be inferred merely from common User ownership. No
  Client/AuditLog mapping may be guessed from unrelated records.
- Before applying `0002` outside disposable tests: inventory that database,
  back it up where data must be retained, report any existing Workspaces, and
  obtain explicit mappings for every unresolved row. The approved development
  target completed this controlled sequence on 2026-10-19; no other target is
  covered by that authorization or evidence.
- Later migrations must add Client, Project, Invoice, public-link, AuditLog,
  and soft-delete changes additively in their approved tasks.

Historical P1-03 verification on 2026-10-18 passed 51/51 targeted Workspace
model/service/migration/access tests and the then-current 80-test full suite.
After P1-04 added only the read API layer and tests, final verification passed
21/21 targeted API tests and the 101-test full PostgreSQL suite. `pip check`,
Django system check, and `makemigrations --check --dry-run` also passed. No
schema migration was created or applied to development by P1-04. The historical
schema-free HT-WORK-P2-02 slice then passed 111/111 targeted Workspace tests,
29/29 Authentication/API Foundation regressions, and 140/140 full PostgreSQL
tests. Its later schema-dependent completion passed 140/140 Workspace and
169/169 full PostgreSQL tests plus dependency, system, and migration-drift
checks. `HT-DB-P1-06` then applied `0003` to the approved development database
after backup/restore rehearsal and passed current direct smoke, 17/17 targeted,
140/140 Workspace, 29/29 auth/API, and 169/169 full PostgreSQL verification.
HT-TASK-P2-03 subsequently passed 33/33 targeted, 169/169 existing regression,
and 202/202 full PostgreSQL tests. Its `tasks.0002`/`reviews.0002` migrations
remain unapplied on development pending separate Owner approval.
Production and other persistent targets remain unauthorized and untouched.
