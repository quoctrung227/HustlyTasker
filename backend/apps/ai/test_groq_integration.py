"""Django API tests with isolated PostgreSQL and a fake Groq HTTP transport."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.core.cache import cache
from django.db import IntegrityError, close_old_connections
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase, APITransactionTestCase

from apps.audit.models import AuditLog
from apps.reviews.models import Deliverable, Review
from apps.tasks.models import Task, TaskAssignment

from . import durable_services, governance
from .groq_adapter import GROQ_CHAT_URL, GroqTransportResponse
from .models import AiBudgetBucket, AiDispatch, AiOperation, AiProposal
from .test_groq_adapter import _envelope, _plan, _response
from .test_live_feedback import QUOTE, valid_analysis
from .test_live_generator import LiveGeneratorData


SETTINGS = dict(AI_PROVIDER="groq", AI_LIVE_ENABLED=True, AI_FIXTURE_ENABLED=True,
                AI_GROQ_FREE_TIER_CONFIRMED=True, AI_MODEL=None)
BRIEF = {"brief": "Kiểm tra phụ đề video giới thiệu.", "task_count": 1}
SMOKE = {"brief": governance._SMOKE_BRIEF, "task_count": 1}


class GroqData(LiveGeneratorData):
    def prepare_groq(self):
        self.data()
        cache.clear()
        self.addCleanup(cache.clear)
        self.client.force_authenticate(self.owner)
        self.send = self.enterContext(patch("apps.ai.live_runtime.GroqHttpsTransport.post",
                                            return_value=_response(_envelope(_plan()))))
        self.enterContext(patch("apps.ai.live_runtime._groq_api_key", return_value="synthetic-test-groq-token"))
        self.openai_send = self.enterContext(patch("apps.ai.live_runtime.OpenAIHttpsTransport.post",
                                                   side_effect=AssertionError("Unexpected OpenAI transport")))

    def generate(self, **kwargs):
        kwargs.setdefault("body", BRIEF)
        return super().generate(**kwargs)

    def analyze(self, task, body, *, key=None):
        url = reverse("ai:feedback-analyze", kwargs={
            "profile_id": self.profile.pk, "workspace_id": self.workspace.pk, "task_id": task.pk,
        })
        return self.client.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY=str(key or uuid4()))

    def feedback_task(self):
        return Task.objects.create(workspace=self.workspace, created_by=self.owner, title="Synthetic task")

    def analysis_response(self, quote):
        payload = valid_analysis()
        payload["issues"][0]["evidence"][0]["quote"] = quote
        self.send.return_value = _response(_envelope(payload))


@override_settings(**SETTINGS)
class GroqIntegrationTests(GroqData, APITestCase):
    def setUp(self):
        self.prepare_groq()

    def test_generate_edit_confirm_and_replay_preserve_provenance_and_hours(self):
        meta = self.client.options(self.url()).data["ai"]
        self.assertEqual((meta["enabled"], meta["mode"]), (True, "groq_live"))
        key = uuid4()
        result = self.generate(key=key)
        self.assertEqual(result.status_code, 201, result.data)
        proposal = result.data
        self.assertEqual((proposal["mode"], proposal["provider"], proposal["scenario_id"]),
                         ("groq_live", "groq", "groq-live-v1"))
        self.assertEqual(proposal["usage"], {"input_tokens": 602, "billable_output_tokens": 151,
                                            "cost_usd": "0.00018090", "status": "provider_reported"})
        self.assertFalse(Task.objects.exists())
        self.assertEqual(self.generate(key=key).status_code, 200)
        self.send.assert_called_once()
        request = self.send.call_args.kwargs
        self.assertEqual(request["url"], GROQ_CHAT_URL)
        self.assertTrue(json.loads(request["body"])["response_format"]["json_schema"]["strict"])
        dispatch = AiDispatch.objects.get()
        self.assertEqual((dispatch.execution_mode, dispatch.usage_status), ("GROQ_LIVE", "REPORTED"))
        self.assertIsNone(dispatch.billed_cost)
        self.assertEqual(dispatch.estimated_cost, Decimal("0.00018090"))
        self.assertEqual(dispatch.accounted_amount, 0)
        self.assertEqual(set(AiBudgetBucket.objects.values_list("execution_mode", "cost_limit")),
                         {("GROQ_LIVE", Decimal("0"))})
        edited = deepcopy(proposal["payload"])
        edited["tasks"][0].update(title="Giờ đã duyệt", estimated_hours="2.35")
        confirmation_key = uuid4()
        confirmed = self.confirm(proposal, key=confirmation_key, payload=edited)
        self.assertEqual(confirmed.status_code, 201, confirmed.data)
        self.assertEqual(self.confirm(proposal, key=confirmation_key, payload=edited).status_code, 200)
        saved = Task.objects.get()
        self.assertEqual((saved.title, saved.estimated_hours), ("Giờ đã duyệt", Decimal("2.35")))
        self.assertEqual(self.client.get(self.task_url(saved.pk)).data["estimated_hours"], "2.35")
        self.assertIsNone(saved.parent_id)
        self.assertFalse(TaskAssignment.objects.exists())
        self.assertTrue(AuditLog.objects.filter(action="ai.proposal.confirmed").exists())

    def test_reject_keeps_provider_and_creates_no_task(self):
        proposal = self.generate().data
        url = self.url("proposal-reject", proposal=proposal)
        rejected = self.client.post(url, {"proposal_revision": proposal["revision"]}, format="json")
        self.assertEqual((rejected.status_code, rejected.data["status"], rejected.data["mode"]),
                         (200, "REJECTED", "groq_live"))
        self.assertIsNone(rejected.data["payload"])
        self.assertFalse(Task.objects.exists())
        self.send.assert_called_once()

    def test_feedback_grounds_review_quote_without_business_mutation(self):
        task = self.feedback_task()
        deliverable = Deliverable.objects.create(task=task, uploaded_by=self.member, revision=1,
                                                 status="REJECTED", file_url="https://example.test/private")
        review = Review.objects.create(deliverable=deliverable, reviewer=self.owner,
                                       status="REQUEST_CHANGE", comment=QUOTE)
        self.analysis_response(QUOTE)
        key = uuid4()
        body = {"sources": [{"kind": "review", "id": str(review.pk)}]}
        before = self.domain()
        result = self.analyze(task, body, key=key)
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual((result.data["mode"], result.data["provider"]), ("groq_live", "groq"))
        self.assertEqual(result.data["payload"]["issues"][0]["evidence"], [{"source_ref": "S1", "quote": QUOTE}])
        self.assertEqual(self.analyze(task, body, key=key).status_code, 409)
        self.assertEqual(self.domain(), before)
        self.assertNotIn(str(review.pk), str(self.send.call_args.kwargs["body"]))
        self.assertNotIn(deliverable.file_url, str(self.send.call_args.kwargs["body"]))
        self.send.assert_called_once()

    def test_429_propagates_header_once_and_does_not_fall_back(self):
        self.send.return_value = GroqTransportResponse(429, b"", "42")
        key = uuid4()
        result = self.generate(key=key)
        self.assertEqual((result.status_code, result.data["code"], result["Retry-After"]),
                         (429, "RATE_LIMITED", "42"))
        self.assertEqual(self.generate(key=key).status_code, 409)
        self.assertEqual(AiDispatch.objects.get().status, "OUTCOME_UNKNOWN")
        self.send.assert_called_once()
        self.openai_send.assert_not_called()

    def test_timeout_holds_reservation_and_blocks_next_send_at_quota(self):
        self.send.side_effect = TimeoutError
        first = self.generate()
        self.assertEqual((first.status_code, first.data["code"]), (504, "PROVIDER_TIMEOUT"))
        second = self.generate(workspace=self.other_workspace)
        self.assertEqual((second.status_code, second.data["code"]), (429, "RATE_LIMITED"))
        self.assertEqual(AiDispatch.objects.get().status, "OUTCOME_UNKNOWN")
        self.send.assert_called_once()
        self.openai_send.assert_not_called()

    def test_malformed_output_with_valid_usage_settles_without_proposal(self):
        response = _envelope(_plan())
        response["choices"][0]["message"]["content"] = "not JSON"
        self.send.return_value = _response(response)
        result = self.generate()
        self.assertEqual((result.status_code, result.data["code"]), (502, "INVALID_PROVIDER_RESPONSE"))
        dispatch = AiDispatch.objects.get()
        self.assertEqual((dispatch.status, dispatch.output_tokens), ("RECONCILED", 151))
        self.assertFalse(AiProposal.objects.exists())
        self.send.assert_called_once()

    def test_refusal_keeps_reported_usage_without_new_attempt(self):
        response = _envelope(_plan())
        response["choices"][0]["message"].update(content=None, refusal="private vendor text")
        self.send.return_value = _response(response)
        result = self.generate()
        self.assertEqual((result.status_code, result.data["code"]), (422, "AI_REFUSED"))
        self.assertNotIn("private vendor text", str(result.data))
        self.assertEqual(AiDispatch.objects.get().usage_status, "REPORTED")
        self.send.assert_called_once()

    @override_settings(AI_GROQ_REQUESTS_PER_MINUTE=1, AI_GROQ_REQUESTS_PER_DAY=2)
    def test_minute_and_day_quota_shared_between_workspaces(self):
        now = timezone.now()
        self.assertEqual(self.generate().status_code, 201)
        limited = self.generate(workspace=self.other_workspace)
        self.assertEqual((limited.status_code, limited.data["code"]), (429, "RATE_LIMITED"))
        cache.clear()
        with patch("apps.ai.governance.timezone.now", return_value=now + timedelta(seconds=61)):
            self.assertEqual(self.generate(workspace=self.other_workspace).status_code, 201)
        with patch("apps.ai.governance.timezone.now", return_value=now + timedelta(minutes=3)):
            limited = self.generate()
        self.assertEqual((limited.status_code, limited.data["code"]), (429, "RATE_LIMITED"))
        self.assertEqual(self.send.call_count, 2)

    @override_settings(AI_GROQ_TOKENS_PER_DAY=5800)
    def test_daily_token_cap_still_applies_after_minute_window(self):
        now = timezone.now()
        self.assertEqual(self.generate().status_code, 201)
        with patch("apps.ai.governance.timezone.now", return_value=now + timedelta(seconds=61)):
            limited = self.generate(workspace=self.foreign_workspace)
        self.assertEqual((limited.status_code, limited.data["code"]), (429, "RATE_LIMITED"))
        self.send.assert_called_once()

    def test_legacy_recovery_and_live_idempotency_when_switching_provider(self):
        key = uuid4()
        proposal = self.generate(key=key).data
        with override_settings(AI_PROVIDER="openai"), patch("apps.ai.live_runtime._api_key",
                                                            return_value="synthetic-openai-token"):
            replay = self.generate(key=key)
            self.assertEqual((replay.status_code, replay.data["code"]), (409, "IDEMPOTENCY_CONFLICT"))
            recovered = self.client.get(self.url("proposal-detail", proposal=proposal))
            self.assertEqual((recovered.status_code, recovered.data["mode"]), (200, "groq_live"))
        self.send.assert_called_once()
        self.openai_send.assert_not_called()

    def test_tenant_csrf_and_trash_guards_precede_provider_dispatch(self):
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.generate().status_code, 404)
        csrf = APIClient(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.url(), BRIEF, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code, 403)
        self.client.force_authenticate(self.owner)
        task = self.feedback_task()
        for deleted in (task, self.workspace, self.profile):
            with self.subTest(scope=type(deleted).__name__):
                cache.clear()
                deleted.deleted_at = timezone.now()
                deleted.purge_after = deleted.deleted_at + timedelta(days=30)
                deleted.save(update_fields=("deleted_at", "purge_after"))
                self.assertEqual(self.analyze(task, {"feedback_text": QUOTE}).status_code, 404)
                deleted.deleted_at = deleted.purge_after = None
                deleted.save(update_fields=("deleted_at", "purge_after"))
        self.send.assert_not_called()
        self.assertFalse(AiDispatch.objects.exists())

    def test_confirm_failure_rolls_back_task_and_keeps_proposal(self):
        proposal = self.generate().data
        create_task = durable_services.create_task

        def fail_after_write(**kwargs):
            create_task(**kwargs)
            raise IntegrityError("synthetic confirmation rollback")

        with patch("apps.ai.durable_services.create_task", side_effect=fail_after_write):
            with self.assertRaises(IntegrityError):
                self.confirm(proposal)
        self.assertFalse(Task.objects.exists())
        self.assertFalse(AiOperation.objects.exists())
        self.assertEqual(AiProposal.objects.get().status, "AVAILABLE")


@override_settings(**SETTINGS, AI_CONTROLLED_LIVE=True)
class GroqControlledTests(GroqData, APITransactionTestCase):
    def setUp(self):
        self.prepare_groq()

    def test_exact_manifest_and_only_one_send_per_feature(self):
        task = self.feedback_task()
        self.assertEqual(self.generate().status_code, 400)
        self.assertEqual(self.generate(body=SMOKE).status_code, 201)
        limited = self.generate(body=SMOKE, workspace=self.other_workspace)
        self.assertEqual((limited.status_code, limited.data["code"]), (429, "RATE_LIMITED"))
        cache.clear()
        self.analysis_response("phụ đề xuất hiện chậm ở giây 12–18")
        body = {"feedback_text": governance._SMOKE_FEEDBACK, "sources": []}
        self.assertEqual(self.analyze(task, {**body, "focus": "Changed"}).status_code, 400)
        self.assertEqual(self.analyze(task, body).status_code, 200)
        limited = self.analyze(task, body)
        self.assertEqual((limited.status_code, limited.data["code"]), (429, "RATE_LIMITED"))
        self.assertEqual(self.send.call_count, 2)
        self.assertEqual(set(AiDispatch.objects.values_list("feature", flat=True)),
                         {"task_plan", "feedback_analysis"})
        self.assertEqual(Task.objects.count(), 1)

    def test_concurrent_fresh_keys_across_workspaces_cannot_duplicate_send(self):
        barrier = Barrier(2, timeout=10)
        urls = [self.url(), self.url(workspace=self.foreign_workspace)]

        def attempt(url):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(self.owner)
                barrier.wait()
                return client.post(url, SMOKE, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, urls))
        self.assertEqual(sorted(results), [201, 429])
        self.assertEqual(AiDispatch.objects.count(), 1)
        self.send.assert_called_once()

    def test_provider_timeout_keeps_slot_across_new_key_and_runtime_configuration(self):
        self.send.side_effect = TimeoutError
        self.assertEqual(self.generate(body=SMOKE).status_code, 504)
        self.assertEqual(self.generate(body=SMOKE).status_code, 429)
        with override_settings(AI_CONTROLLED_LIVE=False):
            self.assertEqual(self.generate(body=SMOKE).status_code, 400)
        self.send.assert_called_once()
