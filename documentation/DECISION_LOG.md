---

# Decision: Backend Architecture Setup

Date:

2026-08-08


Decision:

Use Django modular architecture.


Structure:

backend/apps/

with separated business domains.


Reason:

The system contains multiple modules and requires scalability.


---

# Decision: Database Technology

Date:

2026-08-08


Decision:

Use PostgreSQL with Docker.


Reason:

- Free
- Production compatible
- Easy deployment
- Suitable for Django


---

# Decision: Database Design Process

Date:

2026-08-08


Decision:

Complete DATABASE_SCHEMA.md before creating Django Models.


Reason:

Avoid database migration problems and redesign later.


---

# Decision: Authentication Foundation Uses Django Sessions

Date:

2026-10-14


Status:

Accepted for HT-AUTH-P0-01


Decision:

Use Django server-side sessions with DRF `SessionAuthentication` for the
initial authentication API. Register and login are public but explicitly
CSRF-protected; logout and current-user lookup require an authenticated
session. Logout revokes only the current session.


Reason:

- The active requirement describes creating a session after login.
- Django sessions, CSRF middleware, password hashing, and session rotation are
  already part of the current architecture.
- This choice adds no token dependency, blacklist table, or migration.
- The planned frontend does not yet have a cross-origin or native-client
  contract. A same-origin session flow is the smallest safe foundation.


Consequences:

- Browser clients must bootstrap and submit a CSRF token on unsafe requests.
- Session cookies remain HttpOnly, SameSite `Lax`, and Secure according to the
  environment configuration.
- JWT, cross-origin credentials/CORS, logout-all, activation/OTP, and password
  recovery remain separate decisions and are not implied by this foundation.
- Register creates an active user but does not create a session, Profile, or
  Workspace. Activation must be added before claiming full F01 completion.


---

# Decision: DRF API Boundary and Public Liveness Endpoint

Date:

2026-10-15


Status:

Accepted for HT-API-P0-03


Decision:

All endpoint views below `/api/` use Django REST Framework and inherit its
authenticated-by-default policy. Every public API endpoint must declare
`AllowAny` explicitly and pass a focused security review before joining the
public allowlist. `/admin/` remains outside the DRF boundary and continues to
use Django Admin authentication and authorization.

Provide `/api/health/` as a public, JSON-only liveness endpoint. It bypasses
authentication, sessions, CSRF enforcement, and throttling; performs no
database access; returns `{"status":"ok"}` with `200 OK` for `GET`; and marks
responses `Cache-Control: no-store`. Standard `HEAD` and `OPTIONS` handling is
retained. All other methods return `405 Method Not Allowed`.


Reason:

- A single DRF boundary prevents API endpoints from silently bypassing the
  global authentication and response policies through plain Django views.
- Explicit `AllowAny` declarations make the public attack surface reviewable.
- Process monitoring needs a deterministic liveness signal that remains
  independent of PostgreSQL and does not disclose internal dependency state.
- A minimal response and no-store policy reduce information leakage and stale
  monitoring results.


Consequences:

- The public allowlist currently consists of `/api/health/` and the explicitly
  public CSRF, registration, and login endpoints under `/api/auth/`.
- `/api/health/` proves request-stack liveness only; it does not prove database
  readiness. A future readiness check requires a separate endpoint and failure
  contract.
- `HEAD` and `OPTIONS` are supported by DRF. `POST`, `PUT`, `PATCH`, `DELETE`,
  and `TRACE` return `405 Method Not Allowed`.
- The former `/api/test/` route is removed and returns `404 Not Found`.
- Adding another public API requires an explicit permission declaration,
  allowlist update, security review, and contract tests.


---

# Decision: Profile Tenant Root and Workspace Operational Scope

Date:

2026-10-16


Status:

ACCEPTED (`HT-DATA-P2-01`, owner approval 2026-10-16)


Scope:

The architecture decision is accepted. Its first additive implementation is
the separate `PROFILE/WORKSPACE SCHEMA FOUNDATION` task. That implementation
does not authorize Workspace APIs, full RBAC, Project/Client/Finance schema,
public-link flows, frontend work, or the detailed Task/Review workflow.


