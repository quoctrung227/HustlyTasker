# HT-RBAC-DESIGN-P0-01

## Capability Matrix, Tenant-Scoped Access, and Invitation Contract

Status: `DESIGN READY — PENDING OWNER APPROVAL`

Date: 2026-10-17

This document is a design deliverable. It does not authorize an API, model,
migration, data change, permission grant, or development-database migration.
The current API contract remains limited to Authentication and Health.

## 1. Evidence and decision labels

The following labels prevent legacy behavior or a technical recommendation
from being mistaken for an approved business rule:

- **[REQUIREMENT]** — capability-level need in `ORIGINAL_REQUIREMENTS.md`.
- **[APPROVED]** — one of the owner-approved tenancy/business decisions in
  `DECISION_LOG.md`.
- **[CURRENT]** — behavior or limitation verified in the current Django
  source, migrations, settings, routes, or database inventory.
- **[PROPOSED]** — least-privilege technical contract proposed for owner
  review; it must not be implemented as an accepted rule yet.
- **[OPEN]** — a product or policy decision still required from the owner.

When sources conflict, an approved decision overrides the legacy reference.
Current source remains authoritative for what is actually implemented.

## 2. Confirmed baseline

### 2.1 Approved boundaries

- **[APPROVED]** Profile represents a company/team and is the tenant root.
  Workspace is a monthly operational scope inside exactly one Profile.
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
  least one usable Owner. Owner changes require transaction/concurrency
  protection. Profile Admin cannot appoint, demote, deactivate, or remove an
  Owner.
- **[APPROVED]** Joining a new Profile requires accepted consent through an
  invitation. Profile Owner/Admin may directly add only an already-active
  Profile member to a Workspace. Material membership changes are audited.
- **[APPROVED]** Task belongs to one Workspace. Client belongs to Profile;
  Project may span Workspaces through Tasks. Related Client, Project,
  Workspace, Task, Invoice, and Payment records must preserve the approved
  same-Profile paths.
- **[APPROVED]** Client Portal and Guest Review are external, capability-scoped
  principals. They do not become internal Profile or Workspace roles.
- **[APPROVED]** Soft delete is the target for Profile, Workspace, Client,
  Project, and Task. Retention, purge, and hard-delete authority are not yet
  approved.

### 2.2 Current implementation constraints

- **[CURRENT]** `ProfileMembership` implements `OWNER`, `ADMIN`, `MEMBER`, an
  active flag, and a partial unique constraint for one active Profile/User
  membership while retaining inactive history.
- **[CURRENT]** `WorkspaceMember` contains `OWNER`, `ADMIN`, `MEMBER`, and
  `VIEWER`; it has no active flag. These enum values are storage capability,
  not an approved action-level permission contract.
- **[CURRENT]** `Workspace.profile` is nullable for safe legacy transition.
  Unmapped Workspaces must never be exposed by a tenant API.
- **[CURRENT]** `Workspace.owner` is a transitional protected User FK and is
  not authorization proof.
- **[CURRENT]** Session authentication and global DRF `IsAuthenticated` prove
  identity only. There is no Profile/Workspace API, tenant-scoped queryset,
  object-permission implementation, or invitation model/API.
- **[CURRENT]** Client, Invoice/Payment, and AuditLog do not yet have a safe
  canonical tenant path; Project does not exist. Those APIs must stay closed.
- **[CURRENT]** `update_profile_membership()` resolves `membership_id`
  globally before actor scope is established. `add_workspace_member()`
  resolves `workspace_id` globally and accepts an already-resolved, unscoped
  target User object. This is not exploitable through an API today because no
  Workspace route exists, but both service boundaries must be refactored
  before exposure so lookup/exception differences cannot become an IDOR
  oracle.
- **[CURRENT]** bulk operations, raw SQL, direct ORM writes, User deactivation,
  and global Django Admin surfaces can bypass service-level invariants.

## 3. Role model proposed for review

### 3.1 Effective internal roles

