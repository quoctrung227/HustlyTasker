from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0006_soft_delete")]

    operations = [
        migrations.AddField(
            model_name="task",
            name="estimated_hours",
            field=models.DecimalField(blank=True, decimal_places=2, editable=False, max_digits=6, null=True),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=(models.Q(estimated_hours__isnull=True)
                           | models.Q(estimated_hours__gte=Decimal("0.01"), estimated_hours__lte=Decimal("1000.00"))),
                name="task_estimated_hours_range",
            ),
        ),
    ]
