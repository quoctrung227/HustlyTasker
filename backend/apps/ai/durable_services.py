"""Durable Generator proposals with explicit fixture and OpenAI modes.

All durable accesses acquire the existing tenant locks before AI rows. Provider
execution is outside transactions. Physical purge is deliberately not scheduled.
"""

import hashlib
import json
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.debug import sensitive_variables

from apps.audit.models import AuditLog
from apps.tasks.estimates import normalize_task_estimated_hours
from apps.tasks.services import create_task
from apps.workspace.access import TenantAccessNotFound, can_manage_workspace_tasks
from apps.workspace.services import lock_workspace_mutation_context

from .contracts import TASK_PLAN_VERSION, ValidationLimits
from .errors import AIError, ErrorCode
from .live_generator import LIMITS as LIVE_LIMITS, LIVE_MODE, LIVE_SCENARIO, live_request
from .models import AiDispatch, AiOperation, AiProposal
from .providers import Feature, FixtureAdapter, FixtureScenario, ProviderRequest, RequestControl
from .validation import parse_task_plan, validate_generator_input


_SCENARIOS = {
    "subtitle-check-v1": (FixtureScenario.VALID, "Ví dụ synthetic kiểm tra phụ đề."),
    "task-tree-v1": (FixtureScenario.TASK_TREE, "Ví dụ synthetic Task và Subtask."),
}
_HMAC_PURPOSE = "hustlytasker.ai.fixture-request.v1"
_LIMITS = ValidationLimits()
_BRIEF_UNSET = object()


def _enabled():
    if (
        getattr(settings, "AI_FIXTURE_ENABLED", False) is not True
        or getattr(settings, "ENVIRONMENT", None) != "development"
        or getattr(settings, "IS_PRODUCTION", True)
    ):
        raise AIError(ErrorCode.AI_DISABLED)


def fixture_metadata():
    """Public synthetic configuration only; no provider, persistence or secrets."""
    try:
        _enabled()
        enabled = True
    except AIError as error:
        if error.code is not ErrorCode.AI_DISABLED:
            raise
        enabled = False
    labels = {
        "subtitle-check-v1": "Kiểm tra phụ đề — mẫu giả lập",
        "task-tree-v1": "Task và Subtask — mẫu giả lập",
    }
    return {
        "contract_version": "ai.v1", "enabled": enabled,
        "mode": "fixture_demo", "generated_by_ai": False,
        "scenarios": [{"id": key, "label": labels[key], "brief": value[1]}
                      for key, value in _SCENARIOS.items()],
        "limits": {"max_brief_chars": _LIMITS.max_brief_chars,
                   "max_tasks": _LIMITS.max_tasks, "max_depth": _LIMITS.max_depth,
                   "max_request_bytes": _LIMITS.max_request_bytes},
    }


def generator_metadata():
    from .live_runtime import availability_reason, live_selected

    if not live_selected():
        return fixture_metadata()
    reason = availability_reason()
    return {
        "contract_version": "ai.v1", "enabled": reason is None, "reason": reason, "mode": LIVE_MODE,
        "generated_by_ai": True, "scenarios": [],
        "limits": {"max_brief_chars": LIVE_LIMITS.max_brief_chars,
                   "max_tasks": LIVE_LIMITS.max_tasks, "max_depth": LIVE_LIMITS.max_depth,
                   "max_request_bytes": LIVE_LIMITS.max_request_bytes},
    }


def _selected_live():
    from .live_runtime import live_selected

    return live_selected()


def _require_proposal_mode(proposal):
    if (proposal.scenario_id == LIVE_SCENARIO) != _selected_live():
        raise TenantAccessNotFound()
    if proposal.scenario_id == LIVE_SCENARIO:
        proposal._live_dispatch = _live_dispatch(proposal)


def _live_dispatch(proposal):
    dispatch = getattr(proposal, "_live_dispatch", None)
    if dispatch is None:
        dispatch = proposal.dispatches.filter(
            actor_id=proposal.actor_id, profile_id=proposal.profile_id, workspace_id=proposal.workspace_id,
            execution_mode=AiDispatch.ExecutionMode.OPENAI_LIVE, feature=AiDispatch.Feature.TASK_PLAN,
            provider="openai", status=AiDispatch.Status.SUCCEEDED, usage_status=AiDispatch.UsageStatus.REPORTED,
        ).first()
    if dispatch is None:
        raise AIError(ErrorCode.STALE_PROPOSAL)
    return dispatch


