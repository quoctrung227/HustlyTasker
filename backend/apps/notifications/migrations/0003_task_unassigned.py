from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0002_notification_context")]

    operations = [
        migrations.RemoveConstraint(model_name="notification", name="notif_valid_event_type"),
        migrations.AlterField(
            model_name="notification", name="event_type",
            field=models.CharField(
                blank=True, null=True, max_length=32,
                choices=[
                    ("TASK_ASSIGNED", "Task Assigned"),
                    ("TASK_UNASSIGNED", "Task Unassigned"),
                    ("REVIEW_SUBMITTED", "Review Submitted"),
                    ("REVIEW_APPROVED", "Review Approved"),
                    ("REVIEW_CHANGES_REQUESTED", "Review Changes Requested"),
                    ("TASK_COMMENTED", "Task Commented"),
                ],
            ),
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                condition=models.Q(event_type__isnull=True) | models.Q(event_type__in=(
                    "TASK_ASSIGNED", "TASK_UNASSIGNED", "REVIEW_SUBMITTED", "REVIEW_APPROVED",
                    "REVIEW_CHANGES_REQUESTED", "TASK_COMMENTED",
                )),
                name="notif_valid_event_type",
            ),
        ),
    ]
