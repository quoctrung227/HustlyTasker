# HUSTLYTASKER API DOCUMENTATION

Last updated: 2026-11-10

## HT-FE-TASK-UX-REFINEMENT-01 — Product links and assignee labels

Current Owner-approved contract supersedes earlier **new submission** text/URL
wording in this document. Existing routes, SessionAuthentication, CSRF, tenant
scope, mutation capabilities, transactions and internal Review rules are retained.
No model or migration is added or changed.

### New submissions and resubmissions

`POST /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/deliverables/`
still accepts exactly `{ "file_url": "https://example.test/finished-product" }`
and returns the existing Deliverable DTO with `201`. For every new revision,
`file_url` must be a nonempty HTTP(S) URL of at most **500 Unicode code points**
after trimming leading/trailing whitespace. Raw control characters (C0/C1) and
invalid Unicode are rejected before trimming; internal whitespace, backslashes,
embedded username/password, invalid host/port, nonstrings and other schemes are
rejected with field-level `400`. Both the strict serializer and existing domain
submission service enforce the same validation. This does not validate external
sharing permissions, existence or media contents: no server fetch, preview,
upload, storage integration or external request is performed.

Historical `file_url` values remain unchanged in storage and read responses,
including old text or paths. They are not revalidated, normalized, backfilled or
made unconditionally clickable. React renders legacy non-URL references as
escaped text; a safe HTTP(S) reference has an explicit **Mở sản phẩm** link with
`target="_blank"` and `rel="noopener noreferrer"`. Each revision retains its own
reference. The form is **Link sản phẩm hoàn thành** / **Nộp sản phẩm**, validates
before sending and prevents concurrent duplicate submits. An unknown network
outcome preserves the draft and asks the user to inspect history; it does not
automatically retry or assume a submission succeeded.

Only the current eligible assigned Editor may submit while the Task is WORKING
and has no unresolved Deliverable. Submission allocates the next revision and
sets REVIEW through the existing locked service. A distinct authorized reviewer
may request changes or approve only the latest eligible revision; request changes
returns WORKING, approval completes the Task. Capability hints never replace
live authorization/state checks. No parent/child cascade or optimistic completion
is introduced; existing `403`/tenant-safe `404`/workflow `409` behavior is retained.

### Additive read-only assignee display

Every existing Task response using `TaskReadSerializer` retains
`active_assignment: null` when no active assignment exists. An assignment object
retains `id`, `profile_membership_id` and `assigned_at`, and gains
`display_name: string | null`. This is a display label, not a writable assignment
field or permission/capability. For an eligible current assignee, the backend
uses a safe full name, then a safe username, then **Thành viên được giao**; it
never falls back to an email/contact value or UUID. No separate global User ID,
email or username field is exposed.

The actor must currently read the Task in the verified Profile/Workspace, and
the assignee must have an active account and current same-tenant access. A retained
assignment whose assignee no longer qualifies gets `display_name: null`; missing
or mismatched request/access context also fails closed. Existing archived-context
read rules remain. React distinguishes no assignment from an unavailable label
without showing membership UUIDs. Existing membership IDs are unchanged for
compatibility and must not be used to infer authority.

The projection reuses tenant-scoped SQL predicates and batches the bounded page
in one current-identity lookup rather than issuing a User/roster request for each
Task. Detail and mutation responses use the same projection. It grants no Task
execution, reassignment, metadata or compensation access: the narrower existing
`estimated_compensation_vnd` policy below is unchanged. Display-only access does
not establish valid assignee execution rights.

UTC deadline filter query names, instant boundaries and ordering semantics are
unchanged; React only stacks the existing from/to fields within **Khoảng thời hạn
(UTC)**. No timezone or deadline storage policy changes. Current read-only
development inventory records 37 applied migrations, 5 Users, 2 Sessions,
3 Tasks and 2 Deliverables; tasks.0005 is APPLIED and ai.0002 remains UNAPPLIED.
The earlier rollout inventory below is historical, not a current count.
See [HANDOVER](HANDOVER.md) for final verification and Owner review evidence.

## Historical HT-DB-TASK-BRIEF-ROLLOUT-01 — Development availability

**DEVELOPMENT MIGRATION COMPLETE — OWNER UI ACCEPTANCE PENDING.** The separately
Owner-approved targeted tasks.0005_task_brief rollout completed at
2026-11-10T13:47:38Z, exit0, after backup/restore/migration rehearsal. Development
now has37 applied records and all five Task brief columns; ai.0002 stays UNAPPLIED.
This changes schema availability, not API fields, capabilities, RBAC or workflow.
The field-level compensation projection below remains authoritative.

Read-only updated Task ORM reads both existing Tasks; Django checks/model
consistency and empty targeted plan PASS. The two Task rows retain all five new
metadata fields NULL. Normal
development Django/Vite startup and anonymous GET-only smoke9/9 PASS at13:49:20Z
(health/CSRF200, unauthenticated private endpoints403, Vite proxy working). No
authenticated business mutation or Owner UI acceptance was performed. Historical
isolated test counts below were not rerun in this rollout. Old candidate/no-apply
instructions are superseded for tasks.0005 only; AI/production apply remains
unapproved. HANDOVER contains backup and preservation evidence and manual steps.

## HT-FE-TASK-COMPENSATION-RBAC-01 — Field-level disclosure

Current Owner-approved policy supersedes the original broad compensation-read
policy of the candidate below. All Task DTOs keep the same field shape:
`estimated_compensation_vnd` is an exact canonical digit STRING only for current
authorized managers or the effective current Task assignee; otherwise NULL,
indistinguishable from an unset amount. No new capability flag or endpoint.

Existing authenticated tenant Task read access is mandatory. Profile OWNER/ADMIN
and Workspace ADMIN may read pay in their legitimate scope. An assignee needs
current ACTIVE assignment to that exact Task plus active User/Profile membership
and effective Workspace MEMBER access. Another Task's assignment, historical
assignment, VIEWER downgrade or staff/superuser flag grants no extra authority.
Revoked/out-of-scope actors retain existing safe404/denial behavior. Existing
archived-context read policy is retained; mutation remains lifecycle-restricted.

The shared TaskReadSerializer protects list/filter, detail, direct children,
create/PATCH and assign/start responses. Compensation authorization is batched
for the bounded serialized page with live membership/assignment SQL predicates;
prefetched assignment history cannot grant visibility. Missing/mismatched request
or tenant context redacts. `include_compensation=true` cannot override policy.
Task metadata writes still use existing locked manager services; read permission
never grants PATCH. Omitted compensation in PATCH retains its stored value.

Deliverable/Review/Comment/Workspace responses expose references or their own
scalars, not nested Task pay. Notifications use static event text and target IDs;
AI contracts use separate proposal/feedback/created-ID payloads. No Task export,
dashboard aggregation or public audit endpoint exists. Audit changed_fields only
records names, never pay values. No URL/deadline/Task workflow change. Current
development rollout evidence and pending Owner UI acceptance are in HANDOVER.
Inspection-only Django Admin excludes the compensation field entirely; global
Django model view permission cannot bypass the canonical tenant API projection.

## HT-FE-TASK-BRIEF-24H-VI-01 — Optional Task editing brief

**APPLIED DEVELOPMENT — OWNER UI ACCEPTANCE PENDING.** The schema is provided by
`tasks.0005_task_brief`, following tasks.0004, now applied by the controlled rollout
above. The earlier missing-column startup restriction is resolved. ai.0002 remains
outside this rollout; no authenticated development mutation test or manual UI
acceptance is implied by the read-only postchecks.

Existing nested Task list/detail/create/PATCH/action responses retain old fields
and gain five nullable read fields. Create/PATCH may optionally supply them:

| Field | Exact contract |
|---|---|
| raw_video_url | HTTP(S) raw video link, max2048 characters |
| reference_video_url | HTTP(S) reference video link, max2048 characters |
| template_project_url | HTTP(S) template project/resource link, max2048 characters |
| script_url | HTTP(S) script-document URL, not free text, max2048 characters |
| estimated_compensation_vnd | Whole nonnegative VND for the entire Task; canonical decimal digit STRING/null in responses; maximum999999999999999999 (numeric18,0 storage bound) |

URL null/empty/whitespace-only inputs normalize to null; control characters,
invalid URLs and non-HTTP(S) schemes are rejected. No public-access check, fetch,
embedding or preview call is made. New optional values omitted on legacy create
default null; omitted PATCH fields remain unchanged. Explicit null/empty clears.
No client-controlled role/assignment/tenant fields are added.

Money accepts a strict JSON integer or ASCII digit string/null (empty string
clears). Floats including1.0, booleans, exponent/sign/fraction/negative text,
nonfinite values and overflow are rejected before coercion in serializer AND
service. Clients should send digit strings, never floating numbers or localized
punctuation. Django stores exact Decimal/numeric(18,0); responses use strings to
avoid JavaScript Number precision loss. Frontend groups dots for display only.
This technical bound is not a business budget, payroll, payment or billing rule;
the amount is never multiplied by assignments.

```json
{
  "title": "Dựng video ví dụ giả lập",
  "raw_video_url": "https://example.test/private-source",
  "reference_video_url": null,
  "template_project_url": null,
  "script_url": "https://example.test/script",
  "estimated_compensation_vnd": "500000"
}
```

SessionAuthentication/CSRF/tenant access remain unchanged. Authorized Task readers
may read document links; compensation uses the narrower current field policy
defined above (the earlier broad-reader policy is superseded). Metadata create/
edit remains manager-only. Assigned Editor executes/submits under current rules,
not metadata editing. Existing conditional uniqueness permits ONE active assignee
plus historical rows; this task does not alter assignment semantics. Audits record
only changed field names, not new link/pay values. URLs are opened on explicit
browser action with target_blank and rel=noopener noreferrer.

Backend deadline contract remains an optional timezone-aware instant; legacy API
seconds remain supported. Ordinary React inputs are dd/mm/yyyy plus explicit
00–23/00–59 selects, converted from device local time to UTC at minute precision.
Untouched deadline PATCH is omitted to preserve the actual legacy timestamp.
UTC date-filter boundaries retain existing semantics. No global timezone change.
Ordinary UI removes hierarchy controls but API parent_id/subtasks/history remain
supported. Existing child Tasks stay in all-Task lists and direct detail routes.
Separate AI proposal hierarchy/legacy date helpers retain their existing contract.

