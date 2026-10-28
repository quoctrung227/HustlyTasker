"""Fixture-only Generator lifecycle; no live provider or background work.

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
from apps.tasks.services import create_task
from apps.workspace.access import TenantAccessNotFound, can_manage_workspace_tasks
from apps.workspace.services import lock_workspace_mutation_context

from .contracts import TASK_PLAN_VERSION, ValidationLimits
from .errors import AIError, ErrorCode
from .models import AiOperation, AiProposal
from .providers import Feature, FixtureAdapter, FixtureScenario, ProviderRequest, RequestControl
from .validation import parse_task_plan, validate_generator_input


_SCENARIOS = {
    "subtitle-check-v1": (FixtureScenario.VALID, "Ví dụ synthetic kiểm tra phụ đề."),
    "task-tree-v1": (FixtureScenario.TASK_TREE, "Ví dụ synthetic Task và Subtask."),
}
_HMAC_PURPOSE = "hustlytasker.ai.fixture-request.v1"
_LIMITS = ValidationLimits()


def _enabled():
    if (
        getattr(settings, "AI_FIXTURE_ENABLED", False) is not True
        or getattr(settings, "ENVIRONMENT", None) != "development"
        or getattr(settings, "IS_PRODUCTION", True)
    ):
        raise AIError(ErrorCode.AI_DISABLED)


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


def _operation(*, actor, workspace, operation, key_digest, canonical, proposal):
    # Entire key scope, not only this proposal: another target must conflict.
    row = _operations(actor=actor, workspace=workspace, operation=operation,
                      key_digest=key_digest).select_for_update().first()
    if row and (row.proposal_id != proposal.pk or not _same_body(row, canonical)):
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
                  "mode": "fixture_demo", "node_count": node_count},
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
def _edited_plan(payload):
    if type(payload) is not dict:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("payload",))
    try:
        plan = parse_task_plan(_canonical(payload), _LIMITS)
    except AIError:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("payload",)) from None
    return plan, _plan_json(plan)


def generate_proposal(*, actor, profile_id, workspace_id, scenario_id, idempotency_key):
    _enabled()
    if type(scenario_id) is not str or scenario_id not in _SCENARIOS:
        raise AIError(ErrorCode.VALIDATION_ERROR, fields=("scenario_id",))
    key = _key_digest(idempotency_key)
    canonical = _canonical({"scenario_id": scenario_id, "contract_version": TASK_PLAN_VERSION})
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
    scenario, brief = _SCENARIOS[scenario_id]
    validated = validate_generator_input({"brief": brief}, _LIMITS)
    result = FixtureAdapter(environment="development", scenario=scenario).generate(
        ProviderRequest(Feature.TASK_PLAN, validated, _LIMITS), RequestControl(),
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


def retrieve_proposal(*, actor, profile_id, workspace_id, proposal_id):
    _enabled()
    with transaction.atomic():
        workspace = _manager(actor=actor, profile_id=profile_id, workspace_id=workspace_id)
        return _visible(_proposal(actor=actor, workspace=workspace, proposal_id=proposal_id), timezone.now())


@sensitive_variables("payload", "plan", "normalized", "canonical")
def confirm_proposal(*, actor, profile_id, workspace_id, proposal_id, idempotency_key,
                     proposal_revision, payload, confirmed):
    _enabled()
    if confirmed is not True or type(proposal_revision) is not int or proposal_revision < 1:
        raise AIError(ErrorCode.VALIDATION_ERROR)
    key = _key_digest(idempotency_key)
    plan, normalized = _edited_plan(payload)
    with transaction.atomic():
        workspace = _manager(actor=actor, profile_id=profile_id, workspace_id=workspace_id)
        proposal = _proposal(actor=actor, workspace=workspace, proposal_id=proposal_id)
        canonical = _canonical({"proposal_id": str(proposal.pk),
                                "proposal_revision": proposal_revision, "confirmed": True,
                                "payload": normalized, "scenario_id": proposal.scenario_id})
        previous = _operation(actor=actor, workspace=workspace, operation=AiOperation.Operation.CONFIRM,
                              key_digest=key, canonical=canonical, proposal=proposal)
        now = timezone.now()
        if previous:
            _recoverable(proposal, now)
            if proposal.status != AiProposal.Status.CONFIRMED:
                raise AIError(ErrorCode.STALE_PROPOSAL)
            return _visible(proposal, now), True
        if proposal.status == AiProposal.Status.CONFIRMED:
            raise AIError(ErrorCode.ALREADY_CONFIRMED)
        if proposal_revision != proposal.revision or proposal.contract_version != TASK_PLAN_VERSION:
            raise AIError(ErrorCode.STALE_PROPOSAL)
        if now >= proposal.expires_at or now >= proposal.payload_expires_at or proposal.payload is None:
            raise AIError(ErrorCode.EXPIRED)

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


def serialize_proposal(proposal):
    """Safe current projection, called immediately after a scoped service read."""
    now = timezone.now()
    proposal = _visible(proposal, now)
    expired = proposal.status == AiProposal.Status.AVAILABLE and now >= proposal.expires_at
    return {
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