| Effective role | Scope and proposed meaning |
|---|---|
| Profile Owner | Tenant governance plus inherited Workspace management for every Workspace in the same Profile. Only this role may change Owner status, subject to last-owner locking. |
| Profile Admin | Tenant operations plus inherited Workspace management for every Workspace in the same Profile; never Owner governance. |
| Profile Member without Workspace membership | Profile self/navigation access only; no Workspace content. |
| Workspace Admin | **[PROPOSED]** delegated content manager for exactly one assigned Workspace. Active Profile membership is still mandatory, but the role grants no Profile-admin, Profile-wide CRM, Finance, or Owner authority. |
| Workspace Member | Contributor/editor for exactly one assigned Workspace. Current DB value remains `MEMBER` to avoid an unnecessary migration. |
| Workspace Viewer | **[PROPOSED]** optional read-only role with a field-limited response; do not mint it through an API until its exact read scope is approved. |
| Client/Guest | External principals only, never mapped to an internal role. |

### 3.2 Existing Workspace enum treatment

- **[PROPOSED]** Deprecate `WorkspaceMember.OWNER` as an authorization concept
  and do not create it through new APIs. Profile Owner is the canonical owner.
  Existing rows, if any are later found, require inventory and explicit
  reconciliation.
- **[PROPOSED]** Retain `WorkspaceMember.ADMIN` for narrow Workspace content
  delegation. Removing it would force every Workspace manager to become a
  Profile Admin with access to all Profile Workspaces.
- **[PROPOSED]** Treat `WorkspaceMember.MEMBER` as contributor/editor.
- **[PROPOSED]** Keep `VIEWER` disabled for assignment until the owner approves
  visible fields and download/comment behavior.
- **[PROPOSED]** An inherited Profile Owner/Admin capability takes precedence
  over a lower explicit Workspace role in that same Profile, but never grants
  rights in another Profile.

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
| List/select own active Profiles | A | A | A | A | A | A |
| List Workspaces in Profile | A: all | A: all | Assigned only | Assigned only | Assigned only | DENY |
| Read assigned Workspace metadata | A | A | R/P | R/P | P: limited | DENY |
| Create Workspace / monthly rollover | R/P | R/P | DENY | DENY | DENY | DENY |
| Edit Workspace name/description | R/P | R/P | P | DENY | DENY | DENY |
| Soft-delete/restore Workspace | P: Owner only | DENY | DENY | DENY | DENY | DENY |
| Hard-delete Workspace | DEFER | DENY | DENY | DENY | DENY | DENY |
| Edit Profile settings/branding | P: Owner only | DENY | DENY | DENY | DENY | DENY |
| Soft-delete/restore Profile | P: Owner only | DENY | DENY | DENY | DENY | DENY |
| Read full Profile roster/PII | R/P | R/P | DENY | P: minimal assigned roster | DENY | Self only |
| Invite Profile `MEMBER` | R/P | P | DENY | DENY | DENY | DENY |
| Invite/promote/deactivate Profile `ADMIN` | P: Owner only | DENY | DENY | DENY | DENY | DENY |
| List/revoke/reinvite pending invitations | P: all roles | P: `MEMBER` invites only | DENY | DENY | DENY | DENY |
| Appoint/demote/deactivate Profile `OWNER` | A: Owner only + lock | DENY | DENY | DENY | DENY | DENY |
| Remove/deactivate Profile Member | R/P | P: `MEMBER` only | DENY | DENY | DENY | DENY |
| Leave Profile voluntarily | P: only if another usable Owner | P: self | P: self Profile membership | P: self Profile membership | P: self Profile membership | P: self |
| Direct-add active Profile member to Workspace | A | A | DENY | DENY | DENY | DENY |
| Assign/remove WS Admin/Member/Viewer | P | P | DENY initially | DENY | DENY | DENY |
| Leave/remove own Workspace participation | DEFER: lifecycle | DEFER: lifecycle | DEFER: lifecycle | DEFER: lifecycle | DEFER: lifecycle | N/A |
| Read Task in authorized Workspace | R/P: all | R/P: all | R/P: all | P: assigned + published pool | P: limited | DENY |
| Create/assign/edit any Task | R/P | R/P | R/P | DENY | DENY | DENY |
| Claim/return eligible Task | P: only as contributor | P: only as contributor | P: only as contributor | R/P | DENY | DENY |
| Edit assigned Task / allowed status | R/P | R/P | R/P | R/P | DENY | DENY |
| Comment/upload Deliverable | P: only as contributor | P: only as contributor | P: only as contributor | R/P | DENY | DENY |
| Internal approval/send to Client | DEFER | DEFER | DEFER | DENY | DENY | DENY |
| Manage Profile Client/Project | R/P | R/P | DENY | DENY | DENY | DENY |
| Reference existing same-Profile Client/Project from Task | R/P | R/P | P: scoped selection | P: task-linked only | P: task-linked read | DENY |
| Read/manage Invoice, Payment, payroll | R/P | R/P | DENY | DENY | DENY | DENY |
| Manage Client Portal link | DEFER | DEFER | DENY | DENY | DENY | DENY |
| Manage task-scoped Guest Review link | DEFER | DEFER | DEFER | DEFER | DENY | DENY |
| Read tenant AuditLog | P | P | P: Workspace subset | DENY | DENY | DENY |