Historical verification on candidate schema: targeted132/full937 isolated PostgreSQL,
frontend1047, quality and47 real isolated browser cases PASS with actual child
exits0/owned cleanup. Includes HTTP(S)/strict whole-VND validation, RBAC/IDOR/CSRF,
legacy compatibility, clear/null, HCM18:30↔11:30Z, Editor/Viewer visibility,
hierarchy/data preservation and workflow regressions. At that historical stage
development retained36 migration records and lacked the new columns. Current
development has37 records and Task brief columns, with old business data preserved;
ai.0002 stays unapplied. Historical isolated results are not development API E2E.
HANDOVER records all attempts, rollout evidence and the manual acceptance gate.

## HT-FE-WORKSPACE-INHERITANCE-01 — Workspace creation membership snapshot

**IMPLEMENTATION COMPLETE — OWNER REVIEW GATE.** Owner-approved additive contract; no
model/migration, authentication, role ceiling or email configuration changes.
This section supersedes older blanket statements that Workspace creation and
invitation acceptance never create WorkspaceMember rows.

`POST /api/v1/profiles/{profile_id}/workspaces/` retains required `name`,
canonical first-of-month `period`, optional `description`, and unchanged read DTO.
It additionally accepts either optional `source_workspace_id` (UUID) or optional
`initial_profile_membership_ids` (unique UUID list), never both. Omission retains
existing manual creation. Unknown fields, client roles/User IDs and server-owned
fields remain rejected. SessionAuthentication and CSRF are required.

Only active Profile OWNER/ADMIN create. Source must be readable and same-Profile;
archived readable sources are permitted because they are only snapshot reads.
Backend selects supported active ADMIN/MEMBER/VIEWER assignments backed by an
active same-Profile MEMBER and active User. Revoked/stale/inactive/legacy roles
and redundant Profile Owner/Admin direct assignments are skipped. It recomputes
under Profile-first locks and creates destination, grants and audits in one
transaction through existing membership services. No source row, Task/Assignment/
Review/Comment is copied or changed. Later source changes never cascade. Unique
Profile+period still makes duplicate409; no new retry/idempotency protocol.

Initial IDs apply only when the Profile has no Workspace. Every selected active
ordinary Profile MEMBER is validated and receives fixed MEMBER, never a supplied
role. Profile Owner/Admin governance remains inherited without fabricated rows.
Empty list is allowed; later manual grants use existing membership endpoints.

`GET /api/v1/profiles/{profile_id}/workspace-inheritance/` is a read-only,
never-cache creation preview under the same Profile creation permission.
Optional `source_workspace_id` selects a source; page/page_size use existing
bounded pagination. Without source, mode is `initial` if no Workspace exists,
otherwise `manual`. React obtains choices from the existing Workspace list;
it never infers previous month from creation time.

```json
{
  "count": 1, "next": null, "previous": null,
  "mode": "inheritance",
  "source_workspace": {
    "id": "11111111-1111-4111-8111-111111111111",
    "name": "Workspace nguồn giả lập", "period": "2026-10-01"
  },
  "excluded_count": 0, "has_workspaces": true,
  "results": [{
    "profile_membership_id": "22222222-2222-4222-8222-222222222222",
    "display_name": "Thành viên giả lập", "role": "MEMBER"
  }]
}
```

Preview exposes sanitized labels, membership references and roles, no contact or
global account identifiers. Excluded rows expose only an aggregate count. It is
advisory; POST rechecks current authority/eligibility. Workspace Admins cannot
use creation/preview to exceed existing ceilings. Invalid bodies400, inaccessible
source404, forbidden creation403 and duplicate period409 follow conventions.
React never automatically retries an uncertain mutation.

Only after successful invitation accept, the same atomic transaction may grant
MEMBER in the ACTIVE same-Profile Workspace whose period is the current month's
first day in configured Django timezone (currently UTC). Missing/null legacy/
archived/past/future target means no grant and does not break acceptance.
Compatible Profile reactivation can join only when NO current WorkspaceMember
row exists, including inactive history. Existing stale-access revocation runs
first; revoked rows never reactivate. Invited Profile Admins already inherit
governance. Sending/resending mail, login, replay and failed/wrong-recipient
acceptance never grant access. No Task assignment/status change. Audit failure
rolls back accept and grant together; no email-delivery change.

Current verification: targeted PostgreSQL132/full905, frontend955 and24 real
isolated browser cases PASS with actual process exits0. Identity/CSRF/IDOR,
revoked/inactive membership, snapshot/current-month, rollback/concurrency and
legacy-client behavior are covered; development29-table fingerprint unchanged,
36 migrations andai.0002 unapplied retained. See HANDOVER for exact receipts,
failed-attempt distinctions and manual/genuine-mail limitations.

## HT-FE-WORKSPACE-MEMBERS-01 — Workspace access contract

Status: **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**. This task connects the
existing Workspace membership domain to React. It adds a bounded read-only
candidate endpoint and additive capability hints, not a membership model,
mutation service, role, migration or parallel authorization system. Current
backend, targeted final frontend, real isolated browser and read-only development
preservation checks below pass. Historical839/801/14 results below are not new
results for this task. Manual Owner website acceptance and real SMTP remain
unverified; no next task, AI activation, migration rollout or deployment begins
automatically.

### Actual domain and management authority

`WorkspaceMember` already links User to Workspace with one unique
`(workspace,user)` row. Profile membership, explicit Workspace assignment and
Task assignment are distinct. Active Profile Owner/Admin inherit access and
management across their same-Profile Workspaces without WorkspaceMember rows.
Ordinary Profile MEMBER needs an active explicit ADMIN/MEMBER/VIEWER row;
MEMBER is the stored value for Workspace Editor. Legacy Workspace OWNER,
transitional Workspace.owner and staff/superuser flags grant no authority.

| Caller | Read Workspace | Read roster/candidates | Grant/update/revoke Workspace roles |
|---|---|---|---|
| Active Profile OWNER/ADMIN | Same-Profile Workspaces, inherited | Allowed | ADMIN/MEMBER/VIEWER |
| Profile MEMBER + active Workspace ADMIN | Assigned Workspace only | Allowed | MEMBER/VIEWER; cannot alter an existing ADMIN row |
| Profile MEMBER + active Workspace MEMBER/VIEWER | Assigned Workspace only |403 | None |
| Profile MEMBER without effective assignment |404 |404 | None |
| Inactive/revoked/foreign identity or tenant scope |404 or authentication403 | Denied | None |

Both Profile and Workspace must be ACTIVE for mutations. Manager roster remains
readable in archived scope; mutation hints are false and candidate list is empty.
Outside the explicit conditions above, Profile membership alone never grants
ordinary Members Workspace access. Profile selection in React is not authority.

### Read endpoints and additive capabilities

Prefix: `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}`.

`GET /members/` retains standard bounded pagination and all eight existing row
fields: id,profile_membership_id,display_label,is_assignable,role,is_active,
joined_at,updated_at. It adds response-level `capabilities`:

```json
{
  "can_add": true,
  "allowed_roles": ["ADMIN", "MEMBER", "VIEWER"],
  "profile_role": "OWNER",
  "workspace_role": null,
  "has_inherited_access": true
}
```

`workspace_role` is null for inherited Profile Owner/Admin authority; for a
delegated manager it is ADMIN and allowed_roles is MEMBER/VIEWER. Archived
scope keeps the actual role/inheritance explanation, but can_add:false and
allowed_roles:[]. This resolver role is not an inventory of explicit rows:
null does not prove that an inherited manager lacks an explicit assignment.
Each roster row adds nested `capabilities`:

```json
{
  "can_update": true,
  "can_revoke": true,
  "allowed_roles": ["ADMIN", "MEMBER", "VIEWER"],
  "has_inherited_access": false
}
```

Row mutation flags require current mutation authority and a current target row
role inside the caller's existing management ceiling. They are not a new
permission grant. Target has_inherited_access identifies an active Profile
Owner/Admin whose explicit Workspace row does not define their full authority.
The roster contains only effective explicit assignments; it is not an invented
list of inherited WorkspaceMember records. POST/PATCH retain their old fields
and return additive row hints fail-closed without a verified serializer context;
consumers refresh the authoritative GET after a successful mutation.

**New:** `GET /member-candidates/` permits the same current Workspace managers,
including delegated Workspace Admin who cannot read the Profile governance
roster. It returns standard count/next/previous/results with each result exactly:

```json
{
  "profile_membership_id": "00000000-0000-0000-0000-000000000000",
  "display_label": "Thành viên tổng hợp",
  "profile_role": "MEMBER",
  "has_inherited_access": false
}
```

Candidates are active same-Profile memberships with an active User and no
active WorkspaceMember row. ANY active row excludes a candidate, including a
legacy unsupported role; an inactive historical row remains eligible for the
existing reactivation service. Profile Owner/Admin candidates are not silently
filtered: the existing add service permits them, and inherited access is clearly
identified. Adding an explicit lower role cannot reduce inherited authority.
Candidate membership IDs are Profile-scoped identifiers, never global User IDs.

Roster/candidate lists order by joined_at,id, default page20/max100. GET/HEAD/
OPTIONS only for candidates; session authentication/no-store remain. No email,
username, raw account ID or unrelated Profile data is projected. Display labels
use authorized names or safe membership-prefix fallback. Lazy query predicates
repeat current actor scope and lifecycle; final response revalidates authority.
Archive during candidate serialization clears count/results/links. Joined name
loading and the target Profile-role subquery avoid per-row lookups; current
PostgreSQL tests verify one evaluation query and zero serialization queries for
each prefetched roster/candidate list.

### Existing writes, unchanged

| Method/path | Exact body | Successful result / existing failure |
|---|---|---|
| POST /members/ | `{target_profile_membership_id,role}` |201 new row;200 reactivation of same inactive row;409 already-active duplicate |
| PATCH /members/{membership_id}/ | `{role}` |200; same-role no-op preserves audit history |
| DELETE /members/{membership_id}/ | No fields needed |204 soft revoke; no hard deletion |

