# PROJECT PROGRESS

## Current Snapshot - 2026-10-28 (HT-AI-P4-01)

**DESIGN COMPLETE — PENDING OWNER APPROVAL.** Owner authorizes Phase4 AI architecture,
provider comparison, proposed API/JSON/security and frontend interaction design
only. The shared design is [AI_ARCHITECTURE_DESIGN.md](AI_ARCHITECTURE_DESIGN.md).
No AI runtime integration, key, provider request, billing, SDK installation,
runtime source edit, schema/migration or database access is authorized today.
Private .env is not read; all prior dirty frontend/backend work is preserved.

Two use cases are specified: Smart Task Generator returns a preview that needs
human edits/confirmation before existing create_task services run; Feedback
Analyzer returns cited analysis only and never changes Review, Comment, Task or
Notification state. Existing hierarchy depth3 below root, four priority choices,
aware nullable deadlines, tenant access and SessionAuthentication/CSRF remain.
Estimated duration has no existing field; no Project or dependency schema is
invented. One shared provider abstraction inside the modular monolith is proposed.

PROPOSED, not APPROVED: disabled/fixture/live-synthetic/live-private modes;
Gemini3.5 Flash-Lite for eligible synthetic demo and GPT-6 Luna as an alternative
evaluated adapter; strict versioned JSON/DRF-compatible validation, bounded input/
output, no automatic retries/paid fallback, cross-worker usage reservations and
durable confirmation/idempotency with a separately approved additive schema.
Provider/model/data policy, feature authority, numeric caps, persistence/TTL/
retention and live smoke remain Owner decisions. Official-source snapshot and
cost assumptions are dated2026-10-28 in the design, not guaranteed account quotas.

Frontend UX reuses the existing master/Task forms: Brief→Preview/Edit→Confirm,
scoped feedback source selection/citations, accessible loading/errors and no
automatic mutation. UI UX Pro Max full instructions/master and focused local
UX/React searches were read/executed for this design; no React screen is created.
Final review resolved saved-analysis source revalidation, shared-client422
integration, cross-family locking/FK test gates, replay/TTL and internal keyed
fingerprints.209 runtime hashes/path set are unchanged; exactly8 design/
coordination docs changed. Five JSON blocks parse; two canonical schemas and
three synthetic examples were checked against every used keyword through an
in-memory subset validator, with DAG/depth/citations checked separately. This
is not a full JSON Schema engine or application test PASS. Cost arithmetic for
100/1,000/10,000 requests, 20 local Markdown links and normal git diff --check
pass (existing CRLF notices only). No new application tests are claimed; FE04395
frontend/22 browser/13 launcher and backend485 remain historical checkpoints.
AI implementation is NOT STARTED. Stop at OWNER REVIEW GATE; P4-02/03/04 require
new approval. Project and onboarding retain their separate gates.

## Historical Snapshot - 2026-10-27 (HT-FE-P3-04)

**COMPLETE / OWNER REVIEW GATE.** Owner confirms this MVP includes account
lifecycle and existing Workspace/Task/Review/Comment/Notification flows.
Invitation UI, Profile Creation, membership candidate API and remaining
onboarding/management are OUT OF CURRENT TASK SCOPE / PENDING OWNER REVIEW;
they remain product requirements, not permanently removed features.

DONE source: register/forgot/reset/own-email-verification frontend over existing
APIs, preserved Task/collaboration UI, cohesive acceptance/account-security
browser specs, bounded test-only locmem mailbox bridge, and safe PowerShell
launcher with13 guard tests. No backend/model/migration/auth/RBAC/workflow change.
Token/password state is masked and memory-only; reset/register do not auto-login.

Local configuration blocker is resolved. Owner supplied the two required secret
values in .env.example rather than .env; exact values were preserved privately
in ignored root .env and the example secret fields returned to blank, without
generating/changing credentials. ValidateOnly and existing Windows venv Django
check pass, actual exits0. Django PostgreSQL connection was verified READ ONLY:
PostgreSQL16.14/hustlytasker_db, pending migrations0,35 records/3 Users/2 Sessions,
all checked business/token/Notification/Audit rows0; metadata92/23/7 unchanged.

Final-source frontend395/395 PASS14files15.94s, typecheck/Biome52/build6.65s PASS,
actual native exits0. Two App.test option mismatches were corrected in tests only;
the first acceptance helper incorrectly expected dashboard after every login,
then was corrected to respect the existing safe return-to-Task behavior.

Current real isolated browser acceptance22/22 PASS across five fresh suites:

| Suite | Result | Run ID |
|---|---|---|
| Cohesive Task/Subtask UI acceptance | 1/1 PASS43.6s | 6a1ec11fb62741aabcc330571015c828 |
| Account lifecycle UI | 1/1 PASS22.4s | 77a73580faf34927b8970208eca6f658 |
| Collaboration | 7/7 PASS1.2m | 8a940dabeedc41ceaf63b8669f461b28 |
| Workspace/Task/Start | 7/7 PASS1.0m | e1470330e0904f9d92e5254324892455 |
| Auth/CSRF/tenant | 6/6 PASS36.3s | 5d6f2f14dbbf4829ad54c0d054584d81 |

All actual native/Playwright/backend exits0 and owned DB/resource cleanup verify.
Successful business actions in the cohesive journey use React; API fixtures and
negative probes are distinguished. Registration/verification/reset/replay and
old-session invalidation use the actual backend plus isolated locmem adapter.
REAL EMAIL DELIVERY NOT VERIFIED. Current axe0/keyboard/focus/overflow/reduced-
motion checks pass at375/768/1440 and812x375 landscape. Empty register375,
reset812 and completed Task1440 PNGs were visually inspected without credentials.
Application backend is unchanged;485 is historical baseline, not a new FE04 run.

Local Django8000/Vite5174 non-mutating smoke PASS, orchestrator exit0: direct/
proxied health and CSRF200, anonymous me/profiles403 and register OPTIONS200.
The two owned child servers were intentionally stopped with exit-1; this is not
a server-exit0 claim. AUTOMATED VERIFIED / MANUAL OWNER CHECK PENDING.144
protected source assets match. No implementation blocker remains in this bounded
MVP; final docs/HANDOVER are synchronized. Production, remote CI, real email and
interactive manual Owner testing remain unverified. Exact next step is Owner
review; no AI, onboarding or Project task starts automatically.

## Historical Snapshot - 2026-10-27 (HT-API-FE-P3-03A)

**COMPLETE / OWNER REVIEW GATE. HT-FE-P3-03: IMPLEMENTATION COMPLETE.**
Owner approved the bounded backend and
frontend extension resolving the three FE03 collaboration API gaps. Existing
dirty FE02/API02A/FE03 source is preserved; no schema, migration, service,
workflow, RBAC or authentication change is included.

DONE source: Task `can_submit`; Deliverable `can_approve` and
`can_request_changes`; Comment `can_edit` and `can_delete`. These read-only
booleans bind the authenticated User to the verified live tenant context and
mirror the existing mutation services. Submit requires the assigned active
Editor, WORKING and no unresolved Deliverable. Review requires eligible manager,
REVIEW/SUBMITTED, latest created_at/id submission, non-self uploader and no
existing Review. Comment author edit and author-or-manager soft-delete require
current access and a nondeleted row. Hints never replace locked mutation checks.

DONE frontend source: actual Submit/Approve/Request Changes native-dialog forms
and server-based existing-comment controls after reload/pagination. Strict
contracts fail closed; scoped caches refresh after confirmed success. Existing
Session/CSRF client, 4,000-character Comments, tombstones and teal design master
remain in use. No temporary client ownership proof or new endpoint is required.

Current verification: targeted isolated PostgreSQL **95/95 PASS (13.020s)**,
run a718df8ac97a4813aa6c2aebfff0ccd8, actual native/Python exit0 and owned database
cleanup verified. Frontend **356/356 PASS** across12files (41.49s), strict
typecheck, Biome46files and production build6.69s PASS, exits0. The query-growth
test baseline now compares the same eligible-review path at both collection
sizes; no authorization rule was relaxed.

Final full isolated PostgreSQL **485/485 PASS (231.054s)**, run
3b2abcd913324644b6240bfc49ca1c18; actual native/Python exits0, Django OK and owned
database cleanup verified. Shared harness dependency/system/model-drift and
migration graph/full-chain checks pass; no new migration was created or applied
to persistent development.

Real isolated Django/PostgreSQL/Chrome browser evidence on final source:

- collaboration **7/7 PASS (1.3m)**, run ff6abc6459954d6d83f47ec94c426a62;
- Workspace/Task/Start **7/7 PASS (1.1m)**, run3074e74939f84f3b8039665dab7196ba;
- Auth/CSRF/tenant **6/6 PASS (43.0s)**, run c125145b536b480badeccfba582f4c90.

All actual native launcher/Playwright/backend exits0 and owned database/resource
cleanup verify. Collaboration now proves real React UI submission, independent
reviewer Approve and Request Changes/resubmission, existing-comment edit after
reload/page2, manager moderation, Notifications, denied access and session loss.
API-driven setup/negative probes remain explicitly distinct from UI mutations.
Axe0 violations, keyboard/focus/overflow checks at375/768/1440 and812x375
landscape pass;24 collaboration screenshots retained, three new-form PNGs
visually inspected. No interactive manual-browser or production claim.

Fresh read-only development remains PostgreSQL16.14/hustlytasker_db/original
hustlytasker_postgres/loopback5432/docker_postgres_data,35 migration records,
3 Users/2 Sessions/0 checked business/token/Notification/Audit rows.137 protected
model/service/migration/config/harness hashes are unchanged; existing dirty work
is preserved. All three API gaps and accepted FE03 functionality now pass; no
implementation blocker remains. Real email, remote CI and production remain
unverified separate concerns. Stop at OWNER REVIEW GATE. Project stays PENDING
OWNER DECISION; no AI/next task is started automatically.

## Historical Snapshot - 2026-10-26 (HT-FE-P3-03 before API extension)

The partial gap checkpoint below predates the Owner-approved HT-API-FE-P3-03A
extension above; its missing-contract instructions and test counts are historical.

**PARTIAL — API GAP / OWNER REVIEW.** Owner authorized
frontend collaboration UI on the existing application. FE01, FE02 and API02A
remain completed historical checkpoints; their source and dirty changes are
preserved. No backend, schema, migration, workflow or security-setting change.

Task Detail now integrates paginated Deliverable revisions/nested Review reads
and a Comment thread/composer. Comments use the existing 4,000-character/Unicode
contract, safe feedback, confirmed soft-delete and tombstones. Manager moderation
uses the existing manager capability. Editing/deleting an author's newly created
comment is limited to the exact UUID returned by a legitimate POST in the mounted
User/tenant/Task scope; proof is discarded on remount/logout/context change.
No identity-probe mutation or author inference from names/email is introduced.

Personal Notification preview/feed/unread count/mark-read and `/notifications`
are integrated with the shared shell. Queries are User-scoped, mark-read requires
server confirmation, and navigation derives the internal Task route from validated
IDs rather than trusting server target_url. Existing Session/CSRF and auth cache
cleanup remain in use; no read-all API, realtime infrastructure or extra backend.

Verified before code: `FE03_CONTRACT_MATRIX.md` records exact supported contracts
and core gaps. Deliverable POST metadata proves Editor role but not current
assignee in WORKING. Review metadata does not prove non-self/latest/state
authority. Pre-existing Comment author membership IDs do not identify the current
User. Submit/Review/general old-comment author controls remain unavailable until
Owner approves an appropriate read-only capability contract. Overall FE03 must
not be marked COMPLETE while these gaps remain.

Frozen-source frontend suite322/322 PASS (21.69s); focused contracts/client106
(59 new collaboration +47 existing client), TaskCollaboration27 and Notification12
PASS. The earlier App status-selector assertion failure was corrected. Strict
typecheck, Biome44 files and production build13.75s PASS on current source.

