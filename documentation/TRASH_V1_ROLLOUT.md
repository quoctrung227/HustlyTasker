# HT-TRASH-V1 — controlled development migration rollout

Date: 2026-11-20.

**HT-TRASH-V1 — DEVELOPMENT MIGRATION COMPLETE — PENDING OWNER MANUAL ACCEPTANCE.**

The Owner authorized only `workspace.0006_soft_delete` followed by
`tasks.0006_soft_delete` on the existing development database, after backup and
restore rehearsal. This approval did not authorize purge, scheduler registration,
AI migration, production deployment or creating demonstration records.

## Target, plan and execution

Verified target: PostgreSQL 16.14, `hustlytasker_db`, container
`hustlytasker_postgres`, volume `docker_postgres_data`, loopback
`127.0.0.1:5432`. Container/cluster/volume identity remained the same throughout.
Git remains `main` at `31f0af932a9ffaf3e578115d63faa4a776e75175`; existing dirty
Task, Analytics, Invitation and frontend work was preserved.
Final source audit retains all 861 baseline files, with zero runtime changes and
all 35 migration source hashes unchanged, including the two newly applied files.

Before rollout, development had 31 tables and 41 applied migrations. The exact
Workspace target plan contained only `workspace.0006_soft_delete`; the Task target
initially included that dependency plus `tasks.0006_soft_delete`. After Workspace
was applied, the Task plan contained only `tasks.0006_soft_delete`. No backward
operation or AI migration appeared in either execution plan.

The private gate supplied the existing safe environment loader and called
Django's standard `migrate` command with one explicit target per process:

```text
migrate workspace 0006_soft_delete --noinput
migrate tasks 0006_soft_delete --noinput
```

Each process checked the current exact plan, migration source hashes, database
identity, original data/schema preservation and writer state before executing.
Development application additionally required the retained backup's actual hash,
a matching successful restore rehearsal and the writer-stop receipt. Both native
processes returned exit 0; no generic migrate, fake migration or manual schema/
history update was used. No rollback or restore over development was performed.

| Migration | Actual recorded application time, UTC | Vietnam time |
|---|---|---|
| `workspace.0006_soft_delete` | 2026-11-20 10:47:47.315037 | 17:47:47 |
| `tasks.0006_soft_delete` | 2026-11-20 10:48:00.223314 | 17:48:00 |

`ai.0002_dispatch_governance` remains **UNAPPLIED** and its governance tables
remain absent. A generic startup warning about that pending migration is expected;
do not follow it by running an unscoped migrate command.

## Backup and actual restore rehearsal

The new PostgreSQL custom archive is retained outside the repository with
restricted local access:

```text
D:\da\HustlyTaskerBackups\HT-TRASH-V1-ROLLOUT\20261120T104345Z_9cc7157fd3764eed96955ab59a60fad5\hustlytasker_development_20261120T104345Z.dump
```

- Size: **141,777 bytes**.
- SHA-256: `45EA1FDD1F7736502D21279EF93A6D1C0F5226A0A60D62B4748D8D75FE4A5F37`.
- Dump, custom-format signature, archive list, full archive read and actual
  restore returned exit 0. The retained file's hash was checked again afterward.
- Rehearsal target: `ht_trash_9cc7157fd3764eed96955ab59a60fad5`, in a separate
  PostgreSQL cluster with tmpfs storage, internal-only network and no published
  ports. The backup was mounted read-only; no development data volume or Owner
  `.env` was mounted into the tools container.
- Restore preservation, both exact-target migrations and post-schema gates
  passed there before development execution. No AI migration, purge or business
  fixture was run on the restored database.
- The owned rehearsal containers/network were inspected and removed; final
  ownership queries found zero remaining resources. The backup was not deleted.

Restore reparsed 19 existing CHECK representations involving enum-array casts.
Original/restored names, validation and flags remained intact; PostgreSQL
READ ONLY comparisons proved the old and restored arrays equal, with the rest of
each boolean expression exact. This is a deparser representation difference,
not a development constraint change. An initial string-only proof helper failed
to recognize that representation; the corrected semantic proof passed in
`restored-check-equivalence-verified.json`. The actual archive restore succeeded.

## Schema and data preservation

Development remains at **31 tables**, with applied history **41 → 43** and only
the two approved records appended. Original migration rows remain unchanged.
Profile, Workspace and Task each gained nullable `deleted_at`, `deleted_by_id`
and `purge_after`: **nine columns**, with no database default and NULL on every
legacy row. Each aggregate has one validated metadata CHECK, one validated
deferred User FK, one valid/ready partial due index and one FK lookup index.
Thus the expected additions are three CHECKs, three FKs and six indexes.

`deleted_by` uses Django's ORM `SET_NULL` policy. Its actual PostgreSQL FK is
`DEFERRABLE INITIALLY DEFERRED`, with database `NO ACTION`; it is not SQL
`ON DELETE SET NULL`. All old same-cluster schema definitions remain exact.

