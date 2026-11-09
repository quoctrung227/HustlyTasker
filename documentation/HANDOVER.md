# HUSTLYTASKER HANDOVER

## Current checkpoint — 2026-11-09 — HT-FE-INVITATION-DELIVERY-FIX-01 OWNER REVIEW GATE

**APPLICATION FIX VERIFIED — REAL EMAIL CONFIGURATION PENDING OWNER.**
Investigation and safe UI fixes are verified. Genuine delivery remains blocked
by Owner SMTP/provider configuration and separate real-send authorization.
Do not call this genuine-email completion or silently enable simulated delivery.

Owner reports real development POST Profile invitations503/generic delivery
unavailable and no visible row. Preserve initial CLEAN main/0f71ce502377c032c84fd4adc067370ff9b0e4c9;
770 originals hashed in ignored .local_backups/HT-FE-INVITATION-DELIVERY-FIX-01/.
No persistent development write/migration, AI flag/call, real external mail,
credential change, commit/push or deployment authorized.

ROOT CAUSE VERIFIED: existing .env loader + existing venv Django settings
preflight reports development, mailer_kind console, credential-email preflight
false; SMTP host/username/password absent. Only presence/classification was
emitted, no .env values. An initial unprivileged venv run exited103; permitted
read-only elevated diagnostic exited0 with no stderr/network/send. Template
inspection earlier printed prefilled .env.example values once; do not repeat
that raw read or claim all template output was sanitized. Credentials unchanged.
Console/dummy/filebased are intentionally rejected by common/email_delivery.py
to prevent credential-token logs/false delivery. create_profile_invitation checks
this inside atomic BEFORE token/Invitation/audit creation. Do not weaken guard
or silently use locmem to pretend genuine email works.

READ-ONLY DEVELOPMENT: same original container/volume/loopback/database identity
verified; current baseline29 tables/36 migrations/5 Users/2 Sessions/2 Profiles/
2 ProfileMemberships/1 Workspace/1 Task/4 AuditLogs. Invitations0 and invitation
audits0 (no PENDING/FAILED hidden); ai.0002 unapplied. This is newer Owner data,
not the previous4-User/1-Profile checkpoint. Snapshot/aggregated Invitation states
stored privately as development-before.json / invitation-inventory.json.
Existing development-named logs were scanned for the static error marker only;
no matching stored marker found, Owner interactive terminal log not accessible.
No persistent POST replay was attempted. Source+actual settings preflight+empty
Invitation/audit inventory identify pre-insert failure rather than postcommit.

POSTCOMMIT PATH IS DIFFERENT: configured transport failure after transaction
on_commit keeps PENDING+delivery FAILED and audit, then returns generic503.
Backend/frontend lists do not filter delivery FAILED. Existing pending create
conflicts409; resend rotates ID/token and revokes old row, no automatic retry.
No backend runtime defect found; real SMTP setup requires Owner configuration.

IMPLEMENTED AND VERIFIED:
- New test_invitation_delivery_api.py10 real-commit/fake transport tests cover
  preflight/postcommit503, list visibility/duplicate/resend and auth/CSRF. Backend
  Invitation suite48/48 PASS60.654s, launcher/actual Python0 independently recorded;
  pip/Django/model drift/isolated full-chain/owned cleanup PASS. Backend runtime
  settings/common sender/services/views unchanged; no full backend rerun needed.
- OrganizationMembers.tsx/test fix explicit mutation page reset
  to1 (new/replacement/FAILED rows otherwise offpage), persistent truthful resend
  error notice and configuration-aware503 recovery without hiding commit doubt.
  Normal refetch must preserve current page/form; no new API/RBAC/schema.
- Existing frontend_integration.py/test-frontend-integration.ps1
  + new invitation-delivery-failure.spec.ts. Dedicated test-only serve mode uses
  ownership-checked locmem fail-once for synthetic recipient, never SMTP/development.
- Seven source/config/test files frozen in tested-source.json, including only
  clarifying comments in .env.example; every original assignment/value matches
  HEAD (template-preservation.json). Private .env/settings/credentials unchanged.
  Final component32/32
  PASS15.69s; typecheck/Biome86files/build8.73s exit0. Earlier focused150 run had
 145 PASS/5 FAIL because pagination helper retained a detached Page1 nav after
  loading Page2; fixed test-only by reacquiring live navigation, with all row/
  draft/no-retry/error assertions retained. attempt-1 logs remain, not PASS.
- Root owns diagnostics, runners and documentation. Full skill/master previously
  read; actual offline UIUX error-recovery/feedback/accessibility search applied.

### Final actual test evidence

| Check | Actual result |
|---|---|
| Invitation PostgreSQL |48/48 PASS60.654s; run1c7bbea18b8f4eb8bd4923e5a055eb3d; launcher/actual Python0, dependency/Django/drift/isolated full chain and owned DB cleanup PASS |
| Final component |32/32 PASS15.69s |
| Full frontend (one run) |908/908 PASS34.53s,26 files, launcher0 |
| Final quality | TypeScript/Biome86files/build exit0, build8.73s; existing575.80kB chunk advisory retained |
| Real fake-delivery browser |2/2 PASS11.6s, run7e208697293644eda647ebe746731131; real HTTP503 commit/FAILED/reload/duplicate409 and UI resend200/new ID/fake SENT/replay409 |
| Existing Profile Members |4/4 PASS43.7s, run50f59422dc2244dcaa4606a9db587747 |
| Existing Workspace access |4/4 PASS36.4s, run5fbbaa8a162f43d390477bb4a2ccd6fa |
| Existing Task stability |4/4 PASS22.6s, run82a615665d004214b7f5a3fe4eccc488 |
| Existing Auth/CSRF/tenant |6/6 PASS44.9s, run1b315509f1414b0baa71463e81039907 |
| Browser exit/cleanup |20/20 final cases, every launcher/Playwright/backend0; owned DB/resources removed |

New browser positives use real React/Django/isolated PostgreSQL and private
locmem fail-once transport, not mocked HTTP. It allows exactly one expected
Invitation503 while other500s still fail. It never contacts SMTP or proves
mailbox delivery. First failure-browser attempt had1 PASS/1 FAIL due test-only
resend201 expectation; actual source/docs say200. Corrected exact assertion,
kept all rotation/FAILED/duplicate/replay/no-auto-retry checks and retained logs.
The initial focused150 run's5 stale-nav failures described above are also kept.
No failed attempt is reported as PASS. Other browser suites and full backend
were not rerun; prior863/902/18 remain historical. Backend application runtime
is unchanged, so48 targeted real-commit/security regressions are proportional.

### Final preservation and changed files

At2026-11-09T09:15:53Z final READ ONLY snapshot exactly matches all original
29-table data/schema/constraints/indexes/sequences/history/cluster properties,
excluding transient connections.36 migrations/5 Users/2 Sessions/2 Profiles/
2 memberships/1 Workspace/Task/4 AuditLogs retained. WorkspaceMember/Invitation/
AI0, invitation audit0. ai.0002 remains UNAPPLIED and its three tables absent.
Same original container/volume/loopback verified; no development service restart,
fixture, rollback, schema or credentials change.0 owned containers/networks
remain across the backend and all6browser attempts (7groups total).
770-file comparison:0 missing/unexpected changes, all7 final hashes stable;
backend runtime/models/migrations/AuthProvider/Workspace/AI/AGENTS/README preserved.
All template assignments unchanged; .env.example comments alone explain the
console guard. Private .env was read only through the approved loader into
process memory for presence/preflight checks, not modified or echoed.

Task changes13 files:7 source/config/test and6 docs. Existing:
.env.example (comments only); frontend/src/features/members/OrganizationMembers.tsx
and OrganizationMembers.test.tsx; scripts/frontend_integration.py and
scripts/test-frontend-integration.ps1. New: backend/apps/workspace/test_invitation_delivery_api.py
and frontend/e2e/invitation-delivery-failure.spec.ts. Docs: HANDOVER,FRONTEND_GUIDE,
PROGRESS,CHANGELOG,PROJECT_ROADMAP,REQUIREMENT_STATUS. No source settings/common
mailer/services/views/filters or API contracts changed. Ignored evidence directory
contains sanitized settings/presence/log-review, aggregate Invitation inventory,
before/after snapshots, template/hash proofs, process receipts and cleanup.
Final local-link/whitespace checks are recorded in documentation-check-result.json.

### Exact safe continuation / Owner input

Real SMTP remains UNCONFIGURED/UNVERIFIED. Owner must select an approved SMTP
service/relay, privately fill the exact variables in FRONTEND_GUIDE and restart
the existing --noreload backend. ValidateOnly/Check verify syntax/Django only,
not SMTP auth or delivery. Never paste passwords here or change unrelated Django/
PostgreSQL credentials. No paid service/account/key was created or selected.
Before any genuine delivery test, get explicit Owner authorization naming the
intended recipient/send. Only then manually create a new invitation (current
development has none), or resend a future persisted pending row after checking
history. Check SMTP acceptance and actual recipient mailbox separately.
Until that configuration/authorization arrives, do not repeat the development
POST, send mail, bypass the guard or claim the503 is gone. Application work in
this scope is finished; no further autonomous task/rollout is authorized.
**STOP: HT-FE-INVITATION-DELIVERY-FIX-01 — OWNER REVIEW GATE.**

---

## Historical checkpoint — 2026-11-09 — HT-FE-WORKSPACE-MEMBERS-01 OWNER REVIEW GATE

**IMPLEMENTATION COMPLETE — OWNER REVIEW GATE.** No implementation blocker in
this approved scope. Owner manual website acceptance and real email remain
unverified; no next task, migration rollout or deployment has started.

Owner authorizes minimal Workspace access/member React integration and any
essential migration-free API gap only. Initial repository is CLEAN on main,
HEAD c835904d4dca1b75299e0b07b9317c044e05c699 (Owner committed prior work).
765 original file hashes/status are Git-ignored under
.local_backups/HT-FE-WORKSPACE-MEMBERS-01/. No commit/reset/stash/credentials,
development writes/migrations, AI flag/provider, or deployment authorized.
ai.0002 must remain UNAPPLIED. Preserve Members-01 and Task stability completion.

AUDIT DONE — source-backed matrix shared before code:
- Real WorkspaceMember(User FK, unique workspace+user), ADMIN/MEMBER(Editor)/
  VIEWER; legacy OWNER fails closed. Profile Owner/Admin inherit all same-Profile
  Workspace read/management without explicit rows. Profile MEMBER needs an active
  supported WorkspaceMember; no automatic grant on Profile acceptance/create.
- Profile Owner/Admin assign/manage all3 Workspace roles. Workspace ADMIN only
  MEMBER/VIEWER and cannot update/revoke existing ADMIN. No invented last-WS-Admin
  rule or target-Profile-Owner protection; removing an explicit manager row does
  not remove inherited Profile authority. Archived managers may read, not mutate.
- Existing GET/POST members + PATCH/DELETE members/{membership_id} are reused.
  POST target_profile_membership_id/role =>201 new,200 reactivate,409 duplicate;
  PATCH role=>200, DELETE soft revoke=>204. Current services lock/revalidate/audit.
- Tasks only assign active Profile MEMBER + Workspace MEMBER; actual current
  assignment/state still required for execution. Revoke/downgrade preserves
  Task/TaskAssignment/Deliverable/Review/status; regrant can make old active
  assignments effective again. No auto-unassignment is claimed or added.

IMPLEMENTED AND VERIFIED:
- Backend workspace access/serializers/views/urls, new test_workspace_access_api.py
  (24 tests) and additive expected DTO fields in workspace/test_write_api.py and
  tasks/test_identity_api.py. New GET member-candidates and GET members capability envelope;
  no models/migrations/services changes. Active same-Profile candidate identity,
  no active WS row, sanitized labels and role ceilings; archived candidates empty.
- Extended WorkspaceMembers.tsx + new34 tests reuse the inline section,
  native dialogs, User/Profile/Workspace scope, nonoptimistic grant/role/revoke.
- New workspace-access.ts +67 tests reuse the existing transport/CSRF. Tenant
  page adds a discoverable #workspace-members anchor and current User scope;
  safe static role/target errors, new isolated runner suite and4-case real E2E.
  No second API client, route/store or invitation-by-email workflow.
- Root read full skill/master and executed offline UX confirmation/success search
  and React async-cleanup searches via existing dependency image. Existing
  tokens/keyboard/dialog patterns retained. Native fieldset action grouping and
  one small CSS reset preserve existing spacing without a new theme.
  No new design system, SDK or infrastructure. Local Python PATH absence is
  bypassed with existing isolated Python image, not venv installation/recreation.

READ-ONLY DEVELOPMENT BASELINE: original container49ef9315..., volume
docker_postgres_data,127.0.0.1:5432,hustlytasker_db,PG16.14/Engine29.8.2 verified.
29 tables/36 migrations/4 Users/2 Sessions/1 Profile/membership/Workspace/Task/
3 AuditLogs; WorkspaceMember0,Invitation0,AI0; ai.0002 unapplied. Snapshot stored
as development-before.json; never print its row hashes/whole payload.

### Actual verification and retained earlier attempts

| Check | Actual current-task evidence |
|---|---|
| Backend targeted |95/95 PASS9.634s, run78fe5a21db67485b929f1c2b46b5d075 |
| Full isolated backend (once) |863/863 PASS294.428s, run748db0386bde47ac99acb1dea2aeb720 |
| Backend safety/checks | Both launcher/actual Python0 independently recorded; pip/Django/model drift/graph/full isolated chain and owned DB removal PASS. PG137 is intentional disposable-container cleanup |
| New frontend API |67/67 PASS3.76s, mocked DTO/transport checks, launcher0 |
| Final Workspace UI |34/34 PASS12.40s, includes final semantic markup, launcher0 |
| Broader frontend (once) |902/902 PASS51.11s,26 files, launcher0; before final semantic-only fieldset/CSS reset. No mutation handler/business logic changed afterward |
| Final quality | TypeScript/Biome85 files/build exit0, build8.58s; existing575.27kB chunk advisory remains, no unrelated bundle refactor |
| Workspace real Chromium |4/4 PASS39.1s, runab941585c1e94477ae8d1d951e04a374, first run |
| Profile Members regression |4/4 PASS46.3s, runcfcf1c4def564696af6ca5a9c3446dd8 |
| Task stability regression |4/4 PASS20.3s, run9a56ad93957241c3b627f408c2e89b85 |
| Auth/CSRF/tenant foundation |6/6 PASS45.3s, runf5ccc4c5d8ee402fa07076269b4d6e9e |
| Browser exits/cleanup |18/18 actual Chromium cases, each launcher/Playwright/backend0 and owned DB/resources removed |
| Responsive/accessibility |375/768/1440/812x375 keyboard/focus/reflow/reduced-motion/axe PASS;375/1440 screenshots visually inspected |

Full frontend source hashes and exact two-file semantic follow-up are retained
as frontend-full-source.json / frontend-semantic-followup.json. Final34, quality
and all18 browser tests verify that last markup; broad902 is not misrepresented
as running again on an identical final hash. All16 final source hashes match
tested-source.json; backend7 matches backend-tested-source.json.

Initial backend72-discovery attempt failed on test import/required Task fixture
and additive response-envelope expectation; fixed test-only. Initial focused
frontend179 ran173 PASS/6 FAIL: corrected tests assert absence of private data
rather than disabled-query metadata, and wait for actual batched DOM/effects.
All hidden-state/abort/stale-submit assertions remain. Initial quality fixes
remove invalid Testing Library exact options, make error-focus dependencies real
and use native fieldset grouping/CSS reset. No suppressions or policy weakening.
attempt-1/attempt-2/before-semantic logs remain; no failed attempt is called PASS.

The new browser journey performs real React invitation/registration/acceptance,
Workspace Editor grant, Task create/assign/Start, Viewer/Editor update and revoke.
Read-back/negative authorization probes alone use direct API. Locmem code
extraction is private test-only and in memory; no external email/provider calls.
Revoke removes stale recipient content/returns404 while Task/assignment remain.
Same-node grant/Task forms survive real focus/visibility refresh. Other old
collaboration/work-management/AI browser suites were not rerun; their prior
results stay historical, while full current backend/frontend regressions pass.

### Final preservation and files changed

At2026-11-09T08:17:28Z the READ ONLY development snapshot exactly matches every
original29-table data/schema/constraint/index/sequence/history/cluster property,
excluding transient connections.36 migrations/4 Users/2 Sessions/1 Profile/
membership/Workspace/Task/3 AuditLogs retained; WorkspaceMember/Invitation/AI0.
ai.0002 remains UNAPPLIED with its three tables absent. Original container,
volume and loopback binding verified; no services/volumes restarted or deleted.
All seven isolated backend attempts/browser runs have0 owned containers/networks.
765-file comparison has0 missing/unexpected changes;16 frozen code hashes match.
AI/models/migrations/services/AuthProvider/AGENTS/README and other source preserved.
No .env/credentials read, persistent fixture, AI flag/call, commit or push.

Task changes26 files:16 code/test and10 affected docs. Existing backend:
apps/workspace/{access,serializers,views,urls,test_write_api}.py and
apps/tasks/test_identity_api.py; new apps/workspace/test_workspace_access_api.py.
Existing frontend: src/features/workspaces/WorkspaceMembers.tsx,
src/pages/tenants.tsx,src/services/api/client.ts,src/styles.css. New frontend:
src/features/workspaces/WorkspaceMembers.test.tsx; src/services/api/workspace-access.ts
and workspace-access.test.ts; e2e/workspace-members.spec.ts. Existing runner:
scripts/test-frontend-integration.ps1 (suite mapping only; no new fixture setup).
Docs: HANDOVER,PROGRESS,PROJECT_ROADMAP,REQUIREMENT_STATUS,CHANGELOG,
API_DOCUMENTATION,RBAC_DESIGN,FRONTEND_GUIDE,PROJECT_CONTEXT,FRONTEND_MVP_ACCEPTANCE.
Ignored evidence holds all receipts, snapshots/hashes, cleanup and final link/
whitespace verification. No new database schema documentation is needed.

### Limits and exact next step

REAL EMAIL DELIVERY NOT VERIFIED; invitation tests use locmem. Profile role/
remove, recipient inbox/preview, live AI, production and remote CI are not newly
implemented/verified. Broader frontend semantic-follow-up distinction above is
intentional; no extra full-suite repeat was needed for two markup-only files.
Manual Owner website acceptance remains PENDING. Existing process-local throttle
and large bundle limits remain; no production-ready claim.

Owner next follows the Workspace section in FRONTEND_GUIDE: invite/explicit
Profile accept, open intended Workspace, grant Editor, assign/Start, confirm
Viewer update/revoke and verify access/history. Those real development writes
were NOT performed by the agent. No code work remains in this approved task.
Suggested later priority is Owner acceptance then separately scoped Profile
membership role/remove governance/API/UI; do not invent those contracts here.
Await a new Owner instruction. Do not rerun unchanged tests/start another task
or apply ai.0002. **STOP: HT-FE-WORKSPACE-MEMBERS-01 — OWNER REVIEW GATE.**

---

## Historical checkpoint — 2026-11-08 — HT-FE-MEMBERS-01 OWNER REVIEW GATE

**IMPLEMENTATION COMPLETE — OWNER REVIEW GATE.** Manual Owner website acceptance
and real email delivery remain unverified. No next task or rollout has started.

Owner authorizes React organization Members/Invitation integration and a minimal
migration-free additive API only if needed. Preserve all existing dirty work on
main/32ccad220bee20540ba7a0e0f6f532250139d48c. Initial757 file hashes/status are
Git-ignored in .local_backups/HT-FE-MEMBERS-01/. Original development identity/
volume/loopback verified; read-only baseline29 tables/36 migrations/4 Users/
2 Sessions/1 Profile/membership/Workspace/Task/3 AuditLogs/0 Invitations or AI.
No .env/credential or development write. ai.0002 remains UNAPPLIED; no AI04D,
new schema/migration, provider flag/call or deployment authorized.

AUDIT DONE: existing Invitation list/create/detail/resend/revoke/accept/decline
are real, session+CSRF protected, role/tenant/recipient checked. No Profile roster
API, recipient inbox/preview or Profile membership role/remove API existed.
Profile Owner can invite ADMIN/MEMBER; Profile Admin only MEMBER; no OWNER invite.
Workspace Admin is not Profile governance. Recipient must be the current active,
unique normalized email identity and possess a sent/unexpired secret; global
email verification is independent, not required for current accept/decline.
Accept additionally revalidates original inviter authority; decline does not.

IMPLEMENTED AND VERIFIED:
- Backend4 source files add GET/HEAD/OPTIONS /api/v1/profiles/{id}/members/,
  sanitized paginated same-Profile membership roster and current invitation
  capability envelope. Existing Owner/Admin management authority reused;
  ordinary Member403, outsider404, archived readonly. No membership write/newrole.
  New test_profile_members_api.py13 tests; no model/migration/AI changes.
- New members.ts/test strict DTOs and User/Profile cache keys; API75/75 PASS3.36s
  (fresh), not a whole frontend/backend PASS. Invalid route keys are opaque;
  HTTP helpers still validate IDs. Token never enters a key/cache/storage/URL.
- OrganizationMembers.tsx/test adds roster/history, invitation form, explicit
  revoke confirmation and resend for PENDING/EXPIRED. Backend flags/role ceilings,
  truthful QUEUED/SENT/FAILED delivery, normal-refetch draft preservation,
  scope/user aborts, CSRF recovery and real permission-loss handling.
- New pages/members.tsx/test provides protected /invitations/respond manual
  masked-token form, explicit accept/confirmed decline and generic409. Profile
  pages expose Members/response links; login/signup carry only the fixed response
  path, never a token, and registration still does not auto-login. Query/fragment
  credentials are not ingested. Existing stable AuthProvider remains unchanged.
- Pagination gains an optional accessible label, client gains two static safe
  field messages. Existing test runner gains members suite; private locmem-only
  mailbox bridge adds invitation purpose for fixed synthetic acceptance identity.
  New real browser spec4/4 PASS38.6s; captures token only in Node memory and never
  external mail. No real email delivery claim.

VERIFIED CHECKPOINT: targeted backend51/51 PASS56.587s; full isolated PostgreSQL
839/839 PASS245.158s (one run), dependency/Django/drift/graph/full-chain/cleanup
checks PASS. Both launchers0; full Python child0 independently recorded. The
targeted child's Docker exit event was not retained; do not infer independent
child-exit proof from its successful launcher/51-test summary. Final frontend
801/801 PASS23.61s; focused142/142 PASS13.73s, API75/75 PASS. Typecheck/Biome/build
exit0. Members Chromium4/4 PASS38.6s and Task stability4/4 PASS20.9s; respective
runs ff576a67eb2a483397844103d1eb18c8 / 3c516c63055f4dc8a47238b1120fd5c9.
Each browser launcher/Playwright/backend0 with owned database/resources removed.
Members375/768/1440/812x375 reflow/keyboard/axe PASS;375/1440 PNGs inspected.
Full UI skill/master read and focused offline confirmation/async-cleanup searches
applied. No new style/tokens. Independent read-only security review found no
material defect. Historical689/21/826 are not current results.

Foundation6/6 PASS36.0s, run07e121e66e6d4fd4a55542c2706761d5, completes14/14
current real-browser tests; launcher/Playwright/backend0 with owned DB removal.
Only deliberate negative probes/read-back use direct API calls; management,
registration/login, accept/decline/resend/revoke use real React interactions.
Invitation codes are extracted only in memory from the private locmem test bridge.
No external mail/provider or persistent development write is involved.

### Final evidence and preservation

- Ignored .local_backups/HT-FE-MEMBERS-01 holds per-check stdout/stderr and
  retained-process exit receipts; Backend-child-exits.json independently records
  full backend Python0. PostgreSQL137 is intentional isolated cleanup, not a
  Django test failure. The targeted child's independent event is unavailable.
- First targeted frontend run140/142 failed only on two inaccurate split-label
  assertions; corrected to actual scoped role/status text and pending-until-server
  semantics. Initial lint2 errors/3 warnings fixed with semantic focus Button,
  equivalent NUL validation and explicit test guards. No policy/assertion
  suppression. attempt-1-Targeted / attempt-1-Lint evidence remains retained.
- Final full839 run includes all13 new roster tests, Authentication/Invitation,
  Workspace/RBAC/Task/Review and existing AI regressions. pip check, Django check,
  makemigrations --check --dry-run and isolated graph/full-chain checks pass.
  Development migrate --check is not claimed: candidate ai.0002 is intentionally
  pending and was applied only by the isolated test migration chain.
- At14:48:54Z the final READ ONLY snapshot exactly matches all original29-table
  row fingerprints/schema/constraints/indexes/sequences/history/cluster properties,
  excluding transient connections.36 migrations/4 Users/2 Sessions/1 Profile/
  membership/Workspace/Task/3 AuditLogs retained; WorkspaceMember0, Invitation0,
  AI0. ai.0002 unapplied and its three tables absent. Same original container,
  docker_postgres_data and127.0.0.1:5432 verified. See preservation-result.json.
- Original757-file comparison:0 deleted/missing,0 unexpected changes; only12
  existing code files+10 affected docs intentionally changed,8 new code/test
  files. All20 tested source hashes match; AI/model/migration/AuthProvider,
  AGENTS/README and all other pre-existing work unchanged by this task.
- Cleanup-result.json verifies0 labelled containers/networks across both backend
  and all three browser runs. No development service/volume was restarted or
  deleted. No .env/credential/AI flag read/change, live call, commit or push.
- Documentation consistency/local links and git diff --check are checked at final
  handoff; the actual validation receipt is documentation-check-result.json.

### Files changed by this task

Existing backend: apps/workspace/{access,serializers,views,urls}.py only.
New backend: apps/workspace/test_profile_members_api.py (13 tests).
Existing frontend: src/app/App.tsx; src/pages/{auth,account-security,tenants}.tsx;
src/services/api/client.ts; src/components/ui.tsx. New frontend:
src/services/api/members.ts + members.test.ts;
src/features/members/OrganizationMembers.tsx + OrganizationMembers.test.tsx;
src/pages/members.tsx + members.test.tsx; e2e/members.spec.ts.
Existing test infrastructure: scripts/frontend_integration.py and
scripts/test-frontend-integration.ps1. No package/dependency or design-token change.
Docs: HANDOVER,PROGRESS,PROJECT_ROADMAP,REQUIREMENT_STATUS,CHANGELOG,
API_DOCUMENTATION,RBAC_DESIGN,FRONTEND_GUIDE,PROJECT_CONTEXT,FRONTEND_MVP_ACCEPTANCE.
Other dirty/untracked files in git status were already present; do not revert them.

### Remaining limits and exact continuation

**REAL EMAIL DELIVERY NOT VERIFIED.** Current email contains an opaque code,
not an application link. No recipient inbox/token-preview or Profile role/remove
API exists. Missing safe mail configuration returns503 before creation;
post-commit delivery failure can return503 with a PENDING/delivery FAILED record.
SENT means backend acceptance, not mailbox receipt. No automatic retries or
delivery setup was added. Process-local DRF throttles are not a multi-worker
production guarantee; existing durable invitation quotas remain unchanged.
Profile MEMBER acceptance adds no Workspace membership; Owner/Admin authority
over child Workspaces still follows the existing approved RBAC. No generalized
Workspace direct-add/candidate UI was implemented. Existing large bundle warning
remains, with no unrelated split/refactor. No production readiness is claimed.

No implementation blocker remains in this approved scope. Owner next reviews
the manual steps in FRONTEND_GUIDE (Members section): open selected Profile,
inspect roster/allowed roles, invite an intended recipient only with configured
mail, recipient signs in using that email and explicitly enters/responds to code.
These real website writes were not performed by the agent. Recommended later
frontend priority is separately scoped Workspace membership candidate/management
integration, not AI04D/ai.0002 rollout. Await a new Owner instruction; do not rerun
unchanged tests or start another task automatically.

**STOP: HT-FE-MEMBERS-01 — OWNER REVIEW GATE.**

---

## Historical checkpoint — 2026-11-08 — HT-FE-STABILITY-01 OWNER REVIEW GATE

**IMPLEMENTATION COMPLETE — OWNER REVIEW GATE.** The reproduced source of
periodic UI flicker/Task-create dismissal is fixed and verified on final source.
Owner manual website acceptance is still PENDING. No deployment, AI04D,
development migration, provider activation or next task has started.

### Root cause, correction and security boundary

- Before fix: focus/visibility/60-second auth polling set checking/user:null;
  ProtectedRoute replaced the Outlet with SessionState. This unmounted local
  TaskCreate/TaskForm state even when /me returned the same User. Pre-fix real
  React route tests fail on the lost node/input. No route navigation or full
  reload is needed; StrictMode/HMR/button types are not the demonstrated cause.
- Routine pending/successful same-User checks preserve the mounted subtree and
  draft. Successful routine checks explicitly refresh active authority/data
  queries, preserving the revocation checks formerly incidental to remounting.
  A protected403 identity probe does not invalidate the denied query again.
- Initial/recovery checks still block. Confirmed different User/failure hides
  private content and cancels/clears cache; User-keyed Outlet also resets local
  drafts for same-tenant identity changes. Actual lost tenant authority removes
  the form; automatic polling does not interrupt checking/logout states.
- Login-required redirect now explains that unsent input is not saved. /me
  network/server failure retains existing fail-closed unavailable/recovery
  handling; no persistent draft recovery is promised. No localStorage autosave,
  new auth provider, CSRF/RBAC bypass or form/page redesign.
- Full UI UX Pro Max skill/master read; actual offline loading-flicker UX and
  React stable-key searches inform stable layout/focus/identity boundaries.
  Existing teal/neutral tokens, labels and native dialogs are unchanged.

### Fresh verification on final source

| Check | Actual result |
|---|---|
| Focused regression |147/147 PASS19.97s; final full suite below also covers the subsequent test-only focus-effect synchronization |
| Final frontend unit/contract |689/689 PASS27.24s,21 files; includes14 new auth/route cases vs675 baseline |
| TypeScript/Biome/build | All exit0; Biome74 files, Vite build6.51s. Advisory main chunk532.26kB remains; no unrelated bundle refactor |
| Real Chromium task-stability |4/4 PASS19.9s, runac6e04be1fb74ac4bb497a3e20785fe4 |
| Real Auth/CSRF/tenant foundation |6/6 PASS35.6s, runff1a14ff2d7546aea76c63723202b59c |
| Real Workspace/Task/Start |7/7 PASS58.6s, run876d739e9ae94869a40f5c0f0b33673d |
| Real fixture Generator |4/4 PASS32.4s, run77372f5f5bcb415bb5ff1503c8f5cdd9 |
| Browser aggregate / exit proof |21/21 PASS; each launcher, Playwright and isolated backend exit0; owned database removal confirmed |
| Cleanup | All five task browser attempts/runs have0 owned containers/networks; temporary HMR module removed without changing existing source |
| Responsive/accessibility |375/768/1440/812×375, keyboard/focus/Escape return, reflow and zero axe violations; actual HMR update without navigation/remount;375/1440 PNGs visually inspected |
| Documentation/source checks | Seven affected documents synchronized,40 local Markdown file paths valid, git diff --check exit0; all eight tested source hashes unchanged |

Browser scheduling forwards actual unchanged Django GET/POST responses. One
intentional network abort occurs BEFORE the first POST reaches Django; retry
uses real CSRF/server201 and increases Task count by exactly1 while pending
prevents duplicate submission. Real session expiry uses the ownership-checked
isolated helper. No persistent-development writes or manual Owner login occurred.
Timer60s is exercised with Playwright clock, not claimed as a real60s wall wait.
The HMR test changes only a new self-accepted module under ignored
frontend/playwright-report; it does not prove arbitrary application-boundary
edits/full reload preserve local state. No HMR cause for the original bug is claimed.

Failed attempts remain in ignored evidence: auth RED6fail/15pass21; route RED3
expected dismissal failures plus1 scheduled-observer fixture error/3passes7.
First after-fix focused145 had140passes/5 fixture errors; a later147 run had
146passes/1 immediate focus-effect assertion race. Unobserved hook cache entries
auto-collected with gcTime0 were corrected to test explicit auth clearing,
RTL-only role option types were corrected, and focus assertions now wait for
their post-commit effect while retaining the same requirement. First browser
run247d999... had3/4 PASS then timed out capturing a full-page modal screenshot
after genuine HMR/initialaxe succeeded; compositor cause unproven. Bounded
viewport capture with unchanged assertions passed all four on rerun. No test
assertion/security policy was weakened. Earlier687/pre-synchronization689 runs
are not substituted for the final689 result above.

### Development, source and exact continuation

Read-only pre/post snapshots match all29-table data/schema/FK/index/sequence/
migration/cluster fingerprints at13:51:43Z (20:51:43 Vietnam), connections excluded.
Original container49ef93152944/docker_postgres_data/127.0.0.1:5432,
hustlytasker_db/PG16.14 remains36 migrations/4 Users/2 Sessions/1 Profile/
membership/Workspace/Task/3 AuditLogs/AI0. ai.0002 is UNAPPLIED, its three tables
absent. No .env/secret, persistent flag, schema or data change. Existing isolated
fixtures/bootstrap run only in owned disposable PostgreSQL.

Branch main/32ccad220bee20540ba7a0e0f6f532250139d48c preserved. Initial755 file
hashes/status, final8 tested source hashes, current receipts/logs/screenshots,
cleanup-proof and development/source preservation proofs are Git-ignored under
.local_backups/HT-FE-STABILITY-01/. Backend/AI/config/migrations and all unrelated
source are byte-identical to start; no reset/revert/stash/commit/push.

Changed code/tests/scripts: AuthProvider.tsx/AuthProvider.test.tsx,
app/App.tsx, pages/auth.tsx, features/tasks/TaskForms.test.tsx,
new app/session-stability.test.tsx, new e2e/task-stability.spec.ts and
scripts/test-frontend-integration.ps1 (dedicated suite/artifact mapping only).
Docs: HANDOVER, FRONTEND_GUIDE, PROGRESS, CHANGELOG, PROJECT_ROADMAP,
REQUIREMENT_STATUS and PROJECT_CONTEXT. No API/schema/design-master change.

Commands executed sequentially:

```powershell
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
.\scripts\test-frontend-integration.ps1 -Suite task-stability
.\scripts\test-frontend-integration.ps1 -Suite foundation
.\scripts\test-frontend-integration.ps1 -Suite work-management
.\scripts\test-frontend-integration.ps1 -Suite ai-generator
```

Full backend826 and other browser suites are historical/not rerun for unchanged
backend. No live provider, production or manual development verification is claimed.

No implementation blocker remains for this verified cause. Owner's next safe
action is manual website review: open Create Task, type values, leave beyond60s,
switch tabs/focus and return; verify Cancel and normal server-confirmed save.
Use existing local startup in FRONTEND_GUIDE; do not migrate or seed to test.
Network/identity failure, explicit context navigation and full reload are not
durable draft recovery.04C remains OFFLINE GOVERNANCE IMPLEMENTATION READY /
DEVELOPMENT MIGRATION PENDING; any rollout/live task needs separate approval.
**STOP: HT-FE-STABILITY-01 — OWNER REVIEW GATE.**

---

## Historical checkpoint — 2026-11-08 — HT-FE-STABILITY-01 IN PROGRESS

Owner authorizes targeted investigation/fix of UI flicker and Task-create draft
loss, with isolated browser mutations only. Preserve prior dirty work and the
completed04C offline governance/candidate ai.0002 UNAPPLIED; no AI/backend/
migration/.env/production changes. main/32ccad220bee20540ba7a0e0f6f532250139d48c.
Initial755 tracked/untracked file hashes and status are ignored under
.local_backups/HT-FE-STABILITY-01/. Development target/container/volume/loopback
verified before read-only inventory; no mutation or credential output.

REPRODUCED in real-component tests before runtime edits: AuthProvider.revalidate
cleared user/status to checking on focus/visibility/60-second polling; ProtectedRoute
replaced the whole Outlet with SessionState. TaskCreate/TaskForm unmounted and
lost local input even though /me then returned the same User. No navigation or
HMR is necessary. main.tsx already disables TanStack focus refetch; Task-list
loading is below the create header, stable tenant keys and Dialog/button types
are not the positive-refetch cause. HMR/full-reload cause is not yet demonstrated.

RED evidence: auth6failed/15passed21; real-route3 expected dismissal failures
plus1 modal-background assertion error/3passes7. After minimal runtime changes,
focused145 has140passes/5 fixture-assertion errors: four unobserved hook-cache
entries were auto-collected by gcTime0; one link query ignored modal background
inertness. Fixtures are being corrected without weakening draft/security checks.
No final PASS yet. Root handles all runners; do not duplicate clusters.

Implemented, pending final verification: routine authenticated checks keep the
subtree mounted, initial/recovery checks still block, identity change/failure
clears private cache; authenticated Outlet keyed by User prevents same-tenant
draft carryover. Automatic checks do not interrupt checking/logout. Existing
login page explains login-required/unsaved form state. No localStorage draft.
Native form/layout/teal tokens unchanged. Full skill read; actual offline searches
loading flicker UX (stable layout/focus) and React stable keys guide the fix.

Currently changed: AuthProvider.tsx/AuthProvider.test.tsx, App.tsx, pages/auth.tsx,
new app/session-stability.test.tsx and launcher task-stability suite mapping.
Browser agent owns new e2e/task-stability.spec.ts, still being authored; it must
use isolated fixture DB, real API responses, labeled network scheduling/fault
injection and an owned ignored module for actual Vite HMR (never rewrite an
existing source file). No runtime AI/backend edit. Root owns docs and test runs.

Latest verified checkpoint: final frontend689/689 PASS27.24s,21 files; TypeScript,
Biome74 files and build6.51s exit0. Focused147/147 PASS19.97s preceded a small
test-only focus-effect wait correction, then the final full suite above covers
it. An earlier unobserved cache GC/assertion fixture and RTL role exact option
were corrected, no security assertions removed. One existing focus assertion
was synchronized with its post-commit effect (not a production form change).

To preserve authority refresh previously incidental to remounting, routine
same-user /me success explicitly invalidates active queries; Forbidden probes
do not. Two new tests verify lost Profile access removes the draft without
logging out a valid User, and a Task403 probe does not create a refetch loop.
Runtime/test/script source8 files is frozen in tested-source.json. Build retains
the advisory532.26kB main chunk warning; no unrelated bundle refactor.

Browser first run247d999c92b441deb2778e1848c5e9d5:3/4 PASS (real query/focus/
visibility/60s continuity, injected pre-backend network failure→real201 retry,
actual session expiry). HMR4th received a genuine update and passed initial
draft/axe checks, then full-page screenshot hung90s after fonts loaded. No PNG
was written; exact Chromium cause unknown. Actual Playwright/launcher1, backend0,
owned cleanup confirmed. Screenshot-only capture changed to viewport/animations
disabled/caret hidden/5s timeout, with same-document/draft checks retained.

Current browser runner session10228 is RUNNING isolated task-stability,
foundation, work-management and ai-generator suites sequentially, no parallel
clusters. Do not launch a duplicate. Next safe step: inspect its actual result,
fix only demonstrated issues, collect exit/cleanup/screenshots, final source and
read-only development preservation and finish docs. No further full backend test
run is needed for unchanged backend/AI source. Stop at HT-FE-STABILITY-01 OWNER
REVIEW GATE; no deployment or04D.

---

## Historical checkpoint — 2026-11-08 — HT-AI-P4-04C OWNER REVIEW GATE

**OFFLINE GOVERNANCE IMPLEMENTATION READY / DEVELOPMENT MIGRATION PENDING.**
Owner-approved additive candidate schema and offline governance are implemented
and verified. No persistent development migration, live transport/key/billing,
data egress, frontend change or production action is authorized or performed.
Manual Owner website acceptance remains pending. No next task has started.

### DONE — actual implementation

- Source-backed audit distinguishes confirmation idempotency from pre-transport
  dispatch deduplication. Old fixture Generate/Confirm and stateless Analyzer
  remain unchanged; their successful atomic confirmation is not a paid-call lock.
- `backend/apps/ai/models.py` appends AiDispatch, AiBudgetBucket and
  AiDispatchReservation. Candidate `ai.0002_dispatch_governance` contains three
  CreateModel operations only; no old-table alteration, data backfill or inferred
  tenant/provenance mapping. Old models and applied ai.0001 remain byte-equivalent.
- New `governance.py` implements reserve/get/begin/fail-before-dispatch/unknown/
  reconciliation and Generator/Analyzer offline execution wrappers. Three stable
  lifetime GLOBAL/Profile/User buckets atomically enforce shared cost exposure,
  request count and in-flight limits across features. No daily rollover or reset.
- Lock order: existing tenant manager context → GLOBAL/Profile/User buckets →
  dispatch/reservations. One RESERVED→DISPATCHING claim commits before fake
  transport; a concurrent equivalent request receives the durable receipt without
  another invocation. No database transaction remains open across transport.
- Scoped idempotency binds actor/Profile/Workspace/feature/mode; keyed body and
  policy fingerprints bind actual input/provider/model/config/rates/token bounds.
  Changed input/config conflicts. Key rotation supports Django fallback secrets.
  No raw brief/feedback/provider response is saved in the new accounting tables.
- Pre-dispatch failure releases cost/inflight, retaining request count. Timeout,
  crash, bad usage/output or post-dispatch persistence failure retains holds as
  OUTCOME_UNKNOWN, or DISPATCHING if writing UNKNOWN itself fails. No automatic
  retry, timeout refund or transition back to RESERVED. Explicit simulated
  reconciliation is original-actor/current-authority scoped and idempotent.
- Fake provenance stays generated_by_ai:false; simulated usage/estimated debit
  is distinct from actual billed_cost (NULL). Existing adapter is unchanged.
  Analyzer reuses actual selected Review/Comment authorization and source
  revalidation, remains advisory, and creates no user-facing history/domain rows.

### Fresh checks — final frozen source

Commands executed through the existing shared runner (isolated PostgreSQL):

```powershell
.\scripts\test-backend.ps1 -TestLabel apps.ai.test_governance,apps.ai.test_governance_migrations
.\scripts\test-backend.ps1
```

| Check | Actual result / evidence |
|---|---|
| Focused services/concurrency/migrations | 52/52 PASS,15.286s;46 service tests including two real independent-connection races and6 migration tests; run b9026ca5aa714cf0a7d8ea45c38ae42b |
| Full PostgreSQL regression | 826/826 PASS,231.558s; run13acfbc5330d42c4bccb5dd9423bc7e7, completed10:18:52Z; includes existing fixture/confirmation/adapter/tenant/auth and business regressions |
| Process exits | Final focused and full launcher0 and actual Python0 independently verified by Docker die events; PostgreSQL137 is intentional owned-container cleanup after tests |
| Dependency/Django/schema checks | pip check, system check, model drift/graph/history and full isolated migration chain PASS; empty/legacy-related forward/reverse and constraint/index/FK tests included |
| Cleanup | Owned test databases removed; all six task-run containers/networks remaining0; no persistent volume selected |
| Source preservation |247 originals checked:246 exact; only intended models.py append differs, old model prefix hash matches. All five final tested files unchanged after full run |
| Documentation |12 affected documents synchronized;157 local Markdown file paths checked,0 broken; git diff --check exit0 |

Evidence is Git-ignored under `.local_backups/HT-AI-P4-04C/`:
Focused/Full stdout+stderr logs, process receipts, child-exits/cleanup-proof JSON,
source-before/tested-source/source-proof and development-before/after/
preservation-proof JSON. No raw rows or secrets appear in these reports.

Earlier failures are retained, not presented as passing runs: first focused52
failed with45 setup/negative-fixture errors (duplicate blank User emails and
overlength invalid enum); a second focused run had47 passes/5 setup errors
(TaskComment test used author instead of the actual user FK). Only synthetic
fixtures were corrected; no assertion, production User policy or runtime logic
was weakened. Bounded reruns2/2 and5/5 passed before the final52/826 runs above.
Historical04B55/270 and earlier frontend/browser counts below are not new runs.
Frontend/browser, live billing/provider and persistent-development write flows
were not tested in04C. No new HTTP integration or live quality claim is made.

### Development / Git preservation

Branch main, HEAD32ccad220bee20540ba7a0e0f6f532250139d48c; all earlier dirty and
untracked work retained. No reset/revert/stash/commit/push. Original development
container49ef93152944, volume docker_postgres_data, loopback127.0.0.1:5432,
database hustlytasker_db, PostgreSQL16.14/Engine29.8.2 independently identified.
Read-only snapshots09:53:41Z→10:21:26Z match all29 tables' row fingerprints,
columns/FKs/CHECKs/indexes/sequences/migration history/system identity; ephemeral
connections excluded. Still36 migrations,4 Users,2 Sessions,1 Profile,
1 ProfileMembership,1 Workspace,1 Task,3 AuditLogs and0 Review/Comment/AI rows.
`ai.0001_initial` remains applied; candidate0002 is UNAPPLIED and its three
tables absent. No .env/credential read, persistent flag or data/schema write.

### Pending / limitations / exact safe continuation

- Governance is disabled before new-table queries unless literal
  AI_GOVERNANCE_ENABLED plus trusted enabled GovernancePolicy plus existing
  nonproduction fixture guard pass. The setting is not added to settings.py or
  the environment loader; enabled settings in tests do not enable development.
  OPENAI_LIVE is always rejected, even if a key exists externally.
- Provenance modes/fields for future live usage are staged schema, not live
  functionality. Configured token exposure/rates are simulation assumptions,
  not proven bounds on real model billing. Reconciliation evidence is a trusted
  caller's simulated assertion, not independently verified provider billing.
- No result text is retained/recovered on duplicate calls, no proposal linking
  is wired, no shared-ledger HTTP endpoint or React DTO is introduced. Existing
  fixture routes remain unchanged. No auto fallback or user-facing analysis
  history is added.
- Lifetime counters have no operator reset/window/purge workflow. Unknown holds
  stay indefinitely; revoked actors cannot reconcile. Any future operator role,
  price/window administration or real billing evidence needs separate review.
- Authorized current HTTP/fixture/startup paths do not touch candidate tables.
  Generic ORM hard-delete/AdminCollector maintenance may follow new PROTECT
  relations and requires the candidate schema; do not perform it on development
  before rollout. No hard delete is authorized or claimed compatible here.
- Current code files: models.py, governance.py, migrations/0002_dispatch_governance.py,
  test_governance.py, test_governance_migrations.py. Docs changed: HANDOVER,
  AI_ARCHITECTURE_DESIGN, AI_PERSISTENCE_REVIEW, DATABASE_SCHEMA, API_DOCUMENTATION,
  DECISION_LOG, FEEDBACK_ANALYZER_FOUNDATION, PROGRESS, PROJECT_ROADMAP,
  REQUIREMENT_STATUS, CHANGELOG and PROJECT_CONTEXT.
- Next proposed task: separately authorize controlled ai.0002 development
  migration readiness, fresh inventory/backup and isolated restore rehearsal.
  Read this checkpoint and candidate migration first; do not regenerate or apply
  it automatically. Actual rollout requires its own Owner approval after safety
  evidence. Live HTTP/proposal integration, data/privacy, billing monitoring and
  bounded live smoke each remain separately gated. Project remains pending.

**STOP: HT-AI-P4-04C — OWNER REVIEW GATE.**

---

## Historical checkpoint — 2026-11-08 — HT-AI-P4-04B OFFLINE OPENAI ADAPTER COMPLETE / OWNER REVIEW GATE

Owner approves actual OpenAI adapter code for gpt-5.4-mini + Responses API +
strict Structured Outputs, OFFLINE FAKE TRANSPORT ONLY. This supersedes04A's
provider-selection blocker for this implementation target only. No live request,
key, billing, data egress, schema, persistent flag or production is authorized.
Manual Owner website acceptance and live provenance/accounting/data gates remain.

Read AGENTS/current instructions, source/provider/contracts/validation, current
Generator brief/confirm and stateless Analyzer, fixture guards and prior docs.
Existing main/32ccad220bee20540ba7a0e0f6f532250139d48c dirty work is preserved.
245 original source hashes/status are ignored in .local_backups/HT-AI-P4-04B/.
Actual read-only preflight09:23:04Z confirms PG16.14/Engine29.8.2, original
container49ef93152944/docker_postgres_data/loopback5432,hustlytasker_db,
36 migrations/29 tables/4 Users/2 Sessions/1 Profile/membership/Workspace/Task/
3 AuditLogs/AI0. No .env/credential or development data/flag write.

Official OpenAI model page and Structured Outputs documentation fetchedNov8
confirm the exact target supports Responses/strict output. API-reference HTML
was too large and Markdown content is unsupported by the web tool; use the
official guide/approved reference schema, not an invented Chat Completions DTO.
No provider request or API key lookup is part of documentation retrieval.

DONE: new openai_adapter.py and focused test_openai_adapter.py. Actual
boundary: existing StructuredProvider.generate→explicit enabled offline config→
injected in-memory transport only→bounded Responses envelope→existing domain
parser→ProviderResult marked openai_offline/offline_simulated, unknown monetary
cost. No SDK/network implementation/default transport, env loading or HTTP route
wiring. Current Generator/Analyzer fixture services and React contracts stay.
Default-disabled config, tools empty, nonstreaming/store:false, bounded tokens/
timeouts/bytes, static errors/refusal/incomplete handling and no automatic retry.
RequestControl cancellation is cooperative, never a refund/billing guarantee.

OpenAIConfig(enabled=False,model='gpt-5.4-mini',timeout_seconds=30.0,
max_output_tokens=4096,max_response_bytes=131072) is code-owned, not a settings
flag. Validated caps: timeout≤120s/tokens≤32768/envelope≤1MiB; outbound≤64KiB and
existing domain response≤64KiB. Explicit enabled and trusted transport.offline
literally True are required. Missing/invalid config fails without dispatch.
No key/header/env/SDK/network implementation exists, so no key is requested.
Response must be completed, no contradictory error/incomplete fields, allowed
model and exactly one assistant text message; tools/refusal/bad JSON and invalid
domain fields/graphs/dates/citations are denied. Existing pure parsers are reused.
Generator/Analyzer minimal projections never emit internal tenant/source IDs.
Analyzer's zero-UUID actor slot is only local pure-validator correlation, never
an identity/authorization grant. Future Django wiring must authorize/revalidate.

Upstream401/403 map PROVIDER_UNAVAILABLE, preserving caller RBAC distinction;
429→RATE_LIMITED, timeout→PROVIDER_TIMEOUT, refusal→AI_REFUSED, malformed or
incomplete→INVALID_PROVIDER_RESPONSE, cooperative cancel→CANCELLED. Raw errors
are suppressed, no retry/fallback. Fake token counts are validated and labelled
offline_simulated, monetary cost remains None; no actual inference is claimed.

### Current verification and preservation

Focused adapter **55/55 PASS0.038 seconds**, run34e57d879f494390bac559ab92d54142.
Final apps.ai **270/270 PASS13.347 seconds** (55 new +215 existing),
runa4ea8e5170b04d059576f881633e3166. No failures/errors/skips in these runs.
Both launcher and actual Python container exits0 independently verified by
retained receipts/Docker die events; PG137 is deliberate disposable cleanup.
pip check/Django check/model drift/graph/history/full isolated migration chain
and owned DB removal PASS;0 run-owned containers/networks remain. Evidence:
Focused/AiTargeted stdout/stderr/process receipts and child-exit-events.json in
.local_backups/HT-AI-P4-04B/. The frozen two-file hashes still match.

Tests exercise request/response schemas, config/errors/deadlines/cancellation,
no-network/no-DB/no-domain guards, privacy/canaries, fixture compatibility and
existing authorization/confirmation/idempotency/rollback. No real model, provider
timeout, account/billing or semantic quality result is claimed. Historical215
took16.523 seconds (~16.5s), not16,523 seconds; comma notation caused ambiguity.
Full backend719/frontend675/browser36 and frontend type/lint/build are historical
and not rerun: all245 original runtime/test/config files are byte-identical and
the new adapter is not wired into application/React. No duplicate heavy runner.

Final READ ONLY snapshot2026-11-08T09:31:40.7320302Z matches preflight exactly:
all29 tables' row fingerprints, schema/columns/FKs/constraints/indexes, sequences,
migrations and cluster identity (ephemeral connections excluded). Still36
migrations/4 Users/2 Sessions/1 Profile/membership/Workspace/Task/3 AuditLogs,
Review/Comment/AiProposal/AiOperation0. Original container/volume unchanged;
ai.0001 already applied, untouched. Proof: ignored preservation-proof.json.
No business fixtures, .env read, credentials, live/fixture flag, schema/data write,
commit/push/reset/clean/stash or next task. Final git diff --check exits0 and136
local Markdown paths across affected documents resolve with0 broken links.

Code changed: NEW backend/apps/ai/openai_adapter.py and test_openai_adapter.py
only. Independent source/security review found no concrete blocker; input config
overflow and contradictory completed/error envelope were hardened before tests.
Documentation: AI_ARCHITECTURE_DESIGN, AI_PERSISTENCE_REVIEW,
FEEDBACK_ANALYZER_FOUNDATION, API_DOCUMENTATION, DECISION_LOG, PROGRESS,
PROJECT_ROADMAP, REQUIREMENT_STATUS, CHANGELOG, PROJECT_CONTEXT and HANDOVER.
Future exact provenance/dispatch/budget schema is PROPOSED only; no model or
migration is created. Analyzer remains stateless, Generator fixture persistence
and confirmation unchanged. Store:false is not Zero Data Retention; synchronous
cooperative cancellation does not prove stopped billing or preempt arbitrary
trusted callback code. There is no production HTTP transport or spending ledger.

NEXT: STOP AT04B OWNER REVIEW GATE. Recommended separate next task is Live
Provenance & Shared Dispatch/Accounting Contract/Schema Review, then separately
approved implementation/isolated validation before paid wiring. Live data/terms,
cost controls, capped live smoke, migration rollout and production each remain
gated. Manual Owner website acceptance stays PENDING. Latest task-specific
predeployment question is recorded in DECISION_LOG; no deployment authorized.

---

## Historical checkpoint — 2026-11-08 — HT-AI-P4-04A DESIGN READY / PROVIDER IMPLEMENTATION BLOCKED

Active task: Live AI Integration Readiness & Secure Provider Foundation. The
Owner permits a safe default-off adapter only if approved provider/architecture
choices allow it. Task section7 explicitly says proposal+stop if no provider
choice is approved. Source/DECISION_LOG audit confirms only fixture approval;
Gemini/OpenAI/model/data mode/live budget/provenance accounting remain pending.
No adapter/SDK/runtime/models/migrations/settings/frontend/provider call is added.
This status is not PROVIDER FOUNDATION READY or a live-AI PASS.

Preserve all existing dirty FE05/02C/03A/03C work on
main/32ccad220bee20540ba7a0e0f6f532250139d48c. Initial245 source hashes and Git
status are ignored in .local_backups/HT-AI-P4-04A/. The current readiness proposal
is [AI_ARCHITECTURE_DESIGN](AI_ARCHITECTURE_DESIGN.md#ht-ai-p4-04a--live-provider-readiness-2026-11-08),
including all15 engineering questions, compatibility/privacy/cost gaps and exact
next approval scope. Historical reports below are preserved, not reused as new tests.

### DONE — source audit and design

- Existing StructuredProvider.generate/request/result/control port is reusable,
  but only FixtureAdapter exists; application orchestration rejects other adapter
  types, Generator constructs it directly, and backend/React require synthetic
  mode/false provenance/zero usage. No approved live selector exists.
- Optional validated brief actually reaches ProviderRequest when supplied;
  only absence uses scenario text. The fixture ignores semantic content. Raw
  brief stays transient, bound through stored HMAC only. A real generated plan
  could copy confidential input, so derived-output retention needs approval too.
- Strict task/feedback parsers already enforce exact versions/fields,20 total
  nodes/3 child levels, enums, aware dates, byte/string bounds and authorized
  citations. Future provider-native JSON must still pass them.
- Current manager/tenant/session/CSRF boundaries and explicit atomic human
  confirmation are preserved. Same-key overlapping generation can dispatch
  twice before one durable winner; confirmation safety does not prove no duplicate
  provider charges. No in-flight dispatch or shared spend reservation exists.
- Analyzer source resolution uses selected Review.comment/nondeleted Comments
  for one authorized Task and repeated current checks. Preserve stateless advisory
  behavior. Future outbound projection must send only {ref,text}+focus, stripping
  FeedbackSource's internal tenant/task IDs, source DB IDs, identity, URLs and secrets.
- Cooperative RequestControl is not wired to HTTP disconnect/deadline or actual
  network timeout/retry. Browser abort prevents stale UI, not remote charges.
  Proposed HTTPS transport uses bounded I/O, static errors, no silent fallback
  and no automatic retry until safe provider/cost semantics are approved.
- Default-false fixture flag is unchanged. New live config names in design are
  PROPOSED ONLY; no .env or secret/config value was read, added or changed.
- Official OpenAI structured-output/data docs fetched using OpenAI Docs; Google
  official Markdown terms/schema/rate docs fetched by public HTTP GET after the
  browser tool's content-type failure. Access date2026-11-08; no model requests.
  Provider/account/model quality/terms applicability remain unverified; do not
  infer private-data approval from a free tier, paid account or API key.
- Manual website checklist added to FRONTEND_GUIDE. FE05/Generator/Analyzer
  manual Owner acceptance remains PENDING; fixture-disabled UI is expected.
  Original requirements/reference audit provide business context, not approved
  current SRS/HLD or approval to add Project/client/media functionality.

### Current tests actually run

Exactly one .\scripts\test-backend.ps1 -TestLabel apps.ai run:
**215/215 PASS16.523s**, run3be0225ea26140d0b82b145d60a09879. Launcher0 and actual
Python container0 verified from process receipt and Docker die events. PG137 was
deliberate disposable cleanup, not a test failure. pip check, Django check,
makemigrations drift, graph/history and full isolated migration chain PASS.
Owned test database removed;0 run-labelled containers/networks remain.
Evidence: AiTargeted.stdout.log/stderr.log/process.json and ai-exit-events.json
under the ignored task directory. No current tests failed/skipped in this suite.

These tests verify existing fixture contracts, no-network/error/injection-data
checks, current tenant/CSRF/source controls, no Analyzer domain writes and
Generator confirm/replay/concurrency/rollback. They do not prove live adapter,
provider timeout/billing cancellation, shared budget or model prompt-injection
resistance. Those adapter tests are NOT IMPLEMENTED/NOT RUN because provider
selection is blocked; no extra synthetic feature was added just to increase counts.
Full backend719/frontend675/browser36/type/lint/build below are historical,
not rerun: no runtime/test changes justify repeating them. No manual website,
provider smoke, production or remote CI result is claimed.

### Persistent development and final checks

Read-only preflight2026-11-08T09:00:49.5785442Z confirms original
container49ef9315294450710e2c71eefb1559993c821aff94531e79541d9811534ebbbe,
docker_postgres_data,127.0.0.1:5432,hustlytasker_db,PostgreSQL16.14,Engine29.8.2.
There are36 applied migrations/29 tables, **4 Users**,2 Sessions,
1 Profile/1 ProfileMembership/1 Workspace/1 Task/3 AuditLogs,AI rows0. Four Users
is the new legitimate starting state; never delete one to match historical3.
No .env read, development login/mutation/fixtures, migration or fixture/live flag
change occurred. ai.0001_initial is already applied and never reapplied.

Final READ ONLY comparison at2026-11-08T09:08:21.9174345Z matches all29 tables'
row fingerprints, schema/columns/FKs/constraints/indexes, sequences, migration
history and cluster identity exactly; ephemeral connection counts are excluded.
Still4 Users/2 Sessions/36 migrations/1 Profile/membership/Workspace/Task/
3 AuditLogs;Review/Comment/AI rows0. Proof and before/after snapshots are ignored
under .local_backups/HT-AI-P4-04A/preservation-proof.json. All245 runtime/test/
config source hashes remain identical, preserving every pre-existing dirty edit.
git diff --check exits0;132 local Markdown paths resolve with0 broken links.
No run-owned test container/network remains. No operational blocker is present;
the unresolved dependency is the explicit provider/data/cost/contract approval.
Safe continuation is Owner review only, not another test runner or live code.

### Files and approval dependency

Documentation only: AI_ARCHITECTURE_DESIGN, AI_PERSISTENCE_REVIEW,
FEEDBACK_ANALYZER_FOUNDATION, API_DOCUMENTATION, FRONTEND_GUIDE, PROGRESS,
PROJECT_ROADMAP, REQUIREMENT_STATUS, CHANGELOG, DECISION_LOG, PROJECT_CONTEXT
and this HANDOVER. All runtime/untracked prior work remains preserved.

OWNER DECISION REQUIRED: named provider/model/API/data mode; permitted content,
terms/region/provider and derived-output retention; budget/concurrency limits and
durable enforcement; reviewed Generator provenance/dispatch-accounting contract
and minimum schema scope. Existing manager RBAC/human confirmation/stateless
Analyzer/tenant/task hierarchy rules are ALREADY APPROVED and are not reopened.
Recommended next task after approval is a named-provider offline adapter slice,
followed by separate accounting/schema review before any migration/paid wiring.
Live synthetic smoke, private data, billing and production require explicit
separate approval. No next task begins automatically; preserve the permanent
exact predeployment Owner question in AGENTS.

---

## Historical checkpoint — 2026-11-02 — HT-AI-P4-03C IMPLEMENTATION COMPLETE / OWNER REVIEW GATE

Owner-approved active task is Feedback Analyzer React integration and isolated
E2E validation. P4-03B durable analysis persistence is not needed for the current
stateless fixture MVP and is not implemented. Preserve all existing FE05,
P4-02C and P4-03A dirty work on main/32ccad220bee20540ba7a0e0f6f532250139d48c.
Their implementation/tests are historical; manual Owner FE05/02C acceptance
remains pending. No live provider, persistent flag/schema/data write or deployment.

Before coding, actual source confirms POST nested Task ai/feedback-analysis/
accepts1..20 sources[{kind:review|comment,id:UUID}] +optional focus≤1000. The
ai.v1 READY fixture envelope contains exact ai.feedback.v1 payload, ordered
S1..Sn source manifest, generated_by_ai:false,persisted:false and zero usage.
It has no operation/proposal/confirmation/history semantics. Existing authorized
Deliverable reads expose singular review:{id,comment,...}; current Comment reads
expose id/content/is_deleted. No backend bridge or expanded visibility is needed.

Chosen integration: lightweight section after existing TaskCollaboration in
Task Detail, no route redesign. Current active manageTasks capability gates UI;
existing permission-checked aiApi.availability OPTIONS reuses the shared flag.
Paginated existing Review/Comment reads provide eligible IDs. Only selected
source refs/focus go in POST; original text stays distinct from fixed suggestions.
Result is local only, current User/Profile/Workspace/Task keyed, aborts on exit,
explicit Analyze/no automatic retry/no generator idempotency/no Apply buttons.

DONE: source/contract audit, strict feedback-analysis.ts transport/tests,
FeedbackAnalyzer component/tests, TaskDetail integration, source selection,
validation/citations and clear-on-observed-drift. Existing client gains only
static sources/focus localized errors. Backend runtime/models/migrations/flags
are unchanged. Isolated-only seed scopes/snapshot helper and two browser suites
extend the existing runner, preserving Generator empty fixtures.

UI UX Pro Max/master were read in full. Actual offline searches were
`checkbox group error summary --domain ux` and
`async request cleanup race --stack react`. Their web-appropriate guidance is
applied through semantic checkbox groups, linked/focused errors, pending/cancel
controls and scope-bound async cleanup; existing teal/neutral tokens and shared
components remain. No design-system replacement or dependency was added.

Read-only development inventory at2026-11-02T06:52:44Z confirms original
49ef93152944/docker_postgres_data/127.0.0.1:5432,hustlytasker_db,PG16.14,
36 migrations,3 Users/2 Sessions,1 Profile/Workspace/Task,Review/Comment/AI0.
238 original source SHA256s and snapshots are ignored under
.local_backups/HT-AI-P4-03C/. No .env read or development mutation.
Current Windows venv --version really exits103 (configured Python312 missing);
do not recreate it. Node20.17/npm10.8.2 and existing Docker Python3.12 runner are
used. Old719/537/30 results are not current P4-03C evidence.

### Recovery inventory and work completed

The interrupted work already included the transport, React section, Task Detail
integration, strict contracts, isolated fixtures/browser specs and tests. Recovery
checked actual files/hashes/receipts rather than restarting implementation. The
last saved checkpoint lagged behind the completed tests: the sequential browser
pipeline had finished all ten suites; no duplicate runners were started.

An initial Analyzer browser run was4/5 (43.6s, run14e4d15515f1479e980b823eac458082):
the helper wrongly expected Dashboard after legitimate return-to navigation.
The helper now explicitly opens Dashboard. Independent review also found a real
direct-GET→shared-cache-write race that could restore an unselected deleted
Comment. Selected-page refresh now uses tracked exact-key fetchQuery cancellation
and rejects an aborted query even when TanStack resolves it with reverted cache
data. A focused regression verifies redacted content cannot reappear or trigger
Analyze. Preserve attempt-1 evidence; final results below follow these fixes.

| Recovery requirement | Final status/evidence |
|---|---|
| 1. API transport | DONE — existing nested POST, shared client |
| 2. Request/response types | DONE — exact bounded DTO/provenance/citations |
| 3. Session/CSRF | DONE — shared client + real enforcement tests |
| 4. Task entry | DONE — section after TaskCollaboration, no new route |
| 5. Authorization visibility | DONE — current manager capability; server rechecks |
| 6. Eligible reads | DONE — existing paginated Deliverable.review/Comments |
| 7. Selection | DONE — unique Review/Comment refs, selected-page refresh |
| 8. Source bounds | DONE —1..20 and≤12000 aggregate characters |
| 9. Optional focus | DONE —≤1000 valid characters, no raw logging/storage |
| 10. Request lifecycle | DONE — explicit submit, pending lock/cancel, no POST retry |
| 11. Synthetic results | DONE — honest fixed fixture/no semantic AI claim |
| 12. Citations | DONE — ordered authorized manifest; fixed example cites S1 |
| 13. Errors | DONE — Vietnamese validation/disabled/auth/rate-limit responses |
| 14. Disabled mode | DONE — real browser test, no Analyze POST |
| 15. Context isolation | DONE — User/Profile/Workspace/Task key, abort/unmount/reset |
| 16. Domain preservation | DONE — all installed isolated model fingerprints unchanged |
| 17. Unit/contracts | DONE —675/675 full frontend tests |
| 18. Real browser | DONE —36/36 across10 isolated suites |
| 19. Responsive/accessibility | DONE —4 viewports, keyboard, reduced motion, axe0 |
| 20. Documentation | DONE — synchronized source/test/preservation checkpoint |

No implementation PARTIAL/TODO/BLOCKED remains. Durable history, live AI and
Apply Suggestions are NOT APPLICABLE to this stateless advisory contract.

### Final current verification (not historical baselines)

Transport focused153/153 PASS1.80s (106new+47client); component32/32 PASS13.29s,
including the cache-redaction race. Full frontend675/675 PASS27.31s in20 files;
launcher exit0. TypeScript, Biome and production build exit0, build7.58s.
The existing bundle-size advisory remains (531.77kB JS,153.77kB gzip); no unrelated
splitting/refactor is included.

| Real isolated Chromium suite | Result | Launcher / Playwright / backend exits |
|---|---|---|
| feedback-analyzer |5/5,45.8s|0 /0 /0|
| feedback-disabled |1/1,9.9s|0 /0 /0|
| ai-generator |4/4,32.2s|0 /0 /0|
| ai-disabled |1/1,8.1s|0 /0 /0|
| onboarding |3/3,31.6s|0 /0 /0|
| foundation |6/6,36.7s|0 /0 /0|
| work-management |7/7,1.0m|0 /0 /0|
| collaboration |7/7,1.1m|0 /0 /0|
| acceptance |1/1,33.8s|0 /0 /0|
| account-security |1/1,21.1s|0 /0 /0|

Total36/36. Every suite logs owned database removal and container/network cleanup.
Final Docker inspection finds0 repository-labelled FE containers/networks and0
targeted backend containers. Analyze itself is exercised through React source
selection/focus/button and actual Django/PostgreSQL. Denial checks and the
separate source-deletion/session-expiry setup use API/private isolated helpers;
the delayed-response test holds a real backend response, not invented JSON.
No mock test is called live-provider or UI E2E evidence.

Real Analyze's before/after snapshots compare every installed model's row count
and fingerprint; all match, with only the intended Analyze unsafe request.
No Task/Review/Comment/Notification/AiProposal/AiOperation write occurs. Disabled
mode likewise preserves state. Responsive375/768/1440 and812×375 landscape,
keyboard Space/Enter/result focus, reduced motion and axe WCAG2/2.1AA pass with0
violations. Root visually inspected final375/1440 screenshots. Evidence is ignored
under `.local_backups/HT-AI-P4-03C/screenshots/69fd94a56faa40508b3e0fc68cbe31c3/`.

Fresh current backend apps.ai215/215 PASS16.494s, run09360a4dc2124ce988db57b246499e92,
launcher/actual Python exits0, dependency/Django/model-drift/full migration chain
and owned cleanup PASS. All160 backend source files are unchanged. Full719 is
historical and not rerun for this frontend-only change. No live provider, manual
Owner browser acceptance or production test is claimed.

Final read-only development comparison at2026-11-02T09:24:35.6407031Z matches
all29 tables' row fingerprints, columns/FKs/constraints/indexes, sequences,
migration history and cluster identity exactly (ephemeral connection counts
excluded). Still36 migrations/3 Users/2 Sessions/1 Profile/1 ProfileMembership/
1 Workspace/1 Task/3 AuditLogs; Reviews/Comments/AiProposal/AiOperation0.
Original container49ef93152944/volume docker_postgres_data/loopback5432 remains.
`ai.0001_initial` is already applied and untouched; no migration was created or
applied in P4-03C. Proof: `.local_backups/HT-AI-P4-03C/preservation-proof.json`.
All33 final tested source hashes match. Of238 original source files, only the
five intended existing frontend/test-infrastructure files differ; all other233
and all160 backend files remain byte-identical. Existing dirty work is preserved.
Final `git diff --check` exits0;85 local Markdown links across the affected
documentation/README resolve with0 broken links. Recovery reused the actual
passing test receipts on this exact source rather than restarting finished suites.

### Files changed by P4-03C

- New frontend: src/features/ai/FeedbackAnalyzer.tsx and its test;
  src/services/api/feedback-analysis.ts and its test;
  e2e/feedback-analyzer.spec.ts, feedback-disabled.spec.ts, feedback-helpers.ts.
- Existing runtime: frontend/src/pages/tasks.tsx (section), styles.css (scoped
  existing-token styles), services/api/client.ts (two static localized fields).
- Isolated infrastructure: scripts/frontend_integration.py and
  scripts/test-frontend-integration.ps1; no production/development fixture change.
- Documentation: HANDOVER, PROGRESS, PROJECT_ROADMAP, REQUIREMENT_STATUS,
  CHANGELOG, PROJECT_CONTEXT, FRONTEND_GUIDE, API_DOCUMENTATION,
  FEEDBACK_ANALYZER_FOUNDATION, design-system/hustlytasker/MASTER and README.
  Unrelated pre-existing dirty files belong to earlier tasks, not this change.

### Limits, manual acceptance and safe next step

This is fixed offline synthetic output: it does not understand selected text,
video or audio. Results disappear on reload/navigation and cannot be applied.
The source reads/rechecks are optimistic; they cannot retract content already
delivered or detect unobserved server changes. Shared process-local3/minute20/day
quota is approximate, not a distributed budget; repeated requests are recomputed,
not durable/idempotent recovery. Persistence/live provider require separate scope.

Manual Owner FE05, Generator and Analyzer acceptance remains PENDING. With the
current persistent flag disabled, an authorized Manager can open Task Detail and
verify the honest unavailable state plus unchanged Review/Comments. Do not enable
the persistent fixture flag merely to test this task. For the complete synthetic
flow without development data writes, run from root:
`.\scripts\test-frontend-integration.ps1 -Suite feedback-analyzer`, then
`-Suite feedback-disabled` sequentially. Enabled isolated fixtures cover selecting
Review/Comment→optional focus→Analyze→synthetic result/citations→reload/reset;
Viewer/Editor/CSRF/foreign scope/session expiry are verified independently.

NEXT: STOP AT HT-AI-P4-03C OWNER REVIEW GATE. No implementation blocker remains.
Owner reviews UI/limits and decides a separate future task; do not auto-start
P4-03B, live provider, apply-suggestions, another module or deployment. The exact
permanent predeployment question in AGENTS and explicit authorization remain
mandatory before any public/production rollout.

---

## Historical checkpoint — 2026-11-02 — HT-AI-P4-03A DESIGN AND FIXTURE BACKEND COMPLETE

Active Owner-approved task: Feedback Analyzer domain/security audit and safe
fixture backend foundation. Routine technical choices are delegated; no frontend,
live provider, persistent fixture enablement, schema or development mutation.
Preserve all existing FE05/P4-02C dirty work on main/32ccad220bee20540ba7a0e0f6f532250139d48c.
Their implementation/test completion is historical; Owner manual acceptance of
FE05 and P4-02C is still pending, not inferred from existing business rows.

### Source-backed decisions before implementation

- Actual feedback: reviews.Review.comment through Deliverable→Task, plus
  tasks.TaskComment.content. Exclude deleted/tombstone and null/blank sources.
  Deliverable.file_url is only a URL locator, never fetched or treated as media.
  A legacy clients.Client model exists, but no Client Portal/video/transcript
  source is authorized for this task. Project remains pending separately.
- Reuse current can_manage_workspace_tasks: active Profile/Workspace Owner/Admin
  or Profile Member+Workspace Admin. No Editor/Viewer/staff shortcut. Re-resolve
  current actor and nested Task, and selected source IDs. Existing Review decision
  restrictions remain unchanged; history/self-authored feedback can be read for
  advisory analysis without granting self-review or latest-revision approval.
- Existing FeedbackAnalysis/FeedbackInput/FixtureApplicationService.analyze already
  validate bounded text, citations and pre/post authorization/source changes.
  Reuse them and the offline fixed subtitle fixture. AiProposal/AiOperation are
  Generator-specific; no analysis store or fake confirmation is introduced.
- Chosen stateless POST:
  /api/v1/profiles/{P}/workspaces/{W}/tasks/{T}/ai/feedback-analysis/.
  Body: sources:[{kind:review|comment,id:UUID}],1..20 unique selections, optional
  focus≤1000 Unicode chars. Server assigns S1..Sn in request order. Raw source text,
  arbitrary identity/provider/roles/tenant metadata are not accepted from client.
- Response: ai.v1, status READY (transient response, not persisted lifecycle),
  mode fixture_demo, generated_by_ai false, persisted false, fixture.v1, source
  manifest ref/kind/id only, payload ai.feedback.v1, zero fixture usage. No raw
  source/author/URL/prompt or fake proposal/analysis ID/expiry/retrieval route.
- Reuse existing source≤12000 aggregate,20/request32KiB/output64KiB bounds,
  strict parser, existing fixture-disabled/dev-only guard, shared approximate
 3/minute20/day/user generation quota. Stateless repeats reauthorize/recompute;
  no durable idempotency, operation rows, audit or notifications are written.

Read-only development inventory at2026-11-02T06:13:16Z: Docker29.8.2, original
container49ef93152944/docker_postgres_data,loopback5432,hustlytasker_db/PG16.14,
36 applied migrations,29 tables,3 Users/2 Sessions,1 Profile/1 membership/
1 Workspace/1 Task; Review/Comment/AI rows0. Snapshot/235 original source hashes
are ignored .local_backups/HT-AI-P4-03A/ artifacts. No .env access or write.

DONE: repo/domain/AI audit, read-only identity/inventory and source snapshot;
new feedback_services.py/feedback_api.py, additive errors.NOT_FOUND and URL;
43 focused test methods in test_feedback_api.py. Existing services.py changes
only its orchestration docstring; logic is unchanged. No models, migrations,
settings, provider or Generator service/contract change. Runtime/tests are frozen.

Current apps.ai215/215 PASS15.272s, run9477db811e2c45d0873341d7762ac124, includes
43 new Analyzer and172 existing AI regression tests. Launcher/actual Python exits0
verified (Docker events); PG137 is deliberate owned cleanup. pip check, Django,
model drift/graph/full isolated migration chain and owned DB removal all PASS.
232/235 original source files remain byte-identical; only intended errors.py/
urls.py additive changes and services.py docstring differ. All frontend files,
models/migrations/settings/provider and Generator implementation are preserved.
Full backend719/719 PASS217.696s, rund9a4b96be82a4c4c81de1a6332d4fdfd;
launcher and actual Python container exits0 independently verified through Docker
events. All Auth/Invitation/RBAC/Workspace/Task/Subtask/Review/Comment/Notification/
Generator regressions are included. Owned test databases were removed; final
inspection finds0 target/full owned containers and0 networks. No full test skipped.
Frontend537/browser30 below are historical P4-02C, not run in this backend task.

The existing Owner Windows venv py_compile attempt exited103 (its configured
Python312 interpreter is missing). No venv/credential was recreated. The shared
Docker Python3.12/PostgreSQL runner works and provides real current test results.
Final read-only development comparison at2026-11-02T06:34:34.1216245Z matches all
29 tables' row fingerprints, schema/FKs/indexes, sequences, migration history and
cluster identity exactly. Still36 migrations/3 Users/2 Sessions/1 Profile/
1 membership/1 Workspace/1 Task; Review/Comment/AI rows0. Preservation proof and
before/after snapshots remain Git-ignored in .local_backups/HT-AI-P4-03A/.
All6 tested file hashes are stable and232 unrelated original source files unchanged.

No implementation blocker remains. This completes only the design and fixture
backend foundation, not the complete Feedback Analyzer product. Checks are
optimistic reads/re-reads, not locks/serializable snapshots or a guarantee to
revoke responses already delivered. The shared locmem3/minute20/day limits are
approximate, not distributed quotas. The fixed fixture cites the first selected
source but does not understand feedback/media. No persistence/history/recovery/
confirmation/apply-suggestions, live/private provider or Analyzer frontend.

Files changed by P4-03A: new backend/apps/ai/feedback_services.py,
feedback_api.py,test_feedback_api.py; additive errors.py/urls.py; services.py
docstring only. AGENTS.md adds only the permanent predeployment gate. Docs:
FEEDBACK_ANALYZER_FOUNDATION.md, API_DOCUMENTATION.md, AI_ARCHITECTURE_DESIGN.md,
DECISION_LOG.md, PROJECT_CONTEXT.md, REQUIREMENT_STATUS.md, PROJECT_ROADMAP.md,
CHANGELOG.md, DATABASE_SCHEMA.md, PROGRESS.md, HANDOVER.md and related README.
All prior FE05/P4-02C changes remain intact; no commit/push/reset/clean/stash.

Reproduce current checks from root: .\scripts\test-backend.ps1 -TestLabel apps.ai
and .\scripts\test-backend.ps1. Exact native process receipts/stdout/stderr and
actual Python exit events are in the ignored task directory. No fixture/source
selection was POSTed to persistent development. git diff --check and doc links
pass. No frontend/browser tests run in P4-03A because no frontend source changed.

Next: STOP AT HT-AI-P4-03A OWNER REVIEW GATE. Proposed separate P4-03B could
integrate the existing fixture endpoint with React, after explicit authorization.
Live/private-data, persistence/retention and any apply-suggestion mutation need
their own approved scope; do not auto-start P4-03B/C or any deployment.

Permanent deployment gate is added to AGENTS.md from the explicit Owner request:
before any public/production rollout, ask the specified readiness question and
wait for explicit approval. No deployment is authorized or being attempted.

---

## Historical checkpoint — 2026-11-02 — HT-AI-P4-02C IMPLEMENTATION COMPLETE / OWNER REVIEW GATE

Owner now approves the fixture-only React Smart Task Generator preview/edit/
confirm integration. Preserve all33 pre-existing dirty FE05 files on
main/32ccad220bee20540ba7a0e0f6f532250139d48c. FE05/R3 remain completed historical
checkpoints below; manual Owner development acceptance is still unverified.
No live provider, persistent fixture flag change, migration or development test
mutation is authorized. Backend172/172 targeted and676/676 full PostgreSQL tests
have run and PASS; launcher/Python exits0 are independently verified. The
first AI browser attempt is NOT PASS (2 passed/2 failed): exact priority label
selection failed and axe was interrupted during a source reload. Tiny UI
label/target-revision guards are fixed and frozen; stable-source rerun4/4 PASS.
The ignored operational wrapper initially masked the Playwright failure as0;
the actual runner printed FRONTEND_PLAYWRIGHT_EXIT_CODE=1. Failed evidence is
retained under .local_backups/HT-AI-P4-02C/failed-attempt-1-*. The helper now uses
PowerShell -File for reliable launcher propagation; no production harness rewrite.

### Source-backed integration map — before UI coding

Base: /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/ai/task-proposals/.
Every operation requires current active same-tenant manager authority; read/
confirm/replay also require the original proposal actor. SessionAuth/CSRF remains.

| Contract | Actual source behavior |
|---|---|
| Generate POST base |scenario_id: subtitle-check-v1 or task-tree-v1, plus Owner-approved optional synthetic brief≤6000; Idempotency-Key UUID header;201 first/200 replay. Saves proposal/operation, never raw brief or Tasks/AuditLog|
| Read GET {proposal_id}/ |Current scoped original actor only; returns proposal/recovery, no list endpoint|
| Confirm POST {proposal_id}/confirm/ |Literal confirmed:true, proposal_revision and full edited payload; separate scoped UUID key;201 first/200 same-key/body replay|
| Editing |CASE B: confirm validates the edited plan, then creates topologically using existing Task service in one atomic transaction. No separate draft-save endpoint; local edits are not server-saved before confirm|
| Payload |ai.task-plan.v1;1–20 flat nodes with local_ref/parent_ref, max3 child edges; title255/description2000/notes500; LOW/MEDIUM/HIGH/URGENT; nullable timezone-aware deadline; assumptions/warnings≤10×300|
| Lifecycle |AVAILABLE→CONFIRMED or derived EXPIRED.30-minute preview; confirmation clears payload; created_tasks maps local refs to Task UUIDs;30-day recovery; logical expiry is not physical purge|
| Safety/provenance |mode fixture_demo, generated_by_ai:false, persisted:true; zero usage/cost; no live adapter; feature default false and always refused in production|
| Recovery |Known proposal GET after ambiguous confirm; same generate key/body explicit retry can recover lost generation response. Never ordinary Task POST or a fresh blind confirmation key|
| Errors |Shared frontend client now retains only allowlisted sanitized AI codes; typed expiry410/conflict409/throttle429/disabled503/permission403/tenant-safe404 handling, no raw provider error|

TEXT BRIEF DECISION RESOLVED: Owner explicitly selected the bounded optional
synthetic brief extension during P4-02C. Implement max6000 valid Unicode/nonblank,
no raw storage/logging/response echo, body-bound HMAC idempotency, fixed-output
fixture disclosure. Preserve old scenario-only request canonicalization/replay.
No real customer data, live provider, billing or fixture flag enablement on
persistent development is approved. This supersedes only the prior HTTP brief
rejection within the synthetic demo scope; no Task/schema/lifecycle redesign.

Fresh READ ONLY development inventory differs from FE05 history and is preserved:
PostgreSQL16.14, original container49ef93152944/docker_postgres_data/loopback,
36 migrations,3 Users/2 Sessions,1 Profile/1 ProfileMembership/1 Workspace/1 Task,
AI rows0. Do not infer how these records were created or delete them to match
older0-row snapshots. Manual Owner website acceptance remains unverified.
Ignored evidence .local_backups/HT-AI-P4-02C/development-before.json and45
protected model/migration/settings/provider/validator/business-service hashes.

Implemented additive availability: retain existing permission-checked
OPTIONS base response and add ai metadata(enabled/mode/scenarios/limits), no
new endpoint/permission/schema. OPTIONS does not consume POST generation quota.
Transport uses UUID-only Idempotency-Key and allowlisted AI error codes
through the existing API client; no parallel client/auth store.

IMPLEMENTED: permission-checked OPTIONS metadata, brief/body-bound digest,
strict shared transport, scoped entry/page, local supported edits, native explicit
confirmation and GET recovery. No model/migration/provider/business-service edit.
Final component27/27, combined Tasks/Generator51/51 and frontend537/537 across18
files PASS24.35s; typecheck/Biome/build exit0(build8.97s). The first full frontend
attempt527/537 failed because old direct TasksPage tests lacked the new child's
auth context. A boundary mock in that test harness preserves all original
Task/cache/RBAC assertions and the real AuthProvider403 test. Failure logs retained.

| New current-source verification | Result / run |
|---|---|
| Targeted AI backend |172/172 PASS12.169s; c3841cf24120422ca99d584d6d687a9a|
| Full PostgreSQL |676/676 PASS213.712s;75c0d99a663e4d6faed6ed0596df9728|
| AI enabled browser |4/4 PASS49.5s;71178bfad5c24cefac78ec063cd54897|
| AI disabled browser |1/1 PASS8.4s;4edb6ba5399a4416b55b02043a150156|
| Onboarding browser |3/3 PASS43.4s;721e264a15414462a6ce797980bca286|
| Auth/CSRF/tenant browser |6/6 PASS43.6s;0f7a6fa8b7214139acb12691ec6bf24f|
| Workspace/Task browser |7/7 PASS1.2m;ebbf5ff548ca47b6bf6da51a623473e4|
| Collaboration browser |7/7 PASS1.3m;1113feb3287b401fa05e5b8e6da467cd|
| Whole MVP browser |1/1 PASS34.2s;26221457d5694003b2ec6acb3f5392a0|
| Account lifecycle browser |1/1 PASS23.2s;fde86d5ab20946bca133b5b418e5b6a0|

AI browser tests perform Generate/Edit/Confirm through real React and Django,
assert0 Tasks before confirm,2 PENDING parent/child Tasks only after confirm,
edit persistence, same-key replay/no duplicates, lost-response GET recovery,
actor/tenant/Viewer/CSRF denial and ordinary Task creation. PostgreSQL fixtures
and feature enablement exist only in owned isolated server mode serve-ai.
Four-size375/768/1440/812×375 preview/dialog axe0, keyboard/Escape/focus/overflow
and reduced motion PASS. Eight PNGs retained; root viewed preview1440/confirm375.
This is automated isolated verification, not manual development acceptance.

Read-only development comparison at2026-11-02T05:25:34.4313966Z exactly matches
29 tables' row fingerprints, schema/constraints/indexes, sequences, migration
history and PostgreSQL identity. Still36 migrations/3 Users/2 Sessions/1 Profile/
1 membership/1 Workspace/1 Task/AI0. Protected45 source SHA256s unchanged;
tested33 source hashes unchanged before the additional tested harness mock.
Receipt: .local_backups/HT-AI-P4-02C/preservation-proof.json. No .env access,
persistent migration/fixture/flag write or provider call.
Post-all-tests read-only recheck at2026-11-02T05:31:20Z also matches exactly;
final receipts are development-final-after.json and preservation-final-proof.json
in that same ignored task directory. All34 final tested-source hashes are stable.

All eight real isolated browser suites30/30 PASS. Every launcher, Playwright and
backend exit0 is recorded; owned test database removal is confirmed per run.
Final read-only Docker check05:28:55Z finds0 owned frontend/backend containers
and0 networks. No development volume is mounted by tests. Final tested-source
manifest has34 files (the additional TasksPage harness change is test-only).
Normal repository-configured git diff --check and new-file whitespace checks pass.

Next: OWNER REVIEW ONLY. No runtime work or implementation blocker remains;
documentation is synchronized. Do not auto-start Analyzer, live provider or
another task. Retain build advisory(>500kB bundle)
and local-draft limitation: in-app links/beforeunload prompt; SPA Back/Forward may
discard edits, and refresh recovers original proposal rather than local edits.

### P4-02C files, commands and acceptance boundary

Task-owned backend changes: apps/ai/api.py, durable_services.py, test_api.py and
new test_frontend_contract.py. React additions: services/api/ai.ts + ai.test.ts,
features/ai/GeneratorEntry.tsx, pages/task-generator.tsx + test; integration in
app/App.tsx, pages/tasks.tsx, pages/tasks.test.tsx, services/api/client.ts and
styles.css. New browser specs ai-helpers.ts, ai-generator.spec.ts, ai-disabled.spec.ts;
scripts/frontend_integration.py and test-frontend-integration.ps1 extend only
the isolated fixture mode/suite selection. No dependency/models/migrations/settings
or protected Task/Review/Comment/Notification business-service change.

Docs affected: HANDOVER, PROGRESS, ROADMAP, REQUIREMENT_STATUS, CHANGELOG, API,
FRONTEND_GUIDE, PROJECT_CONTEXT, DATABASE_SCHEMA, DECISION_LOG, AI_ARCHITECTURE_DESIGN,
AI_PERSISTENCE_REVIEW, design-system MASTER and README. Earlier dirty FE05 source
and documentation are retained, not claimed as newly implemented AI work.

Reproduce from repository root using the existing shared launchers:

```powershell
.\scripts\test-backend.ps1 -TestLabel apps.ai
.\scripts\test-backend.ps1
.\scripts\test-frontend-integration.ps1 -Suite ai-generator
.\scripts\test-frontend-integration.ps1 -Suite ai-disabled
cd frontend
npm test
npm run typecheck
npm run lint
npm run build
```

Other browser suites: onboarding, foundation, work-management, collaboration,
acceptance and account-security. Each runner uses a fresh owned database and
records Playwright/backend exit and safe cleanup. Ignored logs/process receipts
are under .local_backups/HT-AI-P4-02C/; screenshots remain Git-ignored.

Owner manual website check: start the existing backend and Vite using FRONTEND_GUIDE,
log in and select an authorized Profile→Workspace→Tasks. Manual Create Task remains
available. With fixture disabled, AI entry/direct page must explain unavailability;
this is expected. Do not turn on the persistent flag or create an AI proposal on
Owner's behalf. Full enabled preview/edit/confirm was verified only in isolated
automated mode serve-ai (AI_FIXTURE_ENABLED=True after ownership/test-settings
checks), using synthetic input. A manual development enabled-demo configuration
requires separate Owner authorization. No live provider/manual Owner development
acceptance, SMTP, remote CI or production verification is claimed.

---

## Historical checkpoint — 2026-11-02 — HT-FE-P3-05 IMPLEMENTATION COMPLETE

**IMPLEMENTATION COMPLETE — HT-FE-P3-05 OWNER REVIEW GATE.** All scoped
implementation, isolated backend/frontend/browser checks and development
preservation checks pass. No manual development login/create was performed.

Owner approved **Create Profile & First-Time User Onboarding**. This task ID is
for onboarding, not AI UI. Keep **HT-AI-P4-02C** reserved for Generator preview/
edit/confirm. The older R3 recommendation below was a proposal and is superseded
by this explicit scope; no AI, Invitation UI or membership-candidate work.

Starting evidence: main/32ccad220bee20540ba7a0e0f6f532250139d48c, clean Owner
commit before this task. Existing R1/R2/R3 evidence retained. Read-only development
inventory confirms original container49ef93152944, docker_postgres_data,
hustlytasker_db/127.0.0.1:5432, PostgreSQL16.14,36 migrations,ai.0001 applied,
3 Users/2 Sessions and0 Profile/Workspace/Task/AI rows. No development mutations.
Safe metadata baseline in ignored .local_backups/HT-FE-P3-05/development-before.json;
52 model/migration/AI source hashes saved separately for preservation comparison.

Discovery DONE: existing create_profile_with_owner is atomic, creates an ACTIVE
Profile, active OWNER membership for the supplied User and safe membership audit.
Profile only needs name(max255), with no global name uniqueness. Existing API
was GET-only /api/v1/profiles/. React has no creation form or global active-Profile
store: current tenant is the /profiles/:profileId URL and scoped query keys.
Workspace create already uses the selected route's Profile plus current backend
permission hints. No schema/migration/service rewrite is needed.

IMPLEMENTED: strict authenticated name-only POST on existing Profile collection,
reusing that service and read DTO; protected /profiles/new page, useful Dashboard/
Profiles empty CTA, existing URL selection and Workspace creation integration.
The form is keyed by current User identity, aborting old requests/drafts even
when quiet authentication revalidation changes User without leaving the route.

Current-source verification (not historical643/395/22): targeted backend
40/40 PASS1.577s; full isolated PostgreSQL662/662 PASS245.938s, native launcher
and actual Python container exit0 independently verified through Docker events.
The disposable PG137 exit is intentional owned cleanup, not a test failure.
Dependency/Django/model-drift/full migration chain and owned DB cleanup PASS.
Frontend full426/426 PASS28.98s/16 files; focused54/54 PASS13.22s. TypeScript,
Biome and build gate exit0. No dependencies/settings/models/migrations changed.

Real isolated onboarding browser3/3 PASS48.1s, launcher/Playwright/backend exits0
and owned DB/container/network cleanup PASS. Actual UI first/second Profile,
Workspace creation, selected URL refresh, cross-user privacy, missing CSRF,
injection and session expiry verified. Keyboard/reduced-motion/no-overflow/axe
checked empty/form errors at375/768/1440/812×375;8 PNGs Git-ignored under
.local_backups/HT-FE-P3-05/screenshots/5c76bc72ce04486ba4b953b3d4b17a8e/.
Root inspected desktop empty/mobile form PNGs; not a manual development login.
All six real isolated Chromium suites now pass **25/25**:

| Suite | Result | Run ID |
|---|---|---|
| Onboarding |3/3 PASS48.1s|5c76bc72ce04486ba4b953b3d4b17a8e|
| Auth/CSRF/tenant foundation |6/6 PASS42.8s|4d5dfb6c08864af18eb48134fb74637d|
| Workspace/Task/Start |7/7 PASS1.2m|422da94c66514827a28409e12b5762d3|
| Collaboration/Notifications |7/7 PASS1.3m|33f650b84e9e41f98908d0d03b8759e7|
| Whole Task→Deliverable→changes→resubmit→approve |1/1 PASS35.1s|e15a0cdab307467a826f55255cd2590a|
| Registration/verification/recovery/session |1/1 PASS23.3s|ffc5a52b1a824dbfb24b4f8ec88a8493|

Each suite records launcher/Playwright/backend exits0, owned DB removal and
container/network cleanup. Backend targeted run2e0ba346095840bd92cef8908f766c44;
full run00041f815e944843a08747702f32b8e8. Full includes current Auth/Invitation/
RBAC/Task/Review/AI regressions, concurrent Profile creates and migration tests.
No full test was skipped or represented using a historical baseline. An initial
targeted launcher invocation rejected comma-joined labels before setup; corrected
array invocation passed40 tests. Initial focused mock selector failure was fixed
by selecting the correct success region, without weakening security assertions.

UI UX Pro Max full skill/master read; local focused empty-state onboarding UX
and React async form error searches executed. Apply helpful CTA, visible label,
linked/focused errors, pending duplicate guard and existing teal/neutral tokens.
Do not create another Profile context, auth client, design system or dependency.

### API and behavior contracts

POST /api/v1/profiles/ accepts exactly a text name, trimmed/nonblank/max255,
rejects invalid Unicode/NUL and client identity/role/status/tenant fields. Owner
is request.user. Existing service atomically creates Profile+active OWNER
membership+safe audit; failure leaves no orphan. Response201 uses the existing
five fields id/name/status/created_at/updated_at, with no User/membership PII.
Current active identity, SessionAuthentication/CSRF and GET pagination remain.
Names are not unique; distinct valid/retried POSTs may create distinct Profiles.
No new idempotency/constraint/quota is introduced. After an ambiguous network
result, check the Profile list before deliberately creating again.

React /profiles/new is protected; Dashboard/Profiles show the actionable zero
state and existing Users have create-another in the list header. A successful
response seeds only the new detail, invalidates Profile list pages and selects
/profiles/{id}/workspaces. Existing server OPTIONS/current tenant context gates
Workspace creation. No Workspace is created automatically, no localStorage or
second active-Profile context. Server still enforces all permissions at mutation.

### Development and source preservation

Final read-only comparison at2026-11-02T04:37:31Z matches the pre-task snapshot
exactly: every row fingerprint, schema object, sequence and migration record.
Still36 migrations/ai.0001 applied,3 Users/2 Sessions,0 business/AI rows. Original
container/volume continues running. No persistent test/demo Profile, Workspace,
Task, AI state, User or Session write; no .env inspection/loading or credential
change; no migration or production action. All52 model/migration/AI files and
19 changed runtime/test file hashes remain stable. No test container/network
remains; no unrelated resource or process was stopped or removed.

Evidence is Git-ignored under .local_backups/HT-FE-P3-05/: before/after inventory,
preservation-report.json, schema-ai-before.json, final-runtime-tested.json,
native process receipts/logs and backend Python die-event receipts. Logs contain
synthetic test context only; no secret/environment/legacy row values. Existing
R1/R2/R3 archives/reports remain untouched. No new backup or migration required.

### Changed files and review steps

Backend: workspace/serializers.py,views.py,test_api.py,new
test_profile_creation_api.py. Existing service/models/permissions/URLs unchanged.
Frontend source: app/App.tsx,App.test.tsx; pages/overview.tsx,tenants.tsx,
profile-create.tsx,profile-create.test.tsx; features/profiles/ProfileOnboarding.tsx;
services/api/queries.ts,types.ts,profile-create.test.ts; styles.css.
Browser/test-only integration: e2e/onboarding.spec.ts,account-security.spec.ts;
scripts/frontend_integration.py,test-frontend-integration.ps1 (new Suite onboarding).
Docs: README plus HANDOVER,PROGRESS,PROJECT_ROADMAP,REQUIREMENT_STATUS,CHANGELOG,
API_DOCUMENTATION,DATABASE_SCHEMA,PROJECT_CONTEXT,DECISION_LOG,RBAC_DESIGN,
FRONTEND_GUIDE,FRONTEND_MVP_ACCEPTANCE and design-system/hustlytasker/MASTER.md.
No dependency/settings/authentication/AI edit, commit/push/reset/stash/revert.

No implementation blocker remains. Manual Owner development browser acceptance
is pending; production, real email delivery and remote CI remain unverified.
Invitation UI/general membership onboarding/candidate API and Project remain
separately gated; physical AI purge/shared quotas retain their prior limitations.
See FRONTEND_GUIDE for two-terminal startup and exact manual React steps:
login→Tổ chức→Tạo tổ chức→name→submit→Tạo không gian→name/month→submit→refresh/
open Workspace→Xem công việc. All successful automated mutations ran in isolation.
Owner should restart an already-running backend in their own terminal before
manual acceptance because start-backend-dev.ps1 uses --noreload; then run the
existing backend/frontend two-terminal commands. The agent stopped no Owner app.

**Exact continuation: STOP AT HT-FE-P3-05 OWNER REVIEW GATE.** Owner reviews and
tests the real React flow; do not create their development organization for them,
repeat completed tests/code, reapply AI migration or begin HT-AI-P4-02C/another
task automatically. Final quality PASS:33 changed files (19 runtime/tests,
14 documentation),49 local Markdown/source links valid/0 missing, new-file
whitespace0, runner PowerShell parse0 and git diff --check exit0. HEAD and all
52 protected/19 tested hashes preserved. quality-report.json/final-report.json
retain this evidence; no further code or required verification remains.

---

## Historical checkpoint — 2026-11-02 — HT-AI-P4-02B-R3 DEVELOPMENT MIGRATION SUCCESS

**DEVELOPMENT MIGRATION SUCCESS — OWNER REVIEW GATE.** Owner's R3 request
conditionally authorized exactly `ai.0001_initial` on development. All gates
passed and the migration was applied once. Earlier R1/R2 no-apply instructions
below are historical. No further task, fixture enablement, live provider or
production change is authorized. **Do not rerun the migration.**

### Execution and target

Existing `backend/venv/Scripts/python.exe`, cwd `backend`, ran exactly:

```text
manage.py migrate ai 0001_initial --noinput
```

Native Python exit **0**, no stderr; `Applying ai.0001_initial... OK`.
Database migration timestamp **2026-11-02T04:07:32.213869Z**, or11:07:32
Asia/Saigon. Target: PostgreSQL16.14/hustlytasker_db,127.0.0.1:5432,
original container49ef9315294450710e2c71eefb1559993c821aff94531e79541d9811534ebbbe,
hustlytasker_postgres/postgres:16, volume docker_postgres_data,
cluster7671936116369391654. Engine29.8.2. No container/server restart by R3.

The existing repository environment parser/assertion/process-construction
functions privately consumed the Git-ignored local configuration for child
processes. No secret value was inspected, displayed, serialized or changed.
Startup script/settings/venv remain unchanged. Read-only checks use libpq
read-only guards; the one apply used5s lock/60s statement timeouts, without
disabling security or enabling AI. Immediate preflight preceded apply by seconds:
target/mount/backup/source hashes, no matching application/test process, no other
DB connections and unchanged snapshot/only-AI plan. No external process stopped.

### Backup and preservation

Retained R2 archive:
`.local_backups/HT-AI-P4-02B-R2/20261028T174156Z_12cd6e8c27b34c3f971b84c00aee32cd/development.dump`.
Size **110161 bytes**, SHA256
`c2987ee549e85ee83536f66bd934033cdbe1aa3dd1b06efc6bf9cb6b6195fe5a`.
Current pre-apply schema, all row fingerprints, sequences and history matched
R2's final snapshot exactly. This made that recovered snapshot suitable; no
unnecessary duplicate backup/rehearsal. Owner-context readability/hash/Git-ignore,
251-line TOC/full archive read reverified. Actual isolated restore PASS/exit0
is retained R2 evidence, not a restore rerun in R3. All backups retained unchanged.

| Development verification | Before → after / result |
|---|---|
| Migration records / AI |35/0 →36/1; exactly ai.0001_initial added; no pending migrations|
| Tables / indexes |27/122 →29/136; old schema exact|
| Constraints / FKs |121/44 →139/51; all valid, indexes valid/ready|
| AI columns |AiProposal15, AiOperation9; types/nullability/defaults match review|
| AI integrity |7 validated deferred NO ACTION FKs, lifecycle CHECKs, scoped key uniqueness, partial one-confirmation uniqueness and lookup/expiry indexes verified|
| Framework metadata |ContentTypes23→25, permissions92→100; only2 AI types/8 AI permissions plus1 migration added|
| Existing data |Every old row fingerprint preserved, Users3/Sessions2/AdminLogs7/business0|
| AI rows |Both tables0; no proposal, operation or Task demo created|
| Sequences |Only migration/ContentType/permission sequences+1/+2/+8; every other sequence unchanged|

SQL FKs/constraints do not enforce all cross-table tenant equality, JSON shape,
hierarchy or current RBAC. Those invariants remain in existing services/tests.

### Checks actually run in R3

- Preflight, immediate-preflight, exact migration and post-verification native
  Python exits **0**. Graph/history/model consistency, Django system check,
  makemigrations --check --dry-run, showmigrations ai and migrate --check PASS;
  final migration plan empty. Independent read-only SQL confirmed one AI record,
  empty AI tables, no invalid constraints/indexes and no other DB connection.
- **8/8 actual loopback HTTP GET smoke checks PASS** through Django WSGI:
  health200, CSRF bootstrap200, auth/me403, Profiles403, Notifications403 and
  three AI route boundaries403 for anonymous callers. CSRF token/cookie values
  never logged; error responses minimized. No login, POST, business fixture or
  provider call. All rows/schema/sequences exact before/after smoke. The owned
  temporary HTTP listener closed; no server or isolated test resource remains.
- AI fixture setting false; no live adapter/provider enabled. All210 reviewed
  runtime hashes match R1/R2 and R3 before/after. No source/model/migration edit.
- R1's72/158 and full643 results remain historical. They were **not rerun** in
  R3; no full-suite, authenticated mutation success or browser UI E2E is claimed.

Evidence stage:
`.local_backups/HT-AI-P4-02B-R3/preflight-005e4ca1ceb04629b47166c777360c95/`.
Contains development-before.json, preflight/post snapshots and reports,
runtime-before.json, final-sql-check.json and native process receipts. The
single-attempt marker prevents automatic reapply. The helpers are Git-ignored
operational artifacts, not application code; no private environment/row values.

### Files, remaining limits and exact continuation

Preserved main/157d495ccc7afe42980d6af7a83dd7f432296092 and the six dirty R2
documentation files. R3 updates documentation only: HANDOVER, readiness,
PROGRESS, PROJECT_ROADMAP, REQUIREMENT_STATUS, CHANGELOG, DATABASE_SCHEMA,
PROJECT_CONTEXT, API_DOCUMENTATION, AI_PERSISTENCE_REVIEW and DECISION_LOG.
No commit/push/reset, fixture enablement, production action, restore or rollback.

No R3 blocker remains. Overall Generator is still PARTIAL: frontend preview/
edit/confirm, live providers and Analyzer are absent. Physical retention purge
and shared multi-worker quotas remain unimplemented. This is development DDL
success, not production/live-AI readiness. Project and onboarding gates remain.

**Exact next step: STOP FOR OWNER REVIEW.** Recommend a separately approved
HT-FE-P3-05 fixture preview/edit/confirm UI, reusing current backend contracts and
isolated tests. Do not start it or enable fixtures/live AI automatically. On any
later anomaly inspect schema/history first; never automatically fake, retry,
rollback or restore development.

Final R3 quality:11 documentation files dirty only; all58 local Markdown/source
links valid/0 missing; four documented PowerShell blocks and the operational
helper parse with0 errors; git diff --check exit0. All210 reviewed runtime hashes
unchanged. Final checks/receipts are retained in quality-report.json and
r3-final-report.json in the R3 stage. No untracked non-ignored source file,
isolated container/network or owned HTTP listener remains. R3 is complete;
**STOP AT OWNER REVIEW GATE**, no migration reapply or follow-on implementation.

---

## Historical checkpoint — 2026-10-29 — HT-AI-P4-02B-R2 READY / OWNER APPROVAL REQUIRED

**HT-AI-P4-02B-R2 — READY FOR DEVELOPMENT MIGRATION EXECUTION — OWNER APPROVAL
REQUIRED.** This means preparation only; ai.0001_initial remains unapplied.

Owner authorizes read-only preflight, fresh inventory/backup/integrity/recovery
verification, plan and checklist only. **NO DEVELOPMENT MIGRATION EXECUTION IS
AUTHORIZED.** Stop at PRE-EXECUTION OWNER GATE after checks. Source baseline is
main/157d495ccc7afe42980d6af7a83dd7f432296092, clean Owner commit; preserve it.
Migration ai.0001 SHA2FA99CFCD14334E270F178EFDEAF1FD0BE7381C1F20459EF5836D535651CBF55
is unchanged/additive-only. No runtime/model/migration edit, .env read or provider.

Fresh read-only preflight: Engine29.8.2; exact original container49ef93152944,
hustlytasker_postgres/postgres:16, docker_postgres_data,127.0.0.1:5432;
PostgreSQL16.14/UTF8/en_US.utf8.35 migrations/0AI; no AI tables;27 tables,
122 indexes,121 constraints/44 FKs all valid/ready. Users3/Sessions2/AdminLogs7/
ContentTypes23/permissions92; all business/token/Audit rows0. No other DB
connections/active transactions or matching Django/Vite process was observed at
inspection; no process was stopped. R2 baseline data matches the newer R1-resume
User/Session snapshot, not the old R1 backup. All snapshots are count/schema/hash
metadata only; no private row values are printed.

Fresh retained archive:
`.local_backups/HT-AI-P4-02B-R2/20261028T174156Z_12cd6e8c27b34c3f971b84c00aee32cd/development.dump`
110161 bytes, SHA256
`c2987ee549e85ee83536f66bd934033cdbe1aa3dd1b06efc6bf9cb6b6195fe5a`.
Custom pg_dump/copy/251-line TOC/full archive read exits0, host/container hashes
match, Git-ignored. Exact Owner account read/write/hash was verified before
archive creation; protected DACL has no broad user-group grant. Initial benign
permission probe failed because only Sandbox/SYSTEM/Admin grants existed;
explicit Owner-account access resolved it without granting broad groups or
touching R1 backups. The timestamp is UTC; local date is29 October.

Artifact stage:
`.local_backups/HT-AI-P4-02B-R2/preflight-12cd6e8c27b34c3f971b84c00aee32cd/`.
It holds inventory.sql, fresh development-before.json, runtime-before.json,
context.json, backup-metadata.json and a new read-only preflight_restore.py.
Runtime snapshot210 files. Do NOT run the old R1 helper: it applies AI schema
and runs mutation tests, which are not part of this R2 preparation scope.

DONE: fresh restore command --single-transaction/--no-owner/--no-acl/
--exit-on-error exited0 on owned database
ht_ai_r2_12cd6e8c27b34c3f971b84c00aee32cd, isolated systemID7701777503690309672,
role ht_test_runner and comment hustlytasker-ai-r2:12cd6e8c27b34c3f971b84c00aee32cd.
The existing test Compose topology verified internal network/tmpfs/no public
DB ports/no persistent development-volume mount. Host→target archive SHA matched.

Redacted evidence is r2-report.json in the stage. Five checkpoints PASS; direct
Python PID1 command/exit0 independently inspected:

| R2 checkpoint | Actual result |
|---|---|
| Fresh restore identity/data/schema comparison |All27 tables, logical columns/constraints/indexes, sequences, migration history and every row fingerprint match the fresh source snapshot, including current User/Session state |
| Dependency check |pip check exit0 |
| Read-only Django check/model/graph/history/plan |PASS; default_transaction_read_only and transaction_read_only verified ON; plan exactly ai.0001_initial forward, two CreateModel; default fixture flag false |
| Restored snapshot preservation |All data/schema/sequences unchanged after checks;35 migrations/0AI; no AI tables or new business rows |
| Source preservation |162 scoped helper hashes stable; separate210-file host snapshot unchanged versus R1 and R2 baseline |

No helper path invokes migrate. No AI migration was applied even in isolation;
no test suite/fixture/mutation/API provider was run. R1's72/158 and implementation
643 remain historical, not R2 results. The prior migration rehearsal remains
applicable to unchanged source/schema; this fresh restore proves recovery of the
newer snapshot. Catalog comparison uses the reviewed logical ordinal and native
PostgreSQL CHECK reparsing, without relaxing any constraint or changing source.

DONE: owned restore DB removed only after exact system/owner/comment/no-use
checks; shared labeled container/network cleanup exit0. No isolated resource
remains. Original container49ef93152944/volume stays running. Final development
READ ONLY comparison matches the fresh R2 baseline in every row fingerprint,
schema object, sequence and migration:35 records/0AI,3 Users/2 Sessions and all
business rows0. No active external DB connection or matching Django/Vite process
was seen at initial/final inspection. These observations do not reserve a future
quiet window. R1 archive is retained and unchanged; R2 archive remains protected.

The reviewed future command is manage.py migrate ai 0001_initial --noinput in
the existing backend venv/cwd, through the documented loader-aware child-process
procedure. It is commented/gated, NOT executed. Expected later outcome is two AI
tables15/9 columns,7 FKs,18 constraints/14 indexes plus exactly1 migration record,
2 ContentTypes and8 permissions; original rows stay exact. Metadata sequences
may increase only by the expected1/2/8; other sequences must remain unchanged.
No fixture/live flag or business data creation is part of that authorization.

R2 Git changes: HANDOVER.md, AI_DEVELOPMENT_MIGRATION_READINESS.md, PROGRESS.md,
CHANGELOG.md plus roadmap/requirement current-status reconciliation. No runtime,
model, migration, settings, secrets or dependency change; no commit/push/reset.
The backup/helper/report artifacts are local and Git-ignored.

**Exact continuation: STOP AT PRE-EXECUTION OWNER REVIEW GATE.** Ask for separate
explicit approval of exact ai.0001_initial on DEVELOPMENT hustlytasker_db,
127.0.0.1:5432, hustlytasker_postgres/docker_postgres_data only. Before any later
write, reverify target/source checksum, unchanged AI-only plan, current inventory,
backup freshness and quiet window. If anything changed, stop and refresh the
affected preflight/backup evidence rather than applying from stale approval.
Never auto-stop a server, fake migration history, rollback/restore development,
enable live/fixture AI, run business fixtures or start frontend/another task.
See AI_DEVELOPMENT_MIGRATION_READINESS.md for exact execution/post-check/recovery
checklist. Passing preflight is not execution permission; no blocker currently
remains except the required Owner approval and immediate pre-write rechecks.
Final R2 quality checks:26 local Markdown links valid/0 missing, both documented
PowerShell blocks parse without errors, git diff --check exit0;210 runtime hashes
unchanged and both retained R1/R2 archive checksums match. Only six documentation
files are dirty against the Owner's main/157d495 baseline.

---

## Historical checkpoint — 2026-10-29 — HT-AI-P4-02B-R1 MIGRATION READINESS VERIFIED

**MIGRATION READINESS VERIFIED — OWNER REVIEW GATE.** Development apply of
`ai.0001_initial` is still **NOT AUTHORIZED**. R1 execution evidence below is
from2026-10-28; the2026-10-29 resume verified retained artifacts/current targets
and completed documentation, without rerunning backup/restore/tests. All older
checkpoints below this section are historical and do not authorize more work.

### Resume classification

| Item | Status / evidence |
|---|---|
| Source/migration audit | DONE — unchanged ai.0001, two additive CreateModel operations; no business-schema/data operation |
| Read-only database inventory | DONE — original development identity verified, inventory described below |
| Docker/PostgreSQL health | DONE — Engine29.8.2, original PostgreSQL16.14 container49ef93152944 running; no restart/recreate |
| Backup preparation | DONE — unique timestamp/run path, Git-ignored, protected local archive |
| Backup creation | DONE — retained custom archive110161 bytes; no overwrite/new dump in resume |
| Backup integrity | DONE — dump/copy/TOC251/full archive read and host/container SHA-256 checks; hash rechecked in resume |
| Isolated restore | DONE — owned PostgreSQL tmpfs/internal network/no public port; restore exit0 |
| AI migration on restored DB | DONE — exact ai.0001 only, standard Django; no development apply |
| Schema/data preservation | DONE — private row fingerprints/sequences/logical schema checks and metadata allowlist |
| Isolated smoke/security | DONE —72 restored-DB tests; separate fresh AI158, both actual exits0 |
| Test resource cleanup | DONE — owned DB/containers/network removed with gates; none remain at resume inspection |
| Development rollout plan | DONE — documented only; apply command commented and separately gated |
| Documentation/HANDOVER | DONE — readiness report and coordination documents synchronized |
| Final report | DONE — evidence and approval package in AI_DEVELOPMENT_MIGRATION_READINESS.md |

Development rollout, live AI, frontend AI, Analyzer, Project and onboarding are
OUT OF SCOPE. No remaining implementation blocker exists for this readiness
task. Current data drift and backup-access limits below remain review items.

### Retained backup and completed rehearsal

Archive:
`.local_backups/HT-AI-P4-02B-R1/20261028T125103Z_c7060a0b55c94f41b44d5c440325d89c/development.dump`

Size110161 bytes; SHA-256
`306e3c49d11b03da3a5e46f7ea6cf5acde2035cd418a44bfb3c09c1bb1144585`.
Custom archive,251-line TOC/full read and actual restore all exited0. It remains
Git-ignored/protected/retained, not uploaded or overwritten. Workspace-context
host readability/hash is verified. The restricted escalated worker's FILE_READ_DATA
limit was handled by binary transfer of the exact matching container-temp archive;
target hash matched. Normal manual Owner readability is not claimed; no broad
Everyone/Authenticated Users/Builtin Users grants were added as a workaround.

Owned restore run c7060a0b55c94f41b44d5c440325d89c used database
`ht_ai_r1_c7060a0b55c94f41b44d5c440325d89c`, private systemID7701703092750774312,
role ht_test_runner and comment hustlytasker-ai-r1:c7060a0b55c94f41b44d5c440325d89c.
Before apply, all27 legacy table fingerprints/sequences/history/logical schema
matched the backup. Comparison preserved visible column order/types/defaults,
normalizing only two historical dropped-column physical slots. Fifteen CHECK
array-cast renderings were reparsed with PostgreSQL on ON COMMIT DROP temporary
tables and required exact canonical equality, without weakening constraints.

Only that restored target received ai.0001: two tables15/9 columns,7 FKs,
18 constraints and14 indexes valid/ready. Its totals became29 tables/136 indexes/
36 migrations,25 ContentTypes and100 permissions. Exactly1 migration record,
2 ContentTypes and8 permissions were added; every original row hash remained.
Users3/Sessions2 were comparison data only, never used as AI fixture identities.

| Verification executed2026-10-28 | Result / actual exit |
|---|---|
| Direct restored-database synthetic security/atomicity/idempotency |72/72 PASS7.337s;0 failures/errors/skips; Python PID1 exit0 |
| Separate fresh-cluster AI migration/concurrency/security |158/158 PASS12.242s; run edc9c2a3ee964c9c9843abb7aa141ad8; launcher/Python exits0 |
| Dependency/Django/model-drift/graph/full-chain/plan |PASS; only pending ai.0001 before restored apply; no pending plan after |
| Owned DB/container/network cleanup |PASS; shared cleanup exit0 after owner/comment/system/inactivity checks |

The72 tests used selected Django TestCase classes directly on the restored DB,
without DiscoverRunner/new database/flush. Rollbacks left legacy data unchanged
and AI rows0. The158 concurrency/migration tests ran separately on a fresh cluster.
Earlier helper exit1 attempts stopped before migration on ACL/catalog comparison
issues and were corrected only in ignored operational helpers. Full643 is
historical, not rerun or claimed as a new R1/resume result.

Retained redacted report:
`.local_backups/HT-AI-P4-02B-R1/c706-final-report.json`.
Operational metadata/helper stage (no raw archive/rows):
`.local_backups/HT-AI-P4-02B-R1/rehearsal-c7060a0b55c94f41b44d5c440325d89c/`.
The helper checked162 scoped runtime files. A separate host snapshot checked210
runtime files unchanged across R1. Resume source baseline is retained at
`.local_backups/HT-AI-P4-02B-R1/resume-20261029-runtime-hashes.json`.

### Development preservation and the later resume delta

R1's2026-10-28 before/after comparison verified every development row fingerprint,
schema object and sequence unchanged. At2026-10-29 resume, the original container/
volume/loopback target is still hustlytasker_postgres/49ef93152944,
docker_postgres_data,127.0.0.1:5432. Schema/sequences/history remain identical:
PostgreSQL16.14,UTF8/en_US.utf8,35 migrations/0AI,27 tables,122 indexes,
121 constraints/44 FKs; business/token/Audit rows0. AI tables remain absent.

Counts remain3 Users/2 Sessions, but one User and one Session row fingerprint
changed between the R1 final snapshot and this resume. Actor/cause is not
verified; no private values were queried or logged. Do not describe all current
data as unchanged since28 October. This resume used READ ONLY inventory, did not
mutate/revert those rows and did not recreate an older state. The original R1
preservation proof remains scoped to its execution window. The retained backup
is not certified as the latest User/Session state; take a fresh backup and
inventory during a quiet window before any separately approved development apply.
Current safe metadata snapshot is development-resume-20261029.json in the stage.

### Files, limits and exact continuation

Only R1 documentation changed: AI_DEVELOPMENT_MIGRATION_READINESS.md, HANDOVER.md,
PROGRESS.md, PROJECT_ROADMAP.md, REQUIREMENT_STATUS.md, CHANGELOG.md,
DECISION_LOG.md and DATABASE_SCHEMA.md. Ignored backup/helpers/reports are local
operational artifacts. Existing dirty code/model/migration/settings files were
preserved. No .env read, credentials change, provider call, production action,
commit/push/reset or database development mutation occurred. Existing venv
Python3.12.5/pip check worked in the escalated context; no venv repair was done.

Physical AI purge and shared multi-worker quota remain outside R1. See
[AI_DEVELOPMENT_MIGRATION_READINESS.md](AI_DEVELOPMENT_MIGRATION_READINESS.md)
for exact future environment loading, command, downtime and failure/restore
limitations. **Exact continuation: STOP FOR OWNER REVIEW.** Require a separate
explicit approval for controlled ai.0001 development rollout with fresh gates;
do not apply from this handover, enable providers or start another task.
Final resume checks:31 local Markdown links valid,0 missing; future PowerShell
plan parsed with0 errors;210 current runtime hashes unchanged; git diff --check
passed. No completed backup/restore/test step was rerun in the final resume.

---

## Historical checkpoint — 2026-10-28 — HT-AI-P4-02B-R1 IN PROGRESS

**IN PROGRESS — BACKUP RESTORED / ISOLATED MIGRATION VERIFICATION PENDING.** R1 permits
read-only development inventory, backup and isolated restore/migration/security
verification only. **Persistent-development apply of ai.0001_initial is NOT
authorized.** Keep all previous dirty source/documentation on main/502a444;
no runtime rewrite, commit/push/reset, live AI or frontend task.

Fresh read-only development identity: PostgreSQL16.14, hustlytasker_db,
container49ef93152944/hustlytasker_postgres, docker_postgres_data,
127.0.0.1:5432; encoding UTF8, locale en_US.utf8. There are35 migration records,
no AI migration/tables,27 existing tables,122 indexes,121 constraints including44
FKs; checked indexes/constraints are valid/ready. Counts:3 Users,2 Sessions,
7 Admin logs,23 ContentTypes,92 permissions,0 inventoried business rows.
Other active connections were0 at inspection. No private row/session/hash values
or .env contents were printed and no development data/schema mutation occurred.

New retained local backup:
`.local_backups/HT-AI-P4-02B-R1/20261028T125103Z_c7060a0b55c94f41b44d5c440325d89c/development.dump`

- PostgreSQL custom archive,110161 bytes.
- SHA-256: `306e3c49d11b03da3a5e46f7ea6cf5acde2035cd418a44bfb3c09c1bb1144585`.
- Dump/copy/pg_restore --list/full archive read exits0; TOC251 lines. Host and
  container sizes/hashes match. Backup is Git-ignored and must be retained.
- Backup ACL protection has no Everyone/Authenticated Users/Builtin Users grants.
  Initial Windows ACL setup denied escalated-worker file access; access was
  corrected for the exact intended identity without broad group grants. The
  protected host archive remains readable/checksum-verified in the workspace
  context; the restricted escalated worker still cannot FILE_READ_DATA. This is
  a worker-access limitation, not evidence of a failed dump, and does not prove
  normal manual Owner readability. Do not weaken ACLs merely to bypass it.
- Binary BaseStream transfer from the exact matching development-container
  temporary archive to the isolated target completed with both process exits0;
  target SHA-256 matches the protected host backup. Restore command
  pg_restore --exit-on-error --single-transaction --no-owner --no-acl exited0.
  Row/schema preservation and actual AI migration are still pending; restore
  exit0 alone is not yet the complete readiness result.

Owned ht-test-c7060a0b55c94f41b44d5c440325d89c target was verified through existing
Compose labels/repository/mount/port checks: internal network, PostgreSQL tmpfs,
no public DB port or development-volume mount. Restore database is exactly
ht_ai_r1_c7060a0b55c94f41b44d5c440325d89c, isolated systemID7701703092750774312,
owner ht_test_runner and comment hustlytasker-ai-r1:c7060a0b55c94f41b44d5c440325d89c.
The test PostgreSQL container remains in use; do not cleanup while helper runs.
Next, compare schema, migration history and legacy row fingerprints privately, apply
exact ai.0001 only on that restored isolated DB, and validate expected new metadata
separately. Run selected synthetic security/smoke tests there; the proposed72
TestCases have not run. New fresh-cluster AI158/158 PASS12.242s, run
edc9c2a3ee964c9c9843abb7aa141ad8: launcher0, Python PID1/container die exit0,
pip/Django/model-drift/graph/full-chain checks and owned DB/container/network
cleanup passed. This is fresh-cluster concurrency/migration/security evidence,
not a test of the restored backup. Historical378/643 below are not R1 results.

Files changed by R1 documentation checkpoint: AI_DEVELOPMENT_MIGRATION_READINESS.md,
PROGRESS.md and HANDOVER.md. Existing code/model/migration/other dirty files stay
preserved. The detailed readiness report is
[AI_DEVELOPMENT_MIGRATION_READINESS.md](AI_DEVELOPMENT_MIGRATION_READINESS.md).
Exact continuation: complete isolated restore/migrate/data-preservation/security
checks and actual exits, then verify owned cleanup and read-only development
preservation. Keep the backup, finish the concrete rollout plan and stop at
OWNER REVIEW GATE. Passing R1 does not authorize the development migration.

---

## Historical checkpoint — 2026-10-28 — HT-AI-P4-02B IMPLEMENTATION COMPLETE

**IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL.**
**STOP AT OWNER REVIEW GATE.** This covers only the fixture Generator backend.
The overall Smart Task Generator remains PARTIAL: no React AI UI/live adapter.
Everything below this current checkpoint is historical unless explicitly reused.

Owner explicitly approved fixture-only Generator backend, concrete manager gate,
durable state and additive migration tested ONLY in isolated PostgreSQL. New
approved v1 policy: confirmation eligibility30 minutes, unconfirmed payload7 days,
recovery metadata30 days; no automatic physical purge if unsafe/unimplemented.
Live/production/provider/Analyzer/frontend remain unauthorized. Previous AI02A
dirty files and docs are preserved on main/502a444; no commit/push/reset.

Schema gate completed BEFORE writing models/migration; see AI02B_SCHEMA_REVIEW.md.
Two tables: AiProposal and scoped AiOperation. PROTECT tenant/actor FKs, status/
timestamp CHECKs, unique actor/Profile/Workspace/operation/key, partial UNIQUE one
CONFIRM per proposal. UUID generated only server-side. Confirmed marker independent
of payload/result so scrub never reopens creation. No cross-table CHECK claim.

Code now present: apps.py/models.py/migrations/0001_initial.py, durable_services.py,
api.py/urls.py, API/durable/concurrency/migration tests. Existing settings register
AI app and add default-false DJANGO_AI_FIXTURE_ENABLED; api/urls includes3AI routes.
Existing errors/provider extended only for lifecycle codes and task-tree synthetic
scenario. No Task/User/business model or applied migration modified. Generate
accepts only two server scenario IDs, no raw brief. Provider call is outside own
transactions; common tenant→proposal→operation lock order. Confirmation reuses
unchanged create_task in one atomic batch, no assignment/status override.

Docker recovered after the previous session's interruption. Current read-only
inspection verified Engine29.8.2 and the unchanged development identity:
hustlytasker_postgres/postgres:16, docker_postgres_data,127.0.0.1:5432. No old
test process/container/network remained; run c8e199e5f66e46bd8f88109019a87637
is historical/uncompleted, not a test result. No restart/prune/development action.

First current isolated run5b8b150d67be48e7a9501b28e5d9c0ff:154/154 PASS10.410s,
launcher exit0, dependency/Django/model-drift/graph/full-chain checks and owned
database/container/network cleanup passed. This is an intermediate result:
afterward generation audit was removed to meet the latest explicit requirement
that generate creates no Task or AuditLog rows, both generation replay branches
were aligned on expiry, and regression proofs were added for final-audit rollback,
concurrent generation, stale deactivated actor and expired session/old CSRF.
Final targeted run bf34f0b7fd384c7a9958b4513cea18ac:158/158 PASS11.208s.
Targeted Task/Review/Workspace/RBAC run d41c6561e93f4b6489e0a858d87a75de:
378/378 PASS165.639s. Both launcher exits0 and Python container die events0
were verified; owned databases/containers/networks removed. Disposable PostgreSQL
exit137 is the launcher's intentional rm --force cleanup, not Python test failure.
Full run6bdba3440f8d46edb28df73a9b30fe03:643/643 PASS215.115s, launcher exit0
and Python container die exit0. Confirmed the test container command was directly
python /workspace/scripts/test_backend.py. Dependency/Django/model drift/graph/
history/full migration-chain checks and owned database/container/network cleanup
passed in all final runs. No test container/network remains; original development
container49ef93152944/volume is still running and was not restarted/recreated.
Historical77/562 below is not current proof. Frozen210 runtime file hashes match
across the final targeted/full tests, with no changed/removed path.

Read-only development verification: PostgreSQL16.14/hustlytasker_db,35 migration
records, no ai migration/tables,3 Users/2 Sessions. Inventoried Profile/membership/
Workspace/invitation/token/Task/assignment/Deliverable/Review/TaskComment/
Notification/Audit/Client/ShareLink/Invoice/Payment rows all0. SQL used BEGIN READ
ONLY and ended ROLLBACK; no .env/key/password/session value read or printed.
One initial inventory statement used the wrong Comment table name and failed;
after inspecting TaskComment source, the corrected read-only inventory passed.
No persistent schema/data mutation or AI migration apply occurred.
Final post-test read-only check again confirmed35 migrations/0AI migrations,
both AI tables absent,3 Users/2 Sessions and0 Profile/Workspace/Task/Audit rows.

DONE: current AI158 includes36 API tests,42 durable-service/concurrency tests,
3 additive empty/related-data/forward/reverse/constraint migration tests and77
existing contract/boundary tests. Verified current manager/original actor, expiry,
cross-tenant denial, Session/CSRF/session expiry, canonical same/different-key
replay, concurrent generate/confirm, archive/revoke serialization, Task/node/audit
failure rollback, stable recovery and HMAC fallback. Full643 covers existing
Authentication/account security/Invitation/Workspace/Task/Review regressions.
No frontend/browser/live-provider test was needed or claimed by this backend slice.

API base: /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/ai/task-proposals/.
POST base generates; GET {proposal_id}/ reads/recover results; POST
{proposal_id}/confirm/ confirms. Both POSTs require UUID Idempotency-Key and CSRF.
Generate accepts scenario_id only: subtitle-check-v1/task-tree-v1. Confirm takes
positive proposal_revision, literal confirmed=true and complete edited payload.
Provenance mode=fixture_demo/generated_by_ai=false/persisted=true/usage0. Manager
checks are repeated under existing tenant locks, with no is_staff shortcut.
See API_DOCUMENTATION.md for strict schema/errors and UI-state contracts.

Physical7d/30d retention is NOT automatically enforced: reads mask expired payload,
recovery stops30d and confirmation clears payload, but controlled purge is deferred.
AI-D decisions are updated only to Owner-approved fixture scope; future live
parts remain pending. Generation throttles3/minute and20/rolling-day/user are
process-local/non-atomic; no shared production quota or live budget guarantee.
Do not enable the default-off DJANGO_AI_FIXTURE_ENABLED on unmigrated development.
No implementation blocker remains within this bounded scope; persistent rollout,
physical purge, frontend, live/provider budgets and Analyzer are separate gates.

Source inventory for this task (including previously existing dirty AI02A files):
- Existing tracked integration changes: backend/config/settings.py and
  backend/api/urls.py only. No existing User/Task/business model, applied migration,
  Task/Review/Comment/Notification service, frontend or dependency change.
- New02B AI files: apps.py, models.py, migrations/__init__.py,
  migrations/0001_initial.py, durable_services.py, api.py, urls.py,
  test_api.py, test_durable_services.py and test_migrations.py.
- Extended existing AI02A files: __init__.py/contracts.py docstrings,
  errors.py lifecycle codes and providers.py fixed Task-tree scenario. Original
  validation.py/services.py/test_contracts.py/test_boundaries.py are preserved.
- Documentation: HANDOVER, PROGRESS, PROJECT_ROADMAP, REQUIREMENT_STATUS,
  CHANGELOG, PROJECT_CONTEXT, DECISION_LOG, API_DOCUMENTATION, DATABASE_SCHEMA,
  AI_ARCHITECTURE_DESIGN, AI_PERSISTENCE_REVIEW and AI02B_SCHEMA_REVIEW.

UI UX Pro Max and the current design master were read. Focused error-summary
validation search ran with existing Python image/read-only skill mount/network
none, exit0: keep inline fields plus focusable summary for the future UI. Safe
API error fields/lifecycle states support it; no frontend UI/a11y PASS is claimed.

Reproduce from repository root, with Docker available; runner never reads .env:
```powershell
.\scripts\test-backend.ps1 -TestLabel apps.ai
.\scripts\test-backend.ps1 -TestLabel @('apps.tasks','apps.reviews','apps.workspace')
.\scripts\test-backend.ps1
```

Exact next step: Owner reviews this implementation. Recommended separate task:
controlled development rollout of ai.0001_initial after fresh identity/inventory,
backup/readability/isolated restore rehearsal and exact plan approval. Then Owner
may authorize P4-02C fixture preview/edit/confirm UI. Do not run either task, enable
live AI, create/apply another migration or change Project/onboarding automatically.
No .env read, credentials change, production action, commit/push/reset occurred.
Final documentation validation found57 valid local Markdown links,0 missing;
git diff --check passed and new AI files have no trailing whitespace.

---

## Historical Owner review checkpoint — 2026-10-28 — AI DECISION PACKAGE PREPARED

Current task is the Owner's final review package for AI-D01–AI-D10, not P4-02B
implementation. Read the architecture/persistence/decision/RBAC/schema/status
documents and current Git evidence. Branch main/502a444; existing AI02A dirty
source and documentation are preserved. No decision status changed: every
unapproved portion of AI-D01–AI-D10 remains PENDING OWNER APPROVAL.

The report distinguishes already approved contracts/fixture-only scope and
unchanged tenant/workflow safeguards from recommended future provider, feature
authority, durable stores, expiry/retention, quotas and confirmation policies.
Recommended next slice for review: backend durable Generator flow with explicit
human confirmation and current tenant checks, using fixtures only and live budget
zero until a separate provider/data/budget authorization. This recommendation is
not approval to create models/migrations, endpoints, Tasks or enable a provider.

Key dependencies: AI-D02/03/04/06/09 gate real authorization/persistence/atomic
confirmation; AI-D05 gates applicable shared quotas and any live spend; AI-D01/10
may be deferred for an explicitly approved fixture-only slice; AI-D08 primarily
gates the later Analyzer. Physical retention/recovery windows and model quality
thresholds have no approved numeric values. Revoked/inactive/cross-tenant users
must never recover saved content or created IDs through replay; archived-preview
policy remains an AI-specific pending decision, not permission from Task reads.

This review did not read .env, run providers, access databases, change runtime,
models/migrations/settings, commit or push. Only this handover checkpoint was
added. Public provider documentation was consulted for policy context; no model
API call/key/account/billing action. Prior AI77/full562 results below are retained
evidence from AI02A, not tests rerun for this report. Final Git diff/whitespace
check passes. Exact next step: Owner chooses/approves pending decisions and a
bounded next scope; STOP AT OWNER REVIEW GATE without implementation.

---

## Historical checkpoint — 2026-10-28 — HT-AI-P4-02A IMPLEMENTATION COMPLETE

**IMPLEMENTATION COMPLETE — OWNER REVIEW PENDING.** This status covers only the
approved stateless contracts/fixture slice. Live AI, durable state/confirmation,
public endpoints and frontend AI are NOT STARTED. Stop at OWNER REVIEW GATE.

Owner authorizes typed contracts, strict validation, a deterministic offline
fixture adapter and persistence/locking review only. This is not blanket approval
of AI-D01–AI-D10. Branch main, starting HEAD502a444, initially clean. The previous
task's changes were committed by Owner before this task; do not reset that history.

DONE: new internal backend/apps/ai package (not an installed Django app), immutable
DTOs, strict bounded JSON/input/Task DAG/deadline/citation validation, static safe
errors, provider Protocol, fixture adapter and fail-closed application boundary.
No models, routes, settings, migrations, SDK, key, live calls, persistence or Task
mutations. Fixture requires explicit test/development construction and opt-in;
production/unknown environments refuse it. No .env is read. Access/source ports
are integration contracts, not a new permission engine or approved AI role grant.
Default access denies; concrete tenant/feature integration remains approval-gated.

Fixture text is fixed synthetic output, not analysis of input by a model. Usage
is zero and provenance explicitly fixture/not generated by AI/not persisted.
All fixture output passes the same strict parsers intended for later adapters.
The bounded fixture limits are technical test contracts, not approved live quotas.
AI_PERSISTENCE_REVIEW.md documents options, scoped idempotency/confirmation,
expiry vs retention and lock/FK risks. No durable guarantee is implemented today.

Current evidence: final shared runner apps.ai77/77 PASS0.046s, run
98c2aecfd05649b0b12c34bc6c617352. Actual launcher/Python exits0; pip check,
Django checks, no model drift, graph/full migration chain and owned DB/container/
network cleanup pass. Prior contracts45 and combined73 runs also passed but are
not final-source evidence after added hardening/citation tests. Initial full
558/558 PASS204.386s (run3e55332122104f0cbf3e0b63fb1d22af) was discovered before
four additional tests and final provider hardening; do not use as final result.
Final full suite run28724dd1667a4fb59dd4932567b9ca3f: **562/562 PASS201.889s**,
actual launcher/Python exits0 and owned DB/container/network cleanup completed.
Pip check, Django system check, makemigrations --check --dry-run, graph/history/
model consistency and complete existing migration chain passed in the isolated
runner. New tests are discovered by the default full runner despite no new
installed app. All eight code hashes match their frozen final-test baseline.
All DB activity is isolated; development was not connected. Historical35/3/2/0
is not a fresh inventory, and no AI migration exists or was applied anywhere.

DONE: boundary/no-network/file-read/no-mutation/error tests and independent review.
Review fixed a hardcoded S1 citation so valid S2-only selection works, strict
limits/control types and finite non-bool clock/cancellation checks. Fixture content
stays synthetic. UI UX Pro Max/master read; focused error-summary search ran via
read-only/no-network existing image, exit0; contracts support later accessible
inline errors/summary, without React UI. No frontend typecheck/lint/build/browser
rerun because frontend is unchanged. No live-provider quality, cost-enforcement,
durability or real AI-RBAC integration claim follows from fixture tests.

Files from this task: eight new backend/apps/ai files (__init__, contracts,
validation, errors, providers, services, test_contracts, test_boundaries); new
AI_PERSISTENCE_REVIEW.md; updated AI_ARCHITECTURE_DESIGN.md, HANDOVER.md,
PROGRESS.md, PROJECT_ROADMAP.md, REQUIREMENT_STATUS.md, CHANGELOG.md,
PROJECT_CONTEXT.md and DECISION_LOG.md. Final comparison: all209 original runtime
hashes/path set preserved, exactly eight new AI files, no tested-code drift.
Documentation links/whitespace and normal git diff --check verified; no existing
runtime, dependencies, frontend, settings, routes, models or migrations changed.

Reproduction commands from repository root (Python supplied by existing isolated
image, no local venv repair or .env needed):

```powershell
.\scripts\test-backend.ps1 -TestLabel apps.ai
.\scripts\test-backend.ps1
```

No blocker remains in the approved technical slice. AccessPort has no concrete
product authorization/source DB implementation: default denial is intentional
until AI-D02 and the next integration scope are approved, not a missing public
feature silently labeled complete. RATE_LIMITED/BUDGET_EXCEEDED are error contracts
only; there is no active limiter/ledger. Cancellation is cooperative, not a live
provider cancellation or refund guarantee. Physical retention/purge remains open.

Exact next safe step: **STOP AT OWNER REVIEW GATE.** Owner review persistence
options/AI-D01–AI-D10 and then explicitly authorize the next bounded P4-02B scope.
Do not infer installed-app/schema/live/confirmation/frontend approval from this
completion status. Do not create models, call a provider or start a new task.

---

## Historical checkpoint — 2026-10-28 — HT-AI-P4-01 DESIGN COMPLETE

**DESIGN COMPLETE — PENDING OWNER APPROVAL. AI implementation: NOT STARTED.**
Owner authorized documentation/design only. Branch main, HEAD e083060; all
pre-existing dirty FE02/API/FE03/API03A/FE04 work is preserved. No runtime,
settings, model, migration, frontend, private environment or database change.
No .env read, database connection, SDK installation, model API call, key/account/
billing setup or cost. No disposable resources were created or need cleanup.

Primary deliverable: [AI_ARCHITECTURE_DESIGN.md](AI_ARCHITECTURE_DESIGN.md),
20 sections covering both use cases, shared adapter/service, strict JSON/API
proposals, privacy/provider/cost review, threat matrix, UX, tests and roadmap.
Source verified LOW/MEDIUM/HIGH/URGENT, nullable aware deadlines, root depth0
plus at most3 child edges, no estimated_duration, Project or durable AI stores.
Existing tenant predicates, create_task locks/validation/PENDING/audit and
independent Deliverable/Review/Comment/Notification workflow are unchanged.

Proposed flow: generate a bounded plan, human preview/edit, separate confirmation,
fresh tenant/role checks, atomic calls to existing Task services. Analyzer uses
selected authorized text/citations and has no business mutation. Every stored
analysis GET/replay must recheck current readable/nondeleted sources; stale data
must not return its old payload. Confidential fingerprints stay server-side as
versioned HMAC; public provenance uses opaque revision. Shared API client will
need a backward-compatible AI error extension in a future approved code slice.

All provider/model choices, feature authority, numeric caps, new app/persistence,
expiry/physical retention and live-data policies are PROPOSED, not APPROVED.
Suggested defaults: disabled, labeled deterministic fixtures first; Gemini
gemini-3.5-flash-lite for server-curated synthetic-only live demo if eligible;
GPT-6 Luna or Gemini Standard Paid for private data only after contract/privacy/
account review and quality evaluation. Official public sources accessed2026-10-28
are linked in the design. No account quota, latency, Vietnamese quality or live
integration is verified. Unpaid mode cannot accept business text by trusting a
client checkbox. No automatic model/provider/paid fallback.

Durable proposal/invocation/usage/idempotency requires a separately approved
additive schema and retention/lock design. Unique request scope+key+body and
single-confirmed proposal protect replay across keys; no network in DB locks.
Budget and business lock families/implicit FK locks require concurrency tests.
Expired unconfirmed preview does not redispatch. Committed same-key confirmation
can recover existing IDs after fresh authorization within retained-ledger policy;
it never creates the batch again. LocMemCache is not a cross-worker budget guard.

UI UX Pro Max full skill/master and focused UX/React searches were applied to
design text: Brief→Preview/Edit→Confirm, inline selected-feedback analysis,
accessible pending/error/focus states and keyboard Move up/down alternative.
No React component or new design system was created.

Current documentation verification (not application tests):

- Independent provider and source/security/UX reviews completed; findings above
  incorporated. Source/requirement traceability and proposed-only labels checked.
- Five JSON blocks parsed; two schemas and three synthetic examples checked
  against every keyword used via an in-memory subset validator, plus sample
  DAG/depth/citations. This is not a full JSON Schema engine or runtime AI test.
- Cost arithmetic checked: at2000 input/1000 total billable output tokens,
  Gemini Standard estimates0.31/3.10/31USD and OpenAI Standard0.07/0.70/7USD
  for100/1000/10000 requests. These exclude taxes/other listed costs, not invoices.
- 20 local Markdown links checked, no missing targets. Runtime path set and all
  209 SHA-256 hashes equal the task-start baseline. Only8 documentation files
  changed. Normal git diff --check exit0; CRLF conversion notices are harmless.
- Optional Python JSON Schema engine availability probe could not run: the
  existing Windows venv points at a missing base Python312 executable. Nothing
  was recreated or repaired; this is outside the design-only scope. The in-memory
  documentation validation above ran successfully without installing packages.
- No backend/frontend/Playwright tests rerun. Historical FE04395/22/13 and
  backend485 remain baseline only. Development35 migrations/3 Users/2 Sessions/
  0 business rows is historical, not freshly inventoried in this task.

Files changed by THIS task only: AI_ARCHITECTURE_DESIGN.md (new), HANDOVER.md,
PROGRESS.md, PROJECT_ROADMAP.md, REQUIREMENT_STATUS.md, CHANGELOG.md,
PROJECT_CONTEXT.md and DECISION_LOG.md. Existing API_DOCUMENTATION, database/
RBAC docs, design master and every runtime dirty/untracked file are preserved.

Pending: Owner review AI-D01–AI-D10 in design section18 (provider/data mode,
authority, durable storage, expiry/retention, caps, strict plan/atomic batch,
dates, Analyzer scope, operator policy and private-data/live evaluation).
No design blocker remains; live account policy/quality and future schema need
approval before implementation. Project and onboarding retain separate gates.

Exact next safe step: **STOP AT OWNER REVIEW GATE.** Proposed next work is
P4-02A contracts/fixture and detailed app/schema/retention/locking review, only
after explicit code/scope approval. Then separately approved Generator backend/
UI slices, Analyzer and hardening. Do not infer approval from DESIGN COMPLETE;
do not call a provider, apply migrations or begin a new task automatically.

---

## Historical checkpoint — 2026-10-27 — HT-FE-P3-04 COMPLETE / OWNER REVIEW GATE

Owner approves MVP completeness audit, bounded missing frontend using existing
APIs, cohesive real UI acceptance and safe PowerShell local startup. Preserve
all existing main/e083060 dirty work. No backend/schema/migration/business-rule/
auth architecture change, persistent business fixtures, AI/Project or next task.

Owner decisions now explicit: MVP is account lifecycle plus current Workspace/
Task/Review/Comment/Notification. Invitation UI, Profile Creation, member-candidate
API and remaining membership onboarding/management are OUT OF CURRENT TASK SCOPE
/ PENDING OWNER REVIEW, retained as future product requirements. Do not add them.

DONE source before resume: new account pages/contracts/tests, registration and
login links, personal account navigation; safe startup launcher+guard tests;
completeness/AI design notes; two real browser specs and isolated mailbox bridge.
No duplicate implementation. Existing Workspace/Task/collaboration and five hints
remain. Historical485 backend/356 frontend/browser7+7+6 are baseline only.
DONE during resume: corrected2 unsupported test-only ByRoleOptions in App tests;
corrected acceptance test login expectation to respect legitimate return route,
then navigate via real sidebar. Neither change weakens application authorization.

Current frontend395/395 PASS14files15.94s; TypeScript0, Biome52files0,
productionbuild6.65s0 (JS479.99kB/gzip139.09kB,CSS39.06kB/gzip11.00kB).
Actual retained native-process exits and paired logs verify. Initial failed
typecheck/acceptance results are retained, not relabelled PASS.
Real isolated acceptance1/1 PASS43.6s, run6a1ec11fb62741aabcc330571015c828:
Task and Subtask creation; parent Task assignment/Start/Submit/changes/resubmit/
approve, comments/read-notification/logout+different User all through React.
The child remains PENDING, proving no automatic status cascade. Separately labeled negative
CSRF/replay/old/self/tenant API probes; axe0 four viewports. Account-security1/1
PASS22.4s, run77a73580faf34927b8970208eca6f658: real UI register/no auto-login,
verification through locmem delivery, neutral reset requests, reset, old-session
expiry/replay/old-password denial and new-password login. All native launcher/
Playwright/backend exits0 and owned DB/resources cleanup verified. Real email
delivery NOT VERIFIED. Final real browser verification totals22/22 across5 suites:

| Suite | Result | Run ID |
|---|---|---|
| Cohesive MVP UI acceptance | 1/1 PASS43.6s | 6a1ec11fb62741aabcc330571015c828 |
| Account lifecycle UI | 1/1 PASS22.4s | 77a73580faf34927b8970208eca6f658 |
| Collaboration | 7/7 PASS1.2m | 8a940dabeedc41ceaf63b8669f461b28 |
| Workspace/Task/Start | 7/7 PASS1.0m | e1470330e0904f9d92e5254324892455 |
| Auth/CSRF/tenant | 6/6 PASS36.3s | 5d6f2f14dbbf4829ad54c0d054584d81 |

All actual native launcher/Playwright/backend exits0, Django check/model-drift/
full migration chain and owned DB/container/network cleanup verified. Successful
Task and account mutations above are actual React actions; direct negative API
probes and fixture setup are labeled separately. Missing CSRF, nonassignee,
Viewer, self-review, old revision, wrong-state/replay, tenant IDOR, revoked access,
archived contexts and session expiry keep existing behavior. Account tokens are
issued by unchanged services, delivered to locmem and consumed through a guarded
container-only mailbox helper into Node memory; no fake API or token logging.
No real provider delivery is inferred from this adapter.

UI UX Pro Max full skill/master and actual focused authentication/navigation/
async-error searches were applied to paste/autocomplete, visible labels, linked
focused safe errors, pending/abort and native focus behavior. Existing teal/
neutral tokens, typography/layout/components stay unchanged. Axe WCAG2/2.1AA0
violations, no horizontal overflow and keyboard/focus/dialog checks pass at375/
768/1440 and812x375 landscape. New acceptance4/account12 screenshots plus current
regression PNGs retained in ignored run folders. Empty Register375, Reset812 and
completed Task1440 PNGs visually inspected; populated secrets are never captured.
No interactive manual browser claim. Final frontend tests include the final
acceptance-spec fix (source predates final TypeScript/Biome/build verification).

Local configuration update resolved: Owner's two configured values were actually
in .env.example, with no root .env. Root preserved the exact values into a NEW
Git-ignored root .env and blanked only example secret fields; no generated or
changed credential and no value printed. Do not overwrite/recreate this .env.
ValidateOnly0 and existing venv Python3.12.5 Django check0 PASS. Read-only Django
connection to PostgreSQL16.14/hustlytasker_db PASS, no pending migration;35 records,
Users3/Sessions2/all business-token-Notification-Audit0, metadata92/23/7 unchanged.
Actual Django8000 and Vite5174 startup/proxy smoke PASS helperexit0: direct/proxy
health and CSRF bootstrap200, anonymous me403, profiles403, register OPTIONS200.
No persistent login or unsafe request. Token/cookies not printed or stored in
logs. Controlled child-server stops exit-1 (intentional termination), not a claim
of graceful server exit0. Backend connection and smoke evidence are ignored in
.local_backups/HT-FE-P3-04/. Existing venv is not broken; sandbox103 is access.
No credential blocker remains. Manual Owner browser/real email/remote CI/production
remain unverified. Final readonly Django inventory again matches before smoke:
all27 public-table counts identical,35 migration records/no pending migrations,
3 Users/2 Sessions/all business-token-Notification-Audit0. No persistent business
or authentication writes occurred. Final launcher guard13/13 PASS/native0;
configuration validation, actual Django check and read-only DB helper each exit0.

Root owns docs, overall security/connectivity/read-only development verification.
Agents own scripts/start-backend-dev.ps1+tests, bounded account lifecycle frontend,
and isolated acceptance spec/launcher selection. All must read AGENTS/current
source; frontend uses full UI UX Pro Max/master and actual focused searches.
All144 protected backend/model/service/migration/config/harness/package hashes
match preflight; no model/schema/migration/backend-application/dependency change.
Full backend485/485 is historical API03A baseline, NOT rerun/relabelled in FE04.
No owned frontend test containers/networks or local smoke servers remain.
Main/HEAD e083060 and earlier dirty code preserved; no commit/push/reset/revert,
venv rebuild, database/volume reset, production action or automatic migration.

Current task files: NEW frontend/src/pages/account-security.tsx+test and services/
api/account-security.ts+test; App.tsx/App.test.tsx, AppLayout.tsx, pages/auth.tsx,
services/api/client.ts/queries.ts/types.ts; NEW e2e/mvp-acceptance.spec.ts and
account-security.spec.ts; scripts/frontend_integration.py and existing frontend
launcher; NEW scripts/start-backend-dev.ps1 and test-backend-dev.ps1. Test mailbox,
fixtures and suite selection are test infrastructure, not application backend.
Root ignored .env contains only preserved Owner configuration; .env.example has
blank secret fields. Edit only private .env for local credentials going forward.
Docs: HANDOVER/PROGRESS/ROADMAP/REQUIREMENT_STATUS/CHANGELOG/PROJECT_CONTEXT/
FRONTEND_GUIDE/API_DOCUMENTATION/MASTER/README/DECISION_LOG and NEW
FRONTEND_MVP_ACCEPTANCE.md. AI readiness, JSON/tenant/hierarchy/human-confirmation
dependencies and SRS/HLD/Project discrepancies are design-only notes there.

DONE: approved MVP audit, account UI, cohesive acceptance/regressions, startup,
connectivity, privacy/source/data checks and affected documentation. PARTIAL/TODO/
BLOCKED within approved implementation: none. OUT OF SCOPE: deferred onboarding,
Project, AI implementation and other business domains. AUTOMATED VERIFIED /
MANUAL OWNER CHECK PENDING. REAL EMAIL DELIVERY NOT VERIFIED. Remote CI and
production are unverified; this is not an all-product/production-ready claim.

Source baseline, initial dirty inventory, paired logs/native exit JSON, aggregate
browser_final_evidence.json, startup/local connectivity/read-only/source safety
evidence are ignored under .local_backups/HT-FE-P3-04/. Screenshots for the two
new suites use its screenshots/<run-id>/; regression screenshots retain existing
FE01/FE02/FE03 runner paths. Exact safe continuation: Owner reviews the completed
MVP and runs the two-terminal procedure in FRONTEND_GUIDE with the existing .env.
Do not overwrite credentials or rerun implementation/migrations. Recommended
next separately approved task: review/design AI provider/API/JSON/permission/cost
contract using the readiness notes; Project and onboarding keep their own gates.
STOP at OWNER REVIEW GATE; no AI/onboarding/Project/next task starts automatically.

---

## Historical checkpoint — 2026-10-27 — HT-API-FE-P3-03A COMPLETE / OWNER REVIEW GATE

**HT-FE-P3-03: IMPLEMENTATION COMPLETE.** All three former core API gaps are
resolved and current acceptance checks pass. No next task is authorized.

Owner now approves resolving the three FE03 gaps through additive read-only
capabilities and real frontend mutations. Preserve all existing dirty FE02/
API02A/FE03 work on main/e083060; no reset/commit/schema/migration/auth/RBAC or
service-workflow change, no persistent development fixtures/writes.

Source verified before code: Task.can_submit uses current active assigned Editor,
WORKING and no unresolved PENDING/SUBMITTED Deliverable. Deliverable.can_approve/
can_request_changes use manager authority, Task.REVIEW, SUBMITTED, latest by
created_at DESC/id DESC (not numeric revision), non-self uploader and no Review
row. Comment.can_edit/delete require current commenter authority, nondeleted
row, author for edit and author-or-manager for delete. Tombstone delete hint is
false even though the unchanged service keeps repeat-delete idempotent.
All fields bind authenticated request/verified tenant context and fail closed;
mutation services remain authoritative under existing locks. No new endpoint.

DONE before resume: backend serializers/query context/annotations,37 new security
tests, frontend required guards/Submit/Approve/RequestChanges forms and server-
based old-comment controls. These parts were preserved, not rewritten on resume.
DONE during resume: equivalent-path query-growth test correction, real UI browser
flows, final runtime verification, independent source review and documentation.
Five exact field names approved: can_submit/can_approve/can_request_changes/
can_edit/can_delete. UI forms reuse existing master/native dialogs; no redesign.
Targeted PostgreSQL95/95 PASS13.020s, runa718df8ac97a4813aa6c2aebfff0ccd8:
native launcher/Python exits0 and owned DB cleanup verified. Initial94/95 run
failed a query comparison between all-REJECTED versus eligible-SUBMITTED paths;
test now compares the same eligible role path, retaining strict +1 query-growth
bound. No service change; initial failed logs retained separately.
Frontend356/356 PASS12files41.49s; actual native typecheck/lint46/build6.69s exits0.
JS465.75kB/gzip135.48kB, CSS39.06kB/gzip11.00kB. No dependency/lock change.
Full isolated PostgreSQL485/485 PASS231.054s, run3b2abcd913324644b6240bfc49ca1c18.
Actual native launcher/Python exits0, Django OK and owned DB cleanup verified.
pip check, Django check, makemigrations --check --dry-run, graph/history/model
drift and full migration chain all PASS in isolated PostgreSQL. Existing
Authentication/account security/Invitation/RBAC/Task/hierarchy/Review/Notification
regressions are included; historical448 is not used as current evidence.

Real isolated Django/PostgreSQL/Chrome browser results on final source:

| Suite | Result | Run ID |
|---|---|---|
| Collaboration | 7/7 PASS,1.3m | ff6abc6459954d6d83f47ec94c426a62 |
| Workspace/Task/Start | 7/7 PASS,1.1m | 3074e74939f84f3b8039665dab7196ba |
| Auth/CSRF/tenant | 6/6 PASS,43.0s | c125145b536b480badeccfba582f4c90 |

All actual native launcher/Playwright/backend exits0, owned DB/container/two-
network cleanup verified. Browser collaboration now performs Submit → Request
Changes → resubmit → Approve through React with a separate reviewer context,
plus independent first-submission approval. Task state is read from backend,
never overridden by client. Existing Comment reload/navigation/page2 edit and
author deletion, manager moderation, Viewer denial, missing CSRF403, stale
revision409, cross-user Notification404, real events/read count/navigation,
revoked target and session-expiry cleanup all pass. Negative API assertions and
fixture setup are labeled separately; they are not substitutes for UI mutations.
The collaboration spec changed after initial checks, so final TypeScript/Biome
were repeated on the final E2E source: both native exits0,46 linted files.

UI UX Pro Max full instructions and existing teal/neutral master were reused.
Actual focused UX error-summary/modal-focus and React async-error searches
informed linked errors, caught failures, pending/abort, native dialogs and focus.
No new theme, dependency, upload/storage or component framework. Axe WCAG2/2.1AA
0 violations, no horizontal overflow, native-dialog keyboard/focus/Escape and
reduced-motion checks pass at375/768/1440 and812x375 landscape.24 collaboration
screenshots retained under .local_backups/HT-FE-P3-03/screenshots/<run-id>/;
Submit375/RequestChanges812/Approve1440 PNGs were visually inspected. No claim of
interactive manual browser review, production, real email or remote CI testing.

Final readonly development identity verified again: original
hustlytasker_postgres, loopback127.0.0.1:5432/docker_postgres_data,
PostgreSQL16.14/hustlytasker_db.35 migrations,3 Users,2 Sessions; all checked
business/token/Notification/Audit rows0, metadata23 content types/92 permissions/
7 Admin logs unchanged. No persistent login/fixture/write/migration/restore.
All137 protected backend/model/service/migration/config/harness hashes unchanged;
no new migration/model or dependency/lock change. No owned backend/frontend test
containers/networks remain. Main/e083060 and all previous dirty work preserved;
no commit/push/reset, venv recreation, production action or infrastructure change.

Current task code files: backend/apps/tasks/{serializers.py,views.py,
comment_serializers.py,comment_views.py,test_api.py,test_comments.py,
NEW test_collaboration_capabilities.py}; frontend/src/features/collaboration/
{TaskCollaboration.tsx,TaskCollaboration.test.tsx,NEW CollaborationActions.tsx,
NEW CollaborationActions.test.tsx}; services/api/{collaboration.ts+test,
work-management.ts+test}; TaskForms.test.tsx and pages/tasks.test.tsx typed fixture
updates; frontend/e2e/collaboration.spec.ts. Other pre-existing dirty source,
including Workspace/API02A/FE03 shell/Notifications/test infrastructure, is kept.
Affected docs: HANDOVER,PROGRESS,ROADMAP,REQUIREMENT_STATUS,CHANGELOG,CONTEXT,
API_DOCUMENTATION,FRONTEND_GUIDE,FE03_CONTRACT_MATRIX,MASTER and README. Schema,
RBAC and accepted architecture decisions have no new change in this task.
Paired logs/native exit JSON/source baseline/final readonly inventory/safety
evidence live ignored under .local_backups/HT-API-FE-P3-03A/.

DONE: all source, security/runtime/UI/browser checks and documentation. PARTIAL/
TODO/BLOCKED within this approved task: none. Limits: no separate Deliverable
edit/delete/upload API (new revision uses existing workflow); no real email,
production, remote CI or AI integration verified or added. Notification/Review
transaction policy and locked service authorization remain unchanged.
Exact safe continuation: Owner reviews this completed extension and FE03 closure.
Do not rerun implementation/migrations or start another task automatically.
Suggested next work for separate approval is SRS/HLD and Project architecture
review, reconciling optional cross-month Profile/Client Project ownership; Project
remains PENDING OWNER DECISION in PROJECT_ARCHITECTURE_REVIEW.md. No Project/AI/
frontend domain starts before a new approved scope. STOP at OWNER REVIEW GATE.

---

## Historical checkpoint — 2026-10-26 — HT-FE-P3-03 PARTIAL — API GAP / OWNER REVIEW GATE

Owner authorizes frontend Deliverable/Review/Comment/Notification UI only.
Read AGENTS/HANDOVER/current docs/source; preserve all dirty FE02/API02A work on
main/e083060. No backend/model/migration/auth/security change or persistent
development writes. Existing review gate superseded only for this FE03 scope.

Before code, verified matrix is documentation/FE03_CONTRACT_MATRIX.md. Existing
Deliverable/Review reads, Comment creation/manager moderation and personal
Notification feed/count/read/navigation are supported. GAP: no can_submit or
general self-membership mapping in WORKING; Review OPTIONS is role-only and
cannot prove non-self/latest workflow permission; existing Comment author IDs
cannot prove current User for old comments. Keep unsupported mutations hidden,
do not fix backend without separate approval. Only legitimate current-scope
comment POST response can prove ownership for that exact newly created comment
while the authenticated component remains mounted; discard proof on remount.

Resume checkpoint: preserved typed collaboration contracts +18k TaskCollaboration
source from interrupted work; they were not recreated. Contracts/client focused
106/106 PASS after safe-URL lint/control test fix. TaskCollaboration27/27 PASS:
bounded Deliverable/review reads, new-comment ownership proof, manager moderation,
Unicode4000 validation, aborts and stale-GET cancellation before confirmed cache
redaction. New NotificationHub12/12 PASS covers feed/filter/page/read/errors,
User-keyed cache/late response isolation, aborts and count/preview behavior.
Root integrated TaskCollaboration into existing detail using current User passed
by existing authenticated Layout Outlet; no second AuthProvider. Personal
/notifications route, navigation, bell/native-dialog preview, unread counter
and same-origin mark-read are implemented. Query reads hide stale private rows
on failed revalidation and denied targets are redacted; no extra polling.
Shared CSS/tokens retained with responsive collaboration/notification patterns.

Final mocked/contract frontend322/322 PASS (11files,21.69s), native npm exit0.
An intermediate320/321 failure was an old App test assuming only one status
region; its loading-message selector was corrected. Strict TypeScript, Biome44
files and production build13.75s PASS (JS460.14kB/gzip134.24kB;
CSS39.06kB/gzip11.00kB), actual exits0. No dependency/lockfile changes.

Real isolated PostgreSQL/Django/Chrome browser suites, current source:
- collaboration7/7 PASS1.4m, runca613d41c174462c9375f03c201ac4c8;
- Workspace/Task/Start7/7 PASS1.6m, runf97f35926ad24bc2abb174f9a4edd83d;
- Auth/CSRF/tenant6/6 PASS55.6s, runf7f4970fb102434699fcd26c9ef9d8e2.
All actual native launcher/Playwright/backend exits0, owned DB/container/two-
network cleanup verified. Collaboration Submit/Review transitions are explicitly
API-driven, not evidence of blocked UI mutation actions. Backend448 is
historical, not rerun because all backend source is unchanged at this checkpoint.
Each isolated startup did Django system/model-drift/full-chain/migrate checks;
existing migrations run only on disposable test DBs, never persistent development.
Current axe WCAG2/2.1 AA0violations, viewport-overflow, keyboard/native-dialog/
focus and reduced-motion checks passed at375/768/1440 and812x375 landscape.
12 collaboration screenshots retained;4 representative desktop/mobile Task,
notification feed/preview PNGs visually inspected. No interactive manual browser
or production/real-email/remote-CI verification claim.
Root owns routing/layout/styles/notification/docs and cache integration; agents
own new contracts, Task collaboration component and new collaboration E2E.
Previous448/224/7/6 results are historical. Final readonly development identity:
PostgreSQL16.14/hustlytasker_db, original hustlytasker_postgres, loopback5432,
docker_postgres_data.35migration records/Users3/Sessions2, all checked business/
token/Notification/Audit rows0. No persistent login/fixture/write/migration.
All144 protected backend/config/model/migration/harness hashes unchanged, stored
ignored in .local_backups/HT-FE-P3-03/protected_baseline.json.0 owned frontend
test containers/networks remain. Existing dirty FE02/API02A work and main/e083060
are preserved; no commit/push/reset or Owner runtime/venv recreation.

DONE: independent Deliverable/Review reads, bounded Comment UI, personal
Notifications, Task-detail integration, final checks and affected documentation.
BLOCKED/API GAP: Submit in WORKING; Approve/Request Changes with verified non-self/
latest capabilities; general old-comment author edit/delete. No unblocked code
or test work remains. Safe next step: Owner reviews UI and approves a bounded
HT-API-FE-P3-03A read-capability proposal (can_submit/per-Deliverable review/
per-Comment edit/delete), using unchanged service predicates/no schema changes.
That task is proposed only. Do not infer backend authorization from this handover
or mark FE03 COMPLETE with these core gaps. No Project/AI/FE04 starts automatically.

FE03 source inventory: NEW services/api/collaboration.ts+test,
features/collaboration/TaskCollaboration.tsx+test,
features/notifications/NotificationHub.tsx+test, pages/notifications.tsx,
e2e/collaboration.spec.ts. Existing frontend files changed minimally: App.tsx+
App.test.tsx, AppLayout.tsx (authenticated Outlet identity and bell/nav),
pages/tasks.tsx, styles.css, client.ts (content/file_url/comment safe field text).
Integration-only scripts/frontend_integration.py and test-frontend-integration.ps1
add owned fixtures and -Suite collaboration; ownership gates retained.
Docs refreshed: HANDOVER,PROGRESS,ROADMAP,REQUIREMENT_STATUS,CHANGELOG,CONTEXT,
FRONTEND_GUIDE,MASTER,API_DOCUMENTATION, NEW FE03_CONTRACT_MATRIX and README.
Ignored paired logs/exit JSON and screenshots live under .local_backups/HT-FE-P3-03/;
regression screenshots keep existing FE01/FE02 runner paths. No backend file was
modified during FE03; prior backend dirty changes belong to completed API02A.

---

## Historical checkpoint — 2026-10-26 — HT-API-FE-P3-02A COMPLETE / OWNER REVIEW GATE

Owner authorizes the bounded API/FE gap-resolution task. Existing FE02 dirty work
is preserved on main/HEAD e083060; no commit/reset/schema/migration or persistent
development writes. The previous gate is superseded only for these two gaps.

Verified source: TaskAssignment.user is a User FK, while assignment inputs/read
identity use ProfileMembership. Start requires active Profile MEMBER + active
Workspace MEMBER, active tenant lifecycle, active current User assignment and
ASSIGNED status. Existing transaction-locked Start service stays unchanged.
Plan approved within task: add TaskRead.can_start from authenticated request and
verified workspace context; existing manager-only WorkspaceMemberRead adds
display_label + is_assignable. Full-name label or safe membership-code fallback,
never email/username fallback. Existing roster visibility/pagination preserved.
No new endpoint/role or access expansion. Only the approved manager display
label is exposed; no email/phone/credential/global User ID fields are added.

DONE implementation: four backend modules tasks/serializers.py+views.py,
workspace/serializers.py+access.py add the three fields and bounded query reads;
no model/service/auth/rule changes. NEW tasks/test_identity_api.py33tests plus
two expected-field sets. Frontend typed guards/TaskStart/assignment labels and
roster integrate both hints; direct Start invokes existing protected service.
Selector submits ProfileMembership ID and filters backend is_assignable, no
client-role identity inference. New browser coverage tests actual Start CSRF/
nonassignee denial/success/replay plus label/eligible roster, not API mocks.

Current targeted PostgreSQL91/91 PASS8.358s, run824d2ba3d4464db5978f8b6ab1895a53,
actual native launcher/Python runner exits0 and owned DB cleanup verified.
Frontend targeted107/107 and full224/224 PASS10.20s, typecheck and lint PASS exits0.
Production build PASS6.42s (JS434.13kB/gzip127.67kB,CSS37.12kB/gzip10.65kB).
node_modules was empty on preflight; npm ci restored181packages from unchanged
lockfile, no dependency upgrade. Work browser run0f46f8b31207406c8b073d606b593d36
7/7 PASS1.1m; actual native/Playwright/backend exits0 and owned cleanup verified.
Real current-assignee Start, nonassignee denial, missing CSRF403 and replay409
passed. Friendly roster labels/exact membership ID/backend eligibility and
no extra email/User fields verified. Four-size axe/overflow/keyboard and existing
Workspace/Task flows passed;20 screenshots retained in reused FE02 run directory.
Full PostgreSQL448/448 PASS199.251s, runcb5fc651e02340989ac22c21b64d8857;
actual native/Python exits0, Django OK and owned test database removal verified.
Runner also passed pip check, Django system check, model drift, migration
graph/history/full-chain checks. No historical415 substitution.
Foundation browser run10f640b6e0e44666874a9cb1a9939186:6/6 PASS36.3s, actual
native/Playwright/backend exits0 and owned cleanup. Current Auth/CSRF/login/logout/
expiry/revoked-access checks passed. Typecheck, Biome36files and git diff check
PASS on final source. Two Start PNGs (375/1440) visually reviewed; current real
browser axe/keyboard/overflow/reduced-motion checks cover four viewports.
No interactive manual browser, real-email/provider, remote-CI or production claim.

Both gaps resolved; HT-FE-P3-02 is now IMPLEMENTATION COMPLETE after its earlier
acceptance criteria were rechecked with the extension. No implementation blocker
or pending migration. Development readonly identity/counts remain PostgreSQL16.14,
hustlytasker_db/hustlytasker_postgres, loopback5432/docker_postgres_data,
35migrations/Users3/Sessions2/all checked business/token/Notification/Audit rows0.
No persistent login/fixture/write/migration.135 protected backend/model/service/
migration/config/harness hashes unchanged; package+lock unchanged. node_modules
restoration did not replace the Owner's Node or Python runtime.

Current task changed backend tasks/serializers.py, views.py, test_api.py,
NEW test_identity_api.py; workspace/access.py, serializers.py, test_write_api.py.
Frontend changes on preserved FE02 files: services/api/work-management.ts+test,
features/tasks/TaskForms.tsx+test, features/workspaces/WorkspaceMembers.tsx,
pages/tasks.tsx+test, e2e/work-management.spec.ts. Integration fixture only:
scripts/frontend_integration.py. No new endpoint/model/migration or service edits.
Docs refreshed: HANDOVER,PROGRESS,ROADMAP,REQUIREMENT_STATUS,CHANGELOG,API,
FRONTEND_GUIDE,PROJECT_CONTEXT and RBAC_DESIGN; README frontend scope reconciled.
Previous FE02 dirty files remain
uncommitted on main/e083060; all earlier change inventories below are historical.

Evidence: ignored .local_backups/HT-API-FE-P3-02A/ contains paired backend/browser
logs, native/Docker-exit JSON and protected hash baseline. Work20screenshots are
under reused .local_backups/HT-FE-P3-02/screenshots/0f46f8b31207406c8b073d606b593d36/;
foundation artifacts retain the FE01 directory by runner convention.
Safe continuation: stop for Owner review; do not rerun implementation or database
rollouts. Proposed HT-FE-P3-03 requires separate approval. Project remains PENDING
OWNER DECISION; no AI/frontend domain expansion is authorized.

---

## Historical checkpoint — 2026-10-26 — HT-FE-P3-02 PARTIAL — API GAP / OWNER REVIEW

Owner authorizes Workspace/Task business UI on the existing frontend, with no
backend business/schema/auth change or persistent development writes. Initial
Git is clean, main/HEAD e083060 (Owner committed the preceding foundation).
Do not reset/recreate frontend, rerun rollout or infer Project/AI approval.
The prior FE01 gate is superseded only for this explicitly approved FE02 scope.

DONE: read current task, AGENTS/HANDOVER/design master/docs/source. Verified
Workspace/Task write/read/filter/assignment contracts and permissions. Existing
foundation/design tokens/AuthProvider/API client are retained. Work is split:
typed work-management API/contracts/OPTIONS hints; Workspace callback-prop
components; new isolated fixtures/browser suite; root Task UI/integration/docs.
Prior96/6/415 are historical baselines. Current FE02 evidence is below.

Important verified constraints/gaps: collection OPTIONS actions.POST rechecks
POST permission and is a current capability hint, unlike static Allow methods.
Task manage and Workspace metadata-edit checks are identical; lifecycle action
OPTIONS enforces Profile-manager capability. Server revalidates every mutation.
START role metadata does NOT prove the caller is the assigned User. me has a
global User ID while assignment/member reads expose only ProfileMembership IDs;
no self-membership mapping is available. Keep Start hidden, document gap; no
fabricated ID match/new backend endpoint. Member selector uses actual scoped
active Workspace MEMBER candidates identified by membership code, no invented
names/global IDs; Profile role eligibility still must be validated by server.
Task.Status also contains existing legacy CANCELLED; render read-only legacy
state, never add a cancel transition. Record this source/doc discrepancy.

Checkpoint implementation: typed work-management contracts/OPTIONS hints have
79/79 focused tests PASS, Workspace forms21/21 PASS. Task list/detail/create/edit,
assignment selector, bounded ancestor/direct-child navigation, deadline/priority,
server filters and pagination are implemented and under final verification.
Workspace create/edit/archive/restore and sanitized member roster are integrated.
Dialog busy blocks Escape/close and Pagination supports disabled while submitting.
Final mocked/contract suite201/201 PASS across8files,11.35s, native npm exit0.
API47+contracts32, primitives15, AuthProvider16, App18, Workspace21, TaskForm31,
Task pages21. Strict typecheck PASS, Biome36files PASS, production build7.01s
PASS (JS432.83kB/gzip127.33kB,CSS37.12kB/gzip10.65kB), actual exits0.
Earlier intermediate failures were fixed; they are not final acceptance evidence.

Development fresh read-only verification: exact Compose container/volume/loopback
identity, PostgreSQL16.14,35migrations,Users3,Sessions2,all checked business/token/
notification/Audit rows0. No migration or writes. Protected backend baseline is
143 source hashes in ignored .local_backups/HT-FE-P3-02/backend_baseline.json.
First real work suite run87075dd1965d423292fc7ed7bc75cc64:1/7 PASS,6 failures,
launcher/Playwright exit1, backendexit0 and owned cleanup PASS. Root cause for
hidden actions: Vite CORS middleware swallowed OPTIONS with204; actual isolated
Django metadata proved POST hints correct. Fixed frontend vite.server.cors=false
so same-origin OPTIONS reaches DRF (no Django CORS/CSRF/security edits). Also
fixed explicit filter accessible labels and ambiguous E2E unavailable heading.
Second run b69905012f6446cabfb8b0fca2864ed9:5/7 PASS; fixed disabled modal
triggers losing return focus and a depth test incorrectly POSTing a GET-only
subtasks route. Native dialogs make background triggers inert without disabling
them before opener focus is captured. Pending form controls remain disabled.
Final work run4f85817849a4403eb4c01d7f72fb6fd5:7/7 PASS56.5s, actual native
launcher/Playwright/backend exits0, owned DB/container/two-network cleanup PASS.
Real Django/PostgreSQL/Chrome, no API mocks. Workspace CRUD/lifecycle, manager
metadata role ceiling, Task metadata/assignment/subtask, filters/pagination,
cross-tenant denial, CSRF, Viewer/Editor and archived-context checks passed.
Axe WCAG2/2.1 AA0 violations/overflow/keyboard modal-return-focus/reduced motion
passed at375/768/1440 and812x375 landscape;16 screenshots retained ignored.
Foundation run72ef3c1c844e40aa8cfe2588d3ff0769:6/6 PASS34.2s with actual
launcher/Playwright/backend exits0 and owned cleanup PASS. Current Auth/CSRF/
login/logout/expiry/revoked-Workspace regressions passed, not historical FE01.
Four representative final FE02 PNGs visually inspected: desktop Task list,
mobile Task form/detail, landscape Workspace form; wrapping/contrast/layout
consistent with master. Dialog scrolling handles short landscape height.
No interactive manual browser verification or production deployment claim.
Shared integration runner now selects -Suite foundation|work-management; default
foundation, fresh owned PostgreSQL for each. Both final suites completed.
Each isolated startup ran Django system check, migration drift/full chain and
migrate --check successfully; no persistent database selected. The historical
415/415 full backend suite was not rerun because backend source is unchanged.

Final readonly development confirms the same35 migrations/Users3/Sessions2 and
all business/token/notification/Audit rows0; task0004/notification0002 remain
applied. No migration, schema, fixture, login or business write performed there.
143 protected backend/config/CI/shared-backend-harness hashes unchanged;0 owned
frontend test containers/networks remain. No dependency/lockfile upgrade.

DONE: all implemented UI, mocked/contract/browser/static/visual verification and
affected documentation. PARTIAL/BLOCKED: START and friendly/prevalidated assignee
identity require an approved backend contract; do not claim full FE02 completion.
No remaining unblocked implementation/testing work. Safe next step: Owner reviews
UI plus API gaps and approves either a bounded identity/capability API task or
explicit deferral. HT-FE-P3-03 remains a proposal, never starts automatically.

Changed source inventory (all uncommitted): frontend/src/app/App.tsx,
components/ui.tsx, pages/tenants.tsx, pages/tasks.tsx+tasks.test.tsx,
features/workspaces/WorkspaceCreate.tsx, WorkspaceActions.tsx+test,
WorkspaceMembers.tsx, useWorkContext.ts; features/tasks/TaskForms.tsx+test;
services/api/client.ts, work-management.ts+test; styles.css; vite.config.ts;
e2e/work-management.spec.ts. Integration-only helpers scripts/frontend_integration.py
and scripts/test-frontend-integration.ps1. Docs: HANDOVER,PROGRESS,ROADMAP,
REQUIREMENT_STATUS,CHANGELOG,PROJECT_CONTEXT,API_DOCUMENTATION,FRONTEND_GUIDE,
design-system/hustlytasker/MASTER.md. No AGENTS/backend/models/migrations edits.
Ignored evidence .local_backups/HT-FE-P3-02/ retains paired launcher logs/exit
JSON, backend hash baseline and16work screenshots; foundation run evidence stays
under .local_backups/HT-FE-P3-01/. Git branch/HEAD still main/e083060; no commit.

Stop at OWNER REVIEW GATE after verified scope; next proposed HT-FE-P3-03 is
not authorized. Project remains PENDING OWNER DECISION; no AI/Finance/Payroll.

---

## Historical checkpoint — 2026-10-26 — HT-FE-P3-01 IMPLEMENTATION COMPLETE / OWNER REVIEW GATE

All foundation acceptance criteria are DONE with current evidence below.
No remaining implementation blocker. Stop for Owner review; do not start
HT-FE-P3-02, Project, AI, another business UI or a persistent migration.
Branch main/HEAD3a736f0 and all pre-existing dirty work are preserved; no commit,
push, reset, production action or Owner venv/runtime replacement.

### Recovery and completed scope

On resume the single frontend already contained transport/contracts, auth state,
layout/routes/pages, design tokens/master, UI primitives and partial test/harness
work. Source was inspected and preserved rather than recreated. The existing
78 mock cases passed. Continued missing App regression coverage, Tailwind lint
configuration, actual build/browser verification and documentation. Fixed a
permission403→me200 remount/refetch loop with a quiet identity probe. Also fixed
private tab-title retention after logout/expiry, safe fatal fallback outside
router context and contextual unavailable/CSRF feedback. These are minimal
frontend fixes; no Django authentication/business rule or schema change.

Actual stack on Node20.17.0/npm10.8.2: React19.3.1,strict TypeScript6.0.3,
Vite6.4.5,ReactRouter7.18.4,Tailwind4.3.3,TanStackQuery5.104.5; Vitest4.1.12,
Playwright1.64.1/axe and Biome2.6.3. Biome replaces the initial incompatible/
deprecated ESLint toolchain without upgrading the Owner's Node. npm lock and
dependency tree verify; installation audit reported0 vulnerabilities.

### Skill, design and implementation

ui-ux-pro-max exists at .agents/skills/ui-ux-pro-max/SKILL.md and was read in
full. Its CLI actually ran in existing Python3.12 image, network none/read-only
skill mount: design-system, narrowed minimal dashboard, color/typography,
accessible authentication, React async errors and keyboard/modal UX searches.
Unsuitable generated landing/motion/native recommendations were filtered, not
persisted as approved design. Verified synthesis is documented in
documentation/design-system/hustlytasker/MASTER.md and frontend/src/styles.css.
Retained deep-teal/warm-neutral/lime, self-hosted Vietnamese PlusJakartaSans,
shared semantic tokens/spacing/radius/controls and reduced-motion behavior.

Single app: app/,features/auth/,services/api/,components/,layouts/,pages/.
Reusable Button/Input/FormField/Card/Badge/Alert/Dialog/Pagination/loading/
empty/error states; responsive sidebar/topbar and native modal navigation.
Dashboard uses actual accessible Profile count/preview, no invented metrics.
Profile/Workspace list/detail, monthly period and ACTIVE/ARCHIVED are read-only;
no dead Task/Review/AI links, creation controls or frontend permission authority.

Public /login,/403,/404 and fallback; protected /dashboard,/profiles,
/profiles/:profileId,/profiles/:profileId/workspaces and nested Workspace detail.
Root redirects through the same auth guard. Local return-to URLs are preserved;
external redirects rejected. Routes keep IDs scoped through actual backend APIs.

### Session/CSRF and privacy

Same-origin /api/ client sends credentials/no-store, typed/runtime-validated
contracts and controlled local errors. CSRF bootstrap token is memory-only;
unsafe requests attach X-CSRFToken, login/logout clear stale CSRF after Django
rotation, and no mutation is automatically replayed. Browser manages HttpOnly
session cookies; no JWT/localStorage/sessionStorage/password/token persistence.
Vite loopback proxy preserves Host; no CORS/CSRF/cookie/backend setting changed.

Initial /me resolves before private queries mount. Focus/visible-page return
and60-second visible-page polling revalidate; uncertain identity hides private
UI. Logout/expiry cancel and clear queries plus private tab titles. Generation/
abort guards prevent stale identities. Tenant403 probes /me quietly and keeps
a stable permission error if session remains valid; anonymous403 and uncertain
network states clear identity. Tenant404 remains non-enumerating. Query cache is
memory-only,staleTime0/gcTime0/no retry; backend memberships remain authoritative.
Logout failure does not pretend the server session has been invalidated.

### Current verification actually run

| Layer | Result |
|---|---|
| Mock API/contract tests |47/47 PASS|
| Mock UI primitives |15/15 PASS|
| Mock AuthProvider |16/16 PASS|
| Mock App/routes/states/privacy |18/18 PASS|
| Full mock frontend suite |96/96 PASS,4 files,8.60s|
| Biome lint |24 files PASS,exit0|
| Strict TypeScript |PASS,exit0|
| Production build |PASS,6.67s;JS388.07kB(gzip116.31kB),CSS31.44kB(gzip9.43kB)|
| Real Django/PostgreSQL/Chrome integration |6/6 PASS,40.7s|

Final real run86b46affb2724fd9be868fac2955c63d uses actual HTTP and synthetic
fixtures only in a fresh owned UUID PostgreSQL16 database. Cases cover real
CSRF failure/rotation, invalid/successful login, me/logout, cookie HttpOnly,
protected return-to, Profile/Workspace pagination/detail/tenant denial,
revoked membership and expired sessions/private UI+tab cleanup. No API mock
response is used by these tests. Native launcher0,Playwright0,Python backend0
and owned database/container/two-network cleanup all explicitly verified.

Responsive375/768/1440 and812×375 landscape: axe WCAG2/2.1A/AA rules found0
violations, no horizontal overflow, visible keyboard focus/reduced-motion and
native dialog Escape/focus return PASS.13 final screenshots retained ignored;
root opened desktop dashboard,mobile login and tablet Workspace screenshots to
review actual layout/typography/states. This is automated browser interaction
plus direct PNG visual review, NOT manual interactive browser testing or a full
accessibility certification. No authenticated E2E on persistent development.

Evidence: .local_backups/HT-FE-P3-01/integration_20261026T062010570Z.stdout.log,
paired stderr and _evidence.json; final screenshots/86b46affb2724fd9be868fac2955c63d/.
Historical attempts are retained: internal-only Docker network prevented host
publication before browser start; fixed by second owned HTTP bridge while PG
stays internal/unpublished. Another attempt had one wrong dashboard-return
test expectation; corrected to intended /profiles return. Both cleaned owned
resources; neither is claimed as a full PASS. Later6/6 run preceded the final
privacy fixes; the final run above verifies the frozen implementation.

### Backend/database safety and files

Before/after read-only development inventory: original PG16.14/hustlytasker_db,
hustlytasker_postgres,127.0.0.1:5432,docker_postgres_data;35 migrations,3 Users,
2 Sessions,0 checked Profile/Workspace/Task/Comment/Notification/Audit rows.
No persistent login, fixture, mutation, migration, email or production contact.
All143 pre-existing backend/config/Docker/CI/shared-harness hashes unchanged.
No existing models, migrations, auth/RBAC/Invitation/Task/Review events edited.
Full backend415/415 is the historical HT-DB-P1-11 baseline, not rerun or claimed
as current frontend proof; unchanged backend plus real isolated checks suffice
for this scope. Integration runs current Django check/model drift/full chain
only against disposable PostgreSQL. New test helpers are separate additions.

Only original development PG container/volume remains; test DB/containers/both
networks are cleaned, Vite/test backend listeners5173/8001 gone. Integration PG
was unpublished tmpfs on an internal UUID network; only backend additionally
used an owned HTTP bridge for127.0.0.1:8001. No development network/credentials
were passed. Private environment/test artifacts remain Git-ignored; frontend
.env.example is explicitly trackable. Final diff/source/ignore checks PASS.

Task files: frontend/ (30 source/config/assets/test/lock/example files), new
scripts/frontend_integration.py and test-frontend-integration.ps1; .gitignore
and README; HANDOVER/PROGRESS/ROADMAP/REQUIREMENT_STATUS/CHANGELOG/PROJECT_CONTEXT;
new FRONTEND_GUIDE/design master, TECH_STACK_DECISION and minimal API/decision
consumer notes. AGENTS/ui-ux skill and all older dirty business files preserved.

### Exact continuation and limits

Start Owner's configured backend on127.0.0.1:8000, then from frontend/ run
npm ci and npm run dev; open127.0.0.1:5173. Full setup/proxy/environment,
commands/architecture/contracts and isolated runner are in FRONTEND_GUIDE.md.
Do not reset credentials/venv, regenerate the app/master or run DB rollout again.

No remaining implementation TODO/blocker for HT-FE-P3-01. Production deployment,
remote CI, real email and manual interactive testing are unverified/out of scope.
Task/Review/write/member/invitation/account-recovery UIs remain future scope;
their existing backend APIs are unchanged. Project remains PENDING OWNER
DECISION; AI has documented future integration points only, no active UI/API.
Safe continuation: Owner review only. Proposed next task HT-FE-P3-02 Workspace
& Task Management UI requires separate approval; do not start automatically.

---

## Historical checkpoint — 2026-10-26 — HT-DB-P1-11 COMPLETE / OWNER REVIEW GATE

All rollout acceptance criteria are DONE. No implementation blocker or remaining
rollout step. Stop for Owner review; Project remains PENDING OWNER DECISION.
Do not reapply migrations, restore development or start another task. Branch
main/HEAD3a736f0 and all39 pre-existing dirty files are preserved; no commit/push.

### Recovery, target and inventory

Before interruption, source/migration review and ignored operational scaffolding
existed, without backup/apply/test evidence for this rollout. Resume verified
the actual database read-only: both target migrations and new columns absent,
case B,33 migration records. Existing stopped container was restarted only after
identity checks, without recreation. Target: PostgreSQL16.14/hustlytasker_db,
original hustlytasker_postgres,127.0.0.1:5432,docker_postgres_data,docker_default,
matching repository Compose service/configuration. No production action.

Pre/post inventory:3 Users,2 Sessions;0 Profiles/ProfileMemberships/Workspaces/
WorkspaceMembers/Invitations/security tokens/Tasks/Assignments/Deliverables/
Reviews/Comments/Notifications/Clients/ShareLinks/Invoices/Payments/AuditLogs.
Metadata23 content types,92 permissions,7 Admin logs unchanged. Exact legacy
values in every public table compared privately in memory before/after each
apply and against restored rehearsal after all regression. Only the two new
migration records and approved nullable columns differ; no demo or guessed mapping.

### Retained backup and staged migration

Fresh Git-ignored custom archive:
`.local_backups/HT-DB-P1-11/hustlytasker_dev_pre_comments_notifications_20261025T175311Z.dump`,
104,092 bytes, SHA256
`72ae8d37df5e35ed535ddd29549bf681ee3de1bfebb703a3433f9d320a5fe4d0`.
Host/container size/hash match;240-line pg_restore TOC/full archive read PASS.
Owned isolated restore DB
`htdb_p111_restore_0f68d3b0f5ea43a78fff281937f41351` was checked by owner/comment
marker and exact restored data, then both migrations rehearsed separately PASS.
Development remained untouched during rehearsal; no persistent restore occurred.

| Exact target | Development applied at UTC | Records / public FKs |
|---|---|---|
| tasks.0004_task_comments | 2026-10-25T17:54:39.849628+00:00 | 33→34 /40 |
| notifications.0002_notification_context | 2026-10-25T17:55:08.420459+00:00 | 34→35 /44 |

Both timestamps are October26 locally. Graph/individual target plans contained
only these migrations, in this order. Each applied once through standard Django;
stage1 integrity passed before stage2. Two transactions, not one atomic rollout.
No migration file changed, new migration, fake, rollback or manual schema fix.

### Schema, APIs and business/security invariants

Comment6→8 columns: nullable edited_at/deleted_at without permanent defaults;
comment_edit_after_create/comment_delete_after_create CHECKs and
comment_task_created_id_idx valid. Existing Task/User FK targets unchanged.
Notification7→12 columns: nullable event_type(varchar32),Profile/Workspace/Task/
AuditLog-event FKs; notif_context_complete/notif_valid_event_type CHECKs,
notif_user_read_created_idx and partial UNIQUE(user_id,event_id) WHERE event_id
IS NOT NULL valid/ready. All44 public FKs validated/orphan-free. New legacy
columns remain NULL; no invalid constraints/indexes or unexpected defaults.
SQL FKs are deferred NO ACTION; PROTECT is ORM policy. The4000 text limit and
cross-row tenant/event proof are application validation, not added DB guarantees.

No API contract, authentication, role or Task/Subtask/Review policy changed.
Comment author-only edit/author-or-manager soft delete/tombstone and current
tenant capability rules remain. Personal notification feed/count/read repeat
current target access. Assignment, submission, approval, requested changes and
comment events use existing recipient rules, event/recipient dedup and atomic
business+AuditLog+notification persistence; insertion failure rolls back all.
Current isolated tests cover tenant/IDOR/revocation/archive/staff/CSRF boundaries,
all events, rollback, moderation, replay and concurrent mutations. No async/email.

### Current verification actually run after rollout

| PostgreSQL test group | Result | Django duration |
|---|---|---|
| Comment + migrations |40/40 PASS|13.140s|
| Notification + migrations |34/34 PASS|8.431s|
| Task/Comment/hierarchy/Deliverable/Review |128/128 PASS|41.694s|
| Auth/security/Invitation/Workspace/RBAC/API |253/253 PASS|224.745s|
| Full suite |415/415 PASS|259.978s|

All five runs through unchanged scripts/test-backend.ps1: actual native launcher
exit0 AND Python runner Docker die-event exit0, Django OK, pip check/system/
model-drift/graph/history/full-chain and owned cleanup PASS. The prior exit-code
capture limitation is resolved for these runs by ignored native Process-handle
and run-labelled die-event evidence; no shared harness edit. Historical415/415
below is not reused. Paired logs and *_exit_evidence.json remain in task directory.

DEVELOPMENT SMOKE PASSED:67 anonymous Django-handler requests inside READ ONLY
transaction +28 serializer-only checks, including health200, CSRF bootstrap200,
unsafe auth CSRF rejection and protected tenant/Task/Comment/Notification403.
New-column ORM selects/context joins PASS, no HTTP500/email/login/fixture/row
change. AUTHENTICATED SUCCESS FLOWS NOT TESTED ON PERSISTENT DEVELOPMENT;
authenticated success/mutations/method contracts are covered only on isolated PG.
Final post checks/showmigrations[X]/migrate-check/empty plan/exact legacy compare
PASS after full regression, before rehearsal cleanup. See final_post.log.

Owned rehearsal DB and exact /tmp dump copy removed after owner/UUID checks;
host backup retained and digest/size reverified. Only hustlytasker_db/postgres
remain on original cluster; no owned test containers/networks remain. Original
development container is running with original named volume. See cleanup.log.

### Files, limits and exact continuation

This task changed documentation only: HANDOVER,PROGRESS,PROJECT_ROADMAP,
REQUIREMENT_STATUS,CHANGELOG,DATABASE_SCHEMA,API_DOCUMENTATION,PROJECT_CONTEXT;
minimal rollout reconciliation in DECISION_LOG/RBAC_DESIGN. All143 protected
backend/config/Docker/CI/test-harness asset hashes match the initial baseline.
Existing uncommitted implementation remains intact. Operational helpers, backup,
inventory/schema logs and test evidence are Git-ignored under the task directory.

REAL EMAIL DELIVERY NOT VERIFIED; remote GitHub Actions NOT VERIFIED. These
are existing limits outside this database rollout. Windows venv unchanged.
AI Feedback Analyzer remains data readiness only; no new provider/AI schema or
frontend. No production, notification policy or workflow change was made.

Safe continuation is Owner review only. Do not rerun apply/rehearsal/cleanup or
the post helper (its comparison DB has been deliberately cleaned). If a future
session must establish state, use read-only history/schema/inventory checks.
Proposed next gate: Owner selects Project scope A/optional Profile/Client-scoped
B′ from PROJECT_ARCHITECTURE_REVIEW.md before a separately scoped implementation;
do not reopen the11 accepted architecture groups or infer Project approval.

---

## Historical checkpoint — 2026-10-25 — HT-COM-P2-06 OWNER REVIEW GATE

**IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL.**
Project remains **PENDING OWNER DECISION**. No next task, persistent migration,
commit, push, reset or production action is authorized. Branch `main`, HEAD
`3a736f0`; preserve all pre-existing dirty hierarchy/source/documentation work.

### Recovery and completed implementation

On resume, Comment CRUD/model/tasks.0004 and Notification model/access/content/
partial services plus Task event hooks already existed, without new test proof.
Those were preserved and completed. Missing Notification API/migration and both
test suites were added; no second Comment/Notification system or duplicate
migration was created. All implementation items are now DONE and verified;
only the separate development rollout and Owner review are pending, no blocker.

Comments reuse TaskComment for roots/subtasks. New/edited text is trimmed,
nonblank valid Unicode without NUL, max 4000 characters. Current Profile
Owner/Admin, Workspace Admin and Editor create; authors with current capability
edit own text; author or manager soft-deletes, never manager rewrite of others.
Viewer is read-only; archive blocks writes; revoked/inactive users lose access.
Author/Task cannot be reassigned through API. Deleted body is retained internally
but API returns tombstone/null content. Audit contains IDs/action facts only.
Repeated delete is idempotent, edits of deleted rows conflict. Supported locks
are Profile→Workspace→Task→Comment. Last-writer-wins edit serialization is not
optimistic versioning/full-text revision history. Task/parent/review state is
unchanged by discussion.

Notifications reuse is_read and add nullable typed Profile/Workspace/Task/
AuditLog-event context. Legacy unscoped records remain unchanged and hidden;
no tenant/event mapping is guessed. Supported events and recipients:

- Task assigned/reassigned → the current eligible Editor assignee.
- Deliverable submitted → current Profile Owner/Admin and Workspace Admin.
- Review approved/request changes → persisted Deliverable uploader if eligible.
- Comment created → Task creator and active assignee if eligible.

Actor, duplicate, inactive and non-readable recipients are excluded. Producer
uses persisted event/entity/Task/Review/uploader proofs and tenant locks. Safe
constant display messages contain no body/title/User PII. `(event,user)` dedup
preserves read state on replay; it is not general HTTP POST idempotency.
Persistence is atomic with business mutation/AuditLog: notification failure
rolls back the whole operation. No email/push/signal/on_commit/worker/outbox.
Own feed/count/read repeat current canonical target and membership predicates;
notification IDs never grant access. Revoked rows are hidden, not deleted, and
may reappear on restored Task access with read state preserved. Mark-read
locks Profile→Workspace→Notification and works on still-readable archives.

### APIs and schema

Base Task path: `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/`.
`comments/` supports GET/POST; `comments/{comment_id}/` GET/PATCH/DELETE.
Personal `/api/v1/notifications/` supports paginated GET with is_read filter;
`notifications/unread-count/` GET; `notifications/{notification_id}/read/` POST.
All use SessionAuthentication, CSRF on unsafe methods, active identity,
strict input, bounded pagination/stable ordering and non-cacheable responses.
No new AllowAny, staff bypass, Client principal or authentication mechanism.

New `tasks.0004_task_comments`: nullable edited_at/deleted_at, Task FK PROTECT,
new-write MaxLengthValidator, timestamp CHECKs and history index. Legacy
oversized text/timestamps remain intact; moderation preserves unchanged text.
New `notifications.0002_notification_context`: nullable context/type/event FKs,
completeness/type checks, unique event/recipient and user/read/created index.
Both migrations were verified only on isolated PostgreSQL, including empty
and related legacy cases. No applied migration or User model was edited.

### Current verification actually run

- Comment/API/model/service/concurrency + migration: **40/40 PASS**, 6.919s.
- Notification/event/API/concurrency + migration: **34/34 PASS**, 5.401s.
- Full Task/Comment/hierarchy/Deliverable/Review: **128/128 PASS**, 22.637s.
- Auth/security/Invitation/Workspace/RBAC/API: **253/253 PASS**, 165.756s.
- Full PostgreSQL: **415/415 PASS**, 191.226s (341 baseline +74 new tests).

All five successful runs have actual native launcher exit 0 and Python runner
container die-event exit 0, Django OK and owned DB/container/network cleanup.
Each runs pip check, system checks, model drift, graph/history and full migration
chain through the unchanged shared harness. Paired logs and *_exit_evidence.json
are retained ignored under `.local_backups/HT-COM-P2-06/`. First Notification
attempt failed (3 failures/2 errors, both exits 1): an intermediate lock-fetch
guard inverted the Workspace existence check. The corrected frozen source
passed rerun/full regression; original attempt1_* evidence is retained. No
permission was relaxed. Independent final source review found no blocker.

Shared StrictInputSerializer has one minimal malformed Unicode/NUL field-name
guard to avoid response-rendering 500; normal unknown-field errors remain
unchanged. Of 84 protected assets captured at resume, 83 match SHA-256 exactly;
that validator is the sole expected exception. Auth/config/harness and applied
migrations are preserved. Final diff/UTF-8 checks pass (line-ending notices only).

### Persistent development and AI limits

Final READ ONLY inventory: original PostgreSQL16.14/hustlytasker_db,
hustlytasker_postgres, loopback127.0.0.1:5432, docker_postgres_data unchanged;
33 migrations, 3 Users/2 Sessions and zero checked Comment/Notification/business/
security-token/Audit rows. tasks.0003 and notifications.0001 remain latest
applied in those apps; **tasks.0004/notifications.0002 and their new columns
are absent**. No fixture/write/migration on development, no production contact.
Only original development PG remains; no test database/container/network or
test process is active. Source needs the separate new-schema rollout before
the new communication flows are exercised on persistent development.

AI Feedback Analyzer is data readiness only: authorized Task/Workspace,
Comment and Review/Deliverable revision projections, honoring soft-delete and
current access. Notification text is navigation/event metadata, not feedback.
Immutable comment edit snapshots/citations, aggregate retrieval/provenance and
human acceptance semantics remain future design. No LLM/provider/key, AI table,
autonomous Task creation or frontend was added.

### Dirty files and exact safe continuation

Task changes: TaskComment section in models.py, notification hooks in services.py,
comment routes in urls.py; comment_{services,serializers,views}.py;
test_comments.py/test_comment_migrations.py; migrations/0004_task_comments.py.
Notification app: models/views/access/content/services/serializers/urls,
test_notifications.py/test_notification_migrations.py and migration0002.
Shared: api/urls.py and workspace/serializers.py. Updated docs: HANDOVER,
PROGRESS, PROJECT_ROADMAP, REQUIREMENT_STATUS, CHANGELOG, DATABASE_SCHEMA,
API_DOCUMENTATION, PROJECT_CONTEXT, RBAC_DESIGN and DECISION_LOG. Older dirty
hierarchy files/PROJECT_ARCHITECTURE_REVIEW.md remain preserved, not newly
implemented here. Operational evidence/capture helpers are Git-ignored.

Stop at OWNER REVIEW GATE. Proposed next task: a separately authorized
controlled development rollout of tasks.0004 then notifications.0002, with
fresh inventory/backup/rehearsal and smoke checks. Do not apply automatically,
rewrite/recreate migrations, commit/push, implement Project/AI or another domain.
Future full command: `.\scripts\test-backend.ps1`; targeted examples use
`-TestLabel apps.tasks.test_comments,apps.tasks.test_comment_migrations` or
`-TestLabel apps.notifications`. Historical notes below do not override this gate.

---

## Historical checkpoint — 2026-10-25 — HT-DB-P1-10 COMPLETE / OWNER REVIEW GATE

Owner conditionally authorized exactly tasks.0003 development rollout after
preflight, fresh backup and isolated restore rehearsal. No production, feature
change, demo data, fake migration, rollback/restore-over-development, commit or
push is authorized. Preserve all 21 dirty feature/doc files from HT-TASK-P2-05.
Branch `main`, HEAD `3a736f0`. All pre-existing source changes are preserved;
129 backend/config/Docker/harness assets match their pre-rollout SHA-256.

Read-only identity verified: repository Compose postgres service/container
hustlytasker_postgres, PostgreSQL 16.14, database hustlytasker_db, loopback
127.0.0.1:5432, original docker_postgres_data volume. Preflight development had
32 migration records; tasks.0001/0002 applied, tasks.0003 absent and no parent_id.
Existing Task CHECK/FK/index definitions are valid/ready. Only development and
standard maintenance DB exist. CaseB (unapplied), no schema/history mismatch.

Independent source review: nullable parent/selfCHECK/lookup index only, no data
backfill/destructive operation/new model. Expected data delta is one migration
record only. PROTECT is Django ORM policy; SQL parent FK was verified as
NO ACTION, DEFERRABLE INITIALLY DEFERRED. Graph/cycle/depth/cross-tenant
rules remain service/model checks, not cross-row database guarantees.

Preflight inventory: 3 Users/2 Sessions, 0 checked business/security-token/Audit
rows; metadata 23 content types/92 permissions/7 admin logs. All 39 public FKs have
zero orphans; constraints/indexes validated. Django system/drift/graph/history
PASS, plan is exactly tasks.0003 (three additive operations).

Fresh retained Git-ignored custom backup:
`.local_backups/HT-DB-P1-10/hustlytasker_dev_pre_tasks_0003_20261025T034208Z.dump`,
102,780 bytes, SHA256
`5225dc8a531df81c30d932bf400c896e707f9562d627e0336c51e1ee50ff4c83`.
Host/container size/hash match, 237-line TOC and full archive read PASS.
Restored into owned isolated DB
`htdb_p110_restore_14fc78f514ef4d8f91b6c165e14786db` (same cluster, separate DB,
UUID+owner/comment verified). Exact legacy rows matched source in memory;
rehearsed exact tasks.0003 successfully, 33 migrations/11 Task columns/40 valid
FKs, parent CHECK/index valid, all legacy rows preserved. Development remained
unchanged during rehearsal. No production contact or secret emitted.

Applied exactly tasks.0003 at 2026-10-25 03:43:19.588793 UTC through standard
Django after all safety gates PASS. Apply/post inventory PASS: 33 migration records, 11 Task
columns, nullable UUID parent_id, validated self-parent CHECK/FK, valid/ready
lookup index, 40 FKs without orphans. Every legacy row compared exactly equal
before/after in process memory; metadata remains 23/92/7, 3 Users/2 Sessions,
no business/token/Audit rows. showmigrations marks 0003[X], migrate --check and
empty pending plan PASS. No rollback/restore/fake or demo data used.

Read-only development smoke PASS: 51 handler requests with CSRF enforcement,
16 serializer-only checks and Task.parent ORM column select. No 500/PII/email/
login/fixture/mutation; exact rows before/after match. Authenticated success,
hierarchy mutations and validation HTTP flows are NOT TESTED ON PERSISTENT
DEVELOPMENT; use isolated test fixtures instead.

Current isolated Task suite 88/88 PASS in 11.780s (hierarchy/API/workflow/migrations,
including two concurrency races). Native shared-launcher exit 0 and Python runner
container die-event exit 0 both verified, Django OK and owned DB cleanup PASS.
No shared harness/source edit needed. Evidence/logs are ignored under this
task folder: tasks_postgresql_tests{,.stderr}.log, tasks_exit_evidence.json.

Current Auth/security/Invitation/Workspace/API regression 253/253 PASS in
162.615s; full PostgreSQL 341/341 PASS in 170.987s. Both have launcher exit 0
and Python runner exit 0, Django OK and owned cleanup PASS. All current runs
include pip check, Django checks, model drift, migration graph/history and
complete migration-chain checks. The Python runner invokes Django in-process;
its Docker die event is process exit evidence, distinct from the native
launcher exit. Missing historical child codes were not treated as zero.
Shared harness files were not changed; only ignored task-specific capture
orchestration was used. Paired stdout/stderr logs and *_exit_evidence.json
for tasks/regression/full are retained under .local_backups/HT-DB-P1-10/.

Final checks after tests: migrate --check, empty plan, model drift, system
check and exact legacy-row comparison with migrated rehearsal all PASS.
Backup original size/hash reverified. The owned rehearsal DB was then dropped
only after checking its UUID/owner/comment; only the task's temporary container
dump copy was removed. Host backup is retained. No test/rehearsal DB, labelled
test container/network or running test process remains; only original
development PostgreSQL/volume remain. Development is 33 migrations, 3 Users,
2 Sessions and zero checked business/token/Audit rows; no demo data exists.

This rollout changes documentation only: HANDOVER, PROGRESS, PROJECT_ROADMAP,
REQUIREMENT_STATUS, CHANGELOG, DATABASE_SCHEMA, API_DOCUMENTATION, PROJECT_CONTEXT;
DECISION_LOG/RBAC_DESIGN have minimal operational-state reconciliation only.
PROJECT_ARCHITECTURE_REVIEW.md and all business/models/migration/harness assets
remain unchanged from task start. The 21 dirty files listed in the historical
checkpoint remain pre-existing feature work, not newly implemented here.
Operational scripts/logs/metadata are ignored; credentials were passed only
in temporary process environment; Owner venv and development Compose untouched.

No blocker remains. Stop at OWNER REVIEW GATE. Do not reapply tasks.0003,
restore development, recreate rehearsal just to repeat evidence, or rerun
case-B operations scripts after cleanup (their old preconditions no longer
hold). The retained custom archive can be inspected with pg_restore --list;
any recovery into persistent development needs separate explicit approval.
Next proposed step: Owner reviews rollout and selects Project A/B′ scope or
another roadmap task before separately authorizing implementation. Project
remains PENDING OWNER DECISION; no Project/Notification/AI/frontend began.

---

## Historical checkpoint — 2026-10-25 — HT-TASK-P2-05 OWNER REVIEW GATE


**IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL.**
**PROJECT ARCHITECTURE REVIEW — PENDING OWNER DECISION.**

Owner authorized Task hierarchy/deadline/priority and Project analysis only.
The pre-existing HANDOVER/PROGRESS revalidation edits were preserved. Branch
`main`, HEAD `3a736f0`; all current feature/documentation work is uncommitted.
No next task, persistent migration, commit, push or reset is authorized here.

### Implemented

- Reused Task and its existing priority/deadline. Added nullable protected
  self-FK `parent` (`subtasks` reverse relation). Root depth0, maximum depth3
  (four levels). Validation rejects self-parent, cycles, cross-Workspace
  parents and moved subtrees exceeding the cap. Same Workspace implies same
  Profile. Services resolve parents within tenant scope and serialize changes
  using the existing Profile→Workspace→membership→Task lock sequence.
- Each node retains independent assignment/status/Deliverable/Review and
  deadline/priority. A parent may complete with unfinished children; approval
  never approves children. Child changes/completion never change parent
  status. Existing reviewer, self-review, revision and audit checks remain.
- Reused nullable aware deadline and LOW/MEDIUM/HIGH/URGENT priority (default
  MEDIUM). API normalizes to UTC, preserves existing UTC interpretation of
  naive ISO input, and rejects invalid/overflowing values. Direct service
  datetimes must be aware. No parent deadline inequality, inheritance,
  overdue status mutation, scheduler or notification is introduced.
- Existing scoped Task POST/PATCH accept `parent_id`, deadline and priority;
  only existing managers may write. New GET/HEAD/OPTIONS
  `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/subtasks/`
  returns paginated direct children. Existing flat list remains default;
  root/parent/status/priority/deadline filters and priority/deadline/creation
  ordering are additive. Old fields/pagination/format behavior remain intact;
  assignment membership lookup no longer adds a query per listed child.
- No Project model/API/migration or estimated-duration field was added.
  `PROJECT_ARCHITECTURE_REVIEW.md` compares A/B and proposes A now, optional
  Profile/Client-scoped B′ later. Literal Workspace-owned B conflicts with
  accepted cross-month Project ownership and needs explicit Owner amendment.
  No separately named new SRS/HLD was found to supersede that decision.

### Migration and verification actually run

- New `tasks.0003_task_hierarchy` depends on tasks.0002 and adds only nullable
  parent, DB self-parent CHECK and Workspace/parent/created lookup index.
  Existing Tasks become roots without guessed mapping/backfill. Applied
  migration files, other models and authentication mechanism are unchanged.
- All runs used `scripts/test-backend.ps1` with disposable PostgreSQL16/Python
  3.12. Dependency (`pip check`), Django, model drift (`makemigrations --check
  --dry-run`), graph/history and full migration-chain checks PASS.
- Hierarchy migration **2/2 PASS**, 1.465s: empty DB and representative related
  legacy Task/Assignment/Deliverable/Review, preserving IDs/metadata/deadlines.
- New planning + existing Task API **42/42 PASS**, 4.990s.
- Hierarchy + existing Task/Review services **43/43 PASS**, 4.770s, including
  two real PostgreSQL concurrent cycle/depth races and audit rollback.
- Workspace/RBAC regression **122/122 PASS**, 60.495s.
- Full PostgreSQL **341/341 PASS**, 174.058s: existing 286 +55 new tests,
  including Auth/security/Invitation/Workspace/Task/Review/migration regression.
  Final independent source review found no outstanding issue.
- Full stdout/stderr logs are retained under ignored
  `.local_backups/HT-TASK-P2-05/full_postgresql_tests{,.stderr}.log`. Django
  reports `OK` and owned-resource removal is verified. The outer PowerShell
  logging wrapper did not retain the child exit code; `.exit` explicitly
  records that limitation rather than inventing one. An earlier log-pipeline
  invocation stopped before tests; no business test failed/code fix was needed.
- Final `git diff --check` passes (line-ending notices only). No test process
  remains active and no labelled test container/network/DB remains.

### Persistent development remains unchanged

Read-only post-test inventory confirms the repository Compose PostgreSQL16.14,
loopback `127.0.0.1:5432`, original `docker_postgres_data` volume, 32 migrations,
3 Users/2 Sessions, zero verified Users/security tokens/checked business and
AuditLog rows. tasks.0002, reviews.0002, workspace.0004 and accounts.0002 remain
applied. **tasks.0003 is NOT APPLIED; parent_id column is absent**. No development
fixture, migration or data write occurred; production was untouched. Do not
run the new source against that old Task schema before its rollout is approved.

### Dirty files and exact continuation

Code: tasks/{models,services,serializers,views,urls,test_api}.py; new
tasks/migrations/0003_task_hierarchy.py, test_hierarchy.py,
test_hierarchy_migrations.py and test_planning_api.py. Docs: HANDOVER, PROGRESS,
PROJECT_ROADMAP, REQUIREMENT_STATUS, CHANGELOG, DATABASE_SCHEMA,
API_DOCUMENTATION, RBAC_DESIGN, DECISION_LOG, PROJECT_CONTEXT and new
PROJECT_ARCHITECTURE_REVIEW.md. Preserve all of them.

No implementation blocker remains. Cross-row graph invariants require the
validated service/model-clean boundary; bulk/raw/unvalidated ORM writes remain
outside it, while DB enforces FK/self-parent. Existing real-email/distributed-
throttling limits and remote-CI-not-verified status are unchanged.

Stop for Owner review of the Task behavior and Project proposal. Proposed next
operational task: separately authorized controlled development rollout of
tasks.0003, with fresh inventory, verified backup/rehearsal and smoke checks.
Do not apply it or implement Project/AI/another module automatically. Future
full command is `.\scripts\test-backend.ps1`; targeted Task command is
`.\scripts\test-backend.ps1 -TestLabel apps.tasks`.

---

## Historical checkpoint — 2026-10-25 — HT-TEST-P1-01 COMPLETE / OWNER REVIEW GATE

**LOCAL TEST HARNESS VERIFIED. CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED.**

Current task: **HT-TEST-P1-01 — PostgreSQL Test Harness Standardization & CI Baseline**.
Owner authorized test tooling/CI only. Preserve all pre-existing uncommitted
Authentication/Invitation/Workspace code. Do not modify business rules/models/
migrations or migrate persistent development.

### Revalidation — 2026-10-25

- The repeated task request was reconciled with actual source, tracked test
  assets, documentation and Git. Branch `main`, HEAD `3a736f0`; the worktree
  was clean before this documentation refresh. The harness/CI implementation
  is already tracked; no unfinished implementation or new local blocker was
  found. No code, model, migration or workflow was rewritten.
- Read-only Docker inspection confirms the original repository Compose
  PostgreSQL service, loopback port and `docker_postgres_data` volume. A
  PostgreSQL `READ ONLY` transaction confirms version 16.14, 32 migrations,
  `accounts.0002` and `workspace.0004` applied, 3 Users, 2 Sessions, zero
  security tokens and zero checked business/AuditLog rows. Only the
  development and standard maintenance databases exist; no labelled test
  containers/networks remain. No migration or data write was performed.
- PowerShell launcher syntax, test Compose `config --quiet`, and
  `git diff --check` pass in this revalidation. The 14/14, 10/10 and 286/286
  test results below belong to the completed 2026-10-24 implementation run;
  they were not rerun or relabelled as a new test run. No implementation
  change required a repeat of the full suite.
- This continuation changes only `documentation/HANDOVER.md` and
  `documentation/PROGRESS.md`. Remote CI remains **NOT VERIFIED**; no commit,
  push, workflow dispatch or next-task implementation occurred. The exact
  next step remains Owner review, then explicit authorization for a new task.

### Implemented and verified

- Dedicated `backend/config/test_environment.py` and `test_settings.py` read
  only explicit test endpoints/run identity, isolate DB/mail/security flags,
  and retain application/session/CSRF/hash/validator behavior.
- `scripts/test_backend.py` runs dependency/system/model-drift/graph checks,
  creates a unique owned PostgreSQL test DB, builds it from the migration chain,
  runs serial full/targeted tests, and cleans only that DB after checking its
  cluster/role/run marker. Existing databases cause refusal, not autoclobber.
- `scripts/test_test_backend.py` contains meaningful safety guard unit tests.
- Local `scripts/test-backend.ps1` plus `docker/compose.test.yml`,
  `Dockerfile.test` and Dockerfile-specific ignore create labelled disposable
  PostgreSQL 16/Python 3.12 resources, no published PG port or persistent data
  volume. Source is read-only; the build context excludes private data.
  A printed UUID supports verified cleanup after a hard interruption.
- `.github/workflows/backend-ci.yml` uses Python 3.12 and a fresh PG16 service,
  runs harness safety tests and the same core command, PR/push-main, no deploy
  or production secrets. **CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED**.
- Read-only development baseline reconfirmed: PostgreSQL 16.14, 32 migrations,
  `accounts.0001`/`0002` applied, 3 Users, 2 Sessions, zero token rows.

### Exact continuation

1. Stop at Owner Review Gate. No task work is outstanding and no command/test
   process remains active. Do not repeat completed rollout/migration work.
2. Local full suite: `.\scripts\test-backend.ps1`; targeted example:
   `.\scripts\test-backend.ps1 -TestLabel apps.accounts.tests,api.tests`.
   Requires Docker Engine/Desktop with Compose v2 and PowerShell 5.1+ (or
   PowerShell 7). It needs no local Python/venv/DB credentials. Build dependency
   image is cached, not production infrastructure.
3. If a future run is forcibly killed, use
   `.\scripts\test-backend.ps1 -CleanupRunId <printed-32-hex-ID>` from this
   repository. Labels/repository/image/mount identities must match or cleanup
   fails closed. No broad prune, development Compose, volume deletion, or
   prefix-based database cleanup is part of the harness.
4. GitHub workflow is ready for the Owner's normal commit/PR process. No push,
   remote workflow run, deploy or remote success claim was made in this task.
5. Next proposed task is **HT-PROJ-P2-05 — Project, Subtask, Deadline & Priority**,
   only after Owner review and task authorization; do not start automatically.

### Verification actually run

- Harness safety unit tests: **14/14 PASS** (0.513s), including settings isolation,
  unsafe endpoint/CLI refusal, existing-DB refusal, marker/cluster/owner cleanup
  guards, and failure exit propagation. No network was available to that unit
  test container.
- Targeted `api.tests`: **10/10 PASS** (0.044s) through the actual PowerShell
  command, with dependency/system/model-drift/graph/full migration-chain checks
  and automatic DB/container/network cleanup. Initial discovery exposed the
  SimpleTestCase-only DB-skip issue; the harness now forces the default test DB
  so even that target verifies the chain. No business source was changed.
- Intentional nonexistent-test failure returned exit 1, with its error visible
  and all owned resources cleaned. It is a negative harness test, not a business
  regression failure.
- Manual hard-interruption recovery (`-CleanupRunId`) removed two correctly
  labelled fixture containers and their network. A wrong-repository-label
  fixture was correctly refused and left intact, then removed separately by
  its captured test-fixture ID.
- PowerShell 5.1 parser, Compose configuration, and actionlint workflow checks
  PASS. Actionlint caught a numeric port-map key; the workflow now uses the
  string key `ports['5432']`. No GitHub run was performed.
- Full PostgreSQL suite: **286/286 PASS** in **166.382s**, local launcher exit 0.
  Dependency/system/model-drift/graph/history/full-chain checks all passed.
  The same full migration chain is checked even for DB-independent slices.
- Development safety after all runs: aggregate User/Session contents compared
  before/after in session memory match; no sensitive row values were emitted.
  Development remains 32 migrations, 3 Users, 2 Sessions, zero token/AuditLog
  rows, and accounts.0002 still applied exactly as before. No persistent
  development migration was run.
- Final inspection found zero labelled test containers/networks and no test
  databases on development. Only the original development PostgreSQL container
  remains. The reusable test dependency image/cache is intentionally retained.
- `git diff --check` PASS, with only existing LF/CRLF notices.

At the 2026-10-24 implementation checkpoint, the added files above were dirty
work and the original dirty business source was preserved. They are tracked
in the clean baseline observed on 2026-10-25; only the two checkpoint documents
listed above are changed by this continuation. The implementation updated
README, HANDOVER, PROGRESS, PROJECT_ROADMAP,
REQUIREMENT_STATUS, CHANGELOG and PROJECT_CONTEXT. No business source/model/
migration, runtime requirements, Owner venv, development Compose/volume, or
authentication mechanism changed. No commit/push/reset occurred.

No local implementation blocker remains. Remote GitHub execution is not
verified. Abrupt host/daemon termination cannot run a Python/PowerShell finally
block; the explicit ownership-checked cleanup path is provided and tested.
Real-provider email, distributed throttling and reset timing limitations from
the previous task remain unchanged. All older checkpoints below are historical.

---

## Historical checkpoint — 2026-10-24 — HT-DB-P1-09 COMPLETE / OWNER REVIEW GATE

Status: **CONTROLLED ACCOUNT-SECURITY DEVELOPMENT ROLLOUT VERIFIED**.

Current task: **HT-DB-P1-09 — Controlled Account Security Development Migration & Verification**.
The Owner conditionally authorized the exact `accounts.0002` development
rollout after preflight, fresh backup, and rehearsal. No other persistent
environment is authorized. Preserve all pre-existing dirty source/docs.

### Verified before development apply

- Target: repository Compose service `postgres`, container
  `hustlytasker_postgres`, PostgreSQL 16.14, database `hustlytasker_db`,
  `127.0.0.1:5432`, named volume `docker_postgres_data`, network
  `docker_default`. Container labels point to this repository's Compose file.
- Development: 31 migrations, accounts only `0001`, workspace `0001`-`0004`;
  3 active Users, 2 Sessions, 7 Admin log rows, 22 content types, 88 permissions,
  zero checked business/AuditLog rows. No verification columns/token table.
  Email null/blank/invalid/normalized-duplicate counts are all zero. All 37
  existing foreign keys have no orphans; constraints and indexes are valid.
  No competing connections or relevant locks were found.
- Global `migrate --plan` lists only
  `accounts.0002_accountsecuritytoken_user_email_verification`. Static/SQL
  review confirms additive transactional schema, no backfill/destructive action.
- Fresh Git-ignored backup:
  `.local_backups/HT-DB-P1-09/hustlytasker_dev_pre_accounts_0002_20261024T062543Z.dump`,
  93,598 bytes, SHA-256
  `195d7406015be1ce4d40f1b0f0f37094282abe7b82b7dd9b9c4b2c070827af49`.
  Host/container size and digest match; TOC has 223 lines; full archive read
  passed. This archive contains private data and must remain ignored/local.
- Restored into isolated `htdb_p109_restore_20261024_062543`; all 26 baseline
  tables compare exactly to development in memory, without logging private
  row contents. Applied the exact accounts.0002 there successfully: 32 migration
  records, 17 token columns, nine validated token CHECKs, two validated token
  FKs, nine valid/ready token indexes, nullable verification columns, no token
  rows or verified Users. All legacy rows still match. Rehearsal system check,
  migration drift, and `migrate --check` passed. Expected Django metadata delta
  is one content type and four permissions for the new model.
- Temporary `htp_p109_runner` (Python 3.12, source bind read-only) used pinned
  requirements and the existing DB credential. Its validation-only Django key
  does not replace local settings or re-sign Sessions. Owner venv untouched.

### Exact safe continuation

1. Stop at **OWNER REVIEW GATE**. All rollout acceptance criteria are met;
   no implementation or rollout work remains for this task. Do not reapply
   accounts.0002, create another migration/backup/rehearsal, or restore/rollback
   development merely to resume this completed task.
2. Owner must choose and authorize the next task. Suggested existing roadmap
   item: `HT-TEST-P1-01`, a reproducible isolated PostgreSQL test harness/CI
   foundation. This is a recommendation only; no new feature is authorized.
3. Retain the ignored host backup. Any later recovery or production/other
   persistent-target rollout needs its own explicit authorization and plan.
   The archive can be read with `pg_restore --list`; its restore into a newly
   created isolated target was already rehearsed with
   `pg_restore --exit-on-error --single-transaction --dbname=<approved-target>`.
   Do not restore over development without separate approval.

### Development apply and smoke completed

- Applied exactly `accounts.0002` through standard Django migration at
  `2026-10-24 06:30:28.634074 UTC`, once, after rechecking the same preflight,
  backup equality, and single-migration plan. No other migration was pending.
- Development now has 32 migration records, 15 User columns, 17 token columns,
  nine validated token CHECKs, two validated token FKs, nine valid/ready token
  indexes, and both User verification constraints. No unintended DB defaults.
  All 39 public foreign keys have zero orphans. Every legacy row still equals
  the restored baseline; the 3 active Users and 2 Sessions are unchanged.
  Verification state stays null and token/business/AuditLog tables stay empty.
  Standard Django metadata is now 23 content types and 92 permissions.
- Dependency, Django system, migration drift/applied/empty-plan checks PASS.
- **DEV SMOKE PASSED**: 36 fixture-free requests through the Django handler
  against development in a PostgreSQL READ ONLY transaction, with real CSRF
  enforcement. Health/CSRF 200, missing-CSRF 403, malformed register/login/reset
  400, anonymous protected/Invitation routes 403, public method restrictions
  405, unknown reset request neutral 202, fake reset confirm generic 400.
  No 500, PII disclosure, email attempt, login, or User/Session/token mutation.
  Authenticated success and real verification/reset/Invitation acceptance are
  **NOT TESTED ON PERSISTENT DEVELOPMENT**; isolated tests cover those paths.
- Resume reconfirmed the same applied migration record/schema and exact legacy
  rows; backup remains the same valid pre-migration archive (no replacement or
  restore to development). Added eight Task/Review anonymous boundary requests
  plus one CSRF bootstrap, all READ ONLY and PASS: list/detail, assign/start,
  Deliverable list/submit, approve/request changes. Total development smoke is
  **45 requests** (36 original + 8 boundaries + 1 bootstrap).

### Current isolated verification

- Account Security: **44/44 PASS** in 30.549s.
- Authentication/API Foundation: **29/29 PASS** in 7.523s.
- Invitation: **40/40 PASS** in 61.679s.
- Workspace/RBAC: **140/140 PASS** in 79.717s.
- Task/Review workflow: **33/33 PASS** in 8.457s.
- Final full PostgreSQL suite: **286/286 PASS** in **197.049s**, exit code 0.
  The interrupted first run had no retained verdict and is not counted as
  passing. Its inactive leftover test database was removed after verification;
  only the unfinished full run was restarted. Final full log and verdict are
  retained Git-ignored at `.local_backups/HT-DB-P1-09/full_postgresql_tests.log`
  and `.local_backups/HT-DB-P1-09/full_postgresql_tests.exit`.
- The five targeted groups above completed in this rollout before the resume
  interruption. Source file timestamps/diff confirm no subsequent backend
  edits, so those valid results are reused without rerunning them. Only the
  incomplete full run was restarted. No migration was reapplied.

### Final preservation, cleanup, and files

- After all tests, full schema/FK/identity checks and exact original-row
  comparison passed again. Users remain active with unchanged original fields,
  passwords and email identities; Session payloads/keys/expiry are unchanged.
  No verified User, token, or business/AuditLog row was created. Only expected
  Django migration/content-type/permission metadata changed.
- Final `pip check`, Django system check, migration drift check,
  `migrate --check`, and `git diff --check` PASS (only existing LF/CRLF notices).
- Removed only this task's isolated rehearsal database (after checking zero
  connections), disposable runner, and container-only backup copy. No
  `test_%`/`htdb_p109%` database remains. The retained host archive is still
  93,598 bytes with the same SHA-256; test logs/helpers remain local/ignored.
  The original PostgreSQL container and named volume remain intact/running.
- Updated `HANDOVER.md`, `PROGRESS.md`, `PROJECT_ROADMAP.md`,
  `REQUIREMENT_STATUS.md`, `CHANGELOG.md`, `DATABASE_SCHEMA.md`,
  `API_DOCUMENTATION.md`, and `PROJECT_CONTEXT.md`. `DECISION_LOG.md` and
  `RBAC_DESIGN.md` received only rollout-authorization/status reconciliation
  to supersede stale pending-development wording; no business rule changed.
- No backend source, models, migration file, requirements, configuration,
  secrets, or API contract was edited by this rollout. All existing dirty code
  was preserved. No commit/push/reset or production access occurred.

Repository edits are documentation and ignored operational helpers only;
pre-existing code/models/migrations have not been changed by this rollout.
No blocker is known. **REAL EMAIL DELIVERY NOT VERIFIED. DISTRIBUTED RATE
LIMITING NOT VERIFIED.** Reset-request status/body neutrality does not
establish timing indistinguishability.

All checkpoints below are historical and do not override this completed
development rollout or its current Owner Review Gate.

---

## Historical checkpoint — 2026-10-24 — HT-AUTH-P1-02 OWNER REVIEW GATE

Status: **IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**

Repository: `D:\da\HustlyTasker`

Current task: **HT-AUTH-P1-02 — Account Verification & Password Recovery Foundation**

This is the authoritative continuation point. Preserve every existing
uncommitted HT-INV-P2-04/HT-DB-P1-08 change and the new Auth work. Do not apply
`accounts.0002_accountsecuritytoken_user_email_verification` to persistent
development or production.

### Completed implementation at this checkpoint

- Added nullable `User.email_verified_at` plus
  `User.verified_email_normalized`. Effective verification requires both fields
  and a normalized snapshot matching the current email. Existing Users are not
  backfilled, disabled, or blocked from login.
- Added `AccountSecurityToken` with separate email-verification/password-reset
  purposes, unique purpose-bound SHA-256 digest, 24-hour verification TTL,
  one-hour reset TTL, one-time lifecycle, delivery state, replacement lineage,
  terminal timestamps, constraints, partial uniqueness, and lookup indexes.
  Password-reset rows additionally store a SHA-256 fingerprint of the encoded
  password state; `acctok_fingerprint_by_purpose` requires that binding only for
  reset tokens.
- Added additive migration
  `accounts.0002_accountsecuritytoken_user_email_verification`. It was applied
  only by Django-created isolated PostgreSQL test databases. It is intentionally
  unapplied on persistent development.
- Added authenticated+CSRF verification request/confirm APIs and explicit
  public+CSRF password-reset request/confirm APIs. Strict serializers, no-cache
  output, separate throttles, HTTP status/body-neutral reset-request responses,
  purpose isolation, password validation, row locks, and atomic AuditLog writes
  are implemented. Reset confirmation has an independent token budget of
  10/hour and client-address budget of 30/hour.
- A normalized email change revokes every pending verification/reset token and
  clears verified state, so an old reset token cannot become usable again after
  an A→B→A email cycle. A normal password save revokes pending reset tokens;
  direct password updates are rejected at confirmation by the password-state
  fingerprint. Reset consumes the credential and changes the password in one
  transaction.
- Password reset uses Django `set_password()` and deliberately does not call
  `update_session_auth_hash()` or login. Existing sessions fail Django's stored
  auth-hash check and are flushed on their next request; two-session coverage
  proves this behavior.
- Added a shared `apps.common.email_delivery` transport guard and retained
  separate account/Invitation lifecycle state. Delivery runs on commit, rejects
  unsafe development backends for credential issuance, stores `SENT`/`FAILED`
  honestly, and never exposes raw credentials through APIs or audit metadata.
- Invitation identity now delegates only normalization/unique-user resolution
  to the shared account identity helper. Invitation proof remains independent:
  verification does not accept an invitation or grant membership; accepting an
  invitation does not set global verified state; unverified legacy Users retain
  the previously implemented invitation flow.
- Malformed Unicode credential/recipient inputs fail closed with HTTP 400 in
  account reset and Invitation paths instead of reaching unsafe hashing code.

### Files changed for this task

- Account/API/config: `backend/apps/accounts/{admin.py,email_delivery.py,identity.py,models.py,security_services.py,security_throttles.py,serializers.py,urls.py,views.py}`,
  `backend/apps/accounts/migrations/0002_accountsecuritytoken_user_email_verification.py`,
  the three `test_security_*.py` modules, `backend/api/tests.py`, and
  `backend/config/settings.py`.
- Shared/Invitation integration: `backend/apps/common/email_delivery.py` and
  the existing `backend/apps/workspace/invitation_{delivery,identity,services,throttles}.py`
  path plus Invitation API regression coverage. Pre-existing Workspace/Task/
  Invitation dirty work was preserved; nothing was reset or overwritten.
- Documentation: `PROGRESS.md`, `PROJECT_ROADMAP.md`, `REQUIREMENT_STATUS.md`,
  `CHANGELOG.md`, `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md`,
  `RBAC_DESIGN.md`, `DECISION_LOG.md`, `PROJECT_CONTEXT.md`, and this
  `HANDOVER.md`.

### Verification actually run

- Development read-only reconfirmation: PostgreSQL 16.14 database
  `hustlytasker_db`, not in recovery, 31 applied migration rows, only
  `accounts.0001` applied, 3 Users, 2 sessions, and zero checked business/AuditLog
  rows. The two new User columns and account-token table are absent. No `test_%`
  database remains.
- Disposable Python 3.12 runner `htp_auth_test_runner`, source mounted
  read-only: `pip check` PASS; Django system check PASS; migration drift check
  PASS (`No changes detected`). The runner had no data volume and was removed
  after final verification; the development PostgreSQL container remains.
- Final Auth security/migration suite: **44/44 PASS** in 32.336s. It covers token
  lifecycle/secrecy, identity ambiguity, CSRF, throttle, delivery failure,
  session invalidation, rollback, PostgreSQL constraints, concurrency, and
  migration `accounts.0001 -> 0002` with legacy rows.
- Authentication/API Foundation plus complete Invitation regression:
  **113/113 PASS** in 99.629s.
- Workspace/RBAC/Task/Review regression: **173/173 PASS** in 93.895s.
- Full PostgreSQL suite after the final fixes: **286/286 PASS** in 188.592s.
- `git diff --check` passes with only existing LF-to-CRLF notices and no
  whitespace error.

### Exact safe continuation

1. Stop at this Owner Review Gate. Do not begin another roadmap task.
2. If the Owner authorizes rollout, open a separate controlled development
   migration task for `accounts.0002`: re-inventory, backup, plan, rehearsal,
   apply, post-check, smoke verification, and regression. This handover does
   not itself authorize applying the migration.
3. Do not apply this migration to production or any other persistent target
   without a target-specific approval and safety gate.

### Current limitations / blockers

- No implementation blocker is known. Persistent development is intentionally
  schema-behind current source; User/account ORM paths (including the four new
  APIs) may fail on missing columns/table until the separately gated
  `accounts.0002` rollout. Do not treat it as a current-source smoke target yet.
- **REAL EMAIL DELIVERY NOT VERIFIED.** Only locmem/mock delivery is tested.
- Auth and Invitation DRF cache throttles remain process-local and are not
  production-grade distributed rate limits. No Redis/shared cache was added.
- Database case-insensitive email uniqueness is not introduced because other
  target inventories are unknown; every security flow fails closed on ambiguous
  case-insensitive identities.
- Password-reset request responses are neutral in status/body, but synchronous
  configured-mail delivery means response timing is not equalized or proven
  indistinguishable between eligible and ineligible identities.

---

## Historical checkpoint — 2026-10-23 — HT-DB-P1-08 COMPLETE / OWNER REVIEW GATE

Status: **CONTROLLED DEVELOPMENT ROLLOUT VERIFIED**

Repository: `D:\da\HustlyTasker`

Current task: **HT-DB-P1-08 — COMPLETE / OWNER REVIEW GATE**

This is the authoritative continuation point. Preserve all existing uncommitted
HT-INV-P2-04 implementation. Do not recreate or edit
`workspace.0004_profileinvitation`.

### Verified target, backup, and rehearsal

- Confirmed the target is the repository-owned PostgreSQL 16.14 development
  service `hustlytasker_postgres`, database `hustlytasker_db`, loopback-bound
  on `127.0.0.1:5432`, not in recovery, with no production indicators.
- Development inventory before migration: 30 migration records; 3 Users; 2
  sessions; zero Profile, ProfileMembership, Workspace, WorkspaceMember,
  ProfileInvitation, Task, TaskAssignment, Deliverable, Review, Client,
  Invoice, Payment, or AuditLog rows. Workspace migrations 0001-0003 are
  applied; `workspace.0004` is pending and its table is absent.
- Static and SQL review found one additive transactional `CreateModel` only:
  no backfill, `RunPython`, `RunSQL`, drop, rename, or alteration of existing
  tables. `migrate --plan` lists only `workspace.0004_profileinvitation`.
- Fresh custom-format backup retained at
  `.local_backups/HT-DB-P1-08/hustlytasker_dev_pre_workspace_0004_20261023T050527Z.dump`
  (78,758 bytes; SHA-256
  `57f05837925c74a1bef83200a4211c3ed1cffbbe1e24552377d7efefc9baaf76`).
  Host/container hashes and sizes matched; `pg_restore --list` returned 198
  TOC lines and a full archive read completed successfully. The path is
  gitignored and no secret was recorded.
- Restored that archive into isolated database
  `htdb_p108_restore_20261023_050527`, verified its baseline, applied only
  `workspace.0004`, and verified 31 migration records, an empty 22-column
  invitation table, seven validated check constraints, seven validated foreign
  keys, two partial unique indexes, all indexes valid/ready, no schema drift,
  and unchanged source counts. Django `check`, migration drift check, and
  `migrate --check` passed there. The exact rehearsal database was then removed
  and its absence verified.

### Development apply and post-check

- Reconfirmed the same target, clean inventory/anomaly checks, no competing
  connection or relevant lock, and a global plan containing only
  `workspace.0004_profileinvitation` immediately before apply.
- Applied exactly `workspace.0004_profileinvitation` to `hustlytasker_db` at
  **2026-10-23 05:09:39.628419 UTC**. No broad/fake/reverse migration, data
  mapping, fixture, deletion, production access, or source/migration edit was
  performed.
- Development now has 31 migration records and exactly one applied 0004 row.
  `workspace_profileinvitation` is empty and has 22 expected columns, seven
  validated named CHECKs, seven validated foreign keys, two partial unique
  constraints, and 16 total indexes that are all valid/ready. It has no
  unintended permanent database defaults.
- Post-apply counts remain 3 Users, 2 sessions, and zero Profile,
  ProfileMembership, Workspace, WorkspaceMember, ProfileInvitation, Task,
  TaskAssignment, Deliverable, Review, Client, Invoice, Payment, or AuditLog
  rows. No integrity, validation, or index anomaly was found.
- Django `check`, `makemigrations --check --dry-run`, and `migrate --check`
  pass against the migrated development schema.

### Fixture-free development smoke

- Health `GET` returns 200 and unsupported `POST` returns 405; CSRF bootstrap
  returns 200; registration without CSRF returns 403; an invalid registration
  payload with a valid CSRF token returns 400.
- Anonymous Auth/Profile route shapes; Profile lifecycle; Workspace
  list/create/detail/update/archive/restore; Workspace membership
  list/create/update/revoke; and Invitation manager
  list/create/detail/revoke/resend plus recipient accept/decline all return
  403. No request returned 500, exposed a token/digest/User PII, or changed
  row/session counts.
- Development has no Profile/Workspace business fixture and no valid existing
  authenticated session. Successful authenticated Invitation mutations were
  therefore **NOT TESTED ON PERSISTENT DEVELOPMENT** and no credential or
  business data was created or changed there.
- **REAL EMAIL DELIVERY NOT VERIFIED.** No SMTP/provider credential was
  configured or exercised. DRF cache throttles remain process-local by
  default; the database-backed issuance ceilings remain authoritative for
  create/resend.

### Regression and cleanup evidence

- Targeted Invitation tests pass **39/39** in 62.528s; Authentication/API pass
  **29/29** in 7.475s; Workspace/RBAC/Task/Review pass **173/173** in 97.378s;
  and the full PostgreSQL suite passes **241/241** in 167.960s. Each
  Django-created test database was destroyed and the full run reported zero
  system-check issues.
- No `test_%` or `htdb_p108_restore_%` database remains. The exact
  container-side temporary backup was verified/hash-matched and removed.
  Disposable runners `htp_p108_runner` and `htp_p108_resume_smoke` were
  removed after their verified checks.
- The host backup remains at the documented path, still 78,758 bytes with the
  same SHA-256, and remains Git-ignored. The original development PostgreSQL
  container was running when the task started and remains intentionally
  running; its named volume was not removed or reset.
- Final `git diff --check` passes with only existing LF-to-CRLF conversion
  warnings and no whitespace error. Final `git status --short` contains the
  expected preserved HT-INV-P2-04 backend/documentation changes only; the
  ignored backup and removed temporary resources do not appear.

### Exact continuation / review gate

Stop at **OWNER REVIEW GATE**. The Owner must select and explicitly authorize
the next roadmap task; `HT-AUTH-P1-02 — Account Verification & Recovery` is a
candidate only. Do not start it or another feature, configure real credentials,
change production, or apply this migration to another target automatically.

### Working-tree and file boundary

- `HT-DB-P1-08` created or edited no backend source, model, API contract, or
  migration file. The pre-existing uncommitted HT-INV-P2-04 source and
  `workspace.0004_profileinvitation` remain preserved exactly as the rollout
  input.
- This operational checkpoint updates only `documentation/PROGRESS.md`,
  `PROJECT_ROADMAP.md`, `CHANGELOG.md`, `REQUIREMENT_STATUS.md`,
  `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md`, `PROJECT_CONTEXT.md`, and this
  `HANDOVER.md`. `DECISION_LOG.md` and `RBAC_DESIGN.md` require no P1-08 change
  because no architecture or product decision changed.
- No implementation or operational blocker remains. The host backup must be
  retained. The task stops because the agreed Owner review gate has been
  reached, not because another feature is implicitly authorized.

---

## Previous checkpoint — 2026-10-23 — HT-INV-P2-04

Status: **IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**

Repository: `D:\da\HustlyTasker`

Current task: **HT-INV-P2-04 — Profile Invitation & Membership Onboarding**

This historical implementation checkpoint records that the Invitation source,
additive migration, services, authenticated APIs, security tests, and required
documentation are complete. The migration was exercised only on disposable
PostgreSQL test databases. It has **not** been applied to persistent
development or production.

### Completed implementation

- Added `ProfileInvitation` in the existing Workspace app with Profile scope,
  normalized recipient email, optional recipient binding, `ADMIN`/`MEMBER`
  role ceiling, protected inviter membership, SHA-256 digest-only credential,
  `PENDING`/`ACCEPTED`/`DECLINED`/`REVOKED`/`EXPIRED` lifecycle, seven-day TTL,
  delivery state, terminal actors/timestamps, replacement lineage, constraints,
  and indexes.
- Added additive `workspace.0004_profileinvitation`. It creates only the new
  aggregate and performs no backfill or guessed tenant/email mapping.
- Added locked transactional create, revoke, resend/rotate, accept, decline,
  expiry, membership create/reactivation, stale Workspace-access revocation,
  original-inviter revalidation, durable issuance limits, and atomic AuditLog
  services.
- Recipient accept/decline requires an active authenticated account whose
  freshly locked current normalized email uniquely matches the invitation,
  plus the one-time credential accepted by the configured mail backend. This
  is proof scoped to one invitation; no global `email_verified` claim or
  recipient inbox was added.
- Added manager list/create/detail/revoke/resend and recipient accept/decline
  routes. All retain SessionAuthentication, CSRF, deny-by-default access,
  scoped/non-enumerating lookup, strict input, role ceilings, no-cache output,
  and token/digest/PII-safe responses.
- Delivery runs through Django's configured mailer after transaction commit.
  `QUEUED`, `SENT`, and `FAILED` are stored honestly. A failed committed
  delivery is recovered by a scoped manager list/detail followed by resend,
  which rotates the token. Console/dummy/file backends are rejected; locmem is
  allowed only in isolated tests.
- Added API, model/service, migration-preservation, concurrency, CSRF, IDOR,
  audit atomicity, lifecycle, role, identity, delivery-failure, replay, and
  throttling tests.

### Verification actually completed

- `python -m pip check`: PASS (`No broken requirements found`).
- `python manage.py check`: PASS (0 issues).
- `python manage.py makemigrations --check --dry-run`: PASS (`No changes
  detected`).
- Targeted Invitation model/service/API/migration suite: **39/39 PASS** in
  61.056s on a Django-created PostgreSQL test database; database destroyed.
- Authentication/API Foundation regression: **29/29 PASS** in 7.220s;
  database destroyed.
- Workspace/RBAC/Task/Review regression: **173/173 PASS** in 90.298s;
  database destroyed.
- Full PostgreSQL suite: **241/241 PASS** in 157.059s; database destroyed and
  system check reported 0 issues.
- Migration plan contains only `workspace.0004_profileinvitation`.
- Final read-only development inventory: 30 migration records; 3 Users; 2
  sessions; zero Profile, ProfileMembership, Workspace, WorkspaceMember, Task,
  Client, Invoice, Payment, or AuditLog rows. `workspace.0004` remains
  unapplied, `workspace_profileinvitation` is absent, and no `test_%` database
  remains.
- Final `git diff --check`: PASS; only line-ending conversion warnings, no
  whitespace error. Disposable runner `htp_inv_test_runner` was removed, and
  `hustlytasker_postgres` was returned to its original stopped state without
  deleting the container or named volume.

### Files changed by HT-INV-P2-04

- Modified backend: `apps/workspace/models.py`, `access.py`, `permissions.py`,
  `serializers.py`, `views.py`, `urls.py`, and `config/settings.py`.
- Added backend: `apps/workspace/invitation_identity.py`,
  `invitation_delivery.py`, `invitation_services.py`,
  `invitation_throttles.py`, `migrations/0004_profileinvitation.py`, and three
  Invitation test modules.
- Reconciled documentation: `PROGRESS.md`, `PROJECT_ROADMAP.md`,
  `CHANGELOG.md`, `REQUIREMENT_STATUS.md`, `DATABASE_SCHEMA.md`,
  `API_DOCUMENTATION.md`, `RBAC_DESIGN.md`, `DECISION_LOG.md`,
  `PROJECT_CONTEXT.md`, and this file.

### Remaining limits and exact continuation

- **REAL EMAIL DELIVERY NOT VERIFIED.** Only locmem/test adapters were used;
  no SMTP/provider credential was configured or tested.
- Cache-based DRF throttles remain process-local by default and are not a
  multi-worker production control. Locked database counters enforce the
  approved create/resend issuance limits.
- No global email-verification state, invitation inbox, automated retention
  purge, Workspace auto-add, Client/Project/Finance/Portal, frontend, or other
  adjacent feature was introduced.
- Stop at **OWNER REVIEW GATE**. The only proposed next operational task is a
  separately authorized `HT-DB-P1-08 — Controlled workspace.0004 Development
  Migration & Invitation Smoke Verification`, beginning with fresh target
  verification, inventory, backup, restore rehearsal, and exact plan review.
  Do not apply `workspace.0004`, configure real credentials, or start another
  module from this checkpoint.

---

## Previous checkpoint — 2026-10-21 — HT-INV-P2-04 IN PROGRESS

Repository: `D:\da\HustlyTasker`

Current task: **HT-INV-P2-04 — Profile Invitation & Membership Onboarding**

This checkpoint supersedes the HT-DB-P1-07 checkpoint below as the safe
continuation point. The Owner opened the Invitation implementation task. The
source implementation is present and preliminary checks pass, but Invitation
targeted/full PostgreSQL verification and final documentation are still in
progress. Do not mark the task complete from this checkpoint alone.

### Recovered state and development boundary

- Existing uncommitted HT-DB-P1-07 documentation was preserved. No reset,
  revert, commit, push, data deletion, or production access occurred.
- The existing local container was identified as PostgreSQL 16.14,
  `hustlytasker_postgres`, loopback-bound on `127.0.0.1:5432`, using named
  volume `docker_postgres_data` and this repository's Compose file.
- Read-only development inventory on 2026-10-21: 3 Users and zero Profile,
  ProfileMembership, Workspace, WorkspaceMember, Task, or AuditLog rows.
  Workspace 0001-0003, Tasks 0001-0002, and Reviews 0001-0002 are applied.
- `workspace.0004_profileinvitation` is **not applied** on development and the
  `workspace_profileinvitation` table is absent there. No development
  migration is authorized by HT-INV-P2-04.

### Implementation present

- Added `ProfileInvitation` under the existing Workspace app with normalized
  recipient email, optional account binding, requested `ADMIN`/`MEMBER` role,
  inviter ProfileMembership, SHA-256 token digest only, five lifecycle states,
  seven-day expiry, delivery state/timestamps, terminal actor/timestamps, and
  immutable resend lineage. Constraints protect role/status/delivery/terminal
  consistency, expiry ordering, pending uniqueness, and token uniqueness.
- Added additive migration
  `workspace.0004_profileinvitation`; it creates only the new invitation table,
  constraints, indexes, and foreign keys. It does not backfill or alter
  existing business rows.
- Added locked transactional services for create, revoke, resend/rotation,
  accept, decline, expiration materialization, role ceilings, original-inviter
  revalidation, durable issuance-count limits, and atomic AuditLog events.
- Acceptance requires an active authenticated account whose freshly locked,
  current normalized email uniquely matches a token delivered with `SENT`
  state. This is per-invitation proof of email control; it does not create or
  claim a global verified-email flag. Ambiguous case-insensitive account
  identity fails closed.
- Compatible single inactive ProfileMembership history is reactivated in the
  same row. Active membership, ambiguous/mismatched history, inactive OWNER,
  or an unauthorized original inviter fails closed. Any stale active
  WorkspaceMember rows for a rejoining user are transactionally soft-revoked
  with audit so Profile rejoin never restores Workspace access implicitly.
- Delivery uses Django's configured mailer after transaction commit. Console,
  dummy, and file backends are rejected for Invitation delivery; locmem is
  permitted for isolated tests. Failure is recorded as `FAILED` and surfaced
  generically; no API returns a token. Real SMTP/provider delivery remains
  unverified.
- Added manager routes for list/create/detail/revoke/resend and authenticated
  recipient routes for accept/decline under `/api/v1/`. No recipient inbox was
  added because the current account model lacks persistent account-level email
  verification. APIs keep SessionAuthentication, CSRF, strict input,
  non-cacheable responses, tenant-safe 404 behavior, role ceilings, and
  sanitized output.
- Added authenticated-user/normalized-recipient cache throttles plus locked
  database issuance counts. The process-local default cache remains a stated
  multi-worker deployment limitation; no Redis infrastructure was introduced.

### Files currently changed for HT-INV-P2-04

- Modified: `backend/apps/workspace/models.py`, `access.py`, `permissions.py`,
  `serializers.py`, `views.py`, `urls.py`, and `backend/config/settings.py`.
- Added: `invitation_identity.py`, `invitation_delivery.py`,
  `invitation_services.py`, `invitation_throttles.py`, and
  `migrations/0004_profileinvitation.py`.
- Invitation test files are being added under `backend/apps/workspace/`; treat
  them as work in progress until the targeted run below is recorded as pass.
- The eight pre-existing modified documentation files from HT-DB-P1-07 remain
  preserved. Final Invitation reconciliation must also update
  `DECISION_LOG.md` and `RBAC_DESIGN.md`.

### Verification actually completed at this checkpoint

- Disposable Python 3.12 runner, source mounted read-only:
  `pip check` PASS; Django system check PASS; migration drift check PASS (`No
  changes detected`); migration plan lists only
  `workspace.0004_profileinvitation`.
- Isolated PostgreSQL Authentication/API regression: **29/29 PASS**. The test
  database successfully applied 0004 and was destroyed afterward.
- Development was queried only read-only for the migration boundary; no
  migration was applied there.
- Not yet authoritative/pending: Invitation targeted tests, migration test,
  Workspace/Task regression, full PostgreSQL suite, final diff check, final
  development post-check, and complete documentation reconciliation.

### Exact safe continuation

1. Finish/review Invitation model/service/API/migration tests; fix production
   defects without changing the approved architecture.
2. Run targeted Invitation tests on a disposable PostgreSQL database, then
   Authentication/API, Workspace/Task/Review, and full regression.
3. Reconfirm no test database remains and development still stops at
   `workspace.0003` with no invitation table.
4. Update all documents required by the Owner and set
   `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL` only if
   every acceptance criterion has current evidence.
5. Stop at the Owner Review Gate. Do not apply 0004 to development, configure
   real credentials, or start another roadmap task.

---

## Previous checkpoint — 2026-10-21 — HT-DB-P1-07 COMPLETE / OWNER REVIEW GATE

Repository: `D:\da\HustlyTasker`

Branch/HEAD at task start: `main` / `f5a2147` (`HT-TASK-P2-03`)

Current task: **HT-DB-P1-07 — COMPLETE / OWNER REVIEW GATE**

Owner authorized a condition-gated rollout of only
`tasks.0002_task_workflow_foundation` and
`reviews.0002_review_workflow_foundation` to the identified local development
database. Inventory, backup, restore rehearsal, explicit apply, post-check,
smoke, and regression verification are complete. Production and feature
implementation remained out of scope.

### Target and pre-apply evidence

- Verified local Docker Desktop/Compose target `hustlytasker_postgres`,
  PostgreSQL 16.14, database `hustlytasker_db`, loopback-only
  `127.0.0.1:5432`, named volume `docker_postgres_data`, and Compose labels
  pointing to this repository's `docker/docker-compose.yml`. No other client
  connection or relevant lock was present.
- Baseline has 28 migration records: Workspace 0001-0003 applied; Tasks and
  Reviews only 0001. The two approved 0002 columns/constraints/indexes were
  absent, so migration history and physical schema agreed.
- Inventory: 3 active Users, 2 sessions, and zero Profile,
  ProfileMembership, Workspace, WorkspaceMember, Task, TaskAssignment,
  TaskComment, Deliverable, Review, Client, Invoice, Payment, or AuditLog rows.
- Legacy preflight found zero invalid Task/Deliverable/Review status, invalid
  Task priority, multiple/duplicate assignment, duplicate Review, orphan,
  unmapped tenant, cross-tenant membership anomaly, or unvalidated
  constraint. No data was edited or mapped.
- `pip check`, Django system check and migration drift check passed. The exact
  plan lists only Tasks 0002 followed by Reviews 0002.
- Fresh ignored custom-format backup:
  `.local_backups/HT-DB-P1-07/hustlytasker_dev_pre_task_review_0002_20261020T233252Z.dump`
  (75,502 bytes), SHA-256
  `4d89fe198da9a245c6ae39c466a11944a80914735c876dbeb18f546d55391f22`.
  Host/container hashes match; `pg_restore --list` produced a readable
  192-line TOC and a full archive read passed.
- Full restore rehearsal in isolated database
  `htdb_p107_restore_20261020233252` reproduced the baseline. Applying Tasks
  0002 then Reviews 0002 there passed, produced 30 migration records and all
  expected validated schema objects without changing inventory. The rehearsal
  database was removed and its absence verified.

### Development apply and post-check

- The final gate immediately before apply still matched the verified baseline.
  `tasks.0002` was applied explicitly at 2026-10-20 23:35:36 UTC; its
  intermediate schema/integrity gate passed. `reviews.0002` was then applied
  explicitly at 2026-10-20 23:36:12 UTC. No migration was faked, reversed,
  edited, or applied outside development.
- Development now has 30 applied migration records: Workspace 0001-0003,
  Tasks 0001-0002, and Reviews 0001-0002 are applied. Inventory remains 3
  active Users, 2 sessions, and zero checked Profile/Workspace/Task/Review,
  Client, Invoice, Payment, or AuditLog rows; no mapping, fixture, or data
  deletion occurred.
- Physical inspection confirmed `TaskAssignment.is_active` is non-null boolean
  with no permanent database default and `Deliverable.revision` is nullable
  integer with no permanent database default. All five named CHECK constraints
  and the Review uniqueness constraint are validated; all six named lookup or
  unique indexes are valid and ready.
- Workflow actor foreign keys are validated with PostgreSQL `NO ACTION`;
  Django's `PROTECT` enforcement remains ORM behavior. Final checks found zero
  invalid enum, duplicate active assignment/revision/Review, orphan,
  cross-tenant, or unvalidated-constraint condition. No other connection,
  test/rehearsal database, or disposable runner remained.
- `pip check`, Django system check, migration drift check, `migrate --check`,
  migration plan, and `showmigrations` all passed after apply.

### Smoke and regression evidence

- **Fixture-free development smoke passed:** health `GET`/`HEAD`/`OPTIONS`
  returned `200`; health `POST`/`PUT`/`DELETE` returned `405`; CSRF bootstrap
  returned `200`; login without CSRF returned `403`; invalid login with a valid
  token returned `400`; anonymous me/logout and Profile/Workspace/Task/
  Deliverable action route shapes returned `403`. No response was `500` and no
  development row/session changed.
- Successful authenticated business mutations and method-specific Task
  behavior were not exercised on persistent development because it has no
  business fixture and credentials were not changed. Isolated PostgreSQL tests
  are the evidence for those paths.
- Current isolated results: Task workflow/API/migration **33/33 PASS** in
  7.998s; Authentication/API Foundation **29/29 PASS** in 7.183s; Workspace
  **140/140 PASS** in 77.774s; full suite **202/202 PASS** in 93.368s. Every
  Django test database was destroyed.
- Two earlier smoke harness invocations stopped before sending any request
  (Docker argument parsing, then a harness `NameError` after Django checks).
  They did not indicate an application failure; the corrected authoritative
  third run produced the smoke evidence above.

### Files and retained recovery artifact

- HT-DB-P1-07 changed documentation only. It did not edit backend source,
  models, migration files, API contracts, Authentication, or business data.
- Updated task documents: `PROGRESS.md`, `PROJECT_ROADMAP.md`, `CHANGELOG.md`,
  `REQUIREMENT_STATUS.md`, `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md`,
  `PROJECT_CONTEXT.md`, and this `HANDOVER.md`. `DECISION_LOG.md` and
  `RBAC_DESIGN.md` remain unchanged because no decision or architecture
  contract changed.
- The verified pre-apply archive remains at the ignored local path listed
  above for controlled recovery. It is not tracked and contains no credential
  in documentation.

### Exact safe continuation / review gate

1. Stop at **HT-DB-P1-07 — COMPLETE / OWNER REVIEW GATE**.
2. The Owner must select and explicitly authorize the next roadmap
   implementation. Do not infer or start a new module from this rollout.
3. Production and every other persistent environment remain unauthorized;
   each requires independent target identification, inventory, backup,
   rehearsal, plan, apply, integrity, smoke, and regression evidence.

---

## Previous checkpoint — 2026-10-21 — HT-TASK-P2-03

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD/local `origin/main`: `9ff7eb0`

Current task: **HT-TASK-P2-03 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**

This checkpoint replaces the prior HT-DB-P1-06 continuation. Owner explicitly
opened the backend-only Task Management & Internal Approval Workflow task.
Implementation, targeted verification, full regression, independent code
review, and final development post-check are complete. The two additive source
migrations remain unapplied and require separate Owner approval.

### Recovered baseline and development state

- Read root `AGENTS.md`, the prior handover/current documentation, dirty Git
  state, Task/Review/Workspace source, migrations, routes, tests, and the
  approved task request before continuing. Existing uncommitted HT-DB-P1-06
  documentation changes were preserved.
- Development is the existing local Compose PostgreSQL 16.14 database from
  HT-DB-P1-06. Final read-only verification found 3 Users, 2 sessions, and zero Profile,
  ProfileMembership, Workspace, WorkspaceMember, Task, TaskAssignment,
  Deliverable, Review, or AuditLog rows.
- Development has `workspace.0003` applied. It has only `tasks.0001` and
  `reviews.0001`; the new `tasks.0002` and `reviews.0002` migrations are not
  applied. `showmigrations` confirms this state; `migrate --plan` succeeds and
  lists only additive `tasks.0002` followed by `reviews.0002`. Production was
  not contacted and no migration was applied.
- This task does not authorize a development or production migration, fixture,
  data mapping, reset, deletion, commit, push, or history rewrite.

### Implementation completed in source

- `Task.created_by`, `TaskAssignment.user`, `TaskComment.user`,
  `Deliverable.uploaded_by`, and `Review.reviewer` now use `PROTECT`.
- `tasks.0002_task_workflow_foundation` adds Task status/priority checks and
  scoped lookup index, `TaskAssignment.is_active`, at most one active assignment
  per Task, and its lookup index. Migration sets every legacy assignment
  inactive before changing the default for new rows to true; it never guesses
  a current assignee.
- `reviews.0002_review_workflow_foundation` adds nullable legacy-safe positive
  Deliverable revisions, unique non-null `(task, revision)`, Deliverable/Review
  status checks and lookup index, and one Review per Deliverable. Existing
  Deliverables retain null revision; no ordering is invented.
- Task create/update/assign/start, Deliverable submit, internal approve, and
  request-changes run through locked transactional services and atomic
  AuditLog writes. Workflow is `PENDING -> ASSIGNED -> WORKING -> REVIEW`, then
  `COMPLETED` after approval or back to `WORKING` after requested changes.
- Profile Owner/Admin and assigned Workspace Admin manage and internally review
  Tasks. Only an active ordinary Profile Member with Workspace `MEMBER`
  (Editor) capability and the Task's current active assignment may start or
  submit. Self-review, stale revision, repeat decision, invalid transition,
  cross-tenant and wrong-parent access fail closed.
- Any effective Workspace reader may read Task/Deliverable history. Serializer
  output contains current ProfileMembership attribution only, never global User
  ID/PII; stale/deactivated membership attribution becomes null.
- Task, TaskAssignment and TaskComment Admin are inspection-only. Workspace
  delete in Django Admin is disabled because the existing Workspace -> Task FK
  would otherwise cascade-delete workflow history.
- Internal approval is not Client/Guest approval and creates no Payroll,
  Payment, Invoice, or compensation calculation. No comments, Marketplace,
  media upload/storage, Finance, Invitation, frontend, soft-delete, arbitrary
  status, cancellation, PUT, or delete API was added.

### Current Task API surface

All paths are under `/api/v1/`, use SessionAuthentication/global
`IsAuthenticated`, tenant-scoped permissions, CSRF on unsafe methods, strict
input, non-cacheable responses, and generic IDOR-safe `404`:

```text
GET/POST  /profiles/{profile_id}/workspaces/{workspace_id}/tasks/
GET/PATCH /profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/
POST      /profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/assign/
POST      /profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/start/
GET/POST  /profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/deliverables/
POST      /profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/deliverables/{deliverable_id}/approve/
POST      /profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/deliverables/{deliverable_id}/request-changes/
```

No Task/Deliverable `DELETE`, no `PUT`, and no arbitrary status endpoint exists.
See `documentation/API_DOCUMENTATION.md` for request/response contracts.

### Verification actually run

Completed in a disposable Python 3.12 runner on `docker_default`, with source
mounted read-only and Django creating/destroying its isolated PostgreSQL test
database:

- `python -m pip check`: PASS.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, `No changes
  detected`.
- `python manage.py test apps.tasks.test_workflow_services apps.tasks.test_api
  apps.tasks.test_migrations -v 2`: PASS, **33/33** in 7.673s.
- Migration coverage preserved legacy Task/Assignment/Deliverable/Review rows,
  left two legacy assignments inactive, retained null legacy revision, and
  enforced the new one-active-assignment constraint.
- Existing Authentication/API/Workspace regression group: PASS, **169/169** in
  87.783s.
- Final full PostgreSQL suite: PASS, **202/202** in 92.343s; the test database
  was destroyed.
- Independent final code review: PASS.
- Documentation-scoped `git diff --check`: PASS; only LF-to-CRLF conversion
  warnings were emitted.
- Final development post-check: Workspace 0001-0003 applied; Tasks/Reviews only
  0001; 3 Users, 2 sessions, zero checked business/workflow rows; no
  test/rehearsal database or `htp203` runner remains.

### Migration rollout hazards and mandatory preflight

Before any future persistent apply, identify the exact authorized target,
inventory and back it up, rehearse, review dependencies and exact plan, then
check at minimum:

- Task/Deliverable/Review status and Task priority values that would violate
  the new CHECK constraints;
- more than one existing Review for the same Deliverable, which would block the
  new uniqueness constraint;
- every legacy Task assignment and Deliverable revision requiring business
  reconciliation.

The migration deliberately preserves ambiguous history. Do not auto-delete or
deduplicate Reviews, choose an active assignee, synthesize a revision, re-parent
a Task, or apply/fake/reverse either migration without separate Owner approval.

### Dirty files to preserve

Current backend/source/test files touched by HT-TASK-P2-03:

- `backend/api/urls.py`
- `backend/apps/tasks/{models,admin,access,permissions,serializers,services,views,urls}.py`
- `backend/apps/tasks/{test_workflow_services,test_api,test_migrations}.py`
- `backend/apps/tasks/migrations/0002_task_workflow_foundation.py`
- `backend/apps/reviews/models.py`
- `backend/apps/reviews/migrations/0002_review_workflow_foundation.py`
- `backend/apps/workspace/{access,services,admin}.py`

Documentation remains dirty because the prior controlled rollout notes and the
current Task checkpoint are uncommitted. Current affected documents are:

- `documentation/PROGRESS.md`
- `documentation/PROJECT_ROADMAP.md`
- `documentation/CHANGELOG.md`
- `documentation/REQUIREMENT_STATUS.md`
- `documentation/DATABASE_SCHEMA.md`
- `documentation/API_DOCUMENTATION.md`
- `documentation/RBAC_DESIGN.md`
- `documentation/DECISION_LOG.md`
- `documentation/PROJECT_CONTEXT.md`
- `documentation/HANDOVER.md`

No file may be reset, reverted, overwritten wholesale, committed, or pushed.

### Exact safe continuation / review gate

1. Re-read this top checkpoint and inspect current `git status`/diff; do not
   redo completed implementation/verification unless evidence changed.
2. Stop for Owner review at `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT
   MIGRATION APPROVAL`.
3. Only if separately authorized, open a controlled development migration task
   that repeats target identity/inventory, backup, preflight, exact plan,
   apply, integrity and API smoke verification for `tasks.0002` then
   `reviews.0002`.
4. Do not apply either migration from this checkpoint; do not
   start Workspace/Task follow-on, Invitation, Client/Project, Finance,
   Client/Guest review, Payroll, frontend, or any other module.

No owner-decision blocker is known for the implemented internal slice. The
only gate is separate Owner authorization for controlled development migration.

---

## Superseded checkpoint — 2026-10-20 — HT-DB-P1-06

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main` before this documentation checkpoint: `9ff7eb0`

Current task: **HT-DB-P1-06 — COMPLETE / OWNER REVIEW GATE**

The Owner authorized a condition-gated application of
`workspace.0003_workspace_lifecycle_and_period` to the identified development
database only. The migration was applied successfully at
2026-10-20 07:44:40 UTC. Production remains out of scope.

### Verified development target and pre-migration state

- Existing Compose-labeled container `hustlytasker_postgres` was already
  running when this task resumed. It is PostgreSQL 16.14, database
  `hustlytasker_db`, bound only to `127.0.0.1:5432`, with named volume
  `docker_postgres_data` mounted at `/var/lib/postgresql/data`. Compose labels
  point to this repository's `docker/docker-compose.yml`; production was not
  contacted.
- Immediately before the approved apply, development had 27 migration records.
  `workspace.0001` and `workspace.0002` were applied; `workspace.0003` and its
  physical columns, constraints, and indexes were absent, so migration history
  and schema agreed.
- Inventory: 3 active Users; 2 existing Django sessions; zero Profile,
  ProfileMembership, Workspace, WorkspaceMember, Task, TaskAssignment,
  TaskComment, Deliverable, Review, Client, ShareLink, Invoice, Payment,
  Notification, and AuditLog rows. There are no other PostgreSQL connections,
  unvalidated constraints, or leftover test/rehearsal databases.
- `pip check`, Django system check, and
  `makemigrations --check --dry-run` passed in a disposable Python 3.12
  container with source mounted read-only. Both global and targeted
  `migrate --plan` list only the reviewed additive `workspace.0003` operations.

### Fresh pre-apply backup

- New ignored custom-format archive:
  `.local_backups/HT-DB-P1-06/hustlytasker_dev_pre_workspace_0003_20261020T073750Z.dump`
- Size: 73,521 bytes.
- SHA-256:
  `b004c1e102b0fedde5eea4418010d46fec76ea18788e59b937e7ef4cb63f7df4`.
- `pg_restore --list` returned a readable 188-line TOC; a complete archive read
  to `/dev/null` passed; container and host hashes match.
- A full restore rehearsal into isolated database
  `htdb_p106_restore_20261020073818` reproduced 27 migrations, 3 Users, zero
  checked business rows, no `0003` columns, and no unvalidated constraint. The
  rehearsal database was then removed and its absence verified.

### Post-apply database checkpoint

- Development now has 28 migration records; `workspace.0001`, `0002`, and
  `0003` are applied.
- `Profile.status` and `Workspace.status` are non-null varchar columns;
  `Workspace.period` is nullable date for legacy compatibility; and
  `WorkspaceMember.is_active` is non-null boolean. Django left no permanent
  database defaults, as expected for these `default=` model fields.
- All three lifecycle/period CHECK constraints are validated. The conditional
  unique `(profile_id, period)` index, including archived rows, and all three
  lookup indexes are valid and ready.
- Pre/post inventory is unchanged: 3 active Users, 2 Django sessions, and zero
  rows in every checked business table. There are no invalid lifecycle values,
  invalid period days, duplicate Profile/period pairs, unvalidated constraints,
  other PostgreSQL connections, or leftover test/rehearsal databases.
- No reverse migration, `--fake`, fixture, data deletion, or production action
  occurred.

### Verification completed after apply

- Dependency and framework checks passed: `pip check`, `manage.py check`,
  `makemigrations --check --dry-run`, and `migrate --check`. `showmigrations`
  reports Workspace `0001`, `0002`, and `0003` applied.
- **DEV SMOKE PASSED:** a direct development request-stack smoke used no
  business fixture and changed no row or session. Health returned `200`; CSRF
  bootstrap returned `200`; login without CSRF returned `403`; invalid login
  with a valid CSRF token returned `400`; anonymous `/api/auth/me/` and
  `POST /api/auth/logout/` returned `403`; and every implemented
  Profile/Workspace/membership business method exercised by the smoke returned
  `403`. Before and after remained 3 active Users, 2 sessions, and zero checked
  business rows.
- **ISOLATED INTEGRATION TEST PASSED:** lifecycle/schema/concurrency 17/17,
  Workspace API/service/migration 140/140, Authentication/API Foundation
  29/29, and the independently rerun full PostgreSQL suite 169/169. The full
  suite ran in 85.858s. Each run created and destroyed its own Django test
  database.
- Final post-check still reports 28 migrations, unchanged inventory, all four
  expected columns, three validated CHECK constraints, and four valid/ready
  indexes. No invalid lifecycle/period row, duplicate Profile/month,
  unvalidated constraint, other database session, temporary test/rehearsal
  database, or temporary runner remains.
- **NOT TESTED ON PERSISTENT DEVELOPMENT:** successful authenticated tenant
  operations, role/tenant/IDOR behavior, archive/restore, and
  revoke/reactivate, because development has no business fixtures and no
  credential was requested or changed. Those cases passed in the isolated
  PostgreSQL integration suites above.

### Files and safe next step

Only tracked repository documentation files were edited by this operational
task:
`documentation/HANDOVER.md`, `PROGRESS.md`, `PROJECT_ROADMAP.md`,
`REQUIREMENT_STATUS.md`, `CHANGELOG.md`, `DATABASE_SCHEMA.md`,
`API_DOCUMENTATION.md`, `PROJECT_CONTEXT.md`, `RBAC_DESIGN.md`, and
`DECISION_LOG.md`. The backup is Git-ignored. Backend source and migration files
were not edited; no business row, credential, authentication mechanism, API
contract, or production state changed.

Stop at the Owner review gate. `HT-TASK-P2-03` is only the next roadmap
candidate and must not start without separate authorization and approval of
the canonical Task states, reviewer authority, and payroll trigger. Invitation,
Client, Project, Finance, Review workflow, and frontend also remain out of
scope. Any rollout outside this development database requires its own
inventory, backup, risk review, and authorization.

---

## Superseded checkpoint — 2026-10-20 — HT-WORK-P2-02

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `cb8e338`

Current task: **HT-WORK-P2-02 — IMPLEMENTATION COMPLETE — PENDING
DEVELOPMENT MIGRATION APPROVAL**

Read root `AGENTS.md` before any later action. Preserve every dirty file, the
development database, and the ignored HT-DB-P1-05 backup. Do not commit, push,
reset, rewrite migration history, apply `workspace.0003`, create development
business fixtures, or begin another roadmap feature without separate Owner
authorization.

### Resume classification

- `DONE before the latest token interruption`: approved schema-dependent code,
  additive migration `0003`, API/service integration, schema/API/concurrency
  tests, the full isolated PostgreSQL verification, and read-only development
  migration/inventory checks.
- `PARTIAL at interruption`: permanent documentation reconciliation. The API
  contract had just been updated; the remaining current-state documents and
  this handover still described the superseded schema approval gate.
- `DONE after resume`: all required current-state documentation reconciled with
  source/test/development evidence and the final dirty-tree checks rerun.
- `BLOCKED`: no source implementation blocker. Applying `workspace.0003` to
  development is intentionally blocked by the required Owner approval gate.

### Implementation now complete in source

- `Profile.status` supports only `ACTIVE` and `ARCHIVED`, defaults safely to
  `ACTIVE`, and has a database check plus lookup index. A current Profile Owner
  may archive/restore; Profile Admin cannot. Archived Profiles remain scoped
  and readable but block supported child and membership writes. Hard delete is
  not exposed.
- `Workspace.period` is a canonical first-of-month date. Supported new writes
  require it, later changes are rejected, and the database prevents more than
  one non-null `(profile, period)` even when the existing Workspace is archived.
  A Profile row lock and database uniqueness protect concurrent creation.
- `Workspace.status` supports `ACTIVE`/`ARCHIVED`. Profile Owner/Admin may
  archive/restore; Workspace Admin cannot. Archived Workspaces stay readable to
  callers with effective access but metadata and membership mutations fail
  closed until restore. Tenant hard delete is not exposed; existing
  platform/Admin destructive paths remain outside this task and require
  separate control.
- `WorkspaceMember.is_active` provides soft revoke. Revoke immediately removes
  effective access and roster visibility while retaining the row. Direct-add
  of the same eligible Profile member reactivates that same unique
  `(workspace, user)` row; no duplicate history row is created.
- Service boundaries lock in Profile → Workspace → membership order, recheck
  active tenant authority and role ceilings, and write lifecycle/revoke/
  reactivate AuditLog events in the same transaction. Audit failure rolls back
  the state change. Workspace Admin stays limited to `MEMBER`/`VIEWER`; legacy
  Workspace `OWNER` remains fail-closed.
- Read selectors remain tenant-scoped, include archived resources when the
  caller still has effective read access, and exclude inactive WorkspaceMember
  assignments immediately. Cross-Profile, wrong-parent, stale-context, and
  concurrent privilege-escalation paths stay fail-closed.
- Django Admin exposes lifecycle values for inspection but does not offer an
  unaudited status or WorkspaceMember activation toggle. A mapped/non-null
  monthly period is read-only.

### Schema and migration state

- New source migration:
  `workspace.0003_workspace_lifecycle_and_period`, dependent only on applied
  `workspace.0002_profile_workspace_foundation`.
- It additively adds `Profile.status`, `Workspace.period`, `Workspace.status`,
  and `WorkspaceMember.is_active`, their status/period checks, uniqueness, and
  lookup indexes. It does not edit `0001`/`0002`, delete a row, invent a tenant,
  or guess a monthly period.
- Existing rows gain `ACTIVE` status and active membership defaults. Existing
  pre-`0003` Workspaces retain `period=NULL` until an explicit verified mapping.
  `NULL` is a transitional direct-write boundary only: model/service/API paths
  reject a new Workspace without a period. Once a non-null period is assigned,
  supported model/API paths do not permit changing it.
- MigrationExecutor rehearsal from `0002` to `0003` on isolated PostgreSQL
  preserved Profile, Workspace, WorkspaceMember and the related
  `Task → Deliverable → Review` chain without synthesizing a period.

### API implemented in source

- Existing Profile/Workspace reads and Workspace create/update remain intact.
  Create now requires `period`; response objects expose lifecycle fields.
- New Profile actions:
  `POST /api/v1/profiles/{profile_id}/archive/` and `/restore/`.
- New Workspace actions:
  `POST /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/archive/` and
  `/restore/`.
- Nested member detail now accepts `DELETE` for soft revoke (`204`). A later
  collection `POST` reactivates the retained row (`200`); a new row returns
  `201`, while an already-active duplicate remains `409`.
- All unsafe routes retain SessionAuthentication and CSRF enforcement. No new
  `AllowAny`, authentication mechanism, frontend, or downstream domain was
  introduced.

### Verification actually run

- `python -m pip check`: PASS, no broken requirements.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- New lifecycle/concurrency service module: PASS, 7/7 in 6.872s.
- Entire Workspace PostgreSQL suite: PASS, 140/140 in 79.278s.
- Full PostgreSQL suite: PASS, 169/169 in 82.920s, including Authentication,
  Session/CSRF, deny-by-default, health, tenant/IDOR, lifecycle, concurrency,
  atomic audit rollback, last-active-Owner, and migration regressions.
- Django applied `workspace.0003` only inside the disposable `test_postgres`
  database and destroyed it after each run; the post-check found zero remaining
  test database.
- Development `showmigrations` shows `0001`/`0002` applied and `0003` unchecked.
  `migrate --plan` lists only the reviewed additive `0003` operations.
  `migrate --check` exits `1` as expected because `0003` is deliberately
  pending; that expected result is not reported as a failed consistency check.
- `git diff --check`: PASS after final source/documentation reconciliation;
  Git may emit only existing LF-to-CRLF conversion warnings.

### Development and production state

- The identified target remains the repository Compose PostgreSQL 16
  development container. A read-only process check on 2026-10-20 found that
  existing container stopped cleanly (`Exited (0)`); it was not restarted or
  altered in this documentation-only resume. Production was not contacted.
- Development has 27 migration rows: `workspace.0002` is applied and
  `workspace.0003` is not applied.
- Latest successful read-only database inventory, taken immediately after the
  full suite on 2026-10-19: 3 Users and zero Profile, ProfileMembership,
  Workspace, WorkspaceMember, Task, Client, Invoice, Payment, and AuditLog
  rows, with no remaining test database. No tenant, period, membership, or
  business fixture was synthesized.
- **IMPLEMENTED IN SOURCE:** yes.
- **TESTED IN ISOLATED POSTGRESQL:** yes.
- **APPLIED TO DEVELOPMENT:** no.
- **PRODUCTION TOUCHED:** no.

### Files changed in the current worktree

Backend implementation:

- `backend/apps/workspace/access.py`
- `backend/apps/workspace/admin.py`
- `backend/apps/workspace/models.py`
- `backend/apps/workspace/permissions.py`
- `backend/apps/workspace/serializers.py`
- `backend/apps/workspace/services.py`
- `backend/apps/workspace/urls.py`
- `backend/apps/workspace/views.py`
- `backend/apps/workspace/migrations/0003_workspace_lifecycle_and_period.py`

Tests:

- `backend/apps/workspace/test_api.py`
- `backend/apps/workspace/test_write_api.py`
- `backend/apps/workspace/tests.py`
- `backend/apps/workspace/test_schema_lifecycle.py`
- `backend/apps/workspace/test_lifecycle_services.py`

Current-state documentation:

- `documentation/API_DOCUMENTATION.md`
- `documentation/CHANGELOG.md`
- `documentation/DATABASE_SCHEMA.md`
- `documentation/DECISION_LOG.md`
- `documentation/HANDOVER.md`
- `documentation/PROGRESS.md`
- `documentation/PROJECT_CONTEXT.md`
- `documentation/PROJECT_ROADMAP.md`
- `documentation/RBAC_DESIGN.md`
- `documentation/REQUIREMENT_STATUS.md`

No file was reset, reverted, deleted, committed, or pushed.

### Exact safe continuation / review gate

Stop at the **OWNER REVIEW GATE**. Review the source diff, additive `0003`, API
contract, isolated migration rehearsal, 140-test Workspace run, and 169-test
full regression. Do not begin Invitation, Client, Project, Task/Review,
Finance, or frontend work.

If the Owner approves development rollout, open a separately controlled
migration task: repeat development identity/inventory, verify the existing
backup policy (and create a fresh pre-apply backup if required), review
`migrate --plan`, apply exactly `workspace.0003` to development, then verify
constraints, inventory, API smoke, and the full regression suite. Do not apply
it from this checkpoint.

---

## Superseded checkpoint — 2026-10-19 — HT-WORK-P2-02 schema approval gate

Historical only: the schema-free slice and schema approval gate below were
superseded after the Owner approved and Codex implemented the schema-dependent
requirements. Do not follow its continuation instruction as current work.

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `b8f1767`

Current task: `HT-WORK-P2-02 — IN PROGRESS / SCHEMA APPROVAL GATE`

Read root `AGENTS.md` before taking any later action. Preserve every dirty
file, the migrated development database, and the verified HT-DB-P1-05 backup.
Do not commit, push, reset, alter migration history, create/apply a new
migration, write development business fixtures, or begin another roadmap task.

Owner accepted `HT-DB-P1-05` and explicitly opened the limited Workspace Write
API and Membership Management task. The schema-free portion is implemented and
fully verified. The task is not `COMPLETE`, because the remaining lifecycle,
monthly-period, and membership-history requirements need an approved additive
schema and business contract.

### Completed implementation

- `POST /api/v1/profiles/{profile_id}/workspaces/` creates a Workspace for a
  Profile Owner/Admin. Profile and legacy owner fields are server-owned; the
  request cannot impersonate an owner or re-parent the Workspace.
- `PATCH /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/` changes only
  `name` and `description`. Profile Owner/Admin and the assigned Workspace
  Admin may perform this action; Editor/Viewer and an unassigned Profile Member
  are denied.
- `GET`/`POST` on the nested Workspace member collection list the effective
  roster and direct-add an active User who already has an active membership in
  the same Profile. `PATCH` on the nested member detail changes the Workspace
  role.
- Profile Owner/Admin may manage `ADMIN`, `MEMBER` (Editor), and `VIEWER`.
  Workspace Admin may manage only `MEMBER` and `VIEWER`. The legacy Workspace
  `OWNER` role fails closed and cannot be assigned or changed through this API.
- Strict input serializers reject unknown and server-owned fields. Member
  output exposes the ProfileMembership reference and assignment metadata, but
  no global User ID, username, email, or other User PII.
- Tenant path and target resolution remain scoped. The implemented mappings are
  invalid input `400`, insufficient capability `403`, unknown/wrong-parent/
  cross-tenant resource `404`, and duplicate direct-add `409`.
- Create, update, direct-add, and role-update run in locked transactions with
  AuditLog writes in the same transaction. Audit failure rolls the state change
  back.
- The final roster hardening binds the queryset to the requesting actor's
  current Profile/Workspace authority in SQL. It also rechecks that roster
  targets still have an active same-Profile membership. A manager role revoked
  after permission resolution but before lazy queryset evaluation therefore
  fails closed instead of returning a late, stale roster.

### Explicitly blocked remainder

- Workspace archive/restore is not exposed. `Workspace` has no lifecycle field,
  so archive state, default visibility, child-write behavior, restore rules,
  and actor ceiling cannot be implemented without inventing policy.
- The approved architectural description says Workspace is monthly, but the
  current model has no month/period field or approved uniqueness semantics.
- WorkspaceMember revoke/deactivate is not exposed. The model has no active or
  history field, and deactivate/rejoin/history semantics are not approved.
- Profile itself has no active/lifecycle field. Tenant lifecycle behavior must
  be decided before relying on such a state in access enforcement.
- `DELETE` remains `405 Method Not Allowed`; there is no hard-delete shortcut.

No model changed and no migration was created or applied in HT-WORK-P2-02.
Development remains at `workspace.0002_profile_workspace_foundation`; there is
no `workspace.0003`.

### Development database evidence

- Read-only verification identified the existing loopback-bound Compose
  PostgreSQL 16.14 development service. Production was not contacted.
- `django_migrations` contains 27 rows and
  `workspace.0002_profile_workspace_foundation` is applied.
- Inventory remains 3 Users and 0 Profile, ProfileMembership, Workspace,
  WorkspaceMember, Task, Client, Invoice, Payment, and AuditLog rows. No
  business fixture or tenant mapping was created, and the final read-only
  check found no `test_%` database left behind.
- There is no `workspace.0003`. HT-WORK-P2-02 performed no development schema
  or data write.

### Verification actually run

- `python -m pip check`: PASS, no broken requirements.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- `python manage.py migrate --check`: PASS.
- Workspace service/read/write/API tests: PASS, 111/111 in 62.011s.
- Authentication/API Foundation regressions (`api apps.accounts`): PASS,
  29/29 in 7.295s.
- Full PostgreSQL suite: PASS, 140/140 in 69.873s.
- The isolated Django test database was destroyed after each test run.
- `git diff --check`: PASS; Git reports only existing LF-to-CRLF conversion
  warnings for several dirty files.

These results include permissions, tenant and wrong-parent isolation, strict
inputs, duplicate handling, CSRF and anonymous denial, role ceilings,
transaction/audit rollback, existing last-active Profile Owner invariants, and
the late-revocation roster regression. They do not constitute approval for a
new schema or for the blocked endpoints.

### Files changed in the current worktree

HT-WORK-P2-02 backend implementation and tests:

- `backend/apps/workspace/access.py`
- `backend/apps/workspace/permissions.py`
- `backend/apps/workspace/serializers.py`
- `backend/apps/workspace/services.py`
- `backend/apps/workspace/urls.py`
- `backend/apps/workspace/views.py`
- `backend/apps/workspace/test_api.py`
- `backend/apps/workspace/test_write_api.py` (new)
- `backend/apps/workspace/tests.py`

Current-state documentation:

- `documentation/API_DOCUMENTATION.md`
- `documentation/CHANGELOG.md`
- `documentation/DATABASE_SCHEMA.md`
- `documentation/DECISION_LOG.md`
- `documentation/HANDOVER.md`
- `documentation/PROGRESS.md`
- `documentation/PROJECT_CONTEXT.md`
- `documentation/PROJECT_ROADMAP.md`
- `documentation/RBAC_DESIGN.md`
- `documentation/REQUIREMENT_STATUS.md`

The pre-existing `.gitignore` change and ignored HT-DB-P1-05 backup remain
preserved. No file was reset, deleted, committed, or pushed.

### Exact continuation / Owner decision required

Stop at `SCHEMA APPROVAL GATE`. Do not start a new task. Owner must approve the
small additive schema and exact contract for all of the following before any
further implementation:

1. Profile active/lifecycle representation and its access effects.
2. Workspace month/period representation and uniqueness rules.
3. Workspace archive/restore state, default visibility, child-write behavior,
   restore rules, and authorized actors.
4. WorkspaceMember revoke/deactivate representation, history retention,
   rejoin semantics, and authorized actors.

After that approval, the safe next step is a separately reviewed additive
migration/backfill plan and test plan. Do not create or apply that migration to
development from this checkpoint. Invitation, Profile Write API, downstream
business domains, and frontend remain out of scope.

---

## Superseded checkpoint — 2026-10-19 — HT-DB-P1-05

Historical only: HT-DB-P1-05 was accepted by the Owner before HT-WORK-P2-02
opened. Its evidence remains below for traceability, but its continuation
instruction is superseded by the current checkpoint above.

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `b8f1767`

Current task: `HT-DB-P1-05 — COMPLETE / OWNER REVIEW GATE`

Read root `AGENTS.md` before taking any later action. Preserve the verified
backup, development database, and all dirty files. Do not commit, push, reset,
recreate PostgreSQL, create business fixtures, or begin Workspace Write,
Membership, Invitation, or frontend work without separate Owner authorization.

### Resume classification and environment

- `ALREADY DONE` before the final resume: repository/source/config audit,
  development database identity and pre-migration inventory, additive
  migration review, verified pre-migration backup, target-specific migration
  plan, safe development apply, post-migration schema/integrity checks, and
  direct HTTP smoke were complete. None was repeated destructively.
- `IN PROGRESS` at the recovered checkpoint: regression evidence and permanent
  documentation. These are now complete.
- `NOT DONE` by design: development business fixtures and a successful login
  using an existing development account. Development has no Profile/Workspace
  rows and no account credential was requested, reset, or invented; successful
  SessionAuthentication, tenant detail, cross-tenant, and IDOR paths were
  verified in Django's isolated PostgreSQL test database instead.
- `BLOCKED`: none inside HT-DB-P1-05. The task stops at Owner review by scope.
- Root/backend `.env` remains absent and was not required or created. Django
  settings do not auto-load `.env`. Commands used a development-only
  cryptographically random Django key in process memory and the existing
  PostgreSQL container runtime values, passed to disposable Python containers
  without logging or persisting secret values.
- The Owner-reported host PowerShell check returned Python 3.12.5 and a clean
  `pip check`, but the live check from Codex's managed execution context exits
  `103` and reports the referenced base interpreter path unavailable. This
  environment-visibility discrepancy was not treated as a Django/database
  failure and the venv was not modified. The approved cached
  `python:3.12-slim` fallback was used; source was mounted read-only and pinned
  requirements passed `pip check`.

### Development target, backup, and restore rehearsal

- The only target changed was the existing local Compose development service
  `hustlytasker_postgres` (PostgreSQL 16.14), loopback-bound on port 5432,
  database `hustlytasker_db`, named volume `docker_postgres_data`. Compose
  labels point to this repository. Production was not contacted and no
  PostgreSQL container or volume was recreated.
- Before apply: 26 migration rows; `workspace.0001_initial` applied;
  `workspace.0002_profile_workspace_foundation` unapplied; Profile tables and
  `workspace_workspace.profile_id` absent. Inventory was 3 active Users and 0
  Workspace, WorkspaceMember, Task, Client, Invoice, Payment, or AuditLog rows,
  with no checked orphan, unvalidated FK, or tenant mapping to infer.
- Backup artifact (Git ignored):
  `.local_backups/HT-DB-P1-05/hustlytasker_dev_pre_workspace_0002_20261018T185438Z.dump`.
  It is a 66,721-byte PostgreSQL custom archive. SHA-256 is
  `118533290c6179e63d71b7abc7b591c0882012b91c0c0e810c1d27e3965c020e`;
  host/container hashes match. `pg_restore --list` and a complete archive read
  to `/dev/null` passed.
- A full restore rehearsal also passed in a uniquely named isolated temporary
  database: 26 migrations, `workspace.0002` absent, 3 Users, 0 Workspaces, and
  the expected pre-migration schema. The exact rehearsal database was dropped;
  final checks found zero `htdb_p105_restore_%` databases.

### Migration applied and post-checked

- `python manage.py check`: PASS before apply.
- Exact plan for `workspace.0002_profile_workspace_foundation`: create
  `Profile`, create `ProfileMembership`, add nullable `Workspace.profile`, and
  alter `Workspace.owner` to the reviewed protected relationship. It matched
  the unchanged additive source and contained no data backfill or destructive
  operation.
- Applied exactly
  `python manage.py migrate workspace 0002_profile_workspace_foundation --noinput`
  on the development database: PASS (`OK`). No `--fake`, rollback, reset, or
  old-migration edit was used.
- Final state: 27 migration rows and `workspace.0002` applied. Tables
  `workspace_profile` and `workspace_profilemembership`, nullable
  `workspace_workspace.profile_id`, reviewed FKs/check/partial-unique
  constraints, and lookup indexes all exist and validate.
- Post-apply inventory remains 3 Users and zero Profile, ProfileMembership,
  Workspace, WorkspaceMember, Task, Client, Invoice, Payment, or AuditLog rows.
  There are zero unmapped Workspaces, orphan Workspace/Profile references, and
  unvalidated constraints. No tenant/backfill row was synthesized.

### Direct development HTTP smoke

- A disposable Django server started successfully against the migrated
  development database; its source mount was read-only and it was removed
  after the smoke.
- `GET /api/health/`: `200`, body status `ok`, non-cacheable response.
- Anonymous requests to all four `/api/v1/` Profile/Workspace routes: `403`;
  none returned `500`. Anonymous `GET /api/auth/me/`: `403`.
- `GET /api/auth/csrf/`: `200` with CSRF cookie. Invalid login without the
  token: `403`; the same neutral invalid credential request with the token:
  `400`. No token, cookie, password, or secret was recorded.
- `django_session` count was `1` before and after smoke. No development
  Profile/Workspace fixture or account/session data was created.

### Verification actually run

- `python -m pip check`: PASS, no broken requirements.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- `python manage.py migrate --check`: PASS.
- `showmigrations workspace --plan`: `0001` and `0002` both applied.
- Targeted `apps.workspace.test_api`: PASS, 21/21 in 0.692s.
- Authentication/API Foundation (`api apps.accounts`): PASS, 29/29 in 7.200s.
- Full PostgreSQL suite: PASS, 101/101 in 55.762s. Every Django test database
  was destroyed.
- Final read-only database check: migration/data/session counts unchanged from
  the intended post-apply state; zero `test_%` and restore-rehearsal databases.
- `git diff --check`: PASS after documentation reconciliation; Git may report
  only existing LF-to-CRLF conversion warnings.

### Files and artifacts changed

- `.gitignore` — excludes `/.local_backups/`.
- Ignored local backup artifact listed above.
- Current-state documentation: `HANDOVER.md`, `PROGRESS.md`,
  `PROJECT_ROADMAP.md`, `CHANGELOG.md`, `REQUIREMENT_STATUS.md`,
  `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md`, `PROJECT_CONTEXT.md`,
  `DECISION_LOG.md`, and `RBAC_DESIGN.md`.

No backend source, model, migration, API contract, authentication setting, or
business row was changed in HT-DB-P1-05. The only application-database schema
change was the already-reviewed existing `workspace.0002` migration on the
approved development target.

### Exact continuation

Stop at `OWNER REVIEW GATE`. Review the backup/rehearsal, migration state,
direct smoke, 101-test evidence, and documentation diff. The roadmap candidate
after approval is `HT-WORK-P2-02`, but its exact Workspace write/membership
slice must be separately authorized; Invitation remains gated by its account/
email-binding dependency. Do not implement either automatically.

---

## Superseded checkpoint — 2026-10-19 — HT-DB-P1-05 pre-migration blocker

Historical only: every status, blocker, instruction, and continuation step in
this block is superseded by the completed checkpoint above.

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `b8f1767`

Current task: `HT-DB-P1-05 — BLOCKED BEFORE MIGRATION / OWNER ACTION REQUIRED`

Read root `AGENTS.md` before taking action. Preserve the verified backup and
all dirty files. Do not commit, push, reset, recreate PostgreSQL, restore over
development, synthesize a Django secret, or start another roadmap task.

### Checkpoint recovered and verified

- `HT-API-P1-04` is committed at `b8f1767`; the worktree was clean when this
  operational task began. Its four read endpoints and 101-test historical
  evidence were not reimplemented.
- The only PostgreSQL container is the existing repository Compose service
  `hustlytasker_postgres` (`postgres:16`), bound to `127.0.0.1:5432`, with the
  existing `docker_postgres_data` named volume. Compose labels point to
  `D:\da\HustlyTasker\docker\docker-compose.yml`. No container, database, or
  volume was created, replaced, reset, or deleted.
- Read-only SQL identified `hustlytasker_db` owned/used by
  `hustlytasker_user`, PostgreSQL 16.14, database size 9,149,463 bytes. The
  local Compose identity, loopback binding, project path, and named volume are
  the evidence that this is the approved development target; production was
  not contacted.
- `django_migrations` has 26 rows. `workspace.0001_initial` and the swappable
  User dependency are applied; `workspace.0002_profile_workspace_foundation`
  is not applied. `workspace_profile`, `workspace_profilemembership`, and
  `workspace_workspace.profile_id` remain absent.
- Pre-migration inventory: 3 Users, all active; 0 Workspace,
  WorkspaceMember, Task, Client, Invoice, Payment, and AuditLog rows. Profile
  and ProfileMembership counts are `TABLE ABSENT`, not zero. Orphan checks for
  Workspace owner, WorkspaceMember workspace/user, and Task workspace/creator
  returned zero; no unvalidated foreign key or leftover test database exists.
- Static review confirms existing migration `0002` is unchanged and additive:
  it creates Profile/ProfileMembership with approved indexes/constraints,
  adds nullable `Workspace.profile`, and changes `Workspace.owner` to
  `PROTECT`. It contains no `RunPython`, backfill, delete, drop, rename, or
  guessed tenant mapping. With zero Workspace rows, no mapping is required.

### Backup completed and verified

- Relative artifact:
  `.local_backups/HT-DB-P1-05/hustlytasker_dev_pre_workspace_0002_20261018T185438Z.dump`.
  The UTC filename corresponds to 2026-10-19 local time. The directory is now
  excluded by root `.gitignore`; the archive is intentionally not tracked.
- Format: PostgreSQL 16.14 custom archive; size: 66,721 bytes; source database
  metadata: `hustlytasker_db`.
- SHA-256:
  `118533290c6179e63d71b7abc7b591c0882012b91c0c0e810c1d27e3965c020e`.
  Host and container hashes match.
- `pg_restore --list` succeeded and exposed the expected migration, User, and
  Workspace schema/data entries. Streaming the entire archive through
  `pg_restore --file=/dev/null` also exited 0 without connecting to a target
  database. This verifies archive readability, not a restore rehearsal.
- The archive requires a separately created empty target database for any
  future rehearsal. Never restore it over development automatically.

### Blocking condition before plan/apply

- Root/backend `.env` files are absent. Required runtime variables are not
  loaded at Process/User/Machine scope, including a legitimate development
  `DJANGO_SECRET_KEY`; Django settings do not load `.env` automatically.
- The PostgreSQL container holds only its database variables and is not a
  source for the missing Django secret. Extracting or inventing credentials is
  prohibited.
- Host `python`, `python3`, and `py` are unavailable. The old
  `backend/venv` launcher points to a removed Python 3.12.5 installation and
  exits 103. A cached `python:3.12-slim` image exists, but it cannot make an
  unapproved secret/configuration legitimate.
- Therefore `manage.py migrate --plan`, the apply, Django system/migration
  checks, live application smoke, targeted regressions, and the full suite
  were not run in this checkpoint. `workspace.0002` remains unapplied and the
  development schema/data remain unchanged. Historical 101/101 results are
  not relabeled as current-task evidence.

### Verification actually run

- Independent Git/source/migration review and two read-only database
  inventories: PASS. The final inventory used an explicit read-only
  transaction and reconfirmed 3 Users, zero checked business rows, `0002`
  unapplied, and all three target schema objects absent.
- Backup hash comparison, `pg_restore --list`, and full archive read to
  `/dev/null`: PASS.
- `git diff --check`: PASS; Git reports only existing LF-to-CRLF conversion
  warnings. Strict UTF-8/no-BOM/no-NUL validation passes for every changed
  text file.
- Django check, migration consistency command, API smoke, targeted tests,
  Authentication/API regressions, and full PostgreSQL suite: **NOT RUN** due
  to the blocking environment condition above.

### Files and artifacts changed in this checkpoint

- `.gitignore` — ignores `/.local_backups/` so operational dumps cannot be
  committed accidentally.
- `.local_backups/HT-DB-P1-05/...dump` — verified local backup, ignored by Git.
- Current-state documentation: `HANDOVER.md`, `PROGRESS.md`,
  `PROJECT_ROADMAP.md`, `CHANGELOG.md`, `REQUIREMENT_STATUS.md`,
  `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md`, `PROJECT_CONTEXT.md`,
  `DECISION_LOG.md`, and `RBAC_DESIGN.md`.

No backend code, model, migration, authentication setting, API contract, or
database row/schema was changed.

### Exact safe continuation

Owner action is required: restore the legitimate ignored development `.env`
or load the approved development variables into the process, especially the
existing/approved `DJANGO_SECRET_KEY`. Do not paste secrets into chat, source,
logs, or documentation, and do not extract/reset PostgreSQL credentials.

After that configuration is available:

1. Reconfirm `DJANGO_ENVIRONMENT=development`, the same local Compose target,
   migration state, counts, archive presence/hash, and absence of anomalies.
2. Use the existing approved Python-container mechanism without recreating
   PostgreSQL. Run `migrate --plan` for exactly
   `workspace.0002_profile_workspace_foundation` and review the plan.
3. Only if the plan still matches the additive source, apply exactly that
   migration. Do not auto-rollback or use `--fake` if it fails.
4. Verify migration history, new tables/column/indexes/constraints, counts,
   relationships, and migration consistency.
5. Smoke health and anonymous denial directly on development without creating
   business fixtures. Because development has no Profile/Workspace and no
   approved session credentials, verify authenticated/session/CSRF/detail,
   tenant isolation, and IDOR behavior in Django's isolated PostgreSQL test
   database.
6. Run system check, migration drift check, targeted API tests,
   Authentication/API Foundation regressions, the full PostgreSQL suite, and
   `git diff --check`; then update this checkpoint with actual results.

Do not mark `HT-DB-P1-05` complete until every acceptance condition above has
current evidence. Stop at `OWNER REVIEW / CONFIGURATION GATE`; do not begin
Workspace Write, Membership, Invitation, or any other task.

---

## Superseded checkpoint — 2026-10-18 — HT-API-P1-04 (historical only)

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `eb76395`

Current task: `HT-API-P1-04 — COMPLETE / OWNER REVIEW GATE`

Read root `AGENTS.md` before taking action. Source, migrations, Git status and
current test output override historical notes. Do not commit, push, reset,
revert, clean, apply migrations or alter development data without owner
authorization.

### What was already complete before this resumed checkpoint

- `HT-RBAC-P1-03` supplied verified Profile/Workspace access contexts,
  tenant-scoped selectors, capability revalidation and scoped membership
  services. The owner authorized using that foundation for this read API task.
- Before the interruption, the complete P1-04 code and 20 API tests were already
  present. Independent review found a late membership-revocation race; it had
  already been fixed by mapping stale access during queryset evaluation to the
  same generic DRF `404` and adding an exact regression.
- Final code/test verification had already passed. The interrupted work was the
  required documentation and handover reconciliation, which this checkpoint
  completes without rewriting the valid implementation.
- Final documentation review then found that unsupported unsafe methods can be
  rejected by session CSRF before DRF reaches method dispatch. One focused API
  regression was added; the read implementation itself did not change.

### Implementation completed

- Added `/api/v1/` routing for exactly four read-only endpoints:
  - `GET /api/v1/profiles/`
  - `GET /api/v1/profiles/{profile_id}/`
  - `GET /api/v1/profiles/{profile_id}/workspaces/`
  - `GET /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/`
- Added minimal Profile and Workspace read serializers. They expose only the
  identifiers, names/descriptions and timestamps documented in
  `API_DOCUMENTATION.md`; no owner, membership, role, email, or PII is exposed.
- Added explicit DRF tenant permissions for a current active identity, active
  Profile access and effective Workspace read access. SessionAuthentication and
  global deny-by-default remain unchanged; no new `AllowAny` exists.
- Lists and lookups use only `profiles_visible_to()` and
  `workspaces_visible_to()`. Owner/Admin inheritance is same-Profile only;
  ordinary Members require an effective explicit `ADMIN`, `MEMBER` or `VIEWER`
  Workspace role. Legacy `OWNER`, transitional owner, Profile-null rows and
  staff/superuser flags fail closed.
- Malformed, random, cross-tenant, wrong-parent and otherwise out-of-scope IDs
  share `404 {"detail":"Not found."}`. Pagination is page-number based,
  default 20/max 100, with fixed `created_at`/`id` ordering.
- Views support only `GET`, `HEAD` and `OPTIONS` and are non-cacheable. Unsafe
  requests run auth/CSRF and tenant permissions first (`403`/`404` on failure);
  an authorized request with valid CSRF then receives `405` for unsupported
  methods. No branch implements a Profile/Workspace write, membership
  management or Invitation.

No endpoint approved for this read-only task remains missing.

### Files changed in the current worktree

Backend:

- `backend/api/urls.py`
- `backend/api/pagination.py` — new
- `backend/apps/workspace/views.py`
- `backend/apps/workspace/permissions.py` — new
- `backend/apps/workspace/serializers.py` — new
- `backend/apps/workspace/urls.py` — new
- `backend/apps/workspace/test_api.py` — new

Documentation:

- `documentation/API_DOCUMENTATION.md`
- `documentation/CHANGELOG.md`
- `documentation/DATABASE_SCHEMA.md` — runtime status wording only; no schema
  design or migration changed
- `documentation/DECISION_LOG.md` — clarified P1-03/P1-04 chronology only; no
  accepted decision changed
- `documentation/HANDOVER.md`
- `documentation/PROGRESS.md`
- `documentation/PROJECT_CONTEXT.md`
- `documentation/PROJECT_ROADMAP.md`
- `documentation/RBAC_DESIGN.md`
- `documentation/REQUIREMENT_STATUS.md`

No model, migration, settings, authentication, `access.py`, `services.py`,
Docker, dependency or development-data file changed in this task.

### Verification actually run

All Django tests below used Django-created disposable PostgreSQL databases; no
SQLite fallback or development migration was used. At resumed verification the
workspace had no `.env` and its old Windows virtualenv pointed to a removed
Python install, so the final run used the already-cached `python:3.12-slim`
image, installed the pinned manifest inside an ephemeral container, and mounted
the repository read-only. The existing PostgreSQL container was not recreated.
The initial local verification attempt therefore did not start Django tests;
only the successful isolated runs below are reported as test evidence.

- Targeted `apps.workspace.test_api`: PASS, 21/21 in 0.747s, including the new
  session-CSRF-before-`405` case.
- Authentication/API Foundation regression run (`api apps.accounts`): PASS,
  29/29, including existing session and CSRF policy coverage.
- Final full PostgreSQL suite after every code/test change: PASS, 101/101 in
  55.129s. This includes 72 Workspace, 19 Authentication and 10 API Foundation
  tests; Django destroyed the test database.
- `python -m pip check`: PASS.
- In-memory Python syntax compile for all new/modified code and tests: PASS.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- `python manage.py showmigrations workspace --plan`: development state remains
  `0001` applied and `0002` unapplied.
- Read-only PostgreSQL check after tests: zero leftover `test_%` databases.
- `git diff --check`: PASS, with only Git's existing LF-to-CRLF conversion
  warnings. Strict UTF-8/no-BOM/no-NUL, balanced-code-fence,
  trailing-whitespace and secret-assignment QA: PASS for all 17 changed/new
  source and documentation files.
- Independent code and test review found no blocking/high/medium issue. Optional
  non-blocking future assertions are page-size cap/default, explicit no-store
  header, and an additional cross-tenant Workspace-list parity case.

### Migration and data state

- Source still contains the unchanged additive
  `workspace/0002_profile_workspace_foundation.py`.
- Development PostgreSQL still has only `workspace.0001_initial` applied;
  `workspace.0002` is intentionally unapplied and Profile tables are absent.
- Final read-only inventory confirms 3 User rows, 0 Workspace rows, no Profile
  table and no leftover test database. Only the pre-existing PostgreSQL
  container remains running; every Python test container was removed. No
  development row/schema/container/volume was created, modified, deleted,
  reset, backfilled or migrated by P1-04.
- The API implementation is complete and verified on isolated PostgreSQL test
  databases, but cannot be runtime-smoked against development before the
  separately approved `0002` operational rollout.

### Remaining boundaries and exact continuation

- Direct ORM/bulk/raw/Admin bypasses, global User-deactivation/session purge,
  Workspace writes/membership lifecycle, Invitation, and all downstream
  Client/Project/Task/Review/Finance APIs remain outside this task.
- There is no implementation blocker inside the approved P1-04 scope. The
  active gate is Owner review of the API contract, diff and 101-test evidence.
- Do not apply `workspace.0002` automatically. If the owner separately
  authorizes a development rollout, first repeat read-only inventory, take the
  required backup, apply only the existing migration, then smoke all four
  endpoints and record the result.
- Do not begin Workspace write/membership or Invitation work automatically.
  After review and any operational migration approval, the next implementation
  task must be separately scoped; Invitation still depends on account/email
  verification.

Stop at `OWNER REVIEW GATE`.

---

## Superseded checkpoint — 2026-10-18 — HT-RBAC-P1-03 (historical only)

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `5e89971`

Current task: `HT-RBAC-P1-03 — COMPLETE / OWNER REVIEW GATE`

Read root `AGENTS.md` before taking action. Source, migrations, Git status and
current test output override historical notes. Do not commit, push, reset,
revert, clean, apply migrations or alter development data without owner
authorization.

### What was completed

- `HT-RBAC-DESIGN-P0-01` is `COMPLETE / ACCEPTED — APPROVED BY OWNER
  DELEGATION`. `RBAC_DESIGN.md` and `DECISION_LOG.md` record all 14 delegated
  decisions; do not ask the owner to decide them again.
- Added `backend/apps/workspace/access.py`:
  - resolver-produced immutable ID-only Profile/Workspace contexts;
  - active-User and active-ProfileMembership verification;
  - tenant-scoped Profile and Workspace selectors;
  - Profile Owner/Admin same-Profile Workspace inheritance;
  - ordinary Profile Member access only with explicit effective
    WorkspaceMember;
  - DB-revalidated read/edit/member-management capabilities;
  - generic `TenantAccessNotFound` for unknown/out-of-scope/malformed tenant
    identifiers;
  - fail-closed handling for direct construction, `dataclasses.replace()`,
    inactive/stale membership and stale Workspace role.
- Kept the existing WorkspaceMember schema vocabulary:
  - `ADMIN` = Workspace Admin;
  - `MEMBER` = Editor;
  - `VIEWER` = read-only Viewer;
  - legacy `OWNER` grants no capability through this boundary and is never
    assigned by the scoped service.
- Refactored `update_profile_membership()`:
  - signature now requires `profile_id`;
  - actor/Profile authorization precedes target lookup;
  - target is filtered inside the verified Profile;
  - Profile Admin may manage a current ordinary Member only and cannot grant
    or modify Admin/Owner;
  - Profile-first locking, last-active-owner, transitional Workspace-owner
    guard and atomic AuditLog behavior remain.
- Refactored `add_workspace_member()`:
  - signature requires `profile_id`, `workspace_id` and
    `target_profile_membership_id`; it no longer accepts a globally resolved
    User;
  - actor, Workspace, target ProfileMembership and active User are verified in
    the same Profile and rechecked under locks;
  - Profile Owner/Admin may grant `ADMIN`, `MEMBER` or `VIEWER`;
  - Workspace Admin may grant only `MEMBER` or `VIEWER` in its own Workspace;
  - Editor/Viewer cannot manage membership; no actor may grant legacy `OWNER`;
  - sequential/concurrent duplicates raise `WorkspaceMembershipConflict` and
    successful mutation writes exactly one audit event.
- Expanded Workspace tests for contexts, tenant isolation, IDOR-equivalent
  failures, stale/forged contexts, role ceilings, denied-audit behavior,
  last-owner protection and duplicate concurrency.
- Independent review found one medium context-forgery issue involving
  `dataclasses.replace()`. It was fixed with non-init provenance plus exact DB
  revalidation, regression tests were added, and follow-up review found no
  blocking/high/medium issue.

### Files changed in the worktree

Backend:

- `backend/apps/workspace/access.py` — new, untracked until the owner chooses to
  commit.
- `backend/apps/workspace/services.py`
- `backend/apps/workspace/tests.py`

Documentation:

- `documentation/CHANGELOG.md`
- `documentation/DATABASE_SCHEMA.md`
- `documentation/DECISION_LOG.md`
- `documentation/HANDOVER.md`
- `documentation/PROGRESS.md`
- `documentation/PROJECT_CONTEXT.md`
- `documentation/PROJECT_ROADMAP.md`
- `documentation/RBAC_DESIGN.md`
- `documentation/REQUIREMENT_STATUS.md`

`API_DOCUMENTATION.md` is unchanged because no HTTP route or API contract was
added. No model or migration file changed.

### Verification actually run

Environment:

- Existing PostgreSQL 16 container `hustlytasker_postgres`; no container was
  created, replaced, stopped or reset.
- Existing local Python 3.12.5 virtualenv synchronized to pinned Django 6.1.2
  and DRF 3.18.3; no requirement file changed.

Final acceptance evidence after the independent-review fix:

- `python -m pip check`: PASS.
- Version assertion: Django 6.1.2 / DRF 3.18.3: PASS.
- Python compile for access/services/tests: PASS.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- `python manage.py test apps.workspace --noinput -v 1`: PASS, 51/51.
- `python manage.py test --noinput -v 1`: PASS, 80/80. This includes all 19
  Authentication and 10 API Foundation regressions.
- `git diff --check`: PASS (only existing LF-to-CRLF conversion warnings).
- Strict UTF-8/no-NUL/code-fence QA and secret-assignment scan: PASS for all
  changed code/documentation files.

Pre-fix diagnostic runs also passed 49/49 targeted and 78/78 full. They are
historical within this task and are not the final acceptance evidence.

Django created and destroyed only disposable `test_hustlytasker_db` databases.
It did not migrate the development database.

### Migration and data state

- Source still contains additive
  `workspace/0002_profile_workspace_foundation.py`; no migration was created or
  edited by HT-RBAC-P1-03.
- Read-only development PostgreSQL inventory on 2026-10-18 confirmed only
  `workspace.0001_initial` is applied. `workspace.0002` is unapplied.
- Development inventory: 3 User rows; 0 Workspace, WorkspaceMember, Task,
  Client, Invoice, Payment and AuditLog business rows. Profile tables do not
  exist in development because `0002` is unapplied.
- No development row was created, changed, deleted, reset or backfilled. The
  named volume was preserved.

### Security boundaries that still exist

- Direct ORM `.save()`/`.update()`, bulk operations, raw SQL and unsafe Django
  Admin paths can bypass the reviewed membership services. This task does not
  claim database-wide enforcement against privileged code.
- Django Admin remains a platform-operations surface. Tenant-wide business
  model access is for platform superusers only until tenant-scoped Admin exists.
- Direct `User.is_active` changes can bypass cross-Profile last-owner and
  session-revocation requirements. The approved account-deactivation service
  and established-session purge are not implemented.
- No Workspace/Profile API or DRF tenant permission class exists. The new
  exception is a service boundary that a future API must map without revealing
  object existence.
- No Invitation model/migration/service/API exists. Verified email/account
  binding is required before production Invitation; token hashing alone is not
  identity verification.
- No Client, Project, Finance, Audit, Task or Review tenant selector/API was
  added. Concrete Review role/states and the payroll trigger remain deferred.
- WorkspaceMember has no active flag and legacy membership/history semantics
  remain for later lifecycle work. Soft delete is not implemented.

### Blockers and exact continuation

There is no implementation blocker for the completed scope. The active gate is
owner review.

1. Review the three backend files, the delegated decisions and the 51/80-test
   evidence. Do not reopen the 14 accepted decisions unless the owner explicitly
   changes them.
2. Do not apply `workspace.0002` as part of this task. A future operational
   apply requires target-specific inventory, retention-appropriate backup and
   explicit authorization even though current development has no business rows.
3. Do not open Workspace or Invitation APIs in this worktree yet.
4. After owner approval, define a separately authorized next task. The expected
   next implementation slice is minimal Profile/Workspace read/API permission
   integration using this foundation, scheduled with the account-verification
   dependency; Invitation remains later.

Stop at `OWNER REVIEW GATE`. Do not start the next task automatically.

---

## Superseded checkpoint — 2026-10-17 (historical only)

Checkpoint: 2026-10-17

Repository: `D:\da\HustlyTasker`

Branch: `main`

HEAD and local `origin/main`: `5e89971`
Current task: `HT-RBAC-DESIGN-P0-01 — DESIGN READY / OWNER REVIEW GATE`

This historical checkpoint is retained only for traceability. Continue from
the current checkpoint above.
Read root `AGENTS.md` before taking action. Source code, migrations, Git status,
and current test results override any stale historical note.

## 1. Project and stack

HustlyTasker is a backend-first workflow system for content-production teams
and agencies.

- Backend: Python 3.12, Django 6.1.2
- API: Django REST Framework 3.18.3
- Database: PostgreSQL 16
- ORM: Django ORM
- Local database workflow: Docker Compose with named volume
  `docker_postgres_data`
- Authentication foundation: Django server-side sessions, CSRF, DRF
  `SessionAuthentication`
- Default API access: DRF `IsAuthenticated`; public endpoints must explicitly
  use reviewed `AllowAny`
- Frontend: planned React/Next.js, no frontend source implemented

Do not replace this stack, start frontend, or introduce another framework
without explicit owner approval.

## 2. Current implementation status

### Backend implemented

- Modular Django apps for accounts, workspace, tasks, reviews, clients,
  finance, notifications, and audit.
- Fourteen concrete initial domain models and eight domain
  `0001_initial.py` migrations.
- Environment-based Django/PostgreSQL/security/mailer configuration and a safe
  `.env.example`.
- PostgreSQL Compose workflow preserving the named volume.
- Session authentication API:
  `/api/auth/csrf/`, `register/`, `login/`, `logout/`, and `me/`.
- DRF deny-by-default policy and reviewed public allowlist.
- Public JSON-only `/api/health/` liveness endpoint; legacy `/api/test/` is
  removed.
- Accepted Profile/Workspace architecture: Profile is the company/team tenant
  root; Workspace is the monthly operational scope; User remains global.
- `Profile` and `ProfileMembership` foundation with Profile roles, uniqueness,
  indexes, multi-owner/last-owner services and membership audit events.
- Transitional nullable `Workspace.profile`, protected Workspace owner
  deletion, and same-Profile validation for validated Workspace writes.
- Additive `workspace/0002_profile_workspace_foundation.py` in source; it has
  run only on disposable PostgreSQL test databases.
- Reviewable `documentation/RBAC_DESIGN.md` with the proposed capability
  matrix, tenant-scoped request/query/service boundary, Profile Invitation
  contract, planned routes, negative/concurrency tests, open decisions, and
  dependency-ordered implementation plan. It is not runtime behavior.

### Not implemented

- Applying Workspace `0002` to the development database
- Workspace lifecycle/invitation API
- Workspace/Profile RBAC and object-scoped querysets
- Owner approval of the seven residual RBAC groups covering Workspace roles,
  Profile Admin/lifecycle, Task visibility/contributor membership, account/
  membership lifecycle, Invitation identity/operations, and error/operator policy
- Project model/API
- Client/Profile, Workspace-scoped Invoice, public-link and soft-delete schema
  migrations
- Task, Review, Client, Finance, Notification, or Audit business APIs
- Account activation/OTP, password recovery, and logout-all
- Frontend
- Backend container image, production deployment, or CI pipeline

Most business app `views.py` files remain scaffolds. Workspace now has focused
foundation tests, but global DRF authentication still proves identity only; it
does not provide tenant authorization.

## 3. Completed tasks and verification evidence

| Task | Status | Evidence |
|---|---|---|
| HT-OPS-P0-01 dependency synchronization | COMPLETE | Clean Python 3.12 install, `pip check`, Django check, dependency versions verified on 2026-10-13. |
| HT-SEC-P0-02 environment hardening | COMPLETE | Development and production-like checks, fail-fast env cases, migration checks, PostgreSQL smoke on 2026-10-13. |
| HT-AUTH-P0-01 authentication foundation | COMPLETE | 19 authentication/session/CSRF/throttle/admin tests and API smoke passed on 2026-10-14. |
| HT-API-P0-03 DRF/health foundation | COMPLETE | Full suite 29/29 (19 auth + 10 API), checks, migration consistency, runserver health/auth smoke passed on 2026-10-15. The same suite and non-server checks passed again on 2026-10-16. |
| Permanent documentation/handover foundation | COMPLETE | Root `AGENTS.md` and this handover checkpoint created on 2026-10-16. |
| HT-DATA-P2-01 Workspace architecture design | COMPLETE / ACCEPTED | Source/reference audit, alternatives, ownership matrix, invariants and migration plan completed; owner approved all 11 decision groups on 2026-10-16. |
| PROFILE/WORKSPACE SCHEMA FOUNDATION | COMPLETE | Foundation implemented and verified: targeted Workspace tests 32/32 and full PostgreSQL suite 61/61 pass; `pip check`, system check and migration drift check pass. Owner authorized the subsequent design task; `0002` intentionally remains unapplied to development. |
| HT-RBAC-DESIGN-P0-01 capability/scoping/invitation design | DESIGN READY / OWNER REVIEW GATE | Full evidence-labeled design in `RBAC_DESIGN.md`; reconciled against all 11 approved groups (all now `MATCH`); seven residual review groups only; source/migration/database unchanged; current PostgreSQL migration/data state reconfirmed read-only on 2026-10-17. |

Latest foundation verification on 2026-10-17: targeted `apps.workspace` tests
passed 32/32 and the complete PostgreSQL suite passed 61/61. The full run
includes 19 Authentication and 10 API Foundation regression tests. `pip check`,
Django system check, and `makemigrations --check --dry-run` passed. See
`PROGRESS.md` for dated evidence.

For `HT-RBAC-DESIGN-P0-01` on 2026-10-17, the final reconciliation QA passed:
the 11-row table and seven open-group structure are present; all nine affected
files pass strict UTF-8/no-NUL/code-fence and secret-pattern checks; and
`git diff --check` passes with only line-ending conversion warnings. No backend
code changed, so the 32/32 and 61/61 results above were not relabeled as a new
run. The local venv references a missing Python 3.12 installation and no
`py`/`python` exists on PATH; no replacement environment or new container was
created for this design-only checkpoint.

## 4. Active task checkpoint

`HT-RBAC-DESIGN-P0-01` has all requested design deliverables and is
`DESIGN READY — PENDING OWNER APPROVAL`. Stop here; this status is not approval
to implement RBAC, Workspace, Invitation, or another business API.

Work completed:

- Re-read requirements, accepted decisions, current models/services/admin,
  migrations, API routing/settings/tests, and relevant legacy discovery. The
  design marks each rule as requirement, approved, current, proposed, or open.
- Added `documentation/RBAC_DESIGN.md` with a full Profile/Workspace capability
  matrix. It preserves approved Owner/Admin inheritance and ordinary-Member
  explicit Workspace access while treating Workspace Admin/Viewer/Owner action
  semantics as proposals pending approval.
- Reconciled the complete RBAC design against all 11 owner-approved
  architecture groups. The original findings were 1–3/5/10 `MATCH`, group 4 a
  labeling `CONFLICT`, and groups 6–9/11 `NOT DOCUMENTED` in part or whole.
  The conflict was corrected back to “at least one active Owner membership”;
  every missing approved boundary was added. All 11 now read as `MATCH` without
  asking the owner to approve them again.
- Defined a fail-closed per-request Profile context, scoped Workspace and
  child-resource querysets, same-tenant request-body resolution, and proposed
  non-enumerating `404`/`403`/generic `400` behavior.
- Defined service/transaction enforcement, Profile-first lock order, database
  versus service responsibilities, and controls for direct ORM, bulk writes,
  jobs, Django Admin, User deactivation, and platform-operator access.
- Identified a concrete pre-API issue: `update_profile_membership()` globally
  resolves membership ID; `add_workspace_member()` globally resolves Workspace
  ID and accepts an already-resolved unscoped target User before actor scope.
  They have no HTTP route today, but implementation must refactor both
  boundaries before exposure to avoid an IDOR existence oracle.
- Defined the Profile Invitation aggregate, recipient/authority boundary,
  `PENDING` terminal transitions, 256-bit token/hash-at-rest rules, CSRF and
  account binding, duplicate/replay/concurrency behavior, audit events,
  proposed routes, and negative tests. Invitation acceptance never creates a
  Workspace membership automatically.
- Defined dependency order from owner approval through safe `0002` apply,
  access primitives, membership-service refactor, minimal endpoints, future
  additive Invitation migration/API, and later business domains.
- Reconfirmed PostgreSQL through read-only SQL on 2026-10-17: only
  `workspace.0001_initial` is applied; 3 Users and 0 Profile, membership,
  Workspace, Task, Client, Invoice, Payment, or AuditLog business rows;
  `workspace.0002` remains unapplied. Existing Docker/PostgreSQL state was
  returned to stopped; no migration or data write occurred.

Work pending at this checkpoint:

- Owner review/edits of the seven genuinely open groups in
  `RBAC_DESIGN.md`: Workspace role/action ceiling; Profile Admin/lifecycle
  authority; Task visibility/contributor attribution; Profile/account/
  membership lifecycle; Invitation identity/role ceiling; Invitation
  operations/retention; and API error/operator policy.
- Development database migration apply is still a separate operational gate.
  Do not apply `0002` merely because the current inventory has no business rows.
- There is no blocker to reviewing the design. The unresolved owner decisions
  intentionally block implementation, not completion of this review package.

Deliberately not implemented in this design task:

- No access context, queryset selector, permission class, RBAC, or Workspace API.
- No Invitation model/migration/service/API or email delivery flow.
- No Client/Profile, Finance, public-link, AuditLog-tenant or soft-delete schema
  was added.
- No User/authentication mechanism, model, migration, database row, frontend,
  or runtime API contract was changed.

## 5. Current ownership facts and gaps

| Entity | Current source truth | Gap before business API |
|---|---|---|
| User | Global Django identity | Profile access is separate; no auth-model change. |
| Profile | Company/team tenant root exists in source | No soft-delete lifecycle or API. |
| ProfileMembership | Partial unique active Profile/User; inactive history; OWNER/ADMIN/MEMBER | Invitation lifecycle/API absent; aggregate last-owner invariant depends on service use; direct User deactivation/ORM mutation can bypass it. |
| Workspace | Nullable protected Profile FK plus transitional protected owner User | Development migration unapplied; FK remains nullable for safe legacy transition; old Workspace role/owner representation remains. |
| WorkspaceMember | Unique Workspace/User with OWNER/ADMIN/MEMBER/VIEWER; persistence validation plus audited direct-add service | No invitation lifecycle/API; bulk/raw writes remain outside the service boundary; inactive Profile membership does not erase historical WorkspaceMember rows. |
| Task | Required Workspace and creator User | Creator/member relationship is not enforced. |
| Assignment/Comment | Derive Workspace through Task | Actor membership is not enforced. |
| Deliverable/Review | Derive Workspace through Task | Uploader/reviewer membership is not enforced. |
| Client | No tenant FK | Cannot be safely tenant-filtered. |
| ShareLink | Client only; raw unique token | Client is global; no hash/revoke/capability/creator contract. |
| Invoice/Payment | Current schema still derives through global Client | Approved target is Invoice→Workspace plus same-Profile Client, but migration is not implemented. |
| Notification | User recipient | No structured tenant/resource context. |
| AuditLog | Optional User + generic entity ID | No reliable tenant path or target integrity. |

There is no current Workspace/business API, so the new foundation does not
claim complete tenant authorization. Django Admin currently uses global model
querysets and must be treated as a platform-operations surface, not a tenant
admin UI.

## 6. Accepted architecture decisions

The following are accepted and implemented:

- Modular Django architecture under `backend/apps/`.
- PostgreSQL with the existing Docker workflow.
- Django server-side session authentication for the current same-origin API.
- DRF session authentication plus global `IsAuthenticated` deny-by-default.
- Explicit reviewed `AllowAny` for health, CSRF bootstrap, registration, and
  login only.
- `/api/health/` is process liveness, not database readiness.

The owner also accepted these tenancy/business boundaries on 2026-10-16:

- Profile represents a company/team and is the tenant root; Workspace is its
  monthly operational scope.
- User may join multiple Profiles. Switching selected Profile is navigation,
  not authorization.
- Profile roles are OWNER/ADMIN/MEMBER. Profile Owner/Admin administer all
  Workspaces in that Profile; ordinary Members need explicit Workspace access;
  nothing is inherited across Profiles.
- Profiles support multiple equal Owners and always retain at least one active
  Owner; Owner changes are transactional and Admin cannot change Owners.
- Joining Profile requires invitation acceptance. Direct Workspace add is
  allowed only for an already-active Profile member; material changes are
  audited and active memberships do not duplicate.
- Client belongs to Profile; a Client has Projects; a Project may span monthly
  Workspaces through Tasks. Task remains in one Workspace and all referenced
  Client/Project/Workspace records must share one Profile.
- Invoice belongs to one Workspace and same-Profile Client; Payment belongs to
  Invoice. Numbering and detailed billing are deferred.
- Client Portal supports account and secure-link access; its link and Guest
  Review link are separate hashed, scoped, expiring and revocable principals.
  Client accounts receive no internal membership automatically.
- Soft delete is the target default for Profile, Workspace, Client, Project
  and Task; hard delete is controlled, finance/audit history is protected, and
  User departure does not cascade-delete business data. Retention duration and
  purge remain deferred.
- Migration requires inventory, no guessed mapping, backup/rehearsal for risky
  data, and new migrations only.
- High-level Task workflow is assignment → work → Deliverable → Review →
  approval/completion or revision/resubmission. Task completes only after its
  Deliverable is approved. Exact states, approvers and payroll trigger are
  deferred.

## 7. Approved target and remaining decisions

Accepted target:

```text
User (global identity)
  ↕ ProfileMembership
Profile / Organization (tenant root)
  ├─ Workspace (operational/monthly scope)
  │    └─ Task → Deliverable/Review
  ├─ Client / CRM → Project (may span monthly Workspaces through Tasks)
  ├─ Workspace → Invoice → Payment (Client must share Profile)
  └─ tenant AuditLog
```

Client Portal and Guest Review remain separate principals/link aggregates and
are not Workspace roles.

Still requires later task decisions:

RBAC owner-review gate (seven groups):

1. Workspace role vocabulary and action ceiling.
2. Profile Admin and Profile/Workspace lifecycle authority.
3. Task visibility and contributor-membership requirement.
4. Profile/account/membership lifecycle, including self-service eligibility,
   leave/rejoin, history, and account/session mechanics. Initial-Owner creation
   already exists and is not pending re-approval.
5. Invitation identity, onboarding, grant/management role ceiling, including
   whether invitations can ever request `OWNER` (proposal: no).
6. Invitation TTL/reinvite/throttle/delivery, inviter revalidation, optional
   combined UX that preserves the two fixed transitions, and record retention.
7. Non-enumerating error/`409` and platform-operator/Django Admin policy.

Separate downstream decisions: Invoice numbering/billing; Client Portal/Guest
Review exact capabilities/account linking/default expiry; retention/legal hold/
purge; and exact Task/Review states, approvers, and payroll trigger. An unknown
tenant mapping becomes a target-environment blocker only when inventory finds
such a row; the approved policy is already to never guess it.

Detailed proposal and owner-review checklist: `documentation/RBAC_DESIGN.md`.
Accepted rationale and proposal status: `documentation/DECISION_LOG.md`.

Current source/development state versus accepted target:
`documentation/DATABASE_SCHEMA.md`.

## 8. Git and uncommitted work to preserve

Repository evidence on 2026-10-17:

- Branch, `HEAD`, and local `origin/main` are `main` / `5e89971`. That existing
  owner commit contains the previously completed environment, authentication,
  API, schema-foundation, and initial RBAC-design work.
- This reconciliation did not commit, push, reset, rewrite history, edit
  backend source, or touch the database.
- `git status --short --untracked-files=all` currently reports exactly nine
  modified tracked documentation files and no untracked files:
  `CHANGELOG.md`, `DATABASE_SCHEMA.md`, `DECISION_LOG.md`, `HANDOVER.md`,
  `PROGRESS.md`, `PROJECT_CONTEXT.md`, `PROJECT_ROADMAP.md`, `RBAC_DESIGN.md`,
  and `REQUIREMENT_STATUS.md` under `documentation/`.
- `API_DOCUMENTATION.md` is unchanged because no runtime API contract changed.

Preserve all nine documentation changes. Before any future edit, rerun
`git status --short --untracked-files=all`; do not use reset/checkout/clean to
make the tree appear clean.

## 9. Environment setup and test commands

The complete Windows/PowerShell onboarding flow is in root `README.md`.

At this checkpoint on 2026-10-17, the development database was queried read-only and
contained 0 business rows and 3 User rows. The named volume was preserved.
Migration `workspace.0002_profile_workspace_foundation` was applied only in
disposable Django test databases and not in development. Future sessions must
inspect Docker and migration state rather than assume either is unchanged.

1. Copy `.env.example` to the ignored `.env` and fill only local values. Never
   paste real values into documentation or Git.
2. Load `.env` into the current PowerShell process using the validated loader
   block in `README.md`.
3. Start PostgreSQL without replacing its named volume:

   ```powershell
   docker compose --env-file .env -f docker/docker-compose.yml config --quiet
   docker compose --env-file .env -f docker/docker-compose.yml up -d postgres
   ```

4. Create/activate a fresh Python 3.12 virtual environment if the existing
   local venv is broken, then install:

   ```powershell
   py -3.12 -m venv backend/venv
   .\backend\venv\Scripts\Activate.ps1
   python -m pip install -r backend/requirements.txt
   ```

5. With environment variables loaded:

   ```powershell
   Set-Location backend
   python -m pip check
   python manage.py check
   python manage.py makemigrations --check --dry-run
   python manage.py test -v 2
   ```

`migrate --check` is expected to report the unapplied Workspace `0002` until an
approved development apply occurs. Do not run `migrate` against an unknown
database, reset the named volume, or reuse production credentials for tests.
Django tests must use a disposable test database.

## 10. Exact safe continuation

Current review gate: `HT-RBAC-DESIGN-P0-01` deliverables are ready. Stop before
Workspace API/RBAC/Invitation implementation until the owner approves or edits
the proposal in `RBAC_DESIGN.md`.

1. Owner reviews only the seven open decision groups in `RBAC_DESIGN.md`. Do
   not request re-approval of the reconciled 11 architecture groups; all now
   match the authoritative accepted decision.
2. Record accepted answers in `DECISION_LOG.md`; proposals remain proposals
   until then. Do not silently select defaults from legacy reference material.
3. If implementation is authorized, repeat Git/source/database inventory.
   Treat the prior 32/32 targeted and 61/61 full PostgreSQL runs as historical
   evidence and rerun checks after any source change.
4. Apply `workspace.0002` only as a separately approved operational step after
   target-specific inventory and backup policy. Preserve nullable legacy rows
   and never synthesize a Profile for unknown data.
5. Proposed first implementation slice of existing `HT-RBAC-P1-03` after
   approval: Tenant Access Context and Scoped Service Foundation. Implement
   scoped selectors/error mapping, refactor the two unsafe membership service
   boundaries, and add IDOR/concurrency tests before opening broad Workspace
   CRUD. Invitation schema/API follows only after its open decisions.

Do not implement Workspace API/RBAC, Invitation, Project/Client/Finance
migration, public-link flows, soft delete, Task workflow, or frontend in this
task. Do not commit, push, reset, rewrite history, or migrate development.
