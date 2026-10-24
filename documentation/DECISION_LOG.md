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
    resubmission. A Task reaches completion only after its Deliverable is
    approved. The later delegated decision requires explicit Review capability
    and forbids self-approval; detailed states and concrete internal reviewer
    authority were delegated to the later Task workflow task, while Client/
    Guest review and Payroll effects remain separate. The later accepted
    HT-TASK-P2-03 result is recorded at the end of this file.


Historical implementation boundary at the schema-foundation checkpoint
(superseded by the later checkpoints in this file):

- **IMPLEMENTED IN SOURCE AT THAT CHECKPOINT:** `Profile`,
  `ProfileMembership`, Profile roles,
  at most one active User/Profile membership while retaining inactive history,
  role check/indexes, a transitional nullable `Workspace.profile`, protected
  Workspace owner deletion, Profile creation with an initial Owner,
  transactional/locked last-owner changes, one-way Workspace tenant mapping,
  and audited direct-add of an existing active Profile member to a Workspace.
- **MIGRATION STATE AT THAT CHECKPOINT:** additive
  `workspace/0002_profile_workspace_foundation.py` exists and has run only on
  disposable PostgreSQL test databases. It has not been applied to the
  development database. The read-only development inventory found 0 business
  rows and 3 User rows; this does not authorize assuming another environment
  is empty.
- **APPROVED TARGET — NOT IMPLEMENTED AT THAT CHECKPOINT:** invitation
  records/APIs, Project,
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


Accepted principal separation and delegated Workspace compatibility mapping:

- Profile roles: `OWNER`, `ADMIN`, `MEMBER`.
- Effective Workspace roles are Admin, Editor, and Viewer. Without a schema
  change, current `WorkspaceMember.ADMIN` maps to Workspace Admin,
  `WorkspaceMember.MEMBER` maps to Editor, and `WorkspaceMember.VIEWER` maps to
  read-only Viewer. Legacy `WorkspaceMember.OWNER` fails closed and is never
  newly assigned.
- `CLIENT` and `GUEST_REVIEWER` are external token principals, not internal
  Workspace roles. A legacy Workspace `GUEST` and an unauthenticated guest
  reviewer are not the same actor.
- Profile OWNER/ADMIN administer same-Profile Workspace content while ordinary
  Profile members require explicit active `WorkspaceMember` access. Profile
  Admin does not inherit sensitive Finance capability. Workspace Admin is
  limited to its own Workspace; Editor performs work and Viewer is read-only.

Requirement-to-capability matrix (design evidence, not an implemented
permission contract):

| Requirement actor | Capabilities explicitly confirmed by `ORIGINAL_REQUIREMENTS.md` | Accepted principal/scope | Remaining implementation detail |
|---|---|---|---|
| Owner | Manage Workspaces, members, Tasks, and finance. | Internal Profile OWNER; multiple equal Owners are accepted and last-owner protection is required. | Exact hard-delete authority and retention duration. |
| Admin | Administer Workspace content and invite ordinary members. | Profile ADMIN administers every same-Profile Workspace, is never equivalent to global Django staff, cannot manage Owners, and receives no implicit sensitive Finance capability. | Workspace archive/restore is now implemented; exact Profile settings and other lifecycle actions remain outside this scope. |
| Member / Editor | Receive and execute Tasks, upload deliverables, and update status; Editor can claim available Tasks. | Ordinary Profile MEMBER plus explicit `WorkspaceMember.MEMBER`, interpreted as Editor. | Allowed Task transitions and review/claim concurrency rules. |
| Viewer | Read within an explicitly assigned Workspace. | `WorkspaceMember.VIEWER` is read-only and receives no mutation capability. | Exact visible fields and download/export rules remain denied until their endpoint contracts are reviewed. |
| Guest Reviewer | Review a product through a public link without an account. | External, capability-scoped `ReviewShareLink` principal; not a membership role. | Exact visible fields, allowed decision/comment actions, expiry, revoke, and identity/audit requirements. |
| Client | View the portal and deliverables; approve or request changes. | Client Portal supports account and secure-link flows, separate from guest review and internal membership. | Exact visible history/actions, account-linking flow, default expiry/rotation, revoke, and audit contract. |

Capabilities not explicitly confirmed above remain denied until their business
rule, tenant scope, and tests are approved. This matrix deliberately does not
authorize Django permission classes or role constants in this design task.


Accepted membership boundary and proposed future invitation lifecycle
(historical `HT-RBAC-P1-03` checkpoint):

The labels in this subsection record what was implemented at the 2026-10-17
RBAC design checkpoint. They are preserved as history and are superseded for
current Invitation behavior by the `HT-INV-P2-04` decision at the end of this
file.

- **[CURRENT IMPLEMENTATION OF APPROVED FOUNDATION]** A new Profile starts with
  its creator as owner in one transaction.
- **[CURRENT]** The implemented partial unique constraint permits inactive
  Profile-membership history but allows at most one active row for each
  `(profile, user)` pair. Role/active changes through the foundation service
  are audited. Workspace membership retains one `(workspace, user)` row and
  now uses `is_active` for locked, audited soft revoke/reactivation; self-leave
  and Profile invitation/rejoin policy remain downstream.
- **[APPROVED TARGET — NOT IMPLEMENTED]** Profile Invitations are email-bound,
  use a one-time expiring credential, enforce a role ceiling, and cannot grant
  `OWNER`. Owner may invite `ADMIN` or `MEMBER`; Admin may invite only `MEMBER`.
  Initial TTL is 7 days; resend/reinvite invalidates the old credential; initial
  limits are 5 attempts/email/24h and 30 invitations/inviter/24h. Terminal
  metadata is retained at least 12 months and no automated purge is authorized
  in `HT-RBAC-P1-03`.
