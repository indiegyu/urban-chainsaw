"""
Search adapters for each source.
Each function returns a list of dicts: {title, snippet, url, source}
"""

import os
import xml.etree.ElementTree as ET

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
    import re
    return re.sub(r"<[^>]+>", "", text)


# ---------- Google Alerts RSS ----------

def fetch_google_alerts(term: str) -> list[dict]:
    """
    Google Alerts RSS URL은 환경변수로 키워드별로 설정.
    GOOGLE_ALERTS_RSS_{N} 형태로 여러 개 지원.
    키워드 매핑: GOOGLE_ALERTS_TERM_{N}=소음발광, GOOGLE_ALERTS_RSS_{N}=https://...

    단순화를 위해 GOOGLE_ALERTS_RSS_URLS 환경변수에
    "키워드1=URL1,키워드2=URL2" 형태로 저장.
    """
    mapping_str = os.environ.get("GOOGLE_ALERTS_RSS_URLS", "")
    if not mapping_str:
        return []

    mapping: dict[str, str] = {}
    for pair in mapping_str.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            mapping[k.strip()] = v.strip()

    rss_url = mapping.get(term)
    if not rss_url:
        return []

    try:
        resp = requests.get(rss_url, timeout=TIMEOUT)
        resp.raise_for_status()
        return _parse_atom_feed(resp.text)
    except Exception as e:
        print(f"  [Google Alerts] 오류: {e}")
        return []


def _parse_atom_feed(xml_text: str) -> list[dict]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    results = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link", ns)
        summary_el = entry.find("atom:summary", ns)
        results.append({
            "title": title_el.text if title_el is not None else "",
            "snippet": summary_el.text if summary_el is not None else "",
            "url": link_el.get("href", "") if link_el is not None else "",
            "source": "Google Alerts",
        })
    return results


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
        raw += fetch_google_alerts(term)
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
