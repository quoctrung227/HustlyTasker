# CHANGELOG

Lịch sử thay đổi của dự án HustlyTasker.

## Unreleased - 2026-10-28

### HT-AI-P4-01 — AI Architecture, Provider Selection & Security Design — DESIGN COMPLETE / PENDING OWNER APPROVAL

- Added a source-backed shared design proposal for Smart Task Generator and
  Feedback Analyzer in AI_ARCHITECTURE_DESIGN.md. Reuses Django/DRF/PostgreSQL,
  SessionAuthentication/CSRF, tenant predicates, current Task hierarchy/deadline/
  priority and locked services. No runtime source or database change.
- Documented official provider/pricing/data-policy snapshot accessed2026-10-28,
  fixture/synthetic/private modes, cost assumptions and disabled-by-default
  controls. Specific models/providers, limits and live data use remain proposed
  pending Owner approval; no key, provider request, billing or SDK action.
- Proposed versioned JSON/DRF-compatible contracts, safe failure responses,
  minimized authorized sources/citations, threat tests and mandatory separate
  human confirmation. Durable proposal/usage/idempotency schema is a future
  approval gate, not an applied migration or implemented API.
- Designed UX using the existing master and actual focused local UI UX Pro Max
  searches; no React page/button/theme is created. Proposed P4-02 slices/P4-03/
  P4-04 remain NOT STARTED. Estimated duration, Project and onboarding are not
  silently added. Final review resolves source revalidation on saved-analysis
  replay, shared-client422 handling, cross-family locking/FK test gates and
  replay/TTL/keyed internal fingerprints.
- Documentation checks preserve209 runtime hashes/path set with exactly8 docs
  changed. Five JSON blocks parse; two canonical schemas/three examples checked
  with a limited in-memory keyword validator plus DAG/depth/citations. Cost
  arithmetic and 20 local Markdown links verify; normal git diff --check passes
  with only existing CRLF notices. No full JSON Schema engine or application
  test PASS is claimed. Stop at OWNER REVIEW GATE; AI implementation NOT STARTED.
- Historical FE04395 frontend/22 browser/13 launcher and backend485 tests are
  not rerun or reported as current AI tests. This entry records design work,
  not AI implementation completion or provider integration verification.

## Unreleased - 2026-10-27

### HT-FE-P3-04 — Frontend MVP acceptance and local startup — COMPLETE / OWNER REVIEW GATE

- Added source-backed completeness matrix and design-only AI readiness. Current
  Task/collaboration UI is preserved; account lifecycle fills existing F01 API
  consumer gaps. Profile/bootstrap and broader membership/onboarding gaps are
  explicitly separated from the implemented core, without invented endpoints.
- Added PowerShell local environment loader and13 passing guard tests. Uses
  existing venv, literal ignored configuration and child-scoped environment;
  never creates credentials, applies migrations or seeds development data.
- Added register/forgot/reset/own-email-verification consumers over existing
  APIs, with no auto-login, masked memory-only credentials, CSRF and safe errors.
  Added cohesive UI acceptance and account-security specs with an owned
  container-local locmem mailbox bridge; no application email service change.
- Applied Owner scope decision: Invitation UI, Profile Creation, membership
  candidate API and remaining onboarding/management remain outside this task
  pending separate review, without deleting them from product requirements.
- Resolved local-file mismatch: Owner-provided values in .env.example were
  preserved exactly in ignored root .env and only example secret fields blanked.
  No credential was generated/reset/changed. Existing venv ValidateOnly/Django
  check and Django READ ONLY PostgreSQL connection pass, exits0; development
  stays35/3/2/0, pending migrations0. The earlier missing-config checkpoint is
  historical and superseded by this verification.
- Final-source frontend395/395 PASS14files15.94s, typecheck/Biome52/build6.65s
  actual exits0; two App.test option mismatches were fixed in tests only.
  Current real acceptance1/1 PASS43.6s (6a1ec11fb62741aabcc330571015c828) and
  account-security1/1 PASS22.4s (77a73580faf34927b8970208eca6f658) have actual
  native/Playwright/backend exits0/cleanup. Current collaboration7/7 PASS1.2m
  (8a940dabeedc41ceaf63b8669f461b28), work7/7 PASS1.0m
  (e1470330e0904f9d92e5254324892455) and foundation6/6 PASS36.3s
  (5d6f2f14dbbf4829ad54c0d054584d81) complete22/22 real browser checks, all actual
  native/Playwright/backend exits0 and owned cleanup. Initial acceptance helper
  was corrected to respect the existing safe post-login return-to-Task behavior;
  no workflow or authorization change was used to make it pass.
- Local Django8000/Vite5174 non-mutating smoke PASS, orchestrator0: direct/proxy
  health+CSRF200, anonymous me/profiles403 and register OPTIONS200. Owned child
  servers were intentionally stopped with exit-1; no false server-exit0 claim.
  AUTOMATED VERIFIED / MANUAL OWNER CHECK PENDING; real email is unverified.
  API03A/backend485 results below remain historical baseline, not new FE04 runs.
- Current axe0/keyboard/focus/overflow at375/768/1440 and landscape pass; empty
  register375/reset812 and completed Task1440 PNGs were visually reviewed without
  credentials.144 protected source assets match and development35/3/2/0 remains.
  Accepted bounded MVP implementation/checks/docs are complete; stop at OWNER
  REVIEW GATE. Real email, remote CI, production and interactive manual Owner
  testing remain unverified. No automatic AI/onboarding/Project task starts.

### HT-API-FE-P3-03A — Collaboration Mutation Capabilities — COMPLETE / OWNER REVIEW GATE

- Added request-bound read-only Task.can_submit, Deliverable.can_approve/
  can_request_changes and Comment.can_edit/can_delete to existing responses.
  Same live tenant/membership/identity/state predicates as existing services;
  latest review target is selected by created_at/id, not numeric revision.
  No new endpoint, role, model, migration, workflow or authentication mechanism.
- Connected actual Submit/Approve/Request Changes native-dialog forms and old
  Comment edit/delete to server hints. Retained strict inputs, double-submit
  guards, safe errors, CSRF, confirmed cache updates and soft-delete redaction.
  Shared ui-ux-pro-max/master tokens and form/focus patterns remain in use.
- Added37 capability/security/contract tests and additive expected response
  fields. Corrected one query-growth fixture to compare eligible-review pages
  at both sizes; strict query bound and service authorization remain unchanged.
- Current targeted isolated PostgreSQL95/95 PASS13.020s
  (runa718df8ac97a4813aa6c2aebfff0ccd8), actual native/Python exits0 and owned
  cleanup verified. Frontend356/356 across12files PASS41.49s; strict typecheck,
  Biome46files and production build6.69s PASS, exits0.
- Full isolated PostgreSQL485/485 PASS231.054s
  (run3b2abcd913324644b6240bfc49ca1c18), actual native/Python exits0, DjangoOK and
  owned database cleanup. Dependency/system/model-drift/full migration chain
  checks pass without a new migration or persistent development apply.
- Current real isolated browser collaboration7/7 PASS1.3m
  (ff6abc6459954d6d83f47ec94c426a62), Workspace/Task/Start7/7 PASS1.1m
  (3074e74939f84f3b8039665dab7196ba) and Auth/CSRF/tenant6/6 PASS43.0s
  (c125145b536b480badeccfba582f4c90), actual native/Playwright/backend exits0 and
  owned cleanup. Submit, independent-reviewer Approve/Request Changes and old
  Comment edit after reload/page2 are actual React UI actions, not API-only setup.
  Axe0/keyboard/focus/overflow at375/768/1440/landscape;24 collaboration PNGs
  retained, three new-form PNGs visually reviewed.
- Fresh read-only development35 migrations/3 Users/2 Sessions/0 checked business/
  token/Notification/Audit rows and137 protected hashes verify preservation. All
  three gaps resolved; HT-FE-P3-03 now IMPLEMENTATION COMPLETE. No implementation
  blocker, persistent write, schema change or automatic next task. Real email,
  remote CI and production remain unverified; Project stays PENDING OWNER
  DECISION. Stop at OWNER REVIEW GATE.

## Historical unreleased checkpoint - 2026-10-26

### HT-FE-P3-03 — Collaboration UI — PARTIAL — API GAP / OWNER REVIEW

Historical FE03 checkpoint before the approved HT-API-FE-P3-03A extension above.

- Integrated Task Detail Deliverable revisions and nested Review reads with
  paginated Comments/composer, bounded author actions and confirmed moderation
  soft-delete. Deleted content is redacted from cached copies before refetch;
  tombstones retain only permitted metadata. No submit/review transition invented.