- **[PROPOSED — NOT IMPLEMENTED]** The future record uses normalized email,
  inviter/tenant scope, a hash-only credential, expiry, and immutable terminal
  state. Raw tokens are never stored or logged.
- **[PROPOSED — NOT IMPLEMENTED]** Acceptance locks/consumes the invitation and
  activates at most one membership using a still-unapproved
  create-versus-reactivate history strategy. Duplicate/concurrent behavior is
  defined for review in `RBAC_DESIGN.md`.
- **[APPROVED]** A User without active Profile membership cannot be directly added to a
  Workspace. The User must first accept a Profile invitation; a future combined
  UX may orchestrate both steps only while preserving that explicit consent.
- **[PARTLY APPROVED TARGET — NOT IMPLEMENTED]** Membership removal, leave,
  suspension, role change, and ownership transfer
  are service operations with audit events. The last owner cannot leave or be
  removed/demoted/deactivated when that would violate the last-active-Owner
  invariant; detailed leave/rejoin history behavior remains downstream work.
- **[APPROVED BOUNDARY; DETAILS PENDING]** Users accept/decline invitations when joining a Profile. The accepted direct
  addition exception applies only when an Owner/Admin adds an already-active
  Profile member to a Workspace.
- **[APPROVED TARGET — NOT IMPLEMENTED AT THIS HISTORICAL CHECKPOINT]** A supported User-deactivation flow
  revokes continued session usability and never cascade-deletes historical or
  business data. This checkpoint treated persisted verified-email identity as
  a production dependency because a hashed token alone is not sufficient
  identity verification. `HT-INV-P2-04` later resolves its narrower acceptance
  boundary through an authenticated uniquely matching account plus a token
  actually accepted by the configured mail backend; it does not create or
  claim a global verified-email flag.


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
   Tenant-wide business-model access is limited to platform superusers until a
   separately reviewed tenant-scoped Admin implementation exists.
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
    complete a Task or trigger payroll; this was required before those APIs.
    HT-TASK-P2-03 later resolved the internal state/completion contract without
    defining a Payroll trigger.


Resolution of that checklist:

- Items 1-11 are approved at the architecture level by the authoritative
  decision above. Profile is the canonical model term; any later UI label does
  not change the tenant boundary.
- The approved policy resolves Profile multi-membership, multiple Owners,
  Profile administrator inheritance, Profile invitation consent, Client and
  Project ownership, Workspace-scoped Invoice ownership, separate public-link
  principals, default soft delete, no guessed backfill, and the high-level
  Task/Review loop.
- The later owner delegation approved the Workspace role compatibility mapping,
  read-only Viewer boundary, invitation role ceilings/TTL/resend limits/rates/
  minimum metadata retention, cross-tenant non-disclosure, and platform-only
  global Django Admin boundary. Those items are no longer pending.
- At this historical checkpoint, details intentionally still downstream were:
  exact Task visibility and
  contributor attribution; concrete Review role/states and payroll trigger;
  general Profile CRUD/settings, self-leave and Profile invitation/rejoin
  policy beyond the implemented bounded lifecycle; verified-email and
  unregistered-recipient onboarding; remaining Invitation delivery/history/
  purge mechanics; invoice numbering/detailed billing; Client Portal and Guest
  Review exact actions/default expiry; and broader retention/legal-hold policy.


---

# Decision: Tenant Capability, Scoped Access, and Profile Invitation Contract

Date:

2026-10-17


Status:

`ACCEPTED — APPROVED BY OWNER DELEGATION` (`HT-RBAC-DESIGN-P0-01`)


Scope and authority:

The owner explicitly delegated the remaining RBAC choices to the Technical
Advisor on 2026-10-17. This entry records the resulting accepted design and
authorizes only `HT-RBAC-P1-03` Tenant Access Context and Scoped Service
Foundation. At approval time this entry did not claim runtime implementation;
the verified implementation outcome is recorded below. It does not authorize a
new API, model, migration, data change, development migration apply, or
Invitation flow. The 11 accepted Profile/Workspace decisions above remain
authoritative. Full matrix, invariants, planned routes, tests, and rationale
are in `documentation/RBAC_DESIGN.md`.


Reconciliation checkpoint — 2026-10-17:

- All 11 accepted groups were compared line-by-line with `RBAC_DESIGN.md`.
  The recorded pre-correction statuses are: 1 `MATCH`, 2 `MATCH`, 3 `MATCH`,
  4 `CONFLICT`, 5 `MATCH`, 6 `NOT DOCUMENTED`, 7 `NOT DOCUMENTED`,
  8 `NOT DOCUMENTED`, 9 `NOT DOCUMENTED`, 10 `MATCH`, and
  11 `NOT DOCUMENTED`.
- Group 4 was a labeling conflict only: the proposal had marked the stronger
  “usable Owner” concept, including `User.is_active`, as approved. The approved
  rule is at least one active Owner membership. The later delegated
  deactivation/session target is recorded separately and cannot weaken that
  approved membership invariant.
- Groups 6–9 and 11 were compatible but incomplete. The design now explicitly
  records Client→Project cardinality, Workspace-scoped finance, both Client
  Portal access modes and independent link principals, complete delete/
  retention boundaries, and completion only after Deliverable approval.
- Group 10 was already represented in the rollout plan and is now also visible
  in the approved baseline. After these documentation corrections, all 11
  groups are `MATCH`; none requires owner re-approval. The detailed comparison
  table is in section 2.2 of `RBAC_DESIGN.md`.


Approved delegated decisions — 2026-10-17:

1. **APPROVED BY OWNER DELEGATION:** Profile Owner/Admin administer Workspace
   content within the same Profile. Sensitive Finance authority is not granted
   to Profile Admin implicitly.
2. **APPROVED BY OWNER DELEGATION:** An ordinary Profile Member must have a
   valid Workspace membership to access work in that Workspace.
