"""Synthetic-brief and read-only discovery contracts on isolated PostgreSQL."""

from datetime import date
import json
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils.crypto import salted_hmac
from rest_framework.test import APITestCase

from apps.audit.models import AuditLog
from apps.tasks.models import Task
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from . import durable_services
from .errors import AIError
from .models import AiOperation, AiProposal
from .providers import FixtureAdapter


User = get_user_model()


@override_settings(AI_FIXTURE_ENABLED=True, ENVIRONMENT="development", IS_PRODUCTION=False)
class FixtureFrontendContractTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        def user(label, **kwargs):
            return User.objects.create_user(
                username=f"ai-ui-{label}", email=f"ai-ui-{label}@example.test",
                password=None, **kwargs,
            )

        cls.owner = user("owner")
        cls.admin = user("admin")
        cls.manager = user("manager")
        cls.viewer = user("viewer")
        cls.staff = user("staff", is_staff=True, is_superuser=True)
        cls.outsider = user("outsider")
        cls.profile = create_profile_with_owner(name="Synthetic AI UI scope", owner=cls.owner)
        cls.workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="Synthetic AI UI month",
            period=date(2026, 11, 1),
        )
        ProfileMembership.objects.create(profile=cls.profile, user=cls.admin, role="ADMIN")
        for actor, role in ((cls.manager, "ADMIN"), (cls.viewer, "VIEWER")):
            ProfileMembership.objects.create(profile=cls.profile, user=actor, role="MEMBER")
            WorkspaceMember.objects.create(workspace=cls.workspace, user=actor, role=role)
        cls.foreign_profile = create_profile_with_owner(name="Foreign synthetic scope", owner=cls.outsider)
        cls.foreign_workspace = Workspace.objects.create(
            profile=cls.foreign_profile, owner=cls.outsider, name="Foreign synthetic month",
            period=date(2026, 11, 1),
        )

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(self.owner)

    def tearDown(self):
        cache.clear()

    def url(self, *, profile=None, workspace=None):
        return reverse("ai:proposal-generate", kwargs={
            "profile_id": str(profile or self.profile.pk),
            "workspace_id": str(workspace or self.workspace.pk),
        })

    def generate(self, body=None, *, key=None):
        return self.client.post(
            self.url(), body if body is not None else {"scenario_id": "subtitle-check-v1"},
            format="json", HTTP_IDEMPOTENCY_KEY=str(key or uuid4()),
        )

    def assert_no_generation_rows(self):
        self.assertEqual(AiProposal.objects.count(), 0)
        self.assertEqual(AiOperation.objects.count(), 0)
        self.assertEqual(Task.objects.count(), 0)

    def test_optional_synthetic_brief_reaches_only_fixed_adapter_without_raw_storage_or_echo(self):
        brief = "Synthetic integration brief 02C: check captions and contrast."
        audits = AuditLog.objects.count()
        original = FixtureAdapter.generate
        with patch.object(FixtureAdapter, "generate", autospec=True, side_effect=original) as adapter, \
                patch("urllib.request.urlopen", side_effect=AssertionError("No provider network")), \
                patch("http.client.HTTPSConnection.connect", side_effect=AssertionError("No provider HTTPS")):
            response = self.generate({"scenario_id": "task-tree-v1", "brief": brief})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(adapter.call_count, 1)
        self.assertEqual(adapter.call_args.args[1].validated_input.brief, brief)
        self.assertEqual(response.data["mode"], "fixture_demo")
        self.assertFalse(response.data["generated_by_ai"])
        self.assertEqual(len(response.data["payload"]["tasks"]), 2)
        self.assertIn("không có model AI xử lý brief", response.data["payload"]["warnings"][0])
        for value in (response.data, list(AiProposal.objects.values()),
                      list(AiOperation.objects.values()), list(AuditLog.objects.values())):
            self.assertNotIn(brief, json.dumps(value, default=str, ensure_ascii=False))
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), audits)
        self.assertEqual(len(AiOperation.objects.get().body_digest), 64)

    def test_different_briefs_do_not_change_fixed_fixture_content(self):
        first = self.generate({"scenario_id": "subtitle-check-v1", "brief": "Synthetic first brief."})
        second = self.generate({"scenario_id": "subtitle-check-v1", "brief": "Synthetic different brief."})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data["payload"], second.data["payload"])
        self.assertEqual(Task.objects.count(), 0)

    def test_maximum_length_synthetic_brief_is_accepted(self):
        response = self.generate({"scenario_id": "subtitle-check-v1", "brief": "界" * 6000})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Task.objects.count(), 0)

    def test_optional_brief_rejects_invalid_types_blank_nul_unicode_and_length(self):
        for brief in ("", " \t\n ", "x" * 6001, None, 5, True, [], {}, "bad\x00text", "bad\ud800text"):
            cache.clear()
            with self.subTest(brief_type=type(brief).__name__):
                response = self.client.generic(
                    "POST", self.url(),
                    data=json.dumps({"scenario_id": "subtitle-check-v1", "brief": brief}, ensure_ascii=True),
                    content_type="application/json", HTTP_IDEMPOTENCY_KEY=str(uuid4()),
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("brief", response.data.get("fields", response.data))
                self.assert_no_generation_rows()

    def test_optional_brief_does_not_allow_protected_or_unknown_fields(self):
        for field in ("provider", "model", "actor_id", "profile_id", "workspace_id", "status", "role"):
            cache.clear()
            with self.subTest(field=field):
                response = self.generate({"scenario_id": "task-tree-v1", "brief": "Synthetic brief.",
                                          field: "private-marker-not-returned"})
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("private-marker-not-returned", str(response.data))
                self.assert_no_generation_rows()

    def test_brief_is_bound_to_same_key_replay_and_changed_brief_conflicts(self):
        key = uuid4()
        body = {"scenario_id": "subtitle-check-v1", "brief": "Synthetic stable body."}
        first = self.generate(body, key=key)
        with patch.object(FixtureAdapter, "generate", side_effect=AssertionError("No replay dispatch")):
            replay = self.generate(body, key=key)
            changed = self.generate({**body, "brief": "Synthetic changed body."}, key=key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(first.data["proposal_id"], replay.data["proposal_id"])
        self.assertEqual(changed.status_code, 409)
        self.assertEqual(changed.data["code"], "IDEMPOTENCY_CONFLICT")
        self.assertEqual(AiProposal.objects.count(), 1)
        self.assertEqual(AiOperation.objects.count(), 1)
        self.assertEqual(Task.objects.count(), 0)

    def test_absent_brief_keeps_legacy_canonical_digest_and_replay_compatible(self):
        key = uuid4()
        first = self.generate(key=key)
        old_body = json.dumps(
            {"scenario_id": "subtitle-check-v1", "contract_version": "ai.task-plan.v1"},
            sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
        )
        expected = salted_hmac("hustlytasker.ai.fixture-request.v1", old_body, algorithm="sha256").hexdigest()
        self.assertEqual(AiOperation.objects.get().body_digest, expected)
        with patch.object(FixtureAdapter, "generate", side_effect=AssertionError("No legacy replay dispatch")):
            replay = self.generate(key=key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.data["proposal_id"], first.data["proposal_id"])

    def test_adding_or_removing_brief_is_a_changed_operation_body(self):
        key = uuid4()
        self.assertEqual(self.generate(key=key).status_code, 201)
        result = self.generate({"scenario_id": "subtitle-check-v1", "brief": "Synthetic added brief."}, key=key)
        self.assertEqual(result.status_code, 409)
        self.assertEqual(Task.objects.count(), 0)

    def test_direct_service_rejects_explicit_null_brief_instead_of_treating_it_as_absent(self):
        with self.assertRaises(AIError) as error:
            durable_services.generate_proposal(
                actor=self.owner, profile_id=self.profile.pk, workspace_id=self.workspace.pk,
                scenario_id="subtitle-check-v1", idempotency_key=uuid4(), brief=None,
            )
        self.assertEqual(error.exception.code.value, "VALIDATION_ERROR")
        self.assert_no_generation_rows()

    def test_options_appends_public_fixture_metadata_without_rows_or_provider_dispatch(self):
        counts = (AiProposal.objects.count(), AiOperation.objects.count(), Task.objects.count(), AuditLog.objects.count())
        with patch.object(FixtureAdapter, "generate", side_effect=AssertionError("No metadata dispatch")):
            response = self.client.options(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.data)
        self.assertIn("renders", response.data)
        self.assertEqual(set(response.headers["Allow"].replace(" ", "").split(",")), {"POST", "OPTIONS"})
        self.assertIn("no-store", response.headers["Cache-Control"])
        ai = response.data["ai"]
        self.assertEqual(set(ai), {"contract_version", "enabled", "mode", "generated_by_ai", "scenarios", "limits"})
        self.assertEqual((ai["contract_version"], ai["enabled"], ai["mode"], ai["generated_by_ai"]),
                         ("ai.v1", True, "fixture_demo", False))
        self.assertEqual(ai["limits"], {"max_brief_chars": 6000, "max_tasks": 20,
                                        "max_depth": 3, "max_request_bytes": 32768})
        self.assertEqual({item["id"] for item in ai["scenarios"]}, {"subtitle-check-v1", "task-tree-v1"})
        for scenario in ai["scenarios"]:
            self.assertEqual(set(scenario), {"id", "label", "brief"})
            self.assertTrue(scenario["brief"].startswith("Ví dụ synthetic"))
        self.assertEqual(counts, (AiProposal.objects.count(), AiOperation.objects.count(), Task.objects.count(), AuditLog.objects.count()))

    def test_options_does_not_consume_or_reset_generation_throttles(self):
        for _ in range(5):
            self.assertEqual(self.client.options(self.url()).status_code, 200)
        self.assertEqual([self.generate().status_code for _ in range(4)], [201, 201, 201, 429])
        self.assertEqual(self.client.options(self.url()).status_code, 200)
        self.assertEqual(self.generate().status_code, 429)
        self.assertEqual(Task.objects.count(), 0)

    def test_options_reports_disabled_and_production_refusal_without_mutating_flag(self):
        for settings in (
            {"AI_FIXTURE_ENABLED": False},
            {"AI_FIXTURE_ENABLED": True, "ENVIRONMENT": "production", "IS_PRODUCTION": True},
            {"AI_FIXTURE_ENABLED": True, "ENVIRONMENT": "production", "IS_PRODUCTION": False},
        ):
            with self.subTest(configuration=settings), override_settings(**settings):
                response = self.client.options(self.url())
                self.assertEqual(response.status_code, 200)
                self.assertIs(response.data["ai"]["enabled"], False)
                self.assertEqual(self.generate().status_code, 503)
        self.assert_no_generation_rows()

    def test_options_requires_current_management_authority_without_staff_shortcut(self):
        for actor in (self.owner, self.admin, self.manager):
            self.client.force_authenticate(actor)
            self.assertEqual(self.client.options(self.url()).status_code, 200)
        for actor in (self.viewer, self.staff, self.outsider, None):
            self.client.force_authenticate(actor)
            response = self.client.options(self.url())
            self.assertIn(response.status_code, (403, 404))
            self.assertNotIn("ai", response.data)
        self.assert_no_generation_rows()

    def test_options_rejects_cross_tenant_archived_and_revoked_context(self):
        response = self.client.options(self.url(profile=self.foreign_profile.pk, workspace=self.foreign_workspace.pk))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("ai", response.data)
        self.client.force_authenticate(self.manager)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.manager).update(is_active=False)
        self.assertIn(self.client.options(self.url()).status_code, (403, 404))
        self.client.force_authenticate(self.owner)
        Workspace.objects.filter(pk=self.workspace.pk).update(status="ARCHIVED")
        self.assertEqual(self.client.options(self.url()).status_code, 403)
        Workspace.objects.filter(pk=self.workspace.pk).update(status="ACTIVE")
        Profile.objects.filter(pk=self.profile.pk).update(status="ARCHIVED")
        self.assertEqual(self.client.options(self.url()).status_code, 403)
        self.assert_no_generation_rows()
