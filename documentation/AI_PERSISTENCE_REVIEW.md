# HT-AI-P4-02A — AI Persistence, Retention & Locking Review

Ngày: **2026-10-28**. Current: **P4-02B IMPLEMENTATION COMPLETE — PENDING
DEVELOPMENT MIGRATION APPROVAL / OWNER REVIEW** after the Owner's scoped
fixture-only approval. Original02A proposal review remains below as historical
design evidence, not a ban on the newly authorized implementation. Overall
Smart Task Generator remains PARTIAL: frontend AI and live provider are absent.

## Current P4-02B persistence checkpoint

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
