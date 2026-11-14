"""
llm.py 단위 테스트 (표준 라이브러리 unittest + 로컬 가짜 서버)
=============================================================
실행:
    python -m unittest discover -s tests -v

실제 Gemini/Groq 키 없이 다음을 검증합니다.
  1. Gemini 정상 호출 (요청 본문 형태 포함)
  2. 429 → RetryInfo.retryDelay 대기 후 재시도 성공
  3. 모델 404 → 다음 모델로 폴백
  4. Gemini 전부 실패 → Groq 폴백
  5. 모두 실패 → LLMError (조용한 실패 없음)
  6. 키 없음 → NoProviderError
  7. 빈 응답(MAX_TOKENS)은 재시도 대상
  8. 지원하지 않는 필드 400 → 필드 제거 후 재시도
  9. JSON 모드 · extract_json
"""

import os
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import llm  # noqa: E402
from llm import complete, extract_json, LLMError, NoProviderError  # noqa: E402
from mock_llm import (  # noqa: E402
    MockLLM,
    gemini_ok,
    gemini_429,
    gemini_404,
    gemini_blocked,
    openai_ok,
)

ENV_KEYS = [
    "GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_API_BASE", "GEMINI_MIN_INTERVAL",
    "GROQ_API_KEY", "GROQ_MODEL", "GROQ_API_BASE",
    "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "OPENROUTER_API_BASE",
    "LLM_PROVIDER_ORDER", "LLM_MAX_RETRIES", "LLM_MAX_BACKOFF", "LLM_TIMEOUT",
]


class LLMTestBase(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ENV_KEYS}
        for key in ENV_KEYS:
            os.environ.pop(key, None)
        os.environ["LLM_MAX_BACKOFF"] = "2"
        os.environ["GEMINI_MIN_INTERVAL"] = "0"
        llm._LAST_CALL.clear()
        self.servers: list[MockLLM] = []

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for server in self.servers:
            server.close()

    def mock(self, responses) -> MockLLM:
        server = MockLLM(responses)
        self.servers.append(server)
        return server


class GeminiTests(LLMTestBase):
    def test_success_and_request_shape(self):
        server = self.mock({"gemini-3.5-flash-lite": [(200, gemini_ok("hello world"))]})
        os.environ["GEMINI_API_KEY"] = "test-key-123456"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"

        text = complete(
            [{"role": "system", "content": "be nice"},
             {"role": "user", "content": "hi"}],
            max_tokens=64, temperature=0.2, json_mode=True,
        )
        self.assertEqual(text, "hello world")
        hit = server.hits[0]
        self.assertIn("/v1beta/models/gemini-3.5-flash-lite:generateContent", hit["path"])
        body = hit["body"]
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], "be nice")
        self.assertEqual(body["contents"][0]["role"], "user")
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 64)
        self.assertEqual(body["generationConfig"]["responseMimeType"], "application/json")
        self.assertIn("thinkingConfig", body["generationConfig"])

    def test_assistant_role_becomes_model(self):
        server = self.mock({"gemini-3.5-flash-lite": [(200, gemini_ok("ok"))]})
        os.environ["GEMINI_API_KEY"] = "k-123456"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
        complete([
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
        ], max_tokens=32)
        roles = [c["role"] for c in server.hits[0]["body"]["contents"]]
        self.assertEqual(roles, ["user", "model", "user"])

    def test_429_then_success(self):
        server = self.mock({
            "gemini-3.5-flash-lite": [(429, gemini_429("1s")), (200, gemini_ok("second try"))]
        })
        os.environ["GEMINI_API_KEY"] = "k-123456"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
        os.environ["LLM_MAX_RETRIES"] = "2"

        started = time.monotonic()
        text = complete([{"role": "user", "content": "hi"}], max_tokens=32)
        elapsed = time.monotonic() - started
        self.assertEqual(text, "second try")
        self.assertEqual(server.count("gemini-3.5-flash-lite"), 2)
        self.assertGreaterEqual(elapsed, 0.9)  # retryDelay를 기다렸는지

    def test_model_404_falls_to_next_model(self):
        server = self.mock({
            "gemini-3.5-flash-lite": [(404, gemini_404("gemini-3.5-flash-lite"))],
            "gemini-3.1-flash-lite": [(200, gemini_ok("fallback model"))],
        })
        os.environ["GEMINI_API_KEY"] = "k-123456"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
        self.assertEqual(complete("hi", max_tokens=32), "fallback model")

    def test_blocked_prompt_is_fatal_then_next_target(self):
        server = self.mock({
            "gemini-3.5-flash-lite": [(200, gemini_blocked())],
            "gemini-3.1-flash-lite": [(200, gemini_ok("fine"))],
        })
        os.environ["GEMINI_API_KEY"] = "k-123456"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
        self.assertEqual(complete("hi", max_tokens=32), "fine")

    def test_max_tokens_empty_is_retried(self):
        server = self.mock({
            "gemini-3.5-flash-lite": [
                (200, gemini_ok("", finish="MAX_TOKENS")),
                (200, gemini_ok("filled")),
            ]
        })
        os.environ["GEMINI_API_KEY"] = "k-123456"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
        os.environ["LLM_MAX_RETRIES"] = "2"
        self.assertEqual(complete("hi", max_tokens=32), "filled")

    def test_unknown_field_is_stripped(self):
        server = self.mock({
            "gemini-3.5-flash-lite": [
                (400, {"error": {"code": 400, "status": "INVALID_ARGUMENT",
                                 "message": 'Invalid JSON payload received. Unknown name "thinkingConfig" at \'generation_config\''}}),
                (200, gemini_ok("stripped ok")),
            ]
        })
        os.environ["GEMINI_API_KEY"] = "k-123456"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
        self.assertEqual(complete("hi", max_tokens=32), "stripped ok")
        self.assertNotIn("thinkingConfig", server.hits[1]["body"]["generationConfig"])


