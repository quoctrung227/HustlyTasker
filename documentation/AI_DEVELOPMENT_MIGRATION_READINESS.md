# HT-AI-P4-02B-R1 — Development Migration Readiness

Finalized on resume: **2026-10-29**. Status: **MIGRATION READINESS VERIFIED —
OWNER REVIEW / DEVELOPMENT APPLY NOT AUTHORIZED**.

The inventory, backup, restore, isolated migration and tests below were completed
in the preceding R1 checkpoint on2026-10-28. The2026-10-29 resume recovered their
retained evidence and finalized this plan; it does not claim those tests were
rerun, create another backup or authorize persistent-development migration.
Fresh resume inventory found one changed User-row fingerprint and one changed
Session-row fingerprint since the R1 final snapshot, while counts and schema
stayed the same. The cause/actor is unverified. The R1 preservation proof remains
valid for its before/after interval; it is not proof that all data stayed unchanged
through2026-10-29. See the separate resume comparison in section3.

This task prepares a possible later rollout of `ai.0001_initial`. The Owner
authorizes source/migration review, read-only development inventory, a protected
local backup, isolated restore/migration rehearsal and appropriate verification.
**Applying the migration to persistent development is NOT authorized.** Passing
rehearsal does not change that gate. Production, live AI, frontend AI and Analyzer
runtime remain outside scope.

## 1. Starting checkpoint and evidence boundaries

Branch `main`, HEAD `502a4440c7512535d280f0b1e4b7fdf0b7a1bc40`. Existing dirty
AI source, integration changes and documentation are preserved. This readiness
task does not authorize rewriting the implemented models or migration.

The prior HT-AI-P4-02B report records AI158/158, Task/RBAC378/378 and full643/643
passing isolated tests. Those results belong to that earlier implementation
checkpoint; they are not new R1 rehearsal results. The R1 read-only inspection
captured the development identity and counts below on2026-10-28; the resume
comparison is separately labeled. Runtime source has not
changed for R1; no new full643 run is claimed or required solely for this
documentation/operational rehearsal.

Related design: [schema review](AI02B_SCHEMA_REVIEW.md),
[database schema](DATABASE_SCHEMA.md), [AI architecture](AI_ARCHITECTURE_DESIGN.md),
[persistence review](AI_PERSISTENCE_REVIEW.md) and [handover](HANDOVER.md).

## 2. Current verification matrix

| Item | Current status | Required evidence |
|---|---|---|
| Source/migration audit | STATIC REVIEW COMPLETE | Two additive CreateModel operations, existing dependencies, seven PROTECT FKs, lifecycle/uniqueness/indexes; no data operation or destructive business-schema change |
| Development identity | VERIFIED READ-ONLY | PostgreSQL16.14, exact original container/database/volume/loopback target; UTF8/en_US.utf8; other connections0 at inspection |
| Development schema/history | VERIFIED READ-ONLY | 35 applied migrations,27 tables,122 indexes,121 constraints/44 FKs; checked objects valid/ready; no AI migration/tables |
| Development data inventory | VERIFIED READ-ONLY | Users3/Sessions2/AdminLogs7/ContentTypes23/permissions92; inventoried business rows0; no private values printed |
| Storage and backup destination | VERIFIED | R1 preflight free space: C16,855,896,064 bytes; D43,336,921,088 bytes; PostgreSQL data filesystem997,566,936 KiB available. New protected/Git-ignored timestamp/UUID path did not overwrite any backup |
| New backup | VERIFIED | Custom archive110161 bytes; dump/copy exit0; host/container size and SHA-256 agree |
| Backup readability | VERIFIED WITH ACCESS LIMITATION | TOC251 lines, full archive read exit0 and workspace host checksum passed; restricted escalated-worker file reads denied; normal Owner manual read not claimed |
| Isolated restore | VERIFIED | Restore exit0 on the exact owned target; source logical schema, sequences, history and all row SHA-256 fingerprints matched |
| Pre-migration legacy comparison | VERIFIED | All27 original tables compared; only physical dropped-column slots and PostgreSQL CHECK rendering were normalized as explained below |
| Isolated AI migration | VERIFIED | Exact plan contained only ai.0001_initial; standard Django apply and consistency checks passed on the restored database |
| Post-migration preservation | VERIFIED | Old schema and rows preserved; only1 migration record,2 ContentTypes and8 permissions added alongside the two AI tables |
| Synthetic smoke/security | VERIFIED |72/72 direct restored-DB tests PASS7.337s,0 failures/errors/skips; fresh separate AI158/158 PASS12.242s includes concurrency/migration coverage |
| Owned-resource cleanup | VERIFIED | Exact owned restore DB dropped after system/owner/comment/inactivity gates; shared container/network cleanup exit0. New and old host backups retained |
| R1 before/after development preservation | VERIFIED READ-ONLY — 2026-10-28 interval | All27 table row fingerprints, schema and sequences unchanged during R1;35 migrations/0AI migrations,3 Users/2 Sessions; no AI tables |
| Resume development comparison | VERIFIED READ-ONLY — 2026-10-29 | Schema/sequences/history and counts unchanged; one User-row and one Session-row fingerprint changed since the R1 final snapshot, cause/actor unverified; no resume mutation |