The existing atomic services lock Profile→Workspace→actor memberships→target,
repeat current authority/role ceilings and write audit in the same transaction.
Invalid/inactive/cross-Profile body targets use generic400; visible forbidden or
archived writes403; unknown/malformed/wrong-parent/out-of-scope URL IDs404.
Client-supplied capabilities, user_id, tenant IDs or unknown fields are rejected.
Session CSRF remains mandatory for every unsafe request. Read hints can become
stale; mutation-time checks always decide. No automatic mutation retry is added.

No separate last-Workspace-Admin invariant exists. Profile managers may revoke
the final explicit Workspace ADMIN because inherited Profile governance remains;
the independent last-active-Profile-Owner invariant is unchanged. Revoking an
explicit row belonging to a Profile Owner/Admin does not remove inherited access.

Revoke only changes WorkspaceMember.is_active and audit. Tasks, TaskAssignment,
Deliverable/Review and workflow status are retained, not deleted/unassigned or
reset. A revoked ordinary member loses Workspace/Task access immediately; a
Viewer downgrade retains reads but cannot execute. Regranting Editor can make
an existing still-active TaskAssignment effective again. Task assignability
still requires active User + active Profile MEMBER + active Workspace MEMBER,
ACTIVE scopes, current manager action and valid Task state; a new Workspace grant
does not itself assign or start a Task. No Task workflow change is introduced.

React integrates the access section into the existing Workspace detail page,
with its **Thành viên / Quyền truy cập** anchor; it does not add a second
Workspace route. The API client strictly projects these DTOs and scopes cache
keys by User/Profile/Workspace/page. Forms consume server role/capability hints,
submit through the existing CSRF/session transport, abort on context changes,
invalidate roster/candidate/assignment-relevant queries after confirmed writes
and preserve drafts during ordinary same-User refresh. Owner/Admin inheritance
is explained separately from direct rows; missing Profile membership directs
authorized managers to the existing organization invitation flow.

### Current verification checkpoint

| Check actually run in this task | Result and limit |
|---|---|
| Targeted isolated backend |95/95 PASS9.634s; launcher and actual Python0 independently recorded |
| Full isolated backend, one run |863/863 PASS294.428s; launcher/actual Python0, dependency/Django/model/migration checks and owned cleanup PASS |
| Workspace access API client, mocked transport |67/67 PASS3.76s, launcher0; not real-browser evidence |
| Final WorkspaceMembers UI unit/component checks |34/34 PASS12.40s, launcher0 after semantic fieldset/CSS correction |
| Broader frontend unit/contract checkpoint |902/902 PASS51.11s before the final semantic-only fieldset/CSS reset; not claimed as a full run of the final source hash |
| TypeScript/Biome/build after final semantic markup |All exit0 |
| Real isolated Workspace access browser |4/4 PASS39.1s on first runab941585c1e94477ae8d1d951e04a374; launcher/Playwright/backend0 and owned database/resources removed |
| Real Profile Members/Invitation regression |4/4 PASS46.3s, runcfcf1c4def564696af6ca5a9c3446dd8; launcher/Playwright/backend0 and owned cleanup |
| Real Task stability regression |4/4 PASS20.3s, run9a56ad93957241c3b627f408c2e89b85; launcher/Playwright/backend0 and owned cleanup |
| Real Auth/CSRF/tenant foundation |6/6 PASS45.3s, runf5ccc4c5d8ee402fa07076269b4d6e9e; launcher/Playwright/backend0 and owned cleanup |
| Current browser aggregate |18/18 PASS on final source, all owned database/resources removed; no historical browser result substituted |
| Final development preservation |2026-11-09T08:17:28Z READ ONLY snapshot exactly matches all29-table data/schema/constraints/indexes/sequences/history/identity, excluding transient connections |

The current browser run performs Profile invitation, recipient registration/
acceptance, Editor grant, Task assignment and Start through real React against
isolated PostgreSQL. It verifies Viewer/Editor role changes preserve WORKING
status/assignment, revocation removes access/stale content and mutation/tenant/
CSRF/duplicate boundaries remain. Four viewport375/768/1440/812x375 keyboard,
focus, axe and reflow checks pass;375/1440 images were visually inspected.
Ordinary same-User focus preserves the same mounted access/Task draft nodes.
These are automated isolated checks, not manual Owner development-site writes.

Development remains36 applied migrations,4 Users,2 Sessions,1 Profile/membership/
Workspace/Task,3 AuditLogs and0 WorkspaceMember/Invitation/AI rows. Candidate
ai.0002_dispatch_governance remains UNAPPLIED with its three tables absent.
No persistent business fixture/schema/AI flag, credential, provider call or
external email change is part of this task. Exact source/cleanup/check receipts
and Owner continuation are recorded in HANDOVER; manual acceptance is still
pending. Stop at **HT-FE-WORKSPACE-MEMBERS-01 — OWNER REVIEW GATE**.

Initial backend attempt had a test import/required fixture field mismatch and
old exact response-key expectations; corrected only test setup/contract additions.
Earlier frontend fixture timing/cache metadata and semantic markup issues were
corrected without weakening authorization, assertions or lint policy. Full run
evidence and exact source chronology remain in HANDOVER. No development fixture/
migration, AI activation, external mail or deployment is authorized; manual Owner
acceptance is not claimed.

Source: [Workspace access selectors/capabilities](../backend/apps/workspace/access.py),
[serializers](../backend/apps/workspace/serializers.py),
[views](../backend/apps/workspace/views.py),
[existing membership services](../backend/apps/workspace/services.py) and
[Task assignment/execution services](../backend/apps/tasks/services.py).

## Historical completed HT-FE-MEMBERS-01 — Organization roster and Invitation React integration

Status: **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**. The Owner authorizes React
membership/invitation integration plus the smallest schema-free API gap fix.
Existing Invitation routes/business rules remain; no model/migration or
persistent development/AI flag change is part of this task. Roster/API client,
React member management and manual recipient flows are implemented. Current
regression/development preservation checks below pass. Manual Owner website
acceptance and actual external email delivery remain unverified; no further
task, migration rollout or deployment is started automatically.

### New manager-only Profile roster

`GET /api/v1/profiles/{profile_id}/members/?page=1` uses standard
`count/next/previous/results` pagination plus root `capabilities`. Default page20,
optional page_size≤100, stable joined_at/id ordering; GET/HEAD/OPTIONS only.
Active User/current same-Profile Owner/Admin membership is required. Ordinary
Profile Members, including Workspace-only managers, get403; wrong-tenant or
outsider IDs get404. Staff is not tenant authority. Responses are non-cacheable.

Each result exposes only `id` (ProfileMembership UUID), `profile_id`,
`display_label` (trimmed full name or membership-prefix fallback),
`role:OWNER|ADMIN|MEMBER`, `is_active` and `joined_at`. Inactive membership history
is manager-readable; is_active describes membership, not account sign-in state.
No email, username, global User ID, credential or unrelated tenant data appears.
The lazy queryset repeats current caller membership/role/active-account checks.

Root capabilities are `can_invite:boolean`, `can_manage_invitations:boolean`,
`allowed_invitation_roles:(MEMBER|ADMIN)[]`. Active Owner gets MEMBER/ADMIN;
active Admin gets MEMBER. Archived Profile roster stays readable with both
mutation flags false/roles[]. Existing Invitation GET remains manager-readable
and role-ceiling filtered, while archived mutations remain denied. These are
UI hints; POST services revalidate. No Profile role/removal/Owner-write API is added.

### React contract and privacy boundaries

