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
- HT-RBAC-DESIGN-P0-01 deliverable in `RBAC_DESIGN.md`: evidence-labeled
  capability matrix, tenant-scoped request/query/service boundary,
  non-enumerating IDOR policy proposal, Profile Invitation contract, planned
  API, negative/concurrency tests, and dependency-ordered rollout. It is
  `DESIGN READY — PENDING OWNER APPROVAL`; none of it is runtime behavior yet.


Approved architecture target, not fully implemented:

- Client belongs to Profile; Project spans monthly Workspaces through Tasks;
  Invoice belongs to one Workspace and same-Profile Client
- Profile and Workspace membership remain separate; Profile Owner/Admin
  administer Profile Workspaces while ordinary Members need explicit Workspace
  assignment
- Client Portal and Guest Review credentials are separate, hashed, expiring,
  revocable capability principals
- Soft delete is the default target for Profile, Workspace, Client, Project,
  and Task; retention duration/purge rules remain future decisions


Not completed:

- Account activation/OTP and password recovery
- Applying Workspace `0002` to the development database; it has run only on
  disposable test databases after read-only inventory found 0 business rows
  and 3 User rows
- Workspace RBAC and object permission system
- Owner approval of the proposed Workspace role/action matrix, Admin/Viewer
  authority, Task visibility, Profile-creation bootstrap, leave/rejoin and
  invitation lifecycle, error semantics, platform-operator/Admin policy, and
  User deactivation/delete protection for the last usable Owner
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

The tenancy design is approved and its schema foundation has completed
regression. The next-level capability/scoping/invitation design is ready but
pending owner approval. No Workspace RBAC or business API may start merely
because a technical proposal exists, regardless of roadmap task numbering.


## AI Development Instructions

When continuing development:

1. Read root `AGENTS.md` and `documentation/HANDOVER.md` first.
2. Read affected documentation and check current phase before coding.
3. Do not recreate completed components.
4. Preserve existing architecture.
5. Explain changes before implementation.
