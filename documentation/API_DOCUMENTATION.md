# HUSTLYTASKER API DOCUMENTATION

Last updated: 2026-10-21

## API boundary and public allowlist

Every endpoint under `/api/` is implemented as a Django REST Framework view.
The global default is `IsAuthenticated`; a public endpoint must declare
`AllowAny` explicitly and must be added only after security review. The current
public allowlist is:

- `/api/health/`
- `/api/auth/csrf/`
- `/api/auth/register/`
- `/api/auth/login/`

Public authentication endpoints retain the CSRF and throttle behavior
documented below. The health endpoint is the deliberate exception described in
the next section. `/admin/` is outside both `/api/` and DRF; it continues to use
Django Admin authentication and authorization.

## Liveness

Canonical path: `/api/health/`

This endpoint is a public, JSON-only process-liveness check. It does not run
authentication (including session authentication), require CSRF, apply DRF
throttling, or query the database. Responses include `Cache-Control: no-store`
and must not expose deployment or dependency details. Clients should send
`Accept: application/json` or `Accept: */*`; an incompatible media type such
as `text/html` receives `406 Not Acceptable`.

| Method | Status | Contract |
|---|---|---|
| `GET` | `200 OK` | Return `{"status":"ok"}`. |
| `HEAD` | `200 OK` | Return the same headers as `GET` with an empty body. |
| `OPTIONS` | `200 OK` | Return the standard DRF method metadata; allowed methods are `GET`, `HEAD`, and `OPTIONS`. |
| `POST`, `PUT`, `PATCH`, `DELETE`, `TRACE` | `405 Method Not Allowed` | Do not perform any action. |

This is intentionally not a database-readiness check: a database outage does
not change its result while the Django request stack remains healthy. A future
readiness endpoint must use a separate path and contract. The legacy
`/api/test/` route has been removed and returns `404 Not Found`.

## Profile and Workspace API

Base path: `/api/v1/`

This is the tenant-scoped Profile/Workspace API foundation. Every endpoint in
this section uses Django `SessionAuthentication`, requires a current active
User, and has no `AllowAny` override. A selected Profile or client-supplied ID
is never authorization evidence; every object is resolved from current tenant
membership and the nested parent path.

