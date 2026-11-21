# HT-ORG-INVITATION-V2 — Controlled development rollout

## Current checkpoint — 2026-11-13

**HT-ORG-INVITATION-V2 — DEVELOPMENT ROLLOUT COMPLETE — PENDING OWNER MANUAL ACCEPTANCE.**

Owner attachment `7575b212-1848-4bcd-aa4b-b5d8afcca480` conditionally authorizes
exactly these development targets, in this order:

1. `workspace.0005_account_invitations`.
2. `notifications.0004_invitation_context`.

This authorization supersedes the earlier pending-approval checkpoint only for
these two targets after all safety gates pass. It does not authorize general
`migrate`, `ai.0002_dispatch_governance`, production, destructive data changes,
new fixtures on development, real email, paid AI, `.env` edits or deployment.
The approved business rules remain in [ORG_INVITATION_V2](ORG_INVITATION_V2.md).
[HANDOVER](HANDOVER.md) owns the latest operational continuation checkpoint.

## Evidence and progress

Private receipts are Git-ignored under
`.local_backups/HT-ORG-INVITATION-V2-ROLLOUT/`. No secret, raw session, token,
customer content or personal identity belongs in this document.

| Gate | Current evidence/status |
|---|---|
| Source and dependency audit | Static source confirms workspace0005 depends on workspace0004 and the existing User model; notifications0004 depends on notifications0003 and workspace0005. No AI dependency, RunPython/RunSQL, table drop or rename |
| Fresh development inventory and SQL planner | Fresh read-only baseline29tables/39migrations; corrected preflight exit0, exact allowed target plans and no AI dependency |
| New custom archive and SHA-256 | New132398-byte custom archive, restricted ACL/outside repository; SHA-256 and actual restore verified |
| Restore rehearsal | Attempt2 PASS: restored fingerprints preserved, exact two-target apply and post gate exit0;31tables/41migration records only on isolated target |
| Legacy/Notification compatibility | Rehearsal post gate confirms original rows/projections and constraints;19synthetic API/service smoke checks PASS with locmem only |
| Old-writer stop and final plan | Writer gate exit0; port8000 was free and no old HustlyTasker backend PID needed stopping. Exact plan rechecked before each target |
| Development execution | workspace0005 applied11:44:56.741107Z, notifications0004 applied11:44:58.160588Z; exact guard/launcher exits0 |
| Preservation and startup | Post gate/read-only projections/final preservation exits0; official backend/Vite loopback startup and25/25HTTP GET checks PASS |
| Owner manual acceptance | PENDING; never inferred from automated checks |

Previous implementation verification is historical for this rollout: focused
backend62/62, full isolated PostgreSQL1108/1108, frontend1236/1236 and six browser
suites25/25 passed. They are not tests newly executed by this rollout.

### Fresh development baseline

Source: `development-before.json`, not a prior chat checkpoint. Actual database
is `hustlytasker_db`, PostgreSQL16.14; schema has29tables and39migration records.

| Data | Before rollout |
|---|---:|
| Users / Sessions |5 /2|
| Profiles / ProfileMemberships |2 /3|
| Workspaces / WorkspaceMembers |3 /3|
| Tasks / TaskAssignments |5 /5|
| Deliverables / Reviews / Comments |3 /0 /1|
| Notifications / AuditLogs |9 /42|
| AccountSecurityTokens |1|
| ProfileInvitations |2|
| AI proposals / operations |0 /0|

The two existing legacy Invitations are1ACCEPTED and1REVOKED, both SENT, with
non-null token digests. There are **zero real PENDING Invitations** in this
baseline. Preserve these actual rows exactly; positive pending-token acceptance
must use a synthetic isolated fixture, not an invented pending development row.
No identity, token value, session value or customer content is reproduced here.

## Backup and restore evidence

The fresh custom archive is retained outside the repository and outside test
resource cleanup, under a directory with restricted ACL:

```text
D:\da\HustlyTaskerBackups\HT-ORG-INVITATION-V2-ROLLOUT\20261113T114057Z_0a7b46be366643fa9f3a52526991b82c\hustlytasker_development_20261113T114057Z.dump
```

- Size:132398bytes. SHA-256:
  `6CB6EB961DF83DA3C819CCD143A17F3C2CFC0FE32379E27216C2ECD43F05ADDC`.
- `pg_dump`/archive-list/full-read and actual archive restore have separate
  native-process receipts. Rehearsal success is not inferred from file presence.
- Successful rehearsal database:
  `ht_inv2_665321a7ed2b4cadaefd13180017b034`, a separate PostgreSQL cluster with
  no writable development volume or live mail/provider configuration.