| Inventory | Before | After |
|---|---:|---:|
| Users / Sessions | 5 / 3 | 5 / 3 |
| Profiles / ProfileMemberships | 2 / 3 | 2 / 3 |
| Workspaces / WorkspaceMembers | 3 / 3 | 3 / 3 |
| Tasks, including any Subtasks / TaskAssignments | 5 / 5 | 5 / 5 |
| Deliverables / Reviews / Comments | 3 / 0 / 1 | 3 / 0 / 1 |
| Invitations / Notifications / AuditLogs | 3 / 12 / 48 | 3 / 12 / 48 |
| AI Proposals / Operations | 0 / 0 | 0 / 0 |
| Content types / Permissions | 27 / 108 | 27 / 108 |

All original tables' row counts and per-row hashes were preserved, including
account tokens, Invitation delivery/quota metadata and framework tables. Hash
projection excludes only the three newly added fields on each aggregate; all
original business fields remain included. Migration rows are the sole expected
data append. No new session, soft deletion, restoration, audit event or business
record was created by rollout verification. Final post-startup preservation also
passed; see `final-state.json` in the private evidence directory.
The aggregate original-row fingerprint before/after is
`130EE97AF4E63A2D6CD9AE6A4F73A48C84FBFBE5E68205E3BF4B30C699D06CA5`,
with original migration rows retained and only the two expected records appended.

## Checks, local startup and limits

| Check executed in this rollout | Result |
|---|---|
| Safe local configuration validation | PASS, exit 0; required names present, secret values hidden, purge flag false |
| Backup/restore/rehearsal and each development migration | PASS; actual child/native exit 0 |
| Schema, exact history, data preservation, Django check and model consistency | PASS, exit 0 |
| Fresh isolated Trash/security tests | 59/59 PASS, 11.389 seconds; Python/launcher 0, no AI0002, owned cleanup |
| Existing-identity READ ONLY handler projections | 46 GET checks PASS, exit 0; no login/session creation |
| Real HTTP GET direct and Vite proxy checks | 27 PASS, exit 0; health/CSRF success and protected anonymous denial as expected |
| Scheduler/process checks | No purge process or registered purge task; exported XML remains disabled |

The implementation checkpoint's full backend 1,168/1,168, frontend 1,295/1,295
and 44 browser cases are **historical for this rollout**, not rerun here. Handler
projections use an existing legitimate identity in a read-only transaction;
they are not a real authenticated HTTP/browser login. HTTP smoke creates no
business data and does not replace manual Owner acceptance. Positive directory
GETs that consume quota were excluded. No real email or live AI call was made.

The official development backend and Vite were started on loopback 8000/5173
using existing launchers, with no migration/fixture startup action. Recorded
launcher PIDs are backend 29320 and Vite 35128; these are checkpoint metadata,
not permanent process identifiers. At handover, use `http://127.0.0.1:5173` and
refresh instead of starting duplicate servers. If the servers have since stopped,
use the documented two-terminal commands in [FRONTEND_GUIDE](FRONTEND_GUIDE.md).

The initial direct PowerShell dot-source was blocked by process execution policy
and did not validate the configuration. The explicit launcher-style PowerShell
process then validated it successfully; no global execution policy or `.env`
value was changed.

## Owner manual acceptance and next gate

The Owner can now verify ordinary soft-delete/restore through React:

1. Open `http://127.0.0.1:5173`, refresh and log in with an authorized account.
2. Choose a non-critical Task, or deliberately create a development Task if
   desired. Record its status, assignment and existing collaboration history.
3. Use ordinary **Xóa**, confirm, and verify it disappears from normal work lists
   without becoming CANCELLED. Open **Thùng rác**, search/filter the entry and
   check the deleter, deadline and impact counts.
4. Restore it within 30 days and verify its original status/history and legitimate
   access remain; revoked rights and independent child deletion must not revive.
5. Optionally repeat with a Workspace or Profile the Owner is willing to place
   temporarily in Trash. Confirm descendants become unavailable, global Trash
   remains reachable, and parent restore leaves separately deleted children alone.
6. Check the existing Viewer/member restrictions. A disabled permanent-delete
   action with a purge/retention reason is expected at this checkpoint.

These manual actions change real development data; the Owner decides what to
create or delete and how to handle it afterward. **Do not test permanent deletion
as part of first acceptance.** Purge remains disabled, no schedule is registered
or enabled, and no purge command was run on development. Any later purge or
scheduler activation needs separate explicit approval and the existing
[conditional retention/FK policy](TRASH_V1_DESIGN.md). No production deployment,
AI migration or next task is authorized by this rollout.

Raw sanitized receipts remain Git-ignored under
`.local_backups/HT-TRASH-V1-ROLLOUT/`: `backup.json`, `rehearsal-result.json`,
`rehearsal-cleanup.json`, `restored-check-equivalence-verified.json`,
`development-*-apply-process.json`, `development-post-gate-process.json`,
`readonly-smoke-*.json`, `http-smoke-result.json`, `startup.json` and
`final-state.json`, `final-data-fingerprint.json` and
`final-source-preservation.json`. [HANDOVER](HANDOVER.md) records the final audit.
