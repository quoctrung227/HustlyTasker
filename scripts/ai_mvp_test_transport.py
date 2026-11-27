"""Deterministic provider wire envelopes for the owned browser test server."""

import json

from apps.ai.contracts import ISSUE_CATEGORIES
from apps.ai.groq_adapter import GROQ_CHAT_URL, GROQ_MODEL, GroqTransportResponse
from apps.ai.openai_adapter import TransportResponse


class BrowserFakeTransport:
    offline = False

    def __init__(self, _key):
        pass

    def post(self, *, url, body, timeout_seconds, max_response_bytes, control):
        control.check()
        request = json.loads(body)
        data = json.loads(request["input"][1]["content"][0]["text"])
        name = request["text"]["format"]["name"]
        output = _synthetic_output(name, data)
        return TransportResponse(200, json.dumps({
            "object": "response", "status": "completed", "model": request["model"],
            "output": [{"type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": json.dumps(output)}]}],
            "usage": {"input_tokens": 150, "output_tokens": 75, "total_tokens": 225},
        }).encode())


def unexpected_ai_transport(self, **kwargs):
    raise AssertionError("An unselected provider cannot be used by the isolated browser runner.")


def groq_browser_post(self, *, url, body, timeout_seconds, max_response_bytes, control):
    control.check()
    request = json.loads(body)
    response_schema = request["response_format"]
    if (url != GROQ_CHAT_URL or request["model"] != GROQ_MODEL
            or request["stream"] or request["include_reasoning"] or "tools" in request
            or response_schema["type"] != "json_schema" or response_schema["json_schema"]["strict"] is not True):
        raise AssertionError("Unexpected isolated Groq wire contract.")
    data = json.loads(request["messages"][1]["content"])
    output = _synthetic_output(response_schema["json_schema"]["name"], data)
    return GroqTransportResponse(200, json.dumps({
        "object": "chat.completion", "model": request["model"],
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": json.dumps(output)}}],
        "usage": {"prompt_tokens": 150, "completion_tokens": 75, "total_tokens": 225,
                  "completion_tokens_details": {"reasoning_tokens": 25}},
    }).encode())


def _synthetic_output(name, data):
    if name == "hustlytasker_live_task_plan_v1":
        return {
            "tasks": [{"title": f"Công việc kiểm thử AI {i + 1}",
                       "description": "Mô tả kiểm thử từ transport giả.",
                       "priority": "MEDIUM", "estimated_hours": 2}
                      for i in range(data["task_count"] or 2)],
            "assumptions": [], "warnings": [],
        }
    if name != "hustlytasker_feedback_v2":
        raise RuntimeError("Unexpected isolated AI schema.")
    source = data["sources"][0]
    return {
        "contract_version": "ai.feedback.v2", "summary": "Tóm tắt kiểm thử AI",
        "issues": [{"category": ISSUE_CATEGORIES[0], "description": "Kiểm tra nguồn phản hồi.",
                    "severity": "MEDIUM", "source_refs": [source["ref"]],
                    "evidence": [{"source_ref": source["ref"], "quote": source["text"][:80].strip()}]}],
        "suggested_actions": [{"action": "Kiểm tra lại phản hồi", "priority": "MEDIUM",
                               "rationale": "", "source_refs": [source["ref"]]}],
        "uncertainty": "", "warnings": [],
    }
