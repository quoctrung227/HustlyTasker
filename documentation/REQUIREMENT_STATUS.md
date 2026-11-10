# HUSTLYTASKER REQUIREMENT STATUS

Last updated: 2026-11-10

## Quy ước đánh giá

- `COMPLETE`: đã triển khai và được kiểm chứng bằng lệnh chạy hoặc test phù hợp.
- `ACCEPTED`: quyết định kiến trúc/nghiệp vụ đã được owner phê duyệt; không tự
  đồng nghĩa mọi phần của kiến trúc đích đã được implement.
- `PARTIAL`: đã có một phần code/schema nhưng chưa hoàn thành luồng nghiệp vụ hoặc chưa đủ test.
- `DESIGN READY — PENDING APPROVAL`: deliverable thiết kế đã đủ để review nhưng
  còn quyết định của owner và chưa cho phép implementation; không đồng nghĩa
  với `COMPLETE` hay `Accepted`.
- `NOT STARTED`: chưa có implementation trong source hiện hành.
- `BLOCKED`: không thể tiếp tục nếu chưa có quyết định hoặc dependency bắt buộc.
- `UNKNOWN`: chưa đủ bằng chứng để kết luận.

Source of truth cho trạng thái là source code, migration đã áp dụng và kết quả kiểm thử. `documentation/` mô tả định hướng hiện hành. `reference/original_document/` là audit của hệ Next.js/Prisma cũ và chỉ được dùng để kế thừa business rules, không phải yêu cầu đổi Django sang Spring Boot hoặc công nghệ khác.

Current checkpoint: **HT-FE-TASK-ASSIGNEE-NAME-FIX-01 — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE**.

| Assignee name fix requirement | Verified status |
|---|---|
| Root cause | Marked anonymous GET goes only to old13:49 --noreload backend, started before14:34 display_name code; second15:05 process did not replace it |
| Correct source of name | Existing server-scoped full name→safe username→safe fallback; no assignment=NULL; frontend preserves field and invalidates current scope |
| Correction | Only verified project servers restarted; one fresh backend handles direct/proxy GETs. Existing launcher gets exclusive occupied-port preflight; no automatic process killing |
| Tests | Fresh isolated PostgreSQL59, frontend122 and launcher15 PASS/exit0; typecheck/lint/Django/model/graph checks PASS |
| Development API diagnostic |4existing Task list/detail actual GET handlers checked in-process/read-only with legitimate Owner actors; names match. No authenticated browser/session claim |
| Preservation | All29-table snapshots unchanged;37migrations/5Users/2Sessions/4Tasks, tasks.0005APPLIED/ai.0002UNAPPLIED. No schema/business writes, pay/RBAC changes or AI/SMTP calls |
| Review | Owner Ctrl+F5 existing Task; manual verification pending. Full suites/build/browser not rerun; no React/Django business code changed |

Historical checkpoint: **HT-FE-TASK-UX-REFINEMENT-01 — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE**.

| Current Task UX requirement | Verified source/evidence |
|---|---|
| Stabledescription | Task-only24remdesktop/fixedheading/nativekeyboardscroll; mobilemax24remnaturalshortheight; complete26ktext/unbrokentokens retained |
| Linked product submission | Reusefile_url500/newHTTP(S)-onlyvalidation; legacyread/revisions unchanged, safeexternalanchor/no fetch; no schema/migration |
| UTCfilterpair | Samecolumn from→to nativefieldset/actions, sameparams/UTCmeaning/validation |
| Assigneename | Current-scoped readonlydisplay_name string/null, fullname→safeusername→generic; noUUIDlabels/perTaskroster; unavailableNULL, noaction/paygrant |
| Verification | Fresh targeted191/full996PostgreSQL/full1123frontend/quality0;37/37realbrowsercases across8suites PASS/actualexits0. Four-sizeaxe0/keyboard/screenshots verified; HANDOVER owns run IDs |
| Development | READONLYbefore/after29-tabledata/schema/history/sequence fingerprints identical;37records/3Tasks/2Deliverables/5Users/2Sessions retained. tasks.0005APPLIED/ai.0002UNAPPLIED. No fixtures/mutationtests |
| Local/source | Existing Django8000/Vite5173 started;9/9anonymousGET and read-only ORM PASS.618originals/22frozen hashes/59initialdirtypaths preserved,71finaldirtypaths;0ownedtestresources |
| Reviewgate |13documents synchronized; OwnerUIreview pending. No migration candidate, automatic nexttask or deploy |

Historical checkpoint: **HT-DB-TASK-BRIEF-ROLLOUT-01 — DEVELOPMENT MIGRATION COMPLETE /
OWNER UI ACCEPTANCE PENDING**.

| Current rollout requirement | Verified status |
|---|---|
| Correct target/plan | PASS original development container/volume/loopback, config.settings/dev; exact forward tasks0005 only |
| Backup/rehearsal | PASS external restricted126444bytecustomarchive/SHA256/list/fullread/restore/isolatedtargetedmigration; ownedtargetsremoved, backupretained |
| Development execution | APPLIED tasks.0005, exit0, history36→37only; ai.0002UNAPPLIED and governance tables absent |
| Schema/data | PASS5nullableTaskfields/exactnonnegativeCHECK; alllegacyTaskfields and otherbusinessrows preserved;2Tasks/0Subtasks/5Users/2Sessions retained |
| Backend/connectivity | PASS system/modeldrift/targetedplanempty/TaskORM2; normal Django+Vite onloopback,9anonymousGETsmokesPASS; no businessmutations |
| Acceptance boundary | OwnerUImanualCreate/Edit/18:30/assignment/payredaction pending; no fullsuite rerun, liveprovider/mail/production claim |

Historical checkpoint: **HT-FE-TASK-COMPENSATION-RBAC-01 — IMPLEMENTATION COMPLETE /
PENDING DEVELOPMENT MIGRATION APPROVAL**.

| Current compensation requirement | Source-backed status |
|---|---|
| Owner-approved visibility | Current Task-readable Profile OWNER/ADMIN, Workspace ADMIN, effective ACTIVE Task assignee; others receive NULL |
| Write authority | Existing manager-only metadata services unchanged; assigned Editor has no pay-write grant |
| Stale authority | Live SQL membership/User/role/assignment predicates; no history/Viewer-downgrade/staff/context/query override |
| API/HTML projection | Common Task DTO list/detail/subtasks/create/PATCH/assign/start; inspection-only Admin excludes pay; other actual response contracts have no pay |
| React privacy | NULL hides card; response replaces old cache; existing auth/tenant cleanup and URL/deadline/draft rules retained |
| Validation | Final targeted164/full969 PostgreSQL, frontend159/full1067, quality0; Brief4+regression39=43real browsers PASS/actual exits0/ownedcleanup. Four-sizeaxe0/keyboard/reflow/PNG inspection. Initial unchanged Workspace focus failure and subsequent passes retained |
| Migration/development | No model/migration changes/apply; tasks.0005 and ai.0002 remain UNAPPLIED, no development fixtures/website acceptance |
| Preservation/review | All29-table data/schema/history/sequences/cluster fingerprints identical13:17:12Z except connections;36migrations/5Users/2Sessions/Owner rows retained.617originals/12source hashes intact,12docs updated,0remaining test resources. STOP at Owner review |

Historical checkpoint: **HT-FE-TASK-BRIEF-24H-VI-01 — CANDIDATE IMPLEMENTATION COMPLETE /
PENDING DEVELOPMENT MIGRATION APPROVAL**.

| Current Task work-brief requirement | Actual scope/evidence |
|---|---|
| Optional documents/pay | Implemented4 nullableHTTP(S) URL2048 fields + exact numeric18,0 wholeTaskVND; digit-string DTO/null; strict protocol/integer checks |
| Permission policy | Existing Task readers includingViewer see pay; only existing managers create/edit; no assignment/payroll/tenant bypass |
| Date/time | ControlledVIcalendar/dd/mm/yyyy and00–23/00–59 selects; local→UTC unchanged; unchanged edit omitted; old AI helpers preserved |
| Ordinary hierarchy UI | Controls/queries/labels removed; all stored children/direct routes/API/AIproposal hierarchy remain, no data deletion |
| Current tests | Targeted132/full937PostgreSQL/Python0; fullfrontend1047,quality0; final Brief4+regression43=47real browsers PASS/actual exits0/ownedcleanup; four-sizeaxe0/keyboard/focus/reflow; earlier failures retained |
| Migration gate | tasks.0005candidate only, not development applied; source Task paths need columns before reload/manual use. ai.0002unapplied; no full development E2E claimed |
| Preservation | VERIFIED all29-table fingerprints/schema/history/sequences unchanged12:34:44Z;36migrations/5Users/2Sessions andOwner rows retained;778originals/31finalsource hashes, previous30dirty paths preserved;0resources across15runs |

Historical checkpoint: **HT-FE-WORKSPACE-INHERITANCE-01 — IMPLEMENTATION COMPLETE /
OWNER REVIEW GATE**.

| Approved inheritance requirement | Current evidence |
|---|---|
| Exact month semantics | VERIFIED existing canonical period+unique Profile/month; current configured timezone UTC; never latest(created_at) |
| Role snapshot/first creation | COMPLETE optional source or confirmed initial MEMBER list, atomic services/audits, legacy omission manual; final real UI4/4 |
| Safe current onboarding | COMPLETE after accept only, exact ACTIVE current period, no existing row revival/past/future grants; concurrency/rollback/rejoin/month-boundary tests |
| RBAC/tenant security | VERIFIED existing Profile OWNER/ADMIN authority and grant ceilings; targeted132/full905 PostgreSQL, frontend955 and24 real browsers PASS/actual exits0 |
| Source/DB preservation | VERIFIED772 originals/19 frozen source hashes, no unrelated changes; full29-table data/schema/history/sequences exact11:12:55Z,36 migrations,ai.0002 unapplied |
| SMTP | Owner reports Gmail working; not retested/reconfigured here; no external email authorized |
| Final acceptance | IMPLEMENTATION COMPLETE; all current checks/owned cleanup pass,11docs synchronized; manual Owner acceptance/genuine Gmail not claimed, no next task/deploy |

Historical checkpoint: **HT-FE-INVITATION-DELIVERY-FIX-01 — APPLICATION FIX VERIFIED /
REAL EMAIL CONFIGURATION PENDING OWNER**.