The requirement to keep a Task, Client, Project, and Workspace in the same
Profile is approved (`A`); the matrix row above concerns who may perform the
reference action and therefore remains `R/P` or `P`.

### 4.1 Viewer proposal

If retained, Viewer may read only approved Workspace metadata, Task
summary/detail, and explicitly visible Deliverable metadata in the assigned
Workspace. Responses must omit finance/payroll, member email/PII, secrets,
integration fields, and Profile-wide Client data. Viewer cannot create,
update, delete, claim, comment, upload, manage members, export, or download
until each action is explicitly approved. Every unsafe HTTP method is denied.

### 4.2 Important non-inheritance rules

- Workspace Admin does not become Profile Admin and cannot manage Profile
  membership, invitations, Owners, Profile-wide CRM, or Finance.
- A Profile Member does not receive Viewer fallback access to every Workspace.
- Client/Guest credentials cannot call internal member endpoints.
- Profile Owner/Admin inheritance is limited to the same Profile.
- Whether a Profile Owner/Admin must also have explicit Workspace membership
  to act as an assignee/contributor is **[OPEN]**. The proposed secure split is
  inherited management but explicit membership for operational assignment,
  upload, and worker attribution.
- Workspace self-leave/removal is **[DEFER]**: the current WorkspaceMember has
  no active/soft-delete state and one unique row per Workspace/User, so history,
  audit, rejoin, and deletion behavior must be approved before an endpoint.

### 4.3 Narrow bootstrap contexts

Two operations occur before the normal active-membership context and must not
be mistaken for tenant access:

- **Profile creation — [CURRENT + PROPOSED API]:** the existing foundation
  service can atomically create a Profile and its initial Owner. If the owner
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

For proposed Workspace creation while the transitional required
`Workspace.owner` FK remains, the service—not request data—sets it to the
creating active Profile Owner/Admin. It remains compatibility data, never an
authorization source. A later reviewed migration may remove or replace that FK
after all consumers have moved to Profile authority.

## 5. Tenant-scoped request and query boundary

### 5.1 Per-request access context

**[PROPOSED]** Resolve an immutable `ProfileAccessContext` per request:

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
- Fail closed for deprecated, unknown, or not-yet-enabled Workspace roles. A
  row carrying current `OWNER` or unapproved `VIEWER` must not grant visibility
  merely because it exists; migration/reconciliation or explicit policy must
  make the role effective first.
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

| Situation | Proposed response |
|---|---|
| Anonymous request to private SessionAuthentication endpoint | Preserve current DRF behavior: `403` |
| Authenticated user lacks active Profile membership | `404` |
| Resource does not exist or exists outside caller scope | Same `404` status and response shape |
| Profile Member lacks target Workspace assignment | `404` |
| Object is visible but role lacks the requested action | `403` |
| Malformed body reference | `400` |
| Body reference is nonexistent or outside scope | Same generic field-level `400 invalid_reference` |
| Domain/concurrency conflict | Proposed `409`; exact response envelope is open |
| List within valid Profile context but no visible rows | `200` with an empty scoped list |

Raw `DoesNotExist`, `IntegrityError`, object names, tenant names, or differing
timing-dependent detail must not escape. A real unauthorized UUID and a random
UUID receive the same contract.

## 6. Service and transaction boundary

### 6.1 Structure

No new Django app is required. A future implementation can place shared access
selectors/capabilities in `apps/workspace/access.py` or `selectors.py`, DRF
permissions in `permissions.py`, and mutations in the existing `services.py`.

