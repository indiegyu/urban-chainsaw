"""
Beehiiv 뉴스레터 자동화 스크립트
==================================
Beehiiv API를 사용해 일일 AI 뉴스 다이제스트를 자동 발송합니다.

Beehiiv 수익화:
  - 구독자 1,000명 달성 시: 스폰서십 $50~$500/발송
  - 2,500명: Boosts (신규 구독자 소개) $1~$3/구독자
  - 10,000명: $5,000~$20,000/월 스폰서 가능
  - 유료 구독 설정 (월 $5~$15)

Beehiiv 무료 플랜: 구독자 2,500명, 무제한 발송
가입: https://www.beehiiv.com/

필요한 환경변수:
  BEEHIIV_API_KEY    — API Key (Settings → API)
  BEEHIIV_PUB_ID     — Publication ID (pub_XXXX)
  GROQ_API_KEY       — 뉴스레터 콘텐츠 생성
  GITHUB_PAGES_URL   — 블로그 URL (클릭 유도용)
"""

import os, json, re, requests
from pathlib import Path
from datetime import datetime, timezone

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
BLOG_OUTPUT = Path(__file__).parent.parent / "blog" / "output"
PAGES_URL   = os.environ.get("GITHUB_PAGES_URL", "").rstrip("/")

NEWSLETTER_NAME = "AI Income Insider"
NEWSLETTER_TAGLINE = "Daily strategies to earn more with AI 🤖"


def groq_request(messages: list, groq_key: str, max_tokens: int = 3000) -> str:
    resp = requests.post(GROQ_URL, headers={
        "Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"
    }, json={
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def generate_newsletter_content(groq_key: str, blog_post_title: str = "") -> dict:
    """오늘의 뉴스레터 콘텐츠를 2단계로 생성합니다."""
    today = datetime.now().strftime("%B %d, %Y")

    # Step 1: 메타데이터
    meta_raw = groq_request([
        {"role": "system", "content": 'Output valid JSON only with keys: "subject" (email subject line, 50 chars max, emoji ok), "preview" (preview text, 80 chars)'},
        {"role": "user", "content": f"Daily AI income newsletter for {today}. Blog post: {blog_post_title}"}
    ], groq_key, max_tokens=150)
    meta_raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', meta_raw)
    if "```" in meta_raw:
        meta_raw = meta_raw.split("```")[1].lstrip("json").strip()
    meta = json.loads(meta_raw)

    # Step 2: HTML 본문
    blog_link = ""
    if PAGES_URL and blog_post_title:
        blog_link = f"<p><a href='{PAGES_URL}' style='background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;margin-top:10px'>Read Full Article →</a></p>"

    body = groq_request([
        {"role": "system", "content": (
            "Write a daily email newsletter in HTML. Structure:\n"
            "1. Warm greeting (1 sentence)\n"
            "2. Today's main insight (2-3 paragraphs, practical, actionable)\n"
            "3. Quick tips (3 bullet points)\n"
            "4. Tool of the day (name + why it's useful for income)\n"
            "5. Action step (one specific thing to do today)\n"
            "Use inline styles only (no <style> tags). Friendly, non-corporate tone. "
            "Max 400 words. Clean, mobile-friendly HTML."
        )},
        {"role": "user", "content": f"Date: {today}. Focus topic: {blog_post_title or 'AI side hustles and passive income'}"}
    ], groq_key, max_tokens=1500)

    full_html = f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:0 auto;color:#1a1a1a">
  <div style="background:linear-gradient(135deg,#0f172a,#1e3a5f);padding:30px;text-align:center;border-radius:12px 12px 0 0">
    <h1 style="color:#fff;margin:0;font-size:24px">🤖 {NEWSLETTER_NAME}</h1>
    <p style="color:#94a3b8;margin:8px 0 0">{NEWSLETTER_TAGLINE}</p>
  </div>
  <div style="background:#fff;padding:30px;border:1px solid #e2e8f0;border-top:none">
    {body}
    {blog_link}
  </div>
  <div style="background:#f8fafc;padding:20px;text-align:center;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px">
    <p style="color:#94a3b8;font-size:12px;margin:0">
      You're receiving this because you subscribed to {NEWSLETTER_NAME}.<br>
      <a href="{{{{unsubscribe}}}}" style="color:#6366f1">Unsubscribe</a>
    </p>
  </div>
</div>"""

    meta["body_html"] = full_html
    return meta


def create_beehiiv_post(content: dict, pub_id: str, api_key: str) -> dict:
    """Beehiiv에 포스트를 생성하고 발송합니다."""
    # 먼저 draft 생성
    payload = {
        "subject_line":   content["subject"],
        "preview_text":   content.get("preview", ""),
        "body":           content["body_html"],
        "audience":       "free",
        "send_to":        "all",
        "status":         "draft",
    }

    resp = requests.post(
        f"https://api.beehiiv.com/v2/publications/{pub_id}/posts",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload, timeout=30
    )
    resp.raise_for_status()
    post = resp.json()["data"]
    post_id = post["id"]
    print(f"  ✓ Draft created: {post_id}")

    # 발송 (schedule → now)
    send_resp = requests.post(
        f"https://api.beehiiv.com/v2/publications/{pub_id}/posts/{post_id}/email",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"send_at": "now"}, timeout=30
    )

    if send_resp.status_code in (200, 201, 202):
        print(f"  ✓ Newsletter sent!")
        return post
    else:
        print(f"  ⚠ Send failed: {send_resp.status_code} — post saved as draft")
        return post


def run():
    beehiiv_key = os.environ.get("BEEHIIV_API_KEY", "")
    pub_id      = os.environ.get("BEEHIIV_PUB_ID", "")
    groq_key    = os.environ.get("GROQ_API_KEY", "")

    if not beehiiv_key or not pub_id:
        print("BEEHIIV_API_KEY / BEEHIIV_PUB_ID not set — skipping newsletter")
        print("  Sign up free at https://www.beehiiv.com/ then add secrets")
        return

    # 오늘 최신 블로그 포스트 제목 가져오기
    json_files = sorted(BLOG_OUTPUT.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    blog_title = ""
    if json_files:
        try:
            meta = json.loads(json_files[0].read_text())
            blog_title = meta.get("title", "")
        except Exception:
            pass

    print(f"\n📧 뉴스레터 생성 중... (주제: {blog_title[:50] or 'AI income'})")
    content = generate_newsletter_content(groq_key, blog_title)
    print(f"  제목: {content['subject']}")

    result = create_beehiiv_post(content, pub_id, beehiiv_key)
    print(f"\n✅ 뉴스레터 발송 완료!")

    return result


if __name__ == "__main__":
    run()