| Current Invitation delivery requirement | Actual status / evidence |
|---|---|
| Root cause of Owner503 | VERIFIED no-send Django preflight: development console backend intentionally refused; SMTP host/username/password absent |
| Owner request persistence | READ-ONLY VERIFIED total Invitation0,Invitation audit0; no hidden PENDING/FAILED row in current development |
| Transaction/failed-delivery semantics | VERIFIED real-commit fake tests: preflight503 creates nothing; postcommit503 keeps PENDING/FAILED+audit, list visible, duplicate409, resend200 rotates |
| UI recovery | IMPLEMENTED explicit mutation page1/new-row visibility, retained resend error notice, configuration-aware uncertainty, no auto-retry/fake success; normal refetch keeps form/page |
| Current verification | Backend48/Python0, component32/full frontend908, quality0 and delivery2+Members4+Workspace4+stability4+foundation6=20/20 real browsers PASS, actual exits0/owned cleanup |
| Preservation | VERIFIED29-table data/schema/history/sequence/identity exact at09:15:53Z;36 migrations/5 Users/2 Sessions/current Owner business rows retained; Invitation/audit0,ai.0002 unapplied;770 originals/7 final hashes stable |
| Genuine SMTP delivery | BLOCKED/PENDING OWNER CONFIGURATION; no provider selected/configured, no external send authorized/performed; fake locmem is not real email |
| Preserved scope | No Session/CSRF/RBAC/schema/services/AI change; ai.0002 remains UNAPPLIED; existing Members/Workspace/Task stability maintained by regressions |

### Historical completed Workspace access integration

Historical checkpoint: **HT-FE-WORKSPACE-MEMBERS-01 — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE**.

| Current Workspace-access requirement | Status / fresh evidence |
|---|---|
| Actual domain and role ceiling | VERIFIED source: WorkspaceMember ADMIN/MEMBER(Editor)/VIEWER; inherited Profile managers, explicit membership for ordinary Profile MEMBER; no last-WS-Admin rule invented |
| Safe candidate selection | IMPLEMENTED manager-only same-Profile active identity GET; excludes all active WS rows, permits inactive reactivation; no User ID/email; lifecycle/late authority rechecked |
| Authoritative grant/update/revoke | IMPLEMENTED React consumption of existing POST/PATCH/DELETE; root/row capability hints, confirmed updates/removal, no optimistic success or duplicate pending submission |
| Inherited vs direct access | IMPLEMENTED explicit roster and inherited explanation; removing a Profile manager's row never falsely promises removal of inherited authority |
| Task compatibility | VERIFIED grant Viewer→Editor→assign/Start→revoke/regrant; existing Task/history/active assignment retained, current Editor/state revalidated |
| Stability/privacy | IMPLEMENTED User/Profile/Workspace keys, abort/late-response guards, stable same-user refresh;403 roster does not erase legitimate Task reads,404 purges lost work scope |
| Current automated checks | Backend95/full863 PASS/Python0; API67/finalUI34 PASS; broader902 pre-final-semantic reset explicitly distinguished; quality0; real Workspace4+Members4+stability4+foundation6=18/18 PASS with actual exits0 |
| Source/development preservation | VERIFIED29-table snapshot exact at08:17:28Z,36 migrations/4 Users/2 Sessions/current business rows retained; WorkspaceMember/Invitation/AI0,ai.0002 unapplied; owned resources0 across7attempts/runs |
| Final acceptance | IMPLEMENTATION COMPLETE; Owner manual website acceptance/real email/production remain unverified, no automatic follow-on authorized |
| Scope retained | No model/migration/RBAC rewrite/AI flag/provider/dev write; Profile role/remove and recipient inbox/preview remain separate; ai.0002 unapplied |

### Historical completed organization Members integration

Historical checkpoint: **HT-FE-MEMBERS-01 — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE**.

| Current Members/Invitation requirement | Status / fresh evidence |
|---|---|
| Discoverable organization Members | COMPLETE: Profile link and protected /profiles/:profileId/members; real paginated sanitized roster, current capabilities; Owner/Admin only |
| Invite and manage pending invitations | COMPLETE: existing create/list/detail/resend/revoke API consumed; Owner ADMIN/MEMBER, Admin MEMBER; current role ceiling, explicit revoke confirmation, safe errors/delivery state |
| Recipient onboarding/response | COMPLETE: protected /invitations/respond, safe fixed login/signup return, manual masked token; explicit accept/confirmed decline, no auto-accept or public token preview |
| Identity, tenant and authority | VERIFIED: current unique normalized email/token checks; Profile membership only, no Workspace auto-grant; outsider404/Member403, archived readonly, no staff/global-user authority |
| Stability/cache/privacy | VERIFIED: User/Profile keys, lost-scope cleanup, abort on identity/context changes; normal refresh preserves draft, token never in URL/query cache/storage; AuthProvider unchanged |
| Current automated verification | Backend51 targeted/full839; frontend75 API/142 focused/full801; real Chromium14(4 Members+4 stability+6 foundation); quality checks exit0; full Python/browser exits0, targeted child event not retained |
| Responsive/accessibility | VERIFIED375/768/1440/812x375, keyboard/focus/axe/reflow;375/1440 screenshot inspection; existing UI UX Pro Max/master components |
| Development/source safety | VERIFIED29-table snapshot exact,36 migrations/4 Users/2 Sessions retained, Invitation0/AI0; no model/migration/AI/runtime flags or credentials changes, ai.0002 UNAPPLIED |
| Real email and manual Owner acceptance | PENDING: locmem automated delivery only; SENT confirms backend acceptance, not recipient mailbox; no real Owner website writes performed |
| Remaining management surface | NOT IMPLEMENTED: Profile role/remove API/UI, recipient inbox/token-preview API, general Workspace candidate/management UI; no fake actions or inferred User IDs |

These are bounded additions under the current Owner approval, not completion of
all membership/onboarding requirements. Earlier FE04/FE05 exclusions are historical
scope decisions. Existing stability completion and AI migration review gates remain.

### Historical completed frontend stability fix

Historical checkpoint: **HT-FE-STABILITY-01 — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE**.

| Current stability requirement | Status / current evidence |
|---|---|
| Reproduce actual dismissal | VERIFIED: pre-fix real React route/auth/form tests lose the form during focus/visibility/60s checking fallback; no reload/navigation is necessary |
| Preserve valid local draft | IMPLEMENTED: same-user pending/success keeps subtree; Task/Profile/Workspace rerender/refetch preserve title/description/priority/deadline, real browser stability4/4 PASS |
| Preserve authority/session checks | VERIFIED: routine success refreshes active authority,403 probe does not refetch-loop; different User/tenant or actual access loss removes old draft/cache; real expiry and CSRF/tenant regressions PASS |
| Request failure/success/pending | VERIFIED existing component regressions plus injected pre-backend network failure→real CSRF201 browser flow; no optimistic close or pending duplicate creation |
| Quality and accessibility | Final frontend689/689, real browser21/21, TypeScript/Biome/build exit0; four viewports/keyboard/axe/HMR and375/1440 screenshot inspection |
| Source/database safety | VERIFIED backend/AI/migrations unchanged, all29-table development fingerprints/schema/history/sequences exact;36 migrations/4 Users/2 Sessions retained,0002 UNAPPLIED; owned cleanup complete |
| Scope/remaining acceptance | Owner manual website review PENDING. No draft recovery after real identity failure/full reload, no proof arbitrary application-boundary HMR preserves state, no production/live activation |

No new product feature, backend endpoint, schema, frontend framework or design
system is added. Existing AI04C status and rollout approval gate remain below.
Backend826 and other browser suites are historical, not new stability results.

### Historical completed P4-04C offline governance

Historical checkpoint: **HT-AI-P4-04C — OFFLINE GOVERNANCE IMPLEMENTATION READY /
DEVELOPMENT MIGRATION PENDING — OWNER REVIEW GATE**.

| Current approved requirement | Status / proof |
|---|---|
| Truthful durable provenance | IMPLEMENTED offline; AiDispatch keeps mode/provider/model/config/nullable usage/estimate/accounted/billed amounts distinct; fake generated_by_ai:false, billed_cost NULL; live fields staged only |
| Cross-worker dispatch dedup | VERIFIED PostgreSQL claim/unique scoped identity, reservation commits before fake transport; same key/body reuses receipt, changed body/policy conflicts; two independent-connection race tests included |
| Shared cost/request/inflight control | IMPLEMENTED atomic GLOBAL/Profile/User lifetime buckets and three holds; fail-before-dispatch releases exposure, post-dispatch uncertainty retains holds; no automatic rollover/refund/retry |
| Privacy and tenant authority | VERIFIED scoped HMAC, no new raw brief/feedback storage/logging; original actor plus current manager checks, actual selected-source resolver; existing confirmation/Analyzer unchanged |
| Candidate schema | PREPARED ai.0002_dispatch_governance, three CreateModel only; isolated empty/legacy/migration/constraints/index tests PASS; development UNAPPLIED |
| Current verification | Focused52/52 PASS15.286s, full isolated826/826 PASS231.558s; actual launcher/Python0, checks/cleanup PASS; old frontend/browser results historical |
| Source/development preservation | VERIFIED246 other original hashes and legacy model prefix exact; five tested hashes stable; all29-table fingerprints/schema/history/sequences/identity unchanged,36 migrations/4 Users/2 Sessions preserved |
| Remaining gates | OWNER REVIEW: development backup/restore/readiness and separate apply approval; live token/billing bounds, provider-side limits/monitoring, evidence reconciliation and HTTP/React/proposal integration remain unimplemented |
| Manual website acceptance | PENDING; no live inference, provider billing or development write-flow acceptance inferred from offline tests |

Simulation rates/token caps are not verified real billing bounds. Lifetime
budgets have no reset/operator workflow; revoked actors cannot reconcile unknown
holds. Existing app paths are gated before new tables, while arbitrary generic
parent hard-delete/AdminCollector maintenance requires rollout. These explicit
limits do not authorize bypasses or migration. See HANDOVER/AI_PERSISTENCE_REVIEW.

### Historical completed P4-04B offline adapter

Historical checkpoint: **HT-AI-P4-04B — OFFLINE OPENAI ADAPTER COMPLETE / OWNER REVIEW GATE**.