3. **APPROVED BY OWNER DELEGATION:** Workspace Admin administers only its own
   Workspace; Editor performs work; Viewer is read-only.
4. **APPROVED BY OWNER DELEGATION:** Only an actor with Review capability may
   approve a Deliverable, and the submitter may not approve their own
   Deliverable. The concrete role/states were intentionally left to the
   dedicated Task/Review task and are now resolved by the later
   HT-TASK-P2-03 decision below.
5. **APPROVED BY OWNER DELEGATION:** Profile creation creates the initial Owner
   atomically in the same transaction.
6. **APPROVED BY OWNER DELEGATION:** Leave, deactivate, demote, or remove is
   rejected when it would violate the last-active-Owner invariant.
7. **APPROVED BY OWNER DELEGATION:** User deactivation must revoke continued
   session usability and must not cascade-delete business or historical data.
   The required account-lifecycle service is later implementation work.
8. **APPROVED BY OWNER DELEGATION:** A Profile Invitation is email-bound, uses
   a one-time expiring credential, enforces a role ceiling, and cannot grant
   `OWNER`.
9. **APPROVED BY OWNER DELEGATION:** Profile Owner may invite `ADMIN` or
   `MEMBER`; Profile Admin may invite only `MEMBER`.
10. **APPROVED BY OWNER DELEGATION:** Direct Workspace add applies only to a
    User with active ProfileMembership in that same Profile.
11. **APPROVED BY OWNER DELEGATION:** Invitation TTL is 7 days; resend/reinvite
    invalidates the previous credential; initial limits are 5 attempts per
    recipient email per 24 hours and 30 invitations per inviter per 24 hours.
12. **APPROVED BY OWNER DELEGATION:** Terminal Invitation metadata is retained
    for at least 12 months. No automated purge is implemented or authorized by
    `HT-RBAC-P1-03`.
13. **APPROVED BY OWNER DELEGATION:** Every current and future tenant API must
    not disclose cross-tenant object existence. Django Admin is a
    platform-operations surface, not tenant RBAC.
14. **APPROVED BY OWNER DELEGATION:** Until tenant-scoped Admin exists,
    tenant-wide Django Admin business-model access is restricted to platform
    superusers.

Compatibility boundary without a schema change:

- `WorkspaceMember.ADMIN` is effective Workspace Admin.
- `WorkspaceMember.MEMBER` is effective Editor.
- `WorkspaceMember.VIEWER` is effective read-only Viewer.
- Legacy `WorkspaceMember.OWNER` fails closed, is never newly assigned, and
  requires explicit later reconciliation if inventory discovers a row.
- Profile Owner/Admin may assign Workspace `ADMIN`, `MEMBER`, or `VIEWER`.
  Workspace Admin may assign only `MEMBER` or `VIEWER` within its own
  Workspace. No supported actor may assign Workspace `OWNER`.
- Under least privilege, Profile Admin may manage an ordinary Profile
  `MEMBER`; it cannot grant or alter Profile `ADMIN` or `OWNER`.

Historical production dependency and implementation boundary:

- Profile Invitation is not implemented by `HT-RBAC-P1-03`.
- At that checkpoint, persisted verified-email identity and reviewed account
  binding were required before enabling Profile Invitation in production. A
  hash-only token remains insufficient proof. The later authorized
  `HT-INV-P2-04` implementation uses the narrower per-invitation proof recorded
  below: an active authenticated account whose current normalized email is the
  sole account match plus a one-time token whose delivery state is `SENT`.
  This does not establish global email verification, and production operation
  still requires a real configured mail provider whose delivery has been
  verified.


Source findings at the design checkpoint before `HT-RBAC-P1-03` implementation:

- DRF authenticates by Django session and denies anonymous access by default,
  but no tenant authorization, Workspace route, or Invitation model/API exists.
- Profile Owner/Admin inheritance, ordinary-member explicit Workspace access,
  cross-Profile isolation, invitation consent, and direct-add boundaries are
  already approved.
- The delegated compatibility mapping now defines the effective meaning of
  `WorkspaceMember.ADMIN/MEMBER/VIEWER`; legacy `OWNER` fails closed.
  `Workspace.owner` remains transitional data, not an authorization source.
- `update_profile_membership()` currently resolves membership ID globally;
  `add_workspace_member()` resolves Workspace ID globally and accepts an
  already-resolved unscoped target User before actor scope is established.
  They are not exposed by an API today, but both boundaries must be refactored
  so lookup/exception differences cannot disclose cross-tenant existence.
- Direct ORM/bulk writes, User deactivation, and global Django Admin operations
  can bypass foundation service invariants. These paths need a separately
  enforced service/platform-operator boundary before tenant APIs open.


Implementation outcome — 2026-10-18:

- `backend/apps/workspace/access.py` implements resolver-produced immutable
  Profile/Workspace contexts, scoped selectors and DB-revalidated read/edit/
  member-management capabilities. Forged, cross-tenant, inactive and stale
  contexts fail closed.
- `update_profile_membership()` now establishes actor/Profile scope before
  target lookup, applies the approved Profile Admin ceiling, and preserves the
  locked last-active-owner/audit invariants.
- `add_workspace_member()` now resolves a scoped Workspace and active
  same-Profile `target_profile_membership_id`, enforces Profile/Workspace role
  ceilings, rejects legacy `OWNER`, and handles duplicate/concurrent adds with
  one stable conflict and no duplicate audit.
- Final PostgreSQL verification passed 51/51 targeted Workspace tests and
  80/80 full tests, plus dependency, compile, system and migration-drift checks.
- No model, migration, API route, authentication mechanism or development data
  changed; at that checkpoint, `workspace.0002` was unapplied to development.


Approved foundation contract and deferred follow-ons:

