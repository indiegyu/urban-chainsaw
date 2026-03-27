"""
Reddit 자동 트래픽 생성기
==========================
블로그 포스트 / YouTube 영상을 관련 서브레딧에 자동 공유합니다.

중요: Reddit 스팸 정책 준수 필수
  - 동일 링크 반복 금지
  - 가치 있는 정보 위주 (링크 + 설명)
  - 계정 karma 50+ 필요 (초기 수동 활동 필요)
  - 서브레딧당 하루 1~2개 최대

Reddit 앱 등록: https://www.reddit.com/prefs/apps
  → "script" 타입으로 앱 생성

필요한 환경변수:
  REDDIT_CLIENT_ID     — 앱 client_id
  REDDIT_CLIENT_SECRET — 앱 secret
  REDDIT_USERNAME      — Reddit 계정
  REDDIT_PASSWORD      — Reddit 비밀번호
  GROQ_API_KEY         — 포스트 제목 최적화용
"""

import os, json, re, time, requests
from pathlib import Path

BLOG_OUTPUT  = Path(__file__).parent.parent / "blog" / "output"
POSTED_LOG   = Path(__file__).parent / ".reddit_posted.json"
PAGES_URL    = os.environ.get("GITHUB_PAGES_URL", "").rstrip("/")
YOUTUBE_CH   = os.environ.get("YOUTUBE_CHANNEL_URL", "")

# 가치 있는 콘텐츠를 허용하는 서브레딧 목록 (규칙 확인 필수)
SUBREDDITS = {
    "passive income blog": [
        "r/passive_income",
        "r/sidehustle",
        "r/Entrepreneur",
    ],
    "ai tools blog": [
        "r/artificial",
        "r/ChatGPT",
        "r/MachineLearning",
    ],
    "make money online blog": [
        "r/beermoney",
        "r/WorkOnline",
        "r/digitalnomad",
    ],
    "youtube automation blog": [
        "r/NewTubers",
        "r/youtubehaiku",
        "r/EntrepreneurRideAlong",
    ],
}

USER_AGENT = "urban-chainsaw-bot/1.0 (educational automation project)"


def get_reddit_token(client_id: str, client_secret: str,
                     username: str, password: str) -> str:
    resp = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client_id, client_secret),
        data={"grant_type": "password", "username": username, "password": password},
        headers={"User-Agent": USER_AGENT},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def load_posted() -> dict:
    if POSTED_LOG.exists():
        return json.loads(POSTED_LOG.read_text())
    return {}


def save_posted(posted: dict):
    POSTED_LOG.parent.mkdir(parents=True, exist_ok=True)
    POSTED_LOG.write_text(json.dumps(posted, indent=2))


def find_best_subreddits(title: str) -> list:
    """제목 키워드로 적합한 서브레딧 선택."""
    title_lower = title.lower()
    for keyword, subs in SUBREDDITS.items():
        if any(w in title_lower for w in keyword.split()):
            return subs[:2]  # 최대 2개
    return ["r/passive_income", "r/sidehustle"]


def submit_link(token: str, subreddit: str, title: str, url: str) -> dict:
    headers = {"Authorization": f"bearer {token}", "User-Agent": USER_AGENT}
    resp = requests.post(
        "https://oauth.reddit.com/api/submit",
        headers=headers,
        data={
            "sr": subreddit.lstrip("r/"),
            "kind": "link",
            "title": title[:300],
            "url": url,
            "resubmit": False,
            "nsfw": False,
            "spoiler": False,
        },
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("success") or (isinstance(data, dict) and "jquery" not in str(data)):
        return data
    # Error check
    errors = data.get("json", {}).get("errors", [])
    if errors:
        raise ValueError(f"Reddit error: {errors}")
    return data


def run():
    client_id     = os.environ.get("REDDIT_CLIENT_ID", "")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
    username      = os.environ.get("REDDIT_USERNAME", "")
    password      = os.environ.get("REDDIT_PASSWORD", "")

    if not all([client_id, client_secret, username, password]):
        print("Reddit credentials not set — skipping")
        print("  Set: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD")
        return

    if not PAGES_URL:
        print("GITHUB_PAGES_URL not set — can't build post URLs")
        return

    try:
        token = get_reddit_token(client_id, client_secret, username, password)
    except Exception as e:
        print(f"  ✗ Reddit auth failed: {e}")
        return

    posted = load_posted()
    json_files = sorted(BLOG_OUTPUT.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    total_posted = 0
    for jf in json_files[:5]:  # 최신 5개 검사
        stem = jf.stem
        if posted.get(stem):
            print(f"  - Already posted: {stem[:50]}")
            continue

        html_f = jf.with_suffix(".html")
        if not html_f.exists():
            continue

        meta = json.loads(jf.read_text())
        title = meta.get("title", "")
        url   = f"{PAGES_URL}/{html_f.name}"
        subs  = find_best_subreddits(title)

        for subreddit in subs[:1]:  # 하루 서브레딧당 1개
            try:
                result = submit_link(token, subreddit, title, url)
                print(f"  ✓ Posted to {subreddit}: {title[:50]}")
                posted[stem] = {"subreddit": subreddit, "url": url}
                total_posted += 1
                time.sleep(2)  # Rate limit
                break
            except Exception as e:
                print(f"  ✗ {subreddit} failed: {e}")

    save_posted(posted)
    print(f"\n✅ Reddit: {total_posted}개 포스트 공유 완료")


if __name__ == "__main__":
    run()
