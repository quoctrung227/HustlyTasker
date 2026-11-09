"""Stateless, current-tenant feedback fixtures; never a domain mutation service."""

import json
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db.models.functions import Substr
from django.views.decorators.debug import sensitive_variables

from apps.reviews.models import Review
from apps.tasks.access import resolve_task_in_scope, tasks_visible_to
from apps.tasks.models import TaskComment
from apps.workspace.access import (
    TenantAccessNotFound,
    can_manage_workspace_tasks,
    resolve_profile_access_context,
    resolve_workspace_access_context,
)

from .contracts import FeedbackAnalysis, FeedbackSource, Scope, ValidationLimits
from .durable_services import _enabled
from .errors import AIError, ErrorCode
from .providers import Feature
from .services import FixtureApplicationService


_LIMITS = ValidationLimits()
User = get_user_model()


def _scope_id(value):
    try:
        if type(value) is UUID:
            return value
        if type(value) is not str or len(value) > 64:
            raise ValueError()
        return UUID(value)
    except (TypeError, ValueError, AttributeError):
        raise AIError(ErrorCode.NOT_FOUND) from None


@sensitive_variables()
def _selected_sources(value):
    if type(value) is not list or not 1 <= len(value) <= _LIMITS.max_sources:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("sources",))
    selected = []
    seen = set()
    for item in value:
        if (type(item) is not dict or set(item) != {"kind", "id"}
                or type(item["kind"]) is not str
                or item["kind"] not in ("review", "comment")
                or type(item["id"]) is not str or len(item["id"]) > 64):
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("sources",))
        try:
            source_id = UUID(item["id"])
        except (TypeError, ValueError, AttributeError):
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("sources",)) from None
        pair = (item["kind"], source_id)
        if pair in seen:
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("sources",))
        seen.add(pair)
        selected.append(pair)
    return tuple(selected)


@sensitive_variables()
def _focus_text(value):
    if type(value) is not str or len(value) > 1000 or "\x00" in value:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("focus",))
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("focus",)) from None
    return value


class _SelectedFeedbackAccess:
    """Request-bound selector, not a replacement for current tenant predicates."""

    def __init__(self, *, actor, scope, task_id, selected):
        self.actor = actor
        self.scope = scope
        self.task_id = task_id
        self.selected = selected
        self._resolved_sources = False

    def _resolve(self, scope, feature):
        _enabled()
        if (scope != self.scope or feature is not Feature.FEEDBACK_ANALYSIS
                or not getattr(self.actor, "is_authenticated", False)
                or getattr(self.actor, "pk", None) != scope.actor_id
                or not User.objects.filter(pk=scope.actor_id, is_active=True).exists()):
            raise AIError(ErrorCode.PERMISSION_DENIED)
        try:
            profile = resolve_profile_access_context(self.actor, scope.profile_id)
            context = resolve_workspace_access_context(profile, scope.workspace_id)
            task = resolve_task_in_scope(context, self.task_id)
        except TenantAccessNotFound:
            raise AIError(ErrorCode.NOT_FOUND) from None
        if not can_manage_workspace_tasks(context):
            raise AIError(ErrorCode.PERMISSION_DENIED)
        return context, task

    def authorize(self, scope, feature):
        self._resolve(scope, feature)

    @sensitive_variables()
    def feedback_sources(self, scope, task_id):
        if task_id != self.task_id:
            raise AIError(ErrorCode.NOT_FOUND)
        context, task = self._resolve(scope, Feature.FEEDBACK_ANALYSIS)
        # Repeat current membership predicates in the SQL scope, not merely a
        # client-provided Task UUID or an earlier request context snapshot.
        try:
            visible_tasks = tasks_visible_to(context).filter(pk=task.pk).values("pk")
        except TenantAccessNotFound:
            raise AIError(ErrorCode.NOT_FOUND) from None
        review_ids = [source_id for kind, source_id in self.selected if kind == "review"]
        comment_ids = [source_id for kind, source_id in self.selected if kind == "comment"]
        reviews = dict(Review.objects.filter(
            pk__in=review_ids, deliverable__task_id__in=visible_tasks,
        ).annotate(_feedback_text=Substr("comment", 1, _LIMITS.max_source_chars + 1))
            .values_list("pk", "_feedback_text")) if review_ids else {}
        comments = dict(TaskComment.objects.filter(
            pk__in=comment_ids, task_id__in=visible_tasks, deleted_at__isnull=True,
        ).annotate(_feedback_text=Substr("content", 1, _LIMITS.max_source_chars + 1))
            .values_list("pk", "_feedback_text")) if comment_ids else {}
        sources = []
        for index, (kind, source_id) in enumerate(self.selected, start=1):
            text = (reviews if kind == "review" else comments).get(source_id)
            if type(text) is not str or not text.strip():
                code = ErrorCode.STALE_CONTEXT if self._resolved_sources else ErrorCode.NOT_FOUND
                raise AIError(code)
            sources.append(FeedbackSource(
                ref=f"S{index}", text=text, profile_id=scope.profile_id,
                workspace_id=scope.workspace_id, task_id=task.pk,
            ))
        self._resolved_sources = True
        return tuple(sources)


