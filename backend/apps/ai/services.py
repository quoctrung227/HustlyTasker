"""Internal fixture orchestration with unimplemented, fail-closed access ports.

These ports are not a second permission engine. A later approved integration
must delegate to existing tenant resolvers/current predicates and authorized
source selectors. DTO identifiers alone never establish authorization.
"""

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from .contracts import FeedbackAnalysis, FeedbackSource, Scope, TaskPlan, ValidationLimits
from .errors import AIError, ErrorCode
from .providers import Feature, FixtureAdapter, ProviderRequest, RequestControl, UsageMetadata
from .validation import (
    parse_feedback_analysis,
    parse_task_plan,
    validate_feedback_input,
    validate_generator_input,
)


class AccessPort(Protocol):
    def authorize(self, scope: Scope, feature: Feature) -> None:
        """Freshly authorize actor/scope/feature; raise AIError on denial.

        Must NOT accept client-constructed role/context DTOs as proof. AI feature
        authority still requires Owner approval; no concrete grant in 02A.
        """
        ...

    def feedback_sources(self, scope: Scope, task_id: UUID) -> tuple[FeedbackSource, ...]:
        """Resolve current readable, nondeleted source text in this exact scope."""
        ...


class DenyAccess:
    def authorize(self, scope: Scope, feature: Feature) -> None:
        raise AIError(ErrorCode.PERMISSION_DENIED)

    def feedback_sources(self, scope: Scope, task_id: UUID) -> tuple[FeedbackSource, ...]:
        raise AIError(ErrorCode.PERMISSION_DENIED)


@dataclass(frozen=True, slots=True)
class FixtureOutcome:
    payload: TaskPlan | FeedbackAnalysis = field(repr=False)
    usage: UsageMetadata
    mode: str = field(default="fixture_demo", init=False)
    generated_by_ai: bool = field(default=False, init=False)
    persisted: bool = field(default=False, init=False)
    fixture_version: str = field(default="fixture.v1", init=False)


class FixtureApplicationService:
    """Opt-in internal fixture runner; not reachable from Django routes/settings.

    No confirmation method, proposal ID, database store or live provider. Numeric
    limits here describe only an offline fixture contract, not approved budgets.
    Cancellation is cooperative; no promise to undo later live provider charges.
    """

    def __init__(self, *, environment: str, enabled: bool = False,
                 access: AccessPort | None = None, adapter: FixtureAdapter | None = None,
                 limits: ValidationLimits | None = None):
        self._adapter = FixtureAdapter(environment=environment) if adapter is None else adapter
        if environment not in ("test", "development") or type(enabled) is not bool:
            raise AIError(ErrorCode.AI_DISABLED)
        # There is intentionally no injection path for a live provider in 02A.
        if type(self._adapter) is not FixtureAdapter:
            raise AIError(ErrorCode.AI_DISABLED)
        if limits is not None and type(limits) is not ValidationLimits:
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("limits",))
        self._enabled = enabled
        self._access = access if access is not None else DenyAccess()
        self._limits = limits if limits is not None else ValidationLimits()

    def _authorize(self, scope, feature, control):
        if type(control) is not RequestControl:
            raise AIError(ErrorCode.VALIDATION_ERROR, fields=("control",))
        control.check()
        if not self._enabled:
            raise AIError(ErrorCode.AI_DISABLED)
        if not isinstance(scope, Scope) or any(
            not isinstance(value, UUID)
            for value in (scope.actor_id, scope.profile_id, scope.workspace_id)
        ):
            raise AIError(ErrorCode.PERMISSION_DENIED)
        if self._access.authorize(scope, feature) is not None:
            raise AIError(ErrorCode.PERMISSION_DENIED)
        control.check()

    def generate(self, *, scope: Scope, payload: dict, control: RequestControl | None = None) -> FixtureOutcome:
        control = control if control is not None else RequestControl()
        try:
            self._authorize(scope, Feature.TASK_PLAN, control)
            validated = validate_generator_input(payload, self._limits)
            result = self._adapter.generate(ProviderRequest(Feature.TASK_PLAN, validated, self._limits), control)
            plan = parse_task_plan(result.raw_json, self._limits)
            self._authorize(scope, Feature.TASK_PLAN, control)
            return FixtureOutcome(plan, result.usage)
        except AIError:
            raise
        except Exception:
            raise AIError(ErrorCode.PROVIDER_UNAVAILABLE) from None

    def analyze(self, *, scope: Scope, task_id: UUID, payload: dict,
                control: RequestControl | None = None) -> FixtureOutcome:
        control = control if control is not None else RequestControl()
        try:
            self._authorize(scope, Feature.FEEDBACK_ANALYSIS, control)
            if not isinstance(task_id, UUID):
                raise AIError(ErrorCode.VALIDATION_ERROR, fields=("task_id",))
            sources = tuple(self._access.feedback_sources(scope, task_id))
            validated = validate_feedback_input(payload, sources, scope, task_id, self._limits)
            result = self._adapter.generate(ProviderRequest(Feature.FEEDBACK_ANALYSIS, validated, self._limits), control)
            analysis = parse_feedback_analysis(result.raw_json, validated.sources, scope, task_id, self._limits)
            self._authorize(scope, Feature.FEEDBACK_ANALYSIS, control)
            current_sources = tuple(self._access.feedback_sources(scope, task_id))
            try:
                current = validate_feedback_input(payload, current_sources, scope, task_id, self._limits)
            except AIError:
                raise AIError(ErrorCode.STALE_CONTEXT) from None
            if current.sources != validated.sources:
                raise AIError(ErrorCode.STALE_CONTEXT)
            return FixtureOutcome(analysis, result.usage)
        except AIError:
            raise
        except Exception:
            raise AIError(ErrorCode.PROVIDER_UNAVAILABLE) from None
