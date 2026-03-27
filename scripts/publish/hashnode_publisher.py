"""
Hashnode 자동 크로스포스팅
===========================
블로그 포스트를 Hashnode에 자동 발행합니다.
Hashnode = 개발자/AI 커뮤니티 1억 UV/월, SEO 트래픽 + 파트너 수익

수익 경로:
  - Hashnode 자체 광고 수익 (Hashnode Pro 이상, 또는 자체 광고 삽입)
  - canonical URL로 내 블로그 SEO 강화 → AdSense 수익 증가
  - 팔로워 → 내 Lemon Squeezy 상품으로 유도

필요한 환경변수:
  HASHNODE_ACCESS_TOKEN  — https://hashnode.com/settings/developer 에서 발급 (무료)
  HASHNODE_PUBLICATION_ID — 내 블로그 Publication ID (hashnode.com/settings/developer)
  GITHUB_PAGES_URL       — canonical URL (예: https://indiegyu.github.io/urban-chainsaw)
"""

import os, json, re, glob, requests
from pathlib import Path
from datetime import datetime

HASHNODE_GQL = "https://gql.hashnode.com/"
BLOG_OUTPUT  = Path(__file__).parent.parent / "blog" / "output"
PUBLISHED_LOG = Path(__file__).parent / ".hashnode_published.json"
STRATEGY_FILE = Path(__file__).parent.parent / "strategy" / "content_strategy.json"


def load_published() -> set:
    if PUBLISHED_LOG.exists():
        return set(json.loads(PUBLISHED_LOG.read_text()).get("published", []))
    return set()


def save_published(published: set):
    PUBLISHED_LOG.write_text(json.dumps({"published": list(published)}, indent=2))


def html_to_markdown(html: str) -> str:
    """간단한 HTML→Markdown 변환 (Hashnode는 Markdown 사용)"""
    md = html
    # 헤딩
    md = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1", md, flags=re.DOTALL)
    md = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1", md, flags=re.DOTALL)
    md = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1", md, flags=re.DOTALL)
    # 굵기/이탤릭
    md = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", md, flags=re.DOTALL)
    md = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", md, flags=re.DOTALL)
    md = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", md, flags=re.DOTALL)
    # 링크
    md = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", md, flags=re.DOTALL)
    # 리스트
    md = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1", md, flags=re.DOTALL)
    md = re.sub(r"<[uo]l[^>]*>|</[uo]l>", "", md)
    # 단락
    md = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", md, flags=re.DOTALL)
    # 나머지 태그 제거
    md = re.sub(r"<[^>]+>", "", md)
    # 연속 빈줄 정리
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def get_tags_from_strategy() -> list[str]:
    """content_strategy.json에서 태그 추출"""
    if STRATEGY_FILE.exists():
        try:
            data = json.loads(STRATEGY_FILE.read_text())
            topics = data.get("top_performing_topics", [])
            tags = []
            for t in topics[:5]:
                slug = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
                tags.append(slug)
            return tags or ["ai", "passive-income", "make-money-online"]
        except Exception:
            pass
    return ["ai", "passive-income", "side-hustle", "chatgpt", "automation"]


def publish_post(post: dict, token: str, pub_id: str, canonical_url: str = "") -> str | None:
    """Hashnode GraphQL API로 포스트 발행"""
    tags = get_tags_from_strategy()
    content_md = html_to_markdown(post.get("html", post.get("content", "")))

    # Lemon Squeezy 상품 링크 CTA 추가
    cta = "\n\n---\n\n## 🚀 무료 AI 수익화 툴킷\n\n"
    cta += "AI로 매달 수익을 만들고 싶다면 → **[무료 ChatGPT 프롬프트 팩 받기](https://indiegyu.github.io/urban-chainsaw/)**\n\n"
    cta += "📊 **[실시간 수익 대시보드 보기](https://indiegyu.github.io/urban-chainsaw/dashboard.html)**\n"
    content_md += cta

    mutation = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post {
          id
          url
          title
        }
      }
    }
    """
    variables = {
        "input": {
            "title": post["title"],
            "contentMarkdown": content_md,
            "publicationId": pub_id,
            "tags": [{"slug": t, "name": t.replace("-", " ").title()} for t in tags[:5]],
            **({"originalArticleURL": canonical_url} if canonical_url else {}),
        }
    }

    try:
        resp = requests.post(
            HASHNODE_GQL,
            json={"query": mutation, "variables": variables},
            headers={"Authorization": token, "Content-Type": "application/json"},
            timeout=30,
        )
        data = resp.json()
        if "errors" in data:
            print(f"  ⚠ Hashnode error: {data['errors'][0]['message']}")
            return None
        post_url = data["data"]["publishPost"]["post"]["url"]
        print(f"  ✓ Published to Hashnode: {post_url}")
        return post_url
    except Exception as e:
        print(f"  ⚠ Hashnode publish failed: {e}")
        return None


def run():
    token = os.environ.get("HASHNODE_ACCESS_TOKEN", "")
    pub_id = os.environ.get("HASHNODE_PUBLICATION_ID", "")
    pages_url = os.environ.get("GITHUB_PAGES_URL", "https://indiegyu.github.io/urban-chainsaw")

    if not token or not pub_id:
        print("⏭ HASHNODE_ACCESS_TOKEN 또는 HASHNODE_PUBLICATION_ID 미설정 — 건너뜀")
        return

    html_files = sorted(BLOG_OUTPUT.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not html_files:
        print("⚠ 발행할 블로그 포스트가 없습니다")
        return

    published = load_published()
    published_count = 0

    for html_file in html_files[:3]:  # 최신 3개만 확인
        if html_file.name in published:
            continue

        try:
            content = html_file.read_text(encoding="utf-8")
            # 메타 데이터 파싱
            title_m = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE)
            desc_m = re.search(r'<meta name="description" content="([^"]+)"', content, re.IGNORECASE)
            title = title_m.group(1) if title_m else html_file.stem.replace("-", " ").title()
            canonical = f"{pages_url}/blog/{html_file.stem}.html"

            post = {"title": title, "html": content}
            post_url = publish_post(post, token, pub_id, canonical)

            if post_url:
                published.add(html_file.name)
                published_count += 1
                save_published(published)

        except Exception as e:
            print(f"  ⚠ {html_file.name}: {e}")

    if published_count == 0:
        print("⏭ 새로 발행할 포스트 없음 (이미 모두 발행됨)")
    else:
        print(f"✅ Hashnode 발행 완료: {published_count}개")


if __name__ == "__main__":
    run()
