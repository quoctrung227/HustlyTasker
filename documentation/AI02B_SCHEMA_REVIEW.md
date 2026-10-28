# HT-AI-P4-02B — Schema and Transaction Review

Date: **2026-10-28**. Status: **SCHEMA REVIEW COMPLETE WITHIN APPROVED SCOPE**.

This review precedes model/migration creation. The Owner's current P4-02B
instruction authorizes a fixture-only Generator, dedicated minimal durable
state, manager authorization, atomic confirmation, 30-minute confirmation
expiry, seven-day unconfirmed-payload retention and 30-day confirmation/recovery
metadata retention. It does not authorize live AI, persistent-development
migration, frontend AI, Analyzer runtime or automatic physical purge.

Existing dirty source/documentation remains protected. No database or private
environment was read for this review. Existing architecture evidence is in
[AI_ARCHITECTURE_DESIGN.md](AI_ARCHITECTURE_DESIGN.md) and
[AI_PERSISTENCE_REVIEW.md](AI_PERSISTENCE_REVIEW.md). This document records the
bounded implementation design, not an already applied schema.

## 1. Source evidence and scope

- [create_task](../backend/apps/tasks/services.py) already runs atomically,
  invokes the public tenant mutation lock helper, verifies manager capability,
  sets PENDING/current creator and writes a safe task.created audit.
- [lock_workspace_mutation_context](../backend/apps/workspace/services.py)
  resolves current active tenant membership, then locks Profile, Workspace,
  actor ProfileMembership and actor WorkspaceMember when applicable. It rejects
  archived Profile and role drift. The domain predicate must still reject an
  archived Workspace.
- [Workspace access](../backend/apps/workspace/access.py) defines current
  manager capability; no new role or is_staff shortcut is required.
- Task parents after a proposal lock may only be nodes newly created in that
  same confirmation transaction. This avoids reversing the existing shared
  Task/proposal lock order.
- Existing account-security transactions lock User then security-token rows;
  no current reverse User→Profile lock path was found in that source review.
  Actor FKs and audit creation can still acquire implicit User locks and must
  be included in concurrency tests, not assumed harmless by documentation.

## 2. Minimal records

Two logical records suffice; no budget ledger or four-table design is required
for zero-cost fixtures. Names below describe the planned responsibilities and
must be reconciled with the final models/migration before task completion.

```text
AiProposal
  id: server-generated UUID primary key, never supplied/upserted by client
  actor, profile, workspace: dedicated tenant binding
  status: AVAILABLE | CONFIRMED
  contract_version: supported Task-plan schema version
  revision: positive immutable proposal revision, initially1
  scenario_id: server-allowlisted synthetic scenario identifier
  payload: normalized bounded JSON, nullable for scrubbed/confirmed rows
  created_at, expires_at
  payload_expires_at: seven days after creation
  confirmed_at: nullable until committed
  created_tasks: local_ref -> server-created Task UUID, nullable after scrub
  recovery_expires_at: nullable until committed;30 days after confirmation

AiOperation
  actor, profile, workspace, operation: GENERATE | CONFIRM
  key_digest: SHA-256 of a high-entropy request idempotency UUID
  body_digest: versioned keyed canonical-body fingerprint, no raw request
  proposal reference
  created_at
  unique(actor, profile, workspace, operation, key_digest)
```

Proposal consumption is the single-confirmation guard; it must survive payload
or result scrubbing. An operation row is not a Task authorization token and is
never sufficient without fresh actor/tenant/role/proposal-ownership checks.

Current synthetic scenarios are server-owned `subtitle-check-v1` and
`task-tree-v1`. Request data cannot choose the provider or supply arbitrary
scenario content. The revision participates in confirmation conflict checks;
the bounded v1 API has no separate proposal-edit persistence endpoint.

## 3. Required fifteen-point gate

