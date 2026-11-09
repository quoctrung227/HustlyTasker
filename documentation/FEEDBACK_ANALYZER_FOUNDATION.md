# HT-AI-P4-03A — Feedback Analyzer Foundation

## HT-AI-P4-04C — Metadata-only governance around offline analysis (2026-11-08)

Status: **HT-AI-P4-04C — OFFLINE GOVERNANCE IMPLEMENTATION READY /
DEVELOPMENT MIGRATION PENDING**. The approved candidate
adds durable dispatch/budget metadata, not an analysis-history product. Existing
stateless Analyzer HTTP/React behavior, fixture envelope, source/citation rules
and manual Review workflow remain unchanged. The candidate migration is not
applied to persistent development and no live provider/data egress is enabled.

The new internal [execute_feedback](../backend/apps/ai/governance.py) wrapper
accepts current actor/nested scope plus Task and selected source kind/IDs. It
reuses existing _SelectedFeedbackAccess to resolve current authorized Review.comment
and nondeleted TaskComment.content before constructing the provider request.
Scope/current source text are revalidated before and after the offline adapter.
A typed DTO or previously selected UUID is not treated as permission evidence.
Opaque refs/text and bounded focus are projected by the preserved OpenAI adapter;
real Review/Comment text is never sent to an external provider in this task.

Internal metadata binds selected database IDs, current text/focus, scope and
trusted configuration through a keyed request fingerprint without retaining
those raw inputs. Same scoped key/body can reserve once across workers; changed
input/configuration conflicts. Budget buckets cover GLOBAL/Profile/User with
stable lifetime limits, and claimed/unknown outcomes retain cost/in-flight holds.
Current offline provenance is SIMULATED, generated_by_ai=False and billed cost
NULL; fake observed tokens, estimated accounting and actual invoicing are distinct.

Only the first successful internal execution returns transient advisory JSON.
Duplicate calls return an authorized metadata receipt without replaying saved
analysis or invoking transport again. No Task/Subtask, Deliverable, Review,
Comment, Notification, AuditLog, AiProposal or AiOperation is created/modified
by the wrapper. No Apply action, result retrieval/history, automatic retry or
background processing is added.

Source/permission change after a claimed request discards the result while
preserving possible usage uncertainty. If recording UNKNOWN is itself blocked
by lost access or database unavailability, the durable DISPATCHING row retains
the hold; no false refund or successful rollback is reported. Reconciliation is
metadata-only, simulated, original-actor/current-manager checked and evidence-
idempotent. It cannot prove real provider cancellation or billing.

Every governance path gates before candidate-table access. Fixture-disabled or
unmigrated persistent development continues using its existing safe paths. The
new schema is detailed in [DATABASE_SCHEMA](DATABASE_SCHEMA.md), and current
verification/rollout approval belongs in [HANDOVER](HANDOVER.md). Final focused
52/52 PASS15.286 seconds and full isolated PostgreSQL826/826 PASS231.558 seconds
have launcher/actual Python exits0, model/migration checks and owned cleanup
verified. The full suite includes existing Analyzer/fixture/confirmation tests;
all provider execution remains offline. Final development29-table row/schema/
sequence/history/cluster comparison is exact at10:21:26Z, still36 migrations/
4 Users and ai.0002 UNAPPLIED. Earlier270/55/browser results remain historical,
not new live proof. Owner manual acceptance remains PENDING. Unapplied schema
compatibility is limited to the existing gated app paths: arbitrary parent
hard-delete/AdminCollector may traverse new PROTECT relations and is outside
this task, not a supported development maintenance workaround.

## HT-AI-P4-04B — Offline OpenAI adapter boundary (2026-11-08)