The existing [Invitation contract](#profile-invitation-and-membership-onboarding-api)
is reused: create sends only recipient_email/requested_role; resend/revoke send
empty objects. Resend creates a NEW identity/credential; refresh the whole list.
Owner sees ADMIN/MEMBER invitations, Admin only MEMBER. Existing API client,
session/CSRF and private User+Profile+page cache scopes are reused; parsed DTOs
project only allowed fields and tokens never enter query keys or read cache.

React routes `/profiles/:profileId/members` and `/invitations/respond` provide
organization management and manual recipient code entry. The recipient page uses
existing authenticated accept/decline POSTs, not an inbox, public token preview
or fabricated email link. Login/registration return only to the fixed safe
recipient path; the code must be re-entered after authentication rather than
persisted in login state/browser storage.
Token is an exact write-only POST value (max512, no trimming), never URL/storage.
No GET performs acceptance. A new recipient may register/sign in first and
explicitly submit the code; acceptance still depends on actual unique recipient
identity and a sent, usable credential. Invalid/expired/revoked/replayed/mismatch
409 responses stay generic, without pretending to identify a particular reason.

SENT means mail-adapter acceptance, not mailbox delivery or invitation acceptance;
QUEUED/FAILED/PENDING/ACCEPTED remain distinct. Missing safe email configuration
can return503 without a row; post-commit delivery failure can return503 WITH a
durable PENDING invitation with delivery_status FAILED. Do not auto-repeat
creation or claim no row exists. **REAL
EMAIL DELIVERY NOT VERIFIED.** Locmem tests do not establish operational SMTP.

Normal same-User refresh preserves invite drafts; genuine identity/tenant/
authority loss removes private state, preserving HT-FE-STABILITY-01.

### Fresh verification available at this checkpoint

| Current check | Actual result |
|---|---|
| Members API/DTO tests |75/75 PASS3.36s |
| Targeted frontend unit/contract/components (mock transport) |142/142 PASS13.73s |
| Final full frontend unit/contract |801/801 PASS23.61s; includes the final NUL-input validation spelling |
| Targeted isolated PostgreSQL |51/51 PASS56.587s, launcher0; independent targeted Python die event unavailable, not inferred |
| Full isolated PostgreSQL |839/839 PASS245.158s, launcher and actual Python0 independently verified, owned cleanup |
| Members real Chromium |4/4 PASS38.6s, runff576a67eb2a483397844103d1eb18c8; launcher/Playwright/isolated backend0 and owned database/resources removed |
| Task-create stability regression |4/4 PASS20.9s, run3c516c63055f4dc8a47238b1120fd5c9; launcher/Playwright/isolated backend0 and owned cleanup |
| Auth/CSRF/tenant foundation |6/6 PASS36.0s, run07e121e66e6d4fd4a55542c2706761d5; launcher/Playwright/isolated backend0 and owned cleanup |
| Frontend quality | TypeScript/Biome/production build exit0 |

Members browser evidence includes a real locmem invitation, newly registered
recipient explicitly accepting through React, server membership creation,
resend/decline/revoke/recipient restrictions and responsive/axe checks. It is
isolated mail-backend delivery, not operational external email delivery. All
three current Chromium suites total14/14 PASS. Four-viewport reflow/keyboard/axe
checks pass; root visually inspected375/1440 screenshots. The14:48:54Z READ ONLY
development comparison exactly preserves all29 tables' row/schema/index/sequence/
history/cluster fingerprints (connections excluded):36 migrations/4 Users/
2 Sessions/1 Profile/membership/Workspace/Task/3 AuditLogs/0 Invitation/AI rows.
Candidate ai.0002 remains UNAPPLIED and its tables absent. No new schema,
persistent test fixture, credential/flag change or live provider request occurs.
Historical689/21/826 counts below remain historical, not substituted for this
task's fresh results. Stop at **HT-FE-MEMBERS-01 — OWNER REVIEW GATE**.

## HT-AI-P4-04C — Internal durable governance; no new HTTP API

Status: **HT-AI-P4-04C — OFFLINE GOVERNANCE IMPLEMENTATION READY /
DEVELOPMENT MIGRATION PENDING**. The Owner now
authorizes additive governance persistence and offline services, with candidate
`ai.0002_dispatch_governance` tested only on isolated PostgreSQL. No development
migration, live OpenAI request, customer-data transfer or browser contract change
is authorized. Existing Generator/Analyzer URLs and fixture DTOs remain unchanged.

[governance.py](../backend/apps/ai/governance.py) adds internal server-callable
`execute_generator`, `execute_feedback`, `reserve_dispatch`, `get_dispatch`,
`begin_dispatch`, `fail_before_dispatch`, `mark_unknown` and `reconcile_dispatch`.
There is no DRF endpoint or client-supplied policy/provider/model/bucket override.
Current actor/tenant manager authority and original dispatch actor are checked
using existing access services; dispatch UUID knowledge is never authority.
All table-using paths fail closed before querying unapplied tables unless
AI_GOVERNANCE_ENABLED is explicitly True, policy.enabled is True, execution mode
is OPENAI_OFFLINE and existing fixture development/nonproduction guards pass.
No new flag is enabled, and no live-mode transport is connected.

The offline wrappers validate the brief or resolve selected actual Review/Comment
sources through existing Django access code, then bind scope/input/policy to a
purpose-specific keyed HMAC. Raw brief, source text, focus, evidence and provider
response bodies are not stored in dispatch/reservation/accounting records or
conflict errors. Sources are rechecked around fake execution. Policy HMAC
prevents same-version provider/rate/token-bound drift; locked budget rows
separately reject changes to budget version, cost/request/inflight limits.

One transaction reserves the stable GLOBAL/Profile/User budget lanes and scoped
dispatch identity before transport. A short committed RESERVED→DISPATCHING claim
selects one caller; fake transport runs outside database transactions. Equivalent
concurrent requests reuse metadata without another invocation; changed input or
configuration conflicts. Lifetime request/cost/in-flight counters do not reset
at midnight, and OUTCOME_UNKNOWN holds remain until explicit reconciliation.

Internal DispatchExecution contains an authorized DispatchReceipt and, only for
the successful first execution, a transient ProviderResult. Replays return the
receipt with result=None: no generated body/history is persisted or reconstructed.
The wrappers do not create AiProposal/AiOperation or business records. This is
governance verification, not a replacement for Generator preview/confirmation
or a complete live application API. Existing explicit Confirm remains unchanged.

Receipt provenance includes provider/model/execution_mode, usage_status,
reserved/estimated/accounted/billed amounts and nullable tokens, with
generated_by_ai=False in this offline slice. Estimated/simulated accounting is
not a provider invoice; billed_cost stays NULL. API-safe errors remain static.
Failures after a committed claim preserve DISPATCHING/OUTCOME_UNKNOWN and holds,
including persistence failure after a possible provider success. No blind retry,
automatic expiry refund or silent fixture fallback is introduced.

Reconciliation requires the original actor to retain current manager access,
the original full policy and simulated evidence. The evidence/amount/token HMAC
is idempotent; a changed reconciliation body conflicts. Revoked access or database
failure can leave a hold unresolved; no new operator role/bypass is invented.
It does not establish actual billing, a shared production spending guarantee or
permission to dispatch live requests. Current tests/exit codes and candidate
rollout state are recorded in [HANDOVER](HANDOVER.md); manual website acceptance
and any future versioned live React/API contract remain separately pending.

Current-source verification: focused52/52 PASS15.286 seconds and full isolated
PostgreSQL826/826 PASS231.558 seconds; both launcher/actual Python exits0,
required checks and owned cleanup verified. Parallel real PostgreSQL connections
exercise cross-worker claim/budget behavior, while fake transport avoids model
requests. Final development29-table row/schema/sequence/history/cluster snapshot
matches preflight exactly, still36 migrations/4 Users and candidate0002 unapplied.
No new HTTP/browser acceptance or live-billing guarantee follows from these tests.
PROTECT reverse relations can affect arbitrary parent hard-delete/AdminCollector
before rollout; existing gated authorized app paths are preserved, not every
possible unmigrated ORM maintenance operation. Do not delete data to bypass it.

## HT-AI-P4-04B — Internal offline OpenAI adapter; HTTP contracts unchanged

Current status: **OFFLINE OPENAI ADAPTER COMPLETE — OWNER REVIEW GATE**.
OpenAI `gpt-5.4-mini`, Responses API and strict JSON Schema are Owner-approved
implementation targets for an injected fake/in-memory transport only. The new
adapter is internal to the existing StructuredProvider boundary. It does not
add an endpoint, modify Generator/Analyzer dispatch, change permissions, enable
live settings or accept provider/model/key overrides from a browser.

The implementation is [openai_adapter.py](../backend/apps/ai/openai_adapter.py):
`OpenAIResponsesAdapter.generate(ProviderRequest, RequestControl)` implements the
existing port. `OpenAIConfig` defaults to `enabled:false`, model `gpt-5.4-mini`,
30-second timeout,4096 maximum output tokens and128KiB response-envelope cap.
Code-owned bounds permit timeout up to120 seconds, output up to32768 tokens and
envelope up to1MiB; outbound request cap is64KiB and existing domain output cap
remains64KiB. These are offline adapter safeguards, not approved live quotas or
spending limits. Only an explicitly injected `OfflineTransport` marked `offline`
literally True can execute; no concrete network transport, API-key parameter,
environment loader or default transport exists.

The internal request mapping targets POST `https://api.openai.com/v1/responses`
through that fake seam, nonstreaming inference, `store:false`, explicit model/
output bounds, strict `text.format` JSON Schema and no tools.
User briefs/focus/selected feedback are data, not privileged instructions. Parsed
output must still pass existing TaskPlan/FeedbackAnalysis validators. Requests
and responses used during this task are invented offline data; no real provider
network transport or credential is required or activated.

Existing public Generator and Analyzer envelopes below remain fixture-only:
`mode:fixture_demo`, `generated_by_ai:false` and exact fixture usage. Do not feed
an offline mocked response into that contract as live output or fabricate actual
usage. Its internal ProviderResult uses `provider:"openai_offline"` and
usage status `offline_simulated`; token counts from fake responses stay explicitly
simulated, missing counts remain unknown and cost is None rather than fabricated
zero or an actual bill. This is not a public API response discriminator.
Current AiProposal/AiOperation records and confirmation/replay semantics
remain unchanged. A future live API needs explicit provenance/usage/lifecycle and
availability design, compatible React parsing and approved cost controls before
activation. [AI_PERSISTENCE_REVIEW](AI_PERSISTENCE_REVIEW.md) proposes the schema
boundary; no migration or live DTO branch is implemented here.

SessionAuthentication, CSRF, nested tenant/manager authorization, server-resolved
feedback/citations and explicit human confirmation remain authoritative. There
is no browser-to-OpenAI route or direct provider mutation authority. Current
adapter/test evidence belongs in [HANDOVER](HANDOVER.md); previous full/fixture
test counts stay historical. Manual website acceptance remains PENDING.

The parser requires a completed Responses envelope and one assistant structured
text message; approved model alias or its documented snapshot must match current
configuration. Refusals, incomplete output, tool calls, malformed/bounded JSON
and invalid domain values fail closed. Provider401/403 map to static
PROVIDER_UNAVAILABLE rather than a caller/tenant PERMISSION_DENIED,
429 to RATE_LIMITED, timeout to PROVIDER_TIMEOUT and transport/unavailable errors
to static safe categories. Raw response bodies, exception causes and credentials
are not exposed. Effective fake timeout is bounded by RequestControl's remaining
deadline, with checks before/after dispatch; no automatic retry/fallback exists.
Cooperative cancellation cannot promise interruption or reversal of future
remote computation or charges, and `store:false` does not imply zero retention.

Current focused adapter55/55 PASS0.038 seconds and apps.ai270/270 PASS13.347
seconds verify the offline implementation and existing fixture regressions;
both launcher/actual Python exits are0. Dependency/Django/migration-chain checks
and owned cleanup pass. Existing public endpoints/business services are not
rewired. No real OpenAI request, actual usage/billing, live error behavior or
customer-data transfer is verified/authorized by these fake-transport tests.
Current evidence and final development/source preservation are in HANDOVER.

## HT-AI-P4-04A — Provider readiness; implemented API unchanged

Status: **DESIGN READY / PROVIDER IMPLEMENTATION BLOCKED — OWNER REVIEW GATE**.
Source audit finds no approved live provider/model or live API selector. This
task does not add an endpoint, request field, response discriminator, runtime
flag, permission or migration. The current fixture contracts below remain the
canonical implemented API; [HANDOVER](HANDOVER.md) records current verification.
See the proposed next boundaries in
[AI architecture](AI_ARCHITECTURE_DESIGN.md#ht-ai-p4-04a--live-provider-readiness-2026-11-08).

Both existing React parsers explicitly require `mode:"fixture_demo"`,
`generated_by_ai:false` and exact zero fixture usage. Generator responses are
durable synthetic proposals; Analyzer responses use `persisted:false` and have
no proposal/operation/history/confirm semantics. An arbitrary provider response
must not be inserted into these envelopes or mislabeled as synthetic/zero cost.
Future live provenance/usage and availability require an explicit compatible
versioned contract and frontend parsing/UI changes in a separately approved
implementation. Client-supplied provider/model/roles or tenant overrides remain
prohibited; fixture availability metadata is not a live activation switch.

Existing SessionAuthentication/CSRF, current manager/tenant checks, strict
TaskPlan/citation validation and explicit human confirmation stay authoritative.
Generator's same-key confirmation prevents duplicate committed Tasks; it does
not prove paid-call deduplication before a proposal exists. Analyzer remains
read-only/stateless. No external provider call, fallback simulation presented as
live output or backend domain mutation is introduced by P4-04A. Historical test
counts below are labeled by their original task, not current readiness tests.

## HT-AI-P4-03C — React consumption of the existing Analyzer contract

Current status: **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**.
No Analyzer endpoint, request/response schema, permission or persistence changed.
Existing
Task-scoped Deliverable GET responses expose a singular nullable `review`
object with its ID/comment; Comment GET exposes nondeleted content/ID and
tombstone state. These are sufficient for authorized source selection.

React POSTs only selected `review`/`comment` UUID references and optional
focus to the existing endpoint below, using the single session/CSRF client.
Fixture availability can be read through the existing permission-checked
Generator OPTIONS metadata because both slices share the same backend guard;
this grants no Task/source authority. No idempotency header, new route, result
history or apply/confirmation contract is added. Current integration/test proof
belongs in [HANDOVER](HANDOVER.md); historical P4-03A evidence stays separate.
Current frontend675/675 and all real isolated browser suites36/36 pass, including
Analyzer5/5 and disabled Analyzer1/1 with real session/CSRF/tenant checks.
All-model counts/fingerprints remain unchanged by Analyze. Current isolated
backend AI215/215 PASS16.494s has verified launcher/actual Python exit0; no backend
code changed and full719 remains historical. The UI refreshes selected source
pages through existing tracked queries; cancelled/reverted reads cannot restore
redacted Comment content or count as fresh source validation. These protections
do not add a realtime server-revocation or serializable-read guarantee.

## HT-AI-P4-03A — DESIGN AND FIXTURE BACKEND COMPLETE / OWNER REVIEW GATE

The Owner delegates a bounded backend foundation after domain/security audit.
The scoped fixture backend is implemented and verified; this does not complete
the full Analyzer product. See [foundation design](FEEDBACK_ANALYZER_FOUNDATION.md) and
[HANDOVER](HANDOVER.md) for current evidence. No frontend, live provider,
AiProposal/AiOperation persistence, model/migration or development flag change.

`POST /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/ai/feedback-analysis/`
(`ai:feedback-analyze`) uses current SessionAuthentication/CSRF and active
`can_manage_workspace_tasks` authority (currently also the internal-review role
predicate). Profile Owner/Admin, or Profile Member with effective Workspace
ADMIN, are eligible; Editor/Viewer or staff without real membership are not.

Request accepts exactly `sources:[{kind,id}]` (1–20 unique pairs, kind `review`
or `comment`, UUID strings) and optional `focus` text≤1000 valid Unicode/NUL-free.
The server resolves only selected Review.comment or nondeleted TaskComment.content
within this exact Task scope and maps input order to S1…Sn. Wrong-parent,
cross-tenant, missing/deleted/null-or-blank sources are unavailable. Total selected
text≤12000 characters, request≤32KiB, provider response≤64KiB. No raw feedback,
actor, role, mode, provider/model, tenant override, file URL or mutation fields.

Success200 is an `ai.v1` envelope: `status:READY`, `mode:fixture_demo`,
`generated_by_ai:false`, `persisted:false`, `fixture_version:fixture.v1`,
`sources:[{ref,kind,id}]`, `payload` using the existing strict `ai.feedback.v1`
summary/issues/suggested_actions/uncertainty/warnings schema, and zero fixture
usage. There is no source text, author PII, URL, proposal/expiry/created-Task
mapping or confirm/apply action. Fixed subtitle-contrast suggestions do not
interpret selected feedback or focus, and never imply video/audio processing.
The fixed example cites only the first selected source; citations are validated
references, not proof that content was semantically read or media processed.

The existing fixture/environment guard and shared per-user3/minute +20/day
process-cache attempt limits are reused. OPTIONS is exempt; existing Generator
limits remain. No persistent feature flag is enabled. Before/after authorization
and selected-source re-query reject drift; no stale saved-analysis replay exists.
These are optimistic checks, not a serializable transaction/locking or real-time
revocation guarantee. They cannot retract delivered responses or prevent a source
or authority change after the final read. Current process-local cache quotas are
not a shared multi-worker production budget.
The operation writes no business/AI/Audit/Notification rows. Repeated calls
recompute and reauthorize; no durable Idempotency-Key protocol is required or
promised for this zero-cost/stateless fixture. Generator idempotency is unchanged.

Errors follow existing safe transport conventions:400 invalid input,403 current
auth/CSRF/permission denial as applicable,404 unavailable nested object/source,
409 stale context,429 throttling,503 disabled/unavailable fixture,502 invalid
output,504 timeout. Responses must be non-cacheable and must not echo raw input,
unknown field names or internal exceptions. Current isolated PostgreSQL AI215/215
PASS15.272s includes43 new Analyzer tests; full719/719 PASS217.696s. Actual
launcher/Python exits0 and owned cleanup are verified; dependency/Django/model/
migration checks pass. Final read-only29-table development preservation is exact
with36 migrations/3 Users/2 Sessions/1 Profile/membership/Workspace/Task and0
Reviews/Comments/AI rows. No frontend/browser/live tests were run for P4-03A;
the P4-02C results below remain historical. Manual Owner FE05/P4-02C acceptance
and live/private-provider/data-policy decisions remain pending, not blockers for
this verified local fixture slice.

## HT-AI-P4-02C — fixture Generator integration / IMPLEMENTATION COMPLETE

The Owner approves the React preview/edit/confirm integration and a bounded
optional synthetic brief. The current contract below supersedes the original
scenario-only HTTP restriction; legacy requests without `brief` remain compatible.
This is deterministic demo data, not analysis by an AI model. No live adapter,
provider key, schema change or persistent development flag enablement is included.

The existing API client now accepts a UUID-only `Idempotency-Key` only for the
scoped AI POST routes. It retains allowlisted AI error codes for safe UI handling;
it does not expose arbitrary headers, provider errors or a parallel auth client.
React validates strict response shape/provenance/lifecycle/size before preview.
Current verification: targeted AI172/172 and full isolated PostgreSQL676/676
PASS, frontend537/537 PASS, typecheck/Biome/build PASS. All eight real isolated
Chromium suites30/30 PASS: Generator enabled4, disabled1, onboarding3,
foundation6, Workspace/Task7, collaboration7, whole workflow1 and account1.
Actual launcher/Python/Playwright/backend exits0 and owned cleanup are verified.
Development preservation and45 protected source hashes match the pre-task
baseline. See [HANDOVER.md](HANDOVER.md) for evidence and the **OWNER REVIEW
GATE**. No live-provider/manual development proof is implied by these results;
no next implementation or persistent feature enablement starts automatically.

### Permission-checked availability

`OPTIONS` on the generation base path retains standard DRF metadata and `Allow`,
and adds `ai` with the following shape:

```json
{
  "contract_version": "ai.v1",
  "enabled": false,
  "mode": "fixture_demo",
  "generated_by_ai": false,
  "scenarios": [
    {"id": "subtitle-check-v1", "label": "Kiểm tra phụ đề — mẫu giả lập", "brief": "Ví dụ synthetic kiểm tra phụ đề."},
    {"id": "task-tree-v1", "label": "Task và Subtask — mẫu giả lập", "brief": "Ví dụ synthetic Task và Subtask."}
  ],
  "limits": {"max_brief_chars": 6000, "max_tasks": 20, "max_depth": 3, "max_request_bytes": 32768}
}
```

`enabled` is calculated from the existing fixture/environment guards. Scenario
briefs are public synthetic examples, not stored User input. Existing tenant and
manager checks run first. OPTIONS creates no proposal/business rows, invokes no
fixture and consumes no generation quota. It grants no mutation authority.
POST generation retains the existing 3/minute and 20/day approximate limits.

### React confirmation boundary

The protected route is
`/profiles/:profileId/workspaces/:workspaceId/tasks/generate?proposal=<UUID>`.
The optional query ID retrieves only the currently authorized original actor's
proposal. Local edits support title, description, priority and deadline; parent
structure stays fixed in this UI. No PATCH/draft-save endpoint is introduced.
The full edited plan is frozen for an explicit confirmation dialog, then sent
through the existing atomic confirmation service. Only the server response can
show successful creation; the client never falls back to ordinary Task POSTs.

A lost generation reply can be recovered by an explicit identical key/body
replay. After ambiguous confirmation, the UI first reads the known proposal ID.
It never automatically confirms with a fresh key; a manual identical frozen
retry is available only after GET reports AVAILABLE for the same proposal ID
and revision as the frozen body. A stale/mismatched proposal discards that
confirmation and requires fresh human review; it is never silently retargeted.
A confirmed result links to
the returned Task UUIDs. Unresolved/expired recovery advises checking Tasks
rather than asserting that no Tasks were created. AI query keys include current
User/Profile/Workspace; exit/identity change aborts requests and removes that
scope. No brief, draft, key or session secret is stored in localStorage.

The historical FE05 and R3 results below are not P4-02C test evidence.

## HT-FE-P3-05 — Profile creation / IMPLEMENTATION COMPLETE — OWNER REVIEW GATE

The Owner-approved onboarding slice adds **POST /api/v1/profiles/** on the
existing collection route. It requires a current active authenticated User and
valid session CSRF, with no AllowAny or staff shortcut. It accepts exactly:

```json
{"name": "Nhóm sáng tạo"}
```

Name must be text, trimmed, nonblank and at most255 Unicode characters; null,
nontext, NUL, invalid Unicode and unknown fields are rejected with400. Do not
send owner/user/membership IDs, role, status, tenant ID, timestamps or description.
The creator comes only from request.user. Existing create_profile_with_owner
atomically persists ACTIVE Profile + active OWNER membership + safe membership
audit; failure rolls back all three. No invitation is required to create a new
tenant, and this grants no access to any existing tenant.

Success201 returns the existing Profile DTO: id,name,status,created_at,updated_at.
It contains no global User ID or private membership details. The new Profile is
immediately visible to its creator through existing list/detail routes; unrelated
Users still receive scoped404. GET pagination and current Profile read shape are
unchanged; collection methods are GET/POST/HEAD/OPTIONS. Detail PATCH/PUT/delete
remain unsupported except existing explicit lifecycle actions.

Names are not globally unique under the existing domain. Separate valid POSTs,
including concurrent/repeated names, create distinct Profiles with one correct
initial membership each. This endpoint adds no idempotency key/deduplication
protocol. React prevents rapid duplicate submits and does not automatically
retry mutation; after an ambiguous network outcome, inspect the Profile list
before intentionally submitting another creation.

Targeted isolated PostgreSQL40/40 PASS1.577s/full662/662 PASS245.938s,
launcher/Python exits0 and cleanup verified. Frontend426/426, typecheck/lint/build
and all six real isolated browser suites25/25 passed; every launcher/Playwright/
backend exit0 and owned cleanup verified. Final development row fingerprints,
schema, sequences and history are exact:36 migrations/ai.0001 applied,
3 Users/2 Sessions/business0/AI0;52 model/migration/AI hashes and19 tested
changed-file hashes stable. No persistent development fixture or migration was
run for this slice. AI schema/feature flags/contracts unchanged. Historical
643/395/22 are separate results; manual Owner website acceptance is pending.

## HT-AI-P4-02B-R3 — DEVELOPMENT SCHEMA APPLIED / API CONTRACT UNCHANGED

The Owner-approved exact development `ai.0001_initial` rollout completed once,
actual child exit0 on2026-11-02. Development now has both AI tables and36 applied
migrations; original User/Session/business rows are preserved and AI rows remain0.
Current system/model/graph/history/showmigrations/migrate-check checks pass.
Actual HTTP on a task-owned loopback Django WSGI listener passed8 GET requests:
health200, CSRF bootstrap200, and anonymous403 for me/Profiles/Notifications and
the three AI routes. No authenticated success, POST/generate/confirm, fixture or
business mutation was tested on persistent development; those flows retain their
isolated historical test evidence below. Listener cleanup passed.

This rollout changes no endpoint, request/response contract, RBAC or workflow.
Fixture flag remains false; no live adapter/provider call, frontend AI, SDK/key
or production action. Environment values were privately loaded through the
existing repository mechanism for child processes only, never printed or changed.
See [HANDOVER.md](HANDOVER.md) and
[AI_DEVELOPMENT_MIGRATION_READINESS.md](AI_DEVELOPMENT_MIGRATION_READINESS.md).
Stop at OWNER REVIEW GATE; no further implementation is authorized here.

## Historical P4-02B implementation verification — 2026-10-28

The bounded fixture-only API below is verified on isolated PostgreSQL. Stop at
OWNER REVIEW GATE; this completion does not authorize development rollout or a
new task. No live AI provider, SDK, API key, provider network call, Analyzer
endpoint or React AI UI is implemented by this slice.

Final-source evidence on 2026-10-28: AI **158/158 PASS** in11.208s
(`bf34f0b7fd384c7a9958b4513cea18ac`); Task/Review/Workspace/RBAC **378/378 PASS**
in165.639s (`d41c6561e93f4b6489e0a858d87a75de`); full isolated backend
**643/643 PASS** in215.115s (`6bdba3440f8d46edb28df73a9b30fe03`). Actual launcher
and Python PID1/container exit codes are0; owned test database/container/network
cleanup, pip/Django/model-drift/migration graph and full-chain checks pass.
At that implementation checkpoint, read-only development verification found
35 migrations, 3 Users, 2 Sessions and 0 business rows; AI tables were absent
and ai.0001 was not applied there. No private .env was read in that earlier
task. R3's later applied state and loader usage are recorded above and in
[HANDOVER.md](HANDOVER.md). Historical FE04/API03A results below remain separate
from that implementation verification.

### Current fixture API access, configuration and methods

- The installed AI app adds `ai.0001_initial` for `AiProposal` and `AiOperation`.
  R3 separately applied this exact schema on development after recovery/safety
  gates. Further migrations, mutation tests on persistent development, feature
  enablement and production rollout still require appropriate separate approval.
- `DJANGO_AI_FIXTURE_ENABLED` defaults to `false`. Explicit opt-in only works
  when `DJANGO_ENVIRONMENT=development` and production mode is false. Production
  always refuses fixture execution; disabled processing returns `503
  AI_DISABLED` after authentication/tenant permission checks.
- All three routes use existing Django `SessionAuthentication`; authenticated
  unsafe requests require a valid CSRF token. No `AllowAny`, JWT, frontend key
  or alternate tenant permission engine is introduced.
- Every generate/read/confirm/recovery requires a currently active User,
  current same-Profile membership and the existing
  `can_manage_workspace_tasks` capability: Profile Owner/Admin, or Profile Member
  with an active Workspace Admin membership. Editor/Viewer and staff/superuser
  flags alone grant no authority. Archived Profile/Workspace is refused.
- Read, confirm and replay additionally require the original proposal actor.
  Another manager cannot view or confirm that actor's proposal. Revoked or
  cross-tenant callers cannot recover payloads or created Task IDs; unknown,
  malformed or unscoped proposal IDs use tenant-safe `404` behavior.
- Responses are `never_cache`. JSON request bodies are capped at **32 KiB**
  before parsing; duplicate JSON keys, non-finite numbers, invalid UTF-8, unknown
  fields and invalid types are rejected. Unsupported content types return
  `415`; unsupported methods return `405` after applicable access checks.

Base path: `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/ai/task-proposals/`.

| Method | Suffix | Purpose | Success |
|---|---|---|---|
| `OPTIONS` | base path | Existing manager-checked metadata plus fixture availability/scenarios/limits; no generation attempt | `200` |
| `POST` | base path | Generate/store a deterministic synthetic proposal; creates no Task | `201` first result; `200` same-key/body replay |
| `GET` | `{proposal_id}/` | Read current actor's proposal or recover committed confirmation result | `200` |
| `POST` | `{proposal_id}/confirm/` | Explicitly confirm an edited plan through existing Task services | `201` first commit; `200` same-key/body replay |

Detail also permits `HEAD`; all routes permit permission-checked `OPTIONS`.
There is no proposal list/edit/delete API or separate recovery endpoint: recovery
uses the scoped detail `GET` or the identical successful confirmation replay.

### Generate request

Both POST routes require `Content-Type: application/json`, existing session/CSRF
handling and a valid UUID in the `Idempotency-Key` header. Clients should retain
the key for retries of the same operation. Generate accepts required `scenario_id`
and optional `brief`; no other request fields are accepted. Example:

```json
{"scenario_id": "task-tree-v1", "brief": "Yêu cầu giả lập: kiểm tra phụ đề cho video demo."}
```

Allowed server-owned scenarios are `subtitle-check-v1` (one root suggestion) and
`task-tree-v1` (a root plus child suggestion). If present, `brief` must be a
nonblank text value of at most 6,000 Unicode characters, without NUL or invalid
Unicode. It is synthetic-only by Owner policy; validation does not automatically
classify/redact real or confidential data. No provider/model override, foreign
tenant ID or client-defined scenario content is accepted. Omitting `brief` uses
the existing server example and preserves legacy scenario-only canonicalization.

When present, the validated brief is bound into the keyed canonical-body digest:
same key/brief replays, changed brief under that key conflicts. Raw input is not
stored in a model, echoed in the response or copied into AuditLog/log messages.
The fixture remains predetermined by scenario and does not analyze the brief.
The disclosure is **Demo fixture cố định, không có model AI xử lý brief.**

Generate attempts use DRF UserRateThrottle limits of **3 per rolling minute**
and **20 per rolling day** per User, shared across that User's scopes in the same
cache. Attempts, including replays that reach throttling, count toward those
limits. The current cache is process-local and throttle updates are non-atomic:
these are approximate single-process protections, not shared multi-worker quotas
or a production-grade budget ledger. Detail/confirm have no new dedicated AI
throttle. Live API budget and fixture provider cost are both zero; no paid
fallback is possible.

### Proposal response and confirmation body

The same response shape is returned from generate, detail and confirm:

- `contract_version`: `ai.v1`; `proposal_id`: server UUID; `revision`: positive
  proposal revision; `scenario_id`: allowed scenario.
- `status`: `AVAILABLE`, derived `EXPIRED`, or durable `CONFIRMED`.
- `mode`: `fixture_demo`; `generated_by_ai`: `false`; `persisted`: `true`.
- UTC-aware `created_at`, `expires_at`, `payload_expires_at`, nullable
  `confirmed_at` and nullable `recovery_expires_at`.
- `payload`: the validated Task-plan object while available, otherwise `null`.
- `created_tasks`: `null` before confirmation; after commit a stable object
  mapping proposal-local references such as `item_1` to backend-created Task UUIDs.
- `usage`: `input_tokens=0`, `billable_output_tokens=0`,
  `cost_usd="0.000000"`, `status="fixture_zero"`.

No global User ID, email, membership ID, raw brief, idempotency-key digest or
request-body fingerprint is returned. The explicit fixture provenance must be
shown as demo/not live AI by the P4-02C frontend consumer.

Confirmation accepts exactly `proposal_revision`, literal JSON `confirmed: true`
and the complete edited `payload`. Example synthetic plan:

```json
{
  "proposal_revision": 1,
  "confirmed": true,
  "payload": {
    "contract_version": "ai.task-plan.v1",
    "tasks": [{
      "local_ref": "item_1",
      "parent_ref": null,
      "title": "Synthetic subtitle check",
      "description": "Review the demo captions before submission.",
      "priority": "MEDIUM",
      "proposed_deadline": null,
      "notes": "Demo suggestion requiring human confirmation."
    }],
    "assumptions": [],
    "warnings": ["Synthetic fixture; not generated by a live AI provider."]
  }
}
```

The existing strict Task-plan parser validates **1–20 nodes**, unique local
references (`item_1` etc.), no missing parent/cycle/self-parent, root depth0 and
at most3 child edges. Priority is `LOW|MEDIUM|HIGH|URGENT`. Each node requires
exactly the shown fields; title is nonblank and at most255 characters,
description at most2,000 and notes at most500. Deadline is nullable or an explicit
timezone-aware RFC3339-style datetime normalized to UTC; no guessed deadline.
Unknown fields, NUL/invalid Unicode, assignment, status, tenant IDs, foreign Task
parents and `estimated_duration` are rejected. `notes`, `assumptions` and warnings
support preview; they are not invented Task model fields.

Human edits stay within this same validated contract. Confirm reauthorizes under
existing tenant locks, validates revision/expiry and creates topologically through
unchanged `create_task`. All accepted Tasks begin `PENDING` with the current actor
as creator and no automatic assignment. Task/Subtask/Deliverable/Review behavior
and hierarchy rules remain unchanged. All nodes, existing task-created audits,
safe AI metadata audit, consumed proposal state, result mapping and confirmation
operation commit in one transaction; any failure rolls back the whole batch.
Generate stores only proposal/operation rows, never Tasks or AuditLog rows before
human confirmation. The fixture adapter is invoked outside the service's database
transactions and is not called during confirmation. Neither flow logs content.

### Expiry, replay and retention

- Preview confirmation eligibility ends **30 minutes after generation**.
  An expired unconfirmed detail returns `status=EXPIRED`, `payload=null` and no
  created IDs; it cannot be confirmed. Replaying expired unconfirmed generation
  is refused rather than generating new state under the old key.
- Unconfirmed payload has a **7-day logical retention bound**; it is already
  hidden on reads after preview expiry. Confirmation immediately clears stored
  proposal payload; accepted content lives in the created Tasks.
- Committed result recovery lasts **30 days after confirmation**, requires
  current authorization and returns the immutable mapping, even after the
  original preview expires. After that bound or result scrubbing, recovery is
  refused with `410 RECOVERY_EXPIRED`.
- Scoped key uniqueness is actor/Profile/Workspace/operation/key. Same key with
  the same canonical body replays; a different body or proposal under that key
  conflicts. Another key cannot reconfirm a consumed proposal. Confirmation
  canonicalization includes target proposal, revision, scenario and edited plan;
  body fingerprints are keyed server-side and never exposed as permission tokens.
- Durable `CONFIRMED` is independent of payload/result scrubbing, so scrubbing
  does not reopen creation. There is **no automatic physical purge** in this
  slice: 7/30-day physical retention maxima are **not automatically enforced**.
  Logical masking/expiry is not a claim that database bytes have been deleted.

### Errors and downstream UI states

AI-domain errors use `{detail, code, fields}`, where `fields` contains only
documented safe field names mapped to static messages. Existing DRF serializer,
parse, permission, CSRF and throttle errors keep their standard response shapes;
consumers must not assume every error carries an AI `code`.

| HTTP | Behavior |
|---|---|
| `400` | Invalid/missing header, request shape/type, malformed/oversized JSON or invalid edited plan; AI validation may use `VALIDATION_ERROR` |
| `403` | Anonymous/session/CSRF or insufficient current management authority according to existing conventions |
| `404` | Missing/unreadable tenant chain, proposal or another actor's proposal; no existence disclosure |
| `409` | `IDEMPOTENCY_CONFLICT`, `ALREADY_CONFIRMED`, `STALE_PROPOSAL` (or supported `STALE_CONTEXT`) |
| `410` | `EXPIRED` confirmation/generate replay; `RECOVERY_EXPIRED` committed recovery |
| `429` | Generation attempt throttle; no claim of a shared budget ledger |
| `503` | `AI_DISABLED`; future-safe `PROVIDER_UNAVAILABLE` mapping does not mean a live adapter exists |

The transport also reserves `502 INVALID_PROVIDER_RESPONSE` and
`504 PROVIDER_TIMEOUT` for safe adapter failures. Current fixtures use no live
provider. The P4-02C consumer handles loading/preview/edit/confirm,
expired/conflict/already-confirmed/denied states without optimistic creation.

Schema/locking rationale: [AI02B_SCHEMA_REVIEW.md](AI02B_SCHEMA_REVIEW.md).
Fixture-only approval and future gates: [DECISION_LOG.md](DECISION_LOG.md) and
[AI_PERSISTENCE_REVIEW.md](AI_PERSISTENCE_REVIEW.md). The existing development
schema was applied by R3; P4-02C authorizes fixture UI only. Live providers,
persistent feature enablement and Analyzer runtime remain separately gated.

## HT-FE-P3-04 account lifecycle consumer — COMPLETE / OWNER REVIEW GATE

Frontend now consumes existing register, email-verification and password-reset
contracts below; no backend endpoint, serializer, permission, model, migration
or service rule changed. Public SPA /register has no automatic login or tenant
membership. /forgot-password preserves the neutral reset-request message;
/reset-password sends token/new_password/new_password_confirm, expects204 and
requires explicit login afterward. Protected /account uses current /me identity,
empty verification-request body and token-only verification confirmation.

All unsafe requests reuse the existing same-origin SessionAuthentication/CSRF
client. Passwords/tokens remain masked form memory and request bodies only,
never query strings, browser storage or logs. Current email_verified is refreshed
from the backend; request acceptance is not verification. Console delivery is
intentionally unavailable for security mail; neutral reset202 does not prove
delivery. Real email remains unverified; isolated tests use the locmem adapter.

Owner keeps Invitation UI, Profile Creation, membership candidate/onboarding
outside current scope and pending review. No guessed tenant IDs, fake endpoint,
new role or authentication mechanism is introduced. Current frontend395/395/
typecheck/lint/build and all five real isolated browser suites22/22 PASS, including
cohesive Task1/1, account-security1/1, collaboration7/7, work7/7 and foundation6/6.
Actual native launcher/Playwright/backend exits0 and owned cleanup are verified.
Local non-mutating smoke and read-only DB connection also pass. Backend485/485
is historical, not rerun: backend/schema/config remain unchanged. Manual Owner
browser, real email, remote CI and production remain unverified. Final evidence
is in HANDOVER.md; stop at Owner review without starting another task.

## HT-API-FE-P3-03A — Collaboration mutation capabilities

Five additive read-only booleans on existing authenticated responses resolve the
FE03 consumer gaps. Existing methods, status codes, fields, pagination and locked
mutation services stay authoritative. No new endpoint/schema/migration or role.

| Response | Field | True when |
|---|---|---|
| Task list/detail/subtasks/mutation | can_submit | Authenticated current active Editor assigned via TaskAssignment.user; ACTIVE Profile/Workspace, WORKING and no unresolved PENDING/SUBMITTED Deliverable |
| Deliverable list/submit/review mutation | can_approve | Current reviewer/manager, ACTIVE scopes, Task REVIEW, Deliverable SUBMITTED, latest by created_at DESC then id DESC, uploader differs from actor, no existing Review row of any status |
| Same Deliverable responses | can_request_changes | Same authority/state predicate as can_approve; nonblank feedback is additionally required by the write serializer |
| Comment list/detail/create/update | can_edit | Current capable commenter in ACTIVE scopes, nondeleted Comment authored by the authenticated User |
| Same Comment responses | can_delete | Current capable commenter in ACTIVE scopes, nondeleted Comment authored by that User or current manager moderation authority |

Flags require request identity matching the verified Workspace access context and
the object's scope. Missing/mismatched context fails closed. Current memberships
and lifecycle predicates reuse existing access services. No client actor ID or
display name/email inference, no extra global User ID/PII. Tombstones have null
content and both flags false; existing repeat DELETE remains idempotent.
List query annotations/prefetch keep capability queries bounded.

Existing writes, all SessionAuthentication + CSRF:

- POST tasks/{t}/deliverables/: {file_url}, valid HTTP(S), trimmed nonblank max500,
  response201. The current HT-FE-TASK-UX-REFINEMENT-01 policy above supersedes the
  original text/URL input policy; legacy reads remain intact. This is not an
  upload. Revision and Task REVIEW come from the existing service.
- POST tasks/{t}/deliverables/{d}/approve/: optional {comment}, response200.
- POST tasks/{t}/deliverables/{d}/request-changes/: required nonblank {comment},
  response200. Backend returns Task to WORKING; approval sets COMPLETED.
- PATCH tasks/{t}/comments/{c}/: {content}, response200; DELETE same URL:204.
  Comment content remains valid Unicode/no NUL, max4000 code points.

All task paths retain /api/v1/profiles/{p}/workspaces/{w}/ nesting. Services repeat
authorization and state checks under existing transaction locks, including stale
hint, latest-submission, replay and self-review restrictions. Capability is a UI
hint, never a durable grant. Standard400 input,403 authority/CSRF,404 scoped target
and409 workflow conflict handling remains. No parent/child status cascade.
See FE03_CONTRACT_MATRIX.md for before/after and HANDOVER.md for current evidence.

Historical API03A verification2026-10-27: targeted PostgreSQL95/95 and full485/485 PASS;
frontend356/356, typecheck/lint/build PASS. Real isolated collaboration7/7 now
performs Submit/Request Changes/resubmit/Approve through React, plus independent
approval and old Comment edit after reload/page2. Work7/7 and Auth/CSRF/tenant6/6
regressions PASS. Native/Python/Playwright/backend exits0 and owned cleanup verify;
development remains35 migrations/3 Users/2 Sessions/0 business rows with no writes.
Both API03A and FE03 accepted scopes are complete; stop at Owner review.

## Historical HT-FE-P3-03 frontend consumer — pre-extension contracts/gaps

The missing capabilities and ephemeral author proof below describe the original
frontend-only checkpoint; the approved extension above supersedes those gaps.

No backend route, serializer, permission, model, migration or service changes in
this task. Full pre-code mapping is [FE03_CONTRACT_MATRIX.md](FE03_CONTRACT_MATRIX.md).
Task detail consumes paginated Deliverable rows with nested Review; no separate
Deliverable detail/update/upload URL is invented. Safe external HTTP(S) URLs
are links; arbitrary stored text is escaped. Comment list/detail/create/update/
soft-delete and own Notification feed/count/read use existing methods and CSRF.

Comment create UI verifies scoped OPTIONS POST metadata. Exact comment IDs from
successful legitimate current User/scope POSTs establish only that comment's
ephemeral authorship while mounted, not a general self-membership capability.
Manager deletion uses the existing management hint; manager editing another
author remains unavailable. Confirmed delete redacts cached bodies immediately
and cancels stale GETs before refetch. Notification navigation uses validated
scope IDs rather than following the returned API target_url. Feed/count/read
remain server-filtered by recipient and current readable target.

API GAP: Task.can_start proves current-assignee execution only in ASSIGNED,
not Submit in WORKING; role-only Deliverable/Review OPTIONS cannot prove
assignee/non-self/latest object conditions. Existing Comment author membership
ID lacks a general current-User mapping. Submit/Approve/Request Changes and
pre-existing author edit controls therefore remain hidden. Proposed read-only
per-object capabilities require Owner approval in a separate bounded API task;
no new policy is implemented here.

Browser coverage distinguishes real UI Comment/Notification flows from
API-driven Submit/Review transitions whose resulting history the UI reads.
API-driven success is not evidence of missing UI mutation functionality.

## HT-API-FE-P3-02A — Task capability and assignment roster (implemented)

Additive read fields on existing authenticated endpoints; no new URL, schema,
permission, status transition or authentication mechanism. Existing fields and
pagination/filter semantics remain compatible.

Task list/detail/direct-subtasks and Task mutation responses include
`can_start: boolean`. It is computed from the authenticated request and verified
Workspace access context, never a client-supplied User ID. The actual identity
chain is request User → active same-Profile membership → active Workspace Editor
membership → active TaskAssignment.user FK. True also requires both tenant
scopes ACTIVE and Task status ASSIGNED. Profile Owner/Admin, Workspace Admin,
Viewer and staff without that exact Editor authority do not gain execution.
Missing/mismatched serializer context fails closed. No new global User identity
or self-membership endpoint is exposed.

The flag is a display hint only. Existing `POST .../tasks/{task_id}/start/` still
accepts an empty object, requires SessionAuthentication + CSRF and repeats live
authorization/assignment/status checks under transaction locks. Success200
transitions ASSIGNED → WORKING and returns `can_start:false`; nonassignee/role
denial403, inaccessible nested scope404, wrong workflow state409. No automatic
retry, review bypass, completion or parent/child propagation is introduced.

Existing manager-only `GET .../workspaces/{workspace_id}/members/` adds:

| Field | Contract |
|---|---|
| profile_membership_id | Existing stable same-Profile identity submitted for assignment |
| display_label | Trimmed User full name; otherwise safe `Thành viên <membership prefix>`. Never username/email fallback |
| is_assignable | Active User + active Profile MEMBER + active Workspace MEMBER/Editor + ACTIVE Profile/Workspace |

Roster visibility is unchanged: current manager scope, effective active supported
Workspace assignments backed by active User/Profile membership; inactive/revoked
rows stay absent. Profile Owner/Admin or Workspace Admin/Viewer may be visible
but are not eligible merely because they have a Workspace row. No email, phone,
password, username or global User ID is added. Pagination is retained. Scoped
Exists/select_related/only and existing Task assignment prefetch keep query
growth bounded rather than fetching an identity per list row.

The frontend selector renders these labels, uses the backend eligibility flag,
excludes the current assignee and submits the original ProfileMembership ID.
Current assignment eligibility is revalidated by the unchanged assignment
service on POST. Reading/opening the selector does not mutate Task state.
Both previously documented API gaps below are superseded by this contract;
current runtime verification and completion status are in HANDOVER.md.

## Historical HT-FE-P3-02 consumer contracts and gaps — 2026-10-26

No backend route/schema/permission changed. The UI now consumes existing
Workspace POST/PATCH/archive/restore and manager-only member reads, Task
GET/POST/PATCH/assign and paginated GET direct-subtasks. Task create with parent_id
is also the Subtask creation contract; POST to the read-only subtasks route is
405. Filters/status/priority/deadline/root_only/parent_id/order/page stay server
scoped. Task update never sets arbitrary status; no Review approval bypass.

DRF OPTIONS.actions.POST is used as a permission hint after its POST permission
check; static Allow is not authorization. Vite's own CORS middleware is disabled
so same-origin OPTIONS reaches Django; backend CORS/CSRF/auth settings unchanged.
Each actual mutation still revalidates permission and requires session CSRF.

API GAP: me exposes global User.id, while TaskAssignment and WorkspaceMember
reads expose ProfileMembership IDs, with no current-self mapping. Start action
metadata checks Editor role, not actual assignee; it cannot safely authorize a
Start button. START remains hidden pending an approved scoped identity/capability
contract. Workspace roster lacks names/email/Profile role; UI displays actual
membership codes, filters active Workspace MEMBER candidates and relies on the
assignment service for final Profile-role eligibility. Friendly identity and
fully prevalidated eligible-target reads remain gaps. No guessed ID equality,
PII expansion or backend implementation is introduced in this frontend task.

Source/documentation discrepancy: Task.Status already includes legacy CANCELLED.
Frontend can render/filter this legacy value without adding a cancel transition.
Dashboard remains a real Profile access overview; no Task aggregate/search API
is invented and current-page local search is explicitly labeled.

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
`is_deleted`, `can_edit`, `can_delete`, `edited_at`, `deleted_at`, `created_at`,
`updated_at`. Both capability fields are request-bound booleans as defined in
the HT-API-FE-P3-03A contract above. No author
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
| `POST` | `/api/v1/profiles/` | Active authenticated User + valid session CSRF | Create a new Profile from name only; request.user becomes its active Owner atomically. No pre-existing Profile membership is required. |
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
| `GET` | `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/member-candidates/` | Profile Owner/Admin or that Workspace's Admin | Bounded same-Profile active membership candidates without an active Workspace row; archived scope returns an empty list. |
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
- `display_label`
- `is_assignable`
- `role`
- `is_active`
- `joined_at`
- `updated_at`
- `capabilities` (read-only nested management/inheritance hints described above)

They intentionally omit global User ID, email and username; authorized labels
use names or safe membership-prefix fallback. Member list results add the
current management capability envelope described above and use bounded pagination
with stable
`joined_at`, then `id`, ordering. Direct add and role update use locked atomic
services and write `workspace.membership.created` or
`workspace.membership.updated` AuditLog events in the same transaction.
`DELETE` sets `is_active=false`, immediately removes effective access and
roster visibility, retains the row, returns `204 No Content`, and writes
`workspace.membership.revoked` atomically. Profile Owner/Admin can manage
`ADMIN`, `MEMBER`, and `VIEWER`; Workspace Admin remains limited to `MEMBER`
and `VIEWER`, including concurrent reactivation attempts.

The current candidate/capability contract above augments these existing writes.
It does not add a last-Workspace-Admin rule, remove inherited Profile manager
authority or change retained Task/Deliverable/Review history on soft revoke.

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

There is deliberately no recipient inbox/list endpoint. Accounts now has
durable current-email verification state (`email_verified_at` plus normalized
email binding), exposed as `email_verified` in the User API. It does not itself
grant inbox/invitation metadata access or add a prerequisite to the reviewed
acceptance contract. A recipient instead proves control for this one invitation by
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
stored. The common token path locks and revalidates the active Profile,
pending/sent and unexpired invitation, authenticated User, uniquely matching
normalized email and optional bound recipient User. Acceptance additionally
checks the original inviter's current authority; decline grants no access and
does not require that original-inviter authorization check. A
token cannot be used when delivery is merely queued or failed. Invalid,
unknown, expired, rotated, consumed, mismatched-recipient, ambiguous-account,
archived-Profile, or (for acceptance) no-longer-authorized-inviter cases fail with the same
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
`PATCH` accepts a subset of these five core metadata fields plus the five nullable
Task brief candidate fields documented at the top; empty or
unchanged input is a no-op with no audit event. The example above remains valid
unchanged. To create a Subtask, include `"parent_id": "same-workspace-task-uuid"`
in the existing collection POST; there is no second Subtask write endpoint.
Unknown and server-owned fields—including
`profile_id`, `workspace_id`, `status`, creator, assignment, revisions,
reviewer, IDs, and timestamps—are rejected with `400 Bad Request`.

Task responses retain these foundation fields; the Task brief candidate adds
the five nullable URL/compensation fields documented at the top:

- `id`
- `workspace_id`
- `parent_id`
- `title`
- `description`
- `status`
- `priority`
- `deadline`
- `active_assignment`
- `can_start`
- `can_submit`
- `created_at`
- `updated_at`

`active_assignment` is null or contains `id`, current
`profile_membership_id`, `assigned_at` and the additive read-only
`display_name: string | null` documented above. No separate global User ID,
email, contact data or username field is exposed; the safe label may use an
eligible username as its fallback. If the assignee no longer has a current active
same-Profile membership, historical attribution is retained in the database
but the serialized ProfileMembership identifier becomes null rather than
exposing a stale tenant identifier. Current access is independently required for
the display label, and an unavailable name serializes as null.

### HT-TASK-P2-05 hierarchy, deadline and priority — 2026-10-25

At that hierarchy checkpoint, `parent_id` was the only added response field;
later capability additions are listed in the current response above. All other
fields and the paginated envelope remain. Null identifies a root. A Task may have many direct
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

Current new submissions/resubmissions require the validated, trimmed HTTP(S)
`file_url` string (max500) defined by HT-FE-TASK-UX-REFINEMENT-01 above. The
foundation originally accepted arbitrary text/URL; that historical write policy
is superseded, while stored legacy text/path values remain readable unchanged.
No resource is uploaded, fetched, scanned or checked for external access/media
contents, and no storage provider is authorized. The service allocates a positive
sequential revision while locking the Task. A Task may have multiple historical
Deliverables, but only its latest submitted revision may be decided.

Deliverable responses contain exactly:

- `id`
- `task_id`
- `revision`
- `file_url`
- `status`
- `uploaded_by_profile_membership_id`
- `review`
- `can_approve`
- `can_request_changes`
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
