from datetime import date
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.reviews.models import Deliverable
from apps.workspace.models import ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.admin import WorkspaceAdmin
from apps.workspace.services import create_profile_with_owner

from .admin import TaskAdmin, TaskAssignmentAdmin, TaskCommentAdmin
from .models import Task, TaskAssignment, TaskComment


User = get_user_model()


class TaskApiTests(APITestCase):
    task_fields = {
        "id",
        "workspace_id",
        "title",
        "description",
        "status",
        "priority",
        "deadline",
        "active_assignment",
        "created_at",
        "updated_at",
    }
    deliverable_fields = {
        "id",
        "task_id",
        "revision",
        "file_url",
        "status",
        "uploaded_by_profile_membership_id",
        "review",
        "created_at",
        "updated_at",
    }
    review_fields = {
        "id",
        "status",
        "comment",
        "reviewer_profile_membership_id",
        "created_at",
        "updated_at",
    }

    @classmethod
    def setUpTestData(cls):
        cls.owner = cls._create_user("owner")
        cls.profile_admin = cls._create_user("profile-admin")
        cls.workspace_admin = cls._create_user("workspace-admin")
        cls.editor = cls._create_user("editor")
        cls.second_editor = cls._create_user("second-editor")
        cls.viewer = cls._create_user("viewer")
        cls.unassigned_member = cls._create_user("unassigned-member")
        cls.other_owner = cls._create_user("other-owner")
        cls.other_editor = cls._create_user("other-editor")
        cls.outsider = cls._create_user("outsider")

        cls.profile = create_profile_with_owner(
            name="Task API Profile",
            owner=cls.owner,
        )
        cls.owner_membership = ProfileMembership.objects.get(
            profile=cls.profile,
            user=cls.owner,
        )
        cls.profile_admin_membership = cls._profile_membership(
            cls.profile_admin,
            role=ProfileMembership.Role.ADMIN,
        )
        cls.workspace_admin_membership = cls._profile_membership(
            cls.workspace_admin
        )
        cls.editor_membership = cls._profile_membership(cls.editor)
        cls.second_editor_membership = cls._profile_membership(
            cls.second_editor
        )
        cls.viewer_membership = cls._profile_membership(cls.viewer)
        cls.unassigned_profile_membership = cls._profile_membership(
            cls.unassigned_member
        )

        cls.workspace = Workspace.objects.create(
            profile=cls.profile,
            owner=cls.owner,
            name="Task API Workspace",
            period=date(2026, 10, 1),
        )
        cls.sibling_workspace = Workspace.objects.create(
            profile=cls.profile,
            owner=cls.owner,
            name="Sibling Task API Workspace",
            period=date(2026, 11, 1),
        )
        WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.workspace_admin,
            role=WorkspaceMember.Role.ADMIN,
        )
        WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.editor,
            role=WorkspaceMember.Role.MEMBER,
        )
        WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.second_editor,
            role=WorkspaceMember.Role.MEMBER,
        )
        WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.viewer,
            role=WorkspaceMember.Role.VIEWER,
        )

        cls.task = Task.objects.create(
            workspace=cls.workspace,
            title="Existing API Task",
            description="Existing task description",
            created_by=cls.owner,
        )
        cls.sibling_task = Task.objects.create(
            workspace=cls.sibling_workspace,
            title="Sibling API Task",
            created_by=cls.owner,
        )

        cls.other_profile = create_profile_with_owner(
            name="Other Task API Profile",
            owner=cls.other_owner,
        )
        cls.other_editor_membership = ProfileMembership.objects.create(
            profile=cls.other_profile,
            user=cls.other_editor,
            role=ProfileMembership.Role.MEMBER,
        )
        cls.other_workspace = Workspace.objects.create(
            profile=cls.other_profile,
            owner=cls.other_owner,
            name="Other Task API Workspace",
            period=date(2026, 10, 1),
        )
        WorkspaceMember.objects.create(
            workspace=cls.other_workspace,
            user=cls.other_editor,
            role=WorkspaceMember.Role.MEMBER,
        )
        cls.other_task = Task.objects.create(
            workspace=cls.other_workspace,
            title="Other Tenant Task",
            created_by=cls.other_owner,
        )

    @classmethod
    def _create_user(cls, suffix):
        return User.objects.create_user(
            email=f"task-api-{suffix}@example.test",
            username=f"task-api-{suffix}",
            password=None,
        )

    @classmethod
    def _profile_membership(
        cls,
        user,
        *,
        role=ProfileMembership.Role.MEMBER,
    ):
        return ProfileMembership.objects.create(
            profile=cls.profile,
            user=user,
            role=role,
        )

    def setUp(self):
        self.client = APIClient()

    def task_list_url(self, *, profile_id=None, workspace_id=None):
        return reverse(
            "tasks:task-list",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "workspace_id": workspace_id or self.workspace.id,
            },
        )

    def task_detail_url(
        self,
        task_id=None,
        *,
        profile_id=None,
        workspace_id=None,
    ):
        return reverse(
            "tasks:task-detail",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "workspace_id": workspace_id or self.workspace.id,
                "task_id": task_id or self.task.id,
            },
        )

    def task_action_url(
        self,
        action,
        task_id=None,
        *,
        profile_id=None,
        workspace_id=None,
    ):
        return reverse(
            f"tasks:task-{action}",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "workspace_id": workspace_id or self.workspace.id,
                "task_id": task_id or self.task.id,
            },
        )

    def deliverable_list_url(
        self,
        task_id=None,
        *,
        profile_id=None,
        workspace_id=None,
    ):
        return reverse(
            "tasks:task-deliverable-list",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "workspace_id": workspace_id or self.workspace.id,
                "task_id": task_id or self.task.id,
            },
        )

    def review_url(
        self,
        action,
        deliverable_id,
        task_id=None,
        *,
        profile_id=None,
        workspace_id=None,
    ):
        return reverse(
            f"tasks:task-deliverable-{action}",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "workspace_id": workspace_id or self.workspace.id,
                "task_id": task_id or self.task.id,
                "deliverable_id": deliverable_id,
            },
        )

    def assert_task_response(self, response, expected_status):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(set(response.data), self.task_fields)
        self.assertNotIn("created_by", response.data)
        self.assertNotIn("owner", response.data)
        self.assertNotIn("profile_id", response.data)

    def assert_deliverable_response(self, response, expected_status):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(set(response.data), self.deliverable_fields)
        self.assertNotIn("uploaded_by", response.data)
        self.assertNotIn("uploaded_by_id", response.data)

    def assign(self, *, actor=None, task=None, membership=None):
        self.client.force_login(actor or self.owner)
        return self.client.post(
            self.task_action_url("assign", task_id=(task or self.task).id),
            {
                "target_profile_membership_id": str(
                    (membership or self.editor_membership).id
                )
            },
            format="json",
        )

    def prepare_submitted_deliverable(self):
        assign_response = self.assign()
        self.assertEqual(assign_response.status_code, status.HTTP_200_OK)

        self.client.force_login(self.editor)
        start_response = self.client.post(
            self.task_action_url("start"),
            {},
            format="json",
        )
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        submit_response = self.client.post(
            self.deliverable_list_url(),
            {"file_url": "https://files.example.test/task/revision-1"},
            format="json",
        )
        self.assertEqual(submit_response.status_code, status.HTTP_201_CREATED)
        return Deliverable.objects.get(id=submit_response.data["id"])

    def test_create_list_and_detail_use_scoped_minimal_responses(self):
        self.client.force_login(self.owner)
        create_response = self.client.post(
            self.task_list_url(),
            {
                "title": "  API-created Task  ",
                "description": "Created through the scoped endpoint",
                "priority": Task.Priority.HIGH,
            },
            format="json",
        )
        self.assert_task_response(create_response, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["title"], "API-created Task")
        self.assertEqual(create_response.data["status"], Task.Status.PENDING)
        self.assertIsNone(create_response.data["active_assignment"])

        created_id = create_response.data["id"]
        for actor in (self.owner, self.editor, self.viewer):
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                list_response = client.get(self.task_list_url())
                self.assertEqual(list_response.status_code, status.HTTP_200_OK)
                self.assertIn(
                    str(created_id),
                    {str(item["id"]) for item in list_response.data["results"]},
                )
                detail_response = client.get(
                    self.task_detail_url(created_id)
                )
                self.assert_task_response(
                    detail_response,
                    status.HTTP_200_OK,
                )

    def test_profile_and_workspace_managers_can_create_and_patch(self):
        actors = (self.owner, self.profile_admin, self.workspace_admin)

        for index, actor in enumerate(actors, start=1):
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                created = client.post(
                    self.task_list_url(),
                    {"title": f"Manager Task {index}"},
                    format="json",
                )
                self.assert_task_response(created, status.HTTP_201_CREATED)
                patched = client.patch(
                    self.task_detail_url(created.data["id"]),
                    {"description": f"Updated by {actor.username}"},
                    format="json",
                )
                self.assert_task_response(patched, status.HTTP_200_OK)
                self.assertEqual(
                    patched.data["description"],
                    f"Updated by {actor.username}",
                )

    def test_editor_viewer_and_unassigned_member_cannot_manage_tasks(self):
        for actor, expected in (
            (self.editor, status.HTTP_403_FORBIDDEN),
            (self.viewer, status.HTTP_403_FORBIDDEN),
            (self.unassigned_member, status.HTTP_404_NOT_FOUND),
        ):
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                created = client.post(
                    self.task_list_url(),
                    {"title": "Forbidden Task"},
                    format="json",
                )
                patched = client.patch(
                    self.task_detail_url(),
                    {"title": "Forbidden update"},
                    format="json",
                )
                self.assertEqual(created.status_code, expected)
                self.assertEqual(patched.status_code, expected)

    def test_task_input_rejects_tenant_status_and_owner_mass_assignment(self):
        self.client.force_login(self.owner)
        before_count = Task.objects.count()
        response = self.client.post(
            self.task_list_url(),
            {
                "title": "Mass assignment attempt",
                "workspace_id": str(self.other_workspace.id),
                "status": Task.Status.COMPLETED,
                "created_by": str(self.outsider.id),
                "active_assignment": {"id": str(uuid4())},
                "unexpected": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSetEqual(
            set(response.data),
            {
                "workspace_id",
                "status",
                "created_by",
                "active_assignment",
                "unexpected",
            },
        )
        self.assertEqual(Task.objects.count(), before_count)

    def test_assignment_and_reassignment_expose_no_user_identity(self):
        first = self.assign()
        self.assert_task_response(first, status.HTTP_200_OK)
        self.assertEqual(first.data["status"], Task.Status.ASSIGNED)
        self.assertEqual(
            str(first.data["active_assignment"]["profile_membership_id"]),
            str(self.editor_membership.id),
        )
        self.assertNotIn("user_id", first.data["active_assignment"])
        self.assertNotIn("email", first.data["active_assignment"])

        second = self.assign(
            actor=self.workspace_admin,
            membership=self.second_editor_membership,
        )
        self.assert_task_response(second, status.HTTP_200_OK)
        self.assertEqual(
            str(second.data["active_assignment"]["profile_membership_id"]),
            str(self.second_editor_membership.id),
        )
        self.assertEqual(
            TaskAssignment.objects.filter(
                task=self.task,
                is_active=True,
            ).count(),
            1,
        )

    def test_assignment_rejects_viewer_cross_tenant_and_raw_user_reference(self):
        for payload in (
            {
                "target_profile_membership_id": str(
                    self.viewer_membership.id
                )
            },
            {
                "target_profile_membership_id": str(
                    self.other_editor_membership.id
                )
            },
            {"target_profile_membership_id": str(uuid4())},
        ):
            with self.subTest(payload=payload):
                self.client.force_login(self.owner)
                response = self.client.post(
                    self.task_action_url("assign"),
                    payload,
                    format="json",
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertEqual(
                    set(response.data),
                    {"target_profile_membership_id"},
                )

        raw_user = self.client.post(
            self.task_action_url("assign"),
            {"user_id": str(self.editor.id)},
            format="json",
        )
        self.assertEqual(raw_user.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(raw_user.data), {"user_id"})

    def test_assigned_editor_can_start_but_cannot_repeat_transition(self):
        self.assign()
        self.client.force_login(self.editor)
        response = self.client.post(
            self.task_action_url("start"),
            {},
            format="json",
        )
        self.assert_task_response(response, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Task.Status.WORKING)

        repeated = self.client.post(
            self.task_action_url("start"),
            {},
            format="json",
        )
        self.assertEqual(repeated.status_code, status.HTTP_409_CONFLICT)

    def test_unassigned_editor_cannot_start_or_submit(self):
        self.assign()
        self.client.force_login(self.second_editor)

        start = self.client.post(
            self.task_action_url("start"),
            {},
            format="json",
        )
        submit = self.client.post(
            self.deliverable_list_url(),
            {"file_url": "https://files.example.test/not-assigned"},
            format="json",
        )
        self.assertEqual(start.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(submit.status_code, status.HTTP_403_FORBIDDEN)

    def test_revision_history_and_internal_approval_workflow(self):
        first = self.prepare_submitted_deliverable()

        self.client.force_login(self.workspace_admin)
        changes = self.client.post(
            self.review_url("request-changes", first.id),
            {"comment": "Please revise this Deliverable."},
            format="json",
        )
        self.assert_deliverable_response(changes, status.HTTP_200_OK)
        self.assertEqual(changes.data["status"], Deliverable.Status.REJECTED)
        self.assertEqual(set(changes.data["review"]), self.review_fields)

        self.client.force_login(self.editor)
        second_response = self.client.post(
            self.deliverable_list_url(),
            {"file_url": "https://files.example.test/task/revision-2"},
            format="json",
        )
        self.assert_deliverable_response(
            second_response,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(second_response.data["revision"], 2)

        self.client.force_login(self.profile_admin)
        approved = self.client.post(
            self.review_url("approve", second_response.data["id"]),
            {"comment": "Approved internally."},
            format="json",
        )
        self.assert_deliverable_response(approved, status.HTTP_200_OK)
        self.assertEqual(approved.data["status"], Deliverable.Status.APPROVED)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        history = self.client.get(self.deliverable_list_url())
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        self.assertEqual(history.data["count"], 2)
        self.assertEqual(
            [item["revision"] for item in history.data["results"]],
            [1, 2],
        )

    def test_reviewer_cannot_self_approve(self):
        deliverable = self.prepare_submitted_deliverable()
        ProfileMembership.objects.filter(id=self.editor_membership.id).update(
            role=ProfileMembership.Role.ADMIN
        )
        self.client.force_login(self.editor)

        response = self.client.post(
            self.review_url("approve", deliverable.id),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        deliverable.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(deliverable.status, Deliverable.Status.SUBMITTED)
        self.assertEqual(self.task.status, Task.Status.REVIEW)

    def test_stale_and_repeated_review_decisions_return_conflict(self):
        first = self.prepare_submitted_deliverable()
        self.client.force_login(self.owner)
        changed = self.client.post(
            self.review_url("request-changes", first.id),
            {"comment": "Revision required."},
            format="json",
        )
        self.assertEqual(changed.status_code, status.HTTP_200_OK)

        self.client.force_login(self.editor)
        second = self.client.post(
            self.deliverable_list_url(),
            {"file_url": "https://files.example.test/task/revision-2"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

        self.client.force_login(self.owner)
        stale = self.client.post(
            self.review_url("approve", first.id),
            {},
            format="json",
        )
        self.assertEqual(stale.status_code, status.HTTP_409_CONFLICT)

        current_url = self.review_url("approve", second.data["id"])
        approved = self.client.post(current_url, {}, format="json")
        repeated = self.client.post(current_url, {}, format="json")
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.assertEqual(repeated.status_code, status.HTTP_409_CONFLICT)

    def test_request_changes_requires_a_nonblank_reason(self):
        deliverable = self.prepare_submitted_deliverable()
        self.client.force_login(self.owner)

        for comment in (None, "", "   "):
            with self.subTest(comment=comment):
                payload = {} if comment is None else {"comment": comment}
                response = self.client.post(
                    self.review_url("request-changes", deliverable.id),
                    payload,
                    format="json",
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertEqual(set(response.data), {"comment"})

    def test_wrong_parent_cross_tenant_and_deliverable_idor_return_404(self):
        self.client.force_login(self.owner)
        wrong_workspace = self.client.get(
            self.task_detail_url(
                self.task.id,
                workspace_id=self.sibling_workspace.id,
            )
        )
        cross_tenant = self.client.get(
            self.task_detail_url(
                self.other_task.id,
                profile_id=self.other_profile.id,
                workspace_id=self.other_workspace.id,
            )
        )
        random_task = self.client.get(self.task_detail_url(uuid4()))
        malformed_task = self.client.get(
            self.task_detail_url("not-a-uuid")
        )

        for response in (
            wrong_workspace,
            cross_tenant,
            random_task,
            malformed_task,
        ):
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response.data, {"detail": "Not found."})

        deliverable = self.prepare_submitted_deliverable()
        self.client.force_login(self.owner)
        wrong_task = self.client.post(
            self.review_url(
                "approve",
                deliverable.id,
                task_id=self.sibling_task.id,
                workspace_id=self.sibling_workspace.id,
            ),
            {},
            format="json",
        )
        self.assertEqual(wrong_task.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(wrong_task.data, {"detail": "Not found."})

        malformed_deliverable = self.client.post(
            self.review_url("approve", "not-a-uuid"),
            {},
            format="json",
        )
        self.assertEqual(
            malformed_deliverable.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            malformed_deliverable.data,
            {"detail": "Not found."},
        )

    def test_archived_profile_and_workspace_block_task_writes(self):
        self.client.force_login(self.owner)
        self.profile.__class__.objects.filter(id=self.profile.id).update(
            status=self.profile.Status.ARCHIVED
        )
        profile_blocked = self.client.post(
            self.task_list_url(),
            {"title": "Blocked by Profile"},
            format="json",
        )
        self.assertEqual(
            profile_blocked.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.profile.__class__.objects.filter(id=self.profile.id).update(
            status=self.profile.Status.ACTIVE
        )
        Workspace.objects.filter(id=self.workspace.id).update(
            status=Workspace.Status.ARCHIVED
        )
        workspace_blocked = self.client.patch(
            self.task_detail_url(),
            {"title": "Blocked by Workspace"},
            format="json",
        )
        self.assertEqual(
            workspace_blocked.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_revoked_workspace_editor_loses_access_immediately(self):
        self.assign()
        WorkspaceMember.objects.filter(
            workspace=self.workspace,
            user=self.editor,
        ).update(is_active=False)
        self.client.force_login(self.editor)

        response = self.client.post(
            self.task_action_url("start"),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_access_is_denied_for_reads_and_writes(self):
        requests = (
            self.client.get(self.task_list_url()),
            self.client.get(self.task_detail_url()),
            self.client.post(
                self.task_list_url(),
                {"title": "Anonymous"},
                format="json",
            ),
            self.client.post(
                self.task_action_url("assign"),
                {
                    "target_profile_membership_id": str(
                        self.editor_membership.id
                    )
                },
                format="json",
            ),
        )
        for response in requests:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_session_task_writes_enforce_csrf(self):
        requests = (
            (
                "post",
                self.task_list_url(),
                {"title": "CSRF create"},
            ),
            (
                "patch",
                self.task_detail_url(),
                {"description": "CSRF update"},
            ),
            (
                "post",
                self.task_action_url("assign"),
                {
                    "target_profile_membership_id": str(
                        self.editor_membership.id
                    )
                },
            ),
        )

        for method, url, payload in requests:
            with self.subTest(method=method, url=url):
                client = APIClient(enforce_csrf_checks=True)
                client.force_login(self.owner)
                response = getattr(client, method)(url, payload, format="json")
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_valid_csrf_token_allows_task_create(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        csrf_response = client.get(reverse("accounts:csrf"))

        response = client.post(
            self.task_list_url(),
            {"title": "CSRF-authorized Task"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
        )

        self.assertEqual(csrf_response.status_code, status.HTTP_200_OK)
        self.assert_task_response(response, status.HTTP_201_CREATED)

    def test_direct_completion_and_hard_delete_are_not_exposed(self):
        self.client.force_login(self.owner)
        completion = self.client.patch(
            self.task_detail_url(),
            {"status": Task.Status.COMPLETED},
            format="json",
        )
        deleted = self.client.delete(self.task_detail_url())

        self.assertEqual(completion.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(completion.data), {"status"})
        self.assertEqual(deleted.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.PENDING)


class TaskWorkflowAdminBoundaryTests(SimpleTestCase):
    def test_admin_does_not_offer_workflow_or_cascading_delete_bypass(self):
        task_admin = TaskAdmin(Task, admin.site)
        assignment_admin = TaskAssignmentAdmin(TaskAssignment, admin.site)
        comment_admin = TaskCommentAdmin(TaskComment, admin.site)
        workspace_admin = WorkspaceAdmin(Workspace, admin.site)

        for model_admin in (
            task_admin,
            assignment_admin,
            comment_admin,
        ):
            self.assertFalse(model_admin.has_add_permission(None))
            self.assertFalse(model_admin.has_change_permission(None))
            self.assertFalse(model_admin.has_delete_permission(None))

        self.assertFalse(workspace_admin.has_delete_permission(None))