| Current approved requirement | Status / proof |
|---|---|
| Existing-port OpenAI adapter | IMPLEMENTED: newmodule, gpt-5.4-mini Responses/strict JSON; default-off explicit fake transport, no new framework/SDK/network/key |
| Input/output privacy and validation | VERIFIED55/55 new tests: minimal projection, same strict domain validators/graphs/citations, bounded envelope, static errors, offline provenance/cost unknown |
| Fixture/domain compatibility | VERIFIED current apps.ai270/27013.347 seconds, launcher/Python0/checks/cleanup; existing app/React/confirmation unmodified |
| Development/source safety | VERIFIED245 originals/two tested hashes stable;29-table row/schema/sequence/history/cluster exact,36 migrations/4 Users preserved |
| Live activation | BLOCKED: shared dispatch/spend control, provenance/retention contract/schema, privacy/cost and separate live approval remain required |
| Manual Owner website acceptance | PENDING; no live/API/browser manual result implied by fake-transport unit tests |

Full719 backend/frontend675/browser36 and frontend quality results are historical,
not rerun in04B because application/frontend paths are unchanged. New adapter
has no endpoint wiring, persisted live result or billable HTTP transport. Future
schema fields/constraints are PROPOSED only; no migration is created/applied.

### Historical completed P4-04A readiness review

Historical checkpoint: **HT-AI-P4-04A — DESIGN READY / PROVIDER IMPLEMENTATION BLOCKED**.

| Current readiness requirement | Status | Evidence / outstanding gate |
|---|---|---|
| Source-backed provider/Generator/Analyzer audit | DESIGN READY |15-question table and source links in AI_ARCHITECTURE_DESIGN; existing fixture paths/strict JSON and atomic confirmation verified |
| Safe live adapter foundation | BLOCKED — OWNER PROVIDER DECISION | Usersection7 requires proposal+stop without approved provider/model; no adapter/runtime or fixture substitution added |
| Privacy/minimization and honest contracts | DESIGN READY, NOT IMPLEMENTED LIVE | Explicit outbound allowlist, no tenant/source/identity/secrets, no raw brief persistence; derived-output retention and live provenance need review |
| Paid reliability/quota | PROPOSED, NOT APPROVED | Concurrent generate can dispatch twice; existing confirmation and locmem throttle are not a spend ledger; budget/claim/schema approval required |
| Existing fixture safety regression | VERIFIED CURRENT TASK | Fresh apps.ai215/21516.523s, launcher/Python0 and Django/dependency/migration/cleanup checks; full719/frontend675/browser36 remain historical |
| Development/manual acceptance | PRESERVE / PENDING OWNER | Read-only starting state36 migrations/4 Users2 Sessions/1 Profile/membership/Workspace/Task/3 AuditLogs/AI0; final preservation in HANDOVER; FE05/02C/03C manual acceptance remains pending |

No live model request, provider/data/billing approval, new infrastructure,
migration or runtime setting is inferred from design readiness. Approved internal
authority/human confirmation/stateless Analyzer are not reopened. Future adapter
tests need the actual approved provider/contract; fixture tests do not establish
model quality, live timeout/cancellation or hard global budget enforcement.

### Historical completed P4-03C checkpoint

Historical checkpoint: **HT-AI-P4-03C — React Feedback Analyzer — IMPLEMENTATION
COMPLETE / OWNER REVIEW GATE**.

| Current approved requirement | Scope / source checkpoint | Verification |
|---|---|---|
| Existing-source selection | Implemented Task Detail section; Deliverable.review and nondeleted Task Comments, unique bounded page selections | Focused UI32/32 and final frontend675/675 PASS; real Analyzer5/5 PASS |
| Bounded advisory request | Existing stateless POST,1–20 unique source pairs, optional focus≤1000; existing session/CSRF/client and manager gate | Transport/client153/153 PASS; current backend AI215 PASS16.494s; actual child0/cleanup; real browser CSRF/denial checks PASS |
| Truthful synthetic result | ai.feedback.v1 with selected S1…Sn mapping, generated_by_ai:false, persisted:false; no Apply/Confirm or domain mutation | Real UI POST/result/citations and all-model before/after fingerprints PASS; disabled Analyzer1/1 PASS |
| Tenant and lifecycle safety | User/Profile/Workspace/Task lifetime, tracked query cancellation/local state; no stale deletion-cache overwrite or new-context result | Race regression and actual browser context-switch/session-expiry/tenant-denial PASS; all browser suites36/36, launcher/Playwright/backend0 and cleanup |
| Preservation/manual scope | No schema/provider/persistent data/flag changes; P4-03B persistence not required/delivered | Final29-table row/schema/sequence/history/cluster preservation exact;33 tested and160 backend hashes stable,0 owned test resources; FE05/P4-02C/Analyzer manual acceptance remains unverified |

The full live Analyzer product remains PARTIAL. This current task authorizes
React fixture integration only. Backend source160 hashes are unchanged. Current
AI215 tests were run again; full frontend675/675, browser36/36 and quality checks
pass on the final source. Historical full719 and537/30 frontend/browser evidence
below is not reused as current P4-03C PASS. Final persistent-development
preservation and375px/1440px screenshot inspection are verified; automated
four-viewport reflow/keyboard/focus/reduced-motion/axe checks pass.

### Historical completed P4-03A checkpoint

Historical checkpoint: **HT-AI-P4-03A — DESIGN AND FIXTURE BACKEND COMPLETE /
OWNER REVIEW GATE**.

| Current approved requirement | Scope / source status | Verification |
|---|---|---|
| Domain/security contract | Review.comment and TaskComment.content, existing nested tenant context and manager/internal-review role gate audited | Source-backed [foundation](FEEDBACK_ANALYZER_FOUNDATION.md), current AI215/215 PASS including43 new Analyzer cases |
| Safe fixture-only backend | Stateless selected-source POST, existing typed analysis/citation parser and deterministic adapter; no automatic domain action | Full isolated PostgreSQL719/719 PASS217.696s, actual launcher/Python exits0; dependency/Django/model/migration checks pass |
| Privacy/persistence | No raw-feedback artifact, AiProposal/AiOperation reinterpretation or schema change; no source text/author/URL in analysis response | Security/nonmutation/network/log tests pass; fixed first-source citation is not semantic analysis |
| Existing Generator and development safety | Preserve P4-02C dirty work, session/CSRF, existing flags/data/migrations | Final29-table row/schema/sequence/history/cluster preservation exact;235 old files preserve232 hashes plus3 intended edits; tested hashes stable and0 owned test resources |
| Deployment/manual acceptance | Exact permanent Owner readiness question and explicit deployment approval required; FE05/P4-02C manual acceptance still unverified | No deployment or manual acceptance claimed |

This is not completion of the full Feedback Analyzer product. Frontend, live
provider, persisted analysis, media handling and applying suggestions remain
outside this slice; routine delegated choices do not approve those capabilities.
Current checks are optimistic pre/post source/authority checks, not serializable
locking or revocation of delivered content. Process-local throttle reuse is not
a multi-worker production quota guarantee. No frontend/browser/live tests were
run for this backend-only task; historical676/537/30 is not new P4-03A evidence.
Development remains36 migrations/3 Users/2 Sessions/1 Profile/membership/Workspace/
Task,Reviews/Comments/AI0. Manual acceptance remains distinct and pending.

### Historical completed P4-02C checkpoint

Historical checkpoint: **HT-AI-P4-02C — Smart Task Generator fixture React UI —
IMPLEMENTATION COMPLETE / OWNER REVIEW GATE**.

| Approved requirement | Source status | Verification status |
|---|---|---|
| Scoped Generate entry and honest disabled state | Implemented using manager capability and permission-checked OPTIONS | Real enabled4/4 and disabled1/1 browser checks PASS; actual process exits0/cleanup verified |
| Optional synthetic brief | Owner-approved max6,000; validation/no raw storage/echo/log and keyed body binding; old absent-brief replay preserved | Targeted AI172/172 PASS12.169s; launcher/actual Python exits0 and owned cleanup verified |
| Preview/edit/human confirmation | Local title/description/priority/deadline edits; fixed hierarchy; explicit dialog calls existing atomic confirm | Frontend537/537 and enabled UI4/4 PASS; typecheck/Biome/build exit0; four-size axe/keyboard/focus verified |
| Recovery and tenant-private cache | Known proposal GET first; frozen key/body retry only after same ID/revision AVAILABLE; stale confirmation requires fresh review; User/Profile/Workspace cache scope/abort | Real lost-response recovery, actor/tenant/Viewer/CSRF probes and all browser regressions PASS |
| Schema/data preservation | No new model/migration/provider/RBAC/business-service change; baseline36 migrations/3 Users/2 Sessions/1 Profile/1 Workspace/1 Task/AI0 | Final29-table row/schema/sequence/history/cluster comparison exact;45 protected hashes unchanged |

Fixed fixture output is never represented as AI analysis. No live provider,
private customer-data authorization, Analyzer, automatic assignment or
autonomous mutation is implemented. Manual development website acceptance
remains unverified; newer business records are preserved without inferring
their creator. Historical FE05/R3 results below are separate evidence.
Full isolated backend676/676 PASS213.712s includes current AI/business/security
regression; native launcher and actual Python child exit0/cleanup are verified.
All eight real isolated Chromium suites30/30 PASS: enabled4, disabled1,
onboarding3, foundation6, Workspace/Task7, collaboration7, whole workflow1 and
account1. Actual launcher/Playwright/backend exits0 and owned cleanup are
verified; final resource inspection finds0 owned test containers/networks.
Development preservation is exact at05:25:34Z. The bounded fixture slice is
complete; no live-provider or production-ready product claim is made. Stop at
Owner review without enabling persistent fixtures or starting another task.

### Historical completed FE05 checkpoint

Historical checkpoint: **HT-FE-P3-05 — Create Profile & First-Time User Onboarding —
IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**.

Owner approved the bounded first-party flow for an active authenticated User
with zero Profiles: create a new Profile, become its legitimate active Owner,
select its URL scope and proceed through existing Workspace creation. Source
implements a strict name-only collection POST plus protected React form/empty
state. Existing atomic service, SessionAuthentication/CSRF, membership rules and
Workspace permissions are reused; no new model, migration, uniqueness or tenant
state mechanism. Global ownership/role input is rejected, not inferred by React.

Current targeted isolated backend40/40 PASS1.577s and full662/662 PASS245.938s,
launcher/Python exits0 and cleanup verified. Frontend426/426 PASS28.98s,
typecheck/lint/build PASS; all six real isolated browser suites25/25 PASS
(onboarding3/foundation6/work7/collaboration7/MVP1/account1), all launcher,
Playwright/backend exits0 and owned cleanup verified. Historical643/395/22 remain
separate. Final read-only comparison confirms every development row fingerprint,
schema, sequence and migration unchanged:36 migrations/ai.0001 applied,
3 Users/2 Sessions/business0/AI0. All52 model/migration/AI hashes and19 tested
changed-file hashes are stable; no test resource remains. Manual Owner website,
real email, remote CI and production verification are not claimed.
Invitation UI, member-candidate/general membership management and remaining
product onboarding remain separate pending scope. Reserve HT-AI-P4-02C for
Generator UI; HT-FE-P3-05 is this onboarding task. See HANDOVER for the gate.

