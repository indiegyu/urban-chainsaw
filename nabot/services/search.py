"""
Search adapters for each source.
Each function returns a list of dicts: {title, snippet, url, source}

Sources:
  naver   - 네이버 뉴스 + 블로그 (동적 쿼리, 무료 25,000/일)
  google  - Google Custom Search API (동적 쿼리, 무료 100/일)
  twitter - Twitter v2 recent search (동적 쿼리, 무료 500k/월)

NOTE: Google Alerts RSS는 운영자가 수동 설정해야 하므로 제거.
      Google Custom Search API를 사용하면 유저 키워드를 동적으로 검색 가능.
"""

import os
import re

import requests

from .filter import is_relevant

TIMEOUT = 15


# ---------- helpers ----------

def _build_query(term: str, exact_match: bool) -> str:
    return f'"{term}"' if exact_match else term


# ---------- Naver ----------

def fetch_naver(term: str, exact_match: bool) -> list[dict]:
    client_id = os.environ.get("NAVER_CLIENT_ID", "")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
    if not (client_id and client_secret):
        print("  [Naver] 자격증명 없음, 건너뜀")
        return []

    query = _build_query(term, exact_match)
    results: list[dict] = []

    for endpoint, label in [
        ("https://openapi.naver.com/v1/search/news.json", "네이버 뉴스"),
        ("https://openapi.naver.com/v1/search/blog.json", "네이버 블로그"),
    ]:
        try:
            resp = requests.get(
                endpoint,
                headers={
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                },
                params={"query": query, "display": 10, "sort": "date"},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            for item in items:
                title = _strip_tags(item.get("title", ""))
                snippet = _strip_tags(item.get("description", ""))
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": item.get("originallink") or item.get("link", ""),
                    "source": label,
                })
        except Exception as e:
            print(f"  [Naver:{label}] 오류: {e}")

    return results


def _strip_tags(text: str) -> str:
    """Remove HTML tags like <b>, </b> from Naver API responses."""
    return re.sub(r"<[^>]+>", "", text)


# ---------- Google Custom Search ----------

def fetch_google(term: str, exact_match: bool) -> list[dict]:
    """
    Google Custom Search API (동적 쿼리 지원).
    무료: 100 queries/day.
    설정: https://programmablesearchengine.google.com → 검색 엔진 생성 → API 키 발급.
    환경변수: GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID
    """
    api_key = os.environ.get("GOOGLE_CSE_API_KEY", "")
    cse_id = os.environ.get("GOOGLE_CSE_ID", "")
    if not (api_key and cse_id):
        return []

    query = _build_query(term, exact_match)
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": api_key,
                "cx": cse_id,
                "q": query,
                "num": 10,
                "sort": "date",
                "lr": "lang_ko",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            {
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
                "source": "Google",
            }
            for item in items
        ]
    except Exception as e:
        print(f"  [Google] 오류: {e}")
        return []


# ---------- Twitter/X ----------

def fetch_twitter(term: str, exact_match: bool) -> list[dict]:
    bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
    if not bearer:
        print("  [Twitter] Bearer Token 없음, 건너뜀")
        return []

    query = _build_query(term, exact_match) + " lang:ko -is:retweet"
    try:
        resp = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            headers={"Authorization": f"Bearer {bearer}"},
            params={
                "query": query,
                "max_results": 10,
                "tweet.fields": "created_at,author_id",
                "expansions": "author_id",
                "user.fields": "username",
            },
            timeout=TIMEOUT,
        )
        if resp.status_code == 429:
            print("  [Twitter] Rate limit 초과, 건너뜀")
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [Twitter] 오류: {e}")
        return []

    tweets = data.get("data", [])
    users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}

    results = []
    for t in tweets:
        username = users.get(t["author_id"], "unknown")
        results.append({
            "title": f"@{username}",
            "snippet": t["text"],
            "url": f"https://twitter.com/{username}/status/{t['id']}",
            "source": "Twitter",
        })
    return results


# ---------- main entry ----------

def search_all(
    term: str,
    exclude_words: list[str],
    exact_match: bool,
    sources: list[str] | None = None,
) -> list[dict]:
    """
    sources: subset of ['naver', 'google', 'twitter']. None = all.
    Returns filtered, deduplicated results.
    """
    if sources is None:
        sources = ["naver", "google", "twitter"]

    raw: list[dict] = []

    if "naver" in sources:
        raw += fetch_naver(term, exact_match)
    if "google" in sources:
        raw += fetch_google(term, exact_match)
    if "twitter" in sources:
        raw += fetch_twitter(term, exact_match)

    seen_urls: set[str] = set()
    results = []
    for item in raw:
        url = item["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        combined_text = f"{item['title']} {item['snippet']}"
        if is_relevant(combined_text, exclude_words):
            results.append(item)

    return results
