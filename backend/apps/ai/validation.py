"""Strict, bounded contract parsing without coercion, logging, ORM or network."""

import json
import re
from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .contracts import (
    FEEDBACK_VERSION, ISSUE_CATEGORIES, PRIORITIES, TASK_PLAN_VERSION,
    FeedbackAnalysis, FeedbackInput, FeedbackIssue, FeedbackSource,
    GeneratorInput, Scope, SuggestedAction, TaskNode, TaskPlan, ValidationLimits,
)
from .errors import AIError, ErrorCode


_LOCAL_REF = re.compile(r"item_[1-9][0-9]{0,2}\Z")
_SOURCE_REF = re.compile(r"S[1-9][0-9]?\Z")
_DATETIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z"
)


def _fail(code, field):
    # Every field name is a code-owned constant, never an untrusted JSON key.
    raise AIError(code, fields=(field,)) from None


def _text(value, *, field, maximum, code, required=False):
    if type(value) is not str or len(value) > maximum:
        _fail(code, field)
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        _fail(code, field)
    if "\x00" in value or (required and not value.strip()):
        _fail(code, field)
    return value


def _object(value, *, fields, required=None, code, path):
    if type(value) is not dict:
        _fail(code, path)
    if any(type(key) is not str for key in value):
        _fail(code, path)
    if set(value) - set(fields) or set(fields if required is None else required) - set(value):
        _fail(code, path)
    return value


def _array(value, *, field, minimum=0, maximum, code):
    if type(value) is not list or not minimum <= len(value) <= maximum:
        _fail(code, field)
    return value


def _enum(value, allowed, *, field, code):
    if type(value) is not str or value not in allowed:
        _fail(code, field)
    return value


def _deadline(value, *, field, code):
    if value is None:
        return None
    if type(value) is not str or not _DATETIME.fullmatch(value):
        _fail(code, field)
    if not value.endswith("Z"):
        offset = value[-6:]
        if int(offset[1:3]) > 23 or int(offset[4:6]) > 59:
            _fail(code, field)
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.utcoffset() is None:
            _fail(code, field)
        return date.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        _fail(code, field)


def _request_size(value, limits):
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        _fail(ErrorCode.VALIDATION_ERROR, "request")
    if len(encoded) > limits.max_request_bytes:
        _fail(ErrorCode.VALIDATION_ERROR, "request")


def _strict_json(raw, limits):
    code = ErrorCode.INVALID_PROVIDER_RESPONSE
    if type(raw) is not str:
        _fail(code, "response")
    # Pre-check characters before encoding to bound any temporary allocation.
    if len(raw) > limits.max_response_bytes:
        _fail(code, "response")
    try:
        encoded = raw.encode("utf-8", errors="strict")
        if len(encoded) > limits.max_response_bytes:
            _fail(code, "response")

        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError()
                result[key] = value
            return result

        def reject_constant(value):
            raise ValueError()

        value = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (ValueError, UnicodeEncodeError, RecursionError):
        _fail(code, "response")
    return value


def validate_generator_input(data, limits: ValidationLimits):
    code = ErrorCode.VALIDATION_ERROR
    _object(data, fields=("brief", "target_deadline", "reference_time", "timezone"),
            required=("brief",), code=code, path="request")
    brief = _text(data["brief"], field="brief", maximum=limits.max_brief_chars,
                  code=code, required=True)
    deadline = _deadline(data.get("target_deadline"), field="target_deadline", code=code)
    reference = _deadline(data.get("reference_time"), field="reference_time", code=code)
    name = data.get("timezone")
    if name is not None:
        _text(name, field="timezone", maximum=128, code=code, required=True)
        try:
            ZoneInfo(name)
        except (ValueError, ZoneInfoNotFoundError):
            _fail(code, "timezone")
    _request_size(data, limits)
    return GeneratorInput(brief, deadline, reference, name)


def _sources(sources, scope, task_id, limits, code):
    if type(scope) is not Scope or type(task_id) is not UUID:
        _fail(code, "sources")
    if type(sources) not in (tuple, list) or not 1 <= len(sources) <= limits.max_sources:
        _fail(code, "sources")
    result = {}
    total = 0
    for source in sources:
        if type(source) is not FeedbackSource:
            _fail(code, "sources")
        if (type(source.ref) is not str or not _SOURCE_REF.fullmatch(source.ref)
                or source.ref in result or source.deleted is not False
                or type(source.profile_id) is not UUID
                or type(source.workspace_id) is not UUID
                or type(source.task_id) is not UUID
                or source.profile_id != scope.profile_id
                or source.workspace_id != scope.workspace_id or source.task_id != task_id):
            _fail(code, "sources")
        _text(source.text, field="sources", maximum=limits.max_source_chars,
              code=code, required=True)
        total += len(source.text)
        if total > limits.max_source_chars:
            _fail(code, "sources")
        result[source.ref] = source
    return result


