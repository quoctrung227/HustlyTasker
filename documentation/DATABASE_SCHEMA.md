# DATABASE_SCHEMA.md

# HustlyTasker Database Design

Version: 0.3

Status:

Implemented initial Django schema + Profile/Workspace foundation in source;
remaining tenant-domain schema is an approved target not yet implemented

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
| created_by | FK User | Required |
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
| user_id | FK |
| assigned_at | timestamp |



Relationships:


Task N --- N User



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
| user_id | FK |
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
| uploaded_by | FK User |
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



---


# Review


Table:

reviews


Fields:


| Field | Type |
|-|-|
| id | UUID |
| deliverable_id | FK |
| reviewer_id | FK User |
| status | enum |
| comment | text |
| created_at | timestamp |



Status:


PENDING

APPROVED

REQUEST_CHANGE



Relationships:


Deliverable 1 --- N Review



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

# 13. Current Ownership Audit — verified 2026-10-18

This section describes the active Django source. The original sections above
document the initial schema; their “future” indexes or relationships must not
be treated as implemented unless they also exist in models/migrations.

| Entity | Current ownership path | Verified gap |
|---|---|---|
| User | Global identity | Profile access now uses separate ProfileMembership; User remains unchanged. |
| Profile/ProfileMembership | Tenant root + User membership | Foundation exists in source; invitation and complete lifecycle API do not. |
| Workspace | `profile → Profile` plus transitional `owner → User` | Profile FK is nullable for safe transition; owner is protected but remains a transitional second ownership representation. |
| WorkspaceMember | `workspace + user` | Unique pair exists; validated writes require active membership in the Workspace Profile. |
| Task | `workspace → Workspace` | Creator is not required to be a member. |
| TaskAssignment/TaskComment | `task → workspace` | Actor membership in that workspace is not enforced. |
| Deliverable/Review | `task → workspace` | Uploader/reviewer membership is not enforced. |
| Client | None | Global row cannot be tenant-filtered safely. |
| ShareLink | `client`, but Client is global | Raw token, no tenant, creator, capabilities, revoke state, or token hash. |
| Invoice/Payment | `invoice → client`, but Client is global | No tenant boundary; invoice number is globally unique. |
| Notification | Recipient User | No structured Profile/Workspace context. |
| AuditLog | Optional User + generic entity ID | No reliable tenant path or enforced target reference. |

The schema foundation adds explicit ProfileMembership uniqueness and role
checks, membership lookup indexes, Workspace/Profile model validation, and
transactional membership services. `HT-RBAC-P1-03` now adds Profile/Workspace
scoped selectors and verified access contexts without a schema change. API
permissions, soft delete, and cross-domain same-Profile constraints are not
implemented.

The eight development domain apps remain at their existing
`0001_initial.py` migrations. The additive
`workspace/0002_profile_workspace_foundation.py` exists in source but has run
only on disposable PostgreSQL test databases at this checkpoint.


---

# 14. Approved Tenancy Architecture and Foundation Status

Architecture status: `ACCEPTED — 2026-10-16`

Foundation status: `COMPLETE IN SOURCE; DEVELOPMENT MIGRATION NOT APPLIED`

RBAC/Invitation design status:
`COMPLETE / ACCEPTED BY OWNER DELEGATION; INVITATION SCHEMA NOT IMPLEMENTED`

Tenant access/service status:
`HT-RBAC-P1-03 COMPLETE; NO MODEL OR MIGRATION CHANGE`

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
| `Profile` | UUID/timestamps inherited from `BaseModel`; required `name`. Represents the company/team tenant root. |
| `ProfileMembership` | Protected Profile and User FKs; `OWNER`, `ADMIN`, `MEMBER`; `is_active`; `joined_at`; inactive history is permitted but only one active row may exist per `(profile, user)`. |
| Membership constraints | Partial unique `uniq_active_profile_user`, role check `profmem_valid_role`; indexes `profmem_user_active_idx` and `profmem_prof_active_role_idx`. |
| `Workspace.profile` | Transitional nullable protected FK. New saves require Profile; a mapped Workspace cannot be re-parented through model/admin writes; an explicit null-to-Profile mapping validates the owner and every existing Workspace member. Mapped saves lock Profile then Workspace; existing legacy null saves lock their Workspace row before validation, preventing concurrent mapping/re-parent and stale null write-back races. Null remains allowed at database level so unknown legacy rows are preserved without guessed backfill. |
| `Workspace.owner` | Existing transitional FK retained; deletion changed from `CASCADE` to `PROTECT`. Validated writes require that owner to be an active Profile Owner or Admin. |
| `WorkspaceMember` validation | `save()` validates an active same-Profile membership and active account. Existing one-row-per-Workspace/User constraint remains; Django Admin membership mutation is read-only. |
| Foundation services | Create Profile plus initial active Owner atomically; tenant-scope Profile membership updates before target lookup; lock Profile during role/active changes; support multiple Owners; block removal/demotion of the last usable active Owner; restrict Profile Admin to current ordinary Members; directly add only an active same-Profile member with Profile/Workspace role ceilings; translate duplicate adds to a stable conflict; write membership AuditLog events atomically. |
| Access contexts/selectors (no schema change) | Resolver-produced immutable Profile/Workspace contexts require active User and ProfileMembership; Profile/Workspace selectors fail closed across tenants; capability checks revalidate current role and reject forged/stale contexts. Existing WorkspaceMember values map `ADMIN` to Workspace Admin, `MEMBER` to Editor and `VIEWER` to read-only Viewer; legacy `OWNER` grants no capability and cannot be assigned by the service. |

