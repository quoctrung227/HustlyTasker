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

Frontend foundation:
- React SPA + strict TypeScript + Vite
- React Router, Tailwind CSS and TanStack Query
- Biome lint, Vitest/Testing Library and Playwright/axe verification
- Existing Django SessionAuthentication/CSRF through same-origin API proxy

Container:
- Docker


## Current Development Status

Current Phase:

PHASE 3 - Frontend Foundation

Current task status:

`HT-FE-P3-01 — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE`

The Owner-authorized first web foundation now exists in the previously empty
frontend directory as one React/TypeScript/Vite application. It reuses the
existing Django/DRF API contracts, session cookies and CSRF without backend
changes, JWT or a second backend. Scope is layout/design system/authentication
and read-only Profile/Workspace pages; Task/Review/Project/AI screens and tenant
mutations remain outside this slice. The shared master is
documentation/design-system/hustlytasker/MASTER.md; ui-ux-pro-max was read and
its CLI research applied to the chosen teal/neutral tokens, Plus Jakarta Sans,
consistent responsive shell and accessible control patterns.

Typed API transport, safe errors, in-memory CSRF, protected routes and auth-state
cache cleanup are implemented and verified. Final strict typecheck, Biome lint,
production build and mocked96/96 tests PASS. Separate real isolated Django/
PostgreSQL/Chrome6/6 PASS verifies login/CSRF rotation/logout/me, scoped tenant
reads/IDOR/return navigation, expiry and revoked access. Native launcher,
Playwright and backend exits0 and owned DB/container/two-network cleanup verify.
Responsive/keyboard/native-dialog and axe WCAG2/2.1 AA checks pass with0 violations
at375/768/1440 and812×375 landscape;13 ignored screenshots and visual PNG review
support layout verification. Interactive manual-browser testing was not run.
Privacy guards clear private tab titles after identity loss and keep the fatal
fallback independent of Router state. No private data persists in browser storage.

Final read-only development remains35 migrations/3 Users/2 Sessions/0 checked
business rows;143 protected backend/config/harness asset hashes unchanged, no
owned test resources remain. Historical backend415/415 is the completed rollout
baseline, not rerun because no backend implementation changed. Authenticated
integration uses disposable fixtures only, never persistent development accounts.
Documentation/HANDOVER complete; no blocker. Stop at OWNER REVIEW GATE; proposed
HT-FE-P3-02 requires separate scope. Project remains PENDING OWNER DECISION;
real email delivery, remote CI and production deployment remain unverified.

### Historical completed backend checkpoint — HT-DB-P1-11 — 2026-10-26

`HT-DB-P1-11 — COMPLETE / OWNER REVIEW GATE`

The approved Comment/Notification development rollout has applied tasks.0004
then notifications.0002 exactly once after backup and isolated restore/rehearsal.
Development and source now share the 0.11 schema: nullable Comment lifecycle and
typed Notification context, with no guessed legacy mapping. The original
PostgreSQL 16.14 development container/database/loopback binding/named volume
are preserved; 35 migration records, 3 Users/2 Sessions and 0 business/token/Audit
rows remain. Legacy values compared exactly before/after migration. No feature,
authentication, RBAC, workflow or production change is part of this rollout.

Development anonymous READ ONLY smoke and serializer checks PASS. Authenticated
success/mutations remain isolated-test-only. Current isolated Comment/Notification/
Task regression passes 40/34/128 tests; security/RBAC passes 253/253 and full
PostgreSQL passes 415/415 in 259.978s. All five actual launcher/Python exits are
0, with required checks and owned cleanup. Final schema/inventory/exact legacy
comparison and backup size/hash recheck PASS. Owned rehearsal/temp copy are
removed, host archive retained; no disposable test resources remain. All 143
protected source/configuration/harness assets are unchanged. HANDOVER.md holds
operational backup, timestamps and evidence. No blocker. Project remains
PENDING OWNER DECISION; proposed next step is Owner Project A/B′ scope review.
Real email delivery/remote CI remain unverified. No AI, frontend or next task
starts automatically. Stop at OWNER REVIEW GATE.

### Historical implementation checkpoint — HT-COM-P2-06 — 2026-10-25

The pending-development status below records the pre-rollout implementation
gate and is superseded operationally by HT-DB-P1-11 above. Feature policies
remain current; historical test results are not post-rollout proof.