def validate_feedback_input(data, sources, scope, task_id, limits: ValidationLimits):
    code = ErrorCode.VALIDATION_ERROR
    _object(data, fields=("source_refs", "focus"), required=("source_refs",),
            code=code, path="request")
    available = _sources(sources, scope, task_id, limits, code)
    refs = _citations(data["source_refs"], available, limits.max_sources, code)
    focus = _text(data.get("focus", ""), field="focus", maximum=1000, code=code)
    _request_size(data, limits)
    return FeedbackInput(tuple(available[ref] for ref in refs), focus)


def _strings(value, *, field, code):
    values = _array(value, field=field, maximum=10, code=code)
    return tuple(_text(item, field=field, maximum=300, code=code) for item in values)


def parse_task_plan(raw, limits: ValidationLimits):
    code = ErrorCode.INVALID_PROVIDER_RESPONSE
    data = _strict_json(raw, limits)
    _object(data, fields=("contract_version", "tasks", "assumptions", "warnings"),
            code=code, path="response")
    _enum(data["contract_version"], (TASK_PLAN_VERSION,), field="contract_version", code=code)
    nodes = []
    refs = {}
    for item in _array(data["tasks"], field="tasks", minimum=1, maximum=limits.max_tasks, code=code):
        _object(item, fields=("local_ref", "parent_ref", "title", "description", "priority",
                              "proposed_deadline", "notes"), code=code, path="tasks")
        ref = item["local_ref"]
        parent = item["parent_ref"]
        if type(ref) is not str or not _LOCAL_REF.fullmatch(ref) or ref in refs:
            _fail(code, "local_ref")
        if parent is not None and (type(parent) is not str or not _LOCAL_REF.fullmatch(parent)):
            _fail(code, "parent_ref")
        node = TaskNode(
            ref, parent,
            _text(item["title"], field="title", maximum=255, code=code, required=True),
            _text(item["description"], field="description", maximum=2000, code=code),
            _enum(item["priority"], PRIORITIES, field="priority", code=code),
            _deadline(item["proposed_deadline"], field="proposed_deadline", code=code),
            _text(item["notes"], field="notes", maximum=500, code=code),
        )
        nodes.append(node)
        refs[ref] = node
    for node in nodes:
        visited = set()
        current = node
        depth = 0
        while current.parent_ref is not None:
            if current.local_ref in visited or current.parent_ref not in refs:
                _fail(code, "parent_ref")
            visited.add(current.local_ref)
            current = refs[current.parent_ref]
            depth += 1
            if depth > limits.max_depth:
                _fail(code, "parent_ref")
    return TaskPlan(TASK_PLAN_VERSION, tuple(nodes),
                    _strings(data["assumptions"], field="assumptions", code=code),
                    _strings(data["warnings"], field="warnings", code=code))


def _citations(value, sources, maximum, code):
    refs = _array(value, field="source_refs", minimum=1, maximum=maximum, code=code)
    if any(type(ref) is not str or ref not in sources for ref in refs):
        _fail(code, "source_refs")
    if len(set(refs)) != len(refs):
        _fail(code, "source_refs")
    return tuple(refs)


def parse_feedback_analysis(raw, sources, scope, task_id, limits: ValidationLimits):
    code = ErrorCode.INVALID_PROVIDER_RESPONSE
    available = _sources(sources, scope, task_id, limits, code)
    data = _strict_json(raw, limits)
    _object(data, fields=("contract_version", "summary", "issues", "suggested_actions",
                          "uncertainty", "warnings"), code=code, path="response")
    _enum(data["contract_version"], (FEEDBACK_VERSION,), field="contract_version", code=code)
    summary = _text(data["summary"], field="summary", maximum=1600, code=code, required=True)
    issues = []
    for item in _array(data["issues"], field="issues", maximum=10, code=code):
        _object(item, fields=("category", "description", "source_refs"), code=code, path="issues")
        issues.append(FeedbackIssue(
            _enum(item["category"], ISSUE_CATEGORIES, field="category", code=code),
            _text(item["description"], field="description", maximum=500, code=code, required=True),
            _citations(item["source_refs"], available, 5, code),
        ))
    actions = []
    for item in _array(data["suggested_actions"], field="suggested_actions", maximum=10, code=code):
        _object(item, fields=("action", "priority", "rationale", "source_refs"),
                code=code, path="suggested_actions")
        actions.append(SuggestedAction(
            _text(item["action"], field="action", maximum=500, code=code, required=True),
            _enum(item["priority"], PRIORITIES, field="priority", code=code),
            _text(item["rationale"], field="rationale", maximum=300, code=code),
            _citations(item["source_refs"], available, 5, code),
        ))
    return FeedbackAnalysis(
        FEEDBACK_VERSION, summary, tuple(issues), tuple(actions),
        _text(data["uncertainty"], field="uncertainty", maximum=600, code=code),
        _strings(data["warnings"], field="warnings", code=code),
    )