Authoritative approved decision:

1. `Profile` represents a company or working group and is the tenant root.
   Each Profile can contain many monthly operational Workspaces.
2. A global User may belong to multiple Profiles and switch navigation
   context. A selected Profile never proves authorization; every backend
   operation checks actual active membership.
3. Profile roles are `OWNER`, `ADMIN`, and `MEMBER`. Active Profile Owners and
   Admins administer every Workspace in that Profile. An ordinary Profile
   Member accesses only explicitly assigned Workspaces. Nothing is inherited
   across Profiles, and Workspace membership remains an independent layer.
4. A Profile may have multiple equal Owners and must retain at least one
   active Owner. Owner changes require transaction/concurrency protection.
   An Admin cannot appoint, demote, deactivate, or remove an Owner.
5. Joining a Profile requires accepting an invitation. An Owner/Admin may
   directly add a User to a Workspace only when that User already has active
   Profile membership. Duplicate active memberships are forbidden and
   important membership changes produce audit events.
6. Client belongs to Profile. A Client may have many Projects; a Project may
   span several monthly Workspaces and link Tasks from those Workspaces. A
   Task still belongs to exactly one Workspace. Any Task Client, Project, and
   Workspace references must resolve to the same Profile.
7. Invoice belongs to one monthly Workspace and references a Client from the
   same Profile. A Workspace may contain multiple Invoices. Payment belongs to
   Invoice. Cross-Profile finance links are forbidden. Invoice numbering and
   detailed billing workflow remain undecided.
8. Client Portal supports both authenticated accounts and secure links.
   Client-portal and guest-review links are separate principals; credentials
   are capability-scoped, expiring, revocable, and stored only as hashes. A
   Client account receives no internal Profile/Workspace membership by
   implication. Exact capabilities and default expiries remain future work.
9. Soft delete is the default target for Profile, Workspace, Client, Project,
   and Task. Hard delete is controlled; Invoice, Payment, and AuditLog are
   protected according to the eventual retention policy. A departing User
   must not cascade-delete business data. Retention periods and automated
   purge are not approved.
10. Every target database is inventoried before migration. Existing rows are
    never assumed absent and unknown rows are never assigned a guessed
    tenant. Risky changes require backup and rehearsal. Only new migrations
    after applied `0001` files are allowed.
11. The approved high-level workflow is assignment, execution, Deliverable
    submission, Review, then either approval/completion or revision and
    resubmission. Detailed states, approval permissions, and payroll trigger
    remain a separate task and are not part of schema foundation.


Implementation boundary at this checkpoint:

- **IMPLEMENTED NOW IN SOURCE:** `Profile`, `ProfileMembership`, Profile roles,
  at most one active User/Profile membership while retaining inactive history,
  role check/indexes, a transitional nullable `Workspace.profile`, protected
  Workspace owner deletion, Profile creation with an initial Owner,
  transactional/locked last-owner changes, one-way Workspace tenant mapping,
  and audited direct-add of an existing active Profile member to a Workspace.
- **MIGRATION STATE:** additive
  `workspace/0002_profile_workspace_foundation.py` exists and has run only on
  disposable PostgreSQL test databases. It has not been applied to the
  development database. The read-only development inventory found 0 business
  rows and 3 User rows; this does not authorize assuming another environment
  is empty.
- **APPROVED TARGET — NOT IMPLEMENTED:** invitation records/APIs, Project,
  Client/Profile migration, Workspace-scoped Invoice, link replacements,
  soft-delete fields/services, tenant-aware RBAC/querysets, and detailed
  Task/Review or billing workflows.
- Authentication remains Django session authentication and no API contract
  changes in this decision.
- **SERVICE BOUNDARY:** locked foundation services preserve the usable
  last-Owner and Workspace-owner invariants for supported writes. Direct
  `ProfileMembership` ORM/bulk mutation or direct `User.is_active` changes can
  bypass them; no account-deactivation workflow was added because User/auth
  changes are outside this task. Future account/membership lifecycle work must
  close that path before claiming a global invariant.
