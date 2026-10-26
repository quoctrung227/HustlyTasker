# HUSTLYTASKER API DOCUMENTATION

Last updated: 2026-10-26

## HT-FE-P3-01 frontend consumer — 2026-10-26

Frontend foundation consumes the existing CSRF/login/logout/me and four scoped
Profile/Workspace read endpoints; no backend route, response or permission
contract changed. Same-origin Vite proxy preserves Host. Browser-managed session
cookies and memory-only CSRF token are used; login rotation, logout/cache/tab
cleanup and anonymous SessionAuthentication403 are handled. A tenant403 checks
current identity quietly without treating every permission denial as logout.
The UI remains read-only for Profile/Workspace. See FRONTEND_GUIDE.md for client,
proxy, routes and runtime contracts. Mock96/96 and real isolated Django/PG/Chrome
integration6/6 PASS are distinct; no persistent-development authenticated or
production-deployment claim follows. HANDOVER.md has exact current evidence.

## HT-DB-P1-11 development verification — 2026-10-26 — COMPLETE / OWNER REVIEW GATE

Approved development rollout applied tasks.0004 then notifications.0002 exactly
once after backup/isolated restore rehearsal. Both source APIs now have their
required development columns; 35 migrations and 44 valid orphan-free FKs verify.
No route, response contract, Authentication, RBAC or Task/Review policy changed.

**DEVELOPMENT SMOKE PASSED:** 67 anonymous requests through the Django handler
in a READ ONLY transaction and 28 serializer-only checks. Health/CSRF bootstrap,
auth CSRF rejection, Profile/Workspace/Task/Comment/Notification anonymous
boundaries and safe method/input checks pass without HTTP 500, login, fixtures,
email or row changes. New-column ORM selects/context joins also pass. Protected
endpoints return 403 before authenticated method/body validation; this does not
claim an authenticated 405/validation success contract was exercised there.

**AUTHENTICATED SUCCESS FLOWS NOT TESTED ON PERSISTENT DEVELOPMENT.** Comment
CRUD/moderation, Notification events/recipients/dedup/read state, current-target
access and authenticated CSRF/mutations are isolated-test obligations. Current
post-rollout Comment 40/40 (13.140s), Notification 34/34 (8.431s) and Task/Review
128/128 (41.694s), security/RBAC 253/253 (224.745s) and full PostgreSQL 415/415
(259.978s) PASS. All five actual launcher/Python exits are 0; Django OK,
dependency/system/model-drift/graph/full-chain and owned cleanup PASS.
**ISOLATED COMMENT/NOTIFICATION TESTS PASSED.** They verify authenticated CRUD,
moderation, recipient/event proof, dedup, rollback, read-state ownership, live
target access, tenant/RBAC/CSRF and concurrency without writing development.

Final development schema/inventory/exact legacy-row comparison and retained
backup size/hash recheck PASS; owned rehearsal/temp copy removed. No disposable
test resources remain and no source/API contract changed. Historical 415/415
below is not reused as post-rollout proof. See HANDOVER.md for current evidence.
No blocker. Project remains PENDING OWNER DECISION; proposed next step is Owner
Project A/B′ scope review. Real email delivery and remote CI remain unverified.
Stop at OWNER REVIEW GATE; no new task starts automatically.

## Historical HT-COM-P2-06 implementation verification — 2026-10-25

The pending-migration status and test results immediately below record the
pre-rollout checkpoint, superseded operationally by HT-DB-P1-11 above. API
contracts following that historical evidence remain current.

Status: **IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**.
Stop at **OWNER REVIEW GATE**. Comment and Notification contracts below
describe the verified source, not an approved development
rollout. New `tasks.0004_task_comments` and
`notifications.0002_notification_context` are **NOT APPLIED TO DEVELOPMENT**.
Read-only inventory remains 33 migrations, tasks.0003/notifications.0001,
3 Users, 2 Sessions and zero checked business/token/Audit rows. Do not run new
write flows against the old persistent schema before a separately approved
rollout. Project remains **PENDING OWNER DECISION**.

Current isolated verification:

| Group | Result |
|---|---|
| Comment/API/service/migrations | **40/40 PASS — 6.919s** |
| Notification/API/events/migrations | **34/34 PASS — 5.401s** |
| Task/Comment/hierarchy/Review regression | **128/128 PASS — 22.637s** |
| Authentication/security/Invitation/Workspace/API regression | **253/253 PASS — 165.756s** |
| Full PostgreSQL suite | **415/415 PASS — 191.226s** |

All five runs pass dependency/system/model-drift/graph/full-chain checks,
native launcher exit 0, Python runner Docker die-event exit 0, Django `OK`
and owned cleanup. These are current runs, not the historical 341/341 evidence.
Final read-only development inventory is unchanged: both new migration records
and their new columns are absent; no Task/Comment/Notification/tenant/token/
Audit rows or test resources were left on development. See HANDOVER.md for
the retained log/exit evidence and exact continuation gate.

### Task and Subtask comments