def _manager(*, actor, profile_id, workspace_id):
    if not getattr(actor, "is_authenticated", False):
        raise PermissionDenied("Authentication is required.")
    context, workspace, _ = lock_workspace_mutation_context(
        actor=actor, profile_id=profile_id, workspace_id=workspace_id,
    )
    if not can_manage_workspace_tasks(context):
        raise PermissionDenied("Task management is not allowed.")
    return workspace


def _key_digest(value):
    try:
        if isinstance(value, UUID):
            key = value
        elif type(value) is str and len(value) <= 64:
            key = UUID(value)
        else:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("idempotency_key",)) from None
    return hashlib.sha256(str(key).encode("ascii")).hexdigest()


@sensitive_variables("value", "encoded")
def _canonical(value):
    try:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > _LIMITS.max_request_bytes:
            raise ValueError()
        return encoded
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("payload",)) from None


@sensitive_variables("canonical", "key")
def _digest(canonical, key=None):
    return salted_hmac(_HMAC_PURPOSE, canonical, secret=key, algorithm="sha256").hexdigest()


@sensitive_variables("canonical", "key")
def _same_body(operation, canonical):
    return any(constant_time_compare(operation.body_digest, _digest(canonical, key))
               for key in (settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS))


def _operations(*, actor, workspace, operation, key_digest):
    return AiOperation.objects.filter(
        actor_id=actor.pk, profile_id=workspace.profile_id, workspace_id=workspace.pk,
        operation=operation, key_digest=key_digest,
    )


def _proposal(*, actor, workspace, proposal_id):
    try:
        row = AiProposal.objects.select_for_update().filter(
            pk=proposal_id, actor_id=actor.pk, profile_id=workspace.profile_id,
            workspace_id=workspace.pk,
        ).first()
    except (ValueError, TypeError, ValidationError):
        raise TenantAccessNotFound() from None
    if row is None:
        raise TenantAccessNotFound()
    return row


def _operation(*, actor, workspace, operation, key_digest, canonical, proposal, legacy_canonical=None):
    # Entire key scope, not only this proposal: another target must conflict.
    row = _operations(actor=actor, workspace=workspace, operation=operation,
                      key_digest=key_digest).select_for_update().first()
    if row:
        if row.proposal_id != proposal.pk or not (
            _same_body(row, canonical) or (legacy_canonical is not None and _same_body(row, legacy_canonical))
        ):
            raise AIError(ErrorCode.IDEMPOTENCY_CONFLICT)
    return row


def _recoverable(proposal, now):
    if proposal.status == AiProposal.Status.CONFIRMED and (
        proposal.recovery_expires_at is None or now >= proposal.recovery_expires_at
        or proposal.created_tasks is None
    ):
        raise AIError(ErrorCode.RECOVERY_EXPIRED)


def _visible(proposal, now):
    _recoverable(proposal, now)
    if (proposal.status != AiProposal.Status.AVAILABLE
            or now >= proposal.expires_at or now >= proposal.payload_expires_at):
        # A projection only; no physical deletion/scrub is claimed on GET.
        proposal.payload = None
    return proposal


def _audit(*, actor, proposal, action, node_count):
    AuditLog.objects.create(
        user=actor, action=action, entity_name="AiProposal", entity_id=proposal.id,
        metadata={"profile_id": str(proposal.profile_id),
                  "workspace_id": str(proposal.workspace_id),
                  "mode": LIVE_MODE if proposal.scenario_id == LIVE_SCENARIO else "fixture_demo",
                  "node_count": node_count},
    )


@sensitive_variables("canonical")
def _new_operation(*, actor, workspace, operation, key_digest, canonical, proposal):
    return AiOperation.objects.create(
        actor=actor, profile_id=workspace.profile_id, workspace=workspace,
        operation=operation, key_digest=key_digest, body_digest=_digest(canonical),
        proposal=proposal,
    )


def _plan_json(plan):
    return {
        "contract_version": plan.contract_version,
        "tasks": [{"local_ref": n.local_ref, "parent_ref": n.parent_ref,
                   "title": n.title, "description": n.description,
                   "priority": n.priority,
                   "proposed_deadline": n.proposed_deadline.isoformat().replace("+00:00", "Z")
                   if n.proposed_deadline is not None else None,
                   "notes": n.notes} for n in plan.tasks],
        "assumptions": list(plan.assumptions), "warnings": list(plan.warnings),
    }