### Historical completed R3 checkpoint

Historical checkpoint: **HT-AI-P4-02B-R3 — DEVELOPMENT MIGRATION SUCCESS — OWNER REVIEW GATE**.

Owner-approved exact development `ai.0001_initial` completed once with actual
child exit0 on2026-11-02. Preflight and immediate preflight verified original
target, unchanged reviewed source, no outside DB/application activity, sufficient
storage and R2 backup freshness: all27 legacy row fingerprints/schema/sequences
matched its restored snapshot. Retained archive110161 bytes/hash/readability/
TOC251/full-read and prior successful isolated restore were verified; no new
backup or rehearsal was needed for identical data.

Post-check exit0:36 migrations/29 tables/136 indexes; AI tables15/9 columns,
7 FKs/18 constraints/14 indexes valid/ready. All original row hashes remain:
3 Users/2 Sessions/business0; AI rows0. Only framework metadata additions
1 migration/2 ContentTypes/8 permissions and sequence increments1/2/8 occurred.
Django checks/model drift/graph/history/showmigrations/migrate-check and8 actual
loopback HTTP GET smoke requests passed without business mutations. Fixture flag
is false; no live provider, SDK/key or production action.210 runtime hashes stable.
R1's72/158 and full643 suites are historical, not rerun in R3.

Overall Generator remains **PARTIAL**: fixture backend and development schema are
ready, React AI/live provider/Analyzer are absent. Proposed HT-FE-P3-05 fixture UI
requires separate Owner approval; no automatic next task or AI enablement.
Physical retention purge and shared multi-worker quota limitations remain.
See [HANDOVER.md](HANDOVER.md) for evidence and the **OWNER REVIEW GATE**.

### Historical completed R2 checkpoint

Historical checkpoint: **HT-AI-P4-02B-R2 — READY FOR DEVELOPMENT MIGRATION EXECUTION —
OWNER APPROVAL REQUIRED**.

R2 pre-execution checks passed; this is not development migration completion.
Fresh protected backup110161 bytes, TOC251/full-read/hash/readability and actual
isolated restore passed. All27 restored table/schema/sequence/history/row
fingerprints matched current data. The read-only Django helper passed5 checkpoints,
Python PID1 exit0, with only ai.0001 pending and no model/graph/history drift.
default_transaction_read_only stayed ON. No AI migration was applied to development
or the fresh restore, which still had35 migrations and no AI tables afterward.

Owned cleanup exited0; no test resource remains. Final read-only development
comparison matches the R2 baseline exactly: PostgreSQL16.14,35 migrations/0 AI,
3 Users/2 Sessions/business0, original container49ef93152944/volume intact.
All210 runtime file hashes are unchanged. No test suite, fixture, live provider,
runtime/model/migration edit or `.env` read ran in R2. Earlier72/158/643 results
are historical. No matching Django/Vite process or other active DB connection/
transaction was observed at initial/final snapshots; repeat those observations
and target/backup-freshness checks immediately before any authorized apply.

Stop at **PRE-EXECUTION OWNER GATE** for separate approval of exact ai.0001_initial
on the verified development target. Do not enable AI or begin frontend/Create
Profile/Analyzer/production work. The overall Generator is still PARTIAL; source
schema is ready but persistent rollout remains pending. See
[AI_DEVELOPMENT_MIGRATION_READINESS.md](AI_DEVELOPMENT_MIGRATION_READINESS.md).

### Historical completed R1 checkpoint

Historical checkpoint: **HT-AI-P4-02B-R1 — MIGRATION READINESS VERIFIED — OWNER
REVIEW / DEVELOPMENT APPLY NOT AUTHORIZED**.

R1 execution evidence below is from 2026-10-28. The 2026-10-29 resume verifies
retained artifacts and read-only state and completes documentation; no backup,
restore, migration or 72/158 tests were rerun in this resume.

Operational readiness is verified, not persistent rollout completion. Fresh
development backup110161 bytes/SHA-256/251-line TOC/full read and isolated restore
passed. All27 legacy tables/schema/sequences/row fingerprints compared correctly
after documented logical catalog normalization. Exact ai.0001 applied only on
the restored isolated target:2 tables,7 FKs,18 constraints,14 indexes valid/ready;
only1 migration/2 ContentTypes/8 permissions were added. Legacy rows and3 Users/
2 Sessions were preserved; no development identity was used for AI test mutations.

Current R1 evidence: direct restored-DB72/72 TestCase tests PASS7.337s with0
failures/errors/skips and no substituted test DB; fresh separate AI158/158
PASS12.242s (`edc9c2a3ee964c9c9843abb7aa141ad8`) covers concurrency. Final
rehearsal Python PID1 and fresh launcher/Python exits0; owned resources cleaned.
Full643 was NOT rerun in R1. At the end of execution on 2026-10-28, development
read-only schema/sequence/all27
table fingerprints were unchanged,35 applied migrations/0AI/3 Users/2 Sessions/
business0; original container/volume and210 runtime file hashes are preserved.

Current resume read-only verification still shows PostgreSQL 16.14, 35 migrations/
0 AI, 27 tables/122 indexes, 3 Users/2 Sessions and 0 business rows; schema/history/
sequences remain identical and no test container/network remains. Backup size/
SHA-256 still match. One User-row and one Session-row fingerprint differ from
the prior R1 final snapshot, with unchanged counts. Cause/actor is not verified;
no User/Session write, repair or rollback occurred in this resume. The prior
R1 preservation result applies to its own execution window. Fresh inventory,
verified backup and a quiet window must protect the newer data before any
separately approved development rollout.

Archive transfer/readability limitations, normalization details and the future
rollout plan are in [AI_DEVELOPMENT_MIGRATION_READINESS.md](AI_DEVELOPMENT_MIGRATION_READINESS.md).
No runtime/model/migration change, .env read, live provider, frontend or Analyzer
was introduced. Overall Generator remains PARTIAL; physical purge and shared
multi-worker limits remain unimplemented. Stop at OWNER REVIEW GATE for separate
approval to apply exact ai.0001 to development; do not auto-start that rollout.

### Historical completed AI02B checkpoint

Historical checkpoint: **HT-AI-P4-02B — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT
MIGRATION APPROVAL / OWNER REVIEW**.
The Owner approved fixture-only Generator backend, dedicated durable proposals,
current tenant/RBAC integration and atomic human confirmation. Source contains
three generate/read/confirm routes (read also recovers committed results),
`AiProposal`/`AiOperation` and reviewed additive `ai.0001_initial`. The approved
fixture backend is now verified; the overall Generator requirement remains
PARTIAL without frontend/live integration. Development rollout is explicitly
pending separate approval; no AI migration is applied there.

Current active Profile Owner/Admin or Workspace Admin authority is required for
each access; only the originating actor may read/confirm/replay a proposal.
Revocation, archived context, cross-tenant IDs and staff-only authority do not
permit saved content/result access. Existing SessionAuthentication/CSRF and Task
creation services remain the source of truth; confirmation creates an atomic
PENDING batch without assignment or automatic workflow transitions. Generate
creates only proposal/operation state, no Task or AuditLog; Task audits and safe
AI confirmation metadata commit atomically with confirmation outcome.

Thirty-minute confirmation eligibility, 7-day unconfirmed payload bound and
30-day result recovery are approved for this slice. Logical expiry/read masking
and confirmation payload clearing are implemented; physical 7/30-day purge is NOT
implemented/enforced. Scoped idempotency/uniqueness/locks and migration,
security, concurrency and rollback tests passed on isolated PostgreSQL. Generation
throttles 3/minute and 20/day/user are process-local/non-atomic, not shared quotas.

Default-disabled development/test fixture mode uses server-owned synthetic
scenarios only, no live provider, SDK/key, egress or cost. Frontend AI, Analyzer,
live budgets/providers and production remain outside this approval. Docker Engine
recovery was independently verified. Current AI 158/158 PASS 11.208s
(bf34f0b7fd384c7a9958b4513cea18ac), Task/Review/Workspace/RBAC 378/378 PASS 165.639s
(d41c6561e93f4b6489e0a858d87a75de), and full backend 643/643 PASS 215.115s
(6bdba3440f8d46edb28df73a9b30fe03); actual launcher/Python PID1 container exits 0.
Pip/Django/model-drift/graph/full-chain checks and owned cleanup pass. PostgreSQL
container 137 was intentional cleanup, not test failure. 210 protected runtime
hashes remained stable across final runs. Read-only development remains 35 applied
migrations/3 Users/2 Sessions/0 business rows with no AI tables; no .env read or
development write. Historical AI 77/full 562 below are not current evidence.

Stop at OWNER REVIEW GATE. Proposed next task: separately approved controlled
ai.0001 development rollout with fresh inventory/backup/rehearsal/plan, before
separately authorized 02C fixture UI. No automatic task transition or live enable.

### Historical completed AI02A checkpoint

Historical checkpoint: **HT-AI-P4-02A — IMPLEMENTATION COMPLETE / OWNER REVIEW PENDING**.
Owner authorizes only typed contracts, validation, provider abstraction and
offline deterministic fixtures plus persistence review. This is limited technical
implementation, not approval of live AI, UI/endpoints, Task creation or durable
storage. Unapproved AI-D01–AI-D10 portions remain PENDING OWNER REVIEW.

Stateless `backend/apps/ai/` is not registered as a Django app. It defines strict
Task/Feedback DTOs, JSON/date/enum/DAG/citation validators, normalized safe errors,
cooperative timeout/cancellation and fixture provenance with zero usage/cost.
Service enablement is opt-in for trusted test/development construction; access
defaults to denial, with pre/post authorization and selected-source revalidation.
No role, model, route, migration, database persistence, Task status or notification
consistency rule changes. No .env read, key, network/provider call or spend.