class FallbackTests(LLMTestBase):
    def test_gemini_to_groq_fallback(self):
        server = self.mock({
            "gemini-3.5-flash-lite": [(500, {"error": {"message": "boom"}})],
            "openai/gpt-oss-120b": [(200, openai_ok("from groq"))],
        })
        os.environ["GEMINI_API_KEY"] = "k-123456"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
        os.environ["GROQ_API_KEY"] = "gsk-test-abcdef"
        os.environ["GROQ_API_BASE"] = server.url + "/openai/v1"
        os.environ["LLM_MAX_RETRIES"] = "0"
        self.assertEqual(complete("hi", max_tokens=32), "from groq")

    def test_all_providers_fail_raises(self):
        server = self.mock({"*": [(401, {"error": {"message": "Unauthorized"}})]})
        os.environ["GEMINI_API_KEY"] = "bad-key-000000"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
        os.environ["GROQ_API_KEY"] = "gsk-bad"
        os.environ["GROQ_API_BASE"] = server.url + "/openai/v1"
        os.environ["LLM_MAX_RETRIES"] = "0"
        with self.assertRaises(LLMError) as ctx:
            complete("hi", max_tokens=32)
        self.assertIn("401", str(ctx.exception))

    def test_no_keys_raises_no_provider(self):
        with self.assertRaises(NoProviderError):
            complete("hi", max_tokens=32)

    def test_daily_quota_is_not_retried(self):
        server = self.mock({
            "*": [(429, {"error": {"message": "You exceeded your current quota per day"}})]
        })
        os.environ["GEMINI_API_KEY"] = "k-123456"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
        os.environ["LLM_MAX_RETRIES"] = "3"
        with self.assertRaises(LLMError):
            complete("hi", max_tokens=32)
        self.assertEqual(server.count(), 1)  # RPD 소진은 재시도하지 않음


class HelperTests(LLMTestBase):
    def test_extract_json_handles_fences_and_noise(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('Sure! {"a": [1,2]} hope this helps'), {"a": [1, 2]})
        self.assertEqual(extract_json('```\n[{"n": 1}]\n```'), [{"n": 1}])
        with self.assertRaises(ValueError):
            extract_json("no json here")

    def test_provider_list_reflects_env(self):
        os.environ["GEMINI_API_KEY"] = "k1,k2"
        os.environ["GEMINI_MODEL"] = "m-a,m-b"
        providers = llm.configured_providers()
        self.assertEqual(providers, [("gemini", "m-a"), ("gemini", "m-a"),
                                     ("gemini", "m-b"), ("gemini", "m-b")])

    def test_check_cli_exit_code_without_keys(self):
        self.assertEqual(llm._main([]), 1)


if __name__ == "__main__":
    unittest.main()
