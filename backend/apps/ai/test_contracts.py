"""Stateless contract/security checks; no database use is permitted."""

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import timezone
from uuid import UUID

from django.test import SimpleTestCase

from apps.tasks.models import Task

from .contracts import (
    MAX_HIERARCHY_DEPTH, PRIORITIES, FeedbackSource, Scope, ValidationLimits,
)
from .errors import AIError, ErrorCode
from .validation import (
    parse_feedback_analysis, parse_task_plan,
    validate_feedback_input, validate_generator_input,
)


def node(ref="item_1", parent=None):
    return {
        "local_ref": ref, "parent_ref": parent, "title": "Synthetic task",
        "description": "Synthetic description", "priority": "MEDIUM",
        "proposed_deadline": None, "notes": "",
    }


def plan():
    return {
        "contract_version": "ai.task-plan.v1", "tasks": [node()],
        "assumptions": [], "warnings": [],
    }


def analysis():
    return {
        "contract_version": "ai.feedback.v1", "summary": "Synthetic subtitle feedback",
        "issues": [{"category": "TECHNICAL", "description": "Check subtitle contrast",
                    "source_refs": ["S1"]}],
        "suggested_actions": [{"action": "Review subtitle contrast", "priority": "MEDIUM",
                               "rationale": "Readability", "source_refs": ["S1"]}],
        "uncertainty": "Text only", "warnings": [],
    }


