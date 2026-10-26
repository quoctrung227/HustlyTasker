import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0002_task_workflow_foundation")]

    operations = [
        migrations.AddField(
            model_name="task",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subtasks",
                to="tasks.task",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=~models.Q(id=models.F("parent_id")),
                name="task_not_own_parent",
            ),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(
                fields=["workspace", "parent", "created_at"],
                name="task_ws_parent_created_idx",
            ),
        ),
    ]