| Gate | Reviewed design |
|---|---|
| 1. Exact minimal fields | Proposal lifecycle/payload/result and scoped operation fingerprint above; no raw brief, provider response, usage ledger or secret fields |
| 2. Primary/stable identity | UUID generated only by server at creation; confirm/retrieve never creates or upserts an absent proposal |
| 3. Actor/Profile/Workspace FKs | PROTECT follows existing business preservation conventions; every service validates Workspace→Profile and current actor authority |
| 4. Status/timestamps | AVAILABLE has no confirmation timestamp/result/recovery window; CONFIRMED has committed timestamp/recovery bound; expiry is computed, not a status that can erase consumption |
| 5. Payload/version | Reuse existing strict Task-plan parser; normalized JSON has at most20 nodes, valid priority/date/DAG and no assignment/status/foreign-parent fields |
| 6. Idempotency/uniqueness | Unique operation scope/key; canonical body binds operation target, revision/provenance and normalized edited plan. Proposal row status/locking blocks a second batch under another key |
| 7. Immutable outcome | Result map is created by backend only and written with Task/audit commit; a retry returns that same map, never recomputes it from current Tasks |
| 8. FK deletion | No cascade from AI rows into Task/Review/Audit/business data. Operation→proposal PROTECT is safe for controlled cleanup; future deletion must handle operations before proposal without reversing lock order |
| 9. Index/query patterns | Primary-key scoped proposal lookup; unique operation scope/key; actor/workspace/time and lifecycle/expiry indexes only where actual queries justify them |
| 10. Lock order | Existing tenant locks first, then proposal then operation; no provider call inside atomic block; no budget-family locks in confirmation |
| 11. Retention separation | Unconfirmed payload window7 days from creation; confirmation eligibility30 minutes from creation; outcome recovery30 days from committed confirmation. Consumed marker remains separate from payload/result |
| 12. Migration rollback | Additive AI migration only. Reverse drops only AI tables; it must not delete Tasks or rewrite existing migrations. Reversal is tested on isolated data and is not authorized for persistent development |
| 13. Synthetic data | Generate accepts server-controlled scenario IDs. Persist normalized fixture proposal/provenance; never raw confidential prompt. Human-edited text is stored only under the synthetic-demo usage policy, not certified synthetic by regex |
| 14. Revoke/replay | Current manager and original actor checks on generate/retrieve/confirm/recovery; revoked/inactive/cross-tenant callers receive no saved payload or created IDs |
| 15. Purge/recovery boundaries | No automatic physical purge in this slice unless separately implemented/tested. Expired or scrubbed content must not reset CONFIRMED. Report physical retention not enforced if only logical gates exist |

## 4. Constraints and invariants

The DB must reject unknown proposal/operation states and enforce scoped operation
key uniqueness. Proposal lifecycle checks should pair confirmation timestamp and
recovery window and reject a result on AVAILABLE. CONFIRMED with null result is
valid for a future scrubbed tombstone; null payload must not mean available.

Deadline ordering constraints should require expiry after creation and recovery
after confirmation where present. The exact approved durations are set by the
service. Profile/Workspace equality across independent FKs is a cross-table
invariant, not something a normal CHECK can guarantee: services must resolve the
full scoped chain. JSON shape, node count, DAG/cycles and deadline representation
remain application validation using the existing contract parser.

AuditLog is metadata only. Task creation audits are reused without copying
proposal titles, descriptions, notes or source text into new audit metadata.

## 5. Generate, confirm and replay transactions

Generate performs input/scenario validation and the deterministic fixture call
outside an atomic block. The storage transaction then locks and reauthorizes the
tenant and checks the scoped request key before storing the normalized proposal.
Two concurrent requests with the same key/body return one stored proposal;
changed body conflicts. Failed storage leaves no business Task.

Confirmation has one outer atomic transaction:

1. Lock and revalidate existing Profile→Workspace→actor memberships; require the
   approved active manager predicate and original proposal actor.
2. Lock the scoped proposal, then operation rows according to a fixed order.
   Check request key across its entire actor/Profile/Workspace/operation scope,
   not merely rows already linked to the requested proposal.
3. A key used for another proposal or canonical body conflicts. A committed
   same-key/body request may recover its stored result while within the approved
   recovery window, even when the preview's30 minutes have passed.
4. An already CONFIRMED proposal under another key conflicts without creating
   another batch. An unconfirmed expired proposal cannot be consumed.
5. Validate the full edited plan, then create topologically through unchanged
   create_task. Parent references map only to IDs created in this transaction.
6. Write immutable result mapping, operation and consumed proposal state with
   Task/audit changes. Any node/audit/constraint failure rolls back all of them.

