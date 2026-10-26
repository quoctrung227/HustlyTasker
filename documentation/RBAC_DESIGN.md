# HT-RBAC-DESIGN-P0-01

## Capability Matrix, Tenant-Scoped Access, and Invitation Contract

Status: `COMPLETE — APPROVED BY OWNER DELEGATION`

Date: 2026-10-18

Last implementation reconciliation: 2026-10-26

The owner delegated the remaining RBAC decisions to the Technical Advisor on
2026-10-17. That approval first authorized `HT-RBAC-P1-03` Tenant Access
Context and Scoped Service Foundation. The owner subsequently authorized
`HT-API-P1-04`, the controlled development rollout `HT-DB-P1-05`, and the
initial schema-free Workspace write/member slice `HT-WORK-P2-02`, followed by
its approved schema-dependent completion. Current `/api/v1/` behavior includes
four Profile/Workspace reads, canonical-month Workspace creation/metadata
update, Profile/Workspace archive/restore, manager-only Workspace-member
list/direct-add/role-update/soft-revoke/reactivation, and the bounded Profile
Invitation management/recipient actions described in section 7. General
Profile CRUD and downstream domain APIs remain unavailable. Additive
`workspace.0003` completed its separately authorized controlled development
rollout in `HT-DB-P1-06`; production and all other persistent environments
remain behind separate approval gates. Owner then authorized the dedicated
`HT-TASK-P2-03` contract. Its Task/Deliverable/internal Review permissions and
routes are implemented in source and have passed 33/33 targeted, 169/169
existing regression, and 202/202 full PostgreSQL tests. Its two additive
migrations completed their development rollout through HT-DB-P1-07. Owner
then authorized `HT-INV-P2-04`; its source, additive `workspace.0004`, APIs,
services, and isolated PostgreSQL verification are complete. Its separately
authorized `HT-DB-P1-08` rollout applied `workspace.0004` to development after
backup/rehearsal and verification; no other persistent target is authorized.
`HT-AUTH-P1-02` implementation is complete. Owner separately authorized the
development-only rollout `HT-DB-P1-09`; exact `accounts.0002` was applied at
2026-10-24 06:30:28.634074 UTC after verified backup/restore rehearsal. The
three legacy Users and two Sessions are preserved and no User is auto-verified.
This operational status reconciliation changes no RBAC or Invitation decision.
Current rollout verification is recorded in `HANDOVER.md`; every other
persistent target remains separately gated.

The authorized `HT-TASK-P2-05` source extension adds Task hierarchy and
planning filters using the same capabilities; it introduces no role or public
principal. See section 10.9 and `API_DOCUMENTATION.md`. Its additive
`tasks.0003_task_hierarchy` was separately authorized and applied to development
by HT-DB-P1-10 on2026-10-25 after verified backup/restore rehearsal. Nullable
parent/selfCHECK/FK/index and exact legacy-row preservation were verified;
no capability, workflow or other-environment authorization changed. Current
rollout regression evidence is in HANDOVER.md. Project remains behind
the explicit Owner design gate in `PROJECT_ARCHITECTURE_REVIEW.md`.

## 1. Evidence and decision labels

The following labels prevent legacy behavior or a technical recommendation
from being mistaken for an approved business rule:

- **[REQUIREMENT]** — capability-level need in `ORIGINAL_REQUIREMENTS.md`.
- **[APPROVED]** — one of the owner-approved tenancy/business decisions in
  `DECISION_LOG.md`.
- **[APPROVED BY OWNER DELEGATION]** — a decision finalized by the Technical
  Advisor under the owner's explicit delegation on 2026-10-17.
- **[CURRENT]** — behavior or limitation verified in the current Django
  source, migrations, settings, routes, or database inventory.
- **[PROPOSED]** — least-privilege technical detail that is not covered by an
  approved decision and remains unavailable until its later review gate.
- **[OPEN]** — a product or policy decision still required from the owner.

When sources conflict, an approved decision overrides the legacy reference.
Current source remains authoritative for what is actually implemented.

## 2. Confirmed baseline

### 2.1 Approved boundaries

- **[APPROVED]** Profile represents a company/team and is the tenant root.
  One Profile may contain many monthly operational Workspaces; each Workspace
  belongs to exactly one Profile in the approved target architecture.
- **[APPROVED]** User is a global identity and may have active membership in
  multiple Profiles. A selected/switched Profile is navigation state, not
  authorization proof.
- **[APPROVED]** Profile roles are `OWNER`, `ADMIN`, and `MEMBER`. Profile
  Owner/Admin administer all Workspaces in their Profile. An ordinary Profile
  Member needs explicit Workspace membership. Rights never cross Profiles.
- **[APPROVED]** Profile and Workspace membership are independent layers. An
  active Workspace membership is never sufficient without an active Profile
  membership and active User.
- **[APPROVED]** A Profile can have multiple equal Owners and must retain at
  least one active Owner membership. Owner changes require transaction/concurrency
  protection. Profile Admin cannot appoint, demote, deactivate, or remove an
  Owner.
- **[APPROVED]** Joining a new Profile requires accepted consent through an
  invitation. Profile Owner/Admin may directly add only an already-active
  Profile member to a Workspace. Duplicate active memberships are forbidden;
  material membership changes are audited.
- **[APPROVED]** Client belongs to Profile and may have many Projects. Project
  belongs to that Client/Profile and may span monthly Workspaces through Tasks.
  Task belongs to exactly one Workspace. Any Task references to Client,
  Project, and Workspace must resolve to the same Profile.
- **[APPROVED]** Invoice belongs to one monthly Workspace and references a
  Client from the same Profile. A Workspace may have many Invoices; Payment
  belongs to Invoice. Cross-Profile finance links are forbidden. Invoice
  numbering and detailed billing workflow remain open for their later task.
- **[APPROVED]** Client Portal supports both an authenticated account and a
  secure-link flow. Client Portal Link and Guest Review Link are independent
  principals; link credentials are capability-scoped, expiring, revocable,
  and stored only as hashes. Client accounts do not receive internal Profile
  or Workspace membership implicitly. Exact capabilities and default expiries
  remain open for their later task.
- **[APPROVED]** Soft delete is the default target for Profile, Workspace,
  Client, Project, and Task; hard delete is controlled. Invoice, Payment, and
  AuditLog are protected under the eventual retention policy, and a departing
  User must not cascade-delete business data. Retention periods and automated
  purge remain open.
- **[APPROVED]** Every target database must be inventoried before migration.
  Existing rows are never assumed absent or assigned a guessed tenant. Risky
  changes require backup and rehearsal, and applied `0001` migrations are
  never rewritten; only additive migrations are allowed.
- **[APPROVED]** The high-level Task workflow is assignment, execution,
  Deliverable submission, Review, then approval/completion or revision and
  resubmission. A Task is complete only after its Deliverable is approved.
  Section 2.4 additionally requires explicit Review capability and forbids
  self-approval. `HT-TASK-P2-03` now fixes the internal state machine and grants
  management/review to same-Profile Owner/Admin or assigned Workspace Admin,
  while execution requires the current active Editor assignee. Client/Guest
  approval and Payroll/Payment pricing/eligibility remain separate.

### 2.2 Reconciliation with the 11 approved decisions — 2026-10-17

The status in the fourth column records the finding against the document as it
stood before this reconciliation. The final column records the corrected state
of this document. An approved group is not `STILL OPEN`; only the explicitly
listed downstream details remain open.

| # | Owner-approved content | Content found before reconciliation | Audit status | Current result |
|---|---|---|---|---|
| 1 | Profile is the company/team tenant root; it has monthly operational Workspaces. | Section 2.1 already stated the same tenant and monthly-scope boundary. | `MATCH` | `MATCH` — retained and made the target cardinality explicit. |
| 2 | A User may join multiple Profiles; switching context never grants access. | Multi-Profile identity and navigation-versus-authorization were explicit. | `MATCH` | `MATCH` — no owner re-approval required. |
| 3 | Profile Owner/Admin administer same-Profile Workspaces; ordinary Member needs assignment; no cross-Profile inheritance; membership layers remain independent. | The baseline, matrix, and non-inheritance rules stated all four boundaries. | `MATCH` | `MATCH` — action-level role details remain separate proposals. |
| 4 | Multiple equal Owners; at least one active Owner; locked/concurrent changes; Admin cannot change an Owner. | The document incorrectly labeled the stronger phrase “usable Owner”, which also incorporated `User.is_active`, as approved. | `CONFLICT` | `MATCH` — restored the approved active-Owner wording. Section 2.4 separately records the later delegated deactivation/session target without changing this membership invariant. |
| 5 | Profile invitation acceptance is mandatory; direct Workspace add is only for an active Profile member; no duplicate active membership; important changes are audited. | The baseline and invitation contract preserved the two distinct transitions and invariants. | `MATCH` | `MATCH` — optional combined UX cannot bypass either transition. |
| 6 | Client belongs to Profile and has many Projects; Project may span Workspaces through Tasks; Task stays in one Workspace; references share one Profile. | Client/Profile, Project spanning, Task/Workspace, and tenant consistency appeared, but Client→many Projects / Project→Client was omitted. | `NOT DOCUMENTED` | `MATCH` — the missing ownership/cardinality is now explicit. |
| 7 | Invoice belongs to one monthly Workspace and same-Profile Client; Workspace has many Invoices; Payment belongs to Invoice. | Only a generic same-Profile relationship statement appeared. | `NOT DOCUMENTED` | `MATCH` — the complete approved finance ownership path is now explicit; numbering/billing remains open. |
| 8 | Client Portal supports account and secure link; portal and guest-review links are independent, scoped, expiring, revocable, hash-only; no implicit internal membership. | The document mentioned external capability principals but omitted account access and most credential/lifecycle boundaries. | `NOT DOCUMENTED` | `MATCH` — all approved access boundaries are now explicit; exact capabilities/default expiries remain open. |
| 9 | Default soft delete for core business aggregates; controlled hard delete; protect finance/audit; no User-departure cascade; retention/purge undecided. | The default soft-delete target and open retention were present, but finance/audit protection and no-cascade behavior were missing. | `NOT DOCUMENTED` | `MATCH` — the complete approved deletion boundary is now recorded. |
| 10 | Inventory first; never assume empty or guess mapping; backup/rehearse risky changes; additive migrations only. | These controls existed in the implementation plan, but were not collected in the approved baseline. | `MATCH` | `MATCH` — elevated to the approved baseline; environment-specific unknown mappings remain operational blockers, not new policy questions. |
| 11 | Assignment → execution → Deliverable → Review → approval/completion or revision/resubmission; completion only after approval. | The document deferred detailed workflow but omitted the already-approved high-level flow and completion invariant. | `NOT DOCUMENTED` | `MATCH` — fixed invariant recorded. The later HT-TASK-P2-03 contract resolves internal states/reviewer authority; external approval and Payroll effects remain separate. |

This reconciliation found no conflict that changes an approved architecture
decision. Row 4 was a documentation-labeling overreach and rows 6–9 and 11
were compatible but incomplete; all are corrected above.

### 2.3 Pre-implementation findings and HT-RBAC-P1-03 resolution

