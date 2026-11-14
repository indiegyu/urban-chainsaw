"""
공용 LLM 클라이언트 (Gemini 무료 티어 우선 + Groq / OpenRouter 폴백)
=====================================================================

모든 파이프라인 스크립트는 이 모듈만 거쳐 LLM을 호출합니다.
provider·모델이 바뀌어도 각 스크립트는 손대지 않아도 됩니다.

사용법
------
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from llm import complete

    text = complete([{"role": "system", "content": "..."},
                     {"role": "user",   "content": "..."}],
                    max_tokens=800, temperature=0.7, json_mode=True)

환경변수
--------
  GEMINI_API_KEY       Google AI Studio(aistudio.google.com) 무료 키.
                       콤마로 여러 개를 넣으면 순서대로 돌려 씁니다(같은 프로젝트 키면
                       할당량이 공유되므로 의미 없음 — 프로젝트가 다를 때만 효과).
  GEMINI_MODEL         기본 "gemini-3.5-flash-lite". 콤마로 여러 개를 넣으면
                       앞에서부터 시도합니다(모델이 내려가거나 할당량이 찰 때 대비).
  GROQ_API_KEY         (선택) Groq 폴백.
  GROQ_MODEL           기본 "openai/gpt-oss-120b".
  OPENROUTER_API_KEY   (선택) OpenRouter 폴백.
  OPENROUTER_MODEL     기본 "openrouter/free".
  LLM_PROVIDER_ORDER   기본 "gemini,groq,openrouter".
  GEMINI_MIN_INTERVAL  Gemini 호출 간 최소 간격(초). 기본 4.2 (15 RPM 무료 한도 기준).
  LLM_MAX_RETRIES      provider 한 곳당 재시도 횟수. 기본 3.
  LLM_MAX_BACKOFF      재시도 대기 상한(초). 기본 60.

무료 티어 주의
--------------
  Gemini 무료 티어는 2026-11 기준 Flash 계열 5 RPM / 20 RPD,
  Flash-Lite 계열 15 RPM / 500 RPD 수준입니다(프로젝트마다 상이, Google 미공개).
  하루 호출량이 많은 이 저장소에는 Flash-Lite가 맞습니다.
  429가 나면 RetryInfo.retryDelay만큼 기다렸다가 재시도하고,
  그래도 안 되면 다음 모델 → 다음 provider로 자동 폴백합니다.
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from typing import Iterable

import requests

# ── 기본값 ───────────────────────────────────────────────────────────────────
GEMINI_BASE_DEFAULT = "https://generativelanguage.googleapis.com"
GROQ_BASE_DEFAULT = "https://api.groq.com/openai/v1"
OPENROUTER_BASE_DEFAULT = "https://openrouter.ai/api/v1"

DEFAULT_GEMINI_MODELS = "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.8-flash"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_OPENROUTER_MODEL = "openrouter/free"

DEFAULT_TIMEOUT = 90


class LLMError(RuntimeError):
    """모든 provider가 실패했을 때."""


class NoProviderError(LLMError):
    """설정된 API 키가 하나도 없을 때."""


class _Retryable(Exception):
    """같은 target으로 다시 시도할 가치가 있는 오류 (429/5xx/타임아웃)."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class _Fatal(Exception):
    """이 target으로는 더 시도해도 소용없는 오류 (401/403/404 등)."""


@dataclass
class Target:
    """호출 대상 1개 = provider + 모델 + 키."""

    provider: str
    model: str
    key: str
    base: str
    min_interval: float = 0.0

    @property
    def label(self) -> str:
        return f"{self.provider}/{self.model}"

    @property
    def masked_key(self) -> str:
        if len(self.key) <= 6:
            return "***"
        return f"***{self.key[-4:]}"


