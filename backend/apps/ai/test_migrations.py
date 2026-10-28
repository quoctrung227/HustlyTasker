"""Additive AI migration/reversal proofs on the owned isolated test database."""

from datetime import date, timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.tasks.models import Task
from apps.tasks.services import create_task
from apps.workspace.models import Workspace
from apps.workspace.services import create_profile_with_owner


class AIFoundationMigrationTests(TransactionTestCase):
    def setUp(self):
        self.addCleanup(self.restore_latest)
        MigrationExecutor(connection).migrate([("ai", None)])

    def restore_latest(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def forward(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("ai", "0001_initial")])
        return executor.loader.project_state([("ai", "0001_initial")]).apps

    def business_fixture(self):
        owner = get_user_model().objects.create_user(
            username="ai-migration-owner", email="ai-migration@example.test", password=None,
        )
        profile = create_profile_with_owner(name="Synthetic migration profile", owner=owner)
        workspace = Workspace.objects.create(profile=profile, owner=owner,
                                             name="Synthetic migration workspace", period=date(2026, 10, 1))
        task = create_task(actor=owner, profile_id=profile.pk, workspace_id=workspace.pk,
                           title="Existing synthetic Task")
        return owner, profile, workspace, task

    def test_empty_ai_schema_forward_reverse_and_original_chain(self):
        self.assertNotIn("ai_aiproposal", connection.introspection.table_names())
        apps = self.forward()
        self.assertEqual(apps.get_model("ai", "AiProposal").objects.count(), 0)
        self.assertEqual(apps.get_model("ai", "AiOperation").objects.count(), 0)
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "ai_aioperation")
        self.assertTrue(constraints["ai_op_scope_key_unique"]["unique"])
        self.assertTrue(constraints["ai_op_one_confirm_per_prop"]["unique"])
        MigrationExecutor(connection).migrate([("ai", None)])
        self.assertNotIn("ai_aiproposal", connection.introspection.table_names())
        self.assertIn("tasks_task", connection.introspection.table_names())

    def test_related_business_rows_survive_forward_and_reverse_with_ai_data(self):
        owner, profile, workspace, task = self.business_fixture()
        before_tasks = list(Task.objects.values())
        before_audits = list(AuditLog.objects.order_by("id").values())
        apps = self.forward()
        Proposal = apps.get_model("ai", "AiProposal")
        Operation = apps.get_model("ai", "AiOperation")
        now = timezone.now()
        proposal = Proposal.objects.create(
            actor_id=owner.pk, profile_id=profile.pk, workspace_id=workspace.pk,
            scenario_id="subtitle-check-v1", payload={"synthetic": True},
            created_at=now, expires_at=now + timedelta(minutes=30),
            payload_expires_at=now + timedelta(days=7),
        )
        Operation.objects.create(actor_id=owner.pk, profile_id=profile.pk,
                                 workspace_id=workspace.pk, proposal_id=proposal.pk,
                                 operation="GENERATE", key_digest="a" * 64, body_digest="b" * 64)
        MigrationExecutor(connection).migrate([("ai", None)])
        self.assertEqual(list(Task.objects.values()), before_tasks)
        self.assertEqual(list(AuditLog.objects.order_by("id").values()), before_audits)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=owner.pk).exists())
        apps = self.forward()
        self.assertEqual(apps.get_model("ai", "AiProposal").objects.count(), 0)

    def test_database_lifecycle_and_idempotency_constraints(self):
        owner, profile, workspace, _ = self.business_fixture()
        apps = self.forward()
        Proposal = apps.get_model("ai", "AiProposal")
        Operation = apps.get_model("ai", "AiOperation")
        now = timezone.now()
        values = dict(actor_id=owner.pk, profile_id=profile.pk, workspace_id=workspace.pk,
                      scenario_id="subtitle-check-v1", created_at=now,
                      expires_at=now + timedelta(minutes=30), payload_expires_at=now + timedelta(days=7))
        for invalid in ({"status": "INVALID"}, {"revision": 0},
                        {"expires_at": now}, {"created_tasks": {"item_1": str(uuid4())}},
                        {"status": "CONFIRMED"}):
            with self.subTest(invalid=tuple(invalid)), self.assertRaises(IntegrityError), transaction.atomic():
                Proposal.objects.create(**(values | invalid))
        proposal = Proposal.objects.create(**values)
        op = dict(actor_id=owner.pk, profile_id=profile.pk, workspace_id=workspace.pk,
                  proposal_id=proposal.pk, operation="GENERATE", key_digest="c" * 64, body_digest="d" * 64)
        Operation.objects.create(**op)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Operation.objects.create(**op)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Operation.objects.create(**(op | {"operation": "INVALID", "key_digest": "e" * 64}))