Subtask is a Task and uses the same routes. Base path:
`/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/comments/`.

| Method/path | Contract |
|---|---|
| `GET` collection | Paginated comments, including redacted deleted tombstones; stable `created_at,id` order. |
| `POST` collection | Strict `{"content":"Feedback text"}`; create as the authenticated author; return `201`. |
| `GET {comment_id}/` | Current scoped comment or generic `404`; deleted comments remain readable as tombstones. |
| `PATCH {comment_id}/` | Author-only content replacement; requires `content`; return `200`. |
| `DELETE {comment_id}/` | Empty body; author or current Task manager soft-deletes; return `204`, idempotent for an already deleted row. |

All routes use SessionAuthentication, active tenant access and no-cache
responses; unsafe methods require CSRF. Existing Task readers may read
comments. Profile Owner/Admin, Workspace Admin and active Editor may create;
Viewer is read-only. The author must retain current commenting capability to
edit/delete. Managers may moderate by deleting but cannot rewrite another
author's text. Staff/superuser flags confer no tenant authority. Archived
Profile/Workspace content retains its existing read policy while mutations
are denied; revoked/inactive memberships grant no access.

Text must be a non-blank string, trimmed, at most 4,000 Unicode characters;
NUL/surrogate input and malformed Unicode field names return `400` without
reflecting unencodable keys. Author, task and lifecycle fields are server-owned
and rejected in request bodies. A known in-scope permission denial is `403`;
malformed/missing/wrong-parent/cross-tenant nested resource resolution uses
generic `404` under the existing permission-first conventions. Editing a
deleted comment returns `409`; repeat deletion does not repeat audit/state
changes. PUT and collection DELETE are not supported.

Read fields are `id`, `task_id`, `author_profile_membership_id`, `content`,
`is_deleted`, `edited_at`, `deleted_at`, `created_at`, `updated_at`. No author
email, username or global User ID is exposed. The author membership projection
is current and nullable if the author no longer belongs to this Profile.
Deleted content is always `null` in API output; the original body stays in
the protected database row. Author projection is batched for list reads.
Pagination keeps the standard `count/next/previous/results` envelope,
default 20/max 100 and existing page/format semantics.

Comment services repeat scope/capability checks under Profile → Workspace →
Task → Comment locks. Creation/edit/soft-delete writes identifier-only audit
metadata in the same transaction; bodies are not copied into AuditLog or
Notification. Only creation emits a notification event. Comment changes never
approve/reject a Deliverable, change Task status/parent policy or create a
Review. Concurrent edits serialize with last-writer-wins behavior; no
optimistic version/ETag contract is implemented. Edit markers and audit events
are not full text-version history. Collection POST has no general
Idempotency-Key contract: a separate successful POST creates another Comment.

### Personal in-app notifications

| Method/path | Contract |
|---|---|
| `GET /api/v1/notifications/` | Own currently accessible notifications; stable `-created_at,id`, standard bounded pagination; optional validated `is_read=true/false`. |
| `GET /api/v1/notifications/unread-count/` | `{"unread_count": number}` from the same current-access scope. |
| `POST /api/v1/notifications/{notification_id}/read/` | Empty strict body; mark own still-accessible row read; return its representation, idempotently. |

These routes require an active authenticated User and retain SessionAuthentication,
CSRF for POST, no-cache responses and the global deny-by-default policy. No
mark-all-read, recipient override, write/create API or public endpoint exists.
Other users' IDs, malformed IDs and inaccessible targets are generic `404`.

Output fields are `id`, `event_type`, `profile_id`, `workspace_id`, `task_id`,
`title`, `message`, `target_url`, `is_read`, `created_at`, `updated_at`. Display
text is fixed per event, never Task titles, free-text comments/review feedback,
raw credentials or actor/recipient PII. `target_url` is generated by reversing
the canonical nested Task route, not taken from user input or external URLs.
Identifiers/links are navigation data, never authorization.

The feed/count/read scope repeats live active-User/Profile membership and
effective Workspace read rules, plus canonical Task → Workspace → Profile
equality. Profile Owner/Admin inherit same-Profile reads; ordinary Members
require active Workspace ADMIN/MEMBER/VIEWER. Revocation or unsupported role
removes old notifications from all three APIs. Incomplete unscoped legacy rows
are retained but hidden. No staff bypass exists. Archived contexts remain
readable where Task reads are allowed; mark-read changes only personal metadata
and locks Profile → Workspace → own Notification before revalidation.
If valid Task read access is later restored, an old notification can reappear
with its existing read state; hiding is not destructive deletion or a new grant.

| Event | Actor/trigger | Eligible recipients |
|---|---|---|
| `TASK_ASSIGNED` | Manager successfully assigns/reassigns Task | That event's current active Editor assignment. |
| `REVIEW_SUBMITTED` | Assigned Editor submits Deliverable | Current same-Profile Owner/Admin and current Workspace Admin reviewers. |
| `REVIEW_APPROVED` | Authorized reviewer approves latest Deliverable | Its uploader, if still a current Task reader. |
| `REVIEW_CHANGES_REQUESTED` | Authorized reviewer requests changes | Its uploader, if still a current Task reader. |
| `TASK_COMMENTED` | Authorized User creates Comment | Task creator and active assignee, where still current readers. |

