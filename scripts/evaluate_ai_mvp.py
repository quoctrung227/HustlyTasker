"""Evaluate saved AI MVP results offline with the application's strict validators."""

import argparse
import hashlib
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from apps.ai.contracts import FeedbackSource, Scope, ValidationLimits
from apps.ai.errors import AIError
from apps.ai.feedback_contracts import parse_live_feedback
from apps.ai.live_generator import live_request
from apps.ai.provider_privacy import REDACTED, redact_provider_text
from apps.ai.validation import _strict_json, validate_feedback_input


MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_CASES = 1000
IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}\Z")
TASK_REF = re.compile(r"item_[1-9][0-9]{0,2}\Z")
FEEDBACK_LIMITS = ValidationLimits()
SCOPE = Scope(UUID(int=1), UUID(int=2), UUID(int=3))
TASK_ID = UUID(int=4)


class EvaluationError(ValueError):
    """Only static reasons may be printed. Reports do not retain input bodies."""


def require(condition, code):
    if not condition:
        raise EvaluationError(code)


def shape(value, required, optional=()):
    require(type(value) is dict and set(required) <= set(value) <= set(required) | set(optional),
            "INVALID_DOCUMENT_SHAPE")


def read_json(path):
    def unique_pairs(pairs):
        result = {}
        for key, item in pairs:
            require(key not in result, "DUPLICATE_JSON_FIELD")
            result[key] = item
        return result

    def reject_nonfinite(_):
        raise EvaluationError("NONFINITE_JSON_NUMBER")

    with path.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    require(len(data) <= MAX_FILE_BYTES, "INPUT_FILE_TOO_LARGE")
    return (json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_pairs,
                       parse_constant=reject_nonfinite), hashlib.sha256(data).hexdigest())


def indexed(rows):
    require(type(rows) is list and len(rows) <= MAX_CASES, "INVALID_CASE_LIST")
    result = {}
    for row in rows:
        require(type(row) is dict and type(row.get("id")) is str and IDENTIFIER.fullmatch(row["id"]),
                "INVALID_CASE_ID")
        require(row["id"] not in result, "DUPLICATE_CASE_ID")
        result[row["id"]] = row
    return result


def measure(value):
    require(type(value) in (int, float, str), "INVALID_NUMERIC_METADATA")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise EvaluationError("INVALID_NUMERIC_METADATA") from None
    require(number.is_finite() and 0 <= number <= 1_000_000_000 and number.as_tuple().exponent >= -12,
            "INVALID_NUMERIC_METADATA")
    return number


def validate_usage(value):
    shape(value, ("input_tokens", "output_tokens", "estimated_cost_usd"))
    for name in ("input_tokens", "output_tokens"):
        count = value[name]
        require(count is None or (type(count) is int and 0 <= count <= 1_000_000_000), "INVALID_TOKEN_COUNT")
    cost = value["estimated_cost_usd"]
    return dict(value, estimated_cost_usd=measure(cost) if cost is not None else None)


def validate_owner_review(value):
    shape(value, ("relevance", "accuracy", "unsupported_claims"))
    for name in ("relevance", "accuracy"):
        score = value[name]
        require(type(score) is int and score in (0, 1, 2), "INVALID_OWNER_RUBRIC_SCORE")
    require(type(value["unsupported_claims"]) is bool, "INVALID_OWNER_UNSUPPORTED_CLAIMS_FLAG")
    return value


def generator_validator(case):
    def valid_hours(value):
        require(type(value) is dict and len(value) <= 20, "INVALID_ACTUAL_HOURS")
        require(all(TASK_REF.fullmatch(key) for key in value), "INVALID_ACTUAL_HOURS_REF")
        return {key: measure(hours) for key, hours in value.items()}

    shape(case, ("id", "input"), ("actual_hours_by_ref",))
    shape(case["input"], ("brief",), ("task_count", "target_deadline"))
    request = live_request(**case["input"])
    return request.validate, valid_hours(case.get("actual_hours_by_ref", {}))


def feedback_validator(case):
    shape(case, ("id", "input"))
    shape(case["input"], ("sources",), ("focus",))
    rows = case["input"]["sources"]
    require(type(rows) is list and 1 <= len(rows) <= FEEDBACK_LIMITS.max_sources, "INVALID_FEEDBACK_SOURCES")
    sources = []
    for index, row in enumerate(rows, start=1):
        shape(row, ("ref", "text"))
        require(row["ref"] == f"S{index}", "INVALID_FEEDBACK_SOURCE_ORDER")
        sources.append(FeedbackSource(row["ref"], row["text"], SCOPE.profile_id, SCOPE.workspace_id, TASK_ID))
    refs = [source.ref for source in sources]
    focus = case["input"].get("focus", "")
    validate_feedback_input({"source_refs": refs, "focus": focus}, sources, SCOPE, TASK_ID, FEEDBACK_LIMITS)
    sanitized = tuple(FeedbackSource(source.ref, redact_provider_text(source.text),
                                    SCOPE.profile_id, SCOPE.workspace_id, TASK_ID) for source in sources)
    require(any(source.text.replace(REDACTED, "").strip() for source in sanitized), "NO_USABLE_FEEDBACK_TEXT")
    validate_feedback_input({"source_refs": refs, "focus": redact_provider_text(focus)},
                            sanitized, SCOPE, TASK_ID, FEEDBACK_LIMITS)
    return lambda raw: parse_live_feedback(raw, sanitized, SCOPE, TASK_ID, FEEDBACK_LIMITS), {}


