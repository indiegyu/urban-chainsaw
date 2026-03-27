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

# Affiliate 링크 매핑 (실제 링크로 교체 필요)
AFFILIATE_LINKS = {
    "n8n":        "https://n8n.io/?ref=YOURID",
    "hostinger":  "https://hostinger.com/affiliate",
    "convertkit": "https://convertkit.com/?lmref=YOURID",
    "beehiiv":    "https://beehiiv.com/partner/YOURID",
    "printify":   "https://printify.com/app/register?referrer=YOURID",
}


def _groq_request(messages: list, groq_api_key: str, max_tokens: int = 2048) -> str:
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
    resp = requests.post(
        GROQ_API_URL,
        headers=headers,
        json={"model": GROQ_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": max_tokens},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


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
    meta = json.loads(meta_raw)

    # Step 2: HTML 본문만 (JSON 불필요, 그냥 텍스트)
    html_content = _groq_request([
        {"role": "system", "content": (
            "Write a complete SEO blog post in clean HTML (body tags only). "
            "Structure: intro paragraph, 4-5 H2 sections (each 150-200 words), conclusion with CTA. "
            "Total ~1000 words. Use <strong> for emphasis. "
            "Where tools like n8n, hostinger, convertkit, beehiiv, or printify are mentioned, "
            "wrap them like: {{AFFILIATE:toolname}}"
        )},
        {"role": "user", "content": f"Write about: {topic}"},
    ], groq_api_key, max_tokens=3000)

    meta["html"] = html_content
    meta["word_count"] = len(html_content.split())
    return meta


def insert_affiliate_links(html: str) -> str:
    """{{AFFILIATE:tool}} 플레이스홀더를 실제 링크로 교체합니다."""
    import re
    def replace_affiliate(match):
        tool = match.group(1).lower().strip()
        url = AFFILIATE_LINKS.get(tool, "#")
        return f'<a href="{url}" target="_blank" rel="noopener sponsored">{tool}</a>'
    return re.sub(r'\{\{AFFILIATE:([^}]+)\}\}', replace_affiliate, html)


def save_post(post: dict, output_dir: Path) -> Path:
    """포스트를 HTML 파일로 저장합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = post.get("slug", "post")[:50]

    # HTML 파일
    html_path = output_dir / f"{ts}_{slug}.html"
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{post.get('meta_description', '')}">
<title>{post.get('title', 'Post')}</title>
<style>
body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; }}
h1 {{ color: #1a1a2e; font-size: 2em; margin-bottom: 0.5em; }}
h2 {{ color: #2d6a4f; font-size: 1.5em; margin-top: 2em; }}
a {{ color: #e94560; }}
strong {{ color: #1a1a2e; }}
.meta {{ color: #6c757d; font-size: 0.9em; margin-bottom: 2em; }}
</style>
</head>
<body>
<h1>{post.get('title', 'Post')}</h1>
<p class="meta">Tags: {', '.join(post.get('tags', []))}</p>
{post.get('html', '')}
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

    if not topic:
        # 실시간 트렌드로 주제 선택 시도
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from research.trend_researcher import research as do_research
            print("🔍 Running trend research for blog topic...")
            result = do_research(groq_api_key=groq_key)
            topic = result["topic"]
            print(f"  📊 Trend-selected: '{topic[:60]}'")
        except Exception as e:
            print(f"  ⚠ Trend research failed ({e}), using static topic")
            topic = random.choice(TRENDING_TOPICS)

    print(f"\n📝 Generating: '{topic}'")
    post = generate_blog_post(topic, groq_key)
    post["html"] = insert_affiliate_links(post["html"])

    saved = save_post(post, OUTPUT_DIR)
    print(f"  ✓ Saved: {saved.name}")
    print(f"  ✓ Title: {post['title']}")
    print(f"  ✓ Words: ~{post.get('word_count', '?')}")

    ghost_post_url = publish_to_ghost(post, ghost_url, ghost_key)

    return {"post": post, "file": str(saved), "ghost_url": ghost_post_url}


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    result = run(topic)