@sensitive_variables()
def _analysis_payload(value):
    if type(value) is not FeedbackAnalysis:
        raise AIError(ErrorCode.INVALID_PROVIDER_RESPONSE)
    return {
        "contract_version": value.contract_version,
        "summary": value.summary,
        "issues": [{
            "category": issue.category, "description": issue.description,
            "source_refs": list(issue.source_refs),
        } for issue in value.issues],
        "suggested_actions": [{
            "action": action.action, "priority": action.priority,
            "rationale": action.rationale, "source_refs": list(action.source_refs),
        } for action in value.suggested_actions],
        "uncertainty": value.uncertainty,
        "warnings": list(value.warnings),
    }


@sensitive_variables()
def analyze_feedback(*, actor, profile_id, workspace_id, task_id, sources, focus=""):
    """Return one offline advisory result; write no business, AI or audit rows.

    Input IDs are resolved from current access twice by the existing fixture
    application service. There is no persistence, replay cache or confirmation.
    """
    _enabled()
    if not getattr(actor, "is_authenticated", False) or getattr(actor, "pk", None) is None:
        raise AIError(ErrorCode.PERMISSION_DENIED)
    scope = Scope(_scope_id(actor.pk), _scope_id(profile_id), _scope_id(workspace_id))
    selected = _selected_sources(sources)
    focus = _focus_text(focus)
    task_id = _scope_id(task_id)
    access = _SelectedFeedbackAccess(actor=actor, scope=scope, task_id=task_id, selected=selected)
    outcome = FixtureApplicationService(
        environment="development", enabled=True, access=access, limits=_LIMITS,
    ).analyze(
        scope=scope, task_id=task_id,
        payload={"source_refs": [f"S{index}" for index in range(1, len(selected) + 1)], "focus": focus},
    )
    try:
        response = {
            "contract_version": "ai.v1", "status": "READY", "mode": outcome.mode,
            "generated_by_ai": outcome.generated_by_ai, "persisted": outcome.persisted,
            "fixture_version": outcome.fixture_version,
            "sources": [{"ref": f"S{index}", "kind": kind, "id": str(source_id)}
                        for index, (kind, source_id) in enumerate(selected, start=1)],
            "payload": _analysis_payload(outcome.payload),
            "usage": {"input_tokens": outcome.usage.input_tokens,
                      "billable_output_tokens": outcome.usage.billable_output_tokens,
                      "cost_usd": format(outcome.usage.cost_usd, ".6f"),
                      "status": outcome.usage.status},
        }
        encoded = json.dumps(response, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > _LIMITS.max_response_bytes:
            raise ValueError()
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
        raise AIError(ErrorCode.INVALID_PROVIDER_RESPONSE) from None
    return response
