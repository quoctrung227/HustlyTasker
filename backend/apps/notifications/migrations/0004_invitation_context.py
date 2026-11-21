import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_task_unassigned"),
        ("workspace", "0005_account_invitations"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="notification", name="notif_context_complete"),
        migrations.RemoveConstraint(model_name="notification", name="notif_valid_event_type"),
        migrations.AddField(
            model_name="notification", name="invitation",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="notifications", to="workspace.profileinvitation",
            ),
        ),
        migrations.AlterField(
            model_name="notification", name="event_type",
            field=models.CharField(blank=True, null=True, max_length=32, choices=[
                ("TASK_ASSIGNED", "Task Assigned"),
                ("TASK_UNASSIGNED", "Task Unassigned"),
                ("REVIEW_SUBMITTED", "Review Submitted"),
                ("REVIEW_APPROVED", "Review Approved"),
                ("REVIEW_CHANGES_REQUESTED", "Review Changes Requested"),
                ("TASK_COMMENTED", "Task Commented"),
                ("PROFILE_INVITED", "Profile Invited"),
            ]),
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(event_type__isnull=True, profile__isnull=True,
                             workspace__isnull=True, task__isnull=True, event__isnull=True,
                             invitation__isnull=True)
                    | models.Q(event_type__in=(
                        "TASK_ASSIGNED", "TASK_UNASSIGNED", "REVIEW_SUBMITTED", "REVIEW_APPROVED",
                        "REVIEW_CHANGES_REQUESTED", "TASK_COMMENTED",
                    ), event_type__isnull=False, profile__isnull=False, workspace__isnull=False, task__isnull=False,
                        event__isnull=False, invitation__isnull=True)
                    | models.Q(event_type="PROFILE_INVITED", event_type__isnull=False, profile__isnull=False,
                               workspace__isnull=True, task__isnull=True, event__isnull=False,
                               invitation__isnull=False)
                ),
                name="notif_context_complete",
            ),
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                condition=models.Q(event_type__isnull=True) | models.Q(event_type__in=(
                    "TASK_ASSIGNED", "TASK_UNASSIGNED", "REVIEW_SUBMITTED", "REVIEW_APPROVED",
                    "REVIEW_CHANGES_REQUESTED", "TASK_COMMENTED", "PROFILE_INVITED",
                )),
                name="notif_valid_event_type",
            ),
        ),
    ]
