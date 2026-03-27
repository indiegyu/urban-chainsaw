"""
실시간 트렌드 연구: Google Trends + YouTube 검색 + Reddit
=========================================================
각 무료 소스에서 AI/수익화 관련 인기 주제를 수집하고
Groq이 최적 YouTube 영상 주제를 선정합니다.

무료 소스:
  - pytrends   (Google Trends 비공식 API, 키 불필요)
  - YouTube Data API v3 search.list  (API key 또는 OAuth token)
  - Reddit JSON API  (인증 불필요, 공개 피드)
"""

import os
import json
import time
import requests
from pathlib import Path

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
GROQ_API         = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL       = "llama-3.3-70b-versatile"

STRATEGY_PATH = Path(__file__).parent.parent / "strategy" / "content_strategy.json"

def _load_strategy_keywords() -> list[str]:
    """content_strategy.json의 target_cpm_keywords를 로드합니다."""
    try:
        s = json.loads(STRATEGY_PATH.read_text())
        kw = s.get("target_cpm_keywords", [])
        topics = s.get("top_performing_topics", [])
        combined = [f"{t} 2026" for t in topics[:2]] + kw[:3]
        return combined[:5] if combined else SEARCH_KEYWORDS
    except Exception:
        return SEARCH_KEYWORDS

SEARCH_KEYWORDS = [
    "AI tools make money 2026",
    "passive income automation 2026",
    "ChatGPT side hustle",
    "faceless YouTube income",
    "AI side hustle beginner",
]

REDDIT_SUBS = ["passive_income", "ChatGPT", "sidehustle", "AItools", "entrepreneur"]

# 폴백 주제 (모든 소스 실패 시)
FALLBACK_TOPICS = [
    "7 AI tools that pay $500 per month in 2026",
    "How I make $3000/month with ChatGPT automation",
    "5 passive income streams using free AI tools",
    "Build a faceless YouTube channel with AI in 1 hour",
    "The $0 AI business model that actually works in 2026",
    "10 side hustles you can start with ChatGPT this week",
]


def _yt_search_oauth(keyword: str, token_path: str = "token.json") -> list[str]:
    """OAuth token으로 YouTube search.list 호출 (별도 API key 불필요)."""
    try:
        tok = json.loads(Path(token_path).read_text())
        access_token = tok.get("token") or tok.get("access_token", "")
        if not access_token:
            return []
        r = requests.get(f"{YOUTUBE_API_BASE}/search", params={
            "part": "snippet", "q": keyword,
            "order": "viewCount", "type": "video",
            "publishedAfter": "2025-10-01T00:00:00Z",
            "maxResults": 8,
        }, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        if r.status_code == 200:
            return [i["snippet"]["title"] for i in r.json().get("items", [])]
    except Exception:
        pass
    return []


def _yt_search_apikey(keyword: str, api_key: str) -> list[str]:
    """단순 API key로 YouTube search.list 호출."""
    try:
        r = requests.get(f"{YOUTUBE_API_BASE}/search", params={
            "part": "snippet", "q": keyword,
            "order": "viewCount", "type": "video",
            "publishedAfter": "2025-10-01T00:00:00Z",
            "maxResults": 8, "key": api_key,
        }, timeout=10)
        if r.status_code == 200:
            return [i["snippet"]["title"] for i in r.json().get("items", [])]
    except Exception:
        pass
    return []


def _reddit_hot(subreddit: str) -> list[dict]:
    """Reddit 공개 JSON에서 핫 포스트 수집 (인증 불필요)."""
    try:
        r = requests.get(
            f"https://www.reddit.com/r/{subreddit}/hot.json?limit=8",
            headers={"User-Agent": "trend-research-bot/1.0"},
            timeout=8,
        )
        if r.status_code == 200:
            return [
                {"title": p["data"]["title"], "score": p["data"]["score"]}
                for p in r.json()["data"]["children"]
                if not p["data"].get("stickied")
            ]
    except Exception:
        pass
    return []


def _google_trends(keywords: list[str]) -> dict[str, int]:
    """pytrends로 지난 7일 Google 관심도 점수를 반환합니다."""
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 25), retries=2, backoff_factor=0.5)
        batch = keywords[:5]
        pt.build_payload(batch, timeframe="now 7-d")
        time.sleep(2)
        df = pt.interest_over_time()
        if not df.empty:
            return {kw: int(df[kw].mean()) for kw in batch if kw in df.columns}
    except Exception as e:
        print(f"  ⚠ pytrends: {e}")
    return {}


