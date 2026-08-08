"""
대시보드 데이터 수집 모듈
========================
YouTube API, 로컬 파일, 헬스 로그에서 데이터를 수집합니다.
모든 시간은 KST(UTC+9) 기준.
"""

import os, json, requests
from pathlib import Path
from datetime import datetime, timezone, timedelta

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
STRATEGY_PATH = Path("scripts/strategy/content_strategy.json")
TOKEN_PATH = "token.json"
REVENUE_HISTORY_PATH = Path(".github/run_logs/revenue_history.json")
HEALTH_LOG_PATH = Path(".github/run_logs/health.json")

KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST)


def now_kst_str() -> str:
    return now_kst().strftime("%Y-%m-%d %H:%M KST")


def _to_kst(ts_str: str) -> str:
    """ISO timestamp → KST 문자열."""
    if not ts_str:
        return ""
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return ts.astimezone(KST).strftime("%m/%d %H:%M")
    except Exception:
        return ts_str[:16]


def relative_time_kst(ts_str: str) -> str:
    """ISO timestamp → 'N분 전' 형식 (KST 기준)."""
    if not ts_str:
        return "미실행"
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        diff = int((now_kst() - ts.astimezone(KST)).total_seconds())
        if diff < 0:
            return "방금"
        if diff < 60:
            return f"{diff}초 전"
        if diff < 3600:
            return f"{diff // 60}분 전"
        if diff < 86400:
            return f"{diff // 3600}시간 전"
        return f"{diff // 86400}일 전"
    except Exception:
        return ts_str[:16]


def _parse_log_field(text: str, field: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return ""


# ── YouTube 채널 통계 + 최근 영상 상세 ────────────────────────────────────────

def fetch_youtube_stats() -> dict:
    try:
        tok = json.loads(Path(TOKEN_PATH).read_text())
        r = requests.post(tok["token_uri"], data={
            "client_id": tok["client_id"], "client_secret": tok["client_secret"],
            "refresh_token": tok["refresh_token"], "grant_type": "refresh_token",
        }, timeout=10)
        access = r.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {access}"}

        ch = requests.get(f"{YOUTUBE_API}/channels?part=statistics,snippet&mine=true",
                          headers=headers, timeout=10).json()
        if not ch.get("items"):
            return {}
        stats = ch["items"][0]["statistics"]
        subs = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        vids = int(stats.get("videoCount", 0))

        # 최근 10개 영상 상세 (개별 조회수/좋아요)
        ch2 = requests.get(f"{YOUTUBE_API}/channels?part=contentDetails&mine=true",
                           headers=headers, timeout=10).json()
        uid = ch2["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = requests.get(f"{YOUTUBE_API}/playlistItems",
                          params={"part": "contentDetails", "playlistId": uid, "maxResults": 10},
                          headers=headers, timeout=10).json()
        vids_ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]

        recent_views, recent_likes, top_video = 0, 0, {}
        recent_videos = []
        if vids_ids:
            vr = requests.get(f"{YOUTUBE_API}/videos",
                              params={"part": "snippet,statistics", "id": ",".join(vids_ids)},
                              headers=headers, timeout=10).json()
            for v in vr.get("items", []):
                vc = int(v["statistics"].get("viewCount", 0))
                lc = int(v["statistics"].get("likeCount", 0))
                recent_views += vc
                recent_likes += lc
                vid_info = {
                    "title": v["snippet"]["title"][:55],
                    "views": vc, "likes": lc,
                    "id": v["id"],
                    "published": v["snippet"]["publishedAt"],
                }
                recent_videos.append(vid_info)
                if vc > top_video.get("views", 0):
                    top_video = vid_info

        est = round(recent_views / 1000 * 3 * 0.45, 2)
        return {
            "subscribers": subs, "total_views": views, "video_count": vids,
            "recent_views": recent_views, "recent_likes": recent_likes,
            "est_monthly": est, "top_video": top_video,
            "recent_videos": recent_videos[:5],
            "monetized": subs >= 1000, "subs_needed": max(0, 1000 - subs),
        }
    except Exception as e:
        return {"error": str(e)}


# ── 전략 데이터 ───────────────────────────────────────────────────────────────

def fetch_strategy_stats() -> dict:
    try:
        s = json.loads(STRATEGY_PATH.read_text())
        return {
            "version": s.get("version", 1),
            "last_updated": s.get("last_updated", ""),
            "top_topics": s.get("top_performing_topics", [])[:5],
            "top_formats": s.get("top_performing_formats", [])[:3],
            "strategy_note": s.get("last_strategy_note", ""),
        }
    except Exception:
        return {}


# ── 로컬 결과물 집계 (확장) ───────────────────────────────────────────────────