| Method | Path | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/profiles/` | Active authenticated User | List Profiles in which the User has an active membership, including an archived Profile that remains in the caller's scope. |
| `GET` | `/api/v1/profiles/{profile_id}/` | Active membership in the Profile | Return minimal Profile metadata. |
| `POST` | `/api/v1/profiles/{profile_id}/archive/` | Profile Owner | Archive the Profile; an empty request body is required. |
| `POST` | `/api/v1/profiles/{profile_id}/restore/` | Profile Owner | Restore the Profile; an empty request body is required. |
| `GET` | `/api/v1/profiles/{profile_id}/workspaces/` | Active Profile access plus the Workspace rules below | List only Workspaces visible to the caller inside the nested Profile, including archived rows. |
| `POST` | `/api/v1/profiles/{profile_id}/workspaces/` | Profile Owner or Profile Admin; Profile must be active | Create one Workspace for a canonical monthly period. |
| `GET` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/` | Effective read access to that Workspace in that Profile | Return minimal Workspace metadata, including lifecycle state. |
| `PATCH` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/` | Profile Owner/Admin or that Workspace's Admin; Profile and Workspace must be active | Update `name` and/or `description`. |
| `POST` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/archive/` | Profile Owner or Profile Admin; Profile must be active | Archive the Workspace. |
| `POST` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/restore/` | Profile Owner or Profile Admin; Profile must be active | Restore the Workspace. |
| `GET` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/members/` | Profile Owner/Admin or that Workspace's Admin | List effective active Workspace assignments without User PII; this remains readable for an archived Workspace. |
| `POST` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/members/` | Profile Owner/Admin or that Workspace's Admin; Profile and Workspace must be active | Direct-add or reactivate an active same-Profile member within the caller's role ceiling. |
| `PATCH` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/members/{membership_id}/` | Profile Owner/Admin or that Workspace's Admin; Profile and Workspace must be active | Change an active Workspace assignment within the caller's role ceiling. |
| `DELETE` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/members/{membership_id}/` | Profile Owner/Admin or that Workspace's Admin; Profile and Workspace must be active | Soft-revoke an active assignment while retaining its row and history. |

Read/list routes support their normal DRF `HEAD`/`OPTIONS` behavior. Action
routes accept `POST` and `OPTIONS`; member detail accepts `PATCH`, `DELETE`, and
`OPTIONS`. Every unsafe method requires a valid session CSRF token. Hard delete
for Profile and Workspace and all `PUT` methods remain disabled with `405
Method Not Allowed`.

### Lifecycle contract

`ACTIVE` and `ARCHIVED` are the only Profile and Workspace states. Profile
archive/restore is Owner-only; a Profile Admin does not receive this authority.
Workspace archive/restore is available to Profile Owner/Admin, not to a
Workspace Admin. Repeating an action already reflected in state is an
idempotent `200 OK` and writes no duplicate audit event.

Archived Profile and Workspace rows remain tenant-scoped and readable by
callers who still have effective read access. An archived Profile blocks every
supported child write except the Owner restore action. An archived Workspace
blocks metadata and roster mutations but remains restorable by a Profile
Owner/Admin while its Profile is active. Lifecycle transitions are locked,
atomic, and write `profile.archived`, `profile.restored`,
`workspace.archived`, or `workspace.restored` in the same transaction.

### Workspace write contracts

Workspace creation accepts exactly:

```json
{
  "name": "October production",
  "description": "Optional description",
  "period": "2026-10-01"
}
```

`name` and `period` are required; `description` is optional and may be null.
`period` is the first day of the represented month and is immutable. At most
one Workspace may exist for a given non-null `(Profile, period)` pair, and an
archived Workspace continues to reserve that period. A missing/noncanonical
period returns `400`; a duplicate period returns `409 Conflict`, including
under concurrent creation.

`PATCH` accepts only `name` and `description`; an empty or unchanged patch is a
no-op and writes no audit event. Unknown or server-owned fields such as `id`,
`profile`, `profile_id`, `owner`, `period`, `status`, timestamps, members, or
roles are rejected with `400 Bad Request`. The server derives the Profile from
the nested URL and keeps the transitional owner field server-controlled, so the
API cannot re-parent a Workspace or impersonate another creator. Successful
create and update return `201 Created` and `200 OK`, respectively.

Workspace create/update run in atomic services, re-resolve authority under
row locks, and write `workspace.created` or `workspace.updated` AuditLog events
in the same transaction. Profile Owner/Admin can create and update Workspaces
in their Profile. A Workspace Admin can update only its assigned Workspace's
`name`/`description`. Workspace Editor (`MEMBER`), Viewer, an unassigned
Profile Member, and legacy Workspace `OWNER` receive no metadata-write
capability.

### Workspace membership contracts

Direct add accepts exactly:

```json
{
  "target_profile_membership_id": "00000000-0000-0000-0000-000000000000",
  "role": "MEMBER"
}
```

The target is an active `ProfileMembership` in the URL Profile, not a global
User identifier. Profile Owner/Admin may assign `ADMIN`, `MEMBER` (Editor), or
`VIEWER`; Workspace Admin may assign or change only `MEMBER` and `VIEWER` and
cannot alter an existing Admin. No supported caller may assign legacy
Workspace `OWNER`. A duplicate assignment returns `409 Conflict`; invalid,
inactive, or cross-Profile target membership input returns a generic validation
`400` without exposing an account. A new assignment returns `201 Created`.

If the `(workspace, user)` row exists but is inactive, direct-add reactivates
that same row with the requested permitted role and returns `200 OK`; it never
creates duplicate history. If the row is already active, the result is `409
Conflict`. Reactivation requires an active User and active ProfileMembership in
the same Profile and writes `workspace.membership.reactivated` atomically.

Role update accepts exactly one `role` field and returns `200 OK`. List and
mutation results contain exactly:

- `id`
- `profile_membership_id`
- `role`
- `is_active`
- `joined_at`
- `updated_at`

They intentionally omit global User ID, email, username, and other PII. Member
list results use the standard bounded pagination envelope and stable
`joined_at`, then `id`, ordering. Direct add and role update use locked atomic
services and write `workspace.membership.created` or
`workspace.membership.updated` AuditLog events in the same transaction.
`DELETE` sets `is_active=false`, immediately removes effective access and
roster visibility, retains the row, returns `204 No Content`, and writes
`workspace.membership.revoked` atomically. Profile Owner/Admin can manage
`ADMIN`, `MEMBER`, and `VIEWER`; Workspace Admin remains limited to `MEMBER`
and `VIEWER`, including concurrent reactivation attempts.

Profile responses contain exactly:

- `id`
- `name`
- `status`
- `created_at`
- `updated_at`

Workspace responses contain exactly:

- `id`
- `profile_id`
- `name`
- `description`
- `period`
- `status`
- `created_at`
- `updated_at`

IDs are canonical UUID strings and timestamps use DRF's ISO-8601 rendering.
Transitional `Workspace.owner`, User identity/PII, and unrelated membership
data are not serialized. A pre-`0003` Workspace preserved for explicit legacy
mapping may read with `period: null`; API-created Workspaces always have a
non-null canonical period, and `PATCH` cannot assign or change it.

List endpoints use the standard DRF page-number envelope:

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

The default `page_size` is 20 and the client may request at most 100 with the
`page_size` query parameter. Profile/Workspace results have fixed stable
ordering by `created_at`, then `id`; member results use `joined_at`, then `id`.
This slice exposes no client-controlled search, filter, or ordering.

Workspace visibility is fail-closed:

- Profile Owner and Profile Admin can read every Profile-mapped Workspace in
  their own Profile.
- An ordinary Profile Member can read only a Workspace with an effective
  explicit `ADMIN`, `MEMBER` (Editor), or `VIEWER` membership.
- Legacy `WorkspaceMember.OWNER`, transitional `Workspace.owner`, staff or
  superuser flags, and a selected Profile do not grant tenant API access.
- An inactive User, inactive Profile membership, missing effective Workspace
  assignment, cross-Profile relationship, or `Workspace.profile=NULL` cannot
  be used for access.

Anonymous access returns `403 Forbidden`. A malformed, unknown, cross-tenant,
wrong-parent, or otherwise out-of-scope Profile/Workspace identifier returns
the same JSON `404` response:

```json
{"detail": "Not found."}
```

An accessible Profile with no visible Workspaces returns a successful empty
page instead of disclosing hidden rows. Responses are marked non-cacheable.

For write routes, syntactically or semantically invalid in-scope input is
`400`; an authenticated caller who can resolve the object but lacks the action
capability receives `403`; unknown, wrong-parent, and out-of-scope object IDs
remain the same generic `404`; and an active duplicate Workspace assignment or
duplicate Profile/month is `409`.

The `/api/v1/` prefix currently applies to tenant business endpoints only;
the established `/api/auth/` and `/api/health/` paths remain unchanged. A
project-wide error-envelope convention beyond this non-enumerating read
contract is deferred to later API slices.

Operational rollout evidence (HT-DB-P1-05, 2026-10-19): after target inventory,
verified backup and isolated restore rehearsal, the existing additive
`workspace.0002_profile_workspace_foundation` migration was applied to the
approved development database. Direct development smoke confirmed health
`200`, anonymous denial (`403`) on all four tenant routes, CSRF bootstrap and
login rejection behavior, with no `500` and no new session or business row.
Because development contains no Profile/Workspace fixture and no approved
account credential was changed or requested, successful SessionAuthentication,
tenant detail, cross-tenant and IDOR cases were verified in Django's isolated
PostgreSQL test database. This is environment-specific rollout evidence and
does not change the API contract or authorize another environment.

HT-WORK-P2-02 schema-dependent implementation was verified on 2026-10-19. Its
isolated migration rehearsal preserved legacy Workspace/WorkspaceMember plus
related Task/Deliverable/Review data without guessing a period.

Operational rollout evidence (HT-DB-P1-06, 2026-10-20): after exact development
target identification, fresh verified backup, full restore rehearsal and plan
review, `workspace.0003_workspace_lifecycle_and_period` was applied to the
approved development database. Post-check reports 28 migration rows, valid
columns/constraints/indexes, 3 active Users, 2 existing sessions, and zero
checked business rows. Production and every other persistent environment were
untouched.

**DEV SMOKE PASSED:** direct development request-stack checks used no business
fixture and changed no row or session. Health returned `200`; CSRF bootstrap
returned `200`; login without CSRF returned `403`; invalid login with a valid
CSRF token returned `400`; anonymous `/api/auth/me/` and logout returned `403`;
and every current Profile/Workspace/membership read or mutation route returned
`403`, with no `500`.

**ISOLATED INTEGRATION TEST PASSED:** successful SessionAuthentication,
authenticated role/capability behavior, tenant isolation, wrong-parent/IDOR,
archive/restore, membership revoke/reactivate, concurrency, and migration
preservation were exercised on Django-created PostgreSQL test databases rather
than persistent development data. Current results are lifecycle/schema 17/17,
Workspace API/service/migration 140/140, Authentication/API Foundation 29/29,
and full PostgreSQL 169/169. The test databases were destroyed after each run.
These operational results do not change the API contract or authorize another
environment.

**NOT TESTED ON PERSISTENT DEVELOPMENT:** successful authenticated session and
tenant operations, role/IDOR success paths, archive/restore, or member
revoke/reactivate. Development has no business fixtures and no account
credential was requested or changed; the isolated results above are the
evidence for those scenarios.

## Task and internal approval workflow API

Source status: `HT-TASK-P2-03 IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT
MIGRATION APPROVAL`

Base nested path:
`/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/`

All routes use the existing Django SessionAuthentication/global
`IsAuthenticated` policy and require an active, tenant-scoped Workspace
context. None uses `AllowAny`. Unsafe requests require a valid session CSRF
token. Responses are non-cacheable, relationship IDs are derived from the
nested authorized path, and no request body may select or move a Task to a
different Profile/Workspace.

| Method | Path suffix | Access | Purpose |
|---|---|---|---|
| `GET` | `(collection)` | Any caller with effective read access to the Workspace | Paginated Task list. |
| `POST` | `(collection)` | Profile Owner/Admin or assigned Workspace Admin | Create a `PENDING` Task. |
| `GET` | `{task_id}/` | Effective Workspace read access | Return one scoped Task. |
| `PATCH` | `{task_id}/` | Profile Owner/Admin or assigned Workspace Admin | Update Task metadata, never status/tenant. |
| `POST` | `{task_id}/assign/` | Profile Owner/Admin or assigned Workspace Admin | Assign/reassign one eligible Editor and enter `ASSIGNED`. |
| `POST` | `{task_id}/start/` | Current active assignee with Editor capability | Move `ASSIGNED -> WORKING`; empty body. |
| `GET` | `{task_id}/deliverables/` | Effective Workspace read access | List revision history for the scoped Task. |
| `POST` | `{task_id}/deliverables/` | Current active assignee with Editor capability | Submit a new URL revision and move `WORKING -> REVIEW`. |
| `POST` | `{task_id}/deliverables/{deliverable_id}/approve/` | Profile Owner/Admin or assigned Workspace Admin, not the submitter | Approve the latest submitted revision and move `REVIEW -> COMPLETED`. |
| `POST` | `{task_id}/deliverables/{deliverable_id}/request-changes/` | Profile Owner/Admin or assigned Workspace Admin, not the submitter | Reject the latest submitted revision and move `REVIEW -> WORKING`. |

Read access follows the effective Workspace rules: same-Profile Owner/Admin can
read every Task in that Profile's mapped Workspace; an ordinary Profile Member
must have an active supported Workspace assignment (`ADMIN`, `MEMBER`, or
`VIEWER`). A Viewer is read-only. Management/review authority is Profile
Owner/Admin or assigned Workspace Admin. Execution authority is deliberately
narrower: an active ordinary Profile `MEMBER` with effective Workspace
`MEMBER` (Editor) role, who must also be the Task's current active assignee.
Manager inheritance does not silently make a manager the worker/submitter.

### Task requests and responses

Create accepts only:

```json
{
  "title": "Produce October report",
  "description": "Optional or null",
  "priority": "MEDIUM",
  "deadline": null
}
```

`title` is required. `description`, `priority`, and `deadline` are optional;
priority defaults to `MEDIUM`. `PATCH` accepts a subset of those four mutable
metadata fields; empty or unchanged input is a no-op with no audit event.
Unknown and server-owned fields—including
`profile_id`, `workspace_id`, `status`, creator, assignment, revisions,
reviewer, IDs, and timestamps—are rejected with `400 Bad Request`.

Task responses contain exactly:

- `id`
- `workspace_id`
- `title`
- `description`
- `status`
- `priority`
- `deadline`
- `active_assignment`
- `created_at`
- `updated_at`

`active_assignment` is null or contains `id`, current
`profile_membership_id`, and `assigned_at`. It never contains global User ID,
email, username, or other PII. If the assignee no longer has a current active
same-Profile membership, historical attribution is retained in the database
but the serialized ProfileMembership identifier becomes null rather than
exposing a stale tenant identifier.

Assign accepts exactly:

```json
{
  "target_profile_membership_id": "00000000-0000-0000-0000-000000000000"
}
```

The target must be an active User with an active ordinary `MEMBER`
ProfileMembership in the URL Profile and effective Workspace `MEMBER` (Editor)
assignment. It is not a global User identifier. Assignment/reassignment is
accepted only while the Task is `PENDING`, `ASSIGNED`, or `WORKING`; exactly one
assignment remains active. Reassigning deactivates the former assignment and
returns the updated Task. Assignment history remains internal and is not a
general roster/PII API.

### Deliverable and internal Review contract

Submit accepts exactly:

```json
{
  "file_url": "https://files.example.invalid/result-v1"
}
```

This foundation stores a URL string; it does not upload, fetch, scan, validate
media contents, or authorize a storage provider. The service allocates a
positive sequential revision while locking the Task. A Task may have multiple
historical Deliverables, but only its latest submitted revision may be decided.

Deliverable responses contain exactly:

- `id`
- `task_id`
- `revision`
- `file_url`
- `status`
- `uploaded_by_profile_membership_id`
- `review`
- `created_at`
- `updated_at`

The nested `review`, when present, contains `id`, `status`, `comment`,
`reviewer_profile_membership_id`, `created_at`, and `updated_at`. Current
ProfileMembership IDs are used for attribution; global User identity and PII
are omitted, and stale membership attribution serializes as null.

Approve accepts optional `comment`; request changes requires a non-blank
`comment`. A reviewer cannot review their own submission. Stale/non-latest,
already-decided, duplicate, or state-incompatible decisions return a workflow
conflict and cannot create a second Review. Request changes marks the
Deliverable `REJECTED` and returns the Task to `WORKING`, allowing the same
current assignee to submit the next revision. Approval marks the Deliverable
`APPROVED` and the Task `COMPLETED` atomically.

This decision is **internal review only**. It is not Client Portal/Guest Review
approval, does not send a Deliverable to a client, and does not create or
calculate Payroll, Payment, Invoice, or compensation data.

### State, errors, and unavailable methods

Supported public transition path:

```text
PENDING -> ASSIGNED -> WORKING -> REVIEW
                                 |-> COMPLETED (internal approval)
                                 `-> WORKING   (request changes -> resubmit)
```

