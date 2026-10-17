# HustlyTasker Agent Working Agreement

This file applies to the entire repository. Any coding agent working on
HustlyTasker must follow it together with the user's current instructions.

## Start every task from repository evidence

Before changing code:

1. Read this file and `documentation/HANDOVER.md`.
2. Read the current sections of `documentation/PROGRESS.md`,
   `documentation/PROJECT_ROADMAP.md`, and the documentation relevant to the
   requested domain.
3. Run `git status --short` and inspect the relevant diff. Treat every
   pre-existing modified or untracked file as user work that must be
   preserved.
4. Inspect the current source, migrations, routes, settings, and tests that
   govern the requested behavior. Documentation and prior chat messages are
   not substitutes for source evidence.
5. Identify the active task, its acceptance criteria, dependencies, and review
   gate. Do not redo completed work or silently move to another roadmap task.

## Architecture and scope rules

- Preserve the current Django + Django REST Framework + PostgreSQL modular
  architecture unless the owner explicitly approves a change.
- Follow the backend-first roadmap. Do not start frontend, Workspace/RBAC, or
  another business domain merely because it is adjacent to the active task.
- Do not invent business rules, fields, roles, status transitions, ownership,
  or tenant boundaries. Record unresolved product decisions for owner review.
- Do not change models or create/edit migrations unless the approved task
  explicitly includes schema work and the design/backfill plan has been
  reviewed. Never rewrite an applied migration to avoid a new migration.
- Never write secrets, credentials, real tokens, or private environment values
  to source, examples, tests, logs, or documentation.
- Do not delete data, reset the database, discard local changes, rewrite Git
  history, commit, or push unless the owner explicitly requests it.

## Implementation and verification

- Make the smallest change that satisfies the approved acceptance criteria.
- Keep public API access explicit. DRF is authenticated by default; every
  `AllowAny` endpoint must be intentional, documented, and tested.
- Add or update tests for changed behavior and relevant regressions.
- Run checks proportional to the change. For backend tasks this normally
  includes `manage.py check`, relevant tests, the full suite when practical,
  and migration consistency checks when models or settings are involved.
- Do not mark a task `COMPLETE` until its acceptance criteria pass with current
  evidence. Use `IN PROGRESS`, `BLOCKED`, or `DESIGN READY — PENDING APPROVAL`
  when that is the truthful state.

## Documentation and checkpoints

Documentation must describe the repository as it actually exists. Update only
the files affected by the task:

- `documentation/PROGRESS.md`: current checkpoint, completed work, validation,
  remaining work, and review gate.
- `documentation/CHANGELOG.md`: material implementation or behavior changes.
- `documentation/PROJECT_ROADMAP.md` and
  `documentation/REQUIREMENT_STATUS.md`: task/requirement status changes.
- `documentation/API_DOCUMENTATION.md`: API contracts, access rules, methods,
  request/response behavior, and security boundaries.
- `documentation/DATABASE_SCHEMA.md`: approved model/schema changes or an
  explicitly labeled proposed schema design.
- `documentation/DECISION_LOG.md`: accepted decisions and clearly labeled
  proposals that still require approval.
- `documentation/PROJECT_CONTEXT.md`: only durable project-level context.
- `documentation/HANDOVER.md`: always refresh the latest handover checkpoint.

For a long task, create a documentation checkpoint after each coherent,
verified portion. A checkpoint must state what is done, what is still pending,
which files are dirty, the last tests run, and the exact safe continuation
step. Do not claim unrun checks as passing.

When pausing or completing any task, leave `HANDOVER.md` sufficient for a new
developer or a new Codex session to continue without relying on chat history.
Keep historical notes clearly labeled so they cannot be mistaken for current
instructions.