Final new AI contracts/boundary tests: 77/77 PASS in 0.046s, run
`98c2aecfd05649b0b12c34bc6c617352`. Full isolated PostgreSQL backend: 562/562
PASS in 201.889s, run `28724dd1667a4fb59dd4932567b9ca3f`. Both actual launcher/
Python exit codes are 0. Required pip/Django/drift/graph/full migration-chain
checks and owned DB/container/network cleanup passed. All 209 original runtime
hashes are unchanged and the 8 new AI code hashes match the final tested source;
normal git diff --check passes. Earlier 45/73/558 are interim snapshots. Historical
frontend 395/browser 22 were not rerun because frontend is unchanged; backend 485
is a prior baseline, not this task's final result.
Technical fixture envelope limits do not approve production quotas or retention.
[AI_PERSISTENCE_REVIEW.md](AI_PERSISTENCE_REVIEW.md) is a proposal; no durable
replay/locking/budget behavior exists yet. Stop at OWNER REVIEW GATE before
HT-AI-P4-02B.

### Historical completed AI01 design checkpoint

Historical checkpoint: **HT-AI-P4-01 — DESIGN COMPLETE / PENDING OWNER APPROVAL**.
Owner newly requests two AI capabilities: Smart Task Generator and Feedback
Analyzer. This is an architecture/security/provider/contract design task only;
it does not make either feature implemented or retroactively complete an Fxx
requirement. [AI_ARCHITECTURE_DESIGN.md](AI_ARCHITECTURE_DESIGN.md) separates
approved boundaries from provider/model, authority, budget and persistence
proposals that still require Owner approval.

Generator needs human preview/edit/confirmation before existing Task services;
Analyzer returns selected-source analysis without Review/Task/Comment/Notification
mutation. Current Task priority/deadline/depth/tenant/workflow constraints stay.
No estimated-duration, Project or new role is added. Shared adapter/strict JSON,
data minimization, synthetic-only unpaid demo, cost reservations and durable
idempotency are designed, not implemented. Final design checks preserve209
runtime hashes/path set with only8 docs changed. Five JSON blocks parse and
two canonical schemas/three examples were checked through a limited in-memory
keyword validator plus DAG/depth/citations; this is not full JSON Schema engine
or application testing. Cost arithmetic, 20 local links and normal git diff
--check pass. No new application tests/provider quality/live result is claimed.
No runtime/.env/database/key/SDK/billing action is part of this task. Historical
FE04395/22/13 and backend485 evidence below is retained under its original scope.
AI implementation remains NOT STARTED. Stop at OWNER REVIEW GATE; proposed
provider/model/roles/caps/schema/retention decisions need explicit approval.

### Historical completed FE04 checkpoint

Historical checkpoint: **HT-FE-P3-04 — COMPLETE / OWNER REVIEW GATE**. Owner
confirms account lifecycle and current Workspace/Task/Review/Comment/Notification
as the accepted MVP. Invitation UI, Profile Creation, membership candidate API
and remaining onboarding/management are OUT OF CURRENT TASK SCOPE / PENDING
OWNER REVIEW. They remain product requirements rather than removed features.

Existing-API registration/recovery/own-verification UI, safe local launcher and
cohesive browser specs/test-only locmem adapter are implemented. Private root
.env now contains the exact Owner-provided values; example secrets are blank.
ValidateOnly, existing venv Django check and Django READ ONLY PostgreSQL
connection pass with exit0:16.14/hustlytasker_db, pending migrations0,
35 records/3 Users/2 Sessions/0 checked business/token/Notification/Audit rows.
Current frontend395/395 PASS15.94s/typecheck/Biome52/build6.65s exits0. Acceptance
1/1 PASS43.6s, account-security1/1 PASS22.4s, collaboration7/7 PASS1.2m,
work7/7 PASS1.0m and foundation6/6 PASS36.3s total22/22, with actual native/
Playwright/backend exits0 and owned cleanup. Local Django/Vite
non-mutating smoke PASS, orchestrator0 and intentional child server stops-1;
AUTOMATED VERIFIED / MANUAL OWNER CHECK PENDING. No new backend/schema/auth/RBAC or
downstream-domain approval. Matrix/AI design-only notes are in
FRONTEND_MVP_ACCEPTANCE.md; older results below are historical baseline. Current
four-size axe0/keyboard/focus/responsive and safe PNG review pass. No bounded-MVP
implementation blocker remains.144 protected assets and development35/3/2/0
are preserved. REAL EMAIL DELIVERY NOT VERIFIED; remote CI/production/manual
Owner remain unverified. Application backend485 tests are historical, not rerun.

### Historical completed API03A checkpoint

Historical checkpoint: **HT-API-FE-P3-03A — COMPLETE / OWNER REVIEW GATE**.
**HT-FE-P3-03 — IMPLEMENTATION COMPLETE.**

Owner approved the limited read-contract/frontend extension. Source resolves
Submit identity/state, Review non-self/latest/state and existing-Comment author
capability gaps through five required read-only booleans: Task.can_submit,
Deliverable.can_approve/can_request_changes and Comment.can_edit/can_delete.
Each uses authenticated request, verified tenant context and existing service
predicates; no role, permission, workflow, model or migration is added.

Frontend uses these hints for real Submit/Approve/Request Changes forms and old
Comment edit/delete after reload/pagination. No guessed identity or mounted-only
ownership proof remains. Server mutations revalidate every check; existing
SessionAuthentication, CSRF, tenant caches and tombstone privacy remain.

Current targeted isolated PostgreSQL95/95 PASS13.020s, run
a718df8ac97a4813aa6c2aebfff0ccd8, actual native/Python exits0 and owned cleanup.
Current frontend356/356 PASS41.49s (12files), typecheck/lint46/build6.69s PASS,
exits0. Full isolated PostgreSQL485/485 PASS231.054s, run
3b2abcd913324644b6240bfc49ca1c18, actual native/Python exits0/DjangoOK/owned cleanup.
Current real browser collaboration7/7 PASS1.3m
(ff6abc6459954d6d83f47ec94c426a62), Workspace/Task/Start7/7 PASS1.1m
(3074e74939f84f3b8039665dab7196ba) and Auth/CSRF/tenant6/6 PASS43.0s
(c125145b536b480badeccfba582f4c90); actual native/Playwright/backend exits0 and
owned cleanup. Real React Submit/Approve/Request Changes and existing-comment
edit after reload/page2 pass. Four-size axe0/keyboard/focus/overflow pass;
24 collaboration screenshots retained and three form PNGs visually reviewed.

All three gaps and accepted FE03 criteria pass. Fresh read-only development
remains35 migrations/3 Users/2 Sessions/0 checked business/token/Notification/
Audit rows;137 protected source hashes unchanged. No new schema/migration,
persistent fixture or production action. No implementation blocker remains;
real email, remote CI and production remain unverified. Stop at OWNER REVIEW
GATE; Project stays PENDING OWNER DECISION and AI remains outside scope.

### Historical FE03 partial checkpoint before HT-API-FE-P3-03A approval

Historical checkpoint: **HT-FE-P3-03 — PARTIAL — API GAP / OWNER REVIEW**.

The existing frontend now integrates Deliverable/revision/nested Review reads,
Comment thread/composer/scoped author actions/manager soft-delete and personal
Notification preview/count/feed/mark-read with `/notifications`. User/tenant/Task
cache keys, SessionAuthentication/CSRF, existing role boundaries and shared
design master remain in use. No backend/model/migration/security-setting change.

The verified `FE03_CONTRACT_MATRIX.md` limits acceptance: Submit metadata does
not prove current assignee in WORKING; Review role metadata does not prove
non-self/latest/state authority; old Comment author membership IDs cannot prove
the current User. These controls remain unavailable. Only exact new comment UUIDs
from a legitimate POST in the current mounted User/scope permit own edit/delete;
that proof is discarded on remount/logout/context change. Manager moderation
uses the existing manager capability and tombstones redact deleted content.

Frozen frontend322/322 PASS (21.69s); focused106 contracts/client,27 collaboration
and12 notifications PASS. Typecheck, Biome44 files and build13.75s PASS. Current
real collaboration7/7 (1.4m; ca613d41c174462c9375f03c201ac4c8) and Workspace/Task/
Start regression7/7 (1.6m; f97f35926ad24bc2abb174f9a4edd83d) PASS with actual
native/Playwright/backend exits0 and owned cleanup. Axe0 at four viewports,
keyboard/overflow and four representative PNG visual reviews pass.144 protected
backend/config hashes and lock unchanged; backend448 stays historical. Existing
API-driven Submit/Review tests do not imply blocked UI actions are implemented.
Current foundation Auth/CSRF/tenant6/6 PASS (55.6s), run
f7f4970fb102434699fcd26c9ef9d8e2, with actual exits0/owned cleanup. Fresh read-only
development35 migrations/3 Users/2 Sessions/0 checked business/token/Notification/
Audit rows and0 owned frontend test containers/networks verify preservation.
All unblocked UI/test work is verified. Keep FE03 partial for the core API gaps
and stop at Owner review. Proposed HT-API-FE-P3-03A would add bounded Submit/
per-Deliverable Review/per-Comment edit-delete hints only after separate approval.

### Historical completed API extension checkpoint before FE03 authorization

Historical checkpoint: **HT-API-FE-P3-02A — COMPLETE / OWNER REVIEW GATE**.
**HT-FE-P3-02 — IMPLEMENTATION COMPLETE.** Both approved API gaps are resolved.

Owner approved resolving the two FE02 gaps through three additive read fields:
Task.can_start and manager-roster display_label/is_assignable. The request and
verified Workspace context bind actual TaskAssignment.User identity; no client
actor ID or email/name identity matching is trusted. Start keeps existing active
Editor/ASSIGNED/assignment predicates and locked mutation revalidation. Roster
eligibility matches active User/Profile MEMBER/Workspace MEMBER and lifecycle
rules; labels use full name or safe membership code, never username/email fallback.
Existing endpoint visibility/pagination, authentication, schema and workflow stay.

Frontend Start/label/eligibility integration uses existing shared components and
tenant cache keys. Final targeted backend91/91 PASS (8.358s), full PostgreSQL
448/448 PASS (199.251s), frontend targeted107/full224 PASS (10.20s), typecheck/
lint36/build6.42s PASS. Current isolated real work-browser7/7 and foundation
Auth/CSRF/tenant6/6 PASS (36.3s), with actual native/Python/Playwright/backend
exits0 and owned cleanup verified. All accepted FE02/extension criteria pass.
Fresh read-only development stays35 migrations/3 Users/2 Sessions/0 business
rows;135 protected model/service/schema/config assets unchanged. No persistent
fixture/login/write/migration, schema or production action occurred. No remaining
blocker within scope. Stop at Owner review; Project/AI and HT-FE-P3-03 retain
their gates, with no automatic next task.

### Historical FE02 partial checkpoint before HT-API-FE-P3-02A

The following gap description and201/7/6 results predate the approved extension.

Historical checkpoint: **HT-FE-P3-02 — PARTIAL — API GAP / OWNER REVIEW**.

