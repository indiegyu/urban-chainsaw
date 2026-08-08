"""
Phase 2 – AI 블로그 포스트 생성기 (Ghost 없이 직접 실행)
==========================================================
Groq으로 SEO 블로그 글을 생성하고 HTML/Markdown 파일로 저장합니다.
Ghost CMS가 있으면 자동 발행하고, 없으면 파일로 저장합니다.

사용법:
  python scripts/blog/generate_post.py "주제"
  python scripts/blog/generate_post.py  # 트렌딩 주제 자동 선택
"""

import os
import sys
import json
import time
import random
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"
OUTPUT_DIR   = Path(__file__).parent / "output"

# 트렌딩 틈새 주제 (수익성 높은 카테고리)
TRENDING_TOPICS = [
    "best AI tools to make money online in 2026",
    "how to start a print on demand business with no money",
    "passive income ideas for beginners 2026",
    "best side hustles for introverts 2026",
    "how to make money with YouTube automation",
    "affiliate marketing for beginners step by step",
    "best remote jobs that pay over $100k",
    "how to build a faceless YouTube channel",
    "ChatGPT side hustle ideas that actually work",
    "dropshipping vs print on demand which is better",
]

# Affiliate 링크는 link_inserter.py의 AFFILIATE_MAP에서 관리
# 환경변수로 ID 설정: AMAZON_TAG, FIVERR_AFF_ID, HOSTINGER_AFF_ID 등
AFFILIATE_LINKS = {}  # 레거시 호환성 유지 (실제 삽입은 link_inserter.py가 처리)


_sys_path = str(Path(__file__).parent.parent)
if _sys_path not in sys.path:
    sys.path.insert(0, _sys_path)
from utils.retry import retry_api_call, notify_error, notify_success, PipelineHealthCheck


