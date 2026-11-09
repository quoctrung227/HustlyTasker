# HustlyTasker frontend guide

## HT-FE-INVITATION-DELIVERY-FIX-01 — Delivery diagnosis and safe recovery (2026-11-09)

**APPLICATION FIX VERIFIED — REAL SMTP PENDING OWNER CONFIGURATION.** This
checkpoint does not claim genuine email delivery. Application recovery and
transport outcomes are verified with isolated/fake mail, including all20 final
browser regressions. No genuine SMTP test has been authorized or performed.
No external email, provider signup/billing, credential change, development
mutation/migration or deployment is authorized by this task.

### Verified development cause of503

The existing loader reads the repository-root Git-ignored local file
`D:\da\HustlyTasker\.env`; the existing backend virtualenv then loads Django
settings. A sanitized diagnostic reports development mode, the **console**
mailer, credential-email preflight denied, and SMTP host/username/password absent.
Only configuration presence/classification was reported, not secret values.

`apps/common/email_delivery.py` intentionally rejects console, dummy and
filebased backends for credential emails. Console/file output could expose a
usable invitation or recovery token; dummy could falsely imply delivery. Do not
disable this guard, print the token or silently switch development to locmem as
a replacement for genuine SMTP setup.

Creation checks mail availability inside its transaction **before** generating
a token or inserting Invitation/AuditLog. This development preflight failure
returns the generic503 without a row. Read-only inventory confirms **0 Invitation
rows and0 invitation audit rows**, including no hidden PENDING/FAILED records.
No automated POST was replayed against persistent development. Existing stored
development logs had no matching static marker; the Owner's interactive terminal
log was unavailable, so no unseen SMTP exception is claimed.

### Two distinct503 outcomes and the visible-list fix

| Failure stage | Persisted result | Safe recovery |
|---|---|---|
| Mail preflight unavailable, as currently configured | No new Invitation/token/audit | Configure an approved working transport first; a later explicit create can then be attempted |
| Configured transport fails in the after-commit callback | PENDING Invitation with delivery_status FAILED and its audit remain; response503 | Inspect the row and use its explicit resend action after transport recovery; do not repeatedly create another invitation |

The backend list does not hide delivery FAILED. It remains scoped to the current
Profile/authority and Admin role ceiling. An unrelated UI visibility defect was
that create/resend from a later pagination page could leave the newest or failed
replacement on page1. Explicit create/resend and uncertain outcomes now return
the invitation list to page1 and refetch; normal background refresh preserves
the selected page and open form draft.

The UI explains503 as unavailable/unconfigured email without claiming that
nothing was saved. It clears stale success feedback, retains failed-create input
and keeps a failed-resend error at Profile-page level even if the replaced row
moves off the current page. Closing the form and inspecting history is safe;
there is no automatic retry or optimistic SENT/success.

For an existing pending row, another create conflicts409. Create success returns
201. **Gửi lại** success returns200 with a new invitation ID/token and deliberately
revokes the old pending credential;
replaying resend on the old row conflicts409. A resend can itself fail after
commit, leaving a visible FAILED replacement and exactly one pending row. If
resend preflight fails before commit, the existing row is unchanged. Do not
recover by deleting rows, resetting the database or bypassing membership consent.

SENT means the configured mail adapter accepted one message. It is neither
mailbox-delivery proof nor invitation acceptance. QUEUED, FAILED, PENDING and
ACCEPTED are distinct delivery/business states. The recipient must still sign
in with the invited email and explicitly accept a usable emailed code.

### Owner-only SMTP configuration, kept private

Choose an SMTP service or relay already approved by the Owner. This task does
not choose a paid service, create credentials or modify local configuration.
Privately edit the existing root `.env` using provider-issued values and the
loader's literal KEY=value format. Do not post secrets in chat, place them in
tracked files or pass them as visible terminal arguments.

| Exact configuration name | What the Owner must supply |
|---|---|
| `DJANGO_MAILER_BACKEND` | Explicit SMTP backend: `django.core.mail.backends.smtp.EmailBackend` |
| `DJANGO_SMTP_HOST` | Provider-approved SMTP host |
| `DJANGO_SMTP_PORT` | Port documented for that host and encryption mode |
| `DJANGO_SMTP_USERNAME` | Authorized SMTP account identity when authentication is required |
| `DJANGO_SMTP_PASSWORD` | Corresponding SMTP credential/app password, privately stored; username/password must be configured together |
| `DJANGO_SMTP_USE_TLS` | Provider-required STARTTLS boolean |
| `DJANGO_SMTP_USE_SSL` | Provider-required implicit TLS boolean; TLS and SSL cannot both be true |
| `DJANGO_SMTP_TIMEOUT` | Valid timeout for the approved SMTP setup |
| `DJANGO_DEFAULT_FROM_EMAIL` | Sender identity/address authorized by the provider |
| `DJANGO_SERVER_EMAIL` | Optional separately authorized sender for Django server/error email |

Do not copy prefilled `.env.example` credential values into reports or treat
template values as validated service credentials. Keep existing Django/PostgreSQL
secrets and database identity unchanged. Do not change AI flags, CSRF/session
settings or the pending ai.0002 migration to address email delivery.

From the repository root, existing checks can validate local syntax/settings:

```powershell
.\scripts\start-backend-dev.ps1 -ValidateOnly
.\scripts\start-backend-dev.ps1 -Check
```

`-ValidateOnly` checks the local launcher configuration; `-Check` additionally
runs Django system checks. Neither sends email or proves SMTP authentication,
provider acceptance or mailbox delivery. After privately changing configuration,
stop/restart the existing backend terminal with
`.\scripts\start-backend-dev.ps1`; it uses `--noreload`, so editing `.env` alone
does not update a running Django process. These commands do not apply migrations
or create fixtures. There is no need to recreate the virtualenv or database.

Before a genuine delivery test, the Owner must explicitly authorize an intended
recipient and the real send. After that authorization, manually use **Tổ chức →
Thành viên tổ chức → Mời thành viên**, or **Gửi lại** for a persisted pending
invitation. Check server status and the recipient mailbox/spam folder separately.
Only an authorized successful real-delivery test can establish genuine email
delivery. Until then: **REAL EMAIL DELIVERY NOT VERIFIED**. The current console
configuration will continue returning503; the UI fix does not configure SMTP.

### Current automated verification and preservation boundary

Targeted isolated PostgreSQL Invitation tests: **48/48 PASS60.654s**, launcher and
actual Python exit0, system/model/migration-chain checks and owned cleanup PASS.
Final Organization Members component tests: **32/32 PASS15.69s**; full frontend
unit/contract **908/908 PASS34.53s**, typecheck/Biome/build exit0 (build8.73s).
Final real Chromium20/20 PASS: delivery failure2(11.6s), Members4(43.7s),
Workspace4(36.4s), Task stability4(22.6s), Auth/CSRF/tenant6(44.9s). All launcher/
Playwright/backend exits0 with owned cleanup. The first failure-browser attempt exposed a test-only wrong
resend status expectation; the unchanged API contract is200, not create's201.
Previous863/902/18 results are historical and are not this task's new results.

The new API tests use actual commit boundaries with SMTP-opening guards and fake
transport, proving preflight no-row503, persisted FAILED503/list visibility,
duplicate protection, resend rotation/failure, tenant/role/session/CSRF behavior.
The private browser failure mode is locmem-only in the ownership-checked isolated
PostgreSQL harness; it is not a public endpoint or normal-development mail mode.
No fake transport result proves real external delivery.

Read-only development baseline:29 tables,36 applied migrations,5 Users,
2 Sessions,2 Profiles/2 ProfileMemberships,1 Workspace,1 Task,4 AuditLogs;
Invitation/invitation-audit/AI rows0. This is newer Owner data than the previous
Workspace task's baseline; do not roll it back. ai.0002 remains UNAPPLIED.
Final09:15:53Z read-only comparison exactly matches all29-table data/schema/
constraint/index/sequence/history/cluster properties except transient connections.
0 owned containers/networks remain across7backend/browser attempts; all770
original files are preserved apart from the documented13 task changes. The
.env.example edit is comment-only and every original assignment is unchanged;
actual .env/settings/provider configuration remains untouched. Manual Owner
acceptance and genuine email remain pending; evidence is recorded in HANDOVER.
Stop at **HT-FE-INVITATION-DELIVERY-FIX-01 — OWNER REVIEW GATE**. No production
deployment or next task follows automatically.

## Historical HT-FE-WORKSPACE-MEMBERS-01 — Workspace access management (2026-11-09)

Status: **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**. Reuse the
existing local startup commands below. No dependency, authentication, schema,
AI flag, email provider or persistent development data change is part of this task.

### Domain and discoverable entry

Open **Tổ chức → Workspace → Thành viên / Quyền truy cập**. The existing Workspace
detail route keeps its inline Members section and anchor #workspace-members;
there is no duplicate page/auth provider. Roster/current capabilities come from
the real manager-only GET members API, including archived read-only contexts.
An Editor/Viewer retains legitimate Workspace/Task read access but cannot read
the management roster or candidates. Knowing a route/UUID never grants access.

