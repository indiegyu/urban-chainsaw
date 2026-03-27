"""
수익 대시보드 자동 생성
========================
실제 작동 중인 파이프라인만 표시.
다중 수익원 추적, 7일 트렌드, 파이프라인 건강도 포함.
"""

import os, json, requests, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

YOUTUBE_API   = "https://www.googleapis.com/youtube/v3"
STRATEGY_PATH = Path("scripts/strategy/content_strategy.json")
DOCS_DIR      = Path("docs")
TOKEN_PATH    = "token.json"
REVENUE_HISTORY_PATH = Path(".github/run_logs/revenue_history.json")
HEALTH_LOG_PATH = Path(".github/run_logs/health.json")

# ── 실제 활성 파이프라인 (확인된 것만) ────────────────────────────────────────
ACTIVE_PIPELINES = [
    ("📺", "YouTube 영상",        "매일 x2",   "AdSense CPM",         "https://studio.youtube.com"),
    ("🩳", "YouTube Shorts",      "매일 x1",   "AdSense + 노출",      "https://studio.youtube.com"),
    ("📝", "블로그 포스트",        "매일 x2",   "어필리에이트 링크",    "https://indiegyu.github.io/urban-chainsaw/"),
    ("🔧", "Dev.to 발행",          "매일",      "트래픽 → 채널 유입",  "https://dev.to/dashboard"),
    ("🎨", "POD 티셔츠 디자인",    "매일",      "Etsy 연동 대기",      "https://github.com/indiegyu/urban-chainsaw/actions"),
    ("📚", "AI Tools 디렉토리",    "매일",      "어필리에이트 SEO",    "https://indiegyu.github.io/urban-chainsaw/ai-tools.html"),
    ("☕", "Ko-fi 후원 버튼",      "상시",      "방문자 후원",         "https://ko-fi.com"),
    ("🐦", "Twitter/X 포스팅",    "매일",      "바이럴 트래픽",       "https://analytics.twitter.com"),
    ("📖", "KDP 이북 생성",        "매주 일",   "Amazon 인세 70%",    "https://kdp.amazon.com"),
    ("🧠", "AI 전략 최적화",       "매주 월",   "성과 기반 자동개선",  "https://github.com/indiegyu/urban-chainsaw/actions"),
    ("🚀", "파이프라인 자동확장",  "매주 화",   "신규 수익모델 추가",  "https://github.com/indiegyu/urban-chainsaw/actions"),
]

# ── 설정 대기 중 파이프라인 ───────────────────────────────────────────────────
PENDING_PIPELINES = [
    ("🍋", "Lemon Squeezy 디지털 상품", "API 키 인증 확인 필요"),
    ("🛒", "Etsy 디지털 상품",           "ETSY_SHOP_ID 미등록"),
]


# ── 데이터 수집 ────────────────────────────────────────────────────────────────

def fetch_youtube_stats() -> dict:
    try:
        tok    = json.loads(Path(TOKEN_PATH).read_text())
        r      = requests.post(tok["token_uri"], data={
            "client_id": tok["client_id"], "client_secret": tok["client_secret"],
            "refresh_token": tok["refresh_token"], "grant_type": "refresh_token",
        }, timeout=10)
        access  = r.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {access}"}

        ch = requests.get(f"{YOUTUBE_API}/channels?part=statistics,snippet&mine=true",
                          headers=headers, timeout=10).json()
        if not ch.get("items"):
            return {}
        stats = ch["items"][0]["statistics"]
        subs  = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        vids  = int(stats.get("videoCount", 0))

        ch2 = requests.get(f"{YOUTUBE_API}/channels?part=contentDetails&mine=true",
                           headers=headers, timeout=10).json()
        uid = ch2["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl  = requests.get(f"{YOUTUBE_API}/playlistItems",
                           params={"part": "contentDetails", "playlistId": uid, "maxResults": 10},
                           headers=headers, timeout=10).json()
        vids_ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]

        recent_views, top_video = 0, {}
        if vids_ids:
            vr = requests.get(f"{YOUTUBE_API}/videos",
                              params={"part": "snippet,statistics", "id": ",".join(vids_ids)},
                              headers=headers, timeout=10).json()
            for v in vr.get("items", []):
                vc = int(v["statistics"].get("viewCount", 0))
                recent_views += vc
                if vc > top_video.get("views", 0):
                    top_video = {"title": v["snippet"]["title"][:55],
                                 "views": vc, "id": v["id"]}

        est = round(recent_views / 1000 * 3 * 0.45, 2)
        return {"subscribers": subs, "total_views": views, "video_count": vids,
                "recent_views": recent_views, "est_monthly": est,
                "top_video": top_video,
                "monetized": subs >= 1000, "subs_needed": max(0, 1000 - subs)}
    except Exception as e:
        return {"error": str(e)}


