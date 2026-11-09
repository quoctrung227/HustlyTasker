# HT-AI-P4-02A — AI Persistence, Retention & Locking Review

## HT-AI-P4-04C — Chosen governance schema and offline implementation checkpoint

Date2026-11-08. **OFFLINE GOVERNANCE IMPLEMENTATION READY / DEVELOPMENT MIGRATION PENDING.** The Owner now authorizes
additive candidate models/migrations and offline governance implementation on
isolated PostgreSQL. This supersedes04B's no-schema-work boundary only for the
candidate; persistent development migration, live transport, billing/data egress
and production remain forbidden. Design was checked against actual models and
reviewed independently before implementation; no destructive business change.

### Chosen minimum structure

Append three models, preserving AiProposal/AiOperation and ai.0001 unchanged:

| Model | Chosen scope / invariants |
|---|---|
| AiDispatch | Actor/Profile/Workspace/feature, trusted provider/model/mode/config/pricing versions, scoped key/body digests and provider-policy HMAC, dispatch lifecycle, token limits/nullable usage, reservation/estimate/billed/accounted amounts kept distinct, claim/timestamps and immutable settlement digest; optional protected proposal link |
| AiBudgetBucket | Shared GLOBAL/Profile/User limits/counters within execution mode; exact scope FKs, lifetime/nonresetting identity, cost/request/inflight bounds, immutable server policy |
| AiDispatchReservation | One protected dispatch→bucket record per each of the three server-derived scopes; immutable reserved amount and HELD/SETTLED/RELEASED settlement state |

Candidate ai.0002_dispatch_governance creates only these new tables/indexes/
constraints. No existing rows need tenant/provenance guessing or backfill; old
fixture proposals/operations keep their current provenance/serializer semantics.
A future proposal link must match actor/Profile/Workspace and contract; this
internal layer does not create a Generator proposal or analysis history itself.
All FKs protect accounting history; no purge/retention scheduler is introduced.
The fields/generated migration pass isolated drift/full-chain and six migration
tests; no migration is applied to persistent development.
The unchanged HTTP/fixture paths do not query these tables before enablement.
Arbitrary parent hard-delete/AdminCollector maintenance can follow newly declared
PROTECT relations and requires the candidate schema; do not perform that
maintenance on development before separately approved rollout. No such operation
is authorized or tested against persistent development here.

Dispatch uniqueness is actor/Profile/Workspace/feature/mode/key_digest. Trusted
provider/model/config/pricing and actual bounded input belong in the keyed body
fingerprint, so a changed configuration with the same key conflicts rather than
silently authorizing another call. HMAC uses a separate Django purpose namespace;
raw canonical inputs, briefs, feedback, focus and provider bodies are transient.

Bucket identity does not include model, pricing/config version or date. Chosen
limits are cumulative/lifetime until a separately reviewed administration/window
policy exists. This deliberately avoids dropping prior-day OUTCOME_UNKNOWN holds
from concurrency or giving a new global budget on model/config change. Incoming
policy disagreement fails closed; no resetting counters or automatic rollover.
All features/providers in a mode share the same scope buckets. Monetary figures
in this task are simulated exposure/accounting, not actual live invoices.

### Locking, state and uncertain outcome contract

Every operation reuses current tenant manager authority and the original actor
boundary. Lock order: existing tenant/Profile/Workspace context → GLOBAL budget
→ Profile budget → User budget → dispatch/reservations. One short atomic reserve
checks shared cost/request/inflight limits and creates the unique claim/holds
before any transport. Equivalent requests reuse metadata; changed bodies conflict.
Only the atomic RESERVED→DISPATCHING winner may invoke the offline adapter, after
commit and outside database locks. No Python mutex or locmem limit is authoritative.

| Transition | Meaning / accounting |
|---|---|
| New→RESERVED | No provider attempted; all three atomic holds/request counts acquired |
| RESERVED→DISPATCHING | Durable claim committed before callback; a crash from here is potentially charged |
| RESERVED→FAILED_BEFORE_DISPATCH | Definitive no-attempt/cancel; release cost/inflight, retain request attempt count |
| DISPATCHING→SUCCEEDED | Valid result and known simulated usage settled once; unused hold/inflight released, accounted estimate distinct from billing |
| DISPATCHING→OUTCOME_UNKNOWN | Timeout/cancel/error/invalid usage or possible success followed by persistence failure; hold cost and concurrency, no automatic retry |
| OUTCOME_UNKNOWN→RECONCILED | Explicit current-authorized original actor supplies consistent simulated evidence; same evidence idempotent, conflicting evidence denied |

DISPATCHING can itself be retained uncertainty if the database is unavailable;
do not claim UNKNOWN was necessarily written after a persistence outage. Worker
expiry/elapsed time never proves no charge and never releases unknown holds.
No transition back to RESERVED and no automatic paid retry is authorized. A
revoked actor cannot read/reconcile; reservations remain held until a separately
approved operator workflow exists, rather than inventing an RBAC bypass.

### Gating, offline execution and live limits

New code is gated before new-table queries by explicit AI_GOVERNANCE_ENABLED,
an enabled trusted GovernancePolicy and current development/nonproduction fixture
guard. This is an additional offline-only gate; fixture enablement alone cannot
activate governance. No runtime setting or persistent .env is changed. Current
services continue on legacy fixture paths without requiring unapplied tables.
Only OPENAI_OFFLINE is executable; OPENAI_LIVE remains rejected regardless of
key/config presence. Existing OpenAI adapter/fake transport stays unchanged.