- **VERIFICATION CHECKPOINT — 2026-10-17:** existing legacy Workspace saves now
  lock the persisted row before validating a null Profile, so a stale save
  cannot undo a concurrent explicit mapping. Cross-Profile negative tests
  confirm that manager authority is scoped to one Profile. Targeted Workspace
  tests pass 32/32 and the full PostgreSQL suite passes 61/61; development
  remains on `workspace.0001` after read-only inventory before and after tests.


The material below is retained as the historical design rationale that led to
the approval. Where proposal wording conflicts with the authoritative decision
above, the approved decision controls.


Evidence classification:

- `documentation/ORIGINAL_REQUIREMENTS.md` is the current capability-level
  product requirement. It explicitly describes `User → Profile → Workspace`
  and workspaces used by a selected profile/team.
- `reference/original_document/00-discovery/` is a forensic snapshot of the
  legacy Next.js/Prisma application. It is evidence of prior behavior, not a
  schema to copy into Django verbatim.
- `reference/original_document/02-migration/` is historical Spring research
  and does not authorize replacing Django.
- The active Django source is authoritative for what exists today.


Pre-implementation source findings (historical audit):

- `Profile` does not exist. `Workspace` has a required `owner` FK to `User`
  and `WorkspaceMember` independently permits role `OWNER`; no invariant keeps
  those two ownership representations aligned.
- `Task` is scoped through `Workspace`. Assignment, comment, upload, and
  review actor FKs do not prove that the user belongs to that workspace.
- `Client`, `ShareLink`, `Invoice`, `Payment`, and `AuditLog` have no reliable
  Profile/Workspace ownership path.
- There is no Workspace invitation lifecycle, tenant-aware queryset/service,
  Workspace/RBAC API, or object permission implementation.
- Deleting several actor/owner rows then cascaded into business records;
  detailed retention policy had not yet been approved.


Options considered:

1. **Workspace as tenant root.** This is the smallest change to the current
   Django schema, but it makes the same entity both the durable agency/team and
   a monthly operational period. It also makes cross-month Client, CRM,
   finance, and membership history awkward and conflicts with the documented
   `Profile → Workspace` requirement.
2. **Profile/Organization as tenant root; Workspace as child.** This requires
   additive models and a reviewed data migration, but matches the requirement,
   preserves a durable team boundary across monthly workspaces, and provides a
   canonical home for CRM, finance configuration, and tenant administration.
3. **Profile as the only work scope.** This would discard the existing
   Workspace/Task relationship and the monthly-workspace workflow, causing the
   largest rewrite. It is not recommended.

Comparison against the required decision criteria:

| Option | Business fit | Model impact | Authentication impact | Extensibility | Security/data isolation | Migration complexity |
|---|---|---|---|---|---|---|
| Workspace is tenant root | Low-to-medium: preserves today's Task path but conflicts with the required Profile/team above monthly Workspaces. | Smaller change around Workspace/Task, but Client, Finance, ShareLink, and AuditLog still need new Workspace ownership paths. Shared Client history would be duplicated or coupled to one period. | Session authentication and global User can remain; authorization would use only Workspace membership. | Weak for durable teams, cross-month CRM/finance, organization settings, and many operational periods. | A single scope is conceptually simple, but duplicating or sharing cross-month records creates ambiguous boundaries and IDOR risk. | Medium, not low: Task data maps readily, but current Client/Finance/Audit rows still have no trustworthy Workspace mapping. |
| Profile/Organization is tenant root; Workspace is child | High: matches `User → Profile → Workspace` and the monthly operational workflow in the current requirement/reference. | Adds Profile/ProfileMembership, `Workspace.profile`, and Profile ownership for durable domains while retaining the existing Task → Workspace path. | No User or session change. Authorization adds Profile membership plus explicit Workspace participation on top of authenticated identity. | Strong for multiple Workspaces, durable CRM/finance, future tenant settings, and audit partitioning. | Gives every business object one canonical Profile path while allowing stricter Workspace scope; layered permissions and negative IDOR tests are required. | High but additive and controllable: nullable FKs, explicit mapping, backfill validation, then constraints. Existing Client/Audit rows require owner input. |
| Profile is the only work scope | Low: removes the explicitly documented monthly Workspace layer and conflicts with current Task relationships. | Largest rewrite: replace or deprecate Workspace, WorkspaceMember, and Task ownership paths and migrate all dependent review data. | Global session authentication can remain, but all current Workspace authorization concepts must be replaced with Profile membership. | Supports durable tenancy but loses an explicit operational/period boundary and makes per-Workspace participation/reporting harder. | One final boundary may be simple, but the broad transition creates a large window for incorrectly reassigned rows and authorization regressions. | Highest: destructive relationship rewrite, broad data reassignment, compatibility period, and substantially larger regression surface. |

