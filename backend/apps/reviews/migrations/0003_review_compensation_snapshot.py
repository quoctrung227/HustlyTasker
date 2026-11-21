import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("reviews", "0002_review_workflow_foundation")]

    operations = [
        migrations.AddField(
            model_name="review", name="compensation_snapshot_recorded",
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AddField(
            model_name="review", name="compensation_snapshot_vnd",
            field=models.DecimalField(
                blank=True, decimal_places=0, editable=False, max_digits=18,
                null=True, validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(
                condition=models.Q(compensation_snapshot_vnd__isnull=True)
                | models.Q(compensation_snapshot_vnd__gte=0),
                name="review_snapshot_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(
                condition=models.Q(compensation_snapshot_recorded=True)
                | models.Q(compensation_snapshot_vnd__isnull=True),
                name="review_snapshot_recorded_pair",
            ),
        ),
    ]