These are completed R1 results, distinct from the earlier implementation suite
and from checks performed in the final resume. Runtime source, models,
migrations, settings and private `.env` were unchanged by R1. The migration was
applied only to the owned restored database, never to development.

## 3. Fresh read-only development inventory

The table below records the R1 inventory on2026-10-28. The same counts and schema
were observed during the resume, but exact User/Session row equality across the
two dates is not claimed.

| Item | Verified R1 value |
|---|---|
| PostgreSQL |16.14|
| Database |`hustlytasker_db`|
| Original container |`hustlytasker_postgres`, ID prefix `49ef93152944`|
| Persistent volume |`docker_postgres_data`, unchanged|
| Published database endpoint |`127.0.0.1:5432`|
| Encoding / locale |`UTF8` / `en_US.utf8`|
| Applied migrations / AI applied migrations |35 /0|
| Existing public tables / indexes |27 /122|
| Constraints / foreign keys |121 /44|
| Index/constraint condition |Checked objects valid/ready; no reported invalid object|
| Users / Sessions |3 /2|
| Admin logs / ContentTypes / permissions |7 /23 /92|
| Inventoried business rows |0|
| Other database connections at inspection |0|

Development still has no AI tables. Counts and schema metadata were supplemented
by the completed private exact-row comparison on the restored target. No User
identity, password hash, Session key/value or confidential business text is
printed in this report. Connection counts are a point-in-time observation, not
a promise that the later rollout has no traffic. Storage figures in the matrix
were measured at the R1 preflight; recheck them before any later rollout.

### Resume comparison — 2026-10-29

The resumed read-only snapshot is retained as metadata/row fingerprints at
`.local_backups/HT-AI-P4-02B-R1/rehearsal-c7060a0b55c94f41b44d5c440325d89c/development-resume-20261029.json`.
Comparison with the retained R1 final snapshot found:

| Category | R1 final → resume |
|---|---|
| Schema, indexes, constraints, sequences and migration history |Identical;35 migrations/0AI migrations,27 tables/122 indexes; no AI tables|
| User count / row fingerprints |3→3; one prior fingerprint replaced by one new fingerprint|
| Session count / row fingerprints |2→2; one prior fingerprint replaced by one new fingerprint|
| Business row counts |Still0|
| Container/volume / test resources |Original49ef93152944 and persistent volume remain; no isolated container/network remains|
| Retained archive |Still110161 bytes; original SHA-256 unchanged and Git-ignored; no new dump or rehearsal in this resume|

No actual User/Session values were returned, inspected or logged to explain these changes.
The resume performed only read-only inventory, not User/Session mutations.
Independent activity is possible, but neither a login nor any other cause/actor
has been established. Do not label the newer rows as corruption or restore them
to the older snapshot. The earlier archive remains valid for its tested checkpoint,
not a current-state backup. A fresh inventory, quiet window and new verified backup
of the then-current state are required before any future development apply.

## 4. Migration audit and compatibility

Audited file: [ai.0001_initial](../backend/apps/ai/migrations/0001_initial.py),
matching [AI02B_SCHEMA_REVIEW.md](AI02B_SCHEMA_REVIEW.md).

- Dependencies are the swappable User migration and
  `workspace.0004_profileinvitation`; both are already represented by the
  development history. Graph/history/model-state checks passed in the isolated
  rehearsal and the fresh AI runner; no dependency cycle or model drift was found.
