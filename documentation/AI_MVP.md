# HT-AI-MVP

Development checkpoint for Smart Task Generator and Feedback Analyzer.
The existing implementation had fixture-only React and DRF flows, durable Task
proposals, an offline Responses API adapter and offline dispatch governance.
The live mode reuses those boundaries, including Django sessions, CSRF, current
tenant membership and the existing Task creation service.

## Groq Free provider integration

**Owner decision, 2026-11-27:** use Groq Free with `openai/gpt-oss-120b` for
the thesis, with a USD 0 API budget. Retain the OpenAI Responses adapter and
manual selection of `gpt-5.4-mini`. Automatic fallback is prohibited.
Owner approved the Groq schema and provider integration on 2026-11-27.
The Owner-approved development rollout applied `ai.0004_groq_governance`
after a protected backup and isolated restore rehearsal. Live remains off.

### Adapter and server configuration

`backend/apps/ai/groq_adapter.py` implements the isolated Chat Completions
adapter and the fixed HTTPS transport. Its default is disabled. It reuses both
existing server-owned `LiveInput` validators. Django uses the existing
governance path for both Groq and OpenAI.

Groq's `POST https://api.groq.com/openai/v1/chat/completions` takes Chat
Completions `messages`, strict `response_format.json_schema`,
`max_completion_tokens`, `reasoning_effort: "low"`, and
`include_reasoning: false`. Use a single non-streaming request with system
instructions and a separate JSON user message. The strict schema retains the
providers' shared structural rules. Local business validation remains
responsible for task counts, string lengths, estimate precision, duplicate
checks, and exact quotes from the sanitized feedback source. Groq completion
usage already includes reasoning tokens. Cached input is likewise part of total
input. The adapter keeps bounded `Retry-After` seconds on its typed 429 error.
Provider bodies and credentials stay out of errors. A 429, timeout,
refusal or invalid response ends that attempt. The API forwards valid bounded
`Retry-After` as an HTTP header.
[Chat compatibility](https://console.groq.com/docs/openai) ·
[Structured Outputs](https://console.groq.com/docs/structured-outputs) ·
[GPT-OSS 120B](https://console.groq.com/docs/model/openai/gpt-oss-120b) ·
[API reference](https://console.groq.com/docs/api-reference) ·
[Reasoning](https://console.groq.com/docs/reasoning) ·
[Errors](https://console.groq.com/docs/errors)

The backend chooses one provider before dispatch. Groq is the default.

| Configuration | Key checked by that provider | Accounting |
|---|---|---|
| `DJANGO_AI_PROVIDER=groq`, `DJANGO_AI_MODEL=openai/gpt-oss-120b` | `GROQ_API_KEY` | Separate Groq provenance, token accounting and Free quotas |
| `DJANGO_AI_PROVIDER=openai`, `DJANGO_AI_MODEL=gpt-5.4-mini` | `OPENAI_API_KEY` | Existing OpenAI Responses adapter and USD budget policy |

Keep `DJANGO_AI_LIVE_ENABLED=false` by default. Fail closed for missing keys,
invalid provider/model tuples and unavailable governance. Groq also requires
`DJANGO_AI_GROQ_FREE_TIER_CONFIRMED=true` as an operator assertion. A deployment
using OpenAI must select `DJANGO_AI_PROVIDER=openai`. If `DJANGO_AI_MODEL` is
empty, explicit OpenAI selection still uses `DJANGO_AI_OPENAI_MODEL`.
The selector is server-side and sits behind current RBAC, Trash, CSRF,
idempotency and dispatch ledger checks. The generator still stores a proposal
first and creates a Task only on confirmation. Feedback remains advisory.
The API preserves Task and feedback payloads and adds the `groq_live` mode.
React labels the provider and the reference estimate separately from billing.
Before changing provider settings, close the live lane and drain in-flight
dispatches. Recover existing proposals with the provider recorded on their
dispatch. A request key already used with the other live provider is a
conflict. The claim check is under the existing tenant locks.

### Approved schema — development rollout complete

Development PostgreSQL 16.14 has 47 applied migrations and an empty plan.
Only `ai.0004_groq_governance` was applied in this rollout. The legacy
fingerprint and complete catalog matched the approved rehearsal.
[Rollout evidence](HANDOVER.md#ht-ai-mvp-groq-governance-development-rollout--2026-11-27)

| CHECK | Before 0004 | After 0004 |
|---|---|---|
| `ai_disp_origin_valid` | Fixture or OpenAI execution-mode/provider pairs | Add `GROQ_LIVE` / `groq` |
| `ai_disp_usage_mode_valid` | Provider-reported usage only for `OPENAI_LIVE` | Also allow reporting on `GROQ_LIVE` |
| `ai_budget_mode_valid` | Fixture and the two OpenAI modes | Add `GROQ_LIVE` |

The migration depends on `ai.0003_proposal_rejection`. It extends model
choices and replaces these three CHECK definitions. Catalog and legacy data
tests verified unchanged columns, indexes, and existing records. The existing
`ai_disp_no_simulated_bill` rule requires Groq `billed_cost=NULL`. The
application cannot verify an invoice. The isolated reverse succeeds before
Groq records exist and refuses atomically when old CHECKs would reject them.

### Free quota and data policy

Official references checked on 2026-11-27 list 30 RPM, 1,000 RPD, 8,000 TPM and
200,000 TPD for this model in the Free tier, shared across the organization.
Verify the actual account limits in the Console before dispatch. The model's
published reference prices are USD 0.15/million input, 0.075/million cached
input, and 0.60/million output tokens. These prices are separate from the
chosen Free-tier USD 0 budget. A key alone does not establish the account tier.
At the two-request planning caps, the uncached price reference would be
USD 0.0024576 for both calls. The Free acceptance plan requires Owner to verify
that the organization remains Free. The wire preflight bounds UTF-8 bytes
plus framing and rejects a request that exceeds the cap.
The application defaults to 20 requests and 6,000 tokens per rolling minute,
plus 500 requests and 100,000 tokens per rolling 24 hours. Each send is checked
under the Groq global budget lock. The next send and unknown/in-flight sends
count at their full input plus completion allowance. Verified settled sends
count at provider-reported totals. The provider-specific lifetime request and
concurrency caps also apply (60/30/20 requests and 3/2/1 active sends by
global/Profile/user). Groq has zero USD allocation in its budget buckets.
Dispatch `estimated_cost` and API `cost_usd` remain reference estimates;
`billed_cost` stays unknown. OpenAI keeps its existing USD controls.
[Rate limits](https://console.groq.com/docs/rate-limits) ·
[Model and reference pricing](https://console.groq.com/docs/model/openai/gpt-oss-120b) ·
[Billing FAQ](https://console.groq.com/docs/billing-faqs)

Use only synthetic data for acceptance. Groq documents default non-retention
with limited exceptions for reliability and abuse investigation, potentially
up to 30 days. Check the account's data controls and applicable terms before
using real data. Authorize only source text required for the current request,
retain sanitization, and keep brief/feedback, raw responses and credentials out
of operational logs. OpenAI's `store: false` is a Responses API option.
[Groq data handling](https://console.groq.com/docs/your-data)

### Acceptance and batch evaluation plan

Set `DJANGO_AI_CONTROLLED_LIVE=true` only on the fresh disposable environment
approved for acceptance. This mode caps each envelope at 4,096 input and
1,024 completion tokens and admits only the two exact synthetic inputs from
the [manifest](#controlled-live-smoke-proposal--exactly-two-provider-requests).
The existing Django dispatch transaction claims at most one durable slot per
feature across workspaces, actors, workers and restarts. Failed attempts,
timeouts and unknown outcomes consume their slot. Controlled budget buckets
use a separate policy version, so switching settings against the same rows
fails closed. Controlled mode refuses OpenAI.

The fake integration checks the two-call limit through the actual Django routes,
including a concurrent race between profiles and a timeout followed by a new
key. Verify one draft with an editable estimate, exact quotes from the
synthetic feedback, and preserved business rows during actual acceptance.
Record the HTTP outcome, model and token counts. Leave the draft unconfirmed.

The local fake-only proof passed 8/8 (exit 0). It pinned both wire payloads
by SHA-256, then checked duplicate attempts, concurrent/restarted callers, timeout,
429, refusal and truncation. Including the 1,024-byte framing allowance, the
synthetic payload bounds were 2,960 and 3,561 against the 4,096 input cap. The
proof uses exclusive disposable markers to count sends and predates the Django
test above.

### Owner setup

The development launcher reads the repository-root file
`D:\da\HustlyTasker\.env`. From that directory, verify the file is ignored
with `git check-ignore -- .env`. Enter the key already created by Owner in
the private local file as `GROQ_API_KEY`. Keep the key server-side. The
normal development settings while waiting for approval are:

```dotenv
DJANGO_AI_PROVIDER=groq
DJANGO_AI_MODEL=openai/gpt-oss-120b
DJANGO_AI_LIVE_ENABLED=false
DJANGO_AI_GROQ_FREE_TIER_CONFIRMED=false
DJANGO_AI_CONTROLLED_LIVE=false
DJANGO_AI_GROQ_REQUESTS_PER_MINUTE=20
DJANGO_AI_GROQ_REQUESTS_PER_DAY=500
DJANGO_AI_GROQ_TOKENS_PER_MINUTE=6000
DJANGO_AI_GROQ_TOKENS_PER_DAY=100000
```

Run `.\scripts\start-backend-dev.ps1 -Check`, then
`.\scripts\start-backend-dev.ps1` to launch the local server with the existing
virtualenv. For the separately approved live test, configure a fresh isolated
runner with the new schema and allow only Groq egress. Confirm the organization
is Free, the key has model access, and each quota is at or below the currently
available limit in the Console. Set its live, Free confirmation and controlled
flags to true for the two-request window, then stop the runner and verify live
is off. The development launcher is for the persistent local database; use the
isolated runner for the two requests. No real call or evaluation ran in this task.
[Groq Console](https://console.groq.com/settings/organization/limits)

For later evaluation, import Owner-approved synthetic cases with stable IDs,
track each attempt and results in a private checkpoint, and resume only
unattempted cases. Reserve quotas using the lower of actual Console allowance
and application limits. At the planning caps of 4,096 input plus 1,024
completion tokens, 8,000 TPM allows one worst-case reservation per minute;
200,000 TPD allows at most 39 per day before headroom and other account usage.
Use smaller batches with explicit approval and save progress after each case.
Do not retry ambiguous outcomes. Score schema validity, estimated-hours error
only when a valid `actual_hours` exists, and grounding against the supplied
quotes. Report case counts, skips, quota, and unknown outcomes separately.

## Request and result contracts

All paths start at `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/`.
The existing permission-checked `OPTIONS ai/task-proposals/` advertises
`groq_live` or `openai_live` availability, limits and the safe readiness reason. The browser
does not supply provider settings, quotas, actor or tenant identities in JSON.

| Action | Request and outcome |
|---|---|
| Generate | `POST ai/task-proposals/`, with UUID `Idempotency-Key`, `brief` (1–6,000 characters), optional integer `task_count` (1–20) and optional offset-aware `target_deadline`. Returns a durable proposal and provider usage. |
| Recover | `GET ai/task-proposals/{proposal_id}/` under current actor and scope. |
| Confirm | `POST ai/task-proposals/{proposal_id}/confirm/`, with UUID `Idempotency-Key`, `proposal_revision`, edited `payload` and literal `confirmed: true`. Only selected original refs are accepted. Each selected live Task can include a decimal-string `estimated_hours` such as `"3.25"`, an exact JSON number or `null`. Creates root Tasks and saves the approved hours in the same transaction. |
| Reject | `POST ai/task-proposals/{proposal_id}/reject/` with `proposal_revision`. Clears the payload and records terminal REJECTED. Repeating the same rejection is safe. |
| Analyze | `POST tasks/{task_id}/ai/feedback-analysis/`, with UUID `Idempotency-Key`, selected Review/Comment refs in `sources`, optional `feedback_text` (up to 4,000 characters) and optional `focus` (up to 1,000 characters). Manually entered text can be the sole source. Result is advisory and editable locally. |

Generator wire schema requires a flat `tasks` array of objects with `title`,
`description`, `priority` (LOW, MEDIUM, HIGH, URGENT), and nullable numeric
`estimated_hours`. It also requires bounded `assumptions` and `warnings`.
The server adds stable refs and copies only the explicit target deadline.
The preview allows editing or clearing estimates. The confirmation dialog
shows the selected values, and the receipt reads them back from the scoped
Task detail API. The confirmation payload cannot create Subtasks, Project,
assignments or reviews.
Each proposal is confirmable for 30 minutes. Expiry hides the payload. Rejection
and confirmation clear the payload. Confirmation recovery lasts up to 30 days.
Expiry is a read/mutation rule. Physical retention cleanup needs its own policy.

Feedback uses `ai.feedback.v2` with `summary`, `issues`, `suggested_actions`,
`uncertainty` and `warnings`. Issues contain category, severity, local source
refs and exact quotes. Backend validation compares each quote against the
sanitized source that was actually sent. Suggested actions must refer to
grounded issues. Analyzer replay returns a conflict. Dispatch metadata is
durable while the analysis response stays in the request and browser state.
Application markup renders suggestions as text. Review decisions use the
existing explicit actions and permissions.

## Provider and cost control

In the current pre-Groq runtime, `gpt-5.4-mini` is the configured OpenAI
default. The server also allows the documented
`gpt-5.4-mini-2026-03-17` snapshot at the same standard rates.
The adapter calls the official [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
over verified HTTPS with strict [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
Static feature instructions describe constraints. Text and selected source refs
go in a separate user message. The route supplies no tools, media, traversal or
continuation identifiers, and sends `store: false`. Text redaction masks
recognized contact, URL and credential patterns. Unstructured text can still
contain identifying details that pattern matching cannot recognize. Review what
is shared before using real customer data and obtain the Owner's authorization.
The adapter requests the standard service tier explicitly. `store: false`
disables response storage for later API retrieval. OpenAI's default abuse
monitoring logs may still be retained for up to 30 days, subject to the project's
approved data controls. [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).

On 2026-11-21 the [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
listed $0.75 per million input tokens and $4.50 per million output tokens in
standard mode. The estimate uses uncached rates on all reported input/output
counts. Rounding is upward to 8 USD decimal places. It represents estimated
spend rather than a billed amount. For example, 2,000 input and 800 output
tokens estimate $0.0051 per request, or $0.51 for 100 similar requests.

By default the live feature is disabled. A trusted server configuration sets
the model, timeout (default 30 seconds), input allowance (32,768) and output
ceiling (2,048). A conservative UTF-8 byte bound plus a 1,024 framing allowance
is checked locally, and reported tokens are checked against the reservation
after the response. The [pricing table](https://developers.openai.com/api/docs/pricing)
must be checked again before live acceptance. The local estimate cannot enforce
the provider's invoice amount.

Live budget buckets are cumulative and shared across features. Defaults are
$1 / 60 requests / 3 concurrent globally, $0.50 / 30 / 2 per Profile and
$0.25 / 20 / 1 per User. A reservation counts the full allowed input and output
at standard rates before dispatch. Process-local request throttles still apply
(3/minute and 20/day per user across these endpoints). Database locking prevents
parallel requests from exceeding the same bucket. Changing configured budget
limits after a bucket exists fails closed until a separately reviewed adjustment.
There is no automatic retry or fallback. A timeout or ambiguous provider
failure retains its hold. An authenticated, verified provider response with
parse/refusal failure can still account for reported usage. Live billing
reconciliation of unknown outcomes remains an operational review item.

AI intent and usage live with the existing AiDispatch, AiBudgetBucket and
AiDispatchReservation tables. The API safely reports configuration/migration
unavailability, refusal, malformed output, timeout, rate/budget limits and
stale context. Raw briefs, selected feedback, keys and provider bodies are
excluded from operational rows and errors. AI output is untrusted and validated
again using the existing business rules at confirmation.

## Migration and live verification gates

Development applied `ai.0002_dispatch_governance` followed by
`ai.0003_proposal_rejection` on 2026-11-21 after protected backup, actual
isolated restore and exact-plan rehearsal. The second migration extends two proposal
constraints and status choices without adding a column or backfilling. Reversing
0003 would require a separate data policy if any REJECTED proposals exist.
See [HANDOVER](HANDOVER.md) for the verified developer database and receipts.

Development applied `tasks.0007_task_estimated_hours` on 2026-11-21 after a
fresh protected backup, isolated restore rehearsal and exact-target checks.
The development plan is empty and all five legacy Tasks have NULL hours.
Live provider use still requires separate approval. See [HANDOVER](HANDOVER.md).

### Known Security Risks

An SMTP app-password-shaped value was tracked in `.env.example:36` starting
at `2c421f1`. The working copy now leaves `DJANGO_SMTP_PASSWORD` blank. The
historical value has no verified revocation or verified safe provenance. The
Owner deferred remediation for this development rollout on 2026-11-21 and
accepted it as an outstanding security risk. SMTP sending, testing and
configuration changes are outside this rollout.

### Estimated hours persistence

The approved nullable `Task.estimated_hours` uses `numeric(6,2)`, no default
or backfill, and a NULL-or-range CHECK for 0.01–1000 hours. The Task service
validates exact Decimal values before database coercion. Confirmation saves
the approved value. Missing or explicitly cleared values remain `null`.
The Task read API returns a fixed two-place string or `null` for list and
detail. The manual create and update contracts are unchanged.

New live receipts hash normalized hours with a version marker. `2` and
`"2.00"` give the same digest. Changing hours under the same new-format key
returns conflict. A matching legacy digest can still recover the original Task
IDs after normal request validation. Legacy receipts with inputs outside the
new precision rule can recover through the scoped proposal GET.

Live is disabled by default. The controlled run below uses a separate, private
backend configuration and a disposable database. The normal development
launcher fixes the connection to `hustlytasker_db` on loopback. It cannot
launch the isolated run with `-EnvFile`. The existing `ai-mvp` browser suite
uses fake HTTPS and serves as an offline regression.

Server-only optional settings are `DJANGO_AI_OPENAI_MODEL`,
`DJANGO_AI_OPENAI_TIMEOUT_SECONDS`, `DJANGO_AI_MAX_INPUT_TOKENS`,
`DJANGO_AI_MAX_OUTPUT_TOKENS`, and the
`DJANGO_AI_{GLOBAL,PROFILE,USER}_{BUDGET_USD,REQUEST_LIMIT}` combinations.
If live mode is selected without a key or the approved schema, the API displays
the corresponding readiness error. It does not fall back to synthetic output.

Manual acceptance should verify a bounded bilingual brief, a selected subset
of drafts, one confirmation replay and a Feedback Analyzer result with exact
evidence. Review status and Task statuses must stay under human control.
Run real-model evaluation separately on the Owner's authorized inputs.

### Controlled live smoke proposal — exactly two provider requests

#### Owner setup and approval

1. In OpenAI Platform, select or create a dedicated API project. Review API
   Billing for the organization and confirm it can fund API usage. If using
   prepaid billing, check the purchase amount separately from the test spend.
   On 2026-11-27, the published minimum prepaid purchase was USD 5. Check the
   project's model access and spend limit. Provider spend enforcement may lag.
   [API billing](https://help.openai.com/en/articles/8264644-setting-up-and-managing-prepaid-api-billing)
   · [Project permissions and limits](https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform)
2. In Project Settings → API Keys, create a dedicated key. Use Restricted
   permissions for the Responses endpoint where available. Save
   `OPENAI_API_KEY=<private value>` with a private editor in a Git-ignored
   backend file for the isolated runner, for example
   `.local_backups/HT-AI-MVP-LIVE-PREFLIGHT/.env.controlled-smoke`. Check it is
   ignored with `git check-ignore --quiet -- <path>`. Keep the key out of React,
   Git, chat, command arguments, logs and screenshots. Leave live false while
   preparing the file. Report only that key and billing are ready.
3. Authorize explicitly the two synthetic inputs below and the run budget.
   Confirm the account permits `gpt-5.4-mini`. Public model documentation
   confirms Responses and Structured Outputs support. Account access and key
   validity have not been tested. [Model](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
   · [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

#### Fixed request manifest

| One request | Synthetic input and expected check |
|---|---|
| Smart Task Generator | `Tạo một công việc dựng video giới thiệu sản phẩm dài 60 giây, yêu cầu cắt ghép cảnh quay, thêm phụ đề tiếng Việt và nhạc nền không vi phạm bản quyền.` Send `task_count=1` with no deadline to the scoped proposal POST. Verify exactly one root draft with title, description, priority and decimal or null `estimated_hours`. Verify proposal count increases by one and Task count is unchanged. Confirmation is outside this run. |
| Feedback Analyzer | `Video có phụ đề xuất hiện chậm ở giây 12–18, nhạc nền quá lớn từ giây 25 và logo cuối video bị mờ. Hãy phân tích các vấn đề và đề xuất chỉnh sửa.` Send exactly that `feedback_text` and `sources: []` to the scoped analysis POST on a synthetic Task. Verify summary, issues, severity, actions and exact grounded quotes from the manual source. Task, Deliverable and Review rows stay unchanged. |

#### Isolation, budget and release gate

Use a fresh disposable PostgreSQL cluster with the current schema and only
`django_migrations` metadata restored. Seed one synthetic authorized actor,
Profile, Workspace and Task on the isolated target before permitting egress.
Verify the cluster ID differs from development, the plan is empty, and the
live budget/dispatch tables are initially empty. The one-shot runner should
have no listening web server and should call only the two existing scoped
Django POST handlers with a different pinned UUID `Idempotency-Key` for each.

Apply `DJANGO_AI_MAX_INPUT_TOKENS=4096`, `DJANGO_AI_MAX_OUTPUT_TOKENS=1024`,
`DJANGO_AI_OPENAI_TIMEOUT_SECONDS=30` and `DJANGO_AI_{GLOBAL,PROFILE,USER}_REQUEST_LIMIT=2`
with `DJANGO_AI_{GLOBAL,PROFILE,USER}_BUDGET_USD=0.02` only in that isolated runner.
The shared ledger reserves USD 0.00768 per dispatch, or USD 0.01536 for two at
USD 0.75/M input and USD 4.50/M output, verified 2026-11-27. The USD 0.02 cap
is local. The output ceiling is sent to the API. The input check uses encoded
UTF-8 bytes plus 1,024 framing and compares actual reported usage after
receipt. The estimate is subject to metering, account settings and pricing.
[OpenAI model and standard rates](https://developers.openai.com/api/docs/models/gpt-5.4-mini)

The app's shared buckets enforce the total. They allow two fresh keys for one
feature. A separate deny-by-default transport gate is required for the
per-feature limit. Bind it to this exact ordered manifest, fixed Responses
URL, model and payloads. Atomically consume one durable slot per feature before
attempting transport. Keep the same run identity and spent state across
restart, including failed or timed-out attempts. Exclude any other key holder
or live app process during the run. The preflight proof exercises the guard
with a fake transport. The live binding still needs review and a fake-only
dry run before granting egress. Do not set `DJANGO_AI_LIVE_ENABLED=true` on
development for this smoke. Set it only in the approved one-shot child and
verify live is off after that process exits.

Preflight evidence on 2026-11-27: the schema-only isolate matched all 46
migration records and no business rows were copied. The fake-only guard test
passed 8/8. The encoded Generator body is 2,130 bytes and Analyzer 2,857
bytes. With 1,024 reserved for framing, the local checks are 3,154 and
3,881 respectively. Account-specific model and billing access remain
unverified. See [HANDOVER](HANDOVER.md).

For each attempt, record HTTP and provider status, model, latency, schema and
evidence validation, provider-reported tokens and estimated cost, with unknown
values marked as such. Compare before/after business snapshots. Keep raw
credentials and private data out of logs. Stop on errors, timeouts, refusal or
truncated output without retrying or resetting a slot. A test result here
does not replace evaluation of the Owner datasets.

Trash soft-delete and restore were accepted by the Owner. Permanent deletion
is a known unavailable action while the purge flag is off. The existing
capability and disabled controls already communicate this state. No purge or
schedule changes belong to AI integration.

## Offline evaluation with the Owner's cases

**Real-model evaluation has not been performed.** The two Owner-prepared sets
of 50 cases were not found at the repository paths or attachment locations
available in this session. The harness tests use small synthetic inputs and
do not establish model quality, runtime latency or cost on the Owner's data.

Keep the datasets and saved output files private. Run the same validator used
by the application against both sets from the repository root.

```powershell
& .\backend\venv\Scripts\python.exe scripts/evaluate_ai_mvp.py `
  --mode live --generator-cases generator-cases.json `
  --generator-results generator-results.json --feedback-cases feedback-cases.json `
  --feedback-results feedback-results.json --output ai-evaluation-report.json
```

Use `--mode mock` with synthetic results in the same live schema for an
offline dry run. Each saved results file must declare the same mode. The
harness never calls a provider. Save real results separately after the Owner
approves test data and cost. The label records declared provenance and does
not authenticate the origin of a saved file. The output path must be new.

Both case manifests have a `cases` array of `{id, input}` objects. Use opaque
case IDs, unique within their set. The Generator `input` contains `brief` and
optional `task_count` and `target_deadline`; the case can also supply
`actual_hours_by_ref` keyed by matched draft refs such as `item_1`. The
Feedback Analyzer `input` contains `sources`, an array of `{ref, text}` in
`S1`, `S2`, … order, and optional `focus`. Use the exact selected input
snapshot, including manually entered feedback when used. The harness applies
the same source redaction before checking evidence.

Both saved files have the shape `{mode, model, results}`. Each result has a
case `id` and `raw_output`, which is the unmodified structured model output
encoded as JSON text. Use `null` when there was no output. The provider
envelope and the React display object are not suitable substitutes. The
result may also include measured `latency_ms`, `usage` with `input_tokens`,
`output_tokens` and `estimated_cost_usd`, and `owner_review`. Record unknown
metrics as `null`; the report tracks observation counts for each metric.

The `owner_review` has `relevance` and `accuracy` scores, each on a 0–2 scale,
and a boolean `unsupported_claims` flag. The Owner is the only reviewer.

| Rating | Relevance | Accuracy |
|---|---|---|
| 0 | Misses the work or feedback requested | Material claims contradict the supplied input or are unsupported |
| 1 | Covers only part of the work or feedback | Some claims need correction or clearer uncertainty |
| 2 | Covers the important details with actionable output | Claims are supported and limitations are stated clearly |

The report distinguishes missing outcomes, invalid JSON and invalid schema
or evidence. Exact quote checks detect invented or wrong-source feedback
citations. The Owner flags unsupported claims outside those automatic checks.
Estimated-hours MAE uses only a valid estimate paired with a supplied actual
value for the same task ref. Leave actual hours absent until measured. The JSON
report includes input-file SHA-256 hashes, case IDs and aggregate metrics, with
case prompts and outputs excluded. Identical files yield the same report.
