"""Reviewed additive AI schema; persistent development apply is NOT approved."""

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("workspace", "0004_profileinvitation"),
    ]
    operations = [
        migrations.CreateModel(
            name="AiProposal",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("AVAILABLE", "Available"), ("CONFIRMED", "Confirmed")], default="AVAILABLE", max_length=12)),
                ("contract_version", models.CharField(default="ai.task-plan.v1", max_length=32)),
                ("revision", models.PositiveIntegerField(default=1)),
                ("scenario_id", models.CharField(max_length=80)),
                ("payload", models.JSONField(blank=True, null=True)),
                ("created_tasks", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("expires_at", models.DateTimeField()),
                ("payload_expires_at", models.DateTimeField()),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("recovery_expires_at", models.DateTimeField(blank=True, null=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="workspace.profile")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="workspace.workspace")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["actor", "profile", "workspace", "-created_at"], name="ai_prop_actor_scope_idx"),
                    models.Index(fields=["status", "payload_expires_at"], name="ai_prop_payload_exp_idx"),
                    models.Index(fields=["status", "recovery_expires_at"], name="ai_prop_recovery_exp_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(status__in=("AVAILABLE", "CONFIRMED")), name="ai_prop_valid_status"),
                    models.CheckConstraint(condition=models.Q(revision__gte=1), name="ai_prop_positive_revision"),
                    models.CheckConstraint(condition=models.Q(expires_at__gt=models.F("created_at")), name="ai_prop_expiry_order"),
                    models.CheckConstraint(condition=models.Q(payload_expires_at__gte=models.F("expires_at")), name="ai_prop_payload_order"),
                    models.CheckConstraint(condition=(models.Q(status="AVAILABLE", confirmed_at__isnull=True, recovery_expires_at__isnull=True, created_tasks__isnull=True) | models.Q(status="CONFIRMED", confirmed_at__isnull=False, recovery_expires_at__isnull=False, payload__isnull=True)), name="ai_prop_lifecycle"),
                    models.CheckConstraint(condition=(models.Q(confirmed_at__isnull=True) | models.Q(confirmed_at__gte=models.F("created_at"), recovery_expires_at__gt=models.F("confirmed_at"))), name="ai_prop_confirm_order"),
                ],
            },
        ),
        migrations.CreateModel(
            name="AiOperation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("operation", models.CharField(choices=[("GENERATE", "Generate"), ("CONFIRM", "Confirm")], max_length=8)),
                ("key_digest", models.CharField(max_length=64)),
                ("body_digest", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="workspace.profile")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="workspace.workspace")),
                ("proposal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="operations", to="ai.aiproposal")),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=models.Q(operation__in=("GENERATE", "CONFIRM")), name="ai_op_valid_operation"),
                    models.UniqueConstraint(fields=("actor", "profile", "workspace", "operation", "key_digest"), name="ai_op_scope_key_unique"),
                    models.UniqueConstraint(fields=("proposal",), condition=models.Q(operation="CONFIRM"), name="ai_op_one_confirm_per_prop"),
                ],
            },
        ),
    ]