- Added User-scoped personal Notification preview/unread count/feed/mark-read and
  `/notifications`. Unsafe writes retain CSRF and require server confirmation;
  target navigation derives validated internal IDs and rechecks Task access.
- Reused ui-ux-pro-max guidance, existing teal/neutral master, shared controls,
  error/pending/focus patterns and auth cache cleanup. No new framework, backend
  contract, schema/migration, role or security-setting change.
- Recorded source-verified gaps in `FE03_CONTRACT_MATRIX.md`: role metadata lacks
  current-assignee Submit/non-self Review proof; pre-existing Comments lack
  current-author mapping. Unsupported controls stay hidden. Own-comment edit/
  delete proof is restricted to the exact natural POST-returned UUID while the
  authenticated scope remains mounted, never an identity-probe mutation.
- Frozen frontend322/322 (21.69s), focused106/27/12, typecheck/lint44/build13.75s
  PASS. Real collaboration7/7 (1.4m; ca613d41c174462c9375f03c201ac4c8) and current
  Workspace/Task/Start7/7 (1.6m; f97f35926ad24bc2abb174f9a4edd83d) PASS with actual
  native/Playwright/backend exits0 and owned cleanup. Axe0/keyboard/overflow pass
  at four sizes;12 collaboration PNGs retained and four representatives reviewed.
  API-driven Submit/Review checks are distinct from unavailable UI actions.
- Current foundation Auth/CSRF/tenant6/6 PASS55.6s
  (runf7f4970fb102434699fcd26c9ef9d8e2), with actual exits0 and owned cleanup.
  All144 protected backend/config asset hashes and lock are unchanged; backend448
  remains historical. Fresh read-only development stays35 migrations/3 Users/
  2 Sessions/0 business/token/Notification/Audit rows;0 owned frontend test
  containers/networks remain. No unblocked implementation/test work remains.
- Stop at Owner review with PARTIAL — API GAP. Proposed HT-API-FE-P3-03A bounded
  Submit/Review/Comment capability hints require separate approval; no backend
  change or automatic next task is included.

### HT-API-FE-P3-02A — Task Identity, Assignment Roster & Start Capability — COMPLETE / OWNER REVIEW GATE

Historical completed extension before the separate Owner-approved FE03 scope.

- Added read-only Task.can_start, bound to authenticated request, verified tenant
  context, current active Editor assignment and ASSIGNED status. Existing Start
  service still rechecks permission/state under locks; no transition, role or
  identity policy changed. Task list/detail/mutation responses use the same hint.
- Extended the existing manager-only roster with display_label/is_assignable.
  Names use trimmed full name or a safe membership-code fallback, never username
  or email fallback. Eligibility follows current assignment-service predicates;
  existing visibility/pagination and ProfileMembership input identity retained.
  Prefetch/Exists/select_related limit query growth and loaded User fields.
- Integrated Start and roster labels/eligibility into the existing frontend forms,
  shared UI/UX master and scoped Query keys. Existing SessionAuthentication/CSRF,
  safe errors and server-confirmed success behavior retained. No new endpoint,
  dependency, model, schema or migration; no persistent development fixtures.
- Final targeted PostgreSQL91/91 PASS8.358s and full PostgreSQL448/448 PASS199.251s
  (runcb5fc651e02340989ac22c21b64d8857). Frontend targeted107/full224 PASS10.20s,
  typecheck/lint36/build6.42s PASS. Current real work-browser7/7 PASS
  (run0f46f8b31207406c8b073d606b593d36) and foundation6/6 PASS36.3s
  (run10f640b6e0e44666874a9cb1a9939186). Actual native/Python/Playwright/backend
  exits0 and owned cleanup verified; older baselines below remain historical.
- Both approved gaps are resolved and HT-FE-P3-02 is now IMPLEMENTATION COMPLETE.
  Fresh read-only development remains35 migrations/3 Users/2 Sessions/0 business
  rows;135 protected model/service/schema/config hashes unchanged. No persistent
  fixture/login/write/migration or production action. Documentation/checkpoint
  updated; no remaining implementation blocker. Stop at OWNER REVIEW GATE;
  proposed HT-FE-P3-03/Project/AI is not started.

### HT-FE-P3-02 — Workspace & Task Management UI — PARTIAL — API GAP / OWNER REVIEW

Historical FE02 checkpoint before Owner approved HT-API-FE-P3-02A above; its
missing-contract statements and201/7/6 counts are retained as historical notes.

- Reused the existing frontend stack, ui-ux-pro-max-guided design master and
  SessionAuthentication/CSRF client. Added Workspace create/metadata/archive/
  restore forms with strict inputs, confirmation, pending state and safe errors.
- Added scoped Task list/detail/create/edit/assignment and direct Subtask create,
  bounded ancestor/direct-child navigation, pagination and existing nullable
  deadline/priority controls. Server status/priority/hierarchy/deadline/order
  filters are distinct from search within the current loaded page. No Task/
  Review state machine or parent/child propagation rule changed.
- Capability controls fail closed using current scoped OPTIONS POST metadata
  and archive state; backend authorization remains final. Assignment uses
  existing sanitized ProfileMembership IDs and current Workspace MEMBER
  candidates without invented names/User-ID mapping; server eligibility is
  rechecked on mutation. No new role or staff authority is introduced.
- Kept START unavailable because available APIs do not safely map current User
  identity to assignment ProfileMembership identity. Role-only execution metadata
  is insufficient. Recorded API GAP for Owner review instead of adding a backend
  endpoint or assuming current-assignee authority. Existing CANCELLED remains a
  legacy display value without a cancel control or new workflow transition.
- Added contract/component/page tests and seven real Django/PostgreSQL browser
  cases with independent synthetic fixtures. The integration runner selects
  foundation/work-management in separate fresh owned runtimes, preserves all
  six foundation cases and existing throttles, and retains FE02 artifacts under
  its own ignored path. Fixture Python AST, runner PS syntax, E2E lint and diff
  checks pass. Final mock 201/201 (11.35s), typecheck/lint 36/build 7.01s, real isolated
  work 7/7 (56.5s) and foundation 6/6 (34.2s) PASS with actual launcher/Playwright/backend
  exits0 and owned cleanup. Responsive/axe0 violations/keyboard and representative
  visual PNG review passed. Vite now forwards OPTIONS instead of returning its
  synthetic CORS204; modal triggers preserve focus when dialogs close.
- Read-only development confirms PostgreSQL16.14,35 migrations,3 Users/2 Sessions
  and0 checked business/token/notification/Audit rows. No backend/model/migration
  change or persistent development fixture/login/write. Project remains pending
  Owner decision; Review/Comment/Notification UI and adjacent domains are not
  included. Full task completion is not claimed while the START gap remains.

### HT-FE-P3-01 — Frontend foundation — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE

Historical foundation checkpoint before the separate FE02 authorization.

- Added a single React/strict TypeScript/Vite frontend with npm lockfile,
  Router, Tailwind, TanStack Query and Node20-compatible Biome lint tooling.
- Added shared typed same-origin API transport, in-memory CSRF initialization/
  rotation, safe errors and login/logout/me auth-state/cache handling, without
  JWT, browser credential storage or backend security configuration changes.
- Added responsive Sidebar/Topbar, reusable accessible controls/states, protected
  routes and real-contract read-only Profile/Workspace pages. No fake dashboard
  metrics, business write controls, Project/AI or Task/Review screens.
- Documented ui-ux-pro-max search selection and stable tokens/components/layout
  in design-system/hustlytasker/MASTER.md; existing skill and design choices retained.
- Added quiet permission403 identity probes, stale-response/cache guards, public
  tab titles after logout/expiry and a Router-independent fatal fallback.
- Final strict typecheck, Biome lint24 files, production build6.67s and mocked
  frontend96/96 (API47,primitives15,AuthProvider16,App18;8.60s) PASS. JS output
  is388.07kB/gzip116.31kB, CSS31.44kB/gzip9.43kB; Vietnamese fonts are local.
- Separate real isolated Django/PostgreSQL/Chrome6/6 PASS40.7s; actual native
  launcher/Playwright/backend exits0 and owned DB/containers/two networks cleanup
  PASS. Real Session/CSRF/tenant reads/return navigation/expiry/revocation verify.
  Responsive375/768/1440 and812×375 landscape, keyboard/native-dialog and axe
  WCAG2/2.1 AA checks return0 violations;13 screenshots/visual PNG review retained.
