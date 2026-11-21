# HT-TRASH-V1 — deletion, retention and purge design

## Current development activation — 2026-11-20

**HT-TRASH-V1 — DEVELOPMENT MIGRATION COMPLETE — PENDING OWNER MANUAL ACCEPTANCE.**

The Owner subsequently authorized and applied only workspace0006 then tasks0006
after backup, actual isolated restore/rehearsal and exact-target gates. Development
has 43 migrations and 31 tables, with all original rows/hash projections preserved
and nine new legacy-NULL metadata columns. AI0002 remains unapplied. This changes
the earlier migration-approval boundary only; all retention, tenant and business
policies below remain. Actual purge flag is false and no scheduler is registered
or enabled. No development purge command or business fixture was run.

[TRASH_V1_ROLLOUT](TRASH_V1_ROLLOUT.md) records backup/checksum, actual schema,
fresh 59-test verification, startup/read-only smoke and the manual acceptance
checklist. Full 1,168/1,295/44 suite results below are the historical implementation
checkpoint, not tests rerun by this database rollout. Manual acceptance and any
later purge/scheduler activation remain separate Owner gates.

## Historical implementation-only boundary — resumed 2026-11-20

The earlier implementation task authorized source, additive migration files and
isolated tests. It did not authorize development migrations, real-data purge, scheduler enable,
development AI migration, `.env` edits, backup changes, commit/push or deployment.
The latest resume permits AI0002 only in a disposable PostgreSQL regression
database if required by the suite; the prior blanket test prohibition is historical.
This exception grants no live provider call or persistent AI schema change.

The Owner selected conservative V1 retention: preserve AuditLog; do not introduce
a financial ledger; block all remaining Review history, completed/financial data,
Invitation retention and unresolved-reference purge. A blocked row stays deleted
and retained, with an explicit reason. Thirty
days makes an object eligible for evaluation, not permission to override retention.

## Storage and effective deletion

Profile, Workspace and Task receive nullable `deleted_at`, `deleted_by` (global
User FK SET_NULL) and `purge_after`. Each valid deletion sets an exact720-hour
boundary; repeated deletion never extends it. A CHECK requires either all metadata
NULL or non-NULL deletion/deadline timestamps separated by exactly30days; deleted_by
may later be NULL through SET_NULL. A partial deadline index supports due scans.
No existing applied migration is edited. Existing `status`/archive policy remains.

Only the explicitly deleted aggregate is stamped/listed in Trash. Descendant
availability is computed from Profile → Workspace → Task ancestor deletion,
including the existing bounded Task hierarchy. Children deleted independently
retain their own timestamps. Restore clears only the target's deletion metadata;
it never rewrites child flags, business status, assignments or membership activity.
Restore requires current management authority, a live parent and `now < purge_after`.
After the deadline, an expired/retention-held object is not silently revived.
Purge of a parent also checks independently deleted descendants: a child's own
unexpired 30-day deadline prevents the parent from removing it prematurely.

Normal model managers remain unchanged. Ordinary API access and mutation services
must explicitly repeat effective-deletion predicates in their live tenant scope.
Related-model managers do not filter JOINs, so membership/Notification/Invitation
queries need their own checks. Trash has its own current-membership authorization
and may resolve an explicitly deleted Profile without granting normal tenant access.

## Authorization and API contract

| Action | V1 authority |
|---|---|
| Profile delete/restore | Current active Profile OWNER |
| Workspace delete/restore | Current active Profile OWNER/ADMIN |
| Task delete/restore | Current active Profile OWNER/ADMIN or effective Workspace ADMIN |
| Any manual permanent purge | Current active Profile OWNER only, after720hours |
| Automatic purge | Explicit execution command, global enable flag, same retention/dependency checks |

`GET /api/v1/trash/` supports `object_type=TASK|WORKSPACE|PROFILE`, bounded search,
optional authorized `profile_id`, positive page and fixed20-row pagination.
Only explicit deletion entries are returned. Item contract:

```text
id, object_type, title, profile_id, workspace_id|null, parent_id|null,
deleted_by:{display_name}, deleted_at, purge_after, days_remaining,
parent_deleted, affected_counts, can_restore, can_purge,
restore_blocker:string|null, purge_blockers:[{code,message}]
```