`HT-COM-P2-06 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL / OWNER REVIEW GATE`

Owner authorized Task Comments and In-App Notification Foundation. Existing
TaskComment and Notification models are reused; Task/Subtask hierarchy,
independent workflow/review, SessionAuthentication and CSRF remain unchanged.
Comments accept 4000 characters on new writes, preserve deleted body internally
behind API tombstones, and audit edit/delete facts without copying content.
Current managers/Editors create; authors with current capability edit own
text; author or manager may soft-delete. Viewer remains read-only and manager
moderation cannot rewrite another author's text.

Typed personal notifications persist atomically with successful assignment,
review submission/outcome or Comment event and its AuditLog. Recipients are
current relevant assignee/review managers/uploader/creator as appropriate,
excluding actor, duplicates and inaccessible users. Own feed/count/read repeat
current Task access and canonical tenant relationships. Safe constant text
contains no Task title, feedback body, token or user identity. Existing is_read
is retained; archived-but-readable targets permit personal mark-read.

Source adds tasks.0004 and notifications.0002 only. They are not applied to
persistent development; legacy lifecycle/context remains nullable without
guessed mapping. Unscoped legacy Notifications remain stored but hidden from
the new API. Current isolated Comment 40/40 (6.919s), Notification 34/34 (5.401s),
Task/Review 128/128 (22.637s), security/RBAC 253/253 (165.756s) and full
PostgreSQL 415/415 (191.226s) PASS. All five native launcher/Python Docker-die
exits are 0, with Django OK, dependency/system/drift/graph/full-chain and
owned cleanup verified. Historical 341/341 is not proof for this extension.
Read-only development remains 33 migrations, 3 Users/2 Sessions and 0 Comment/
Notification/business/token/Audit rows, with new columns absent.
No disposable test DB/container/network remains; only original development
PostgreSQL remains. Applied migration files and protected assets were preserved;
the one shared strict-input guard is the documented minimal integration change.

Comment edits are last-writer-wins, not full text revision history. Deduplication
is per AuditLog event/recipient, not a whole HTTP POST idempotency contract.
Notifications hidden after revocation can reappear if access is restored, with
their read state preserved. Notification insertion failure deliberately rolls
back the business mutation and audit under the chosen atomic consistency policy.

Feedback Analyzer readiness is data preparation only: authorized Task context,
Comments and existing Review/Deliverable revision sources. Full Comment text
revision history, exact revision attribution, source/version citations and
human acceptance of suggestions need future design. No LLM/provider/key,
AI Suggestions table or automatic Task writer is introduced. Project remains
PENDING OWNER DECISION; no Project/Client Portal/Finance/frontend expansion.
Retained deleted Comment text is not an AI-readable source by default; future
retrieval must use authorized projections and honor tombstone redaction.

Historical completed preceding checkpoint:

`HT-DB-P1-10 — COMPLETE / OWNER REVIEW GATE`

The Owner conditionally authorized the exact tasks.0003 development rollout.
Fresh target inventory, verified custom backup and isolated restore/rehearsal
passed before apply. Standard Django applied `tasks.0003_task_hierarchy` once
at `2026-10-25 03:43:19.588793 UTC` on the original repository PostgreSQL16.14
development database only. Task parent is now nullable UUID in development,
with validated self-parent CHECK/FK and valid/ready lookup index. SQL FK uses
deferrable NO ACTION; Django ORM deletion policy remains PROTECT. Cross-row
cycle/depth/tenant invariants still require the unchanged scoped services.

Development now has 33 migration records, 11 Task columns and 40 valid foreign
keys without orphans. Exact legacy-row comparison before/after apply passes:
3 Users/2 Sessions, zero checked business/token/AuditLog rows, and metadata
23 content types/92 permissions/7 Admin logs remain unchanged. No fixture,
new feature, business-rule change, production write or shared-harness edit is
part of this rollout.

Current direct development smoke passes 51 read-only handler requests plus
16 serializer-only checks, with CSRF enforcement and no 500/PII/email/login or
row mutation. Authenticated success and mutation flows are NOT TESTED ON
PERSISTENT DEVELOPMENT; current isolated Task tests pass 88/88 (11.780s),
related Auth/security/Invitation/Workspace/API regression passes 253/253
(162.615s), and full PostgreSQL passes 341/341 (170.987s). All three runs have
actual native-launcher exit 0 and Python-runner container die-event exit 0,
Django `OK` and verified owned test DB cleanup. The older missing-exit-code
limitation below applies only to the historical implementation run.