Every set excludes actor, duplicates, inactive identities and recipients lacking
current Task access. There is no whole-Profile broadcast or parent/subtask
cascade. Producer validation binds the persisted AuditLog event and entity to
the canonical Task context; replaying an assignment event does not target a
later assignee. New notifications are not generated for archived/ineligible
event replays or a now-deleted Comment.

Consistency is **atomic database persistence**, not best effort: business
mutation + AuditLog + notifications share the enclosing transaction, and a
notification insert failure rolls all of them back. The `(user,event)` unique
constraint and get-or-create deduplicate retries of the same persisted event
without resetting `is_read`. This is event deduplication, not a general HTTP
POST idempotency-key service. No signal, `on_commit` delivery callback,
background worker, Celery/Redis, SMTP or push provider is introduced.

### AI Feedback Analyzer readiness

Authorized Task/Workspace context, individual Review feedback, Comment IDs/
timestamps and Deliverable revisions can become future feedback sources.
They are not automatically interpreted as Review outcomes or Task instructions.
Notifications are event indicators, not a feedback-text source. Retained
deleted Comment bodies must not bypass tombstones or authorized projections
in any future analyzer. Remaining design gaps include immutable edited-text versions/source citations,
an explicitly authorized aggregate feedback retrieval contract, source
invalidation/deletion handling, and human confirmation before creating suggested
Task/Subtask changes. No LLM/provider/key, AI Suggestions table or autonomous
database write is part of this task. Project scope remains independently gated.

## API boundary and public allowlist

Every endpoint under `/api/` is implemented as a Django REST Framework view.
The global default is `IsAuthenticated`; a public endpoint must declare
`AllowAny` explicitly and must be added only after security review. The current
public allowlist is:

- `/api/health/`
- `/api/auth/csrf/`
- `/api/auth/register/`
- `/api/auth/login/`
- `/api/auth/password-reset/request/`
- `/api/auth/password-reset/confirm/`

Public authentication endpoints retain the CSRF and throttle behavior
documented below. The health endpoint is the deliberate exception described in
the next section. `/admin/` is outside both `/api/` and DRF; it continues to use
Django Admin authentication and authorization.

The password-reset routes are intentionally public because a user who cannot
authenticate must be able to recover access. They still require CSRF and use a
neutral request response plus generic token errors. Email-verification request
and confirm are not public: both require the current authenticated session.

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

## Profile Invitation and membership onboarding API

Source/development status: `HT-INV-P2-04 IMPLEMENTATION COMPLETE;
HT-DB-P1-08 COMPLETE — DEVELOPMENT ROLLOUT VERIFIED`

The implementation adds six authenticated route shapes under `/api/v1/`.
They use the existing Django `SessionAuthentication` policy; none is public
and none uses `AllowAny`. Every `POST` requires a valid session CSRF token,
all responses are non-cacheable, and the invitation token is a credential
rather than an authentication mechanism.

| Method | Path | Access | Purpose |
|---|---|---|---|
| `GET`, `POST` | `/api/v1/profiles/{profile_id}/invitations/` | Active Profile Owner or Admin; role ceiling applies | List visible invitation metadata, or create and email one invitation. |
| `GET` | `/api/v1/profiles/{profile_id}/invitations/{invitation_id}/` | Active Profile Owner or Admin; tenant and role ceiling apply | Read one sanitized invitation record. |
| `POST` | `/api/v1/profiles/{profile_id}/invitations/{invitation_id}/revoke/` | Active Profile Owner or Admin; tenant and role ceiling apply | Irreversibly revoke one pending invitation. |
| `POST` | `/api/v1/profiles/{profile_id}/invitations/{invitation_id}/resend/` | Active Profile Owner or Admin; tenant and role ceiling apply | Revoke/retain the prior credential and create a newly delivered replacement record. |
| `POST` | `/api/v1/invitations/accept/` | Active authenticated User matching the unique normalized recipient email | Consume a sent token and create or safely reactivate Profile membership. |
| `POST` | `/api/v1/invitations/decline/` | Active authenticated User matching the unique normalized recipient email | Consume a sent token and terminalize the invitation as declined. |

There is deliberately no recipient inbox/list endpoint. The current User
model has no persistent account-level verified-email marker, so merely being
signed in with an asserted address does not authorize discovery of invitation
metadata. A recipient instead proves control for this one invitation by
possessing the emailed secret and signing in with the uniquely matching
normalized account email. This does not mark the account email globally
verified.

### Manager contracts and role ceiling

Creation accepts exactly:

```json
{
  "recipient_email": "recipient@example.com",
  "requested_role": "MEMBER"
}
```