There is no arbitrary status field update. `CANCELLED` remains a constrained
storage value but has no route in this slice. No `PUT` or `DELETE` method is
available for Task or Deliverable; Comments, claim/Marketplace, Client/Guest
review, file-upload/media, Finance/Payroll, and soft-delete APIs are absent.

- invalid or unknown input fields: `400`;
- visible object but missing action capability/self-review: `403`;
- anonymous SessionAuthentication request: `403`;
- malformed, unknown, cross-tenant, wrong-parent, or out-of-scope URL resource:
  generic `404`;
- invalid/stale/repeated workflow state or assignment/review conflict: `409`;
- unsupported method: `405` after normal authentication/CSRF/tenant checks.

Task and Deliverable lists use the existing page-number envelope, default 20
and maximum 100, with stable `created_at`, then `id`, ordering. All mutations
revalidate tenant capability under row locks and write material AuditLog events
in the same transaction; audit failure rolls back the mutation. Audit metadata
does not include file URLs, free-text descriptions, or review comments.

### Migration and rollout boundary

The routes require source migrations `tasks.0002_task_workflow_foundation` and
`reviews.0002_review_workflow_foundation`. They have passed the current 33/33
targeted service/API/migration suite in 7.673s, the 169/169 existing
Authentication/API/Workspace regression in 87.783s, and the final full
PostgreSQL suite 202/202 in 92.343s. Test databases were destroyed; dependency,
Django system and migration-drift checks and independent final code review
passed.