- Its restored pre-migration data/schema/history match development; after the
  exact workspace0005 then notifications0004 targets, post gate exit0 confirms
  preserved prior row fingerprints/metadata, expected new metadata and schema.
  Rehearsal has31tables/41migration records and no `ai.0002`/governance tables.
- A separate disposable clone with suffix `_smoke` ran19synthetic API/service
  checks, exit0, including positive directory/privacy/page20, role ceilings,
  wrong-account/tenant denial, zero-Profile recipient, SMTP-failure Web accept,
  same-ID retry/attempt budget, independent notification read, replay/current-
  month grant, CSRF, legacy pending-token compatibility and typed constraints.
  All original restored rows were preserved. Four messages were accepted by
  locmem; real external mail and AI calls were0. This is not browser E2E or
  a real authenticated persistent-development HTTP test.

Two verifier-only failed attempts remain recorded, with no development write:
the first preflight encountered a string JSONB value where the helper expected
a dict, corrected by explicit JSON decoding; the first restore comparison found
only historical physical column-number gaps compacted by pg_dump/restore in
django_content_type. Logical names/order/types/nullability/defaults matched.
Cross-cluster comparison now uses logical ordinals; same-development-cluster
checks remain exact. Neither correction changed runtime or migration source.
Attempt2 cleanup confirms the owned container/network were removed and backup
retained. Separate fresh development identity/planner/preservation gates passed
before execution; rehearsal success did not substitute for those final checks.

## Actual development execution and post-migration data

The standard targeted migrations executed, in UTC, with guard/launcher exit0:

1. `workspace.0005_account_invitations`:2026-11-13T11:44:56.741107Z.
2. `notifications.0004_invitation_context`:2026-11-13T11:44:58.160588Z.

Each immediate plan contained only its own target. The initial notification
preflight plan included workspace0005 plus notifications0004, both approved;
after the first target, only notifications0004 remained. No AI or other target
was executed; `ai.0002` remains UNAPPLIED and governance tables absent.

Post gate and read-only projections return exit0. Tables29→31 and migration
history39→41 are expected. All prior business row SHA fingerprints match the
fresh baseline, including Users/Sessions, legacy Invitations, membership,
Workspace access, Task/Deliverable/Comment, Task Notifications and AuditLogs.
Existing Invitation rows gain only EMAIL_TOKEN, Notifications only null
Invitation context. No membership/Workspace permission or business row was added.
The two quota tables are empty.

Django's expected framework metadata changes are content types25→27 and
permissions100→108 for the two quota models; every original metadata row hash
remains. These intentional metadata additions are not unexpected business writes.
Five read-only in-process authenticated GET projections return200 using an
existing legitimate Owner, without creating a session. They are not real
authenticated HTTP/browser acceptance. Positive directory checks remain isolated
because successful directory GET records a quota event.

## Backend/frontend startup and HTTP smoke

The existing `scripts/start-backend-dev.ps1` launcher and Vite started on
loopback8000/5173, with no automatic migrations, reload, fixtures or duplicate
backend. A unique health marker in the new backend log and the listener PID
verify the intended process. Startup uses the existing local configuration
through the repository loader with values hidden; `.env` was not edited.

`http-smoke-result.json` records25/25HTTP GET checks PASS, direct to Django and
through the Vite proxy. Health/CSRF return200, CSRF cookie presence is checked
without printing its value, and anonymous protected candidate/inbox/detail/
Notification/auth boundaries return403 as expected. This is an HTTP smoke run,
not a new Playwright suite, authenticated browser login or Owner acceptance.
Final read-only preservation after startup returns0: every original business
fingerprint remains exact and both quota tables stay empty. The only known
pending migration remains the deliberately excluded `ai.0002`.

Independent final source/resource checks also pass:833baseline files retained,
0runtime file changes,33migration files unchanged and Git main/HEAD
31f0af932a9ffaf3e578115d63faa4a776e75175 preserved. Both owned rehearsal runs have
0remaining containers/networks. The protected backup remains present with the
same SHA-256, and the original development container is still running. Existing
dirty/untracked work is retained; no commit/push/reset/clean/deploy occurred.

Use the already-running website at `http://127.0.0.1:5173`, then Ctrl+F5. If both
servers have later been stopped, first verify8000/5173are free, then use two
PowerShell terminals:

```powershell
Set-Location D:\da\HustlyTasker
.\scripts\start-backend-dev.ps1
```

```powershell
Set-Location D:\da\HustlyTasker\frontend
npm.cmd run dev -- --host 127.0.0.1
```