On balance, the Profile-root/Workspace-child option costs more to migrate than
keeping Workspace as root, but materially less than eliminating Workspace. It
is the only option that matches the confirmed business hierarchy without
discarding working Workspace/Task relationships. The migration plan below
reduces that risk by remaining additive until mappings and constraints are
verified.


Accepted target (historical proposal rationale):

- Use `Profile` as the canonical model for a company or working group and as
  the tenant root. Keep `User` as a global identity; do not add tenant fields
  to the authentication identity itself.
- A Profile contains one or more Workspaces. A Workspace is an operational
  scope/period (the outsource material describes monthly workspaces), not an
  independent tenant.
- Use `ProfileMembership` for User ↔ Profile access.
  Retain `WorkspaceMember` for explicit Workspace participation.
- Prefer one canonical owner representation at the Profile level. Deprecate
  `Workspace.owner` only after data has been backfilled and all code has
  switched; do not maintain an owner FK and an unrelated OWNER membership as
  permanent independent truths.
- A user may belong to multiple Profiles. Any remembered/default Profile is
  navigation state only and must never be accepted as authorization evidence.
- A user may hold independent active `WorkspaceMember` rows in multiple
  Workspaces, including multiple Workspaces inside the same Profile. Enforce
  one membership per `(workspace, user)`; role, lifecycle, and revocation are
  evaluated separately for each Workspace. Access in one Workspace never
  grants access to another merely because both rows share a User or Profile.
- Cross-Profile Workspace membership is valid only when the same User also has
  the required active Profile membership in each Profile. A selected/current
  Workspace is navigation context, not authorization evidence. Profile
  OWNER/ADMIN may administer all Workspaces in their Profile; ordinary Profile
  members require explicit Workspace participation. Action-level content
  capabilities remain for the RBAC task.


Accepted ownership boundaries:

| Domain object | Canonical accepted boundary | Notes |
|---|---|---|
| User/session | Global identity | Session authentication stays unchanged. |
| Profile/ProfileMembership | Profile | Tenant administration and durable team membership. |
| Workspace/WorkspaceMember | Profile → Workspace | Operational period and explicit workspace participation. |
| Task/Assignment/TaskComment | Workspace | Profile is derived through Workspace. |
| Deliverable/Review | Task → Workspace | Uploader/reviewer must be authorized in the same workspace. |
| Client/CRM | Profile | Client history must survive and span monthly workspaces. |
| Project | Profile + Client | May span monthly Workspaces through Tasks; same-Profile invariant required. |
| Invoice/Payment | Workspace → Profile; Invoice → Client; Payment → Invoice | Invoice Client must share the Workspace Profile; numbering/billing details pending. |
| Payroll/performance | Workspace | Monthly operational data; also derives Profile. |
| Client portal link | Client → Profile | Separate from review-share credentials. |
| Review share link | Review asset/task → Workspace | Separate credential and capability set from client portal. |
| Notification | User, optional Profile/Workspace context | Recipient ownership and tenant navigation context are different concerns. |
| AuditLog | Explicit Profile; optional Workspace; nullable actor | Global auth/system events need an explicitly distinguishable null tenant. |


Accepted principal separation and pending Workspace capability detail:

- Profile roles: `OWNER`, `ADMIN`, `MEMBER`.
- Workspace roles: proposed `ADMIN`, `EDITOR`, `VIEWER`; the exact mapping from
  current `OWNER/ADMIN/MEMBER/VIEWER` requires owner approval.
