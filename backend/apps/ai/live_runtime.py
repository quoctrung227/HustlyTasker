"""Explicit live configuration, readiness and direct HTTPS transport."""

import http.client
import os
import ssl
from decimal import Decimal

from django.conf import settings
from django.db import DatabaseError, connection
from django.db.migrations.recorder import MigrationRecorder
from django.views.decorators.debug import sensitive_variables

from .errors import AIError, ErrorCode
from .groq_adapter import GROQ_MODEL, GroqChatCompletionsAdapter, GroqConfig, GroqHttpsTransport
from .openai_adapter import (
    RESPONSES_URL, LiveOpenAIResponsesAdapter, OpenAIConfig, TransportResponse,
)

SUPPORTED_MODELS = frozenset(("gpt-5.4-mini", "gpt-5.4-mini-2026-03-17"))
INPUT_RATE = Decimal("0.75")
OUTPUT_RATE = Decimal("4.50")
PRICING_VERSION = "openai-2026-11-21"
GROQ_INPUT_RATE = Decimal("0.15")
GROQ_OUTPUT_RATE = Decimal("0.60")
GROQ_PRICING_VERSION = "groq-reference-2026-11-27"
REQUIRED_MIGRATIONS = frozenset({
    ("ai", "0002_dispatch_governance"), ("ai", "0003_proposal_rejection"),
    ("tasks", "0007_task_estimated_hours"),
})
GROQ_REQUIRED_MIGRATIONS = REQUIRED_MIGRATIONS | {("ai", "0004_groq_governance")}


def live_selected():
    return getattr(settings, "AI_LIVE_ENABLED", False) is True


def selected_mode():
    if not live_selected():
        return None
    provider = settings.AI_PROVIDER
    return {"groq": "GROQ_LIVE", "openai": "OPENAI_LIVE"}.get(provider)


@sensitive_variables()
def _key_from_environment(variable):
    key = os.environ.get(variable, "")
    if 16 <= len(key) <= 512 and key.isascii() and all(33 <= ord(c) <= 126 for c in key):
        return key
    return None


def _api_key():
    return _key_from_environment("OPENAI_API_KEY")


def _groq_api_key():
    return _key_from_environment("GROQ_API_KEY")


def _selected_model(mode):
    return settings.AI_MODEL or (GROQ_MODEL if mode == "GROQ_LIVE" else settings.AI_OPENAI_MODEL)


def availability_reason():
    if not live_selected():
        return ErrorCode.AI_DISABLED.value
    mode = selected_mode()
    if mode == "GROQ_LIVE":
        if (settings.AI_GROQ_FREE_TIER_CONFIRMED is not True
                or _selected_model(mode) != GROQ_MODEL or not _groq_api_key()):
            return ErrorCode.AI_NOT_CONFIGURED.value
        required = GROQ_REQUIRED_MIGRATIONS
    elif mode == "OPENAI_LIVE":
        if (settings.AI_CONTROLLED_LIVE is True
                or _selected_model(mode) not in SUPPORTED_MODELS or not _api_key()):
            return ErrorCode.AI_NOT_CONFIGURED.value
        required = REQUIRED_MIGRATIONS
    else:
        return ErrorCode.AI_NOT_CONFIGURED.value
    try:
        if required <= set(MigrationRecorder(connection).applied_migrations()):
            return None
    except DatabaseError:
        return ErrorCode.PROVIDER_UNAVAILABLE.value
    return ErrorCode.AI_MIGRATION_REQUIRED.value


class OpenAIHttpsTransport:
    """One POST to the fixed API host, with TLS validation and no redirects."""

    offline = False

    @sensitive_variables()
    def __init__(self, key):
        self._key = key

    @sensitive_variables()
    def post(self, *, url, body, timeout_seconds, max_response_bytes, control):
        if url != RESPONSES_URL:
            raise AIError(ErrorCode.PROVIDER_UNAVAILABLE)
        control.check()
        client = http.client.HTTPSConnection("api.openai.com", timeout=timeout_seconds,
                                            context=ssl.create_default_context())
        try:
            client.request("POST", "/v1/responses", body=body, headers={
                "Authorization": "Bearer " + self._key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            })
            control.check()
            active_socket = client.sock
            if active_socket is not None:
                active_socket.settimeout(min(timeout_seconds, control.deadline - control.clock()))
            response = client.getresponse()
            if response.status != 200:
                return TransportResponse(response.status, b"")
            with response:
                chunks = []
                remaining = max_response_bytes + 1
                while remaining:
                    control.check()
                    if active_socket is not None:
                        active_socket.settimeout(min(timeout_seconds, control.deadline - control.clock()))
                    chunk = response.read1(min(8192, remaining))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                control.check()
                return TransportResponse(response.status, b"".join(chunks))
        finally:
            client.close()