| Actor | Workspace access | Member administration |
|---|---|---|
| Active Profile Owner/Admin | All same-Profile Workspaces; explicit WorkspaceMember not required | ADMIN/MEMBER/VIEWER while both scopes are active |
| Profile MEMBER + active Workspace ADMIN | Assigned Workspace | MEMBER/VIEWER only; cannot edit/revoke an existing ADMIN |
| Profile MEMBER + active Workspace MEMBER | Assigned Workspace, Editor execution requires active TaskAssignment/current state | None |
| Profile MEMBER + active Workspace VIEWER | Assigned Workspace read-only | None |
| Profile MEMBER with no effective Workspace row | None, tenant-safe404 | None |

The real model is WorkspaceMember(User FK, unique Workspace+User), not a new
WorkspaceMembership table. Profile acceptance and Workspace creation do not
create these rows. The roster lists effective explicit assignments, not every
inherited Profile manager. An inherited context's workspace_role may be null
even when a lower explicit row exists; UI labels the access context rather than
claiming that null proves no assignment. Workspace OWNER is unsupported legacy
authority, not a choice. Staff/Workspace.owner alone grants no tenant authority.

### Grant, role update and revoke

**Thêm thành viên** opens a shared native dialog with a paginated **Chọn thành
viên tổ chức** selector. New manager-only GET member-candidates returns active
same-Profile memberships/Users without an active Workspace row. It includes
inactive rows eligible for reactivation and Profile managers with a clear
inherited-access explanation. No unrelated tenant/User directory/email is shown.
Archived contexts return no candidates and disable mutation capabilities.

Choose a server-allowed **Vai trò trong Workspace** and **Cấp quyền truy cập**.
ADMIN means Quản lý, MEMBER means Editor, VIEWER means Chỉ xem. Existing POST
members sends only target_profile_membership_id/role; new201, reactivation200,
already-active duplicate409. Neither Admin/Viewer nor Profile Owner/Admin becomes
an Editor/Task assignee merely through broad read/management authority.

Each row uses server can_update/can_revoke/allowed_roles. **Cập nhật quyền** opens
a role form requiring **Xác nhận cập nhật quyền**; existing PATCH sends role only.
**Thu hồi quyền** requires **Xác nhận thu hồi quyền**, then existing DELETE204
soft-revokes the explicit assignment. Controls are pending-disabled and never
optimistically report success. Recoverable errors retain input;409/uncertain
outcomes refresh actual data rather than automatically repeat a write.

Removing/demoting a Profile manager's explicit row does not remove inherited
authority; the UI warns before mutation. There is no existing last-Workspace-
Admin invariant; do not invent one. The separate last-active-Profile-Owner rule
remains unchanged. People not yet in this Profile must use the existing Profile
invitation workflow first; a Workspace Admin without Profile governance is told
to contact the Profile Owner/Admin instead of receiving an unauthorized invite link.

### Task compatibility, stability and private state

Membership writes invalidate the new User/Profile/Workspace access scope plus
the existing workKeys scope, Workspace lists and current authority, so TaskAssign
refreshes the existing is_assignable roster. Only active Profile MEMBER + active
Workspace MEMBER is an eligible assignee; actual assignment/state is still checked
for Start/Submit. No Task forms, workflow or assignment service is rewritten.

Revoke/downgrade preserves Task, TaskAssignment, Deliverable, Review and status.
Revoke removes effective Workspace reads/execution; Viewer downgrade retains
reads but denies execution. Regranting Editor can reactivate the effect of an
old still-active TaskAssignment; no auto-unassignment is claimed.

Normal refetch/focus/auth validation keeps the same form and draft. User/Profile/
Workspace changes abort and discard old pending state. Actual lost authority
removes candidate/roster data;404 also removes the old work scope and refreshes
Workspace authority. A roster403 does not erase legitimate Editor/Viewer Task
read cache. Recoverable CSRF403 is distinguished from lost authority. No private
state is persisted in localStorage or a new global store.

Full UI UX Pro Max/master read and actual offline `confirmation permission
changes --domain ux` / `async request cleanup race --stack react` searches inform
explicit confirmation, truthful success, abort cleanup and caught async failures.
Existing teal/neutral tokens, typography, lists, native selects/dialogs, focus and
linked errors remain. Native fieldset labels the row action group; a small CSS
reset preserves the existing work-actions spacing without a new visual direction.

### Owner manual acceptance — not performed on persistent development

1. Log in as authorized Owner/Admin, invite the intended recipient through
   **Thành viên tổ chức** with an approved working mail backend. Recipient signs
   in and explicitly accepts the emailed code. REAL EMAIL DELIVERY NOT VERIFIED
   by this task; automated tests use locmem only.
2. Verify an ordinary Profile MEMBER initially sees no unassigned Workspace.
   Open the intended Workspace as its manager, choose **Thêm thành viên**, select
   that accepted member and grant MEMBER/Editor. No Workspace email invitation
   or guessed User ID is needed.
3. Recipient opens only permitted Workspaces. Assign a Task using the existing
   form; the Editor can Start/Submit only when its current workflow permits.
4. Manager changes the explicit role to VIEWER and confirms. Recipient keeps
   reads but loses execution. Restore MEMBER or confirm revoke as intended;
   revoke removes Workspace access while preserving Task/history.
5. Check Workspace Admin cannot grant ADMIN/manage another ADMIN; archived
   contexts are read-only. Keep a grant/Task form open during normal focus/refetch
   and confirm that a real logout/context switch removes old private content.

### Fresh verification and isolated commands

Backend targeted95/95 PASS9.634s, full863/863 PASS294.428s (one full run),
launcher/actual Python0 and dependency/Django/isolated migration-chain checks
PASS. API client67/67 PASS3.76s; final UI34/34 PASS12.40s. Broader frontend902/902
PASS51.11s ran once before the final semantic-only fieldset/native CSS reset;
only that markup changed afterward, with final34/typecheck/Biome/build and all
18 real browser tests passing on the final source. No handler/workflow changed.

Browser: Workspace4/4 PASS39.1s, Profile Members4/4 PASS46.3s, Task stability4/4
PASS20.3s, foundation6/6 PASS45.3s. All launcher/Playwright/isolated backend exits0,
owned DB removal and0 remaining containers/networks across7attempts/runs verified.
Four viewports/keyboard/focus/reflow/axe pass;375/1440 PNGs visually inspected in
Git-ignored .local_backups/HT-FE-WORKSPACE-MEMBERS-01/screenshots/.

```powershell
.\scripts\test-backend.ps1 -TestLabel apps.workspace.test_workspace_access_api,apps.workspace.test_write_api,apps.tasks.test_identity_api
npm.cmd --prefix frontend test -- src/services/api/workspace-access.test.ts src/features/workspaces/WorkspaceMembers.test.tsx
.\scripts\test-frontend-integration.ps1 -Suite workspace-members
.\scripts\test-frontend-integration.ps1 -Suite members
.\scripts\test-frontend-integration.ps1 -Suite task-stability
.\scripts\test-frontend-integration.ps1 -Suite foundation
```

Final2026-11-09T08:17:28Z read-only snapshot exactly matches all original29-table
data/schema/constraint/index/sequence/history/cluster properties except transient
connections:36 migrations/4 Users/2 Sessions/1 Profile/membership/Workspace/Task/
3 AuditLogs; WorkspaceMember/Invitation/AI0. No .env/credentials read or migration
apply; ai.0002 remains UNAPPLIED. Existing large bundle advisory remains.

These real website writes are reserved for Owner acceptance. Automated business
mutations use only owned isolated PostgreSQL. Current counts/exits, failed-attempt
corrections, cleanup and preservation evidence are in HANDOVER; no manual website
or production readiness is inferred. Profile role/remove and recipient inbox/
preview remain separate scope. ai.0002 development rollout is still unapproved.

## Historical HT-FE-MEMBERS-01 — Organization Members and Invitation (2026-11-08)

**IMPLEMENTATION COMPLETE — OWNER REVIEW GATE.** This bounded integration adds
protected /profiles/:profileId/members and /invitations/respond. Use the existing
local startup commands later in this guide; no new dependencies, environment
credentials, AI flags, migration or email provider are configured by this task.

### Management workflow and authority

Open **Tổ chức → selected Profile → Thành viên tổ chức**. Owner/Admin see a
paginated membership roster and invitation history using actual Django responses.
Labels/roles/membership activity are scoped to this Profile; there is no global
User directory or email/username fallback. The stored membership activity flag
alone is not proof of current account/session authority.

- Profile Owner may invite ADMIN or MEMBER. Profile Admin may invite MEMBER.
  No OWNER invitation; Workspace Manager/Admin is not Profile governance.
- **Mời thành viên** opens the shared native dialog. Enter the intended account's
  email and a server-allowed organization role. Pending disables duplicate submit;
  failures keep the draft. Normal focus/visibility/auth refetch keeps that draft.
- **Gửi lại** uses the existing resend service for PENDING/EXPIRED invitations;
  the server returns a new invitation ID and invalidates the old credential.
  **Hủy lời mời** requires explicit confirmation and only operates on an eligible
  current pending invitation. Expired/revoked/consumed entries remain history.
- Archived Profile is read-only. Revoked/inactive authority or changed identity/
  Profile aborts stale requests and removes old private data/actions. A recoverable
  CSRF error preserves retryable input and does not masquerade as lost membership.
- No Profile role editing/removal or Workspace direct-add control is fabricated.
  General Workspace candidate/management integration requires its own approved
  API/UI scope. Accepting Profile MEMBER does not grant any Workspace membership.

### Recipient workflow and actual email behavior