Generator wrapper validates brief; Analyzer wrapper reuses existing selected
Review/Comment resolver and current-source checks, not client-constructed DTOs
as authorization. No new public endpoint/response or user-facing history is added.
First execution can return a transient ProviderResult; a duplicate receives its
durable receipt without redispatch or recovery of unstored response text. Live
proposal storage/response integration remains a later separately reviewed slice.

Known fake usage may generate a synthetic rate-based estimate and budget debit;
actual billed_cost remains NULL for offline records. Unknown usage, usage beyond
configured exposure or estimate beyond reservation retains uncertainty. Policy
rates/token bounds are server-owned simulation parameters, not proven strict
upper bounds for real OpenAI billing. Live stays disabled until model-specific
input/output/reasoning overhead, pricing, shared limits and billing monitoring
are reviewed; database controls alone cannot promise absolute billing prevention.

### Actual service surface and limits

Implemented functions are reserve_dispatch/get_dispatch/begin_dispatch/
fail_before_dispatch/mark_unknown/reconcile_dispatch and execute_generator/
execute_feedback. GovernancePolicy and BudgetLimits are trusted frozen
dataclasses; default enabled false and zero cost/request/inflight limits deny
work. The missing AI_GOVERNANCE_ENABLED setting defaults false through getattr;
no production setting/env-loader addition is implied. Internal DispatchReceipt
is metadata only; DispatchExecution carries an optional transient ProviderResult.
No public endpoint or generic proposal/result recovery is wired.

Reconciliation accepts bounded simulated amounts and optional paired token
counts; its HMAC binds dispatch/actor/scope/evidence. Same evidence is idempotent,
conflicting evidence is rejected. It is a trusted caller assertion, not verified
OpenAI usage/billing evidence. There is no budget reset/purge/operator role or
administrative bypass. This intentionally fails closed for revoked actors and
uncertain holds; operational recovery must be reviewed before live activation.

### Fresh verification and exact continuation gate

Final focused52/52 PASS15.286s:46 service/security tests including same-key
single-fake-dispatch and different-Profile global-cap races on independent
PostgreSQL connections, plus6 migration cases. Full isolated826/826 PASS231.558s
covers existing Generator/confirmation/Analyzer/adapter and domain regressions.
Final focused/full launcher and actual Python exits0; dependency/Django/drift/
graph/full migration chain and owned cleanup PASS. Initial fixture-only setup
errors and corrected reruns are preserved in HANDOVER/ignored evidence, not
counted as successful runs. No frontend/browser/live-provider tests were rerun.

At10:21:26Z final read-only29-table data/schema/index/sequence/history/cluster
fingerprints exactly match preflight:36 migrations/4 Users/2 Sessions/
1 Profile/membership/Workspace/Task/3 AuditLogs/ReviewCommentAI0. Candidate0002
and its three tables remain absent.246 other original files plus old model code
are unchanged; all five tested files are stable after the full suite.
No .env/credential or development data/flag/schema change was made.

Status: **HT-AI-P4-04C — OWNER REVIEW GATE**. Proposed next slice is separately
approved development migration readiness with fresh backup/isolated restore;
actual apply needs an explicit subsequent approval. Do not regenerate candidate
0002, apply it, enable governance/live transport or begin another task here.

## HT-AI-P4-04B — Offline OpenAI target and proposed live accounting (2026-11-08)

Historical04B checkpoint; the chosen04C candidate and verification are above.

