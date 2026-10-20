# HustlyTasker Project Context

## Project Overview

HustlyTasker is a workflow management system designed for content production teams and agencies.

The target product workflow is below. On 2026-10-16 the owner approved
`Profile` (a company or working group) as the tenant root and Workspace as its
operational/monthly child. A User remains global and may belong to multiple
Profiles; selected navigation context is never authorization evidence:

User
→ Profile
→ Workspace
→ Task
→ Assignment
→ Deliverable
→ Internal Review
→ Task Completion

Client/Guest approval and Finance are separate downstream workflows. Internal
approval does not imply client approval and does not automatically create any
Payroll, Payment, Invoice, or compensation record.


## Main Goals

The system helps teams:

- Manage workspace collaboration.
- Create and assign tasks.
- Track production progress.
- Review deliverables.
- Manage clients.
- Track invoices and payments.
- Maintain workflow history.


## Current Technology Stack

Backend:
- Django

API:
- Django REST Framework

Database:
- PostgreSQL

ORM:
- Django ORM

Frontend planned:
- React / Next.js

Container:
- Docker


## Current Development Status

Current Phase:

PHASE 2.2 - API Architecture

Current task status:

`HT-TASK-P2-03 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`


Completed:

- Project documentation
- Django setup
- PostgreSQL Docker environment
- Django applications structure
- Initial database schema
- Initial Django models
- Initial migrations
- Django Admin testing
- DRF foundation
- Session-based authentication foundation (register/login/logout/me)


Completed in the current phase:

- DRF deny-by-default API policy and reviewed public allowlist
- Database-independent `/api/health/` liveness endpoint; legacy `/api/test/`
  has been removed
- Repository-wide agent/documentation handover rules in `AGENTS.md`
- HT-DATA-P2-01 source/reference audit, evaluated ownership boundaries,
  isolation invariants, and migration plan
- Owner approval of the 11 Profile/Workspace architecture decision groups
- Profile/Workspace schema foundation in source: `Profile`,
  `ProfileMembership`, transitional `Workspace.profile`, membership/owner
  invariants, additive `workspace/0002_profile_workspace_foundation.py`, and
  targeted 32/32 plus full-suite 61/61 PostgreSQL tests verified on 2026-10-17
- HT-RBAC-DESIGN-P0-01 is `COMPLETE / ACCEPTED — APPROVED BY OWNER
  DELEGATION`; `RBAC_DESIGN.md` and `DECISION_LOG.md` hold the approved
  Profile/Workspace roles, least-privilege ceilings, IDOR/operator policy and
  Profile Invitation contract.
- HT-RBAC-P1-03 Tenant Access Context and Scoped Service Foundation: immutable
  verified Profile/Workspace contexts, scoped selectors, revalidated
  capabilities and tenant-scoped membership services. Compatibility mapping is
  `WorkspaceMember.ADMIN` = Workspace Admin, `MEMBER` = Editor, `VIEWER` =
  read-only Viewer; legacy `OWNER` fails closed and cannot be newly assigned.
  Final PostgreSQL verification passed 51/51 targeted and 80/80 full tests on
  2026-10-18 without an API, model or migration change.
- HT-API-P1-04 Profile/Workspace Read API & DRF Permission Integration: four
  read-only `/api/v1/` routes, minimal serializers, active tenant permission
  adapters, scoped querysets, bounded pagination, generic IDOR-safe `404`, and
  GET/HEAD/OPTIONS-only behavior. Final PostgreSQL verification passed 21/21
  targeted API and 101/101 full tests on 2026-10-18 without a model, migration,
  authentication, service-rule, or development-data change.
- HT-DB-P1-05 controlled development rollout: revalidated the local Compose
  target and zero-business-row inventory; verified the Git-ignored backup;
  completed an isolated restore rehearsal; applied the existing additive
  `workspace.0002`; post-checked schema/data; direct-smoked health, anonymous
  tenant denial and CSRF behavior; and passed current 21/21 targeted, 29/29
  auth/API and 101/101 full PostgreSQL tests. No source, business row, fixture,
  authentication mechanism or API contract changed.
- HT-WORK-P2-02 Workspace write/membership implementation, including its
  schema-dependent extension: `Profile.status`, canonical immutable
  `Workspace.period`, `Workspace.status`, `WorkspaceMember.is_active`, and at
  most one non-null `(profile, period)` even when the Workspace is archived;
  Profile Owner-only archive/restore; Profile Owner/Admin Workspace
  archive/restore; and manager-only Workspace-member list/direct-add/role
  update/soft-revoke/same-row reactivation. Archived objects remain scoped and
  readable while normal writes are blocked. Hard delete is not exposed by the
  tenant API/service contract; existing platform/Admin destructive paths remain
  outside this task and require separate control.
  Additive `workspace.0003_workspace_lifecycle_and_period` exists in source and
  first passed isolated PostgreSQL migration/regression verification.
