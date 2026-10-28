"""Static errors safe to expose without confidential payloads or provider text."""

from enum import Enum


class ErrorCode(str, Enum):
    AI_DISABLED = "AI_DISABLED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    INVALID_PROVIDER_RESPONSE = "INVALID_PROVIDER_RESPONSE"
    RATE_LIMITED = "RATE_LIMITED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    STALE_CONTEXT = "STALE_CONTEXT"
    CANCELLED = "CANCELLED"
    AI_REFUSED = "AI_REFUSED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    ALREADY_CONFIRMED = "ALREADY_CONFIRMED"
    STALE_PROPOSAL = "STALE_PROPOSAL"
    EXPIRED = "EXPIRED"
    RECOVERY_EXPIRED = "RECOVERY_EXPIRED"


_MESSAGES = {
    ErrorCode.AI_DISABLED: "AI processing is disabled for this operation.",
    ErrorCode.VALIDATION_ERROR: "The supplied input is not valid.",
    ErrorCode.PROVIDER_UNAVAILABLE: "The provider is unavailable.",
    ErrorCode.PROVIDER_TIMEOUT: "The provider deadline was exceeded.",
    ErrorCode.INVALID_PROVIDER_RESPONSE: "The provider response is not valid.",
    ErrorCode.RATE_LIMITED: "The request limit was reached.",
    ErrorCode.BUDGET_EXCEEDED: "The configured spending limit was reached.",
    ErrorCode.PERMISSION_DENIED: "The operation is not authorized.",
    ErrorCode.STALE_CONTEXT: "The authorized context has changed.",
    ErrorCode.CANCELLED: "The operation was cancelled.",
    ErrorCode.AI_REFUSED: "No usable proposal was returned.",
    ErrorCode.IDEMPOTENCY_CONFLICT: "This request key was already used for a different operation body.",
    ErrorCode.ALREADY_CONFIRMED: "This proposal has already been confirmed.",
    ErrorCode.STALE_PROPOSAL: "The proposal revision is no longer current.",
    ErrorCode.EXPIRED: "The proposal is no longer available for confirmation.",
    ErrorCode.RECOVERY_EXPIRED: "The confirmation recovery window has ended.",
}

_FIELD_NAMES = frozenset({
    "brief", "target_deadline", "reference_time", "timezone", "source_refs",
    "focus", "sources", "scope", "task_id", "contract_version", "tasks",
    "local_ref", "parent_ref", "title", "description", "priority",
    "proposed_deadline", "notes", "assumptions", "warnings", "summary",
    "issues", "suggested_actions", "uncertainty", "category", "action",
    "rationale", "limits", "control", "scenario_id", "payload",
    "proposal_revision", "confirmed", "idempotency_key",
})


class AIError(Exception):
    """No caller-controlled text, unknown field names or identifiers in errors."""

    def __init__(self, code: ErrorCode, *, fields: tuple[str, ...] = ()):
        if not isinstance(code, ErrorCode):
            code = ErrorCode.INVALID_PROVIDER_RESPONSE
        self.code = code
        self.message = _MESSAGES[code]
        self.fields = tuple(sorted({
            name for name in fields if type(name) is str and name in _FIELD_NAMES
        }))
        super().__init__(self.message)

    def __repr__(self):
        return f"AIError(code={self.code.value!r}, fields={self.fields!r})"

    def as_public_error(self):
        """Transport-neutral data; HTTP/client mapping is a future code slice."""
        return {"code": self.code.value, "message": self.message, "fields": self.fields}