Real isolated collaboration browser7/7 PASS (1.4m), run
ca613d41c174462c9375f03c201ac4c8; current Workspace/Task/Start regression7/7 PASS
(1.6m), runf97f35926ad24bc2abb174f9a4edd83d. Actual native/Playwright/backend
exits0 and owned cleanup verified for both. Comment/Notification UI and read
panels are verified; API-driven Submit/Review transitions are not evidence that
the blocked Submit/Review UI exists. Axe0 violations, keyboard/focus/overflow
checks pass at375/768/1440 and812x375 landscape;12 collaboration PNGs retained,
four representative images visually reviewed. Foundation Auth/CSRF/tenant browser
regression6/6 PASS (55.6s), runf7f4970fb102434699fcd26c9ef9d8e2, with actual
native/Playwright/backend exits0 and owned cleanup. All three browser runs are
current FE03 verification, distinct from historical baselines.

All144 protected backend/config asset hashes and the dependency lock are unchanged.
Backend448/448 is a historical baseline, not rerun for this frontend-only task.
Fresh read-only development remains35 migrations,3 Users,2 Sessions and0 checked
business/token/Notification/Audit rows; no owned frontend test containers/networks
remain. Independent UI/tests are verified, with no remaining unblocked test work.
Stop at OWNER REVIEW GATE with PARTIAL — API GAP. Proposed
HT-API-FE-P3-03A would add bounded Submit/per-Deliverable Review/per-Comment
edit-delete capability hints only after separate Owner approval; no such backend
implementation, Project, AI, Finance, Client Portal or next task is authorized.

## Historical Snapshot - 2026-10-26 (HT-API-FE-P3-02A)

The completed API extension below predates the separate FE03 authorization.

**COMPLETE / OWNER REVIEW GATE. HT-FE-P3-02: IMPLEMENTATION COMPLETE.**
Owner approved the bounded API/consumer
extension to resolve the two FE02 gaps. Existing Task reads now add `can_start`;
existing manager-only Workspace member reads add `display_label` and
`is_assignable`. No endpoint, model, migration, authentication mechanism or
Task/Review business rule is added or changed.

Identity is derived from authenticated request and verified Workspace access
context. The actual TaskAssignment foreign key is User; the existing assignment
input remains ProfileMembership ID. `can_start` requires the current active
Editor, same scoped Workspace, ASSIGNED status and current active assignment.
It is only a UI hint: POST Start retains existing locked permission/state checks.
Roster eligibility mirrors assignment-service target predicates: active User,
active same-Profile MEMBER and active Workspace MEMBER in active tenant scopes.
Labels use trimmed full name or a safe membership-code fallback, never email or
username fallback. Roster authority, visibility and pagination remain unchanged.

Frontend consumes the three fields, exposes Start only from the current scoped
hint, submits the existing Start service action and refreshes scoped Task data
after success. Assignment shows actual labels, filters `is_assignable` candidates
and still submits ProfileMembership ID. Existing Session/CSRF, shared form/error/
focus patterns, ui-ux-pro-max-guided master and tenant cache boundaries remain.

Final verification: targeted PostgreSQL Task/roster/security API tests91/91 PASS
(8.358s), full isolated PostgreSQL448/448 PASS (199.251s), targeted frontend107/107
and full frontend224/224 PASS (10.20s). Strict typecheck, Biome36 files and
production build6.42s PASS. Actual native/Python exits0 and owned DB cleanup
verify for backend run cb5fc651e02340989ac22c21b64d8857.

Current real Django/PostgreSQL browser work7/7 PASS (run
0f46f8b31207406c8b073d606b593d36), foundation Auth/CSRF/tenant6/6 PASS36.3s
(run10f640b6e0e44666874a9cb1a9939186). Actual native/Playwright/backend exits0
and owned cleanup verify. These runs replace historical415/201/7/6 baselines
as current evidence; full acceptance of the implemented scope now passes.

Fresh read-only development verification remains35 migrations,3 Users,2 Sessions
and0 business rows. All135 protected model/service/schema/config assets retain
their hashes. No persistent fixtures, login/write, migration, model, workflow,
authentication or production change. Both API gaps are resolved; no remaining
implementation blocker. Stop at OWNER REVIEW GATE. Proposed HT-FE-P3-03 remains
unstarted; Project remains PENDING OWNER DECISION and no AI is authorized.

## Historical Snapshot - 2026-10-26 (HT-FE-P3-02 before API extension)

This partial checkpoint predates the Owner-approved HT-API-FE-P3-02A contract
extension above. Its gap instructions and counts are historical.

**PARTIAL — API GAP / OWNER REVIEW.** Owner authorized Workspace & Task
Management UI after the completed HT-FE-P3-01 foundation. The existing single
React/TypeScript SPA and design-system master are reused; the backend,
authentication mechanism, database schema and applied migrations are unchanged.

Current source implements Workspace create, metadata edit, archive and restore;
Task list/detail/create/edit/assignment and direct Subtask creation; bounded
ancestor navigation and paginated direct children; existing priority choices,
nullable deadline and local-time input/UTC API conversion. Server status,
priority, hierarchy, deadline and ordering filters are separate from the clearly
labeled search within the currently loaded page. The backend retains all
workflow transitions, hierarchy validation and tenant/RBAC authority.

Write controls fail closed until current scoped OPTIONS metadata confirms the
relevant POST capability. Profile/Workspace archive state also prevents write
controls. Mutations use the existing SessionAuthentication/CSRF transport,
strict inputs, pending/error feedback and explicit cache invalidation. Member
choices expose only existing ProfileMembership IDs; current Workspace MEMBER
rows are candidates, while Profile role/eligibility is finally checked by the
assignment service. No invented names, global User IDs or staff bypass.

**API GAP:** START remains intentionally unavailable in the UI. The current-user
API returns a User ID and Task assignment returns a ProfileMembership ID; the
available APIs do not prove that these represent the same current assignee.
Role-level OPTIONS permission is insufficient for that identity check. No
backend endpoint or mapping is fabricated in this frontend task. Owner review
must decide a separately scoped identity/capability contract before START UI.
The source also contains legacy CANCELLED; it is displayed as a legacy value,
with no cancel action or change to the approved five-state workflow.

Final strict typecheck, Biome 36 files and production build 7.01s PASS with exits0.
Mocked/contract201/201 tests PASS11.35s across8files. Actual isolated Django/
PostgreSQL/Chrome work-management7/7 PASS56.5s and foundation regression6/6
PASS34.2s, each launcher/Playwright/backend exit0 with owned cleanup verified.
Axe0violations/overflow/keyboard/native-dialog/reduced-motion checks passed at
375/768/1440 and812x375 landscape;16 FE02 screenshots retained and4 representative
PNGs visually reviewed. No interactive manual-browser testing is claimed.
The runner separates foundation/work-management
into fresh owned runtimes, preserves the existing six foundation cases and the
real login throttle, and keeps FE02 screenshots under its own ignored task
directory. Targeted static E2E lint, fixture Python AST, PowerShell parser and
diff checks have passed. Both final browser runs and implemented UI verification
are complete; overall acceptance stays partial because the API gap remains.

Read-only development verification confirms original PostgreSQL16.14,
hustlytasker_db/hustlytasker_postgres, loopback5432/docker_postgres_data,
35 migration records,3 Users/2 Sessions and0 checked business/token/notification/
Audit rows. No development login, fixture, migration or data write. Project is
PENDING OWNER DECISION; Review UI, Comments/Notifications UI, AI and other
modules remain outside this task. Verification/documentation are complete; stop
at OWNER REVIEW GATE; do not mark full HT-FE-P3-02 COMPLETE while the gap remains.

## Historical Snapshot - 2026-10-26 (HT-FE-P3-01)

The foundation checkpoint below predates the separate HT-FE-P3-02 authorization.

**IMPLEMENTATION COMPLETE / OWNER REVIEW GATE.** Owner authorized the
first web UI foundation after the completed backend rollout. The existing empty
frontend directory now contains a single React19.3.1/TypeScript6/Vite6.4.5 SPA,
React Router7.18.4, Tailwind4, TanStack Query5 and Biome2.6.3 lint, with npm lock.
Node20.17/npm10.8.2 are retained; no backend dependency or architecture changed.

Source implements shared typed API transport, in-memory CSRF bootstrap/rotation,
SessionAuthentication login/logout/me and fail-closed auth initialization/cache
cleanup. Sidebar/topbar, reusable components, protected routes and read-only
Profile/Workspace list/detail pages exist with loading/empty/error states.
ui-ux-pro-max was read and its CLI searches ran; selected tokens/layout/font
are recorded in design-system/hustlytasker/MASTER.md and frontend/src/styles.css.
No Task/Review/Project/AI/write UI or fake dashboard metrics are introduced.

Final frozen-source verification: strict TypeScript and Biome lint24 files PASS;
production build PASS in6.67s (JS388.07kB/gzip116.31kB; CSS31.44kB/gzip9.43kB;
Vietnamese fonts locally bundled). Full mocked frontend suite96/96 PASS across
4 files in8.60s: API47, primitives15, AuthProvider16, App18. This includes quiet
permission403 identity probes, cache cleanup, stale-response guards, finite route
handling, public tab titles after identity loss and a Router-independent fatal fallback.

Real isolated Django/PostgreSQL integration6/6 PASS in40.7s, run
86b46affb2724fd9be868fac2955c63d. Actual native launcher/Playwright/backend exits
are0; owned database/containers/two networks cleanup PASS. Real Session/CSRF
rotation, invalid login/logout/me, scoped Profile/Workspace, IDOR, return redirect,
session expiry and revoked access verify. Automated Chrome responsive/keyboard/
native-dialog checks and axe WCAG2/2.1 AA return0 violations at375/768/1440 and
812×375 landscape;13 ignored screenshots retained, with visual PNG review.
Interactive manual-browser testing was not run. Earlier launcher attempts are
historical; the first did not reach browser tests, and owned cleanup was verified.

Final read-only development: PostgreSQL16.14,35 migrations,3 Users/2 Sessions,
0 checked business rows unchanged.143 protected backend/config/shared-harness
hashes match; no owned test resources or5173/8001 listeners remain. Backend
415/415 is the historical completed rollout baseline, not rerun because no
backend implementation changed. Authenticated success was tested only in isolated
fixtures, never persistent development. No production deployment or real email/
remote CI verification is claimed. Documentation/HANDOVER refreshed; no blocker.
Stop at OWNER REVIEW GATE; HT-FE-P3-02 is proposed only, with no automatic work.

## Historical Snapshot - 2026-10-26 (HT-DB-P1-11)

**COMPLETE / OWNER REVIEW GATE.** Resume verified both migrations absent and
preserved existing source; original stopped container restarted after identity/
volume/loopback checks. Fresh104,092-byte custom backup/size/SHA256/240-line TOC/
fullread and exact-data isolated restore/rehearsal PASS. Applied only tasks.0004
then notifications.0002 once each, with stage1 integrity before stage2.
Development now35 records,8 Comment/12 Notification columns and44 valid FKs
without orphans; CHECKs/partial UNIQUE/indexes/nullability/defaults valid.
Exact legacy values preserved:3 Users/2 Sessions,0 business/token/Audit rows,
metadata23/92/7 unchanged. System/drift/graph/history/migrate-check/empty plan PASS.

Development READ ONLY smoke67 requests +28 serializer checks PASS; authenticated
success/mutations remain isolated-only. Current Comment40/40 (13.140s),
Notification34/34 (8.431s),Task128/128 (41.694s),security253/253 (224.745s),
full PostgreSQL415/415 (259.978s) PASS. All actual launcher/Python exits0,
shared dependency/system/model-drift/graph/full-chain and owned cleanup PASS.
Final legacy/schema comparison after tests PASS; owned rehearsal/temp dump
removed, host backup hash/size retained, no test resources remain.143 protected
assets unchanged; documentation/handover updated, no backend/harness edits.
No rollout TODO/blocker. Project remains PENDING OWNER DECISION; proposed next
step is Owner Project scope review, no automatic task. Do not reapply migrations.

## Historical Snapshot - 2026-10-25 (HT-COM-P2-06)