class TaskContractTests(SimpleTestCase):
    def setUp(self):
        self.limits = ValidationLimits()

    def parse(self, payload):
        return parse_task_plan(json.dumps(payload), self.limits)

    def invalid(self, payload):
        with self.assertRaises(AIError) as error:
            self.parse(payload)
        self.assertEqual(error.exception.code, ErrorCode.INVALID_PROVIDER_RESPONSE)

    def test_contract_constants_match_existing_task_source(self):
        self.assertEqual(tuple(Task.Priority.values), PRIORITIES)
        self.assertEqual(Task.MAX_HIERARCHY_DEPTH, MAX_HIERARCHY_DEPTH)
        self.assertEqual(Task._meta.get_field("title").max_length, 255)

    def test_valid_plan_returns_immutable_typed_contract(self):
        result = self.parse(plan())
        self.assertEqual(result.tasks[0].priority, "MEDIUM")
        self.assertIsInstance(result.tasks, tuple)
        with self.assertRaises(FrozenInstanceError):
            result.tasks = ()

    def test_four_priority_values_are_supported(self):
        for priority in PRIORITIES:
            with self.subTest(priority=priority):
                payload = plan()
                payload["tasks"][0]["priority"] = priority
                self.assertEqual(self.parse(payload).tasks[0].priority, priority)

    def test_invalid_priority_or_numeric_coercion_is_rejected(self):
        for value in ("CRITICAL", "low", 1, True, None, ["HIGH"]):
            with self.subTest(value=value):
                payload = plan()
                payload["tasks"][0]["priority"] = value
                self.invalid(payload)

    def test_aware_deadline_is_normalized_to_utc(self):
        payload = plan()
        payload["tasks"][0]["proposed_deadline"] = "2026-10-30T18:00:00+07:00"
        result = self.parse(payload).tasks[0].proposed_deadline
        self.assertEqual(result.isoformat(), "2026-10-30T11:00:00+00:00")
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_invalid_naive_overflow_and_malformed_offset_deadlines(self):
        values = ("tomorrow", "2026-10-30", "2026-10-30T18:00:00",
                  "2026-02-30T18:00:00Z", "0001-01-01T00:00:00+14:00",
                  "9999-12-31T23:59:59-14:00", "2026-10-30T18:00:00+01:99", 1, True)
        for value in values:
            with self.subTest(value=value):
                payload = plan()
                payload["tasks"][0]["proposed_deadline"] = value
                self.invalid(payload)

    def test_root_and_maximum_three_child_edges(self):
        payload = plan()
        payload["tasks"] = [node("item_1"), node("item_2", "item_1"),
                            node("item_3", "item_2"), node("item_4", "item_3")]
        self.assertEqual(len(self.parse(payload).tasks), 4)

    def test_depth_four_is_rejected(self):
        payload = plan()
        payload["tasks"] = [node(f"item_{i}", f"item_{i-1}" if i > 1 else None)
                            for i in range(1, 6)]
        self.invalid(payload)

    def test_self_parent_and_multinode_cycle_rejected(self):
        for nodes in ([node("item_1", "item_1")],
                      [node("item_1", "item_2"), node("item_2", "item_1")]):
            payload = plan()
            payload["tasks"] = nodes
            self.invalid(payload)

    def test_missing_parent_or_uuid_parent_is_rejected(self):
        for parent in ("item_2", "00000000-0000-4000-8000-000000000099", 1):
            payload = plan()
            payload["tasks"][0]["parent_ref"] = parent
            self.invalid(payload)

    def test_duplicate_local_identifier_rejected(self):
        payload = plan()
        payload["tasks"].append(node())
        self.invalid(payload)

    def test_parent_order_does_not_have_to_be_topological(self):
        payload = plan()
        payload["tasks"] = [node("item_2", "item_1"), node("item_1")]
        self.assertEqual(len(self.parse(payload).tasks), 2)

    def test_unexpected_status_owner_membership_and_duration_rejected(self):
        for field in ("status", "owner", "assignee", "profile_id", "workspace_id",
                      "membership_id", "estimated_duration", "subtasks"):
            payload = plan()
            payload["tasks"][0][field] = "synthetic-untrusted"
            self.invalid(payload)

    def test_unknown_top_level_field_or_missing_field_rejected(self):
        payload = plan()
        payload["extra"] = True
        self.invalid(payload)
        payload = plan()
        del payload["tasks"][0]["notes"]
        self.invalid(payload)

    def test_title_empty_oversize_or_wrong_primitive_rejected(self):
        for title in ("", "  ", "x" * 256, 42, None, False):
            payload = plan()
            payload["tasks"][0]["title"] = title
            self.invalid(payload)

    def test_unicode_and_nul_rejected_without_echo(self):
        for text in ("synthetic-secret\x00", "synthetic-secret\ud800"):
            payload = plan()
            payload["tasks"][0]["description"] = text
            with self.assertRaises(AIError) as error:
                self.parse(payload)
            self.assertNotIn("synthetic-secret", str(error.exception))
            self.assertNotIn("synthetic-secret", repr(error.exception))
            self.assertIsNone(error.exception.__cause__)

    def test_excessive_task_count_and_empty_list_rejected(self):
        for count in (0, 21):
            payload = plan()
            payload["tasks"] = [node(f"item_{i}") for i in range(1, count + 1)]
            self.invalid(payload)

    def test_long_description_notes_and_warnings_rejected(self):
        for field, size in (("description", 2001), ("notes", 501)):
            payload = plan()
            payload["tasks"][0][field] = "x" * size
            self.invalid(payload)
        payload = plan()
        payload["warnings"] = ["x"] * 11
        self.invalid(payload)

    def test_version_is_exact(self):
        payload = plan()
        payload["contract_version"] = "ai.task-plan.v999"
        self.invalid(payload)

    def test_malformed_duplicate_json_keys_and_nonfinite_values_rejected(self):
        samples = ('', '[]', 'null', '{} trailing', '```json\n{}\n```',
                   '{"tasks":[],"tasks":[]}', '{"tasks":NaN}',
                   '{"tasks":Infinity}', '{"tasks":-Infinity}', '{"tasks":')
        for raw in samples:
            with self.subTest(raw=raw), self.assertRaises(AIError):
                parse_task_plan(raw, self.limits)

    def test_response_byte_cap_includes_multibyte_content(self):
        limits = ValidationLimits(max_response_bytes=150)
        with self.assertRaises(AIError):
            parse_task_plan('"' + "ế" * 100 + '"', limits)

    def test_excessive_json_nesting_is_safe_error(self):
        with self.assertRaises(AIError):
            parse_task_plan("[" * 2000 + "]" * 2000, self.limits)

    def test_confidential_plan_text_not_present_in_dataclass_repr(self):
        result = self.parse(plan())
        self.assertNotIn("Synthetic task", repr(result))
        self.assertNotIn("Synthetic task", repr(result.tasks[0]))