@sensitive_variables("payload", "plan", "canonical")
def _edited_plan(payload, *, live=False):
    if type(payload) is not dict:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("payload",))
    amounts = []
    try:
        if live and type(payload.get("tasks")) is list:
            tasks = []
            for row in payload["tasks"]:
                if type(row) is not dict:
                    raise AIError(ErrorCode.VALIDATION_ERROR, fields=("payload",))
                amounts.append(normalize_task_estimated_hours(row.get("estimated_hours")))
                tasks.append({key: value for key, value in row.items() if key != "estimated_hours"})
            payload = {**payload, "tasks": tasks}
        plan = parse_task_plan(_canonical(payload), LIVE_LIMITS if live else _LIMITS)
    except ValidationError:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("estimated_hours",)) from None
    except AIError:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("payload",)) from None
    estimates = {node.local_ref: amount for node, amount in zip(plan.tasks, amounts)}
    return plan, estimates


@sensitive_variables("canonical", "canonical_input", "brief", "validated", "validated_input")
def generate_proposal(*, actor, profile_id, workspace_id, scenario_id, idempotency_key,
                      brief=_BRIEF_UNSET):
    _enabled()
    if type(scenario_id) is not str or scenario_id not in _SCENARIOS:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("scenario_id",))
    key = _key_digest(idempotency_key)
    canonical_input = {"scenario_id": scenario_id, "contract_version": TASK_PLAN_VERSION}
    validated = None
    if brief is not _BRIEF_UNSET:
        validated = validate_generator_input({"brief": brief}, _LIMITS)
        canonical_input["brief"] = validated.brief
    # Preserve the exact old scenario-only fingerprint when the field is absent.
    # Provided synthetic text is body-bound, never stored as raw proposal content.
    canonical = _canonical(canonical_input)
    # First short authorization/replay transaction; never call the adapter here.
    with transaction.atomic():
        workspace = _manager(actor=actor, profile_id=profile_id, workspace_id=workspace_id)
        existing = _operations(actor=actor, workspace=workspace,
                               operation=AiOperation.Operation.GENERATE, key_digest=key).first()
        if existing:
            proposal = _proposal(actor=actor, workspace=workspace, proposal_id=existing.proposal_id)
            _operation(actor=actor, workspace=workspace, operation=AiOperation.Operation.GENERATE,
                       key_digest=key, canonical=canonical, proposal=proposal)
            if proposal.status == AiProposal.Status.AVAILABLE and timezone.now() >= proposal.expires_at:
                raise AIError(ErrorCode.EXPIRED)
            return _visible(proposal, timezone.now()), True

    if any(not getattr(block, "_from_testcase", False)
           for block in transaction.get_connection().atomic_blocks):
        # Never invoke even a fixture from an outer business transaction.
        # Django TestCase isolation blocks are harness-owned, not application
        # transaction/lock boundaries; real non-atomic behavior is tested using
        # TransactionTestCase and PostgreSQL below the HTTP boundary.
        raise AIError(ErrorCode.VALIDATION_ERROR)
    scenario, scenario_brief = _SCENARIOS[scenario_id]
    validated_input = validated if validated is not None else validate_generator_input(
        {"brief": scenario_brief}, _LIMITS,
    )
    result = FixtureAdapter(environment="development", scenario=scenario).generate(
        ProviderRequest(Feature.TASK_PLAN, validated_input, _LIMITS), RequestControl(),
    )
    plan = parse_task_plan(result.raw_json, _LIMITS)
    payload = _plan_json(plan)
    with transaction.atomic():
        workspace = _manager(actor=actor, profile_id=profile_id, workspace_id=workspace_id)
        existing = _operations(actor=actor, workspace=workspace,
                               operation=AiOperation.Operation.GENERATE, key_digest=key).first()
        if existing:
            proposal = _proposal(actor=actor, workspace=workspace, proposal_id=existing.proposal_id)
            _operation(actor=actor, workspace=workspace, operation=AiOperation.Operation.GENERATE,
                       key_digest=key, canonical=canonical, proposal=proposal)
            if proposal.status == AiProposal.Status.AVAILABLE and timezone.now() >= proposal.expires_at:
                raise AIError(ErrorCode.EXPIRED)
            return _visible(proposal, timezone.now()), True
        now = timezone.now()
        proposal = AiProposal.objects.create(
            actor=actor, profile_id=workspace.profile_id, workspace=workspace,
            scenario_id=scenario_id, payload=payload, created_at=now,
            expires_at=now + timedelta(minutes=30), payload_expires_at=now + timedelta(days=7),
        )
        _new_operation(actor=actor, workspace=workspace, operation=AiOperation.Operation.GENERATE,
                       key_digest=key, canonical=canonical, proposal=proposal)
        return proposal, False