- Earlier failed launcher attempts were isolated and cleaned; final frozen-source
  run passes. Final read-only development inventory and143 protected hashes are
  unchanged; no test resources/listeners remain. Backend415 historical baseline
  was not rerun because no backend implementation changed. No authenticated
  persistent test, interactive manual-browser or production-deployment claim.
  Documentation/HANDOVER complete; stop for Owner review before HT-FE-P3-02.

### HT-DB-P1-11 — Controlled Comment/Notification development rollout — COMPLETE / OWNER REVIEW GATE

- Verified original development PostgreSQL16.14 identity,33 applied migrations,
  current inventory and schema before writes; restarted the stopped existing
  container without recreation or volume changes.
- Created fresh104,092-byte Git-ignored custom backup; matching SHA256/size,
  240-line TOC/full-read and owned isolated restore/rehearsal PASS. Exact legacy
  values compared privately in memory; no fixture or inferred tenant mapping.
- Applied only tasks.0004 then notifications.0002, once each in separate
  migration transactions. Development now has35 records,8 Comment/12
  Notification columns,44 valid orphan-free FKs, valid CHECKs/partial unique/
  lookup indexes and unchanged3 Users/2 Sessions/business/metadata rows.
- Development read-only smoke67 anonymous requests +28 serializer-only checks
  PASS. Authenticated success/mutation flows remain isolated-test-only.
- Current isolated Comment40/40 (13.140s),Notification34/34 (8.431s),Task128/128
  (41.694s),security253/253 (224.745s),full415/415 (259.978s) PASS. All actual
  native launcher/Python runner exits0, dependency/system/model-drift/graph/
  full-chain checks and owned cleanup PASS. Historical415/415 is not reused.
- Final exact legacy/schema comparison after regression PASS. Owned rehearsal
  DB/temp dump removed, host backup retained with matching size/hash; no test
  container/network remains. All143 protected source/config/harness assets
  unchanged. Documentation/handover complete; stop for Owner review.
- Existing source, migrations, authentication, RBAC and event transaction
  policy are unchanged. Project remains PENDING OWNER DECISION.

## Unreleased - 2026-10-25

### HT-COM-P2-06 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

- Reused TaskComment for Task/Subtask discussion with 4000-character new-write
  validation, nullable edit/delete timestamps, protected Task history and
  paginated scoped CRUD. Current managers/Editors create; authors edit own
  content while authorized; authors/managers soft-delete, with redacted API
  tombstones and retained internal body. Viewer remains read-only; no manager
  rewrite of another author's text. Audit stores identifiers/facts, not body.
- Reused Notification/is_read with typed nullable legacy-safe tenant/Task/
  AuditLog-event context, completeness/type checks, unique recipient/event and
  feed index. Added only five explicit event producers: assignment, review
  submission, approval, requested changes and Comment creation. Current relevant
  recipients exclude actor, duplicates and revoked/inactive users. Notification
  persistence is atomic with the business mutation/audit; failure rolls back
  all of them. No signals, email/push, worker or second event system.
- Added own current-access-filtered Notification list/unread-count/mark-read
  APIs. Display text is constant; canonical target URLs contain only existing
  route IDs. Notifications grant no access; stale membership hides list/count/
  read mutation alike, including cross-user/tenant denial. Personal read state
  can change on archived targets that retain ordinary Task read access.
- Hardened strict-input malformed Unicode/NUL field names to return safe 400
  responses while preserving existing normal unknown-field errors. Existing
  Task hierarchy/review, authentication mechanism and CSRF remain unchanged.
- Added source migrations tasks.0004_task_comments and
  notifications.0002_notification_context; no guessed legacy mapping, content
  trimming, applied-migration rewrite or persistent development apply.
- Current isolated Comment 40/40 (6.919s), Notification 34/34 (5.401s),
  Task/Review 128/128 (22.637s), security/RBAC 253/253 (165.756s) and full
  PostgreSQL 415/415 (191.226s) PASS; all five native launcher/Python runner
  Docker-die exits are 0, Django OK and dependency/system/drift/graph/full-chain/
  owned cleanup PASS. Historical 341/341 is not reused. Final read-only
  development remains 33 records, 3 Users/2 Sessions and 0 Comment/Notification/
  business/token/Audit rows; new records/columns absent. No disposable test
  DB/container/network remains; only original development PostgreSQL remains.
- Documented limits: last-writer-wins Comment edits/no full text revision
  history; dedup is per event/recipient, not an HTTP POST idempotency key;
  hidden notifications may reappear after access restoration with read state
  preserved. Notification insert failure intentionally rolls back business/audit.
- AI Feedback Analyzer readiness records existing authorized feedback/context
  sources and gaps in full text revision/source attribution/human acceptance;
  no AI provider, Suggestions model or autonomous writer. Project remains
  PENDING OWNER DECISION. Retained deleted text is not an AI-readable source by
  default; future retrieval must honor authorization/redaction. Stop at Owner
  review; next proposed task is controlled development rollout of exact
  tasks.0004/notifications.0002 only after explicit approval. No task starts
  automatically and no persistent migration/commit/push occurred.

### HT-DB-P1-10 — Controlled Task hierarchy development rollout: COMPLETE / OWNER REVIEW GATE

- Verified original repository PostgreSQL 16.14 development identity,
  loopback/container/named-volume, 32 migration records and absent parent column;
  graph/history/drift/plan checks identified only exact additive tasks.0003.
- Retained fresh Git-ignored custom backup
  `.local_backups/HT-DB-P1-10/hustlytasker_dev_pre_tasks_0003_20261025T034208Z.dump`,
  102,780 bytes, SHA256
  `5225dc8a531df81c30d932bf400c896e707f9562d627e0336c51e1ee50ff4c83`.
  Matching host/container size/hash, 237-line TOC/full archive read and isolated
  exact-row restore plus migration rehearsal PASS.
- Applied existing tasks.0003 once at 2026-10-25 03:43:19.588793 UTC. Development
  now has 33 migrations/11 Task columns/40 validated FKs without orphans;
  nullable UUID parent/self-parent CHECK/FK and valid/ready lookup index verify. SQL FK
  is deferrable NO ACTION; ORM PROTECT and service graph validation are unchanged.
  All legacy rows remain exactly equal; 3 Users/2 Sessions and 0 checked business/
  token/Audit rows preserved, metadata 23 content types/92 permissions/7 Admin logs.
- Read-only development smoke 51 requests and 16 serializer-only checks PASS;
  no 500/PII/email/login/fixture/mutation. Authenticated success and mutation
  flows are NOT TESTED ON PERSISTENT DEVELOPMENT. Current isolated Task 88/88
  PASS (11.780s), related Auth/security/Invitation/Workspace/API regression
  253/253 PASS (162.615s), full PostgreSQL 341/341 PASS (170.987s). All three
  actual native-launcher/Python-container die exit codes are 0; Django `OK`
  and owned DB cleanup verified. Historical 341/341 is not reused.
- Final post-test checks/empty migration plan and exact legacy-row comparison
  PASS. Only ownership-verified rehearsal DB/container dump copy removed; fresh
  host backup retains original size/hash. No test/rehearsal resources remain;
  original development container/volume and all 129 baseline backend/config/
  Docker/harness asset hashes unchanged. No shared-harness or business-source
  edit, migration rewrite or new feature was introduced.
- Project remains PENDING OWNER DECISION. This task authorizes no production,
  Project, AI, Notification, frontend, commit/push or automatic next task.

### HT-TASK-P2-05 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

Historical implementation gate; the separate HT-DB-P1-10 rollout above now
applies its exact existing migration to the approved development target only.

- Reused Task for Subtasks through nullable protected `parent`, self-parent
  CHECK, same-Workspace/cycle validation, depth cap3 (root0) and subtree depth
  checks. Hierarchy mutations reuse existing scoped Profile/Workspace locks,
  manager capability and atomic audit. Existing legacy Tasks remain roots;
  no guessed mapping or change to Task/Deliverable/Review keys.
- Added `parent_id` to existing Task create/update/read contracts and a
  read-only paginated direct-children route. The default Task list stays flat;
  optional root/parent/status/priority/deadline filters and structured ordering
  support hierarchy navigation without recursive trees. Active-assignment
  membership lookup is batched for Task list reads.
- Reused existing LOW/MEDIUM/HIGH/URGENT priority (default MEDIUM) and nullable
  aware deadline, with safe API normalization/range validation. Existing
  Task manager permissions control writes. No overdue status changes,
  scheduler, notification, duration field or AI writer is added.
- Each Task/Subtask keeps independent workflow, assignment and review;
  parent completion may coexist with unfinished children. No automatic
  parent/child completion, assignment, priority or deadline propagation.