Owner-authorized source extends the existing SPA with Workspace create/edit/
archive/restore and Task list/detail/create/edit/assignment, direct Subtask
creation/navigation, existing priority/deadline and paginated server filters.
The existing design master, SessionAuthentication, CSRF and server tenant/RBAC
rules are retained. Verified scoped OPTIONS POST metadata and archive state are
UI hints only; current server permissions govern every write. Assignment choices
are sanitized ProfileMembership IDs, with final Profile/Workspace eligibility
checked by the backend rather than inferred from a display name or global ID.

START UI is **BLOCKED / API GAP**: current User ID and assignment membership ID
cannot be safely mapped through the available contracts. Role-only OPTIONS
authorization does not prove current-assignee identity. No new backend API is
included; Owner review must separately scope the missing contract. CANCELLED
exists in current source as a legacy status and is read-only in the UI, without
a cancel action or a new five-state workflow transition.

New mocked and seven isolated real-browser cases exist; the shared integration
runner separates them from the preserved six foundation cases in fresh owned
database/runtime runs, without changing throttles. Current typecheck/lint 36/
build 7.01s, mock 201/201 (11.35s), real work 7/7 (56.5s) and foundation 6/6 (34.2s) PASS.
Each actual launcher/Playwright/backend exit0 and owned cleanup verified;
responsive/axe/keyboard and representative PNG visual checks passed. These
results cover implemented surfaces, not the missing START/identity contract.
Read-only development confirms PostgreSQL16.14,35 migrations,3 Users/2 Sessions
and0 checked business/token/notification/Audit rows. No persistent fixture,
login or migration was performed. Project remains PENDING OWNER DECISION;
no adjacent module starts automatically. Stop at OWNER REVIEW GATE with partial
status while the START gap remains.

### Historical completed frontend checkpoint — HT-FE-P3-01 — 2026-10-26

The foundation evidence below predates the separate HT-FE-P3-02 authorization.

Historical checkpoint: **HT-FE-P3-01 — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE**.

Owner-authorized frontend source now provides one strict TypeScript React/Vite
SPA with a shared design system, layout/routes, typed same-origin API client,
SessionAuthentication/CSRF login/logout/me and Profile/Workspace read-only UI.
Final strict typecheck, Biome lint24 files, production build6.67s and full
frontend mocked96/96 (4 files,8.60s) PASS. Separate real isolated Django/
PostgreSQL/Chrome6/6 PASS40.7s with actual launcher/Playwright/backend exits0
and owned database/container/two-network cleanup. Responsive375/768/1440 and
812×375 landscape, keyboard/native-dialog and axe WCAG2/2.1 AA checks PASS with
0 violations;13 screenshots retained and visually reviewed. Interactive manual
browser testing and authenticated persistent-development flows were not run.
Final development35 migrations/3 Users/2 Sessions/0 checked business rows and143
protected backend/config/harness hashes unchanged. Backend415/415 is historical,
not rerun because no backend code changed. Source privacy hardening clears
private tab titles after identity loss and keeps fatal fallback Router-independent.
The design master documents actual ui-ux-pro-max research and selected tokens.
No business write UI, backend/schema/data change, Project/AI or production
deployment is included. Documentation/HANDOVER updated; no blocker remains.
HT-FE-P3-02 remains pending separate Owner authorization. Real email delivery,
remote CI and production deployment are unverified; stop at OWNER REVIEW GATE.

### Historical completed backend checkpoint — HT-DB-P1-11 — 2026-10-26

Historical checkpoint: **HT-DB-P1-11 — COMPLETE / OWNER REVIEW GATE**.

DONE: approved development-only application of tasks.0004 followed by
notifications.0002, each exactly once after verified backup/restore rehearsal.
Development now has 35 migration records, 8 Comment/12 Notification columns and
44 valid orphan-free FKs. CHECKs/indexes/partial UNIQUE/nullability/defaults
verify; no guessed mapping or schema drift. Exact legacy rows remain unchanged:
3 Users/2 Sessions, 0 business/token/Audit rows and metadata 23/92/7. No source,
Authentication, RBAC or Task/Review policy changed in this rollout.

Development READ ONLY smoke: 67 anonymous requests plus 28 serializer-only checks
PASS without login/fixture/email/row changes/HTTP 500. Authenticated success and
mutations are reserved for isolated PostgreSQL tests. Current post-rollout
Comment 40/40 (13.140s), Notification 34/34 (8.431s), Task/Review 128/128
(41.694s), security/RBAC 253/253 (224.745s) and full PostgreSQL 415/415
(259.978s) PASS. All five actual launcher/Python exits are 0; Django OK,
dependency/system/model-drift/graph/full-chain and owned cleanup PASS. Final
schema/inventory/exact legacy-row comparison and backup size/hash recheck PASS.
Owned rehearsal DB/container copy removed; host backup retained. No disposable
test resources remain; all 143 protected asset hashes unchanged. No blocker.
The prior 415/415 implementation run below is historical. See HANDOVER.md for
backup, apply times and evidence. Project remains PENDING OWNER DECISION;
stop at OWNER REVIEW GATE. Proposed next step is Project A/B′ scope review,
with no automatic implementation. Real email delivery/remote CI remain unverified.

### Historical implementation checkpoint — HT-COM-P2-06 — 2026-10-25

The pre-rollout pending-migration state below is superseded by HT-DB-P1-11.

Historical checkpoint: **HT-COM-P2-06 — IMPLEMENTATION COMPLETE — PENDING
DEVELOPMENT MIGRATION APPROVAL / OWNER REVIEW GATE**.

Source now implements scoped Task/Subtask Comment CRUD and typed personal
in-app Notifications. Current Comment **40/40 (6.919s)**, Notification
**34/34 (5.401s)**, Task/Review **128/128 (22.637s)**, security/RBAC
**253/253 (165.756s)** and full PostgreSQL **415/415 (191.226s)** PASS. All five
native launcher/Python die-event exits are 0; Django OK, dependency/system/
drift/graph/full-chain and owned cleanup checks pass. The older 341/341 result
below is historical, not new-feature evidence. Final read-only development stays
at 33 migrations, 3 Users/2 Sessions, 0 Comment/Notification/business/token/Audit
rows. New tasks.0004 and notifications.0002 are not applied or authorized for
persistent development in this task. Project remains PENDING OWNER DECISION.
New columns/migration records remain absent; no disposable test DB/container/
network remains. Proposed next step is Owner review, then explicitly authorized
controlled development rollout of these exact two migrations.

Historical completed rollout checkpoint: **HT-DB-P1-10 — COMPLETE / OWNER REVIEW GATE**.

Exact tasks.0003 applied once to the approved PostgreSQL 16.14 development
target at 2026-10-25 03:43:19.588793 UTC after fresh backup/restore rehearsal.
Development now has 33 migrations, 11 Task columns, 40 valid FKs/no orphans,
validated nullable UUID parent/self-parent CHECK/FK and ready/valid lookup index.
All legacy rows compare exactly before/after: 3 Users/2 Sessions, 0 checked
business/security-token/AuditLog rows; metadata 23/92/7 unchanged. Direct smoke
passes 51 read-only requests plus 16 serializer-only checks, no fixture/login/
email/mutation/500. Authenticated success/mutations are NOT TESTED ON PERSISTENT
DEVELOPMENT. Current isolated Task 88/88 PASS (11.780s), related regression
253/253 PASS (162.615s), full PostgreSQL 341/341 PASS (170.987s). Each run has
actual launcher exit 0/Python-container die-event exit 0, Django `OK` and owned
DB cleanup. Final system/drift/migration checks, empty plan and exact post-test
legacy-row comparison PASS. Fresh host backup remains unchanged and retained;
only verified rehearsal/temp copy removed. No test/rehearsal resources remain.
All 129 baseline backend/configuration/Docker/harness asset hashes unchanged.
Project stays PENDING OWNER DECISION. No adjacent task starts automatically.

Historical preceding implementation checkpoint: **HT-TASK-P2-05 — IMPLEMENTATION COMPLETE — PENDING
DEVELOPMENT MIGRATION APPROVAL / OWNER REVIEW GATE**.
Task hierarchy/deadline/priority implementation is present. Isolated Task API
42/42 (4.990s), hierarchy/existing workflow43/43 (4.770s), and migration2/2
(1.465s) pass with dependency/system/model-drift/migration-chain checks.
Workspace/RBAC122/122 (60.495s) and full PostgreSQL341/341 (174.058s) PASS.
Django reports `OK` and owned-test-DB removal is verified in logs; the wrapper
did not retain the child exit code, so no launcher exit-0 claim is made.
At that earlier gate, `tasks.0003_task_hierarchy` was isolated-test-only and
development had 32 migrations, 3 Users, 2 Sessions, zero verified Users/tokens
and zero checked business/AuditLog rows; parent column/migration record were
absent. No disposable test resources remained. Persistent rollout required
the later separate HT-DB-P1-10 authorization and is now completed above.

The Owner replaced the proposed bundled HT-PROJ-P2-05 with authorized
HT-TASK-P2-05 plus **PROJECT ARCHITECTURE REVIEW — PENDING OWNER DECISION**.
`PROJECT_ARCHITECTURE_REVIEW.md` compares A/B and an optional cross-month
Profile/Client-scoped B′. No Project model/API/migration is included.

Historical preceding checkpoint: **HT-TEST-P1-01 — COMPLETE / OWNER REVIEW GATE**.
**LOCAL TEST HARNESS VERIFIED**. Dedicated isolated test
settings, shared guarded PostgreSQL runner, PowerShell/Docker local command,
and backend GitHub Actions workflow are implemented. Historical tooling evidence
is 14/14 harness guard tests, targeted API 10/10, and full PostgreSQL 286/286
(166.382s) PASS with migration-chain/owned-DB cleanup checks. Failure exit-code,
owned-interruption cleanup and wrong-repository refusal checks pass. Local
PowerShell/Compose/actionlint/diff checks and exact original User/Session
preservation pass. **CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED.**

HT-DB-P1-09 remains the completed rollout baseline: `accounts.0002` applied
once, 32 migrations, 3 active Users/2 Sessions preserved, and zero verified
Users/token/business/AuditLog rows. Its historical 286/286 result does not
substitute for the current Task hierarchy gate. That completed tooling task
changed no development migration, business rule, authentication mechanism or
API contract. HT-TASK-P2-05 adds the Task hierarchy contract described above.

## Tổng quan hiện tại