`requested_role` is optional and defaults to `MEMBER`. A Profile Owner may
invite `ADMIN` or `MEMBER`; a Profile Admin may invite only `MEMBER`. No API
may invite an `OWNER`. Admin list/detail/action scope also omits `ADMIN`
invitations, so an Admin cannot inspect or act on records above that role
ceiling. A current active Profile membership and User are required. Archived
Profiles remain readable to scoped managers but block create, revoke, resend,
accept, and decline mutations.

Create returns `201 Created`. Manager detail, revoke, and resend return `200
OK`; revoke/resend bodies must be an empty JSON object, and unknown fields are
rejected. Manager list uses the standard bounded page-number envelope ordered
by newest `created_at`, then `id`. Every manager representation contains only:

- `id`
- `profile_id`
- `recipient_email`
- `requested_role`
- `status`
- `delivery_status`
- `expires_at`
- `delivery_attempted_at`
- `delivered_at`
- `accepted_at`
- `declined_at`
- `revoked_at`
- `expired_at`
- `created_at`
- `updated_at`

`status` is rendered as `EXPIRED` once the seven-day boundary has passed even
before the next locked mutation materializes that state. Responses never
include the raw token, token digest, recipient User ID, inviter identity, or
terminal actor IDs. The raw token is sent only through the configured mailer.

Revoke accepts only an unexpired `PENDING` record. Resend accepts an unexpired
pending or expired record, never mutates a consumed terminal record, and
creates a new invitation with a new credential and immutable `replaces`
lineage. If the old record is pending, it becomes `REVOKED`. Consequently an
old, consumed, revoked, expired, or rotated token cannot be replayed.

### Recipient contracts and membership effect

Accept and decline each accept exactly one write-only field:

```json
{"token": "opaque-token-received-by-email"}
```

The token has at least 256 bits of randomness. Only its SHA-256 digest is
stored. The service locks and revalidates the active Profile, pending/sent and
unexpired invitation, authenticated User, uniquely matching normalized email,
optional bound recipient User, and original inviter's current authority. A
token cannot be used when delivery is merely queued or failed. Invalid,
unknown, expired, rotated, consumed, mismatched-recipient, ambiguous-account,
archived-Profile, or no-longer-authorized-inviter cases fail with the same
generic conflict response and disclose no invitation metadata.

Successful acceptance returns:

```json
{
  "status": "ACCEPTED",
  "profile_id": "00000000-0000-0000-0000-000000000000",
  "membership_id": "00000000-0000-0000-0000-000000000000",
  "role": "MEMBER"
}
```

It creates one active ProfileMembership when no history exists. Exactly one
inactive membership may be reactivated in place only when its role exactly
matches the invitation and it is not `OWNER`; ambiguous or mismatched history
fails closed. An existing active membership is a conflict and is never used to
change role. Acceptance never creates a WorkspaceMember. To prevent a Profile
rejoin from implicitly restoring old Workspace authorization, any stale active
WorkspaceMember rows in that Profile are soft-revoked atomically and require a
later explicit direct-add. Invitation, ProfileMembership, WorkspaceMember, and
AuditLog changes participate in the locked transaction.

Successful decline returns `{"status":"DECLINED"}` and creates no membership.
Terminal `ACCEPTED`, `DECLINED`, `REVOKED`, and `EXPIRED` records are immutable
through this API.

### Delivery, throttling, and errors

Delivery is scheduled with `transaction.on_commit()`. The configured console,
dummy, and file mail backends are rejected for invitations because they could
expose or falsely discard a credential; the locmem backend is allowed only as
an isolated-test adapter. A real SMTP/provider path must be configured and
verified before operational use. If no safe backend is configured, create or
resend returns generic `503 Service Unavailable` without creating a record. If
the mailer fails after the invitation/audit transaction commits, the API still
returns generic `503`, the pending row honestly records `delivery_status:
"FAILED"`, and managers can discover it through the scoped list/detail API and
recover with resend. The API never claims `SENT` unless the adapter reports one
successful send.

Create and resend share a durable 24-hour issuance budget of 30 records per
inviter and 5 records per normalized recipient email. PostgreSQL row/advisory
locking serializes those counters. DRF also applies `30/day` per authenticated
sender, `5/day` per normalized create recipient, and `5/day` per authenticated
User across accept/decline attempts. These DRF counters use the configured
cache; with the current default process-local cache they are defense-in-depth
only and require a shared production cache for multi-worker enforcement. The
database-backed issuance limits remain authoritative for create/resend.

Invitation errors follow the existing tenant contract:

- malformed or unknown input, including malformed Unicode recipient email:
  `400 Bad Request` rather than `500`;
- anonymous SessionAuthentication, invalid CSRF, inactive account, insufficient
  role, or archived-Profile manager mutation: `403 Forbidden`;
- malformed, unknown, cross-tenant, wrong-parent, or role-ceiling-hidden
  manager resource: generic `404 Not Found`;
- duplicate/replayed/terminal/expired token, unsafe membership history, or
  other current-state conflict: generic `409 Conflict`;
- cache or durable invitation limit exceeded: `429 Too Many Requests`;
- unavailable or failed safe mail delivery: generic `503 Service Unavailable`.