Current backend mail contains an opaque code, not an application URL. There is
no recipient inbox/token-preview endpoint. **Tôi có mã lời mời** on the login or
Profile page opens the protected response flow; a logged-out user logs in first,
or registers and then logs in. Only the fixed /invitations/respond return path
survives signup/login. A token in query/fragment is never ingested or forwarded.

The recipient signs in with the invited email, manually enters **Mã lời mời**
in a masked field, then chooses **Chấp nhận lời mời** or explicitly confirms
**Từ chối lời mời**. Merely opening the page/logging in/registering never accepts
anything. The backend validates current unique normalized email identity, token,
expiry/delivery/state/Profile and, for acceptance, original inviter authority.
Email verification is a separate account lifecycle, not implicit invitation
acceptance. Invalid/wrong-user/expired/revoked/used codes receive a generic409;
the UI does not diagnose another recipient or expose token metadata.

On confirmed acceptance, code memory is cleared, accessible Profile queries are
invalidated and **Đến tổ chức** uses the server-returned Profile ID. No Workspace
is automatically created/granted. Decline creates no membership. Code remains
only transient input state and POST body, never localStorage, query key/cache,
URL, screenshot evidence or logs. Logout/identity changes discard private state.

**REAL EMAIL DELIVERY NOT VERIFIED.** Automated tests use Django locmem only.
SENT means the configured mail backend accepted a message, not proof of mailbox
delivery. QUEUED and FAILED remain distinct. No safe email backend configuration
causes503 before creation; a failure after transaction commit can also return503
with an existing pending FAILED invitation. Inspect refreshed history before
retrying; the UI never automatically retries or claims nothing was created.
No SMTP provider or credentials were configured or changed in this task.

### Fresh verification and reproducible commands

Frontend API75/75 and focused142/142 are mocked unit/contract checks, not E2E.
Final full frontend801/801 PASS23.61s; TypeScript/Biome/build exit0. Targeted
PostgreSQL51/51 PASS56.587s; full839/839 PASS245.158s, actual full Python0.
Targeted launcher0/summary verified; independent targeted child event unavailable.
Real Chromium14/14 PASS: Members4(38.6s), Task stability4(20.9s), foundation6(36.0s).
Each browser launcher/Playwright/backend exit0 and owned cleanup confirmed.

```powershell
.\scripts\test-backend.ps1 -TestLabel apps.workspace.test_profile_members_api,apps.workspace.test_invitation_api,apps.workspace.test_invitation_model_services
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
.\scripts\test-frontend-integration.ps1 -Suite members
.\scripts\test-frontend-integration.ps1 -Suite task-stability
.\scripts\test-frontend-integration.ps1 -Suite foundation
```

All browser business mutations occur only in ownership-checked isolated
PostgreSQL fixtures. Locmem code extraction is a private test-only helper;
it is not a public API or a manual development email retrieval mechanism.
The invitation management, recipient registration/acceptance, resend/decline/
revoke actions run through real React forms against Django; API calls in these
specs provide read-back and intentional negative authorization assertions.
375/768/1440/812x375 keyboard/focus/reflow/axe checks PASS;375/1440 PNGs inspected
under Git-ignored .local_backups/HT-FE-MEMBERS-01/screenshots/.

Full local UI UX Pro Max/master read and offline `confirmation destructive
action --domain ux` / `async request cleanup --stack react` searches informed
explicit confirmations, truthful delivery outcomes, abort cleanup, stable forms,
native dialog focus and accessible labels/errors. Existing teal/neutral tokens,
typography, sidebar/topbar and primitives are reused; no new design system.

### Manual Owner acceptance — not executed against persistent development

1. Start backend/frontend using the existing commands below; log in as a real
   authorized Profile Owner/Admin and open **Thành viên tổ chức**.
2. Verify this Profile's roster/history and allowed roles. Ordinary Member or
   Workspace-only management must not gain Profile invitation authority.
3. When an approved working mail backend is configured, invite the intended
   real recipient. Confirm status/history; do not interpret SENT as mailbox proof.
4. Recipient registers if needed, logs in with the invited email, opens
   **Tôi có mã lời mời**, enters the code from their email and explicitly accepts
   or declines. Check the resulting Profile access; MEMBER has no implicit
   Workspace access. Test resend/revoke only with intended invitations.
5. Verify open invitation/Task forms survive normal focus/refetch, and logout/
   another identity cannot see the previous User's private data.

These Owner actions may create real development records and were deliberately
not performed by the agent. Final read-only task proof at14:48:54Z matches every
original29-table data/schema/history/index/sequence/cluster property, excluding
transient connections:36 migrations,4 Users,2 Sessions,Invitation0/AI0. Candidate
ai.0002 remains UNAPPLIED. Manual website acceptance remains pending; no rollout
or next task is authorized by these automated results.

## Historical HT-FE-STABILITY-01 — Session revalidation and Task draft continuity (2026-11-08)

Current status: **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**. This is a
targeted lifecycle fix, not a Task-page redesign or draft-storage feature.

### Reproduced cause and implemented correction

Before the fix, normal window focus/visibility and the60-second auth timer called
verifyIdentity with quiet=false. It set checking/user:null even for a valid
session; ProtectedRoute replaced the entire Outlet with SessionState. The Task
dialog and local inputs unmounted without a route change or document reload.
Pre-fix real-route/component tests reproduce this; normal successful Task-list
refetch alone does not replace the header containing TaskCreate. No evidence
attributes that periodic bug to StrictMode, HMR or accidental button submission.

Routine verification of an already authenticated session now preserves the
mounted subtree while /me is pending and returns the same identity. Successful
routine checks invalidate active queries to refresh actual tenant authority/data,
without clearing the cache or mounting a new page. A permission403 identity
probe deliberately does NOT invalidate the denied query again; this avoids a
refetch loop. The60-second timer remains; automatic checks run only for an
authenticated session and do not interrupt login/logout checking states.

| Identity/context result | Required UI behavior |
|---|---|
| Initial session or explicit recovery | Existing blocking SessionState; no unverified private UI |
| Pending/successful same-User routine check | Same Task dialog/input state; active permission/data queries refresh without full-page loading fallback |
| Verified different User | Hide previous UI, cancel/clear private cache and remount User-keyed Outlet; same tenant ID never preserves another User's draft |
| /me401/403 | Clear private cache, leave protected route and show login-required/unsaved-input explanation |
| /me network/server failure | Existing fail-closed unavailable page hides private data with explicit recovery; no draft recovery guarantee |
| Tenant change or confirmed lost capability/access | Existing tenant keys/permission checks remove old draft/actions; no stale privilege retention |

Task form values remain in component memory only. No localStorage/sessionStorage,
server autosave or new authentication/RBAC/API policy is introduced. Recoverable
creation failures keep the form, success closes it only after confirmation, and
the existing pending guard prevents rapid duplicate submits. Session failure,
manual document reload and deliberate context navigation do not promise recovery.

The full UI UX Pro Max skill/master were read. Verified offline searches
`loading flicker --domain ux` and `stable keys --stack react` informed stable
layout/focus and identity boundaries; no palette/layout/token/dependency change.
The existing teal/neutral forms, native dialog and accessible feedback are reused.

### Verification scope and Owner acceptance

Final frontend689/689 PASS27.24s; TypeScript/Biome/build exit0. Current real
Chromium suites21/21 PASS: stability4, foundation6, work-management7 and
fixture Generator4. Each launcher/Playwright/backend exit0 with owned cleanup.
Four viewport reflow/keyboard/axe checks pass;375/1440 screenshots visually
inspected. Development29-table fingerprints/schema/history remain exact,
36 migrations/4 Users/2 Sessions preserved; candidate ai.0002 is UNAPPLIED.
No backend source changed, so backend826 is historical and not rerun here.
Earlier screenshot capture timeout and fixture/type/focus assertion corrections
are preserved in HANDOVER. The final HMR capture uses a bounded viewport image,
not a full tall background-page resize; all behavioral/axe assertions remain.

Use the existing isolated runner; it never seeds persistent development:

```powershell
.\scripts\test-frontend-integration.ps1 -Suite task-stability
.\scripts\test-frontend-integration.ps1 -Suite foundation
.\scripts\test-frontend-integration.ps1 -Suite work-management
.\scripts\test-frontend-integration.ps1 -Suite ai-generator
```

The stability spec forwards actual Django responses with controlled delivery
timing, injects one explicit network failure before its first POST reaches the
backend, and verifies the next real CSRF-protected creation. These distinctions
are intentional: timing/fault injection is not a fabricated successful API.
DOM identity, document sentinel and main-frame navigation distinguish rerender
from remount/reload. The HMR probe is a newly owned Git-ignored self-accepted
module, not a rewrite/restore of existing source; it cannot prove that arbitrary
React-boundary edits/full reload preserve local drafts. Screenshots contain
synthetic test data only. Actual results/failed attempts/cleanup are in HANDOVER.

Manual Owner check after reviewing the report (not claimed performed by Codex):

1. Use the existing two-terminal local startup instructions below and log in
   with your own legitimate account/context. Do not enable live AI or migrate.
2. Open Create Task; enter title/description/priority/deadline. Leave it open
   beyond60 seconds, switch browser focus/tab and return. Values should remain.
3. Cancel explicitly, then reopen to check the normal empty draft. Use existing
   Task create/edit/detail navigation as intended, without demo fixtures.