- Profile Owner governs Owners and the Profile, and inherits management of all
  same-Profile Workspaces. Profile Admin inherits Workspace management but no
  Owner governance. Profile Member receives no Workspace access without an
  explicit, effective Workspace membership.
- Retain Workspace Admin as a narrow, single-Workspace manager; treat
  Workspace Member as Editor; enable Viewer only as read-only; and treat
  Workspace Owner as legacy fail-closed data that no supported service assigns.
  Endpoint-specific Viewer fields/downloads remain denied until reviewed.
- Resolve Profile from nested URL plus an active ProfileMembership on every
  ordinary tenant-resource request. Scope querysets before object lookup,
  derive Task/Review through Workspace, and resolve request-body relationships
  from same-tenant querysets. The only proposed pre-membership contexts are
  creation of a new Profile with its initial Owner and a recipient's own
  sanitized invitation inbox/accept/decline; neither grants access to an
  existing tenant before membership commits. Selected Profile state and
  knowledge of a UUID never grant access.
- Never disclose cross-tenant object existence. The proposed HTTP mapping uses
  the same `404` for nonexistent and outside-scope URL resources, `403` for a
  visible object whose action is forbidden, and generic field-level `400` for
  nonexistent/out-of-scope body references. Exact shared error envelopes and a
  `409` domain-conflict shape remain for the API foundation task.
- Sensitive mutations re-check authorization and same-tenant invariants inside
  transactions, use Profile-first lock ordering, and write material AuditLog
  events atomically. Application bulk/raw/direct writes are not supported
  mutation paths.
- Profile Invitation is separate from Workspace membership. Only after the
  recipient accepts and gains active Profile membership may a Profile
  Owner/Admin direct-add that User to a Workspace.
- The future Invitation credential design uses at least 256 bits of randomness
  and stores only a unique SHA-256 digest. Credentials are never logged or
  serialized and are accepted or declined only by CSRF-protected POST from the
  matching authenticated User.
  Proposed terminal states are `ACCEPTED`, `DECLINED`, `EXPIRED`, and
  `REVOKED`; replacement rotates the token rather than reviving a record.
- The future Invitation acceptance service locks Profile → Invitation →
  relevant memberships, activates at most one membership using the
  still-pending history strategy,
  consumes the invitation, and writes audit events in one transaction.
  Concurrent transitions have one terminal winner and replay never creates
  another membership.


Resolution of the former owner-review checklist:

- The Workspace role vocabulary/action ceiling, Profile/Workspace inherited
  management boundary, initial-Owner transaction, last-active-Owner guard,
  User-deactivation target, invitation role/TTL/resend/rate/retention ceilings,
  cross-tenant non-disclosure, and global Django Admin boundary are accepted by
  owner delegation. They must not be sent back for re-decision.
- At this historical design checkpoint the concrete reviewer role and
  Task/Review states remained downstream. HT-TASK-P2-03 later fixed the
  internal manager/Editor split and state machine; external review and Payroll
  effects remain downstream.
- At the `HT-RBAC-P1-03` checkpoint, verified-email/account binding was a
  production dependency and Invitation was not implemented. This historical
  statement is superseded for the bounded `HT-INV-P2-04` acceptance proof by
  the later decision below; token hashing remains mandatory and is never a
  substitute for authenticated recipient matching or actual email delivery.
- Remaining downstream gates cover Task soft delete/cancellation/comments/
  Marketplace/media and external Client/Guest review; lifecycle policy beyond
  the implemented bounded Profile/Workspace
  archive/restore and Workspace-member revoke/reactivate behavior (including
  self-leave, retention/purge, and Profile-membership rejoin/history);
  Invitation onboarding,
  delivery, inviter revalidation, exact state/history and purge mechanics;
  exact API envelopes/platform-operator API bypass; Invoice numbering/billing;
  Client Portal/Guest Review capabilities/default expiry; and broader
  retention/legal-hold/purge policy. None blocks the scoped access/service
  foundation authorized here.


Consequences:

- `HT-RBAC-P1-03` implemented only reusable access contexts, tenant-scoped
  selectors/capabilities, scoped membership-service refactors, and regression
  tests under the accepted contract. This decision does not authorize routes,
  models, migrations, data changes, or Invitation implementation.
- At completion of `HT-RBAC-P1-03`, the Authentication/Health API contract was
  unchanged. The owner later authorized `HT-API-P1-04`, which added four
  read-only tenant routes with no new `AllowAny`; this chronology does not
  alter the accepted RBAC decision.
- Client/Project/Finance/Audit APIs remain closed until each domain has its
  approved canonical tenant path.
- The safe implementation order is: delegated design approval → access
  context/scoped selectors → membership-service refactor and IDOR tests →
  separately approved target inventory/backup and `workspace.0002` apply before
  any development Workspace API exercise → minimal Profile/Workspace reads →
  separately authorized schema-free Workspace write/member-manager slice →
  Owner-approved lifecycle/period schema and implementation → separately
  approved development application of `workspace.0003` → Invitation or later
  Task and tenant-domain work under their own gates.
- Any existing row that cannot be mapped from verified evidence remains an
  operational blocker for its constraint/backfill phase. It is not permission
  to synthesize a tenant mapping.


Operational rollout checkpoint — 2026-10-19:

- Owner authorized a development-only, condition-gated rollout of the existing
  `workspace.0002_profile_workspace_foundation` migration through HT-DB-P1-05.
  This does not change any accepted tenancy/RBAC decision or authorize a new
  migration/API.
- The target local Compose database was re-inventoried: 3 active Users and no
  Workspace or other checked business rows. No mapping was needed or
  synthesized.
- A Git-ignored custom-format backup passed hash, TOC, and full archive-read
  verification. An isolated full restore rehearsal reproduced the expected
  pre-migration state and its temporary database was removed.