# ── 설정 읽기 ────────────────────────────────────────────────────────────────
def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _split(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def configured_providers() -> list[tuple[str, str]]:
    """(provider, model) 목록 — 키가 설정된 것만. 진단/헬스체크용."""
    return [(t.provider, t.model) for t in _targets()]


def _targets(only: Iterable[str] | None = None) -> list[Target]:
    order = _split(os.environ.get("LLM_PROVIDER_ORDER", "gemini,groq,openrouter"))
    if only:
        order = [p for p in order if p in set(only)]

    gemini_keys = _split(os.environ.get("GEMINI_API_KEY", "")) or _split(
        os.environ.get("GOOGLE_API_KEY", "")
    )
    gemini_models = _split(os.environ.get("GEMINI_MODEL", "")) or _split(
        DEFAULT_GEMINI_MODELS
    )
    gemini_base = (os.environ.get("GEMINI_API_BASE", "") or GEMINI_BASE_DEFAULT).rstrip("/")
    gemini_interval = _env_float("GEMINI_MIN_INTERVAL", 4.2)

    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    groq_model = os.environ.get("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL
    groq_base = (os.environ.get("GROQ_API_BASE", "") or GROQ_BASE_DEFAULT).rstrip("/")

    or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    or_model = os.environ.get("OPENROUTER_MODEL", "").strip() or DEFAULT_OPENROUTER_MODEL
    or_base = (os.environ.get("OPENROUTER_API_BASE", "") or OPENROUTER_BASE_DEFAULT).rstrip("/")

    targets: list[Target] = []
    for provider in order:
        if provider == "gemini":
            for model in gemini_models:
                for key in gemini_keys:
                    targets.append(
                        Target("gemini", model, key, gemini_base, gemini_interval)
                    )
        elif provider == "groq" and groq_key:
            targets.append(Target("groq", groq_model, groq_key, groq_base, 0.0))
        elif provider == "openrouter" and or_key:
            targets.append(Target("openrouter", or_model, or_key, or_base, 0.0))

    # 같은 provider 안에서 두 번째 키는 첫 키가 할당량 초과일 때만 쓰도록 뒤로 보냄
    return targets


def ensure_available() -> None:
    """키가 하나도 없으면 즉시 명확한 오류로 실패시킵니다(거짓 성공 방지)."""
    if not _targets():
        raise NoProviderError(
            "LLM API 키가 없습니다. GitHub Secrets에 GEMINI_API_KEY를 등록하세요 "
            "(무료 발급: https://aistudio.google.com/apikey). "
            "보조로 GROQ_API_KEY 또는 OPENROUTER_API_KEY를 넣어도 됩니다."
        )


# ── 메시지 변환 ──────────────────────────────────────────────────────────────
def _split_system(messages: list[dict]) -> tuple[str, list[dict]]:
    """OpenAI 형식 메시지를 (시스템 지시문, 나머지 턴)으로 나눕니다."""
    system_parts: list[str] = []
    turns: list[dict] = []
    for msg in messages:
        role = (msg.get("role") or "user").lower()
        content = msg.get("content") or ""
        if isinstance(content, list):  # parts 배열 형식도 허용
            content = "\n".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        if role == "system":
            system_parts.append(content)
        else:
            turn_role = "model" if role == "assistant" else "user"
            if turns and turns[-1]["role"] == turn_role:
                turns[-1]["parts"][0]["text"] += "\n\n" + content
            else:
                turns.append({"role": turn_role, "parts": [{"text": content}]})
    if not turns:
        turns = [{"role": "user", "parts": [{"text": "Continue."}]}]
    if turns[0]["role"] == "model":  # Gemini는 user로 시작해야 함
        turns.insert(0, {"role": "user", "parts": [{"text": "Continue."}]})
    return "\n\n".join(system_parts), turns


# ── Gemini 네이티브 호출 ─────────────────────────────────────────────────────
def _gemini_body(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    model: str,
) -> dict:
    system, turns = _split_system(messages)
    config: dict = {
        "maxOutputTokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        config["responseMimeType"] = "application/json"
    if model.startswith("gemini-3"):
        # Flash 계열은 thinking 토큰이 출력 한도를 잡아먹어 본문이 비는 일이 있음
        config["thinkingConfig"] = {"thinkingLevel": "minimal"}
    body: dict = {"contents": turns, "generationConfig": config}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    return body


_UNSUPPORTED_FIELD_RE = re.compile(r'Unknown name \\?"([^"\\]+)\\?"|Invalid value at \'([^\']+)\'')


def _strip_unsupported(body: dict, error_text: str) -> bool:
    """400 응답이 특정 generationConfig 필드 때문이면 그 필드를 빼고 재시도."""
    config = body.get("generationConfig")
    if not isinstance(config, dict) or not error_text:
        return False

    # 400 본문에는 문제 필드 이름이 그대로 들어옵니다
    # (예: Unknown name \"thinkingConfig\" at 'generation_config')
    lowered = error_text.lower()
    for key in list(config.keys()):
        if key.lower() in lowered or _snake(key).lower() in lowered:
            config.pop(key, None)
            return True

    match = _UNSUPPORTED_FIELD_RE.search(error_text)
    names = [n for n in (match.groups() if match else []) if n]
    for name in names:
        leaf = name.split(".")[-1]
        for key in (leaf, _snake(leaf)):
            if key in config:
                config.pop(key, None)
                return True
    return False


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _gemini_call(
    target: Target, messages: list[dict], max_tokens: int, temperature: float,
    json_mode: bool, timeout: float,
) -> str:
    body = _gemini_body(messages, max_tokens, temperature, json_mode, target.model)
    url = f"{target.base}/v1beta/models/{target.model}:generateContent"
    headers = {"x-goog-api-key": target.key, "Content-Type": "application/json"}

    for _ in range(3):  # 지원하지 않는 필드 제거 후 재시도 (최대 2회 제거)
        resp = _post(url, headers, body, timeout)
        if resp.status_code == 200:
            return _gemini_text(resp.json(), target)
        text = resp.text or ""
        if resp.status_code == 400:
            if _strip_unsupported(body, text):
                continue
            if "API key not valid" in text or "API_KEY_INVALID" in text:
                raise _Fatal(f"API 키가 유효하지 않습니다: {_short(text)}")
            raise _Fatal(f"400 잘못된 요청: {_short(text)}")
        _raise_for_status(resp, target)
    raise _Fatal("400 요청 형식을 맞추지 못했습니다.")


def _gemini_text(data: dict, target: Target) -> str:
    feedback = (data.get("promptFeedback") or {}).get("blockReason")
    candidates = data.get("candidates") or []
    if not candidates:
        raise _Fatal(f"응답 없음(blockReason={feedback or 'unknown'})")
    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(
        p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought")
    ).strip()
    finish = candidate.get("finishReason")
    if not text:
        if finish == "MAX_TOKENS":
            raise _Retryable("출력 한도(MAX_TOKENS)로 본문이 비었습니다.")
        raise _Retryable(f"빈 응답(finishReason={finish or 'unknown'})")
    if finish in {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"}:
        raise _Fatal(f"안전 정책으로 차단됨(finishReason={finish})")
    return text


# ── OpenAI 호환 호출 (Groq / OpenRouter) ─────────────────────────────────────
def _openai_call(
    target: Target, messages: list[dict], max_tokens: int, temperature: float,
    json_mode: bool, timeout: float,
) -> str:
    body: dict = {
        "model": target.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    url = f"{target.base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {target.key}",
        "Content-Type": "application/json",
    }
    resp = _post(url, headers, body, timeout)
    if resp.status_code == 200:
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise _Retryable("응답에 choices가 없습니다.")
        content = (choices[0].get("message") or {}).get("content") or ""
        text = content.strip()
        if not text:
            if choices[0].get("finish_reason") == "length":
                raise _Retryable("출력 한도(length)로 본문이 비었습니다.")
            raise _Retryable("빈 응답")
        return text
    _raise_for_status(resp, target)
    raise _Fatal("응답을 해석하지 못했습니다.")


def _post(url: str, headers: dict, body: dict, timeout: float):
    try:
        return requests.post(url, headers=headers, json=body, timeout=timeout)
    except requests.Timeout as exc:
        raise _Retryable(f"시간 초과({timeout}s): {exc}") from exc
    except requests.RequestException as exc:
        raise _Retryable(f"네트워크 오류: {exc}") from exc


_RETRY_DELAY_RE = re.compile(r'"?retryDelay"?\s*:\s*"(\d+(?:\.\d+)?)s"')


def _raise_for_status(resp, target: Target) -> None:
    status = resp.status_code
    text = resp.text or ""
    if status == 429:
        retry_after = None
        match = _RETRY_DELAY_RE.search(text)
        if match:
            retry_after = float(match.group(1))
        header = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
        if header:
            try:
                retry_after = max(retry_after or 0.0, float(header))
            except ValueError:
                pass
        message = _short(text)
        if re.search(r"per day|PerDay|daily", text, re.I):
            raise _Fatal(f"일일 할당량(RPD) 소진: {message}")
        raise _Retryable(f"429 요청 한도: {message}", retry_after=retry_after)
    if status in (500, 502, 503, 504):
        raise _Retryable(f"{status} 서버 오류: {_short(text)}")
    if status in (408,):
        raise _Retryable(f"{status} 시간 초과: {_short(text)}")
    if status in (401, 403):
        raise _Fatal(f"{status} 인증/권한 오류: {_short(text)}")
    if status == 404:
        raise _Fatal(f"404 모델을 쓸 수 없습니다({target.model}): {_short(text)}")
    raise _Fatal(f"{status} 오류: {_short(text)}")


def _short(text: str, limit: int = 200) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text[:limit]


# ── 공개 API ─────────────────────────────────────────────────────────────────
def complete(
    messages: list[dict] | str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    json_mode: bool = False,
    timeout: float | None = None,
    only: Iterable[str] | None = None,
    quiet: bool = False,
) -> str:
    """여러 provider를 순서대로 시도해 텍스트를 반환합니다.

    Args:
        messages: OpenAI 형식 메시지 리스트(또는 단일 프롬프트 문자열)
        max_tokens: 출력 토큰 상한
        temperature: 샘플링 온도
        json_mode: JSON 응답 강제 (Gemini responseMimeType / OpenAI response_format)
        timeout: 요청 1회 타임아웃(초)
        only: 특정 provider만 사용 (예: ["gemini"])
        quiet: 진행 로그 생략

    Raises:
        NoProviderError: 키가 하나도 없을 때
        LLMError: 모든 provider가 실패했을 때 (개별 사유 포함)
    """
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    targets = _targets(only=only)
    if not targets:
        ensure_available()
        raise NoProviderError("사용할 수 있는 LLM provider가 없습니다.")

    max_retries = _env_int("LLM_MAX_RETRIES", 3)
    max_backoff = _env_float("LLM_MAX_BACKOFF", 60.0)
    timeout = timeout or _env_float("LLM_TIMEOUT", DEFAULT_TIMEOUT)
    errors: list[str] = []
    dead_keys: set[str] = set()

    for target in targets:
        if target.key in dead_keys:
            continue
        attempt = 0
        while attempt <= max_retries:
            _throttle(target)
            started = time.monotonic()
            try:
                if target.provider == "gemini":
                    text = _gemini_call(
                        target, messages, max_tokens, temperature, json_mode, timeout
                    )
                else:
                    text = _openai_call(
                        target, messages, max_tokens, temperature, json_mode, timeout
                    )
                if not quiet:
                    elapsed = time.monotonic() - started
                    print(f"  ⚙ LLM {target.label} · {len(text)}자 · {elapsed:.1f}s")
                return text
            except _Retryable as exc:
                attempt += 1
                errors.append(f"{target.label}: {exc}")
                if attempt > max_retries:
                    if not quiet:
                        print(f"  ⚠ {target.label} 재시도 소진 — 다음 provider로 폴백")
                    break
                wait = min(max_backoff, exc.retry_after or (2.0 * (2 ** (attempt - 1))))
                wait += random.uniform(0, 0.5)
                if not quiet:
                    print(f"  ⚠ {target.label}: {exc} → {wait:.0f}초 후 재시도 "
                          f"({attempt}/{max_retries})")
                time.sleep(wait)
            except _Fatal as exc:
                errors.append(f"{target.label}: {exc}")
                errors_text = str(exc)
                if exc.args and ("401" in errors_text or "403" in errors_text
                                 or "API 키가 유효하지" in errors_text):
                    dead_keys.add(target.key)
                if not quiet:
                    print(f"  ⚠ {target.label} 사용 불가: {exc}")
                break

    detail = " | ".join(errors[:6]) if errors else "설정된 provider 없음"
    raise LLMError(f"LLM 호출 실패 — {detail}")


# 프로세스 전역 스로틀 상태 (target 객체는 호출마다 새로 만들어지므로 키로 관리)
_LAST_CALL: dict[str, float] = {}


def _throttle(target: Target) -> None:
    if target.min_interval <= 0:
        return
    now = time.monotonic()
    wait = target.min_interval - (now - _LAST_CALL.get(target.label, 0.0))
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL[target.label] = time.monotonic()


def extract_json(text: str):
    """코드펜스/설명이 섞인 응답에서 JSON만 뽑아 파싱합니다."""
    raw = (text or "").strip()
    if "```" in raw:
        parts = raw.split("```")
        if len(parts) >= 2:
            raw = parts[1]
            if raw.lstrip().lower().startswith("json"):
                raw = raw.lstrip()[4:]
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    for pattern in (r"\{.*\}", r"\[.*\]"):
        match = re.search(pattern, raw, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
    raise ValueError(f"JSON 파싱 실패: {_short(raw, 300)}")


# ── CLI: 설정 확인 / 실제 호출 확인 ──────────────────────────────────────────
def _main(argv: list[str]) -> int:
    check = "--check" in argv or "-c" in argv
    targets = _targets()
    if not targets:
        print("❌ LLM provider가 설정되지 않았습니다.")
        print("   GEMINI_API_KEY를 발급해 등록하세요 → https://aistudio.google.com/apikey")
        return 1

    print(f"설정된 호출 대상 {len(targets)}개 (순서대로 시도):")
    for target in targets:
        throttle = f", 최소간격 {target.min_interval:.1f}s" if target.min_interval else ""
        print(f"  - {target.label} (key {target.masked_key}{throttle})")

    if not check:
        return 0

    print("\n실제 호출 확인 (짧은 프롬프트 1회)...")
    try:
        text = complete(
            [{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=32,
            temperature=0.0,
        )
        print(f"✅ 응답: {text.strip()[:80]}")
        return 0
    except LLMError as exc:
        print(f"❌ 실패: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
