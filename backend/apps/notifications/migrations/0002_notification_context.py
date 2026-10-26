import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"), ("tasks", "0004_task_comments"),
        ("workspace", "0004_profileinvitation"), ("audit", "0001_initial"),
    ]

    operations = [
        migrations.AddField(model_name="notification", name="event_type", field=models.CharField(
            blank=True, null=True, max_length=32, choices=[
                ("TASK_ASSIGNED", "Task Assigned"), ("REVIEW_SUBMITTED", "Review Submitted"),
                ("REVIEW_APPROVED", "Review Approved"),
                ("REVIEW_CHANGES_REQUESTED", "Review Changes Requested"),
                ("TASK_COMMENTED", "Task Commented")])),
        migrations.AddField(model_name="notification", name="profile", field=models.ForeignKey(
            blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
            related_name="notifications", to="workspace.profile")),
        migrations.AddField(model_name="notification", name="workspace", field=models.ForeignKey(
            blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
            related_name="notifications", to="workspace.workspace")),
        migrations.AddField(model_name="notification", name="task", field=models.ForeignKey(
            blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
            related_name="notifications", to="tasks.task")),
        migrations.AddField(model_name="notification", name="event", field=models.ForeignKey(
            blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
            related_name="notifications", to="audit.auditlog")),
        migrations.AddConstraint(model_name="notification", constraint=models.CheckConstraint(
            condition=(models.Q(event_type__isnull=True, profile__isnull=True,
                                workspace__isnull=True, task__isnull=True, event__isnull=True)
                       | models.Q(event_type__isnull=False, profile__isnull=False,
                                  workspace__isnull=False, task__isnull=False, event__isnull=False)),
            name="notif_context_complete")),
        migrations.AddConstraint(model_name="notification", constraint=models.CheckConstraint(
            condition=models.Q(event_type__isnull=True) | models.Q(event_type__in=(
                "TASK_ASSIGNED", "REVIEW_SUBMITTED", "REVIEW_APPROVED",
                "REVIEW_CHANGES_REQUESTED", "TASK_COMMENTED")), name="notif_valid_event_type")),
        migrations.AddConstraint(model_name="notification", constraint=models.UniqueConstraint(
            fields=("user", "event"), condition=models.Q(event__isnull=False), name="uniq_notif_event_user")),
        migrations.AddIndex(model_name="notification", index=models.Index(
            fields=["user", "is_read", "-created_at", "id"], name="notif_user_read_created_idx")),
    ]
