"""
Patreon 자동 포스트
====================
매주 Patreon에 프리미엄 콘텐츠를 자동 발행합니다.
무료 티어 + 유료 티어 게시물 자동 분류.

수익 구조:
  Free tier ($0)  : 기본 팁 → 구독자 모집
  Paid tier ($5)  : 심화 전략 + 툴 리스트 → 월정액 수익
  Paid tier ($15) : 주간 AI 수익 리포트 + 프롬프트팩

필요 시크릿:
  PATREON_ACCESS_TOKEN — patreon.com/portal/registration/register-clients
                          → Create Client → Generate Creator Access Token
  PATREON_CAMPAIGN_ID  — Patreon 캠페인 ID (크리에이터 페이지 URL에서 확인)
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

API           = "https://www.patreon.com/api/oauth2/api"
GROQ_API      = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = "llama-3.3-70b-versatile"
STRATEGY_PATH = Path("scripts/strategy/content_strategy.json")
STATE_FILE    = Path("scripts/social/.patreon_posted.json")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def generate_patreon_post(groq_key: str, is_premium: bool = False) -> dict:
    """이번 주 Patreon 포스트 콘텐츠를 Groq으로 생성합니다."""
    import re

    strategy = {}
    if STRATEGY_PATH.exists():
        strategy = json.loads(STRATEGY_PATH.read_text())

    top_topics = strategy.get("top_performing_topics", ["AI tools", "passive income"])
    week = datetime.now().strftime("Week %V, %Y")

    tier = "exclusive premium" if is_premium else "free preview"
    raw = requests.post(GROQ_API, headers={
        "Authorization": f"Bearer {groq_key}", "Content-Type": "application/json",
    }, json={
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": (
                "Write a Patreon creator post in clean HTML (body only). "
                f"This is a {tier} post for an AI income channel. "
                "Include: a warm greeting, the main insight or strategy for this week, "
                "2-3 specific action items, and a CTA to subscribe/upgrade. "
                "Tone: friendly, insider, exclusive. ~300 words."
            )},
            {"role": "user", "content": (
                f"Write a {tier} Patreon post for {week}. "
                f"Topics this week: {', '.join(top_topics[:3])}. "
                f"{'Include specific income numbers, tool names, and a downloadable resource mention.' if is_premium else 'Give a taste of value, tease the premium content.'}"
            )},
        ],
        "temperature": 0.8,
        "max_tokens": 600,
    }, timeout=30)

    content = raw.json()["choices"][0]["message"]["content"].strip() if raw.status_code == 200 else ""
    title = f"{'🔒 ' if is_premium else ''}AI Income {week} — {'Full Strategy' if is_premium else 'Weekly Tip'}"

    return {"title": title, "content": content, "is_premium": is_premium}


def post_to_patreon(campaign_id: str, token: str, post: dict) -> bool:
    """Patreon API로 포스트를 발행합니다."""
    payload = {
        "data": {
            "type": "post",
            "attributes": {
                "title":          post["title"],
                "content":        post["content"],
                "is_paid":        post["is_premium"],
                "is_public":      not post["is_premium"],
                "post_type":      "text_only",
                "published_at":   datetime.now().isoformat() + "Z",
            },
            "relationships": {
                "campaign": {"data": {"type": "campaign", "id": str(campaign_id)}}
            },
        }
    }
    r = requests.post(f"{API}/posts", headers=_headers(token), json=payload, timeout=20)
    if r.status_code in (200, 201):
        post_id  = r.json().get("data", {}).get("id", "")
        post_url = f"https://www.patreon.com/posts/{post_id}"
        print(f"  ✓ {'[Premium]' if post['is_premium'] else '[Free]'} {post['title'][:50]}")
        print(f"    {post_url}")
        return True
    print(f"  ✗ Patreon 포스트 실패: {r.status_code} {r.text[:200]}")
    return False


def run():
    from dotenv import load_dotenv
    load_dotenv()

    token       = os.environ.get("PATREON_ACCESS_TOKEN", "")
    campaign_id = os.environ.get("PATREON_CAMPAIGN_ID", "")
    groq_key    = os.environ.get("GROQ_API_KEY", "")

    if not token or not campaign_id:
        missing = [k for k, v in {"PATREON_ACCESS_TOKEN": token,
                                   "PATREON_CAMPAIGN_ID": campaign_id}.items() if not v]
        print(f"  ⚠ Patreon 시크릿 없음 ({', '.join(missing)}) — 스킵")
        print("  → patreon.com/portal/registration/register-clients")
        return

    # 이번 주 이미 포스팅했는지 확인
    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    week_key = datetime.now().strftime("%Y-W%V")
    if week_key in state.get("posted_weeks", []):
        print(f"  - 이번 주 이미 포스팅됨 ({week_key})")
        return

    print("🎯 Patreon 주간 포스트 발행...")

    # 무료 포스트 (공개)
    free_post    = generate_patreon_post(groq_key, is_premium=False)
    # 유료 포스트 (구독자 전용)
    premium_post = generate_patreon_post(groq_key, is_premium=True)

    ok1 = post_to_patreon(campaign_id, token, free_post)
    ok2 = post_to_patreon(campaign_id, token, premium_post)

    if ok1 or ok2:
        posted_weeks = state.get("posted_weeks", [])
        posted_weeks.append(week_key)
        state["posted_weeks"] = posted_weeks[-52:]  # 최근 1년만 보관
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
        print(f"  ✅ Patreon 포스팅 완료 ({week_key})")


if __name__ == "__main__":
    run()
