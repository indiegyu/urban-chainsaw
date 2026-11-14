"""
Medium 자동 발행 스크립트
=========================
Medium Integration API를 사용해 블로그 포스트를 Medium에 자동 발행합니다.
Medium은 월 1억 명 이상의 독자를 보유한 플랫폼으로,
Partner Program 참여 시 읽기 수에 비례한 수익 (월 $100~$1000+) 을 제공합니다.

필요한 환경변수:
  MEDIUM_TOKEN    — https://medium.com/me/settings 에서 Integration Token 발급
  GEMINI_API_KEY  — 태그 자동 생성용 (무료 티어, 선택)
"""

import os, sys, json, re, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import complete as llm_complete, extract_json  # noqa: E402

MEDIUM_API = "https://api.medium.com/v1"

BLOG_OUTPUT   = Path(__file__).parent.parent / "blog" / "output"
PUBLISHED_LOG = Path(__file__).parent / ".medium_published.json"


def load_published() -> set:
    if PUBLISHED_LOG.exists():
        return set(json.loads(PUBLISHED_LOG.read_text()).get("published", []))
    return set()


def save_published(published: set):
    PUBLISHED_LOG.parent.mkdir(parents=True, exist_ok=True)
    PUBLISHED_LOG.write_text(json.dumps({"published": list(published)}, indent=2))


def get_medium_user_id(token: str) -> str:
    resp = requests.get(f"{MEDIUM_API}/me",
                        headers={"Authorization": f"Bearer {token}"}, timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]["id"]


def llm_tags(title: str) -> list:
    default_tags = ["Productivity", "Technology", "Side Hustle", "AI", "Make Money Online"]
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GROQ_API_KEY"):
        return default_tags
    try:
        raw = llm_complete(
            [
                {"role": "system", "content": "Output a JSON array of exactly 5 Medium tags (title case, max 25 chars). Examples: Productivity, Artificial Intelligence, Make Money Online, Side Hustle, Technology"},
                {"role": "user", "content": f"Title: {title}"},
            ],
            max_tokens=100,
            temperature=0.3,
            json_mode=True,
        )
        tags = extract_json(raw)
        if isinstance(tags, dict):
            tags = tags.get("tags", [])
        return tags[:5] or default_tags
    except Exception:
        return default_tags


def publish_to_medium(json_path: Path, html_path: Path,
                      user_id: str, token: str) -> dict:
    meta = json.loads(json_path.read_text())
    html = html_path.read_text()

    # body만 추출
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.S)
    body = body_match.group(1) if body_match else html

    tags = llm_tags(meta.get("title", ""))

    payload = {
        "title": meta.get("title", "Untitled"),
        "contentFormat": "html",
        "content": body,
        "tags": tags,
        "publishStatus": "public",
        "notifyFollowers": True,
    }

    resp = requests.post(
        f"{MEDIUM_API}/users/{user_id}/posts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload, timeout=30
    )

    if resp.status_code in (200, 201):
        data = resp.json()["data"]
        print(f"  ✓ Medium published: {data.get('url', '')} | {meta['title'][:50]}")
        return data
    else:
        print(f"  ✗ Medium failed {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()


def run():
    token    = os.environ.get("MEDIUM_TOKEN", "")

    if not token:
        print("MEDIUM_TOKEN not set — skipping Medium publish")
        return

    published = load_published()
    json_files = sorted(BLOG_OUTPUT.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not json_files:
        print("No blog posts found.")
        return

    try:
        user_id = get_medium_user_id(token)
    except Exception as e:
        print(f"  ✗ Medium auth failed: {e}")
        return

    posted = 0
    for jf in json_files[:2]:  # 하루 2개 (스팸 방지)
        stem = jf.stem
        if stem in published:
            print(f"  - Already published: {stem[:60]}")
            continue
        html_f = jf.with_suffix(".html")
        if not html_f.exists():
            continue
        try:
            publish_to_medium(jf, html_f, user_id, token)
            published.add(stem)
            posted += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")

    save_published(published)
    print(f"\n✅ Medium: {posted}개 포스트 발행 완료")


if __name__ == "__main__":
    run()