Sensitive service signatures must include the authorized parents, for example:

```text
update_profile_membership(actor, profile_id, membership_id, ...)
add_workspace_member(
    actor, profile_id, workspace_id, target_profile_membership_id, role
)
```

They must not accept a request-derived User/object that was fetched globally.
Before API exposure, refactor both current membership services to:

1. establish/authorize Profile scope;
2. enter an atomic transaction;
3. lock the aggregate in canonical order;
4. re-read actor membership and action capability under lock;
5. resolve targets from tenant-scoped querysets;
6. validate same-tenant and lifecycle invariants;
7. mutate and write AuditLog in the same transaction; and
8. translate constraint conflicts to stable domain errors.

Every sensitive mutation locks `Profile` first. The remaining order is
operation-specific so no path acquires Invitation after Membership:

```text
Workspace/membership: Profile → Workspace (when relevant)
                      → ProfileMembership / WorkspaceMember ordered by UUID
                      → business resource → AuditLog write

Invitation:           Profile → Invitation
                      → relevant ProfileMembership rows ordered by UUID
                      → AuditLog write
```

Read-only requests need no lock. Task/content writes should lock only the rows
needed to make membership validation race-safe; locking an entire Profile for
every content write would be unnecessarily expensive.

### 6.2 Defense allocation

| Invariant | Primary enforcement |
|---|---|
| Ownership path | PostgreSQL foreign key |
| One active Profile/User membership | Existing partial unique constraint |
| Valid role/status | PostgreSQL check constraint after contract approval |
| Workspace must be mapped | Service now; DB `NOT NULL` only after safe reconciliation |
| Visibility and IDOR | Tenant-scoped queryset |
| Action permission | Central capability policy plus DRF permission |
| Same-Profile cross-table relationship | Transactional service validation; DB constraint where representable |
| Last usable Owner | Locked service plus available DB defenses |
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
- Superuser/platform operations are distinct from Profile roles and require a
  separately approved bypass/audit policy.

### 6.4 User deactivation and usable-Owner invariant

`User.is_active=False` currently bypasses ProfileMembership services and can
make the last Owner unusable. **[PROPOSED]** Before any account-deactivation or
User-delete flow is exposed:

1. use a dedicated account-lifecycle service, not direct User Admin/ORM write;
2. enumerate every active Profile where the target User is an Owner;
3. inside one transaction lock those Profiles in stable UUID order, then lock
   their relevant Owner memberships in stable UUID order;
4. recheck that every affected Profile retains another active Owner whose User
   is active, otherwise reject the operation;
5. deactivate the User, revoke their sessions as approved, and write per-Profile
   plus account audit events atomically; and
6. make `is_active` and User deletion unavailable through default Admin paths,
   or route a reviewed Admin action through the same service.

Tests must cover a User who owns several Profiles, concurrent owner demotion
versus deactivation, sole-owner denial, session-established-then-deactivated
requests, rollback/audit, and stable multi-Profile lock ordering. Direct SQL
outside reviewed application/maintenance services remains an operational
privilege and must be audited; a simple row constraint cannot enforce this
cross-row/cross-table invariant.

## 7. Profile Invitation contract

Unless a bullet is explicitly labeled **[APPROVED]** or **[REQUIREMENT]**, the
record, role ceiling, state, token, identity-binding, delivery, API, and error
details in this section are **[PROPOSED]** and require owner approval.

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
- **[PROPOSED]** A combined UI may orchestrate these two explicit operations
  later, but it must not hide or bypass the Profile-consent transition.

### 7.2 Authority and requested role

- **[REQUIREMENT]** The outsource assigns invitation sending to Owner/Admin.
  It described a Workspace invitation; the later approved consent boundary
  requires the invitation to join Profile first.
- **[PROPOSED]** Active Profile Owner/Admin in the exact Profile may
  create/list/revoke that Profile invitation; Profile Member and every
  Workspace-only role are denied.
- **[PROPOSED]** Owner may invite `MEMBER` or `ADMIN`.
- **[PROPOSED]** Admin may invite `MEMBER` only. Whether Admin may grant Admin
  remains **[OPEN]**.