def fetch_strategy_stats() -> dict:
    try:
        s = json.loads(STRATEGY_PATH.read_text())
        return {
            "version":      s.get("version", 1),
            "last_updated": s.get("last_updated", ""),
            "top_topics":   s.get("top_performing_topics", [])[:4],
        }
    except Exception:
        return {}


def count_local_outputs() -> dict:
    """로컬 결과물 수 집계"""
    blog_count = len(list(Path("scripts/blog/output").glob("*.html"))) if Path("scripts/blog/output").exists() else 0
    pod_count  = len(list(Path("scripts/pod/output").glob("*.png")))   if Path("scripts/pod/output").exists() else 0
    vid_count  = len(list(Path("scripts/video/output").glob("*")))     if Path("scripts/video/output").exists() else 0
    return {"blogs": blog_count, "pods": pod_count, "videos": vid_count}


def _parse_log_field(text: str, field: str) -> str:
    """run_logs txt 파일에서 'field: value' 형식 파싱."""
    for line in text.splitlines():
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return ""


def _relative_time(ts_str: str) -> str:
    """ISO timestamp → 'N분 전' / 'N시간 전' 형식."""
    if not ts_str:
        return "미실행"
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = int((now - ts).total_seconds())
        if diff < 60:
            return f"{diff}초 전"
        elif diff < 3600:
            return f"{diff // 60}분 전"
        elif diff < 86400:
            return f"{diff // 3600}시간 전"
        else:
            return f"{diff // 86400}일 전"
    except Exception:
        return ts_str[:16]