- Exactly two `CreateModel` operations create `AiProposal` and `AiOperation`.
  There is no `RunPython`, `RunSQL`, legacy backfill, business-column alteration,
  rename/drop, automatic Task creation or sample fixture insertion.
- Seven FKs bind actor/Profile/Workspace and operation/proposal. Django PROTECT
  is the ORM deletion policy; it is not a PostgreSQL FK action named PROTECT.
  Cross-record tenant equality and current RBAC remain service validation.
- Proposal CHECKs enforce valid status, positive revision, lifecycle pairing
  and timestamp ordering. A confirmed consumed marker is independent of
  payload/result scrubbing. JSON/DAG/depth constraints remain application rules.
- Operation CHECK restricts GENERATE/CONFIRM. Unique scope is
  actor/Profile/Workspace/operation/key digest; a partial unique constraint
  permits only one CONFIRM operation per proposal. Fingerprints are not access
  tokens and do not replace current authorization.
- Existing reviewed indexes support actor/tenant history and expiry lookups.
  No business Task FK is introduced solely to store the JSON result mapping;
  AI migration reversal cannot cascade into existing Tasks.
- Standard Django `migrate` also sends `post_migrate`. Expected additions are
  one AI migration record, two ContentTypes and eight permissions. Comparison
  must preserve every original row and allow only these intended metadata
  additions, rather than demand unchanged metadata-table counts.

Verified totals after the isolated migration were36 migration records,
25 ContentTypes and100 permissions, with the original3 Users/2 Sessions and7
Admin logs preserved. The restored database had29 tables and136 indexes.
The two new AI tables had15/9 columns,7 FKs,18 constraints and14 indexes,
with checked constraints valid and indexes valid/ready. SQL FKs were deferrable,
initially deferred NO ACTION; ORM PROTECT remains a separate deletion policy.
Audit/Task/Review/
Comment/Notification workflow and existing applied migrations remain unchanged.
FK creation can acquire locks on referenced User/Profile/Workspace tables;
inspect traffic and agree a maintenance/lock-wait procedure before real rollout.

## 5. Backup evidence and access limitation

Retained archive, timestamp in UTC:

`.local_backups/HT-AI-P4-02B-R1/20261028T125103Z_c7060a0b55c94f41b44d5c440325d89c/development.dump`

| Evidence | Actual outcome |
|---|---|
| Format / size |PostgreSQL custom archive /110161 bytes|
| SHA-256 |`306e3c49d11b03da3a5e46f7ea6cf5acde2035cd418a44bfb3c09c1bb1144585`|
| Dump / copy |Exit0; host/container archive size/hash match|
| TOC readability |`pg_restore --list` exit0,251 lines|
| Full archive read |Exit0; archive SQL/data not printed|
| Git / path protection |Git-ignored, unique timestamp/UUID path; no earlier backup overwritten|
| Local ACL |No Everyone/Authenticated Users/Builtin Users grant; protected archive retained|

Workspace-context host checksum succeeded after ACL protection. A restricted
escalated worker can inspect metadata but still cannot read FILE_READ_DATA;
directory/ACL readability is not proof of file readability under that token.
This limitation does not invalidate the previously checked archive bytes, and
permissions were not broadened to public groups merely to bypass it. **Normal
manual Owner file-read verification is not claimed.** The Owner should verify
access through the normal private workstation workflow before relying on this
copy for a later real rollout; never send the archive or secrets into chat.

Rehearsal transfer used a binary stream from the exact matching development-
container temporary archive to the isolated container, avoiding the denied host
read and Windows PowerShell text-pipeline conversion. The destination checksum
was verified against the retained backup checksum. No archive contents, raw
credentials, password hashes, Session values or confidential rows were logged.

## 6. Isolated restore rehearsal — current execution checkpoint

| Item | Verified identifier or current state |
|---|---|
| Run ID |`c7060a0b55c94f41b44d5c440325d89c`|
| Compose project |`ht-test-c7060a0b55c94f41b44d5c440325d89c`|
| Restore database |`ht_ai_r1_c7060a0b55c94f41b44d5c440325d89c`|
| Expected ownership comment |`hustlytasker-ai-r1:c7060a0b55c94f41b44d5c440325d89c`|
| Isolated cluster system identifier |`7701703092750774312`|
| Topology |Existing Compose test mechanism, internal network, PostgreSQL tmpfs; no published DB port or persistent development mount|
| Actual restore command policy |`--single-transaction --no-owner --no-acl --exit-on-error`; exit0|
| Restore schema/data/history comparison |PASS:27 original tables, sequences/history/all row SHA-256 fingerprints preserved|
| Exact isolated AI migration / consistency |PASS: only ai.0001_initial; new AI schema and expected metadata verified|
| Restored-database synthetic smoke/security |72/72 PASS7.337s,0 failures/errors/skips; actual Python PID1 exit0|
| Owned cleanup / final development comparison |PASS: owned DB/container/network removed; development exact before/after comparison unchanged|