- `CLIENT` and `GUEST_REVIEWER` are external token principals, not internal
  Workspace roles. A legacy Workspace `GUEST` and an unauthenticated guest
  reviewer are not the same actor.
- Profile OWNER/ADMIN administer Profile workspaces while ordinary Profile
  members require explicit active `WorkspaceMember` access. Exact content
  read/write capabilities belong to the later RBAC contract.

Requirement-to-capability matrix (design evidence, not an implemented
permission contract):

| Requirement actor | Capabilities explicitly confirmed by `ORIGINAL_REQUIREMENTS.md` | Accepted principal/scope | Remaining implementation detail |
|---|---|---|---|
| Owner | Manage Workspaces, members, Tasks, and finance. | Internal Profile OWNER; multiple equal Owners are accepted and last-owner protection is required. | Exact action capabilities, hard-delete authority, and retention duration. |
| Admin | Administer Workspace, assign user permissions, approve workflow, and invite Workspace members. | Internal Profile/Workspace membership; Profile ADMIN administers every Workspace but is never equivalent to global Django staff. | Exact content read/write capabilities; Admin cannot appoint/remove an Owner. |
| Member / Editor | Receive and execute Tasks, upload deliverables, and update status; Editor can claim available Tasks. | Proposed ordinary Profile member plus explicit Workspace `EDITOR` participation. | Whether `Member` and `Editor` are one role or two, allowed Task transitions, and review/claim concurrency rules. |
| Viewer | No Viewer capability is defined by the outsource requirement; `VIEWER` exists only in the current Django `WorkspaceMember` choices. | No proposed capability may be assumed merely from the current enum. | Keep/remove/rename the role and define its read scope before RBAC implementation. |
| Guest Reviewer | Review a product through a public link without an account. | External, capability-scoped `ReviewShareLink` principal; not a membership role. | Exact visible fields, allowed decision/comment actions, expiry, revoke, and identity/audit requirements. |
| Client | View the portal and deliverables; approve or request changes. | Client Portal supports account and secure-link flows, separate from guest review and internal membership. | Exact visible history/actions, account-linking flow, default expiry/rotation, revoke, and audit contract. |

Capabilities not explicitly confirmed above remain denied until their business
rule, tenant scope, and tests are approved. This matrix deliberately does not
authorize Django permission classes or role constants in this design task.


Accepted membership boundary and proposed future invitation lifecycle:

- **[CURRENT IMPLEMENTATION OF APPROVED FOUNDATION]** A new Profile starts with
  its creator as owner in one transaction.
- **[CURRENT]** The implemented partial unique constraint permits inactive membership history
  but allows at most one active row for each `(profile, user)` pair. Role/active
  changes through the foundation service are audited. The existing schema also
  keeps one `(workspace, user)` row; its complete lifecycle remains for the
  Workspace task.
- **[PROPOSED — NOT ACCEPTED]** Invitations are separate records with normalized email, requested role,
  inviter, tenant scope, hashed one-time token, expiry, and terminal state
  (`ACCEPTED`, `DECLINED`, `EXPIRED`, or `REVOKED`). Raw tokens are never
  stored or logged.
- **[PROPOSED — NOT ACCEPTED]** Acceptance locks/consumes the invitation and
  activates at most one membership using a still-unapproved
  create-versus-reactivate history strategy. Duplicate/concurrent behavior is
  defined for review in `RBAC_DESIGN.md`.
- **[APPROVED]** A User without active Profile membership cannot be directly added to a
  Workspace. The User must first accept a Profile invitation; a future combined
  UX may orchestrate both steps only while preserving that explicit consent.
- **[PROPOSED — NOT ACCEPTED]** Membership removal, leave, suspension, role change, and ownership transfer
  are service operations with audit events. The last owner cannot leave or be
  removed.
- **[APPROVED BOUNDARY; DETAILS PENDING]** Users accept/decline invitations when joining a Profile. The accepted direct
  addition exception applies only when an Owner/Admin adds an already-active
  Profile member to a Workspace.


Data-isolation invariants:

