"""Deterministic OpenAI wire envelopes for the owned browser test server."""

import json

from apps.ai.contracts import ISSUE_CATEGORIES
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
        if name == "hustlytasker_live_task_plan_v1":
            output = {
                "tasks": [{"title": f"Công việc kiểm thử AI {i + 1}",
                           "description": "Mô tả kiểm thử từ transport giả.",
                           "priority": "MEDIUM", "estimated_hours": 2}
                          for i in range(data["task_count"] or 2)],
                "assumptions": [], "warnings": [],
            }
        elif name == "hustlytasker_feedback_v2":
            source = data["sources"][0]
            output = {
                "contract_version": "ai.feedback.v2", "summary": "Tóm tắt kiểm thử AI",
                "issues": [{"category": ISSUE_CATEGORIES[0], "description": "Kiểm tra nguồn phản hồi.",
                            "severity": "MEDIUM", "source_refs": [source["ref"]],
                            "evidence": [{"source_ref": source["ref"], "quote": source["text"][:80].strip()}]}],
                "suggested_actions": [{"action": "Kiểm tra lại phản hồi", "priority": "MEDIUM",
                                       "rationale": "", "source_refs": [source["ref"]]}],
                "uncertainty": "", "warnings": [],
            }
        else:
            raise RuntimeError("Unexpected isolated AI schema.")
        return TransportResponse(200, json.dumps({
            "object": "response", "status": "completed", "model": request["model"],
            "output": [{"type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": json.dumps(output)}]}],
            "usage": {"input_tokens": 150, "output_tokens": 75, "total_tokens": 225},
        }).encode())