The actual restore and completed comparisons establish recoverability for the
tested archive and source checkpoint, beyond a TOC listing alone.
Restoration deliberately normalizes object ownership to the isolated test role;
it must not recreate deployment roles or production credentials. No `--create`,
`--clean`, persistent restore or development migration is performed.

The restored-database verification ran72 selected existing Django
TestCases (36 API and36 nonconcurrent durable-service cases), without Django
database creation or flush. They must use new synthetic actors/business data,
not the restored legacy identities. All original rows compared unchanged after
the tests' transaction rollbacks, and both AI tables returned to0 rows. No
legacy Session was decoded/authenticated and no restored content was supplied
to a fixture/provider. Fixture output remained deterministic, with no live call.

A separate fresh shared AI runner, run
`edc9c2a3ee964c9c9843abb7aa141ad8`, completed158/158 PASS12.242s, including
concurrency and migration tests. Launcher and Python PID1/container exits were0;
pip check, Django checks, model-drift/graph/full-chain checks and owned cleanup
passed. This was a separate fresh cluster, not the restored archive. Prior
full643 is historical and was not rerun in R1 or this final resume.

Retained redacted result: `.local_backups/HT-AI-P4-02B-R1/c706-final-report.json`.
It records PASS, exit0, exact target binding, schema/metadata checks,72 test
counts and post-test preservation. The rehearsal helper verified162 scoped
backend/script hashes; root separately verified210 protected runtime hashes
unchanged across R1. These are different snapshot scopes, not contradictory counts.

### Catalog comparison and interrupted attempts

The first helper attempt stopped with a Windows file-read permission error
before database work. A Git-ignored read-only execution stage then held only
the helper, inventory SQL and row fingerprints; no archive, credentials or raw
rows were copied into that stage. Backup ACLs were not broadened.

Strict comparisons next stopped before migration on catalog representations:

- Two `django_content_type` physical column numbers closed gaps left by an old
  dropped column: app_label3→2 and model4→3. Visible column order, names, types,
  nullability and defaults were exact. Only physical slots were normalized.
- Fifteen existing CHECKs deparsed array casts differently after restore.
  Each expected CHECK was reparsed by PostgreSQL on an empty transaction-local
  `ON COMMIT DROP` table of the same column types, then required to match the
  restored CHECK definition exactly. No CHECK text/property was discarded and
  no source/migration/business DDL was changed. Unknown mismatches still failed.

The final helper passed all comparisons and then performed the single isolated
migration. Earlier exit1 reports are retained; they are not reported as successful
runs. This was a verification-helper correction, not a schema/business-rule fix.

## 7. Backup, restore and cleanup boundaries

Use the existing repository/PostgreSQL mechanisms after verifying the target.
The backup remains local, Git-ignored and uncommitted, with a unique path that
does not overwrite earlier backups. Do not read or print private `.env` values,
put a password in command arguments, extract credentials into logs, or upload
the archive. Record only safe archive metadata and validation outcomes here.

Restore into a uniquely identified disposable database/container. It must not
use the persistent development target/name, writable development data volume,
or public database port. Verify ownership before creation/restore/cleanup.
Actual restored Users/Sessions remain comparison data; any functional smoke
fixtures must use new synthetic identities and business records in isolation.
Never submit restored customer/private content to a fixture or external provider.

Only the exact task-owned test database/container/network may be removed after
ownership labels, repository/run identifiers, cluster identity and current use
are checked. The persistent development container/volume/database, the retained
new archive and all older backups must remain. Never prune resources by name
pattern alone or use `docker compose down -v`, system/volume prune, fake
migrations or direct edits to `django_migrations`.

## 8. Proposed later development rollout sequence — NOT EXECUTED

