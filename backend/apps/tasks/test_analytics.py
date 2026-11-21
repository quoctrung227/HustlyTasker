"""Analytics contracts/security, tested only on the owned PostgreSQL harness."""
import json
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient, APITestCase

from apps.reviews.models import Deliverable, Review
from apps.workspace.access import resolve_profile_access_context, resolve_workspace_access_context
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .access import task_compensation_visible_to
from .analytics import _financial_tasks, analytics_employees, resolve_analytics_scope
from .analytics_serializers import AnalyticsQuerySerializer
from .models import Task, TaskAssignment


User = get_user_model()
NOW = datetime(2026, 11, 20, 12, tzinfo=dt_timezone.utc)
CREATED = datetime(2026, 11, 5, 5, tzinfo=dt_timezone.utc)
APPROVED = datetime(2026, 11, 10, 5, tzinfo=dt_timezone.utc)


class AnalyticsDateTests(SimpleTestCase):
    def test_vietnam_dates_form_half_open_utc_range(self):
        serializer = AnalyticsQuerySerializer(data={"from": "2026-11-01", "to": "2026-11-30"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["start_at"], datetime(2026, 10, 31, 17, tzinfo=dt_timezone.utc))
        self.assertEqual(serializer.validated_data["end_before"], datetime(2026, 11, 30, 17, tzinfo=dt_timezone.utc))

    def test_invalid_dates_extra_fields_and_excessive_range_are_rejected(self):
        for values in (
            {"from": "2026-02-30"}, {"from": "2026-1-1"},
            {"from": "2026-12-01", "to": "2026-11-01"},
            {"from": "2020-01-01", "to": "2026-11-01"},
            {"from": "9999-12-31", "to": "9999-12-31"},
            {"user_id": str(uuid4())}, {"search": "bad\x00name"},
            {"ordering": "user__email"}, {"workspace_id": "bad"},
        ):
            with self.subTest(values=values):
                serializer = AnalyticsQuerySerializer(data=values)
                self.assertFalse(serializer.is_valid())

    def test_default_period_uses_current_vietnam_month(self):
        with patch("apps.tasks.analytics_serializers.timezone.now", return_value=datetime(2026, 10, 31, 18, tzinfo=dt_timezone.utc)):
            serializer = AnalyticsQuerySerializer(data={})
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data["from"], date(2026, 11, 1))
            self.assertEqual(serializer.validated_data["to"], date(2026, 11, 30))


class AnalyticsApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        for label in ("owner", "admin", "manager", "editor", "other", "viewer", "foreign", "outsider"):
            setattr(cls, label, User.objects.create_user(username=f"analytics-{label}", email=f"analytics-{label}@example.test", password=None))
        cls.profile = create_profile_with_owner(name="Analytics tenant", owner=cls.owner)
        cls.workspace = Workspace.objects.create(profile=cls.profile, owner=cls.owner, name="Analytics month", period=date(2026, 11, 1))
        cls.sibling = Workspace.objects.create(profile=cls.profile, owner=cls.owner, name="Analytics other", period=date(2026, 12, 1))
        cls.memberships = {"owner": ProfileMembership.objects.get(profile=cls.profile, user=cls.owner)}
        for label, profile_role, workspace_role in (
            ("admin", "ADMIN", None), ("manager", "MEMBER", "ADMIN"),
            ("editor", "MEMBER", "MEMBER"), ("other", "MEMBER", "MEMBER"),
            ("viewer", "MEMBER", "VIEWER"),
        ):
            cls.memberships[label] = ProfileMembership.objects.create(profile=cls.profile, user=getattr(cls, label), role=profile_role)
            if workspace_role:
                WorkspaceMember.objects.create(workspace=cls.workspace, user=getattr(cls, label), role=workspace_role)
        cls.foreign_profile = create_profile_with_owner(name="Other analytics tenant", owner=cls.foreign)
        cls.foreign_workspace = Workspace.objects.create(profile=cls.foreign_profile, owner=cls.foreign, name="Foreign analytics", period=date(2026, 11, 1))
        cls.foreign_task = Task.objects.create(workspace=cls.foreign_workspace, created_by=cls.foreign, title="Other tenant private", estimated_compensation_vnd="777777777777777777")

    def setUp(self):
        self.client.force_login(self.owner)
        self.patcher = patch("apps.tasks.analytics.timezone.now", return_value=NOW)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def url(self, suffix="", profile=None):
        return f"/api/v1/profiles/{(profile or self.profile).pk}/analytics/{suffix}"

    def query(self, **values):
        return {"from": "2026-11-01", "to": "2026-11-30", **values}

    def task(self, title="Analytics work", *, status="PENDING", amount=None, actor=None, created=CREATED, workspace=None, deadline=None):
        task = Task.objects.create(
            workspace=workspace or self.workspace, created_by=self.owner, title=title,
            status=status, estimated_compensation_vnd=amount, deadline=deadline,
        )
        Task.objects.filter(pk=task.pk).update(created_at=created)
        task.created_at = created
        if actor:
            TaskAssignment.objects.create(task=task, user=actor)
        return task

    def approve(self, task, *, actor=None, amount=None, recorded=True, approved_at=APPROVED):
        Task.objects.filter(pk=task.pk).update(status="COMPLETED")
        task.status = "COMPLETED"
        deliverable = Deliverable.objects.create(task=task, uploaded_by=actor or self.editor, file_url="https://example.test/analytics-product", revision=1, status="APPROVED")
        review = Review.objects.create(deliverable=deliverable, reviewer=self.owner, status="APPROVED", compensation_snapshot_recorded=recorded, compensation_snapshot_vnd=amount if recorded else None)
        Review.objects.filter(pk=review.pk).update(created_at=approved_at)
        return review

    def summary(self, **params):
        response = self.client.get(self.url(), self.query(**params))
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_metrics_and_donut_use_distinct_states_and_overdue_is_overlapping(self):
        self.task(status="WORKING", amount="10", actor=self.editor, deadline=NOW - timedelta(seconds=1))
        self.task(status="PENDING")
        self.task(status="ASSIGNED", amount="20", actor=self.other)
        self.task(status="REVIEW", amount="30", actor=self.editor, deadline=NOW - timedelta(days=1))
        completed = self.task(status="COMPLETED", amount="400", actor=self.editor, deadline=NOW - timedelta(days=2))
        self.approve(completed, amount="40")
        self.task(status="CANCELLED", amount="0", deadline=NOW - timedelta(days=1))
        self.task(status="COMPLETED", amount="60")
        data = self.summary()
        self.assertEqual(data["kpis"], {"total_tasks": 7, "approved_tasks": 1, "working_tasks": 1, "review_tasks": 1, "overdue_tasks": 2, "unassigned_tasks": 1, "unverified_completed_tasks": 1, "unattributed_approved_tasks": 0})
        self.assertEqual(sum(item["count"] for item in data["distribution"]), 7)
        self.assertEqual({item["status"] for item in data["distribution"]}, set(Task.Status.values))
        self.assertEqual(data["finance"]["estimated_total_vnd"], "520")
        self.assertEqual(data["finance"]["estimated_unpriced_tasks"], 1)
        self.assertEqual(data["finance"]["approved_total_vnd"], "40")
        self.assertEqual(data["approval_trend"], [{"month": "2026-11", "count": 1}])

    def test_approval_event_period_is_independent_from_task_creation_period(self):
        old = self.task(created=datetime(2026, 10, 1, tzinfo=dt_timezone.utc), amount="900", actor=self.editor)
        self.approve(old, amount="50")
        current = self.task(actor=self.other, amount="800")
        self.approve(current, actor=self.other, amount="80", approved_at=datetime(2026, 12, 1, tzinfo=dt_timezone.utc))
        data = self.summary()
        self.assertEqual(data["kpis"]["total_tasks"], 1)
        self.assertEqual(data["kpis"]["approved_tasks"], 1)
        self.assertEqual(data["finance"]["estimated_total_vnd"], "800")
        self.assertEqual(data["finance"]["approved_total_vnd"], "50")
        self.assertEqual(data["approval_trend"][0]["count"], 1)

    def test_legacy_unknown_unpriced_and_explicit_zero_are_distinct(self):
        self.approve(self.task(), recorded=False)
        self.approve(self.task(), recorded=True, amount=None)
        self.approve(self.task(), recorded=True, amount="0")
        finance = self.summary()["finance"]
        self.assertEqual(finance["approved_total_vnd"], "0")
        self.assertEqual((finance["approved_unknown_tasks"], finance["approved_unpriced_tasks"], finance["approved_priced_tasks"]), (1, 1, 1))
        self.assertIsNone(finance["estimated_total_vnd"])

    def test_large_exact_totals_exceed_javascript_safe_integer_and_single_field_bound(self):
        for _ in range(4):
            self.approve(self.task(amount="999999999999999999"), amount="999999999999999999")
        finance = self.summary()["finance"]
        self.assertEqual(finance["estimated_total_vnd"], "3999999999999999996")
        self.assertEqual(finance["approved_total_vnd"], "3999999999999999996")

    def test_hcm_midnight_boundaries_and_empty_months(self):
        boundary = datetime(2026, 10, 31, 17, tzinfo=dt_timezone.utc)
        self.task(created=boundary - timedelta(microseconds=1))
        within = self.task(created=boundary)
        self.approve(within, approved_at=boundary)
        self.task(created=datetime(2026, 11, 30, 17, tzinfo=dt_timezone.utc))
        data = self.summary()
        self.assertEqual(data["kpis"]["total_tasks"], 1)
        self.assertEqual(data["approval_trend"], [{"month": "2026-11", "count": 1}])
        response = self.client.get(self.url(), {"from": "2026-10-01", "to": "2026-12-31"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["approval_trend"], [{"month": "2026-10", "count": 0}, {"month": "2026-11", "count": 1}, {"month": "2026-12", "count": 0}])

    def test_only_latest_approved_revision_counts(self):
        task = self.task()
        self.approve(task, amount="50")
        newer = Deliverable.objects.create(task=task, uploaded_by=self.editor, file_url="https://example.test/newer", status="REJECTED", revision=2)
        # The suite freezes timezone.now(); make revision chronology explicit
        # instead of relying on random UUID ordering when timestamps are equal.
        Deliverable.objects.filter(pk=newer.pk).update(created_at=NOW + timedelta(microseconds=1))
        data = self.summary()
        self.assertEqual(data["kpis"]["approved_tasks"], 0)
        self.assertEqual(data["kpis"]["unverified_completed_tasks"], 1)
        self.assertIsNone(data["finance"]["approved_total_vnd"])

    def test_employee_attribution_uses_uploader_not_current_assignment(self):
        task = self.task(actor=self.other, amount="500")
        self.approve(task, actor=self.editor, amount="40")
        response = self.client.get(self.url("employees/"), self.query())
        self.assertEqual(response.status_code, 200, response.data)
        rows = {item["id"]: item for item in response.data["results"]}
        credited = rows[str(self.memberships["editor"].pk)]
        self.assertEqual(credited["approved_tasks"], 1)
        self.assertEqual(credited["finance"]["approved_total_vnd"], "40")
        self.assertEqual(rows[str(self.memberships["other"].pk)]["approved_tasks"], 0)
        detail = self.client.get(self.url(f"employees/{credited['id']}/"), self.query())
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data["results"][0]["relation"], "approved")
        self.assertEqual(detail.data["results"][0]["id"], str(task.pk))

    def test_reassignment_changes_current_employee_totals_without_changing_organization(self):
        task = self.task(status="ASSIGNED", amount="500000", actor=self.editor)
        before = self.summary()
        first = self.client.get(self.url("employees/"), self.query()).data["results"]
        self.assertEqual(next(row for row in first if row["id"] == str(self.memberships["editor"].pk))["active_tasks"], 1)
        TaskAssignment.objects.filter(task=task).update(is_active=False)
        TaskAssignment.objects.create(task=task, user=self.other)
        after = self.summary()
        second = self.client.get(self.url("employees/"), self.query()).data["results"]
        old = next(row for row in second if row["id"] == str(self.memberships["editor"].pk))
        new = next(row for row in second if row["id"] == str(self.memberships["other"].pk))
        self.assertEqual(old["active_tasks"], 0)
        self.assertEqual(new["active_tasks"], 1)
        self.assertEqual(new["finance"]["active_total_vnd"], "500000")
        self.assertIsNone(old["finance"]["active_total_vnd"])
        self.assertEqual(before["kpis"], after["kpis"])
        self.assertEqual(before["finance"], after["finance"])

    def test_employee_identity_is_tenant_membership_only_and_revoked_names_are_redacted(self):
        self.approve(self.task(), actor=self.editor, amount="20")
        User.objects.filter(pk=self.editor.pk).update(first_name="Do not reveal", last_name="Private")
        ProfileMembership.objects.filter(pk=self.memberships["editor"].pk).update(is_active=False)
        response = self.client.get(self.url("employees/"), self.query())
        row = next(item for item in response.data["results"] if item["id"] == str(self.memberships["editor"].pk))
        self.assertIsNone(row["display_name"])
        self.assertFalse(row["is_available"])
        serialized = json.dumps(response.data)
        self.assertNotIn("Do not reveal", serialized)
        self.assertNotIn(str(self.editor.pk), serialized)
        self.assertNotIn(self.editor.email, serialized)
        hidden_search = self.client.get(self.url("employees/"), self.query(search="Private"))
        self.assertEqual(hidden_search.data["count"], 0)

    def test_employee_search_sort_and_pagination(self):
        User.objects.filter(pk=self.editor.pk).update(first_name="An", last_name="Nguyễn")
        self.task(actor=self.editor, status="WORKING", amount="30")
        self.approve(self.task(), actor=self.other, amount="90")
        response = self.client.get(self.url("employees/"), self.query(search="Nguyễn", page_size=1))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        ordered = self.client.get(self.url("employees/"), self.query(ordering="-approved_value"))
        self.assertEqual(ordered.status_code, 200, ordered.data)
        self.assertEqual(ordered.data["results"][0]["id"], str(self.memberships["other"].pk))

    def test_profile_managers_and_selected_workspace_admin_get_management_scope(self):
        self.task(amount="50")
        self.task(amount="90", workspace=self.sibling)
        for actor in (self.owner, self.admin):
            self.client.force_login(actor)
            data = self.summary()
            self.assertEqual(data["scope"]["mode"], "management")
            self.assertEqual(data["finance"]["estimated_total_vnd"], "140")
        self.client.force_login(self.manager)
        data = self.summary(workspace_id=str(self.workspace.pk))
        self.assertEqual(data["scope"]["mode"], "management")
        self.assertEqual(data["finance"]["estimated_total_vnd"], "50")
        own = self.summary()
        self.assertEqual(own["scope"]["mode"], "self")
        self.assertEqual(own["kpis"]["total_tasks"], 0)

    def test_member_self_scope_does_not_disclose_coworker_tasks_or_money(self):
        own = self.task(actor=self.editor, amount="10")
        self.task(title="Coworker private task", actor=self.other, amount="987654321")
        self.client.force_login(self.editor)
        data = self.summary()
        self.assertEqual(data["scope"]["mode"], "self")
        self.assertEqual(data["kpis"]["total_tasks"], 1)
        self.assertEqual(data["finance"]["estimated_total_vnd"], "10")
        self.assertNotIn("987654321", json.dumps(data))
        members = self.client.get(self.url("employees/"), self.query())
        self.assertEqual([row["id"] for row in members.data["results"]], [str(self.memberships["editor"].pk)])
        denied = self.client.get(self.url(f"employees/{self.memberships['other'].pk}/"), self.query())
        self.assertEqual(denied.status_code, 404)
        own_detail = self.client.get(self.url(f"employees/{self.memberships['editor'].pk}/"), self.query())
        self.assertEqual([row["id"] for row in own_detail.data["results"]], [str(own.pk)])

    def test_viewer_retained_assignment_never_gets_finance(self):
        self.task(actor=self.viewer, amount="7654321")
        self.client.force_login(self.viewer)
        data = self.summary()
        self.assertIsNone(data["finance"])
        self.assertFalse(data["capabilities"]["can_view_financial_totals"])
        rows = self.client.get(self.url("employees/"), self.query()).data["results"]
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["finance"])
        self.assertNotIn("7654321", json.dumps(rows))
        self.assertEqual(self.client.get(self.url("employees/"), self.query(ordering="-approved_value")).status_code, 400)

    def test_historical_uploader_without_current_assignment_has_no_old_pay_privilege(self):
        task = self.task(actor=self.other)
        self.approve(task, actor=self.editor, amount="123456789")
        self.client.force_login(self.editor)
        data = self.summary()
        self.assertEqual(data["kpis"]["approved_tasks"], 1)
        self.assertIsNone(data["finance"]["approved_total_vnd"])
        self.assertNotIn("123456789", json.dumps(data))

    def test_self_statistics_never_credit_a_different_historical_uploader(self):
        task = self.task(actor=self.other, amount="500")
        self.approve(task, actor=self.editor, amount="123456789")
        self.client.force_login(self.other)
        data = self.summary()
        self.assertEqual(data["kpis"]["total_tasks"], 1)
        self.assertEqual(data["kpis"]["approved_tasks"], 0)
        self.assertEqual(data["kpis"]["unverified_completed_tasks"], 0)
        self.assertEqual(data["approval_trend"][0]["count"], 0)
        self.assertIsNone(data["finance"]["approved_total_vnd"])
        self.assertNotIn("123456789", json.dumps(data))

    def test_financial_selector_agrees_with_existing_task_compensation_policy(self):
        self.task(actor=self.editor, amount="1")
        self.task(actor=self.other, amount="2")
        filters = AnalyticsQuerySerializer(data=self.query(workspace_id=str(self.workspace.pk)))
        self.assertTrue(filters.is_valid())
        for actor in (self.owner, self.admin, self.manager, self.editor, self.viewer):
            scope = resolve_analytics_scope(actor=actor, profile_id=self.profile.pk, filters=filters.validated_data)
            ctx = resolve_workspace_access_context(resolve_profile_access_context(actor, self.profile.pk), self.workspace.pk)
            expected = set(task_compensation_visible_to(actor, ctx).filter(pk__in=scope.tasks.values("pk")).values_list("pk", flat=True))
            self.assertEqual(set(_financial_tasks(scope).values_list("pk", flat=True)), expected)

    def test_cross_profile_workspace_and_employee_idor_are_denied(self):
        self.assertEqual(self.client.get(self.url(profile=self.foreign_profile), self.query()).status_code, 404)
        self.assertEqual(self.client.get(self.url(), self.query(workspace_id=str(self.foreign_workspace.pk))).status_code, 404)
        foreign_membership = ProfileMembership.objects.get(profile=self.foreign_profile, user=self.foreign)
        self.assertEqual(self.client.get(self.url(f"employees/{foreign_membership.pk}/"), self.query()).status_code, 404)
        self.assertEqual(self.client.get(self.url("employees/not-a-uuid/"), self.query()).status_code, 404)

    def test_revoked_membership_inactive_user_and_staff_flag_do_not_grant_analytics(self):
        self.client.force_login(self.editor)
        ProfileMembership.objects.filter(pk=self.memberships["editor"].pk).update(is_active=False)
        self.assertEqual(self.client.get(self.url(), self.query()).status_code, 404)
        self.client.force_login(self.outsider)
        User.objects.filter(pk=self.outsider.pk).update(is_staff=True, is_superuser=True)
        self.assertEqual(self.client.get(self.url(), self.query()).status_code, 404)

    def test_archived_scopes_keep_existing_read_only_analytics_policy(self):
        self.task(amount="30")
        Profile.objects.filter(pk=self.profile.pk).update(status="ARCHIVED")
        Workspace.objects.filter(pk=self.workspace.pk).update(status="ARCHIVED")
        self.assertEqual(self.summary()["finance"]["estimated_total_vnd"], "30")

    def test_lazy_scope_fails_closed_after_profile_or_workspace_role_revocation(self):
        self.task(amount="99")
        serializer = AnalyticsQuerySerializer(data=self.query(workspace_id=str(self.workspace.pk)))
        self.assertTrue(serializer.is_valid())
        scope = resolve_analytics_scope(actor=self.manager, profile_id=self.profile.pk, filters=serializer.validated_data)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.manager).update(role="VIEWER")
        self.assertFalse(scope.tasks.exists())
        self.assertFalse(_financial_tasks(scope).exists())

    def test_profile_manager_downgrade_cannot_keep_management_money(self):
        self.task(amount="987654321")
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.admin, role="VIEWER")
        serializer = AnalyticsQuerySerializer(data=self.query())
        self.assertTrue(serializer.is_valid())
        scope = resolve_analytics_scope(actor=self.admin, profile_id=self.profile.pk, filters=serializer.validated_data)
        ProfileMembership.objects.filter(pk=self.memberships["admin"].pk).update(role="MEMBER")
        self.assertFalse(scope.tasks.exists())
        self.assertFalse(_financial_tasks(scope).exists())

    def test_legacy_approved_uploader_without_membership_is_counted_as_unattributed(self):
        self.approve(self.task(), actor=self.outsider, amount="30")
        data = self.summary()
        self.assertEqual(data["kpis"]["unattributed_approved_tasks"], 1)
        self.assertEqual(data["approval_trend"][0]["count"], 1)
        self.assertEqual(data["finance"]["approved_total_vnd"], "30")
        employees = self.client.get(self.url("employees/"), self.query())
        self.assertNotIn(str(self.outsider.pk), json.dumps(employees.data))

    def test_pagination_query_count_does_not_grow_per_employee(self):
        with CaptureQueriesContext(connection) as small:
            first = self.client.get(self.url("employees/"), self.query(page_size=100))
        self.assertEqual(first.status_code, 200, first.data)
        for index in range(15):
            actor = User.objects.create_user(username=f"analytics-extra-{index}", email=f"analytics-extra-{index}@example.test", password=None)
            ProfileMembership.objects.create(profile=self.profile, user=actor)
            WorkspaceMember.objects.create(workspace=self.workspace, user=actor, role="MEMBER")
        with CaptureQueriesContext(connection) as large:
            response = self.client.get(self.url("employees/"), self.query(page_size=100))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], first.data["count"] + 15)
        self.assertLessEqual(len(large), len(small) + 1)

    def test_anonymous_mutation_methods_and_cache_headers(self):
        anonymous = APIClient(enforce_csrf_checks=True)
        self.assertEqual(anonymous.get(self.url(), self.query()).status_code, 403)
        self.assertEqual(self.client.post(self.url(), {}, format="json").status_code, 405)
        response = self.client.get(self.url(), self.query())
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response.status_code, 200)

    def test_snapshot_database_checks_reject_negative_or_unrecorded_nonnull_values(self):
        task = self.task()
        review = self.approve(task, amount="0")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.filter(pk=review.pk).update(compensation_snapshot_vnd=-1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.filter(pk=review.pk).update(compensation_snapshot_recorded=False, compensation_snapshot_vnd=1)

    def test_approval_service_freezes_price_and_later_task_edit_cannot_rewrite_it(self):
        from .services import approve_deliverable, submit_deliverable, update_task
        task = self.task(status="WORKING", actor=self.editor, amount="500000")
        deliverable = submit_deliverable(actor=self.editor, profile_id=self.profile.pk, workspace_id=self.workspace.pk, task_id=task.pk, file_url="https://example.test/snapshot-work")
        review = approve_deliverable(actor=self.owner, profile_id=self.profile.pk, workspace_id=self.workspace.pk, task_id=task.pk, deliverable_id=deliverable.pk)
        self.assertTrue(review.compensation_snapshot_recorded)
        self.assertEqual(review.compensation_snapshot_vnd, Decimal("500000"))
        update_task(actor=self.owner, profile_id=self.profile.pk, workspace_id=self.workspace.pk, task_id=task.pk, estimated_compensation_vnd="900000")
        review.refresh_from_db()
        self.assertEqual(review.compensation_snapshot_vnd, Decimal("500000"))

