# PROJECT ARCHITECTURE REVIEW — PENDING OWNER DECISION

Date: 2026-10-25  
Task: `HT-TASK-P2-05 — Task Hierarchy, Deadline & Priority Foundation`  
Status: **DESIGN PROPOSAL ONLY — PROJECT IMPLEMENTATION NOT AUTHORIZED**

## 1. Evidence and authority

The current Owner instruction authorizes Task/Subtask, deadline and priority
work independently of Project. It explicitly prohibits a Project model, API
or migration until a separate Owner decision and implementation scope exist.

Repository evidence at the start of this task:

- `backend/apps/tasks/models.py` has a required `Task.workspace`, existing
  `priority` (`LOW`, `MEDIUM`, `HIGH`, `URGENT`, default `MEDIUM`) and nullable
  datetime `deadline`. No Project relationship or Project model exists.
- `backend/apps/tasks/urls.py`, serializers, access selectors and services
  use nested Profile/Workspace/Task scope. Deliverable and internal Review
  belong to an individual Task. Task management/execution/review capabilities
  come from the existing Workspace access context.
- `documentation/ORIGINAL_REQUIREMENTS.md`, F04, describes Task workflow and
  deadline. Its business architecture directly links Workspace to Task; it
  does not require a Project between them.
- `documentation/DECISION_LOG.md`, accepted 2026-10-16 decision group 6 and
  accepted ownership table, already establish Client → many Projects, with
  Project belonging to Profile/Client and potentially spanning monthly
  Workspaces through Tasks. Task still belongs to exactly one Workspace;
  Task/Project/Client/Workspace references must share one Profile.
- `documentation/RBAC_DESIGN.md` explicitly repeats that approved cross-month
  boundary and keeps Client/Project APIs closed until tenant schema exists.
- `reference/original_document/00-discovery/parts/03-models.md` inventories a
  legacy Prisma Project and optional Task.projectId. This is reference
  discovery about another implementation, not Django code or new approval.

No separately named SRS/HLD document or Word specification was found in the
repository inventory for this task. Existing material is the requirements and
architecture Markdown, legacy discovery/diagrams, and the reference audit
PDFs (`HustlyTasker-System-Audit.pdf`, `system-overview.pdf`). The new SRS/HLD
mentioned by the Owner is therefore a planned artifact, not evidence that a
new Project schema has been approved. Existing legacy audit PDFs do not
override accepted decisions or the current implementation scope.

## 2. Alternatives A and B

**A — Retain the operational hierarchy now:**

```text
Profile → monthly Workspace → Task → Subtask
```

**B — Add an optional Project between Workspace and Task:**

```text
Profile → monthly Workspace → optional Project → Task → Subtask
```

For comparison, B retains direct Workspace Tasks when no Project is selected.
Making Project mandatory would be a further change and is not proposed here.

| Criterion | A: direct Workspace Tasks | B: optional Workspace-owned Project |
|---|---|---|
| Graduation topic: team work management | Task decomposition, assignments, deadlines, priority and reviewed completion support the core topic directly. | Adds grouping by initiative; useful when that grouping is an explicit requirement. |
| Current schema | Add Task hierarchy independently; reuse existing deadline/priority fields. | Requires Project aggregate and optional Task association, plus decisions about tenant/client ownership. |
| RBAC / tenant isolation | Reuses current Workspace context and task capabilities. | Must authorize Project and linked Tasks separately; Project knowledge cannot grant Workspace access. |
| Monthly Workspace | Work remains in its existing operational month. | A canonical Workspace owner restricts one Project to one month, conflicting with the accepted cross-month Project target. |
| Task/Review workflow | Each Task/Subtask retains its own assignment, Deliverable and Review. | Grouping must not change approval authority or automatically complete related Tasks. |
| API compatibility | Existing nested Task routes remain canonical; hierarchy can be additive. | Preserve Task.workspace and existing routes; a required Project route would break existing clients. |
| Legacy data and migration | Nullable parent retains existing Tasks as roots; no inferred grouping. | Existing Tasks need nullable Project association; no guessed Project or Client assignment. Client currently lacks the approved Profile tenant FK. |
| AI Smart Task Generator | Can propose a Task/Subtask plan within an authorized Workspace without Project. | Can additionally propose grouping, but requires more metadata, authorization and confirmation rules. |
| Frontend / thesis complexity | Smallest backend and UI surface; hierarchy and review are already substantial. | Adds Project selection, filters, lifecycle and cross-month navigation before they are necessary. |