Mutation routes:
`POST /api/v1/trash/{task|workspace|profile}/{uuid}/{delete|restore|purge}/`.
Delete/restore require strict empty JSON. Purge requires `confirm:true`; Workspace
and Profile additionally require an exact `confirmation_name`. Unknown fields,
bad Unicode, wrong account/tenant and stale authority fail closed. SessionAuth,
CSRF, current backend permissions and non-enumerating404 remain mandatory.

`can_delete` is an additive current-response hint, never a mutation grant.
Before every mutation recheck current role/lifecycle/deletion state under locks.

## Mandatory model impact matrix before purge code

| Model / current FK | Soft delete and restore | Permanent V1 disposition |
|---|---|---|
| Profile | Hide whole descendant scope; retain archive status | Delete only after all scoped dependencies resolved; never global User |
| Workspace → Profile PROTECT; owner User PROTECT | Hide descendant Tasks, retain members/period | Explicit bounded cleanup; unresolved AI/financial references block |
| Task → Workspace CASCADE; parent Task PROTECT; creator User PROTECT | Retain state and all child rows | Delete complete planned subtree in one bounded bulk statement; unplanned referencing children/cross-scope dependencies block; surviving parents are not deleted; database FK checks enforce closure |
| TaskAssignment → Task CASCADE; User PROTECT | Keep active/revoked history unchanged | Remove only for purged Task IDs; do not delete User |
| Deliverable → Task CASCADE; uploader User PROTECT | Preserve revisions/content/author | Delete only if no Review or other protected history remains in scope |
| Review → Deliverable CASCADE; reviewer User PROTECT | Preserve feedback and compensation snapshot | Any Review state blocks V1 purge, including pending/revision feedback; COMPLETED Task history is also protected; no ledger introduced |
| TaskComment → Task/User PROTECT | Preserve independent comment tombstones | Explicit scoped deletion before Task; audit events retained |
| Notification → Profile/Workspace/Task/Invitation/AuditLog PROTECT | Suppress unavailable target through current read policy | Remove only matching target scope; retain referenced AuditLog and global User |
| ProfileMembership → Profile/User PROTECT | Never deactivate/reactivate on delete/restore | Remove only after issuer Invitation references are safely resolvable |
| WorkspaceMember → Workspace/User CASCADE | Never reactivate revoked rows | Explicit scoped deletion; does not delete forward-referenced User |
| ProfileInvitation → Profile/issuer membership/User/replaces PROTECT | Preserve identity/status/expiry/delivery; disable unavailable target actions | Pending/unresolved rows block; terminal rows retained at least 12 calendar months; a complete closed replacement chain may be deleted together after retention, while referencing rows outside the plan block |
| InvitationEmailAttempt → Invitation PROTECT | Preserve delivery history | Cleanup only with safely purgeable Invitation; pending delivery blocks |
| InvitationDirectoryAccess → global User PROTECT | Unchanged | Not Profile-owned; never removed by tenant purge |
| AuditLog → User SET_NULL; resource IDs scalar/JSON | Preserve all events | Retain existing rows and append metadata-only purge proof; no business content copy |
| AiProposal/AiOperation → Profile/Workspace/User PROTECT; created_tasks JSON IDs | Existing access must fail for unavailable scope | Unresolved retained state/recovery references block; no AI retention redesign |
| AiDispatch/Budget/Reservation PROTECT, ai0002 not applied development | No AI behavior changed | Inspect actual tables; no forced missing-table query/migration; present references block |
| Client/ShareLink/Invoice/Payment, no Profile/Workspace/Task FK | Unchanged | No tenant inference and no deletion; finance/audit retention remains protected |
| Global User, Sessions, account security tokens | Unchanged | Never a tenant purge target |

## Financial and Invitation retention

Current approved analytics are live joins through latest Review → Deliverable →
Task. Cascading approved/snapshot history would erase historical totals. V1 blocks
that purge and also retains all other Review history per the resume instruction.
Operational analytics exclude effectively deleted Tasks; historical
financial approval totals retain eligible old snapshots under current live RBAC.
Trash UI does not expose private compensation or reviewer feedback.