The canonical fingerprint must include proposal target identity as well as the
confirmation body. Otherwise the same key can accidentally be reused for a
different proposal. Date normalization is UTC; JSON object keys are canonical,
array order and local references retain defined semantics. No raw canonical body
or fingerprint is returned in public errors/logs.

For this fixture-only implementation, body fingerprints use Django salted_hmac
with an AI-specific purpose salt derived from the existing configured SECRET_KEY.
This does not generate/store another credential or read the private env file.
Verification checks the current configured key plus SECRET_KEY_FALLBACKS for
rotation compatibility; a missing old key fails closed with conflict, never a
second creation. No secret/key value is printed or stored in an AI row. A future
private-data encryption/key-governance change still requires its own review.

User/account lifecycle checks are read in current authorization and FK effects
must be covered by tests. P4-02B does not invent a User deactivation service or
alter last-active-owner invariants.

## 6. Retention and physical deletion limitation

Recommended minimization is to clear proposal payload when confirmation commits:
the resulting Tasks hold the accepted content, while recovery only needs the
immutable map and fingerprint. Unconfirmed payload becomes unusable after preview
expiry and may be logically hidden/scrubbed according to the seven-day bound.

Recovery access ends30 days after confirmation. A consumed proposal must never
be made AVAILABLE by payload/result scrub. If an eventual approved purge fully
deletes the proposal, old confirm URLs must return missing; they must never
recreate the old identity from client input. A new generated proposal has a new
server UUID and needs a new explicit confirmation.

Until a controlled purge/scrub implementation exists, the task must explicitly
report that logical expiry/read/recovery limits are enforced but **physical
retention maxima are not automatically enforced**. This is the fallback the
Owner permitted, not permission to claim deletion happened. Existing development
rows are never deleted by this task.

## 7. Migration and test gates

The migration may create only dedicated AI records, after the root implementation
checks this review against final field/constraint/index names. Planned new
ai.0001 uses workspace.0004 and the swappable User dependency. There is no Task FK
solely for the JSON created_tasks mapping. This is additive to the existing
current schema; no prior migration is edited and no historical tenant backfill
is introduced. Django model-state checks must validate the resulting dependency
graph. Any material mismatch requires updating this review before migration code.

Required isolated PostgreSQL proofs: concurrent same/different-key confirmation,
same key reused on another proposal, audit/node rollback, stale/revoked/archive
authorization, replay after preview expiry and after recovery bound, metadata/
payload scrub without duplicate creation, implicit FK/User locks, schema checks
and reverse migration preserving existing Tasks. No proof is claimed by this
review alone. Full regressions and explicit exit/cleanup evidence remain required.

Migration creation is not persistent rollout approval. Development apply still
requires its own task, fresh inventory, backup/restore rehearsal and plan review.
No production or development database operation is part of this review.

## 8. Review outcome

The two-record design above fits the Owner's approved fixture-only scope and the
existing transaction/service architecture. No unresolved product decision blocks
writing the matching additive AI models/migration and testing them in isolation.
This is a technical schema review under the current explicit authorization, not
new approval for persistent rollout, live AI, Analyzer or frontend.

Outstanding verification risks are concrete: implicit FK/User/audit lock effects,
concurrent key/proposal races, retention/recovery boundaries and complete rollback.
They must pass the isolated PostgreSQL tests listed above. Physical retention
remains explicitly unenforced until controlled purge/scrub is implemented; logical
limits and a durable consumption marker must not be described as physical deletion.

## 9. Post-implementation verification — 2026-10-28

The reviewed two-model design is now implemented by ai.0001_initial and checked
without model drift. Final isolated PostgreSQL evidence: AI158/158 PASS11.208s
(including3 migration tests and actual generation/confirmation concurrency),
Task/Review/Workspace/RBAC378/378 PASS165.639s and full643/643 PASS215.115s.
All actual launcher/Python-container exit codes0 and owned DB/container/network
cleanup verified. See HANDOVER.md for run IDs and commands. Generation persists
only proposal/operation; the latest resume requirement forbids pre-confirmation
Task/AuditLog rows. Confirmation Task/audit/state/result remains one transaction.

The source migration was applied/reversed ONLY in isolated PostgreSQL tests.
Read-only development verification still shows35 migration records and no AI
tables. No persistent rollout or physical-retention enforcement follows from
these tests. HT-AI-P4-02B is IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT
MIGRATION APPROVAL, stopped at OWNER REVIEW GATE.