Dự án đang ở `PHASE 3 - Frontend Foundation`; Owner đã phê duyệt
HT-API-FE-P3-03A để đóng ba API GAP của HT-FE-P3-03; cả hai phạm vi hiện đã
hoàn thành implementation và dừng OWNER REVIEW GATE. Source có năm capability
read-only và form Submit/Approve/Request Changes, Comment cũ edit/delete theo
quyền server. Backend targeted95/full485, frontend356/typecheck/lint/build và
real UI browser7/7/6 đã PASS với exit0/cleanup; responsive/axe/focus và bảo toàn
development đã kiểm chứng. Không đổi models, schema, migrations, service
business rules, RBAC hoặc authentication. Backend
history below remains a completed historical baseline:
`HT-RBAC-DESIGN-P0-01` đã
`COMPLETE / ACCEPTED — APPROVED BY OWNER DELEGATION`; `HT-RBAC-P1-03` Tenant
Access Context and Scoped Service Foundation đã hoàn thành, sau đó Owner cho
phép triển khai `HT-API-P1-04`. Bốn Profile/Workspace read route, DRF tenant
permissions, scoped querysets và pagination đã hoàn thành. Owner đã mở
`HT-DB-P1-05` để rollout có kiểm soát migration hiện hữu trên development;
task đó đã hoàn thành với full PostgreSQL suite 101/101. Owner sau đó mở
`HT-WORK-P2-02`, rồi phê duyệt rollout `workspace.0003` qua `HT-DB-P1-06`.
Sau review gate đó, Owner mở `HT-TASK-P2-03`, rồi phê duyệt controlled
development rollout qua `HT-DB-P1-07`. Owner tiếp tục mở `HT-INV-P2-04`.
Sau khi implementation đạt review gate, Owner mở controlled rollout
`HT-DB-P1-08`. That rollout is the immediate completed baseline. The Owner
subsequently authorized HT-AUTH-P1-02 implementation, now complete, and then
controlled development rollout HT-DB-P1-09 as recorded above.
Workspace write/membership, Profile/Workspace lifecycle, monthly period và
membership soft revoke/reactivate đã triển khai; `workspace.0003` đã được
backup/rehearsal và apply lên development. Direct smoke và full PostgreSQL
169/169 của gate trước PASS. Task/Deliverable/internal Review workflow mới đã
implement trong source; `tasks.0002`/`reviews.0002` đã được backup/rehearsal và
apply trên development. Current Task 33/33, Auth/API 29/29, Workspace 140/140
và full PostgreSQL 202/202 đều PASS. Profile Invitation hiện đã implement model,
additive `workspace.0004`, locked services, mail-delivery abstraction, RBAC/API,
audit và tests; Invitation 39/39, regression liên quan 173/173 và full
PostgreSQL 241/241 PASS tại implementation gate. `workspace.0004` hiện đã được
backup/rehearsal và apply có kiểm soát trên development; schema/inventory và
fixture-free smoke đạt.
Current Invitation 39/39, Auth/API 29/29, Workspace/RBAC/Task/Review 173/173
và full PostgreSQL 241/241 đều PASS; từng test DB đã bị hủy. Production không
bị truy cập. Account verification/recovery is implementation-complete in
source and its additive migration is applied to approved development through
HT-DB-P1-09. Older counts/tests in this overview are historical. Owner then
authorized HT-TEST-P1-01 test tooling/CI standardization, whose local
verification is complete as recorded above. Remote GitHub execution,
real-provider verification,
remaining business APIs, frontend, and deployment are not complete.

## Nền tảng kỹ thuật

| Hạng mục | Trạng thái | Đã triển khai | Còn thiếu / vấn đề | Căn cứ |
|---|---|---|---|---|
| Dependency manifest | COMPLETE | Pinned manifests retained; existing Windows venv Python3.12.5 and Django check verified in FE04 with permitted access | Sandbox exit103 is an access limitation, not evidence of broken venv; production/runtime upgrades remain separate | `backend/requirements.txt`; `HANDOVER.md` |
| Django configuration | PARTIAL OVERALL — existing settings retained | Historical FE04 local startup/connectivity verified; current Workspace task runs Django/dependency/model checks on isolated settings and read-only development identity/inventory only, no .env access | Development ai.0002 intentionally pending; no current startup/manual/production/real-email verification claimed | `scripts/start-backend-dev.ps1`; `FRONTEND_GUIDE.md`; `HANDOVER.md` |
| Database migrations | PARTIAL OVERALL — current development36 applied | Prior approved ai.0001 rollout retained; current read-only29-table schema/data/history exact and36 records preserved; isolated full chain/drift checks PASS, no Workspace migration needed | ai.0002_dispatch_governance UNAPPLIED, three governance tables absent; new development/production rollout needs separate approval | Current HANDOVER preservation; historical R3/DB-P1-11 evidence; `DATABASE_SCHEMA.md` |
| Business schema | PARTIAL | Existing hierarchy/workflow retained; Comment lifecycle/protected Task FK and nullable complete-or-legacy Notification context/event/recipient uniqueness now exist in approved development | Cross-row tenant checks remain validated service/query responsibilities; Task soft delete and other tenant domains absent | Task/Notification models; HT-DB-P1-11; `DATABASE_SCHEMA.md` |
| Tenancy/ownership design | COMPLETE / ACCEPTED | Owner đã phê duyệt 11 nhóm quyết định; HT-TASK-P2-03 tiếp tục chốt internal workflow trong đúng tenant boundary | Billing, public-link capabilities, retention duration và các domain action chưa implement vẫn defer sang task tương ứng; Client/Guest review và Payroll tách khỏi internal approval | `documentation/DECISION_LOG.md`; owner approvals 2026-10-16 và 2026-10-21 |
| RBAC/access/invitation design | COMPLETE / ACCEPTED | 14 nền RBAC được chốt; Task manager/reviewer contract và Profile Invitation role/identity/lifecycle contract đã được hiện thực hóa trong các slice được duyệt | Client/Guest capabilities, payroll pricing/eligibility và downstream domain details vẫn ở task riêng | `documentation/RBAC_DESIGN.md`; `DECISION_LOG.md`; HT-INV-P2-04 checkpoint |
| Django Admin | PARTIAL | User, Workspace, WorkspaceMember, Task, TaskAssignment, TaskComment; Task domain hiện inspection-only; Workspace hard delete bị chặn để không cascade workflow history; mapped Profile/period và lifecycle/member fields vẫn protected/read-only | Profile/ProfileMembership và 8 model trước chưa register; chưa có tenant-scoped Admin; aggregate CASCADE vẫn tồn tại ở schema và chỉ được chặn trên current Admin/API surfaces | `backend/apps/{tasks,workspace}/admin.py`; source review 2026-10-21 |
| DRF/API foundation | PARTIAL OVERALL — WORKSPACE-MEMBERS-01 BOUNDED ACCESS COMPLETE | Existing Profile/invitation/member writes retained; new scoped candidate GET and additive roster capabilities,24 new tests; targeted95/full863 PostgreSQL PASS with Python0, no schema/service change | Profile role/remove and recipient inbox/preview APIs not added; no persistent development mutation tests | Workspace access/serializers/views/test_workspace_access_api; `API_DOCUMENTATION.md`; `HANDOVER.md` |
| Authentication/RBAC | PARTIAL OVERALL — WORKSPACE-MEMBERS-01 REGRESSION VERIFIED | Existing Session/CSRF, inherited Profile authority, Workspace role ceilings and locked services retained; scoped abort/cache/stable forms, full863 backend and18 real browser tests PASS | Real email/distributed throttle/deploy remain separate; no new auth mechanism/role or last-WS-Admin rule | Existing access/services; `RBAC_DESIGN.md`; `HANDOVER.md` |
| Automated tests | INVITATION-DELIVERY-FIX-01 APPLICATION SCOPE VERIFIED | Invitation48/Python0 with real commit/fake transport, UI32/full frontend908, type/lint/build and20 real browser cases PASS;770 originals/7 final hashes stable, owned resources0 | Full backend not rerun because application backend unchanged; prior863 remains historical. Real SMTP, Owner manual/remote CI/production unverified | `FRONTEND_GUIDE.md`; `PROGRESS.md`; `HANDOVER.md` |
| Frontend | PARTIAL OVERALL — WORKSPACE ACCESS/MEMBER IMPLEMENTATION COMPLETE | Previous Profile/invitation/work/collaboration/fixture AI UI retained; inline Workspace roster/candidates/grant/confirmed role/revoke now consume real APIs, Task assignment/stability compatible; final34/quality/browser18 PASS and exact development preservation | Manual Owner/real email pending; Profile role/remove and recipient inbox/preview remain separate; no live AI/downstream domain/deploy completion claim | `frontend/`; `FRONTEND_MVP_ACCEPTANCE.md`; `HANDOVER.md` |
| Docker/deployment/CI | PARTIAL — TEST BASELINE IMPLEMENTED | Development Compose retained; separate tmpfs PostgreSQL 16/Python 3.12 local test project/dependency-only image and PR/push-main backend CI workflow; source read-only, no development volume/credentials, contents-read/no deploy; local full/failure/cleanup/actionlint PASS | CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED; production backend image/deploy/monitoring still absent | `docker/compose.test.yml`; `docker/Dockerfile.test`; `.github/workflows/backend-ci.yml`; `README.md` |

## Trạng thái yêu cầu nghiệp vụ F01-F16