- Added `tasks.0003_task_hierarchy`, tested only on isolated PostgreSQL.
  Persistent development remains unmigrated for this change; no production
  action is authorized. Existing migration files are preserved.
- Current evidence: Task API42/42 PASS (4.990s), hierarchy/existing workflow
  services43/43 PASS (4.770s), migration2/2 PASS (1.465s), with dependency,
  Django, model-drift and migration-chain checks. Workspace/RBAC122/122 PASS
  (60.495s) and full PostgreSQL341/341 PASS (174.058s), including Auth/security,
  Invitation and Task/Review regression. Django `OK`, required checks and
  owned-test-DB cleanup are verified in logs. The wrapper did not retain the
  child exit code; no launcher exit-0 claim is made.
- Final read-only development: 32 migrations, 3 Users, 2 Sessions, zero verified
  Users/tokens/checked business/AuditLog rows; no tasks.0003 record or parent
  column. No test DB/container/network remains; only development PostgreSQL
  runs. No persistent migration or development business write was performed.
- Added `PROJECT_ARCHITECTURE_REVIEW.md`: **PENDING OWNER DECISION**. Compare
  A/B and future B′ preserving accepted Profile/Client-scoped cross-month
  Projects; no Project implementation. Current HT-TASK-P2-05 replaces the
  earlier proposed bundled HT-PROJ-P2-05 scope. Stop at **OWNER REVIEW GATE**.
  Proposed next operational task is controlled development tasks.0003 rollout
  after explicit approval and target inventory/backup/rehearsal. Project
  architecture remains a separate Owner decision; no automatic next task.

## Unreleased - 2026-10-24

### HT-TEST-P1-01 — PostgreSQL test harness and CI baseline complete

- Added dedicated test environment/settings, a shared serial PostgreSQL test
  command, and meaningful safety guard unit tests. The command checks pinned
  dependency consistency, Django, model/migration drift, graph/history, and
  the complete chain on a uniquely created/marked test DB before tests.
  It refuses non-fresh clusters/existing DBs and validates cluster/role/run
  ownership before cleanup; unsafe settings/runner/keepdb/parallel overrides
  are not exposed.
- Added a one-command PowerShell launcher plus test-only Compose/Dockerfile
  and restrictive build context. Each run gets a separate labelled PG16
  tmpfs cluster/internal network, no published PG port or persistent volume,
  Python 3.12, and read-only source. Verified run-ID cleanup supports hard
  interruptions without touching development resources or the Owner's venv.
- Added PR/push-main GitHub Actions backend CI using a fresh PostgreSQL 16
  service and the same shared core, read-only repository permissions, no
  production secrets/deploy, and nonzero failure propagation.
  **CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED.**
- Current actual evidence: guard unit tests 14/14 in 0.513s, targeted API
  10/10 in 0.044s, and full PostgreSQL 286/286 in 166.382s PASS through the
  one-command launcher, including dependency/system/model-drift/graph/history/
  migration-chain and owned-DB cleanup checks.
  The initial targeted attempt found a harness-only SimpleTestCase DB-selection
  issue, now fixed. A deliberate nonexistent label returns exit 1 and cleans
  its resources. Run-ID cleanup removes owned interruption fixtures; wrong-
  repository ownership is correctly refused. PowerShell parser, Compose,
  actionlint and diff checks PASS after fixing the workflow service-port key.
- README documents full/targeted commands, environment isolation, cleanup,
  and CI result interpretation. No business source/model/migration, API,
  SessionAuthentication/CSRF, or persistent development DB change is included.
  Development remains at 32 migrations, 3 Users/2 Sessions and zero tokens;
  original User/Session fields compare equal before/after in memory. No owned
  test container/network or test DB remains. **LOCAL TEST HARNESS VERIFIED**;
  task COMPLETE / OWNER REVIEW GATE. GitHub execution was not performed, so
  remote CI remains unverified. The full application is not declared complete.

### HT-DB-P1-09 — Controlled account-security development rollout complete

- Verified the repository-owned PostgreSQL 16.14 loopback development target;
  no production or other persistent target was accessed.
- Created a Git-ignored 93,598-byte custom backup, verified matching
  host/container SHA-256
  `195d7406015be1ce4d40f1b0f0f37094282abe7b82b7dd9b9c4b2c070827af49`,
  read its 223-line TOC/full archive, and restored it into an isolated
  PostgreSQL rehearsal database. Legacy rows matched before and after the
  exact additive migration rehearsal.
- Applied only `accounts.0002_accountsecuritytoken_user_email_verification`
  to approved development at `2026-10-24 06:30:28.634074 UTC`. Migration count
  is now 32. Added nullable verification fields and the empty 17-column token
  table with validated constraints/indexes. All 39 FKs have no orphans.
  All existing Users, Sessions, and business/AuditLog rows remain unchanged;
  no legacy User was verified or disabled. Django added only the expected new
  model content type/four permissions.
- Dependency/system/migration checks pass. Direct development smoke passes
  45 read-only fixture-free requests with enforced CSRF, including eight
  Task/Review boundary requests and one extra bootstrap, with no 500, PII/email
  disclosure, or row/session mutation. Authenticated success is not tested on
  persistent development; isolated fixtures cover that behavior.
- Current isolated account security 44/44 (30.549s), Authentication/API
  29/29 (7.523s), Invitation 40/40 (61.679s), Workspace/RBAC 140/140
  (79.717s), and Task/Review 33/33 (8.457s) PASS. Those completed runs were
  reused after resume with unchanged source/schema; the unfinished full-suite
  gate was rerun and passes 286/286 in 197.049s, exit 0. Full-test log/exit
  record remain under Git-ignored `.local_backups/HT-DB-P1-09/`.
  No feature source, model, migration file, or API contract changed.
- Final dependency/system/migration and exact legacy-row preservation checks
  pass. Test/rehearsal databases, the temporary runner, and container-side
  backup copy were removed. The verified host backup remains retained;
  development PostgreSQL remains running. Task COMPLETE / OWNER REVIEW GATE.
- **REAL EMAIL DELIVERY NOT VERIFIED. DISTRIBUTED RATE LIMITING NOT VERIFIED.**
  The process-local cache and non-equalized reset-request timing limits remain.

### HT-AUTH-P1-02 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

Historical implementation gate: the development migration prohibition and
inventory in this subsection were superseded by HT-DB-P1-09 above.

- Added nullable, current-email-bound verification state to `User` and a
  purpose-bound `AccountSecurityToken` aggregate for email verification and
  password reset. Tokens use high-entropy random credentials, persist only a
  purpose-separated SHA-256 digest, expire after 24 hours or one hour
  respectively, rotate on resend, and have locked single-use terminal states.
- Added additive
  `accounts.0002_accountsecuritytoken_user_email_verification` with paired
  verification-state checks, verified-identity uniqueness, token
  purpose/status/delivery/terminal consistency, pending-token uniqueness, and
  lookup indexes. Password-reset rows carry a SHA-256 fingerprint of the
  encoded Django password state, while `acctok_fingerprint_by_purpose`
  requires verification credentials to have no fingerprint and reset
  credentials to have one. The migration performs no verification backfill,
  is tested only on disposable PostgreSQL databases, and is not applied to
  persistent development or production.
- Added authenticated email-verification request/confirm and reviewed public
  password-reset request/confirm endpoints. All four unsafe routes require
  CSRF, strict input, scoped throttles, and non-cacheable responses. Reset
  requests return the same HTTP status/body across account outcomes;
  confirmation applies Django password validators, consumes the credential,
  does not create a session, and causes existing sessions to fail Django's
  password-backed session-hash check. Request timing is not equalized or
  verified indistinguishable.
- Material email changes clear verification and revoke pending verification
  and reset tokens, including an `A -> B -> A` sequence. Password changes via
  `User.save()` revoke pending resets; direct queryset updates still invalidate
  the stored password fingerprint at confirmation. Existing registration/login
  behavior remains available to unverified legacy users. Profile Invitation
  retains its independent authenticated, unique-current-email, delivered-
  invitation-token proof and was not changed into a global-verification gate.
- Extracted the shared configured-mail safety primitive used by Invitation and
  account-security delivery. Credential delivery rejects console/dummy/file
  backends; locmem is permitted only for isolated tests. No raw token or
  password is returned, logged, audited, or persisted. Reset confirmation now
  uses independent raw-token-fingerprint `10/hour` and client-address
  `30/hour` throttles. Malformed Unicode on public reset and Invitation
  recipient input fails closed with `400` instead of reaching a `500` path.