These findings were verified before `HT-RBAC-P1-03` implementation began. The
current-result wording below distinguishes the original gap from the verified
implementation completed on 2026-10-18.

- **[CURRENT]** `ProfileMembership` implements `OWNER`, `ADMIN`, `MEMBER`, an
  active flag, and a partial unique constraint for one active Profile/User
  membership while retaining inactive history.
- **[CURRENT]** `WorkspaceMember` contains `OWNER`, `ADMIN`, `MEMBER`, and
  `VIEWER`, and now has `is_active` for retained soft-revoke/reactivation
  history. These enum values are storage capability, not by themselves an
  action-level permission contract.
- **[CURRENT]** `Workspace.profile` is nullable for safe legacy transition.
  Unmapped Workspaces must never be exposed by a tenant API.
- **[CURRENT]** `Workspace.owner` is a transitional protected User FK and is
  not authorization proof.
- **[CURRENT — HT-API-P1-04 / HT-WORK-P2-02]** Session authentication and global DRF
  `IsAuthenticated` establish identity. `apps/workspace/access.py` supplies
  the authorization facts, while `permissions.py` and tenant views adapt those
  facts to DRF with scoped querysets, action permissions, and non-enumerating
  errors. Four reads plus the bounded Workspace write/member-manager,
  Profile/Workspace lifecycle, and Profile Invitation operations in section 8
  are implemented; general Profile CRUD/membership API remains unavailable.
- **[CURRENT]** Client, Invoice/Payment, and AuditLog do not yet have a safe
  canonical tenant path; Project does not exist. Those APIs must stay closed.
- **[CURRENT — HT-RBAC-P1-03]** `update_profile_membership()` now establishes
  actor/Profile scope before target lookup. `add_workspace_member()` resolves
  the actor's scoped Workspace first and accepts a same-Profile
  `target_profile_membership_id`, not a globally resolved User. Both revalidate
  authority under locks and use the same tenant-not-found domain error for
  out-of-scope and unknown identifiers.
- **[CURRENT]** bulk operations, raw SQL, direct ORM writes, User deactivation,
  and global Django Admin surfaces can bypass service-level invariants.
- **[CURRENT]** supported foundation Owner mutations additionally filter on an
  active User, but direct User deactivation/delete can bypass that service.
  The delegated account-lifecycle decision now requires owner protection and
  session revocation for a future User-deactivation flow, but that flow is not
  implemented by the current foundation or by `HT-RBAC-P1-03`.

### 2.4 Owner-delegated RBAC decisions — approved 2026-10-17

The following decisions are **APPROVED BY OWNER DELEGATION**. They refine the
11 architecture groups without replacing or weakening them:

1. Profile Owner/Admin may administer Workspace content in the same Profile.
   Sensitive Finance capability is not granted to Profile Admin implicitly.
2. An ordinary Profile Member needs a valid Workspace membership before they
   may access work in that Workspace.
3. Workspace Admin administers only its assigned Workspace; Editor performs
   work; Viewer is read-only.
4. Deliverable approval requires an explicit Review capability, and a submitter
   may not approve their own Deliverable. This design originally deferred the
   concrete role/state machine; HT-TASK-P2-03 later approved Profile
   Owner/Admin and Workspace Admin for internal review and the bounded
   state/revision flow recorded in sections 4 and 8.2.
5. Profile creation creates the initial Owner in the same transaction.
6. Leave, deactivate, demote, or remove operations must be rejected when they
   would violate the last-active-Owner invariant.
7. User deactivation must revoke the ability to use existing sessions and must
   not cascade-delete business or historical data. The account-lifecycle
   service that enforces this is approved target behavior, not implemented in
   this task.
8. A Profile invitation is bound to email, has a one-time expiring credential
   and an enforced role ceiling, and cannot grant `OWNER`.
9. Profile Owner may invite `ADMIN` or `MEMBER`; Profile Admin may invite only
   `MEMBER`.
10. Direct Workspace add is allowed only for a User with an active
    ProfileMembership in the same Profile.
11. Invitation TTL is seven days. Resend/reinvite invalidates the prior
    credential. Initial limits are five attempts per recipient email per 24
    hours and 30 invitations per inviter per 24 hours.
12. Terminal Invitation metadata is retained for at least 12 months. This task
    does not implement automated purge.
13. Cross-tenant object existence must not be disclosed through the API.
    Django Admin is a platform-operations surface, not tenant RBAC.
14. Until a tenant-scoped Admin implementation exists, tenant-wide Django Admin
    access is restricted to platform superusers.

These approvals remove the former seven-group owner-review blocker for
`HT-RBAC-P1-03`. Decisions still deferred to later domain tasks remain denied
or unavailable; they do not authorize scope expansion in this implementation
slice.

## 3. Approved role model and compatibility boundary

### 3.1 Effective internal roles

| Effective role | Scope and effective meaning |
|---|---|
| Profile Owner | Tenant governance plus inherited Workspace management for every Workspace in the same Profile. Only this role may change Owner status, subject to last-owner locking. |
| Profile Admin | Tenant operations plus inherited Workspace content management for every Workspace in the same Profile; never Owner governance and never implicit sensitive Finance access. |
| Profile Member without Workspace membership | Profile self/navigation access only; no Workspace content. |
| Workspace Admin | **[APPROVED BY OWNER DELEGATION]** delegated manager for exactly one assigned Workspace. Active Profile membership is mandatory. It may assign/remove Editor and Viewer participation in that Workspace, but cannot grant Workspace Admin/Owner, Profile, CRM, Finance, or Owner authority. |
| Workspace Editor | **[APPROVED BY OWNER DELEGATION]** performs work in exactly one assigned Workspace. The current DB value remains `MEMBER`; no enum/schema change is made in `HT-RBAC-P1-03`. |
| Workspace Viewer | **[APPROVED BY OWNER DELEGATION]** read-only in exactly one assigned Workspace. It receives no mutation capability. Endpoint-specific visible fields and download/export behavior remain denied until their contracts are implemented. |
| Client/Guest | External principals only, never mapped to an internal role. |

### 3.2 Existing Workspace enum treatment

- **[APPROVED BY OWNER DELEGATION]** `WorkspaceMember.OWNER` is legacy
  compatibility data, fails closed as an effective authorization role, and is
  never assigned by the scoped service. Profile Owner is the canonical owner.
  Existing rows, if any are later found, require inventory and explicit
  reconciliation.
- **[APPROVED BY OWNER DELEGATION]** `WorkspaceMember.ADMIN` maps to Workspace
  Admin for narrow, single-Workspace administration.
- **[APPROVED BY OWNER DELEGATION]** `WorkspaceMember.MEMBER` maps to Editor.
- **[APPROVED BY OWNER DELEGATION]** `WorkspaceMember.VIEWER` maps to read-only
  access. No write operation may treat it as sufficient authorization.
- **[APPROVED BY OWNER DELEGATION]** An inherited Profile Owner/Admin capability takes precedence
  over a lower explicit Workspace role in that same Profile, but never grants
  rights in another Profile. Profile Owner/Admin may assign Workspace
  `ADMIN`, `MEMBER`, or `VIEWER`; Workspace Admin may assign only `MEMBER` or
  `VIEWER`; no supported actor may assign Workspace `OWNER`.

## 4. Capability matrix

Legend:

- `A` — follows an approved boundary directly.
- `R/P` — requirement-level capability with the proposed least-privilege
  interpretation; owner approval is still required for the exact action.
- `P` — technical/product proposal only.
- `DENY` — denied by default.
- `DEFER` — cannot be granted until its separate workflow/policy is approved.

`P-Member only` means an active Profile Member without an effective Workspace
role for the target Workspace.

Workspace-role columns assume the User's Profile role is `MEMBER`. A User who
is also Profile Owner/Admin receives only the same-Profile inherited management
capabilities shown in the Profile columns; role composition never crosses a
Profile and does not automatically make that manager a contributor/assignee.

| Capability | P-Owner | P-Admin | WS-Admin | WS-Member | WS-Viewer | P-Member only |
|---|---|---|---|---|---|---|
| List/select own scoped Profiles, including archived | A | A | A | A | A | A |
| List Workspaces in Profile | A: all | A: all | Assigned only | Assigned only | Assigned only | DENY |
| Read assigned Workspace metadata | A | A | A | A | A: read-only | DENY |
| Create Workspace | A | A | DENY | DENY | DENY | DENY |
| Create canonical monthly Workspace | A: unique period | A: unique period | DENY | DENY | DENY | DENY |
| Edit Workspace name/description | A | A | A | DENY | DENY | DENY |
| Archive/restore Workspace | A | A | DENY | DENY | DENY | DENY |
| Hard-delete Workspace | DEFER | DENY | DENY | DENY | DENY | DENY |
| Edit Profile settings/branding | P: Owner only | DENY | DENY | DENY | DENY | DENY |
| Archive/restore Profile | A: Owner only | DENY | DENY | DENY | DENY | DENY |
| Read full Profile roster/PII | R/P | R/P | DENY | DENY | DENY | Self only |
| List effective Workspace assignments (no User PII) | A | A | A: assigned Workspace | DENY | DENY | DENY |
| Invite Profile `MEMBER` | A | A | DENY | DENY | DENY | DENY |
| Invite Profile `ADMIN` | A: Owner only | DENY | DENY | DENY | DENY | DENY |
| Promote/deactivate Profile `ADMIN` | P: Owner only | DENY | DENY | DENY | DENY | DENY |
| List/revoke/reinvite pending invitations | DEFER: Invitation API | DEFER: `MEMBER` ceiling | DENY | DENY | DENY | DENY |
| Appoint/demote/deactivate Profile `OWNER` | A: Owner only + lock | DENY | DENY | DENY | DENY | DENY |
| Remove/deactivate Profile Member | R/P | P: `MEMBER` only | DENY | DENY | DENY | DENY |
| Leave Profile voluntarily | P: only if another active Owner membership remains | P: self | P: self Profile membership | P: self Profile membership | P: self Profile membership | P: self |
| Direct-add active Profile member to Workspace | A: Admin/Editor/Viewer | A: Admin/Editor/Viewer | A: Editor/Viewer only | DENY | DENY | DENY |
| Update Workspace assignment role | A: Admin/Editor/Viewer | A: Admin/Editor/Viewer | A: Editor/Viewer only | DENY | DENY | DENY |
| Soft-revoke/reactivate Workspace participation | A: Admin/Editor/Viewer | A: Admin/Editor/Viewer | A: Editor/Viewer only | DENY | DENY | DENY |
| Leave/remove own Workspace participation | DEFER: lifecycle | DEFER: lifecycle | DEFER: lifecycle | DEFER: lifecycle | DEFER: lifecycle | N/A |
| Read Task/Deliverable history in authorized Workspace | A: all | A: all | A: assigned Workspace | A: assigned Workspace | A: assigned Workspace, read-only | DENY |
| Create/assign/edit Task metadata | A | A | A: assigned Workspace | DENY | DENY | DENY |
| Claim/return eligible Task | P: only as contributor | P: only as contributor | P: only as contributor | R/P | DENY | DENY |
| Start assigned Task / submit Deliverable revision | DENY unless separately an eligible assigned Editor | DENY unless separately an eligible assigned Editor | DENY unless separately an eligible assigned Editor | A: current active assignee only | DENY | DENY |
| Comment on Task | CURRENT: create/own edit/moderate delete | CURRENT: create/own edit/moderate delete | CURRENT: assigned Workspace, create/own edit/moderate delete | CURRENT: create/own edit/delete | DENY: read-only | DENY |
| Internal approve/request changes | A: not own submission | A: not own submission | A: assigned Workspace, not own submission | DENY | DENY | DENY |
| Send to Client / Client or Guest approval | DEFER | DEFER | DEFER | DEFER | DENY | DENY |
| Manage Profile Client/Project | R/P | R/P | DENY | DENY | DENY | DENY |
| Reference existing same-Profile Client/Project from Task | R/P | R/P | P: scoped selection | P: task-linked only | P: task-linked read | DENY |
| Read/manage Invoice, Payment, payroll | R/P | DENY: no implicit sensitive Finance | DENY | DENY | DENY | DENY |
| Manage Client Portal link | DEFER | DEFER | DENY | DENY | DENY | DENY |
| Manage task-scoped Guest Review link | DEFER | DEFER | DEFER | DEFER | DENY | DENY |
| Read tenant AuditLog | P | P | P: Workspace subset | DENY | DENY | DENY |