@sensitive_variables()
def generate_live_proposal(*, actor, profile_id, workspace_id, idempotency_key,
                           brief, task_count=None, target_deadline=None):
    from .governance import _execute
    from .live_runtime import live_runtime

    request = live_request(brief=brief, task_count=task_count, target_deadline=target_deadline)
    policy, adapter = live_runtime()

    def persist(row, result):
        now = timezone.now()
        # Settlement holds and revalidates the same actor/Profile/Workspace locks.
        row.proposal = AiProposal.objects.create(
            actor_id=row.actor_id, profile_id=row.profile_id, workspace_id=row.workspace_id,
            scenario_id=LIVE_SCENARIO, payload=request.validate(result.raw_json), created_at=now,
            expires_at=now + timedelta(minutes=30), payload_expires_at=now + timedelta(days=7),
        )

    execution = _execute(
        actor=actor, profile_id=profile_id, workspace_id=workspace_id,
        idempotency_key=idempotency_key, policy=policy, adapter=adapter, request=request,
        canonical_input={**request.data, "brief": brief}, control=RequestControl(), persist=persist,
    )
    receipt = execution.receipt
    if receipt.status != AiDispatch.Status.SUCCEEDED or receipt.proposal_id is None:
        raise AIError(ErrorCode.ALREADY_DISPATCHED)
    proposal = retrieve_proposal(actor=actor, profile_id=profile_id, workspace_id=workspace_id,
                                 proposal_id=receipt.proposal_id)
    if proposal.status == AiProposal.Status.AVAILABLE and timezone.now() >= proposal.expires_at:
        raise AIError(ErrorCode.EXPIRED)
    return proposal, execution.result is None


def retrieve_proposal(*, actor, profile_id, workspace_id, proposal_id):
    if not _selected_live():
        _enabled()
    with transaction.atomic():
        workspace = _manager(actor=actor, profile_id=profile_id, workspace_id=workspace_id)
        proposal = _proposal(actor=actor, workspace=workspace, proposal_id=proposal_id)
        _require_proposal_mode(proposal)
        return _visible(proposal, timezone.now())


@sensitive_variables("payload", "plan", "normalized", "canonical")
def confirm_proposal(*, actor, profile_id, workspace_id, proposal_id, idempotency_key,
                     proposal_revision, payload, confirmed):
    live = _selected_live()
    if not live:
        _enabled()
    if confirmed is not True or type(proposal_revision) is not int or proposal_revision < 1:
        raise AIError(ErrorCode.VALIDATION_ERROR)
    key = _key_digest(idempotency_key)
    plan, estimates = _edited_plan(payload, live=live)
    with transaction.atomic():
        workspace = _manager(actor=actor, profile_id=profile_id, workspace_id=workspace_id)
        proposal = _proposal(actor=actor, workspace=workspace, proposal_id=proposal_id)
        _require_proposal_mode(proposal)
        body = {"proposal_id": str(proposal.pk), "proposal_revision": proposal_revision,
                "confirmed": True, "payload": _plan_json(plan), "scenario_id": proposal.scenario_id}
        legacy_canonical = None
        if live:
            # Old receipts can still recover the same Task IDs. Only the new
            # digest is written, so changes to hours conflict for new receipts.
            legacy_canonical = _canonical(body)
            body["confirmation_version"] = 2
            for row in body["payload"]["tasks"]:
                amount = estimates[row["local_ref"]]
                row["estimated_hours"] = str(amount) if amount is not None else None
        canonical = _canonical(body)
        previous = _operation(actor=actor, workspace=workspace, operation=AiOperation.Operation.CONFIRM,
                              key_digest=key, canonical=canonical, proposal=proposal,
                              legacy_canonical=legacy_canonical)
        now = timezone.now()
        if previous:
            _recoverable(proposal, now)
            if proposal.status != AiProposal.Status.CONFIRMED:
                raise AIError(ErrorCode.STALE_PROPOSAL)
            return _visible(proposal, now), True
        if proposal.status == AiProposal.Status.CONFIRMED:
            raise AIError(ErrorCode.ALREADY_CONFIRMED)
        if (proposal.status != AiProposal.Status.AVAILABLE
                or proposal_revision != proposal.revision or proposal.contract_version != TASK_PLAN_VERSION):
            raise AIError(ErrorCode.STALE_PROPOSAL)
        if now >= proposal.expires_at or now >= proposal.payload_expires_at or proposal.payload is None:
            raise AIError(ErrorCode.EXPIRED)
        if live:
            allowed_refs = {row["local_ref"] for row in proposal.payload["tasks"]}
            if any(node.local_ref not in allowed_refs for node in plan.tasks):
                raise AIError(ErrorCode.VALIDATION_ERROR, fields=("payload",))

        created = {}
        pending = list(plan.tasks)
        while pending:
            for node in list(pending):
                if node.parent_ref is not None and node.parent_ref not in created:
                    continue
                task = create_task(
                    actor=actor, profile_id=workspace.profile_id, workspace_id=workspace.pk,
                    title=node.title, description=node.description, priority=node.priority,
                    deadline=node.proposed_deadline,
                    parent_id=created.get(node.parent_ref),
                    estimated_hours=estimates.get(node.local_ref),
                )
                created[node.local_ref] = str(task.pk)
                pending.remove(node)
        proposal.status = AiProposal.Status.CONFIRMED
        proposal.confirmed_at = now
        proposal.recovery_expires_at = now + timedelta(days=30)
        proposal.created_tasks = created
        proposal.payload = None
        proposal.save(update_fields=("status", "confirmed_at", "recovery_expires_at", "created_tasks", "payload"))
        _new_operation(actor=actor, workspace=workspace, operation=AiOperation.Operation.CONFIRM,
                       key_digest=key, canonical=canonical, proposal=proposal)
        _audit(actor=actor, proposal=proposal, action="ai.proposal.confirmed", node_count=len(created))
        return proposal, False