1. Every tenant business row has exactly one canonical path to a Profile.
2. Every Workspace belongs to exactly one Profile.
3. Every Task belongs to one Workspace; its Client/Project, if present, must
   belong to the same Profile.
4. Task creators, assignees, commenters, deliverable uploaders, and internal
   reviewers must hold the required active access to the Task's Workspace.
5. Public Client/guest access is limited by a hashed, expiring, revocable,
   capability-scoped credential; knowing a UUID is never authorization.
6. API reads start from a queryset already restricted to authorized Profile
   and Workspace IDs. Cross-tenant identifiers return a non-enumerating `404`
   rather than fetching globally and checking afterward.
7. Serializer input never supplies a trusted tenant ID. The server derives
   ownership from the authorized parent resource.
8. Role changes, invitation acceptance, ownership transfer, and last-owner
   checks execute transactionally and use locking where races are possible.
9. Django Admin is a platform-operations surface, not a substitute tenant UI.
   If non-superuser staff will use it, its querysets and FK choices need tenant
   scoping before that use is allowed.
10. Deletion must not cascade from a departed user into a whole tenant or from
    a Client into legally relevant finance history without an approved policy.
11. Audit records are append-oriented, retain tenant context and actor
    snapshots, and must not depend only on an unvalidated generic entity ID.


Database and application enforcement split:

- PostgreSQL should enforce unique active membership pairs, valid
  invitation-token hashes, required tenant FKs after backfill, and useful
  tenant indexes.
  Multiple Owners are accepted; the at-least-one-active-Owner invariant is
  preserved transactionally by the service layer.
- Cross-table invariants such as “assignee is a member of the Task workspace”
  require a transactional service/validator unless the final schema adopts
  deliberate composite keys. They must also have negative integration tests.
- Text choices alone are application validation, not PostgreSQL CHECK
  constraints. Critical role/status constraints should be explicit in the
  approved migration design.


Staged migration strategy under the accepted decision:

1. Freeze the final role, owner, delete/retention, Project, and finance-scope
   decisions. Back up and inventory the target environment; never edit any
   applied `0001_initial.py`.
2. Add `Profile` and `ProfileMembership`, plus nullable tenant FKs required for
   transition. Keep existing relationships operational during this additive
   phase.
3. Produce an explicit Workspace → Profile mapping. Do not automatically merge
   workspaces merely because they share an owner. A one-Profile-per-Workspace
   fallback is isolation-safe but should be used only with owner approval.
4. Create owner/profile memberships from the approved mapping and report all
   conflicts between `Workspace.owner` and OWNER membership rows.
5. Map Client rows explicitly because the current schema contains no reliable
   path from Client to Workspace/Profile. Derive Invoice and Payment scope only
   after Client mapping is validated. Treat unmappable rows as a blocking
   reconciliation list, not as a guessed tenant.
6. Derive Task/Review scope through Workspace and report users acting outside
   membership. Decide whether each mismatch is corrected, grandfathered, or
   rejected before enabling constraints.
7. Backfill explicit tenant context for tenant AuditLog rows where the target
   can be resolved; retain clearly classified global/auth events separately.
8. Validate orphan counts, duplicate memberships, owner count, cross-tenant
   references, token exposure, and delete behavior. Rehearse on a copy of
   representative data.
9. Add non-null constraints, uniqueness/check constraints, and indexes only
   after validation is clean. Switch services/querysets to the new canonical
   ownership path.
10. Remove/deprecate `Workspace.owner` or other transitional columns in a
    later migration only after code and data no longer depend on them.


Required tests across the full staged tenant rollout:

- Migration tests for an empty database and representative populated data,
  including a reversible additive phase and an explicit orphan report.
- Profile/Workspace membership and ownership-transfer concurrency tests.
- Full role matrix plus cross-Profile and cross-Workspace read/write/IDOR
  negative tests for every business resource.
- Actor-membership validation for Task creation, assignment, comments,
  deliverables, and reviews.
- Client/Invoice/Payment same-tenant tests and deletion/retention tests.
- Invitation expiry/revoke/replay/concurrent-accept tests and public-link token
  scope/revoke/expiry tests.