The requirement to keep a Task, Client, Project, and Workspace in the same
Profile is approved (`A`); the matrix row above concerns who may perform the
reference action and therefore remains `R/P` or `P`.

The implemented internal Task lifecycle constrains every role: no capability
may mark a Task complete before its latest submitted Deliverable is approved,
and the submitter cannot perform that approval. The concrete internal reviewer
roles and state machine are no longer open. Client/Guest review and any Payroll
pricing, eligibility, or payment effect remain deferred; internal approval
does not create those records.

### 4.1 Approved Viewer read-only boundary

The delegated decision approves the read-only invariant, not a complete API
field set. A Viewer can satisfy only a read capability in its assigned
Workspace and cannot create, update, delete, claim, comment, upload, or manage
members. Future responses must omit finance/payroll, member email/PII, secrets,
integration fields, and Profile-wide Client data unless a later contract says
otherwise. Export, download, and every unsafe HTTP method remain denied until
explicitly reviewed. `HT-RBAC-P1-03` itself opened no endpoint; the later
  `HT-API-P1-04` slice and later lifecycle extension let an assigned Viewer
  read only Workspace fields `id`, `profile_id`, `name`, `description`,
  `period`, `status`, `created_at`, and `updated_at`.

### 4.2 Important non-inheritance rules

- Workspace Admin does not become Profile Admin and cannot manage Profile
  membership, invitations, Owners, Profile-wide CRM, or Finance.
- A Profile Member does not receive Viewer fallback access to every Workspace.
- Client/Guest credentials cannot call internal member endpoints.
- Profile Owner/Admin inheritance is limited to the same Profile.
- Profile Owner/Admin management inheritance does not make that manager an
  assignee/contributor. In `HT-TASK-P2-03`, operational execution requires an
  active ordinary Profile Member with effective Workspace `MEMBER` (Editor)
  assignment and the current active Task assignment.
- Workspace self-leave/removal is **[DEFER]**: `WorkspaceMember.is_active` and
  the manager-only soft-revoke/reactivation service now preserve one historical
  row per Workspace/User, but self-service eligibility and its audit/rejoin
  policy have not been approved and no self-leave endpoint is exposed.

### 4.3 Narrow bootstrap contexts

Two operations occur before the normal active-membership context and must not
be mistaken for tenant access:

- **Profile creation — [CURRENT; API POLICY OPEN]:** the approved schema
  foundation already provides a service that atomically creates a Profile and
  its initial Owner. This bootstrap is not an exception to joining an existing
  Profile: the tenant does not exist before the transaction. If the owner
  approves self-service `POST /api/v1/profiles/`, an eligible active
  authenticated User acts in a creation-only bootstrap context and becomes the
  first Owner; invitation is not applicable because no existing Profile is
  being joined. Eligibility, quotas, abuse controls, and whether creation is
  staff-mediated remain **[OPEN]**.
- **Invitation recipient — [PROPOSED]:** an active authenticated User without
  Profile membership may use only an `InvitationRecipientContext` for their
  sanitized inbox and accept/decline operation after token/account binding.
  That context grants no Profile metadata, roster, Workspace, Task, Client, or
  Finance read access before acceptance commits.

For supported Workspace creation while the transitional required
`Workspace.owner` FK remains, the service—not request data—sets it to the
creating active Profile Owner/Admin. It remains compatibility data, never an
authorization source. A later reviewed migration may remove or replace that FK
after all consumers have moved to Profile authority.

## 5. Tenant-scoped request and query boundary

### 5.1 Per-request access context

**[APPROVED BY OWNER DELEGATION]** Resolve an immutable
`ProfileAccessContext` for each request or sensitive service call:

```text
SessionAuthentication
        ↓
active request.user
        ↓
profile_id from nested URL (candidate only)
        ↓
active ProfileMembership(user, profile_id)
        ↓
ProfileAccessContext(user, profile, membership, profile_role)
        ↓
Workspace queryset already scoped to that context
        ↓
resource queryset derived from Workspace
        ↓
action capability check
        ↓
transactional service re-check for mutation
```

This normal flow applies after Profile membership. The two bootstrap contexts
in section 4.3 are narrow exceptions and cannot call ordinary tenant
selectors. No role or Profile stored in a header, cookie, session-selected context, or
request body is trusted as authorization. Context is not cached between
requests. API staff/superuser status does not create an implicit tenant bypass
unless the owner later approves a separate platform-operator contract.

### 5.2 Canonical queryset rules

```text
profiles_visible_to(user)
  = Profiles with active ProfileMembership for an active user

workspaces_visible_to(context)
  OWNER/ADMIN → every mapped Workspace in context.profile
  MEMBER      → mapped Workspaces in context.profile with WorkspaceMember(user)
                whose role is enabled by the owner-approved role policy
```

- Always exclude `Workspace.profile IS NULL`.
- Fail closed for deprecated or unknown Workspace roles. A row carrying legacy
  `OWNER` must not grant visibility merely because it exists; it needs explicit
  reconciliation. Current `ADMIN`, `MEMBER`, and `VIEWER` map respectively to
  Workspace Admin, Editor, and read-only Viewer for this compatibility slice.
- Task scopes through `task.workspace.profile`.
- TaskAssignment and TaskComment scope through `task.workspace.profile`.
- Deliverable and Review scope through `deliverable.task.workspace.profile`.
- Filters, search, ordering, prefetching, annotation, pagination, and counts
  run only after the base tenant queryset is established.
- DRF object permissions are defense-in-depth; they never replace a scoped
  `get_queryset()`.
- `get_object()` selects from the scoped queryset. Do not fetch globally and
  check later.
- Do not expose Client/Project/Finance/Audit tenant APIs until their approved
  ownership paths exist in schema and services.

### 5.3 Input relationships

- The nested authorized parent supplies Profile/Workspace ownership. Tenant
  fields are omitted or read-only in serializers.
- Request actors such as creator, commenter, uploader, and the reviewer who is
  performing an action are set server-side from `request.user`; their IDs are
  never accepted from the body. Selectable assignee/reviewer targets,
  memberships, Client, Project, and Workspace IDs are resolved only from
  parent-scoped eligible querysets.
- Do not use unrestricted `PrimaryKeyRelatedField(queryset=User.objects.all())`
  for tenant-sensitive relationships.
- Unique validators and validation messages must not reveal values in another
  tenant.
- Same-Profile cross-table relationships are rechecked in the mutation
  transaction, not only by serializer validation.

### 5.4 Non-enumerating error contract

**[APPROVED BY OWNER DELEGATION]** Every current and future tenant API must not
disclose whether an object exists outside the caller's tenant scope. The
implemented Profile/Workspace endpoints follow the least-privilege status
mapping below. Exact shared error-envelope details beyond their bounded
contracts remain an API implementation concern; `HT-RBAC-P1-03` itself added
no endpoint.

| Situation | Required response contract |
|---|---|
| Anonymous request to private SessionAuthentication endpoint | Preserve current DRF behavior: `403` |
| Authenticated user lacks active Profile membership | `404` |
| Resource does not exist or exists outside caller scope | Same `404` status and response shape |
| Profile Member lacks target Workspace assignment | `404` |
| Object is visible but role lacks the requested action | `403` |
| Malformed body reference | `400` |
| Body reference is nonexistent or outside scope | Same generic field-level `400 invalid_reference` |
| Domain/concurrency conflict | `409` for the implemented Workspace conflict cases; the project-wide response envelope remains open |
| List within valid Profile context but no visible rows | `200` with an empty scoped list |

Raw `DoesNotExist`, `IntegrityError`, object names, tenant names, or differing
timing-dependent detail must not escape. A real unauthorized UUID and a random
UUID receive the same contract.

## 6. Service and transaction boundary

### 6.1 Structure

No new Django app is required. `HT-RBAC-P1-03` placed shared access
selectors/capabilities in `apps/workspace/access.py` and mutations in the
existing `services.py`. The subsequently approved tenant APIs adapt those
capabilities through `permissions.py`; they do not create a parallel
authorization system.

Sensitive service signatures must include the authorized parents, for example:

```text
update_profile_membership(actor, profile_id, membership_id, ...)
add_workspace_member(
    actor, profile_id, workspace_id, target_profile_membership_id, role
)
```

They must not accept a request-derived User/object that was fetched globally.
The currently exposed Profile/Workspace services follow this boundary, and
future sensitive services must preserve it:

1. establish/authorize Profile scope;
2. enter an atomic transaction;
3. lock the aggregate in canonical order;
4. re-read actor membership and action capability under lock;
5. resolve targets from tenant-scoped querysets;
6. validate same-tenant and lifecycle invariants;
7. mutate and write AuditLog in the same transaction; and
8. translate constraint conflicts to stable domain errors.

Every sensitive mutation locks `Profile` first. That Profile lock serializes
the current same-Profile membership mutations before their operation-specific
actor/target row reads. The remaining order is:

```text
Workspace/membership: Profile → Workspace (when relevant)
                      → actor ProfileMembership / WorkspaceMember
                      → target ProfileMembership / WorkspaceMember
                      → business resource → AuditLog write

Invitation:           Profile → Invitation
                      → relevant ProfileMembership rows ordered by UUID
                      → AuditLog write
```

Stable UUID ordering remains mandatory for future operations that lock multiple
Profiles or cannot serialize first on one Profile. The current services do not
lock multiple Profiles.

Read-only requests need no lock. Task/content writes should lock only the rows
needed to make membership validation race-safe; locking an entire Profile for
every content write would be unnecessarily expensive.

### 6.2 Defense allocation

