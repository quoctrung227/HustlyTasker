"""Request-bound UI hints must agree with the existing locked mutation policy."""

from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory, APITestCase

from apps.reviews.models import Deliverable, Review
from apps.workspace.access import resolve_profile_access_context, resolve_workspace_access_context
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember

from .comment_serializers import CommentReadSerializer
from .models import Task, TaskAssignment, TaskComment
from .serializers import DeliverableReadSerializer, TaskReadSerializer
from .test_comments import discussion_fixture


class CollaborationCapabilityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        for name, value in discussion_fixture("collaboration-capabilities").items():
            setattr(cls, name, value)
        cls.task.status = Task.Status.WORKING
        cls.task.save(update_fields=("status",))

    def setUp(self):
        self.client.force_login(self.editor)

    def url(self, name="task-detail", task=None, **overrides):
        return reverse(f"tasks:{name}", kwargs={
            "profile_id": self.profile.id,
            "workspace_id": self.workspace.id,
            "task_id": (task or self.task).id,
            **overrides,
        })

    def task_data(self, task=None):
        response = self.client.get(self.url(task=task))
        self.assertEqual(response.status_code, 200)
        return response.data

    def submit(self, task=None, **payload):
        return self.client.post(self.url("task-deliverable-list", task), {
            "file_url": "https://example.test/submission", **payload,
        }, format="json")

    def deliverable(self, *, task=None, actor=None, status=Deliverable.Status.SUBMITTED, revision=1):
        return Deliverable.objects.create(
            task=task or self.task, uploaded_by=actor or self.editor,
            file_url="https://example.test/existing", status=status, revision=revision,
        )

    def review_ready(self, **kwargs):
        Task.objects.filter(pk=self.task.pk).update(status=Task.Status.REVIEW)
        return self.deliverable(**kwargs)

    def deliverable_data(self, deliverable):
        response = self.client.get(self.url("task-deliverable-list"))
        self.assertEqual(response.status_code, 200)
        return next(row for row in response.data["results"] if str(row["id"]) == str(deliverable.id))

    def decide(self, deliverable, action="approve", task=None):
        return self.client.post(self.url(
            f"task-deliverable-{action}", task, deliverable_id=deliverable.id,
        ), {"comment": "Please revise the opening."}, format="json")

    def assert_review_hint(self, deliverable, expected):
        data = self.deliverable_data(deliverable)
        self.assertIs(data["can_approve"], expected)
        self.assertIs(data["can_request_changes"], expected)
        return data

    def comment_url(self, comment=None, **kwargs):
        if comment is None:
            return self.url("task-comment-list", **kwargs)
        return self.url("task-comment-detail", comment_id=comment.id, **kwargs)

    def comment_data(self, comment=None):
        response = self.client.get(self.comment_url(comment or self.comment))
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_submit_hint_and_mutation_agree_for_assigned_editor(self):
        self.assertIs(self.task_data()["can_submit"], True)
        response = self.submit()
        self.assertEqual(response.status_code, 201)
        self.assertIs(response.data["can_approve"], False)
        self.assertIs(response.data["can_request_changes"], False)
        self.assertIs(self.task_data()["can_submit"], False)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.REVIEW)
        self.assertEqual(self.submit().status_code, 409)

    def test_submit_hint_requires_working_state(self):
        for task_status in Task.Status.values:
            if task_status == Task.Status.WORKING:
                continue
            with self.subTest(status=task_status):
                Task.objects.filter(pk=self.task.pk).update(status=task_status)
                self.assertIs(self.task_data()["can_submit"], False)
                self.assertEqual(self.submit().status_code, 409)

    def test_other_editor_cannot_submit_despite_same_workspace_role(self):
        self.client.force_login(self.peer)
        self.assertIs(self.task_data()["can_submit"], False)
        self.assertEqual(self.submit().status_code, 403)

    def test_managers_viewers_and_staff_cannot_inherit_executor_power(self):
        for actor in (self.owner, self.admin, self.manager, self.viewer):
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                self.assertIs(self.task_data()["can_submit"], False)
                self.assertEqual(self.submit().status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_submit_membership_in_another_profile_does_not_change_current_role(self):
        ProfileMembership.objects.create(
            profile=self.foreign_profile, user=self.editor, role=ProfileMembership.Role.ADMIN,
        )
        self.assertIs(self.task_data()["can_submit"], True)
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(self.client.get(self.url(task=self.foreign_task)).status_code, 404)

    def test_pending_or_submitted_history_blocks_submit_even_with_working_task(self):
        deliverable = self.deliverable(status=Deliverable.Status.PENDING)
        for deliverable_status in (Deliverable.Status.PENDING, Deliverable.Status.SUBMITTED):
            with self.subTest(status=deliverable_status):
                Deliverable.objects.filter(pk=deliverable.pk).update(status=deliverable_status)
                self.assertIs(self.task_data()["can_submit"], False)
                self.assertEqual(self.submit().status_code, 409)

    def test_resolved_history_allows_new_revision(self):
        self.deliverable(status=Deliverable.Status.REJECTED)
        self.assertIs(self.task_data()["can_submit"], True)
        response = self.submit()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["revision"], 2)

    def test_subtask_uses_its_own_assignment_and_workflow(self):
        Task.objects.filter(pk=self.child.pk).update(status=Task.Status.WORKING)
        self.assertIs(self.task_data(self.child)["can_submit"], False)
        TaskAssignment.objects.create(task=self.child, user=self.editor)
        self.assertIs(self.task_data(self.child)["can_submit"], True)
        self.assertEqual(self.submit(self.child).status_code, 201)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.WORKING)

    def test_stale_submit_hint_does_not_survive_assignment_revocation(self):
        self.assertIs(self.task_data()["can_submit"], True)
        TaskAssignment.objects.filter(task=self.task).update(is_active=False)
        self.assertEqual(self.submit().status_code, 403)
        self.assertIs(self.task_data()["can_submit"], False)
        self.assertFalse(Deliverable.objects.filter(task=self.task).exists())

    def test_stale_submit_hint_does_not_survive_membership_role_change(self):
        self.assertIs(self.task_data()["can_submit"], True)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(role=WorkspaceMember.Role.VIEWER)
        self.assertIs(self.task_data()["can_submit"], False)
        self.assertEqual(self.submit().status_code, 403)

    def test_revoked_profile_or_workspace_membership_hides_task(self):
        self.editor_membership.is_active = False
        self.editor_membership.save(update_fields=("is_active",))
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(self.submit().status_code, 404)
        self.editor_membership.is_active = True
        self.editor_membership.save(update_fields=("is_active",))
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(is_active=False)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(self.submit().status_code, 404)

    def test_archived_scope_keeps_hints_false_and_mutations_denied(self):
        for model, instance in ((Workspace, self.workspace), (Profile, self.profile)):
            with self.subTest(model=model.__name__):
                model.objects.filter(pk=instance.pk).update(status=model.Status.ARCHIVED)
                self.assertIs(self.task_data()["can_submit"], False)
                self.assertEqual(self.submit().status_code, 403)
                comment = self.comment_data()
                self.assertIs(comment["can_edit"], False)
                self.assertIs(comment["can_delete"], False)
                model.objects.filter(pk=instance.pk).update(status=model.Status.ACTIVE)

    def test_submit_capability_is_read_only_and_does_not_bypass_csrf(self):
        self.assertEqual(self.submit(can_submit=True).status_code, 400)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.editor)
        self.assertIs(client.get(self.url()).data["can_submit"], True)
        response = client.post(self.url("task-deliverable-list"), {"file_url": "https://example.test"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Deliverable.objects.filter(task=self.task).exists())

    def test_reviewer_roles_have_capabilities_and_executor_viewer_do_not(self):
        deliverable = self.review_ready()
        for actor, expected in ((self.owner, True), (self.admin, True), (self.manager, True), (self.editor, False), (self.peer, False), (self.viewer, False)):
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                self.assert_review_hint(deliverable, expected)
                if not expected:
                    self.assertEqual(self.decide(deliverable).status_code, 403)

    def test_approve_response_clears_capabilities_after_existing_service_transition(self):
        deliverable = self.review_ready()
        self.client.force_login(self.owner)
        self.assert_review_hint(deliverable, True)
        response = self.decide(deliverable)
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.data["can_approve"], False)
        self.assertIs(response.data["can_request_changes"], False)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        self.assertEqual(self.decide(deliverable).status_code, 409)

    def test_request_changes_response_clears_capabilities_and_allows_resubmit(self):
        deliverable = self.review_ready()
        self.client.force_login(self.manager)
        self.assert_review_hint(deliverable, True)
        response = self.decide(deliverable, "request-changes")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.data["can_approve"], False)
        self.assertIs(response.data["can_request_changes"], False)
        self.client.force_login(self.editor)
        self.assertIs(self.task_data()["can_submit"], True)
        self.assertEqual(self.submit().status_code, 201)

    def test_self_review_is_false_even_for_eligible_manager(self):
        deliverable = self.review_ready(actor=self.manager)
        self.client.force_login(self.manager)
        self.assert_review_hint(deliverable, False)
        self.assertEqual(self.decide(deliverable).status_code, 403)
        self.assertEqual(self.decide(deliverable, "request-changes").status_code, 403)
        self.assertFalse(Review.objects.filter(deliverable=deliverable).exists())

    def test_latest_submission_uses_created_time_not_largest_revision_number(self):
        older = self.review_ready(revision=99)
        Deliverable.objects.filter(pk=older.pk).update(created_at=timezone.now() - timedelta(days=1))
        latest = self.deliverable(revision=1)
        self.client.force_login(self.owner)
        self.assert_review_hint(older, False)
        self.assert_review_hint(latest, True)
        self.assertEqual(self.decide(older).status_code, 409)
        self.assertEqual(self.decide(latest).status_code, 200)

    def test_latest_submission_breaks_equal_timestamp_ties_by_uuid(self):
        first = self.review_ready(revision=1)
        second = self.deliverable(revision=2)
        Deliverable.objects.filter(pk__in=(first.pk, second.pk)).update(created_at=timezone.now())
        latest, older = sorted((first, second), key=lambda item: item.id, reverse=True)
        self.client.force_login(self.owner)
        self.assert_review_hint(older, False)
        self.assert_review_hint(latest, True)
        self.assertEqual(self.decide(older).status_code, 409)
        self.assertEqual(self.decide(latest).status_code, 200)

    def test_wrong_task_state_or_deliverable_state_clears_review_capabilities(self):
        deliverable = self.review_ready()
        self.client.force_login(self.owner)
        for task_status in Task.Status.values:
            if task_status != Task.Status.REVIEW:
                with self.subTest(task_status=task_status):
                    Task.objects.filter(pk=self.task.pk).update(status=task_status)
                    self.assert_review_hint(deliverable, False)
                    self.assertEqual(self.decide(deliverable).status_code, 409)
        Task.objects.filter(pk=self.task.pk).update(status=Task.Status.REVIEW)
        for status in (Deliverable.Status.PENDING, Deliverable.Status.APPROVED, Deliverable.Status.REJECTED):
            with self.subTest(deliverable_status=status):
                Deliverable.objects.filter(pk=deliverable.pk).update(status=status)
                self.assert_review_hint(deliverable, False)
                self.assertEqual(self.decide(deliverable).status_code, 409)

    def test_any_existing_review_row_blocks_decision_not_only_approved(self):
        deliverable = self.review_ready()
        review = Review.objects.create(deliverable=deliverable, reviewer=self.owner, status=Review.Status.PENDING)
        self.client.force_login(self.manager)
        for review_status in Review.Status.values:
            with self.subTest(status=review_status):
                Review.objects.filter(pk=review.pk).update(status=review_status)
                self.assert_review_hint(deliverable, False)
                self.assertEqual(self.decide(deliverable).status_code, 409)

    def test_stale_review_hint_revalidates_latest_submission(self):
        deliverable = self.review_ready()
        self.client.force_login(self.owner)
        self.assert_review_hint(deliverable, True)
        self.deliverable(revision=2)
        self.assertEqual(self.decide(deliverable).status_code, 409)
        self.assertFalse(Review.objects.filter(deliverable=deliverable).exists())

    def test_stale_review_hint_revalidates_reviewer_membership(self):
        deliverable = self.review_ready()
        self.client.force_login(self.manager)
        self.assert_review_hint(deliverable, True)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.manager).update(role=WorkspaceMember.Role.VIEWER)
        self.assert_review_hint(deliverable, False)
        self.assertEqual(self.decide(deliverable).status_code, 403)

    def test_review_of_archived_scope_is_not_actionable(self):
        deliverable = self.review_ready()
        self.client.force_login(self.owner)
        for model, instance in ((Workspace, self.workspace), (Profile, self.profile)):
            with self.subTest(model=model.__name__):
                model.objects.filter(pk=instance.pk).update(status=model.Status.ARCHIVED)
                self.assert_review_hint(deliverable, False)
                self.assertEqual(self.decide(deliverable).status_code, 403)
                model.objects.filter(pk=instance.pk).update(status=model.Status.ACTIVE)

    def test_wrong_parent_and_cross_tenant_ids_do_not_expose_review_or_comment(self):
        self.client.force_login(self.owner)
        foreign = self.deliverable(task=self.foreign_task)
        sibling = self.deliverable(task=self.sibling_task)
        for deliverable in (foreign, sibling):
            with self.subTest(deliverable=deliverable.id):
                self.assertEqual(self.decide(deliverable).status_code, 404)
        for comment in (self.foreign_comment, self.sibling_comment):
            with self.subTest(comment=comment.id):
                self.assertEqual(self.client.get(self.comment_url(comment)).status_code, 404)
                self.assertEqual(self.client.patch(self.comment_url(comment), {"content": "Denied"}, format="json").status_code, 404)

    def test_old_author_comment_capabilities_survive_reload_and_pagination(self):
        for number in range(4):
            TaskComment.objects.create(task=self.task, user=self.editor, content=f"Existing feedback {number}")
        self.client = APIClient()
        self.client.force_login(self.editor)
        response = self.client.get(self.comment_url(), {"page_size": 2, "page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["results"])
        self.assertTrue(all(row["can_edit"] and row["can_delete"] for row in response.data["results"]))
        data = self.comment_data()
        self.assertIs(data["can_edit"], True)
        self.assertIs(data["can_delete"], True)
        response = self.client.patch(self.comment_url(self.comment), {"content": "After reload"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.data["can_edit"], True)

    def test_manager_moderates_but_cannot_edit_another_author(self):
        self.client.force_login(self.manager)
        data = self.comment_data()
        self.assertIs(data["can_edit"], False)
        self.assertIs(data["can_delete"], True)
        self.assertEqual(self.client.patch(self.comment_url(self.comment), {"content": "No rewrite"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.comment_url(self.comment)).status_code, 204)
        data = self.comment_data()
        self.assertIs(data["can_edit"], False)
        self.assertIs(data["can_delete"], False)
        self.assertIsNone(data["content"])

    def test_peer_and_historical_viewer_author_have_no_comment_mutation_capabilities(self):
        own_viewer = TaskComment.objects.create(task=self.task, user=self.viewer, content="Legacy viewer feedback")
        for actor, comment in ((self.peer, self.comment), (self.viewer, own_viewer)):
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                data = self.comment_data(comment)
                self.assertIs(data["can_edit"], False)
                self.assertIs(data["can_delete"], False)
                self.assertEqual(self.client.patch(self.comment_url(comment), {"content": "No change"}, format="json").status_code, 403)
                self.assertEqual(self.client.delete(self.comment_url(comment)).status_code, 403)

    def test_stale_comment_author_hint_does_not_survive_role_downgrade(self):
        self.assertIs(self.comment_data()["can_edit"], True)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(role=WorkspaceMember.Role.VIEWER)
        data = self.comment_data()
        self.assertIs(data["can_edit"], False)
        self.assertIs(data["can_delete"], False)
        self.assertEqual(self.client.patch(self.comment_url(self.comment), {"content": "Denied"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.comment_url(self.comment)).status_code, 403)

    def test_revoked_author_cannot_read_or_edit_existing_comment(self):
        self.assertIs(self.comment_data()["can_edit"], True)
        ProfileMembership.objects.filter(pk=self.editor_membership.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.comment_url(self.comment)).status_code, 404)
        self.assertEqual(self.client.patch(self.comment_url(self.comment), {"content": "Denied"}, format="json").status_code, 404)

    def test_author_delete_tombstone_redacts_body_and_clears_both_capabilities(self):
        self.assertEqual(self.client.delete(self.comment_url(self.comment)).status_code, 204)
        data = self.comment_data()
        self.assertIs(data["can_edit"], False)
        self.assertIs(data["can_delete"], False)
        self.assertIsNone(data["content"])
        self.assertEqual(self.client.patch(self.comment_url(self.comment), {"content": "Restore"}, format="json").status_code, 409)
        listing = self.client.get(self.comment_url())
        self.assertNotIn("Original feedback", listing.content.decode())

    def test_capability_payloads_are_identity_minimal_and_strict_inputs_cannot_forge_them(self):
        comment = self.comment_data()
        for forbidden in ("user_id", "author_id", "email", "username"):
            self.assertNotIn(forbidden, comment)
        for value in (self.editor.username, self.editor.email, str(self.editor.id)):
            self.assertNotIn(value, str(comment))
        response = self.client.patch(self.comment_url(self.comment), {"content": "Denied", "can_edit": True, "can_delete": True}, format="json")
        self.assertEqual(response.status_code, 400)
        deliverable = self.review_ready()
        self.client.force_login(self.owner)
        response = self.client.post(self.url("task-deliverable-approve", deliverable_id=deliverable.id), {"can_approve": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Review.objects.filter(deliverable=deliverable).exists())

    def test_missing_or_mismatched_request_context_fails_closed_for_every_capability(self):
        context = resolve_workspace_access_context(resolve_profile_access_context(self.editor, self.profile.id), self.workspace.id)
        request = APIRequestFactory().get("/")
        request.user = self.peer
        Task.objects.filter(pk=self.child.pk).update(status=Task.Status.REVIEW)
        self.child.refresh_from_db()
        deliverable = self.deliverable(task=self.child)
        for serializer_context in ({}, {"workspace_access_context": context}, {"request": request}, {"request": request, "workspace_access_context": context}):
            with self.subTest(context=tuple(serializer_context)):
                self.assertIs(TaskReadSerializer(self.task, context=serializer_context).data["can_submit"], False)
                data = CommentReadSerializer(self.comment, context=serializer_context).data
                self.assertIs(data["can_edit"], False)
                self.assertIs(data["can_delete"], False)
        owner_context = resolve_workspace_access_context(resolve_profile_access_context(self.owner, self.profile.id), self.workspace.id)
        for serializer_context in ({}, {"workspace_access_context": owner_context}, {"request": request}, {"request": request, "workspace_access_context": owner_context}):
            with self.subTest(review_context=tuple(serializer_context)):
                data = DeliverableReadSerializer(deliverable, context=serializer_context).data
                self.assertIs(data["can_approve"], False)
                self.assertIs(data["can_request_changes"], False)
        request.user = self.editor
        valid_context = {"request": request, "workspace_access_context": context}
        self.assertIs(TaskReadSerializer(self.task, context=valid_context).data["can_submit"], True)
        self.assertIs(CommentReadSerializer(self.comment, context=valid_context).data["can_edit"], True)
        request.user = self.owner
        valid_context = {"request": request, "workspace_access_context": owner_context}
        self.assertIs(DeliverableReadSerializer(deliverable, context=valid_context).data["can_approve"], True)

    def test_serializer_context_cannot_authorize_another_workspace_object(self):
        context = resolve_workspace_access_context(resolve_profile_access_context(self.owner, self.profile.id), self.workspace.id)
        request = APIRequestFactory().get("/")
        request.user = self.owner
        serializer_context = {"request": request, "workspace_access_context": context}
        Task.objects.filter(pk=self.sibling_task.pk).update(status=Task.Status.REVIEW)
        self.sibling_task.refresh_from_db()
        deliverable = self.deliverable(task=self.sibling_task)
        data = DeliverableReadSerializer(deliverable, context=serializer_context).data
        self.assertIs(data["can_approve"], False)
        self.assertIs(data["can_request_changes"], False)
        data = CommentReadSerializer(self.sibling_comment, context=serializer_context).data
        self.assertIs(data["can_edit"], False)
        self.assertIs(data["can_delete"], False)

    def test_task_submit_capability_query_growth_is_bounded(self):
        url = reverse("tasks:task-list", kwargs={"profile_id": self.profile.id, "workspace_id": self.workspace.id})
        with CaptureQueriesContext(connection) as small:
            response = self.client.get(url, {"page_size": 50})
        self.assertEqual(response.status_code, 200)
        for number in range(12):
            task = Task.objects.create(workspace=self.workspace, created_by=self.owner, title=f"Additional task {number}", status=Task.Status.WORKING)
            TaskAssignment.objects.create(task=task, user=self.editor)
        with CaptureQueriesContext(connection) as large:
            response = self.client.get(url, {"page_size": 50})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 12)
        self.assertLessEqual(len(large), len(small) + 1)
        self.assertTrue(any(row["can_submit"] for row in response.data["results"]))

    def test_review_capability_query_growth_is_bounded(self):
        initial = self.review_ready()
        self.client.force_login(self.owner)
        url = self.url("task-deliverable-list")
        with CaptureQueriesContext(connection) as small:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sum(row["can_approve"] for row in response.data["results"]), 1)
        # Compare the same eligible-review path on both pages. An entirely
        # resolved history skips the fixed role checks and is not an N+1 baseline.
        Deliverable.objects.filter(pk=initial.pk).update(status=Deliverable.Status.REJECTED)
        for revision in range(2, 14):
            self.deliverable(revision=revision, status=Deliverable.Status.REJECTED)
        self.deliverable(revision=14)
        with CaptureQueriesContext(connection) as large:
            response = self.client.get(url, {"page_size": 50})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(large), len(small) + 1)
        self.assertEqual(sum(row["can_approve"] for row in response.data["results"]), 1)

    def test_comment_capability_query_growth_is_bounded(self):
        with CaptureQueriesContext(connection) as small:
            self.assertEqual(self.client.get(self.comment_url()).status_code, 200)
        for number in range(12):
            TaskComment.objects.create(task=self.task, user=self.editor, content=f"More feedback {number}")
        with CaptureQueriesContext(connection) as large:
            response = self.client.get(self.comment_url(), {"page_size": 50})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(large), len(small) + 1)
        self.assertTrue(all(row["can_edit"] and row["can_delete"] for row in response.data["results"]))
