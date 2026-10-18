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
  and Task; hard delete is controlled, finance/audit records are protected,
  and User departure does not cascade-delete business data; retention duration/
  purge rules remain future decisions
- Task completes only after its submitted Deliverable passes Review approval;
  exact states, approver authority, and payroll trigger remain future decisions


Not completed:

- Account activation/OTP and password recovery
- Applying Workspace `0002` to the development database; it has run only on
  disposable test databases after read-only inventory found 0 business rows
  and 3 User rows
- Workspace/Invitation API and DRF tenant permission layer; the current access
  foundation is service/query infrastructure only
- Cross-domain Client/Finance/Audit selectors and Task/Review enforcement;
  exact reviewer/workflow states remain a later contract
- Account deactivation service that preserves last-owner invariants across
  Profiles and revokes established sessions
- Invitation model/API, Project model, Client/Finance tenant migrations,
  public-link replacement and soft-delete services
- Business APIs
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
Invitation remains design-only and downstream; no Workspace API, full RBAC, or
business API may start until the owner authorizes the next implementation task,
regardless of roadmap task numbering.


## AI Development Instructions

When continuing development:

1. Read root `AGENTS.md` and `documentation/HANDOVER.md` first.
2. Read affected documentation and check current phase before coding.
3. Do not recreate completed components.
4. Preserve existing architecture.
5. Explain changes before implementation.