The conflict in B is its **canonical Workspace ownership**, not the existence
of optional grouping. An optional Workspace → Project UI view alone does not
need to mean that Workspace owns Project in the database.

## 3. Recommended reconciliation: A now, optional B′ later

**Proposal, awaiting Owner decision:** complete A for this task. If Project is
needed later, preserve the accepted Profile/Client ownership through B′:

```text
Profile
├── monthly Workspace → Task → Subtask
└── Client → Project ── optional association ──→ Task
```

Here the Profile derives from canonical tenant relations. Each Task keeps its
required Workspace. One future Project may link Tasks in multiple Workspaces
of the same Profile. A Workspace page can display relevant Projects through
its own Tasks without assigning canonical Project ownership to that Workspace.
No Project relation is added by HT-TASK-P2-05.

This proposal preserves approved ownership rather than asking the Owner to
reapprove the 11 architecture groups. Choosing literal Workspace-owned B
instead would require an explicit amendment of the accepted cross-month
decision; it must not be introduced as an implementation detail.

## 4. Consequences for a future Project implementation

The following are a future design checklist, not approved fields or APIs:

1. Inventory each target database and first establish the approved tenant
   path for existing Client data. Stop for unknown mappings; do not invent a
   Profile or attach legacy Tasks to a synthetic Project.
2. Review an additive Profile/Client-scoped Project design and nullable
   Task-to-Project link. Keep Task.workspace, Task parent scope and existing
   Task/Deliverable/Review keys intact. No mandatory Project backfill.
3. Define Project metadata/lifecycle and authorization in a separate task.
   Existing Workspace membership continues to control Task access. A Project
   association must never expose Tasks in other inaccessible Workspaces.
   Cross-Workspace project summaries require an explicitly reviewed projection
   and permission contract before exposure.
4. Validate same-Profile references in scoped services and transactions;
   review appropriate FKs, indexes and enforceable constraints. A normal
   row CHECK alone cannot prove a related row's tenant identity.
5. Retain accepted soft-delete/controlled-hard-delete direction and protect
   workflow/audit history. Do not introduce retention periods or purge policy.
6. Rehearse additive migrations with empty and representative legacy data on
   isolated PostgreSQL. Any persistent rollout remains a separately approved
   inventory/backup/rehearsal/migration gate.

## 5. AI readiness without an AI implementation

The Task foundation provides a natural plan target: authorized Workspace,
title, description, parent relationship, priority and nullable aware deadline.
Task assignments and individual review history remain execution data, not
permission for an automated generator to write records.

A future generator can propose Requirement → Task/Subtask, suggested priority
and deadline. Human confirmation must precede creation through the normal
authorized services; generated content does not bypass RBAC, tenant checks,
hierarchy depth or review requirements.

`estimated_duration` is **PROPOSED FOR A FUTURE AI/DESIGN TASK**, not a field
added here. Unit, nullability, manual versus suggested value, confidence,
capacity assumptions, provenance and acceptance semantics remain undefined.
No provider, LLM integration, API key, AI endpoint or autonomous database
writer is included. AI readiness does not require a Project aggregate.

## 6. SRS/HLD updates after Owner review

Until Project scope is decided, SRS/HLD should distinguish implemented A from
the approved long-term cross-month Project boundary and this pending proposal.
Add traceability for hierarchy safety, deadline/priority, existing workflow,
tenant authorization and human-confirmed AI planning. Do not draw Project as
a required parent or claim Project API implementation.

If B′ is selected for a future task, SRS/HLD should show Project as a parallel
Profile/Client grouping related to Tasks across monthly Workspaces. If literal
B is selected, record its explicit ownership amendment and consequences first.
Do not revise historical decisions to make either choice appear previously
implemented or approved.

## 7. Owner review gate and genuine open question

Choose the next Project scope after reviewing the Task foundation:

- **Recommended:** retain A for the current delivery and defer Project;
  consider a separately authorized B′ design/implementation when needed.
- Authorize a separate Project task based on B′ while retaining accepted
  Profile/Client ownership and cross-month Tasks.
- Request literal Workspace-owned B, explicitly revisiting the existing
  cross-month ownership decision before any implementation.

Project field details, lifecycle and Project-specific metadata permissions
can be reviewed in that separate task. No answer is required to implement
Subtask/Deadline/Priority safely. **Project remains PENDING OWNER DECISION;
there is no Project model, API or migration in this task.**