- Runtime configuration was supplied only to disposable processes; no `.env`
  or secret was persisted/logged and no credential was reset. The exact plan
  matched the reviewed additive migration, after which `workspace.0002` was
  applied to development and its schema/constraints/data were post-checked.
- Direct development smoke and current PostgreSQL regressions passed (21/21
  targeted read API, 29/29 Authentication/API Foundation, 101/101 full suite).
  This closes only the authorized development rollout and does not change an
  architecture decision or authorize another target. It did not itself open a
  write/Invitation API; the later HT-WORK-P2-02 authorization is recorded
  separately below.


Historical Workspace write/member schema-free checkpoint — 2026-10-19
(superseded for current source behavior):

- After accepting HT-DB-P1-05, the Owner explicitly authorized
  `HT-WORK-P2-02` for the schema-free Workspace write and membership-management
  subset. This is implementation authorization under the existing delegated
  RBAC decisions, not approval of a new lifecycle, retention, period, rejoin,
  or deletion policy.
- At that checkpoint, endpoints included `POST` Workspace collection, `PATCH` Workspace
  detail, `GET`/`POST` Workspace members, and `PATCH` Workspace-member detail.
  Strict serializers allow only `name`/`description`,
  `target_profile_membership_id`/`role`, or `role` as applicable; Profile,
  transitional owner, actors, IDs, timestamps, and unknown fields remain
  server-controlled or rejected.
- Profile Owner/Admin may create and edit Workspaces and manage supported
  `ADMIN/MEMBER/VIEWER` assignments in their Profile. The assigned Workspace
  Admin may edit that Workspace's metadata and manage only `MEMBER/VIEWER`.
  Editor, Viewer, unassigned Profile Member, legacy Workspace `OWNER`, and
  platform staff/superuser flags grant no additional capability.
- Manager roster queries retain current actor authority in SQL, include only
  supported assignments backed by an active User and active same-Profile
  ProfileMembership, and return no User ID/email/username/PII. Locked services
  revalidate tenant scope and write atomic Workspace/membership AuditLog events.
  API mapping is fail-closed: invalid body `400`, visible forbidden action
  `403`, unknown/wrong-parent/out-of-scope URL resource `404`, duplicate direct
  add `409`.
- Verification passed 111/111 targeted Workspace tests, 29/29
  Authentication/API Foundation regressions, and 140/140 full PostgreSQL tests,
  plus Django system and migration consistency checks. No model, migration,
  authentication, or development-data change occurred; development remains at
  applied `workspace.0002` with 3 Users and zero business rows.
- At that historical checkpoint, no lifecycle decision had yet been inferred:
  `Profile` lacked an active lifecycle, `Workspace` lacked archive state and a
  canonical month/period, `WorkspaceMember` lacked active/history state, and no
  `workspace.0003` existed. The Owner subsequently approved the bounded
  schema-dependent behavior recorded below; broader retention, purge,
  self-leave, and Profile-membership rejoin policy remain separate.


Historical schema-dependent lifecycle/period source checkpoint — 2026-10-19:

- **APPROVED AND IMPLEMENTED IN SOURCE:** `Profile.status` and
  `Workspace.status` use `ACTIVE`/`ARCHIVED`. Profile archive/restore is
  Owner-only; Profile Admin cannot perform it. Profile Owner/Admin may
  archive/restore a same-Profile Workspace; Workspace Admin cannot. Archived
  rows remain tenant-scoped/readable, while an archived Profile blocks normal
  child writes and an archived Workspace blocks normal metadata/membership
  mutations. Hard delete is not exposed by the tenant API/service contract;
  existing platform/Admin destructive paths remain outside this task and
  require separate control.
- **APPROVED AND IMPLEMENTED IN SOURCE:** every supported new Workspace has an
  immutable canonical monthly `period` represented by the first day. A Profile
  may have at most one Workspace for a non-null period, including archived
  rows. Null exists only to preserve unresolved legacy rows; no backfill month
  is guessed, and direct ORM/bulk/raw paths that bypass supported validation
  remain outside the mutation contract.
- **APPROVED AND IMPLEMENTED IN SOURCE:** `WorkspaceMember.is_active` retains
  one `(workspace, user)` history row. DELETE soft-revokes effective access;
  later direct-add reactivates that same row with the requested permitted role.
  Actor ceilings, Profile-first locking, concurrent-conflict behavior, and
  material lifecycle/membership AuditLog events are enforced transactionally.
- Additive `workspace.0003_workspace_lifecycle_and_period` creates only the
  approved fields, checks, conditional Profile/period uniqueness, and indexes.
  An isolated PostgreSQL `0002 → 0003` migration test preserved legacy
  Workspace/WorkspaceMember and Task → Deliverable → Review relationships
  without assigning a period.
- Verification passed `pip check`, Django system check,
  `makemigrations --check --dry-run`, 140/140 Workspace tests in 79.278s, and
  169/169 full PostgreSQL tests in 82.920s.
- **ROLLOUT BOUNDARY:** the latest successful post-suite development inventory
  on 2026-10-19 showed 27 applied migrations with `workspace.0002` applied and
  `workspace.0003` absent, 3 Users and zero checked business rows/test
  databases. A read-only check on 2026-10-20 found the existing development
  PostgreSQL container stopped; it was not started or changed. Production was
  not touched. The source implementation status is therefore `IMPLEMENTATION
  COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`; this checkpoint is not
  permission to apply `0003` anywhere.


Controlled Workspace 0003 development rollout checkpoint — 2026-10-20:

- **OWNER AUTHORIZATION EXECUTED WITHIN BOUNDARY:** the Owner approved a
  condition-gated application of the existing
  `workspace.0003_workspace_lifecycle_and_period` migration to the identified
  development database only. The authorization did not include production,
  another target, a new migration, fixture creation, or feature implementation.
