# HT-AI-MVP

Development checkpoint for Smart Task Generator and Feedback Analyzer.
The existing implementation had fixture-only React and DRF flows, durable Task
proposals, an offline Responses API adapter and offline dispatch governance.
The live mode reuses those boundaries, including Django sessions, CSRF, current
tenant membership and the existing Task creation service.

## Request and result contracts

All paths start at `/api/v1/profiles/{profile_id}/workspaces/{workspace_id}/`.
The existing permission-checked `OPTIONS ai/task-proposals/` advertises
`openai_live` availability, limits and the safe readiness reason. The browser
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

`gpt-5.4-mini` is the default. The server also allows the documented
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

After separate live provider approval, set `OPENAI_API_KEY` in the ignored repository-root
`.env` or in a private file passed via `-EnvFile`. Run
`.\scripts\start-backend-dev.ps1` from the repository root. The launcher
strips inherited OpenAI environment variables. Supply `DJANGO_AI_LIVE_ENABLED=true`
only after the Owner approves the provider data policy and cost. The toggle
defaults off. Set OpenAI project limits/alerts and plan a small smoke with
synthetic inputs before using real feedback. Never place the key in browser
files, command arguments, Git or screenshots.

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

After explicit approval of the synthetic data and spend, use one authorized
tester in one active test Workspace. Have the Owner create a dedicated OpenAI
project key and put it in the Git-ignored local `.env` using a private editor.
Keep it out of React, Git, command arguments, chat and screenshots. The launcher
reads that file and ignores inherited OpenAI settings. Before enabling live,
check the model is permitted, its standard-tier rates still match the configured
rates, the development plan is clean and the live budgets are unused or match
the approved policy. Current development `.env` was checked by presence only:
the key is absent, live defaults off and the default model is `gpt-5.4-mini`.

| One request | Synthetic input and expected check |
|---|---|
| Smart Task Generator | Brief `Kiểm tra 6 đoạn phụ đề trong video giả lập dài 90 giây, ghi lại đoạn sai chính tả.` Set `task_count=1` and leave deadline blank. Verify one root draft. If confirming this synthetic Task is approved, edit the estimate and verify the saved value after reload. Null is valid if the model has insufficient information. |
| Feedback Analyzer | In a synthetic Task, enter only `Phụ đề tiêu đề xuất hiện 1 giây. Yêu cầu hiển thị 3 giây.` Confirm the quoted text matches that source, then edit or discard the guidance locally. Review and Task state stay unchanged. |

Proposed backend settings after approval only: 4,096 input and 1,024 output
tokens, 30-second timeout, `REQUEST_LIMIT=2` and `BUDGET_USD=0.02` for each
of the global, profile and user settings. The shared ledger reserves up to
USD 0.00768 per dispatch and USD 0.01536 total for this configuration at
USD 0.75/M input and USD 4.50/M output. These are local estimates, with a
proposed USD 0.02 application cap. Check the provider project's own spend
controls separately. [OpenAI model and standard rates](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
Offline encoding confirmed both documented inputs fit the proposed local
4,096 limit, including the 1,024-byte framing allowance. Actual usage and
response quality remain unmeasured.

Send each input once. An ambiguous timeout can still consume the reservation.
Record latency, response status, actual reported token counts and estimated
cost from dispatch metadata. Leave raw inputs, responses and keys out of
operational logs. A third dispatch is outside this smoke approval. Switch
live off after the two attempts. Smoke results do not replace evaluation of
the Owner datasets.

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
