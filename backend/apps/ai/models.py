"""Dedicated synthetic proposal state, separate from business/audit content."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AiProposal(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE"
        CONFIRMED = "CONFIRMED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    profile = models.ForeignKey("workspace.Profile", on_delete=models.PROTECT)
    workspace = models.ForeignKey("workspace.Workspace", on_delete=models.PROTECT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE)
    contract_version = models.CharField(max_length=32, default="ai.task-plan.v1")
    revision = models.PositiveIntegerField(default=1)
    scenario_id = models.CharField(max_length=80)
    payload = models.JSONField(null=True, blank=True)
    created_tasks = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    expires_at = models.DateTimeField()
    payload_expires_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    recovery_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=("AVAILABLE", "CONFIRMED")), name="ai_prop_valid_status"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="ai_prop_positive_revision"),
            models.CheckConstraint(condition=models.Q(expires_at__gt=models.F("created_at")), name="ai_prop_expiry_order"),
            models.CheckConstraint(condition=models.Q(payload_expires_at__gte=models.F("expires_at")), name="ai_prop_payload_order"),
            models.CheckConstraint(condition=(
                models.Q(status="AVAILABLE", confirmed_at__isnull=True,
                         recovery_expires_at__isnull=True, created_tasks__isnull=True)
                | models.Q(status="CONFIRMED", confirmed_at__isnull=False,
                           recovery_expires_at__isnull=False, payload__isnull=True)
            ), name="ai_prop_lifecycle"),
            models.CheckConstraint(condition=(
                models.Q(confirmed_at__isnull=True)
                | models.Q(confirmed_at__gte=models.F("created_at"),
                           recovery_expires_at__gt=models.F("confirmed_at"))
            ), name="ai_prop_confirm_order"),
        ]
        indexes = [
            models.Index(fields=("actor", "profile", "workspace", "-created_at"), name="ai_prop_actor_scope_idx"),
            models.Index(fields=("status", "payload_expires_at"), name="ai_prop_payload_exp_idx"),
            models.Index(fields=("status", "recovery_expires_at"), name="ai_prop_recovery_exp_idx"),
        ]

    def clean(self):
        super().clean()
        if self.workspace_id and self.profile_id and self.workspace.profile_id != self.profile_id:
            raise ValidationError({"workspace": "Workspace does not belong to this Profile."})


class AiOperation(models.Model):
    class Operation(models.TextChoices):
        GENERATE = "GENERATE"
        CONFIRM = "CONFIRM"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    profile = models.ForeignKey("workspace.Profile", on_delete=models.PROTECT)
    workspace = models.ForeignKey("workspace.Workspace", on_delete=models.PROTECT)
    operation = models.CharField(max_length=8, choices=Operation.choices)
    key_digest = models.CharField(max_length=64)
    body_digest = models.CharField(max_length=64)
    proposal = models.ForeignKey(AiProposal, on_delete=models.PROTECT, related_name="operations")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(operation__in=("GENERATE", "CONFIRM")), name="ai_op_valid_operation"),
            models.UniqueConstraint(fields=("actor", "profile", "workspace", "operation", "key_digest"), name="ai_op_scope_key_unique"),
            models.UniqueConstraint(fields=("proposal",), condition=models.Q(operation="CONFIRM"), name="ai_op_one_confirm_per_prop"),
        ]

    def clean(self):
        super().clean()
        if self.proposal_id and any(
            getattr(self, name) != getattr(self.proposal, name)
            for name in ("actor_id", "profile_id", "workspace_id")
        ):
            raise ValidationError("Operation and proposal scopes must match.")


class AiDispatch(models.Model):
    """Metadata-only governance; neither raw input nor generated output belongs here."""

    class ExecutionMode(models.TextChoices):
        FIXTURE = "FIXTURE", "Synthetic fixture"
        OPENAI_OFFLINE = "OPENAI_OFFLINE", "Offline OpenAI transport"
        OPENAI_LIVE = "OPENAI_LIVE", "Live OpenAI (not enabled)"

    class Feature(models.TextChoices):
        TASK_PLAN = "task_plan", "Task plan"
        FEEDBACK_ANALYSIS = "feedback_analysis", "Feedback analysis"

    class Status(models.TextChoices):
        RESERVED = "RESERVED", "Reserved"
        DISPATCHING = "DISPATCHING", "Dispatching"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED_BEFORE_DISPATCH = "FAILED_BEFORE_DISPATCH", "Failed before dispatch"
        OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN", "Outcome unknown"
        RECONCILED = "RECONCILED", "Reconciled"

    class UsageStatus(models.TextChoices):
        UNKNOWN = "UNKNOWN", "Unknown"
        SIMULATED = "SIMULATED", "Simulated"
        REPORTED = "REPORTED", "Provider reported"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    profile = models.ForeignKey("workspace.Profile", on_delete=models.PROTECT, related_name="+")
    workspace = models.ForeignKey("workspace.Workspace", on_delete=models.PROTECT, related_name="+")
    proposal = models.ForeignKey(AiProposal, on_delete=models.PROTECT, null=True, blank=True, related_name="dispatches")
    feature = models.CharField(max_length=32, choices=Feature.choices)
    provider = models.CharField(max_length=32)
    model = models.CharField(max_length=100)
    execution_mode = models.CharField(max_length=20, choices=ExecutionMode.choices)
    contract_version = models.CharField(max_length=32, default="ai.governance.v1")
    config_version = models.CharField(max_length=64)
    pricing_version = models.CharField(max_length=64)
    policy_digest = models.CharField(max_length=64)
    key_digest = models.CharField(max_length=64)
    body_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.RESERVED)
    reserved_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    accounted_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    billed_cost = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    input_token_limit = models.PositiveIntegerField()
    output_token_limit = models.PositiveIntegerField()
    input_tokens = models.PositiveBigIntegerField(null=True, blank=True)
    output_tokens = models.PositiveBigIntegerField(null=True, blank=True)
    usage_status = models.CharField(max_length=12, choices=UsageStatus.choices, default=UsageStatus.UNKNOWN)
    claim_id = models.UUIDField(null=True, blank=True)
    error_code = models.CharField(max_length=32, blank=True, default="")
    settlement_digest = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("actor", "profile", "workspace", "feature", "execution_mode", "key_digest"), name="ai_disp_identity_unique"),
            models.UniqueConstraint(fields=("proposal",), condition=models.Q(proposal__isnull=False), name="ai_disp_one_per_proposal"),
            models.CheckConstraint(condition=models.Q(feature__in=("task_plan", "feedback_analysis")), name="ai_disp_feature_valid"),
            models.CheckConstraint(condition=(models.Q(execution_mode="FIXTURE", provider="fixture") | models.Q(execution_mode__in=("OPENAI_OFFLINE", "OPENAI_LIVE"), provider="openai")), name="ai_disp_origin_valid"),
            models.CheckConstraint(condition=(~models.Q(model="") & ~models.Q(contract_version="") & ~models.Q(config_version="") & ~models.Q(pricing_version="")), name="ai_disp_versions_nonempty"),
            models.CheckConstraint(condition=models.Q(key_digest__regex=r"^[0-9a-f]{64}$", body_digest__regex=r"^[0-9a-f]{64}$"), name="ai_disp_digests_valid"),
            models.CheckConstraint(condition=models.Q(policy_digest__regex=r"^[0-9a-f]{64}$"), name="ai_disp_policy_digest_valid"),
            models.CheckConstraint(condition=(models.Q(settlement_digest="") | models.Q(settlement_digest__regex=r"^[0-9a-f]{64}$")), name="ai_disp_settle_digest_valid"),
            models.CheckConstraint(condition=models.Q(usage_status__in=("UNKNOWN", "SIMULATED", "REPORTED")), name="ai_disp_usage_valid"),
            models.CheckConstraint(condition=(models.Q(usage_status="UNKNOWN") | models.Q(execution_mode__in=("FIXTURE", "OPENAI_OFFLINE"), usage_status="SIMULATED") | models.Q(execution_mode="OPENAI_LIVE", usage_status="REPORTED")), name="ai_disp_usage_mode_valid"),
            models.CheckConstraint(condition=(models.Q(execution_mode="OPENAI_LIVE") | models.Q(billed_cost__isnull=True)), name="ai_disp_no_simulated_bill"),
            models.CheckConstraint(condition=models.Q(reserved_amount__gte=0, reserved_amount__lt=1000000000000), name="ai_disp_reservation_bounds"),
            models.CheckConstraint(condition=(models.Q(accounted_amount__isnull=True) | models.Q(accounted_amount__gte=0, accounted_amount__lte=models.F("reserved_amount"))), name="ai_disp_accounted_bounds"),
            models.CheckConstraint(condition=(models.Q(estimated_cost__isnull=True) | models.Q(estimated_cost__gte=0, estimated_cost__lt=1000000000000)), name="ai_disp_estimate_bounds"),
            models.CheckConstraint(condition=(models.Q(billed_cost__isnull=True) | models.Q(billed_cost__gte=0, billed_cost__lt=1000000000000)), name="ai_disp_bill_bounds"),
            models.CheckConstraint(condition=models.Q(input_token_limit__gte=1, output_token_limit__gte=1), name="ai_disp_token_limits"),
            models.CheckConstraint(condition=(models.Q(input_tokens__isnull=True, output_tokens__isnull=True) | models.Q(input_tokens__isnull=False, output_tokens__isnull=False)), name="ai_disp_token_pair"),
            models.CheckConstraint(condition=(~models.Q(status="SUCCEEDED") | models.Q(usage_status__in=("SIMULATED", "REPORTED"), input_tokens__isnull=False, output_tokens__isnull=False)), name="ai_disp_success_usage_known"),
            models.CheckConstraint(condition=(
                models.Q(status="RESERVED", dispatched_at__isnull=True, claim_id__isnull=True, completed_at__isnull=True, reconciled_at__isnull=True, accounted_amount__isnull=True)
                | models.Q(status="DISPATCHING", dispatched_at__isnull=False, claim_id__isnull=False, completed_at__isnull=True, reconciled_at__isnull=True, accounted_amount__isnull=True)
                | models.Q(status="OUTCOME_UNKNOWN", dispatched_at__isnull=False, claim_id__isnull=False, reconciled_at__isnull=True, accounted_amount__isnull=True)
                | models.Q(status="SUCCEEDED", dispatched_at__isnull=False, claim_id__isnull=False, completed_at__isnull=False, reconciled_at__isnull=True, accounted_amount__isnull=False)
                | models.Q(status="FAILED_BEFORE_DISPATCH", dispatched_at__isnull=True, claim_id__isnull=True, completed_at__isnull=False, reconciled_at__isnull=True, accounted_amount__isnull=False, accounted_amount=0)
                | models.Q(status="RECONCILED", dispatched_at__isnull=False, claim_id__isnull=False, completed_at__isnull=False, reconciled_at__isnull=False, accounted_amount__isnull=False)
            ), name="ai_disp_lifecycle"),
            models.CheckConstraint(condition=(models.Q(dispatched_at__isnull=True) | models.Q(dispatched_at__gte=models.F("created_at"))), name="ai_disp_dispatch_time"),
            models.CheckConstraint(condition=(models.Q(completed_at__isnull=True) | models.Q(completed_at__gte=models.F("created_at"))), name="ai_disp_complete_time"),
            models.CheckConstraint(condition=(models.Q(reconciled_at__isnull=True) | models.Q(reconciled_at__gte=models.F("completed_at"))), name="ai_disp_reconcile_time"),
            models.CheckConstraint(condition=models.Q(lease_expires_at__gt=models.F("created_at")), name="ai_disp_lease_order"),
        ]
        indexes = [
            models.Index(fields=("actor", "profile", "workspace", "-created_at"), name="ai_disp_actor_scope_idx"),
            models.Index(fields=("status", "lease_expires_at"), name="ai_disp_lease_idx"),
        ]

    def clean(self):
        super().clean()
        if self.workspace_id and self.profile_id and self.workspace.profile_id != self.profile_id:
            raise ValidationError({"workspace": "Workspace does not belong to this Profile."})
        if self.proposal_id and any(
            getattr(self, name) != getattr(self.proposal, name)
            for name in ("actor_id", "profile_id", "workspace_id")
        ):
            raise ValidationError({"proposal": "Proposal and dispatch scopes must match."})


class AiBudgetBucket(models.Model):
    """Stable lifetime scope counters; no period or policy rollover can reset holds."""

    class Scope(models.TextChoices):
        GLOBAL = "GLOBAL", "Global"
        PROFILE = "PROFILE", "Profile"
        USER = "USER", "User"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(max_length=8, choices=Scope.choices)
    execution_mode = models.CharField(max_length=20, choices=AiDispatch.ExecutionMode.choices)
    profile = models.ForeignKey("workspace.Profile", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    policy_version = models.CharField(max_length=64)
    cost_limit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    reserved_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    accounted_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    request_limit = models.PositiveBigIntegerField(default=0)
    concurrency_limit = models.PositiveIntegerField(default=0)
    request_count = models.PositiveBigIntegerField(default=0)
    active_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(scope="GLOBAL", profile__isnull=True, user__isnull=True) | models.Q(scope="PROFILE", profile__isnull=False, user__isnull=True) | models.Q(scope="USER", profile__isnull=True, user__isnull=False)), name="ai_budget_scope_valid"),
            models.CheckConstraint(condition=models.Q(execution_mode__in=("FIXTURE", "OPENAI_OFFLINE", "OPENAI_LIVE")), name="ai_budget_mode_valid"),
            models.CheckConstraint(condition=~models.Q(policy_version=""), name="ai_budget_policy_nonempty"),
            models.UniqueConstraint(fields=("execution_mode",), condition=models.Q(scope="GLOBAL"), name="ai_budget_global_unique"),
            models.UniqueConstraint(fields=("profile", "execution_mode"), condition=models.Q(scope="PROFILE"), name="ai_budget_profile_unique"),
            models.UniqueConstraint(fields=("user", "execution_mode"), condition=models.Q(scope="USER"), name="ai_budget_user_unique"),
            models.CheckConstraint(condition=models.Q(cost_limit__gte=0, cost_limit__lt=1000000000000, reserved_amount__gte=0, reserved_amount__lt=1000000000000, accounted_amount__gte=0, accounted_amount__lt=1000000000000), name="ai_budget_amount_bounds"),
            models.CheckConstraint(condition=models.Q(cost_limit__gte=models.F("reserved_amount") + models.F("accounted_amount")), name="ai_budget_total_limit"),
            models.CheckConstraint(condition=models.Q(request_count__lte=models.F("request_limit")), name="ai_budget_request_limit"),
            models.CheckConstraint(condition=(models.Q(active_count__lte=models.F("concurrency_limit")) & models.Q(active_count__lte=models.F("request_count"))), name="ai_budget_inflight_limit"),
        ]


class AiDispatchReservation(models.Model):
    """Immutable dispatch exposure linked to each authoritative shared scope."""

    class Status(models.TextChoices):
        HELD = "HELD", "Held"
        SETTLED = "SETTLED", "Settled"
        RELEASED = "RELEASED", "Released"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispatch = models.ForeignKey(AiDispatch, on_delete=models.PROTECT, related_name="reservations")
    bucket = models.ForeignKey(AiBudgetBucket, on_delete=models.PROTECT, related_name="reservations")
    amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.HELD)
    settled_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("dispatch", "bucket"), name="ai_res_dispatch_bucket_unique"),
            models.CheckConstraint(condition=models.Q(amount__gte=0, amount__lt=1000000000000), name="ai_res_amount_bounds"),
            models.CheckConstraint(condition=(models.Q(settled_amount__isnull=True) | models.Q(settled_amount__gte=0, settled_amount__lte=models.F("amount"))), name="ai_res_settled_bounds"),
            models.CheckConstraint(condition=(models.Q(status="HELD", settled_amount__isnull=True) | models.Q(status="SETTLED", settled_amount__isnull=False) | models.Q(status="RELEASED", settled_amount__isnull=False, settled_amount=0)), name="ai_res_lifecycle"),
        ]