def reject_proposal(*, actor, profile_id, workspace_id, proposal_id, proposal_revision):
    if not _selected_live():
        raise AIError(ErrorCode.AI_DISABLED)
    with transaction.atomic():
        workspace = _manager(actor=actor, profile_id=profile_id, workspace_id=workspace_id)
        proposal = _proposal(actor=actor, workspace=workspace, proposal_id=proposal_id)
        _require_proposal_mode(proposal)
        if type(proposal_revision) is not int or proposal_revision != proposal.revision:
            raise AIError(ErrorCode.STALE_PROPOSAL)
        if proposal.status == AiProposal.Status.REJECTED:
            return proposal
        if proposal.status != AiProposal.Status.AVAILABLE:
            raise AIError(ErrorCode.ALREADY_CONFIRMED)
        if timezone.now() >= proposal.expires_at or proposal.payload is None:
            raise AIError(ErrorCode.EXPIRED)
        proposal.status = AiProposal.Status.REJECTED
        proposal.payload = None
        proposal.save(update_fields=("status", "payload"))
        _audit(actor=actor, proposal=proposal, action="ai.proposal.rejected", node_count=0)
        return proposal


def serialize_proposal(proposal):
    """Safe current projection, called immediately after a scoped service read."""
    now = timezone.now()
    proposal = _visible(proposal, now)
    expired = proposal.status == AiProposal.Status.AVAILABLE and now >= proposal.expires_at
    result = {
        "contract_version": "ai.v1", "proposal_id": str(proposal.pk),
        "revision": proposal.revision, "scenario_id": proposal.scenario_id,
        "status": "EXPIRED" if expired else proposal.status,
        "mode": "fixture_demo", "generated_by_ai": False, "persisted": True,
        "created_at": proposal.created_at, "expires_at": proposal.expires_at,
        "payload_expires_at": proposal.payload_expires_at,
        "confirmed_at": proposal.confirmed_at, "recovery_expires_at": proposal.recovery_expires_at,
        "payload": proposal.payload, "created_tasks": proposal.created_tasks,
        "usage": {"input_tokens": 0, "billable_output_tokens": 0,
                  "cost_usd": "0.000000", "status": "fixture_zero"},
    }
    if proposal.scenario_id == LIVE_SCENARIO:
        dispatch = _live_dispatch(proposal)
        result.update(
            mode=LIVE_MODE, generated_by_ai=True, provider=dispatch.provider, model=dispatch.model,
            usage={"input_tokens": dispatch.input_tokens, "billable_output_tokens": dispatch.output_tokens,
                   "cost_usd": format(dispatch.estimated_cost, ".8f"), "status": "provider_reported"},
        )
    return result
