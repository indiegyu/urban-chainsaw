"""
파이프라인 상태 기록 유틸리티
=============================
거짓 성공(false-green)을 막기 위한 공통 장치입니다.

  - health.json : 최근 실행 이벤트 100건 (성공/경고/실패)
  - GitHub Job Summary : 실행 화면에 바로 보이는 요약 표
  - Discord    : DISCORD_WEBHOOK_URL이 있으면 실패 알림

사용법:
    from utils.health import record, fail, summary_line

    record("pod", "warn", "2/5 디자인만 생성됨")
    fail("pod", "디자인을 하나도 만들지 못했습니다")   # 로그 남기고 exit 1
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HEALTH_LOG = Path(
    os.environ.get("HEALTH_LOG_PATH", ".github/run_logs/health.json")
)
MAX_EVENTS = 100


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record(pipeline: str, status: str, detail: str = "", context: dict | None = None) -> dict:
    """health.json에 이벤트를 추가합니다 (최근 100건 유지)."""
    entry = {
        "pipeline": pipeline,
        "status": status,          # ok | warn | fail
        "detail": (detail or "")[:500],
        "timestamp": _now(),
        "run": os.environ.get("GITHUB_RUN_NUMBER", ""),
        "context": context or {},
    }
    try:
        HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(HEALTH_LOG.read_text()) if HEALTH_LOG.exists() else {}
        events = data.get("events", [])
        events.append(entry)
        data["events"] = events[-MAX_EVENTS:]
        data["last_updated"] = entry["timestamp"]
        HEALTH_LOG.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as exc:  # 상태 기록 실패가 파이프라인을 죽이면 안 됨
        print(f"  ⚠ health.json 기록 실패: {exc}")
    return entry


def summary_line(pipeline: str, status: str, detail: str = "") -> None:
    """GitHub Actions Job Summary에 한 줄 남깁니다."""
    path = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if not path:
        return
    icon = {"ok": "✅", "warn": "⚠️", "fail": "❌"}.get(status, "•")
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"- {icon} **{pipeline}** — {detail or status}\n")
    except Exception:
        pass


def _discord(pipeline: str, message: str) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return
    try:
        import requests

        requests.post(
            url,
            json={
                "embeds": [
                    {
                        "title": f"🚨 {pipeline} 실패",
                        "description": message[:1000],
                        "color": 15548997,
                        "footer": {"text": f"AI Income Daily · {_now()}"},
                    }
                ]
            },
            timeout=10,
        )
    except Exception:
        pass


def fail(pipeline: str, message: str, context: dict | None = None, code: int = 1) -> None:
    """실패를 기록하고 프로세스를 실패로 끝냅니다(거짓 성공 방지)."""
    print(f"  ✗ {pipeline} 실패: {message}")
    record(pipeline, "fail", message, context)
    summary_line(pipeline, "fail", message)
    _discord(pipeline, message)
    sys.exit(code)


def warn(pipeline: str, message: str, context: dict | None = None) -> None:
    print(f"  ⚠ {pipeline} 경고: {message}")
    record(pipeline, "warn", message, context)
    summary_line(pipeline, "warn", message)


def ok(pipeline: str, message: str = "", context: dict | None = None) -> None:
    record(pipeline, "ok", message, context)
    summary_line(pipeline, "ok", message)
