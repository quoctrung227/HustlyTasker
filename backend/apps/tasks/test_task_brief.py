"""Task video brief metadata, exact VND and existing tenant/RBAC boundaries."""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.workspace.models import ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .brief import (
    TASK_BRIEF_URL_FIELDS, TASK_COMPENSATION_MAX,
    normalize_task_compensation, normalize_task_reference,
)
from .models import Task, TaskAssignment
from .serializers import TaskCreateSerializer
from .services import create_task, update_task


User = get_user_model()
URLS = {
    "raw_video_url": "https://drive.example.test/raw?resource=synthetic",
    "reference_video_url": "http://example.test/reference",
    "template_project_url": "https://example.test/template-project",
    "script_url": "https://docs.example.test/script/edit",
}


class TaskBriefValueTests(SimpleTestCase):
    def test_http_https_private_document_links_are_validated_without_fetching(self):
        for field, value in URLS.items():
            with self.subTest(field=field):
                self.assertEqual(normalize_task_reference(f" {value} ", field=field), value)
        self.assertEqual(normalize_task_reference("HTTPS://example.test/private", field="script_url"), "HTTPS://example.test/private")

    def test_blank_reference_values_are_nullable(self):
        for value in (None, "", "  "):
            self.assertIsNone(normalize_task_reference(value, field="script_url"))

    def test_unsafe_schemes_controls_unicode_and_overflow_are_rejected(self):
        for value in (
            "javascript:alert(1)", "data:text/html,test", "ftp://example.test/file",
            "file:///tmp/file", "//example.test/file", "not a URL",
            "https://example.test/\x00", "https://example.test/\ud800",
            "https://example.test/" + "x" * 2048, {}, 42,
        ):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValidationError):
                    normalize_task_reference(value, field="script_url")

    def test_whole_vnd_values_keep_exact_storage_precision(self):
        self.assertEqual(normalize_task_compensation("999999999999999999"), TASK_COMPENSATION_MAX)
        self.assertEqual(normalize_task_compensation(500000), 500000)
        self.assertEqual(normalize_task_compensation("000500000"), 500000)
        self.assertEqual(normalize_task_compensation(0), 0)
        self.assertIsNone(normalize_task_compensation(None))
        self.assertIsNone(normalize_task_compensation(""))

    def test_float_bool_scientific_signed_fractional_and_out_of_range_vnd_are_rejected(self):
        for value in (
            True, False, 1.0, 1.2, float("inf"), float("nan"), -1,
            "-1", "+1", "1.0", "1e3", "500.000", "1,000", " 100 ",
            "1000000000000000000", 10 ** 30, {}, [], Decimal("1"),
        ):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValidationError):
                    normalize_task_compensation(value)

    def test_model_read_decimal_validation_is_bounded_before_integer_conversion(self):
        self.assertEqual(normalize_task_compensation(Decimal("500000"), allow_decimal=True), 500000)
        for value in (Decimal("1.5"), Decimal("1e100000"), Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValidationError):
                    normalize_task_compensation(value, allow_decimal=True)

    def test_serializer_rejects_lone_unicode_surrogate_before_http_encoding(self):
        serializer = TaskCreateSerializer(data={"title": "Brief", "script_url": "https://example.test/\ud800"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("script_url", serializer.errors)


class TaskBriefApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        for label in ("owner", "manager", "editor", "viewer", "outsider", "foreign"):
            setattr(cls, label, User.objects.create_user(
                username=f"brief-{label}", email=f"brief-{label}@example.test", password=None,
            ))
        cls.profile = create_profile_with_owner(name="Task brief profile", owner=cls.owner)
        cls.workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="Brief month", period=date(2026, 11, 1),
        )
        cls.memberships = {}
        for label, role in (("manager", "ADMIN"), ("editor", "MEMBER"), ("viewer", "VIEWER")):
            actor = getattr(cls, label)
            cls.memberships[label] = ProfileMembership.objects.create(profile=cls.profile, user=actor)
            WorkspaceMember.objects.create(workspace=cls.workspace, user=actor, role=role)
        cls.foreign_profile = create_profile_with_owner(name="Foreign brief profile", owner=cls.foreign)
        cls.foreign_workspace = Workspace.objects.create(
            profile=cls.foreign_profile, owner=cls.foreign, name="Foreign month", period=date(2026, 11, 1),
        )
        cls.task = Task.objects.create(
            workspace=cls.workspace, created_by=cls.owner, title="Existing task", description="Existing description",
        )
        cls.child = Task.objects.create(
            workspace=cls.workspace, created_by=cls.owner, title="Existing child", parent=cls.task,
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def url(self, task=None, **scope):
        kwargs = {"profile_id": self.profile.id, "workspace_id": self.workspace.id, **scope}
        name = "task-list"
        if task is not None:
            kwargs["task_id"] = getattr(task, "pk", task)
            name = "task-detail"
        return reverse(f"tasks:{name}", kwargs=kwargs)

    def create(self, **metadata):
        return self.client.post(self.url(), {"title": "New brief", **metadata}, format="json")

    def patch_task(self, **metadata):
        return self.client.patch(self.url(self.task), metadata, format="json")

    def test_legacy_title_only_create_and_read_preserve_existing_contract_with_null_metadata(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "New brief")
        self.assertEqual(response.data["priority"], "MEDIUM")
        self.assertIsNone(response.data["deadline"])
        for field in (*TASK_BRIEF_URL_FIELDS, "estimated_compensation_vnd"):
            self.assertIsNone(response.data[field])
        detail = self.client.get(self.url(response.data["id"]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data, response.data)

    def test_all_four_urls_and_exact_amount_round_trip_in_create_list_detail_update(self):
        response = self.create(**URLS, estimated_compensation_vnd="999999999999999999")
        self.assertEqual(response.status_code, 201)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.estimated_compensation_vnd, Decimal("999999999999999999"))
        for field, value in URLS.items():
            self.assertEqual(response.data[field], value)
            self.assertEqual(getattr(task, field), value)
        self.assertEqual(response.data["estimated_compensation_vnd"], "999999999999999999")
        listed = self.client.get(self.url())
        listed_row = next(row for row in listed.data["results"] if str(row["id"]) == str(task.id))
        self.assertEqual(listed_row["estimated_compensation_vnd"], "999999999999999999")
        detail = self.client.get(self.url(task))
        self.assertEqual(detail.data, response.data)

    def test_patch_updates_each_url_independently_without_clearing_other_fields(self):
        self.assertEqual(self.patch_task(**URLS, estimated_compensation_vnd=500000).status_code, 200)
        expected = dict(URLS)
        for field in TASK_BRIEF_URL_FIELDS:
            value = f"https://example.test/updated/{field}"
            response = self.patch_task(**{field: value})
            self.assertEqual(response.status_code, 200)
            expected[field] = value
            for current_field, current_value in expected.items():
                self.assertEqual(response.data[current_field], current_value)
            self.assertEqual(response.data["estimated_compensation_vnd"], "500000")
            self.assertEqual(response.data["title"], "Existing task")
            self.assertEqual(response.data["description"], "Existing description")

    def test_blank_and_null_references_and_compensation_can_be_cleared(self):
        self.assertEqual(self.patch_task(**URLS, estimated_compensation_vnd=500000).status_code, 200)
        for index, field in enumerate(TASK_BRIEF_URL_FIELDS):
            response = self.patch_task(**{field: "" if index % 2 else None})
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.data[field])
        self.assertEqual(self.patch_task(estimated_compensation_vnd=None).status_code, 200)
        self.task.refresh_from_db()
        self.assertTrue(all(getattr(self.task, field) is None for field in TASK_BRIEF_URL_FIELDS))
        self.assertIsNone(self.task.estimated_compensation_vnd)

    def test_empty_optional_create_values_are_normalized_to_null(self):
        response = self.create(**{field: "  " for field in TASK_BRIEF_URL_FIELDS}, estimated_compensation_vnd="")
        self.assertEqual(response.status_code, 201)
        for field in (*TASK_BRIEF_URL_FIELDS, "estimated_compensation_vnd"):
            self.assertIsNone(response.data[field])

    def test_dangerous_or_malformed_reference_urls_are_rejected_without_creating_rows(self):
        before = (Task.objects.count(), AuditLog.objects.count())
        for field in TASK_BRIEF_URL_FIELDS:
            for value in ("javascript:alert(1)", "data:text/plain,no", "ftp://example.test/file", "not a URL", "https://example.test/\x00"):
                with self.subTest(field=field):
                    response = self.create(**{field: value})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.data)
        self.assertEqual((Task.objects.count(), AuditLog.objects.count()), before)

    def test_maximum_reference_length_is_enforced_on_create_and_patch(self):
        too_long = "https://example.test/" + "x" * 2048
        for field in TASK_BRIEF_URL_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(self.create(**{field: too_long}).status_code, 400)
                self.assertEqual(self.patch_task(**{field: too_long}).status_code, 400)

    def test_zero_integer_and_digit_string_compensation_are_exact(self):
        for value, expected in ((0, "0"), (500000, "500000"), ("000500000", "500000")):
            with self.subTest(value=value):
                response = self.patch_task(estimated_compensation_vnd=value)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["estimated_compensation_vnd"], expected)
                self.task.refresh_from_db()
                self.assertEqual(self.task.estimated_compensation_vnd, Decimal(expected))

    def test_invalid_compensation_is_rejected_without_task_or_audit_mutation(self):
        before = AuditLog.objects.count()
        for value in (-1, -1.5, 1.0, 1.2, True, False, "+1", "-1", "1.0", "1e3", "1000000000000000000", [], {}):
            with self.subTest(value_type=type(value).__name__):
                response = self.patch_task(estimated_compensation_vnd=value)
                self.assertEqual(response.status_code, 400)
                self.assertIn("estimated_compensation_vnd", response.data)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.estimated_compensation_vnd)
        self.assertEqual(AuditLog.objects.count(), before)

    def test_compensation_is_redacted_for_unassigned_member_and_viewer(self):
        self.assertEqual(self.patch_task(estimated_compensation_vnd=500000).status_code, 200)
        for actor in (self.owner, self.manager, self.editor, self.viewer):
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                response = self.client.get(self.url(self.task))
                self.assertEqual(response.status_code, 200)
                expected = "500000" if actor in (self.owner, self.manager) else None
                self.assertEqual(response.data["estimated_compensation_vnd"], expected)

    def test_editor_and_viewer_cannot_edit_brief_or_pay(self):
        for actor in (self.editor, self.viewer):
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                self.assertEqual(self.patch_task(**URLS, estimated_compensation_vnd=500000).status_code, 403)
                self.assertEqual(self.create(**URLS).status_code, 403)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.script_url)

    def test_workspace_manager_can_edit_metadata_without_workflow_changes(self):
        self.client.force_login(self.manager)
        response = self.patch_task(**URLS, estimated_compensation_vnd=500000)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertIsNone(response.data["active_assignment"])

    def test_outsider_foreign_scope_and_revoked_membership_never_expose_pay(self):
        self.assertEqual(self.patch_task(estimated_compensation_vnd=500000).status_code, 200)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.url(self.task)).status_code, 404)
        self.client.force_login(self.foreign)
        self.assertEqual(self.client.get(self.url(self.task)).status_code, 404)
        self.assertEqual(self.client.get(self.url(self.task, profile_id=self.foreign_profile.id, workspace_id=self.foreign_workspace.id)).status_code, 404)
        ProfileMembership.objects.filter(pk=self.memberships["editor"].id).update(is_active=False)
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(self.url(self.task)).status_code, 404)

    def test_archived_workspace_keeps_existing_reads_but_denies_metadata_writes(self):
        Workspace.objects.filter(pk=self.workspace.id).update(status="ARCHIVED")
        self.assertEqual(self.client.get(self.url(self.task)).status_code, 200)
        self.assertEqual(self.patch_task(**URLS, estimated_compensation_vnd=500000).status_code, 403)

    def test_unknown_server_controlled_fields_do_not_change_authority(self):
        for injected in ({"compensation_user_id": str(self.editor.id)}, {"status": "COMPLETED"}, {"workspace_id": str(self.foreign_workspace.id)}):
            with self.subTest(field=next(iter(injected))):
                self.assertEqual(self.create(**injected, **URLS).status_code, 400)

    def test_metadata_audit_uses_field_names_only_not_urls_or_amount_values(self):
        response = self.patch_task(**URLS, estimated_compensation_vnd=500000)
        self.assertEqual(response.status_code, 200)
        audit = AuditLog.objects.filter(action="task.updated", entity_id=self.task.id).latest("created_at")
        self.assertEqual(set(audit.metadata), {"profile_id", "workspace_id", "changed_fields"})
        self.assertEqual(set(audit.metadata["changed_fields"]), {*TASK_BRIEF_URL_FIELDS, "estimated_compensation_vnd"})
        rendered = json.dumps(audit.metadata)
        for value in (*URLS.values(), "500000"):
            self.assertNotIn(value, rendered)

    def test_failed_audit_rolls_back_brief_create_and_update(self):
        before = (Task.objects.count(), AuditLog.objects.count())
        with patch("apps.tasks.services._write_audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                create_task(actor=self.owner, profile_id=self.profile.id, workspace_id=self.workspace.id,
                            title="Rollback brief", **URLS, estimated_compensation_vnd=500000)
            with self.assertRaises(RuntimeError):
                update_task(actor=self.owner, profile_id=self.profile.id, workspace_id=self.workspace.id,
                            task_id=self.task.id, **URLS, estimated_compensation_vnd=500000)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.script_url)
        self.assertIsNone(self.task.estimated_compensation_vnd)
        self.assertEqual((Task.objects.count(), AuditLog.objects.count()), before)

    def test_service_callers_cannot_bypass_url_or_numeric_input_validation(self):
        for metadata in ({"script_url": "javascript:alert(1)"}, {"estimated_compensation_vnd": 1.0}, {"estimated_compensation_vnd": True}):
            with self.subTest(field=next(iter(metadata))):
                with self.assertRaises(ValidationError):
                    create_task(actor=self.owner, profile_id=self.profile.id, workspace_id=self.workspace.id,
                                title="Invalid service brief", **metadata)
                with self.assertRaises(ValidationError):
                    update_task(actor=self.owner, profile_id=self.profile.id, workspace_id=self.workspace.id,
                                task_id=self.task.id, **metadata)

    def test_model_validation_does_not_coerce_float_or_allow_non_http_url(self):
        for metadata in ({"script_url": "ftp://example.test/file"}, {"estimated_compensation_vnd": 1.0}):
            with self.subTest(field=next(iter(metadata))):
                task = Task(workspace=self.workspace, created_by=self.owner, title="Invalid model brief", **metadata)
                with self.assertRaises(ValidationError):
                    task.full_clean()

    def test_brief_update_preserves_existing_subtask_relationships_and_assignment_history(self):
        assignment = TaskAssignment.objects.create(task=self.child, user=self.editor, is_active=True)
        before = (self.child.id, self.child.parent_id, self.child.status, self.child.priority)
        self.assertEqual(self.patch_task(**URLS, estimated_compensation_vnd=500000).status_code, 200)
        self.child.refresh_from_db()
        self.assertEqual((self.child.id, self.child.parent_id, self.child.status, self.child.priority), before)
        self.assertTrue(TaskAssignment.objects.filter(pk=assignment.id, task=self.child, is_active=True).exists())
        old_child_detail = self.client.get(self.url(self.child))
        self.assertEqual(old_child_detail.status_code, 200)
        self.assertIsNone(old_child_detail.data["estimated_compensation_vnd"])
        child_route = reverse("tasks:task-subtask-list", kwargs={"profile_id": self.profile.id, "workspace_id": self.workspace.id, "task_id": self.task.id})
        self.assertEqual(str(self.client.get(child_route).data["results"][0]["id"]), str(self.child.id))

    def test_pay_is_one_task_amount_not_multiplied_by_assignment_history(self):
        TaskAssignment.objects.create(task=self.task, user=self.owner, is_active=False)
        TaskAssignment.objects.create(task=self.task, user=self.editor, is_active=True)
        response = self.patch_task(estimated_compensation_vnd=500000)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["estimated_compensation_vnd"], "500000")
        self.assertEqual(TaskAssignment.objects.filter(task=self.task).count(), 2)
        self.assertEqual(TaskAssignment.objects.filter(task=self.task, is_active=True).count(), 1)

    def test_authenticated_mutation_still_requires_session_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.url(), {"title": "Anonymous"}, format="json").status_code, 403)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url(), {"title": "No CSRF"}, format="json").status_code, 403)
        csrf = client.get("/api/auth/csrf/")
        self.assertEqual(csrf.status_code, 200)
        response = client.post(self.url(), {"title": "With CSRF", **URLS}, format="json", HTTP_X_CSRFTOKEN=csrf.data["csrf_token"])
        self.assertEqual(response.status_code, 201)