- Final isolated PostgreSQL verification passes account security 44/44 in
  32.336s, Authentication/API/Invitation 113/113 in 99.629s,
  Workspace/RBAC/Task/Review 173/173 in 93.895s, and the full suite 286/286 in
  188.592s. `pip check`, Django system check, migration drift, and
  `git diff --check` pass; diff check emits only existing LF/CRLF notices.
- Read-only development remains PostgreSQL 16.14 `hustlytasker_db` with 31
  migrations, `accounts.0001` only, `workspace.0001`-`0004`, 3 Users, 2
  sessions, zero checked business/AuditLog rows, no verification columns/token
  table, and no test database. `accounts.0002` requires separate Owner approval.
- **REAL EMAIL DELIVERY NOT VERIFIED.** No real provider was configured or
  exercised. Default DRF cache throttles remain process-local rather than
  distributed multi-worker enforcement.

## Unreleased - 2026-10-23

### HT-DB-P1-08 — Controlled Invitation development rollout completed

- Verified the repository-owned loopback PostgreSQL 16.14 development target.
  Its pre-apply state had 30 migrations, 3 Users, 2 sessions, no Invitation
  table, and zero checked business rows; production was not accessed.
- Created a retained Git-ignored custom-format backup (78,758 bytes; matching
  SHA-256
  `57f05837925c74a1bef83200a4211c3ed1cffbbe1e24552377d7efefc9baaf76`),
  verified its 198-line TOC and full archive read, and completed/removed an
  isolated restore-and-apply rehearsal.
- Applied only `workspace.0004_profileinvitation` to development at
  2026-10-23 05:09:39.628419 UTC. Post-check reports 31 migration records, an
  empty 22-column Invitation table, seven validated CHECKs, seven validated
  foreign keys, two partial unique constraints, and all 16 indexes valid/ready.
  Existing row/session counts did not change.
- Django system, migration-drift, and `migrate --check` checks pass.
  Fixture-free direct smoke passes health, CSRF/registration, anonymous
  Profile lifecycle, Workspace read/write/lifecycle, Workspace membership,
  and every Invitation route shape without a 500, token/digest/User-PII leak,
  or row/session mutation. Authenticated success/mutation paths were not run
  on persistent development.
- Current isolated PostgreSQL reruns pass: Invitation 39/39 in 62.528s,
  Auth/API 29/29 in 7.475s, Workspace/RBAC/Task/Review 173/173 in 97.378s, and
  full suite 241/241 in 167.960s. Each Django test database was destroyed and
  the full run reported zero system-check issues. Status is **COMPLETE / OWNER
  REVIEW GATE**.
- Verified cleanup left no test/rehearsal database or disposable runner. The
  exact container temporary archive was hash-checked and removed; the host
  backup remains Git-ignored with its original size/hash. The development
  PostgreSQL container was already running at task start and remains running.
- Final `git diff --check` passes with only existing LF-to-CRLF conversion
  warnings; final Git status preserves the expected uncommitted Invitation
  implementation/documentation files and introduces no operational artifact.
- **REAL EMAIL DELIVERY NOT VERIFIED** and the process-local cache-throttle
  limitation remain unchanged. No API contract, feature source, migration file,
  production target, or other persistent environment was changed by this
  operational task.

### HT-INV-P2-04 — Profile Invitation & Membership Onboarding

- Added `ProfileInvitation` and additive
  `workspace.0004_profileinvitation`: Profile/email/account/inviter scope,
  `ADMIN`/`MEMBER` ceiling, digest-only 256-bit credential, seven-day expiry,
  five terminal/lifecycle states, delivery state, actor timestamps, immutable
  replacement lineage, database checks, partial uniqueness, and indexes.
- Added locked services for create, revoke, resend/rotation, accept, decline,
  expiry, compatible ProfileMembership creation/reactivation, stale
  WorkspaceMember revocation on rejoin, original-inviter revalidation,
  database-backed issuance limits, and atomic AuditLog events.
- Added authenticated manager list/create/detail/revoke/resend and recipient
  accept/decline APIs. SessionAuthentication, CSRF, tenant-safe lookup, role
  ceilings, strict input, non-cacheable output, and no token/hash/User-PII
  disclosure are enforced. No anonymous preview or recipient inbox was added.
- Added `transaction.on_commit` mail delivery with honest
  `QUEUED`/`SENT`/`FAILED` state. Failed committed delivery is recoverable only
  through manager discovery plus resend/token rotation. Unsafe development mail
  backends are rejected; locmem is isolated-test-only.
- Added lifecycle, RBAC, identity, IDOR, CSRF, replay, delivery failure,
  rollback, audit, migration-preservation, throttle, and concurrency coverage.
  Invitation **39/39**, Auth/API **29/29**, Workspace/RBAC/Task/Review
  **173/173**, and full PostgreSQL **241/241** pass. Dependency, Django system,
  and migration-drift checks pass; every test database was destroyed.
- At the HT-INV-P2-04 implementation checkpoint, persistent development still
  had 30 migrations, 3 Users, 2 sessions, zero checked business rows, no
  Invitation table, and `workspace.0004` unapplied. That historical boundary
  was superseded when the Owner separately opened controlled rollout
  `HT-DB-P1-08`; production remains untouched.
- **REAL EMAIL DELIVERY NOT VERIFIED.** No real provider credential was
  configured; current cache throttles are process-local in multi-worker
  deployments. These deployment limits are documented rather than hidden.

## Unreleased - 2026-10-21

### HT-DB-P1-07 — Controlled Task/Review development rollout completed

- Xác minh đúng local Docker Desktop/Compose PostgreSQL 16.14 development
  target, loopback binding và named volume; production không được truy cập.
  Baseline có 28 migration, 3 active Users, 2 sessions, zero checked business/
  workflow rows, schema/history khớp và toàn bộ preflight integrity checks bằng
  zero.
- Tạo backup custom-format Git-ignored 75,502 bytes; SHA-256 host/container
  khớp, TOC 192 dòng đọc được và full archive read PASS. Restore rehearsal
  cô lập tái tạo baseline, apply tuần tự Tasks/Reviews 0002, kiểm tra schema
  thành công rồi được xóa.
- Apply explicit `tasks.0002_task_workflow_foundation` lúc 2026-10-20 23:35:36
  UTC, kiểm tra intermediate gate, rồi apply explicit
  `reviews.0002_review_workflow_foundation` lúc 23:36:12 UTC trên development.
  Migration count tăng 28 → 30; inventory dữ liệu/session không đổi.
- Hậu kiểm xác nhận column nullability/no permanent DB default, năm CHECK và
  Review unique constraint validated, sáu index valid/ready, actor FK validated
  và mọi invalid-enum/duplicate/orphan/cross-tenant/unvalidated check bằng
  zero. Không fake/reverse/edit migration, guessed backfill, fixture hoặc xóa
  dữ liệu.
- Fixture-free development smoke PASS cho health, CSRF/login và anonymous
  denial của Profile/Workspace/Task/Deliverable route shapes; không `500` và
  không đổi row/session. Authenticated business mutation không chạy trực tiếp
  trên development trống; isolated PostgreSQL tests là evidence cho các path
  đó.
- Verification hiện thời: Task 33/33, Auth/API 29/29, Workspace 140/140 và full
  PostgreSQL 202/202 PASS; dependency/system/migration checks PASS. Test/
  rehearsal databases và runner tạm đã được dọn.
- Task vận hành này chỉ thay đổi documentation; không sửa backend source,
  model, migration file, Authentication hoặc API contract. Dừng tại Owner
  review gate; không tự mở module tiếp theo và không authorize môi trường khác.

### HT-TASK-P2-03 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

- Bổ sung service/API foundation cho Task management và internal Deliverable
  approval: create/update/assign/start, revisioned submit, approve và request
  changes; completion chỉ xảy ra sau internal approval hợp lệ.
- Áp dụng tenant-scoped permission hiện hữu: Profile Owner/Admin và Workspace
  Admin manage/review; active Profile Member + Workspace Editor chỉ start/submit
  Task đang được assign cho mình; self-review và stale/repeat review bị chặn.
- Thêm nested `/api/v1/` routes, strict serializer inputs, no-PII attribution,
  bounded pagination, non-enumerating IDOR behavior, SessionAuthentication và
  CSRF; không expose PUT/DELETE hoặc arbitrary status mutation.
- Thêm additive source migrations `tasks.0002_task_workflow_foundation` và
  `reviews.0002_review_workflow_foundation`: actor FK `PROTECT`, status/priority
  checks, indexes, một active assignment/Task, positive revision và một
  Review/Deliverable. Legacy assignment được giữ nhưng inactive; legacy
  revision giữ `NULL`; không guessed backfill.
