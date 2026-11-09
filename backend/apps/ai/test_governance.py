"""Offline governance/state-machine proofs on owned isolated PostgreSQL.

All actors and content are invented. Threads use independent Django database
connections; no process-local lock is used to provide dispatch protection.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier, Event
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection, transaction
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.reviews.models import Deliverable, Review
from apps.tasks.models import Task, TaskAssignment, TaskComment
from apps.tasks.services import create_task
from apps.workspace.access import TenantAccessNotFound
from apps.workspace.models import ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from . import governance
from .errors import AIError, ErrorCode
from .models import AiBudgetBucket, AiDispatch, AiDispatchReservation, AiOperation, AiProposal
from .openai_adapter import OpenAIConfig, OpenAIResponsesAdapter
from .providers import Feature, RequestControl
from .test_openai_adapter import MemoryTransport, analysis, envelope, response


SETTINGS = {
    "AI_GOVERNANCE_ENABLED": True, "AI_FIXTURE_ENABLED": True,
    "ENVIRONMENT": "development", "IS_PRODUCTION": False,
}
BRIEF = "GOVERNANCE_SYNTHETIC_BRIEF: kiểm tra phụ đề minh họa."
FEEDBACK = "GOVERNANCE_SYNTHETIC_FEEDBACK: nhận xét minh họa."
FOCUS = "GOVERNANCE_SYNTHETIC_FOCUS: độ rõ ràng."
SECRET = "GOVERNANCE_SYNTHETIC_SECRET_NEVER_EXPOSE"
User = get_user_model()


def limits(*, cost="10", requests=100, active=10):
    return governance.BudgetLimits(cost_limit=Decimal(cost), request_limit=requests,
                                   concurrency_limit=active)


def policy(**values):
    defaults = {
        "enabled": True, "global_limits": limits(), "profile_limits": limits(),
        "user_limits": limits(),
    }
    defaults.update(values)
    return governance.GovernancePolicy(**defaults)


class GovernanceData:
    def data(self):
        self.owner = User.objects.create_user(
            username="governance-owner", email="governance-owner@example.test", password=None,
        )
        self.member = User.objects.create_user(
            username="governance-member", email="governance-member@example.test", password=None,
        )
        self.outsider = User.objects.create_user(
            username="governance-outsider", email="governance-outsider@example.test", password=None,
        )
        self.profile = create_profile_with_owner(name="Governance synthetic profile", owner=self.owner)
        self.workspace = Workspace.objects.create(
            profile=self.profile, owner=self.owner, name="Governance synthetic month",
            period=date(2026, 11, 1),
        )
        self.other_workspace = Workspace.objects.create(
            profile=self.profile, owner=self.owner, name="Governance other month",
            period=date(2026, 12, 1),
        )
        self.other_profile = create_profile_with_owner(name="Governance second profile", owner=self.owner)
        self.foreign_workspace = Workspace.objects.create(
            profile=self.other_profile, owner=self.owner, name="Governance second profile month",
            period=date(2026, 11, 1),
        )
        self.membership = ProfileMembership.objects.create(
            profile=self.profile, user=self.member, role=ProfileMembership.Role.ADMIN,
        )
        self.rules = policy()

    def scope(self, actor=None, workspace=None):
        workspace = workspace or self.workspace
        return {"actor": actor or self.owner, "profile_id": workspace.profile_id,
                "workspace_id": workspace.pk}

    def reserve(self, *, key=None, content=None, rules=None, actor=None, workspace=None):
        return governance.reserve_dispatch(
            **self.scope(actor, workspace), feature=Feature.TASK_PLAN,
            idempotency_key=str(key or uuid4()),
            canonical_input={"brief": BRIEF} if content is None else content,
            policy=rules or self.rules,
        )

    def call(self, *, key=None, brief=BRIEF, transport=None, rules=None, actor=None,
             workspace=None, control=None):
        transport = MemoryTransport() if transport is None else transport
        adapter = OpenAIResponsesAdapter(config=OpenAIConfig(enabled=True), transport=transport)
        return governance.execute_generator(
            **self.scope(actor, workspace), brief=brief, idempotency_key=str(key or uuid4()),
            adapter=adapter, policy=rules or self.rules, control=control,
        )

    def transition(self, method, dispatch_id, **values):
        return method(**self.scope(), dispatch_id=dispatch_id, policy=self.rules, **values)

    def error(self, code, callback):
        with self.assertRaises(AIError) as caught:
            callback()
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertNotIn(BRIEF, repr(caught.exception.as_public_error()))
        return caught.exception

    def buckets(self):
        return list(AiBudgetBucket.objects.order_by("scope").values(
            "scope", "reserved_amount", "accounted_amount", "request_count", "active_count",
        ))

    def domain(self):
        return {model._meta.label: list(model.objects.order_by("pk").values()) for model in (
            User, ProfileMembership, Workspace, Task, TaskAssignment, TaskComment,
            Deliverable, Review, Notification, AuditLog, AiProposal, AiOperation,
        )}


class GovernanceDefaultOffTests(SimpleTestCase):
    def test_default_off_rejects_before_querying_unapplied_tables(self):
        with override_settings(AI_GOVERNANCE_ENABLED=False):
            with self.assertRaises(AIError) as caught:
                governance.reserve_dispatch(actor=None, profile_id=uuid4(), workspace_id=uuid4(),
                    feature=Feature.TASK_PLAN, idempotency_key=str(uuid4()),
                    canonical_input={"brief": BRIEF}, policy=policy())
        self.assertEqual(caught.exception.code, ErrorCode.AI_DISABLED)

    @override_settings(**SETTINGS)
    def test_policy_default_disabled_and_live_mode_fail_before_database(self):
        for rules in (governance.GovernancePolicy(), policy(execution_mode="OPENAI_LIVE")):
            with self.subTest(mode=rules.execution_mode), self.assertRaises(AIError) as caught:
                governance.reserve_dispatch(actor=None, profile_id=uuid4(), workspace_id=uuid4(),
                    feature=Feature.TASK_PLAN, idempotency_key=str(uuid4()),
                    canonical_input={"brief": BRIEF}, policy=rules)
            self.assertEqual(caught.exception.code, ErrorCode.AI_DISABLED)


@override_settings(**SETTINGS)
class GovernanceServiceTests(GovernanceData, TransactionTestCase):
    def setUp(self):
        self.data()

    def test_reservation_atomically_creates_dispatch_and_three_server_scoped_holds(self):
        receipt = self.reserve()
        dispatch = AiDispatch.objects.get(pk=receipt.dispatch_id)
        self.assertEqual(dispatch.status, "RESERVED")
        self.assertTrue(receipt.created)
        self.assertEqual(dispatch.actor_id, self.owner.pk)
        self.assertEqual(dispatch.profile_id, self.profile.pk)
        self.assertEqual(dispatch.workspace_id, self.workspace.pk)
        reservations = list(AiDispatchReservation.objects.filter(dispatch=dispatch).select_related("bucket"))
        self.assertEqual({item.bucket.scope for item in reservations}, {"GLOBAL", "PROFILE", "USER"})
        self.assertEqual(len(reservations), 3)
        for item in reservations:
            self.assertEqual(item.status, "HELD")
            self.assertEqual(item.amount, dispatch.reserved_amount)
            self.assertEqual(item.bucket.active_count, 1)
            self.assertEqual(item.bucket.request_count, 1)
            self.assertEqual(item.bucket.reserved_amount, dispatch.reserved_amount)
        self.assertIsNone(dispatch.billed_cost)

    def test_same_key_body_reuses_dispatch_without_duplicate_reservations(self):
        key = uuid4()
        first = self.reserve(key=key)
        before = self.buckets()
        second = self.reserve(key=key)
        self.assertEqual(first.dispatch_id, second.dispatch_id)
        self.assertFalse(second.created)
        self.assertEqual(self.buckets(), before)
        self.assertEqual(AiDispatch.objects.count(), 1)
        self.assertEqual(AiDispatchReservation.objects.count(), 3)

    def test_same_key_changed_input_conflicts_without_echo_or_accounting_change(self):
        key = uuid4()
        self.reserve(key=key)
        before = self.buckets()
        self.error(ErrorCode.IDEMPOTENCY_CONFLICT,
            lambda: self.reserve(key=key, content={"brief": SECRET}))
        self.assertEqual(self.buckets(), before)
        self.assertEqual(AiDispatch.objects.count(), 1)

    def test_same_key_changed_provider_configuration_is_conflict_not_a_new_dispatch(self):
        key = uuid4()
        self.reserve(key=key)
        self.error(ErrorCode.IDEMPOTENCY_CONFLICT,
            lambda: self.reserve(key=key, rules=replace(self.rules, config_version="offline-v2")))
        self.assertEqual(AiDispatch.objects.count(), 1)

    def test_key_rotation_with_configured_fallback_preserves_scoped_replay(self):
        key = uuid4()
        first = self.reserve(key=key)
        before = self.buckets()
        # Both settings values belong to the isolated harness, never Owner .env.
        with override_settings(SECRET_KEY="synthetic-governance-rotation-test-key",
                               SECRET_KEY_FALLBACKS=[settings.SECRET_KEY]):
            replay = self.reserve(key=key)
        self.assertEqual(replay.dispatch_id, first.dispatch_id)
        self.assertFalse(replay.created)
        self.assertEqual(self.buckets(), before)

    def test_same_key_is_separate_for_user_profile_and_workspace(self):
        key = uuid4()
        receipts = [self.reserve(key=key), self.reserve(key=key, actor=self.member),
                    self.reserve(key=key, workspace=self.other_workspace),
                    self.reserve(key=key, workspace=self.foreign_workspace)]
        self.assertEqual(len({item.dispatch_id for item in receipts}), 4)
        global_bucket = AiBudgetBucket.objects.get(scope="GLOBAL")
        self.assertEqual(global_bucket.request_count, 4)
        self.assertEqual(global_bucket.active_count, 4)
        self.assertEqual(len(set(AiDispatch.objects.values_list("body_digest", flat=True))), 4)

    def test_budget_exhaustion_rolls_back_dispatch_and_all_partial_holds(self):
        for scope in ("global_limits", "profile_limits", "user_limits"):
            with self.subTest(scope=scope):
                rules = replace(self.rules, **{scope: limits(cost="0.00000001")})
                self.error(ErrorCode.BUDGET_EXCEEDED, lambda: self.reserve(rules=rules))
                self.assertEqual(AiDispatch.objects.count(), 0)
                self.assertEqual(AiDispatchReservation.objects.count(), 0)
                self.assertEqual(AiBudgetBucket.objects.count(), 0)

    def test_request_limit_is_shared_and_failure_before_dispatch_does_not_reset_attempts(self):
        rules = replace(self.rules, user_limits=limits(requests=1))
        first = self.reserve(rules=rules)
        governance.fail_before_dispatch(**self.scope(), dispatch_id=first.dispatch_id, policy=rules)
        self.error(ErrorCode.BUDGET_EXCEEDED, lambda: self.reserve(rules=rules))
        bucket = AiBudgetBucket.objects.get(scope="USER")
        self.assertEqual(bucket.request_count, 1)
        self.assertEqual(bucket.active_count, 0)
        self.assertEqual(bucket.reserved_amount, Decimal("0"))

    def test_per_profile_and_global_request_caps_aggregate_across_users_and_tenants(self):
        rules = replace(self.rules, global_limits=limits(requests=1))
        self.reserve(rules=rules)
        self.error(ErrorCode.BUDGET_EXCEEDED,
            lambda: self.reserve(rules=rules, workspace=self.foreign_workspace))
        self.assertEqual(AiDispatch.objects.count(), 1)

    def test_profile_request_cap_is_shared_by_different_authorized_users(self):
        rules = replace(self.rules, profile_limits=limits(requests=1))
        self.reserve(rules=rules)
        self.error(ErrorCode.BUDGET_EXCEEDED,
            lambda: self.reserve(rules=rules, actor=self.member))
        self.assertEqual(AiDispatch.objects.count(), 1)
        self.assertEqual(AiBudgetBucket.objects.get(scope="PROFILE").request_count, 1)

    def test_inflight_limit_and_unknown_hold_survive_calendar_change(self):
        rules = replace(self.rules, user_limits=limits(active=1))
        first = self.reserve(rules=rules)
        governance.begin_dispatch(**self.scope(), dispatch_id=first.dispatch_id, policy=rules)
        governance.mark_unknown(**self.scope(), dispatch_id=first.dispatch_id, policy=rules)
        before = self.buckets()
        with patch("apps.ai.governance.timezone.now", return_value=timezone.now() + timedelta(days=2)):
            self.error(ErrorCode.BUDGET_EXCEEDED, lambda: self.reserve(rules=rules))
        self.assertEqual(self.buckets(), before)
        self.assertEqual(AiBudgetBucket.objects.get(scope="USER").active_count, 1)

    def test_existing_budget_policy_cannot_be_replaced_to_reset_or_widen_limits(self):
        self.reserve()
        before = self.buckets()
        with self.assertRaises(AIError):
            self.reserve(rules=replace(self.rules, global_limits=limits(cost="999")))
        self.assertEqual(self.buckets(), before)
        self.assertEqual(AiBudgetBucket.objects.filter(scope="GLOBAL").count(), 1)

    def test_before_dispatch_failure_releases_hold_and_prevents_late_begin(self):
        receipt = self.reserve()
        self.transition(governance.fail_before_dispatch, receipt.dispatch_id)
        dispatch = AiDispatch.objects.get(pk=receipt.dispatch_id)
        self.assertEqual(dispatch.status, "FAILED_BEFORE_DISPATCH")
        for item in AiBudgetBucket.objects.all():
            self.assertEqual(item.reserved_amount, Decimal("0"))
            self.assertEqual(item.accounted_amount, Decimal("0"))
            self.assertEqual(item.active_count, 0)
            self.assertEqual(item.request_count, 1)
        before = self.buckets()
        self.transition(governance.fail_before_dispatch, receipt.dispatch_id)
        self.assertEqual(self.buckets(), before)
        denied = self.transition(governance.begin_dispatch, receipt.dispatch_id)
        self.assertFalse(denied.claimed)
        self.assertEqual(denied.status, "FAILED_BEFORE_DISPATCH")
        self.assertEqual(self.buckets(), before)

    def test_begin_commits_before_transport_and_no_domain_rows_are_created(self):
        observed = []

        def during():
            self.assertFalse(connection.in_atomic_block)
            dispatch = AiDispatch.objects.get()
            self.assertEqual(dispatch.status, "DISPATCHING")
            self.assertIsNotNone(dispatch.claim_id)
            self.assertIsNotNone(dispatch.dispatched_at)
            self.assertEqual(AiDispatchReservation.objects.filter(status="HELD").count(), 3)
            observed.append(dispatch.pk)

        before = self.domain()
        result = self.call(transport=MemoryTransport(after=during))
        self.assertEqual(observed, [result.receipt.dispatch_id])
        self.assertEqual(self.domain(), before)
        self.assertEqual(result.result.provider, "openai_offline")
        self.assertEqual(result.result.usage.status, "offline_simulated")

    def test_success_settles_simulated_estimate_once_and_never_fabricates_invoice(self):
        key = uuid4()
        transport = MemoryTransport()
        result = self.call(key=key, transport=transport)
        dispatch = AiDispatch.objects.get(pk=result.receipt.dispatch_id)
        self.assertEqual(dispatch.status, "SUCCEEDED")
        self.assertEqual(dispatch.execution_mode, "OPENAI_OFFLINE")
        self.assertEqual(dispatch.usage_status, "SIMULATED")
        self.assertEqual((dispatch.input_tokens, dispatch.output_tokens), (10, 20))
        self.assertIsNone(dispatch.billed_cost)
        self.assertIsNotNone(dispatch.estimated_cost)
        self.assertLessEqual(dispatch.estimated_cost, dispatch.reserved_amount)
        self.assertEqual(dispatch.accounted_amount, dispatch.estimated_cost)
        for bucket in AiBudgetBucket.objects.all():
            self.assertEqual(bucket.reserved_amount, Decimal("0"))
            self.assertEqual(bucket.accounted_amount, dispatch.estimated_cost)
            self.assertEqual(bucket.active_count, 0)
        before = self.buckets()
        replay = self.call(key=key, transport=transport)
        self.assertIsNone(replay.result)
        self.assertEqual(replay.receipt.dispatch_id, result.receipt.dispatch_id)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(self.buckets(), before)

    def test_post_dispatch_timeout_retains_unknown_reservations_and_never_retries(self):
        key = uuid4()
        transport = MemoryTransport(error=TimeoutError(SECRET))
        with self.assertRaises(AIError):
            self.call(key=key, transport=transport)
        dispatch = AiDispatch.objects.get()
        self.assertEqual(dispatch.status, "OUTCOME_UNKNOWN")
        self.assertIsNone(dispatch.billed_cost)
        self.assertEqual(AiDispatchReservation.objects.filter(status="HELD").count(), 3)
        before = self.buckets()
        replay = self.call(key=key, transport=transport)
        self.assertIsNone(replay.result)
        self.assertEqual(replay.receipt.status, "OUTCOME_UNKNOWN")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(self.buckets(), before)

    def test_invalid_provider_output_is_unknown_after_attempt_not_refunded(self):
        transport = MemoryTransport(response(raw=b"not-json"))
        self.error(ErrorCode.INVALID_PROVIDER_RESPONSE, lambda: self.call(transport=transport))
        dispatch = AiDispatch.objects.get()
        self.assertEqual(dispatch.status, "OUTCOME_UNKNOWN")
        self.assertEqual(AiDispatchReservation.objects.filter(status="HELD").count(), 3)
        for bucket in AiBudgetBucket.objects.all():
            self.assertEqual(bucket.active_count, 1)

    def test_success_with_unknown_usage_does_not_release_possible_exposure(self):
        value = envelope()
        value["usage"] = None
        self.error(ErrorCode.INVALID_PROVIDER_RESPONSE,
            lambda: self.call(transport=MemoryTransport(response(value))))
        dispatch = AiDispatch.objects.get()
        self.assertEqual(dispatch.status, "OUTCOME_UNKNOWN")
        self.assertEqual(dispatch.usage_status, "UNKNOWN")
        self.assertIsNone(dispatch.estimated_cost)
        self.assertIsNone(dispatch.billed_cost)
        self.assertEqual(AiDispatchReservation.objects.filter(status="HELD").count(), 3)

    def test_provider_success_followed_by_persistence_failure_preserves_unknown_hold(self):
        transport = MemoryTransport()
        with patch("apps.ai.governance._settle_success", side_effect=RuntimeError(SECRET)):
            self.error(ErrorCode.PROVIDER_UNAVAILABLE, lambda: self.call(transport=transport))
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(AiDispatch.objects.get().status, "OUTCOME_UNKNOWN")
        self.assertEqual(AiDispatchReservation.objects.filter(status="HELD").count(), 3)
        for bucket in AiBudgetBucket.objects.all():
            self.assertEqual(bucket.active_count, 1)
            self.assertGreater(bucket.reserved_amount, Decimal("0"))

    def test_unknown_mark_persistence_failure_leaves_dispatching_uncertainty_and_holds(self):
        transport = MemoryTransport(error=TimeoutError(SECRET))
        with patch("apps.ai.governance.mark_unknown", side_effect=RuntimeError(SECRET)):
            self.error(ErrorCode.PROVIDER_TIMEOUT, lambda: self.call(transport=transport))
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(AiDispatch.objects.get().status, "DISPATCHING")
        self.assertEqual(AiDispatchReservation.objects.filter(status="HELD").count(), 3)

    def test_fake_usage_exceeding_reserved_input_bound_is_unknown_and_not_refunded(self):
        value = envelope()
        value["usage"] = {"input_tokens": 65537, "output_tokens": 20, "total_tokens": 65557}
        self.error(ErrorCode.INVALID_PROVIDER_RESPONSE,
            lambda: self.call(transport=MemoryTransport(response(value))))
        self.assertEqual(AiDispatch.objects.get().status, "OUTCOME_UNKNOWN")
        self.assertEqual(AiDispatchReservation.objects.filter(status="HELD").count(), 3)

    def test_mark_unknown_after_worker_crash_is_idempotent_and_never_releases_hold(self):
        receipt = self.reserve()
        self.transition(governance.begin_dispatch, receipt.dispatch_id)
        before = self.buckets()
        self.transition(governance.mark_unknown, receipt.dispatch_id)
        self.transition(governance.mark_unknown, receipt.dispatch_id)
        dispatch = AiDispatch.objects.get(pk=receipt.dispatch_id)
        self.assertEqual(dispatch.status, "OUTCOME_UNKNOWN")
        self.assertEqual(self.buckets(), before)
        with self.assertRaises(AIError):
            self.transition(governance.fail_before_dispatch, receipt.dispatch_id)

    def test_read_and_transitions_reject_changed_reserved_policy_without_repricing(self):
        receipt = self.reserve()
        self.transition(governance.begin_dispatch, receipt.dispatch_id)
        self.transition(governance.mark_unknown, receipt.dispatch_id)
        before = self.buckets()
        changed = (
            replace(self.rules, model="gpt-5.4-mini-2026-03-17"),
            replace(self.rules, config_version="offline-v2"),
            replace(self.rules, pricing_version="synthetic-v2"),
            replace(self.rules, max_input_tokens=65535),
            replace(self.rules, max_output_tokens=4095),
            replace(self.rules, input_rate_per_million=Decimal("2")),
            replace(self.rules, output_rate_per_million=Decimal("2")),
            # 65536*.5 +4096*9 equals the original reservation; a mere amount
            # comparison cannot establish that the original pricing is intact.
            replace(self.rules, input_rate_per_million=Decimal("0.5"),
                    output_rate_per_million=Decimal("9")),
        )
        methods = ((governance.get_dispatch, {}), (governance.begin_dispatch, {}),
                   (governance.reconcile_dispatch,
                    {"accounted_amount": Decimal("0"), "evidence": "synthetic-policy-change"}))
        for rules in changed:
            for method, extra in methods:
                with self.subTest(method=method.__name__, model=rules.model,
                                  config=rules.config_version, pricing=rules.pricing_version), self.assertRaises(AIError):
                    method(**self.scope(), dispatch_id=receipt.dispatch_id, policy=rules, **extra)
                self.assertEqual(self.buckets(), before)

    def test_reconciliation_digest_binds_dispatch_identity_and_scope(self):
        ids = []
        for workspace in (self.workspace, self.other_workspace):
            receipt = self.reserve(workspace=workspace)
            context = {**self.scope(workspace=workspace), "dispatch_id": receipt.dispatch_id,
                       "policy": self.rules}
            governance.begin_dispatch(**context)
            governance.mark_unknown(**context)
            governance.reconcile_dispatch(**context, accounted_amount=Decimal("0"),
                                           evidence="same-synthetic-evidence")
            ids.append(receipt.dispatch_id)
        digests = list(AiDispatch.objects.filter(pk__in=ids).values_list("settlement_digest", flat=True))
        self.assertEqual(len(set(digests)), 2)

    def test_cancellation_after_possible_dispatch_keeps_unknown_exposure(self):
        cancelled = [False]
        transport = MemoryTransport(after=lambda: cancelled.__setitem__(0, True))
        control = RequestControl(is_cancelled=lambda: cancelled[0])
        self.error(ErrorCode.CANCELLED, lambda: self.call(transport=transport, control=control))
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(AiDispatch.objects.get().status, "OUTCOME_UNKNOWN")
        self.assertEqual(AiDispatchReservation.objects.filter(status="HELD").count(), 3)

    def test_worker_loss_after_dispatch_marker_does_not_create_a_retry_opportunity(self):
        key = uuid4()
        receipt = self.reserve(key=key)
        self.transition(governance.begin_dispatch, receipt.dispatch_id)
        before = self.buckets()
        later = self.reserve(key=key)
        self.assertFalse(later.created)
        self.assertEqual(later.status, "DISPATCHING")
        self.assertEqual(self.buckets(), before)
        self.assertEqual(AiDispatch.objects.count(), 1)

    def test_reconciliation_is_simulated_idempotent_and_conflicting_evidence_denied(self):
        receipt = self.reserve()
        self.transition(governance.begin_dispatch, receipt.dispatch_id)
        self.transition(governance.mark_unknown, receipt.dispatch_id)
        args = {"accounted_amount": Decimal("0.00003000"), "evidence": "synthetic-evidence-v1",
                "input_tokens": 10, "output_tokens": 20}
        self.transition(governance.reconcile_dispatch, receipt.dispatch_id, **args)
        dispatch = AiDispatch.objects.get(pk=receipt.dispatch_id)
        self.assertEqual(dispatch.status, "RECONCILED")
        self.assertEqual(dispatch.usage_status, "SIMULATED")
        self.assertIsNone(dispatch.billed_cost)
        before = self.buckets()
        self.transition(governance.reconcile_dispatch, receipt.dispatch_id, **args)
        self.assertEqual(self.buckets(), before)
        self.error(ErrorCode.IDEMPOTENCY_CONFLICT,
            lambda: self.transition(governance.reconcile_dispatch, receipt.dispatch_id,
                                   **(args | {"evidence": "different-synthetic-evidence"})))
        self.assertEqual(self.buckets(), before)

    def test_reconciliation_cannot_exceed_original_reservation_or_use_negative_amount(self):
        receipt = self.reserve()
        self.transition(governance.begin_dispatch, receipt.dispatch_id)
        self.transition(governance.mark_unknown, receipt.dispatch_id)
        dispatch = AiDispatch.objects.get(pk=receipt.dispatch_id)
        before = self.buckets()
        for amount in (Decimal("-1"), dispatch.reserved_amount + Decimal("0.1")):
            with self.subTest(amount=amount), self.assertRaises(AIError):
                self.transition(governance.reconcile_dispatch, dispatch.pk,
                                accounted_amount=amount, evidence="synthetic-invalid-evidence")
        self.assertEqual(self.buckets(), before)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, "OUTCOME_UNKNOWN")

    def test_reconciliation_rejects_incomplete_usage_pair_without_integrity_error(self):
        receipt = self.reserve()
        self.transition(governance.begin_dispatch, receipt.dispatch_id)
        self.transition(governance.mark_unknown, receipt.dispatch_id)
        before = self.buckets()
        self.error(ErrorCode.VALIDATION_ERROR,
            lambda: self.transition(governance.reconcile_dispatch, receipt.dispatch_id,
                accounted_amount=Decimal("0"), evidence="synthetic-partial-usage", input_tokens=10))
        self.assertEqual(self.buckets(), before)

    def test_outsider_or_wrong_nested_scope_cannot_reserve_or_read_dispatch(self):
        receipt = self.reserve()
        for values in (self.scope(actor=self.outsider),
                       {"actor": self.owner, "profile_id": self.other_profile.pk,
                        "workspace_id": self.workspace.pk}, self.scope(workspace=self.foreign_workspace)):
            with self.subTest(scope=values["profile_id"]), self.assertRaises((AIError, PermissionDenied, TenantAccessNotFound)):
                governance.get_dispatch(**values, dispatch_id=receipt.dispatch_id, policy=self.rules)
        with self.assertRaises((AIError, PermissionDenied, TenantAccessNotFound)):
            self.reserve(actor=self.outsider)

    def test_other_authorized_manager_cannot_read_or_reconcile_original_actor_dispatch(self):
        receipt = self.reserve()
        for method, extra in ((governance.get_dispatch, {}),
                              (governance.reconcile_dispatch,
                               {"accounted_amount": Decimal("0"), "evidence": "synthetic"})):
            with self.assertRaises((AIError, PermissionDenied, TenantAccessNotFound)):
                method(**self.scope(actor=self.member), dispatch_id=receipt.dispatch_id,
                       policy=self.rules, **extra)

    def test_revoked_membership_blocks_current_read_and_preserves_unknown_hold(self):
        receipt = self.reserve(actor=self.member)
        governance.begin_dispatch(**self.scope(actor=self.member), dispatch_id=receipt.dispatch_id,
                                  policy=self.rules)
        governance.mark_unknown(**self.scope(actor=self.member), dispatch_id=receipt.dispatch_id,
                                policy=self.rules)
        self.membership.is_active = False
        self.membership.save(update_fields=("is_active",))
        before = self.buckets()
        with self.assertRaises((AIError, PermissionDenied, TenantAccessNotFound)):
            governance.get_dispatch(**self.scope(actor=self.member), dispatch_id=receipt.dispatch_id,
                                    policy=self.rules)
        self.assertEqual(self.buckets(), before)

    def test_archived_profile_or_workspace_denies_reservation(self):
        self.workspace.status = Workspace.Status.ARCHIVED
        self.workspace.save(update_fields=("status",))
        with self.assertRaises((AIError, PermissionDenied, TenantAccessNotFound)):
            self.reserve()
        self.assertEqual(AiDispatch.objects.count(), 0)

    def test_archived_profile_denies_reservation_without_new_accounting_rows(self):
        self.profile.status = "ARCHIVED"
        self.profile.save(update_fields=("status",))
        with self.assertRaises((AIError, PermissionDenied, TenantAccessNotFound)):
            self.reserve()
        self.assertEqual(AiDispatch.objects.count(), 0)
        self.assertEqual(AiBudgetBucket.objects.count(), 0)

    def test_raw_inputs_and_error_canaries_are_not_stored_or_logged(self):
        with self.assertNoLogs(level="DEBUG"):
            self.call(brief=BRIEF + SECRET)
        stored = json.dumps({model._meta.label: list(model.objects.values()) for model in (
            AiDispatch, AiDispatchReservation, AiBudgetBucket, AiProposal, AiOperation, AuditLog,
        )}, default=str)
        for marker in (BRIEF, FEEDBACK, FOCUS, SECRET):
            self.assertNotIn(marker, stored)
        dispatch = AiDispatch.objects.get()
        self.assertEqual(len(dispatch.body_digest), 64)
        self.assertNotEqual(dispatch.body_digest, dispatch.key_digest)

    def test_fake_transport_does_not_attempt_external_network_or_domain_mutation(self):
        before = self.domain()
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch(target, side_effect=AssertionError("Unapproved network")))
                for target in ("socket.create_connection", "urllib.request.urlopen",
                               "http.client.HTTPConnection.request", "http.client.HTTPSConnection.request")]
            self.call()
            for guard in mocks:
                guard.assert_not_called()
        self.assertEqual(self.domain(), before)

    def feedback_data(self):
        task = create_task(**self.scope(), title="Synthetic governance feedback Task")
        comment = TaskComment.objects.create(task=task, user=self.owner, content=FEEDBACK)
        return task, comment

    def feedback_call(self, task, comment, *, key=None, actor=None, transport=None):
        return governance.execute_feedback(
            **self.scope(actor=actor), task_id=task.pk,
            sources=[{"kind": "comment", "id": str(comment.pk)}], focus=FOCUS,
            idempotency_key=str(key or uuid4()), policy=self.rules,
            adapter=OpenAIResponsesAdapter(config=OpenAIConfig(enabled=True),
                transport=transport or MemoryTransport(response(envelope(analysis())))),
        )

    def test_feedback_resolves_authorized_current_source_and_remains_stateless(self):
        task, comment = self.feedback_data()
        before = self.domain()
        transport = MemoryTransport(response(envelope(analysis())))
        result = self.feedback_call(task, comment, transport=transport)
        self.assertEqual(self.domain(), before)
        self.assertEqual(result.result.provider, "openai_offline")
        wire = json.loads(transport.calls[0]["body"])
        data = json.loads(wire["input"][1]["content"][0]["text"])
        self.assertEqual(data, {"sources": [{"ref": "S1", "text": FEEDBACK}], "focus": FOCUS})
        dispatch = AiDispatch.objects.get()
        self.assertEqual(dispatch.feature, "feedback_analysis")
        self.assertIsNone(dispatch.proposal_id)
        self.assertNotIn(FEEDBACK, json.dumps(list(AiDispatch.objects.values()), default=str))

    def test_feedback_wrong_task_or_deleted_source_is_denied_before_fake_dispatch(self):
        task, comment = self.feedback_data()
        wrong = create_task(**self.scope(), title="Synthetic wrong feedback Task")
        transport = MemoryTransport(response(envelope(analysis())))
        with self.assertRaises((AIError, PermissionDenied, TenantAccessNotFound)):
            self.feedback_call(wrong, comment, transport=transport)
        self.assertEqual(transport.calls, [])
        self.assertEqual(AiDispatch.objects.count(), 0)

    def test_soft_deleted_feedback_cannot_be_selected_from_retained_database_text(self):
        task, comment = self.feedback_data()
        TaskComment.objects.filter(pk=comment.pk).update(deleted_at=timezone.now())
        transport = MemoryTransport(response(envelope(analysis())))
        with self.assertRaises((AIError, PermissionDenied, TenantAccessNotFound)):
            self.feedback_call(task, comment, transport=transport)
        self.assertEqual(transport.calls, [])
        self.assertEqual(AiDispatch.objects.count(), 0)

    def test_same_key_with_changed_feedback_source_identity_is_conflict(self):
        task, comment = self.feedback_data()
        another = TaskComment.objects.create(task=task, user=self.owner, content=FEEDBACK)
        key = uuid4()
        first = self.feedback_call(task, comment, key=key)
        before = self.buckets()
        transport = MemoryTransport(response(envelope(analysis())))
        self.error(ErrorCode.IDEMPOTENCY_CONFLICT,
            lambda: self.feedback_call(task, another, key=key, transport=transport))
        self.assertEqual(transport.calls, [])
        self.assertEqual(AiDispatch.objects.count(), 1)
        self.assertEqual(self.buckets(), before)
        self.assertEqual(AiDispatch.objects.get().pk, first.receipt.dispatch_id)

    def test_feedback_source_change_after_transport_does_not_publish_stale_analysis(self):
        task, comment = self.feedback_data()

        def edit_source():
            TaskComment.objects.filter(pk=comment.pk).update(content="Changed synthetic feedback")

        transport = MemoryTransport(response(envelope(analysis())), after=edit_source)
        with self.assertRaises(AIError):
            self.feedback_call(task, comment, transport=transport)
        self.assertEqual(AiDispatch.objects.get().status, "OUTCOME_UNKNOWN")
        self.assertEqual(AiDispatchReservation.objects.filter(status="HELD").count(), 3)

    def test_outer_business_transaction_is_rejected_before_transport(self):
        transport = MemoryTransport()
        with transaction.atomic(), self.assertRaises(AIError):
            self.call(transport=transport)
        self.assertEqual(transport.calls, [])


@override_settings(**SETTINGS)
class GovernanceConcurrencyTests(GovernanceData, TransactionTestCase):
    def setUp(self):
        self.data()

    def worker(self, callback):
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET lock_timeout = '6s'")
                cursor.execute("SET statement_timeout = '12s'")
            return callback()
        finally:
            connection.close()

    def test_same_key_parallel_connections_invoke_fake_transport_exactly_once(self):
        key, start, completed = uuid4(), Barrier(2), Event()

        def during():
            self.assertFalse(connection.in_atomic_block)
            # The duplicate must finish without waiting for an I/O-held DB lock.
            if len(transport.calls) > 1:
                completed.set()
            self.assertTrue(completed.wait(8), "Equivalent request did not reuse the committed dispatch")

        transport = MemoryTransport(after=during)

        def invoke():
            start.wait(timeout=8)
            try:
                return self.call(key=key, transport=transport)
            finally:
                completed.set()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=20) for future in [
                pool.submit(self.worker, invoke), pool.submit(self.worker, invoke),
            ]]
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(len({item.receipt.dispatch_id for item in results}), 1)
        self.assertEqual(sum(item.result is not None for item in results), 1)
        self.assertEqual(AiDispatch.objects.count(), 1)
        self.assertEqual(AiDispatchReservation.objects.count(), 3)
        self.assertEqual(AiDispatch.objects.get().status, "SUCCEEDED")

    def test_parallel_different_keys_cannot_exceed_global_inflight_cap(self):
        start, completed = Barrier(2), Event()
        rules = replace(self.rules, global_limits=limits(active=1))

        def during():
            self.assertTrue(completed.wait(8), "The competing request did not fail on the shared cap")

        transport = MemoryTransport(after=during)

        def invoke(workspace):
            start.wait(timeout=8)
            try:
                return self.call(workspace=workspace, transport=transport, rules=rules)
            except AIError as error:
                self.assertEqual(error.code, ErrorCode.BUDGET_EXCEEDED)
                return None
            finally:
                completed.set()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.worker, lambda: invoke(self.workspace)),
                       pool.submit(self.worker, lambda: invoke(self.foreign_workspace))]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(sum(item is not None for item in results), 1)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(AiDispatch.objects.count(), 1)
        self.assertEqual(AiDispatchReservation.objects.count(), 3)
        self.assertEqual(AiBudgetBucket.objects.get(scope="GLOBAL").request_count, 1)