| Invariant | Primary enforcement |
|---|---|
| Ownership path | PostgreSQL foreign key |
| One active Profile/User membership | Existing partial unique constraint |
| Valid role/status | Current PostgreSQL checks cover ProfileMembership roles and Profile/Workspace statuses; serializer/service policy constrains supported WorkspaceMember roles and lifecycle mutations, with any additional DB check requiring an approved migration |
| Workspace must be mapped | Service now; DB `NOT NULL` only after safe reconciliation |
| Visibility and IDOR | Tenant-scoped queryset |
| Action permission | Central capability policy plus DRF permission |
| Same-Profile cross-table relationship | Transactional service validation; DB constraint where representable |
| Last active Owner membership | Locked service plus available DB defenses |
| Invitation one-time/concurrent acceptance | Constraint plus locked service |
| Syntax/field shape | Serializer |
| Material audit event | Same transaction as mutation |
| Model `clean()` | Defense-in-depth, not a security boundary |

Signals do not authorize writes: they lack a reliable actor and are bypassed
by bulk/raw operations.

### 6.3 ORM, bulk, job, and Admin bypass controls

- ProfileMembership, WorkspaceMember, tenant mapping, and ownership writes use
  reviewed services. Application paths must not call `QuerySet.update()`,
  `bulk_create()`, `bulk_update()`, raw SQL, or direct `.save()` for those
  invariant-bearing changes.
- Imports, management commands, background jobs, and webhooks call the same
  services or a separately reviewed, scoped, audited maintenance service.
- Tenant Owner/Admin use the API, not Django Admin.
- Until a tenant-aware Admin design exists, business-model Admin permissions
  are limited to platform operations. Non-superuser staff must not receive
  global business-model access.
- Current Workspace/Task Admin delete paths and User Admin delete/deactivate
  paths are destructive global operations. Disable them or restrict them to a
  separately approved platform maintenance workflow before relying on the
  soft-delete/retention target; do not expose their default Django actions to
  tenant managers.
- Any future tenant-aware Admin must scope `get_queryset()` and FK choices,
  disable unsafe bulk actions, make sensitive fields read-only, route writes
  through services, and have cross-tenant tests.
- Superuser/platform operations are distinct from Profile roles. The delegated
  decision permits tenant-wide Django Admin access only for platform
  superusers until tenant-scoped Admin exists; it does not create an API tenant
  bypass. Sensitive maintenance mutations still require an explicit audited
  operational path.

### 6.4 User deactivation and the active-Owner boundary

The approved invariant requires at least one active Owner membership. Current
supported membership mutations go further and also require that Owner's User
account be active, but a direct `User.is_active=False` write can bypass those
services.

**[APPROVED BY OWNER DELEGATION]** A supported User-deactivation flow must
revoke the account's ability to continue using established sessions, preserve
the last-active-Owner invariant in every affected Profile, and must not
cascade-delete business or historical data. The account-lifecycle service and
Admin restrictions needed to make that global guarantee are not part of
`HT-RBAC-P1-03`; direct ORM/Admin writes remain a documented bypass until that
separate implementation is completed.

The approved target for that later account-lifecycle implementation is:

1. use a dedicated account-lifecycle service, not direct User Admin/ORM write;
2. enumerate every active Profile where the target User is an Owner;
3. inside one transaction lock those Profiles in stable UUID order, then lock
   their relevant Owner memberships in stable UUID order;
4. recheck that every affected Profile retains another active Owner whose User
   is active, otherwise reject the operation;
5. deactivate the User, revoke their sessions, and write per-Profile
   plus account audit events atomically; and
6. make `is_active` and User deletion unavailable through default Admin paths,
   or route a reviewed Admin action through the same service.

Tests for the future account-lifecycle implementation must cover a User who owns
several Profiles, concurrent owner demotion versus deactivation, sole-owner
handling, session-established-then-deactivated requests, rollback/audit, and
stable multi-Profile lock ordering. Direct SQL
outside reviewed application/maintenance services remains an operational
privilege and must be audited; a simple row constraint cannot enforce this
cross-row/cross-table invariant.

## 7. Profile Invitation contract

### Current implementation reconciliation — HT-INV-P2-04 (2026-10-23)

This paragraph is authoritative for current source and supersedes the
historical proposal/dependency/open wording retained in sections 7.3-7.7 for
design traceability. `ProfileInvitation` and additive
`workspace.0004_profileinvitation` are implemented. The aggregate stores only
a unique SHA-256 digest of a >=256-bit credential, normalized recipient email,
optional recipient binding, requested `ADMIN`/`MEMBER` role, protected Profile
and inviter membership, seven-day expiry, five-state lifecycle,
`QUEUED`/`SENT`/`FAILED` delivery state, terminal actors/timestamps, and
one-to-one replacement lineage. Database constraints/indexes enforce the
approved enums, consistency, ordering, uniqueness, and lookup paths.

Recipient accept/decline requires an active authenticated User whose freshly
locked current email is the unique normalized account match, an optional bound
recipient match, a `SENT` invitation, and the one-time credential. This is
email-control proof scoped to the invitation, not global verified-email state;
therefore no recipient inbox is exposed. Issuance before registration is
allowed, but eventual ambiguous/mismatching/inactive identity fails closed.
Acceptance never changes an active membership role. It creates one membership
or reactivates exactly one compatible inactive non-Owner row, and atomically
soft-revokes stale active WorkspaceMember rows so Profile rejoin never restores
Workspace access.

Create/revoke/resend/accept/decline use Profile-first locking, revalidate the
manager/original inviter, write AuditLog in the state transaction, and allow
one terminal winner under concurrency. Resend creates a replacement and rotates
the credential; replay fails. Delivery runs on commit, refuses console/dummy/
file backends, records failures honestly, and recovers through scoped manager
discovery plus resend. Durable PostgreSQL issuance limits enforce five per
normalized recipient/24h and 30 per inviter/24h; cache throttles are additional
process-local protection pending a shared deployment cache. **REAL EMAIL
DELIVERY NOT VERIFIED.** `workspace.0004` has completed its separately
authorized development rollout; production and every other persistent target
remain unauthorized.

### HT-AUTH-P1-02 compatibility reconciliation — 2026-10-24

HT-AUTH-P1-02 adds a durable current-email verification signal and independent
email-verification/password-reset credentials in the Accounts domain. This is
global identity-security state, not a Profile/Workspace role, membership, or
tenant authorization claim. Verification request and confirmation require the
same authenticated User. Password reset is public and neutral in HTTP status/
body across account outcomes, but request timing is not equalized or verified
indistinguishable. Neither verification nor reset can grant Profile access.

Reset credentials are also bound to a fingerprint of the exact encoded Django
password state. A normal password change revokes pending reset credentials;
even a direct queryset password update that bypasses the model hook fails the
fingerprint comparison at confirmation. A material email change revokes both
pending verification and reset credentials, including an `A -> B -> A`
sequence. These identity controls remain independent of tenant capabilities.

The existing Invitation contract is deliberately unchanged by this task.
Accept/decline continues to require an active authenticated recipient, a unique
fresh match between the current normalized account email and invitation email,
delivery state `SENT`, and that invitation's one-time credential. It does not
also require `User.is_email_verified`. This preserves the reviewed Invitation
flow and avoids suddenly blocking the three unverified legacy development
Users. No verified status is inferred from legacy data or from accepting an
Invitation.

The new verification state makes a future stricter Invitation policy
technically possible, but introducing such a gate would be a separate approved
behavior change with legacy/onboarding compatibility tests. Until then, the
historical verified-email dependency wording in section 7.4 is superseded by
the current implementation reconciliations above. **REAL EMAIL DELIVERY NOT
VERIFIED** remains true for both Invitation and account-security messages, and
their cache throttles remain process-local without a shared production cache.
Reset confirmation uses independent token-fingerprint `10/hour` and client-
address `30/hour` counters. Malformed Unicode in public reset or Invitation
recipient input fails closed with `400`, not `500`.

The consent boundary, email binding, one-time expiring credential, role ceiling,
seven-day TTL, resend invalidation, initial rate limits, and minimum metadata
retention below are **[APPROVED BY OWNER DELEGATION]**. This remains a design
contract only: `HT-RBAC-P1-03` does not add an Invitation model, migration,
service, endpoint, token, or delivery flow. Bullets still labeled
**[PROPOSED]**, **[OPEN]**, or **[DEFER]** remain unavailable.

### 7.1 Aggregate and consent boundary

- **[APPROVED]** The invitation joins a User to a Profile, not directly to a
  Workspace. Acceptance is required before that User becomes an active member,
  and duplicate active Profile memberships are forbidden.
- **[OPEN]** Acceptance will either reactivate a selected inactive history row
  or create a new active ProfileMembership. The row-history strategy must be
  approved before implementation.
- **[APPROVED]** Only after acceptance may Profile Owner/Admin use the separate
  direct-add operation to create Workspace membership for that active Profile
  member.
- **[DEFER]** A combined UI may orchestrate these two explicit operations
  later, but it must not hide or bypass the Profile-consent transition.

### 7.2 Authority and requested role

- **[REQUIREMENT]** The outsource assigns invitation sending to Owner/Admin.
  It described a Workspace invitation; the later approved consent boundary
  requires the invitation to join Profile first.
- **[APPROVED BY OWNER DELEGATION]** Active Profile Owner/Admin in the exact
  Profile may create a Profile invitation; Profile Member and every
  Workspace-only role are denied.
- **[APPROVED BY OWNER DELEGATION]** Owner may invite `MEMBER` or `ADMIN`.
- **[APPROVED BY OWNER DELEGATION]** Admin may invite `MEMBER` only and cannot
  invite `ADMIN`.
- **[DEFER]** Exact list/revoke/reinvite authority and visibility remain part of
  the later Invitation API contract. No role may use those operations to exceed
  its approved creation ceiling.
- **[APPROVED BY OWNER DELEGATION]** Invitation cannot grant `OWNER`.
  Ownership is a separate
  Owner-only, locked transition after accepted membership. This avoids an
  invitation bypass around last-owner/Owner governance.
- **[APPROVED BY OWNER DELEGATION]** The invitation is bound to its recipient
  email. Exact account binding still depends on verified-email support as
  described in section 7.4.

### 7.3 Historical record proposal (superseded by HT-INV-P2-04)

The following table is retained as design history. The implementation
reconciliation above and current source are authoritative:

| Field/constraint | Proposed contract |
|---|---|
| `profile` | Required tenant FK |
| `recipient_email_normalized` | Required canonical invitation identity snapshot |
| `recipient_user` | Nullable binding when resolution is unambiguous |
| `requested_role` | Approved Profile role ceiling only |
| `invited_by` | Actor snapshot/FK subject to retention policy |
| `status` | `PENDING`, `ACCEPTED`, `DECLINED` (recipient reject), `EXPIRED`, `REVOKED` |
| `token_hash` | Unique digest only; raw token is never persisted |
| `expires_at` | Required; approved initial TTL is 7 days |
| terminal metadata | Retained for at least 12 months after terminal state; terminal timestamp, actor/reason where applicable, optional superseded link |
| uniqueness | At most one `PENDING` invitation per Profile/normalized email and, when bound, per Profile/recipient User; stale pending is terminalized under lock before replacement |
| indexes | Profile/status/expiry and safe recipient-inbox lookup |