They are **not applied to development or production**. Final read-only
development `showmigrations` confirms Workspace 0001-0003 applied, with Tasks
and Reviews still at 0001. `migrate --plan` succeeds and lists only additive
`tasks.0002` then `reviews.0002`; no migration was applied. Do not direct
development business traffic to this source contract before a separately
approved controlled inventory/backup/plan/apply/smoke task.

## Authentication foundation

Base path: `/api/auth/`

The current authentication contract uses Django server-side sessions and DRF
`SessionAuthentication`. It assumes a same-origin frontend (or a reverse proxy
that presents frontend and API as the same site). CORS is not enabled.

### Browser client flow

1. Call `GET /api/auth/csrf/` while retaining cookies.
2. Send the returned `csrf_token` as the `X-CSRFToken` header on register,
   login, logout, and every later unsafe session-authenticated request.
3. Call register if needed. Registration does not create a session.
4. Call login and retain the returned `sessionid` cookie.
5. Call `GET /api/auth/me/` to resolve the current identity.
6. Call logout with `POST` and a valid CSRF token.

### Endpoints

| Method | Path | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/auth/csrf/` | Public | Set the CSRF cookie and return a masked CSRF token. |
| `POST` | `/api/auth/register/` | Public + CSRF | Create an active user; does not log the user in. |
| `POST` | `/api/auth/login/` | Public + CSRF | Validate email/password and create a server-side session. |
| `POST` | `/api/auth/logout/` | Authenticated + CSRF | Revoke the current session. |
| `GET` | `/api/auth/me/` | Authenticated | Return the current public user identity. |

Registration accepts `email`, `username`, `password`, `password_confirm`, and
optional `first_name`/`last_name`. Login accepts `email` and `password`.

Successful register, login, and me responses use this envelope:

```json
{
  "user": {
    "id": "00000000-0000-0000-0000-000000000000",
    "email": "user@example.com",
    "username": "user",
    "first_name": "",
    "last_name": "",
    "created_at": "2026-10-14T00:00:00Z"
  }
}
```

Logout returns `204 No Content`. Invalid login credentials return the same
neutral `400` response whether the email is unknown, the password is wrong, or
the account is inactive. Anonymous access to session-protected endpoints
returns `403` with DRF `SessionAuthentication`. Throttled requests return `429`.

### Security and current boundaries

- Registration applies Django password validators and stores passwords only
  through `create_user()`/Django password hashing.
- The session cookie is HttpOnly and SameSite `Lax`; its Secure flag follows
  the environment configuration.
- Register and login are explicitly CSRF-protected even before authentication.
- Register and login have scoped DRF rate limits of `5/hour` and `10/minute`
  per client address. `DRF_NUM_PROXIES=0` ignores spoofable forwarding headers
  by default. The in-process cache is only defense-in-depth; production needs
  a shared cache and reviewed trusted-proxy count before the limits can be
  considered distributed enforcement.
- New email addresses are canonicalized. Email and username are checked
  case-insensitively in the application, but race-proof database constraints
  are deferred because they require a reviewed migration/backfill plan.
- Duplicate registration returns field-specific validation errors. This is a
  deliberate foundation-stage UX contract and permits account enumeration;
  revisit it together with activation and public-signup abuse controls.
- OTP/email activation, password reset, logout-all, JWT, and OAuth are not part
  of this foundation. The separately documented `/api/v1/` tenant slice now
  includes the Workspace metadata, lifecycle, and membership operations above.
  General Profile create/update, Invitation, downstream business APIs, and
  frontend integration remain unimplemented. The schema-dependent routes have
  completed the approved development-only `workspace.0003` rollout; deployment
  to production or any other persistent target still requires separate review
  and authorization.