def fetch_pipeline_status() -> dict:
    """각 파이프라인의 최근 실행 상태를 수집합니다."""
    status = {}

    # ── YouTube 영상 run log ──────────────────────────────────────
    yt_log = Path(".github/run_logs/last_run.txt")
    if yt_log.exists():
        txt = yt_log.read_text()
        status["youtube"] = {
            "ok":        _parse_log_field(txt, "status") == "success",
            "detail":    _parse_log_field(txt, "status"),
            "ts":        _parse_log_field(txt, "timestamp"),
            "run":       _parse_log_field(txt, "run"),
        }

    # ── YouTube Shorts run log ────────────────────────────────────
    sh_log = Path(".github/run_logs/last_shorts_run.txt")
    if sh_log.exists():
        txt = sh_log.read_text()
        status["shorts"] = {
            "ok":     _parse_log_field(txt, "status") == "success",
            "detail": _parse_log_field(txt, "status"),
            "ts":     _parse_log_field(txt, "timestamp"),
            "run":    _parse_log_field(txt, "run"),
        }

    # ── 블로그 (파일 mtime 기준) ──────────────────────────────────
    blog_dir = Path("scripts/blog/output")
    if blog_dir.exists():
        html_files = sorted(blog_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        if html_files:
            mtime = datetime.fromtimestamp(html_files[0].stat().st_mtime, tz=timezone.utc)
            status["blog"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "detail": f"{len(html_files)}개 포스트"}

    # ── Dev.to 발행 로그 ──────────────────────────────────────────
    devto_log = Path("scripts/publish/.devto_published.json")
    if devto_log.exists():
        try:
            data = json.loads(devto_log.read_text())
            published = data.get("published", [])
            mtime = datetime.fromtimestamp(devto_log.stat().st_mtime, tz=timezone.utc)
            status["devto"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "detail": f"{len(published)}개 발행"}
        except Exception:
            pass

    # ── POD 디자인 (파일 mtime 기준) ─────────────────────────────
    pod_dir = Path("scripts/pod/output")
    if pod_dir.exists():
        png_files = sorted(pod_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
        if png_files:
            mtime = datetime.fromtimestamp(png_files[0].stat().st_mtime, tz=timezone.utc)
            status["pod"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "detail": f"{len(png_files)}개 디자인"}

    # ── KDP 이북 ─────────────────────────────────────────────────
    ebook_dir = Path("scripts/ebook/output")
    if ebook_dir.exists():
        ebook_files = sorted(ebook_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        if ebook_files:
            mtime = datetime.fromtimestamp(ebook_files[0].stat().st_mtime, tz=timezone.utc)
            status["ebook"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "detail": f"{len(ebook_files)}개 이북"}

    # ── 전략 최적화 (content_strategy.json mtime) ─────────────────
    if STRATEGY_PATH.exists():
        mtime = datetime.fromtimestamp(STRATEGY_PATH.stat().st_mtime, tz=timezone.utc)
        status["strategy"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "detail": "전략 파일 최신"}

    # ── Twitter 포스팅 로그 ───────────────────────────────────────
    tw_log = Path("scripts/social/.twitter_posted.json")
    if tw_log.exists():
        try:
            data = json.loads(tw_log.read_text())
            posted = data.get("posted", [])
            mtime = datetime.fromtimestamp(tw_log.stat().st_mtime, tz=timezone.utc)
            status["twitter"] = {"ok": True, "ts": mtime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                 "detail": f"누적 {len(posted)}개 트윗"}
        except Exception:
            pass

    return status


# ── 수익 히스토리 추적 ────────────────────────────────────────────────────────

def save_revenue_snapshot(yt: dict, outputs: dict):
    """매일 수익/생산량 스냅샷을 저장합니다 (최근 90일 유지)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    REVENUE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        history = json.loads(REVENUE_HISTORY_PATH.read_text()) if REVENUE_HISTORY_PATH.exists() else {"daily": []}
    except (json.JSONDecodeError, FileNotFoundError):
        history = {"daily": []}

    # 같은 날짜 중복 방지
    history["daily"] = [d for d in history["daily"] if d.get("date") != today]

    snapshot = {
        "date": today,
        "yt_est_monthly": yt.get("est_monthly", 0) if "error" not in yt else 0,
        "yt_subscribers": yt.get("subscribers", 0) if "error" not in yt else 0,
        "yt_recent_views": yt.get("recent_views", 0) if "error" not in yt else 0,
        "videos": outputs.get("videos", 0),
        "blogs": outputs.get("blogs", 0),
        "pods": outputs.get("pods", 0),
    }
    history["daily"].append(snapshot)
    history["daily"] = history["daily"][-90:]  # 최근 90일만 유지
    history["last_updated"] = today

    REVENUE_HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    return history


def get_revenue_trend(history: dict, days: int = 7) -> list[dict]:
    """최근 N일간 수익 트렌드를 반환합니다."""
    daily = history.get("daily", [])
    return daily[-days:] if len(daily) >= days else daily


def fetch_pipeline_health() -> dict:
    """health.json에서 파이프라인 에러율/성공률을 계산합니다."""
    try:
        data = json.loads(HEALTH_LOG_PATH.read_text()) if HEALTH_LOG_PATH.exists() else {"events": []}
    except (json.JSONDecodeError, FileNotFoundError):
        return {"total": 0, "success": 0, "error": 0, "rate": 100, "recent_errors": []}

    events = data.get("events", [])
    # 최근 7일 이벤트만
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent = [e for e in events if e.get("timestamp", "") >= cutoff]

    success = sum(1 for e in recent if e.get("status") == "success")
    errors = [e for e in recent if "error" in e]
    total = len(recent)

    return {
        "total": total,
        "success": success,
        "error": len(errors),
        "rate": round(success / total * 100) if total > 0 else 100,
        "recent_errors": errors[-5:],  # 최근 에러 5건
    }


def _build_sparkline_svg(values: list[float], width: int = 200, height: int = 40) -> str:
    """간단한 SVG 스파크라인 차트를 생성합니다."""
    if not values or len(values) < 2:
        return ""
    max_val = max(values) or 1
    min_val = min(values)
    val_range = max_val - min_val or 1

    points = []
    step = width / (len(values) - 1)
    for i, v in enumerate(values):
        x = round(i * step, 1)
        y = round(height - (v - min_val) / val_range * (height - 4) - 2, 1)
        points.append(f"{x},{y}")

    # 그라디언트 영역
    fill_points = points + [f"{width},{height}", f"0,{height}"]

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle">'
        f'<defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#818cf8" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="#818cf8" stop-opacity="0.02"/>'
        f'</linearGradient></defs>'
        f'<polygon points="{" ".join(fill_points)}" fill="url(#sg)"/>'
        f'<polyline points="{" ".join(points)}" fill="none" stroke="#818cf8" stroke-width="2"/>'
        f'<circle cx="{points[-1].split(",")[0]}" cy="{points[-1].split(",")[1]}" r="3" fill="#a5b4fc"/>'
        f'</svg>'
    )


# ── HTML 빌드 ─────────────────────────────────────────────────────────────────

def build_dashboard(yt: dict, strategy: dict, outputs: dict, pipe_status: dict = None,
                    revenue_history: dict = None, health: dict = None) -> str:
    now      = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    est_usd  = yt.get("est_monthly", 0) if "error" not in yt else 0
    trend_data = get_revenue_trend(revenue_history or {}, days=7)
    health = health or {}

    # ── YouTube 카드 ──────────────────────────────────────────────────────────
    if "error" not in yt and yt:
        subs = yt.get("subscribers", 0)
        mon_badge = (
            '<span class="badge green">✅ 수익화 조건 충족</span>'
            if yt.get("monetized") else
            f'<span class="badge yellow">⏳ 구독자 {yt.get("subs_needed", 0):,}명 더 필요</span>'
        )
        top_v    = yt.get("top_video", {})
        top_line = (
            f'<p style="margin-top:10px;font-size:.85em">🏆 인기 영상: '
            f'<a href="https://youtu.be/{top_v["id"]}" target="_blank" style="color:#818cf8">'
            f'{top_v["title"]}</a> ({top_v["views"]:,} views)</p>'
        ) if top_v else ""

        yt_body = f"""
<div class="stats-row">
  <div class="stat"><span class="stat-num">{subs:,}</span><span class="stat-label">구독자</span></div>
  <div class="stat"><span class="stat-num">{yt.get('recent_views',0):,}</span><span class="stat-label">최근 10개 영상 조회수</span></div>
  <div class="stat"><span class="stat-num">${est_usd:.2f}</span><span class="stat-label">예상 월 AdSense</span></div>
  <div class="stat"><span class="stat-num">{yt.get('video_count',0):,}</span><span class="stat-label">총 영상 수</span></div>
</div>
{mon_badge}
{top_line}
<div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
  <a href="https://studio.youtube.com" target="_blank" class="btn-primary">🎬 YouTube Studio</a>
  <a href="https://adsense.google.com" target="_blank" class="btn-secondary">💵 AdSense 출금</a>
  <a href="https://www.youtube.com/@psg9806" target="_blank" class="btn-secondary">👁 채널 보기</a>
</div>"""
    else:
        yt_body = f'<p class="error">⚠ YouTube 데이터 로드 실패: {yt.get("error","token 확인 필요")}</p>'

    # ── 콘텐츠 생산량 카드 ───────────────────────────────────────────────────
    output_body = f"""
<div class="stats-row">
  <div class="stat"><span class="stat-num">{outputs['videos']}</span><span class="stat-label">생성된 영상</span></div>
  <div class="stat"><span class="stat-num">{outputs['blogs']}</span><span class="stat-label">블로그 포스트</span></div>
  <div class="stat"><span class="stat-num">{outputs['pods']}</span><span class="stat-label">POD 디자인</span></div>
</div>
<p class="muted">매일 자동 생성 · GitHub Actions Artifacts에서 다운로드 가능</p>
<div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
  <a href="https://indiegyu.github.io/urban-chainsaw/" target="_blank" class="btn-primary">📝 블로그 보기</a>
  <a href="https://github.com/indiegyu/urban-chainsaw/actions" target="_blank" class="btn-secondary">📦 결과물 다운로드</a>
  <a href="https://dev.to/dashboard" target="_blank" class="btn-secondary">📊 Dev.to 통계</a>
</div>"""

    # ── 전략 카드 ────────────────────────────────────────────────────────────
    topics_html = " ".join(
        f'<span class="tag">{t}</span>' for t in strategy.get("top_topics", [])
    ) or '<span class="muted">분석 대기</span>'
    strategy_body = f"""
<p><strong>전략 v{strategy.get('version', 1)}</strong>
   <span class="muted" style="margin-left:8px">업데이트: {strategy.get('last_updated','미실행')}</span></p>
<p style="margin-top:10px"><strong>현재 최적 토픽:</strong></p>
<p style="margin-top:6px">{topics_html}</p>
<p class="muted" style="margin-top:12px">매주 월요일 YouTube 성과 분석 → 자동 업데이트</p>"""

    # ── 파이프라인 현황 카드 (실시간 상태 포함) ─────────────────────────────
    ps = pipe_status or {}

    PIPE_STATUS_KEYS = {
        "YouTube 영상":      "youtube",
        "YouTube Shorts":    "shorts",
        "블로그 포스트":      "blog",
        "Dev.to 발행":        "devto",
        "POD 티셔츠 디자인":  "pod",
        "Twitter/X 포스팅":  "twitter",
        "KDP 이북 생성":      "ebook",
        "AI 전략 최적화":     "strategy",
    }

    def _status_cell(name: str) -> str:
        key = PIPE_STATUS_KEYS.get(name)
        if not key or key not in ps:
            return '<td style="color:#334155;font-size:.75em">–</td>'
        info = ps[key]
        rel  = _relative_time(info.get("ts", ""))
        detail = info.get("detail", "")
        detail_span = f' <span style="color:#475569">· {detail}</span>' if detail else ""
        if info.get("ok"):
            return (f'<td style="font-size:.75em">'
                    f'<span style="color:#6ee7b7">✓</span> '
                    f'<span style="color:#64748b">{rel}</span>'
                    f'{detail_span}</td>')
        else:
            err = info.get("detail", "실패")
            return (f'<td style="font-size:.75em">'
                    f'<span style="color:#f87171">✗ {err}</span>'
                    + (f' <span style="color:#475569">{rel}</span>' if rel else "")
                    + '</td>')

    active_rows = "".join(
        f'<tr>'
        f'<td style="font-size:.85em">{icon} {name}</td>'
        f'<td style="color:#94a3b8;font-size:.78em">{freq}</td>'
        f'<td style="color:#6ee7b7;font-size:.78em">{revenue}</td>'
        f'{_status_cell(name)}'
        f'<td><a href="{link}" target="_blank" style="color:#818cf8;font-size:.8em">→</a></td>'
        f'</tr>'
        for icon, name, freq, revenue, link in ACTIVE_PIPELINES
    )
    pending_rows = "".join(
        f'<tr>'
        f'<td>{icon} {name}</td>'
        f'<td colspan="4" style="color:#fbbf24;font-size:.78em">{reason}</td>'
        f'</tr>'
        for icon, name, reason in PENDING_PIPELINES
    )
    pipeline_body = f"""
<p style="margin-bottom:12px">
  <strong style="color:#6ee7b7">🟢 활성 {len(ACTIVE_PIPELINES)}개</strong>
  <span style="margin-left:12px;color:#fbbf24">🟡 대기 {len(PENDING_PIPELINES)}개</span>
</p>
<table class="data-table">
<tr><th>파이프라인</th><th>주기</th><th>수익</th><th>최근 실행</th><th></th></tr>
{active_rows}
</table>
<p style="margin-top:16px;margin-bottom:8px;color:#fbbf24;font-size:.85em;font-weight:600">⏳ 설정 대기</p>
<table class="data-table">
{pending_rows}
</table>"""

    # ── 수익 추이 카드 (7일) ──────────────────────────────────────────────────
    if trend_data and len(trend_data) >= 2:
        views_vals = [d.get("yt_recent_views", 0) for d in trend_data]
        subs_vals = [d.get("yt_subscribers", 0) for d in trend_data]
        views_spark = _build_sparkline_svg(views_vals, 180, 36)
        subs_spark = _build_sparkline_svg(subs_vals, 180, 36)

        # 성장률 계산
        if views_vals[0] > 0:
            views_growth = round((views_vals[-1] - views_vals[0]) / views_vals[0] * 100, 1)
        else:
            views_growth = 0
        subs_growth = subs_vals[-1] - subs_vals[0] if len(subs_vals) >= 2 else 0

        views_arrow = "📈" if views_growth >= 0 else "📉"
        subs_arrow = "📈" if subs_growth >= 0 else "📉"

        trend_body = f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
  <div style="background:#1e293b;border-radius:10px;padding:14px">
    <p style="color:#64748b;font-size:.75em;margin-bottom:6px">최근 조회수 (7일)</p>
    <p style="font-size:1.1em;font-weight:700;color:#fff">{views_vals[-1]:,} {views_arrow} {views_growth:+.1f}%</p>
    <div style="margin-top:8px">{views_spark}</div>
  </div>
  <div style="background:#1e293b;border-radius:10px;padding:14px">
    <p style="color:#64748b;font-size:.75em;margin-bottom:6px">구독자 변화 (7일)</p>
    <p style="font-size:1.1em;font-weight:700;color:#fff">{subs_vals[-1]:,} {subs_arrow} {subs_growth:+,}</p>
    <div style="margin-top:8px">{subs_spark}</div>
  </div>
</div>
<p class="muted" style="margin-top:10px">최근 7일간 추이 · 매일 22:00 UTC 자동 기록</p>"""
    else:
        trend_body = '<p class="muted">데이터 수집 중... (2일 후 트렌드 표시 시작)</p>'

    # ── 파이프라인 건강도 카드 ─────────────────────────────────────────────────
    h_rate = health.get("rate", 100)
    h_total = health.get("total", 0)
    h_errors = health.get("error", 0)
    h_color = "#6ee7b7" if h_rate >= 90 else ("#fbbf24" if h_rate >= 70 else "#f87171")

    recent_err_html = ""
    for err in health.get("recent_errors", [])[-3:]:
        ts = _relative_time(err.get("timestamp", ""))
        recent_err_html += (
            f'<p style="font-size:.78em;color:#f87171;margin-top:4px">'
            f'⚠ [{err.get("pipeline","?")}] {err.get("error","")[:60]} · {ts}</p>'
        )

    health_body = f"""
<div style="display:flex;align-items:center;gap:16px;margin-bottom:12px">
  <div style="position:relative;width:80px;height:80px">
    <svg viewBox="0 0 36 36" width="80" height="80">
      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke="#1e293b" stroke-width="3"/>
      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke="{h_color}" stroke-width="3"
            stroke-dasharray="{h_rate}, 100" stroke-linecap="round"/>
    </svg>
    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                font-size:1.1em;font-weight:700;color:{h_color}">{h_rate}%</div>
  </div>
  <div>
    <p style="font-weight:600;color:#e2e8f0">7일 성공률</p>
    <p style="color:#64748b;font-size:.83em">실행 {h_total}회 중 에러 {h_errors}회</p>
  </div>
</div>
{recent_err_html if recent_err_html else '<p style="color:#6ee7b7;font-size:.83em">✓ 최근 에러 없음</p>'}"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Income Daily — 수익 대시보드</title>
<meta http-equiv="refresh" content="3600">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#080e1a;color:#e2e8f0;min-height:100vh}}

  /* 상단 헤더 */
  .header{{background:linear-gradient(135deg,#1e1b4b 0%,#312e81 50%,#1e1b4b 100%);
           padding:36px 20px 30px;text-align:center;border-bottom:1px solid #2d2d6b}}
  .header h1{{font-size:1.5em;font-weight:700;color:#a5b4fc;letter-spacing:.05em;margin-bottom:4px}}
  .header .amount{{font-size:3.5em;font-weight:800;color:#fff;margin:8px 0;line-height:1}}
  .header .amount-label{{color:#818cf8;font-size:.9em;margin-bottom:16px}}
  .header .pipeline-count{{display:inline-block;background:rgba(99,102,241,.2);
    border:1px solid rgba(99,102,241,.4);border-radius:20px;
    padding:6px 18px;font-size:.85em;color:#a5b4fc}}

  /* 레이아웃 */
  .main{{max-width:960px;margin:0 auto;padding:28px 16px}}

  /* 수확 버튼 섹션 */
  .harvest-section{{background:#0f172a;border:1px solid #1e293b;border-radius:16px;
                    padding:24px;margin-bottom:24px}}
  .harvest-section h2{{font-size:1em;color:#64748b;text-transform:uppercase;
                       letter-spacing:.08em;margin-bottom:16px}}
  .harvest-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}}
  .harvest-link{{background:#1e293b;border:1px solid #334155;border-radius:10px;
                 padding:14px 16px;text-decoration:none;display:block;transition:.15s}}
  .harvest-link:hover{{border-color:#6366f1;background:#1e2a45;transform:translateY(-1px)}}
  .harvest-link .h-icon{{font-size:1.3em;display:block;margin-bottom:6px}}
  .harvest-link .h-name{{color:#e2e8f0;font-weight:600;font-size:.9em;display:block}}
  .harvest-link .h-note{{color:#475569;font-size:.75em;display:block;margin-top:2px}}

  /* 카드 그리드 */
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(440px,1fr));gap:16px}}
  .card{{background:#0f172a;border:1px solid #1e293b;border-radius:14px;overflow:hidden}}
  .card-header{{padding:14px 20px;border-bottom:1px solid #1e293b;display:flex;align-items:center;gap:10px}}
  .card-header .card-title{{font-size:.8em;color:#64748b;text-transform:uppercase;letter-spacing:.06em;font-weight:600}}
  .card-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
  .card-body{{padding:20px}}

  /* 통계 */
  .stats-row{{display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:10px;margin-bottom:14px}}
  .stat{{background:#1e293b;border-radius:10px;padding:12px;text-align:center}}
  .stat-num{{display:block;font-size:1.4em;font-weight:700;color:#fff}}
  .stat-label{{font-size:.7em;color:#475569;margin-top:3px;display:block;line-height:1.3}}

  /* 배지 */
  .badge{{display:inline-block;padding:4px 12px;border-radius:20px;font-size:.8em;font-weight:500}}
  .badge.green{{background:#052e16;color:#86efac;border:1px solid #166534}}
  .badge.yellow{{background:#1c1400;color:#fbbf24;border:1px solid #92400e}}

  /* 버튼 */
  .btn-primary{{background:#4f46e5;color:#fff;padding:8px 16px;border-radius:8px;
               text-decoration:none;font-size:.82em;font-weight:600;white-space:nowrap}}
  .btn-primary:hover{{background:#4338ca}}
  .btn-secondary{{background:#1e293b;color:#94a3b8;padding:8px 16px;border-radius:8px;
                  text-decoration:none;font-size:.82em;border:1px solid #334155;white-space:nowrap}}
  .btn-secondary:hover{{border-color:#6366f1;color:#e2e8f0}}

  /* 테이블 */
  .data-table{{width:100%;border-collapse:collapse;font-size:.83em}}
  .data-table th{{text-align:left;padding:8px 6px;color:#475569;border-bottom:1px solid #1e293b;font-weight:500}}
  .data-table td{{padding:8px 6px;border-bottom:1px solid #0f172a}}

  /* 태그 */
  .tag{{background:#1e3a5f;color:#93c5fd;padding:3px 10px;border-radius:12px;
        font-size:.78em;margin-right:5px;margin-bottom:4px;display:inline-block}}

  .muted{{color:#475569;font-size:.83em}}
  .error{{color:#f87171;font-size:.83em}}

  .footer{{text-align:center;color:#1e293b;font-size:.75em;padding:24px 0 40px}}
</style>
</head>
<body>

<div class="header">
  <p class="header h1">AI INCOME DAILY</p>
  <h1>💰 수익 대시보드</h1>
  <div class="amount">${est_usd:.2f}</div>
  <div class="amount-label">이번 달 YouTube 예상 수익 · {now} 기준</div>
  <span class="pipeline-count">🚀 자동 파이프라인 {len(ACTIVE_PIPELINES)}개 운영 중</span>
</div>

<div class="main">

  <!-- 수확 링크 -->
  <div class="harvest-section">
    <h2>🌾 수확하기</h2>
    <div class="harvest-grid">
      <a href="https://studio.youtube.com" target="_blank" class="harvest-link">
        <span class="h-icon">🎬</span>
        <span class="h-name">YouTube Studio</span>
        <span class="h-note">수익 → 지급 신청</span>
      </a>
      <a href="https://adsense.google.com" target="_blank" class="harvest-link">
        <span class="h-icon">💵</span>
        <span class="h-name">Google AdSense</span>
        <span class="h-note">$100 이상 시 출금</span>
      </a>
      <a href="https://dev.to/dashboard" target="_blank" class="harvest-link">
        <span class="h-icon">📊</span>
        <span class="h-name">Dev.to</span>
        <span class="h-note">발행 통계 확인</span>
      </a>
      <a href="https://ko-fi.com" target="_blank" class="harvest-link">
        <span class="h-icon">☕</span>
        <span class="h-name">Ko-fi</span>
        <span class="h-note">후원금 수령</span>
      </a>
      <a href="https://kdp.amazon.com" target="_blank" class="harvest-link">
        <span class="h-icon">📚</span>
        <span class="h-name">Amazon KDP</span>
        <span class="h-note">이북 인세 수령</span>
      </a>
      <a href="https://github.com/indiegyu/urban-chainsaw/actions" target="_blank" class="harvest-link">
        <span class="h-icon">⚙️</span>
        <span class="h-name">GitHub Actions</span>
        <span class="h-note">워크플로 현황</span>
      </a>
    </div>
  </div>

  <!-- 카드 그리드 -->
  <div class="grid">

    <!-- YouTube -->
    <div class="card">
      <div class="card-header">
        <div class="card-dot" style="background:#ff0000"></div>
        <span class="card-title">YouTube 채널</span>
      </div>
      <div class="card-body">{yt_body}</div>
    </div>

    <!-- 콘텐츠 생산량 -->
    <div class="card">
      <div class="card-header">
        <div class="card-dot" style="background:#10b981"></div>
        <span class="card-title">콘텐츠 생산 현황</span>
      </div>
      <div class="card-body">{output_body}</div>
    </div>

    <!-- 수익 추이 -->
    <div class="card">
      <div class="card-header">
        <div class="card-dot" style="background:#818cf8"></div>
        <span class="card-title">7일 수익 추이</span>
      </div>
      <div class="card-body">{trend_body}</div>
    </div>

    <!-- 전략 -->
    <div class="card">
      <div class="card-header">
        <div class="card-dot" style="background:#6366f1"></div>
        <span class="card-title">AI 전략 상태</span>
      </div>
      <div class="card-body">{strategy_body}</div>
    </div>

    <!-- 파이프라인 건강도 -->
    <div class="card">
      <div class="card-header">
        <div class="card-dot" style="background:{h_color}"></div>
        <span class="card-title">파이프라인 건강도</span>
      </div>
      <div class="card-body">{health_body}</div>
    </div>

    <!-- 파이프라인 -->
    <div class="card">
      <div class="card-header">
        <div class="card-dot" style="background:#f59e0b"></div>
        <span class="card-title">전체 파이프라인 현황</span>
      </div>
      <div class="card-body">{pipeline_body}</div>
    </div>

  </div>
</div>

<div class="footer">마지막 업데이트: {now} · 매일 22:00 UTC 자동 갱신</div>

</body>
</html>"""


def run():
    from dotenv import load_dotenv
    load_dotenv()

    print("📊 수익 대시보드 생성 중...")

    yt          = fetch_youtube_stats()
    strategy    = fetch_strategy_stats()
    outputs     = count_local_outputs()
    pipe_status = fetch_pipeline_status()
    health      = fetch_pipeline_health()

    # 수익 스냅샷 저장 (히스토리 누적)
    rev_history = save_revenue_snapshot(yt, outputs)

    print(f"  YouTube: 구독자 {yt.get('subscribers', 0):,} / 예상 ${yt.get('est_monthly', 0):.2f}")
    print(f"  콘텐츠: 영상 {outputs['videos']}개 / 블로그 {outputs['blogs']}개 / POD {outputs['pods']}개")
    print(f"  파이프라인 상태 수집: {len(pipe_status)}개 확인됨")
    print(f"  건강도: {health.get('rate', 100)}% (최근 7일 에러 {health.get('error', 0)}건)")
    print(f"  히스토리: {len(rev_history.get('daily', []))}일 누적됨")

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "dashboard.html").write_text(
        build_dashboard(yt, strategy, outputs, pipe_status, rev_history, health),
        encoding="utf-8"
    )

    print(f"\n✅ 대시보드 저장 완료")
    print(f"   → https://indiegyu.github.io/urban-chainsaw/dashboard.html")


if __name__ == "__main__":
    run()