def count_local_outputs() -> dict:
    def _count(path, ext):
        p = Path(path)
        return len(list(p.glob(f"*.{ext}"))) if p.exists() else 0

    def _recent_files(path, ext, limit=3):
        p = Path(path)
        if not p.exists():
            return []
        files = sorted(p.glob(f"*.{ext}"), key=lambda f: f.stat().st_mtime, reverse=True)
        return [{"name": f.stem[:50], "date": datetime.fromtimestamp(
            f.stat().st_mtime, tz=KST).strftime("%m/%d %H:%M")} for f in files[:limit]]

    return {
        "blogs": _count("scripts/blog/output", "html"),
        "blogs_recent": _recent_files("scripts/blog/output", "html"),
        "pods": _count("scripts/pod/output", "png"),
        "videos": len([d for d in Path("scripts/video/output").iterdir() if d.is_dir()])
                  if Path("scripts/video/output").exists() else 0,
        "ebooks": _count("scripts/ebook/output", "html"),
    }


# ── 파이프라인 실행 상태 (실사용만) ──────────────────────────────────────────

def fetch_pipeline_status() -> dict:
    status = {}

    # YouTube 영상
    yt_log = Path(".github/run_logs/last_run.txt")
    if yt_log.exists():
        txt = yt_log.read_text()
        status["youtube"] = {
            "ok": _parse_log_field(txt, "status") == "success",
            "detail": _parse_log_field(txt, "status"),
            "ts": _parse_log_field(txt, "timestamp"),
            "run": _parse_log_field(txt, "run"),
        }

    # YouTube Shorts
    sh_log = Path(".github/run_logs/last_shorts_run.txt")
    if sh_log.exists():
        txt = sh_log.read_text()
        status["shorts"] = {
            "ok": _parse_log_field(txt, "status") == "success",
            "detail": _parse_log_field(txt, "status"),
            "ts": _parse_log_field(txt, "timestamp"),
            "run": _parse_log_field(txt, "run"),
        }

    # 블로그
    blog_dir = Path("scripts/blog/output")
    if blog_dir.exists():
        html_files = sorted(blog_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        if html_files:
            mtime = datetime.fromtimestamp(html_files[0].stat().st_mtime, tz=timezone.utc)
            status["blog"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "detail": f"{len(html_files)}개 포스트"}

    # POD 디자인
    pod_dir = Path("scripts/pod/output")
    if pod_dir.exists():
        png_files = sorted(pod_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
        if png_files:
            mtime = datetime.fromtimestamp(png_files[0].stat().st_mtime, tz=timezone.utc)
            status["pod"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "detail": f"{len(png_files)}개 디자인"}

    # KDP 이북
    ebook_dir = Path("scripts/ebook/output")
    if ebook_dir.exists():
        ebook_files = sorted(ebook_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        if ebook_files:
            mtime = datetime.fromtimestamp(ebook_files[0].stat().st_mtime, tz=timezone.utc)
            status["ebook"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "detail": f"{len(ebook_files)}개 이북"}

    # 전략 최적화
    if STRATEGY_PATH.exists():
        mtime = datetime.fromtimestamp(STRATEGY_PATH.stat().st_mtime, tz=timezone.utc)
        status["strategy"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "detail": "전략 파일 최신"}

    return status


# ── 수익 히스토리 ─────────────────────────────────────────────────────────────

def save_revenue_snapshot(yt: dict, outputs: dict) -> dict:
    today = now_kst().strftime("%Y-%m-%d")
    REVENUE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        history = json.loads(REVENUE_HISTORY_PATH.read_text()) if REVENUE_HISTORY_PATH.exists() else {"daily": []}
    except (json.JSONDecodeError, FileNotFoundError):
        history = {"daily": []}

    history["daily"] = [d for d in history["daily"] if d.get("date") != today]
    history["daily"].append({
        "date": today,
        "yt_est_monthly": yt.get("est_monthly", 0) if "error" not in yt else 0,
        "yt_subscribers": yt.get("subscribers", 0) if "error" not in yt else 0,
        "yt_recent_views": yt.get("recent_views", 0) if "error" not in yt else 0,
        "videos": outputs.get("videos", 0),
        "blogs": outputs.get("blogs", 0),
        "pods": outputs.get("pods", 0),
        "ebooks": outputs.get("ebooks", 0),
    })
    history["daily"] = history["daily"][-90:]
    history["last_updated"] = today
    REVENUE_HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    return history


def get_revenue_trend(history: dict, days: int = 7) -> list[dict]:
    daily = history.get("daily", [])
    return daily[-days:] if len(daily) >= days else daily


# ── 파이프라인 건강도 ─────────────────────────────────────────────────────────

def fetch_pipeline_health() -> dict:
    try:
        data = json.loads(HEALTH_LOG_PATH.read_text()) if HEALTH_LOG_PATH.exists() else {"events": []}
    except (json.JSONDecodeError, FileNotFoundError):
        return {"total": 0, "success": 0, "error": 0, "rate": 100, "recent_errors": []}

    cutoff = (now_kst() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent = [e for e in data.get("events", []) if e.get("timestamp", "") >= cutoff]
    success = sum(1 for e in recent if e.get("status") == "success")
    errors = [e for e in recent if "error" in e]

    return {
        "total": len(recent), "success": success, "error": len(errors),
        "rate": round(success / len(recent) * 100) if recent else 100,
        "recent_errors": errors[-5:],
    }