4. Verify pending/failed-request feedback; success must only follow server
   confirmation. A real session failure must hide private fields and explain
   sign-in/recovery. Do not test revocation by altering development records merely
   to reproduce a fixture scenario.

04C offline governance remains ready with its development migration pending.
No backend/AI/migration/credential or persistent development write is part of this
fix. Stop at HT-FE-STABILITY-01 OWNER REVIEW GATE; no deployment is authorized.

## HT-AI-P4-04A — Integration readiness and Owner acceptance (2026-11-08)

Status: **DESIGN READY / PROVIDER IMPLEMENTATION BLOCKED — OWNER REVIEW GATE**.
This is a source/contract readiness review, not a new React implementation or
visual redesign. The existing fixture Generator and Analyzer UI remain intact.
Their strict transport parsers require synthetic provenance and zero usage;
genuine provider responses need a separately reviewed compatible contract and
truthful UI provenance. No persistent fixture/live flag or provider is enabled.
The current architecture proposal is
[AI_ARCHITECTURE_DESIGN](AI_ARCHITECTURE_DESIGN.md#ht-ai-p4-04a--live-provider-readiness-2026-11-08).

### Concise manual acceptance — Owner confirmation still PENDING

These are checks for the Owner after review, not claims that manual testing has
occurred. FE05 Create Profile, P4-02C Generator and P4-03C Analyzer manual
acceptance remain PENDING until explicit Owner confirmation. Use legitimate
Owner-selected development data for normal website acceptance. Implementation
tests/fixtures and AI synthetic mutation demonstrations belong only to isolated
PostgreSQL; do not seed development, alter its flags or use another user's
credentials merely to complete this checklist.

| Area | Manual acceptance outcome to confirm |
|---|---|
| Authentication | Login/logout and account recovery/verification states are clear; expired session returns to login and private content disappears |
| First Profile | A zero-Profile account can use Tạo tổ chức; the new Profile is selected and its creator has backend-confirmed Owner access |
| Profile switching | Only accessible Profiles appear; switching changes the route/context without showing the prior tenant's content |
| Workspace | The selected Profile scopes monthly Workspace creation/navigation; authorized edit/archive/restore and read-only member states are clear |
| Task/Subtask | Create/edit/assign/Start, deadline/priority, hierarchy and pagination follow actual role/status permissions |
| Deliverable/Review | Submit→Request Changes→resubmit→Approve follows the existing workflow, with separate actors and no self-review bypass |
| Comment/Notification | Authorized edit/delete produces a tombstone; personal feed/count/mark-read and target navigation respect current access |
| Smart Task Generator | Disabled fixture shows honest unavailability; an isolated enabled demo labels fixed synthetic output, requires preview/edit and explicit confirmation before Tasks exist |
| Feedback Analyzer | Disabled fixture is expected configuration, not proof of a failed feature; an isolated enabled demo selects existing sources, shows citations/synthetic disclosure, and has no Apply/domain mutation |
| User/session change | Logout, session expiry and User/Profile/Task changes remove stale private query/results; Viewer/Editor do not gain manager AI controls |

No new product screen, browser-to-provider call or authentication mechanism is
introduced. Browser AbortSignal protects stale UI but does not demonstrate
cancellation of future remote computation or charges. Live AI requires approved
provider/model/data terms, a compatible provenance/usage contract and reliable
cost enforcement before activation. No manual/live PASS is inferred from earlier
automated tests. Current P4-04A checks are in [HANDOVER](HANDOVER.md);675 frontend
and36 browser results in the next section are historical P4-03C evidence.

## HT-AI-P4-03C — Feedback Analyzer React integration

Status: **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**, 2026-11-02. The Owner approves a
lightweight advisory fixture UI in the existing Task Detail, not a new workflow,
Analyzer persistence or a live AI provider. Existing manual Review/Comment and
Smart Task Generator actions remain independent.

The integration reuses current Task/Workspace manager capability hints and the
existing permission-checked AI availability request. Server authorization is
still required at analysis time; a role label, known UUID or old result grants
no access. With the fixture disabled, the UI must explain unavailability rather
than expose an action that pretends to run live AI. No persistent development
feature flag is enabled by this task.

Eligible source IDs already exist in the authorized paginated APIs: each
Deliverable can contain one `review` with usable text, while nondeleted Task
Comments expose their current content/ID. Selection sends unique
`{kind:"review"|"comment",id}` references for this Task,1–20 sources, plus
optional focus≤1,000 valid Unicode/NUL-free characters. The source-text budget
is12,000 aggregate characters. No source author/role/tenant/provider field or
raw source body is added to the POST contract.

The section is keyed by current User/Profile/Workspace/Task. Opening it lazily
loads existing20-per-page source APIs; selected sources can span pages without
duplicate kind/ID pairs. Before/after sending, only selected pages are refreshed
through their existing tracked cache keys. A newer deletion/redaction cannot be
overwritten by an untracked old GET, and a cancelled read's reverted cached data
is not accepted as a completed refresh. Scope/auth/permission/source changes
abort requests and clear local results rather than populating a new context.

Results say **Kết quả mô phỏng** and explain that a real model has not
understood the selected feedback or focus. S1…Sn labels map to the returned
selected-source manifest, not invented quotations or semantic evidence. Local
results are not saved as history, proposal IDs or operations. Repeating after
a lost response is an explicit new stateless analysis and consumes quota again;
there is no Generator confirmation/idempotency recovery or automatic retry.

Final frontend675/675 PASS27.31s includes106 new transport tests and32 component
tests; focused transport/client153/153 and component32/32 also pass. TypeScript,
Biome and build exit0 (build7.58s). All10 real isolated browser suites36/36 PASS:
Analyzer5, disabled Analyzer1, Generator4, disabled Generator1, onboarding3,
auth/CSRF/tenant6, Workspace/Task7, collaboration7, complete workflow1 and account1.
Every suite reports launcher/Playwright/backend exit0 and owned database/resource
cleanup. Analyzer verifies UI selection/POST/citations, deleted-source handling,
Viewer/Editor/CSRF/cross-tenant denial, Task-switch cancellation/session expiry,
keyboard focus and375/768/1440/812×375 reflow with zero axe violations. All-model
row counts/fingerprints remain unchanged by the advisory analysis operation.
The deleted-source test uses a separately labeled API-driven fixture deletion.

Current isolated backend AI215/215 PASS16.494s confirms compatibility, actual
launcher/Python exits0 and owned cleanup; backend160 source hashes remain intact.
Full backend719 is historical and was not rerun for this frontend slice. The
initial Analyzer browser4/5 role-helper return-to assertion was corrected; final
5/5 passed. Source-refresh cancellation now also rejects reverted cached values,
with a regression proving that an old read cannot restore an unselected deleted
Comment. Final read-only29-table development comparison preserves all row hashes,
schema/FKs/indexes, sequences, migrations and cluster identity exactly; all33
tested source hashes and160 backend hashes match. Owned test resources are gone.
The375px/1440px screenshots were visually inspected for readable source/result
separation, focus and reflow. Source-backed details belong in
[foundation](FEEDBACK_ANALYZER_FOUNDATION.md) and [HANDOVER](HANDOVER.md).
Historical P4-02C results below are not P4-03C tests. Manual Owner acceptance of
Create Profile, Generator and this Analyzer UI remains unverified.

The route stays `/profiles/:profileId/workspaces/:workspaceId/tasks/:taskId`.
An eligible manager opens **Phân tích phản hồi** beside the existing collaboration
sections, selects **Phản hồi đánh giá** and/or **Bình luận công việc**, optionally
enters **Trọng tâm phân tích (không bắt buộc)**, then explicitly submits. Current
source text is distinct from the readonly **Kết quả mô phỏng** section. Changing
selection/focus discards the previous result; closing the panel clears its local
draft/result. Existing Review/Comment buttons retain their ordinary independent
backend-authorized behavior.

Reproduce the isolated automated acceptance after implementation verification:

```powershell
.\scripts\test-frontend-integration.ps1 -Suite feedback-analyzer
.\scripts\test-frontend-integration.ps1 -Suite feedback-disabled
```

The enabled fixture setting is confined to the owned isolated test server.
These commands are not a manual acceptance run on the Owner's development data.
For manual website review, use the existing two-terminal startup instructions,
log in with the Owner's own account, open an authorized Task and verify truthful
unavailability/empty-source behavior under current configuration. Do not change
the persistent fixture flag or seed feedback merely to make the panel available.
An enabled interactive development demonstration requires separate authorization;
full enabled flow evidence belongs to isolated browser tests. No new local setup,
secret, API key or provider is required by this React implementation.
The prior P4-03A Windows-venv interpreter limitation is historical evidence, not
a new startup PASS or a reason to recreate that venv. Current toolchain/startup
verification and any remaining limitation must be reported separately in HANDOVER.

## HT-AI-P4-02C — Smart Task Generator fixture UI

Status: **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**, 2026-11-02. This is the
Owner-approved fixture preview/edit/confirm UI. Live AI, Analyzer, provider keys,
production and persistent development fixture enablement remain excluded.

An active manager sees **Tạo công việc bằng AI** next to the existing manual
creation action in the Task list. Permission-checked OPTIONS reports actual
fixture availability. With the existing flag off, the entry is disabled with an
explanation; opening the route shows **Bản mô phỏng chưa khả dụng**, and manual
Task creation remains usable. This task does not change private environment or
runtime flags to make the button available on persistent development.

When enabled on the owned isolated test server, the protected route
`/profiles/:profileId/workspaces/:workspaceId/tasks/generate` offers two server
scenarios and optional **Mô tả yêu cầu giả lập**, at most 6,000 characters. The
banner says **Bản mô phỏng — không phải AI thật**: only synthetic input is allowed;
the output is a fixed scenario, not AI analysis. Backend validation checks text
shape/length, not whether arbitrary input is genuinely synthetic.

**Đề xuất công việc** saves a proposal, not Tasks. Preview supports local edits
to title, description, priority and nullable deadline, using existing timezone
handling. Parent/Subtask links remain unchanged. Notes, assumptions and warnings
are preview metadata, not Task fields. Edits are not saved to the server before
confirmation and can be lost on refresh; the known proposal URL restores only
the server proposal. No draft, brief or idempotency key is persisted in browser
storage.

Internal anchor navigation and full-page unload use discard warnings. Browser
Back/Forward within the SPA is not intercepted by that anchor guard: unsaved
local edits can be lost. This is a draft-persistence UX limitation, not server
confirmation or idempotency bypass; refresh still retrieves only server state.

**Kiểm tra và xác nhận** opens the shared native **Xác nhận tạo công việc** dialog
with the frozen edited payload and exact Workspace. Only **Xác nhận tạo công
việc** calls the existing atomic confirmation API. Pending controls block
duplicate clicks. Success displays actual returned Task links and refreshes the
current Workspace cache; there is no optimistic success, assignment or status
override, and no ordinary Task POST fallback.

If generation loses its response, explicitly retry the same frozen generation
key/body. If confirmation loses its response, the client first GETs the known
proposal; confirmed results recover the same Task mapping. Explicit resend of
the frozen confirmation is offered only after GET says AVAILABLE for the same
proposal ID/revision. A mismatch cancels the old confirmation and requires
review of current server content; route changes never retarget the frozen body.
Do not create a new batch to guess whether the previous confirmation committed. Expiry or an
unresolved recovery asks the User to inspect Tasks before starting over.

Queries include User/Profile/Workspace. Leaving or changing identity aborts old
requests and removes scoped AI cache; existing logout/session-expiry private
cache cleanup stays authoritative. Mutation still requires current backend
manager/original-actor authorization and session CSRF, even after preview.

Use the isolated suites for automated acceptance; they never seed persistent
development and do not call a live provider:

```powershell
.\scripts\test-frontend-integration.ps1 -Suite ai-generator
.\scripts\test-frontend-integration.ps1 -Suite ai-disabled
```

The enabled suite's `serve-ai` mode turns on fixtures only after checking owned
isolated PostgreSQL identity. The disabled suite uses the normal false default.
Current final-source frontend537/537 PASS24.35s/18 files; typecheck/Biome/build
exit0, build8.97s with an advisory >500kB chunk warning. Focused Generator27 and
Generator/Task51 checks also pass. Real enabled4/4 PASS49.5s, disabled1/1
PASS8.4s and onboarding3/3 PASS43.4s; launcher/Playwright/backend exits0 and
owned cleanup are verified. Four-size preview/dialog axe, keyboard/focus and
overflow checks passed; desktop preview/mobile dialog PNGs were visually
inspected. Foundation6/6 PASS43.6s and Workspace/Task7/7 PASS1.2m also passed,
actual launcher/Playwright/backend exits0/cleanup verified. Collaboration7/7
PASS1.3m, whole workflow1/1 PASS34.2s and account-security1/1 PASS23.2s complete
all eight real isolated Chromium suites: **30/30 PASS**, actual exits0 and
owned cleanup verified. Final read-only
development comparison at2026-11-02T05:25:34Z matches all29 table fingerprints,
schema/FKs/indexes/sequences/history/cluster identity and45 protected source
hashes. Development remains36 migrations/3 Users/2 Sessions/1 Profile/1 membership/
1 Workspace/1 Task/AI0; no persistent fixture or feature-flag change was used.
Final resource inspection at05:28:55Z found0 owned frontend/backend test
containers and0 owned networks. No unrelated process/resource was stopped.

The initial enabled-browser2/4 run and initial unit527/537 run are retained as
failures, followed by corrected final-source runs. Fixes cover an exact label,
stale identity/revision guards and the pre-existing Task-page test harness's
Auth boundary; no security assertion was weakened. Exact run/exit/cleanup
evidence belongs in [HANDOVER.md](HANDOVER.md). Existing FE05 acceptance below
is historical and does not prove P4-02C tests or manual development usage.
No manual development login/generation/confirmation is claimed. Existing FE05
manual Owner acceptance remains unverified. Review this fixture-only slice
before requesting any later implementation or feature enablement.

## HT-FE-P3-05 — Create Profile & First-Time User Onboarding

Status: **IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**,2026-11-02. The Owner now
approves first-party Profile creation only; Invitation UI and general membership
onboarding remain separate. HT-AI-P4-02C is reserved for future Generator UI.

An authenticated User with no Profiles sees **Bạn chưa có tổ chức nào** on
Dashboard or Tổ chức, with a working **Tạo tổ chức** link to protected
`/profiles/new`. Existing Users can create another Profile from the Tổ chức
header. The form has one supported field, **Tên tổ chức**, uses existing
teal/neutral shared controls, validates1–255 Unicode characters, retains drafts
on recoverable failures and prevents rapid duplicate submits. Errors are safe
Vietnamese messages with linked field errors and focused summary. Requests use
the existing API client's same-origin cookies and CSRF; no user/owner IDs.

Success201 seeds only the returned Profile detail, invalidates current Profile
list pages and navigates to `/profiles/{id}/workspaces`. That URL is the existing
active-Profile mechanism, not a new global store/localStorage selector. Refresh
retains URL scope and the backend revalidates access. **Tạo không gian** is then
resolved through existing server capability hints and Workspace creation; no
Workspace is created automatically. Existing Profile cards switch scopes.
Draft/request lifetime is bound to the current User and canceled on unmount or
identity change, preventing late replies from repopulating another User's cache.

Manual Owner acceptance after review, using the existing two-terminal startup
commands below:

If a backend terminal is already running, press Ctrl+C in that Owner-controlled
terminal and restart `.\scripts\start-backend-dev.ps1` from the repository root.
The launcher uses `--noreload`, so an existing process will not automatically
load this new POST. The agent stopped no Owner process and changed no credential.
In the second terminal, `cd frontend` and `npm run dev`; no migration/seed command.

1. Open http://127.0.0.1:5173 and log in through React.
2. With no Profiles, choose **Tạo tổ chức**, enter a valid name and submit once.
3. Confirm the new organization name and selected Workspace URL; choose
   **Tạo không gian**, enter its name and month, then submit.
4. Confirm the Workspace appears, refresh, open it and choose **Xem công việc**.
5. Open **Tổ chức**, confirm the Profile card, create another organization if
   desired and switch through its card. Log out when finished.

The agent does not perform these mutations on persistent development. Automated
acceptance uses isolated PostgreSQL and the shared launcher:

```powershell
.\scripts\test-frontend-integration.ps1 -Suite onboarding
```

Current targeted backend40/40/full662 passed with actual launcher/Python exits0
and cleanup. Frontend426/426, typecheck/lint/build and all six real isolated
browser suites25/25 passed (onboarding3/foundation6/work7/collaboration7/MVP1/
account1), every launcher/Playwright/backend exit0 and owned cleanup verified.
Final development row fingerprints/schema/sequences/history are unchanged:
36 migrations/ai.0001 applied,3 Users/2 Sessions/business0/AI0. All52 model/
migration/AI and19 tested changed-file hashes are stable; no test resources remain.
Exact evidence is in HANDOVER; historical395/22/643 are separate results.
No schema/migration, AI runtime, secret loading or persistent development test
data is part of FE05. **AUTOMATED VERIFIED / MANUAL OWNER CHECK PENDING.**
Separate valid POSTs can create separate Profiles with equal names: after an
uncertain network outcome, check Tổ chức before intentionally submitting again.

## Historical HT-FE-P3-04 verification

HT-FE-P3-04: **COMPLETE / OWNER REVIEW GATE**. MVP audit, account lifecycle
consumers, cohesive isolated UI acceptance and local startup are verified within
the approved scope. See FRONTEND_MVP_ACCEPTANCE.md and
HANDOVER.md for current scope and evidence. The Owner supplied local environment
configuration; launcher validation, Django check, read-only DB connection and
non-mutating direct/proxy smoke now pass. Earlier
completed FE03/API03A checkpoints below remain historical verification.

HT-FE-P3-01 foundation, FE02 Workspace/Task and FE03 collaboration UI, including
the Owner-approved HT-API-FE-P3-03A capability extension. One React SPA consumes
the existing Django/DRF APIs. Current verification/status is in HANDOVER.md.
Source now includes Deliverable Submit, Review Approve/Request Changes, existing
Comment author actions and personal Notifications. HT-API-FE-P3-03A is COMPLETE;
HT-FE-P3-03 is IMPLEMENTATION COMPLETE. Final regression verification passes;
stop at OWNER REVIEW GATE without starting another task. The API
extension adds five read-only flags; models, migrations, authentication, RBAC
and mutation workflow services remain unchanged. Project/AI remain outside scope.

## Stack and prerequisites

Node20.17+ and npm10+; verified locally on20.17.0/10.8.2 without replacing the
Owner's Node or Python installation. Use npm and the checked-in package-lock.
React19,strict TypeScript6,Vite6.4,ReactRouter7,Tailwind4,TanStackQuery5.
Vitest/TestingLibrary cover mocked units; Playwright/axe cover real isolated
browser integration. Biome is the lint equivalent: its maintained runtime works
on the installed Node; the initial older ESLint toolchain was removed before
completion. No Zod is needed for this small surface: transport read contracts
are validated explicitly at runtime in services/api/queries.ts.

Vite6.4 was selected for installed Node compatibility and its security-supported
branch, instead of bypassing newer tools' Node engine checks. See official
[Vite support policy](https://main.vite.dev/releases) and
[Node requirement change](https://v7.vite.dev/guide/migration).
Routes use ReactRouter's [declarative SPA mode](https://reactrouter.com/start/declarative/installation);
Tailwind uses its [Vite plugin](https://tailwindcss.com/docs/installation/using-vite).
Versions resolved by package-lock are authoritative. Future engine upgrades
belong to a deliberate dependency task, not an implicit backend upgrade.

## Local development

HT-FE-P3-04 adds a repeatable Windows launcher; Django settings still intentionally
read process environment, not a .env file automatically. Running bare
`python manage.py runserver` in a fresh PowerShell therefore reports missing
variables. Load the selected private file through the launcher instead.

Configure once, from the repository root, only if .env does not already exist:

```powershell
Copy-Item .env.example .env
```

Privately edit .env: supply a stable DJANGO_SECRET_KEY and the EXISTING
POSTGRES_PASSWORD, retaining the known development database/user/loopback values.
If either existing value is unknown, stop and recover it through the Owner's
normal private configuration process. Do not extract passwords from Docker
inspect, reset credentials, recreate venv/DB, run rollout helpers or migrate just
to start the website. Never repeat Copy-Item over an existing private .env.

The launcher accepts literal single-line KEY=value matching the sample. Only
whole-line # comments and blank lines are skipped. Values do not interpolate;
#, $, quotes and backticks inside values are literal. Do not add surrounding
quotes as shell syntax, export prefixes, inline comments or multiline values.
The file must be regular, repository-local and Git-ignored. All nine mandatory
Django/PostgreSQL names are validated together without displaying their values;
optional settings retain Django defaults. No need to enter27 variables each run.

Terminal1, from D:\da\HustlyTasker:

```powershell
.\scripts\start-backend-dev.ps1 -ValidateOnly
.\scripts\start-backend-dev.ps1 -Check
.\scripts\start-backend-dev.ps1
```

ValidateOnly checks file/required names/development endpoint, not Django or DB.
Check runs the existing backend/venv/Scripts/python.exe manage.py check; it does
not prove DB connectivity. Default starts Django at http://127.0.0.1:8000 with
--noreload; Ctrl+C stops it and code changes require a manual restart. Environment
is passed only to the child; parent PowerShell and security policy are not
modified. There are no automatic migrations, fixtures or credential generation.
Optional -EnvFile selects another ignored repository-local file; -Port changes
only the loopback HTTP listener. If changing port, match DJANGO_API_TARGET below.

Terminal2:

```powershell
cd D:\da\HustlyTasker\frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Non-mutating connectivity checks from a third terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/
Invoke-RestMethod http://127.0.0.1:5173/api/health/
```

Both should return status=ok; liveness does not prove DB readiness. Do not print
CSRF bootstrap response bodies or cookies into logs. Use browser login only with
the Owner's own authorized account; automated mutation tests use disposable
PostgreSQL through the integration runner, never persistent development.
At FE04 preflight no private .env existed. The Owner subsequently supplied the
configuration; the two configured fields were preserved exactly in the ignored
root .env and blanked in the tracked example. No credential was regenerated.
Current automated local verification: ValidateOnly0, existing-venv Django check0,
read-only PostgreSQL16.14/hustlytasker_db with35 migrations/no pending migrations,
3 Users/2 Sessions/0 business rows. Django8000 and temporary Vite5174 returned
health200 direct/proxy, CSRF bootstrap200 without token logging, anonymous me403
direct/proxy, scoped Profile403 and public registration OPTIONS200. No persistent
login or business mutation was performed. The smoke helper returned0; intentional
server termination returned native-1, not a claimed graceful server exit0.
Default developer frontend port remains5173. Manual Owner browser verification,
production, real email delivery and remote CI remain unverified.

Use the frontend origin consistently rather than switching localhost/127.0.0.1
while testing cookies. Optional Vite-only configuration, inside frontend/:

```powershell
Copy-Item .env.example .env.local
```

`DJANGO_API_TARGET=http://127.0.0.1:8000` is the only frontend setting. It is
read by Vite on the server and must be an HTTP loopback origin without path,
credentials, query or fragment. It is NOT a VITE_* public bundle variable.
There are no browser database credentials, authentication keys or LLM keys.
Do not add private credentials to frontend environment variables.

Development proxy sends `/api/` to Django and preserves Host (`changeOrigin:
false`), so Origin/Host and browser cookies stay same-origin without CORS,
wildcard credentials, trusted-origin expansion or CSRF settings changes.
Vite `server.cors=false` lets same-origin OPTIONS reach DRF instead of its own
CORS middleware returning a synthetic204. Django settings remain unchanged.
Static production deployment is not part of this task. A future deployment
must serve SPA files with navigation fallback and route `/api/` to Django
before that fallback, retaining secure cookie/HTTPS/proxy configuration.
The Vite dev/preview server is not a production deployment.

## Source map and routes

| Area | Responsibility |
|---|---|
| src/app | One route tree, protected routes, fatal UI fallback |
| src/features/auth | Single identity state machine, revalidation, cache cleanup |
| src/services/api | Fixed same-origin client, CSRF, safe errors, typed read contracts |
| src/layouts | Responsive sidebar/topbar, navigation, own account/logout |
| src/components | Shared semantic controls, native dialog, states, pagination |
| src/pages | Login/register/recovery/current-account verification, real-data overview, tenant and scoped Task pages |
| src/features/workspaces | Capability hints, Workspace forms/lifecycle and sanitized roster |
| src/features/tasks | Task metadata/child forms, deadline conversion and assignment |
| src/features/collaboration | Deliverable/Review reads and mutations, scoped Comment thread/forms |
| src/features/notifications | Personal feed, preview/count and confirmed mark-read |
| src/styles.css | Tailwind entry, shared semantic design tokens and responsive rules |
| e2e | Real HTTP/browser tests against isolated Django/PostgreSQL |

Public routes: `/login`, `/register`, `/forgot-password`, `/reset-password`,
`/403`, `/404`, fallback404. Protected routes include `/account`,
`/dashboard`, `/notifications`, `/profiles`, `/profiles/:profileId`,
`/profiles/:profileId/workspaces`,
`/profiles/:profileId/workspaces/:workspaceId`, and that Workspace's
`/tasks` and `/tasks/:taskId`. `/` redirects to dashboard
through the same auth guard. Return-to paths are local; external redirect
destinations are rejected. Only implemented navigation is enabled.

## Authentication, privacy and access

The shared client always sends credentials same-origin and no-store. It gets
a masked token from GET`/api/auth/csrf/`, holds it only in memory and sends
X-CSRFToken on unsafe requests. POSTlogin uses email/password; login success
invalidates the old token because Django rotates it. POSTlogout fetches fresh
CSRF when necessary. Mutations are never silently replayed after failure.
Browser-managed HttpOnly session cookies are not read by JavaScript, and no
password/session/token/private Query cache is persisted to localStorage or
sessionStorage. UI errors use controlled local text, not raw HTML/stack traces.

GET`/api/auth/me/` resolves initial identity before any private page/query mounts.
Focus, return to a visible document and a60-second visible-page interval
revalidate identity; private UI is hidden during that check. Expiry/uncertain
network identity cancels and clears private queries. Logout clears immediately
and only claims server-confirmed success when its request succeeds; failure
shows an unavailable state. Identity generation/abort guards reject stale
responses from previous sessions. Query caching is in-memory,staleTime0,gcTime0,
no retry, no persisted state; central auth handles focus revalidation.

DRF SessionAuthentication can return403 for anonymous users. A tenant403 probes
`/me` quietly: valid same-user session retains a stable permission error rather
than remounting/refetching forever; invalid/uncertain identity clears private
state. Tenant-safe404 is kept generic and does not reveal object existence.
Current backend permission/membership checks remain authoritative. Knowing an
ID or switching the UI context grants no access.

### Account lifecycle — HT-FE-P3-04

Registration sends email/username/password/password_confirm with optional names
to the existing POST /api/auth/register/. It neither logs in nor creates Profile
membership. Login links expose registration and recovery; the shared authenticated
navigation exposes /account for the current User only.

/forgot-password sends POST /api/auth/password-reset/request/ with email. The
neutral202 message explicitly does not confirm that an account exists or that
email delivery succeeded. /reset-password accepts a manually pasted masked token
and matching new passwords, sends the existing confirm contract, clears inputs/
stale CSRF after204 and revalidates identity to clear invalidated session data.
It does not auto-login; the user must sign in explicitly with the new password.

/account displays only /me identity and email_verified. Verification request
sends an empty object for the current session; confirmation sends only token.
A request202 never marks the email verified. Successful confirmation refreshes
server identity; legacy unverified Users keep existing permissions. Neither
verification nor recovery accepts an Invitation or grants tenant membership.

All forms reuse shared teal/neutral components, visible labels, focused linked
error summaries, static safe field errors, pending/duplicate guards and abort on
unmount. Password-manager autofill/paste is allowed. Tokens are password-type
inputs kept only in mounted form memory and POST bodies, not URLs/query keys,
browser storage or logs. No fake email link contract or real provider is added.
The current console backend intentionally cannot deliver security credentials;
real email requires a separately configured safe provider. Browser success tests
use only the isolated locmem adapter/mailbox, never production email.

Owner retains the MVP scope above. Invitation UI, Profile Creation and membership
candidate/onboarding management are OUT OF CURRENT TASK SCOPE / PENDING OWNER
REVIEW; their target product requirements remain. See FRONTEND_MVP_ACCEPTANCE.md
for exact API gaps and AI readiness proposals. No new backend/schema/RBAC rule.

Current frontend unit/contract395/395 PASS (14files,15.94s), typecheck0,
Biome52files0 and build6.65s0 (JS479.99kB/gzip139.09,CSS39.06kB/gzip11.00).
Initial typecheck found two unsupported ByRoleOptions in App tests; those test
selectors were corrected and the full checks rerun. All current real isolated
Django/PostgreSQL/Chrome suites pass:

| Suite | Result | Run ID |
|---|---|---|
| Cohesive business UI acceptance | 1/1 PASS43.6s | 6a1ec11fb62741aabcc330571015c828 |
| Account lifecycle/email adapter | 1/1 PASS22.4s | 77a73580faf34927b8970208eca6f658 |
| Collaboration | 7/7 PASS1.2m | 8a940dabeedc41ceaf63b8669f461b28 |
| Workspace/Task/Start | 7/7 PASS1.0m | e1470330e0904f9d92e5254324892455 |
| Auth/CSRF/tenant foundation | 6/6 PASS36.3s | 5d6f2f14dbbf4829ad54c0d054584d81 |

All22 browser tests have actual native launcher/Playwright/backend exits0 and
owned DB/container/network cleanup evidence. The cohesive case creates a Task
and Subtask, then assigns/starts/submits/reviews the parent through React;
the child remains PENDING, proving no status cascade. Comment CRUD, Notification
read and same-browser User switching are also performed through React.
Account registration/verification/reset use React plus the isolated delivered-mail
adapter; fixture setup and negative direct API probes are labeled separately.
No real email-provider success is inferred.

Responsive375/768/1440/812x375 landscape, native dialog focus/keyboard, overflow
and axe WCAG2/2.1AA checks pass with0 violations. Empty registration375, reset812
landscape and completed Task1440 screenshots were visually inspected. No manual
interactive Owner browser claim follows. Backend485/485 remains historical and
was not rerun because all144 protected backend/config/harness/dependency assets
are unchanged; no schema/migration or production action. FE04 is COMPLETE within
the retained MVP scope. Stop at Owner review without starting AI or onboarding.

Run each suite separately against fresh owned PostgreSQL fixtures:

```powershell
.\scripts\test-frontend-integration.ps1 -Suite acceptance
.\scripts\test-frontend-integration.ps1 -Suite account-security
.\scripts\test-frontend-integration.ps1 -Suite collaboration
.\scripts\test-frontend-integration.ps1 -Suite work-management
.\scripts\test-frontend-integration.ps1 -Suite foundation
```

New acceptance/account screenshots and paired evidence are Git-ignored under
.local_backups/HT-FE-P3-04/. Browser actions versus API fixture/negative probes,
final responsive/axe results, exit codes and cleanup are recorded in HANDOVER.

## Profile/Workspace contracts and states

The foundation uses five read contracts: current User envelope, paginated
Profile list, Profile detail, nested paginated Workspace list and Workspace
detail. Lists use count/next/previous/results; request page numbers locally
with server-default20/page, never follow arbitrary absolute next links.
Workspace.profile_id must match nested scope; nullable legacy period and
description are supported. ACTIVE/ARCHIVED are visible read states. Dashboard
counts come from the actual accessible Profile response; no fake analytics.
FE02 adds authorized Workspace/Task writes as detailed below. FE03 and API03A
add the bounded collaboration and personal Notification surfaces described
below. Profile writes, membership mutation and AI UI remain outside scope.
Loading skeletons, useful empty states, generic403/404, validation,
CSRF,409,429,5xx and network failures have explicit feedback/retry behavior.

## Design reference

Read [the shared master](design-system/hustlytasker/MASTER.md) and current
tokens before UI changes. ui-ux-pro-max was fully read and its CLI used for
design-system/focused UX/React/color/typography searches; unsuitable landing,
motion and native-only recommendations were not applied. Deep teal/warm
neutral/lime, self-hosted Vietnamese PlusJakartaSans, consistent spacing,
component states, native dialog and responsive rules are shared across pages.
Primary semantic control/keyboard/focus/contrast/reduced-motion checks are
applied and recorded in the verification checkpoint, not inferred from styling.

## Checks and real isolated integration

```powershell
cd D:\da\HustlyTasker\frontend
npm run typecheck
npm run lint
npm test
npm run build
```

`npm test` is explicitly MOCK FRONTEND/API CONTRACT testing; it does not prove
a real Django login. The actual HTTP/browser suite is run from repository root:

```powershell
.\scripts\test-frontend-integration.ps1
```

Requires Docker, existing dependency image hustlytasker-backend-tests:local
(built by the shared backend test launcher) and installed Chrome/Edge or a
Playwright-supported Chromium installation. The runner selects an installed
Chrome/Edge without modifying it. It creates a fresh unpublished PostgreSQL16
tmpfs service/internal database network, gates cluster+role+owned UUID database, applies
the existing migration chain only there and creates synthetic fixtures. Django
HTTP is published only on127.0.0.1:8001 via a second owned HTTP bridge attached
only to the backend; PostgreSQL stays internal and unpublished. This is needed
for host port publication on the verified Docker Desktop runtime. Neither
network is the development network. Vite runs on5173 with that proxy target.
Generated fixture credentials stay in process memory/env, never docs/logs.

Real tests exercise CSRF rejection/rotation, login/logout/me, private route
boundaries, nested tenant denial, current membership, session expiry and
read-only pages, plus responsive/axe/keyboard/native-dialog checks. Screenshots
of synthetic fixtures are retained ignored in .local_backups/HT-FE-P3-01/.
Cleanup gates exact UUID/repository/image/network/mount ownership and verifies
backend exit and owned DB removal before removing only test resources.
No persistent development credentials/network or Owner accounts are selected.
After hard interruption inspect exact labelled run resources; never use broad
Docker prune/down-volume or substitute development as a test target.

Current PASS/failure counts and visual inspection status belong in HANDOVER.md.
No manual authenticated E2E on persistent development, production deployment,
real email delivery or remote CI verification is implied by local isolated tests.

## Workspace and Task management — HT-FE-P3-02

Protected routes add `/profiles/:profileId/workspaces/:workspaceId/tasks` and
the nested `/:taskId` detail. Workspace list creates an authorized monthly
Workspace; detail edits metadata, confirms archive/restore and shows the
manager-only sanitized member roster. Period is chosen as month and sent as
YYYY-MM-01 at creation, not edited later. That FE02 slice did not include Profile
creation or membership mutation UI; FE05 separately adds only Profile creation.

Task list renders real title/description/status/priority/deadline, assignment
membership code and update time. Filters/sort/page go to the server. Local
"Tìm trong trang" searches only current-page titles. Root-only is a server
filter; detail's direct-child link selects parent_id. Filter dates use UTC day
bounds. No global search or aggregate Task dashboard is invented.

Detail requests one Task, paginated direct children and at most3 ancestors.
Breadcrumb shows root0/child1–3; a fourth child level is unavailable. Create
child fixes parent_id from current context. Each Task keeps its own workflow;
there is no completion/priority/deadline cascade or arbitrary status PATCH.
Metadata edit sends changed fields only; assignment is a separate action.
Empty deadline sends null; browser-local datetime is validated and converted
to UTC. Overdue is an indicator, not a new state. Collaboration UI is tracked
in the separately approved HT-FE-P3-03 section below.

Workspace/Task metadata form hints come from DRF OPTIONS.actions.POST, never
static Allow. Object-specific Start/Submit/Review/Comment actions instead use
the corresponding read-only flags described below. Hints default closed and
discard stale data after failed refetch. Backend always
revalidates writes. Queries/invalidation include Profile/Workspace. Forms keep
drafts on recoverable errors, prevent duplicate submit and abort UI requests
on unmount/scope switch. HTTP abort cannot undo a committed transaction;
unsafe requests never automatically replay.

### Identity/Start/assignment extension — HT-API-FE-P3-02A

The Owner approved resolving the two original FE02 API gaps. Task responses now
include a required boolean can_start, computed by Django from the authenticated
request, live tenant capability, current active User assignment and ASSIGNED
state. The client never compares global User.id with a ProfileMembership ID.
Start appears only with that hint in an active matching Workspace. It uses the
existing POST Start service with CSRF, pending/duplicate guards and safe errors;
no optimistic transition or automatic retry. Success invalidates the current
Task/list/child scope;403/404/409 refresh current scope and suppress stale action.
Backend revalidates every mutation regardless of the displayed hint.

Manager-only roster adds display_label and is_assignable without a new endpoint.
The selector uses the server eligibility flag and excludes the current assignee,
renders friendly labels, and submits the original ProfileMembership ID. Duplicate
labels receive a short membership suffix for disambiguation. Full-name labels
fall back to a safe membership code, never username or email. No global User ID,
phone or credential is added. Workspace member list uses the same labels with
existing role/activity information; the selector omits ineligible rows. Names
do not confer authority.

Type guards reject missing/invalid hint/label fields. Query/cache keys stay tenant
scoped; failed requests keep safe feedback, not a success status. Current results
and FE02 completion reconciliation are in HANDOVER.md. No schema, new role,
workflow change or dependency upgrade. Existing legacy CANCELLED is a status
display only; no cancellation action is introduced. Task dashboard analytics
are still unavailable and are not a blocker or an invented aggregate.

Both gaps are resolved and HT-FE-P3-02 is IMPLEMENTATION COMPLETE through the
approved HT-API-FE-P3-02A extension. Historical backend448/frontend224/browser7+6,
type/lint/build and responsive/axe checks passed; exact runs are in HANDOVER.
That historical extension stopped at Owner review before FE03 was authorized.
UI work reused ui-ux-pro-max's full
instructions and the existing master; the actual focused React async-error
search informed safe feedback/pending behavior. No theme/component redesign.

Run separate fresh isolated suites to retain existing login throttles:

```powershell
.\scripts\test-frontend-integration.ps1 -Suite foundation
.\scripts\test-frontend-integration.ps1 -Suite work-management
```

Default remains foundation. Work screenshots live ignored under
`.local_backups/HT-FE-P3-02/screenshots/<run-id>/`. Foundation retains FE01 path.
All mutation flows use disposable synthetic fixtures, never development users.
If a personal Django terminal lacks DJANGO_ENVIRONMENT/SECRET_KEY/DEBUG/
ALLOWED_HOSTS/POSTGRES_DB, follow README's private environment setup. This is a
separate development setup issue; do not regenerate credentials, recreate venv,
relax backend security or reset/migrate development to run frontend tests.

## Collaboration — HT-FE-P3-03

Task/Subtask detail reuses existing overview, assignment, Start and hierarchy.
It now includes `#deliverables` and `#comments` sections, with per-Task paginated
revision cards, nested Review status/feedback and comment thread/composer.
Review detail is shown from the existing Deliverable row; no fake detail route.
Safe absolute HTTP(S) product URLs open with noopener/noreferrer/no-referrer;
other supplied content remains escaped text, never executable HTML or links.
No storage/upload, rich text, mention or attachment system is added.

Comment text validates4,000 Unicode code points, rejects NUL/unpaired surrogates,
shows counter/inline errors/focused summary and preserves drafts on recoverable
failures. POST OPTIONS verifies current commenter role; writes still require CSRF.
Each Comment response now supplies required `can_edit`/`can_delete` booleans
computed by the backend for the current request. These support existing comments
after reload, pagination or navigation; temporary POST-response ownership proof
has been removed. The UI never maps global User IDs to membership IDs or infers
authorship from a display name. Current authorized authors may edit; an authorized
author or manager may delete. Managers cannot edit another author's text and
tombstones expose neither action. Delete requires confirmation. Confirmed edit/delete
cancels older Comment GETs and updates/redacts all matching cached copies before
refetch; deleted retained content is never rendered. No optimistic success.

`/notifications` is a protected personal feed, with all/read/unread filter,
server pagination, explicit refresh and mark-read. Topbar bell opens a native
modal preview of at most5 rows from the first server page. Badge count is the
server's own readable-target unread count; contextual atomic status text avoids
announcing a bare number. Feed is User-keyed and spans the User's currently
authorized Profiles, not a fabricated current-Workspace aggregate. Header/page
queries refresh on mount and mutations, with the existing auth focus/visibility
revalidation; no new polling/WebSocket/worker infrastructure.

Mark-read changes only after server confirmation. On denied target, cached rows
for that Workspace are redacted and feed/count revalidated. Failed refresh hides
stale private rows/count. Navigation is a SPA Task path derived from validated
Profile/Workspace/Task UUIDs; raw server target_url is never followed. Opening
the target rechecks current scoped read access. No read-all or mark-unread API
is invented. Logout/expiry uses the existing AuthProvider cancel+cache clear.

All collaboration keys include User/Profile/Workspace/Task; notification keys
include authenticated User. Unsafe requests reuse the single memory-CSRF client
with no automatic replay. Existing tenant403 quiet identity probe stays finite.

### Collaboration mutation extension — HT-API-FE-P3-03A

Verified contracts and the historical gap matrix are in
[FE03_CONTRACT_MATRIX.md](FE03_CONTRACT_MATRIX.md). The separately approved
extension resolves all three gaps in source without a new endpoint:

- Task `can_submit`: current assigned active Editor in an active authorized
  scope, Task WORKING and no unresolved PENDING/SUBMITTED Deliverable.
- Deliverable `can_approve`/`can_request_changes`: current reviewer/manager
  authority, Task REVIEW, this submission SUBMITTED and latest by created_at/id,
  non-self uploader and no existing Review row.
- Comment `can_edit`/`can_delete`: current commenter authority, nondeleted row,
  author for edit and author-or-manager for delete.

Every flag is a required runtime-validated boolean bound to authenticated request
and verified tenant context. Missing or malformed fields fail closed. Hints do
not grant durable authority: the existing locked mutation service checks live
membership, assignment and state again at POST/PATCH/DELETE time. OPTIONS alone
is not used as proof for Submit, Review decisions or existing Comment authorship.

`CollaborationActions` reuses native Dialog and the established work-form/error
patterns. Submit sends `{file_url}` as text or URL (maximum500 Unicode code
points), not a file upload. Approve sends optional `{comment}`; Request Changes
requires nonblank `{comment}`. Forms reject NUL/unpaired Unicode, retain drafts
and focused linked errors on failure, prevent duplicate submission, abort on
unmount and disable dismissal while pending. No success or Task status is shown
optimistically. Safe400/403/404/409 responses remain visible; unsafe requests do
not automatically retry. A stale hint never overrides the server's decision.

Confirmed success invalidates the current Profile/Workspace Task scope, the
User/Profile/Workspace/Task collaboration scope and that User's Notification
prefix. Failed authorization refreshes the scope without displaying stale
private content. Comment deletion still cancels older reads and redacts cached
pages before refetch. Logout/expiry retains the single AuthProvider's cache clear.

No Deliverable update/delete/upload endpoint is invented; new submissions after
Request Changes use the existing revision-creation workflow. No self-review,
revision, RBAC, AuditLog or Notification transaction policy changes. There is no
schema/migration change. Project remains PENDING OWNER DECISION.

Historical API03A resume checks: frontend356/356 (12files,41.49s), strict typecheck exit0,
Biome46files exit0 and productionbuild6.69s exit0 (JS465.75kB/gzip135.48kB,
CSS39.06kB/gzip11.00kB). These local unit/contract/build checks are separate from
the current real PostgreSQL/Django/Chrome collaboration7/7 PASS (1.3m,
runff6abc6459954d6d83f47ec94c426a62). Native launcher, Playwright and backend
exits0 and owned database/container/network cleanup are evidenced. Actual React
Submit/Request Changes/resubmit/Approve and a separate fresh Submit/Approve
flow pass, as do existing Comment edit after reload/navigation, moderation,
Notification actions, revocation and expiry. Full isolated PostgreSQL485/485
PASS (231.054s, run3b2abcd913324644b6240bfc49ca1c18), work-management7/7
PASS (1.1m, run3074e74939f84f3b8039665dab7196ba) and foundation Auth/CSRF/tenant6/6
PASS (43s, runc125145b536b480badeccfba582f4c90) complete the regressions. Actual
native/Python/Playwright/backend exit0 and owned cleanup are verified for their
respective runners. Final E2E-spec typecheck/lint also return0. All three gaps
are closed and FE03 is IMPLEMENTATION COMPLETE; HANDOVER.md is the authoritative
final evidence and OWNER REVIEW GATE. No next task is started automatically.

UI UX Pro Max's full instructions and the unchanged master were read. Actual
focused `error summary validation --domain ux` and `async form error --stack react`
searches informed linked focused errors, inline messages, caught asynchronous
failures and pending feedback. Recommendations did not introduce a new theme or
replace existing mutation/state handling with a framework-wide refactor.

```powershell
.\scripts\test-frontend-integration.ps1 -Suite collaboration
```

Run foundation/work-management/collaboration separately on fresh owned isolated
PostgreSQL instances; each preserves existing login throttles. Collaboration
tests distinguish fixture/API setup from mutations actually performed through
React. The earlier FE03 API-driven Submit/Review run is historical and does not
prove the newly added mutation UI. The current API03A run exercises actual Submit,
Request Changes and Approve dialogs, with axe WCAG2/2.1 AA0 violations, native
keyboard/focus checks and no overflow at375/768/1440 and812x375 landscape.
24 screenshots are retained; Submit375, RequestChanges812 landscape and
Approve1440 were visually inspected. Screenshots remain ignored under
`.local_backups/HT-FE-P3-03/`; current API03A logs/exit evidence are under
`.local_backups/HT-API-FE-P3-03A/`. Exact final
counts, exits, cleanup and preservation evidence are in HANDOVER.md.
