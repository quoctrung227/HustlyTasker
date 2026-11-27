"""Strict Groq Chat Completions adapter, independent of runtime selection."""

import http.client
import math
import re
import ssl
from dataclasses import dataclass, field

from django.views.decorators.debug import sensitive_variables

from .errors import AIError, ErrorCode
from .openai_adapter import LiveInput, ReportedProviderError, TransportResponse, _decode, _json
from .providers import Feature, ProviderResult, RequestControl, UsageMetadata


_HOST = "api.groq.com"
_PATH = "/openai/v1/chat/completions"
GROQ_CHAT_URL = f"https://{_HOST}{_PATH}"
GROQ_MODEL = "openai/gpt-oss-120b"
_INVALID = ErrorCode.INVALID_PROVIDER_RESPONSE
_SCHEMA_NAME = re.compile(r"[a-zA-Z0-9_-]{1,64}\Z")
_SCHEMA_KEYS = frozenset({"type", "properties", "required", "additionalProperties", "enum", "items", "anyOf"})
_LOCAL_SCHEMA_BOUNDS = frozenset({"minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum"})
_MAX_RETRY_AFTER_SECONDS = 86400


@dataclass(frozen=True, slots=True)
class GroqConfig:
    enabled: bool = False
    model: str = GROQ_MODEL
    timeout_seconds: float = 30.0
    max_input_tokens: int = 4096
    max_output_tokens: int = 1024
    max_response_bytes: int = 131072

    def __post_init__(self):
        if type(self.enabled) is not bool or type(self.model) is not str or self.model != GROQ_MODEL:
            raise AIError(ErrorCode.VALIDATION_ERROR)
        if type(self.timeout_seconds) not in (int, float) or not 0 < self.timeout_seconds <= 120:
            raise AIError(ErrorCode.VALIDATION_ERROR)
        for value, maximum in ((self.max_input_tokens, 65536), (self.max_output_tokens, 4096),
                               (self.max_response_bytes, 1048576)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise AIError(ErrorCode.VALIDATION_ERROR)


@dataclass(frozen=True, slots=True)
class GroqTransportResponse(TransportResponse):
    retry_after: str | None = field(default=None, repr=False)


class GroqRateLimitedError(AIError):
    """Retry-After is advisory. This adapter does not retry or wait."""

    def __init__(self, retry_after):
        super().__init__(ErrorCode.RATE_LIMITED)
        self.retry_after_seconds = None
        if (type(retry_after) is str and 1 <= len(retry_after) <= 5
                and retry_after.isascii() and retry_after.isdecimal()):
            seconds = int(retry_after)
            if seconds <= _MAX_RETRY_AFTER_SECONDS:
                self.retry_after_seconds = seconds


def _wire_schema(schema):
    # These bounds remain enforced by LiveInput.validate after decoding.
    if type(schema) is not dict or schema.keys() - _SCHEMA_KEYS - _LOCAL_SCHEMA_BOUNDS:
        raise AIError(ErrorCode.VALIDATION_ERROR)
    projected = {key: value for key, value in schema.items() if key in _SCHEMA_KEYS}
    if "properties" in projected:
        projected["properties"] = {
            key: _wire_schema(value) for key, value in projected["properties"].items()
        }
    if "items" in projected:
        projected["items"] = _wire_schema(projected["items"])
    if "anyOf" in projected:
        projected["anyOf"] = [_wire_schema(option) for option in projected["anyOf"]]
    return projected


def _reported_usage(value, config):
    if type(value) is not dict:
        raise AIError(_INVALID)
    input_tokens, output_tokens, total = (value.get(name) for name in (
        "prompt_tokens", "completion_tokens", "total_tokens",
    ))
    if (any(type(count) is not int for count in (input_tokens, output_tokens, total))
            or not 1 <= input_tokens <= config.max_input_tokens
            or not 0 <= output_tokens <= config.max_output_tokens
            or total != input_tokens + output_tokens):
        raise AIError(_INVALID)
    details = value.get("completion_tokens_details")
    if details is not None:
        reasoning = details.get("reasoning_tokens") if type(details) is dict else None
        if type(reasoning) is not int or not 0 <= reasoning <= output_tokens:
            raise AIError(_INVALID)
    details = value.get("prompt_tokens_details")
    if details is not None:
        cached = details.get("cached_tokens") if type(details) is dict else None
        if type(cached) is not int or not 0 <= cached <= input_tokens:
            raise AIError(_INVALID)
    # Completion tokens already count reasoning. Actual charges are unknown here.
    return UsageMetadata(input_tokens, output_tokens, None, "provider_reported")


@sensitive_variables()
def _completed_text(envelope):
    choices = envelope.get("choices")
    if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
        raise AIError(_INVALID)
    choice = choices[0]
    index, message = choice.get("index"), choice.get("message")
    if type(index) is not int or index != 0 or type(message) is not dict or message.get("role") != "assistant":
        raise AIError(_INVALID)
    if (envelope.get("mcp_list_tools") or envelope.get("usage_breakdown")
            or any(message.get(key) for key in ("tool_calls", "function_call", "executed_tools", "reasoning"))):
        raise AIError(_INVALID)
    refusal, finish = message.get("refusal"), choice.get("finish_reason")
    if refusal is not None and type(refusal) is not str:
        raise AIError(_INVALID)
    if refusal or finish == "content_filter":
        raise AIError(ErrorCode.AI_REFUSED)
    raw = message.get("content")
    if finish != "stop" or type(raw) is not str or not raw.strip():
        raise AIError(_INVALID)
    return raw


class GroqHttpsTransport:
    """Exactly one direct TLS POST to the pinned Groq endpoint."""

    @sensitive_variables()
    def __init__(self, key):
        if type(key) is not str or not 16 <= len(key) <= 512 or not all(33 <= ord(c) <= 126 for c in key):
            raise AIError(ErrorCode.AI_NOT_CONFIGURED)
        self._key = key

    @sensitive_variables()
    def post(self, *, url, body, timeout_seconds, max_response_bytes, control):
        if url != GROQ_CHAT_URL:
            raise AIError(ErrorCode.PROVIDER_UNAVAILABLE)
        control.check()
        client = http.client.HTTPSConnection(_HOST, timeout=timeout_seconds,
                                             context=ssl.create_default_context())
        try:
            client.request("POST", _PATH, body=body, headers={
                "Authorization": "Bearer " + self._key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            })
            active_socket = client.sock

            def check_timeout():
                control.check()
                if active_socket is not None and control.deadline is not None:
                    remaining = control.deadline - control.clock()
                    if remaining <= 0:
                        raise TimeoutError()
                    active_socket.settimeout(min(timeout_seconds, remaining))

            check_timeout()
            with client.getresponse() as response:
                if response.status != 200:
                    retry_after = response.getheader("Retry-After") if response.status == 429 else None
                    return GroqTransportResponse(response.status, b"", retry_after)
                chunks = []
                remaining_bytes = max_response_bytes + 1
                while remaining_bytes:
                    check_timeout()
                    chunk = response.read1(min(8192, remaining_bytes))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining_bytes -= len(chunk)
                check_timeout()
                return GroqTransportResponse(response.status, b"".join(chunks))
        finally:
            client.close()


class GroqChatCompletionsAdapter:
    def __init__(self, *, config=None, transport=None):
        if config is not None and type(config) is not GroqConfig:
            raise AIError(ErrorCode.VALIDATION_ERROR)
        self._config = config if config is not None else GroqConfig()
        self._transport = transport

    @property
    def max_input_tokens(self):
        return self._config.max_input_tokens

    def _transport_allowed(self):
        return (type(self._transport) is GroqHttpsTransport
                or getattr(self._transport, "offline", None) is True)

    @sensitive_variables()
    def _encode(self, request):
        config = self._config
        if (type(request) is not LiveInput
                or not isinstance(request.feature, Feature) or type(request.data) is not dict
                or type(request.schema_name) is not str or not _SCHEMA_NAME.fullmatch(request.schema_name)
                or type(request.instructions) is not str or not callable(request.validate)):
            raise AIError(ErrorCode.VALIDATION_ERROR)
        try:
            body = _json({
                "model": config.model,
                "messages": [
                    {"role": "system", "content": request.instructions},
                    {"role": "user", "content": _json(request.data)},
                ],
                "response_format": {"type": "json_schema", "json_schema": {
                    "name": request.schema_name, "strict": True, "schema": _wire_schema(request.schema),
                }},
                "max_completion_tokens": config.max_output_tokens,
                "reasoning_effort": "low",
                "include_reasoning": False,
                "stream": False,
            }).encode("utf-8", errors="strict")
        except (AttributeError, TypeError, ValueError, RecursionError):
            raise AIError(ErrorCode.VALIDATION_ERROR) from None
        # Conservatively bound the wire bytes plus provider framing before dispatch.
        if len(body) + 1024 > config.max_input_tokens:
            raise AIError(ErrorCode.VALIDATION_ERROR)
        return body

    @sensitive_variables()
    def generate(self, request: LiveInput, control: RequestControl) -> ProviderResult:
        config, transport = self._config, self._transport
        if not config.enabled or not self._transport_allowed():
            raise AIError(ErrorCode.AI_DISABLED)
        if type(control) is not RequestControl or not callable(getattr(transport, "post", None)):
            raise AIError(ErrorCode.VALIDATION_ERROR)
        control.check()
        body = self._encode(request)
        now = control.clock()
        RequestControl._finite_time(now)
        deadline = min(now + config.timeout_seconds, control.deadline if control.deadline is not None else math.inf)
        bounded = RequestControl(deadline=deadline, is_cancelled=control.is_cancelled, clock=control.clock)
        bounded.check()
        try:
            response = transport.post(url=GROQ_CHAT_URL, body=body, timeout_seconds=deadline - now,
                                      max_response_bytes=config.max_response_bytes, control=bounded)
        except TimeoutError:
            raise AIError(ErrorCode.PROVIDER_TIMEOUT) from None
        except AIError as error:
            raise AIError(error.code) from None
        except Exception:
            raise AIError(ErrorCode.PROVIDER_UNAVAILABLE) from None
        bounded.check()
        if type(response) is not GroqTransportResponse or type(response.status_code) is not int:
            raise AIError(_INVALID)
        if response.status_code == 429:
            raise GroqRateLimitedError(response.retry_after)
        if response.status_code == 408:
            raise AIError(ErrorCode.PROVIDER_TIMEOUT)
        if response.status_code != 200:
            raise AIError(ErrorCode.PROVIDER_UNAVAILABLE)

        envelope = _decode(response.body, config.max_response_bytes)
        if envelope.get("object") != "chat.completion" or envelope.get("model") != config.model or "error" in envelope:
            raise AIError(_INVALID)
        usage = _reported_usage(envelope.get("usage"), config)
        try:
            raw = _completed_text(envelope)
            if not usage.billable_output_tokens:
                raise AIError(_INVALID)
            request.validate(raw)
        except AIError as error:
            raise ReportedProviderError(error.code, usage, config.model) from None
        except Exception:
            raise ReportedProviderError(_INVALID, usage, config.model) from None
        bounded.check()
        return ProviderResult(raw, usage, provider="groq", model=config.model)
