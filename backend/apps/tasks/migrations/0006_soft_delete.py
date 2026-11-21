from datetime import timedelta

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0005_task_brief"), ("workspace", "0006_soft_delete"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="task", name="deleted_at", field=models.DateTimeField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="task", name="deleted_by", field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="task", name="purge_after", field=models.DateTimeField(blank=True, editable=False, null=True)),
        migrations.AddConstraint(model_name="task", constraint=models.CheckConstraint(condition=(models.Q(deleted_at__isnull=True, purge_after__isnull=True, deleted_by__isnull=True) | models.Q(deleted_at__isnull=False, purge_after__isnull=False, purge_after=models.F("deleted_at") + timedelta(days=30))), name="task_trash_metadata_valid")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=("purge_after", "id"), condition=models.Q(deleted_at__isnull=False), name="task_trash_due_idx")),
    ]