**[APPROVED BY OWNER DELEGATION]** Reinvite/resend invalidates the prior
credential and issues a new one; it never silently extends or reuses the old
token. The proposed state machine keeps terminal records immutable and retains
their metadata for at least 12 months. Automated purge is explicitly outside
this task.

### 7.4 Historical recipient/account proposal (superseded)

- **[REQUIREMENT]** Input identity is email; username is never invitation
  identity.
- **[PROPOSED]** Validate as an email, trim surrounding whitespace, then apply
  Unicode NFC plus whole-value `casefold()` (matching the current registration
  direction) once and persist that canonical value. Enforce pending uniqueness
  on the stored normalized field, not on caller input. Because current User
  email has no race-proof case-insensitive DB constraint, an existing-account
  lookup must fail closed unless it resolves exactly one User; identity
  hardening may require HT-AUTH-P1-02 before launch.
- **[DEPENDENCY]** Production Profile Invitation must not be enabled until the
  recipient account has a reviewed, persisted verified-email signal and the
  acceptance flow binds the active authenticated account to the invitation's
  normalized email. A hashed one-time token alone does not verify email
  identity and is not sufficient to claim that the flow is production-safe.
  Exact registration/linking behavior for an unregistered recipient belongs to
  `HT-AUTH-P1-02` and the later Invitation task. Token possession alone never
  grants tenant read access.
- If the target is already an active Profile member, invitation creation
  returns a deterministic `already_member` conflict and never changes their
  role. Role change and Workspace add are separate flows.
- An inactive historical membership must still go through invitation. Whether
  to reactivate a prior membership row or create a new active row is **[OPEN]**.
- **[PROPOSED]** Rejoining a Profile must not silently restore historical
  Workspace access. The current schema distinguishes soft-revoked
  `WorkspaceMember.is_active=false` rows, which remain ineffective, from rows
  left active while Profile membership is inactive. The latter would become
  effective again if Profile membership were reactivated, so Invitation/rejoin
  implementation still needs an Owner-approved deactivate/restore strategy.
- Invitations to unregistered email addresses remain **[DEFER]** because
  current authentication has no verified-email invitation onboarding flow.
  Ambiguous case-insensitive account matches must fail closed.

### 7.5 Historical token/delivery proposal (superseded)

- Generate at least 32 cryptographically random bytes (256 bits) and encode
  URL-safely. Store only a unique SHA-256 digest; never store or log raw token.
- Raw token exists only long enough to construct delivery. It is absent from
  management responses, serializers, AuditLog, exceptions, telemetry, and
  access logs.
- Accept/decline are CSRF-protected `POST` mutations. Prefer token in the POST
  body after landing/login, not a path or query. Any landing page must use
  `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, no analytics, and
  remove token material from browser history.
- Send notification only with `transaction.on_commit`. Delivery failure does
  not create membership; retry rotates the credential. Permission state and
  delivery telemetry remain separate.
- Invalid, unknown, expired, revoked, declined, or wrong-recipient tokens use
  a uniform non-enumerating response. An already-accepted token may return the
  same logical success only to the same authenticated recipient, with no new
  write; every other replay uses the generic invalid response.
- **[APPROVED BY OWNER DELEGATION]** Initial limits are five invitation
  attempts per recipient email per 24 hours and 30 invitations per inviter per
  24 hours. The implementation must use a deployment-appropriate shared
  enforcement mechanism before production; these approved limits are not
  implemented by this task.

### 7.6 Historical state/concurrency proposal (superseded)

```text
PENDING ──accept──> ACCEPTED
        ├─decline─> DECLINED
        ├─expire──> EXPIRED
        └─revoke──> REVOKED
