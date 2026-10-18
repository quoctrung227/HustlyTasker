# HUSTLYTASKER API DOCUMENTATION

Last updated: 2026-10-18

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

## Profile and Workspace read API

Base path: `/api/v1/`

This is the first tenant-scoped business API slice. Every endpoint in this
section uses Django `SessionAuthentication`, requires a current active User,
and has no `AllowAny` override. The selected Profile or any identifier supplied
by the client is never authorization evidence; access is resolved from current
database membership through the tenant access foundation.

| Method | Path | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/profiles/` | Active authenticated User | List Profiles in which the User has an active membership. |
| `GET` | `/api/v1/profiles/{profile_id}/` | Active membership in the Profile | Return minimal Profile metadata. |
| `GET` | `/api/v1/profiles/{profile_id}/workspaces/` | Active Profile access plus the Workspace rules below | List only Workspaces visible to the caller inside the nested Profile. |
| `GET` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/` | Effective read access to that Workspace in that Profile | Return minimal Workspace metadata. |

All four routes also support `HEAD` and `OPTIONS` for authorized callers.
`POST`, `PUT`, `PATCH`, and `DELETE` are not implemented. DRF performs
authentication, permission, and session-CSRF checks before method dispatch, so
anonymous or CSRF-invalid unsafe requests may return `403 Forbidden`; an active
authorized session with a valid CSRF token reaches method dispatch and returns
`405 Method Not Allowed`. No branch writes data or creates audit events.

Profile responses contain exactly:

- `id`
- `name`
- `created_at`
- `updated_at`

Workspace responses contain exactly:

- `id`
- `profile_id`
- `name`
- `description`
- `created_at`
- `updated_at`

IDs are canonical UUID strings and timestamps use DRF's ISO-8601 rendering.
Transitional `Workspace.owner`, memberships, roles, emails, and other PII are
not serialized.

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
`page_size` query parameter. Results have fixed stable ordering by
`created_at`, then `id`; this slice exposes no client-controlled search,
filter, or ordering.

Workspace visibility is fail-closed:

- Profile Owner and Profile Admin can read every Profile-mapped Workspace in
  their own Profile.
- An ordinary Profile Member can read only a Workspace with an effective
  explicit `ADMIN`, `MEMBER` (Editor), or `VIEWER` membership.
- Legacy `WorkspaceMember.OWNER`, transitional `Workspace.owner`, staff or
  superuser flags, and a selected Profile do not grant tenant API access.
- An inactive User, inactive Profile membership, revoked Workspace membership,
  cross-Profile relationship, or `Workspace.profile=NULL` cannot be used for
  access.

Anonymous access returns `403 Forbidden`. A malformed, unknown, cross-tenant,
wrong-parent, or otherwise out-of-scope Profile/Workspace identifier returns
the same JSON `404` response:

```json
{"detail": "Not found."}
```

An accessible Profile with no visible Workspaces returns a successful empty
page instead of disclosing hidden rows. Responses are marked non-cacheable.

The `/api/v1/` prefix currently applies to tenant business endpoints only;
the established `/api/auth/` and `/api/health/` paths remain unchanged. A
project-wide error-envelope convention beyond this non-enumerating read
contract is deferred to later API slices.

Operational limitation: the source migration was exercised successfully on
disposable PostgreSQL test databases that Django then destroyed, but
`workspace.0002_profile_workspace_foundation` is intentionally still unapplied
on the development database. A separately approved development sequence is:
repeat read-only inventory, take the required backup, apply only the existing
`0002`, then smoke these four routes.

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
  of this foundation. The separately documented `/api/v1/` tenant slice adds
  read-only Profile/Workspace authorization; Profile/Workspace writes,
  membership management, and Invitation APIs remain unimplemented.
