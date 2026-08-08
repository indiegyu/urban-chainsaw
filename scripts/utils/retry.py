"""
API 호출 재시도 + 에러 알림 유틸리티
====================================
모든 파이프라인 스크립트에서 공통으로 사용합니다.

사용법:
  from utils.retry import retry_api_call, notify_error, PipelineHealthCheck

  data = retry_api_call(lambda: requests.get(url), max_retries=3)
  notify_error("youtube", "Upload failed", {"run": 31})
"""

import os
import time
import json
import functools
import requests
from pathlib import Path
from datetime import datetime, timezone


# ── 재시도 데코레이터 ─────────────────────────────────────────────────────────

def retry_api_call(func, max_retries: int = 3, base_delay: float = 2.0,
                   retryable_exceptions: tuple = (requests.RequestException, TimeoutError, ConnectionError)):
    """지수 백오프로 API 호출을 재시도합니다.

    Args:
        func: 호출할 함수 (인자 없는 callable)
        max_retries: 최대 재시도 횟수
        base_delay: 초기 대기 시간(초)
        retryable_exceptions: 재시도 대상 예외 타입들

    Returns:
        함수 반환값

    Raises:
        마지막 시도에서 발생한 예외
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except retryable_exceptions as e:
            last_error = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  ⚠ 시도 {attempt + 1}/{max_retries + 1} 실패: {e}")
                print(f"    → {delay:.0f}초 후 재시도...")
                time.sleep(delay)
            else:
                print(f"  ✗ {max_retries + 1}회 시도 후 최종 실패: {e}")
    raise last_error


def with_retry(max_retries: int = 3, base_delay: float = 2.0,
               retryable_exceptions: tuple = (requests.RequestException, TimeoutError, ConnectionError)):
    """재시도 로직을 적용하는 데코레이터.

    사용법:
        @with_retry(max_retries=3)
        def fetch_data(url):
            return requests.get(url, timeout=10)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry_api_call(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay,
                retryable_exceptions=retryable_exceptions,
            )
        return wrapper
    return decorator


# ── 에러 알림 ─────────────────────────────────────────────────────────────────

HEALTH_LOG_PATH = Path(".github/run_logs/health.json")


def notify_error(pipeline: str, error_msg: str, context: dict = None):
    """파이프라인 에러를 기록하고 선택적으로 외부 알림을 발송합니다.

    1. 항상: health.json에 에러 기록
    2. Discord webhook 설정 시: Discord 알림
    3. GitHub Actions 환경: Job Summary에 기록
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    error_entry = {
        "pipeline": pipeline,
        "error": error_msg[:500],
        "timestamp": now,
        "context": context or {},
    }

    # 1. health.json에 기록
    _append_health_log(error_entry)

    # 2. Discord webhook (선택)
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if discord_url:
        _send_discord_alert(discord_url, pipeline, error_msg, now)

    # 3. GitHub Actions Job Summary
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(f"\n### ❌ {pipeline} 파이프라인 에러\n")
            f.write(f"- **시간**: {now}\n")
            f.write(f"- **에러**: {error_msg[:300]}\n")
            if context:
                f.write(f"- **컨텍스트**: `{json.dumps(context, ensure_ascii=False)[:200]}`\n")


def notify_success(pipeline: str, details: str = "", context: dict = None):
    """파이프라인 성공을 기록합니다."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "pipeline": pipeline,
        "status": "success",
        "details": details[:300],
        "timestamp": now,
        "context": context or {},
    }
    _append_health_log(entry)


def _append_health_log(entry: dict):
    """health.json에 항목을 추가합니다 (최근 100건 유지)."""
    HEALTH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(HEALTH_LOG_PATH.read_text()) if HEALTH_LOG_PATH.exists() else {"events": []}
    except (json.JSONDecodeError, FileNotFoundError):
        data = {"events": []}

    data["events"].append(entry)
    data["events"] = data["events"][-100:]  # 최근 100건만 유지
    data["last_updated"] = entry["timestamp"]

    HEALTH_LOG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _send_discord_alert(webhook_url: str, pipeline: str, error_msg: str, timestamp: str):
    """Discord 웹훅으로 에러 알림을 보냅니다."""
    try:
        requests.post(webhook_url, json={
            "embeds": [{
                "title": f"🚨 {pipeline} 파이프라인 에러",
                "description": error_msg[:1000],
                "color": 15548997,  # 빨간색
                "footer": {"text": f"AI Income Daily · {timestamp}"},
            }]
        }, timeout=10)
    except Exception:
        pass  # 알림 실패는 조용히 무시


# ── 헬스체크 ──────────────────────────────────────────────────────────────────

class PipelineHealthCheck:
    """파이프라인 실행 상태를 추적하고 요약을 제공합니다."""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.steps = []

    def step_ok(self, name: str, detail: str = ""):
        self.steps.append({"name": name, "status": "ok", "detail": detail,
                           "ts": datetime.now(timezone.utc).strftime("%H:%M:%S")})
        print(f"  ✓ {name}" + (f": {detail}" if detail else ""))

    def step_fail(self, name: str, error: str):
        self.steps.append({"name": name, "status": "fail", "error": error,
                           "ts": datetime.now(timezone.utc).strftime("%H:%M:%S")})
        print(f"  ✗ {name}: {error}")

    def step_warn(self, name: str, warning: str):
        self.steps.append({"name": name, "status": "warn", "warning": warning,
                           "ts": datetime.now(timezone.utc).strftime("%H:%M:%S")})
        print(f"  ⚠ {name}: {warning}")

    @property
    def ok(self) -> bool:
        return all(s["status"] == "ok" for s in self.steps)

    @property
    def duration_sec(self) -> float:
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def summary(self) -> dict:
        return {
            "ok": self.ok,
            "steps": self.steps,
            "duration_sec": round(self.duration_sec, 1),
            "failed_steps": [s["name"] for s in self.steps if s["status"] == "fail"],
        }

    def write_github_summary(self, pipeline: str):
        """GitHub Actions Job Summary에 실행 결과를 기록합니다."""
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "")
        if not summary_path:
            return

        icon = "✅" if self.ok else "❌"
        with open(summary_path, "a") as f:
            f.write(f"\n## {icon} {pipeline} 파이프라인 결과\n\n")
            f.write(f"| 단계 | 상태 | 상세 |\n|------|------|------|\n")
            for s in self.steps:
                status_icon = {"ok": "✅", "fail": "❌", "warn": "⚠️"}.get(s["status"], "?")
                detail = s.get("detail") or s.get("error") or s.get("warning") or ""
                f.write(f"| {s['name']} | {status_icon} | {detail[:80]} |\n")
            f.write(f"\n⏱️ 총 소요시간: {self.duration_sec:.1f}초\n")