def _groq_request(messages: list, groq_api_key: str, max_tokens: int = 2048) -> str:
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
    def _call():
        resp = requests.post(
            GROQ_API_URL,
            headers=headers,
            json={"model": GROQ_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": max_tokens},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    return retry_api_call(_call, max_retries=3)


def generate_blog_post(topic: str, groq_api_key: str) -> dict:
    """Groq으로 완전한 SEO 블로그 포스트를 2단계로 생성합니다."""
    # Step 1: 메타데이터만 JSON으로
    meta_raw = _groq_request([
        {"role": "system", "content": (
            "Output valid JSON only (no markdown, no code blocks) with keys: "
            "'title' (max 70 chars SEO title), 'slug' (url-friendly), "
            "'meta_description' (155 chars), 'tags' (list of 5 strings)"
        )},
        {"role": "user", "content": f"Blog post topic: {topic}"},
    ], groq_api_key, max_tokens=300)
    import re
    meta_raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', meta_raw)
    if "```" in meta_raw:
        meta_raw = meta_raw.split("```")[1].lstrip("json").strip()
    # Groq이 JSON 앞뒤에 텍스트를 붙이는 경우를 대비해 중괄호 블록만 추출
    json_match = re.search(r'\{.*\}', meta_raw, re.S)
    if json_match:
        meta_raw = json_match.group(0)
    try:
        meta = json.loads(meta_raw)
    except json.JSONDecodeError:
        # 메타 파싱 실패 시 기본값으로 진행
        slug = re.sub(r'[^a-z0-9]+', '-', topic.lower())[:50]
        meta = {
            "title": topic[:70],
            "slug": slug,
            "meta_description": f"Learn how to {topic} with AI tools in 2026.",
            "tags": ["ai", "passive-income", "side-hustle", "make-money-online", "automation"],
        }

    # Step 2: HTML 본문만 (JSON 불필요, 그냥 텍스트)
    html_content = _groq_request([
        {"role": "system", "content": (
            "You are a top SEO content writer. Write a complete blog post in clean HTML (body tags only).\n\n"
            "STRUCTURE (total 1200-1500 words):\n"
            "1. INTRO (100-150 words): Start with a bold stat or surprising fact. "
            "State the problem. Promise the solution. Use <strong> for key phrases.\n"
            "2. BODY (4-6 H2 sections, each 150-250 words):\n"
            "   - Each section: clear H2 heading with keyword → explanation → "
            "specific tool/method → concrete result/number\n"
            "   - Include <blockquote> for pro tips or key takeaways\n"
            "   - Use ordered/unordered lists for steps and comparisons\n"
            "   - Mention specific tools naturally: n8n, hostinger, convertkit, beehiiv, printify\n"
            "   - Wrap tool mentions like: {{AFFILIATE:toolname}}\n"
            "3. FAQ SECTION: Add H2 'Frequently Asked Questions' with 3 Q&A pairs using H3 for questions\n"
            "4. CONCLUSION (100 words): Summarize top 3 takeaways, clear CTA to subscribe/follow\n\n"
            "SEO RULES:\n"
            "- Target keyword should appear in first 100 words and 2-3 H2 headings\n"
            "- Use LSI keywords naturally throughout\n"
            "- Short paragraphs (2-3 sentences max)\n"
            "- Include internal linking placeholders: {{INTERNAL:related-topic}}\n"
            "STYLE: Authoritative but conversational. Data-driven. No fluff."
        )},
        {"role": "user", "content": f"Write about: {topic}"},
    ], groq_api_key, max_tokens=4000)

    meta["html"] = html_content
    meta["word_count"] = len(html_content.split())
    return meta


def insert_affiliate_links(html: str) -> str:
    """본문에서 키워드를 감지해 affiliate 링크 자동 삽입 + {{AFFILIATE:tool}} 플레이스홀더 처리."""
    import re, sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from affiliate.link_inserter import insert_affiliate_links as _insert, _build_affiliate_map
        aff_map = _build_affiliate_map()
        # 레거시 플레이스홀더 처리
        def replace_placeholder(match):
            tool = match.group(1).lower().strip()
            info = aff_map.get(tool, {})
            url = info.get("url", "#")
            return f'<a href="{url}" target="_blank" rel="noopener sponsored">{tool}</a>'
        html = re.sub(r'\{\{AFFILIATE:([^}]+)\}\}', replace_placeholder, html)
        # 키워드 자동 감지 삽입 (최대 5개)
        html, _ = _insert(html, max_per_post=5)
    except Exception as e:
        print(f"  ⚠ Affiliate insert skipped: {e}")
    return html


def _build_post_cta() -> str:
    """포스트 하단 수익화 CTA 박스"""
    beehiiv_pub = os.environ.get("BEEHIIV_PUB_ID", "")
    kofi        = os.environ.get("KOFI_USERNAME", "")
    sub_btn = (f'<a href="https://www.beehiiv.com/subscribe/{beehiiv_pub}" target="_blank" '
               f'style="display:inline-block;background:#6366f1;color:#fff;padding:10px 22px;'
               f'border-radius:8px;text-decoration:none;font-weight:700;margin:4px 4px">📧 뉴스레터 무료 구독</a>'
               if beehiiv_pub else "")
    kofi_btn = (f'<a href="https://ko-fi.com/{kofi}" target="_blank" '
                f'style="display:inline-block;background:#ff5e5b;color:#fff;padding:10px 22px;'
                f'border-radius:8px;text-decoration:none;font-weight:700;margin:4px 4px">☕ 커피 한 잔</a>'
                if kofi else "")
    return f"""
<div style="background:linear-gradient(135deg,#1e1b4b,#0f172a);border:1px solid #312e81;
            border-radius:14px;padding:28px 20px;margin:40px 0;text-align:center;color:#e2e8f0;
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <p style="font-size:1.5em;margin-bottom:6px">🤖</p>
  <h3 style="color:#a5b4fc;font-size:1.1em;margin:0 0 8px">매일 AI 수익화 전략 — 무료로 받기</h3>
  <p style="color:#94a3b8;font-size:.85em;margin:0 0 18px;line-height:1.6">
    실제 작동하는 AI 수익화 방법을 매일 아침 메일로 받아보세요
  </p>
  <div style="display:flex;flex-wrap:wrap;justify-content:center">
    {sub_btn}
    {kofi_btn}
    <a href="https://www.youtube.com/@psg9806" target="_blank"
       style="display:inline-block;background:#ff0000;color:#fff;padding:10px 22px;
              border-radius:8px;text-decoration:none;font-weight:700;margin:4px 4px">▶ YouTube 구독</a>
  </div>
</div>"""


def save_post(post: dict, output_dir: Path) -> Path:
    """포스트를 HTML 파일로 저장합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = post.get("slug", "post")[:50]

    cta_box = _build_post_cta()
    # HTML 파일
    html_path = output_dir / f"{ts}_{slug}.html"
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{post.get('meta_description', '')}">
<title>{post.get('title', 'Post')} | AI Income Daily</title>
<style>
body {{ font-family: Georgia, serif; max-width: 820px; margin: 0 auto; padding: 20px 20px 60px; line-height: 1.85; color: #1a1a2e; background: #f8fafc; }}
h1 {{ color: #0f172a; font-size: 2em; margin-bottom: 0.4em; line-height: 1.3; }}
h2 {{ color: #1e3a5f; font-size: 1.4em; margin-top: 2.2em; border-left: 4px solid #6366f1; padding-left: 12px; }}
h3 {{ color: #2d6a4f; font-size: 1.15em; margin-top: 1.6em; }}
a {{ color: #4f46e5; }}
a:hover {{ text-decoration: underline; }}
strong {{ color: #0f172a; }}
.meta {{ color: #6c757d; font-size: 0.85em; margin-bottom: 2em; }}
.tag {{ background: #e0e7ff; color: #4f46e5; border-radius: 4px; padding: 2px 8px; font-size: .75em; margin-right: 4px; font-family: sans-serif; }}
blockquote {{ border-left: 4px solid #6366f1; margin: 1.5em 0; padding: 12px 20px; background: #f0f4ff; border-radius: 0 8px 8px 0; }}
/* 어필리에이트 링크 강조 */
a[rel~="sponsored"] {{ color: #059669; font-weight: 600; }}
a[rel~="sponsored"]:hover {{ color: #047857; }}
/* 광고 박스 */
.ad-box {{ background: #fffbeb; border: 1px solid #fbbf24; border-radius: 10px; padding: 16px; margin: 24px 0; font-family: sans-serif; font-size: .88em; }}
.ad-box strong {{ color: #92400e; }}
</style>
</head>
<body>
<h1>{post.get('title', 'Post')}</h1>
<p class="meta">
  📅 {ts[:4]}-{ts[4:6]}-{ts[6:8]} &nbsp;|&nbsp;
  🏷 {''.join(f'<span class="tag">{t}</span>' for t in post.get('tags', []))}
</p>
{post.get('html', '')}
{cta_box}
</body>
</html>"""
    html_path.write_text(full_html)

    # 메타데이터 JSON
    meta_path = output_dir / f"{ts}_{slug}.json"
    meta_path.write_text(json.dumps({k: v for k, v in post.items() if k != 'html'},
                                     ensure_ascii=False, indent=2))

    return html_path


def publish_to_ghost(post: dict, ghost_url: str, ghost_api_key: str) -> str | None:
    """Ghost CMS에 포스트를 발행합니다 (선택사항)."""
    if not ghost_url or not ghost_api_key:
        return None
    try:
        headers = {
            "Authorization": f"Ghost {ghost_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "posts": [{
                "title": post["title"],
                "slug": post["slug"],
                "html": post["html"],
                "custom_excerpt": post["meta_description"],
                "tags": [{"name": t} for t in post.get("tags", [])],
                "status": "published",
            }]
        }
        resp = requests.post(f"{ghost_url}/ghost/api/admin/posts/",
                             headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        post_url = f"{ghost_url}/{post['slug']}/"
        print(f"  ✓ Published to Ghost: {post_url}")
        return post_url
    except Exception as e:
        print(f"  ⚠ Ghost publish failed: {e}")
        return None


def run(topic: str = None, count: int = 1):
    groq_key = os.environ.get("GROQ_API_KEY", "")
    ghost_url = os.environ.get("GHOST_URL", "")
    ghost_key = os.environ.get("GHOST_ADMIN_API_KEY", "")

    health = PipelineHealthCheck()

    if not topic:
        # 실시간 트렌드로 주제 선택 시도
        try:
            from research.trend_researcher import research as do_research
            print("🔍 Running trend research for blog topic...")
            result = do_research(groq_api_key=groq_key)
            topic = result["topic"]
            health.step_ok("트렌드 연구", f"주제: {topic[:50]}")
        except Exception as e:
            health.step_warn("트렌드 연구", str(e))
            topic = random.choice(TRENDING_TOPICS)

    print(f"\n📝 Generating: '{topic}'")
    try:
        post = generate_blog_post(topic, groq_key)
        post["html"] = insert_affiliate_links(post["html"])
        health.step_ok("포스트 생성", f"{post.get('word_count', '?')}단어")
    except Exception as e:
        health.step_fail("포스트 생성", str(e))
        notify_error("blog", f"Post generation failed: {e}")
        raise

    saved = save_post(post, OUTPUT_DIR)
    health.step_ok("파일 저장", saved.name)
    print(f"  ✓ Saved: {saved.name}")
    print(f"  ✓ Title: {post['title']}")
    print(f"  ✓ Words: ~{post.get('word_count', '?')}")

    ghost_post_url = publish_to_ghost(post, ghost_url, ghost_key)

    notify_success("blog", f"블로그 포스트 생성: {post['title'][:50]}")
    health.write_github_summary("블로그 포스트")

    return {"post": post, "file": str(saved), "ghost_url": ghost_post_url}


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    result = run(topic)
