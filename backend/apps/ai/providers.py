"""Provider-independent port and one offline, deterministic fixture adapter."""

import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from time import monotonic
from typing import Protocol

from .contracts import FeedbackInput, GeneratorInput, ValidationLimits
from .errors import AIError, ErrorCode


class Feature(str, Enum):
    TASK_PLAN = "task_plan"
    FEEDBACK_ANALYSIS = "feedback_analysis"


@dataclass(frozen=True, slots=True)
class RequestControl:
    """Cooperative cancellation/monotonic deadline, not a background job."""

    deadline: float | None = None
    is_cancelled: Callable[[], bool] = field(default=lambda: False, repr=False)
    clock: Callable[[], float] = field(default=monotonic, repr=False)

    def __post_init__(self):
        if self.deadline is not None:
            self._finite_time(self.deadline)
        if not callable(self.is_cancelled) or not callable(self.clock):
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("control",))

    @staticmethod
    def _finite_time(value):
        try:
            valid = type(value) in (float, int) and math.isfinite(value) and value >= 0
        except (OverflowError, ValueError):
            valid = False
        if not valid:
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("control",))

    def check(self):
        cancelled = self.is_cancelled()
        if type(cancelled) is not bool:
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("control",))
        if cancelled:
            raise AIError(ErrorCode.CANCELLED)
        if self.deadline is not None:
            now = self.clock()
            self._finite_time(now)
            if now >= self.deadline:
                raise AIError(ErrorCode.PROVIDER_TIMEOUT)


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    feature: Feature
    validated_input: GeneratorInput | FeedbackInput = field(repr=False)
    limits: ValidationLimits = field(repr=False)


@dataclass(frozen=True, slots=True)
class UsageMetadata:
    input_tokens: int | None
    billable_output_tokens: int | None
    cost_usd: Decimal | None
    status: str


@dataclass(frozen=True, slots=True)
class ProviderResult:
    raw_json: str = field(repr=False)
    usage: UsageMetadata
    provider: str = "fixture"
    model: str = "deterministic-fixture-v1"


class StructuredProvider(Protocol):
    """Future adapters must translate SDK types here; no SDK leaks into domain."""

    def generate(self, request: ProviderRequest, control: RequestControl) -> ProviderResult:
        ...


class FixtureScenario(str, Enum):
    VALID = "valid"
    TASK_TREE = "task_tree"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    MALFORMED = "malformed"
    INVALID = "invalid"
    EMPTY = "empty"
    REFUSAL = "refusal"
    UNEXPECTED = "unexpected"


class FixtureAdapter:
    """Explicitly constructed offline fixture, never selected by deployment env.

    Environment is trusted construction input, not an API request parameter.
    This does not infer production safety from Django DEBUG. No live selector
    or adapter exists. Brief/source text is deliberately not transformed.
    """

    def __init__(self, *, environment: str, scenario: FixtureScenario = FixtureScenario.VALID):
        if type(environment) is not str or environment not in ("test", "development"):
            raise AIError(ErrorCode.AI_DISABLED)
        if not isinstance(scenario, FixtureScenario):
            raise AIError(ErrorCode.VALIDATION_ERROR)
        self.scenario = scenario

    def generate(self, request: ProviderRequest, control: RequestControl) -> ProviderResult:
        if type(control) is not RequestControl:
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("control",))
        control.check()
        if not isinstance(request, ProviderRequest):
            raise AIError(ErrorCode.VALIDATION_ERROR)
        if type(request.limits) is not ValidationLimits:
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("limits",))
        expected = GeneratorInput if request.feature is Feature.TASK_PLAN else FeedbackInput
        if not isinstance(request.feature, Feature) or not isinstance(request.validated_input, expected):
            raise AIError(ErrorCode.VALIDATION_ERROR)
        failures = {
            FixtureScenario.UNAVAILABLE: ErrorCode.PROVIDER_UNAVAILABLE,
            FixtureScenario.TIMEOUT: ErrorCode.PROVIDER_TIMEOUT,
            FixtureScenario.REFUSAL: ErrorCode.AI_REFUSED,
        }
        if self.scenario in failures:
            raise AIError(failures[self.scenario])
        if self.scenario is FixtureScenario.UNEXPECTED:
            raise RuntimeError("Synthetic adapter failure; no provider request was made.")
        if self.scenario is FixtureScenario.MALFORMED:
            raw = '{"contract_version":'
        elif self.scenario is FixtureScenario.EMPTY:
            raw = ""
        elif self.scenario is FixtureScenario.INVALID:
            raw = '{"contract_version":"unsupported"}'
        elif request.feature is Feature.TASK_PLAN:
            raw = json.dumps({
                "contract_version": "ai.task-plan.v1",
                "tasks": [{
                    "local_ref": "item_1", "parent_ref": None,
                    "title": "Kiểm tra phụ đề — ví dụ synthetic",
                    "description": "Kiểm tra khả năng đọc phụ đề của video giả lập.",
                    "priority": "MEDIUM", "proposed_deadline": None, "notes": "",
                }],
                "assumptions": [],
                "warnings": ["Demo fixture cố định, không có model AI xử lý brief."],
            }, ensure_ascii=False)
        else:
            # Fixed synthetic text; only citation labels follow the already
            # validated selection. Never inspect or transform source content.
            if not request.validated_input.sources:
                raise AIError(ErrorCode.VALIDATION_ERROR, fields=("source_refs",))
            source_ref = request.validated_input.sources[0].ref
            raw = json.dumps({
                "contract_version": "ai.feedback.v1",
                "summary": "Ví dụ synthetic: kiểm tra độ tương phản phụ đề.",
                "issues": [{"category": "TECHNICAL", "description": "Ví dụ về khả năng đọc.", "source_refs": [source_ref]}],
                "suggested_actions": [{"action": "Kiểm tra tương phản phụ đề.", "priority": "MEDIUM", "rationale": "Gợi ý synthetic cố định.", "source_refs": [source_ref]}],
                "uncertainty": "Không phân tích nội dung nguồn bằng model; chỉ fixture synthetic.",
                "warnings": ["Demo fixture — không gọi AI."],
            }, ensure_ascii=False)
        if self.scenario is FixtureScenario.TASK_TREE and request.feature is Feature.TASK_PLAN:
            tree = json.loads(raw)
            tree["tasks"].append({
                "local_ref": "item_2", "parent_ref": "item_1",
                "title": "Kiểm tra tương phản — subtask synthetic",
                "description": "Kiểm tra trên nền sáng trong ví dụ mô phỏng.",
                "priority": "MEDIUM", "proposed_deadline": None, "notes": "",
            })
            raw = json.dumps(tree, ensure_ascii=False)
        control.check()
        return ProviderResult(raw, UsageMetadata(0, 0, Decimal("0"), "fixture_zero"))