- Authentication regression tests proving that existing session login/logout
  behavior is unchanged.


Historical owner-review checklist (resolved or narrowed on 2026-10-16):

1. Approve Profile/Organization as tenant root and define its user-facing name.
2. Confirm that a User may join multiple Profiles and whether a default/home
   Profile is needed for navigation.
3. Approve the two-level role vocabulary and the mapping from current roles;
   decide whether Profile admins automatically access workspace content.
4. Choose one primary owner versus multiple owners, and approve ownership
   transfer/last-owner rules.
5. Decide whether every membership requires invitation acceptance, including
   existing users in the same Profile, and whether a Workspace invite may
   atomically create the required base ProfileMembership or must follow a
   separate Profile invitation.
6. Confirm that Client is Profile-scoped and whether Project is required; if
   it is, decide whether Projects span multiple monthly Workspaces.
7. Confirm Invoice/Payment scope, invoice-number uniqueness, and whether an
   invoice can aggregate Tasks across Workspaces.
8. Approve two separate public-link aggregates and their exact capability,
   expiry, rotation, and revocation policies; decide whether Client portal
   access is token-only, account-backed, or supports both through explicit
   separate flows.
9. Approve soft-delete/hard-delete/retention policies for Profile, Workspace,
   Client, Task, finance records, and AuditLog.
10. Approve the mapping/backfill source for every existing Workspace and
    currently unscoped Client/AuditLog row.
11. Separately approve canonical Task/Review states and the event that may
    complete a Task or trigger payroll; this is required before those APIs.


Resolution of that checklist:

- Items 1-11 are approved at the architecture level by the authoritative
  decision above. Profile is the canonical model term; any later UI label does
  not change the tenant boundary.
- The approved policy resolves Profile multi-membership, multiple Owners,
  Profile administrator inheritance, Profile invitation consent, Client and
  Project ownership, Workspace-scoped Invoice ownership, separate public-link
  principals, default soft delete, no guessed backfill, and the high-level
  Task/Review loop.
- Details intentionally still pending are: Workspace role/action capability
  mapping; invitation token expiry/revoke/reinvite behavior; invoice numbering
  and detailed billing workflow; Client Portal and guest-review visible fields,
  actions and default expiry; retention durations and purge authority; and
  exact Task/Review states, approvers, and payroll trigger.


---

# Proposal: Tenant Capability, Scoped Access, and Profile Invitation Contract

Date:

2026-10-17


Status:

`DESIGN READY — PENDING OWNER APPROVAL` (`HT-RBAC-DESIGN-P0-01`)


Scope and authority:

This entry records a reviewable proposal, not an accepted decision or runtime
permission contract. The 11 accepted Profile/Workspace decisions above remain
authoritative. Full matrix, invariants, planned routes, tests, and rationale
are in `documentation/RBAC_DESIGN.md`.


Current source findings:

- DRF authenticates by Django session and denies anonymous access by default,
  but no tenant authorization, Workspace route, or Invitation model/API exists.
- Profile Owner/Admin inheritance, ordinary-member explicit Workspace access,
  cross-Profile isolation, invitation consent, and direct-add boundaries are
  already approved.
- Existing `WorkspaceMember.OWNER/ADMIN/MEMBER/VIEWER` values do not themselves
  approve action capabilities. `Workspace.owner` is transitional data, not an
  authorization source.
- `update_profile_membership()` currently resolves membership ID globally;
  `add_workspace_member()` resolves Workspace ID globally and accepts an
  already-resolved unscoped target User before actor scope is established.
  They are not exposed by an API today, but both boundaries must be refactored
  so lookup/exception differences cannot disclose cross-tenant existence.
- Direct ORM/bulk writes, User deactivation, and global Django Admin operations
  can bypass foundation service invariants. These paths need a separately
  enforced service/platform-operator boundary before tenant APIs open.


Proposed least-privilege contract:

- Profile Owner governs Owners and the Profile, and inherits management of all
  same-Profile Workspaces. Profile Admin inherits Workspace management but no
  Owner governance. Profile Member receives no Workspace access without an
  explicit, effective Workspace membership.
