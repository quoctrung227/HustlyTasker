"""Add optional Task brief metadata; persistent development rollout is gated."""

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0004_task_comments")]

    operations = [
        migrations.AddField(
            model_name="task", name="raw_video_url",
            field=models.URLField(blank=True, max_length=2048, null=True,
                                  validators=[django.core.validators.URLValidator(schemes=("http", "https"))]),
        ),
        migrations.AddField(
            model_name="task", name="reference_video_url",
            field=models.URLField(blank=True, max_length=2048, null=True,
                                  validators=[django.core.validators.URLValidator(schemes=("http", "https"))]),
        ),
        migrations.AddField(
            model_name="task", name="template_project_url",
            field=models.URLField(blank=True, max_length=2048, null=True,
                                  validators=[django.core.validators.URLValidator(schemes=("http", "https"))]),
        ),
        migrations.AddField(
            model_name="task", name="script_url",
            field=models.URLField(blank=True, max_length=2048, null=True,
                                  validators=[django.core.validators.URLValidator(schemes=("http", "https"))]),
        ),
        migrations.AddField(
            model_name="task", name="estimated_compensation_vnd",
            field=models.DecimalField(blank=True, decimal_places=0, max_digits=18,
                                      null=True, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=(models.Q(estimated_compensation_vnd__isnull=True)
                           | models.Q(estimated_compensation_vnd__gte=0)),
                name="task_compensation_vnd_nonnegative",
            ),
        ),
    ]