- **[PROPOSED]** Owner may list/revoke/reinvite every permitted requested role;
  Admin may manage only `MEMBER` invitations. Admin cannot revoke or rotate an
  Owner-created `ADMIN` invitation. The exact management ceiling is **[OPEN]**.
- **[PROPOSED]** Invitation cannot grant `OWNER`. Ownership is a separate
  Owner-only, locked transition after accepted membership. This avoids an
  invitation bypass around last-owner/Owner governance.
- **[PROPOSED]** Only the bound recipient may accept or decline.

### 7.3 Proposed future record

This is schema design only; no model or migration exists:

| Field/constraint | Proposed contract |
|---|---|
| `profile` | Required tenant FK |
| `recipient_email_normalized` | Required canonical invitation identity snapshot |
| `recipient_user` | Nullable binding when resolution is unambiguous |
| `requested_role` | Approved Profile role ceiling only |
| `invited_by` | Actor snapshot/FK subject to retention policy |
| `status` | `PENDING`, `ACCEPTED`, `DECLINED` (recipient reject), `EXPIRED`, `REVOKED` |
| `token_hash` | Unique digest only; raw token is never persisted |
| `expires_at` | Required; exact default/max TTL is open |
| terminal metadata | Terminal timestamp, actor/reason where applicable, optional superseded link |
| uniqueness | At most one `PENDING` invitation per Profile/normalized email and, when bound, per Profile/recipient User; stale pending is terminalized under lock before replacement |
| indexes | Profile/status/expiry and safe recipient-inbox lookup |

**[PROPOSED]** Only `PENDING` may transition. Terminal states are immutable. A
reinvite or resend revokes/replaces the old pending credential and creates a
new token; it never revives a terminal row or extends/reuses a token silently.

### 7.4 Recipient and account binding

- **[REQUIREMENT]** Input identity is email; username is never invitation
  identity.
- **[PROPOSED]** Validate as an email, trim surrounding whitespace, then apply
  Unicode NFC plus whole-value `casefold()` (matching the current registration
  direction) once and persist that canonical value. Enforce pending uniqueness
  on the stored normalized field, not on caller input. Because current User
  email has no race-proof case-insensitive DB constraint, an existing-account
  lookup must fail closed unless it resolves exactly one User; identity
  hardening may require HT-AUTH-P1-02 before launch.
- **[PROPOSED / OPEN]** Acceptance requires an active authenticated Django
  session, CSRF, a valid raw token, an active account, and an unambiguous
  account email matching the invitation snapshot. The owner must decide
  whether mailbox-token possession plus session match is sufficient for an
  existing account or whether a separately persisted verified-email state is
  a prerequisite. Token possession alone never grants tenant read access.
- If the target is already an active Profile member, invitation creation
  returns a deterministic `already_member` conflict and never changes their
  role. Role change and Workspace add are separate flows.
- An inactive historical membership must still go through invitation. Whether
  to reactivate a prior membership row or create a new active row is **[OPEN]**.
- **[PROPOSED]** Rejoining a Profile must not silently restore historical
  Workspace access. The current WorkspaceMember schema would make old rows
  effective again once Profile membership is active, so implementation needs
  an owner-approved deactivate/archive/remove strategy before rejoin ships.
- Invitations to unregistered email addresses are **[OPEN]** because current
  authentication has no verified-email invitation onboarding flow. Ambiguous
  case-insensitive account matches must fail closed.

### 7.5 Token and delivery security

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
- Endpoint throttling is required, but exact limits and distributed cache
  deployment are **[OPEN]**. Legacy 14-day/legacy rate limits are evidence,
  not accepted defaults.

### 7.6 State and concurrency contract

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
- Accept activates at most one membership using the owner-approved
  create-versus-reactivate strategy, marks the invite accepted, and writes both
  invitation and membership audit events atomically.
- Concurrent accept/accept, accept/revoke, and accept/reinvite produce exactly
  one terminal winner. Reconcile any `IntegrityError` by rereading; never
  overwrite an existing membership role.
- A retry by the same recipient after successful acceptance may return the
  same logical result without another write. Other replays get the generic
  invalid response.
- Whether acceptance revalidates the inviter's current authority, or pending
  invitations survive inviter demotion/removal, is **[OPEN]**. Revalidation is
  the proposed fail-closed policy.

