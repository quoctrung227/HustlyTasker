from datetime import timedelta

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("workspace", "0005_account_invitations"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = []
    for model, prefix in (("profile", "profile"), ("workspace", "workspace")):
        operations.extend([
            migrations.AddField(model_name=model, name="deleted_at", field=models.DateTimeField(blank=True, editable=False, null=True)),
            migrations.AddField(model_name=model, name="deleted_by", field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            migrations.AddField(model_name=model, name="purge_after", field=models.DateTimeField(blank=True, editable=False, null=True)),
            migrations.AddConstraint(model_name=model, constraint=models.CheckConstraint(condition=(models.Q(deleted_at__isnull=True, purge_after__isnull=True, deleted_by__isnull=True) | models.Q(deleted_at__isnull=False, purge_after__isnull=False, purge_after=models.F("deleted_at") + timedelta(days=30))), name=f"{prefix}_trash_metadata_valid")),
            migrations.AddIndex(model_name=model, index=models.Index(fields=("purge_after", "id"), condition=models.Q(deleted_at__isnull=False), name=f"{prefix}_trash_due_idx")),
        ])
