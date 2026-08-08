"""
대시보드 HTML 빌드 모듈
========================
데이터를 받아서 완성된 HTML 문자열을 반환합니다.
"""

from .dashboard_data import relative_time_kst, now_kst_str

# ── 실제 활성 파이프라인 (출력 확인된 것만) ──────────────────────────────────
ACTIVE_PIPELINES = [
    ("📺", "YouTube 영상",    "매일 2회", "18:00, 06:00", "AdSense CPM",    "youtube"),
    ("🩳", "YouTube Shorts",  "매일 1회", "00:00",        "AdSense + 노출", "shorts"),
    ("📝", "블로그 포스트",    "매일 2회", "17:00, 01:00", "어필리에이트",   "blog"),
    ("🎨", "POD 디자인",      "매일 1회", "17:00",        "Etsy/Printify",  "pod"),
    ("📖", "KDP 이북",        "매주 일",  "16:00",        "Amazon 인세",    "ebook"),
    ("🧠", "AI 전략 최적화",   "매주 월",  "자동",         "성과 기반 개선", "strategy"),
]

PIPE_STATUS_KEYS = {p[1]: p[5] for p in ACTIVE_PIPELINES}


def _sparkline(values, width=180, height=36, color="#818cf8"):
    if not values or len(values) < 2:
        return ""
    mx, mn = max(values) or 1, min(values)
    rng = mx - mn or 1
    step = width / (len(values) - 1)
    pts = [f"{round(i*step,1)},{round(height-(v-mn)/rng*(height-4)-2,1)}" for i, v in enumerate(values)]
    fill_pts = pts + [f"{width},{height}", f"0,{height}"]
    lx, ly = pts[-1].split(",")
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle">'
        f'<defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>'
        f'</linearGradient></defs>'
        f'<polygon points="{" ".join(fill_pts)}" fill="url(#sg)"/>'
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>'
        f'<circle cx="{lx}" cy="{ly}" r="3" fill="{color}"/></svg>'
    )


# ── 개별 카드 빌더들 ─────────────────────────────────────────────────────────

def card_youtube(yt):
    if "error" in yt or not yt:
        return f'<p class="error">YouTube 데이터 로드 실패: {yt.get("error","token 확인 필요")}</p>'

    subs = yt.get("subscribers", 0)
    badge = ('<span class="badge green">수익화 조건 충족</span>' if yt.get("monetized")
             else f'<span class="badge yellow">구독자 {yt.get("subs_needed",0):,}명 더 필요</span>')

    top_v = yt.get("top_video", {})
    top_html = (f'<p style="margin-top:10px;font-size:.85em">🏆 '
                f'<a href="https://youtu.be/{top_v["id"]}" target="_blank" style="color:#818cf8">'
                f'{top_v["title"]}</a> ({top_v["views"]:,} views)</p>') if top_v else ""

    # 최근 영상 목록
    vids_html = ""
    for v in yt.get("recent_videos", [])[:5]:
        vids_html += (f'<tr><td style="font-size:.8em">'
                      f'<a href="https://youtu.be/{v["id"]}" target="_blank" style="color:#94a3b8">'
                      f'{v["title"][:40]}</a></td>'
                      f'<td style="color:#6ee7b7;font-size:.8em;text-align:right">{v["views"]:,}</td>'
                      f'<td style="color:#818cf8;font-size:.8em;text-align:right">{v["likes"]:,}</td></tr>')

    vids_table = ""
    if vids_html:
        vids_table = (f'<table class="data-table" style="margin-top:14px">'
                      f'<tr><th>최근 영상</th><th style="text-align:right">조회</th>'
                      f'<th style="text-align:right">좋아요</th></tr>{vids_html}</table>')

    return f"""
<div class="stats-row">
  <div class="stat"><span class="stat-num">{subs:,}</span><span class="stat-label">구독자</span></div>
  <div class="stat"><span class="stat-num">{yt.get('recent_views',0):,}</span><span class="stat-label">최근 조회수</span></div>
  <div class="stat"><span class="stat-num">${yt.get('est_monthly',0):.2f}</span><span class="stat-label">예상 월수익</span></div>
  <div class="stat"><span class="stat-num">{yt.get('video_count',0):,}</span><span class="stat-label">총 영상</span></div>
</div>
{badge}{top_html}{vids_table}
<div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
  <a href="https://studio.youtube.com" target="_blank" class="btn-primary">YouTube Studio</a>
  <a href="https://adsense.google.com" target="_blank" class="btn-secondary">AdSense</a>
</div>"""


def card_content(outputs):
    recent_html = ""
    for b in outputs.get("blogs_recent", []):
        recent_html += f'<p style="font-size:.78em;color:#64748b;margin-top:2px">📄 {b["name"][:35]} · {b["date"]}</p>'

    return f"""
<div class="stats-row">
  <div class="stat"><span class="stat-num">{outputs['videos']}</span><span class="stat-label">영상</span></div>
  <div class="stat"><span class="stat-num">{outputs['blogs']}</span><span class="stat-label">블로그</span></div>
  <div class="stat"><span class="stat-num">{outputs['pods']}</span><span class="stat-label">POD</span></div>
  <div class="stat"><span class="stat-num">{outputs.get('ebooks',0)}</span><span class="stat-label">이북</span></div>
</div>
{recent_html if recent_html else '<p class="muted">최근 블로그 없음</p>'}
<div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
  <a href="https://indiegyu.github.io/urban-chainsaw/" target="_blank" class="btn-primary">블로그 보기</a>
  <a href="https://github.com/indiegyu/urban-chainsaw/actions" target="_blank" class="btn-secondary">Actions</a>
</div>"""


