"""Durable fixture workflow, rollback and concurrency on isolated PostgreSQL.

No live provider or persistent-development connection is used by these tests.
They exercise current tenant services rather than granting authority from DTOs.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, timedelta, timezone as datetime_timezone
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.reviews.models import Deliverable, Review
from apps.tasks.models import Task, TaskAssignment
from apps.tasks.services import create_task
from apps.workspace.access import TenantAccessNotFound
from apps.workspace.models import ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import (
    archive_profile, archive_workspace, create_profile_with_owner,
    revoke_workspace_member, update_profile_membership,
)

from . import durable_services
from .errors import AIError, ErrorCode
from .models import AiOperation, AiProposal
from .providers import FixtureAdapter


User = get_user_model()
FIXTURE_SETTINGS = {
    "AI_FIXTURE_ENABLED": True, "ENVIRONMENT": "development", "IS_PRODUCTION": False,
}


def node(ref="item_1", parent=None, title="Synthetic task", **values):
    result = {
        "local_ref": ref, "parent_ref": parent, "title": title,
        "description": "Synthetic description", "priority": "MEDIUM",
        "proposed_deadline": None, "notes": "",
    }
    result.update(values)
    return result


def plan(nodes=None):
    return {
        "contract_version": "ai.task-plan.v1",
        "tasks": nodes if nodes is not None else [node()],
        "assumptions": [], "warnings": [],
    }


class DurableDataMixin:
    def setup_data(self, prefix):
        def user(suffix):
            return User.objects.create_user(
                username=f"{prefix}-{suffix}", email=f"{prefix}-{suffix}@example.test",
                password=None,
            )

        self.owner = user("owner")
        self.admin = user("admin")
        self.manager = user("manager")
        self.editor = user("editor")
        self.viewer = user("viewer")
        self.staff = user("staff")
        self.staff.is_staff = True
        self.staff.save(update_fields=("is_staff",))
        self.profile = create_profile_with_owner(name="Synthetic AI Profile", owner=self.owner)
        self.workspace = Workspace.objects.create(
            profile=self.profile, owner=self.owner, name="Synthetic October",
            period=date(2026, 10, 1),
        )
        self.other_workspace = Workspace.objects.create(
            profile=self.profile, owner=self.owner, name="Synthetic November",
            period=date(2026, 11, 1),
        )
        self.admin_membership = ProfileMembership.objects.create(
            profile=self.profile, user=self.admin, role=ProfileMembership.Role.ADMIN,
        )
        for actor, role in (
            (self.manager, WorkspaceMember.Role.ADMIN),
            (self.editor, WorkspaceMember.Role.MEMBER),
            (self.viewer, WorkspaceMember.Role.VIEWER),
        ):
            membership = ProfileMembership.objects.create(
                profile=self.profile, user=actor, role=ProfileMembership.Role.MEMBER,
            )
            workspace_membership = WorkspaceMember.objects.create(
                workspace=self.workspace, user=actor, role=role,
            )
            if actor == self.manager:
                self.manager_membership = membership
                self.manager_workspace_membership = workspace_membership
        self.other_profile = create_profile_with_owner(
            name="Second synthetic AI Profile", owner=self.owner,
        )
        self.foreign_workspace = Workspace.objects.create(
            profile=self.other_profile, owner=self.owner, name="Second Profile October",
            period=date(2026, 10, 1),
        )

    def scope(self, actor=None, workspace=None):
        workspace = workspace or self.workspace
        return {
            "actor": actor or self.owner, "profile_id": workspace.profile_id,
            "workspace_id": workspace.id,
        }

    def generate(self, actor=None, workspace=None, key=None, scenario="subtitle-check-v1"):
        return durable_services.generate_proposal(
            **self.scope(actor, workspace), scenario_id=scenario,
            idempotency_key=str(key or uuid4()),
        )

    def confirm(self, proposal, *, payload=None, actor=None, workspace=None,
                key=None, revision=1, confirmed=True):
        return durable_services.confirm_proposal(
            **self.scope(actor, workspace), proposal_id=proposal.id,
            idempotency_key=str(key or uuid4()), proposal_revision=revision,
            payload=deepcopy(proposal.payload) if payload is None else payload,
            confirmed=confirmed,
        )

    def retrieve(self, proposal, actor=None, workspace=None):
        return durable_services.retrieve_proposal(
            **self.scope(actor, workspace), proposal_id=proposal.id,
        )

    def assert_code(self, code, callback):
        with self.assertRaises(AIError) as caught:
            callback()
        self.assertEqual(caught.exception.code.value, code)
        return caught.exception


@override_settings(**FIXTURE_SETTINGS)
class DurableProposalServiceTests(DurableDataMixin, TestCase):
    def setUp(self):
        self.setup_data("ai-durable")

    def test_generate_persists_scoped_validated_proposal_without_business_creation(self):
        audits_before = AuditLog.objects.count()
        proposal, replayed = self.generate(scenario="task-tree-v1")
        self.assertFalse(replayed)
        self.assertEqual(proposal.status, "AVAILABLE")
        self.assertEqual(proposal.actor_id, self.owner.id)
        self.assertEqual(proposal.profile_id, self.profile.id)
        self.assertEqual(proposal.workspace_id, self.workspace.id)
        self.assertEqual(proposal.revision, 1)
        self.assertEqual(proposal.payload["contract_version"], "ai.task-plan.v1")
        self.assertEqual(proposal.expires_at - proposal.created_at, timedelta(minutes=30))
        self.assertEqual(proposal.payload_expires_at - proposal.created_at, timedelta(days=7))
        self.assertEqual(AiProposal.objects.count(), 1)
        self.assertEqual(AiOperation.objects.count(), 1)
        self.assertEqual(AuditLog.objects.count(), audits_before)
        for model in (Task, TaskAssignment, Deliverable, Review, Notification):
            self.assertEqual(model.objects.count(), 0)

    def test_generation_same_key_reuses_proposal_and_does_not_call_fixture_again(self):
        key = uuid4()
        first, _ = self.generate(key=key)
        with patch.object(FixtureAdapter, "generate", side_effect=AssertionError("No redispatch")):
            second, replayed = self.generate(key=key)
        self.assertTrue(replayed)
        self.assertEqual(first.id, second.id)
        self.assertEqual(AiProposal.objects.count(), 1)
        self.assertEqual(AiOperation.objects.count(), 1)

    def test_generation_same_key_changed_valid_scenario_conflicts(self):
        key = uuid4()
        self.generate(key=key)
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.generate(key=key, scenario="task-tree-v1"))
        self.assertEqual(AiProposal.objects.count(), 1)

    def test_invalid_scenario_does_not_persist_operation_or_proposal(self):
        self.assert_code("VALIDATION_ERROR", lambda: self.generate(scenario="unknown-synthetic-scenario"))
        self.assertEqual(AiProposal.objects.count(), 0)
        self.assertEqual(AiOperation.objects.count(), 0)

    def test_generation_key_is_scoped_to_actor(self):
        key = uuid4()
        owner_proposal, _ = self.generate(key=key)
        admin_proposal, replayed = self.generate(actor=self.admin, key=key)
        self.assertFalse(replayed)
        self.assertNotEqual(owner_proposal.id, admin_proposal.id)
        self.assertEqual(AiOperation.objects.count(), 2)

    def test_generation_key_is_scoped_to_workspace_and_profile(self):
        key = uuid4()
        first, _ = self.generate(key=key)
        second, _ = self.generate(key=key, workspace=self.other_workspace)
        third, _ = self.generate(key=key, workspace=self.foreign_workspace)
        self.assertEqual(len({first.id, second.id, third.id}), 3)
        self.assertEqual(AiOperation.objects.count(), 3)

    def test_manager_gate_allows_existing_owner_admin_and_workspace_admin(self):
        for actor in (self.owner, self.admin, self.manager):
            with self.subTest(role=actor.username):
                proposal, _ = self.generate(actor=actor)
                self.assertEqual(self.retrieve(proposal, actor).id, proposal.id)

    def test_editor_viewer_staff_cannot_gain_generation_authority(self):
        for actor in (self.editor, self.viewer, self.staff):
            with self.subTest(role=actor.username), self.assertRaises((PermissionDenied, TenantAccessNotFound)):
                self.generate(actor=actor)
        self.assertEqual(AiProposal.objects.count(), 0)

    def test_other_manager_cannot_read_or_confirm_actor_bound_proposal(self):
        proposal, _ = self.generate()
        for callback in (
            lambda: self.retrieve(proposal, self.admin),
            lambda: self.confirm(proposal, actor=self.admin),
        ):
            with self.assertRaises(TenantAccessNotFound):
                callback()
        self.assertEqual(Task.objects.count(), 0)

    def test_cross_workspace_and_profile_proposal_references_are_not_visible(self):
        proposal, _ = self.generate()
        for workspace in (self.other_workspace, self.foreign_workspace):
            with self.subTest(workspace=workspace.id):
                with self.assertRaises(TenantAccessNotFound):
                    self.retrieve(proposal, workspace=workspace)
                with self.assertRaises(TenantAccessNotFound):
                    self.confirm(proposal, workspace=workspace)

    def test_revoked_workspace_membership_blocks_read_confirm_and_recovery(self):
        proposal, _ = self.generate(actor=self.manager)
        payload = deepcopy(proposal.payload)
        key = uuid4()
        self.confirm(proposal, actor=self.manager, key=key, payload=payload)
        revoke_workspace_member(
            actor=self.owner, profile_id=self.profile.id, workspace_id=self.workspace.id,
            membership_id=self.manager_workspace_membership.id,
        )
        for callback in (
            lambda: self.retrieve(proposal, self.manager),
            lambda: self.confirm(proposal, actor=self.manager, key=key, payload=payload),
        ):
            with self.assertRaises((PermissionDenied, TenantAccessNotFound)):
                callback()
        self.assertEqual(Task.objects.count(), 1)

    def test_inactive_profile_membership_blocks_existing_proposal(self):
        proposal, _ = self.generate(actor=self.manager)
        update_profile_membership(
            actor=self.owner, profile_id=self.profile.id,
            membership_id=self.manager_membership.id, is_active=False,
        )
        with self.assertRaises((PermissionDenied, TenantAccessNotFound)):
            self.retrieve(proposal, self.manager)
        with self.assertRaises((PermissionDenied, TenantAccessNotFound)):
            self.confirm(proposal, actor=self.manager)
        self.assertEqual(Task.objects.count(), 0)

    def test_archived_workspace_blocks_generate_retrieve_confirm(self):
        proposal, _ = self.generate()
        archive_workspace(actor=self.owner, profile_id=self.profile.id, workspace_id=self.workspace.id)
        for callback in (lambda: self.generate(), lambda: self.retrieve(proposal), lambda: self.confirm(proposal)):
            with self.assertRaises(PermissionDenied):
                callback()
        self.assertEqual(Task.objects.count(), 0)

    def test_archived_profile_blocks_existing_proposal(self):
        proposal, _ = self.generate()
        archive_profile(actor=self.owner, profile_id=self.profile.id)
        with self.assertRaises(PermissionDenied):
            self.retrieve(proposal)
        with self.assertRaises(PermissionDenied):
            self.confirm(proposal)

    def test_confirm_revalidates_and_creates_topologically_with_original_services(self):
        proposal, _ = self.generate()
        payload = plan([
            node("item_3", "item_2", "Synthetic grandchild"),
            node("item_2", "item_1", "Synthetic child", priority="HIGH"),
            node("item_1", title="Synthetic root", proposed_deadline="2026-11-01T14:00:00+07:00"),
        ])
        with patch.object(FixtureAdapter, "generate", side_effect=AssertionError("No fixture during confirmation")):
            confirmed, replayed = self.confirm(proposal, payload=payload)
        self.assertFalse(replayed)
        self.assertEqual(confirmed.status, "CONFIRMED")
        self.assertIsNone(confirmed.payload)
        self.assertEqual(set(confirmed.created_tasks), {"item_1", "item_2", "item_3"})
        root = Task.objects.get(pk=confirmed.created_tasks["item_1"])
        child = Task.objects.get(pk=confirmed.created_tasks["item_2"])
        grandchild = Task.objects.get(pk=confirmed.created_tasks["item_3"])
        self.assertIsNone(root.parent_id)
        self.assertEqual(child.parent_id, root.id)
        self.assertEqual(grandchild.parent_id, child.id)
        self.assertEqual(root.deadline.isoformat(), "2026-11-01T07:00:00+00:00")
        self.assertEqual(root.deadline.tzinfo, datetime_timezone.utc)
        for task in (root, child, grandchild):
            self.assertEqual(task.status, Task.Status.PENDING)
            self.assertEqual(task.created_by_id, self.owner.id)
            self.assertEqual(task.workspace_id, self.workspace.id)
        self.assertEqual(TaskAssignment.objects.count(), 0)
        self.assertEqual(Deliverable.objects.count(), 0)
        self.assertEqual(Review.objects.count(), 0)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(action="task.created").count(), 3)
        self.assertEqual(confirmed.recovery_expires_at - confirmed.confirmed_at, timedelta(days=30))

    def test_confirm_same_key_body_recovers_same_mapping_without_new_tasks(self):
        proposal, _ = self.generate()
        payload = deepcopy(proposal.payload)
        key = uuid4()
        first, replayed = self.confirm(proposal, key=key, payload=payload)
        self.assertFalse(replayed)
        second, replayed = self.confirm(proposal, key=key, payload=deepcopy(payload))
        self.assertTrue(replayed)
        self.assertEqual(first.created_tasks, second.created_tasks)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="task.created").count(), 1)

    def test_confirm_changed_canonical_body_conflicts(self):
        proposal, _ = self.generate()
        payload = deepcopy(proposal.payload)
        key = uuid4()
        self.confirm(proposal, key=key, payload=payload)
        changed = deepcopy(payload)
        changed["tasks"][0]["title"] = "Changed synthetic title"
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.confirm(proposal, key=key, payload=changed))
        self.assertEqual(Task.objects.count(), 1)

    def test_confirm_canonical_object_key_order_does_not_change_request_identity(self):
        proposal, _ = self.generate()
        payload = deepcopy(proposal.payload)
        key = uuid4()
        self.confirm(proposal, key=key, payload=payload)
        reordered = dict(reversed(tuple(payload.items())))
        reordered["tasks"] = [dict(reversed(tuple(item.items()))) for item in payload["tasks"]]
        _, replayed = self.confirm(proposal, key=key, payload=reordered)
        self.assertTrue(replayed)
        self.assertEqual(Task.objects.count(), 1)

    def test_different_confirmation_key_cannot_create_second_batch(self):
        proposal, _ = self.generate()
        payload = deepcopy(proposal.payload)
        self.confirm(proposal, payload=payload)
        self.assert_code("ALREADY_CONFIRMED", lambda: self.confirm(proposal, payload=payload))
        self.assertEqual(Task.objects.count(), 1)

    def test_idempotency_key_is_scoped_by_operation(self):
        key = uuid4()
        proposal, _ = self.generate(key=key)
        confirmed, replayed = self.confirm(proposal, key=key)
        self.assertFalse(replayed)
        self.assertEqual(confirmed.status, "CONFIRMED")
        self.assertEqual(AiOperation.objects.count(), 2)

    def test_same_confirm_key_cannot_be_reused_for_a_different_proposal(self):
        first, _ = self.generate()
        second, _ = self.generate()
        payload = deepcopy(first.payload)
        key = uuid4()
        self.confirm(first, key=key, payload=payload)
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.confirm(second, key=key, payload=payload))
        self.assertEqual(Task.objects.count(), 1)
        second.refresh_from_db()
        self.assertEqual(second.status, "AVAILABLE")

    def test_stale_revision_and_nonexplicit_confirmation_do_not_create(self):
        proposal, _ = self.generate()
        self.assert_code("STALE_PROPOSAL", lambda: self.confirm(proposal, revision=2))
        for value in (False, 1, "true", None):
            with self.subTest(confirmed=value):
                self.assert_code("VALIDATION_ERROR", lambda: self.confirm(proposal, confirmed=value))
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(AiOperation.objects.count(), 1)

    def test_expired_unconfirmed_preview_cannot_create_tasks(self):
        proposal, _ = self.generate()
        later = proposal.expires_at + timedelta(seconds=1)
        with patch("apps.ai.durable_services.timezone.now", return_value=later):
            current = self.retrieve(proposal)
            self.assertIsNone(current.payload)
            self.assert_code("EXPIRED", lambda: self.confirm(proposal, payload=plan()))
        self.assertEqual(Task.objects.count(), 0)

    def test_generation_replay_after_expiry_does_not_redispatch_or_extend_lifetime(self):
        key = uuid4()
        proposal, _ = self.generate(key=key)
        with patch("apps.ai.durable_services.timezone.now", return_value=proposal.expires_at + timedelta(seconds=1)):
            with patch.object(FixtureAdapter, "generate", side_effect=AssertionError("No redispatch")):
                self.assert_code("EXPIRED", lambda: self.generate(key=key))
        proposal.refresh_from_db()
        self.assertEqual(AiProposal.objects.count(), 1)
        self.assertEqual(Task.objects.count(), 0)

    def test_confirmation_result_recovery_after_preview_expiry(self):
        proposal, _ = self.generate()
        payload = deepcopy(proposal.payload)
        key = uuid4()
        confirmed, _ = self.confirm(proposal, key=key, payload=payload)
        later = proposal.expires_at + timedelta(minutes=1)
        with patch("apps.ai.durable_services.timezone.now", return_value=later):
            recovered, replayed = self.confirm(proposal, key=key, payload=payload)
            read = self.retrieve(proposal)
        self.assertTrue(replayed)
        self.assertEqual(recovered.created_tasks, confirmed.created_tasks)
        self.assertEqual(read.created_tasks, confirmed.created_tasks)
        self.assertEqual(Task.objects.count(), 1)

    def test_recovery_window_expiry_does_not_resurrect_confirmation_under_any_key(self):
        proposal, _ = self.generate()
        payload = deepcopy(proposal.payload)
        key = uuid4()
        confirmed, _ = self.confirm(proposal, key=key, payload=payload)
        later = confirmed.recovery_expires_at + timedelta(seconds=1)
        with patch("apps.ai.durable_services.timezone.now", return_value=later):
            self.assert_code("RECOVERY_EXPIRED", lambda: self.retrieve(proposal))
            self.assert_code("RECOVERY_EXPIRED", lambda: self.confirm(proposal, key=key, payload=payload))
            self.assert_code("ALREADY_CONFIRMED", lambda: self.confirm(proposal, payload=payload))
        self.assertEqual(Task.objects.count(), 1)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "CONFIRMED")

    def test_unconfirmed_payload_retention_window_does_not_extend_confirmation(self):
        proposal, _ = self.generate()
        with patch("apps.ai.durable_services.timezone.now", return_value=proposal.payload_expires_at + timedelta(seconds=1)):
            hidden = self.retrieve(proposal)
            self.assertIsNone(hidden.payload)
            self.assert_code("EXPIRED", lambda: self.confirm(proposal, payload=plan()))
        self.assertEqual(Task.objects.count(), 0)
        # Logical omission is tested; no claim that physical purge has run.
        self.assertTrue(AiProposal.objects.filter(pk=proposal.pk).exists())

    def test_invalid_edited_plans_revalidate_before_any_task_or_operation(self):
        proposal, _ = self.generate()
        invalid = []
        bad_priority = plan()
        bad_priority["tasks"][0]["priority"] = "CRITICAL"
        invalid.append(bad_priority)
        invalid.append(plan([node("item_1", "item_1")]))
        invalid.append(plan([node("item_1", "item_2"), node("item_2", "item_1")]))
        invalid.append(plan([node(f"item_{i}", f"item_{i-1}" if i > 1 else None) for i in range(1, 6)]))
        invalid.append(plan([node(), node()]))
        injected = plan()
        injected["tasks"][0]["assignee_id"] = str(self.editor.id)
        invalid.append(injected)
        for payload in invalid:
            with self.subTest(payload_shape=len(payload["tasks"])):
                self.assert_code("VALIDATION_ERROR", lambda: self.confirm(proposal, payload=payload))
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(AiOperation.objects.count(), 1)

    def test_twenty_nodes_allowed_but_twenty_one_rejected_without_partial_batch(self):
        too_large, _ = self.generate()
        self.assert_code("VALIDATION_ERROR", lambda: self.confirm(
            too_large, payload=plan([node(f"item_{i}") for i in range(1, 22)]),
        ))
        self.assertEqual(Task.objects.count(), 0)
        accepted, _ = self.generate()
        confirmed, _ = self.confirm(accepted, payload=plan([node(f"item_{i}") for i in range(1, 21)]))
        self.assertEqual(len(confirmed.created_tasks), 20)
        self.assertEqual(Task.objects.count(), 20)

    def test_task_audit_failure_rolls_back_tasks_confirmation_and_operation(self):
        proposal, _ = self.generate()
        with patch("apps.tasks.services._write_audit", side_effect=RuntimeError("Synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.confirm(proposal, payload=plan([node(), node("item_2", "item_1")]))
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "AVAILABLE")
        self.assertIsNone(proposal.created_tasks)
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(AiOperation.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="task.created").count(), 0)

    def test_confirmation_audit_failure_rolls_back_completed_batch_and_outcome(self):
        proposal, _ = self.generate()
        payload = plan([node(), node("item_2", "item_1")])
        audit_count = AuditLog.objects.count()
        with patch("apps.ai.durable_services.create_task", wraps=create_task) as create:
            with patch("apps.ai.durable_services._audit", side_effect=RuntimeError("Synthetic confirmation audit failure")):
                with self.assertRaises(RuntimeError):
                    self.confirm(proposal, payload=payload)
        self.assertEqual(create.call_count, 2)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "AVAILABLE")
        self.assertIsNone(proposal.confirmed_at)
        self.assertIsNone(proposal.recovery_expires_at)
        self.assertIsNone(proposal.created_tasks)
        self.assertIsNotNone(proposal.payload)
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(AiOperation.objects.count(), 1)
        self.assertEqual(AuditLog.objects.count(), audit_count)

    def test_stale_active_actor_cannot_read_confirm_or_recover_after_database_deactivation(self):
        pending, _ = self.generate()
        consumed, _ = self.generate()
        payload = deepcopy(consumed.payload)
        key = uuid4()
        self.confirm(consumed, key=key, payload=payload)
        operation_count = AiOperation.objects.count()
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertTrue(self.owner.is_active)
        for callback in (
            lambda: self.generate(),
            lambda: self.retrieve(pending),
            lambda: self.retrieve(consumed),
            lambda: self.confirm(pending),
            lambda: self.confirm(consumed, key=key, payload=payload),
        ):
            with self.assertRaises((PermissionDenied, TenantAccessNotFound)):
                callback()
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(AiOperation.objects.count(), operation_count)

    def test_second_node_failure_rolls_back_first_task_and_all_audits(self):
        proposal, _ = self.generate()
        calls = []

        def fail_second(**kwargs):
            calls.append(kwargs["title"])
            if len(calls) == 2:
                raise ValidationError("Synthetic second node failure")
            return create_task(**kwargs)

        with patch("apps.ai.durable_services.create_task", side_effect=fail_second):
            with self.assertRaises(ValidationError):
                self.confirm(proposal, payload=plan([node(), node("item_2", "item_1")]))
        self.assertEqual(len(calls), 2)
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(action="task.created").count(), 0)
        self.assertEqual(AiOperation.objects.count(), 1)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "AVAILABLE")

    def test_scoped_operation_uniqueness_is_enforced_by_postgresql(self):
        self.generate()
        original = AiOperation.objects.get()
        with self.assertRaises(IntegrityError), transaction.atomic():
            AiOperation.objects.create(
                actor_id=original.actor_id, profile_id=original.profile_id,
                workspace_id=original.workspace_id, operation=original.operation,
                key_digest=original.key_digest, body_digest="0" * 64,
                proposal_id=original.proposal_id,
            )
        self.assertEqual(AiOperation.objects.count(), 1)

    def test_postgresql_single_confirmation_constraint_also_blocks_a_new_key(self):
        proposal, _ = self.generate()
        self.confirm(proposal)
        original = AiOperation.objects.get(operation="CONFIRM")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AiOperation.objects.create(
                actor_id=original.actor_id, profile_id=original.profile_id,
                workspace_id=original.workspace_id, operation="CONFIRM",
                key_digest="f" * 64, body_digest=original.body_digest,
                proposal_id=original.proposal_id,
            )
        self.assertEqual(AiOperation.objects.filter(operation="CONFIRM").count(), 1)

    def test_hmac_key_rotation_with_explicit_fallback_preserves_replay(self):
        proposal, _ = self.generate()
        payload = deepcopy(proposal.payload)
        key = uuid4()
        with override_settings(SECRET_KEY="synthetic-ai-hmac-rotation-a", SECRET_KEY_FALLBACKS=[]):
            first, _ = self.confirm(proposal, key=key, payload=payload)
        with override_settings(SECRET_KEY="synthetic-ai-hmac-rotation-b", SECRET_KEY_FALLBACKS=["synthetic-ai-hmac-rotation-a"]):
            replay, replayed = self.confirm(proposal, key=key, payload=payload)
        self.assertTrue(replayed)
        self.assertEqual(first.created_tasks, replay.created_tasks)
        self.assertEqual(Task.objects.count(), 1)


@override_settings(**FIXTURE_SETTINGS)
class DurableConfirmationConcurrencyTests(DurableDataMixin, TransactionTestCase):
    def setUp(self):
        self.setup_data("ai-race")

    def race(self, first, second):
        barrier = Barrier(2)

        def run(operation):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '10s'")
                barrier.wait(timeout=10)
                try:
                    return "success", operation()
                except (AIError, PermissionDenied, TenantAccessNotFound) as exc:
                    return "denied", exc
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = (pool.submit(run, first), pool.submit(run, second))
            return [future.result(timeout=20) for future in futures]

    def test_concurrent_same_key_confirmation_returns_one_batch_and_replay(self):
        proposal, _ = self.generate(scenario="task-tree-v1")
        payload = deepcopy(proposal.payload)
        key = uuid4()
        results = self.race(
            lambda: self.confirm(proposal, key=key, payload=deepcopy(payload)),
            lambda: self.confirm(proposal, key=key, payload=deepcopy(payload)),
        )
        self.assertEqual([kind for kind, _ in results], ["success", "success"])
        outcomes = [result for _, result in results]
        self.assertCountEqual([replayed for _, replayed in outcomes], [False, True])
        self.assertEqual(outcomes[0][0].created_tasks, outcomes[1][0].created_tasks)
        self.assertEqual(Task.objects.count(), len(payload["tasks"]))
        self.assertEqual(AuditLog.objects.filter(action="task.created").count(), len(payload["tasks"]))

    def test_concurrent_generation_same_key_persists_one_proposal_and_operation(self):
        key = uuid4()
        adapter_barrier = Barrier(2)
        original = FixtureAdapter.generate
        audit_count = AuditLog.objects.count()

        def synchronized_generate(adapter, request, control):
            adapter_barrier.wait(timeout=10)
            return original(adapter, request, control)

        with patch.object(FixtureAdapter, "generate", new=synchronized_generate):
            results = self.race(
                lambda: self.generate(key=key),
                lambda: self.generate(key=key),
            )
        self.assertEqual([kind for kind, _ in results], ["success", "success"])
        outcomes = [result for _, result in results]
        self.assertCountEqual([replayed for _, replayed in outcomes], [False, True])
        self.assertEqual(outcomes[0][0].pk, outcomes[1][0].pk)
        self.assertEqual(AiProposal.objects.count(), 1)
        self.assertEqual(AiOperation.objects.count(), 1)
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), audit_count)

    def test_concurrent_different_keys_cannot_confirm_same_proposal_twice(self):
        proposal, _ = self.generate()
        payload = deepcopy(proposal.payload)
        results = self.race(
            lambda: self.confirm(proposal, payload=deepcopy(payload)),
            lambda: self.confirm(proposal, payload=deepcopy(payload)),
        )
        self.assertCountEqual([kind for kind, _ in results], ["success", "denied"])
        error = next(value for kind, value in results if kind == "denied")
        self.assertIsInstance(error, AIError)
        self.assertEqual(error.code.value, "ALREADY_CONFIRMED")
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="task.created").count(), 1)

    def test_confirm_and_archive_serialize_without_partial_state_or_deadlock(self):
        proposal, _ = self.generate(scenario="task-tree-v1")
        payload = deepcopy(proposal.payload)
        results = self.race(
            lambda: self.confirm(proposal, payload=payload),
            lambda: archive_workspace(**self.scope()),
        )
        self.assertEqual(results[1][0], "success")
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.status, Workspace.Status.ARCHIVED)
        proposal.refresh_from_db()
        if results[0][0] == "success":
            self.assertEqual(proposal.status, "CONFIRMED")
            self.assertEqual(Task.objects.count(), len(payload["tasks"]))
        else:
            self.assertEqual(proposal.status, "AVAILABLE")
            self.assertEqual(Task.objects.count(), 0)

    def test_confirm_and_membership_revocation_serialize_without_leaking_replay(self):
        proposal, _ = self.generate(actor=self.manager)
        payload = deepcopy(proposal.payload)
        key = uuid4()
        results = self.race(
            lambda: self.confirm(proposal, actor=self.manager, key=key, payload=payload),
            lambda: revoke_workspace_member(
                actor=self.owner, profile_id=self.profile.id, workspace_id=self.workspace.id,
                membership_id=self.manager_workspace_membership.id,
            ),
        )
        self.assertEqual(results[1][0], "success")
        self.manager_workspace_membership.refresh_from_db()
        self.assertFalse(self.manager_workspace_membership.is_active)
        self.assertIn(Task.objects.count(), (0, 1))
        with self.assertRaises((PermissionDenied, TenantAccessNotFound)):
            self.confirm(proposal, actor=self.manager, key=key, payload=payload)

    def test_fixture_generation_occurs_outside_database_transaction(self):
        original = FixtureAdapter.generate
        observed = []

        def observe(adapter, request, control):
            observed.append(connection.in_atomic_block)
            return original(adapter, request, control)

        with patch.object(FixtureAdapter, "generate", new=observe):
            self.generate()
        self.assertEqual(observed, [False])