- HT-DB-P1-06 controlled development rollout: verified the exact local Compose
  PostgreSQL 16.14 target and zero-business-row inventory; created and fully
  restore-rehearsed a fresh Git-ignored backup; applied only `workspace.0003`;
  and post-checked 28 migrations, columns, validated constraints, valid/ready
  indexes and unchanged data. Direct development smoke changed no row/session.
  Current isolated results passed 17/17 lifecycle/schema, 140/140 Workspace,
  29/29 Authentication/API Foundation, and 169/169 full PostgreSQL tests.
  Production and every other persistent target were untouched.
- HT-TASK-P2-03 source implementation: Task create/update/assign/start;
  revisioned Deliverable submit/history; internal approve/request changes;
  manager/Editor role split; no self-review; tenant-scoped strict/no-PII API;
  transactional AuditLog; additive `tasks.0002`/`reviews.0002`; protected actor
  history and inspection-only Task Admin. Current targeted PostgreSQL
  service/API/migration verification passes 33/33, existing regressions pass
  169/169, and final full PostgreSQL passes 202/202. Dependency/system/
  migration-drift checks, cleanup and independent code review pass. Final
  read-only development checks keep Tasks/Reviews at 0001; neither workflow
  migration is applied to development.


Approved architecture target, not fully implemented:

- Client belongs to Profile and has many Projects; Project spans monthly
  Workspaces through Tasks; Invoice belongs to one Workspace and same-Profile
  Client; Payment belongs to Invoice
- Profile and Workspace membership remain separate; Profile Owner/Admin
  administer Profile Workspaces while ordinary Members need explicit Workspace
  assignment
- Client Portal supports both authenticated-account and secure-link access;
  Client Portal and Guest Review links are separate, hashed, expiring,
  revocable capability principals and grant no implicit internal membership
- Soft delete is the default target for Profile, Workspace, Client, Project,
  and Task; the bounded Profile/Workspace archive state and Workspace-member
  soft revoke are implemented in source. Hard delete remains controlled,
  finance/audit records are protected, and User departure does not
  cascade-delete business data; retention duration/purge rules remain future
  decisions
- Task completes only after its latest submitted Deliverable passes internal
  Review approval. The internal states and reviewer authority are now fixed and
  implemented by HT-TASK-P2-03; Client/Guest approval and Payroll pricing/
  eligibility/business effects remain future decisions.


Not completed:

- Account activation/OTP and password recovery
- Applying the Profile schema to any environment other than the approved
  development database. Each target still requires its own inventory, backup,
  risk review, and authorization. Development has applied `workspace.0002` and
  `workspace.0003`.
- Applying `workspace.0003_workspace_lifecycle_and_period` to production or any
  persistent environment other than the specifically approved development
  database. Development completed the controlled rollout on 2026-10-20 and now
  has 28 migrations, 3 active Users, 2 sessions, zero checked business rows,
  and no leftover test/rehearsal database. Every other target still requires
  separate inventory, backup, risk review, and authorization.
- Cross-domain Client/Finance/Audit selectors, external Client/Guest review,
  Task soft delete/retention, Comments/Marketplace/media upload, and Payroll
  rules. Internal Task/Review enforcement has completed verification but still
  awaits a separately approved controlled development migration.
- Account deactivation service that preserves last-owner invariants across
  Profiles and revokes established sessions
- Invitation model/API, Project model, Client/Finance tenant migrations,
  public-link replacement and soft-delete services
- General Profile CRUD/membership API, Workspace self-leave, Profile invitation
  and rejoin policy, and downstream domain APIs beyond the completed bounded
  Workspace/Profile lifecycle and member-manager slice
- Frontend
- Deployment


## Architecture Rules

Do not:

- Change technology stack without approval.
- Replace Django architecture.
- Rebuild database without reason.

Development follows:

Models
↓
Migration
↓
API
↓
Frontend

The tenancy design and capability/scoping/invitation contract are approved, and
the schema plus tenant-access/service foundations have completed regression.
The owner separately authorized and the project completed the minimal
Profile/Workspace reads, canonical monthly Workspace writes, bounded
Profile/Workspace archive/restore, manager-only Workspace membership lifecycle,
and controlled development rollout of `workspace.0003` listed above.
Invitation, general Profile CRUD/membership, self-leave/rejoin, full
cross-domain RBAC, Task workflow development rollout, other business APIs, and
every non-development rollout remain behind their own Owner review gates,
regardless of roadmap task numbering.


## AI Development Instructions

When continuing development:

1. Read root `AGENTS.md` and `documentation/HANDOVER.md` first.
2. Read affected documentation and check current phase before coding.
3. Do not recreate completed components.
4. Preserve existing architecture.
5. Explain changes before implementation.
