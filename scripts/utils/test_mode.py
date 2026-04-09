"""
테스트 모드 인프라 — 피처 플래그 + 스텁 클라이언트
=====================================================
환경변수 TEST_MODE=1 또는 CI=true 시 자동으로 활성화됩니다.
실제 외부 API 호출을 모두 스텁으로 대체하므로 시크릿 없이 CI 실행 가능.

사용법:
    from scripts.utils.test_mode import is_test_mode, stub_response, MockOAuthToken

    if is_test_mode():
        token = MockOAuthToken().get_access_token()
    else:
        token = get_real_access_token()
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone


# ── 피처 플래그 ────────────────────────────────────────────────────────────────

def is_test_mode() -> bool:
    """TEST_MODE=1 또는 CI=true 일 때 True."""
    return (
        os.environ.get("TEST_MODE", "").strip() in ("1", "true", "yes") or
        os.environ.get("CI", "").strip().lower() == "true"
    )


def require_secret(env_key: str, description: str = "") -> str:
    """
    시크릿을 읽습니다. 테스트 모드에서는 test-stub-<env_key> 를 반환.
    실제 모드에서는 값이 없으면 RuntimeError를 발생시킵니다.
    """
    value = os.environ.get(env_key, "").strip()
    if value:
        return value
    if is_test_mode():
        stub = f"test-stub-{env_key.lower().replace('_', '-')}"
        print(f"  [TEST_MODE] {env_key} not set → using stub: {stub}")
        return stub
    raise RuntimeError(
        f"Missing required secret: {env_key}"
        + (f" ({description})" if description else "")
        + "\n  → 테스트 모드로 실행하려면 TEST_MODE=1 을 설정하세요."
    )


# ── OAuth / YouTube 목(Mock) ────────────────────────────────────────────────────

class MockOAuthToken:
    """테스트 모드용 OAuth 토큰 — 실제 Google API를 호출하지 않습니다."""

    ACCESS_TOKEN = "ya29.test-stub-access-token"
    REFRESH_TOKEN = "test-stub-refresh-token"

    def get_access_token(self) -> str:
        print("  [TEST_MODE] MockOAuthToken.get_access_token() → stub token")
        return self.ACCESS_TOKEN

    def write_token_file(self, path: str = "token.json"):
        data = {
            "token": self.ACCESS_TOKEN,
            "refresh_token": self.REFRESH_TOKEN,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        }
        Path(path).write_text(json.dumps(data, indent=2))
        print(f"  [TEST_MODE] Mock token.json written to {path}")
        return path


# ── HTTP 목 응답 ────────────────────────────────────────────────────────────────

class StubResponse:
    """requests.Response를 흉내 내는 스텁."""

    def __init__(self, body: dict, status_code: int = 200, headers: dict = None):
        self._body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.text = json.dumps(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.text}")


def stub_youtube_upload(video_path: str, title: str, **_) -> dict:
    """YouTube 업로드를 흉내 내는 스텁 — 테스트 모드 전용."""
    fake_id = f"TEST_{int(time.time())}"
    print(f"  [TEST_MODE] Stub YouTube upload: '{title}' → https://youtu.be/{fake_id}")
    return {"id": fake_id, "url": f"https://youtu.be/{fake_id}"}


def stub_api_post(url: str, payload: dict, description: str = "") -> StubResponse:
    """범용 API POST 스텁."""
    print(f"  [TEST_MODE] Stub POST {url[:60]} {description}")
    return StubResponse({"stub": True, "url": url, "payload_keys": list(payload.keys())})


# ── 테스트 출력 디렉토리 ────────────────────────────────────────────────────────

def test_output_dir(pipeline: str) -> Path:
    """테스트 모드 파이프라인 출력 경로."""
    d = Path(f"scripts/{pipeline}/test_output")
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── 진단 헬퍼 ──────────────────────────────────────────────────────────────────

def print_test_banner(pipeline: str):
    """테스트 모드 실행임을 명확히 표시."""
    print(f"""
╔══════════════════════════════════════════════════════╗
║  [TEST_MODE] {pipeline:<40} ║
║  실제 API 호출 없음 — 스텁 모드로 실행 중           ║
║  라이브 실행: TEST_MODE 환경변수 제거 후 시크릿 설정 ║
╚══════════════════════════════════════════════════════╝""")


def assert_test_mode(pipeline: str):
    """테스트 모드가 아닐 때 경고를 출력합니다 (스크립트 self-test용)."""
    if not is_test_mode():
        print(f"  ⚠ [{pipeline}] TEST_MODE 미설정 — 실제 API를 사용합니다.")
    else:
        print_test_banner(pipeline)


# ── 런타임 요약 ────────────────────────────────────────────────────────────────

def test_mode_summary() -> dict:
    return {
        "test_mode": is_test_mode(),
        "env_TEST_MODE": os.environ.get("TEST_MODE", "(not set)"),
        "env_CI": os.environ.get("CI", "(not set)"),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
