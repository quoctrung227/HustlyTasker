"""Live advisory analysis over request-bound feedback with shared dispatch limits."""

import json
from dataclasses import replace

from django.views.decorators.debug import sensitive_variables

from .contracts import FeedbackSource, Scope, ValidationLimits
from .errors import AIError, ErrorCode
from .feedback_contracts import (
    LIVE_FEEDBACK_INSTRUCTIONS, MAX_MANUAL_FEEDBACK_CHARS, live_feedback_schema, parse_live_feedback,
)
from .feedback_services import _SelectedFeedbackAccess, _focus_text, _scope_id, _selected_sources
from .governance import _execute
from .live_runtime import live_runtime
from .openai_adapter import LiveInput
from .provider_privacy import REDACTED, redact_provider_text
from .providers import Feature, RequestControl
from .validation import _text, validate_feedback_input


_LIMITS = ValidationLimits()


@sensitive_variables()
def analyze_live_feedback(*, actor, profile_id, workspace_id, task_id, sources,
                          idempotency_key, focus="", feedback_text=None):
    if not getattr(actor, "is_authenticated", False) or getattr(actor, "pk", None) is None:
        raise AIError(ErrorCode.PERMISSION_DENIED)
    scope = Scope(_scope_id(actor.pk), _scope_id(profile_id), _scope_id(workspace_id))
    task_id = _scope_id(task_id)
    selected = _selected_sources(sources, allow_empty=True)
    focus = _focus_text(focus)
    if feedback_text is not None:
        _text(feedback_text, field="feedback_text", maximum=MAX_MANUAL_FEEDBACK_CHARS,
              code=ErrorCode.VALIDATION_ERROR, required=True)
    size = len(selected) + (feedback_text is not None)
    if not 1 <= size <= _LIMITS.max_sources:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("sources",))

    access = _SelectedFeedbackAccess(
        actor=actor, scope=scope, task_id=task_id, selected=selected, fixture_only=False,
    )
    access.authorize(scope, Feature.FEEDBACK_ANALYSIS)
    # This gate validates configuration and migrated schema before reading any
    # saved feedback bodies. Authentication and tenant RBAC run first.
    policy, adapter = live_runtime()
    snapshot = access.feedback_sources(scope, task_id)
    raw_sources = snapshot
    if feedback_text is not None:
        raw_sources += (FeedbackSource(f"S{size}", feedback_text, scope.profile_id,
                                       scope.workspace_id, task_id),)
    refs = tuple(source.ref for source in raw_sources)
    validate_feedback_input({"source_refs": list(refs), "focus": focus}, raw_sources, scope, task_id, _LIMITS)
    sanitized = tuple(replace(source, text=redact_provider_text(source.text)) for source in raw_sources)
    if not any(source.text.replace(REDACTED, "").strip() for source in sanitized):
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("sources",))
    data = {"sources": [{"ref": source.ref, "text": source.text} for source in sanitized],
            "focus": redact_provider_text(focus)}
    validate_feedback_input({"source_refs": list(refs), "focus": data["focus"]}, sanitized, scope, task_id, _LIMITS)

    def validate(raw):
        return parse_live_feedback(raw, sanitized, scope, task_id, _LIMITS)

    def revalidate():
        if access.feedback_sources(scope, task_id) != snapshot:
            raise AIError(ErrorCode.STALE_CONTEXT)

    request = LiveInput(
        feature=Feature.FEEDBACK_ANALYSIS, data=data, schema=live_feedback_schema(refs),
        schema_name="hustlytasker_feedback_v2", instructions=LIVE_FEEDBACK_INSTRUCTIONS,
        validate=validate,
    )
    # Raw content is local only. Governance derives an HMAC so replay also
    # detects a change to source text that happens to redact identically.
    canonical = {"task_id": str(task_id), "focus": focus, "manual_feedback": feedback_text,
                 "sources": [{"kind": kind, "id": str(source_id), "text": source.text}
                             for (kind, source_id), source in zip(selected, snapshot)]}
    execution = _execute(
        actor=actor, profile_id=scope.profile_id, workspace_id=scope.workspace_id,
        idempotency_key=idempotency_key, policy=policy, adapter=adapter, request=request,
        canonical_input=canonical, control=RequestControl(), revalidate=revalidate,
    )
    if execution.result is None:
        # The durable dispatch holds cost/replay metadata only. No prior
        # private analysis is retrieved or redispatched with this key.
        raise AIError(ErrorCode.ALREADY_DISPATCHED)
    result = execution.result
    result_sources = [{"ref": source.ref, "kind": kind, "id": str(source_id)}
                      for (kind, source_id), source in zip(selected, snapshot)]
    if feedback_text is not None:
        result_sources.append({"ref": refs[-1], "kind": "manual", "id": None})
    receipt = execution.receipt
    if not receipt.generated_by_ai or result.provider != "openai" or result.usage.status != "provider_reported":
        raise AIError(ErrorCode.INVALID_PROVIDER_RESPONSE)
    response = {
        "contract_version": "ai.v1", "status": "READY", "mode": "openai_live",
        "generated_by_ai": True, "persisted": False, "fixture_version": None,
        "provider": result.provider, "model": result.model,
        "sources": result_sources, "payload": validate(result.raw_json),
        "usage": {"input_tokens": receipt.input_tokens, "billable_output_tokens": receipt.output_tokens,
                  "cost_usd": format(receipt.estimated_cost, ".8f"), "status": result.usage.status},
    }
    if len(json.dumps(response, ensure_ascii=False, allow_nan=False).encode("utf-8")) > _LIMITS.max_response_bytes:
        raise AIError(ErrorCode.INVALID_PROVIDER_RESPONSE)
    return response