The new routes depend on additive source migration
`workspace.0004_profileinvitation`. Under the separately authorized
`HT-DB-P1-08`, a fresh verified backup was restore-rehearsed and only this
migration was applied to the persistent development database at 2026-10-23
05:09:39.628419 UTC. Development now has 31 migration records and an empty
22-column Invitation table; expected constraints, foreign keys, and indexes
are validated/valid, and pre/post business-row and session counts are
unchanged. Production and every other persistent target remain unauthorized.

**DEVELOPMENT SMOKE PASSED** without fixtures: health `GET` returned 200 and
`POST` 405; CSRF bootstrap returned 200; missing-CSRF registration returned
403; an invalid registration payload with valid CSRF returned 400; and
anonymous Profile lifecycle, Workspace read/write/lifecycle, Workspace
membership read/write/revoke, and all manager/recipient Invitation route
shapes returned 403. No request returned 500, exposed a token/digest/User PII,
or changed any row/session count. **NOT TESTED ON PERSISTENT DEVELOPMENT:** successful
authenticated Invitation list/create/detail/revoke/resend/accept/decline flows,
because development has no Profile/Workspace fixture or usable authenticated
session. Those behavior paths are covered by isolated tests.

At the implementation gate, Invitation model/service/API/migration tests pass
39/39, related Workspace/RBAC/Task/Review regression passes 173/173,
Authentication/API passes 29/29, and the full PostgreSQL suite passes 241/241.
Post-apply Django system, migration-drift, and `migrate --check` checks pass;
current P1-08 reruns also pass Invitation 39/39 in 62.528s, Authentication/API
29/29 in 7.475s, Workspace/RBAC/Task/Review 173/173 in 97.378s, and full
PostgreSQL 241/241 in 167.960s. Each Django test database was destroyed and the
full run reported zero system-check issues. **REAL EMAIL DELIVERY NOT
VERIFIED**: locmem was used for isolated tests and no SMTP/provider integration
was configured. Cache-based DRF throttles remain process-local by default.

## Task and internal approval workflow API

Source/development status: `HT-TASK-P2-03 COMPLETE — DEVELOPMENT ROLLOUT
VERIFIED BY HT-DB-P1-07`

The base workflow rollout above remains valid. The hierarchy/planning
extension below is `HT-TASK-P2-05`: **IMPLEMENTATION COMPLETE**. Owner later
authorized HT-DB-P1-10, which applied exact `tasks.0003_task_hierarchy` to
development after fresh verified backup and isolated restore rehearsal on
2026-10-25. At that historical checkpoint, development had 33 migration records
and nullable parent_id; HT-DB-P1-11 now supersedes the operational state above.
No API contract, permission or workflow was changed by either rollout. Historical
Task 88/88, broader regression 253/253 and full PostgreSQL 341/341 (170.987s)
PASS, with native launcher/Python runner exits 0 and owned cleanup verified.
The 51-request READ ONLY development handler smoke also passes; authenticated
success/mutations remain isolated-test-only. HT-DB-P1-10 is COMPLETE / OWNER
REVIEW GATE at that earlier checkpoint. Historical implementation results below
remain distinct from current HT-DB-P1-11 evidence; production remains unauthorized.

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
| `GET` | `{task_id}/subtasks/` | Effective Workspace read access | Paginated direct children of one scoped Task; no recursive tree. |
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

`title` is required. `description`, `priority`, `deadline`, and `parent_id` are
optional; priority defaults to `MEDIUM` and parent defaults to null (root).
`PATCH` accepts a subset of these five mutable metadata fields; empty or
unchanged input is a no-op with no audit event. The example above remains valid
unchanged. To create a Subtask, include `"parent_id": "same-workspace-task-uuid"`
in the existing collection POST; there is no second Subtask write endpoint.
Unknown and server-owned fields—including
`profile_id`, `workspace_id`, `status`, creator, assignment, revisions,
reviewer, IDs, and timestamps—are rejected with `400 Bad Request`.

Task responses contain exactly:

- `id`
- `workspace_id`
- `parent_id`
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

### HT-TASK-P2-05 hierarchy, deadline and priority — 2026-10-25

`parent_id` is the only added response field; all existing fields and the
paginated envelope remain. Null identifies a root. A Task may have many direct
children. The maximum depth is three parent edges below a root (depth 0), or
four levels total. Reparenting and detaching use the existing Task PATCH;
`parent_id: null` detaches. Both the ancestor chain and the deepest moved
descendant must remain within that cap. Self-parent, cycles and invalid depth
return `400`; a syntactically valid missing, foreign-Workspace or foreign-
Profile parent reference returns the same generic `404`. Malformed body UUIDs
return serializer `400`. Workspace/Profile identity never changes.