Final system/model-drift/migration checks and empty pending plan pass. Every
legacy development row again matches the migrated rehearsal after all tests.
Only the ownership-verified rehearsal DB and container backup copy were
removed; the fresh host backup remains retained with original size/hash.
No test/rehearsal DB, labelled test container or network remains. The original
development PostgreSQL container/volume is preserved; 129 baseline backend,
configuration, Docker and harness assets have unchanged SHA-256 values.

Stop at Owner review. Project remains PENDING OWNER DECISION. Proposed next
step is Owner selection of Project A/B′ scope or another separately authorized
roadmap task; do not reapply tasks.0003 or open adjacent implementation.

Historical implementation checkpoint, before the separately authorized rollout:

`HT-TASK-P2-05 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL / OWNER REVIEW GATE`

Owner authorized Task Hierarchy, Deadline & Priority Foundation after the
completed test-harness gate. Reuse Task with nullable protected parent;
maximum parent-edge depth is 3 (root0). Parent/child remain in the same
Workspace and retain independent status/assignment/Deliverable/Review,
priority and nullable deadline. No automatic completion or deadline inheritance
is introduced. Existing Task manager/executor/reviewer capabilities and
SessionAuthentication/CSRF remain unchanged.

Source adds scoped manager parent writes, additive `parent_id` reads and a
paginated direct-children route, plus Task status/priority/deadline/root/parent
filters and ordering. Existing deadline/priority fields are reused. At that
implementation gate, `tasks.0003_task_hierarchy` had run only on isolated
PostgreSQL; persistent apply was not yet authorized. Targeted checks passed (Task API42/42,
hierarchy/workflow43/43, migration2/2). Workspace/RBAC122/122 (60.495s) and full
PostgreSQL341/341 (174.058s) PASS, including Authentication/security/Invitation
and Task/Review regressions. Required dependency/system/model-drift/full-chain
checks and owned-DB cleanup pass. Django `OK` and cleanup are evidenced by
logs; no unretained child-launcher exit code is claimed.

At that implementation gate, read-only development had 32 migrations, 3 Users/2 Sessions, zero verified
Users/tokens and zero checked business/AuditLog rows. tasks.0003 and parent
column were absent there. No disposable test DB/container/network remained;
only development PostgreSQL ran. The proposed controlled rollout at that gate
was subsequently authorized and completed as HT-DB-P1-10 above. No new migration
or feature starts automatically.

**PROJECT ARCHITECTURE REVIEW — PENDING OWNER DECISION.** The previously
proposed HT-PROJ-P2-05 bundle is replaced by HT-TASK-P2-05 and a design-only
Project gate. `PROJECT_ARCHITECTURE_REVIEW.md` recommends the direct Workspace
Task hierarchy now, and optional future Profile/Client-scoped cross-month
Project grouping. No Project model/API/migration, estimated-duration field,
AI integration, frontend or notification was included in that earlier task.

HT-AUTH-P1-02 implementation is complete. Its exact additive `accounts.0002`
is applied to the separately approved repository development database after
inventory, verified backup, and isolated restore rehearsal. Production and all
other persistent environments remain outside that authorization.

Historical completed preceding checkpoint: the Owner authorized PostgreSQL
test harness/CI standardization.
Dedicated isolated settings, a shared serial runner, a local Docker launcher,
and GitHub Actions backend workflow are present. **LOCAL TEST HARNESS VERIFIED**:
guard14/14, targeted API10/10 and full PostgreSQL286/286 (166.382s), required
checks, failure/ownership cleanup and development preservation PASS.
**CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED.** No business
domain, API contract, or persistent migration was changed by that tooling task.


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
  migration-drift checks, cleanup and independent code review pass.
- HT-DB-P1-07 controlled development rollout: verified the same local Compose
  PostgreSQL 16.14 target and zero-business-row baseline; created and fully
  restore-rehearsed a fresh ignored backup; explicitly applied `tasks.0002`
  then `reviews.0002`; and post-checked 30 migration records, validated
  constraints/FKs, valid/ready indexes and unchanged data. Fixture-free
  development smoke passed without a `500` or row/session change. Current
  isolated results pass Task 33/33, Auth/API 29/29, Workspace 140/140 and full
  PostgreSQL 202/202. Production and every other persistent target remain
  untouched.