Status **IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**.
Stop at OWNER REVIEW GATE. Preserved partial Comment/Notification source on
resume, completed missing Notification API/migration/tests, hardened persisted
event proof and Unicode input, and verified the integrated foundation.

Comments reuse TaskComment: manager/Editor create, current author edits own,
author/manager soft-delete with body hidden as tombstone. Notification has five
audit-backed atomic event types, scoped relevant recipients and live own-feed/
count/read authorization. No Task/Review/parent workflow, User schema, auth
mechanism, Client/Project/AI/frontend change. Full rules/limits are in HANDOVER.

Current isolated results: Comment **40/40 PASS (6.919s)**, Notification
**34/34 PASS (5.401s)**, Task/Comment/hierarchy/Review **128/128 PASS (22.637s)**,
security/RBAC **253/253 PASS (165.756s)**, full PostgreSQL **415/415 PASS
(191.226s)**. All five successful runs: launcher0/Python0, Django OK, dependency/
system/drift/graph/full-chain/owned cleanup PASS. Initial Notification attempt
failed on an inverted intermediate Workspace guard; corrected frozen source
passed rerun and full regression, without loosening permissions. attempt1 and
current paired logs/exit JSON remain ignored under .local_backups/HT-COM-P2-06/.

Final development READ ONLY: PG16.14,33 migrations,3 Users/2 Sessions and
zero checked Comment/Notification/business/token/Audit rows. New tasks.0004/
notifications.0002 records/columns are absent; no persistent writes/migration.
No test resources remain.83 protected assets unchanged; the sole expected
shared validator change safely rejects malformed Unicode field names.
Docs refreshed and current gate explicit. Next proposed task is controlled
development rollout only after separate approval. Project remains pending.

## Historical Snapshot - 2026-10-25 (HT-DB-P1-10)

Status: **COMPLETE / OWNER REVIEW GATE**. Owner conditionally authorized controlled tasks.0003
development rollout only. Preflight identity/schema/history rechecked read-only:
correct repository PostgreSQL16.14/loopback/volume,32 migration records,
tasks.0003 and parent_id absent, existing Task constraints/indexes valid.
That preflight state is superseded by the applied state below. No source blocker.
Fresh inventory confirms3 Users/2 Sessions and0 business/token/Audit rows;
all39 FKs have no orphans. New102,780-byte custom backup verified by matching
size/SHA256,237-line TOC/fullread and owned isolated restore. Exact legacy-row
comparison and rehearsal tasks.0003 PASS; plan contains only that migration.
Standard development apply and post-check PASS:33 migrations,11 Task columns,
nullable parent/selfCHECK/FK/index valid,40 FKs no orphans. Exact legacy rows
preserved (only one new migration record),3 Users/2 Sessions and0 business rows.
Fixture-free READ ONLY development smoke51 requests and16 serializer-only
checks PASS, no login/fixture/PII/email/write. Current isolated Task88/88
PASS11.780s; Auth/security/Invitation/Workspace/API253/253 PASS162.615s.
Launcher/Python exit 0 confirmed by native Process handle and Docker die event,
with Django OK and owned cleanup. Current full suite **341/341 PASS in 170.987s**
with both exits 0; dependency/system/drift/graph/history/full-chain checks PASS.
Final exact legacy-row comparison with rehearsal and backup size/hash PASS.
Owned rehearsal DB/container dump copy removed; host backup retained. No test
DB/container/network remains; only original development PostgreSQL/volume.
129 business/config/harness assets unchanged by SHA-256; documentation only.
Backup details are in HANDOVER. Do not reapply migration.
Preserve all existing dirty code/docs; Project remains pending Owner decision.

## Historical Snapshot - 2026-10-25 (HT-TASK-P2-05)

Status: **IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**.
Stop at **OWNER REVIEW GATE**; Project architecture is **PENDING OWNER DECISION**.

- Reused existing deadline/priority and added nullable protected Task.parent,
  max depth3 (root0), cycle/self/cross-Workspace/moved-subtree validation under
  existing tenant locks. Nodes retain independent workflows/reviews/deadlines;
  no status inheritance or completion aggregation. Existing managers alone
  create/reparent/change planning fields. No new role/authentication scheme.
- Existing POST/PATCH accepts parent_id. New paginated direct-child GET and
  optional root/parent/status/priority/deadline filters/order are additive;
  old fields, flat-list default, pagination and CSRF remain compatible. List
  assignment membership lookup is batched rather than per-row.
- New tasks.0003 is additive, with no guessed legacy mapping. Migration tests
  **2/2 PASS** (1.465s), Task API **42/42 PASS** (4.990s), hierarchy/workflow
  **43/43 PASS** (4.770s, including two concurrency races), Workspace/RBAC
  **122/122 PASS** (60.495s), full PostgreSQL **341/341 PASS** (174.058s).
  All use shared isolated harness; dependency/system/drift/graph/history/
  full-chain/owned cleanup checks pass. Full paired logs are retained ignored
  under `.local_backups/HT-TASK-P2-05/`; no unrecorded child exit code is claimed.
- Final development read-only inventory: PG16.14, original Compose/loopback/
  volume, 32 migrations, 3 Users/2 Sessions, zero verified Users/tokens/checked
  business/AuditLog rows. tasks.0003 and parent column remain absent; no
  persistent migration/write occurred. No test container/network/DB remains.
- All affected docs refreshed, including A/B Project analysis and independent
  node behavior. Literal Workspace-owned Project conflicts with accepted
  cross-month Profile/Client Project scope; propose A now/B′ later. Project,
  estimated duration, AI/Notification and frontend are not implemented.
- No implementation blocker. Next step is Owner review, then a separately
  authorized controlled tasks.0003 development rollout; no automatic new task.
  Preserve current dirty code/docs and the pre-existing two checkpoint edits.

## Revalidation - 2026-10-25 (HT-TEST-P1-01)

Status remains **COMPLETE / OWNER REVIEW GATE — LOCAL TEST HARNESS VERIFIED**.

- Re-read the repeated request and checked the actual tracked harness/CI,
  relevant settings/migrations/tests and documentation. Branch `main`, HEAD
  `3a736f0`, clean worktree before this checkpoint update. No incomplete
  implementation was found; no business/tooling code was changed or recreated.
- Read-only development inventory confirms PostgreSQL 16.14, the original
  repository Compose/loopback/volume identity, 32 migrations with
  `accounts.0002` and `workspace.0004`, 3 Users, 2 Sessions, zero security
  tokens and zero checked business/AuditLog rows. No test DB or labelled test
  container/network remains. No persistent migration or data write occurred.
- Current PowerShell syntax, test Compose configuration and diff checks pass.
  The guard 14/14, targeted 10/10 and full PostgreSQL 286/286 results below are
  the completed 2026-10-24 run, not a new run today. The unchanged
  implementation does not require repeating completed regression work.
- Only HANDOVER and this progress checkpoint changed. **CI WORKFLOW
  IMPLEMENTED — REMOTE RUN NOT VERIFIED.** Stop for Owner review; do not start
  `HT-PROJ-P2-05` automatically. No implementation blocker remains.

## Historical Snapshot - 2026-10-24 (HT-TEST-P1-01)

Status: **COMPLETE / OWNER REVIEW GATE — LOCAL TEST HARNESS VERIFIED**

- Added dedicated `backend/config/test_environment.py` and `test_settings.py`
  for explicit isolated test endpoints. Deployment/`POSTGRES_*`/PG connection
  variables and `.env` do not supply the test target. Session authentication,
  CSRF, password hashing/validators, application rules, and migration files are
  unchanged; credential email uses the locmem test adapter.
- `scripts/test_backend.py` is the shared local/CI command. It runs dependency,
  system, model-drift and migration graph/history checks, creates a unique
  owned database, verifies the full migration chain there, runs serial
  full/targeted tests, and cleans only that database after cluster/role/run-
  marker checks. It refuses pre-existing DB/non-fresh cluster and unsafe CLI
  settings/runner/keepdb/parallel overrides.
- Local `scripts/test-backend.ps1`, `docker/compose.test.yml`, and the test
  Dockerfile/ignore create a separate labelled Python 3.12/PostgreSQL 16 test
  project with read-only source, tmpfs PG data, an internal network, no
  published PG port, and no persistent volume. Normal/signal cleanup and an
  explicit verified `-CleanupRunId` path handle disposable resources.
- Added `.github/workflows/backend-ci.yml`: PR/push-main, Python 3.12, fresh
  job-local PostgreSQL 16 service, pinned requirements, harness guard tests,
  and the same full core command. No deploy/production secrets; repository
  permissions are read-only and required failures are not suppressed.
  **CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED.**
- Actual current evidence: harness safety unit tests **14/14 PASS** in 0.513s;
  targeted API **10/10 PASS** in 0.044s; full PostgreSQL **286/286 PASS** in
  **166.382s** through the one-command local launcher, exit 0. Dependency,
  system, model-drift, graph/history, full migration-chain and owned-DB
  cleanup checks all pass. The first targeted attempt exposed a harness-only
  SimpleTestCase DB-selection issue, which was fixed without business edits.
- A deliberate nonexistent label returns exit 1 and cleans all run resources.
  Simulated hard-interruption fixtures (two owned containers/network) clean
  through `-CleanupRunId`; a wrong-repository network is correctly refused and
  preserved, then removed separately by its verified fixture ID. PowerShell
  parser, Compose configuration, actionlint, and `git diff --check` pass;
  actionlint's initial service-port numeric-key issue was fixed to a string key.
- Final read-only development baseline remains 32 migration records, including
  `accounts.0002`, 3 Users, 2 Sessions, and zero account-security token rows.
  Original User/Session fields compare equal before/after in memory without
  exposing private values. Audit/business data is unchanged. No labelled test
  containers/networks or test DB remains; only the original PostgreSQL container
  is running. No development migration is part of this task. Existing dirty
  source/docs are preserved; README documents full/targeted commands and cleanup.

All local acceptance criteria pass. **CI WORKFLOW IMPLEMENTED — REMOTE RUN
NOT VERIFIED**: no GitHub push/remote run was performed. Stop at **OWNER REVIEW
GATE**. The proposed next task is `HT-PROJ-P2-05 — Project, Subtask, Deadline &
Priority`, only after Owner review/authorization. Real email, distributed
production throttling, and reset timing limitations are unchanged; this does
not mark the full application complete.

---

## Historical Snapshot - 2026-10-24 (HT-DB-P1-09)

The rollout below is the completed baseline preceding HT-TEST-P1-01. Its test
results do not substitute for the current harness verification gates.

Status: **COMPLETE / OWNER REVIEW GATE**

- Owner-authorized conditional rollout targets only the repository Compose
  development PostgreSQL 16.14 database `hustlytasker_db`, container
  `hustlytasker_postgres`, loopback `127.0.0.1:5432`, volume
  `docker_postgres_data`. Production and other persistent environments remain
  outside this authorization.
- Re-inventory before apply found 31 migrations, 3 active Users, 2 Sessions,
  zero checked business/AuditLog rows, 22 content types, 88 permissions, and
  7 Admin log rows. Existing foreign keys had no orphans and no ambiguous
  legacy email identities were found.
- Retained fresh Git-ignored custom backup
  `.local_backups/HT-DB-P1-09/hustlytasker_dev_pre_accounts_0002_20261024T062543Z.dump`:
  93,598 bytes; SHA-256
  `195d7406015be1ce4d40f1b0f0f37094282abe7b82b7dd9b9c4b2c070827af49`.
  Host/container size/hash match; 223-line TOC and full archive read PASS.
  Restore into an isolated PostgreSQL database matched every legacy row;
  applying the exact migration there and rehearsal checks passed.
- Applied exactly `accounts.0002_accountsecuritytoken_user_email_verification`
  once to development at `2026-10-24 06:30:28.634074 UTC`. Development now has
  32 migrations, 15 User columns, and an empty 17-column token table. Token
  CHECKs/FKs/indexes and the User verification constraints are validated;
  all 39 public FKs have zero orphans. Legacy rows are byte-exact unchanged,
  including 3 Users and 2 Sessions. Zero Users were verified; no token or
  business/AuditLog rows were created. Standard Django metadata is now 23
  content types and 92 permissions; Admin log count remains 7.
