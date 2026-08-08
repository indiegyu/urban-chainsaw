"""
주간 성과 분석 + 전략 자동 업데이트
=====================================
매주 월요일 실행:
  1. YouTube API로 모든 영상 조회수/좋아요/댓글 수집
  2. Groq이 데이터 분석 → 다음 주 전략 도출
  3. content_strategy.json 자동 업데이트

완전 무인화: 사람 개입 없이 시스템이 스스로 학습합니다.
"""

import os
import json
import requests
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.retry import retry_api_call, notify_error, notify_success

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
GROQ_API    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL  = "llama-3.3-70b-versatile"
STRATEGY_PATH = Path(__file__).parent.parent / "strategy" / "content_strategy.json"
TOKEN_PATH    = "token.json"


def get_access_token() -> str:
    tok = json.loads(Path(TOKEN_PATH).read_text())
    def _refresh():
        r = requests.post(tok["token_uri"], data={
            "client_id": tok["client_id"], "client_secret": tok["client_secret"],
            "refresh_token": tok["refresh_token"], "grant_type": "refresh_token",
        }, timeout=15)
        r.raise_for_status()
        return r.json()["access_token"]
    return retry_api_call(_refresh, max_retries=3)


def get_channel_videos(token: str) -> list[dict]:
    """채널의 모든 영상 통계를 가져옵니다."""
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 채널 uploads 플레이리스트 ID
    ch = requests.get(f"{YOUTUBE_API}/channels?part=contentDetails&mine=true",
                      headers=headers).json()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # 2. 플레이리스트 아이템 (최근 50개)
    items_resp = requests.get(f"{YOUTUBE_API}/playlistItems", headers=headers, params={
        "part": "contentDetails", "playlistId": uploads_id, "maxResults": 50,
    }).json()
    video_ids = [i["contentDetails"]["videoId"] for i in items_resp.get("items", [])]

    if not video_ids:
        return []

    # 3. 영상별 통계
    stats_resp = requests.get(f"{YOUTUBE_API}/videos", headers=headers, params={
        "part": "snippet,statistics", "id": ",".join(video_ids),
    }).json()

    videos = []
    for v in stats_resp.get("items", []):
        stats = v.get("statistics", {})
        videos.append({
            "id":       v["id"],
            "title":    v["snippet"]["title"],
            "views":    int(stats.get("viewCount", 0)),
            "likes":    int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "published": v["snippet"]["publishedAt"][:10],
        })

    videos.sort(key=lambda x: x["views"], reverse=True)
    return videos


def groq_analyze(videos: list[dict], current_strategy: dict, groq_key: str) -> dict:
    """Groq으로 성과 데이터를 분석하고 새 전략을 JSON으로 반환합니다."""
    if not videos:
        print("  ⚠ 영상 데이터 없음 — 전략 업데이트 스킵")
        return {}

    top5 = videos[:5]
    bottom5 = videos[-5:] if len(videos) > 5 else []

    data_summary = (
        f"TOP PERFORMING VIDEOS:\n" +
        "\n".join(f"  [{v['views']} views] {v['title']}" for v in top5) +
        ("\n\nLOW PERFORMING VIDEOS:\n" +
         "\n".join(f"  [{v['views']} views] {v['title']}" for v in bottom5)
         if bottom5 else "")
    )

    r = requests.post(GROQ_API, headers={
        "Authorization": f"Bearer {groq_key}", "Content-Type": "application/json",
    }, json={
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": (
                "You are a YouTube channel strategist. Analyze video performance data and output "
                "ONLY valid JSON (no markdown) with these exact keys:\n"
                "- top_performing_formats: list of 5 title format templates that work best (use X/Y as placeholders)\n"
                "- top_performing_topics: list of 5 topic areas driving most views\n"
                "- avoid_topics: list of topics/formats that underperformed\n"
                "- best_thumbnail_style: string describing what works for thumbnails\n"
                "- product_ideas: list of 5 digital product ideas matching top content themes\n"
                "- strategy_note: one sentence explaining the key insight from this week's data"
            )},
            {"role": "user", "content": (
                f"Analyze this YouTube channel performance data and update the content strategy:\n\n"
                f"{data_summary}\n\n"
                f"Channel niche: AI tools, passive income, automation\n"
                f"Goal: maximize views AND advertiser CPM (finance/AI = high CPM)"
            )},
        ],
        "temperature": 0.5,
        "max_tokens": 800,
    }, timeout=30)

    if r.status_code != 200:
        print(f"  ✗ Groq 분석 실패: {r.status_code}")
        return {}

    import re
    raw = r.json()["choices"][0]["message"]["content"].strip()
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    if "```" in raw:
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def update_strategy(new_data: dict, videos: list[dict]):
    """content_strategy.json을 새 데이터로 업데이트합니다."""
    strategy = json.loads(STRATEGY_PATH.read_text())

    # 성과 통계 업데이트
    if videos:
        strategy["weekly_stats"] = {
            "total_videos":    len(videos),
            "avg_views":       int(sum(v["views"] for v in videos) / len(videos)),
            "top_video_id":    videos[0]["id"],
            "top_video_title": videos[0]["title"],
            "top_video_views": videos[0]["views"],
        }

    # Groq 분석 결과 병합
    for key in ["top_performing_formats", "top_performing_topics",
                "avoid_topics", "best_thumbnail_style", "product_ideas"]:
        if key in new_data:
            strategy[key] = new_data[key]

    if "strategy_note" in new_data:
        strategy["last_strategy_note"] = new_data["strategy_note"]

    strategy["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    strategy["version"] = strategy.get("version", 1) + 1

    STRATEGY_PATH.write_text(json.dumps(strategy, indent=2, ensure_ascii=False))
    print(f"  ✅ 전략 업데이트 완료 (v{strategy['version']})")
    if "strategy_note" in new_data:
        print(f"  💡 인사이트: {new_data['strategy_note']}")


def run():
    from dotenv import load_dotenv
    load_dotenv()
    groq_key = os.environ["GROQ_API_KEY"]

    print("📊 주간 성과 분석 시작...")

    # 1. YouTube 데이터 수집
    try:
        token = get_access_token()
        videos = get_channel_videos(token)
        print(f"  ✓ 영상 {len(videos)}개 수집")
        for v in videos[:3]:
            print(f"    [{v['views']:,} views] {v['title'][:55]}")
    except Exception as e:
        print(f"  ✗ YouTube 데이터 수집 실패: {e}")
        videos = []

    # 2. Groq 분석
    print("\n🤖 Groq 전략 분석 중...")
    current = json.loads(STRATEGY_PATH.read_text())
    new_strategy = groq_analyze(videos, current, groq_key)

    # 3. 전략 업데이트
    print("\n📝 전략 파일 업데이트...")
    update_strategy(new_strategy, videos)


if __name__ == "__main__":
    run()
