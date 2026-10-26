# HUSTLYTASKER HANDOVER

## Current checkpoint — 2026-10-26 — HT-FE-P3-01 IMPLEMENTATION COMPLETE / OWNER REVIEW GATE

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
