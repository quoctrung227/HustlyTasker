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
