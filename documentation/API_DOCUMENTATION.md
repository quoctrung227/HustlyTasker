# HUSTLYTASKER API DOCUMENTATION

Last updated: 2026-10-20

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

HT-WORK-P2-02 schema-dependent implementation was verified on 2026-10-19. The
Workspace suite passed 140/140 tests in 79.278s and the full PostgreSQL suite,
including Authentication/API Foundation regressions, passed 169/169 in
82.920s. `pip check`, Django system checks, and
`makemigrations --check --dry-run` also passed. Migration rehearsal applied
`workspace.0003_workspace_lifecycle_and_period` only to an isolated Django test
database and preserved legacy Workspace/WorkspaceMember plus related
Task/Deliverable/Review data without guessing a period.

Deployment state is deliberately separate from source state: these contracts
are **implemented in source and tested in isolated PostgreSQL**, but migration
`workspace.0003` is **not applied to development** and production was not
touched. Development remains at 27 migration rows with `workspace.0002`
applied, 3 Users, and zero business rows. The source API must not be started for
development business traffic until the Owner separately approves and the
controlled development migration process applies and verifies `0003`.

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
  frontend integration remain unimplemented; the schema-dependent routes are
  not deployed to development until `workspace.0003` receives rollout approval.