Current status: **OFFLINE OPENAI ADAPTER COMPLETE — OWNER REVIEW GATE**.
The Owner approves OpenAI `gpt-5.4-mini` and Responses strict Structured Outputs
as the target of a fake/in-memory transport adapter under the existing provider
port. This does not activate the Analyzer's HTTP service or change its current
fixture response/React contract. No real key, model request, billing, customer
data transfer, result persistence, schema change or domain mutation is approved.

The typed feedback contract can support the adapter without a new Analyzer
entity. Only the selected sources already authorized/resolved by Django may
become provider input. The adapter's projection must contain opaque short
citations and text plus bounded focus, rather than serialize FeedbackSource's
internal Profile/Workspace/Task UUIDs. Do not include source DB UUIDs, identity,
email metadata, membership, cookies, credentials, AuditLog or Deliverable URLs.
Input text itself can contain sensitive information; tests use invented text
only and are not proof of automatic PII removal.

The implemented internal [OpenAIResponsesAdapter](../backend/apps/ai/openai_adapter.py)
supports Feature.FEEDBACK_ANALYSIS with fake transport and the same strict
FeedbackAnalysis parser. It returns `provider:openai_offline`, simulated usage
and unknown cost; this is neither a live response nor the public fixture DTO.
The local zero-UUID parser correlation sentinel is not a User identity or access
grant and is never transmitted/stored. Django must resolve actual authorization
before constructing ProviderRequest; typed source correlation cannot replace it.

Offline response parsing must reuse `parse_feedback_analysis` with the exact
authorized source set: unknown citations, unsupported fields, malformed JSON,
refusal/incomplete output and bad types/lengths fail closed. A valid DTO is not
proof of semantic model correctness or new permission. Current source resolution,
manager authorization and optimistic post-work source rechecks remain in the
existing service; the internal adapter does not replace them or infer authority
from a UUID-bearing DTO.

Keep analysis advisory/stateless. There is no Apply action, Task/Subtask creation,
Review decision, Comment/Notification write or hidden AiProposal/AiOperation
entry. Fake-transport provenance must remain explicitly simulated and must not be
returned as real AI through the strict fixture envelope. Timeout/cancellation
cannot establish stopped remote computation or zero cost in a future live mode.
See [persistence/accounting proposal](AI_PERSISTENCE_REVIEW.md) for separately
gated metadata-only dispatch controls; no analysis history is required.

The adapter and its deterministic test module are implemented. Current focused
55/55 PASS0.038 seconds and full apps.ai270/270 PASS13.347 seconds use isolated
PostgreSQL, with launcher/actual Python0, dependency/Django/model/migration-chain
checks and owned cleanup verified. Existing Generator/Analyzer fixture regression
is included; no live/provider-quality assertion follows from these results.
All245 original source hashes are unchanged, and final29-table development
preservation is exact with4 Users/2 Sessions/36 migrations and0 AI rows.
Implementation and current test receipts are recorded in [HANDOVER](HANDOVER.md).
Historical P4-04A/P4-03C results below are not new adapter evidence. Manual Owner
acceptance remains PENDING, and live activation remains blocked by truthful
provenance, shared accounting and private-data approval even when offline code
is verified.

## HT-AI-P4-04A — Live Analyzer readiness (2026-11-08)