1. Obtain separate explicit Owner approval for the exact development migration.
2. Reconfirm database identity, current history/schema, exact-row inventory,
   storage and active connections. Account for the User/Session changes observed
   in the resume; stop on unexplained schema or migration-state differences.
3. Obtain a new verified backup of the current state and restore rehearsal
   appropriate to the actual rollout checkpoint, in a quiet controlled window.
   Retain this R1 backup as additional evidence, not as a substitute for a
   fresh backup that includes the newer User/Session state.
4. Review the exact migration plan and establish a short controlled maintenance
   window if active traffic could conflict with DDL or post-migration checks.
5. Reuse the existing local environment/startup primitives and standard Django
   migration command for exact `ai.0001_initial`, as proposed below. There is no
   existing `-Migrate` launcher switch; no development command below was run.
6. Verify migration history, both AI tables, columns, FKs, lifecycle constraints,
   indexes/unique guards, model consistency and preservation of legacy rows.
7. Keep fixture execution disabled until schema and separately authorized smoke
   checks are complete. No live provider is enabled by this migration.
8. If apply or verification fails, preserve the actual state and report it.
   Do not fake migration history, edit applied migrations, roll back or restore
   development automatically.

### Concrete PowerShell plan for a separately approved rollout — pseudocode only

The following is documentation, **not an executable R1 helper or authorization**.
Do not run it in this task. The future operator must first obtain explicit Owner
approval, complete fresh inventory/backup/rehearsal and check the exact plan.
Reading the local private environment is proposed only for that future approved
startup/migration process; R1 has not read `.env` or changed its values.

```powershell
# FUTURE OWNER-APPROVED ROLLOUT ONLY — NOT EXECUTED IN R1.
$htRepository = [IO.Path]::GetFullPath('D:\da\HustlyTasker').TrimEnd([IO.Path]::DirectorySeparatorChar)
. (Join-Path $htRepository 'scripts/start-backend-dev.ps1') # Defines pure functions only.
$htEnvPath = [IO.Path]::GetFullPath((Join-Path $htRepository '.env'))
if (-not $htEnvPath.StartsWith("$htRepository$([IO.Path]::DirectorySeparatorChar)", [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Private environment must be repository-local.'
}
if (-not (Test-Path -LiteralPath $htEnvPath -PathType Leaf)) { throw 'Private environment is missing.' }
if ((Get-Item -LiteralPath $htEnvPath).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Linked private environment is refused.'
}
& git -C $htRepository check-ignore --quiet -- $htEnvPath
if ($LASTEXITCODE -ne 0) { throw 'Private environment must be Git-ignored.' }
$htValues = Read-HustlyDevelopmentEnvironment -Lines ([IO.File]::ReadAllLines($htEnvPath))
Assert-HustlyDevelopmentEnvironment -Values $htValues # Exact existing development DB/loopback checks.
$htPython = Join-Path $htRepository 'backend/venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $htPython -PathType Leaf)) { throw 'Existing venv Python is missing.' }

function Invoke-HustlyReviewedManagementCommand([string]$Command) {
    # Exact allowlist; no arbitrary management arguments or provider enable.
    $htAllowedCommands = @(
        'manage.py check',
        'manage.py makemigrations --check --dry-run',
        'manage.py migrate ai 0001_initial --plan',
        'manage.py migrate ai 0001_initial --noinput',
        'manage.py showmigrations ai',
        'manage.py migrate --check'
    )
    if ($Command -cnotin $htAllowedCommands) { throw 'Management command is not approved by this plan.' }
    $htProcess = New-Object System.Diagnostics.Process
    try {
        $htInfo = New-HustlyDevelopmentProcessInfo -Repository $htRepository -Values $htValues -Mode 'check'
        $htInfo.Arguments = $Command # Static allowlisted command only.
        $htInfo.CreateNoWindow = $true
        $htProcess.StartInfo = $htInfo
        if (-not $htProcess.Start()) { throw 'Cannot start the existing Python child process.' }
        $htHandle = $htProcess.Handle
        $htProcess.WaitForExit()
        if ($htProcess.ExitCode -ne 0) { throw 'Management command failed; preserve state and stop.' }
    } finally {
        $htProcess.Dispose()
    }
}

# Future approved preflight only. These commands do not apply migration.
Invoke-HustlyReviewedManagementCommand 'manage.py check'
Invoke-HustlyReviewedManagementCommand 'manage.py makemigrations --check --dry-run'
Invoke-HustlyReviewedManagementCommand 'manage.py migrate ai 0001_initial --plan'

# STOP. Review the exact plan and obtain the separate persistent-development
# approval after fresh identity/inventory/backup/restore gates. No write command
# is invoked by this documentation example. Only a later authorized operator
# may explicitly execute the following commented command:
# Invoke-HustlyReviewedManagementCommand 'manage.py migrate ai 0001_initial --noinput'

# Post-apply commands, also left commented until that separately approved apply:
# Invoke-HustlyReviewedManagementCommand 'manage.py showmigrations ai'
# Invoke-HustlyReviewedManagementCommand 'manage.py migrate --check'
```