- Chuyển Task/TaskAssignment/TaskComment Admin thành inspection-only và chặn
  Workspace hard delete trong Admin để tránh cascade xóa Task workflow history.
- AuditLog được ghi atomic cho create/update/assign/reassign/start/submit/
  approve/request-changes. Internal approval được đánh dấu riêng, không phải
  Client approval và không tạo Payroll/Payment hay tính compensation.
- Targeted PostgreSQL service/API/migration suite PASS 33/33 trong 7.673s;
  existing Authentication/API/Workspace regression PASS 169/169 trong
  87.783s; final full PostgreSQL PASS 202/202 trong 92.343s. Dependency,
  Django system và migration-drift checks PASS; test DB được hủy; independent
  final code review PASS.
- Hai migration mới chưa apply development hoặc production. Trước rollout phải
  inventory invalid enum, duplicate Review per Deliverable và legacy assignment,
  backup, review plan và dừng nếu cần mapping/cleanup chưa được phê duyệt.
- Read-only development post-check giữ nguyên 3 Users, 2 sessions và zero
  checked workflow/business rows; `showmigrations` xác nhận Workspace 0001-0003
  applied, Tasks/Reviews chỉ 0001. `migrate --plan` thành công và chỉ liệt kê
  additive `tasks.0002` rồi `reviews.0002`; không migration nào được apply.

## Unreleased - 2026-10-20

### Controlled Workspace 0003 development rollout completed (HT-DB-P1-06)

- Xác minh đúng local development target: Compose container
  `hustlytasker_postgres`, PostgreSQL 16.14, database `hustlytasker_db`,
  loopback-only port và named volume hiện hữu; production không được truy cập.
- Kiểm kê pre-apply có 27 migrations, 3 active Users, 2 Django sessions và zero
  checked business rows. History/schema cùng xác nhận `workspace.0003` chưa
  tồn tại vật lý; exact plan chỉ có 11 additive operations đã review.
- Tạo custom-format backup Git-ignored 73,521 bytes, xác minh SHA-256, TOC và
  full archive read; full restore rehearsal tái tạo đúng 27 migrations/3 Users
  trong database tạm rồi cleanup.
- Áp dụng đúng `workspace.0003_workspace_lifecycle_and_period` lên development.
  Post-check có 28 migrations, bốn field mới đúng nullability/no permanent DB
  default, ba CHECK constraints validated, partial unique Profile/month và ba
  lookup indexes valid/ready. Inventory không đổi; không có invalid lifecycle/
  period, duplicate month, unvalidated constraint hoặc guessed mapping.
- **DEV SMOKE PASSED** không tạo fixture: health `200`, CSRF/login behavior đúng,
  mọi Profile/Workspace/membership route từ chối anonymous `403`, và row/session
  counts không đổi. Authenticated role/tenant/IDOR/lifecycle success cases chỉ
  được chạy trên isolated PostgreSQL test databases.
- **ISOLATED INTEGRATION TEST PASSED:** lifecycle/schema 17/17, Workspace
  140/140, Authentication/API Foundation 29/29 và full PostgreSQL 169/169;
  dependency/system/migration checks PASS. Mọi test database và runner tạm đã
  được hủy.
- Không sửa backend source, applied migration, Authentication hay API contract;
  không reverse/`--fake`, xóa dữ liệu, tạo business fixture hoặc tác động
  production. Task dừng tại Owner review gate.

### Historical HT-WORK-P2-02 implementation checkpoint — superseded by HT-DB-P1-06 rollout

- Bổ sung additive source migration
  `workspace.0003_workspace_lifecycle_and_period`: Profile/Workspace lifecycle
  status, canonical Workspace monthly period, constraints/indexes và
  `WorkspaceMember.is_active`. Unique `(profile, period)` bao gồm cả Workspace
  archived; legacy `NULL` period được giữ cho controlled rollout, còn supported
  create bắt buộc ngày đầu tháng.
- Bổ sung `POST` cho Workspace collection và `PATCH` cho Workspace detail dưới
  nested Profile. Create bắt buộc `period`; non-first-day trả `400`, monthly
  duplicate kể cả archived trả `409`; server-owned/unknown fields bị từ chối,
  không cho re-parent Workspace hoặc giả mạo owner.
- Bổ sung Profile archive/restore cho Profile Owner và Workspace
  archive/restore cho Profile Owner/Admin. Archived record vẫn đọc được trong
  tenant scope, nhưng normal metadata/child/membership mutation bị chặn cho tới
  khi restore. Profile/Workspace hard delete không được expose.
- Bổ sung Workspace-member manager roster `GET`, direct-add `POST` bằng
  `target_profile_membership_id`, role-update `PATCH`, và soft revoke `DELETE`.
  Revoke giữ row lịch sử, mất effective access ngay; eligible re-add tái kích
  hoạt cùng row. Response chỉ gồm assignment/ProfileMembership metadata, role,
  active state và timestamps; không trả User ID, email, username hoặc PII.
- Áp dụng role ceilings đã duyệt: Profile Owner/Admin tạo/cập nhật Workspace và
  quản lý `ADMIN/MEMBER/VIEWER`; Workspace Admin chỉ sửa metadata Workspace của
  mình và quản lý `MEMBER/VIEWER`. Editor, Viewer, Profile Member chưa được gán,
  legacy Workspace `OWNER`, staff/superuser và cross-tenant input đều fail
  closed.
- Roster được ràng buộc với authority hiện tại của actor ngay trong queryset và
  chỉ trả assignment hiệu lực có active User + active same-Profile membership.
  Lookup nested sai tenant/wrong parent không làm lộ tồn tại; API chuẩn hóa
  validation/permission/not-found/conflict thành `400`/`403`/`404`/`409`.
- Các write service dùng transaction, Profile-first row locks, revalidation và
  AuditLog nguyên tử cho create/update/lifecycle và membership create/update/
  revoke/reactivate; rollback cả mutation khi audit thất bại và xử lý
  duplicate/concurrency ổn định.
- Giữ SessionAuthentication, CSRF cho unsafe methods, DRF deny-by-default và
  không thêm `AllowAny`. Verification cuối: `pip check`, Django system check và
  `makemigrations --check --dry-run` PASS; Workspace PostgreSQL 140/140 trong
  79.278s và full PostgreSQL 169/169 trong 82.920s PASS. Migration rehearsal
  `0002 -> 0003` bảo toàn Task/Deliverable/Review.
- Latest successful development inventory ngày 2026-10-19 có 27 migration
  rows, `workspace.0002` applied, `workspace.0003` unapplied, 3 User, zero
  business rows và không còn test database. Read-only check ngày 2026-10-20
  thấy PostgreSQL container đang dừng và không khởi động lại. `migrate --check`
  exit `1` đúng dự kiến do pending migration. Không apply migration/write
  development và không truy cập production; bước tiếp theo chỉ là Owner review
  và quyết định controlled development migration.

### Controlled development migration completed (HT-DB-P1-05)

- Khôi phục Django development runtime bằng biến môi trường chỉ tồn tại trong
  process và cached Python 3.12 container; không tạo `.env`, không ghi secret,
  không reset credential và không sửa venv/source.
- Xác minh lại backup trước migration và thực hiện restore rehearsal đầy đủ
  trên database tạm biệt lập; schema/data trước migration khớp archive và
  database rehearsal đã được dọn.
- Review `migrate --plan` và áp dụng đúng migration additive
  `workspace.0002_profile_workspace_foundation` lên development. Hậu kiểm xác
  nhận 27 migration rows, Profile/ProfileMembership tables,
  `Workspace.profile_id`, constraints/indexes hợp lệ; 3 User và toàn bộ
  business counts vẫn không đổi, không tạo tenant mapping giả định.
- Direct HTTP smoke đạt: health `200`; bốn Profile/Workspace route và
  `/api/auth/me/` anonymous `403`; CSRF bootstrap `200`; login giả thiếu token
  `403`, có token hợp lệ `400`; không có `500` hoặc session mới.
- Regression gate hiện thời PASS: targeted read API 21/21, Authentication/API
  Foundation 29/29, full PostgreSQL suite 101/101; dependency, Django system,
  migration drift/applied checks và cleanup checks đều đạt.
- Không thay đổi backend source, model, migration file, authentication hoặc API
  contract. Chỉ existing migration được apply trên development đã phê duyệt;
  không production, không business fixture, không write/membership/Invitation
  API.

### Pre-migration safety checkpoint (superseded historical evidence)

- Xác minh độc lập PostgreSQL development hiện hữu từ Compose của repository:
  `workspace.0001` đã apply, `workspace.0002` chưa apply; Profile tables và
  `Workspace.profile_id` chưa tồn tại.