Current status: **OFFLINE OPENAI ADAPTER COMPLETE — OWNER REVIEW GATE**.
The Owner has selected OpenAI, `gpt-5.4-mini`, Responses API and strict Structured
Outputs for an offline injected-transport implementation. This supersedes the
P4-04A provider-selection blocker only for that bounded implementation target.
Real inference budget remains USD0; private data egress, live activation and
database migrations are not approved. No AiProposal/AiOperation field or existing
confirmation/replay policy changes. Current results belong in [HANDOVER](HANDOVER.md);
the P4-04A215-test duration below is **16.523 seconds**, not16,523 seconds.
Current offline tests:55/55 PASS0.038 seconds, followed by apps.ai270/270
PASS13.347 seconds (55 new plus215 existing). Launcher and actual Python exits0
are verified for both runs; required checks and owned cleanup pass. Every245
pre-existing source hash remains unchanged, with only the adapter and its test
new. Final read-only29-table fingerprints/schema/sequences/history/cluster match
the new4-User baseline exactly; no schema/data/flag change. Live activation is
still blocked by the proposed provenance/accounting and privacy gates below.
See [current architecture](AI_ARCHITECTURE_DESIGN.md#ht-ai-p4-04b--offline-openai-adapter-2026-11-08).

### Existing fixture records remain authoritative

AiProposal stores a validated synthetic TaskPlan under its current scenario,
actor/Profile/Workspace, revision and expiry lifecycle. AiOperation's successful
GENERATE/CONFIRM digests and one-confirmation constraint remain unchanged.
An offline adapter response is not inserted into a fixture proposal or relabeled
as live output; all HTTP application paths stay on their existing FixtureAdapter
guards. No provider call is introduced into confirmation or a tenant lock.

The internal adapter can construct/parse an OpenAI request without changing these
models. That is not evidence that current storage can retain truthful live
provider/model/usage provenance or prevent duplicate paid calls. Generated text
can repeat a confidential brief; raw-input exclusion alone does not settle
derived-output retention.

Its current internal ProviderResult is explicitly `provider:openai_offline`,
usage status `offline_simulated`, with fake token values or unknown values and
cost None. No provider-returned token count is represented as measured billing.
The module has no ORM, environment/key loading or application dispatch wiring;
it cannot create a proposal, operation, Task or analysis record by itself.

### Proposed migration design — NOT IMPLEMENTED / NOT APPROVED

Before any future paid application wiring, review the smallest provenance and
dispatch/accounting extension. The following concrete fields/constraints describe
a design candidate, not Django models or a migration authorization:

| Candidate change | Purpose and required compatibility rule |
|---|---|
| Proposal `provider`, `model`, `execution_mode`, `provider_contract_version` | Server-controlled immutable origin, independent of generated TaskPlan JSON. Existing rows backfill only to known `fixture` / `deterministic-fixture-v1` / `fixture_demo`; never infer a live origin from payload text |
| Proposal or linked dispatch `usage_state`, `input_tokens`, `output_tokens`, `cost_usd`, `pricing_version` | Nullable token/cost values mean unknown, not zero. Distinguish simulated data from provider-reported usage and reconciled accounting; exact numeric units and bounds need approval |
| Metadata-only `AiDispatch` identity | UUID, actor/Profile/Workspace, feature, key digest, canonical body digest, trusted provider/model/config-contract version, optional proposal FK. No raw brief, feedback, focus, provider body or credential |
| Dispatch lifecycle | Explicit RESERVED/DISPATCHED/SUCCEEDED/FAILED/UNKNOWN states, created/dispatched/completed timestamps, lease/claim owner and safe error category. UNKNOWN means remote completion or usage may have occurred and requires reconciliation |
| Scoped dispatch uniqueness | Unique actor/Profile/Workspace/feature/provider-config-version/key digest; body mismatch is conflict. A first committed reservation owns dispatch; simultaneous requests cannot each acquire the same claim |
| Budget reservation metadata | Approved User/Profile/global period keys, currency/pricing version, reserved and settled amounts. Nonnegative amounts and an immutable reservation link; locking/atomic updates must enforce limits across workers |

Existing fixture HMAC/replay namespaces must stay byte-compatible. A future live
canonical body includes its request/contract/provider configuration version and
all allowed business input; it cannot collide with an old fixture key. Do not
store raw canonical bodies. Retain original-actor/current-authorization checks
for proposal read, confirmation and replay; a dispatch or proposal UUID grants
no authority. Do not broaden supported AiOperation operations silently.

### Dispatch, accounting and recovery proposal

1. Authorize current actor/scope and validate input, then reserve the unique
   request and approved User/Profile/global budget atomically using a documented
   lock order. Compute a conservative reservation from bounded input and approved
   output/reasoning tokens and current pricing. Do not use locmem as the ledger.
2. Commit the short reservation transaction before network I/O. Claim once and
   dispatch outside tenant/Task/proposal locks. A same-key/body duplicate receives
   pending/recovery semantics; it must not dispatch merely because no proposal
   has yet been stored. A different body conflicts.
3. Validate output/provenance/usage, reauthorize, and atomically link the winning
   proposal and settle known usage. Provider response arrival does not authorize
   Task creation; existing human confirmation remains the mutation boundary.
4. A timeout, disconnect, cancellation or terminated worker after dispatch moves
   to UNKNOWN unless no dispatch/charge is demonstrably proven. Preserve its
   reservation rather than automatically refunding or issuing a new call.
   Recovery/reconciliation must distinguish pre-dispatch lease loss from uncertain
   remote completion; no universal exactly-once billing promise is possible.
5. Start with no automatic retries. Any later retry policy needs an approved
   provider-specific idempotency/retry-cost analysis. Alerts/provider rate limits
   supplement the shared ledger; they do not establish a hard application budget.

Exact types, field lengths, unique/check constraints, scope indexes, FK policies,
lease behavior, lock order, retry/recovery API and retention durations require
Owner review and isolated concurrency tests. Inventory existing rows, review
deterministic fixture backfill, backup and restore rehearsal before a separately
approved schema rollout. No destructive change or rewrite of ai.0001 is proposed.

Analyzer stays stateless: a future metadata-only cost/dispatch record need not
retain source text, analysis JSON or history. Its final source/permission recheck
can discard an advisory result without erasing an actual charge. No text purge,
shared ledger, migration or new infrastructure is implemented by P4-04B.

## HT-AI-P4-04A — Live persistence readiness (2026-11-08)

Status: **DESIGN READY / PROVIDER IMPLEMENTATION BLOCKED — OWNER REVIEW GATE**.
The current task permits engineering audit and a safe adapter only when provider
choice/architecture are already approved. Existing decisions approve fixture-only
v1; a live provider/model, data-processing mode and spending enforcement remain
unapproved. No model, migration, persistence service or development database is
changed by this readiness review. See the current
[provider readiness proposal](AI_ARCHITECTURE_DESIGN.md#ht-ai-p4-04a--live-provider-readiness-2026-11-08).

### Existing guarantees and the live gap

- [AiProposal/AiOperation](../backend/apps/ai/models.py) store the Generator's
  validated TaskPlan, scoped operation/body digests and confirmation outcome.
  AiProposal requires `scenario_id`; neither model records provider/model, live
  provenance, metered usage, dispatch ownership or a spending reservation.
- [generate_proposal](../backend/apps/ai/durable_services.py) validates an optional
  brief transiently and binds it to the HMAC request digest. When present, that
  validated brief reaches ProviderRequest; otherwise the scenario brief is used.
  FixtureAdapter deliberately ignores semantic content. Raw brief is not stored
  in proposal/operation fields or copied to public errors/AuditLog.
- Two short authorization/replay transactions surround adapter dispatch. Two
  concurrent same-key requests can both dispatch before the second transaction
  chooses one stored outcome. Existing scoped replay and atomic confirmation
  prevent duplicate committed Tasks; they do **not** prevent duplicate live
  provider charges. Do not hold tenant/Task locks across a network request to
  hide this gap.
- Reusing `payload` for a validated live TaskPlan is structurally possible, but
  current response serialization hardcodes fixture provenance and zero usage.
  Silently storing live output there would make retrieval/replay misleading.
  Generated titles/descriptions can also repeat confidential input, so excluding
  the raw brief does not make derived proposal retention a solved privacy issue.

### Proposed only — requires separate approval before schema work

Design the smallest durable provenance and dispatch/accounting extension after
provider/data/budget choices are approved. Record trusted provider/model/contract
provenance independently of generated JSON; reserve an authorized scoped request
before dispatch; represent in-flight, completed, failed and ambiguous outcomes;
reconcile actual usage without automatically releasing an unknown charge.
Enforce any approved global/per-tenant budget through shared durable accounting,
not locmem counters. Confirm's existing original-actor/current-permission checks,
body-bound replay and atomic existing Task services remain the mutation boundary.

Exact fields, locking order, unique constraints, request identity, retry/recovery,
retention and migration/backfill are a **proposal**, not an accepted schema.
No additive migration is created or applied here, and physical purge remains
unimplemented. Existing fixture TTL/recovery rules are not automatically approved
for private live inputs or their derived output.

Feedback Analyzer remains stateless and advisory. It needs no analysis-history
model for the approved workflow. A later live budget/dispatch ledger would track
safe operational metadata, not implicitly authorize raw feedback persistence or
history. Neither live activation nor a new infrastructure dependency is approved.

Current-task validation belongs in [HANDOVER](HANDOVER.md). The tests and database
snapshots below are historical; they are not new P4-04A test/preservation claims.

## Historical P4-02C checkpoint

Updated: **2026-11-02**. At that checkpoint: **P4-02C fixture React integration — IMPLEMENTATION
COMPLETE / OWNER REVIEW GATE**. R3's development rollout remains preserved.
Original02A/02B proposal and implementation evidence remain historical below.
Overall Smart Task Generator remains PARTIAL: fixture UI implementation is complete;
live provider/budget/private-data integration remains absent and separately gated.

## Verified P4-02C persistence integration

No model, migration or lifecycle change is needed for React preview/edit/confirm.
AiProposal/AiOperation and R3's36 applied migrations stay intact. The Owner's
bounded optional synthetic brief is validated transiently; when present it joins
the canonical HMAC body fingerprint, not a raw database field. Absent `brief`
retains legacy scenario-only digest/replay compatibility. Response and AuditLog
do not copy brief content. Fixed fixture output still does not analyze input.

UI edits stay in User-scoped memory until full edited-plan confirmation; there
is no PATCH save or localStorage draft/key persistence. Refreshing the known
proposal URL retrieves the stored server proposal, not unsaved local changes.
Preview notes/assumptions/warnings are not Task model fields. The existing
30-minute preview,7-day logical payload bound and30-day result recovery remain;
no automatic physical purge is added.

The confirmation dialog freezes key/revision/payload and uses the unchanged
atomic service. An ambiguous response triggers known-ID GET reconciliation
before any manual same-key/body resend, and retry requires AVAILABLE with the
same proposal ID/revision as the frozen confirmation. Stale state cancels the
old confirmation and requires fresh review. A fresh blind key never becomes the
recovery strategy. Original actor plus current tenant/manager authorization is
rechecked for read, confirm and replay. Revocation/archive prevents recovery;
the proposal UUID or cached preview is not an access grant.

Fresh read-only development baseline:36 migrations,3 Users/2 Sessions,
1 Profile/1 membership/1 Workspace/1 Task and0 AI rows. Preserve these newer
records; older zero-business snapshots are historical. Current full isolated
backend676/frontend537, quality and all8 real isolated Chromium suites30/30
pass; actual exits0/cleanup and final0 owned test containers/networks are
verified in HANDOVER. Final
read-only development29-table row/schema/sequence/history/cluster comparison
is exact and45 protected source hashes are unchanged. Proof is retained in
`.local_backups/HT-AI-P4-02C/preservation-proof.json`; inventory is still36
migrations/3 Users/2 Sessions/1 Profile/1 membership/1 Workspace/1 Task/AI0.
P4-02C changes no persistent
flag, provider, retention policy, Task workflow or development data.
Manual development acceptance remains unverified; fixture enablement or another
implementation requires the next Owner decision. No automatic follow-on task.

## Historical R3 persistence deployment checkpoint

Only `ai.0001_initial` was applied once through standard Django on the verified
development PostgreSQL16.14 target, actual child exit0 at2026-11-02T04:07:32Z.
The current pre-apply snapshot matched R2's schema/sequences/all row fingerprints;
its retained110161-byte archive and successful isolated restore remained valid.
R3 reverified checksum/readability/TOC251/full read, without unnecessary backup
or rehearsal repetition. Source migration and210 runtime hashes are unchanged.

Post-checks confirm AiProposal15 columns/AiOperation9,7 FKs,18 constraints and14
indexes valid/ready;36 total migrations/29 tables/136 indexes. Every original row
was preserved, including3 Users/2 Sessions/business0; both AI tables are empty.
Only expected1 migration/2 ContentTypes/8 permissions and sequence increments
1/2/8 were added. Django/model/graph/history/migration consistency and8 actual
loopback HTTP GET smoke checks passed, all preflight/apply/post child exits0.

The existing environment loader consumed private local values only for child
processes, without displaying or changing them. No provider call, fixture or
business mutation test, production action, new model/migration or runtime edit.
R1's72/158 and full643 suites below remain historical, not rerun in R3.
Fixture flag remains false; physical purge and shared quota limitations remain.
See [AI_DEVELOPMENT_MIGRATION_READINESS.md](AI_DEVELOPMENT_MIGRATION_READINESS.md)
and [HANDOVER.md](HANDOVER.md) for retained evidence. Proposed fixture UI requires
separate Owner approval; stop at OWNER REVIEW GATE.

## Historical P4-02B persistence implementation checkpoint — 2026-10-28

The Owner now approves a minimal durable Generator with manager/actor binding,
atomic confirmation, scoped idempotency and additive AI migrations applied only
to isolated PostgreSQL tests. [AI02B_SCHEMA_REVIEW.md](AI02B_SCHEMA_REVIEW.md)
documents the fifteen-point pre-model gate. Source has AiProposal/AiOperation,
registered apps.ai and ai.0001_initial; development apply is NOT authorized.
Current targeted isolated PostgreSQL AI suite: **158/158 PASS in 11.208s**, run
`bf34f0b7fd384c7a9958b4513cea18ac`. Actual launcher/Python-container exits0 and
owned DB/container/network cleanup are verified. This includes 3 migration tests
covering empty/related-data forward/reverse and constraints, plus durable
concurrency/rollback/security. Targeted Task/Review/Workspace/RBAC regression
**378/378 PASS in 165.639s**, run `d41c6561e93f4b6489e0a858d87a75de`;
full isolated PostgreSQL backend **643/643 PASS in 215.115s**, run
`6bdba3440f8d46edb28df73a9b30fe03`. Actual launcher exits and Python PID1
container die exit codes are0; pip check, Django/model drift, migration graph/
full chain and owned DB/container/network cleanup PASS. Final 210 test-source
hashes remain unchanged. Docker Engine recovered and was checked before these
runs; no Docker/WSL/PostgreSQL restart occurred. Historical 77/562 below does not
replace this final current-source evidence.

Development read-only verification found PostgreSQL 16.14, 35 migration records,
3 Users, 2 Sessions, 0 business rows and no AI tables. No development migration,
fixture creation or data modification occurred. Persistent rollout needs its
own approval, inventory, backup and rehearsal.

AiProposal holds stable UUID, actor/Profile/Workspace, AVAILABLE/CONFIRMED,
contract_version/revision/scenario, nullable normalized payload/created_tasks,
created_at, expires_at, payload_expires_at, confirmed_at and recovery_expires_at.
AiOperation holds the same scope, GENERATE/CONFIRM, key/body digests, protected
proposal FK and created_at. Every scope FK is PROTECT; JSON Task mapping creates
no cascade/deletion dependency on business Task rows. Constraints enforce valid
states, timestamp/lifecycle ordering, unique(scope,operation,key_digest) and one
CONFIRM operation per proposal. Cross-table scope equality remains service/model
validation, not a claimed SQL CHECK across tables.

Current policy: preview30 minutes from creation; unconfirmed payload ceiling7
days; confirmation recovery30 days from committed confirmation. Payload is
cleared on successful confirm; metadata/result are not returned after recovery
expiry. Minimal consumed state persists independently and cannot be reset by
scrub. Physical purge is not implemented: seven-/30-day physical retention maxima
are **not automatically enforced**. No development data is scrubbed or deleted.

Body fingerprints use purpose-derived Django salted_hmac with current configured
key and SECRET_KEY_FALLBACKS verification; no raw body, key or confidential text
is logged. Missing old key fails closed rather than allowing duplicate creation.
Generate fixture runs outside business atomic blocks; storage/confirm/retrieve
then reauthorize under existing tenant locks followed by proposal/operation.
Generation stores only proposal/operation state: no Task and no AuditLog.
Confirmation only calls current create_task; all Task/audit/outcome writes share
one transaction, including safe ai.proposal.confirmed metadata. No budget
ledger/lease lock family is introduced for zero-cost
fixtures. Full key scope lookup detects same key reused for another proposal.

Current Owner decisions are in AI_ARCHITECTURE_DESIGN section18 and the P4-02B
DECISION_LOG entry. Production/live/provider/account/private-data policy remains
pending; Analyzer runtime/frontend and persistent rollout remain excluded.

## Historical P4-02A review scope

Sections 1–12 below preserve the original 02A review and its decisions at that
time. They are historical/future-design evidence, not as-of-now denials of the
fixture-only02B authorization and tested source described above. In particular,
the 30-minute/7-day/30-day fixture windows, manager/actor gate, two-record schema
and bounded confirmation now have scoped approval; live/private/Analyzer/budget
designs remain deferred. They do not imply physical purge enforcement.

Tài liệu này là proposal/pseudocode, **không phải Django models, migrations hoặc
cơ chế durability đã triển khai**. HT-AI-P4-02A chỉ cho phép contracts, validation,
provider interface và deterministic fixture không network/chi phí/ghi dữ liệu.
Không phê duyệt toàn bộ AI-D01–AI-D10; không cho phép P4-02B, live provider hoặc
confirmation tạo Task. Thiết kế tổng thể ở
[AI_ARCHITECTURE_DESIGN.md](AI_ARCHITECTURE_DESIGN.md).

## 1. Historical02A evidence và ranh giới

Checkpoint Git khi bắt đầu: `main`, HEAD `502a444`. AGENTS.md, HANDOVER và source
được đối chiếu; không đọc `.env`, kết nối development hoặc tạo database fixture.

| Evidence | Hệ quả cho persistence tương lai |
|---|---|
| [create_task](../backend/apps/tasks/services.py) | Atomic; gọi tenant mutation helper, chỉ Manager hợp lệ; status PENDING, creator từ actor và safe audit. Không có batch confirmation/idempotency |
| [lock_workspace_mutation_context](../backend/apps/workspace/services.py) | Profile → Workspace → actor ProfileMembership → WorkspaceMember nếu cần; kiểm tra lại lifecycle/role, không tin snapshot UI |
| [Task model](../backend/apps/tasks/models.py) | Root depth0, tối đa3 child edges; parent cùng Workspace; no duration/dependency/Project storage |
| [Comment services](../backend/apps/tasks/comment_services.py) | Soft-delete vẫn giữ content trong DB; không được dùng retained text làm AI source hoặc trả saved analysis chứa nội dung suy ra từ nguồn đã xóa |
| [AuditLog](../backend/apps/audit/models.py) | JSON metadata cho kiểm toán, không phải confidential proposal store, usage ledger hoặc unique idempotency registry |

Fixture/contracts có thể chạy thuần bộ nhớ vì không tạo Task và không gọi live
provider. Một preview fixture không được coi là chứng nhận rằng durability,
cross-worker budget, confirmation hoặc live AI đã hoạt động.

## 2. Có cần persistence không? Có tái sử dụng models hiện tại không?

| Phương án | Phù hợp | Thiếu sót / quyết định |
|---|---|---|
| In-memory typed DTO, không ghi DB | Contracts/fixture unit tests trong P4-02A | Đúng scope hiện tại; mất khi restart, không đảm bảo replay/budget/confirmation |
| Frontend state hoặc client-signed proposal | Preview tạm thời có thể dùng sau này | Không đủ để bảo đảm một lần confirm xuyên worker/restart; chữ ký không thay current authorization hoặc durable uniqueness |
| LocMemCache/cache TTL | Có thể giảm tải không nhạy cảm | Process-local; expiry/restart làm mất replay evidence; không là authority/budget guard |
| Nhét payload vào AuditLog/Task/Comment hiện hữu | Không đề xuất | Sai mục đích; lộ nội dung qua audit, thiếu unique state/locking; không tạo Task nháp chỉ để giữ AI preview |
| Dedicated AI proposal/invocation/confirmation và budget state | Đề xuất cho task triển khai tương lai | Cần app/schema, retention/access/key/locking approval; không có model/migration trong P4-02A |

Recommendation: **stateless fixture/contracts hôm nay; dedicated durable state
trước khi triển khai confirmation hoặc live budget guarantees**. Không tạo một
AI permission engine, không đổi Task/AuditLog/Review để né migration review.

## 3. Original02A schema proposal — pseudocode, không executable ORM

Tên record dưới đây mô tả logical responsibilities. Có thể gộp/split sau schema
review; chưa quyết định tên bảng, Django app registration hoặc migration number.

```text
Proposal
  id: server UUID
  scope: actor identity + authorized Profile/Workspace; optional Task for analysis
  purpose: TASK_PLAN | FEEDBACK_ANALYSIS
  mode/provenance: server-owned fixture/live mode; contract/prompt/model versions
  payload: bounded normalized proposal/analysis JSON; no raw provider response
  revision: server-owned positive revision
  source_manifest: selected source kinds/IDs + internal keyed fingerprints/version
  generated_at, preview_expires_at
  lifecycle: available | invalidated | confirmed
  confirmed_result: local_ref -> created Task IDs, only after atomic confirmation

Invocation
  id: server UUID
  scope: actor + Profile/Workspace + optional Task + operation
  idempotency_key_digest, canonical_request_hmac, hmac_key_version
  request_state: reserved | dispatched | completed | failed | outcome_unknown
  proposal reference if validated output was safely published
  reservation/actual usage: exact integer micro-USD or Decimal; token categories
  policy/price/adapter versions; sanitized outcome; timestamps/correlation ID
  NO prompt, brief, feedback body, raw provider JSON, API key or session cookie

Confirmation
  id: server UUID; proposal reference
  scope: actor + Profile/Workspace + operation
  idempotency_key_digest, canonical_edited_plan_hmac, hmac_key_version
  immutable result mapping + committed_at
  unique(scope, actor, operation, key_digest)
  unique(proposal) for the single committed creation batch

BudgetState / DispatchGate (logical state; detailed schema still pending)
  deterministic global/Profile/Workspace/User keys + UTC period identifiers
  exact reserved/settled cost, active leases; enabled policy/version
  unique(key, period); transaction-safe updates, no floating-point money
```

Foreign keys must preserve existing business data on User departure and controlled
tenant deletion. No cascade from an AI record to Task/Review/AuditLog. The precise
PROTECT/SET_NULL policy, pseudonymous retained actor identity and allowed hard
delete process need review; this document does not impose a new User retention
rule. Never make confirmed Tasks dependent on deleting an AI preview record.

Scope consistency is not automatically guaranteed by two independent foreign
keys. If Profile and Workspace are both stored, every write/read must verify
Workspace belongs to Profile; detailed schema review must decide whether approved
composite constraints can reinforce it. Task/source IDs are resolved through the
same tenant chain. Do not claim a normal CHECK constraint can inspect other tables.

Unique key constraints are necessary but not sufficient: actor/workspace/operation,
body match, state, membership, source permissions and proposal consumption must
be checked in services. DB constraints only enforce the guarantees they express.

## 4. Minimize stored confidential content

Store only normalized bounded payload needed for preview/recovery. Derived
analysis can itself disclose confidential feedback; omitting raw prompts does
not make it public or anonymous. Do not copy raw brief, selected Comment/Review
body, raw provider response, hidden reasoning or credentials into usage/audit.

Canonical body/source fingerprints should use versioned server-keyed HMAC rather
than plain hashes of low-entropy confidential text. Canonicalization must specify
JSON key order, Unicode handling, normalized dates, omitted-vs-null semantics and
contract version; it must not silently reinterpret a changed confirmation body.
Key rotation/recovery and encryption-at-rest policy remain Owner decisions. No
new key is generated or reused from another credential in this task.

Public provenance should contain opaque revision/source labels, not internal
content fingerprints. Source mappings are scoped and server-generated; a model
cannot provide valid database IDs, assign membership or authorize a source.

## 5. Original02A retention/expiry proposal — fixture approval superseded above

| Data | Recommendation | Chưa được quyết định |
|---|---|---|
| Unconfirmed preview | Expire for use after a bounded interval; 30 minutes is the earlier proposal only | Exact TTL; allowed preview access; physical retention |
| Feedback analysis | Treat as confidential derived source content; revalidate source state on every retrieval/replay | Whether to persist analyses at all; retention/encryption/access |
| Committed confirmation/result | Keep replay evidence for an explicitly approved recovery window | Duration, minimum metadata after preview expiry, deletion/backup policy |
| Usage/reservation/outcome_unknown | Retain enough to reconcile cost/concurrency without raw content | Accounting retention, operator access, unresolved outcome handling |
| Audit metadata | Preserve under applicable AuditLog retention policy | AI event vocabulary and storage duration; no invented financial/legal period |

Preview expiry is **not physical deletion**. An expired unconfirmed proposal must
not create Tasks; generate/analyze replay returns EXPIRED without redispatch.
For an already committed confirmation, current-authorized same-key/same-body
recovery may return the existing result even after preview expiry while the
approved confirmation ledger is retained. It never recreates the batch.

Do not purge idempotency evidence early then pretend the same old request is
new. Behavior after the approved retention window must be explicit in API docs;
do not promise infinite replay guarantees. No cron/background purge is implemented
or approved here. Backup copies and encryption keys also need a deletion policy;
removing a live DB row does not prove all retained copies have disappeared.

## 6. Original02A access/source proposal — current fixture gate superseded above

Every future generate/analyze/retrieve/replay/confirm operation must resolve the
authenticated actor and current Profile/Workspace context with existing helpers.
The proposed Manager/Reviewer AI gate remains AI-D02 pending; normal read access,
is_staff or possession of a UUID cannot independently authorize an AI request.

- Revoked/inactive membership or cross-tenant ID: return the existing safe scoped
  denial; do not reveal saved payload or created IDs through an idempotency replay.
- Archived Profile/Workspace: apply the approved active AI feature policy before
  dispatch/confirmation. AI-D02 must settle whether any archived preview reads
  are allowed; do not assume normal archived Task readability grants AI authority.
- Source edited/deleted or no longer readable: invalidate saved analysis for use;
  fail with a safe stale-source result, not the old derived content. Soft-deleted
  Comment retained text is never a fallback source.
- Review revision changes: preserve source manifest/version and require a fresh
  selected-source analysis if the prior context is stale. Analysis does not
  alter the current review decision/latest-revision policy.
- Ownership transfer/sharing: default proposal actor binding is recommended;
  cross-user proposal sharing or moderation requires a separate product rule.

Revalidate immediately before publishing a future provider result and on each
GET/same-key replay. Egress already sent cannot be undone by late revocation.
Browser cache must be cleared on auth/scope change; without realtime there is no
claim that already displayed text vanishes instantly from another open browser.

## 7. Idempotency và confirmation protocol

Scope key: authenticated actor + authorized Profile/Workspace + operation, plus
Task where the operation is Task-scoped. Key digests do not grant authorization.
Same raw key in another actor/Workspace/operation must not reveal or reuse the
first request's private result. Bind canonical body and schema/provenance version.

| Request state | Same scope/key/body | Same key, different body |
|---|---|---|
| Generate/analyze in flight | IN_PROGRESS; no second provider dispatch | Conflict; no dispatch |
| Generate/analyze completed, current preview/source valid | Existing artifact; no second provider call | Conflict |
| Provider outcome unknown | No automatic redispatch; controlled reconciliation | Conflict |
| Unconfirmed preview expired | EXPIRED; new explicit generation needed | Conflict |
| Confirmation already committed and ledger retained | Fresh authorization then same created mapping | Conflict; never create again |

Single-confirmed-proposal uniqueness also blocks a second batch under a different
idempotency key. Two different briefs with different keys are not guaranteed to
be semantic duplicates; AI text similarity is not a safe uniqueness constraint.

Future confirmation transaction, after approved schema/code scope:

1. Resolve current actor and scoped capability, validate the complete edited plan
   and its schema/DAG. Do not call a provider during confirmation.
2. Begin one outer transaction; acquire existing tenant locks, then proposal and
   confirmation guard. Recheck permission, provenance, revision/body and expiry.
   Look up committed recovery before refusing a new creation due to preview TTL.
3. Insert/topologically create the new nodes via unchanged create_task. Parent
   refs refer only to nodes created in this plan, not arbitrary existing IDs.
   Existing service assigns actor/PENDING; no auto assignment/status override.
4. Commit Task rows, existing audit records, proposal consumed state and immutable
   result mapping atomically. Failure at any node/audit rolls back the entire
   creation batch and confirmation marker.
5. Lost response: recover via same key/body after fresh authorization. Concurrency
   losers return the committed result or a safe conflict; never create a second
   batch. Do not blindly retry unrelated IntegrityError/transaction failures.

This is a design protocol. P4-02A does not call create_task or implement durable
confirmation; fixture output is not a Task creation authorization ticket.

## 8. Lock families và transaction boundaries

**No provider/network call while holding DB transaction locks.** Future dispatch
reserves usage in a short transaction, releases locks, calls the provider, then
reauthorizes/validates and settles in a separate short transaction.

Proposed common ordering for code paths needing shared rows:

```text
budget advisory/state locks: global -> Profile -> Workspace -> User
then existing business locks: Profile -> Workspace -> actor ProfileMembership
  -> actor WorkspaceMember if required -> existing Task/source rows
then AI rows: proposal -> confirmation/invocation in an explicit fixed order
```

Budget-only reserve/settle must not take business locks implicitly in an opposite
order. Confirmation must never acquire budget locks or charge/generate again.
Budget accounting and confirmation use separate logical records so a response
recovery does not need a billing-row lock first.

If a settlement also validates current source/business state, it must either
follow the full common order or separate safe accounting settlement from content
publication. No path may hold proposal/invocation and then request an existing
Profile/Workspace/Task lock while another path does the reverse. Inserting FKs
can acquire implicit locks on referenced rows; enumerate them in schema review,
including actor/User references and existing audit service effects.

After locking a proposal, confirmation creates new Task rows and may lock parents
newly created in its own transaction. It must not attach to an external existing
Task parent at that stage. Existing shared Task/source locks, if needed, must
already be acquired before proposal lock. Source rows of the same kind use a
deterministic ID ordering; any multi-scope lock policy must also be explicit.

Use unique constraints and a locked guard row, not check-then-create alone.
Transaction boundaries, deferred constraints, FK behavior and concurrent User/
membership/lifecycle operations require PostgreSQL tests after the schema is
approved. No statement here proves a future database deadlock-free.

The previous architecture document's concurrency/deadlock proof requirement is
**not fulfilled by stateless fixture tests in P4-02A**. This task reviews the lock
graph only; actual persistence/concurrency tests remain a future acceptance gate
because Owner expressly forbids creating models/migrations in this slice.

## 9. Future schema rollout requirements

Before any later model/migration code: Owner approve app boundary, fields,
constraints/FKs/deletion semantics, AI-D02/03/04/05/06/09 and private-content policy.
Only additive migrations; do not modify applied Task/Workspace migrations or
backfill legacy Users/Tasks/tenants. New AI stores can start empty without
inventing historical AI usage or proposal mappings.

Before any persistent development apply: separate rollout approval, read-only
identity/inventory, schema/history graph checks, fresh backup/readability and
isolated restore/migration rehearsal, then planned apply and integrity/regression
checks. An older report of zero business rows does not replace fresh inventory.
No migration number or persistent rollout is assigned by this review.

## 10. Original02A future test plan — not the current02B execution result

- Cross-worker duplicate confirm, same/different keys, response loss after commit,
  edited-body conflict, expired preview and retained-ledger recovery.
- All-or-nothing Task+audit rollback, denied actor/scope, revoke/archive between
  preview and confirm; no assignment/status/Review/Notification bypass.
- Concurrent reserve/settle/confirmation/archival/revocation/User lifecycle, FK and
  lock ordering; repeated stress plus deterministic barrier/deadlock tests on
  isolated PostgreSQL, never persistent development.
- Budget exhaustion across simultaneous requests, zero/unknown usage distinction,
  crash between reservation/dispatch/settlement, no automatic paid retry.
- Saved analysis GET/replay after source edit/delete/revoke; tombstone, citations,
  no content in logs/audit/error responses, HMAC rotation and scoped replay.
- Retention/window tests with controlled clocks, no premature replay evidence
  removal, encryption/access/backup policy checks if those controls are approved.

## 11. Historical AI-D01–AI-D10 status after P4-02A authorization

| Decision | What P4-02A authorizes | Still pending Owner review |
|---|---|---|
| AI-D01 provider/data mode | Deterministic offline fixture only, no live provider/cost | Gemini/OpenAI/model/account, free/paid/private mode |
| AI-D02 AI authority | Review/reuse existing tenant integration points; no new public feature permission | Final allowed roles, archived reads and cost authority |
| AI-D03 app/persistence | Stateless technical contracts/interface; this persistence review | Django app/models/tables/counters and migration approval |
| AI-D04 expiry/retention | Describe lifecycle and distinguish expiry from physical retention | 30-minute TTL, actual storage periods, encryption, access/delete/purge |
| AI-D05 numeric controls | Bounded fixture/contract validation in this technical slice; live budget0/no calls | Production quotas/token caps/concurrency/timeouts/budgets/alerts |
| AI-D06 plan/confirmation | Strict contract/DAG validation with source hierarchy invariants | Atomic persisted confirmation and final product limits/schema approval |
| AI-D07 ambiguous dates | Strict typed/date validation; no guessed deadlines or status changes | Product deadline recommendation behavior/reference-time policy |
| AI-D08 Analyzer scope | Validate selected authorized-source references in contracts/fixtures | Live source retrieval/product roles and analysis presentation; no auto mutation |
| AI-D09 operator/shared gate | Document provider/error/usage boundaries, no active budget state | Shared operator controls, ledger/leases, kill-switch governance |
| AI-D10 private-data/live eval | No egress/key/billing; no live evaluation | DPA/region/retention/sharing terms, smoke budget and model eval thresholds |

None of these rows is blanket approval. Current Task→Deliverable→Review workflow,
multi-Profile isolation, last-active-owner and deferred Project/onboarding decisions
remain unchanged. Explicit Owner instruction, rather than the old proposed table,
defines what can be coded in this task.

## 12. Historical P4-02A review outcome and next gate

Persistence review is complete as a **proposal**, not persistence implementation.
The stateless contracts/fixture slice can be completed independently. Durable
confirmation, usage/budget enforcement, schema/retention/operator choices and live
provider activation remain approval-gated, not silently excluded from the roadmap.

Recommended next action: Owner review this document with AI-D01–AI-D10 and the
actual P4-02A test evidence in HANDOVER. Do not automatically start HT-AI-P4-02B.
No `.env`, database, model/migration, credential or business-data operation was
needed for this review. Only this documentation file was created by this review
subtask; no runtime code or existing coordination documentation was edited.
