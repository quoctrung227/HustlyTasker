"""Expand live dispatch provenance, usage and budget to the Groq provider."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ai", "0003_proposal_rejection")]

    execution_modes = [
        ("FIXTURE", "Synthetic fixture"),
        ("OPENAI_OFFLINE", "Offline OpenAI transport"),
        ("OPENAI_LIVE", "Live OpenAI (not enabled)"),
        ("GROQ_LIVE", "Live Groq"),
    ]

    operations = [
        # These fields change only Django's validation choices.
        migrations.AlterField(
            model_name="aidispatch", name="execution_mode",
            field=models.CharField(choices=execution_modes, max_length=20),
        ),
        migrations.AlterField(
            model_name="aibudgetbucket", name="execution_mode",
            field=models.CharField(choices=execution_modes, max_length=20),
        ),
        migrations.RemoveConstraint(model_name="aidispatch", name="ai_disp_origin_valid"),
        migrations.AddConstraint(
            model_name="aidispatch",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(execution_mode="FIXTURE", provider="fixture")
                    | models.Q(execution_mode__in=("OPENAI_OFFLINE", "OPENAI_LIVE"), provider="openai")
                    | models.Q(execution_mode="GROQ_LIVE", provider="groq")
                ),
                name="ai_disp_origin_valid",
            ),
        ),
        migrations.RemoveConstraint(model_name="aidispatch", name="ai_disp_usage_mode_valid"),
        migrations.AddConstraint(
            model_name="aidispatch",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(usage_status="UNKNOWN")
                    | models.Q(execution_mode__in=("FIXTURE", "OPENAI_OFFLINE"), usage_status="SIMULATED")
                    | models.Q(execution_mode__in=("OPENAI_LIVE", "GROQ_LIVE"), usage_status="REPORTED")
                ),
                name="ai_disp_usage_mode_valid",
            ),
        ),
        migrations.RemoveConstraint(model_name="aibudgetbucket", name="ai_budget_mode_valid"),
        migrations.AddConstraint(
            model_name="aibudgetbucket",
            constraint=models.CheckConstraint(
                condition=models.Q(execution_mode__in=("FIXTURE", "OPENAI_OFFLINE", "OPENAI_LIVE", "GROQ_LIVE")),
                name="ai_budget_mode_valid",
            ),
        ),
    ]
