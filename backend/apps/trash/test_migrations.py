"""Trash metadata migration checks on the owned PostgreSQL test database only."""
from datetime import date, timedelta

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


def applied_leaf_targets(executor):
    applied = set(executor.loader.applied_migrations)
    return sorted(
        key for key, node in executor.loader.graph.node_map.items()
        if key in applied and not any(child.key in applied for child in node.children)
    )


class TrashMetadataMigrationTests(TransactionTestCase):
    candidates = {("workspace", "0006_soft_delete"), ("tasks", "0006_soft_delete")}

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.initial_ai_applied = ("ai", "0002_dispatch_governance") in executor.loader.applied_migrations
        self.original_targets = applied_leaf_targets(executor)
        self.addCleanup(self.restore_original)
        # Preserve every unrelated applied leaf, including the test run's
        # explicitly selected AI policy; never request a new AI migration.
        self.before = [target for target in self.original_targets
                       if target[0] not in ("workspace", "tasks")]
        self.before += [("workspace", "0005_account_invitations"), ("tasks", "0005_task_brief")]
        executor.migrate(self.before)
        self.old_apps = executor.loader.project_state(self.before).apps

    def restore_original(self):
        MigrationExecutor(connection).migrate(self.original_targets)

    def forward(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(self.original_targets)
        self.assertEqual({(item.app_label, item.name) for item, _ in plan}, self.candidates)
        self.assertTrue(all(not backwards for _, backwards in plan))
        executor.migrate(self.original_targets)
        self.assertEqual(("ai", "0002_dispatch_governance") in MigrationExecutor(connection).loader.applied_migrations,
                         self.initial_ai_applied)
        return executor.loader.project_state(self.original_targets).apps

    def fixture(self):
        apps = self.old_apps
        User = apps.get_model("accounts", "User")
        owner = User.objects.create(username="trash-migration-owner", email="owner@example.test", password="!")
        recipient = User.objects.create(username="trash-migration-recipient", email="recipient@example.test", password="!")
        profile = apps.get_model("workspace", "Profile").objects.create(name="Legacy Trash organization")
        membership = apps.get_model("workspace", "ProfileMembership").objects.create(profile=profile, user=owner, role="OWNER")
        workspace = apps.get_model("workspace", "Workspace").objects.create(profile=profile, owner=owner, name="Legacy month", period=date(2026, 11, 1))
        task = apps.get_model("tasks", "Task").objects.create(workspace=workspace, created_by=owner,
            title="Legacy approved Task", status="COMPLETED", estimated_compensation_vnd="500000")
        assignment = apps.get_model("tasks", "TaskAssignment").objects.create(task=task, user=recipient, is_active=False)
        deliverable = apps.get_model("reviews", "Deliverable").objects.create(task=task, uploaded_by=recipient,
            revision=1, status="APPROVED", file_url="https://example.test/legacy")
        review = apps.get_model("reviews", "Review").objects.create(deliverable=deliverable, reviewer=owner,
            status="APPROVED", comment="Preserve review", compensation_snapshot_recorded=True,
            compensation_snapshot_vnd="500000")
        comment = apps.get_model("tasks", "TaskComment").objects.create(task=task, user=recipient, content="Preserve comment")
        now = timezone.now()
        invitation = apps.get_model("workspace", "ProfileInvitation").objects.create(profile=profile,
            recipient_user=recipient, recipient_email_normalized=recipient.email, invited_by_membership=membership,
            requested_role="MEMBER", acceptance_kind="EMAIL_TOKEN", token_digest="a" * 64,
            expires_at=now + timedelta(days=7), delivery_status="SENT", delivery_attempted_at=now, delivered_at=now)
        audit = apps.get_model("audit", "AuditLog").objects.create(user=owner, action="task.assigned",
            entity_name="Task", entity_id=task.pk, metadata={"profile_id": str(profile.pk)})
        notice = apps.get_model("notifications", "Notification").objects.create(user=recipient, title="Legacy notice",
            message="Preserve notice", event_type="TASK_ASSIGNED", profile=profile, workspace=workspace, task=task, event=audit)
        return [profile, workspace, task, assignment, deliverable, review, comment, invitation, audit, notice, membership, owner, recipient]

    def test_populated_forward_adds_only_null_metadata_and_preserves_every_legacy_value(self):
        originals = self.fixture()
        before = {
            obj._meta.label: (obj.pk, obj.__class__.objects.filter(pk=obj.pk).values().get())
            for obj in originals if obj._meta.model_name != "user"
        }
        users_before = list(self.old_apps.get_model("accounts", "User").objects.order_by("id").values("id", "username", "is_active"))
        apps = self.forward()
        for label, (pk, values) in before.items():
            app, model = label.split(".")
            current = apps.get_model(app, model).objects.filter(pk=pk).values().get()
            self.assertEqual({name: current[name] for name in values}, values)
            if model.lower() in ("profile", "workspace", "task"):
                self.assertIsNone(current["deleted_at"])
                self.assertIsNone(current["deleted_by_id"])
                self.assertIsNone(current["purge_after"])
        self.assertEqual(list(apps.get_model("accounts", "User").objects.order_by("id").values("id", "username", "is_active")), users_before)

    def test_empty_forward_has_valid_fk_deadline_checks_and_indexes(self):
        apps = self.forward()
        User = apps.get_model("accounts", "User")
        owner = User.objects.create(username="trash-migration-constraints", email="constraints@example.test", password="!")
        Profile = apps.get_model("workspace", "Profile")
        Workspace = apps.get_model("workspace", "Workspace")
        Task = apps.get_model("tasks", "Task")
        profile = Profile.objects.create(name="Constraint organization")
        workspace = Workspace.objects.create(profile=profile, owner=owner, name="Constraint month", period=date(2026, 11, 1))
        task = Task.objects.create(workspace=workspace, created_by=owner, title="Constraint Task")
        at = timezone.now()
        for obj, prefix in ((profile, "profile"), (workspace, "workspace"), (task, "task")):
            model = type(obj)
            for changes in ({"deleted_at": at}, {"deleted_by_id": owner.pk},
                            {"deleted_at": at, "purge_after": at + timedelta(days=29)}):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    model.objects.filter(pk=obj.pk).update(**changes)
            model.objects.filter(pk=obj.pk).update(deleted_at=at, deleted_by_id=owner.pk, purge_after=at + timedelta(days=30))
            with connection.cursor() as cursor:
                constraints = connection.introspection.get_constraints(cursor, model._meta.db_table)
            self.assertTrue(constraints[f"{prefix}_trash_metadata_valid"]["check"])
            self.assertTrue(constraints[f"{prefix}_trash_due_idx"]["index"])
            self.assertTrue(any(value["foreign_key"] == ("accounts_user", "id") and value["columns"] == ["deleted_by_id"]
                                for value in constraints.values()))
            model.objects.filter(pk=obj.pk).update(deleted_at=None, deleted_by_id=None, purge_after=None)
