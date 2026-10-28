"""Immutable internal DTOs; fixture limits are not an approved live AI policy.

Scope and FeedbackSource carry data, never authorization. Application boundaries
must resolve and revalidate them through existing tenant/RBAC services.
This module defines no Django model, endpoint, persistence or provider SDK type.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


PRIORITIES = ("LOW", "MEDIUM", "HIGH", "URGENT")
MAX_HIERARCHY_DEPTH = 3
TASK_PLAN_VERSION = "ai.task-plan.v1"
FEEDBACK_VERSION = "ai.feedback.v1"
ISSUE_CATEGORIES = ("CLARITY", "TECHNICAL", "CONTENT", "PROCESS", "OTHER")


@dataclass(frozen=True, slots=True)
class Scope:
    """Correlation identifiers only, not a verified WorkspaceAccessContext."""

    actor_id: UUID = field(repr=False)
    profile_id: UUID = field(repr=False)
    workspace_id: UUID = field(repr=False)

    def __post_init__(self):
        if any(type(value) is not UUID for value in (
            self.actor_id, self.profile_id, self.workspace_id,
        )):
            raise ValueError("Scope identifiers must be UUID values.")


@dataclass(frozen=True, slots=True)
class ValidationLimits:
    """Bounded fixture contract profile, not live rate/budget policy approval."""

    max_brief_chars: int = 6000
    max_source_chars: int = 12000
    max_tasks: int = 20
    max_sources: int = 20
    max_response_bytes: int = 65536
    max_request_bytes: int = 32768
    max_depth: int = MAX_HIERARCHY_DEPTH

    def __post_init__(self):
        ceilings = {
            "max_brief_chars": 6000, "max_source_chars": 12000,
            "max_tasks": 20, "max_sources": 20,
            "max_response_bytes": 65536, "max_request_bytes": 32768,
        }
        for name, ceiling in ceilings.items():
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError("Invalid fixture validation limits.")
        if type(self.max_depth) is not int or not 0 <= self.max_depth <= MAX_HIERARCHY_DEPTH:
            raise ValueError("Invalid fixture hierarchy limit.")


@dataclass(frozen=True, slots=True)
class GeneratorInput:
    brief: str = field(repr=False)
    target_deadline: datetime | None = None
    reference_time: datetime | None = None
    timezone_name: str | None = None


@dataclass(frozen=True, slots=True)
class FeedbackSource:
    ref: str
    text: str = field(repr=False)
    profile_id: UUID = field(repr=False)
    workspace_id: UUID = field(repr=False)
    task_id: UUID = field(repr=False)
    deleted: bool = False


@dataclass(frozen=True, slots=True)
class FeedbackInput:
    sources: tuple[FeedbackSource, ...] = field(repr=False)
    focus: str = field(default="", repr=False)

    @property
    def source_refs(self):
        return tuple(source.ref for source in self.sources)


@dataclass(frozen=True, slots=True)
class TaskNode:
    local_ref: str
    parent_ref: str | None
    title: str = field(repr=False)
    description: str = field(repr=False)
    priority: str
    proposed_deadline: datetime | None
    notes: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class TaskPlan:
    contract_version: str
    tasks: tuple[TaskNode, ...] = field(repr=False)
    assumptions: tuple[str, ...] = field(repr=False)
    warnings: tuple[str, ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class FeedbackIssue:
    category: str
    description: str = field(repr=False)
    source_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SuggestedAction:
    action: str = field(repr=False)
    priority: str
    rationale: str = field(repr=False)
    source_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FeedbackAnalysis:
    contract_version: str
    summary: str = field(repr=False)
    issues: tuple[FeedbackIssue, ...] = field(repr=False)
    suggested_actions: tuple[SuggestedAction, ...] = field(repr=False)
    uncertainty: str = field(repr=False)
    warnings: tuple[str, ...] = field(repr=False)