class InputContractTests(SimpleTestCase):
    def setUp(self):
        self.limits = ValidationLimits()
        self.scope = Scope(UUID(int=1), UUID(int=2), UUID(int=3))
        self.task_id = UUID(int=4)
        self.source = FeedbackSource("S1", "Synthetic feedback", self.scope.profile_id,
                                     self.scope.workspace_id, self.task_id)

    def test_valid_generator_input_supports_explicit_timezone_and_deadline(self):
        value = validate_generator_input({
            "brief": "Synthetic brief", "target_deadline": "2026-10-30T18:00:00+07:00",
            "reference_time": "2026-10-28T00:00:00Z", "timezone": "Asia/Ho_Chi_Minh",
        }, self.limits)
        self.assertEqual(value.target_deadline.hour, 11)
        self.assertEqual(value.timezone_name, "Asia/Ho_Chi_Minh")

    def test_generator_does_not_invent_deadline(self):
        result = validate_generator_input({"brief": "Finish by the weekend"}, self.limits)
        self.assertIsNone(result.target_deadline)
        self.assertIsNone(result.reference_time)

    def test_empty_oversized_numeric_and_invalid_brief_rejected(self):
        for brief in ("", "  ", "x" * 6001, 12, False, "x\x00", "x\udfff"):
            with self.subTest(brief_type=type(brief)), self.assertRaises(AIError) as error:
                validate_generator_input({"brief": brief}, self.limits)
            self.assertEqual(error.exception.code, ErrorCode.VALIDATION_ERROR)

    def test_unknown_tenant_provider_status_and_membership_input_rejected(self):
        for key in ("workspace_id", "profile_id", "membership_id", "provider", "status"):
            with self.subTest(key=key), self.assertRaises(AIError):
                validate_generator_input({"brief": "Synthetic", key: "bad"}, self.limits)

    def test_invalid_timezone_or_deadline_rejected(self):
        for extra in ({"timezone": "No/Such_Zone"}, {"timezone": 7},
                      {"target_deadline": "2026-10-29T10:00:00"},
                      {"reference_time": "2026-10-29"}):
            with self.subTest(extra=extra), self.assertRaises(AIError):
                validate_generator_input({"brief": "Synthetic", **extra}, self.limits)

    def test_request_byte_cap_enforced(self):
        with self.assertRaises(AIError):
            validate_generator_input({"brief": "Synthetic"}, ValidationLimits(max_request_bytes=10))

    def test_invalid_input_container_is_rejected(self):
        for value in (None, [], "brief", {1: "synthetic"}):
            with self.subTest(value_type=type(value)), self.assertRaises(AIError):
                validate_generator_input(value, self.limits)

    def test_limits_cannot_bypass_existing_depth_or_fixture_bounds(self):
        for options in ({"max_tasks": 21}, {"max_depth": 4}, {"max_depth": True},
                        {"max_sources": 0}, {"max_response_bytes": -1},
                        {"max_brief_chars": 10**12}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                ValidationLimits(**options)

    def test_scope_requires_uuid_without_claiming_authorization(self):
        with self.assertRaises(ValueError):
            Scope("synthetic", self.scope.profile_id, self.scope.workspace_id)
        self.assertNotIn(str(self.scope.actor_id), repr(self.scope))

    def test_generator_sensitive_text_is_hidden_from_repr(self):
        value = validate_generator_input({"brief": "synthetic-confidential"}, self.limits)
        self.assertNotIn("synthetic-confidential", repr(value))

    def test_feedback_selection_returns_only_selected_sources(self):
        second = replace(self.source, ref="S2", text="Second synthetic source")
        value = validate_feedback_input({"source_refs": ["S2"], "focus": "Clarity"},
                                        (self.source, second), self.scope, self.task_id, self.limits)
        self.assertEqual(value.source_refs, ("S2",))
        self.assertNotIn("Second synthetic", repr(value))

    def test_invalid_feedback_selection_rejected(self):
        for refs in ([], ["S99"], ["S1", "S1"], [1], "S1"):
            with self.subTest(refs=refs), self.assertRaises(AIError):
                validate_feedback_input({"source_refs": refs}, (self.source,),
                                        self.scope, self.task_id, self.limits)

    def test_feedback_input_cross_profile_workspace_task_and_deleted_sources_rejected(self):
        for update in ({"profile_id": UUID(int=11)}, {"workspace_id": UUID(int=12)},
                       {"task_id": UUID(int=13)}, {"deleted": True}):
            with self.subTest(update=update), self.assertRaises(AIError):
                validate_feedback_input({"source_refs": ["S1"]},
                                        (replace(self.source, **update),),
                                        self.scope, self.task_id, self.limits)

    def test_source_total_length_and_count_are_bounded(self):
        source = replace(self.source, text="x" * 12001)
        with self.assertRaises(AIError):
            validate_feedback_input({"source_refs": ["S1"]}, (source,),
                                    self.scope, self.task_id, self.limits)
        sources = tuple(replace(self.source, ref=f"S{i}") for i in range(1, 22))
        with self.assertRaises(AIError):
            validate_feedback_input({"source_refs": ["S1"]}, sources,
                                    self.scope, self.task_id, self.limits)


class FeedbackContractTests(SimpleTestCase):
    def setUp(self):
        self.limits = ValidationLimits()
        self.scope = Scope(UUID(int=1), UUID(int=2), UUID(int=3))
        self.task_id = UUID(int=4)
        self.sources = (FeedbackSource("S1", "Synthetic subtitle feedback",
                                       self.scope.profile_id, self.scope.workspace_id,
                                       self.task_id),)

    def parse(self, value, sources=None):
        return parse_feedback_analysis(json.dumps(value), self.sources if sources is None else sources,
                                       self.scope, self.task_id, self.limits)

    def test_valid_feedback_analysis_typed_and_immutable(self):
        result = self.parse(analysis())
        self.assertEqual(result.issues[0].source_refs, ("S1",))
        self.assertEqual(result.suggested_actions[0].priority, "MEDIUM")
        with self.assertRaises(FrozenInstanceError):
            result.summary = "Changed"

    def test_unknown_citation_duplicate_and_fake_url_are_rejected(self):
        for refs in (["S99"], ["https://example.invalid/source"], ["S1", "S1"], [], [1]):
            payload = analysis()
            payload["issues"][0]["source_refs"] = refs
            with self.subTest(refs=refs), self.assertRaises(AIError):
                self.parse(payload)

    def test_deleted_or_cross_tenant_source_cannot_authorize_citation(self):
        for update in ({"deleted": True}, {"workspace_id": UUID(int=21)},
                       {"profile_id": UUID(int=22)}, {"task_id": UUID(int=23)}):
            with self.subTest(update=update), self.assertRaises(AIError):
                self.parse(analysis(), (replace(self.sources[0], **update),))

    def test_duplicate_source_labels_rejected(self):
        with self.assertRaises(AIError):
            self.parse(analysis(), self.sources + self.sources)

    def test_empty_summary_wrong_category_priority_and_count_rejected(self):
        samples = []
        for field, value in (("summary", ""), ("summary", "x" * 1601),
                             ("uncertainty", "x" * 601), ("warnings", [False])):
            payload = analysis()
            payload[field] = value
            samples.append(payload)
        payload = analysis()
        payload["issues"][0]["category"] = "PRIVATE"
        samples.append(payload)
        payload = analysis()
        payload["suggested_actions"][0]["priority"] = "CRITICAL"
        samples.append(payload)
        payload = analysis()
        payload["issues"] *= 11
        samples.append(payload)
        for payload in samples:
            with self.assertRaises(AIError):
                self.parse(payload)

    def test_unknown_action_fields_and_model_ids_are_rejected(self):
        for key in ("status", "review_id", "owner_id", "workspace_id", "url"):
            payload = analysis()
            payload["suggested_actions"][0][key] = "synthetic"
            with self.subTest(key=key), self.assertRaises(AIError):
                self.parse(payload)

    def test_feedback_version_and_malformed_json_rejected(self):
        payload = analysis()
        payload["contract_version"] = "ai.feedback.v2"
        with self.assertRaises(AIError):
            self.parse(payload)
        with self.assertRaises(AIError):
            parse_feedback_analysis("not-json", self.sources, self.scope, self.task_id, self.limits)

    def test_confidential_fields_are_not_in_repr_or_error(self):
        result = self.parse(analysis())
        self.assertNotIn("Synthetic subtitle", repr(result))
        self.assertNotIn("Check subtitle", repr(result.issues[0]))
        self.assertNotIn("Synthetic subtitle", repr(self.sources[0]))
        payload = deepcopy(analysis())
        payload["summary"] = {"synthetic-sensitive": "invalid"}
        with self.assertRaises(AIError) as error:
            self.parse(payload)
        self.assertNotIn("synthetic-sensitive", repr(error.exception))
        self.assertEqual(error.exception.code, ErrorCode.INVALID_PROVIDER_RESPONSE)
