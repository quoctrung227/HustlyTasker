"""Candidate governance migration proofs on the owned isolated PostgreSQL DB."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models import ProtectedError
from django.db.models.expressions import RawSQL
from django.test import TransactionTestCase
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.tasks.models import Task
from apps.tasks.services import create_task
from apps.workspace.models import Workspace
from apps.workspace.services import create_profile_with_owner


OLD = ("ai", "0001_initial")
NEW = ("ai", "0002_dispatch_governance")
TABLES = ("ai_aidispatch", "ai_aibudgetbucket", "ai_aidispatchreservation")


class AIGovernanceMigrationTests(TransactionTestCase):
    def setUp(self):
        self.addCleanup(self.restore_latest)
        self.migrate(OLD)

    def restore_latest(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def fixture(self):
        actor = get_user_model().objects.create_user(
            username="governance-migration", email="governance-migration@example.test",
            password=None,
        )
        profile = create_profile_with_owner(name="Synthetic governance migration", owner=actor)
        workspace = Workspace.objects.create(
            profile=profile, owner=actor, name="Synthetic monthly Workspace", period=date(2026, 11, 1),
        )
        task = create_task(actor=actor, profile_id=profile.pk, workspace_id=workspace.pk,
                           title="Existing synthetic Task")
        return actor, profile, workspace, task

    def dispatch_values(self, actor, profile, workspace, **overrides):
        now = timezone.now()
        values = dict(
            actor_id=actor.pk, profile_id=profile.pk, workspace_id=workspace.pk,
            feature="task_plan", provider="openai", model="gpt-5.4-mini",
            execution_mode="OPENAI_OFFLINE", config_version="synthetic-v1",
            pricing_version="synthetic-v1", key_digest="a" * 64, body_digest="b" * 64,
            policy_digest="e" * 64,
            reserved_amount=Decimal("1"), input_token_limit=100, output_token_limit=100,
            created_at=now, lease_expires_at=now + timedelta(minutes=5),
        )
        return values | overrides

    def bucket_values(self, **overrides):
        return dict(
            scope="GLOBAL", execution_mode="OPENAI_OFFLINE", policy_version="synthetic-v1",
            cost_limit=Decimal("10"), reserved_amount=Decimal("1"),
            request_limit=10, concurrency_limit=2, request_count=1, active_count=1,
        ) | overrides

    def test_empty_candidate_forward_reverse_preserves_original_ai_tables(self):
        self.assertTrue(all(name not in connection.introspection.table_names() for name in TABLES))
        apps = self.migrate(NEW)
        for name in ("AiDispatch", "AiBudgetBucket", "AiDispatchReservation"):
            self.assertEqual(apps.get_model("ai", name).objects.count(), 0)
        self.migrate(OLD)
        self.assertTrue(all(name not in connection.introspection.table_names() for name in TABLES))
        self.assertIn("ai_aiproposal", connection.introspection.table_names())
        self.assertIn("ai_aioperation", connection.introspection.table_names())

    def test_legacy_fixture_and_related_rows_survive_candidate_forward_reverse(self):
        actor, profile, workspace, task = self.fixture()
        old_apps = self.migrate(OLD)
        Proposal = old_apps.get_model("ai", "AiProposal")
        Operation = old_apps.get_model("ai", "AiOperation")
        now = timezone.now()
        proposal = Proposal.objects.create(
            actor_id=actor.pk, profile_id=profile.pk, workspace_id=workspace.pk,
            scenario_id="subtitle-check-v1", payload={"synthetic": True},
            created_at=now, expires_at=now + timedelta(minutes=30),
            payload_expires_at=now + timedelta(days=7),
        )
        Operation.objects.create(
            actor_id=actor.pk, profile_id=profile.pk, workspace_id=workspace.pk,
            proposal_id=proposal.pk, operation="GENERATE", key_digest="c" * 64, body_digest="d" * 64,
        )
        before = (list(Proposal.objects.values()), list(Operation.objects.values()),
                  list(Task.objects.values()), list(AuditLog.objects.order_by("id").values()))
        with connection.cursor() as cursor:
            original_columns = {
                name: connection.introspection.get_table_description(cursor, name)
                for name in ("ai_aiproposal", "ai_aioperation")
            }
        apps = self.migrate(NEW)
        Dispatch = apps.get_model("ai", "AiDispatch")
        Budget = apps.get_model("ai", "AiBudgetBucket")
        Reservation = apps.get_model("ai", "AiDispatchReservation")
        self.assertEqual(Dispatch.objects.count(), 0)  # No invented backfill.
        dispatch = Dispatch.objects.create(**self.dispatch_values(
            actor, profile, workspace, proposal_id=proposal.pk,
            execution_mode="FIXTURE", provider="fixture", model="deterministic-fixture-v1",
        ))
        budget = Budget.objects.create(**self.bucket_values(execution_mode="FIXTURE"))
        Reservation.objects.create(dispatch_id=dispatch.pk, bucket_id=budget.pk, amount=Decimal("1"))
        self.migrate(OLD)
        self.assertEqual((list(Proposal.objects.values()), list(Operation.objects.values()),
                          list(Task.objects.values()), list(AuditLog.objects.order_by("id").values())), before)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=actor.pk).exists())
        with connection.cursor() as cursor:
            for name, columns in original_columns.items():
                self.assertEqual(connection.introspection.get_table_description(cursor, name), columns)

    def test_dispatch_lifecycle_provenance_and_identity_constraints(self):
        actor, profile, workspace, _ = self.fixture()
        apps = self.migrate(NEW)
        Dispatch = apps.get_model("ai", "AiDispatch")
        values = self.dispatch_values(actor, profile, workspace)
        for invalid in (
            {"status": "LIVE_SUCCESS"}, {"status": "DISPATCHING"}, {"status": "SUCCEEDED"},
            {"status": "OUTCOME_UNKNOWN"}, {"status": "RECONCILED"},
            {"execution_mode": "OPENAI_OFFLINE", "billed_cost": Decimal("1")},
            {"usage_status": "REPORTED"}, {"provider": "fixture"},
            {"key_digest": "not-a-digest"}, {"body_digest": "z" * 64},
            {"settlement_digest": "not-a-digest"}, {"reserved_amount": Decimal("-1")},
            {"policy_digest": "not-a-digest"},
            {"accounted_amount": Decimal("2")}, {"input_token_limit": 0},
            {"output_tokens": 10}, {"input_tokens": -1, "output_tokens": 0},
            {"lease_expires_at": values["created_at"]},
            {"status": "SUCCEEDED", "dispatched_at": values["created_at"],
             "completed_at": values["created_at"], "claim_id": uuid4(),
             "accounted_amount": Decimal("0"), "usage_status": "UNKNOWN"},
            {"status": "SUCCEEDED", "dispatched_at": values["created_at"],
             "completed_at": values["created_at"], "claim_id": uuid4(),
             "accounted_amount": Decimal("0"), "usage_status": "SIMULATED"},
        ):
            with self.subTest(invalid=tuple(invalid)), self.assertRaises(IntegrityError), transaction.atomic():
                Dispatch.objects.create(**(values | invalid))
        Dispatch.objects.create(**values)
        # Changing a model/config does not create a second lane for the same key.
        with self.assertRaises(IntegrityError), transaction.atomic():
            Dispatch.objects.create(**(values | {"config_version": "synthetic-v2", "model": "gpt-5.4-mini-2026-03-17"}))

    def test_budget_scope_limits_nan_and_stable_identity_constraints(self):
        apps = self.migrate(NEW)
        Budget = apps.get_model("ai", "AiBudgetBucket")
        values = self.bucket_values()
        for invalid in (
            {"scope": "INVALID"}, {"scope": "PROFILE"}, {"scope": "USER"},
            {"execution_mode": "INVALID"}, {"policy_version": ""},
            {"reserved_amount": Decimal("-1")}, {"accounted_amount": Decimal("-1")},
            {"cost_limit": Decimal("0.5")}, {"request_count": 11},
            {"active_count": 3}, {"active_count": 2, "request_count": 1},
        ):
            with self.subTest(invalid=tuple(invalid)), self.assertRaises(IntegrityError), transaction.atomic():
                Budget.objects.create(**(values | invalid))
        budget = Budget.objects.create(**values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Budget.objects.create(**(values | {"policy_version": "synthetic-v2"}))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Budget.objects.filter(pk=budget.pk).update(cost_limit=RawSQL("'NaN'::numeric", []))

    def test_reservation_uniqueness_amount_lifecycle_and_protect(self):
        actor, profile, workspace, _ = self.fixture()
        apps = self.migrate(NEW)
        Dispatch = apps.get_model("ai", "AiDispatch")
        Budget = apps.get_model("ai", "AiBudgetBucket")
        Reservation = apps.get_model("ai", "AiDispatchReservation")
        dispatch = Dispatch.objects.create(**self.dispatch_values(actor, profile, workspace))
        bucket = Budget.objects.create(**self.bucket_values())
        values = dict(dispatch_id=dispatch.pk, bucket_id=bucket.pk, amount=Decimal("1"))
        for invalid in ({"amount": Decimal("-1")}, {"settled_amount": Decimal("0")},
                        {"status": "SETTLED"}, {"status": "RELEASED"},
                        {"status": "SETTLED", "settled_amount": Decimal("2")}):
            with self.subTest(invalid=tuple(invalid)), self.assertRaises(IntegrityError), transaction.atomic():
                Reservation.objects.create(**(values | invalid))
        Reservation.objects.create(**values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reservation.objects.create(**values)
        with self.assertRaises(ProtectedError):
            bucket.delete()
        with self.assertRaises(ProtectedError):
            dispatch.delete()

    def test_candidate_constraints_and_lookup_indexes_exist(self):
        self.migrate(NEW)
        expected = {
            "ai_aidispatch": ("ai_disp_identity_unique", "ai_disp_lifecycle", "ai_disp_no_simulated_bill", "ai_disp_actor_scope_idx", "ai_disp_lease_idx"),
            "ai_aibudgetbucket": ("ai_budget_global_unique", "ai_budget_profile_unique", "ai_budget_user_unique", "ai_budget_total_limit"),
            "ai_aidispatchreservation": ("ai_res_dispatch_bucket_unique", "ai_res_lifecycle"),
        }
        with connection.cursor() as cursor:
            for table, names in expected.items():
                constraints = connection.introspection.get_constraints(cursor, table)
                self.assertTrue(all(name in constraints for name in names))
            cursor.execute("SELECT bool_and(convalidated) FROM pg_constraint WHERE conrelid = ANY(%s::regclass[])", [list(TABLES)])
            self.assertIs(cursor.fetchone()[0], True)
            cursor.execute("SELECT bool_and(indisvalid AND indisready) FROM pg_index WHERE indrelid = ANY(%s::regclass[])", [list(TABLES)])
            self.assertIs(cursor.fetchone()[0], True)
