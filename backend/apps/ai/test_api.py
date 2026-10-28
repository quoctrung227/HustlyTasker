"""HTTP/security contracts on the shared isolated PostgreSQL test database."""

import json
from copy import deepcopy
from datetime import date, timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.tasks.models import Task, TaskAssignment
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .api import FixtureGenerationDayThrottle, FixtureGenerationMinuteThrottle
from .test_contracts import node


User = get_user_model()


@override_settings(AI_FIXTURE_ENABLED=True)
class DurableProposalApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = cls.user("owner")
        cls.profile_admin = cls.user("profile-admin")
        cls.manager = cls.user("workspace-admin")
        cls.editor = cls.user("editor")
        cls.viewer = cls.user("viewer")
        cls.staff = cls.user("staff", is_staff=True)
        cls.outsider = cls.user("outsider")
        cls.other_owner = cls.user("other-owner")
        cls.profile = create_profile_with_owner(name="Synthetic AI API Profile", owner=cls.owner)
        ProfileMembership.objects.create(profile=cls.profile, user=cls.profile_admin,
                                         role=ProfileMembership.Role.ADMIN)
        for actor in (cls.manager, cls.editor, cls.viewer, cls.staff):
            ProfileMembership.objects.create(profile=cls.profile, user=actor, role=ProfileMembership.Role.MEMBER)
        cls.workspace = Workspace.objects.create(profile=cls.profile, owner=cls.owner,
                                                name="Synthetic AI API Workspace", period=date(2026, 10, 1))
        cls.sibling = Workspace.objects.create(profile=cls.profile, owner=cls.owner,
                                              name="Synthetic Sibling Workspace", period=date(2026, 11, 1))
        for actor, role in ((cls.manager, WorkspaceMember.Role.ADMIN),
                            (cls.editor, WorkspaceMember.Role.MEMBER),
                            (cls.viewer, WorkspaceMember.Role.VIEWER)):
            WorkspaceMember.objects.create(workspace=cls.workspace, user=actor, role=role)
        cls.other_profile = create_profile_with_owner(name="Other Synthetic Profile", owner=cls.other_owner)
        cls.other_workspace = Workspace.objects.create(profile=cls.other_profile, owner=cls.other_owner,
                                                      name="Other Synthetic Workspace", period=date(2026, 10, 1))

    @classmethod
    def user(cls, suffix, **kwargs):
        return User.objects.create_user(username=f"ai-api-{suffix}", email=f"ai-api-{suffix}@example.test",
                                        password=None, **kwargs)

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def tearDown(self):
        cache.clear()

    def url(self, name="proposal-generate", *, proposal_id=None, profile=None, workspace=None):
        kwargs = {"profile_id": str(profile or self.profile.pk),
                  "workspace_id": str(workspace or self.workspace.pk)}
        if proposal_id is not None:
            kwargs["proposal_id"] = str(proposal_id)
        return reverse(f"ai:{name}", kwargs=kwargs)

    def generate(self, *, scenario_id="subtitle-check-v1", key=None, **kwargs):
        return self.client.post(self.url(**kwargs), {"scenario_id": scenario_id}, format="json",
                                HTTP_IDEMPOTENCY_KEY=str(key or uuid4()))

    def confirm(self, proposal, *, payload=None, key=None, **kwargs):
        body = {"proposal_revision": proposal["revision"], "confirmed": True,
                "payload": deepcopy(proposal["payload"]) if payload is None else payload}
        return self.client.post(self.url("proposal-confirm", proposal_id=proposal["proposal_id"], **kwargs),
                                body, format="json", HTTP_IDEMPOTENCY_KEY=str(key or uuid4()))

    def test_generate_has_fixture_provenance_and_creates_no_task(self):
        result = self.generate()
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data["mode"], "fixture_demo")
        self.assertFalse(result.data["generated_by_ai"])
        self.assertTrue(result.data["persisted"])
        self.assertEqual(result.data["revision"], 1)
        self.assertEqual(result.data["payload"]["contract_version"], "ai.task-plan.v1")
        self.assertEqual(result.data["usage"]["cost_usd"], "0.000000")
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(TaskAssignment.objects.count(), 0)
        self.assertIn("no-store", result.headers["Cache-Control"])

    def test_both_server_scenarios_produce_valid_proposals(self):
        for scenario in ("subtitle-check-v1", "task-tree-v1"):
            with self.subTest(scenario=scenario):
                result = self.generate(scenario_id=scenario)
                self.assertEqual(result.status_code, 201)
                self.assertEqual(result.data["scenario_id"], scenario)
        self.assertEqual(Task.objects.count(), 0)

    def test_retrieve_own_proposal_exposes_no_global_actor_identity(self):
        proposal = self.generate().data
        result = self.client.get(self.url("proposal-detail", proposal_id=proposal["proposal_id"]))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["payload"], proposal["payload"])
        self.assertFalse({"actor_id", "user_id", "email", "body_digest", "key_digest"} & set(result.data))
        self.assertNotIn(str(self.owner.pk), str(result.data))
        self.assertIn("no-store", result.headers["Cache-Control"])

    def test_owner_profile_admin_and_workspace_admin_can_generate(self):
        for actor in (self.owner, self.profile_admin, self.manager):
            with self.subTest(actor=actor.username):
                self.client.force_authenticate(actor)
                result = self.generate()
                self.assertEqual(result.status_code, 201)

    def test_editor_viewer_and_staff_cannot_generate(self):
        for actor in (self.editor, self.viewer, self.staff):
            with self.subTest(actor=actor.username):
                self.client.force_authenticate(actor)
                self.assertIn(self.generate().status_code, (403, 404))
        self.assertEqual(Task.objects.count(), 0)

    def test_global_superuser_flag_without_membership_is_not_tenant_authority(self):
        self.outsider.is_staff = True
        self.outsider.is_superuser = True
        self.outsider.save(update_fields=("is_staff", "is_superuser"))
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.generate().status_code, 404)

    def test_inactive_user_cannot_use_active_membership(self):
        self.owner.is_active = False
        self.owner.save(update_fields=("is_active",))
        self.assertEqual(self.generate().status_code, 403)

    def test_another_manager_cannot_read_or_confirm_actors_proposal(self):
        proposal = self.generate().data
        self.client.force_authenticate(self.profile_admin)
        result = self.client.get(self.url("proposal-detail", proposal_id=proposal["proposal_id"]))
        self.assertEqual(result.status_code, 404)
        self.assertEqual(self.confirm(proposal).status_code, 404)
        self.assertEqual(Task.objects.count(), 0)

    def test_unauthenticated_requests_are_denied(self):
        proposal = self.generate().data
        self.client.force_authenticate(user=None)
        self.assertEqual(self.generate().status_code, 403)
        self.assertEqual(self.client.get(self.url("proposal-detail", proposal_id=proposal["proposal_id"])).status_code, 403)
        self.assertEqual(self.confirm(proposal).status_code, 403)

    def test_unknown_or_malformed_proposal_has_same_generic_404(self):
        for proposal_id in (uuid4(), "malformed-proposal"):
            with self.subTest(proposal_id=proposal_id):
                result = self.client.get(self.url("proposal-detail", proposal_id=proposal_id))
                self.assertEqual(result.status_code, 404)
                self.assertNotIn(str(proposal_id), str(result.data))

    def test_cross_profile_and_cross_workspace_paths_deny_proposal_access(self):
        proposal = self.generate().data
        paths = (
            {"workspace": self.sibling.pk},
            {"profile": self.other_profile.pk, "workspace": self.other_workspace.pk},
            {"profile": self.profile.pk, "workspace": self.other_workspace.pk},
        )
        for scope in paths:
            with self.subTest(scope=scope):
                result = self.client.get(self.url("proposal-detail", proposal_id=proposal["proposal_id"], **scope))
                self.assertEqual(result.status_code, 404)
                self.assertEqual(self.confirm(proposal, **scope).status_code, 404)
        self.assertEqual(Task.objects.count(), 0)

    def test_multiple_profile_memberships_do_not_move_proposal_scope(self):
        proposal = self.generate().data
        ProfileMembership.objects.create(profile=self.other_profile, user=self.owner, role=ProfileMembership.Role.ADMIN)
        result = self.client.get(self.url("proposal-detail", proposal_id=proposal["proposal_id"],
                                         profile=self.other_profile.pk, workspace=self.other_workspace.pk))
        self.assertEqual(result.status_code, 404)
        self.assertEqual(self.generate(profile=self.other_profile.pk, workspace=self.other_workspace.pk).status_code, 201)

    def test_revoked_workspace_membership_prevents_read_confirm_and_replay(self):
        self.client.force_authenticate(self.manager)
        key = uuid4()
        proposal = self.generate().data
        self.assertEqual(self.confirm(proposal, key=key).status_code, 201)
        WorkspaceMember.objects.filter(user=self.manager, workspace=self.workspace).update(is_active=False)
        result = self.client.get(self.url("proposal-detail", proposal_id=proposal["proposal_id"]))
        self.assertIn(result.status_code, (403, 404))
        self.assertIn(self.confirm(proposal, key=key).status_code, (403, 404))
        self.assertNotIn("created_tasks", result.data)

    def test_inactive_profile_membership_denies_existing_proposal(self):
        proposal = self.generate().data
        ProfileMembership.objects.filter(user=self.owner, profile=self.profile).update(is_active=False)
        self.assertIn(self.client.get(self.url("proposal-detail", proposal_id=proposal["proposal_id"])).status_code, (403, 404))
        self.assertIn(self.confirm(proposal).status_code, (403, 404))
        self.assertEqual(Task.objects.count(), 0)

    def test_archived_workspace_denies_generation_read_and_confirmation(self):
        proposal = self.generate().data
        Workspace.objects.filter(pk=self.workspace.pk).update(status=Workspace.Status.ARCHIVED)
        self.assertEqual(self.generate().status_code, 403)
        self.assertEqual(self.client.get(self.url("proposal-detail", proposal_id=proposal["proposal_id"])).status_code, 403)
        self.assertEqual(self.confirm(proposal).status_code, 403)
        self.assertEqual(Task.objects.count(), 0)

    def test_archived_profile_denies_ai_actions(self):
        proposal = self.generate().data
        Profile.objects.filter(pk=self.profile.pk).update(status=Profile.Status.ARCHIVED)
        self.assertEqual(self.generate().status_code, 403)
        self.assertEqual(self.confirm(proposal).status_code, 403)

    def test_disabled_feature_denies_without_creating_task(self):
        with override_settings(AI_FIXTURE_ENABLED=False):
            self.assertEqual(self.generate().status_code, 503)
        self.assertEqual(Task.objects.count(), 0)

    def test_production_cannot_enable_fixture_with_setting_or_request(self):
        with override_settings(AI_FIXTURE_ENABLED=True, ENVIRONMENT="production", IS_PRODUCTION=True):
            self.assertEqual(self.generate().status_code, 503)
        self.assertEqual(Task.objects.count(), 0)

    def test_provider_mode_brief_or_unknown_fields_are_rejected_without_echo(self):
        for field in ("brief", "provider", "model", "fixture_mode", "workspace_id", "SYNTHETIC_PRIVATE_FIELD"):
            cache.clear()
            with self.subTest(field=field):
                response = self.client.post(self.url(), {"scenario_id": "subtitle-check-v1", field: "synthetic-private-value"},
                                            format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("synthetic-private-value", str(response.data))
                self.assertNotIn("SYNTHETIC_PRIVATE_FIELD", str(response.data))

    def test_unknown_or_nonstring_scenario_is_rejected(self):
        for value in ("unknown-synthetic-scenario", "", 1, True, None):
            cache.clear()
            with self.subTest(value=value):
                self.assertEqual(self.generate(scenario_id=value).status_code, 400)
        self.assertEqual(Task.objects.count(), 0)

    def test_missing_invalid_idempotency_header_is_rejected(self):
        for headers in ({}, {"HTTP_IDEMPOTENCY_KEY": "not-a-valid-key"}):
            with self.subTest(headers=headers):
                response = self.client.post(self.url(), {"scenario_id": "subtitle-check-v1"}, format="json", **headers)
                self.assertEqual(response.status_code, 400)

    def test_generate_idempotency_replays_existing_proposal(self):
        key = uuid4()
        first = self.generate(key=key)
        second = self.generate(key=key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["proposal_id"], second.data["proposal_id"])
        self.assertEqual(Task.objects.count(), 0)

    def test_generate_same_key_with_different_scenario_conflicts(self):
        key = uuid4()
        self.assertEqual(self.generate(key=key).status_code, 201)
        second = self.generate(key=key, scenario_id="task-tree-v1")
        self.assertEqual(second.status_code, 409)

    def test_confirm_creates_root_and_subtask_with_server_owned_status(self):
        proposal = self.generate().data
        payload = deepcopy(proposal["payload"])
        payload["tasks"].append(node("item_2", "item_1"))
        result = self.confirm(proposal, payload=payload)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(Task.objects.count(), 2)
        roots = Task.objects.filter(parent_id=None)
        self.assertEqual(roots.count(), 1)
        self.assertEqual(Task.objects.exclude(parent_id=None).get().parent_id, roots.get().pk)
        self.assertEqual(set(Task.objects.values_list("status", flat=True)), {Task.Status.PENDING})
        self.assertEqual(set(Task.objects.values_list("created_by_id", flat=True)), {self.owner.pk})
        self.assertEqual(TaskAssignment.objects.count(), 0)
        self.assertEqual(set(result.data["created_tasks"]), {"item_1", "item_2"})
        self.assertIsNone(result.data["payload"])

    def test_confirm_same_key_replays_and_different_key_cannot_create_second_batch(self):
        proposal = self.generate().data
        key = uuid4()
        first = self.confirm(proposal, key=key)
        second = self.confirm(proposal, key=key)
        third = self.confirm(proposal)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["created_tasks"], first.data["created_tasks"])
        self.assertEqual(third.status_code, 409)
        self.assertEqual(Task.objects.count(), len(proposal["payload"]["tasks"]))

    def test_confirm_same_key_changed_body_conflicts(self):
        proposal = self.generate().data
        key = uuid4()
        self.assertEqual(self.confirm(proposal, key=key).status_code, 201)
        changed = deepcopy(proposal["payload"])
        changed["tasks"][0]["title"] = "A changed synthetic title"
        self.assertEqual(self.confirm(proposal, key=key, payload=changed).status_code, 409)
        self.assertEqual(Task.objects.count(), 1)

    def test_confirmation_is_explicit_and_serializer_does_not_coerce_scalars(self):
        proposal = self.generate().data
        base = {"proposal_revision": 1, "confirmed": True, "payload": proposal["payload"]}
        for updates in ({"confirmed": False}, {"confirmed": "true"}, {"confirmed": 1},
                        {"proposal_revision": True}, {"proposal_revision": "1"}, {"payload": []}):
            with self.subTest(updates=updates):
                result = self.client.post(self.url("proposal-confirm", proposal_id=proposal["proposal_id"]),
                                          {**base, **updates}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
                self.assertEqual(result.status_code, 400)
        self.assertEqual(Task.objects.count(), 0)

    def test_invalid_edited_plan_priority_cycle_depth_count_or_injection_is_denied(self):
        proposal = self.generate().data
        invalid = []
        priority = deepcopy(proposal["payload"])
        priority["tasks"][0]["priority"] = "CRITICAL"
        invalid.append(priority)
        cycle = deepcopy(proposal["payload"])
        cycle["tasks"][0]["parent_ref"] = cycle["tasks"][0]["local_ref"]
        invalid.append(cycle)
        depth = deepcopy(proposal["payload"])
        depth["tasks"] = [node(f"item_{i}", f"item_{i-1}" if i > 1 else None) for i in range(1, 6)]
        invalid.append(depth)
        count = deepcopy(proposal["payload"])
        count["tasks"] = [node(f"item_{i}") for i in range(1, 22)]
        invalid.append(count)
        injected = deepcopy(proposal["payload"])
        injected["tasks"][0]["assignee_id"] = str(self.editor.pk)
        invalid.append(injected)
        for payload in invalid:
            with self.subTest(case=invalid.index(payload)):
                self.assertEqual(self.confirm(proposal, payload=payload).status_code, 400)
        self.assertEqual(Task.objects.count(), 0)

    def test_deadline_normalization_is_preserved_in_created_task(self):
        proposal = self.generate().data
        payload = deepcopy(proposal["payload"])
        payload["tasks"][0]["proposed_deadline"] = "2026-10-30T18:00:00+07:00"
        self.assertEqual(self.confirm(proposal, payload=payload).status_code, 201)
        self.assertEqual(Task.objects.get().deadline.isoformat(), "2026-10-30T11:00:00+00:00")

    def test_invalid_unicode_and_empty_title_are_rejected(self):
        proposal = self.generate().data
        for title in ("", "bad\x00title", "bad\ud800title", "x" * 256):
            with self.subTest(title_length=len(title)):
                payload = deepcopy(proposal["payload"])
                payload["tasks"][0]["title"] = title
                body = json.dumps({"proposal_revision": 1, "confirmed": True, "payload": payload},
                                  ensure_ascii=True)
                result = self.client.post(self.url("proposal-confirm", proposal_id=proposal["proposal_id"]),
                                          body, content_type="application/json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
                self.assertEqual(result.status_code, 400)
        self.assertEqual(Task.objects.count(), 0)

    def test_oversized_duplicate_nonfinite_and_malformed_json_are_static_400(self):
        bodies = (
            '{"scenario_id":"subtitle-check-v1","padding":"' + "x" * (32 * 1024) + '"}',
            '{"scenario_id":"subtitle-check-v1","scenario_id":"task-tree-v1"}',
            '{"scenario_id":NaN}', '{"scenario_id":',
        )
        for body in bodies:
            cache.clear()
            with self.subTest(length=len(body)):
                result = self.client.post(self.url(), body, content_type="application/json",
                                          HTTP_IDEMPOTENCY_KEY=str(uuid4()))
                self.assertEqual(result.status_code, 400)
                self.assertNotIn("padding", str(result.data))
        self.assertEqual(Task.objects.count(), 0)

    def test_method_restrictions_and_non_json_input(self):
        proposal = self.generate().data
        self.assertEqual(self.client.get(self.url()).status_code, 405)
        detail = self.url("proposal-detail", proposal_id=proposal["proposal_id"])
        self.assertEqual(self.client.delete(detail).status_code, 405)
        self.assertEqual(self.client.patch(detail, {}, format="json").status_code, 405)
        self.assertEqual(self.client.post(self.url(), "scenario_id=x", content_type="text/plain").status_code, 415)

    def test_generation_minute_limit_is_process_cache_throttle(self):
        self.assertEqual(FixtureGenerationMinuteThrottle.rate, "3/minute")
        self.assertEqual(FixtureGenerationDayThrottle.rate, "20/day")
        responses = [self.generate() for _ in range(4)]
        self.assertEqual([response.status_code for response in responses], [201, 201, 201, 429])
        self.assertEqual(Task.objects.count(), 0)

    def test_authenticated_session_requires_csrf_for_both_mutations(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        proposal = self.generate().data
        result = client.post(self.url(), {"scenario_id": "subtitle-check-v1"}, format="json",
                             HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(result.status_code, 403)
        result = client.post(self.url("proposal-confirm", proposal_id=proposal["proposal_id"]),
                             {"proposal_revision": 1, "confirmed": True, "payload": proposal["payload"]},
                             format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(result.status_code, 403)
        self.assertEqual(Task.objects.count(), 0)

    def test_valid_session_csrf_allows_generate_and_confirm(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        csrf = client.get(reverse("accounts:csrf"))
        headers = {"HTTP_X_CSRFTOKEN": csrf.data["csrf_token"]}
        first = client.post(self.url(), {"scenario_id": "subtitle-check-v1"}, format="json",
                            HTTP_IDEMPOTENCY_KEY=str(uuid4()), **headers)
        self.assertEqual(first.status_code, 201)
        result = client.post(self.url("proposal-confirm", proposal_id=first.data["proposal_id"]),
                             {"proposal_revision": 1, "confirmed": True, "payload": first.data["payload"]},
                             format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()), **headers)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(Task.objects.count(), 1)

    def test_expired_session_cannot_read_generate_or_confirm_with_old_csrf(self):
        proposal = self.generate().data
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        csrf = client.get(reverse("accounts:csrf"))
        headers = {"HTTP_X_CSRFTOKEN": csrf.data["csrf_token"]}
        Session.objects.filter(session_key=client.session.session_key).update(
            expire_date=timezone.now() - timedelta(seconds=1),
        )
        detail = self.url("proposal-detail", proposal_id=proposal["proposal_id"])
        self.assertEqual(client.get(detail).status_code, 403)
        self.assertEqual(client.post(
            self.url(), {"scenario_id": "subtitle-check-v1"}, format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid4()), **headers,
        ).status_code, 403)
        self.assertEqual(client.post(
            self.url("proposal-confirm", proposal_id=proposal["proposal_id"]),
            {"proposal_revision": 1, "confirmed": True, "payload": proposal["payload"]},
            format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()), **headers,
        ).status_code, 403)
        self.assertEqual(Task.objects.count(), 0)