No new runtime code, migration source, SMTP/AI configuration, genuine email,
live provider call, commit/push or deployment was included. on_commit is still
not a durable outbox; crash recovery is explicit bounded retry, and automatic
quota retention remains separate future work. Genuine mail delivery remains
unverified in this rollout. Stop for Owner manual acceptance; do not begin the
next feature, AI migration, public release or production deployment.

## Preservation criteria

- Take a fresh inventory and data fingerprints from the actual development
  database; do not assume the previous39-migration/row-count checkpoint remains.
- A normal Django migration may append two content types and their eight
  permissions for the new quota models. Verify those exact metadata changes
  separately from protected business data; preserve every prior metadata row.
- Existing Invitation rows must retain every old column, especially identity,
  token digest, status, delivery state and actual expiry. The expected added
  discriminator is `EMAIL_TOKEN`, with no guessed recipient or reissued token.
- Existing Notification rows must retain every old column and gain only
  `invitation_id=NULL`; existing Task events and recipient/read state stay intact.
- Memberships, Workspace access, Users, Sessions, Tasks, assignments, Reviews,
  Comments and AuditLogs must not be created, updated or removed by rollout
  smoke checks. New quota tables remain empty on development during verification.
- Only the two candidate migration records may be appended. `ai.0002` and its
  governance tables must remain absent. Never use fake/manual migration history.

## Read-only smoke boundary

Successful authenticated account-directory GET is **not read-only** in current
source: `invitation_candidates` takes locks and appends an
`InvitationDirectoryAccess` quota row. Therefore positive directory schema,
privacy and authorization checks belong on the isolated restored/synthetic
database, not persistent development in this rollout.

Development smoke must use only requests/handlers that do not persist writes.
Do not create a login session or business fixture merely to obtain an HTTP200.
Report anonymous HTTP boundaries, any read-only authenticated handler checks,
and isolated positive directory checks separately. Do not call an in-process
forced-authentication handler check a real authenticated browser/session test.
CSRF bootstrap does not grant tenant authority; no real email is sent.

## Failure and recovery boundary

If identity, drift, backup, restore, migration plan or preservation fails, stop
before the next write. If one candidate has already applied, record its actual
state; do not label it unapplied or automatically reverse/restore development.
New source requires the new columns, while old writers omit the required
acceptance discriminator. Stop old writers before execution and start the new
backend only after both schemas pass. A reverse with ACCOUNT/Invitation
Notification data is not guaranteed safe and requires separate Owner approval.
After these targets, Django may still warn about the deliberately unapplied
`ai.0002_dispatch_governance`. Do not follow a generic `migrate` suggestion to
remove that warning; AI governance rollout is not authorized by this task.

## Owner acceptance after successful rollout

This checklist becomes usable only after both migrations, preservation and new
backend startup have actually passed. Owner may then choose to perform these
real development mutations; the rollout does not perform them automatically.

1. Reload React and log in as the legitimate Profile Owner/Admin. Open
   **Tổ chức → Thành viên tổ chức → Thêm thành viên**; verify the account picker
   replaces email/code entry and search/pagination work with safe labels.
2. Owner may choose ADMIN or MEMBER; Admin may choose only MEMBER. An ordinary
   MEMBER/Workspace-only manager must not gain directory/invitation authority.
3. Select a registered account and send one invitation. This is real data and
   may send notification email using the existing configuration; Owner decides
   whether to proceed. Do not repeat create merely because email reports FAILED.
4. Sign in as the exact recipient, including a zero-Profile account when available.
   Open **Thông báo** or **Lời mời tổ chức**; verify the invited Profile/role,
   explicit Accept/Decline and independent notification read state.
5. Accept a valid invitation; verify the Profile becomes available and the
   approved current-month Workspace access is granted without Task assignment or
   reactivation of revoked Workspace access. The current Profile must not switch
   silently. Refresh and repeated accept must not duplicate membership.
6. On a separate invitation, decline and verify no membership is granted.
   Terminal status must refresh in the manager list.
7. If a real delivery fails, use the existing same-ID bounded retry rather than
   issuing another invitation. Role, expiry and read state must not reset.
   Do not deliberately break SMTP credentials to test this; isolated fake-mail
   failure coverage is separate from genuine delivery verification.
8. Log out/switch accounts and verify previous recipient data is not visible.
   Legacy compatibility applies only to a pre-existing valid token and its
   actual expiry; no new code-entry flow should be promoted.

Owner may keep or later manage records created during manual acceptance. This
rollout does not delete them or claim Owner approval in advance. No genuine
email send is automated by the rollout; fake/locmem success is not proof of
inbox delivery or authorization for an external send.