| ID | Module | Trạng thái | Đã triển khai | Còn thiếu / vấn đề |
|---|---|---|---|---|
| F01 | Authentication | PARTIAL OVERALL — FE04 accepted account lifecycle UI VERIFIED | Existing Session/verification/reset backend and applied accounts.0002 retained; register/forgot/reset/own-verification UI with masked memory-only credentials/no auto-login; current frontend395/395 and five real browser suites22/22 pass | Locmem proves test delivery only: REAL EMAIL DELIVERY NOT VERIFIED. Timing equalization, logout-all/deactivation, real provider/distributed throttle and production remain separate |
| F02 | Profile & Workspace | PARTIAL OVERALL — PROFILE BOOTSTRAP / ACCESS / INHERITANCE IMPLEMENTATION COMPLETE | Existing create/monthly lifecycle and member grant/update/revoke retained; bounded optional source role snapshots and confirmed first-Workspace MEMBER selection added; current backend132/full905, frontend955 and24real browsers PASS, full development/source preservation in HANDOVER | Manual Owner acceptance pending; Profile role/remove/general metadata administration and recipient inbox/preview separate; no schema or TaskAssignment mutation |
| F03 | Membership Invitation | PARTIAL OVERALL — DELIVERY RECOVERY AND ACCEPTED CURRENT-MONTH ONBOARDING VERIFIED | Existing consent/token/role-ceiling/identity/audit and workspace.0004 retained; bounded successful-accept grant only in exact current ACTIVE month when no assignment history; postcommit503/FAILED visibility, create409/resend200 unchanged; current real inheritance/Members/failure-browser regressions pass | Gmail SMTP now Owner-reported working, not a genuine send test by this task. No live mail/config change or automatic fallback. No inbox/preview or Profile role/remove API; revoked rows/past/future months/login/send never auto-granted |
| F04 | Task Lifecycle | PARTIAL OVERALL — TASK BRIEF DEVELOPMENT ROLLOUT COMPLETE; OWNER UI ACCEPTANCE PENDING | Four optional URLs/exact VND/VI24h inputs and compensation RBAC implemented; tasks.0005 now applied development after verifiedbackup/rehearsal. Legacy data preserved, updatedTaskORM/read-onlyHTTPPASS; historical fulltests labeled in HANDOVER | Owner manually accepts Create/Edit/18:30/assignment/payredaction. Assigned Editor cannot metadata Create/Edit; other readers getNULL. No arbitrary status/auto-complete/payroll; backend and separate AI hierarchy retained. ai.0002 remains unapplied |
| F05 | Marketplace | NOT STARTED | Chưa có implementation | Publish/claim rules, concurrency guard, API và tests |
| F06 | Review Upload | PARTIAL OVERALL — accepted text/file_url backend and UI COMPLETE | Existing revisioned text/file_url API/read UI retained; Task.can_submit proves current assignee/state; real React Submit and targeted/full regression PASS | Only text/file_url backend, no upload/storage/media service; other target rollout unauthorized |
| F07 | Team Review Status | PARTIAL OVERALL — internal backend/rollout/UI COMPLETE | Existing manager review services, one decision per Deliverable and self/stale/concurrency guards retained; per-Deliverable hints and real React Approve/Request Changes/resubmission verified | Client/Guest approval and other target rollout remain separate |
| F08 | Guest Review Decision | NOT STARTED | Kiến trúc đã chốt GuestReviewLink tách khỏi Client Portal | Chưa có scoped hashed token, exact capabilities, expiry/revoke, decision flow hoặc throttle |
| F09 | Client Portal | NOT STARTED | Client/ShareLink hiện chỉ là schema primitive; target hỗ trợ account và secure link độc lập với internal membership | Chưa migrate Client→Profile, chưa có secure link replacement, portal/API/capabilities |
| F10 | Client Request Inbox | NOT STARTED | Chưa có model/code | Request intake, triage, conversion to task và permissions |
| F11 | Task Comments | ACCEPTED backend/rollout/FE03 CRUD scope COMPLETE | Existing4000-character/current-access CRUD, soft-delete/tombstone/audit retained. Server can_edit/can_delete author/moderation controls after reload/pagination and cache redaction verified by current unit/security/real browser tests | No rich text, mentions, revision history, realtime or retention expansion |
| F12 | Notifications | PARTIAL OVERALL — BACKEND/ROLLOUT AND FE03 UI VERIFIED | Existing five atomic events, recipient dedup/current-access projection and personal list/count/read API retained. FE03 User-keyed preview/badge/feed/filter/page/mark-read and safe Task navigation verified | No read-all, unread toggle, email/push/worker or retention expansion; restored access may reveal earlier valid feed rows |
| F13 | Payroll | NOT STARTED | Chưa có model/code | Payroll calculation, lock, approval/payment workflow và audit |
| F14 | Finance Invoice | PARTIAL | Invoice và Payment models; approved target places Invoice in one Workspace, same-Profile Client, Payment under Invoice | Target ownership chưa migrate; numbering/billing workflow, positive amount constraints, service/API/tests còn thiếu |
| F15 | CRM Share Link | PARTIAL | Client và ShareLink models; approved target puts Client in Profile and separates portal/review credentials | Tenant ownership chưa migrate; token hiện plaintext/có thể lộ qua `__str__`; thiếu hash/revoke/capability/expiry |
| F16 | Automation | NOT STARTED | Chưa có cron/webhook worker hiện hành | Job design, idempotency, authentication, monitoring và deployment |

## AI capabilities requested by Owner — 2026-10-28

These are new Phase4 requirements traced to the current Owner instruction, not
claims that the original F01–F16 already contain implemented AI runtime.

| Capability | Design status | Implementation status | Required gate |
|---|---|---|---|
| AI Smart Task Generator | FIXTURE BACKEND/DEVELOPMENT SCHEMA/FIXTURE REACT UI APPROVED; LIVE GATE RETAINED | PARTIAL OVERALL — P4-02C FIXTURE UI IMPLEMENTATION COMPLETE / OWNER REVIEW GATE | R3 applied exact ai.0001; optional synthetic brief/OPTIONS/UI preview/edit/atomic confirmation/recovery verified by backend676/frontend537/browser30 PASS and preservation. Live provider/shared budgets remain unimplemented and require separate approval; FE05 is onboarding only |
| AI Feedback Analyzer | P4-03A domain/security fixture foundation and P4-03C React implementation complete | PARTIAL OVERALL — STATELESS FIXTURE BACKEND/REACT COMPLETE / OWNER REVIEW GATE | Current frontend675/browser36/AI215 PASS and preservation exact; full719 remains historical; no live product/persistence completion claim; P4-03B storage not required/delivered, manual Owner review pending, no automatic Review/Task action |
| Shared AI provider/cost/security foundation | FIXTURE CONTRACT/DURABLE GENERATOR SCOPE APPROVED | PARTIAL OVERALL —02B fixture backend verified, no live infrastructure | Current manager-only access, actor scope and durable confirmation passed PostgreSQL tests; physical purge, shared live budgets, provider SDKs and production controls remain absent/gated |

Historical FE05 changed only bounded F02 Profile creation/selection integration;
F04/F06/F07/F11/F12 business workflows remain unchanged. Project, Invitation UI,
general membership/onboarding, production, real email and remote CI keep their
separate scope/review limitations. P4-02C adds only the approved fixture contract
and React consumer; existing AI models/migrations/provider/settings and business
workflow services remain unchanged.

## Quyết định sản phẩm/kiến trúc còn cần chốt

**PROJECT ARCHITECTURE REVIEW — PENDING OWNER DECISION:** Task/Subtask,
deadline and priority continue independently under HT-TASK-P2-05. Choose
whether to defer Project or separately scope optional Profile/Client-owned
cross-month grouping. Literal Workspace-owned Project would require explicit
revision of accepted cross-month ownership. See `PROJECT_ARCHITECTURE_REVIEW.md`.
AI estimated duration remains a future proposal; no AI schema/provider is added.
Feedback Analyzer readiness now includes authorized Task/Workspace context,
Comments and existing Review/Deliverable revisions. Comments do not constitute
Review decisions. Full Comment text revision history, exact revision binding,
source citation/versioning and human-confirmed suggestion semantics remain
future data/API decisions; no AI writer or Suggestions table is implemented.
Retained soft-deleted bodies are not available to an AI consumer by default;
future retrieval must honor current authorization and the tombstone projection.
Notification failure intentionally rolls back business mutation/audit under the
chosen atomic policy; successful replay preserves existing notification read state.

The implementation review gate was followed by completed Owner-authorized
HT-DB-P1-10, which applied tasks.0003 after inventory, verified backup and
rehearsal. Current smoke, isolated regression/full suite and cleanup pass.
Stop at **OWNER REVIEW GATE**. Proposed next step is Project A/B′ scope selection
or another separately authorized roadmap task, not another tasks.0003 apply.
Project implementation remains unauthorized; no new domain starts automatically.

Không còn câu hỏi nào của review gate `HT-RBAC-DESIGN-P0-01`; 14 quyết định đã
được chốt qua Owner delegation và không được yêu cầu quyết định lại.

Các task sau vẫn phải chốt contract riêng trước implementation: payroll
pricing/eligibility và business trigger ngoài invariant “internal approval
không tự tạo Payroll/Payment”; full deactivation/standalone logout-all flow;
production email-provider/shared-cache
deployment cho Invitation; Invoice numbering/billing;
Client Portal/Guest Review exact capabilities/default expiry; retention legal
hold/purge; và project-wide response/error convention ngoài các mapping hiện
có. Policy migration vẫn là kiểm kê từng môi trường, không tự gán tenant
cho dữ liệu không xác định.

`HT-API-P1-04`, `HT-DB-P1-05`, implementation `HT-WORK-P2-02`, rollout
`HT-DB-P1-06`, `HT-TASK-P2-03` và rollout `HT-DB-P1-07` đã hoàn thành.
`HT-DB-P1-06` đã backup/rehearse/apply `workspace.0003` đúng development,
post-check schema/data, smoke request stack và rerun full regressions đạt;
production không bị tác động. `HT-TASK-P2-03` source implementation và
`HT-DB-P1-07` controlled development rollout đều đạt: backup/restore rehearsal,
explicit Tasks/Reviews 0002 apply, post-check, direct fixture-free smoke,
targeted suites và full 202/202. `HT-INV-P2-04` implementation tiếp theo đã
đạt Invitation 39/39 và full 241/241. Owner sau đó mở `HT-DB-P1-08`; fresh
backup/restore rehearsal, exact development apply 0004, schema/inventory
post-check và fixture-free smoke đã đạt. Current targeted/regression/full rerun
cũng đạt Invitation 39/39, Auth/API 29/29, Workspace/RBAC/Task/Review 173/173
và full 241/241. Đây là completed baseline **HT-DB-P1-08 — COMPLETE / OWNER
REVIEW GATE** ngay trước task hiện tại.

The Owner subsequently opened `HT-AUTH-P1-02 — Account Verification &
Recovery` and then separately authorized `HT-DB-P1-09`. The existing migration
is now applied to approved development; final full-suite verification,
cleanup, and documentation are complete. HT-DB-P1-09 is COMPLETE. Owner then
opened HT-TEST-P1-01, limited to test tooling and CI. Its local gates and
documentation are complete: LOCAL TEST HARNESS VERIFIED; CI WORKFLOW
IMPLEMENTED — REMOTE RUN NOT VERIFIED. That historical gate is followed by the
Owner-authorized HT-TASK-P2-05 and separate pending Project architecture gate
described above; the earlier proposed HT-PROJ-P2-05 bundle is superseded. See
`documentation/HANDOVER.md`, `RBAC_DESIGN.md`, and `DECISION_LOG.md`.
