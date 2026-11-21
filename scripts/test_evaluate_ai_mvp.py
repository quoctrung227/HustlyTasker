"""Synthetic checks for the offline evaluation harness, independent of Owner data."""

import json
import unittest
from decimal import Decimal

from evaluate_ai_mvp import EvaluationError, evaluate, feedback_validator, generator_validator


def proposal(hours):
    return json.dumps({"tasks": [{"title": "Check captions", "description": "Check legibility.",
                                  "priority": "MEDIUM", "estimated_hours": hours}],
                       "assumptions": [], "warnings": []})


def feedback(quote):
    return json.dumps({"contract_version": "ai.feedback.v2", "summary": "Improve captions.",
                       "issues": [{"category": "TECHNICAL", "description": "Low contrast.",
                                   "severity": "HIGH", "source_refs": ["S1"],
                                   "evidence": [{"source_ref": "S1", "quote": quote}]}],
                       "suggested_actions": [], "uncertainty": "", "warnings": []})


class EvaluationTests(unittest.TestCase):
    def test_mae_uses_only_matched_actual_hours_and_non_null_estimates(self):
        data = {"cases": [
            {"id": "G1", "input": {"brief": "Synthetic brief."}, "actual_hours_by_ref": {"item_1": 4}},
            {"id": "G2", "input": {"brief": "Synthetic brief."}},
            {"id": "G3", "input": {"brief": "Synthetic brief."}, "actual_hours_by_ref": {"item_1": 10}},
            {"id": "G4", "input": {"brief": "Synthetic brief."}},
        ]}
        saved = {"mode": "mock", "model": "synthetic", "results": [
            {"id": "G1", "raw_output": proposal(2.5), "latency_ms": 100,
             "usage": {"input_tokens": 12, "output_tokens": None, "estimated_cost_usd": None},
             "owner_review": {"relevance": 2, "accuracy": 1, "unsupported_claims": True}},
            {"id": "G2", "raw_output": proposal(3)},
            {"id": "G3", "raw_output": proposal(None)},
        ]}
        report = evaluate(data, saved, generator_validator, "mock")
        summary = report["summary"]
        self.assertEqual(summary["estimated_hours_mae"], {"matched_estimates": 1, "hours": Decimal("1.5")})
        self.assertEqual(summary["observed_cases"], 3)
        self.assertEqual(summary["owner_scores"]["unsupported_claims_cases"], 1)
        self.assertEqual(summary["usage"]["input_tokens"], {"observations": 1, "total": 12})
        self.assertEqual(summary["usage"]["estimated_cost_usd"], {"observations": 0, "total": None})
        self.assertNotIn("Synthetic brief", str(report))
        self.assertNotIn("Check captions", str(report))

    def test_fabricated_and_redacted_quotes_fail_business_validation(self):
        source = {"sources": [{"ref": "S1", "text": "Low contrast. See https://private.example.test/p"}]}
        data = {"cases": [{"id": name, "input": source} for name in ("F1", "F2", "F3", "F4")]}
        saved = {"mode": "mock", "model": "synthetic", "results": [
            {"id": "F1", "raw_output": feedback("Low contrast.")},
            {"id": "F2", "raw_output": feedback("Wrong quotation")},
            {"id": "F3", "raw_output": feedback("https://private.example.test/p")},
            {"id": "F4", "raw_output": '{"not": "JSON"'},
        ]}
        report = evaluate(data, saved, feedback_validator, "mock")
        self.assertEqual(report["summary"]["usable_json_cases"], 3)
        self.assertEqual(report["summary"]["valid_business_cases"], 1)
        self.assertIsNone(report["summary"]["owner_scores"]["unsupported_claims_cases"])
        self.assertEqual([item["status"] for item in report["cases"]],
                         ["valid", "invalid_schema_or_content", "invalid_schema_or_content", "invalid_json_or_size"])

    def test_declared_lanes_and_unique_case_ids_are_enforced(self):
        case = {"id": "G1", "input": {"brief": "Synthetic brief."}}
        saved = {"mode": "mock", "model": "synthetic", "results": []}
        with self.assertRaisesRegex(EvaluationError, "RESULT_MODE_MISMATCH"):
            evaluate({"cases": [case]}, saved, generator_validator, "live")
        with self.assertRaisesRegex(EvaluationError, "DUPLICATE_CASE_ID"):
            evaluate({"cases": [case, case]}, saved, generator_validator, "mock")