Each Subtask is a Task with its own assignment, status, Deliverables and
Reviews. Its lifecycle remains `PENDING -> ASSIGNED -> WORKING -> REVIEW ->
COMPLETED`, with request-changes returning that same Task to `WORKING`.
Parent and child status are independent: a parent can be approved while
children remain unfinished; parent approval does not approve or complete
children; completed children do not complete their parent; child revision
does not reopen the parent. Existing reviewer capability, no-self-review,
latest-revision and atomic audit checks apply separately to each Task.
These are the bounded implementation choices for the authorized foundation,
not a claim of a new separate Owner approval of downstream aggregate rules.

Deadline remains nullable and is not tied to the Workspace month. ISO datetime
input with an offset is normalized to UTC; input without an offset follows the
existing Django UTC timezone. Invalid formats/calendar dates and timezone
conversion overflow return `400`, never an intentional `500` path. A child
deadline is independent of its parent's deadline and may fall later; no
clamping, propagation, automatic overdue status, deadline-triggered notification or scheduler is
introduced. Existing legacy Task deadlines are not backfilled or rewritten.

Priority reuses the existing `LOW`, `MEDIUM`, `HIGH`, `URGENT` choices and
`MEDIUM` default. A change never changes status. Only current Task managers
(same-Profile Owner/Admin or the Workspace's active Admin) may change
parent/deadline/priority. An assigned Editor and a Viewer cannot change those
fields. Creation and material changes use the existing atomic
`task.created`/`task.updated` audit conventions; parent changes record previous
and next parent IDs. Archived Profile/Workspace writes remain forbidden and
inactive memberships do not grant access.

Collection GET stays flat and includes roots and descendants by default.
Clients can reconstruct a bounded structure from `id`/`parent_id`, or request
one paginated child level through `{task_id}/subtasks/` (`GET`/`HEAD`/`OPTIONS`
only). No nested children or unbounded tree is embedded in a Task response.
The existing prefetch now also obtains active same-Profile membership IDs in
one query, avoiding per-child assignment-identity queries.

Optional domain filters on the collection and child list:

| Parameter | Contract |
|---|---|
| `root_only=true` | Roots only; cannot combine true with `parent_id`. |
| `parent_id=<uuid>` | Direct children of an existing Task resolved inside the current Workspace; inaccessible/missing parent is generic `404`. |
| `status` | One existing status choice. |
| `priority` | One existing priority choice. |
| `deadline_after`, `deadline_before` | Inclusive lower/upper ISO datetime bounds; null deadlines are excluded; reversed bounds return `400`. |
| `ordering` | `created_at` (default), `-created_at`, `priority`, `-priority`, `deadline`, or `-deadline`; ID breaks ties. Priority uses `LOW < MEDIUM < HIGH < URGENT`; null deadlines sort last in both directions. |

Invalid domain filter values return `400`. DRF retains its existing
`page`, `page_size`, maximum-page-size and format negotiation behavior,
including `page=last` and default fallback for invalid/nonpositive page size.
All filters run after tenant scoping and cannot widen access. No route is
public; SessionAuthentication, CSRF, read-only Viewer access, inactive-member
denial and staff-without-membership denial remain unchanged.

Historical HT-TASK-P2-05 isolated evidence: new and existing Task API **42/42 PASS** (4.990s),
model/service and existing workflow **43/43 PASS** (4.770s), and hierarchy
migration tests **2/2 PASS** (1.465s), including legacy relationship retention.
Workspace/RBAC regression **122/122 PASS** (60.495s) and full PostgreSQL
regression **341/341 PASS** (174.058s). Dependency/system/model-drift/migration-
chain checks and owned-resource cleanup pass through the shared harness.
At that implementation gate development had32 migrations,3 Users/2 Sessions
and zero token/business rows, with no parent column or tasks.0003 record.
HT-DB-P1-10 superseded that state at its checkpoint: migration applied,33 records,
nullable parent column and unchanged legacy data. Current HT-DB-P1-11 evidence
is in HANDOVER.md. Authenticated success/mutation/hierarchy validation HTTP
flows are **NOT TESTED ON PERSISTENT DEVELOPMENT**: they use isolated fixtures.
The 51-request read-only handler smoke has no 500/PII/CSRF bypass or row mutation;
16 serializer-only checks are not authenticated HTTP coverage.
Project remains design-only:
`PROJECT_ARCHITECTURE_REVIEW.md` is **PENDING OWNER DECISION**.

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
available for Task or Deliverable. HT-COM-P2-06 adds only the separately
documented Comment CRUD routes; claim/Marketplace, Client/Guest review,
file-upload/media, Finance/Payroll and Task soft-delete APIs remain absent.

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
`reviews.0002_review_workflow_foundation`. `HT-DB-P1-07` verified the local
development target and zero-business-row baseline, created and restore-
rehearsed a fresh backup, then applied exactly `tasks.0002` followed by
`reviews.0002`. Development now has Workspace 0001-0003, Tasks 0001-0002 and
Reviews 0001-0002 applied (30 migration records). Expected columns,
constraints, indexes and foreign keys are valid; row/session counts are
unchanged. Production and every other persistent environment remain
unauthorized.

Fixture-free development smoke passed with no row/session change:

- health `GET`/`HEAD`/`OPTIONS` returned `200`, while health
  `POST`/`PUT`/`DELETE` returned `405`;
- CSRF bootstrap returned `200`, login without CSRF returned `403`, and invalid
  login with a valid token returned `400`;
- anonymous Auth, Profile, Workspace, Task, Deliverable and internal Review
  route shapes returned `403`; no request returned `500`.

Successful authenticated tenant mutations and method-specific Task behavior
were intentionally not exercised on persistent development because it has no
business fixture and no credential was changed. Current isolated PostgreSQL
evidence covers those paths: Task workflow/API/migration 33/33 in 7.998s,
Authentication/API 29/29 in 7.183s, Workspace 140/140 in 77.774s, and full
suite 202/202 in 93.368s. Test databases were destroyed; dependency, Django
system, migration-drift and `migrate --check` checks passed.

## Authentication foundation

Base path: `/api/auth/`

Implementation status: **HT-AUTH-P1-02 — IMPLEMENTATION COMPLETE / DEVELOPMENT
SCHEMA APPLIED**. HT-DB-P1-09 applied exact additive `accounts.0002` to the
approved development database after backup and restore rehearsal. The
rollout is COMPLETE / OWNER REVIEW GATE; production and other persistent
targets remain unauthorized. This operational task changes no API contract.

The current authentication contract uses Django server-side sessions and DRF
`SessionAuthentication`. It assumes a same-origin frontend (or a reverse proxy
that presents frontend and API as the same site). CORS is not enabled.

### Browser client flow

1. Call `GET /api/auth/csrf/` while retaining cookies.
2. Send the returned `csrf_token` as the `X-CSRFToken` header on every unsafe
   request, including public register/login/password-reset operations.
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
| `POST` | `/api/auth/email-verification/request/` | Authenticated + CSRF | Send a fresh verification credential for the authenticated User's current email. |
| `POST` | `/api/auth/email-verification/confirm/` | Authenticated + CSRF | Consume that User's delivered credential and mark the current email verified. |
| `POST` | `/api/auth/password-reset/request/` | Public + CSRF | Return a neutral acceptance response and, when eligible, email a reset credential. |
| `POST` | `/api/auth/password-reset/confirm/` | Public + CSRF | Consume a delivered credential and set a validator-approved new password without logging in. |

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
    "created_at": "2026-10-14T00:00:00Z",
    "email_verified": false
  }
}
```

Logout returns `204 No Content`. Invalid login credentials return the same
neutral `400` response whether the email is unknown, the password is wrong, or
the account is inactive. Anonymous access to session-protected endpoints
returns `403` with DRF `SessionAuthentication`. Throttled requests return `429`.

### Email verification

`POST /api/auth/email-verification/request/` accepts exactly an empty JSON
object. It uses only the authenticated User and never accepts a client-supplied
email or User ID. A successful new request, resend/rotation, or already-verified
no-op returns:

```json
{
  "detail": "Verification request accepted."
}
```

with `202 Accepted`. Unsafe/misconfigured credential delivery returns a generic
`503`; an unusable/ambiguous current account state returns generic `409`.
Requesting again revokes the previous pending verification credential before a
replacement is issued. The new credential expires after 24 hours.

`POST /api/auth/email-verification/confirm/` accepts exactly:

```json
{
  "token": "credential-received-by-email"
}
```

The authenticated actor must be the token's active User. The token must be
pending, delivered, unexpired, and bound to the uniquely resolved normalized
current email. Success returns `200 OK` with
`{"detail":"Email verified."}`. Invalid, expired, replayed, wrong-actor, stale-
email, or ambiguous-identity credentials share the generic `400` response.
A material normalized-email change clears persisted verification and revokes
pending verification and reset tokens, including an `A -> B -> A` sequence.
Casing-only changes keep the same identity.

### Password reset

`POST /api/auth/password-reset/request/` accepts exactly:

```json
{
  "email": "user@example.com"
}
```

Every well-formed request returns the same `202 Accepted` payload regardless
of whether the normalized address identifies exactly one active User with a
usable password, is unknown/ambiguous/inactive, or encounters a delivery
failure:

```json
{
  "detail": "If an eligible account exists, the request has been accepted."
}
```

Only an eligible uniquely resolved User receives a one-hour reset credential.
No email, User ID, token, digest, or delivery outcome is returned. A resend
rotates the previous pending reset token. This makes the HTTP status and body
neutral across account outcomes; the implementation does not pad or equalize
execution time and does not claim timing-indistinguishability.

`POST /api/auth/password-reset/confirm/` accepts exactly:

```json
{
  "token": "credential-received-by-email",
  "new_password": "validator-approved password",
  "new_password_confirm": "validator-approved password"
}
```

The credential must be pending, delivered, unexpired, still bound to the User's
uniquely resolved current email, and match the SHA-256 fingerprint of the exact
encoded Django password state captured when issued. A password change through
`User.save()` revokes pending reset credentials. Even a direct queryset update
that bypasses that hook makes the fingerprint comparison fail closed. Success
returns `204 No Content`, atomically consumes the credential before replacing
the Django password hash, and creates no session. Existing authenticated
sessions become unusable when Django compares their stored authentication hash
after the password change. The old password no longer authenticates; the user
must log in explicitly with the new one. Invalid, expired, changed-email,
changed-password, ambiguous, or replayed credentials share a generic `400`; a
password-validator error is also `400` but does not consume an otherwise valid
token.

All four account-security POST routes reject unknown input fields with `400`,
return `405` for unsupported methods, mark responses `Cache-Control: no-store`,
and never include the submitted raw credential in responses. Verification
request and confirm have separate authenticated-user throttles of `5/hour` and
`10/hour`. Reset request combines normalized-email `5/hour` and client-address
`20/hour` throttles. Reset confirm independently applies a submitted-token
fingerprint limit of `10/hour` across client addresses and a client-address
limit of `30/hour` across rotating tokens. Cache keys use one-way fingerprints,
not raw emails/tokens. Malformed Unicode is fingerprinted safely and then fails
closed as `400` during validation/service processing, avoiding an encoding-
driven `500` path.

The endpoints and schema are an implementation-complete HT-AUTH-P1-02
contract. Historical implementation PostgreSQL gates passed account security 44/44
(32.336s), Authentication/API/Invitation 113/113 (99.629s),
Workspace/RBAC/Task/Review 173/173 (93.895s), and full suite 286/286
(188.592s). Additive `accounts.0002` is now applied to approved development
through HT-DB-P1-09, never to production or another persistent target.

### HT-DB-P1-09 development rollout verification — 2026-10-24

**DEV SMOKE PASSED**: 45 fixture-free requests (the original 36 plus eight
Task/Review boundary requests and one extra CSRF bootstrap) through the Django
request handler against persistent development in a PostgreSQL READ ONLY transaction,
with CSRF enforcement enabled. Health/CSRF bootstrap return 200; unsafe auth/
reset requests without CSRF return 403; malformed registration/login/reset
inputs return 400; protected anonymous account/Profile/Workspace/Task/Review/
Invitation route shapes return 403; unsupported methods return 405. An unknown
reset request returns neutral 202 and invalid reset confirmation generic 400.
No 500, token/digest/User PII disclosure, delivery attempt, login, or User/
Session/token mutation occurred. This is direct request-handler smoke against
development, not an external-network/browser test.

Authenticated success, real verification/reset consumption, session
invalidation, and Invitation acceptance are **NOT TESTED ON PERSISTENT
DEVELOPMENT**. Those operations use isolated PostgreSQL fixtures: account
security 44/44 (30.549s), Authentication/API 29/29 (7.523s), Invitation 40/40
(61.679s), Workspace/RBAC 140/140 (79.717s), and Task/Review 33/33 (8.457s) PASS.
The completed targeted runs were reused after resume with unchanged source/
schema. The unfinished full-suite gate was rerun and passes 286/286 in
197.049s, exit 0. Final checks, exact legacy-row preservation, and cleanup
pass; the verified host backup and ignored full-test log/exit record remain.
HT-DB-P1-09 is COMPLETE / OWNER REVIEW GATE. No real provider delivery or
distributed rate-limit verification is established by this rollout.

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
- Email verification and password-reset foundations are now implemented in
  source by HT-AUTH-P1-02. Verification is not an account-activation gate:
  registration still creates an active User and existing unverified Users may
  log in. Standalone logout-all/account deactivation, OTP, JWT, and OAuth remain
  outside this task. The separately documented `/api/v1/` tenant slice now
  includes the Workspace metadata/lifecycle/membership operations and the
  implemented Profile Invitation/onboarding slice above. General Profile
  create/update, downstream business APIs, and frontend integration remain
  unimplemented. The Workspace schema-dependent routes have
  completed the approved development-only `workspace.0003` rollout; deployment
  to production or any other persistent target still requires separate review
  and authorization. Invitation migration `workspace.0004` has completed its
  authorized development-only backup/rehearsal/apply/schema/smoke/regression
  gates under HT-DB-P1-08; no other target is authorized.
- Account-security tokens are random, purpose-separated before SHA-256 digest,
  stored digest-only, expiring, rotated, and consumed under locks. Raw tokens
  appear only in the configured email message. Audit metadata contains purpose
  and state transitions, never token, digest, email, or password values.
  Password-reset records additionally hold a fingerprint of the encoded Django
  password state; the purpose constraint forbids it on verification records.
- Credential delivery reuses the configured default mailer safety boundary and
  refuses console/dummy/file backends; isolated tests use locmem. **REAL EMAIL
  DELIVERY NOT VERIFIED.** No SMTP/provider credential was configured or
  exercised. The default cache throttles remain process-local and are not a
  distributed multi-worker production control.
- Profile Invitation behavior is unchanged: its own authenticated recipient,
  unique-current-email, delivery-`SENT`, and one-time invitation-token proof
  remains sufficient. The new global verification signal is not retroactively
  required for Invitation accept/decline, so legacy onboarding is not blocked.
