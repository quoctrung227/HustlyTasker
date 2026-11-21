"""Permit explicitly rejected drafts without adding columns or rewriting rows."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ai", "0002_dispatch_governance")]

    operations = [
        migrations.AlterField(
            model_name="aiproposal", name="status",
            field=models.CharField(
                choices=[("AVAILABLE", "Available"), ("CONFIRMED", "Confirmed"), ("REJECTED", "Rejected")],
                default="AVAILABLE", max_length=12,
            ),
        ),
        migrations.RemoveConstraint(model_name="aiproposal", name="ai_prop_valid_status"),
        migrations.RemoveConstraint(model_name="aiproposal", name="ai_prop_lifecycle"),
        migrations.AddConstraint(
            model_name="aiproposal",
            constraint=models.CheckConstraint(
                condition=models.Q(status__in=("AVAILABLE", "CONFIRMED", "REJECTED")),
                name="ai_prop_valid_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="aiproposal",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(status="AVAILABLE", confirmed_at__isnull=True,
                             recovery_expires_at__isnull=True, created_tasks__isnull=True)
                    | models.Q(status="CONFIRMED", confirmed_at__isnull=False,
                               recovery_expires_at__isnull=False, payload__isnull=True)
                    | models.Q(status="REJECTED", confirmed_at__isnull=True,
                               recovery_expires_at__isnull=True, payload__isnull=True,
                               created_tasks__isnull=True)
                ),
                name="ai_prop_lifecycle",
            ),
        ),
    ]