- Runtime identity, 27-migration pre-state, 3 active Users/2 sessions/zero
  business rows, physical schema, additive plan, fresh verified backup and full
  restore rehearsal all passed before apply. No tenant/month mapping was needed
  or synthesized.
- `workspace.0003` was applied successfully. Development now has 28 migrations;
  the four fields, three validated checks, partial unique Profile/month index
  and three lookup indexes are present and valid/ready. Inventory stayed
  unchanged and post-check found no anomaly or temporary database.
- Direct non-mutating development request-stack smoke and current isolated
  PostgreSQL regressions passed: 17/17 lifecycle/schema, 140/140 Workspace,
  29/29 Authentication/API Foundation, and 169/169 full suite.
- This closes only `HT-DB-P1-06` at its Owner review gate. It changes no
  tenancy/RBAC decision and authorizes no Invitation, Task/business feature, or
  rollout to another environment.


---

# Decision: Task Management and Internal Approval Workflow

Date:

2026-10-21


Status:

`IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`


Approved scope and business boundary:

1. A Task belongs to exactly one Workspace and derives exactly one Profile
   through that Workspace. Supported APIs do not move/re-parent a Task.
2. The internal state flow is `PENDING -> ASSIGNED -> WORKING -> REVIEW`.
   Internal approval moves the Task to `COMPLETED`; request changes moves it
   back to `WORKING` for revision/resubmission. A Task cannot complete before
   its latest submitted Deliverable is approved.
3. Profile Owner/Admin and an assigned Workspace Admin manage Tasks and perform
   internal Review in an active same-Profile Workspace. An ordinary active
   Profile Member with effective Workspace `MEMBER` (Editor) capability may
   execute only a Task for which they are the current active assignee.
4. The current active assignee alone starts and submits. An internal reviewer
   cannot approve or request changes on their own Deliverable. Only the latest
   submitted revision may be decided, and repeated/stale decisions are
   rejected.
5. All callers with effective Workspace read access may read the Task and its
   Deliverable/internal Review history. Viewer is read-only; an unassigned
   ordinary Profile Member receives no fallback access.
6. Internal Review is not Client Portal or Guest Review approval. It does not
   send work to a client and does not create Invoice, Payment, Payroll, or
   compensation calculations. Those contracts remain separate.
7. This slice has no arbitrary status update, public cancellation, hard delete,
   soft-delete implementation, Comments API, Marketplace/claim, actual file
   upload/media pipeline, external review, Invitation, Finance, frontend, or
   Authentication change.


Implementation/security consequences:

- SessionAuthentication, global `IsAuthenticated`, session CSRF, existing
  tenant access contexts and generic IDOR-safe `404` remain unchanged.
- Manager, execute and review capabilities are action-specific. Inherited
  manager authority never implies contributor attribution; execution still
  requires ordinary Profile Member + Workspace Editor + active Task assignment.
- State transitions, assignment replacement, revision allocation, Review
  creation, Task/Deliverable synchronization and AuditLog writes are atomic and
  revalidated under row locks. Audit failure rolls back the mutation.
- Actor references use `PROTECT`. Task/Assignment/Comment Admin is
  inspection-only, and Workspace hard delete is disabled in Django Admin to
  avoid cascade deletion of workflow history. This is bounded protection, not
  a full Task soft-delete/retention implementation.
- Public API output uses current ProfileMembership IDs for tenant attribution
  and omits global User ID/PII. A deactivated/stale membership serializes as
  null rather than exposing its historical tenant identifier.


Schema and migration decision:

- Only new additive migrations are used:
  `tasks.0002_task_workflow_foundation` and
  `reviews.0002_review_workflow_foundation`; no applied migration is edited.
- At most one current active TaskAssignment is enforced. During migration all
  legacy assignments become inactive so the system does not guess which row is
  current; new service-created assignments default active.
- New Deliverables use positive sequential revisions unique per Task. Existing
  Deliverables retain `revision=NULL`; migration does not invent order.
- One internal Review per Deliverable and status/priority/revision checks are
  database-enforced after apply.
- Before any persistent rollout, inventory invalid status/priority values,
  duplicate Reviews per Deliverable, legacy assignments and Deliverable
  revision state. A conflict requires explicit reconciliation/Owner review; no
  record may be silently deleted, deduplicated, activated or renumbered.


Current evidence and rollout boundary:

- Targeted Task service/API/migration verification passes 33/33 in 7.673s;
  existing Authentication/API/Workspace regression passes 169/169 in 87.783s;
  and final full PostgreSQL passes 202/202 in 92.343s. Dependency, Django
  system and migration-drift checks, test-database cleanup, and independent
  final code review pass.
- Development has `workspace.0003` but only `tasks.0001` and `reviews.0001`;
  both new workflow migrations remain unapplied. Neither development nor
  production migration apply is authorized by this task.
- Read-only `showmigrations` and final counts reconfirm that state;
  `migrate --plan` succeeds and lists only additive `tasks.0002` followed by
  `reviews.0002`. No migration was applied.
- Stop at `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`.
  A separate controlled rollout must identify
  the exact target, inventory, back up, review the plan, apply, smoke, and
  regress before claiming deployment.


---

# Decision: Profile Invitation and Membership Onboarding

Date:

2026-10-21


Status:

`IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`


Authority and scope:

The Owner explicitly authorized `HT-INV-P2-04` as a backend implementation
task. This decision applies the already-approved Invitation role, lifetime,
abuse-control, retention, tenancy, and consent boundaries without changing
Django SessionAuthentication or introducing a second authorization model. It
does not authorize a migration on a persistent development/production database
or any Client, Finance, Portal, frontend, or unrelated workflow work.


Accepted implementation contract:

1. Profile Owner may issue and manage invitations requesting `ADMIN` or
   `MEMBER`; Profile Admin may issue and manage only `MEMBER`. `MEMBER` is the
   default. Invitation never grants `OWNER`, Workspace roles grant no Profile
   invitation capability, and Django `is_staff`/`is_superuser` is not tenant
   authorization.
