"""Durable offline dispatch governance; never a live provider activation path.

Every callable gates before touching candidate tables. Budget buckets are stable,
cumulative lifetime lanes: no midnight rollover can discard an unresolved hold.
All monetary accounting here is simulated exposure, never an actual invoice.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from uuid import UUID, uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.debug import sensitive_variables

from apps.workspace.access import TenantAccessNotFound

from .contracts import Scope, ValidationLimits
from .durable_services import _enabled as _fixture_enabled, _key_digest, _manager
from .errors import AIError, ErrorCode
from .feedback_services import _SelectedFeedbackAccess, _focus_text, _scope_id, _selected_sources
from .models import AiBudgetBucket, AiDispatch, AiDispatchReservation
from .openai_adapter import OpenAIResponsesAdapter
from .providers import Feature, ProviderRequest, ProviderResult, RequestControl, UsageMetadata
from .validation import validate_feedback_input, validate_generator_input


_QUANTUM = Decimal("0.00000001")
_MAX_MONEY = Decimal("999999999999.99999999")
_MILLION = Decimal("1000000")
_PURPOSE = "hustlytasker.ai.governance.body.v1"
_EVIDENCE_PURPOSE = "hustlytasker.ai.governance.settlement.v1"
_POLICY_PURPOSE = "hustlytasker.ai.governance.policy.v1"
_VERSION = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}\Z")
_MODEL = re.compile(r"[a-z0-9][a-z0-9._-]{0,99}\Z")
_LIMITS = ValidationLimits()


def _fail(code=ErrorCode.VALIDATION_ERROR):
    raise AIError(code) from None


def _amount(value):
    if type(value) not in (Decimal, str, int) or type(value) is bool:
        _fail()
    try:
        result = Decimal(value)
        if (not result.is_finite() or not 0 <= result <= _MAX_MONEY
                or result.quantize(_QUANTUM) != result):
            _fail()
    except (InvalidOperation, ValueError, OverflowError):
        _fail()
    return result.quantize(_QUANTUM)


def _count(value, maximum=1000000000):
    if type(value) is not int or not 0 <= value <= maximum:
        _fail()
    return value


@dataclass(frozen=True, slots=True)
class BudgetLimits:
    cost_limit: Decimal = Decimal("0")
    request_limit: int = 0
    concurrency_limit: int = 0

    def __post_init__(self):
        object.__setattr__(self, "cost_limit", _amount(self.cost_limit))
        _count(self.request_limit)
        _count(self.concurrency_limit)


@dataclass(frozen=True, slots=True)
class GovernancePolicy:
    """Trusted server-code configuration, never accepted from a public request."""

    enabled: bool = False
    provider: str = "openai"
    model: str = "gpt-5.4-mini"
    execution_mode: str = "OPENAI_OFFLINE"
    config_version: str = "offline-v1"
    pricing_version: str = "synthetic-v1"
    budget_version: str = "offline-budget-v1"
    max_input_tokens: int = 65536
    max_output_tokens: int = 4096
    input_rate_per_million: Decimal = Decimal("1")
    output_rate_per_million: Decimal = Decimal("1")
    lease_seconds: int = 300
    global_limits: BudgetLimits = field(default_factory=BudgetLimits)
    profile_limits: BudgetLimits = field(default_factory=BudgetLimits)
    user_limits: BudgetLimits = field(default_factory=BudgetLimits)

    def __post_init__(self):
        if (type(self.enabled) is not bool or self.provider != "openai"
                or type(self.model) is not str or not _MODEL.fullmatch(self.model)):
            _fail()
        for value in (self.config_version, self.pricing_version, self.budget_version):
            if type(value) is not str or not _VERSION.fullmatch(value):
                _fail()
        if type(self.execution_mode) is not str:
            _fail()
        for value in (self.max_input_tokens, self.max_output_tokens):
            if not _count(value, 1000000):
                _fail()
        if type(self.lease_seconds) is not int or not 1 <= self.lease_seconds <= 3600:
            _fail()
        for name in ("input_rate_per_million", "output_rate_per_million"):
            object.__setattr__(self, name, _amount(getattr(self, name)))
        if any(type(value) is not BudgetLimits for value in (
                self.global_limits, self.profile_limits, self.user_limits)):
            _fail()


@dataclass(frozen=True, slots=True)
class DispatchReceipt:
    dispatch_id: UUID
    status: str
    provider: str
    model: str
    execution_mode: str
    usage_status: str
    reserved_amount: Decimal
    estimated_cost: Decimal | None
    billed_cost: Decimal | None
    accounted_amount: Decimal | None
    input_tokens: int | None
    output_tokens: int | None
    created: bool = False
    claimed: bool = False
    generated_by_ai: bool = False


@dataclass(frozen=True, slots=True)
class DispatchExecution:
    receipt: DispatchReceipt
    result: ProviderResult | None = field(default=None, repr=False)


def _gate(policy):
    if (type(policy) is not GovernancePolicy or policy.enabled is not True
            or getattr(settings, "AI_GOVERNANCE_ENABLED", False) is not True
            or policy.execution_mode != AiDispatch.ExecutionMode.OPENAI_OFFLINE):
        _fail(ErrorCode.AI_DISABLED)
    _fixture_enabled()


def _outside_business_transaction():
    if any(not getattr(block, "_from_testcase", False)
           for block in transaction.get_connection().atomic_blocks):
        _fail()


def _workspace(actor, profile_id, workspace_id):
    try:
        return _manager(actor=actor, profile_id=profile_id, workspace_id=workspace_id)
    except PermissionDenied:
        _fail(ErrorCode.PERMISSION_DENIED)
    except (TenantAccessNotFound, TypeError, ValueError, ValidationError):
        _fail(ErrorCode.NOT_FOUND)


@sensitive_variables("value", "encoded")
def _canonical(value):
    if type(value) is not dict:
        _fail()
    try:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 131072:
            _fail()
        return encoded
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        _fail()


@sensitive_variables("value", "key")
def _hmac(value, *, purpose=_PURPOSE, key=None):
    return salted_hmac(purpose, value, secret=key, algorithm="sha256").hexdigest()


@sensitive_variables("value", "key")
def _matches(digest, value, purpose=_PURPOSE):
    return any(constant_time_compare(digest, _hmac(value, purpose=purpose, key=key))
               for key in (settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS))


def _cost(policy, inputs, outputs):
    try:
        value = ((Decimal(inputs) * policy.input_rate_per_million
                  + Decimal(outputs) * policy.output_rate_per_million) / _MILLION)
        return _amount(value.quantize(_QUANTUM, rounding=ROUND_CEILING))
    except (InvalidOperation, ValueError, OverflowError):
        _fail()


def _policy_canonical(policy):
    return _canonical({
        "contract_version": "ai.governance.v1", "provider": policy.provider,
        "model": policy.model, "execution_mode": policy.execution_mode,
        "config_version": policy.config_version, "pricing_version": policy.pricing_version,
        "max_input_tokens": policy.max_input_tokens, "max_output_tokens": policy.max_output_tokens,
        "input_rate": str(policy.input_rate_per_million),
        "output_rate": str(policy.output_rate_per_million),
    })


def _bucket_specs(actor, workspace, policy):
    return (
        (AiBudgetBucket.Scope.GLOBAL, None, None, policy.global_limits),
        (AiBudgetBucket.Scope.PROFILE, workspace.profile_id, None, policy.profile_limits),
        (AiBudgetBucket.Scope.USER, None, actor.pk, policy.user_limits),
    )


def _buckets(actor, workspace, policy):
    """Call under tenant locks: GLOBAL→PROFILE→USER, never period/model split."""
    rows = []
    for scope, profile_id, user_id, limits in _bucket_specs(actor, workspace, policy):
        query = dict(scope=scope, execution_mode=policy.execution_mode,
                     profile_id=profile_id, user_id=user_id)
        row, _ = AiBudgetBucket.objects.get_or_create(**query, defaults={
            "policy_version": policy.budget_version, "cost_limit": limits.cost_limit,
            "request_limit": limits.request_limit, "concurrency_limit": limits.concurrency_limit,
        })
        row = AiBudgetBucket.objects.select_for_update().get(pk=row.pk)
        if (row.policy_version != policy.budget_version or row.cost_limit != limits.cost_limit
                or row.request_limit != limits.request_limit
                or row.concurrency_limit != limits.concurrency_limit):
            _fail()
        rows.append(row)
    return rows


def _row(actor, workspace, dispatch_id, policy):
    try:
        value = AiDispatch.objects.select_for_update().filter(
            pk=dispatch_id, actor_id=actor.pk, profile_id=workspace.profile_id,
            workspace_id=workspace.pk, execution_mode=policy.execution_mode,
        ).first()
    except (ValueError, TypeError, ValidationError):
        _fail(ErrorCode.NOT_FOUND)
    if value is None:
        _fail(ErrorCode.NOT_FOUND)
    if (value.provider != policy.provider or value.model != policy.model
            or value.config_version != policy.config_version
            or value.pricing_version != policy.pricing_version
            or value.input_token_limit != policy.max_input_tokens
            or value.output_token_limit != policy.max_output_tokens
            or not _matches(value.policy_digest, _policy_canonical(policy), _POLICY_PURPOSE)
            or value.reserved_amount != _cost(policy, policy.max_input_tokens, policy.max_output_tokens)):
        _fail(ErrorCode.STALE_CONTEXT)
    return value


def _receipt(row, *, created=False, claimed=False):
    return DispatchReceipt(
        dispatch_id=row.pk, status=row.status, provider=row.provider, model=row.model,
        execution_mode=row.execution_mode, usage_status=row.usage_status,
        reserved_amount=row.reserved_amount, estimated_cost=row.estimated_cost,
        billed_cost=row.billed_cost, accounted_amount=row.accounted_amount,
        input_tokens=row.input_tokens, output_tokens=row.output_tokens,
        created=created, claimed=claimed,
    )


def _locked(actor, profile_id, workspace_id, dispatch_id, policy):
    workspace = _workspace(actor, profile_id, workspace_id)
    buckets = _buckets(actor, workspace, policy)
    row = _row(actor, workspace, dispatch_id, policy)
    return row, buckets


@sensitive_variables("canonical_input", "canonical", "body")
def reserve_dispatch(*, actor, profile_id, workspace_id, feature, idempotency_key,
                     canonical_input, policy):
    _gate(policy)
    _outside_business_transaction()
    if not isinstance(feature, Feature):
        _fail()
    key_digest = _key_digest(idempotency_key)
    if type(canonical_input) is not dict:
        _fail()
    body = {
        "contract_version": "ai.governance.v1", "provider": policy.provider,
        "model": policy.model, "execution_mode": policy.execution_mode,
        "config_version": policy.config_version, "pricing_version": policy.pricing_version,
        "feature": feature.value, "input_token_limit": policy.max_input_tokens,
        "output_token_limit": policy.max_output_tokens,
        "input_rate": str(policy.input_rate_per_million),
        "output_rate": str(policy.output_rate_per_million), "input": canonical_input,
    }
    reservation = _cost(policy, policy.max_input_tokens, policy.max_output_tokens)
    with transaction.atomic():
        workspace = _workspace(actor, profile_id, workspace_id)
        canonical = _canonical(body | {"scope": {
            "actor_id": str(actor.pk), "profile_id": str(workspace.profile_id),
            "workspace_id": str(workspace.pk),
        }})
        buckets = _buckets(actor, workspace, policy)
        row = AiDispatch.objects.select_for_update().filter(
            actor=actor, profile_id=workspace.profile_id, workspace=workspace,
            feature=feature.value, execution_mode=policy.execution_mode, key_digest=key_digest,
        ).first()
        if row:
            if not _matches(row.body_digest, canonical):
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT)
            return _receipt(row)
        for bucket in buckets:
            if (bucket.request_count >= bucket.request_limit
                    or bucket.active_count >= bucket.concurrency_limit
                    or bucket.reserved_amount + bucket.accounted_amount + reservation > bucket.cost_limit):
                _fail(ErrorCode.BUDGET_EXCEEDED)
        now = timezone.now()
        row = AiDispatch.objects.create(
            actor=actor, profile_id=workspace.profile_id, workspace=workspace,
            feature=feature.value, provider=policy.provider, model=policy.model,
            execution_mode=policy.execution_mode, config_version=policy.config_version,
            pricing_version=policy.pricing_version, key_digest=key_digest,
            body_digest=_hmac(canonical), reserved_amount=reservation,
            policy_digest=_hmac(_policy_canonical(policy), purpose=_POLICY_PURPOSE),
            input_token_limit=policy.max_input_tokens, output_token_limit=policy.max_output_tokens,
            lease_expires_at=now + timedelta(seconds=policy.lease_seconds),
        )
        for bucket in buckets:
            bucket.request_count += 1
            bucket.active_count += 1
            bucket.reserved_amount += reservation
            bucket.save(update_fields=("request_count", "active_count", "reserved_amount"))
            AiDispatchReservation.objects.create(dispatch=row, bucket=bucket, amount=reservation)
        return _receipt(row, created=True)


def get_dispatch(*, actor, profile_id, workspace_id, dispatch_id, policy):
    _gate(policy)
    with transaction.atomic():
        row, _ = _locked(actor, profile_id, workspace_id, dispatch_id, policy)
        return _receipt(row)


def begin_dispatch(*, actor, profile_id, workspace_id, dispatch_id, policy):
    _gate(policy)
    _outside_business_transaction()
    with transaction.atomic():
        row, _ = _locked(actor, profile_id, workspace_id, dispatch_id, policy)
        if row.status != AiDispatch.Status.RESERVED:
            return _receipt(row)
        if row.lease_expires_at <= timezone.now():
            _fail(ErrorCode.EXPIRED)
        row.status = AiDispatch.Status.DISPATCHING
        row.dispatched_at = timezone.now()
        row.claim_id = uuid4()
        row.save(update_fields=("status", "dispatched_at", "claim_id"))
        return _receipt(row, claimed=True)


def _finish_reservations(row, buckets, amount, *, released=False):
    links = {link.bucket_id: link for link in AiDispatchReservation.objects.select_for_update().filter(dispatch=row)}
    if set(links) != {bucket.pk for bucket in buckets}:
        _fail(ErrorCode.STALE_CONTEXT)
    for bucket in buckets:
        link = links[bucket.pk]
        if link.status != AiDispatchReservation.Status.HELD or link.amount != row.reserved_amount:
            _fail(ErrorCode.STALE_CONTEXT)
        bucket.reserved_amount -= link.amount
        bucket.active_count -= 1
        bucket.accounted_amount += amount
        bucket.save(update_fields=("reserved_amount", "active_count", "accounted_amount"))
        link.status = (AiDispatchReservation.Status.RELEASED if released
                       else AiDispatchReservation.Status.SETTLED)
        link.settled_amount = amount
        link.save(update_fields=("status", "settled_amount"))


def _safe_error(code):
    return code.value if isinstance(code, ErrorCode) else ErrorCode.PROVIDER_UNAVAILABLE.value


def fail_before_dispatch(*, actor, profile_id, workspace_id, dispatch_id, policy,
                         error_code=ErrorCode.PROVIDER_UNAVAILABLE):
    _gate(policy)
    _outside_business_transaction()
    with transaction.atomic():
        row, buckets = _locked(actor, profile_id, workspace_id, dispatch_id, policy)
        if row.status == AiDispatch.Status.FAILED_BEFORE_DISPATCH:
            return _receipt(row)
        if row.status != AiDispatch.Status.RESERVED:
            _fail(ErrorCode.STALE_CONTEXT)
        _finish_reservations(row, buckets, Decimal("0"), released=True)
        row.status = AiDispatch.Status.FAILED_BEFORE_DISPATCH
        row.completed_at = timezone.now()
        row.accounted_amount = Decimal("0")
        row.error_code = _safe_error(error_code)
        row.save(update_fields=("status", "completed_at", "accounted_amount", "error_code"))
        return _receipt(row)


def mark_unknown(*, actor, profile_id, workspace_id, dispatch_id, policy,
                 error_code=ErrorCode.PROVIDER_UNAVAILABLE):
    _gate(policy)
    _outside_business_transaction()
    with transaction.atomic():
        row, _ = _locked(actor, profile_id, workspace_id, dispatch_id, policy)
        if row.status == AiDispatch.Status.OUTCOME_UNKNOWN:
            return _receipt(row)
        if row.status != AiDispatch.Status.DISPATCHING:
            _fail(ErrorCode.STALE_CONTEXT)
        row.status = AiDispatch.Status.OUTCOME_UNKNOWN
        row.error_code = _safe_error(error_code)
        row.save(update_fields=("status", "error_code"))
        return _receipt(row)


def _usage(policy, result):
    accepted_models = {policy.model}
    if policy.model == "gpt-5.4-mini":
        accepted_models.add("gpt-5.4-mini-2026-03-17")
    if (type(result) is not ProviderResult or result.provider != "openai_offline"
            or result.model not in accepted_models
            or type(result.usage) is not UsageMetadata
            or result.usage.status != "offline_simulated" or result.usage.cost_usd is not None):
        _fail(ErrorCode.INVALID_PROVIDER_RESPONSE)
    inputs, outputs = result.usage.input_tokens, result.usage.billable_output_tokens
    if (inputs is None or outputs is None or type(inputs) is not int or type(outputs) is not int
            or not 0 <= inputs <= policy.max_input_tokens
            or not 0 <= outputs <= policy.max_output_tokens):
        _fail(ErrorCode.INVALID_PROVIDER_RESPONSE)
    return inputs, outputs, _cost(policy, inputs, outputs)


@sensitive_variables("result")
def _settle_success(*, actor, profile_id, workspace_id, dispatch_id, policy, result):
    _gate(policy)
    _outside_business_transaction()
    inputs, outputs, cost = _usage(policy, result)
    with transaction.atomic():
        row, buckets = _locked(actor, profile_id, workspace_id, dispatch_id, policy)
        if row.status != AiDispatch.Status.DISPATCHING or cost > row.reserved_amount:
            _fail(ErrorCode.STALE_CONTEXT)
        _finish_reservations(row, buckets, cost)
        row.status = AiDispatch.Status.SUCCEEDED
        row.completed_at = timezone.now()
        row.usage_status = AiDispatch.UsageStatus.SIMULATED
        row.input_tokens, row.output_tokens = inputs, outputs
        row.estimated_cost = row.accounted_amount = cost
        row.save(update_fields=("status", "completed_at", "usage_status", "input_tokens",
                                "output_tokens", "estimated_cost", "accounted_amount"))
        return _receipt(row)


@sensitive_variables("evidence", "canonical")
def reconcile_dispatch(*, actor, profile_id, workspace_id, dispatch_id, policy,
                       accounted_amount, evidence, input_tokens=None, output_tokens=None):
    _gate(policy)
    _outside_business_transaction()
    amount = _amount(accounted_amount)
    if (input_tokens is None) != (output_tokens is None):
        _fail()
    if type(evidence) is not str or not evidence.strip() or len(evidence) > 300 or "\x00" in evidence:
        _fail()
    for value in (input_tokens, output_tokens):
        if value is not None:
            _count(value)
    with transaction.atomic():
        row, buckets = _locked(actor, profile_id, workspace_id, dispatch_id, policy)
        canonical = _canonical({"dispatch_id": str(row.pk), "actor_id": str(row.actor_id),
                                "profile_id": str(row.profile_id), "workspace_id": str(row.workspace_id),
                                "amount": str(amount), "evidence": evidence,
                                "input_tokens": input_tokens, "output_tokens": output_tokens})
        if row.status == AiDispatch.Status.RECONCILED:
            if not _matches(row.settlement_digest, canonical, _EVIDENCE_PURPOSE):
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT)
            return _receipt(row)
        if (row.status != AiDispatch.Status.OUTCOME_UNKNOWN or amount > row.reserved_amount
                or (input_tokens is not None and input_tokens > row.input_token_limit)
                or (output_tokens is not None and output_tokens > row.output_token_limit)):
            _fail(ErrorCode.STALE_CONTEXT)
        _finish_reservations(row, buckets, amount)
        row.status = AiDispatch.Status.RECONCILED
        row.completed_at = row.reconciled_at = timezone.now()
        row.usage_status = AiDispatch.UsageStatus.SIMULATED
        row.input_tokens, row.output_tokens = input_tokens, output_tokens
        row.estimated_cost = row.accounted_amount = amount
        row.settlement_digest = _hmac(canonical, purpose=_EVIDENCE_PURPOSE)
        row.save(update_fields=("status", "completed_at", "reconciled_at", "usage_status",
                                "input_tokens", "output_tokens", "estimated_cost",
                                "accounted_amount", "settlement_digest"))
        return _receipt(row)


def _adapter(adapter, policy):
    if (type(adapter) is not OpenAIResponsesAdapter or not adapter._config.enabled
            or adapter._config.model != policy.model
            or adapter._config.max_output_tokens > policy.max_output_tokens
            or adapter._transport is None
            or getattr(adapter._transport, "offline", None) is not True):
        _fail(ErrorCode.AI_DISABLED)


def _unknown_safely(context, code):
    try:
        mark_unknown(**context, error_code=code)
    except Exception:
        # If access or database availability changed, durable DISPATCHING itself
        # remains uncertainty and keeps every hold. Never imply rollback/refund.
        pass


@sensitive_variables()
def _execute(*, actor, profile_id, workspace_id, idempotency_key, policy,
             adapter, request, canonical_input, control, revalidate=None):
    _gate(policy)
    _outside_business_transaction()
    _adapter(adapter, policy)
    if type(control) is not RequestControl:
        _fail()
    control.check()
    reserved = reserve_dispatch(actor=actor, profile_id=profile_id, workspace_id=workspace_id,
                                idempotency_key=idempotency_key, feature=request.feature,
                                canonical_input=canonical_input, policy=policy)
    if not reserved.created:
        return DispatchExecution(reserved)
    context = dict(actor=actor, profile_id=profile_id, workspace_id=workspace_id,
                   dispatch_id=reserved.dispatch_id, policy=policy)
    try:
        control.check()
        if revalidate is not None:
            revalidate()
    except Exception:
        try:
            fail_before_dispatch(**context)
        except Exception:
            pass  # RESERVED is retained; no call can occur without begin_dispatch.
        raise
    claimed = begin_dispatch(**context)
    if not claimed.claimed:
        return DispatchExecution(claimed)
    try:
        result = adapter.generate(request, control)
        control.check()
        if revalidate is not None:
            revalidate()
        settled = _settle_success(**context, result=result)
        return DispatchExecution(settled, result)
    except AIError as error:
        _unknown_safely(context, error.code)
        raise
    except Exception:
        _unknown_safely(context, ErrorCode.PROVIDER_UNAVAILABLE)
        raise AIError(ErrorCode.PROVIDER_UNAVAILABLE) from None


@sensitive_variables("brief", "validated", "request")
def execute_generator(*, actor, profile_id, workspace_id, brief, idempotency_key,
                      adapter, policy, control=None):
    _gate(policy)
    validated = validate_generator_input({"brief": brief}, _LIMITS)
    request = ProviderRequest(Feature.TASK_PLAN, validated, _LIMITS)
    return _execute(actor=actor, profile_id=profile_id, workspace_id=workspace_id,
                    idempotency_key=idempotency_key, policy=policy, adapter=adapter,
                    request=request, canonical_input={"brief": validated.brief},
                    control=control if control is not None else RequestControl())


@sensitive_variables("sources", "focus", "snapshot", "request", "canonical")
def execute_feedback(*, actor, profile_id, workspace_id, task_id, sources, focus="",
                     idempotency_key, adapter, policy, control=None):
    _gate(policy)
    _outside_business_transaction()
    if not getattr(actor, "is_authenticated", False) or getattr(actor, "pk", None) is None:
        _fail(ErrorCode.PERMISSION_DENIED)
    selected = _selected_sources(sources)
    scope = Scope(_scope_id(actor.pk), _scope_id(profile_id), _scope_id(workspace_id))
    task_id = _scope_id(task_id)
    focus = _focus_text(focus)
    access = _SelectedFeedbackAccess(actor=actor, scope=scope, task_id=task_id, selected=selected)
    access.authorize(scope, Feature.FEEDBACK_ANALYSIS)
    snapshot = access.feedback_sources(scope, task_id)
    validated = validate_feedback_input({"source_refs": [item.ref for item in snapshot], "focus": focus},
                                        snapshot, scope, task_id, _LIMITS)
    request = ProviderRequest(Feature.FEEDBACK_ANALYSIS, validated, _LIMITS)

    def revalidate():
        access.authorize(scope, Feature.FEEDBACK_ANALYSIS)
        if access.feedback_sources(scope, task_id) != snapshot:
            _fail(ErrorCode.STALE_CONTEXT)

    canonical = {"task_id": str(task_id), "focus": focus,
                 "sources": [{"kind": kind, "id": str(source_id), "ref": source.ref, "text": source.text}
                             for (kind, source_id), source in zip(selected, snapshot)]}
    return _execute(actor=actor, profile_id=profile_id, workspace_id=workspace_id,
                    idempotency_key=idempotency_key, policy=policy, adapter=adapter,
                    request=request, canonical_input=canonical,
                    control=control if control is not None else RequestControl(), revalidate=revalidate)