### 7.7 Audit events

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

## 8. Planned API surface — not implemented

All routes below are proposals under global SessionAuthentication and
`IsAuthenticated`; every mutation requires CSRF. No route receives `AllowAny`
without a separate security review.

### 8.1 Profile, Workspace, and membership

```text
GET/POST   /api/v1/profiles/
GET/PATCH  /api/v1/profiles/{profile_id}/
GET        /api/v1/profiles/{profile_id}/members/
PATCH      /api/v1/profiles/{profile_id}/members/{membership_id}/

GET/POST   /api/v1/profiles/{profile_id}/workspaces/
GET/PATCH  /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/
GET/POST   /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/members/
PATCH/DELETE
            /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/members/{membership_id}/
```

Delete/restore endpoints remain blocked until soft-delete and retention
authority are approved. The final method set must be narrowed to the approved
capability matrix.

Proposed validation contract:

- Profile creation accepts only approved mutable fields such as `{name}`;
  creator/initial Owner and timestamps are server-set through the bootstrap
  service. Self-service eligibility remains open.
- Workspace creation accepts approved mutable metadata only. `profile`,
  transitional `owner`, and timestamps are server-set from the authorized
  parent/context; body values cannot reparent or impersonate ownership.
- Direct Workspace add accepts `{target_profile_membership_id, role}`, not a
  global User ID. The target membership must be active in the nested Profile;
  the role must be owner-approved and effective. Current/deprecated
  `WorkspaceMember.OWNER` and unapproved Viewer assignment fail closed.
- Profile/Workspace membership mutations accept only the exact approved
  role/active operation. Actor, tenant, target User, audit fields, and owner
  status are never writable implicitly. Profile leave and Workspace removal/
  `DELETE` stay disabled until lifecycle/history behavior is approved.
- Responses expose only fields approved for the caller's effective role and
  never treat nested IDs or serializer uniqueness checks as authorization.

### 8.2 Profile invitations

```text
GET/POST   /api/v1/profiles/{profile_id}/invitations/
POST       /api/v1/profiles/{profile_id}/invitations/{invitation_id}/revoke/
POST       /api/v1/profiles/{profile_id}/invitations/{invitation_id}/reinvite/
GET        /api/v1/profile-invitations/me/
POST       /api/v1/profile-invitations/accept/   {"token": "..."}
POST       /api/v1/profile-invitations/decline/  {"token": "..."}
```

Management list/detail never returns token or hash. Avoid a public invitation
preview. If future UX requires one, it needs explicit owner/security approval,
uniform minimal responses, no-store/no-referrer behavior, and throttling.

Compact proposed contract (exact envelope/status approval remains part of the
error-contract review):

| Operation | Actor/input | Validation and response boundary |
|---|---|---|
| List Profile invitations | Profile Owner; Admin only within approved role ceiling | Tenant-scoped sanitized records; no token/hash, unmasked email outside approved management scope, or cross-Profile count |
| Create | Authorized manager; `{recipient_email, requested_role}` | Server sets Profile/inviter/status/expiry/hash; canonicalize email; enforce role ceiling, existing-member and pending-duplicate rules; proposed `201` sanitized record; conflict uses stable `409` without leaking accounts publicly |
| Revoke | Authorized manager; no client-supplied status/actor | Lock/recheck pending record and management ceiling; proposed `200` sanitized terminal state; outside scope `404`, visible forbidden action `403` |
| Reinvite | Authorized manager; optional approved delivery channel only | Terminalize/replace pending credential atomically; never return raw token/hash; proposed `201` replacement summary; delivery runs after commit |
| Recipient inbox | Active authenticated User; no tenant supplied | Only safely bound/matching invitations; sanitized result grants no Profile/Workspace read before acceptance |
| Accept/decline | Matching active authenticated User; `{token}`; CSRF | Server derives invitation/Profile/recipient; ignores all role/tenant fields; same-recipient accepted replay may return idempotent `200`; invalid/unavailable cases use one proposed generic `400` shape; accept returns only approved membership/navigation summary |

Request serializers reject/ignore server-owned fields including Profile,
recipient User, inviter, status, digest, expiry overrides, terminal metadata,
membership User, and audit metadata. The unregistered-recipient, email
verification, TTL, throttle, and exact error-envelope choices remain open.