- HT-INV-P2-04 Profile Invitation implementation: Profile-scoped digest-only
  invitations, seven-day lifecycle, delivery state, role ceilings, locked
  create/revoke/resend/accept/decline services, safe membership
  create/reactivation, rejoin Workspace-access revocation, audit, abuse
  controls, and six authenticated API route shapes. Per-invitation recipient
  proof requires the uniquely matching current account email plus the delivered
  one-time credential; it does not claim global email verification. Targeted
  Invitation 39/39 and full PostgreSQL 241/241 pass. Additive
  `workspace.0004` first remained gated from persistent rollout at this
  implementation checkpoint.
- HT-DB-P1-08 controlled Invitation development rollout is complete. It
  verified the PostgreSQL 16.14 development target and zero-business-row
  baseline, retained a verified custom-format backup, completed and removed an
  isolated restore/apply rehearsal, then applied only `workspace.0004` at
  2026-10-23 05:09:39.628419 UTC. Development now has 31 migrations and an
  empty 22-column Invitation table with validated constraints/FKs and
  valid/ready indexes; all pre/post counts are unchanged. Fixture-free direct
  health/CSRF and anonymous Profile/Workspace/membership/Invitation route
  smoke passes without a 500, sensitive-data disclosure, or mutation.
  Authenticated Invitation success paths were not run on persistent
  development. Current isolated Invitation 39/39, Auth/API 29/29,
  Workspace/RBAC/Task/Review 173/173, and full PostgreSQL 241/241 reruns pass;
  every test database and the temporary runner were removed while the retained
  host backup remains Git-ignored. The original development PostgreSQL
  container was running at task start and remains intentionally running.
- HT-AUTH-P1-02 account-security implementation is complete in source:
  current-email-bound verification state, digest-only purpose-bound
  verification/reset tokens, transactional rotation/expiry/replay handling,
  reset credentials bound to an encoded-password-state fingerprint,
  configured-mail delivery, audit, authenticated verification APIs, public
  HTTP-status/body-neutral reset APIs, Django password validation, and session
  invalidation after reset. Email changes revoke both pending purposes even for
  `A -> B -> A`; normal password saves revoke pending reset tokens and direct
  queryset changes fail the fingerprint check. Reset confirmation has separate
  token `10/hour` and client-address `30/hour` throttles, and malformed Unicode
  reset/Invitation inputs fail closed. Existing registration/login and Profile
  Invitation behavior remain available to unverified legacy Users. Additive
  `accounts.0002` has no backfill. Its implementation-gate isolated evidence
  passed account security
  44/44, Auth/API/Invitation 113/113, Workspace/RBAC/Task/Review 173/173, and
  full PostgreSQL 286/286 plus dependency/system/migration-drift/diff checks.
  **REAL EMAIL DELIVERY NOT VERIFIED**; request timing is not equalized and
  cache throttles remain process-local.
- HT-DB-P1-09 controlled account-security development rollout has applied
  exact `accounts.0002` at `2026-10-24 06:30:28.634074 UTC` after fresh backup,
  full archive read, isolated restore, exact legacy-row comparison and additive
  migration rehearsal. PostgreSQL 16.14 `hustlytasker_db` now has 32 migrations,
  nullable User verification columns and an empty AccountSecurityToken table,
  validated constraints/indexes and zero orphan FKs. Existing 3 active Users,
  2 Sessions and business/AuditLog rows are unchanged; no User was auto-verified.
  Direct development smoke passes 45 read-only CSRF-enforced requests,
  including Task/Review anonymous boundaries and an extra CSRF bootstrap.
  Authenticated success is covered only on isolated fixtures. Current isolated
  security 44/44, Auth/API 29/29, Invitation 40/40, Workspace/RBAC 140/140 and
  Task/Review 33/33 PASS. Those completed runs were reused after resume with
  unchanged source/schema; final full PostgreSQL rerun passes 286/286 in
  197.049s, exit 0, with a retained ignored log. Final checks, exact legacy-row
  preservation, and cleanup pass: no test/rehearsal database or runner remains,
  while the verified host backup is retained and development remains running.
  HT-DB-P1-09 is COMPLETE / OWNER REVIEW GATE.
  This task changes no source, migration file, API contract or business rule.