This reuses the existing parser, development-target assertion, correct venv and
sanitized child-process environment without modifying `settings.py` or inventing
a launcher parameter. The secret values are process-local and never printed;
the child's deployment-related configuration comes from the validated local file.
The existing virtualenv was checked in the permitted execution context:
Python3.12.5 and pip check exit0. A default sandbox agent's earlier AST exit103
was an execution-context/path limitation, not evidence that the Owner's venv
needed replacement. No venv recreation or environment-file read occurred in R1.
The existing launcher
does not accept the AI fixture flag in its private-file allowlist, so this plan
does not enable it. Provider/live/frontend/Analyzer execution remains disabled.

Pause active development requests for the reviewed maintenance interval. If DDL
waits on locks or any command fails, record actual state and stop; do not kill
other connections, increase timeouts, fake history or retry blindly. Before
resuming traffic verify actual migration applied once, both tables, expected
columns/FKs/CHECKs/unique indexes, current model/graph consistency, original
User/Session/business rows and only the expected metadata additions. Any
authenticated mutation smoke belongs to a separately approved isolated target
unless the Owner explicitly authorizes otherwise.

### Failure, reversal and restore strategy

Django migration reversal removes the dedicated AI schema; backup restoration
recovers a database snapshot. They are distinct mechanisms with different data
loss risks. Neither is authorized for persistent development in R1. Any eventual
reversal/restore must be reviewed against new AI rows and changes since backup.

Before any future reversal, review `migrate ai zero --plan` and whether AI rows,
confirmed Tasks or downstream dependencies now exist. Reversing AI tables does
not undo Tasks previously created through confirmation. Restoring a whole
database can overwrite every change made after the backup. No automatic Django
rollback, backup restore or transaction-history repair is authorized by R1.
An interrupted failure needs fresh schema/history/transaction inspection and
separate Owner direction; do not infer that a nonzero process exit means the
whole database needs restoring.

## 9. Completion and Owner gate

**HT-AI-P4-02B-R1 — MIGRATION READINESS VERIFIED.** The preceding R1 checkpoint
passed inventory, archive validation, isolated restore/apply, original-data
preservation, schema/constraint/index checks,72 direct restored-DB tests and158
fresh-cluster AI tests. The owned database was dropped only after checking its
cluster system ID, exact owner/comment marker and lack of active connections.
Shared ownership-checked container/network cleanup exited0; backups were retained.

The R1 final read-only comparison on2026-10-28 kept all27 table row fingerprints,
schema and sequences identical during that task interval:35 migrations,0AI
migrations,3 Users,2 Sessions,business rows0 and no AI tables. The original
container/volume remained intact. The2026-10-29 resume separately found the two
User/Session fingerprint changes described in section3; it does not claim exact
data equality across those dates or identify their cause.
No runtime/model/migration/private-environment change, live provider call,
production action, commit or push occurred. Current-resume artifact/document
checks do not relabel earlier R1 tests as newly executed.

No blocker remains for readiness of the tested migration and snapshot. Actual
rollout remains gated on a fresh inventory, a quiet window and a new backup of
the latest state; verify normal Owner access to the retained backup and review
the exact plan. Never roll back newer User/Session state to this older backup
merely to match its fingerprints. No automatic restore/repair is authorized.
Physical retention purge remains unimplemented and fixture throttles remain
process-local; this rehearsal does not approve live/production deployment.

**Required next approval:** controlled application of exactly `ai.0001_initial`
to the verified `hustlytasker_db` development target under the fresh safety gates
above. That approval has not been given. Keep fixture execution disabled and
do not begin rollout, frontend, live provider, Analyzer or another task automatically.
**STOP AT OWNER REVIEW GATE.**