2. The lifecycle is `PENDING` to exactly one of `ACCEPTED`, `DECLINED`,
   `REVOKED`, or `EXPIRED`. The default TTL is seven days. A resend creates a
   new record and credential linked by immutable replacement history; it
   revokes an old still-pending record or replaces an expired record rather
   than reviving or extending the old credential.
3. Credentials contain at least 256 bits of cryptographic randomness. Only a
   unique SHA-256 digest is stored. Raw credentials are excluded from models,
   manager responses, AuditLog metadata, logs, documentation, and exception
   details and are single-use through locked terminal-state transitions.
4. Acceptance/decline requires an active authenticated User whose freshly read
   current email normalizes to the invitation email and resolves to exactly
   that one account. A pre-bound `recipient_user`, when present, must also be
   the actor. The invitation must have delivery state `SENT`, and the actor
   must present the one-time credential received through the configured email
   channel. These facts form proof scoped only to that invitation; they do not
   create or assert a persistent/global verified-email flag. Token possession
   is not authentication.
5. An invitation may be issued before its recipient account exists. After the
   recipient registers/signs in with the uniquely matching normalized email,
   the same authenticated-plus-email-delivered-token proof applies. Ambiguous
   case-insensitive account matches, changed/mismatching emails, inactive
   accounts, a non-`SENT` delivery, and a mismatching stored account binding
   fail closed.
6. No recipient inbox endpoint is exposed. Without a persistent global
   verified-email signal, listing invitations from only a self-asserted account
   email would be a wider disclosure than the one-invitation token proof. The
   public contract therefore exposes only authenticated token accept/decline
   actions and no anonymous preview/inspection route.
7. Acceptance never changes an existing active Profile membership. With no
   history it creates one membership at the requested role. With exactly one
   inactive non-Owner history row, it reactivates that same row only when its
   stored role exactly equals the invitation role. Multiple inactive rows, a
   role mismatch, or inactive `OWNER` history fail closed; history is not
   deleted or silently rewritten.
8. Rejoining a Profile does not restore historical Workspace authority.
   Acceptance locks and soft-revokes any still-active same-Profile
   `WorkspaceMember` rows for that User and writes audit events. A later
   Workspace direct-add remains a separate explicit manager action.
9. The original inviter's active same-Profile membership, active User, and
   authority for the requested role are revalidated when an invitation is
   accepted. Every manager mutation independently revalidates the current
   actor under locks. An archived Profile blocks create, revoke, resend, and
   acceptance; restoration never revives a terminal invitation.
10. Issuance enforces the approved rolling 24-hour ceilings of five
    invitations per normalized recipient email and 30 invitations per inviter.
    Create/resend also use authenticated/cache throttles, and accept/decline
    token attempts share an authenticated-user five-per-day throttle. Database
    counts and PostgreSQL locking protect the issuance ceilings; the default
    process-local cache remains an explicit multi-worker deployment limitation.
11. Terminal metadata follows the approved minimum 12-month retention policy.
    No automatic purge, anonymization schedule, or legal-hold rule is inferred
    by this task.
12. Delivery is scheduled with `transaction.on_commit`, so a rolled-back
    invitation is not emailed. The persisted state distinguishes `QUEUED`,
    `SENT`, and `FAILED`; a failed send is recorded and reported generically,
    never claimed as sent. Console, dummy, and file backends are refused for
    Invitation delivery; locmem is restricted to isolated testing. The source
    abstraction exists, but real SMTP/provider delivery is not yet verified.


Current API contract — six route shapes:

```text
GET/POST /api/v1/profiles/{profile_id}/invitations/
GET      /api/v1/profiles/{profile_id}/invitations/{invitation_id}/
POST     /api/v1/profiles/{profile_id}/invitations/{invitation_id}/revoke/
POST     /api/v1/profiles/{profile_id}/invitations/{invitation_id}/resend/
POST     /api/v1/invitations/accept/
POST     /api/v1/invitations/decline/
```

All routes retain SessionAuthentication, deny anonymous access, enforce CSRF
on unsafe methods, return non-cacheable responses, and use strict inputs.
Manager querysets are Profile-scoped; Admin visibility is additionally limited
to `MEMBER` invitations. Wrong-parent/cross-tenant objects are not disclosed.
Manager output is sanitized and contains neither raw credential nor digest.


Schema, audit, and rollout boundary:

- `ProfileInvitation` is implemented in the existing Workspace app with
  tenant/account/inviter relationships, requested role, digest, lifecycle,
  expiry, delivery metadata, terminal actors/timestamps, and replacement
  lineage. Database checks/unique constraints protect allowed roles/states,
  terminal/delivery consistency, expiry ordering, credential uniqueness, and
  at most one pending Profile/email or bound Profile/User invitation.
- Locked services write material invitation, Profile membership, and stale
  Workspace-access revocation events atomically with their state mutations.
  Recipient email and raw/digested credentials are not stored in AuditLog.
- The additive source migration is
  `workspace.0004_profileinvitation`. It creates the new aggregate only and
  performs no guessed mapping/backfill. As of this checkpoint it is not
  applied to the persistent development database; production is untouched.
- Verification is complete: targeted Invitation model/service/API/migration
  tests pass 39/39, Authentication/API passes 29/29,
  Workspace/RBAC/Task/Review passes 173/173, and the full PostgreSQL suite
  passes 241/241. Dependency, Django system, and migration-drift checks pass.
  The persistent development database is reconfirmed unchanged at 30 migration
  records with `workspace.0004` unapplied and no Invitation table. The status
  is therefore `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION
  APPROVAL`; this is not authorization to apply the migration or configure a
  real provider.

