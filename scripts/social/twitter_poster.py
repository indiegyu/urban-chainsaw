"""
Twitter/X 자동 포스팅 스크립트
================================
블로그 포스트와 YouTube 영상 링크를 Twitter/X에 자동 공유합니다.

Twitter API v2 무료 티어:
  - 월 1,500 트윗 작성
  - 앱 등록: https://developer.twitter.com/

수익화 경로:
  - 블로그 트래픽 → AdSense 수익
  - YouTube 클릭 → 구독자 → AdSense
  - Affiliate 링크 트윗 (직접)

필요한 환경변수:
  TWITTER_BEARER_TOKEN  — API Bearer Token
  TWITTER_API_KEY       — API Key (Consumer Key)
  TWITTER_API_SECRET    — API Secret
  TWITTER_ACCESS_TOKEN  — Access Token
  TWITTER_ACCESS_SECRET — Access Token Secret
"""

import os, json, re, time, requests, hmac, hashlib, base64, urllib.parse
from pathlib import Path
from datetime import datetime

BLOG_OUTPUT  = Path(__file__).parent.parent / "blog" / "output"
POSTED_LOG   = Path(__file__).parent / ".twitter_posted.json"
PAGES_URL    = os.environ.get("GITHUB_PAGES_URL", "").rstrip("/")
YOUTUBE_CH   = os.environ.get("YOUTUBE_CHANNEL_URL", "")

TWEET_TEMPLATES = [
    "🤖 {title}\n\n{hook}\n\nRead more 👇\n{url}\n\n#AI #SideHustle #MakeMoneyOnline",
    "💡 {title}\n\n{hook}\n\n{url}\n\n#PassiveIncome #AITools #Productivity",
    "🚀 New post: {title}\n\n{hook}\n\n{url}\n\n#Entrepreneur #AI #Tech",
    "📈 {title}\n\n{hook}\n\n🔗 {url}\n\n#MakeMoneyOnline #AIAutomation",
]


def load_posted() -> set:
    if POSTED_LOG.exists():
        return set(json.loads(POSTED_LOG.read_text()).get("posted", []))
    return set()


def save_posted(posted: set):
    POSTED_LOG.parent.mkdir(parents=True, exist_ok=True)
    POSTED_LOG.write_text(json.dumps({"posted": list(posted)}, indent=2))


def oauth1_header(method: str, url: str, params: dict,
                  api_key: str, api_secret: str,
                  access_token: str, access_secret: str) -> str:
    """OAuth 1.0a 헤더 생성."""
    import time, uuid
    oauth_params = {
        "oauth_consumer_key":     api_key,
        "oauth_nonce":            uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_token":            access_token,
        "oauth_version":          "1.0",
    }
    all_params = {**params, **oauth_params}
    sorted_params = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )
    base_str = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(sorted_params, safe=""),
    ])
    signing_key = f"{urllib.parse.quote(api_secret, safe='')}&{urllib.parse.quote(access_secret, safe='')}"
    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base_str.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_params["oauth_signature"] = sig
    header = "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(str(v), safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
    return header


def post_tweet(text: str, api_key: str, api_secret: str,
               access_token: str, access_secret: str) -> dict:
    url = "https://api.twitter.com/2/tweets"
    payload = {"text": text[:280]}
    auth = oauth1_header("POST", url, {}, api_key, api_secret, access_token, access_secret)
    resp = requests.post(url, headers={
        "Authorization": auth,
        "Content-Type": "application/json"
    }, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def make_tweet(title: str, meta_desc: str, url: str, idx: int = 0) -> str:
    # 훅: 설명에서 첫 문장 추출
    hook = (meta_desc or "").split(".")[0][:100]
    template = TWEET_TEMPLATES[idx % len(TWEET_TEMPLATES)]
    tweet = template.format(title=title[:80], hook=hook, url=url)
    return tweet[:280]


def run():
    api_key       = os.environ.get("TWITTER_API_KEY", "")
    api_secret    = os.environ.get("TWITTER_API_SECRET", "")
    access_token  = os.environ.get("TWITTER_ACCESS_TOKEN", "")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("Twitter credentials not set — skipping")
        print("  Set: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET")
        return

    if not PAGES_URL:
        print("GITHUB_PAGES_URL not set — skipping Twitter")
        return

    posted = load_posted()
    json_files = sorted(BLOG_OUTPUT.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    total = 0
    for i, jf in enumerate(json_files[:3]):  # 하루 3개 트윗
        stem = jf.stem
        if stem in posted:
            print(f"  - Already tweeted: {stem[:50]}")
            continue
        html_f = jf.with_suffix(".html")
        if not html_f.exists():
            continue

        meta  = json.loads(jf.read_text())
        title = meta.get("title", "")
        desc  = meta.get("meta_description", "")
        url   = f"{PAGES_URL}/{html_f.name}"
        tweet = make_tweet(title, desc, url, i)

        try:
            result = post_tweet(tweet, api_key, api_secret, access_token, access_secret)
            tweet_id = result.get("data", {}).get("id", "?")
            print(f"  ✓ Tweeted: {title[:50]} (id:{tweet_id})")
            posted.add(stem)
            total += 1
            time.sleep(3)
        except Exception as e:
            print(f"  ✗ Tweet failed: {e}")

    # YouTube 채널 홍보 트윗 (주 1회)
    if YOUTUBE_CH and total == 0:
        promo = f"🎬 New AI tips video is up on our YouTube channel!\n\nSubscribe for daily automated income tips 👇\n{YOUTUBE_CH}\n\n#YouTube #AI #PassiveIncome"
        try:
            post_tweet(promo, api_key, api_secret, access_token, access_secret)
            print(f"  ✓ YouTube promo tweet posted")
            total += 1
        except Exception as e:
            print(f"  ✗ Promo tweet failed: {e}")

    save_posted(posted)
    print(f"\n✅ Twitter: {total}개 트윗 완료")


if __name__ == "__main__":
    run()