- Kiểm kê trước migration ghi nhận 3 User đều active và 0 Workspace,
  WorkspaceMember, Task, Client, Invoice, Payment, AuditLog; không có orphan,
  foreign key chưa validate hoặc test database còn sót.
- Xác nhận migration `workspace.0002_profile_workspace_foundation` không đổi,
  chỉ gồm thay đổi additive và không có backfill/delete/drop/rename hay mapping
  tenant giả định.
- Tạo backup PostgreSQL custom-format trong `.local_backups/HT-DB-P1-05/`,
  thêm thư mục này vào `.gitignore`, và xác minh host/container SHA-256 khớp,
  TOC đọc được, toàn bộ archive stream qua `pg_restore` thành công. Không restore
  vào database nào.
- Dừng trước `migrate --plan` và apply vì repository không có `.env`, runtime
  không có `DJANGO_SECRET_KEY` development hợp lệ, còn Python/venv host không
  hoạt động. Không tự tạo secret, trích xuất/reset credential hay lách settings.
- Không thay đổi backend code, model, migration, API contract, authentication,
  development schema hoặc row. Smoke/regression mới chưa chạy; kết quả 101/101
  của P1-04 vẫn chỉ là bằng chứng lịch sử.

### Profile/Workspace read API and DRF tenant permissions

- Thêm bốn endpoint read-only dưới `/api/v1/`: Profile list/detail và nested
  Workspace list/detail. Giữ nguyên SessionAuthentication, global
  deny-by-default và không thêm `AllowAny`.
- Thêm minimal serializers chỉ trả metadata đã phê duyệt; không expose
  transitional owner, membership, role, email hoặc PII.
- Nối DRF permission trực tiếp với tenant access contexts và scoped selectors
  từ HT-RBAC-P1-03. Profile Owner/Admin đọc mapped Workspace cùng Profile;
  ordinary Member chỉ đọc Workspace có effective `ADMIN`, `MEMBER` hoặc
  `VIEWER`; legacy `OWNER`, Profile-null, transitional owner và platform flags
  không bypass scope.
- Chuẩn hóa list bằng page-number pagination bounded (20 mặc định, 100 tối đa)
  và stable ordering. Malformed, unknown, cross-tenant, wrong-parent và
  out-of-scope IDs cùng trả generic JSON `404`.
- Chỉ hỗ trợ `GET`/`HEAD`/`OPTIONS`, thêm no-cache boundary và xác nhận unsafe
  request phải qua auth/CSRF và tenant permission trước (`403`/`404` nếu fail);
  request đã được authorize với CSRF hợp lệ mới trả `405`. Không nhánh nào thay
  đổi dữ liệu hay AuditLog.
- Sửa race khi Profile membership bị revoke sau DRF permission nhưng trước lúc
  queryset được evaluate: late stale-context exception được map về cùng generic
  `404`; thêm regression cho Workspace list/detail.
- Thêm 21 PostgreSQL API tests cho session access/CSRF, multi-Profile, role matrix,
  revoke/inactive, IDOR, legacy/unmapped data, staff non-bypass, pagination và
  no-write contract. Final full suite PASS 101/101; Authentication/API
  Foundation regression PASS 29/29.
- Không đổi model, schema, migration, authentication, service business rule,
  Docker hoặc development data. `workspace.0002` vẫn chưa apply development;
  rollout và smoke test cần một operational approval riêng.

### Documentation and handover governance

- Thêm root `AGENTS.md` làm quy tắc bắt buộc cho mọi agent: đọc source/docs và
  Git trước khi code, bảo toàn dirty worktree, không scope creep, checkpoint
  task dài, verification trung thực và cập nhật tài liệu theo thay đổi thực tế.
- Thêm `documentation/HANDOVER.md` làm checkpoint bàn giao độc lập với lịch sử
  hội thoại, gồm trạng thái stack, task, Git, test, quyết định, setup và bước
  tiếp tục an toàn.
- README trỏ developer mới tới `AGENTS.md` và `HANDOVER.md`; không ghi secret
  hoặc credential vào tài liệu.

### Workspace architecture decision

- Hoàn tất audit thiết kế `HT-DATA-P2-01` dựa trên current Django source,
  migrations, requirement gốc và legacy discovery evidence.
- Ghi nhận tại thời điểm audit trước implementation: schema chưa có Profile;
  Workspace ownership có hai nguồn truth; Client/Finance/Audit chưa có tenant
  path; Task actors chưa được ràng buộc cùng Workspace.
- Owner phê duyệt Profile làm tenant root và Workspace làm operational scope
  theo tháng; tách Profile membership, Workspace participation và
  Client/Guest access principals.
- Bổ sung ownership matrix, data-isolation invariants, migration/backfill plan
  và test plan vào `DECISION_LOG.md` và `DATABASE_SCHEMA.md`.
- Chốt 11 nhóm quyết định: multi-Profile, multi-Owner, administrator
  inheritance, invitation consent/direct-add boundary, Client/Project,
  Workspace-scoped finance, separate public links, soft-delete target,
  migration safety và high-level Task/Review loop.
- HT-DATA-P2-01 design là `COMPLETE / ACCEPTED`; bản thân task design không
  thay đổi model, migration, User/authentication, API, dữ liệu hoặc frontend.

### RBAC, tenant access và invitation design

- Thêm `documentation/RBAC_DESIGN.md` cho `HT-RBAC-DESIGN-P0-01`; task hiện
  `COMPLETE / ACCEPTED — APPROVED BY OWNER DELEGATION`.
- Hoàn thiện capability matrix hai tầng Profile/Workspace, tách internal roles
  khỏi Client Portal/Guest Review và không coi enum hiện có là quyền đã duyệt.
- Đề xuất request context, tenant-scoped queryset, same-tenant input
  validation, non-enumerating IDOR/error behavior, service/transaction lock
  order và controls cho ORM/bulk/job/Django Admin bypass.
- Ghi nhận `update_profile_membership()` lookup membership globally, còn
  `add_workspace_member()` lookup Workspace globally và nhận target User đã
  resolve ngoài scope; chưa có API khai thác nhưng phải refactor trước exposure.
- Hoàn thiện Profile Invitation contract: recipient consent/binding, token
  hash-at-rest, state/expiry/replay, duplicate/concurrency, audit, planned API,
  negative tests và dependency-ordered rollout.
- Đối chiếu toàn bộ RBAC design với 11 nhóm quyết định đã duyệt: audit ban đầu
  xác định nhóm 4 bị mở rộng sai nhãn từ active Owner sang usable Owner và nhóm
  6–9/11 thiếu ghi nhận một phần/toàn bộ. Đã sửa tài liệu để cả 11 nhóm đều
  `MATCH`, không thay đổi quyết định nghiệp vụ đã duyệt.
- Owner ủy quyền Technical Advisor chốt 14 quyết định: role compatibility và
  action ceilings, last-owner/deactivation target, Invitation identity/TTL/rate/
  retention, non-enumeration và platform-superuser Admin boundary.
- Ghi rõ reviewer role/workflow states và các domain downstream vẫn cần contract
  riêng; Invitation chưa được triển khai và verified email là dependency trước
  production enablement.

### Tenant access context and scoped membership services

- Thêm `backend/apps/workspace/access.py` với immutable verified Profile/
  Workspace contexts, Profile/Workspace scoped selectors và capability checks
  revalidate active account/membership/role trước khi cấp read, edit hoặc member
  management.
- Giữ nguyên enum: `WorkspaceMember.ADMIN` = Workspace Admin, `MEMBER` = Editor,
  `VIEWER` = read-only Viewer; legacy `OWNER` fail closed và không được cấp mới.
- Refactor `update_profile_membership()` để scope actor/Profile trước target,
  áp dụng Profile Admin least privilege, giữ last-active-owner locking và audit.
- Refactor `add_workspace_member()` dùng scoped ProfileMembership target, cho
  Profile Owner/Admin cấp `ADMIN/MEMBER/VIEWER`, Workspace Admin chỉ cấp
  `MEMBER/VIEWER` trong Workspace của mình, và xử lý duplicate/concurrency bằng
  stable domain conflict.
- Harden context trước direct construction, `dataclasses.replace()` role
  forgery và stale User/Profile/Workspace role; denied mutation không tạo audit.
- Không đổi model, schema, migration, SessionAuthentication hoặc route/API.

### Profile/Workspace schema foundation

- Thêm `Profile` và `ProfileMembership` với role
  `OWNER`/`ADMIN`/`MEMBER`, active state, partial unique constraint for active
  Profile/User membership (inactive history is retained), role
  check và tenant lookup indexes.
