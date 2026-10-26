import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0003_task_hierarchy")]

    operations = [
        migrations.AddField(
            model_name="taskcomment", name="edited_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskcomment", name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="taskcomment", name="task",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                    related_name="comments", to="tasks.task"),
        ),
        migrations.AlterField(
            model_name="taskcomment", name="content",
            field=models.TextField(validators=[django.core.validators.MaxLengthValidator(4000)]),
        ),
        migrations.AddConstraint(
            model_name="taskcomment",
            constraint=models.CheckConstraint(
                condition=models.Q(edited_at__isnull=True) | models.Q(edited_at__gte=models.F("created_at")),
                name="comment_edit_after_create",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskcomment",
            constraint=models.CheckConstraint(
                condition=models.Q(deleted_at__isnull=True) | models.Q(deleted_at__gte=models.F("created_at")),
                name="comment_delete_after_create",
            ),
        ),
        migrations.AddIndex(
            model_name="taskcomment",
            index=models.Index(fields=["task", "created_at", "id"], name="comment_task_created_id_idx"),
        ),
    ]