Operational supersession note (2026-10-23): the Owner later authorized
HT-DB-P1-08, which backed up/rehearsed and applied `workspace.0004` to the
development database. Production and every other target remain unauthorized.


---

# Decision: Account Email Verification and Password Recovery Foundation

Date:

2026-10-23

Implementation reconciliation: 2026-10-24


Status:

`HT-AUTH-P1-02` implementation is complete. Its original implementation gate
did not authorize a persistent migration. The Owner subsequently conditionally
authorized development-only `HT-DB-P1-09`: fresh inventory, verified backup,
restore/migration rehearsal, and exact plan were required before applying
`accounts.0002`. Those gates passed and the exact migration was applied to
development at 2026-10-24 06:30:28.634074 UTC. No production or other persistent
target is authorized. This records the actual rollout authorization/status;
the ten identity/security decisions below remain unchanged. See `HANDOVER.md`
for current verification and the Owner Review Gate.


Decision:

1. Keep Django server-side sessions and DRF `SessionAuthentication`; do not
   introduce JWT, OAuth, a new authentication framework, or automatic login
   after password reset.
2. Email verification proves control of the currently normalized User email.
   Persist a nullable verification timestamp and normalized-email snapshot;
   verification is valid only while both exist and the snapshot still matches
   the current email. A material email change clears verification and revokes
   pending verification and reset credentials, including if the address later
   changes back to its earlier value.
3. Verification is not an activation gate in this slice. Registration still
   creates an active User, and existing unverified Users may continue to log
   in. The three legacy development Users are not auto-verified, deactivated,
   or backfilled.
4. Use a purpose-bound `AccountSecurityToken` for `EMAIL_VERIFICATION` and
   `PASSWORD_RESET`. Generate at least 256 bits of randomness, persist only a
   purpose-separated SHA-256 digest, bind to User and normalized-email
   snapshot, require successful delivery before consumption, and enforce
   expiry, rotation, replay protection, and one terminal transition under
   transaction locks. Password-reset rows also store a SHA-256 fingerprint of
   the encoded Django password state; verification rows must not store one.
5. Email-verification credentials expire after 24 hours. Password-reset
   credentials expire after one hour. Resend revokes the prior pending token
   and creates an independently random replacement; a consumed, revoked, or
   expired credential is never reusable.
6. Email verification request/confirm requires the authenticated User and
   CSRF. Password reset request/confirm is explicitly `AllowAny` because a
   locked-out User cannot authenticate, but both public POSTs still require
   CSRF. All four routes use strict input, no-cache responses, scoped abuse
   throttles, and sensitive-parameter protection. Reset confirmation applies
   independent submitted-token-fingerprint `10/hour` and client-address
   `30/hour` limits.
7. Password-reset request returns one neutral `202` HTTP status/body for eligible,
   missing, ambiguous, inactive, unusable-password, and delivery-failure
   cases. The API never returns a raw token, digest, email-resolution result,
   or delivery outcome. Confirmation uses a generic invalid-token error. This
   contract does not pad execution or claim timing-indistinguishability.
8. Password reset runs Django password validators and `set_password()`. It
   consumes the token atomically, creates no new session, and relies on
   Django's password-backed session authentication hash to invalidate existing
   sessions when they next authenticate. A change through `User.save()`
   revokes pending reset credentials; a direct queryset change that bypasses
   the hook still invalidates the stored fingerprint at confirmation. A
   material email change revokes both verification and reset credentials,
   including an `A -> B -> A` sequence.
9. Security state transitions write AuditLog events without raw credentials,
   digests, email addresses, or passwords. Credential email is scheduled only
   after transaction commit and reuses the configured default-mail safety
   boundary. Console/dummy/file backends are rejected; locmem remains limited
   to isolated tests.
10. Profile Invitation keeps its independent reviewed proof: authenticated
    recipient, unique current-email match, delivery `SENT`, and that
    invitation's one-time credential. HT-AUTH-P1-02 does not retroactively add
    a global-verification gate, change invitation lifecycle, or infer global
    verification from invitation acceptance. Any future stricter coupling
    requires a separately approved compatibility change.


Consequences:

- Additive `accounts.0002_accountsecuritytoken_user_email_verification` adds
  nullable User verification fields plus the account-security-token aggregate,
  checks, partial uniqueness, and indexes. Its
  `acctok_fingerprint_by_purpose` constraint requires password-state binding
  only for reset credentials. It performs no data backfill.
- `UserSerializer` exposes only the derived boolean `email_verified`; internal
  timestamps/snapshots and token records are not serialized.
- Public API allowlist gains only the two password-reset routes. Verification
  routes remain authenticated. The existing registration/login/logout/me and
  Profile Invitation contracts remain compatible.
- Malformed Unicode in public reset and Invitation recipient input is handled
  fail-closed as `400`, not an encoding-driven `500`; cache fingerprints never
  contain raw submitted email/token values.
- Final isolated PostgreSQL checks pass account security 44/44 in 32.336s,
  Authentication/API/Invitation 113/113 in 99.629s,
  Workspace/RBAC/Task/Review 173/173 in 93.895s, and full suite 286/286 in
  188.592s. `pip check`, Django system, migration-drift, and diff checks pass.
- At the historical implementation gate, development was PostgreSQL 16.14 `hustlytasker_db` at 31
  migrations (`accounts.0001`, `workspace.0001`-`0004`), 3 Users, 2 sessions,
  zero checked business/AuditLog rows, and no new columns/token table. The
  separately authorized HT-DB-P1-09 now has 32 migrations and the verified new
  schema, with unchanged Users/Sessions, no verified Users, and no token rows.
  Authorization and inventory for every other target remain separate.
- **REAL EMAIL DELIVERY NOT VERIFIED.** No real provider credential was used.
  DRF throttles currently use the default process-local cache and therefore do
  not provide distributed multi-worker enforcement. These deployment limits
  must not be described as production-verified.