### 8.3 Deliberately deferred APIs

- Task endpoints wait for approved visibility, state, reviewer, and payroll
  contracts after the tenant/RBAC foundation.
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
- A WorkspaceMember row with deprecated, unknown, or not-yet-enabled role is
  denied until explicitly reconciled/approved; mere row existence is not access.
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
- Workspace Admin cannot manage Profile membership/invitations, Profile-wide
  Client data, or Finance.
- Viewer is denied every mutation and all unapproved export/download paths.
- Transitional `Workspace.owner` and `WorkspaceMember.OWNER` do not grant
  Profile authority.
- Client/Guest credentials cannot call internal endpoints.
- Task creator, assignee, commenter, uploader, and reviewer are authorized in
  the Task Workspace at write time.

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
- Invitation acceptance never creates Workspace membership automatically.
- Direct Workspace add still rejects missing/inactive/cross-Profile membership.
- Raw token/hash is absent from serialized responses, AuditLog, and captured
  application/access logs.
- CSRF, throttle, no-store/no-referrer, empty migration, populated migration,
  and PostgreSQL constraint behavior are tested.

### 9.5 Bypass and regression

- Last-owner and role-revocation races preserve a usable Owner.
- Sole-Owner User deactivation is denied; multi-Profile deactivation locks in
  stable order; a session established before `is_active=False` cannot continue
  using private tenant endpoints.
- Duplicate direct-add cannot create duplicate Workspace membership.
- Audit write rolls back with the state mutation.
- Constraint conflicts become domain errors, never unhandled `500` responses.
- Reviewed import/job/Admin paths cannot bypass scope or audit.
- Every endpoint remains a DRF view; no accidental `AllowAny`; unsafe session
  mutations enforce CSRF.
- All 19 Authentication and 10 API Foundation regressions continue to pass.

## 10. Dependency-ordered implementation plan

1. Owner approves or edits this capability matrix, role vocabulary, tenant
   error/bypass policy, and invitation decisions.
2. Repeat target-environment read-only inventory, apply backup policy, then
   safely apply existing `workspace.0002` before exercising Workspace APIs in
   development. Never synthesize mappings for unknown legacy rows.
3. Implement request access context, tenant-scoped selectors, capability
   primitives, and stable domain exception mapping without opening broad CRUD.
4. Refactor current membership services to authorize/scoped-resolve before
   target lookup; add IDOR, service, and concurrency tests.
5. Add minimal Profile/Workspace read endpoints, then approved membership and
   Workspace lifecycle mutations under `/api/v1/`.
6. After invitation decisions are accepted, add only a new additive migration
   (expected `workspace/0003+`), migration rehearsals, locked service, hashed
   token/delivery flow, audit events, and invitation API tests.
7. Design/approve Task visibility and workflow; only then open Task APIs.
8. Add Client/Project/Finance/Audit tenant schema and APIs in their own
   reviewed migrations/tasks.
9. Add Client Portal and Guest Review principals only after their independent
   capability/expiry contracts are approved.

### 10.1 Acceptance gates for future implementation slices