- Retain Workspace Admin only as a narrow, single-Workspace content manager;
  treat Workspace Member as contributor/editor; keep Viewer disabled until its
  exact read/download scope is approved; deprecate Workspace Owner for new API
  assignments. These role choices remain pending.
- Resolve Profile from nested URL plus an active ProfileMembership on every
  ordinary tenant-resource request. Scope querysets before object lookup,
  derive Task/Review through Workspace, and resolve request-body relationships
  from same-tenant querysets. The only proposed pre-membership contexts are
  creation of a new Profile with its initial Owner and a recipient's own
  sanitized invitation inbox/accept/decline; neither grants access to an
  existing tenant before membership commits. Selected Profile state and
  knowledge of a UUID never grant access.
- Use the same `404` for nonexistent and outside-scope URL resources, `403` for
  a visible object whose action is forbidden, and generic field-level `400`
  for nonexistent/out-of-scope body references. A `409` domain-conflict shape
  remains to be approved.
- Sensitive mutations re-check authorization and same-tenant invariants inside
  transactions, use Profile-first lock ordering, and write material AuditLog
  events atomically. Application bulk/raw/direct writes are not supported
  mutation paths.
- Profile Invitation is separate from Workspace membership. Only after the
  recipient accepts and gains active Profile membership may a Profile
  Owner/Admin direct-add that User to a Workspace.
- Invitation credentials use at least 256 bits of randomness, store only a
  unique SHA-256 digest, are never logged/serialized, and are accepted or
  declined only by CSRF-protected POST from the matching authenticated User.
  Proposed terminal states are `ACCEPTED`, `DECLINED`, `EXPIRED`, and
  `REVOKED`; replacement rotates the token rather than reviving a record.
- Invitation acceptance locks Profile → Invitation → relevant memberships,
  activates at most one membership using the still-pending history strategy,
  consumes the invitation, and writes audit events in one transaction.
  Concurrent transitions have one terminal winner and replay never creates
  another membership.


Owner decisions required before implementation:

1. Keep Workspace Admin, deprecate Workspace Owner, and retain/disable Viewer
   with which exact field/download/comment scope.
2. Profile Admin authority over other Admins and Workspace memberships;
   Workspace/Profile soft-delete/restore authority.
3. Task visibility and whether inherited Profile managers require explicit
   Workspace membership for contributor attribution.
4. Invitation role ceiling; existing-only versus unregistered recipients;
   existing-account verification requirement; normalization/account linking;
   management ceiling; TTL, reinvite, throttling, and delivery.
5. Profile creation self-service eligibility/limits and its initial-Owner
   bootstrap exception; voluntary leave, rejoin row strategy, and how
   historical WorkspaceMember rows are prevented from silently restoring access.
6. Account-deactivation/User Admin policy that protects a usable Owner across
   every affected Profile.
7. Whether acceptance revalidates inviter authority, and whether a combined
   Profile+Workspace UX is desired while preserving two state transitions.
8. Non-enumerating error/`409` contract and any API superuser/platform-operator
   or tenant-aware Django Admin policy.
9. Terminal invitation/recipient-PII retention and hard-delete authority.

The detailed 16-question checklist in `RBAC_DESIGN.md` controls review scope;
this condensed list does not approve an omitted `R/P` or `P` capability.


Consequences:

- No proposal above may be converted into permissions, routes, models, or a
  migration until owner review.
- The current Authentication/Health API contract is unchanged, and no new
  `AllowAny` endpoint is proposed by default.
- Client/Project/Finance/Audit APIs remain closed until each domain has its
  approved canonical tenant path.
- The safe implementation order is: owner approval → target inventory/backup
  and separately approved `workspace.0002` apply → access context/scoped
  selectors → membership-service refactor and IDOR tests → minimal
  Profile/Workspace endpoints → additive Invitation migration/service/API →
  later Task and tenant-domain work.
- Any existing row that cannot be mapped from verified evidence remains an
  operational blocker for its constraint/backfill phase. It is not permission
  to synthesize a tenant mapping.