- Thêm transitional nullable `Workspace.profile`; bảo vệ Workspace owner bằng
  `PROTECT`; thêm validation cho Workspace owner và Workspace member phải có
  active membership trong cùng Profile.
- Thêm transactional services để tạo Profile cùng initial Owner và cập nhật
  membership an toàn: hỗ trợ nhiều Owner, giữ ít nhất một active Owner, chặn
  Admin thay đổi Owner và ghi AuditLog cho thay đổi membership.
- Khóa Profile/Workspace theo thứ tự thống nhất cho normal persistence, chặn
  concurrent re-parent/mapping và yêu cầu reassign transitional Workspace owner
  trước khi bỏ Profile manager status.
- Khóa cả save của Workspace legacy hiện hữu trước khi chấp nhận Profile null,
  ngăn stale instance ghi đè một mapping Profile vừa commit; bổ sung regression
  concurrency test cho tình huống này.
- Thêm audited direct-add service: Profile Owner/Admin chỉ có thể thêm User đã
  có active Profile membership vào Workspace.
- Thêm negative tests xác nhận quyền quản lý ở một Profile không cấp quyền thay
  đổi membership hoặc direct-add Workspace ở Profile khác.
- Thêm additive migration
  `workspace/0002_profile_workspace_foundation.py`, model/service/concurrency
  tests và populated-data migration test. Không sửa `0001_initial.py`.
- Read-only development inventory ghi nhận 0 business rows và 3 User rows;
  không tạo mapping giả định. `0002` mới chạy trên disposable PostgreSQL test
  databases và chưa apply development database.
- Không thay đổi User/session authentication hoặc API contract. Không triển
  khai Invitation, Workspace API/full RBAC, Project/Client/Finance migration,
  public-link flows, soft delete hay detailed Task/Review workflow.

### Authentication

- Thêm session authentication API tại `/api/auth/`: CSRF bootstrap, register, login, logout và current user.
- Dùng Django password validators và `create_user()`; password chỉ write-only, login lỗi trung tính và user inactive bị chặn.
- Bảo vệ register/login/logout bằng CSRF đúng với session flow; logout chỉ dùng `POST` và revoke current session.
- Chuyển DRF sang explicit `SessionAuthentication` và permission mặc định `IsAuthenticated`; public auth endpoints khai báo `AllowAny`.
- Thêm scoped throttle (`10/minute` login, `5/hour` register), giới hạn password input 128 ký tự và mặc định `DRF_NUM_PROXIES=0` để không tin forwarding header chưa được kiểm soát.
- Sửa User admin bằng cách đặt `created_at`/`updated_at` readonly.
- Không thay đổi User model, Profile, Workspace, schema hoặc migration.

### API security baseline

- Hoàn tất implementation deny-by-default cho DRF và thêm regression guard để
  mọi route trong API URL tree đều là DRF view.
- Giới hạn explicit `AllowAny` vào public allowlist đã review; view dùng
  permission mặc định từ chối anonymous và chấp nhận authenticated user.
- Gỡ legacy `/api/test/` và thay bằng `/api/health/` public, không auth,
  throttle hoặc database query; payload chỉ gồm `{"status":"ok"}` và response
  không được cache.
- Health hỗ trợ `GET`, `HEAD`, `OPTIONS`; mutation method và `TRACE` trả `405`.
- Thêm 10 API health/policy tests; chưa thay đổi Workspace, RBAC, business
  models, schema hoặc migrations.

### Security and dependencies

- Chuẩn hóa `backend/requirements.txt` sang UTF-8 để Git và công cụ dependency đọc ổn định.
- Nâng Django từ 6.1 lên 6.1.2 để nhận các bản vá bảo mật hiện hành.
- Nâng Django REST Framework từ 3.15.0 lên 3.18.3 để dùng phiên bản hỗ trợ Django 6.1 và có các bản vá bảo mật mới.
- Externalize Django secret, debug, allowed hosts, PostgreSQL, CSRF, HTTPS/cookie/HSTS và Django 6.1 mailer configuration qua environment variables có validation fail-fast.
- Thêm `.env.example` sạch, giữ `.env` ngoài Git và tài liệu hóa đầy đủ quy trình local setup.
- Chuyển PostgreSQL Compose credential sang biến bắt buộc và bind port vào `127.0.0.1` mặc định mà không thay named volume.

### Verification

- Fresh install và `pip check` thành công trong Python 3.12 container.
- Django system check, migration drift check, applied-migration check và legacy `/api/test/` smoke test từng thành công; endpoint này sau đó được thay bằng `/api/health/`.
- Tại thời điểm HT-OPS-P0-01, test discovery chạy được nhưng dự án chưa có automated tests; các task Authentication/API sau đó đã bổ sung test suite.
- Các case thiếu/sai environment fail rõ; production-like `check --deploy --fail-level WARNING` thành công khi cung cấp HTTPS, secure-cookie, HSTS, host và SMTP values phù hợp.
- Tại checkpoint `HT-SEC-P0-02`, chưa có model/migration thay đổi; PostgreSQL
  development khi đó có 8 domain migrations và 23 public tables trên named
  volume hiện hữu.
- `pip check`, Django system check, migration drift/applied checks và full suite 19/19 tests đều thành công trên PostgreSQL.
- Development server khởi động thành công; `GET /api/auth/csrf/` trả `200` cùng CSRF cookie/token.
- `pip check`, Django system check, migration drift/applied checks và full suite 29/29 tests (19 authentication + 10 API health/policy) đều thành công trên PostgreSQL ngày 2026-10-15.
- Development server smoke thành công: `GET /api/health/` trả `200` JSON/no-store, `POST` trả `405`, legacy `/api/test/` trả `404`, và `/api/auth/csrf/` vẫn trả `200` cùng CSRF cookie.
- Sau audit thiết kế ngày 2026-10-16, chạy lại `pip check`, Django system
  check, migration drift/applied checks và toàn bộ 29/29 regression tests trên
  PostgreSQL: PASS; test database tạm được Django xóa, không có schema hay dữ
  liệu ứng dụng bị thay đổi.
- Verification cuối của schema foundation ngày 2026-10-17: targeted
  `apps.workspace` 32/32 và full PostgreSQL suite 61/61 PASS; `pip check`,
  `manage.py check` và `makemigrations --check --dry-run` PASS. Read-only
  inventory trước/sau test không đổi, và không còn test database tạm.
- Verification tài liệu cho HT-RBAC-DESIGN-P0-01 ngày 2026-10-17: required
  section/status check, UTF-8/no-NUL, secret-pattern scan và
  `git diff --check` PASS (chỉ có cảnh báo LF→CRLF hiện hữu). Không rerun backend
  tests vì task không đổi code và local Python/venv hiện không khả dụng; không
  tạo container hoặc môi trường thay thế mới.
- Verification cuối HT-RBAC-P1-03 ngày 2026-10-18 trên PostgreSQL 16: local
  Python 3.12 virtualenv được đồng bộ đúng Django 6.1.2/DRF 3.18.3; `pip check`,
  compile, `manage.py check` và `makemigrations --check --dry-run` PASS; targeted
  Workspace 51/51 và full suite 80/80 PASS, gồm 19 Authentication và 10 API
  Foundation regressions. Test database tạm được Django hủy; development
  `workspace.0002` vẫn unapplied và development data không đổi.
- Verification cuối HT-API-P1-04 ngày 2026-10-18 trên PostgreSQL 16: targeted
  read API 21/21, Authentication/API Foundation 29/29 và full suite 101/101
  PASS; `pip check`, compile, Django system check và migration drift check PASS.
  Test database tạm được hủy, không còn `test_%` database; development migration
  và data không đổi.


# Version 0.0-foundation

Date:
2026-08-08


## Completed

### Project Structure

- Created project folder structure.
- Created backend folder.
- Created frontend folder.
- Created docker folder.
- Created database folder.


### Documentation

Created:

- ORIGINAL_REQUIREMENTS.md
- DEVELOPER_PROFILE.md
- ARCHITECTURE.md
- TECH_STACK_DECISION.md
- DATABASE_SCHEMA.md
- API_DOCUMENTATION.md
- REQUIREMENT_STATUS.md
- PROJECT_ROADMAP.md
- PROGRESS.md
- DECISION_LOG.md
- AI_INSTRUCTION.md


### Reference Documents

Imported original system documents:

- Discovery documents.
- Architecture diagrams.
- State diagrams.
- Security documents.
- Account documents.


### Version Control

Completed:

- Git initialization.
- First commit.
- GitHub repository connection.


## Historical initial status

Project foundation completed.


## Historical initial next phase

Phase 1:
Development Environment Setup