- `pip check`, Django system check, `makemigrations --check --dry-run`,
  `migrate --check`, and the empty migration plan PASS.
- **DEV SMOKE PASSED**: 45 fixture-free Django-handler requests (the original
  36 plus eight Task/Review boundary requests and one extra CSRF bootstrap)
  against persistent development in a PostgreSQL READ ONLY transaction with CSRF
  enforced. Health/CSRF return 200, missing-CSRF 403, malformed auth/reset
  input 400, protected anonymous routes 403, disallowed methods 405,
  unknown-email reset request neutral 202, and invalid reset confirm generic
  400. Supplemental Task/Review anonymous boundaries return 403. No 500, PII
  disclosure, email attempt, or User/Session/token mutation.
  Authenticated success and real verification/reset/Invitation acceptance are
  **NOT TESTED ON PERSISTENT DEVELOPMENT**; those paths use isolated tests.
- Current isolated reruns: account security **44/44 PASS** in 30.549s;
  Authentication/API Foundation **29/29 PASS** in 7.523s; Invitation
  **40/40 PASS** in 61.679s; Workspace/RBAC **140/140 PASS** in 79.717s; and
  Task/Review **33/33 PASS** in 8.457s. These completed task runs were reused
  after resume because source/schema had not changed. Only the unfinished
  full-suite gate was rerun: **286/286 PASS** in 197.049s, exit 0. Its log and
  exit record are retained under Git-ignored
  `.local_backups/HT-DB-P1-09/full_postgresql_tests.log` and
  `.local_backups/HT-DB-P1-09/full_postgresql_tests.exit`.
- Final system/dependency/migration checks pass. Exact legacy-row comparison
  against the rehearsal again passes. The rehearsal database, temporary
  Python runner, and container-side backup copy were removed; no `test_%` or
  `htdb_p109%` database remains. The verified host backup is retained with its
  original size/digest. Development PostgreSQL remains running with 32
  migrations, 3 Users, 2 Sessions, and no account-security token rows.
- No feature code, model, migration file, environment credential, or business
  rule changes are part of this operational task. All pre-existing dirty work
  is preserved.

All rollout acceptance criteria pass. Stop at **OWNER REVIEW GATE**; no
implementation blocker remains and no next feature starts automatically.
**REAL EMAIL DELIVERY NOT VERIFIED. DISTRIBUTED RATE LIMITING NOT VERIFIED.**
Cache throttles remain process-local; reset-request response neutrality does
not establish timing indistinguishability.

---

## Historical Snapshot - 2026-10-24 (HT-AUTH-P1-02 implementation gate)

The following records the pre-rollout implementation gate. Its source-only
migration boundary and inventory are superseded by HT-DB-P1-09 above.

### Current Phase

`PHASE 2.2 - API Architecture / account verification and recovery`

### HT-AUTH-P1-02 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

Status: **IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**

- Added a persistent email-verification signal to `User` and a purpose-bound
  `AccountSecurityToken` aggregate for email verification and password reset.
  Raw credentials are generated with high entropy, delivered only by email,
  and represented in PostgreSQL only by a unique SHA-256 digest. Tokens are
  single-use, expiring, rotated on resend, and transitioned under row locks.
  Password-reset records additionally store a SHA-256 fingerprint of the
  encoded Django password state. `acctok_fingerprint_by_purpose` requires that
  fingerprint only for reset credentials.
- Added additive `accounts.0002_accountsecuritytoken_user_email_verification`.
  It adds nullable verification fields and the token table, constraints, and
  indexes without backfilling or guessing verification for legacy users. The
  migration exists in source and passes isolated migration tests, but it is
  **NOT APPLIED TO PERSISTENT DEVELOPMENT OR PRODUCTION**.
- Added authenticated, CSRF-protected email-verification request/confirm
  routes and public, CSRF-protected password-reset request/confirm routes.
  Password-reset request returns the same `202` HTTP status/body for eligible,
  unknown, ambiguous, inactive, unusable-password, or delivery-failure cases.
  Confirmation applies Django password validators, consumes the token, does
  not log the user in, and invalidates established sessions through Django's
  password-backed session authentication hash. This response contract does
  not equalize or prove indistinguishable request timing.
- A material email change clears the persisted verification signal and
  revokes pending email-verification and password-reset tokens, including an
  `A -> B -> A` email sequence. A password change through `User.save()` revokes
  pending reset credentials; a direct queryset password update that bypasses
  that hook still fails confirmation because the stored password fingerprint
  no longer matches. Verification is tied to the uniquely resolved normalized
  current email. Existing registration and login remain active for the three
  legacy development users; no account was auto-verified or blocked. Profile
  Invitation keeps its existing independent delivered-token/current-email
  proof and is not newly gated by this task.
- Account security mail now reuses the shared configured-mail safety boundary.
  Console/dummy/file backends are refused for credential delivery; locmem is
  used only by isolated tests. Responses, logs, audit metadata, and model
  string representations do not expose raw credentials or passwords. Reset
  confirmation has independent token-fingerprint `10/hour` and client-address
  `30/hour` throttles; malformed Unicode is handled fail-closed so public reset
  and Invitation recipient input return `400` instead of `500`.
- Final isolated PostgreSQL evidence: account security **44/44 PASS** in
  32.336s; Authentication/API/Invitation **113/113 PASS** in 99.629s;
  Workspace/RBAC/Task/Review **173/173 PASS** in 93.895s; and the full suite
  **286/286 PASS** in 188.592s. `pip check`, Django system check,
  `makemigrations --check --dry-run`, and `git diff --check` pass; the latter
  reports only existing LF/CRLF notices, not whitespace errors.
- Read-only development inventory remains PostgreSQL 16.14 on
  `hustlytasker_db`, 31 applied migrations (`accounts.0001` only and
  `workspace.0001`-`0004`), 3 Users, 2 sessions, and zero checked business or
  AuditLog rows. The verification columns and
  `accounts_accountsecuritytoken` table are absent, and no test database
  remains.
### Owner review gate

- **REAL EMAIL DELIVERY NOT VERIFIED.** No provider credential was configured
  or exercised. DRF throttle state uses the default process-local cache and is
  not distributed protection for a multi-worker deployment.
- Response status/body neutralization does not provide constant-time password-
  reset requests; timing equalization remains unimplemented and unverified.
- Do not apply `accounts.0002` to persistent development or production and do
  not start another feature. The next allowed action is Owner review and, only
  with separate authorization, a controlled development migration rollout.

---

## Previous Snapshot - 2026-10-23 (HT-DB-P1-08)

### Current Phase

`PHASE 2.2 - API Architecture / controlled Invitation development rollout`

### HT-DB-P1-08 — COMPLETE / OWNER REVIEW GATE

Status: **CONTROLLED DEVELOPMENT ROLLOUT VERIFIED**

- Reconfirmed the repository-owned PostgreSQL 16.14 development target
  `hustlytasker_db`. Before apply it had 30 migration records, 3 Users, 2
  sessions, no `workspace_profileinvitation` table, and zero checked business
  rows. No production target was accessed.
- Created and retained the Git-ignored custom-format backup
  `.local_backups/HT-DB-P1-08/hustlytasker_dev_pre_workspace_0004_20261023T050527Z.dump`
  (78,758 bytes; SHA-256
  `57f05837925c74a1bef83200a4211c3ed1cffbbe1e24552377d7efefc9baaf76`).
  Host/container size and digest matched, the 198-line TOC was readable, and a
  full archive read passed.
- Restored that backup into an isolated rehearsal database, applied only
  `workspace.0004_profileinvitation`, verified its schema and unchanged source
  counts, then removed the exact rehearsal database with absence confirmed.
- Applied only `workspace.0004_profileinvitation` to development at
  2026-10-23 05:09:39.628419 UTC. Development now has 31 migration records and
  an empty 22-column `workspace_profileinvitation` table. Seven CHECKs and
  seven foreign keys are validated; two partial unique constraints and all 16
  table indexes are valid/ready. Users, sessions, and all checked business-row
  counts are unchanged.
- Django system check, migration drift check, and `migrate --check` pass after
  apply. Fixture-free direct smoke passes: health `GET` 200 / `POST` 405,
  CSRF bootstrap 200, missing-CSRF registration 403, valid-CSRF invalid
  registration payload 400, and anonymous Profile lifecycle, Workspace
  read/write/lifecycle, Workspace membership read/write/revoke, and every
  Invitation route shape 403. No request returned 500, exposed a
  token/digest/User PII, or changed row/session counts.
- Current isolated PostgreSQL verification passes: Invitation **39/39** in
  62.528s, Authentication/API **29/29** in 7.475s,
  Workspace/RBAC/Task/Review **173/173** in 97.378s, and full suite **241/241**
  in 167.960s. Each Django-created test database was destroyed; the full run
  reported zero system-check issues.
- Cleanup is verified: no `test_%` or `htdb_p108_restore_%` database remains;
  the exact container-side temporary archive was hash-checked then removed;
  disposable runners `htp_p108_runner` and `htp_p108_resume_smoke` were
  removed. The host backup remains at the documented Git-ignored path with the
  same size/hash. The development
  PostgreSQL container was running at task start and remains intentionally
  running.
- Final `git diff --check` passes; Git reports only existing LF-to-CRLF
  conversion warnings and no whitespace error. Final `git status --short`
  contains only the preserved HT-INV-P2-04 source/documentation work.
- Persistent development has no Profile/Workspace fixture and no valid
  authenticated session available for the smoke. Therefore authenticated
  Invitation success/mutation flows were **NOT TESTED ON PERSISTENT
  DEVELOPMENT**; isolated test databases remain the evidence for those paths.
- **REAL EMAIL DELIVERY NOT VERIFIED.** No SMTP/provider credential was
  configured. Cache-based DRF throttles remain process-local for multi-worker
  deployments; locked database issuance limits remain authoritative for
  create/resend.

### Exact continuation / review gate

Stop at `HT-DB-P1-08 — COMPLETE / OWNER REVIEW GATE`. The Owner must select
and explicitly authorize the next roadmap task; a candidate is
`HT-AUTH-P1-02 — Account Verification & Recovery`. Do not start it, another
feature, or a rollout to another environment automatically.

---

## Previous Snapshot - 2026-10-23 (HT-INV-P2-04)

### Current Phase

`PHASE 2.2 - API Architecture / Profile Invitation onboarding`

### HT-INV-P2-04 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

- Implemented the Profile-scoped `ProfileInvitation` aggregate and additive
  `workspace.0004_profileinvitation` with digest-only one-time credentials,
  seven-day lifecycle, delivery/terminal metadata, resend lineage, constraints,
  indexes, and no data backfill.
- Implemented locked transactional creation, revoke, resend/rotation,
  accept/decline, expiration, original-inviter revalidation, compatible
  membership creation/reactivation, stale Workspace-access soft revocation,
  durable issuance limits, and atomic audit events.
- Recipient actions require SessionAuthentication, CSRF, a uniquely matching
  freshly locked current account email, and a one-time credential whose mail
  adapter accepted delivery. This is per-invitation email-control proof, not a
  global verified-email flag. No recipient inbox or anonymous preview exists.
- Added six manager/recipient route shapes with tenant scoping, Owner/Admin
  role ceilings, strict input, sanitized/no-cache output, generic IDOR-safe
  responses, replay protection, and cache/durable abuse controls.
- Targeted Invitation PostgreSQL tests pass **39/39** (61.056s), Auth/API
  regression **29/29** (7.220s), Workspace/RBAC/Task/Review regression
  **173/173** (90.298s), and the full PostgreSQL suite **241/241** (157.059s).
  `pip check`, Django system check, and migration-drift check also pass.
- Read-only development post-check remains unchanged at 30 migration records,
  3 Users, 2 sessions, and zero checked business rows. `workspace.0004` is
  unapplied, its table is absent, and no test database remains. Production was
  not contacted.
