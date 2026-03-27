"""
Dev.to 자동 발행 스크립트
=========================
scripts/blog/output/ 의 최신 HTML 파일을 읽어
Dev.to API로 자동 발행합니다.

필요한 환경변수:
  DEVTO_API_KEY  — https://dev.to/settings/extensions 에서 발급 (무료)
  GROQ_API_KEY   — 태그/요약 자동 생성용

Dev.to는 월 100만 UV 이상의 개발자 커뮤니티로, 포스트 하나당
AdSense 연동 없이도 canonical URL을 내 블로그로 지정해 SEO 트래픽을 가져올 수 있습니다.
"""

import os, sys, json, re, glob, requests
from pathlib import Path
from datetime import datetime

DEVTO_API = "https://dev.to/api/articles"
GROQ_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

BLOG_OUTPUT = Path(__file__).parent.parent / "blog" / "output"
PUBLISHED_LOG = Path(__file__).parent / ".devto_published.json"


def load_published() -> set:
    if PUBLISHED_LOG.exists():
        return set(json.loads(PUBLISHED_LOG.read_text()).get("published", []))
    return set()


def save_published(published: set):
    PUBLISHED_LOG.parent.mkdir(parents=True, exist_ok=True)
    PUBLISHED_LOG.write_text(json.dumps({"published": list(published)}, indent=2))


def html_to_markdown(html: str) -> str:
    """기본 HTML → Markdown 변환 (외부 라이브러리 불필요)."""
    md = html
    md = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', md, flags=re.S)
    md = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', md, flags=re.S)
    md = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', md, flags=re.S)
    md = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', md, flags=re.S)
    md = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', md, flags=re.S)
    md = re.sub(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', md, flags=re.S)
    md = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', md, flags=re.S)
    md = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', md, flags=re.S)
    md = re.sub(r'<[^>]+>', '', md)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip()


def groq_tags(title: str, groq_key: str) -> list:
    """Groq으로 Dev.to 태그 4개 생성."""
    try:
        resp = requests.post(GROQ_URL, headers={
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }, json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "Output a JSON array of exactly 4 dev.to tags (lowercase, no spaces, max 20 chars each). Common tags: webdev, productivity, ai, tutorial, career, beginners, javascript, python"},
                {"role": "user", "content": f"Title: {title}"}
            ],
            "max_tokens": 80, "temperature": 0.3
        }, timeout=30)
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r'```.*?```', '', raw, flags=re.S).strip()
        tags = json.loads(raw)
        return [str(t).lower().replace(" ", "")[:20] for t in tags[:4]]
    except Exception:
        return ["productivity", "ai", "tutorial", "career"]


def publish_to_devto(json_path: Path, html_path: Path, devto_key: str, groq_key: str) -> dict:
    """단일 포스트를 Dev.to에 발행합니다."""
    meta = json.loads(json_path.read_text())
    html = html_path.read_text()

    # body_html에서 실제 본문 부분만 추출
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.S)
    body_html = body_match.group(1) if body_match else html
    # h1, meta 태그 등 제거하고 본문만
    body_html = re.sub(r'<h1[^>]*>.*?</h1>', '', body_html, flags=re.S)
    body_html = re.sub(r'<p class="meta"[^>]*>.*?</p>', '', body_html, flags=re.S)
    body_md = html_to_markdown(body_html)

    tags = groq_tags(meta.get("title", ""), groq_key)

    payload = {
        "article": {
            "title": meta.get("title", "Untitled"),
            "body_markdown": body_md,
            "published": True,
            "tags": tags,
            "description": meta.get("meta_description", "")[:160],
            "canonical_url": "",  # 본인 블로그 URL 있으면 여기 입력
        }
    }

    resp = requests.post(DEVTO_API, headers={
        "api-key": devto_key,
        "Content-Type": "application/json"
    }, json=payload, timeout=30)

    if resp.status_code in (200, 201):
        data = resp.json()
        print(f"  ✓ Dev.to published: {data.get('url', '')} | {meta['title'][:50]}")
        return data
    else:
        print(f"  ✗ Dev.to failed {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()


def run():
    devto_key = os.environ.get("DEVTO_API_KEY", "")
    groq_key  = os.environ.get("GROQ_API_KEY", "")

    if not devto_key:
        print("DEVTO_API_KEY not set — skipping Dev.to publish")
        return

    published = load_published()
    json_files = sorted(BLOG_OUTPUT.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not json_files:
        print("No blog posts found in output directory.")
        return

    posted = 0
    for jf in json_files[:3]:  # 최대 3개 (API rate limit 고려)
        stem = jf.stem
        if stem in published:
            print(f"  - Already published: {stem[:60]}")
            continue
        html_f = jf.with_suffix(".html")
        if not html_f.exists():
            continue
        try:
            publish_to_devto(jf, html_f, devto_key, groq_key)
            published.add(stem)
            posted += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")

    save_published(published)
    print(f"\n✅ Dev.to: {posted}개 포스트 발행 완료")


if __name__ == "__main__":
    run()