def score_case(case, observation, validator):
    validate, actual = validator(case)
    result = {"id": case["id"], "status": "missing_result", "json_valid": None,
              "business_valid": None, "owner_review": None, "latency_ms": None, "usage": None}
    errors = []
    if observation is None:
        return result, errors
    shape(observation, ("id", "raw_output"), ("latency_ms", "usage", "owner_review"))
    if observation.get("owner_review") is not None:
        result["owner_review"] = validate_owner_review(observation["owner_review"])
    if observation.get("latency_ms") is not None:
        result["latency_ms"] = measure(observation["latency_ms"])
    if observation.get("usage") is not None:
        result["usage"] = validate_usage(observation["usage"])
    raw = observation["raw_output"]
    require(raw is None or type(raw) is str, "RAW_OUTPUT_MUST_BE_TEXT_OR_NULL")
    if raw is None:
        result["status"] = "no_output"
        return result, errors
    try:
        _strict_json(raw, FEEDBACK_LIMITS)
    except AIError:
        result.update(status="invalid_json_or_size", json_valid=False, business_valid=False)
        return result, errors
    result["json_valid"] = True
    try:
        output = validate(raw)
    except AIError:
        result.update(status="invalid_schema_or_content", business_valid=False)
        return result, errors
    for estimate in output.get("tasks", []):
        hours = estimate["estimated_hours"]
        ref = estimate["local_ref"]
        if hours is not None and ref in actual:
            errors.append(abs(Decimal(str(hours)) - actual[ref]))
    result.update(status="valid", business_valid=True)
    return result, errors


def summarize(rows, errors):
    scores = [row["owner_review"] for row in rows if row["owner_review"] is not None]
    latencies = [row["latency_ms"] for row in rows if row["latency_ms"] is not None]
    usage = [row["usage"] for row in rows if row["usage"] is not None]
    totals = {}
    for field in ("input_tokens", "output_tokens", "estimated_cost_usd"):
        values = [value[field] for value in usage if value[field] is not None]
        totals[field] = {"observations": len(values), "total": sum(values) if values else None}
    return {"planned_cases": len(rows), "observed_cases": sum(row["status"] != "missing_result" for row in rows),
            "usable_json_cases": sum(row["json_valid"] is True for row in rows),
            "valid_business_cases": sum(row["business_valid"] is True for row in rows),
            "owner_scores": {"reviewed_cases": len(scores),
                             "mean_relevance_0_to_2": sum(row["relevance"] for row in scores) / len(scores) if scores else None,
                             "mean_accuracy_0_to_2": sum(row["accuracy"] for row in scores) / len(scores) if scores else None,
                             "unsupported_claims_cases": sum(row["unsupported_claims"] for row in scores) if scores else None},
            "latency_ms": {"observations": len(latencies), "mean": sum(latencies) / len(latencies) if latencies else None},
            "usage": totals, "estimated_hours_mae": {"matched_estimates": len(errors),
                                                      "hours": sum(errors) / len(errors) if errors else None}}


def evaluate(manifest, outputs, validator, mode):
    shape(manifest, ("cases",))
    shape(outputs, ("mode", "model", "results"))
    require(outputs["mode"] == mode, "RESULT_MODE_MISMATCH")
    model = outputs["model"]
    require(type(model) is str and IDENTIFIER.fullmatch(model), "INVALID_MODEL_LABEL")
    cases = indexed(manifest["cases"])
    results = indexed(outputs["results"])
    require(cases and set(results) <= set(cases), "EMPTY_MANIFEST_OR_UNKNOWN_RESULT_CASE")
    rows = []
    errors = []
    for case_id in sorted(cases):
        row, case_errors = score_case(cases[case_id], results.get(case_id), validator)
        rows.append(row)
        errors.extend(case_errors)
    return {"model": model, "summary": summarize(rows, errors), "cases": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mock", "live"), required=True)
    parser.add_argument("--generator-cases", type=Path, required=True)
    parser.add_argument("--generator-results", type=Path, required=True)
    parser.add_argument("--feedback-cases", type=Path, required=True)
    parser.add_argument("--feedback-results", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args(argv)
    try:
        report = {"version": "ht.ai.eval.v1", "mode": options.mode, "declared_result_provenance": True,
                  "live_provider_calls": 0, "rubric_method": "single_owner"}
        for name, validator, cases, results in (
            ("generator", generator_validator, options.generator_cases, options.generator_results),
            ("feedback", feedback_validator, options.feedback_cases, options.feedback_results),
        ):
            manifest, manifest_hash = read_json(cases)
            saved, results_hash = read_json(results)
            report[name] = evaluate(manifest, saved, validator, options.mode)
            report[name].update(manifest_sha256=manifest_hash, saved_results_sha256=results_hash)
        data = json.dumps(report, sort_keys=True, ensure_ascii=True, indent=2, default=str, allow_nan=False) + "\n"
        if options.output:
            with options.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(data)
        else:
            sys.stdout.write(data)
        return 0
    except EvaluationError as error:
        print(f"Evaluation rejected: {error}", file=sys.stderr)
    except (AIError, OSError, ValueError, UnicodeError, RecursionError):
        print("Evaluation rejected: unreadable file or invalid evaluation input.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