The pre-existing terminal Invitation policy retains metadata for at least12months;
V1 does not repeal it. Such references can keep a Profile in retention hold beyond
its30-day trash deadline. No fabricated identity/backfill, expiry extension,
membership revival or delivery state change is used to make purge possible.

## Transaction, FK and scheduler safeguards

Use existing Profile-first scope serialization, then Workspace/Task locks in stable
order. Avoid joined User locks. Delete/restore/purge races must re-evaluate state
after locks; only one terminal outcome may commit. Audit and resource mutations
share a transaction. A dependency/FK failure rolls the whole transaction back.

Purge preflight computes the exact scoped deletion set and rejects unknown FK
references before deleting. Explicit ordered deletion avoids generic Collector
queries against unapplied AI tables. Database FKs remain the final fail-closed
barrier; there is no disabled constraint, forced CASCADE or manual FK-null bypass.

`TRASH_PURGE_ENABLED` defaultsFalse. Both API and command enforce it. Management
command defaults to dry-run; `--execute` requires the flag and the720-hour boundary.
No scheduler is enabled by this task. A documented Windows scheduled command can
be approved later; a powered-off development machine cannot execute its schedule.
No user request/on_commit callback is described as a durable scheduler.
Due candidates are streamed in bounded chunks; the command limit counts eligible
evaluations, not an oldest blocked prefix, so retained records cannot starve later
eligible records. Task and Invitation self-references are deleted as a closed
bulk set, with immediate FK verification inside the purge transaction.
Command output is sanitized JSON with dry_run/scanned/eligible/purged/blocked,
already_absent/errors and allowlisted blocker_counts. A concurrent already-gone
target is a safe no-op. Unexpected errors produce a nonzero command result and
do not label the failed transaction as purged. Retention-held rows remain for
later evaluation; permanent holds require a separately approved retention policy.

## Historical isolated implementation verification

Required isolated PostgreSQL coverage: deletion/restoration across Task states,
parent independent flags and expiry, current RBAC/revocation, actual concurrent
operations, approval/Invitation/AI holds, unknown FK, rollback/audit atomicity,
no global User deletion, idempotent due purge and dry-run/disabled execution.
Frontend/browser verify effective absence, Trash pagination/filters, accessible
confirmations and status/error handling. `ai.0002` may be applied only in a
disposable regression database if needed under the latest resume authorization;
it remains forbidden on development. Scoped non-AI test mode remains available.

**HT-TRASH-V1 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION AND PURGE APPROVAL.**

Fresh final verification is isolated and does not imply development rollout:

| Gate | Executed result |
|---|---|
| Focused Trash/PostgreSQL migration tests | 59/59 PASS, 11.085 seconds; Python/launcher 0; 43 migrations without AI0002 |
| Corrected read/write role contracts | 141/141 PASS, 19.911 seconds; Python/launcher 0 |
| Full PostgreSQL backend | 1,168/1,168 PASS, 448.046 seconds; 0 failures/errors/skips; Python/launcher 0; 44 disposable migrations including AI0002 |
| Frontend | 1,295/1,295 across 38 files; focused Trash 59/59; final typecheck/lint/build 0 |
| Browser | Eight suites, 44 unique PASS; final repeated Trash 7/7 in 51.1 seconds, Playwright/launcher/backend 0; four viewports, keyboard/focus and axe 0 |
| Harness / launcher safety | 19 and 16 tests respectively PASS |
| Ownership / preservation | Owned test resources cleaned; 834 baseline source files retained, 33 prior migrations unchanged |
| Development read-only metadata | 41 applied records; both new0006 migrations and AI0002 absent; no Trash columns or task-issued writes |

The first full run's 17 failures and the initial obsolete Workspace browser
fixture failure are retained in [PROGRESS](PROGRESS.md), with the actual context
fix and passing reruns. No historical baseline is presented as a current run.
Migration/purge rollout, scheduler activation and retention exceptions remain
separately gated. No development business-row recount or manual UI acceptance
is claimed; no new feature is started.