- Delivery abstraction is implemented and locmem-tested, but **REAL EMAIL
  DELIVERY NOT VERIFIED**. Default cache throttles are process-local; a shared
  production cache remains deployment work. Database issuance counters remain
  authoritative for create/resend limits.

### Exact continuation / review gate

Stop at `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`.
Do not apply `workspace.0004` or start another feature. After Owner review, the
next proposed task is a separately authorized controlled development
inventory/backup/rehearsal/apply/smoke for `workspace.0004`.

---

## Previous Snapshot - 2026-10-21 (HT-DB-P1-07)

### Current Phase

`PHASE 2.2 - API Architecture / controlled Task and Review development rollout`

### HT-DB-P1-07 — COMPLETE / OWNER REVIEW GATE

- Confirmed the authorized target is the repository's local Docker Desktop
  Compose PostgreSQL 16.14 development database `hustlytasker_db`, exposed only
  on `127.0.0.1:5432` with named volume `docker_postgres_data`. Production was
  not contacted.
- Pre-apply state had 28 migrations: Workspace 0001-0003 applied and
  Tasks/Reviews only 0001. Counts were 3 active Users, 2 sessions, and zero
  checked tenant/workflow rows. Migration history, physical schema, connection
  state, locks, and every invalid-enum/duplicate/orphan/cross-tenant/
  unvalidated preflight check matched the safe baseline.
- Created and verified the ignored custom-format backup
  `.local_backups/HT-DB-P1-07/hustlytasker_dev_pre_task_review_0002_20261020T233252Z.dump`
  (75,502 bytes; SHA-256
  `4d89fe198da9a245c6ae39c466a11944a80914735c876dbeb18f546d55391f22`).
  Host/container hashes match, the 192-line TOC is readable, and a complete
  archive read passed.
- A full restore rehearsal in isolated database
  `htdb_p107_restore_20261020233252` reproduced the baseline, applied
  `tasks.0002` then `reviews.0002`, passed schema/integrity checks, and was
  removed with absence verified.
- Applied `tasks.0002_task_workflow_foundation` explicitly to development at
  2026-10-20 23:35:36 UTC, passed its intermediate gate, then applied
  `reviews.0002_review_workflow_foundation` explicitly at 23:36:12 UTC.
  Development now has 30 migration records.
- Post-check confirmed `TaskAssignment.is_active` and nullable
  `Deliverable.revision` with expected nullability/no permanent database
  defaults, five validated named CHECKs, one validated Review uniqueness
  constraint, six valid/ready named indexes, and validated actor FKs. All
  integrity/duplicate/orphan checks remain zero and row/session counts are
  unchanged.
- Fixture-free development smoke passed: health methods, CSRF/login behavior,
  and anonymous denial across Profile/Workspace/Task/Deliverable route shapes
  matched the contract with no `500`. Successful authenticated business
  mutations were intentionally not run on persistent development because it
  has no business fixtures; isolated tests cover those paths.
- `pip check`, Django system/migration checks, Task 33/33 (7.998s), Auth/API
  29/29 (7.183s), Workspace 140/140 (77.774s), and full PostgreSQL 202/202
  (93.368s) all passed. Test/rehearsal databases and temporary runners were
  removed. No code, migration file, Authentication contract, fixture, or
  production environment changed.

### Exact continuation / review gate

Stop at `HT-DB-P1-07 — COMPLETE / OWNER REVIEW GATE`. The Owner must select
and explicitly authorize the next roadmap implementation. Do not automatically
start another module. Every non-development rollout remains separately gated.

---

## Previous Snapshot - 2026-10-21 (HT-TASK-P2-03)

### Current Phase

`PHASE 2.2 - API Architecture / Task and internal approval workflow`

### HT-TASK-P2-03 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

The approved backend-only Task/Deliverable/internal Review slice is implemented
in source. It keeps the existing Task ownership path (`Task -> Workspace ->
Profile`), SessionAuthentication, tenant contexts, and deny-by-default DRF
policy.

Implemented at this checkpoint:

- Additive `tasks.0002_task_workflow_foundation` and
  `reviews.0002_review_workflow_foundation` harden actor deletion with
  `PROTECT`, add status/priority checks and lookup indexes, retain one current
  active Task assignment, add positive per-Task Deliverable revisions, and
  enforce one internal Review per Deliverable. Legacy assignments become
  inactive, legacy Deliverable revisions remain `NULL`, and no current
  assignee/revision is guessed.
- Manager Task create/update/assign, assignee-only start and Deliverable
  submission, and manager-only internal approve/request-changes are provided
  through locked transactional services with atomic AuditLog events.
- The state machine is `PENDING -> ASSIGNED -> WORKING -> REVIEW`, then either
  `COMPLETED` after approval or `WORKING` after requested changes and a later
  resubmission. No arbitrary status mutation exists; `CANCELLED` is reserved
  and has no public transition.
- Profile Owner/Admin and assigned Workspace Admin manage/review Tasks in an
  active Workspace. Only an active ordinary Profile Member with effective
  Workspace `MEMBER` (Editor) capability and the current active assignment may
  start or submit. Self-review, stale revision review, repeat review, and
  cross-tenant/wrong-parent access fail closed.
- Seven nested `/api/v1/` route shapes provide Task list/create,
  detail/update, assign, start, Deliverable list/submit, approve, and
  request-changes operations. Inputs are strict, outputs omit User PII, list
  responses are bounded/paginated, unsafe methods retain session CSRF, and no
  Task/Deliverable delete or arbitrary status endpoint is exposed.
- Internal approval is explicitly separate from Client approval. Completion
  creates no Payroll/Payment row and performs no compensation calculation.
  Comments API, upload/media pipeline, Marketplace, Client Portal/Guest Review,
  Finance, Invitation, and frontend remain outside this task.
- Task, TaskAssignment, and TaskComment Django Admin surfaces are
  inspection-only. Workspace deletion through Django Admin is disabled because
  the existing Workspace -> Task FK would otherwise cascade-delete workflow
  history. Task soft delete and the wider retention/purge implementation are
  still pending a separate approved task.

Verification actually completed:

- `python -m pip check`: PASS.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, `No changes
  detected`.
- Targeted Task service/API/migration suite: PASS, **33/33** on a
  Django-created PostgreSQL test database in 7.673s; the database was
  destroyed.
- The migration rehearsal preserves legacy Task/Deliverable/Review rows,
  deliberately leaves legacy assignments inactive and Deliverable revisions
  null, and verifies the one-active-assignment constraint.
- Existing Authentication/API/Workspace regression group: PASS, **169/169** in
  87.783s.
- Final full PostgreSQL suite: PASS, **202/202** in 92.343s. The run also
  repeated dependency, Django system, and migration-drift checks; its test
  database was destroyed.
- Independent final code review: PASS; no unresolved implementation blocker.
- Documentation-scoped `git diff --check`: PASS; only existing LF-to-CRLF
  conversion warnings were emitted.

Development state is intentionally unchanged: `workspace.0003` is applied,
while `tasks.0002` and `reviews.0002` have **not** been applied. The latest
read-only post-check found `workspace.0001/0002/0003`, `tasks.0001` only and
`reviews.0001` only; 3 Users, 2 sessions, and zero Profile,
ProfileMembership, Workspace, WorkspaceMember, Task, TaskAssignment,
Deliverable, Review, or AuditLog rows. No test/rehearsal database or
`htp203` runner remains. No development or production migration is authorized
by this implementation checkpoint.

### Exact continuation / review gate

Stop at `IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL`.
The next allowed action is Owner review and, only under a separate explicit
authorization, a controlled development inventory/backup/plan/apply/smoke for
`tasks.0002` then `reviews.0002`. Do not apply either migration or start another
module from this checkpoint.

---

## Previous Snapshot - 2026-10-20 (HT-DB-P1-06)

### Current Phase

`PHASE 2.2 - API Architecture / controlled Workspace 0003 rollout`

### HT-DB-P1-06 — COMPLETE / OWNER REVIEW GATE

- Verified the existing development target as Compose container
  `hustlytasker_postgres`, PostgreSQL 16.14, database `hustlytasker_db`,
  loopback-only port 5432, and named volume `docker_postgres_data`.
- Immediately before apply, confirmed 27 migrations with `workspace.0002`
  applied and `workspace.0003` absent from both history and physical schema.
  Inventory was 3 active Users, 2 Django sessions, and zero checked business
  rows; no other PostgreSQL connection, unvalidated constraint, test database,
  or rehearsal database existed.
- Re-reviewed the tracked additive migration. `pip check`, Django system check,
  migration-drift check, global plan, and targeted plan pass; the plan contains
  only `workspace.0003`.
- Created the mandatory fresh pre-apply custom backup at
  `.local_backups/HT-DB-P1-06/hustlytasker_dev_pre_workspace_0003_20261020T073750Z.dump`
  (73,521 bytes; SHA-256
  `b004c1e102b0fedde5eea4418010d46fec76ea18788e59b937e7ef4cb63f7df4`).
  TOC listing, complete archive read, and container/host hash comparison pass.
- Full restore rehearsal passed in isolated database
  `htdb_p106_restore_20261020073818`; it reproduced the pre-migration state and
  was removed with cleanup verified.

`workspace.0003` was applied successfully to development at 2026-10-20
07:44:40 UTC. Development now has 28 migration records. All four new columns,
validated CHECK constraints, the conditional unique Profile/month index, and
lookup indexes exist and are valid/ready. Pre/post counts remain 3 active Users,
2 Django sessions, and zero checked business rows; no invalid lifecycle/period
value, duplicate period, unvalidated constraint, other session, or leftover
test/rehearsal database was found.

Post-apply verification is complete:

- `pip check`, Django system check, migration drift check, `migrate --check`,
  and Workspace `showmigrations` all PASS.
- **DEV SMOKE PASSED:** health `200`, CSRF bootstrap `200`, login without CSRF
  `403`, invalid login with valid CSRF `400`, and anonymous denial `403` across
  all current Profile/Workspace/membership read and mutation routes. No
  business row or session changed.
- **ISOLATED INTEGRATION TEST PASSED:** lifecycle/schema/concurrency 17/17 in
  13.341s; Workspace API/service/migration 140/140 in 76.602s;
  Authentication/API Foundation 29/29 in 7.327s; full PostgreSQL 169/169 in
  85.858s. Every temporary test database was destroyed.
- Final database inventory and integrity checks remain unchanged and clean;
  the disposable runner was removed. **NOT TESTED ON PERSISTENT DEVELOPMENT:**
  authenticated role/tenant/IDOR and successful lifecycle/member flows, because
  development has no business fixture; the isolated suites cover those cases.

No reverse migration, `--fake`, fixture, data deletion, source/API contract
change, or production action occurred. Stop at the Owner review gate. The next
roadmap candidate is `HT-TASK-P2-03`, but implementation requires separate
authorization and approval of Task states, reviewer authority, and payroll
trigger.

---

## Previous Snapshot - 2026-10-20 (HT-WORK-P2-02)

### Current Phase

`PHASE 2.2 - API Architecture / Workspace write foundation`

### HT-WORK-P2-02 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

The Owner-approved schema-dependent remainder is implemented in source and
verified on isolated PostgreSQL without applying the new migration to the
development or production database:

- Additive migration `workspace.0003_workspace_lifecycle_and_period` adds
  `Profile.status`, canonical `Workspace.period`, `Workspace.status`, and
  `WorkspaceMember.is_active`, together with status/period checks and lookup
  indexes. The `(profile, period)` uniqueness rule includes archived
  Workspaces. Existing legacy `NULL` periods are preserved for a controlled
  rollout; supported Workspace creation requires a first-of-month period.
- Profile Owner-only archive/restore and Profile Owner/Admin Workspace
  archive/restore endpoints are implemented. Archived Profile/Workspace data
  remains tenant-safe and readable, while ordinary metadata, child, and
  membership writes fail closed until restoration.
- Workspace create requires `period`; a non-first-day value is invalid and a
  duplicate monthly period, including an archived Workspace, maps to `409`.
  Period and lifecycle fields are server-controlled after creation.