Status: **DESIGN READY / PROVIDER IMPLEMENTATION BLOCKED — OWNER REVIEW GATE**.
The fixture backend and React integration remain the implemented behavior.
No live provider/model or external processing of user feedback is approved.
Current design and remaining approvals are in the
[provider readiness proposal](AI_ARCHITECTURE_DESIGN.md#ht-ai-p4-04a--live-provider-readiness-2026-11-08).

Source inspection confirms that [feedback_services.py](../backend/apps/ai/feedback_services.py)
resolves only selected Review.comment and nondeleted TaskComment.content through
the current actor's Profile/Workspace/Task access and manager capability. It
rechecks visibility/source content before publishing the result. The existing
strict parser validates citations against server-assigned S1…Sn; a model-provided
source identifier must never expand the authorized selection.

For a future approved provider, build an explicit outbound projection containing
only authorized `{ref,text}` pairs plus bounded optional focus. Do **not** serialize
the internal [FeedbackSource DTO](../backend/apps/ai/contracts.py) generically:
it also carries Profile/Workspace/Task UUIDs for local validation. Keep those
UUIDs, source database IDs, actor/membership details, cookies, credentials, audit
content and Deliverable URLs out of provider requests. Text/focus can themselves
contain PII or confidential client information; a prompt warning or regex is not
evidence of anonymization. Owner must approve data classes and provider terms
before any external transmission. No such transmission occurs in P4-04A.

Retain the stateless advisory design: no analysis-history/proposal record,
Review decision, Task creation, Comment mutation, Notification or Apply action.
Browser cancellation protects local display, not proof that future remote work
or billing stopped. Current pre/post reads are optimistic and cannot revoke
content already sent or received. Live output must be discarded if final access
or source checks fail, while any actual provider cost remains accountable.

Current exact fixture provenance/zero-usage DTO and React parser cannot truthfully
represent live analysis. A separately reviewed backward-compatible response
contract and default-disabled provider selector are needed first. No endpoint,
flag, schema, source permission or fixture behavior is changed by this review.
Process-local limits remain demo attempt throttles, not live global spending
controls. See [HANDOVER](HANDOVER.md) for current-task checks; P4-03C results below
remain historical. Owner manual Analyzer acceptance is still PENDING.

## Verified integration — HT-AI-P4-03C — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE

The Owner now authorizes React integration with the already implemented stateless
fixture endpoint. This supersedes the earlier recommendation to wait for another
frontend task; it does not approve live providers, persistence, media processing,
applying suggestions or production. P4-03B persistence is not required for this
stateless fixture MVP and is not represented as delivered.

Source discovery confirms that current authorized Deliverable reads expose one
nullable `review` object with its ID/comment/status/timestamps, and Task Comment
reads expose ID/content/deletion state. No source-visibility expansion or new
read bridge is needed. The React slice selects usable Review comments and
nondeleted Task Comments for one Task, using current manager capabilities and
the existing permission-checked fixture availability metadata.

The implemented lightweight Task Detail section reuses the existing route,
transport, session/CSRF and design system. It sends only typed source references
and optional bounded focus to the existing
POST; source text stays in the ordinary authorized read UI. Analysis state is
local to current User/Profile/Workspace/Task, not a durable proposal or shared
history. Results must remain explicitly synthetic and advisory, with citations
mapped only to the selected manifest. No Apply/Confirm or domain-mutation action.

Source selection retains unique choices across bounded pages and refreshes only
selected source pages before/after analysis. Refreshes use the existing tracked
query keys and cancellation protocol; they never write an older direct GET over
a shared Comment cache that has already been redacted by deletion. A cancelled
read returning reverted cache data is not accepted as fresh source validation.
Observed changes affecting selected sources or current authority discard the
invalidated local result/selection and pending work safely. This is not realtime
revocation of content already received or detection of unobserved server changes.

Final-source verification: full frontend675/675 PASS27.31s (20 files), including
106 new transport cases and32 component cases. The focused transport/client
run153/153 and component32/32 also pass. TypeScript, Biome and production build
exit0 (build7.58s). Real isolated PostgreSQL/Chromium suites36/36 PASS: Analyzer5,
disabled Analyzer1, Generator4, disabled Generator1, onboarding3, auth/CSRF/tenant6,
Workspace/Task7, collaboration7, complete workflow1 and account1. Each suite has
verified launcher/Playwright/backend exit0 and owned database/resource cleanup.
Analyzer checks include real UI source selection/POST/result/citations, denied
access/CSRF, stale-source failure, in-flight Task switching, session expiry,
keyboard focus, four viewports, reduced motion and zero axe violations. Counts
and fingerprints of all installed models are identical before/after Analyze;
the deleted-source test's separate API-driven fixture change is explicitly
distinguished from the advisory UI operation under test.

Current isolated `apps.ai`215/215 PASS16.494s; launcher/actual Python exits0,
Django/dependency/migration-chain checks and owned cleanup are verified. All160
backend source hashes are unchanged. Full719 was not rerun and remains historical
P4-03A. An initial Analyzer browser4/5 run exposed a helper expecting Dashboard
instead of valid login return-to navigation; the helper was corrected and final
5/5 passed. A separate shared-cache deletion race found during review was fixed
with tracked query cancellation and a32nd component regression test; a cancelled
query's reverted value cannot validate a source or restore a redacted Comment.
Final read-only comparison at2026-11-02T09:24:35.6407031Z matches all29 tables'
row fingerprints, schema/FKs/indexes, sequences, migration history and PostgreSQL
cluster identity exactly, excluding only ephemeral connection counts. Development
still has36 migrations,3 Users/2 Sessions,1 Profile/membership/Workspace/Task,
3 Audit rows and0 Review/Comment/AI rows. Original container/volume/loopback
identity is unchanged. All33 tested source hashes are stable; all160 backend
files are unchanged. Final owned test-container/network inspection finds0.
The375px and1440px screenshots were visually inspected: source/result content
remains distinct/readable, focused result visible and no horizontal overflow.
Earlier537/30 results below remain historical. FE05/P4-02C and Analyzer manual
Owner acceptance remains pending. [HANDOVER](HANDOVER.md) owns the complete
evidence/file inventory. Stop at P4-03C Owner review; do not auto-start another
task or enable a persistent fixture/live provider.

## Historical verified backend foundation — HT-AI-P4-03A

Date: 2026-11-02. **HT-AI-P4-03A — DESIGN AND FIXTURE BACKEND COMPLETE /
OWNER REVIEW GATE.**
This document distinguishes current source evidence from the proposed or newly
implemented Analyzer slice. Final test evidence belongs in [HANDOVER](HANDOVER.md).
No live-provider, frontend, schema rollout or production deployment is approved.

## Source-backed domain map

| Entity | Existing source and contract | Analyzer consequence |
|---|---|---|
| User | [accounts models](../backend/apps/accounts/models.py): global UUID User, session-authenticated identity, is_active | Resolve the actual current User; no supplied actor/role or staff shortcut |
| Profile | [workspace models](../backend/apps/workspace/models.py): tenant root; ACTIVE/ARCHIVED lifecycle | Profile ID is a scope request, never authority |
| ProfileMembership | [workspace models](../backend/apps/workspace/models.py): OWNER/ADMIN/MEMBER, active membership; one User may belong to multiple Profiles | Use the current membership for this Profile only |
| Workspace | [access resolvers](../backend/apps/workspace/access.py): Profile child, independent membership, current verified access context | Revalidate active tenant and Workspace access before using sources |
| Task | [Task model](../backend/apps/tasks/models.py) and [scope selector](../backend/apps/tasks/access.py): Task belongs to one Workspace | Resolve nested Task through authorized Workspace, not global ID lookup |
| Subtask | Same Task model, nullable parent, maximum three child edges | No separate Analyzer entity or automatic parent/child aggregation |
| Deliverable | [reviews models](../backend/apps/reviews/models.py): Task FK, uploaded_by, file_url and nullable legacy revision; no feedback body | Use only as relationship/revision context; never fetch file_url or imply media analysis |
| Review | Same reviews module: Deliverable FK, reviewer, PENDING/APPROVED/REQUEST_CHANGE and nullable comment | Review.comment is existing internal feedback, scoped through Deliverable→Task→Workspace→Profile |
| TaskComment | [TaskComment model](../backend/apps/tasks/models.py) and [comment services](../backend/apps/tasks/comment_services.py): Task FK, author User, content≤4000 for current writes, edited_at/deleted_at | Select current nondeleted readable sources only; retained soft-deleted text is not an input |
| AiProposal | [AI models](../backend/apps/ai/models.py): ai.task-plan.v1, AVAILABLE/CONFIRMED, edited task plan, created_tasks recovery | Generator-specific durable store; do not reinterpret as an analysis record |
| AiOperation | Same AI module: operation constrained to GENERATE/CONFIRM, scoped key/body digests and proposal FK | No new ANALYZE operation can be inserted without schema work; do not reuse Generator replay records |

The actual current feedback stores are Review.comment and TaskComment.content.
Task descriptions and Deliverable URLs are not silently treated as feedback.
No Client Portal, transcript, video frame/audio processing or new Project entity
is required or inferred by this foundation.
There is a [legacy Client model](../backend/apps/clients/models.py); its presence
does not implement a Client Portal or make it an authorized feedback source.
The Analyzer does not read that table or introduce Client/Project relationships.

## Existing workflow and access boundaries

[Task workflow services](../backend/apps/tasks/services.py) already implement
WORKING→REVIEW on current-assignee submission. Internal approval changes the
Task to COMPLETED; request changes requires a nonblank reason and returns the
Task to WORKING. Only the latest submitted Deliverable can receive a decision;
self-review and duplicate decisions are rejected. Review and Task changes,
safe AuditLog metadata and Notification rows share the mutation transaction.

Comments are discussion, not approval. Current author edits and author/manager
soft-delete are separate domain actions; deletion retains text in the database
but the ordinary API exposes a tombstone. Analyzer access must not recover that
retained text or make a previous analysis a new source of leaked deleted text.

Existing [permission classes](../backend/apps/tasks/permissions.py) resolve
current tenant/Workspace/Task scope. Owner/Admin at Profile level manage the
Profile's Workspaces; a Profile Member needs the appropriate independent
Workspace role. Normal read access and permission to submit/review are distinct.
An Analyzer request is advisory and cannot grant either mutation capability.

## Reusable AI foundation and architecture choice

[Contracts](../backend/apps/ai/contracts.py) already define FeedbackInput,
FeedbackSource, FeedbackAnalysis, issue categories and priorities. The
[provider port](../backend/apps/ai/providers.py) already supports
Feature.FEEDBACK_ANALYSIS using one offline deterministic FixtureAdapter.
[Validation](../backend/apps/ai/validation.py) checks source whitelist/scope,
input/output sizes, exact output fields, citation membership and enum values.

[FixtureApplicationService](../backend/apps/ai/services.py) already authorizes
before dispatch and before returning, then re-fetches selected sources and
compares their current values. Stale/deleted/unreadable sources must not return
an apparently current successful analysis. Its previous DenyAccess default is
not an authorization grant; a concrete integration must use existing resolvers.

The safe first slice is stateless fixture analysis. There is no durable analysis
history, saved draft, expiry store or confirmation. Requests do not create
AiProposal/AiOperation, Task, Review, Comment, AuditLog or Notification rows.
Repeated requests can recompute the same deterministic response; this is not a
durable idempotency protocol or an exactly-once live-provider charge guarantee.
Future persistence/costly dispatch would need a separately reviewed lifecycle,
source-state recovery/access, retention, idempotency and migration design.

## Implemented scoped HTTP contract

The delegated technical choice is a conservative current manager/reviewer gate:
`can_manage_workspace_tasks` (the same predicate currently used by
`can_review_workspace_deliverables`). Active Profile Owner/Admin, or an active
Profile Member with effective Workspace ADMIN, may request analysis. Editor,
Viewer, inactive/revoked membership, archived Profile/Workspace and staff without
real membership do not gain this authority. Self-review/latest-revision rules
remain on actual Review decisions; advisory analysis grants no such decision.
An accessible older Review can be selected for advisory analysis; the Task need
not currently be in REVIEW. That does not permit approving an old revision or
changing Task state, and no existing decision restriction is relaxed.

Canonical route: `POST /api/v1/profiles/{profile_id}/workspaces/{workspace_id}/tasks/{task_id}/ai/feedback-analysis/`.
URL name: `ai:feedback-analyze`. Session authentication and CSRF remain required.

```json
{
  "sources": [
    {"kind": "review", "id": "00000000-0000-4000-8000-000000000001"},
    {"kind": "comment", "id": "00000000-0000-4000-8000-000000000002"}
  ],
  "focus": "Synthetic example: readability and revision priorities."
}
```

Only these fields are accepted. `sources` has1–20 unique `(kind,id)` pairs with
kind exactly `review` or `comment` and a UUID string. Optional focus is text≤1000
Unicode characters, NUL-free. No raw source-feedback field, actor, role, provider,
model, tenant override, Deliverable URL or desired business state is accepted.
References must resolve through this exact Task's current readable source set.
Missing/wrong-parent/deleted/null-or-blank feedback is not an analysis source.

The server loads only the selected Review.comment/TaskComment.content and maps
their request order to S1…Sn for the existing citation contract. Aggregate selected
source text is at most12000 Unicode characters. Existing byte limits remain
32KiB/request and64KiB/provider response. These are bounded fixture-validation
limits, not new production token budgets or proof that arbitrary text is synthetic.

Success is an `ai.v1` envelope with `status:READY`, `mode:fixture_demo`,
`generated_by_ai:false`, `persisted:false`, `fixture_version:fixture.v1`, selected
`sources:[{ref,kind,id}]`, the typed `payload:ai.feedback.v1` and zero fixture usage.
There is no proposal ID, expiry, confirm link, created Task mapping, source body,
author identity, email, file URL or hidden provider prompt.

The payload uses the existing exact contract:

| Field | Existing validation |
|---|---|
| contract_version | `ai.feedback.v1` |
| summary | Nonblank string≤1600 |
| issues | At most10 objects: category, description≤500,1–5 selected source_refs |
| suggested_actions | At most10 objects: action≤500, priority, rationale≤300,1–5 selected source_refs |
| uncertainty | String≤600; no invented confidence percentage |
| warnings | At most10 strings≤300 each |

Issue categories are CLARITY/TECHNICAL/CONTENT/PROCESS/OTHER. Suggested priority
is LOW/MEDIUM/HIGH/URGENT. All text must be valid Unicode/NUL-free; unknown fields,
invented citations, malformed JSON, oversized arrays and invalid enums are rejected.
The one fixed subtitle-contrast fixture never inspects or semantically transforms
source text. The response must say so even when focus or selected feedback differs.
The fixture cites only the first selected source. Its citations are correlation
labels for a validated selection, not evidence of semantic reading or analysis
of all selected sources; no video/audio content is fetched or processed.

Illustrative single-source response shape (synthetic IDs, not a live-provider run):

```json
{
  "contract_version": "ai.v1",
  "status": "READY",
  "mode": "fixture_demo",
  "generated_by_ai": false,
  "persisted": false,
  "fixture_version": "fixture.v1",
  "sources": [{"ref":"S1","kind":"review","id":"00000000-0000-4000-8000-000000000001"}],
  "payload": {
    "contract_version": "ai.feedback.v1",
    "summary": "Ví dụ synthetic: kiểm tra độ tương phản phụ đề.",
    "issues": [{"category":"TECHNICAL","description":"Ví dụ về khả năng đọc.","source_refs":["S1"]}],
    "suggested_actions": [{"action":"Kiểm tra tương phản phụ đề.","priority":"MEDIUM","rationale":"Gợi ý synthetic cố định.","source_refs":["S1"]}],
    "uncertainty": "Không phân tích nội dung nguồn bằng model; chỉ fixture synthetic.",
    "warnings": ["Demo fixture — không gọi AI."]
  },
  "usage": {"input_tokens":0,"billable_output_tokens":0,"cost_usd":"0.000000","status":"fixture_zero"}
}
```

The existing AI_FIXTURE_ENABLED/development/nonproduction guard is reused without
changing persistent flags. Existing shared per-user3/minute and20/day approximate
process-cache throttles are reused; OPTIONS does not consume generation/analysis
quota. The current process-local cache is not a multi-worker production quota
guarantee and no shared budget ledger
is added. Stateless analysis does not require or implement durable Idempotency-Key
semantics. This supersedes the old generic future unsafe-AI idempotency proposal
only for this free/no-write fixture operation; Generator replay remains unchanged.

Expected failures follow existing transport conventions:400 invalid input,
403 authentication/CSRF/role denial as applicable to SessionAuthentication,
404 unavailable scoped source/object,409 source/context drift,429 throttling,
503 disabled/unavailable fixture,502 invalid fixture output,504 fixture timeout.
No automatic retries, fallback provider or domain mutation occurs on failure.
Source and authority checks are optimistic pre/post checks, not a serializable
transaction or locking guarantee across concurrent membership/source updates.
They cannot retract an already delivered response or prevent a change after the
last successful read. No real-time revocation guarantee is claimed.

## Threat and verification map

| Threat | Boundary/control | Required verification |
|---|---|---|
| Cross-Profile/Workspace/Task source injection | Current nested scope and selected-object lookup, not client role/ID trust | Foreign and wrong-parent IDs denied without source disclosure |
| Revoked/archived context | Current manager predicate before and after analysis | Inactive/revoked membership and archive denial; drift fails closed |
| Deleted/edited source during request | Current nondeleted source selection plus post-dispatch re-query | No stale successful response after source removal/change |
| Raw text, PII or URL leak | Selected citation metadata only, static public errors, no source/body logging | Output/log/exception tests omit source text, User identities and URLs |
| Prompt instructions or malformed output | Fixed offline adapter; exact structured-output/citation validation | Injection text causes no action; unknown citations/invalid output rejected |
| Unwanted approval/task/notification | No domain mutation or persistence path | Compare every relevant business/AI/Audit/Notification row before/after |
| Provider/network/cost activation | Explicit fixture adapter and disabled live mode | Network sentinels, production/feature-disabled tests |
| Resource abuse | Existing byte/text/count bounds and shared attempt limits | Boundary/overflow/duplicate/source-limit/throttle tests |
| Claiming exactly-once or persisted analysis | Stateless response, no AiOperation/AiProposal write | Repeated requests remain deterministic, reauthorized and nonmutating |

The implemented security behavior is covered by the current isolated runs below;
future live/persisted behavior is not inferred from these fixture tests.

## Privacy and failure policy

Only selected readable text is eligible; do not load an entire Workspace,
unselected history, account identity, AuditLog, credentials or internal prompts.
Fixture output is fixed synthetic text, not interpretation of arbitrary input.
No file download, network provider, SDK/key, billing or automatic fallback.
Text-size validation does not prove that user input is synthetic or nonsensitive.

Raw source/input/output content must not be copied to application logs or audit
metadata. Public failures use fixed safe messages and field names, not raw input,
unknown attacker-controlled field names or provider exception text. Session/CSRF
and backend current authorization remain mandatory; HTTP responses must not be
publicly cached or persisted as an Analyzer artifact.

## Review gates and remaining scope

[ORIGINAL_REQUIREMENTS](ORIGINAL_REQUIREMENTS.md) F06/F07 establish Deliverable
review and internal review tracking. The two AI features are new Owner-requested
Phase4 capabilities, recorded separately in [REQUIREMENT_STATUS](REQUIREMENT_STATUS.md)
and [AI architecture](AI_ARCHITECTURE_DESIGN.md), not a claim that legacy F01–F16
already implemented AI. No separate SRS/HLD Markdown file was found under the
repository documentation/reference paths during this audit. That is not
evidence of academic approval or permission to expand Client/media/Project scope.

HT-FE-P3-05 and HT-AI-P4-02C implementation/test completion do not imply manual
Owner website acceptance. Those manual checks remain pending. They do not block
safe isolated backend work without a concrete discovered dependency risk.

Frontend Analyzer, live provider, media analysis, applying suggestions, durable
analysis history and production are outside HT-AI-P4-03A. Any later Create Task,
Approve or Request Changes action needs its own authorization, human decision
and existing domain service; there is no Analyzer confirm/apply endpoint here.

The Owner explicitly requires a permanent pre-deployment review before any
production deployment, externally accessible hosting/release or production
migration. Ask exactly: "Website HustlyTasker đã hoàn thiện đúng ý bạn chưa? Bạn
có muốn chỉnh sửa giao diện, chức năng hoặc quy trình nào trước khi deploy không?"
Deployment requires the Owner's explicit readiness confirmation and deployment
authorization even when every automated test passes. Current authority remains
local development and isolated testing only.

## Current verification and safe continuation

| Actual P4-03A check | Result / evidence |
|---|---|
| Targeted `apps.ai` through `.\scripts\test-backend.ps1 -TestLabel apps.ai` |215/215 PASS15.272s, including43 new Analyzer tests and172 existing Generator/internal tests; run9477db811e2c45d0873341d7762ac124|
| Full `.\scripts\test-backend.ps1` |719/719 PASS217.696s; rund9a4b96be82a4c4c81de1a6332d4fdfd|
| Dependencies/Django/model drift/migration graph/full chain |PASS via the existing Python3.12/PostgreSQL isolated harness|
| Process and cleanup |Actual launcher/Python exits0 independently verified by Docker events; owned DB removal confirmed; final0 owned containers/networks. Disposable PostgreSQL137 is intentional owned cleanup|
| Development preservation |Final read-only06:34:34.1216245Z: all29 table row fingerprints/schema/FKs/indexes/sequences/history/cluster exactly unchanged;36 migrations,3 Users/2 Sessions,1 Profile/membership/Workspace/Task,0 Reviews/Comments/AI rows|
| Source preservation |235 existing backend/frontend/scripts baselines:232 unchanged; only errors enum, URL route and internal-service docstring are intended edits. Six final changed/new backend source hashes stable|
| Frontend/browser/live/manual |NOT RUN for P4-03A: no frontend changes or live provider. Historical P4-02C537 frontend/30 browser tests are not new results; FE05/P4-02C manual Owner acceptance remains pending|

Ignored receipts and safe metadata are under `.local_backups/HT-AI-P4-03A/`,
including `preservation-proof.json`, test stdout/stderr/process receipts and
actual Python exit events. A local Windows-venv py_compile attempt returned103
because its installed Python interpreter is unavailable; the venv was not
recreated. Actual isolated Django/test verification used the existing Docker
Python3.12 runner successfully. No local-venv startup PASS is claimed.

Runtime files: new [feedback API](../backend/apps/ai/feedback_api.py),
[stateless service](../backend/apps/ai/feedback_services.py) and
[43 security tests](../backend/apps/ai/test_feedback_api.py); additive
[route](../backend/apps/ai/urls.py), [safe NOT_FOUND code](../backend/apps/ai/errors.py)
and a documentation-only [internal-service description](../backend/apps/ai/services.py).
No model, migration, frontend, SDK/provider, `.env` or persistent flag/data write.

No implementation blocker remains for this slice. The recommended next task is
Owner-reviewed Analyzer React integration using this advisory contract, not
automatic P4-03B/P4-03C. Live/private processing, shared budgets, durable history,
applying suggestions and deployment remain separately gated. Stop for Owner
review without enabling fixtures on persistent development or starting new work.
