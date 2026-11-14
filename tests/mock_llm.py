"""
테스트용 가짜 LLM 서버
======================
Gemini(:generateContent)와 OpenAI 호환(/chat/completions) 엔드포인트를 흉내 냅니다.
실제 API 키 없이 폴백·백오프·거짓 성공 방지 로직을 검증하기 위한 것입니다.

사용:
    from mock_llm import MockLLM
    server = MockLLM({
        "gemini-3.5-flash-lite": [(200, {"text": "hello"})],
    })
    server.url  # http://127.0.0.1:PORT  (GEMINI_API_BASE 로 지정)
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def gemini_ok(text: str, finish: str = "STOP") -> dict:
    return {
        "candidates": [
            {"content": {"parts": [{"text": text}], "role": "model"}, "finishReason": finish}
        ]
    }


def openai_ok(text: str, finish: str = "stop") -> dict:
    return {
        "choices": [{"message": {"content": text}, "finish_reason": finish, "index": 0}]
    }


def gemini_429(retry_delay: str = "1s") -> dict:
    return {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "message": "Quota exceeded for metric: generate_content_free_tier_requests, limit: 15",
            "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo",
                         "retryDelay": retry_delay}],
        }
    }


def gemini_404(model: str) -> dict:
    return {"error": {"code": 404, "status": "NOT_FOUND",
                      "message": f"models/{model} is not found for API version v1beta"}}


def gemini_blocked() -> dict:
    return {"promptFeedback": {"blockReason": "SAFETY"}}


class MockLLM:
    """모델별 응답 시퀀스를 돌려주는 로컬 HTTP 서버."""

    def __init__(self, responses: dict[str, list[tuple[int, dict]]]):
        self.responses = {k: list(v) for k, v in responses.items()}
        self.hits: list[dict] = []
        self._lock = threading.Lock()
        mock = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):  # 테스트 출력 조용히
                pass

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    body = {}
                model = mock._model_for(self.path, body)
                with mock._lock:
                    mock.hits.append({"path": self.path, "model": model, "body": body})
                    status, payload = mock._next(model)
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}"

    @staticmethod
    def _model_for(path: str, body: dict) -> str:
        if ":generateContent" in path:
            return path.split("/models/")[1].split(":")[0]
        return body.get("model", "unknown")

    def _next(self, model: str) -> tuple[int, dict]:
        queue = self.responses.get(model)
        if not queue:
            queue = self.responses.get("*")
        if not queue:
            return 200, gemini_ok("default mock response")
        if len(queue) > 1:
            return queue.pop(0)
        return queue[0]

    def count(self, model: str | None = None) -> int:
        if model is None:
            return len(self.hits)
        return sum(1 for h in self.hits if h["model"] == model)

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