- Workspace-member `DELETE` is a soft revoke that retains the assignment row
  and immediately removes effective access. A later eligible `POST` reactivates
  that same row instead of creating duplicate active/history rows. Role ceilings,
  same-Profile eligibility, row locking, and atomic AuditLog behavior remain in
  force.
- Profile and Workspace hard delete are not exposed. This task does not add
  Invitation, Profile creation, another business domain, or frontend work.

### Verification status

Final verification for the complete source implementation is current:

- `python -m pip check`: PASS.
- `python manage.py check`: PASS.
- `python manage.py makemigrations --check --dry-run`: PASS; no changes.
- Workspace PostgreSQL suite: PASS, 140/140 in 79.278s.
- Full PostgreSQL suite: PASS, 169/169 in 82.920s.
- The isolated `0002 -> 0003` migration rehearsal passed, preserving Task,
  Deliverable, and Review rows while applying lifecycle defaults without
  synthetic tenant mapping.
- `python manage.py migrate --check` exits `1` as expected because `0003` is
  intentionally pending on development. The reviewed migration plan is
  additive; this expected result is not a consistency failure.

The latest successful post-suite development inventory on 2026-10-19 recorded
the existing loopback Compose PostgreSQL 16.14 target with 27 migration rows,
`workspace.0002` applied, 3 Users, zero Profile, ProfileMembership, Workspace,
WorkspaceMember, Task, Client, Invoice, Payment, or AuditLog rows, and no
`test_%` database. A read-only container-state check on 2026-10-20 found that
existing PostgreSQL container stopped; it was not started, so no newer database
inventory is claimed. `workspace.0003` remains unapplied, no development
business/schema write occurred, and production was not contacted.

### Exact continuation / review gate

Stop at `PENDING DEVELOPMENT MIGRATION APPROVAL`. The exact next action is
Owner review of the source/migration/test evidence and, only if separately
approved, a controlled development rollout of
`workspace.0003_workspace_lifecycle_and_period` with fresh inventory, backup,
plan review, apply, and smoke verification. Do not apply `0003`, open another
feature task, or change production from this checkpoint.

---

## Previous Snapshot - 2026-10-19 (HT-DB-P1-05, superseded)

### Current Phase

`PHASE 2.2 - API Architecture / controlled development rollout`

### HT-DB-P1-05 - COMPLETE / OWNER REVIEW GATE

The condition-gated development rollout is complete without source changes,
business fixtures, data deletion, credential reset, or production access.

Completed and verified:

- Reconfirmed the existing local Compose PostgreSQL 16.14 development target,
  3 active Users, zero checked business rows, no orphan/unvalidated FK, and
  the pre-apply state of 26 migrations with `workspace.0002` unapplied.
- Revalidated the Git-ignored 66,721-byte custom backup by matching SHA-256,
  TOC listing, and full archive read. A full restore rehearsal into a uniquely
  named isolated database passed and the rehearsal database was removed.
- Used a process-only development configuration in disposable Python 3.12
  containers. No `.env` or secret file was created; no secret was printed or
  documented. Although the Owner's host shell reported a working venv, the
  Codex managed context exits 103 and reports its base path unavailable; the
  venv was not modified or replaced.
- Reviewed the exact additive migration plan and applied only
  `workspace.0002_profile_workspace_foundation` to development. Final state is
  27 migration rows with Profile/ProfileMembership tables and nullable
  `Workspace.profile_id`; constraints/indexes validate and all business counts
  remain zero. No tenant mapping was synthesized.
- Direct development smoke passed: health `200`; all four tenant routes and
  `/api/auth/me/` anonymous `403`; CSRF bootstrap `200`; invalid login without
  CSRF `403` and with valid CSRF `400`; no `500` and no new Django session.
- Current verification passed: `pip check`; Django system check;
  `makemigrations --check --dry-run`; `migrate --check`; targeted read API
  21/21; Authentication/API Foundation 29/29; full PostgreSQL suite 101/101.
  Final checks found no test/rehearsal databases or temporary containers.

Development after migration: 3 Users; 0 Profile, ProfileMembership, Workspace,
WorkspaceMember, Task, Client, Invoice, Payment, and AuditLog rows; 1 existing
Django session; zero unmapped Workspace/orphan/unvalidated constraints.

### Review Gate

Stop for Owner review. Do not begin Workspace Write, Membership, Invitation,
or frontend work. `HT-WORK-P2-02` is only the roadmap candidate after an
explicitly approved implementation scope; Invitation retains its account/email
binding dependency.

---

## Superseded Snapshot - 2026-10-19 (pre-migration blocker)

Historical only. The status and continuation instructions below were valid
before the Owner-authorized runtime recovery, migration apply, and verification.

### Current Phase

`PHASE 2.2 - API Architecture / controlled development rollout`

### HT-DB-P1-05 - BLOCKED BEFORE MIGRATION / OWNER ACTION REQUIRED

The owner conditionally authorized applying the existing
`workspace.0002_profile_workspace_foundation` migration to the development
database only, after identity, inventory, backup, plan, and risk gates.

Completed and verified at this checkpoint:

- Recovered a clean `main` worktree at `b8f1767`; did not redo P1-04.
- Independently identified the existing local Compose PostgreSQL target:
  `hustlytasker_postgres`, PostgreSQL 16.14, loopback port 5432, database
  `hustlytasker_db`, and preserved named volume `docker_postgres_data`.
- Confirmed 26 applied migration rows: `workspace.0001` is applied and
  `workspace.0002` is not. Profile/ProfileMembership tables and
  `Workspace.profile_id` are absent.
- Inventoried 3 active Users and zero Workspace, WorkspaceMember, Task,
  Client, Invoice, Payment, or AuditLog rows. Profile counts are not reported
  as zero because their tables do not yet exist. No checked orphan,
  unvalidated FK, or leftover test database was found.
- Re-reviewed unchanged `0002`: additive create/add/alter-to-`PROTECT` only,
  with no data migration, deletion, guessed mapping, or destructive operation.
- Created a Git-ignored PostgreSQL custom archive under
  `.local_backups/HT-DB-P1-05/`. Host/container SHA-256 matches; TOC listing
  and a complete `pg_restore` stream to `/dev/null` both pass. No restore was
  attempted.

Blocking condition:

- No ignored `.env` or complete approved runtime environment is available to
  the Django management-command runner, including a legitimate development
  `DJANGO_SECRET_KEY` and its database connection variables. The PostgreSQL
  service retains its own internal variables, but settings deliberately fail
  fast and do not auto-load `.env`.
- Host Python is unavailable and the old virtualenv points to a removed
  Python 3.12.5 installation. The cached Python image is usable only after the
  approved development configuration is restored.
- Per owner instruction, no secret/credential was generated, extracted,
  reset, or substituted. Consequently `migrate --plan`, migration apply,
  live API smoke, Django checks, and current regression suites have not run.
  Development remains on `workspace.0001`; schema and rows are unchanged.

### Review / Configuration Gate

Owner must restore the legitimate local development environment variables
without placing secrets in source, documentation, logs, or chat. Then resume
at `migrate --plan`, apply only `workspace.0002` if the plan still matches,
perform post-migration integrity checks, separate direct-development smoke
from isolated-test verification, and run all required regressions.

Do not begin Workspace Write, Membership, Invitation, or another task.

---

## Previous Snapshot - 2026-10-18 (HT-API-P1-04, superseded)

This historical snapshot records the completed P1-04 state before the owner
opened HT-DB-P1-05. Use the current snapshot above.

### Current Phase

`PHASE 2.2 - API Architecture`

### HT-API-P1-04 - COMPLETE / OWNER REVIEW GATE

The owner authorized the minimal Profile/Workspace read API after
`HT-RBAC-P1-03`. The implementation reuses its access contexts and selectors;
it does not create a parallel authorization system.

Completed in this task:

- Added four read-only tenant routes under `/api/v1/`: Profile list/detail and
  nested Workspace list/detail.
- Added minimal read serializers. Profile responses expose only `id`, `name`,
  `created_at`, and `updated_at`; Workspace responses add `profile_id`,
  `description`, and no owner/member/role/PII field.
- Added DRF permission adapters for an active authenticated identity, active
  Profile access, and effective Workspace read access. No new endpoint uses
  `AllowAny`; SessionAuthentication and global deny-by-default remain intact.
- Every list and object lookup starts from `profiles_visible_to()` or
  `workspaces_visible_to()`. Cross-Profile, wrong-parent, sibling,
  malformed, random, revoked, inactive, legacy-role, Profile-null, and
  transitional-owner cases fail closed without disclosing existence.
- Added bounded page-number pagination: default 20, client maximum 100, stable
  `created_at`/`id` ordering, and no client-controlled search/filter/order.
- Limited all four views to `GET`, `HEAD`, and `OPTIONS` and marked responses
  non-cacheable. Unsupported unsafe requests enforce SessionAuthentication/
  CSRF and tenant permissions first (`403`/`404` when those checks fail), then
  return `405` for an authorized request with valid auth/CSRF; no path changes
  Profile, Workspace, membership, or AuditLog data.
- Independent review identified a late membership-revocation race between DRF
  permission resolution and queryset evaluation. The shared view mixin now
  maps that stale access exception to the same generic JSON `404`, with a
  regression test for both Workspace list and detail.
- No authentication mechanism, model, schema, migration, service business
  rule, development row, or Docker resource changed.

Verification actually run against Django-created disposable PostgreSQL test
databases:

- Targeted `apps.workspace.test_api`: PASS, 21/21, including an explicit
  session-CSRF-before-`405` regression.
- Authentication and API Foundation regressions (`api apps.accounts`): PASS,
  29/29, including the existing SessionAuthentication/CSRF policy coverage.
- Final full PostgreSQL suite after all code/test changes: PASS, 101/101 in
  55.129s inside a disposable Python 3.12 container with the source mounted
  read-only; Django destroyed the disposable test database.
- `python -m pip check`: PASS.
- In-memory Python syntax compile for the new modules/tests: PASS.
- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes.
- Read-only migration plan still shows `workspace.0001_initial` applied and
  `workspace.0002_profile_workspace_foundation` unapplied in development.
- Post-test read-only verification found no leftover `test_%` database.
- Current local `.env` is absent and the historical Windows virtualenv points
  to a removed Python installation; verification was safely restored with the
  cached ephemeral Python image, without recreating PostgreSQL infrastructure.
- `git diff --check`: PASS (only existing LF-to-CRLF conversion warnings).
  Strict UTF-8/no-BOM/no-NUL/code-fence/trailing-whitespace QA and
  secret-assignment scan: PASS for all 17 changed/new code/documentation files.

Known boundary: the source migration was exercised on disposable test
databases that Django destroyed, but development still has only
`workspace.0001` and no Profile table.
The new routes must not be exercised there until the owner separately approves
inventory, backup, the existing `0002` rollout, and a development smoke test.
No endpoint required by this read-only task remains missing; Workspace writes,
membership management, Invitation, and downstream business APIs are explicitly
outside scope.

### Review Gate

Stop at the `HT-API-P1-04` owner review gate. Do not apply `workspace.0002`,
open write/Invitation APIs, or begin another roadmap task automatically.

---

## Previous Snapshot - 2026-10-18 (HT-RBAC-P1-03, superseded)

This historical snapshot describes the completed access/service foundation
before the owner authorized HT-API-P1-04. Use the current snapshot above.

### Current Phase

`PHASE 2.2 - API Architecture`

### HT-RBAC-P1-03 - COMPLETE / OWNER REVIEW GATE

The owner delegated the remaining RBAC design decisions to the Technical
Advisor. `HT-RBAC-DESIGN-P0-01` is therefore `COMPLETE / ACCEPTED - APPROVED BY
OWNER DELEGATION`; its 14 delegated decisions are recorded in
`RBAC_DESIGN.md` and `DECISION_LOG.md`.

Implemented in this task:

- Added `backend/apps/workspace/access.py` with immutable, resolver-produced
  Profile/Workspace contexts, tenant-scoped Profile/Workspace selectors, and
  fail-closed read/edit/member-management capability checks.