```

- Valid means `status=PENDING` and `expires_at > now`, even before a cleanup
  job materializes `EXPIRED`.
- Token lookup may identify the Profile; inside `atomic`, lock in the order
  Profile → Invitation → relevant ProfileMembership rows, then revalidate all
  actor/recipient/status/expiry/role conditions.
- Accept activates at most one membership using the create-versus-reactivate
  history strategy selected in the later Invitation implementation review,
  marks the invite accepted, and writes both invitation and membership audit
  events atomically.
- Concurrent accept/accept, accept/revoke, and accept/reinvite produce exactly
  one terminal winner. Reconcile any `IntegrityError` by rereading; never
  overwrite an existing membership role.
- A retry by the same recipient after successful acceptance may return the
  same logical result without another write. Other replays get the generic
  invalid response.
- Whether acceptance revalidates the inviter's current authority, or pending
  invitations survive inviter demotion/removal, is **[DEFER]** to the Invitation
  implementation review. Revalidation is the proposed fail-closed policy.

### 7.7 Historical audit proposal (superseded)

Proposed events:

- `profile.invitation.created`
- `profile.invitation.accepted`
- `profile.invitation.declined`
- `profile.invitation.expired`
- `profile.invitation.revoked`
- `profile.invitation.replaced`
- corresponding `profile.membership.created` or `.reactivated`

Record Profile/invitation/target User IDs, requested role, before/after state,
actor, timestamps, reason, and request/correlation ID as appropriate. Never
record raw token, token hash, or unmasked recipient email in general logs.
Current AuditLog lacks a canonical tenant FK; tenant-aware audit schema is a
dependency before exposing tenant audit history.

## 8. API surface — Workspace and internal Task workflow implemented

All routes use global SessionAuthentication and `IsAuthenticated`; no tenant
route receives `AllowAny`. `HT-API-P1-04` supplies the four reads and
`HT-WORK-P2-02` supplies the bounded Workspace write/member-manager and
Profile/Workspace lifecycle operations marked current below. Every unsafe
method requires CSRF. General Profile CRUD/membership APIs, hard delete, and
self-leave remain unavailable behind their own gates. `HT-INV-P2-04` adds the
bounded authenticated Invitation routes in section 8.3; `workspace.0004`
remains unapplied to development.

`HT-TASK-P2-03` additionally implements the bounded Task and internal Review
routes in section 8.2. Those source routes are not deployed to development
until `tasks.0002` and `reviews.0002` receive a separate controlled rollout.

### 8.1 Profile, Workspace, and membership

Current routes:

```text
GET /api/v1/profiles/
GET /api/v1/profiles/{profile_id}/
POST /api/v1/profiles/{profile_id}/archive/
POST /api/v1/profiles/{profile_id}/restore/
GET/POST /api/v1/profiles/{profile_id}/workspaces/
GET/PATCH /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/
POST /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/archive/
POST /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/restore/
GET/POST /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/members/
PATCH/DELETE /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/members/{membership_id}/
```

Proposed and not implemented:

```text
POST       /api/v1/profiles/
PATCH      /api/v1/profiles/{profile_id}/
GET        /api/v1/profiles/{profile_id}/members/
PATCH      /api/v1/profiles/{profile_id}/members/{membership_id}/
```

Profile and Workspace use `ACTIVE`/`ARCHIVED`; Workspace membership uses
`is_active`. Profile archive/restore is Profile Owner-only. Profile Owner/Admin
may archive/restore a Workspace, while Workspace Admin cannot. Archived rows
remain tenant-scoped/readable; archived Profile blocks supported child writes,
and archived Workspace blocks metadata/member mutations but remains restorable
while its Profile is active. Transitions are idempotent, locked, and audited.
Hard delete is not exposed.

Current Workspace write-validation contract:

- Workspace creation accepts exactly required `name`, required `period`, and
  optional `description`. `period` must be the first day of the represented
  month, is immutable through supported paths, and is unique per Profile even
  when the existing Workspace is archived. Metadata update accepts only
  `name`/`description`; empty/unchanged input is a no-op with no audit event.
  `profile`, transitional `owner`, lifecycle `status`, IDs, timestamps,
  membership data, roles, and unknown fields are rejected. Profile and owner
  are server-set from the authorized parent/actor, so a body cannot reparent or
  impersonate ownership.
- Direct Workspace add accepts `{target_profile_membership_id, role}`, not a
  global User ID. The target membership must be active in the nested Profile;
  the role must be approved and effective. `ADMIN`, `MEMBER` (Editor), and
  `VIEWER` are supported subject to the actor's ceiling;
  `WorkspaceMember.OWNER` always fails closed and is never newly assigned. If
  the one `(workspace, user)` row is inactive, direct-add reactivates that same
  row with the permitted requested role; an already-active duplicate conflicts.
- Role update accepts exactly `role`. Soft revoke uses `DELETE`, immediately
  removes effective access, and retains the row. Profile Owner/Admin may manage
  `ADMIN/MEMBER/VIEWER`; Workspace Admin may manage only `MEMBER/VIEWER` and
  cannot alter an Admin. Editor, Viewer, an unassigned Profile Member, legacy
  `OWNER`, staff/superuser flags, and transitional owner do not grant a write
  capability.
- The member roster is manager-only and actor-bound in SQL. It returns only
  supported effective assignments backed by an active User and active
  same-Profile ProfileMembership; stale/downgraded actor authority fails
  closed. Results expose assignment ID, ProfileMembership ID, effective role,
  active state, and timestamps only—never User ID, email, username, or other
  PII. Only effective active assignments are listed.
- Services re-resolve tenant authority under Profile-first locks and write
  `profile.archived/restored`, `workspace.created/updated/archived/restored`,
  or `workspace.membership.created/updated/revoked/reactivated` audit events in
  the mutation transaction. Audit failure rolls back the mutation; idempotent
  lifecycle replay writes no duplicate audit, and duplicate direct-add returns
  stable `409` without creating one.
- Invalid in-scope bodies use `400`, visible but forbidden actions use `403`,
  malformed/unknown/wrong-parent/out-of-scope URL resources use the same
  generic `404`, and duplicate active assignment or Profile/month uses `409`.
  Nested IDs and serializer checks are never authorization evidence.

Profile creation/update and Profile membership mutation remain proposed, not
implemented. Future Profile creation may accept approved mutable fields such
as `{name}` with creator/initial Owner server-set through the bootstrap service,
but self-service eligibility remains open.

### 8.2 Task and internal Review workflow

Current source routes:

```text
GET/POST  /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/
GET/PATCH /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/
POST      /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/assign/
POST      /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/start/
GET/POST  /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/deliverables/
POST      /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/deliverables/{deliverable_id}/approve/
POST      /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/deliverables/{deliverable_id}/request-changes/
```

- Every effective Workspace reader may read Task and Deliverable history.
  Viewer remains read-only. An unassigned Profile Member has no fallback.
- Profile Owner/Admin and assigned Workspace Admin create/update/assign Tasks
  and perform internal approval/request-changes. Only the current active
  assignee with ordinary Profile `MEMBER` plus Workspace `MEMBER` (Editor)
  capability may start or submit.
- Workflow is `PENDING -> ASSIGNED -> WORKING -> REVIEW`, then `COMPLETED`
  after approval or back to `WORKING` after changes are requested. There is no
  arbitrary status, cancellation, PUT, delete, claim, or comments endpoint.
- Review capability never permits self-review. Only the latest submitted
  revision can be decided; repeat/stale decisions conflict.
- Strict input, server-derived tenant ownership, no-PII attribution, scoped
  querysets, lock-time capability revalidation, atomic audit, CSRF, and generic
  wrong-parent/cross-tenant `404` apply throughout.
- Internal approval is not Client/Guest approval and creates no Payroll,
  Payment, Invoice, or compensation calculation.

### 8.3 Profile invitations

```text
GET/POST   /api/v1/profiles/{profile_id}/invitations/
GET        /api/v1/profiles/{profile_id}/invitations/{invitation_id}/
POST       /api/v1/profiles/{profile_id}/invitations/{invitation_id}/revoke/
POST       /api/v1/profiles/{profile_id}/invitations/{invitation_id}/resend/
POST       /api/v1/invitations/accept/   {"token": "..."}
POST       /api/v1/invitations/decline/  {"token": "..."}
```

These routes are implemented in source by `HT-INV-P2-04`. There is no
recipient inbox or anonymous preview. HT-AUTH-P1-02 now adds a global
verified-email signal in source, but `accounts.0002` is not yet applied to
development and the Invitation API deliberately retains its narrower
delivered-token proof rather than changing discovery/access behavior in this
task. Management list/detail never returns token, digest, recipient User ID,
inviter identity, or terminal actor IDs.

Current contract:

| Operation | Actor/input | Validation and response boundary |
|---|---|---|
| List/detail Profile invitations | Profile Owner; Admin only within `MEMBER` ceiling | Tenant-scoped paginated/sanitized records; token/digest and User/actor identities omitted; wrong-parent/cross-tenant/hidden role is generic `404` |
| Create | Owner invites `ADMIN`/`MEMBER`; Admin only `MEMBER`; `{recipient_email, requested_role?}` | Server sets tenant/inviter/lifecycle/expiry/digest; default role `MEMBER`; returns sanitized `201`; malformed Unicode recipient is `400`, never `500`; no pre-accept grant |
| Revoke | Authorized manager; exactly empty object | Locked pending transition; sanitized `200`; current capability revalidated |
| Resend | Authorized manager; exactly empty object | Pending/expired source gets an immutable replacement and new credential; old token cannot replay; sanitized `200`; delivery runs after commit |
| Accept/decline | Matching active authenticated User; `{token}`; CSRF | Server derives tenant/recipient and requires unique current-email match plus `SENT` delivery; terminal/expired/replayed/mismatched state is generic `409`; accept returns only membership/navigation summary |

Request serializers reject unknown/server-owned fields. All routes use
SessionAuthentication, deny anonymous callers, enforce CSRF on unsafe methods,
and return non-cacheable responses. The approved seven-day TTL, resend
invalidation, role ceilings, durable issuance limits, token-action throttle,
inviter revalidation, and locked membership/rejoin behavior are implemented.
`workspace.0004` is applied only to the approved development database after
HT-DB-P1-08; all other persistent rollouts remain gated. Delivery was tested
only with the isolated locmem adapter; **REAL EMAIL DELIVERY NOT VERIFIED**.

### 8.4 Deliberately deferred APIs

- Task comments, Marketplace/claim, Task soft delete, cancellation, external
  Client/Guest review, media upload/storage, and Payroll effects remain behind
  their own contracts.
- Client/Project/Finance/Audit endpoints wait for their canonical tenant schema.
- Client Portal and Guest Review wait for separate capability contracts.

## 9. Required negative and concurrency tests

### 9.1 Tenant/query isolation

- Profile A membership never grants Profile B access.
- Profile selection in cookie/header/session never grants rights.
- InvitationRecipientContext before acceptance can access only the recipient's
  sanitized invitation operations and cannot read the invited Profile,
  Workspace, roster, Task, Client, Project, Finance, or Audit data.
- Profile creation bootstrap creates exactly one Profile plus initial Owner
  atomically when enabled, but cannot be reused as access to an existing Profile.
- Profile Member without Workspace membership gets the same `404` as an
  unknown Workspace/Task.
- Profile Owner/Admin sees all mapped Workspaces in the same Profile without
  needing Workspace membership.
- Existing WorkspaceMember plus inactive ProfileMembership is denied.
- A WorkspaceMember row with legacy `OWNER` or an unknown role is denied;
  approved `ADMIN`, `MEMBER`, and `VIEWER` rows map only to their documented
  Workspace-scoped capabilities.
- Inactive User is denied.
- `Workspace.profile=NULL` is never listed or retrieved.
- Nested Profile A with Workspace B returns `404`.
- Search/filter/order/prefetch/pagination/count cannot widen scope.
- Staff/superuser does not bypass API tenant scope unless a separate approved
  operator path is used.

### 9.2 Object/body IDOR

- A real unauthorized UUID and random UUID return the same status/body.
- Task in another or sibling unauthorized Workspace returns `404`.
- Cross-tenant assignee/Client/Project/Workspace/reference IDs return generic
  validation error and create no row.
- Tenant IDs in request body cannot reparent an object.
- Workspace creation ignores/rejects a body-supplied transitional owner and
  sets compatibility ownership server-side to the authorized creator.
- Denied requests create neither partial writes nor audit events.
- Current membership services are tested after refactor to prove no global
  pre-authorization lookup leaks target existence.

### 9.3 Roles and actor invariants

- Admin cannot create/update/deactivate/remove Owner or mint Workspace Owner.
- Profile Admin cannot archive/restore a Profile; Profile Owner can.
- Profile Owner/Admin can archive/restore a same-Profile Workspace; Workspace
  Admin cannot.
- Workspace Admin cannot manage Profile membership/invitations, Profile-wide
  Client data, or Finance.
- Workspace Admin can assign only Editor (`MEMBER`) or Viewer in its own
  Workspace; it cannot grant Workspace Admin/Owner or act in another Workspace.
- Viewer is denied every mutation and all unapproved export/download paths.
- Transitional `Workspace.owner` and `WorkspaceMember.OWNER` do not grant
  Profile authority.
- Client/Guest credentials cannot call internal endpoints.
- Task creator, assignee, commenter, uploader, and reviewer are authorized in
  the Task Workspace at write time.
- A submitter cannot approve their own Deliverable; approval remains unavailable
  until a concrete Review capability and workflow are implemented.

### 9.4 Invitation and concurrency

- Unauthenticated, ordinary member, Workspace-only, cross-Profile sender, and
  Admin→Owner invitation attempts are denied.
- Email case variants and concurrent creation produce at most one pending
  invitation per Profile/recipient.
- Existing active member cannot be reinvited or role-changed via invitation.
- Wrong logged-in user, inactive user, changed email, malformed/unknown,
  expired, declined, revoked, and replayed token cases are non-enumerating.
- Concurrent accept/accept creates/reactivates exactly one active membership
  with one effective transition; accept versus revoke/reinvite has one winner.
- Invitation expiry uses the approved seven-day TTL; resend/reinvite invalidates
  the previous credential. Creation enforces five attempts per recipient email
  and 30 invitations per inviter in 24 hours.
- Invitation acceptance never creates Workspace membership automatically.
- Direct Workspace add still rejects missing/inactive/cross-Profile membership.
- Raw token/hash is absent from serialized responses, AuditLog, and captured
  application/access logs.
- CSRF, throttle, no-store/no-referrer, empty migration, populated migration,
  and PostgreSQL constraint behavior are tested.

### 9.5 Bypass and regression

- Last-owner and role-revocation races preserve an active Owner membership.
- The future approved account-lifecycle implementation denies unsafe sole-Owner
  deactivation, locks multi-Profile changes in stable order, revokes continued
  use of sessions established before `is_active=False`, and preserves history.
- Duplicate direct-add cannot create duplicate Workspace membership.
- Concurrent creation for the same Profile/month produces one Workspace and
  one stable domain conflict; an archived row still reserves its period.
- Soft-revoked Workspace participation immediately loses effective access;
  concurrent reactivation reuses the same row with one effective transition.
- Archived Profile/Workspace remains tenant-scoped/readable but blocks every
  normal write covered by the lifecycle contract.
- Audit write rolls back with the state mutation.
- Constraint conflicts become domain errors, never unhandled `500` responses.
- Reviewed import/job/Admin paths cannot bypass scope or audit.
- Every endpoint remains a DRF view; no accidental `AllowAny`; unsafe session
  mutations enforce CSRF.
- All 19 Authentication and 10 API Foundation regressions continue to pass.

## 10. Dependency-ordered implementation plan

1. **Completed 2026-10-17:** owner delegation approved the role compatibility
   mapping, tenant non-disclosure rule, account-lifecycle target, and invitation
   ceilings/TTL/throttles/retention listed in section 2.4.
2. **Completed 2026-10-19:** HT-DB-P1-05 verified the target inventory and
   backup, completed an isolated restore rehearsal, reviewed the exact plan,
   applied the existing `workspace.0002` to development, post-checked schema
   and data, then passed direct smoke and the full regression gate. No mapping,
   secret file, business fixture, or authorization for another environment was
   synthesized.
3. **Completed 2026-10-18:** implement verified access contexts,
   tenant-scoped Profile/Workspace selectors, revalidated capability primitives,
   and stable domain exception mapping without opening CRUD.
4. **Completed 2026-10-18:** refactor membership services to
   authorize/scoped-resolve before target lookup and add IDOR, role-ceiling,
   stale/forged-context, service, duplicate, and concurrency tests.
5. **Read slice completed 2026-10-18; schema-free write/member slice and its
   schema-dependent lifecycle/period extension completed in source
   2026-10-19; development rollout completed 2026-10-20:** four minimal
   Profile/Workspace reads are joined by canonical
   monthly Workspace create/metadata update, Profile/Workspace archive/restore,
   and manager-only member list/direct-add/role-update/soft-revoke/reactivation.
   `workspace.0003` is applied only to the approved development database; every
   other target still requires separate approval.
6. After verified-email/account-binding dependencies and the remaining
   Invitation implementation details are reviewed, add only a new additive
   migration (now expected `workspace/0004+`), migration rehearsals, locked service,
   hashed token/delivery flow, audit events, and Invitation API tests.
7. **Implementation complete 2026-10-21; development migration pending:** approved Task
   visibility, management/execution/internal-review roles and state machine are
   encoded in nested Task APIs. PostgreSQL verification is 33/33 targeted,
   169/169 existing regression and 202/202 full; only the controlled
   development migration approval remains pending.
8. Add Client/Project/Finance/Audit tenant schema and APIs in their own
   reviewed migrations/tasks.
9. Add Client Portal and Guest Review principals only after their independent
   capability/expiry contracts are approved.

### 10.1 Acceptance gates for implementation slices

| Slice | Acceptance criteria before the slice can close | Minimum verification |
|---|---|---|
| Access context and selectors | Active User + active ProfileMembership resolved from URL parent; Profile Member Workspace scope is explicit; Profile-null rows and cross-Profile rows are absent from every list/detail/count/search path | Unit tests for context predicates; PostgreSQL API/query tests for nested URL tampering, real-vs-random UUID, pagination/filter leakage, inactive memberships, and Profile-null rows |
| Capability policy | Only owner-approved matrix actions are encoded; inheritance is same-Profile only; no enum, staff flag, selected Profile, or transitional owner FK grants an unstated capability | Parameterized role/action matrix tests; every deny case tested; Client/Guest rejected from internal endpoints |
| Membership services | Parent scope established before target lookup; mutation revalidates under lock; last-owner, same-tenant, duplicate, and audit invariants are atomic; no supported direct/bulk bypass | Service tests for cross-tenant IDs and uniform domain errors; concurrent demote/remove/direct-add tests; rollback/audit tests |
| Minimal Profile/Workspace read API — completed historical slice | Nested/scoped queryset used for every object; no new `AllowAny`; response fields follow approved role visibility; at that slice only safe read methods were exposed and unsupported unsafe methods passed through session-CSRF enforcement | 21 permission/IDOR/API contract tests plus 29 Authentication/API Foundation regressions and full 101-test PostgreSQL suite |
| Workspace write/member manager API — completed schema-free checkpoint | Strict server-owned fields, same-tenant nested scope, approved action ceilings, actor-bound effective roster, locked revalidation, atomic audit, no PII, CSRF, and stable `400`/`403`/`404`/`409`; at that checkpoint lifecycle methods remained `405` | 111 targeted Workspace tests, 29 Authentication/API Foundation regressions, 140 full PostgreSQL tests, Django system check, and migration consistency checks |
| Workspace lifecycle/period extension — implementation and development rollout complete | Additive lifecycle/period schema; canonical immutable unique Profile/month; Owner-only Profile lifecycle; Owner/Admin Workspace lifecycle; archived reads with normal writes blocked; same-row member revoke/reactivate; lock/role/audit/CSRF/IDOR boundaries; tenant hard-delete API absent | Isolated PostgreSQL `0002→0003` preservation test; controlled development backup/restore/apply/post-check; direct non-mutating smoke; 17/17 targeted lifecycle/schema, 140/140 Workspace, 29/29 auth/API and 169/169 full PostgreSQL tests; dependency/system/migration checks |
| Task/internal Review workflow — implementation complete; development migration pending | Nested tenant scope; manager vs current-assignee role split; one active assignment; revisioned submission; latest-only non-self review; completion only after approval; strict/no-PII API; transactional audit; no Client/Payroll side effects | 33/33 targeted, 169/169 existing regression and 202/202 full PostgreSQL tests; dependency/system/migration-drift checks and independent code review PASS; controlled development migration remains pending |
| Invitation schema/migration | Additive migration only; token digest/status/role constraints and pending uniqueness match approved policy; existing rows are preserved; no plaintext token field | Migration consistency plus empty/populated PostgreSQL forward tests and constraint tests |
| Invitation service | Authorized sender/recipient binding; expiry/replay/reinvite semantics; exactly one active membership and one terminal winner; Workspace membership is never implicit; audit is atomic | Token secrecy/log capture, duplicate/case variants, wrong-user/inactive/expired/revoked/replay, concurrent accept/accept and accept/revoke tests |
| Invitation API/delivery | Authenticated session and CSRF; non-enumerating failures; scoped manager lists; no token/hash serialization; send only after commit; approved throttle/cache contract | API contract, CSRF, throttle, cache/header, delivery-failure, and cross-Profile negative tests |
| Business-domain onboarding | Domain has a canonical non-null/reconciled tenant path and same-tenant relationship service before route exposure | Domain migration rehearsal, cross-tenant relationship tests, API matrix tests, and full PostgreSQL regression |

No slice may claim a pass from design text alone. A completed slice needs
current implementation and actual test evidence, as recorded below; all
unimplemented slices retain their later authorization and verification gates.

### 10.2 HT-RBAC-P1-03 implementation evidence — 2026-10-18

- Final targeted Workspace suite: PASS, 51/51.
- Final full PostgreSQL suite: PASS, 80/80, including all 19 Authentication and
  10 API Foundation regressions.
- `pip check`, Python compile, Django system check and
  `makemigrations --check --dry-run`: PASS.
- Independent review found a `dataclasses.replace()` context-forgery risk; the
  context marker was changed to non-init state, capabilities now revalidate
  exact database roles, and forged/stale-context regressions pass.
- No model, migration, route, authentication mechanism or development data
  changed. At that checkpoint, `workspace.0002` was unapplied to development.
- Direct ORM/bulk/raw/Admin writes and the unimplemented global User
  deactivation/session-revocation flow remain explicit boundaries.

### 10.3 HT-API-P1-04 implementation evidence — 2026-10-18

- Four current routes provide Profile list/detail and nested Workspace
  list/detail under `/api/v1/`; all use SessionAuthentication and explicit
  tenant permissions with no `AllowAny`.
- Minimal serializers, tenant-scoped querysets, stable bounded pagination,
  generic malformed/unknown/out-of-scope `404`, and GET/HEAD/OPTIONS-only
  behavior are implemented. A late membership-revocation race maps to the same
  generic response instead of escaping as a server error.
- Targeted read API tests: PASS, 21/21, including CSRF-before-`405` behavior.
  Authentication/API Foundation regressions: PASS, 29/29. Final full
  PostgreSQL suite: PASS, 101/101.
- `pip check`, Python compile, Django system check, and
  `makemigrations --check --dry-run`: PASS.
- No model, migration, authentication mechanism, membership-service rule, or
  development data changed in P1-04. The later HT-DB-P1-05 operational task
  applied existing `workspace.0002` to development under separate controls.

### 10.4 HT-DB-P1-05 operational evidence — 2026-10-19

- Existing local Compose PostgreSQL development target independently verified.
  Pre-apply inventory found 3 active Users and zero checked business rows, with
  no checked orphan, unvalidated FK, or leftover test database. The unchanged
  `0002` was additive and required no mapping for this inventory.
- A Git-ignored custom archive passed host/container SHA-256 comparison,
  `pg_restore --list`, and complete archive streaming to `/dev/null`. A full
  isolated restore rehearsal reproduced the expected pre-`0002` state and was
  removed afterward.
- Development-only runtime values were passed in process without a persistent
  `.env` or logged secret. The exact migration plan matched source;
  `workspace.0002` then applied successfully. Final state is 27 migrations,
  Profile/ProfileMembership tables and nullable `Workspace.profile_id`, with
  reviewed constraints/indexes valid and all business counts still zero.
- Direct smoke passed health, anonymous tenant denial and CSRF behavior with no
  `500` or new session. Current isolated PostgreSQL tests passed 21/21 targeted
  read API, 29/29 Authentication/API Foundation and 101/101 full suite. This is
  not authorization for another environment or Invitation APIs; the later,
  separate HT-WORK-P2-02 authorization and result are recorded below.

### 10.5 Historical HT-WORK-P2-02 schema-free evidence — 2026-10-19

This subsection records the earlier checkpoint and is superseded for current
source behavior by section 10.6.

- Implemented `POST` on the Workspace collection and `PATCH` on Workspace
  detail, accepting only `name`/`description` while deriving Profile and
  transitional owner server-side.
- Implemented manager-only Workspace-member `GET`/`POST` collection and
  `PATCH` detail. Direct add uses an active same-Profile
  `target_profile_membership_id`; output omits User identity/PII. Profile
  Owner/Admin and Workspace Admin ceilings match section 2.4, while legacy
  `OWNER` and platform flags fail closed.
- Roster visibility remains tied to current actor authority in SQL and includes
  only effective supported assignments backed by active Profile membership and
  active User. Mutations use scoped locked services and atomic AuditLog events;
  cross-tenant/wrong-parent identifiers are non-enumerating and duplicate add
  maps to stable `409`.
- Verification passed 111/111 targeted Workspace tests, 29/29
  Authentication/API Foundation regressions, and 140/140 full PostgreSQL tests,
  together with Django system and migration consistency checks.
- No model, migration, authentication, or development-data change occurred at
  that checkpoint.
  Development remains at applied `workspace.0002`, with 3 Users and zero
  business rows. Archive/restore and member revoke/deactivate then remained
  `405`; the later approved extension is recorded below.

### 10.6 Historical HT-WORK-P2-02 schema-dependent evidence — 2026-10-19

Status: `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`

- Additive `workspace.0003_workspace_lifecycle_and_period` adds only the
  approved lifecycle/period fields, checks, conditional Profile/month
  uniqueness, and indexes. It changes no applied migration and guesses no
  monthly period for a legacy row.
- An isolated PostgreSQL `0002 → 0003` migration exercise preserved
  Workspace/WorkspaceMember and Task → Deliverable → Review relations while
  leaving legacy period null. Supported new creation requires a first-of-month
  period; direct ORM/bulk/raw null writes remain an explicitly unsupported
  bypass permitted only by the transitional database nullability.
- Profile Owner-only archive/restore, Profile Owner/Admin Workspace
  archive/restore, canonical-month creation, and locked same-row member
  soft-revoke/reactivation are implemented with scoped reads, normal-write
  blocking for archived state, role ceilings, and transactional audit.
- `pip check`, Django system check, and
  `makemigrations --check --dry-run`: PASS. Workspace suite: PASS, 140/140 in
  79.278s. Full PostgreSQL suite: PASS, 169/169 in 82.920s.
- The latest successful post-suite development inventory on 2026-10-19 showed
  27 applied migrations, `workspace.0002` applied, `workspace.0003` absent,
  3 Users, zero checked business rows, and no test database. A read-only check
  on 2026-10-20 found the existing development PostgreSQL container stopped;
  it was not started or changed. Production was not touched.

### 10.7 HT-DB-P1-06 controlled development rollout evidence — 2026-10-20

Status: `COMPLETE / OWNER REVIEW GATE`

- The existing local Compose PostgreSQL 16.14 target was re-identified from
  runtime labels, database, loopback port and named volume. Pre-apply history
  and physical schema agreed at 27 migrations with `workspace.0003` absent;
  inventory was 3 active Users, 2 sessions and zero checked business rows.
- A fresh ignored backup passed SHA-256 comparison, TOC listing, full archive
  read and isolated full restore rehearsal before the exact additive plan was
  applied. `workspace.0003` completed successfully without guessed mapping,
  `--fake`, reverse, deletion or production action.
- Post-apply development has 28 migrations. The four new columns, three
  validated checks, partial unique Profile/month index and three lookup indexes
  are present and valid/ready; inventory is unchanged and no schema/data anomaly
  or temporary database remains.
- Direct development request-stack smoke used no business fixture and changed
  no row/session. Fixture-dependent RBAC, tenant/IDOR, lifecycle, membership and
  concurrency cases passed on isolated PostgreSQL: 17/17 targeted
  lifecycle/schema, 140/140 Workspace, 29/29 auth/API and 169/169 full suite.
- This operational evidence changes no approved RBAC contract and authorizes no
  environment beyond the named development database.

### 10.8 HT-TASK-P2-03 source evidence — 2026-10-21

Status: `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`

- Task read scope reuses the verified Profile/Workspace context and repeats
  live tenant predicates in query evaluation. Malformed, wrong-parent,
  cross-tenant and inaccessible nested resources share a generic `404`.
- `can_manage_workspace_tasks`, `can_execute_workspace_tasks`, and
  `can_review_workspace_deliverables` encode the approved manager/Editor split.
  Services repeat those checks under Profile-first locks and bind execution to
  the current active assignee.
- Additive migrations enforce valid status/priority, one active assignment,
  positive unique revisions and one Review per Deliverable. Protected actor
  FKs and inspection-only Task Admin preserve attribution; Workspace Admin
  delete is disabled to avoid the existing cascade into Task history.
- Targeted service/API/migration verification passes 33/33 in 7.673s,
  existing Authentication/API/Workspace regression passes 169/169 in 87.783s,
  and the final full PostgreSQL suite passes 202/202 in 92.343s. `pip check`,
  Django system check, migration-drift check and independent final code review
  pass; test databases are destroyed.
- Development remains at `tasks.0001` and `reviews.0001`. The source migrations
  are not authorized for apply. `showmigrations` confirms Workspace 0001-0003
  applied; `migrate --plan` succeeds with only additive `tasks.0002` then
  `reviews.0002`. A future rollout must inventory invalid enum
  values, duplicate Reviews and legacy assignments, back up the target and
  stop rather than inventing a cleanup/mapping.

### 10.9 HT-TASK-P2-05 hierarchy/planning source evidence — 2026-10-25

- **[CURRENT]** The Owner authorized Task/Subtask, deadline and priority
  foundation independently from the Project architecture gate. The existing
  Task model is reused; nullable `parent` identifies the same-Workspace parent.
  Root depth is 0, maximum depth is 3 parent edges. Self-parent, cycles,
  cross-Workspace parent relationships and excessive moved-subtree depth are
  validated. The database adds self-parent protection and a protected parent
  FK; cross-row graph invariants require the validated mutation services.
- **[CURRENT]** Reads repeat the existing verified Profile/Workspace scope.
  The new paginated `GET .../tasks/{task_id}/subtasks/` returns direct children
  only. Existing collection POST creates roots/children via optional
  `parent_id`; existing detail PATCH changes parent/deadline/priority. No new
  write route, authentication mechanism, `AllowAny`, role or capability exists.
  Flat lists remain compatible and scoped filters/orderings cannot widen access.
- **[CURRENT]** Profile Owner/Admin and the current Workspace Admin retain
  Task-management capability. An Editor, even when assigned to that Task, and
  a Viewer cannot alter planning metadata. Staff without actual tenant
  membership receive no exception. Archived Profile/Workspace writes and
  inactive membership remain denied. Generic `404` hides foreign or missing
  valid-UUID parents; malformed serializer values and invalid graphs are
  `400`; known in-scope insufficient capability is `403`.
- **[CURRENT IMPLEMENTATION CHOICE]** Each Task/Subtask has an independent
  workflow, assignment, Deliverable/Review history and nullable deadline.
  Parent approval may leave children unfinished; it grants no child approval.
  Child completion does not complete the parent; child request-changes does
  not reopen it. Deadlines do not propagate or constrain each other. These
  simple choices implement the authorized foundation without inventing
  aggregate completion/approval rules or claiming separate new Owner approval.
  Reviewer authority, self-review prohibition, latest-revision validation,
  active-assignee execution and audit atomicity remain unchanged per Task.
- **[CURRENT]** Hierarchy mutations reuse the common Profile -> Workspace ->
  membership locks before Task/parent locks. Shared Workspace serialization
  prevents competing supported reparent operations from creating a cycle or
  exceeding the depth cap. Direct queryset/bulk/raw mutations are outside that
  validated boundary and must not be used to modify the hierarchy. Admin
  remains inspection-only; no hierarchy bypass was exposed there.
- **[CURRENT]** Deadline input is normalized to aware UTC; bad or overflowing
  datetime input is rejected. Existing priority choices/default and manager
  ceiling are reused; status never automatically changes with priority or
  deadline. Material changes are audited in the same transaction.
- **[HISTORICAL IMPLEMENTATION VERIFICATION]** Isolated new/existing Task API **42/42 PASS**
  (4.990s), model/service/workflow **43/43 PASS** (4.770s), and hierarchy
  migration **2/2 PASS** (1.465s). Workspace/RBAC regression **122/122 PASS**
  (60.495s), full PostgreSQL **341/341 PASS** (174.058s), required checks and
  owned-resource cleanup PASS. Status: **IMPLEMENTATION COMPLETE — PENDING
  DEVELOPMENT MIGRATION APPROVAL / OWNER REVIEW GATE**.
  At that gate development had tasks.0002 with no parent column,32 migrations,
  3 Users/2 Sessions and zero token/business rows. HT-DB-P1-10 supersedes this
  operational state with the separately approved exact development apply
  described above. No production write is authorized.
- **[OPEN PROJECT GATE]** Project remains design-only. The literal
  Workspace-owned Project alternative conflicts with the previously accepted
  cross-month Project target. The A/B comparison and reconciled optional
  Profile/Client-scoped alternative are in `PROJECT_ARCHITECTURE_REVIEW.md`;
  no Project model/API/migration or change to the accepted history was made.

### 10.10 HT-COM-P2-06 communication foundation — 2026-10-25

The Owner authorized Comment/Notification implementation, not a new role or
public principal. These are current implementation choices for Owner review,
not retroactive claims of approval for previously deferred numeric/policy
details. All earlier tenancy, Viewer read-only and Task review rules remain.

- Task readers may read comments, including tombstones and archived history.
  Active Profile Owner/Admin, Workspace Admin and Editor may create; only
  the author with current comment capability may edit. The author or a
  current manager may soft-delete. Managers cannot rewrite another author.
  Viewer/staff flags/client identity alone grant no mutation. Revocation and
  inactive membership remove access; archived Profile/Workspace blocks writes.
- New content is plain text, nonblank, valid Unicode without NUL, at most4000
  characters. The author and Task are immutable through API. Soft-delete
  retains internal content and emits a redacted tombstone; repeated delete
  is idempotent. IDs/timestamps in audit preserve action history without
  copying full text. Full text edit revisions are not implemented.
- Comment mutations reuse Profile→Workspace→Task→Comment locks and atomic
  audit. Task/parent/Deliverable/Review state does not change from a comment.
- Notifications are personal database projections of successful audit-backed
  Task events. They are atomic with mutation/audit: persistence failure rolls
  back all three. No signal, post-commit delivery, worker, email or new event
  broker exists. `(event,user)` prevents repeated fanout to the same recipient.
- Assignment targets its Editor; submitted review targets current managers;
  review results target the uploader; new comments target creator and active
  assignee. Actor, duplicate, inactive and unreadable recipients are excluded.
  Event/Task/Deliverable/Review/uploader proofs come from persisted records.
- Own feed/count/mark-read repeat live User/Profile/Workspace and canonical
  target predicates. Revoked access hides the row and unread count, never
  grants access via notification UUID. Staff has no bypass. Mark-read uses
  Profile→Workspace→Notification locks and permits still-readable archives.
  Legacy unscoped notifications remain unmapped/hidden. Display text is
  constant, with no comment body, task title or User PII.
- **[HISTORICAL HT-COM-P2-06 verification]** Only tasks.0004 and notifications.0002 were pending; development remained
  at33 migrations/tasks.0003/notifications.0001. Comment40/40 tests pass;
  Notification34/34 and Task/Review128/128 tests pass after correcting an
  inverted Workspace existence guard; no scope/permission relaxation occurred.
  Security253/253 and full PostgreSQL415/415 (191.226s) PASS, both runner
  exits0, required checks and owned cleanup PASS. Status: IMPLEMENTATION
  COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL / OWNER REVIEW GATE.
  See HANDOVER for the authoritative current verification checkpoint.

Operational reconciliation — HT-DB-P1-11, 2026-10-26: Owner conditionally
authorized exactly those two development migrations. Both applied once after
verified backup/restore rehearsal; development has35 migration records,44
orphan-free valid FKs and unchanged legacy data. Read-only smoke, current
Comment40/Notification34/Task128/security253/full415 regression and final
integrity/owned cleanup PASS, all launcher/Python exits0 (see HANDOVER).
HT-DB-P1-11 COMPLETE / OWNER REVIEW GATE. No capability, recipient, consistency
or Task/Review rule changed. Project remains PENDING OWNER DECISION.

## 11. Delegated decisions resolved and downstream review gates

The former seven-group RBAC owner-review blocker is resolved by the decisions
in section 2.4. `HT-RBAC-DESIGN-P0-01` is complete and approved by owner
delegation. In particular, no later review may silently reopen these rules:

- Profile Owner/Admin inherit same-Profile Workspace content management, while
  Profile Admin receives no implicit sensitive Finance capability.
- Workspace `ADMIN`, `MEMBER`, and `VIEWER` map to Workspace Admin, Editor, and
  read-only Viewer. Legacy Workspace `OWNER` fails closed and is never newly
  assigned. Workspace Admin can manage only its own Workspace and may grant
  only Editor or Viewer participation.
- Profile Admin follows a least-privilege membership ceiling: it may manage an
  ordinary Profile `MEMBER`, but cannot grant or alter `ADMIN` or `OWNER`.
- Profile creation and last-active-Owner protection are transactional. A future
  supported User-deactivation flow must revoke session usability and preserve
  historical/business data.
- Invitation email binding, one-time expiry, no-`OWNER` ceiling, Owner/Admin
  invite ceilings, seven-day TTL, resend invalidation, initial 5/email/24h and
  30/inviter/24h limits, and 12-month minimum terminal-metadata retention are
  fixed target rules. They are not runtime behavior yet.
- Cross-tenant existence is non-enumerating. Global Django Admin is not tenant
  RBAC, and tenant-wide business-model access remains platform-superuser-only
  until a tenant-scoped Admin exists.
- Deliverable approval requires a distinct Review capability and forbids
  self-approval. HT-TASK-P2-03 now grants internal review to Profile
  Owner/Admin and assigned Workspace Admin, and fixes the bounded Task/
  Deliverable/Review state machine. This does not grant Client/Guest approval
  or any Payroll/Payment effect.

The following are separate downstream review gates, not stale questions that
block `HT-RBAC-P1-03`:

1. Task soft delete/retention, cancellation, full Comment text revision history,
   Marketplace/claim,
   media upload/storage, Client/Guest review, and Payroll pricing/eligibility/
   business trigger. The internal visibility, assignee attribution, state
   transitions and reviewer authority implemented by HT-TASK-P2-03 are no
   longer open questions.
2. General Profile create/edit/settings API, Workspace self-leave,
   Profile-membership invitation/rejoin behavior, and self-service eligibility
   beyond the implemented canonical-period, archive/restore, and manager-only
   Workspace membership lifecycle.
3. Verified-email persistence and account linking before production
   Invitation, plus unregistered-recipient onboarding, delivery channel,
   inviter-authority revalidation, exact terminal-state/history strategy,
   anonymization, legal hold, and controlled purge after the approved minimum.
   Token hashing by itself is not sufficient email-identity verification.
4. Exact API error envelope/status choices beyond the approved non-disclosure
   requirement, plus any future audited platform-operator API bypass.
5. Invoice numbering/detailed billing; Client Portal/Guest Review exact
   capabilities, account linking, and default expiry; and broader retention/
   purge policy.

Every `R/P`, `P`, or `DEFER` capability not covered by an approved rule remains
denied/unimplemented until its own task. An unknown row discovered in a target
database remains an environment-specific mapping blocker to escalate with
evidence, never permission to invent a tenant mapping.