@sensitive_variables()
def live_runtime():
    from .governance import BudgetLimits, GovernancePolicy

    if reason := availability_reason():
        raise AIError(ErrorCode(reason))
    mode = selected_mode()
    model = _selected_model(mode)
    if mode == "GROQ_LIVE":
        key = _groq_api_key()
        if key is None:
            raise AIError(ErrorCode.AI_NOT_CONFIGURED)
        controlled = settings.AI_CONTROLLED_LIVE is True
        input_limit = settings.AI_GROQ_MAX_INPUT_TOKENS
        output_limit = settings.AI_GROQ_MAX_OUTPUT_TOKENS
        if controlled:
            input_limit = min(input_limit, 4096)
            output_limit = min(output_limit, 1024)
        policy = GovernancePolicy(
            enabled=True, provider="groq", execution_mode=mode, model=model,
            config_version="groq-live-v1", pricing_version=GROQ_PRICING_VERSION,
            budget_version="groq-free-controlled-v1" if controlled else "groq-free-v1",
            max_input_tokens=input_limit,
            max_output_tokens=output_limit, input_rate_per_million=GROQ_INPUT_RATE,
            output_rate_per_million=GROQ_OUTPUT_RATE, controlled_live=controlled,
            groq_requests_per_minute=settings.AI_GROQ_REQUESTS_PER_MINUTE,
            groq_requests_per_day=settings.AI_GROQ_REQUESTS_PER_DAY,
            groq_tokens_per_minute=settings.AI_GROQ_TOKENS_PER_MINUTE,
            groq_tokens_per_day=settings.AI_GROQ_TOKENS_PER_DAY,
            global_limits=BudgetLimits(request_limit=settings.AI_GLOBAL_REQUEST_LIMIT, concurrency_limit=3),
            profile_limits=BudgetLimits(request_limit=settings.AI_PROFILE_REQUEST_LIMIT, concurrency_limit=2),
            user_limits=BudgetLimits(request_limit=settings.AI_USER_REQUEST_LIMIT, concurrency_limit=1),
        )
        adapter = GroqChatCompletionsAdapter(
            config=GroqConfig(enabled=True, model=model, max_input_tokens=input_limit,
                              max_output_tokens=output_limit, timeout_seconds=settings.AI_GROQ_TIMEOUT_SECONDS),
            transport=GroqHttpsTransport(key),
        )
        return policy, adapter
    if mode != "OPENAI_LIVE":
        raise AIError(ErrorCode.AI_NOT_CONFIGURED)
    policy = GovernancePolicy(
        enabled=True, execution_mode=mode, model=model,
        config_version="live-mvp-v1", pricing_version=PRICING_VERSION,
        budget_version="live-mvp-v1", max_input_tokens=settings.AI_MAX_INPUT_TOKENS,
        max_output_tokens=settings.AI_MAX_OUTPUT_TOKENS, input_rate_per_million=INPUT_RATE,
        output_rate_per_million=OUTPUT_RATE,
        global_limits=BudgetLimits(settings.AI_GLOBAL_BUDGET_USD, settings.AI_GLOBAL_REQUEST_LIMIT, 3),
        profile_limits=BudgetLimits(settings.AI_PROFILE_BUDGET_USD, settings.AI_PROFILE_REQUEST_LIMIT, 2),
        user_limits=BudgetLimits(settings.AI_USER_BUDGET_USD, settings.AI_USER_REQUEST_LIMIT, 1),
    )
    key = _api_key()
    if key is None:
        raise AIError(ErrorCode.AI_NOT_CONFIGURED)
    adapter = LiveOpenAIResponsesAdapter(
        config=OpenAIConfig(enabled=True, model=policy.model,
                            max_output_tokens=policy.max_output_tokens,
                            timeout_seconds=settings.AI_OPENAI_TIMEOUT_SECONDS),
        transport=OpenAIHttpsTransport(key), max_input_tokens=policy.max_input_tokens,
    )
    return policy, adapter