- Context resolution requires a current active User and active
  ProfileMembership. Profile Owner/Admin see mapped Workspaces in their own
  Profile; ordinary Profile Members see only Workspaces with an effective
  explicit WorkspaceMember role.
- Kept the existing schema vocabulary with the approved compatibility map:
  WorkspaceMember `ADMIN` = Workspace Admin, `MEMBER` = Editor, `VIEWER` =
  read-only Viewer. Legacy `OWNER` is not assignable and grants no capability
  through the new boundary.
- Hardened contexts against direct construction, `dataclasses.replace()` role
  escalation, stale account/Profile membership, and stale Workspace role.
- Refactored `update_profile_membership()` to authorize Profile scope before
  resolving the target. Profile Admin may manage current ordinary Members only;
  Owner changes and the last-active-owner invariant remain locked and audited.
- Refactored `add_workspace_member()` to accept a scoped
  `target_profile_membership_id`, revalidate authority under locks, require an
  active same-Profile membership and active User, enforce role ceilings, and
  translate duplicate/concurrent adds to a stable domain conflict. Audit is
  written only after a successful mutation.
- No API route, authentication mechanism, model, schema, or migration changed.
  Workspace/Invitation APIs remain unopened.

Verification on PostgreSQL 16 using Django-created disposable test databases:

- Local Python 3.12 environment synchronized to Django 6.1.2 and DRF 3.18.3;
  `pip check`: PASS.
- Python compile check for access/services/tests: PASS.
- `manage.py check`: PASS, no issues.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- Final targeted `apps.workspace` suite after independent-review hardening:
  PASS, 51/51.
- Final full suite: PASS, 80/80, including all 19 Authentication and 10 API
  Foundation regressions.
- The earlier pre-hardening runs also passed 49/49 targeted and 78/78 full;
  they are not used as the final acceptance evidence.
- Read-only development inventory reconfirmed 3 Users and 0 business rows.
  Only `workspace.0001_initial` is applied; `workspace.0002` remains unapplied.
- Post-test read-only verification found no leftover `test_hustlytasker_db` and
  the Profile table remains absent from development, as expected before `0002`.
- `git diff --check`: PASS (only existing LF-to-CRLF conversion warnings).
  Strict UTF-8/no-NUL/code-fence QA and secret-assignment scan: PASS for all
  changed code/documentation files.

Known boundaries:

- Direct ORM, bulk, raw-SQL, or unsafe Django Admin writes can bypass service
  invariants. Tenant managers must use reviewed services; Django Admin remains
  a platform-superuser surface until a tenant-scoped Admin exists.
- Direct `User.is_active` mutation still lacks the approved cross-Profile
  last-owner/session-revocation lifecycle service. This task rechecks inactive
  accounts but does not implement global account deactivation or session purge.
- There are no Client, Finance, Audit, Task, Review, Invitation, or Workspace
  API selectors yet. Concrete reviewer role/workflow states remain deferred.
- `workspace.0002` is intentionally not applied to development. No development
  row was created, changed, deleted, or backfilled.

### Review Gate

Stop at the `HT-RBAC-P1-03` owner review gate. Do not apply `workspace.0002`,
open Workspace/Invitation APIs, or begin the next task in this worktree without
owner review.

---

## Previous Snapshot - 2026-10-17 (superseded)

This superseded snapshot is retained only as development history and may
describe earlier phases. Use the current 2026-10-18 snapshot above.

### Current Phase

`PHASE 2.2 - API Architecture`

### Audit Result

- Git branch `main` and the local `origin/main` ref both point to `5e89971`.
  The current worktree contains only the nine modified documentation files for
  this reconciliation, as inventoried in `HANDOVER.md`; all are being preserved.
- Read-only PostgreSQL development inventory, reconfirmed on 2026-10-17, found
  0 business rows and 3 User
  rows. It contains the initial migrations; the new Workspace `0002` has not
  been applied there and the named volume is preserved.
- `makemigrations --check --dry-run` reports no model/migration drift relative
  to the new migration in source.
- Authentication foundation, the deny-by-default API policy, and the
  `/api/health/` liveness endpoint are implemented and verified on PostgreSQL;
  Workspace/RBAC and business APIs are not implemented.
- `HT-DATA-P2-01` architecture/design and all 11 decision groups were approved
  by the owner on 2026-10-16. `PROFILE/WORKSPACE SCHEMA FOUNDATION` is now
  complete in source and verified on disposable PostgreSQL test databases. It
  remains unchanged; development `0002` is still unapplied by design.
- `HT-RBAC-DESIGN-P0-01` has completed its design deliverables and is
  `DESIGN READY — PENDING OWNER APPROVAL`. The capability matrix,
  tenant-scoped query/service boundary, invitation contract, proposed API,
  isolation tests, dependency order, and 11-group reconciliation table are
  recorded in `RBAC_DESIGN.md`. All 11 approved groups now match; only seven
  grouped decisions remain for owner review. No API, model, migration,
  permission code, or database row changed.
- Root `AGENTS.md` now defines mandatory documentation/checkpoint/handover
  rules. `documentation/HANDOVER.md` is the continuation entry point.
- Frontend and production deployment/CI are not started.
- `reference/original_document/` describes the legacy Next.js/Prisma system and historical Spring migration research; it is not the active Django architecture.

Detailed status and evidence:

- `documentation/REQUIREMENT_STATUS.md`
- `documentation/PROJECT_ROADMAP.md`

### Completed In This Session

`HT-OPS-P0-01 - Backend dependency synchronization`

- Normalized `backend/requirements.txt` from malformed UTF-16/double-BOM content to UTF-8.
- Updated Django `6.1` to security patch `6.1.2`.
- Updated Django REST Framework `3.15.0` to `3.18.3`, which supports Django 6.1.
- Kept all other dependency pins unchanged.

Verification in an isolated Python 3.12 container:

- Fresh dependency install: PASS.
- `pip check`: PASS.
- Django/DRF version assertions: PASS.
- `manage.py check`: PASS.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- `manage.py migrate --check`: PASS, no unapplied migrations.
- Legacy `/api/test/` smoke test: PASS at the time of HT-OPS-P0-01; this route is later replaced by `/api/health/` in HT-API-P0-03.
- Django test discovery: executed successfully but found 0 tests; this is a coverage gap, not a test-suite pass.
- The initial `manage.py check --deploy` failure was resolved by `HT-SEC-P0-02` using an explicit production-like environment.

`HT-SEC-P0-02 - Baseline safe configuration`

- Removed the tracked Django secret and PostgreSQL credential literals from active configuration.
- Added strict environment parsing and explicit development/production behavior for Django, PostgreSQL, hosts, CSRF, HTTPS/cookies/HSTS, and Django 6.1 mailers.
- Added a clean, trackable root `.env.example`; real secret fields remain blank.
- Changed PostgreSQL Compose variables to required interpolation and loopback-only binding by default while preserving the existing named volume.
- Replaced the placeholder README setup with an explicit PowerShell onboarding flow.
- Did not add CORS, authentication, RBAC, business APIs, models, or migrations.

Verification in an isolated Python 3.12 container and the existing development PostgreSQL instance:

- Missing secret/database password, invalid boolean/integer, production debug, wildcard production host, and conflicting SMTP TLS/SSL checks: PASS (failed fast as expected).
- `pip check` and development `manage.py check`: PASS.
- Production-like `manage.py check --deploy --fail-level WARNING`: PASS with explicit HTTPS, secure-cookie, HSTS, host, and SMTP values. The development `.env.example` is not a production config.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- `manage.py migrate --check`: PASS, no unapplied migrations.
- Development server startup and legacy `GET /api/test/`: PASS at the time of HT-SEC-P0-02; this route is later replaced by `/api/health/`.
- PostgreSQL remained on named volume `docker_postgres_data` with 8 domain migrations, 23 public tables, and no leftover test database.

`HT-AUTH-P0-01 - User Authentication Foundation`

- Audited the current `AbstractUser` model, migrations, related foreign keys,
  admin, documentation, and legacy reference material.
- Kept the User model unchanged and did not create Profile, Workspace, schema,
  or migration changes.
- Chose Django server-side sessions with DRF `SessionAuthentication`; removed
  implicit HTTP Basic authentication and set DRF permissions deny-by-default.
- Added CSRF bootstrap, register, login, logout, and current-user endpoints
  under `/api/auth/`.
- Applied Django password validation and hashing, neutral invalid-login errors,
  inactive-user blocking, input length limits, no-cache identity responses,
  current-session revocation, and scoped authentication throttles.
- Defaulted `DRF_NUM_PROXIES` to zero so client-supplied forwarding headers do
  not bypass throttle identity before a trusted proxy chain is configured.
- Fixed the existing User admin change form by making auto-managed timestamps
  readonly.
- Documented the endpoint/CSRF contract and the session architecture decision.

Verification in a Python 3.12 container against PostgreSQL 16:

- `pip check`: PASS.
- `manage.py check`: PASS, no issues.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- `manage.py migrate --check`: PASS, no unapplied migrations.
- Full Django suite: PASS, 19/19 tests.
- Development server startup and `GET /api/auth/csrf/`: PASS (`200`, CSRF cookie and token returned).
- Temporary test database and backend smoke container were removed; the existing PostgreSQL data volume was preserved.

`HT-API-P0-03 - API deny-by-default and health endpoint`

- Kept DRF globally deny-by-default with `SessionAuthentication` and
  `IsAuthenticated`.
- Added a regression guard requiring every route in the API URL tree to use a
  DRF view and limiting explicit anonymous access to the reviewed public
  allowlist.
- Replaced the legacy `/api/test/` Django view with the public
  `/api/health/` DRF liveness endpoint.
- Kept health independent of authentication, throttling and database queries;
  it returns only `{"status": "ok"}` with no-store caching.
- Limited health to `GET`, standard `HEAD`/`OPTIONS`, and `405` for mutation
  methods and `TRACE`.
- Did not add Workspace/Profile code, RBAC, a business endpoint, model or
  migration changes.

Verification in a Python 3.12 container against PostgreSQL 16:

- `pip check`: PASS.
- `manage.py check`: PASS, no issues.
- `manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- `manage.py migrate --check`: PASS, no unapplied migrations.
- Full Django suite: PASS, 29/29 tests (19 authentication and 10 API
  health/policy tests).
- Development server startup: PASS.
- `GET /api/health/`: PASS (`200`, `application/json`, exact
  `{"status":"ok"}` payload and `Cache-Control: no-store`).
- `POST /api/health/`: PASS (`405`, `Allow: GET, HEAD, OPTIONS`); legacy
  `/api/test/`: PASS (`404`).
- Authentication regression smoke: `GET /api/auth/csrf/` returned `200` with
  a CSRF cookie.
- The temporary test database and smoke container were removed; the existing
  PostgreSQL named volume was preserved and its container was returned to its
  prior stopped state.

`Documentation and permanent handover foundation`

- Added root `AGENTS.md` with mandatory startup evidence checks, dirty-worktree
  preservation, architecture/scope rules, truthful task states, verification,
  per-document update routing, and checkpoint requirements.
- Added `documentation/HANDOVER.md` as the current, chat-independent transfer
  checkpoint for developers and future Codex sessions.
- Kept existing documentation files as the domain sources of truth rather than
  creating duplicate progress, roadmap, schema, API, or decision documents.
- No secrets or private environment values were copied into documentation.

`HT-DATA-P2-01 - Workspace architecture and ownership design`

- Audited all active Django models and initial migrations, current session/DRF
  permissions, API routes, Django Admin exposure, product requirements, and
  the relevant legacy discovery/security diagrams.
- Classified sources correctly: `ORIGINAL_REQUIREMENTS.md` is the
  capability-level requirement; `reference/original_document/00-discovery/`
  is legacy behavior evidence; the Spring material is historical research;
  current Django source remains authoritative for implementation state.
- Verified that Profile, invitation, Project, Workspace/RBAC API, and
  tenant-aware services do not exist. Current Workspace ownership has two
  unsynchronized truths (`Workspace.owner` and OWNER membership).
- Verified that Task derives Workspace scope, while Client/ShareLink,
  Invoice/Payment, and AuditLog currently lack a reliable tenant path.
- Verified that creator/assignee/commenter/uploader/reviewer membership in the
  Task Workspace is not enforced and several CASCADE relationships can erase
  business history when an actor/owner is deleted.
- Compared Workspace-root, Profile-root, and Profile-only options. Recommends
  Profile/Organization as tenant root, Workspace as operational/monthly child,
  User as global identity, Client/CRM as Profile-owned, and Task/Review as
  Workspace-owned.
- Proposed separate Profile and Workspace membership layers, internal roles
  separated from Client/Guest token principals, deny-by-scope query rules,
  actor membership invariants, last-owner transactions, and tenant-aware audit
  context.
- Produced a staged additive migration/backfill plan. Existing Workspace and
  especially Client/AuditLog rows require an owner-approved mapping; the plan
  forbids guessing tenants, editing `0001_initial.py`, or adding non-null
  constraints before reconciliation.
- Recorded the full proposal and decisions in `DECISION_LOG.md`, and current
  versus proposed schema in `DATABASE_SCHEMA.md`.
- The design task itself did not modify a model, migration,
  User/authentication mechanism, API, PostgreSQL row, Workspace permission, or
  frontend code. The separately authorized schema-foundation task below now
  implements its first additive portion.

Verification rerun on 2026-10-16 in an isolated Python 3.12 container against
PostgreSQL 16:

- `pip check`: PASS.
- `manage.py check`: PASS, no issues.
- `manage.py makemigrations --check --dry-run`: PASS, no model/migration drift.
- `manage.py migrate --check`: PASS, no unapplied migration.
- Full regression suite: PASS, 29/29 tests (19 authentication and 10 API
  health/policy tests).
- Django created and destroyed only the disposable `test_hustlytasker_db`;
  no application migration or PostgreSQL application row was changed.

Task status:

`COMPLETE / ACCEPTED — 2026-10-16`

The owner approved all 11 architecture decision groups. The intentionally
deferred details are listed below and do not authorize their future APIs or
workflows.

`PROFILE/WORKSPACE SCHEMA FOUNDATION — COMPLETE`

Implemented in source:

- Added `Profile` as company/team tenant root and `ProfileMembership` with
  protected User/Profile links, `OWNER`/`ADMIN`/`MEMBER`, active state,
  partial uniqueness for active Profile/User membership, inactive history, a
  role check, and tenant lookup indexes.
- Added transitional nullable `Workspace.profile` and changed
  `Workspace.owner` deletion from `CASCADE` to `PROTECT`. Validated new
  Workspaces require a Profile and an active Profile Owner/Admin as their
  transitional owner.
- Added persistence validation for Workspace and WorkspaceMember, prevents a
  mapped Workspace from changing Profile, and validates every legacy member
  before an explicit null-to-Profile mapping.
- Existing legacy Workspace saves lock the persisted row before accepting a
  null Profile, preventing a stale save from undoing a concurrent mapping.
- Added atomic Profile creation plus initial Owner, transactional/locked
  Profile membership updates, multiple-owner support, last-active-owner
  protection, Admin restrictions on Owner changes, a requirement to reassign
  transitional Workspace ownership before removing manager status, and
  membership AuditLog events.
- Added an audited service for Profile Owner/Admin to add an existing active
  Profile member directly to a Workspace. Generic membership reactivation is
  reserved for the future invitation-acceptance flow.
- Added additive `workspace/0002_profile_workspace_foundation.py`; no existing
  `0001_initial.py` was modified.
- Added model/service/concurrency tests and a populated migration test that
  preserves Workspace → Task → Deliverable → Review relationships without
  guessing a Profile for legacy rows.
- Added cross-Profile negative service tests proving that Profile manager
  authority never transfers to another Profile.

Data and migration evidence:

- Read-only development PostgreSQL inventory: 0 business rows, 3 User rows.
- No Profile/backfill row was synthesized.
- `0002` ran only on disposable PostgreSQL test databases, including empty and
  populated cases. It has not been applied to the development database.

Current verification (rerun on 2026-10-17):

- Targeted `apps.workspace`: PASS, 32/32.
- `manage.py check`: PASS.
- `manage.py makemigrations --check --dry-run`: PASS.
- `pip check`: PASS.
- Full PostgreSQL suite after this schema change: PASS, 61/61. This includes
  all 19 Authentication and 10 API Foundation regression tests.

Known service boundary, not hidden as a database guarantee:

- Normal Workspace/WorkspaceMember writes and membership services share
  Profile-first locking, including concurrent legacy mapping and manager-role
  transitions. Bulk/raw writes can bypass this boundary.
- Direct `User.is_active` changes and direct ProfileMembership ORM mutation can
  still bypass the foundation service's stronger effective-Owner check. The
  approved invariant is at least one active Owner membership; account activity,
  deletion, and session mechanics remain open. No account lifecycle change was
  made in this task.
- Inactive Profile membership does not erase WorkspaceMember history. Future
  permission code must check both layers, and invitation/rejoin policy must
  decide whether old Workspace access is restored.

Approved target not implemented in this task: Invitation/API, Project,
Client/Profile and Finance migrations, public-link replacements, soft delete,
tenant query scoping/full RBAC, detailed Task/Review workflow, and frontend.

`HT-RBAC-DESIGN-P0-01 — DESIGN READY / PENDING OWNER APPROVAL`

Completed as design evidence:

- Classified outsource requirements, the 11 approved decisions, current
  Django source, legacy reference evidence, proposals, and open decisions so
  proposed permissions cannot be mistaken for accepted policy.
- Produced an action-level matrix for Profile Owner/Admin/Member and proposed
  Workspace Admin/Member/Viewer behavior. Existing Workspace `OWNER` and
  `VIEWER` enum values are not treated as approved capabilities.
- Defined fail-closed request context, scoped querysets, same-tenant input
  validation, `404`/`403`/generic `400` IDOR behavior, transaction/lock order,
  and controls for ORM, bulk, jobs, and Django Admin bypass paths.
- Found that `update_profile_membership()` globally resolves membership ID,
  while `add_workspace_member()` globally resolves Workspace ID and accepts an
  already-resolved unscoped target User before actor scope. No route exposes
  them today; both boundaries must be refactored before an API is opened.
- Defined a Profile-only invitation lifecycle with authenticated recipient
  binding, CSRF, hashed one-time token, terminal states, concurrency/audit
  rules, planned routes, and negative tests. Workspace direct-add remains a
  separate operation available only after active Profile membership.
- Reconciled the full design against all 11 approved decision groups. Initial
  findings: groups 1–3/5/10 `MATCH`; group 4 `CONFLICT` because “usable Owner”
  had been over-labeled as approved; groups 6–9/11 `NOT DOCUMENTED` in part or
  whole. Corrected the label and added every missing approved boundary; all 11
  now read as `MATCH`. The review gate is reduced from 16 granular questions
  to seven genuinely open decision groups.
- Reconfirmed development PostgreSQL read-only: only `workspace.0001` is
  applied; 3 Users and 0 business rows; `workspace.0002` was not applied and
  Docker was returned to its prior stopped state.
- Documentation QA after reconciliation: required 11-row comparison and seven
  open-group structure PASS; UTF-8/no-NUL/code-fence checks PASS for all nine
  affected files; secret-pattern scan found no matches; `git diff --check`
  PASS with only line-ending conversion warnings.
- No backend implementation test was rerun for this documentation-only task.
  The local venv points to a missing Python 3.12 installation and neither
  `py` nor `python` is installed on PATH. No replacement environment or new
  container was created. The latest actual source evidence remains targeted
  32/32 and full PostgreSQL 61/61 from the schema-foundation checkpoint.

Implementation deliberately not performed: no source model/service/API or
migration was edited, no migration was applied, and no data was written. The
current runtime API documentation therefore remains unchanged.

### Review Gate

`HT-AUTH-P0-01`, `HT-API-P0-03`, and the `HT-DATA-P2-01` architecture decision
are complete. The schema foundation implementation and verification are also
complete. The owner then authorized this design task only.

Stop at `HT-RBAC-DESIGN-P0-01` owner review. Do not begin Workspace API, RBAC
implementation, Invitation migration/API, Project/Client/Finance migration,
Task workflow, or another business API. Do not apply `0002` without a separate
approved operational step, repeated inventory, and backup policy appropriate
to the target environment.

### Decisions Required Before RBAC Implementation

The 11 approved architecture groups are reconciled and must not be reviewed
again. Owner review is limited to these seven groups:

1. Workspace role vocabulary and action ceiling.
2. Profile Admin and Profile/Workspace lifecycle authority.
3. Workspace Member Task visibility and contributor-membership requirement.
4. Profile/account/membership lifecycle: self-service eligibility/limits,
   leave/rejoin/history, and deactivate/delete/session mechanics. Atomic
   initial-Owner creation already exists and is not an open decision.
5. Invitation identity/onboarding and role/management ceiling, including
   whether an invitation can ever request `OWNER` (proposal: no).
6. Invitation TTL/reinvite/throttle/delivery, inviter revalidation, record/PII
   retention, and optional combined UX that preserves acceptance then direct-add.
7. Non-enumerating error/`409` and platform-operator/Django Admin policy.

Other genuine decisions remain scoped to their later tasks: authentication
activation method; Invoice numbering/billing; Client Portal/Guest Review exact
capabilities/account linking/default expiry; retention/legal hold/purge; and
exact Task/Review states, approvers, and payroll trigger. A tenant row that
cannot be mapped becomes an evidence-specific migration blocker if encountered;
the already-approved rule is not to guess.

---

## Historical Log - Superseded Snapshots

The remaining sections are preserved from earlier development phases. They are
not current tasks or instructions; use the snapshot and review gate above as
the source of truth.

### Historical Current Phase

PHASE 2.2 - API Architecture


### Historical Latest Completed Phase

PHASE 2.1 - Django REST Framework Foundation


Completed:

- Added Django REST Framework.
- Created API routing.
- Created the legacy `/api/test/` endpoint (later replaced by `/api/health/`).
- Verified API response.


### Historical Next Step

PHASE 2.2

Tasks:

- Design API structure.
- Define serializers.
- Define authentication flow.
- Define permission system.
- Prepare API documentation.


### Historical Overall Progress

10%


---

# Historical foundation notes — superseded by the current snapshot above


## Documentation

[x] Imported original system documents

[x] Created requirement documentation

[x] Created developer profile

[x] Created architecture documentation

[x] Created technology decision document


## Project Management

[x] Created project folder structure

[x] Initialized Git repository

[x] Connected GitHub repository

[x] Created first commit


---

# Current Status

The project is ready for development.


---

# Next Phase

## Phase 1 - Development Environment Setup


Tasks:

- Setup Python environment.
- Install Django.
- Create Django project.
- Setup PostgreSQL.
- Connect Django with PostgreSQL.
- Create Docker environment.


---

# Known Issues

# Historical initial backend progress


## Historical current phase

Phase 1.6 - Database Schema Design


## Completed Today

[x] Setup Django environment

[x] Setup PostgreSQL using Docker

[x] Connect Django with PostgreSQL

[x] Create modular Django app structure

[x] Fix Django app namespace configuration

[x] Create initial database schema

[x] Improve DATABASE_SCHEMA.md


## Current Status

Backend foundation completed.

Database design is currently being reviewed before creating Django Models.


## Current Working Files

Modified:

- documentation/DATABASE_SCHEMA.md
- documentation/PROGRESS.md


Created:

- backend/apps/
- backend/common/


## Next Step

PHASE 1.6.3:

Create Entity Relationship Diagram (ERD)

Then:

PHASE 1.7:

Create Django Models


## Known Issues

## Phase 1.8 Completed

Completed:
- Django models created
- Initial migrations generated
- PostgreSQL schema created
- Custom User Model verified
- Database relationships verified

Next:
PHASE 1.9 Django Admin + CRUD Testing

PHASE 2.1 completed.

DRF foundation created.