- HT-TEST-P1-01 adds dedicated `config.test_settings`/test environment and
  shared `scripts/test_backend.py` for dependency/system/model-drift/graph/
  history/full-chain checks and full/targeted serial tests. The core creates
  a uniquely marked owned DB and validates cluster/role/marker before cleanup;
  existing DBs and non-fresh targets are refused. Test settings do not use
  development environment/secrets or `.env`; normal session/CSRF/password
  behavior remains intact and mail is locmem. Local PowerShell+test Compose
  provisions a separate tmpfs PG16 cluster/internal network and Python 3.12
  runner with read-only source, no published PG port/persistent volume, and
  verified run-ID cleanup. CI uses a fresh job-local PG16 service on a random
  port, read-only repository permissions, no deploy or production secrets,
  and the same core command. Guards 14/14 (0.513s), targeted API 10/10
  (0.044s), and full PostgreSQL 286/286 (166.382s) PASS. Required dependency/
  Django/migration-chain checks and PowerShell/Compose/actionlint/diff validation
  pass. Intentional nonexistent-label failure propagates exit 1 and cleans;
  owned interruption fixtures clean while a wrong-repository fixture is
  refused. Original development User/Session fields match before/after in
  memory, with 32 migrations, 3 Users/2 Sessions and zero tokens unchanged.
  No owned test resources remain. **LOCAL TEST HARNESS VERIFIED — REMOTE RUN
  NOT VERIFIED**. CI implementation does not imply remote GitHub success.


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

- Owner review of completed HT-FE-P3-01 before broader frontend business screens.
  Typecheck/lint/build/mock96/real6/responsive/keyboard/axe and final safety checks
  pass; this is not a production-deployment claim. Project A/B′ scope remains pending
  Owner decision; the older bundled proposal is superseded and no Project
  implementation is authorized.
- Remote GitHub CI execution remains unverified; the local test harness and
  workflow implementation are already complete.
- Applying the Profile schema to any environment other than the approved
  development database. Each target still requires its own inventory, backup,
  risk review, and authorization. Development has applied `workspace.0002` and
  `workspace.0003`.
- Applying `workspace.0003_workspace_lifecycle_and_period` to production or any
  persistent environment other than the specifically approved development
  database. Development completed that rollout on 2026-10-20 and subsequently
  completed the Task/Review rollout through HT-DB-P1-07; that historical
  checkpoint had 30 migrations, 3 active Users, 2 sessions, zero checked business
  rows, and no leftover test/rehearsal database. Later rollout state is recorded
  in the current checkpoint above. Every other target still requires separate
  inventory, backup, risk review, and authorization.
- Cross-domain Client/Finance/Audit selectors, external Client/Guest review,
  Task soft delete/retention, Marketplace/media upload, and Payroll
  rules. Internal Task/Review enforcement and its controlled development
  migration are complete; these adjacent product domains remain separate.
- Comment full text revision history/mentions and broader notification
  email/push/worker/retention features; current foundation is limited to scoped
  discussion and atomic personal database notifications.
- Account deactivation service that preserves last-owner invariants across
  Profiles and revokes established sessions
- Applying `workspace.0004_profileinvitation` to production or any persistent
  target other than the specifically authorized development database. Each
  target still requires separate authorization, inventory, backup, rehearsal,
  plan review, smoke, and regression evidence.
- Real SMTP/provider verification, a shared production throttle cache,
  invitation inbox/global-verification coupling, automated invitation retention
  purge, general Profile CRUD/membership API, Workspace self-leave, Project,
  Client/Finance tenant migrations, public-link replacement, and broader
  soft-delete services
- Frontend business screens beyond the completed HT-FE-P3-01 foundation;
  HT-FE-P3-02 is proposed only, pending Owner review and scope.
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
Profile Invitation is implemented in source and isolated PostgreSQL tests.
Its `workspace.0004` development apply/schema/smoke gates are verified under
HT-DB-P1-08, and its current isolated regression and cleanup gates also pass.
General Profile CRUD/membership, self-leave, full cross-domain RBAC, other
business APIs, real provider integration, and every non-development rollout
remain separately gated regardless of roadmap task numbering.


## AI Development Instructions

When continuing development:

1. Read root `AGENTS.md` and `documentation/HANDOVER.md` first.
2. Read affected documentation and check current phase before coding.
3. Do not recreate completed components.
4. Preserve existing architecture.
5. Explain changes before implementation.