| Slice | Acceptance criteria before the slice can close | Minimum verification |
|---|---|---|
| Access context and selectors | Active User + active ProfileMembership resolved from URL parent; Profile Member Workspace scope is explicit; Profile-null rows and cross-Profile rows are absent from every list/detail/count/search path | Unit tests for context predicates; PostgreSQL API/query tests for nested URL tampering, real-vs-random UUID, pagination/filter leakage, inactive memberships, and Profile-null rows |
| Capability policy | Only owner-approved matrix actions are encoded; inheritance is same-Profile only; no enum, staff flag, selected Profile, or transitional owner FK grants an unstated capability | Parameterized role/action matrix tests; every deny case tested; Client/Guest rejected from internal endpoints |
| Membership services | Parent scope established before target lookup; mutation revalidates under lock; last-owner, same-tenant, duplicate, and audit invariants are atomic; no supported direct/bulk bypass | Service tests for cross-tenant IDs and uniform domain errors; concurrent demote/remove/direct-add tests; rollback/audit tests |
| Minimal Profile/Workspace API | Nested/scoped queryset used for every object; CSRF on mutation; no new `AllowAny`; response fields follow approved role visibility; soft/hard delete remains absent unless separately approved | API permission/IDOR/CSRF tests plus all Authentication/API Foundation regressions |
| Invitation schema/migration | Additive migration only; token digest/status/role constraints and pending uniqueness match approved policy; existing rows are preserved; no plaintext token field | Migration consistency plus empty/populated PostgreSQL forward tests and constraint tests |
| Invitation service | Authorized sender/recipient binding; expiry/replay/reinvite semantics; exactly one active membership and one terminal winner; Workspace membership is never implicit; audit is atomic | Token secrecy/log capture, duplicate/case variants, wrong-user/inactive/expired/revoked/replay, concurrent accept/accept and accept/revoke tests |
| Invitation API/delivery | Authenticated session and CSRF; non-enumerating failures; scoped manager lists; no token/hash serialization; send only after commit; approved throttle/cache contract | API contract, CSRF, throttle, cache/header, delivery-failure, and cross-Profile negative tests |
| Business-domain onboarding | Domain has a canonical non-null/reconciled tenant path and same-tenant relationship service before route exposure | Domain migration rehearsal, cross-tenant relationship tests, API matrix tests, and full PostgreSQL regression |

No slice may claim a pass from this design document. These gates become
executable acceptance criteria only after the corresponding implementation is
authorized and the listed tests are actually run.

## 11. Owner decisions required before implementation

Every `R/P` and `P` cell in the capability matrix remains pending. The grouped
questions below are a review checklist, not implicit approval for any proposal
that is not named word-for-word.

1. Keep Workspace Admin as narrow Workspace content manager, or use only
   inherited Profile Owner/Admin management?
2. Deprecate `WorkspaceMember.OWNER` and prohibit new API assignments?
3. Retain Viewer with the limited scope above, or disable it? If retained,
   exactly which comments, Deliverables, downloads, exports, and member fields
   are visible?
4. May Profile Admin invite/grant/deactivate another Admin, or only Members?
   Which pending invitations may Admin list/revoke/reinvite, including an
   Owner-created `ADMIN` invitation? Proposed default: Owner-only Admin
   governance and Admin management of `MEMBER` invitations only.
5. Who may soft-delete/restore Workspace and Profile? Proposed default:
   Profile Owner only; hard delete remains deferred.
6. May Workspace Admin change Workspace membership? Proposed first phase: no;
   Profile Owner/Admin only.
7. Does Workspace Member read all Workspace Tasks, only assigned Tasks, or
   assigned plus a published claimable pool?
8. Must inherited Profile Owner/Admin also be explicit Workspace members to be
   assigned/upload as contributors? Proposed: yes for operational attribution.
9. For an existing account, is mailbox-token possession plus a matching active
   session sufficient, or is persisted verified-email state required? Are
   unregistered recipients supported? Approve normalization, registration/
   linking, ambiguous account, and email-change behavior.
10. Invitation default/max TTL, resend/reinvite semantics, throttle limits,
    and delivery channels.
11. On voluntary Profile/Workspace leave and later Profile rejoin, what is
    deactivated/retained/audited? Reactivate an old membership or create a new
    row, and how are historical WorkspaceMember rows prevented from silently
    restoring access?
12. Do pending invitations survive inviter demotion/deactivation/removal, or
    must acceptance revalidate current issuer authority? Proposed: revalidate.
13. Is a Profile-only invitation sufficient, or should a later combined UI
    collect a requested Workspace role while preserving two distinct state
    transitions?
14. Approve `404`/`403`/generic `400` semantics, `409` domain conflict shape,
    whether any API platform-operator bypass exists, and the User lifecycle/
    Admin policy for `is_active`, deletion, sole/multi-Profile Owners, and
    session revocation.
15. Retention/anonymization and hard-delete authority for terminal invitations
    and recipient PII.
16. Is Profile creation self-service for every active authenticated User, or
    staff-mediated/limited? Approve eligibility, quotas/abuse controls, and the
    creation-only initial-Owner bootstrap exception to invitation consent.

Detailed Task/Review transitions, Finance numbering, public-link capabilities,
and global retention policy remain separate roadmap decisions and are not
implicitly approved by this design.