def card_trend(trend_data):
    if not trend_data or len(trend_data) < 2:
        return '<p class="muted">데이터 수집 중... (2일 후 트렌드 표시)</p>'

    views = [d.get("yt_recent_views", 0) for d in trend_data]
    subs = [d.get("yt_subscribers", 0) for d in trend_data]
    vg = round((views[-1] - views[0]) / views[0] * 100, 1) if views[0] > 0 else 0
    sg = subs[-1] - subs[0]

    return f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
  <div style="background:#1e293b;border-radius:10px;padding:12px">
    <p style="color:#64748b;font-size:.73em;margin-bottom:4px">조회수 (7일)</p>
    <p style="font-size:1em;font-weight:700;color:#fff">{views[-1]:,} <span style="font-size:.8em;color:{'#6ee7b7' if vg>=0 else '#f87171'}">{vg:+.1f}%</span></p>
    <div style="margin-top:6px">{_sparkline(views)}</div>
  </div>
  <div style="background:#1e293b;border-radius:10px;padding:12px">
    <p style="color:#64748b;font-size:.73em;margin-bottom:4px">구독자 (7일)</p>
    <p style="font-size:1em;font-weight:700;color:#fff">{subs[-1]:,} <span style="font-size:.8em;color:{'#6ee7b7' if sg>=0 else '#f87171'}">{sg:+,}</span></p>
    <div style="margin-top:6px">{_sparkline(subs, color="#6ee7b7")}</div>
  </div>
</div>
<p class="muted" style="margin-top:8px">매일 07:00 KST 자동 기록</p>"""


def card_strategy(strategy):
    topics = " ".join(f'<span class="tag">{t}</span>' for t in strategy.get("top_topics", [])) or '<span class="muted">분석 대기</span>'
    note = strategy.get("strategy_note", "")
    note_html = f'<p style="margin-top:8px;font-size:.83em;color:#a5b4fc;font-style:italic">💡 {note}</p>' if note else ""

    return f"""
<p><strong>전략 v{strategy.get('version', 1)}</strong>
   <span class="muted" style="margin-left:8px">{strategy.get('last_updated','미실행')}</span></p>
<p style="margin-top:8px">{topics}</p>
{note_html}
<p class="muted" style="margin-top:10px">매주 월요일 YouTube 성과 분석 → 자동 업데이트</p>"""


def card_health(health):
    rate = health.get("rate", 100)
    total = health.get("total", 0)
    errs = health.get("error", 0)
    color = "#6ee7b7" if rate >= 90 else ("#fbbf24" if rate >= 70 else "#f87171")

    err_html = ""
    for e in health.get("recent_errors", [])[-3:]:
        ts = relative_time_kst(e.get("timestamp", ""))
        err_html += f'<p style="font-size:.76em;color:#f87171;margin-top:3px">[{e.get("pipeline","?")}] {e.get("error","")[:50]} · {ts}</p>'

    return f"""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:10px">
  <div style="position:relative;width:72px;height:72px">
    <svg viewBox="0 0 36 36" width="72" height="72">
      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke="#1e293b" stroke-width="3"/>
      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="{rate}, 100" stroke-linecap="round"/>
    </svg>
    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:1em;font-weight:700;color:{color}">{rate}%</div>
  </div>
  <div>
    <p style="font-weight:600;color:#e2e8f0">7일 성공률</p>
    <p style="color:#64748b;font-size:.8em">실행 {total}회 · 에러 {errs}회</p>
  </div>
</div>
{err_html if err_html else '<p style="color:#6ee7b7;font-size:.8em">최근 에러 없음</p>'}""", color


def card_pipelines(pipe_status):
    ps = pipe_status or {}

    def _cell(key):
        if key not in ps:
            return '<td style="color:#334155;font-size:.73em">–</td>'
        info = ps[key]
        rel = relative_time_kst(info.get("ts", ""))
        detail = info.get("detail", "")
        d_span = f' <span style="color:#475569">· {detail}</span>' if detail else ""
        if info.get("ok"):
            return f'<td style="font-size:.73em"><span style="color:#6ee7b7">✓</span> <span style="color:#64748b">{rel}</span>{d_span}</td>'
        return f'<td style="font-size:.73em"><span style="color:#f87171">✗ {info.get("detail","실패")}</span></td>'

    rows = ""
    for icon, name, freq, time_kst, revenue, key in ACTIVE_PIPELINES:
        rows += (f'<tr><td style="font-size:.83em">{icon} {name}</td>'
                 f'<td style="color:#94a3b8;font-size:.76em">{freq}</td>'
                 f'<td style="color:#64748b;font-size:.76em">{time_kst}</td>'
                 f'<td style="color:#6ee7b7;font-size:.76em">{revenue}</td>'
                 f'{_cell(key)}</tr>')

    return f"""
<p style="margin-bottom:10px"><strong style="color:#6ee7b7">활성 {len(ACTIVE_PIPELINES)}개</strong>
<span class="muted" style="margin-left:8px">시간은 KST 기준</span></p>
<table class="data-table">
<tr><th>파이프라인</th><th>주기</th><th>실행 시간</th><th>수익</th><th>상태</th></tr>
{rows}
</table>"""
