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
→ Review
→ Client Approval
→ Completion
→ Finance


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

`HT-WORK-P2-02 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`


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
  was verified only in isolated PostgreSQL. `pip check`, Django system checks,
  and `makemigrations --check --dry-run` passed; Workspace tests passed 140/140
  in 79.278s and the full PostgreSQL suite passed 169/169 in 82.920s.


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
- Task completes only after its submitted Deliverable passes Review approval;
  exact states, approver authority, and payroll trigger remain future decisions


Not completed:

- Account activation/OTP and password recovery
- Applying the Profile schema to any environment other than the approved
  development database. Each target still requires its own inventory, backup,
  risk review, and authorization. Development has applied `workspace.0002`.
- Applying `workspace.0003_workspace_lifecycle_and_period` to development or
  any other persistent environment. Its implementation and isolated
  PostgreSQL rehearsal are complete, but development remains on applied
  `workspace.0002` pending explicit migration approval; production was not
  touched. The latest successful post-suite inventory on 2026-10-19 found 27
  migrations, 3 Users, zero checked business rows, and no test database. A
  read-only check on 2026-10-20 found the existing development PostgreSQL
  container stopped; it was not started or changed.
- Cross-domain Client/Finance/Audit selectors and Task/Review enforcement;
  exact reviewer/workflow states remain a later contract
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
Profile/Workspace archive/restore, and manager-only Workspace membership
lifecycle listed above. Development rollout of `workspace.0003`, Invitation,
general Profile CRUD/membership, self-leave/rejoin, full cross-domain RBAC, and
other business APIs remain behind their own Owner review gates, regardless of
roadmap task numbering.


## AI Development Instructions

When continuing development:

1. Read root `AGENTS.md` and `documentation/HANDOVER.md` first.
2. Read affected documentation and check current phase before coding.
3. Do not recreate completed components.
4. Preserve existing architecture.
5. Explain changes before implementation.