`Workspace.save()` and `WorkspaceMember.save()` call `full_clean()`, but bulk
updates, raw SQL, and direct `ProfileMembership` ORM mutations can bypass
service invariants. Direct User deactivation can also make an Owner account
unusable without going through the owner service. Profile/ProfileMembership are
not exposed in Admin and WorkspaceMember Admin is read-only, but future APIs
must use reviewed services. This foundation is not a complete authorization
layer or a database-wide guarantee of the aggregate last-owner invariant.

## Migration and inventory evidence

- New additive migration:
  `workspace/0002_profile_workspace_foundation.py`.
- No applied `0001_initial.py` was edited.
- Read-only PostgreSQL development inventory before migration: 0 business
  rows and 3 User rows; reconfirmed before and after tests on 2026-10-18.
- No synthetic Profile or tenant mapping was created.
- `0002` was exercised on disposable PostgreSQL test databases, including an
  empty test schema and a populated migration fixture retaining Workspace,
  WorkspaceMember, Task, Deliverable, and Review relationships while leaving
  unknown `Workspace.profile` as null.
- `0002` has **not** been applied to the development database. A different
  environment must be inventoried and backed up independently before apply.

## Approved target — not implemented

| Domain | Approved boundary/behavior still awaiting its own task |
|---|---|
| Invitation | Joining Profile requires accepted invitation; direct Workspace add is limited to an already-active Profile member. A proposed ProfileInvitation record/token/state contract is documented below and in `RBAC_DESIGN.md`; no model, migration, service, or API exists. |
| Project/Client | Client belongs to Profile; Project belongs to Client/Profile and may span Workspaces. Current models have not been migrated. |
| Finance | Invoice belongs to Workspace and same-Profile Client; Payment belongs to Invoice. Current finance schema has not been migrated and numbering/billing details remain undecided. |
| Public access | Client Portal account and secure link are supported targets; ClientPortalLink and GuestReviewLink are separate, hashed, expiring, revocable, capability-scoped principals. Replacements are absent. |
| Soft delete/retention | Soft delete is the target default for Profile, Workspace, Client, Project, and Task; hard delete is controlled; Invoice/Payment/AuditLog are protected under the eventual retention policy; User departure must not cascade-delete business data. Current foundation adds no soft-delete fields/services. Retention periods and automated purge remain undecided. |
| Tenant authorization | Profile Owner/Admin Workspace-content inheritance and ordinary-Member explicit assignment are approved. Profile/Workspace contexts, scoped selectors, action-level capability helpers and IDOR/service tests now exist; DRF permission classes/endpoints and Client/Finance/Audit/Task/Review scoping remain absent. |
| Task/Review workflow | Assignment → Deliverable → Review → approval/completion or revision/resubmission is approved at high level; Task completion is allowed only after Deliverable approval. Detailed states, approvers, and payroll trigger remain undecided. |

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
  obtain explicit mappings for every unresolved row.
- Later migrations must add Client, Project, Invoice, public-link, AuditLog,
  and soft-delete changes additively in their approved tasks.

Verification recorded for this checkpoint on 2026-10-18: final targeted
Workspace/model/service/migration/access tests passed 51/51 and the full
80-test PostgreSQL suite passed. The full run includes the 19 Authentication
and 10 API Foundation regression tests. `pip check`, Django system check, and
`makemigrations --check --dry-run` also passed. No migration was created or
applied to development.