def pick_best_topic(research_data: dict, groq_api_key: str) -> str:
    """Groq에게 연구 데이터를 주고 최적 YouTube 주제를 AI로 선정합니다."""
    context_parts = []

    yt_titles = research_data.get("youtube_titles", [])
    if yt_titles:
        context_parts.append("CURRENTLY HIGH-VIEW YOUTUBE VIDEOS IN NICHE:\n" +
                             "\n".join(f"  - {t}" for t in yt_titles[:8]))

    reddit_hot = research_data.get("reddit_hot", [])
    if reddit_hot:
        top_reddit = sorted(reddit_hot, key=lambda x: x.get("score", 0), reverse=True)[:5]
        context_parts.append("TRENDING ON REDDIT (upvotes):\n" +
                             "\n".join(f"  - {p['title']} ({p['score']} pts)"
                                       for p in top_reddit))

    trends = research_data.get("trends", {})
    if trends:
        top = sorted(trends.items(), key=lambda x: x[1], reverse=True)[:5]
        context_parts.append("GOOGLE SEARCH INTEREST (7-day avg, 0-100):\n" +
                             "\n".join(f"  {kw}: {score}" for kw, score in top))

    context = "\n\n".join(context_parts) if context_parts else "No external data. Use best judgment."

    try:
        r = requests.post(GROQ_API, headers={
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
        }, json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": (
                    "You are a YouTube growth strategist. Pick the single BEST video topic for a faceless "
                    "AI/passive income channel that will maximize views and ad revenue. "
                    "Criteria: (1) high search volume keyword in title, (2) advertiser-friendly category "
                    "(finance/business/AI = high CPM $8-20), (3) promise/benefit is crystal clear, "
                    "(4) contains a specific number or dollar amount for credibility. "
                    "Output ONLY the video topic as one sentence, max 80 characters. No quotes, no explanation."
                )},
                {"role": "user", "content": (
                    f"Based on this real-time data, pick the BEST YouTube video topic:\n\n{context}"
                )},
            ],
            "temperature": 0.7,
            "max_tokens": 100,
        }, timeout=30)
        if r.status_code == 200:
            topic = r.json()["choices"][0]["message"]["content"].strip().strip('"').strip("'")
            return topic
    except Exception as e:
        print(f"  ⚠ Groq topic selection failed: {e}")

    # 폴백: 트렌드 상위 키워드 기반
    if trends:
        top_kw = sorted(trends.items(), key=lambda x: x[1], reverse=True)[0][0]
        return f"How to make passive income with {top_kw} in 2026"
    if yt_titles:
        return f"5 AI income strategies beating these: {yt_titles[0][:40]}"
    import random
    return random.choice(FALLBACK_TOPICS)


def research(groq_api_key: str = None, youtube_api_key: str = None) -> dict:
    """
    전체 트렌드 연구 수행 후 최적 주제 + SEO 컨텍스트를 반환합니다.

    Returns:
        topic        (str)  Groq이 선정한 최적 주제
        seo_context  (str)  스크립트 생성 시 Groq에 주입할 SEO 힌트
        raw          (dict) 수집된 원본 데이터
    """
    groq_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
    yt_key   = youtube_api_key or os.environ.get("YOUTUBE_API_KEY", "")

    # 전략 파일 기반 키워드 사용 (성과 기반으로 진화)
    keywords = _load_strategy_keywords()

    print("🔍 Researching trending topics...")

    # 1. YouTube 검색 (API key → OAuth token 순으로 시도)
    youtube_titles = []
    if yt_key:
        for kw in keywords[:2]:
            youtube_titles.extend(_yt_search_apikey(kw, yt_key))
            time.sleep(0.4)
    else:
        for kw in keywords[:2]:
            youtube_titles.extend(_yt_search_oauth(kw))
            time.sleep(0.4)

    print(f"  ✓ YouTube: {len(youtube_titles)} trending titles")

    # 2. Reddit 핫 포스트
    reddit_posts = []
    for sub in REDDIT_SUBS[:3]:
        reddit_posts.extend(_reddit_hot(sub))
        time.sleep(0.3)
    print(f"  ✓ Reddit: {len(reddit_posts)} hot posts")

    # 3. Google 트렌드 (pytrends)
    trends = _google_trends(SEARCH_KEYWORDS)
    print(f"  ✓ Google Trends: {len(trends)} keywords scored")

    raw = {"youtube_titles": youtube_titles, "reddit_hot": reddit_posts, "trends": trends}

    # 4. Groq으로 최적 주제 AI 선정
    topic = pick_best_topic(raw, groq_key)
    print(f"  ✅ Topic selected: {topic[:70]}")

    # 5. SEO 컨텍스트 구성 (스크립트 생성 Groq 프롬프트에 삽입됨)
    seo_lines = []
    if youtube_titles:
        seo_lines.append("TOP YOUTUBE TITLES IN NICHE (for title/tag inspiration):")
        seo_lines.extend(f"  · {t}" for t in youtube_titles[:5])
    if trends:
        top3 = sorted(trends.items(), key=lambda x: x[1], reverse=True)[:3]
        seo_lines.append("TRENDING SEARCH TERMS: " + " | ".join(kw for kw, _ in top3))

    return {
        "topic": topic,
        "seo_context": "\n".join(seo_lines),
        "raw": raw,
    }


if __name__ == "__main__":
    result = research()
    print("\n--- Research Result ---")
    print(f"Topic:       {result['topic']}")
    print(f"SEO Context:\n{result['seo_context']}")
