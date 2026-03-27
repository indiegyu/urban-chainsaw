"""
수익 대시보드 자동 생성
========================
모든 수익 채널 데이터를 한 페이지에 모아 docs/dashboard.html 생성.
GitHub Pages로 배포 → URL 하나에서 전체 수익 확인 + 수확 링크.

매주 월요일 weekly_optimize.yml에서 자동 실행.
수동: workflow_dispatch로 즉시 새로고침 가능.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta

YOUTUBE_API   = "https://www.googleapis.com/youtube/v3"
LS_API        = "https://api.lemonsqueezy.com/v1"
STRATEGY_PATH = Path("scripts/strategy/content_strategy.json")
DOCS_DIR      = Path("docs")
TOKEN_PATH    = "token.json"


# ── 데이터 수집 ────────────────────────────────────────────────────────────────

def fetch_youtube_stats() -> dict:
    try:
        tok = json.loads(Path(TOKEN_PATH).read_text())
        r   = requests.post(tok["token_uri"], data={
            "client_id": tok["client_id"], "client_secret": tok["client_secret"],
            "refresh_token": tok["refresh_token"], "grant_type": "refresh_token",
        })
        access = r.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {access}"}

        # 채널 기본 통계
        ch = requests.get(f"{YOUTUBE_API}/channels?part=statistics,snippet&mine=true",
                          headers=headers, timeout=10).json()
        if not ch.get("items"):
            return {}
        stats = ch["items"][0]["statistics"]
        subs  = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        vids  = int(stats.get("videoCount", 0))

        # 최근 영상 통계 (최대 10개)
        ch_detail = requests.get(
            f"{YOUTUBE_API}/channels?part=contentDetails&mine=true",
            headers=headers, timeout=10).json()
        uploads_id = ch_detail["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = requests.get(f"{YOUTUBE_API}/playlistItems",
                          params={"part":"contentDetails","playlistId":uploads_id,"maxResults":10},
                          headers=headers, timeout=10).json()
        video_ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
        recent_views = 0
        top_video = {}
        if video_ids:
            vr = requests.get(f"{YOUTUBE_API}/videos",
                              params={"part":"snippet,statistics","id":",".join(video_ids)},
                              headers=headers, timeout=10).json()
            for v in vr.get("items", []):
                vc = int(v["statistics"].get("viewCount", 0))
                recent_views += vc
                if vc > top_video.get("views", 0):
                    top_video = {"title": v["snippet"]["title"][:60],
                                 "views": vc, "id": v["id"]}

        # AdSense 예상 수익 (CPM $3 가정, 45% 크리에이터 몫)
        est_monthly_usd = round(recent_views / 1000 * 3 * 0.45, 2)

        return {
            "subscribers":    subs,
            "total_views":    views,
            "video_count":    vids,
            "recent_views":   recent_views,
            "est_monthly":    est_monthly_usd,
            "top_video":      top_video,
            "monetized":      subs >= 1000,
            "subs_needed":    max(0, 1000 - subs),
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_lemonsqueezy_stats() -> dict:
    token = os.environ.get("LEMONSQUEEZY_API_KEY", "")
    if not token:
        return {"error": "LEMONSQUEEZY_API_KEY 시크릿 없음"}
    try:
        headers = {"Authorization": f"Bearer {token}",
                   "Accept": "application/vnd.api+json"}

        # 스토어 목록 먼저 확인 (API 키 유효성 검증 + store_id 확보)
        stores_r = requests.get(f"{LS_API}/stores", headers=headers, timeout=10)
        print(f"  LS /stores → HTTP {stores_r.status_code}")
        if stores_r.status_code == 401:
            return {"error": "API 키 인증 실패 (401) — app.lemonsqueezy.com → Settings → API 키 재확인"}
        if stores_r.status_code != 200:
            return {"error": f"HTTP {stores_r.status_code}: {stores_r.text[:150]}"}

        stores = stores_r.json().get("data", [])
        if not stores:
            return {"total_revenue": 0, "total_orders": 0, "month_revenue": 0,
                    "note": "스토어 없음 — app.lemonsqueezy.com 에서 스토어 생성 필요"}

        store_id = stores[0]["id"]
        print(f"  LS store_id={store_id}")

        # 주문 목록 조회
        r = requests.get(f"{LS_API}/orders", headers=headers,
                         params={"filter[store_id]": store_id, "page[size]": 50},
                         timeout=10)
        print(f"  LS /orders → HTTP {r.status_code}")
        if r.status_code != 200:
            return {"error": f"주문 조회 실패 HTTP {r.status_code}: {r.text[:150]}"}

        orders = r.json().get("data", [])
        total  = sum(o["attributes"].get("total", 0) for o in orders) / 100
        count  = len(orders)
        now    = datetime.now()
        month_total = sum(
            o["attributes"].get("total", 0) / 100 for o in orders
            if o["attributes"].get("created_at", "")[:7] == now.strftime("%Y-%m")
        )
        return {"total_revenue": round(total, 2),
                "total_orders": count,
                "month_revenue": round(month_total, 2)}
    except Exception as e:
        return {"error": str(e)}


def fetch_strategy_stats() -> dict:
    try:
        s = json.loads(STRATEGY_PATH.read_text())
        return {
            "version":          s.get("version", 1),
            "last_updated":     s.get("last_updated", ""),
            "products_made":    len(s.get("gumroad_products_created", [])),
            "products":         s.get("gumroad_products_created", [])[-5:],
            "top_topics":       s.get("top_performing_topics", [])[:3],
            "strategy_note":    s.get("last_strategy_note", ""),
            "income_streams":   s.get("income_streams", {}),
            "activated_streams": s.get("activated_streams", []),
            "total_pipelines":  s.get("total_pipelines", 0),
            "last_expansion":   s.get("last_expansion", ""),
            "groq_suggested":   s.get("groq_suggested_streams", [])[-3:],
        }
    except Exception:
        return {}


# ── HTML 생성 ──────────────────────────────────────────────────────────────────

def _card(title: str, body: str, color: str = "#6366f1") -> str:
    return f"""
<div class="card">
  <div class="card-header" style="border-left:4px solid {color}">
    <h3>{title}</h3>
  </div>
  <div class="card-body">{body}</div>
</div>"""


def _harvest_btn(label: str, url: str, note: str = "") -> str:
    return (f'<a href="{url}" class="harvest-btn" target="_blank">💰 {label}</a>'
            + (f'<span class="harvest-note">{note}</span>' if note else ""))


def build_dashboard(yt: dict, ls: dict, strategy: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # ── YouTube 카드 ──
    if "error" not in yt:
        subs      = f"{yt.get('subscribers',0):,}"
        views     = f"{yt.get('recent_views',0):,}"
        est       = f"${yt.get('est_monthly',0):.2f}"
        mon_badge = ('✅ 수익화 가능' if yt.get('monetized')
                     else f"⏳ 구독자 {yt.get('subs_needed',0):,}명 더 필요")
        top_v     = yt.get("top_video", {})
        top_line  = (f'<p>🏆 최고 영상: <a href="https://youtu.be/{top_v["id"]}" target="_blank">'
                     f'{top_v["title"]} ({top_v["views"]:,} views)</a></p>'
                     if top_v else "")
        yt_body = f"""
<div class="stats-row">
  <div class="stat"><span class="stat-num">{subs}</span><span class="stat-label">구독자</span></div>
  <div class="stat"><span class="stat-num">{views}</span><span class="stat-label">최근 조회수</span></div>
  <div class="stat"><span class="stat-num">{est}</span><span class="stat-label">예상 월 수익</span></div>
</div>
<p class="badge {'green' if yt.get('monetized') else 'yellow'}">{mon_badge}</p>
{top_line}
<div class="harvest-row">
  {_harvest_btn("YouTube Studio", "https://studio.youtube.com", "수익 → 지급")}
  {_harvest_btn("AdSense", "https://adsense.google.com", "$100 이상 시 출금")}
</div>"""
    else:
        yt_body = f'<p class="error">⚠ 데이터 로드 실패: {yt["error"]}</p>'

    # ── Lemon Squeezy 카드 ──
    if "error" not in ls:
        ls_body = f"""
<div class="stats-row">
  <div class="stat"><span class="stat-num">${ls.get('month_revenue',0):.2f}</span><span class="stat-label">이번 달</span></div>
  <div class="stat"><span class="stat-num">${ls.get('total_revenue',0):.2f}</span><span class="stat-label">누적 수익</span></div>
  <div class="stat"><span class="stat-num">{ls.get('total_orders',0)}</span><span class="stat-label">총 주문</span></div>
</div>
<div class="harvest-row">
  {_harvest_btn("Lemon Squeezy 출금", "https://app.lemonsqueezy.com/payouts", "매월 자동 지급")}
</div>"""
    else:
        err_msg = ls.get("error", "알 수 없는 오류")
        note    = ls.get("note", "")
        ls_body = (f'<p class="error">⚠ {err_msg}</p>'
                   + (f'<p class="muted">{note}</p>' if note else "")
                   + '<div class="harvest-row">'
                   + _harvest_btn("Lemon Squeezy 설정", "https://app.lemonsqueezy.com/settings/api")
                   + '</div>')

    # ── 상품 목록 카드 ──
    products = strategy.get("products", [])
    if products:
        prod_rows = "".join(
            f'<tr><td>{p.get("title","")[:45]}</td>'
            f'<td>${p.get("price_usd",0)}</td>'
            f'<td>{p.get("created_at","")}</td>'
            f'<td>{"<a href=\"" + p["url"] + "\" target=\"_blank\">보기</a>" if p.get("url") else "-"}</td></tr>'
            for p in reversed(products)
        )
        prod_body = f"""
<table class="data-table">
<tr><th>상품명</th><th>가격</th><th>생성일</th><th>링크</th></tr>
{prod_rows}
</table>
<p class="muted" style="margin-top:8px">매주 수·토 자동 생성됨</p>"""
    else:
        prod_body = "<p class='muted'>아직 상품 없음 — 첫 수요일에 자동 생성됩니다</p>"

    # ── 전략 카드 ──
    topics_html = "".join(f"<span class='tag'>{t}</span>" for t in strategy.get("top_topics", []))
    strategy_body = f"""
<p><strong>전략 버전:</strong> v{strategy.get('version',1)} &nbsp;
   <strong>마지막 업데이트:</strong> {strategy.get('last_updated','')}</p>
<p><strong>현재 최적 토픽:</strong> {topics_html or '분석 대기 중'}</p>
{f"<p class='insight'>💡 {strategy.get('strategy_note','')}</p>" if strategy.get('strategy_note') else ''}
<p class="muted">매주 월요일 자동 분석·업데이트</p>"""

    # ── 파이프라인 현황 카드 ──
    core_streams = [
        ("🟢", "YouTube 영상", "x2/일", "AdSense"),
        ("🟢", "YouTube Shorts", "x1/일", "AdSense + 알고리즘"),
        ("🟢", "블로그 (GitHub Pages)", "x2/일", "AdSense + 어필리에이트"),
        ("🟢", "KDP 이북 자동 생성", "x1/주", "Amazon 인세 70%"),
        ("🟢", "Lemon Squeezy 상품", "x2/주", "디지털 상품 95%"),
        ("🟢", "AI Tools 디렉토리", "매일 업데이트", "어필리에이트 SEO"),
    ]
    maybe_streams = [
        ("🟡", "Dev.to 발행", "DEVTO_API_KEY"),
        ("🟡", "Medium 파트너", "MEDIUM_TOKEN"),
        ("🟡", "Hashnode 크로스포스팅", "HASHNODE_ACCESS_TOKEN + HASHNODE_PUBLICATION_ID"),
        ("🟡", "Pinterest 핀", "PINTEREST_ACCESS_TOKEN"),
        ("🟡", "Patreon 유료 구독", "PATREON_ACCESS_TOKEN + PATREON_CAMPAIGN_ID"),
        ("🟡", "Twitter/X 포스팅", "TWITTER_API_KEY x4"),
        ("🟡", "Reddit 공유", "REDDIT_CLIENT_ID x4"),
        ("🟡", "Beehiiv 뉴스레터", "BEEHIIV_API_KEY + BEEHIIV_PUB_ID"),
        ("🟡", "Printify POD (티셔츠)", "PRINTIFY_API_KEY + PRINTIFY_SHOP_ID"),
        ("🟡", "Etsy 디지털 상품", "ETSY_API_KEY + ETSY_SHOP_ID"),
        ("🟡", "Ko-fi 후원 버튼", "KOFI_USERNAME"),
        ("🟡", "TikTok 자동 포스팅", "TIKTOK_ACCESS_TOKEN + TIKTOK_OPEN_ID"),
    ]
    active_streams = strategy.get("income_streams", {})
    expanded_rows = "".join(
        f'<tr><td>{info.get("name","")}</td>'
        f'<td><span class="badge {"green" if info.get("status")=="active" else "yellow"}">'
        f'{"🟢 활성" if info.get("status")=="active" else "🟡 대기"}</span></td>'
        f'<td style="color:#64748b;font-size:.8em">{info.get("est_monthly","?")}</td></tr>'
        for sid, info in active_streams.items()
    )

    core_rows = "".join(
        f'<tr><td>{icon} {name}</td><td style="color:#64748b;font-size:.8em">{freq}</td>'
        f'<td style="color:#6ee7b7;font-size:.8em">{revenue}</td></tr>'
        for icon, name, freq, revenue in core_streams
    )
    maybe_rows = "".join(
        f'<tr><td>{icon} {name}</td>'
        f'<td colspan="2" style="color:#fcd34d;font-size:.75em">시크릿 필요: {secret}</td></tr>'
        for icon, name, secret in maybe_streams
    )

    last_exp = strategy.get("last_expansion", "")
    total_p  = strategy.get("total_pipelines", len(core_streams))
    pipeline_body = f"""
<p style="margin-bottom:12px"><strong>총 파이프라인: {total_p + len(core_streams)}개</strong>
  <span class="muted" style="margin-left:8px">마지막 확장: {last_exp[:10] if last_exp else '미실행'}</span></p>
<table class="data-table">
<tr><th>스트림</th><th>주기</th><th>수익 방식</th></tr>
{core_rows}
</table>
<p style="margin-top:12px;color:#fcd34d;font-size:.85em">⏳ 시크릿 등록 시 즉시 활성화</p>
<table class="data-table">
<tr><th>스트림</th><th colspan="2">필요 시크릿</th></tr>
{maybe_rows}
</table>
<p class="muted" style="margin-top:10px">매주 화요일 자동 확장 (weekly_expand.yml)</p>"""

    # ── 전체 수익 합산 ──
    total_est = (yt.get("est_monthly", 0) if "error" not in yt else 0) + \
                (ls.get("month_revenue", 0) if "error" not in ls else 0)
    total_active = len(core_streams) + len(strategy.get("income_streams", {}))

    # ── 플랫폼 수확 링크 ──
    harvest_links = [
        ("YouTube Studio",   "https://studio.youtube.com",                      "AdSense → 지급"),
        ("Lemon Squeezy",    "https://app.lemonsqueezy.com/payouts",             "매월 자동 지급"),
        ("Etsy",             "https://www.etsy.com/your/account",                "Finance → 수령"),
        ("Patreon",          "https://www.patreon.com/dashboard",                "Payouts 탭"),
        ("Dev.to",           "https://dev.to/dashboard",                         "통계 확인"),
        ("Medium",           "https://medium.com/me/partner/dashboard",          "파트너 수익"),
        ("Pinterest",        "https://analytics.pinterest.com",                  "트래픽 확인"),
        ("Google AdSense",   "https://adsense.google.com/adsense/web/main",      "잔액 출금"),
    ]
    harvest_buttons = "".join(
        f'<a href="{url}" class="platform-btn" target="_blank">'
        f'<span class="platform-name">{name}</span>'
        f'<span class="platform-note">{note}</span></a>'
        for name, url, note in harvest_links
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>💰 AI Income Daily — 수익 대시보드</title>
<meta http-equiv="refresh" content="3600">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
  .top-bar{{background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:24px 20px;text-align:center}}
  .top-bar h1{{font-size:1.8em;color:#fff;margin-bottom:.3em}}
  .top-bar .total{{font-size:3em;color:#fff;font-weight:700;margin:.2em 0}}
  .top-bar .sub{{color:rgba(255,255,255,.8);font-size:.9em}}
  .main{{max-width:1000px;margin:0 auto;padding:30px 20px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(440px,1fr));gap:20px;margin-bottom:30px}}
  .card{{background:#1e293b;border:1px solid #334155;border-radius:14px;overflow:hidden}}
  .card-header{{padding:16px 20px;background:#0f172a}}
  .card-header h3{{font-size:1em;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em}}
  .card-body{{padding:20px}}
  .stats-row{{display:flex;gap:16px;margin-bottom:16px}}
  .stat{{flex:1;background:#0f172a;border-radius:10px;padding:14px;text-align:center}}
  .stat-num{{display:block;font-size:1.6em;font-weight:700;color:#fff}}
  .stat-label{{font-size:.75em;color:#64748b;margin-top:4px;display:block}}
  .badge{{display:inline-block;padding:4px 12px;border-radius:20px;font-size:.8em;margin-bottom:12px}}
  .badge.green{{background:#064e3b;color:#6ee7b7}}
  .badge.yellow{{background:#451a03;color:#fcd34d}}
  .harvest-row{{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}}
  .harvest-btn{{background:#6366f1;color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:.85em;white-space:nowrap}}
  .harvest-btn:hover{{background:#4f46e5}}
  .harvest-note{{color:#64748b;font-size:.75em;margin-left:6px;align-self:center}}
  .data-table{{width:100%;border-collapse:collapse;font-size:.85em}}
  .data-table th{{text-align:left;padding:8px;color:#64748b;border-bottom:1px solid #334155}}
  .data-table td{{padding:8px;border-bottom:1px solid #1e293b}}
  .data-table a{{color:#818cf8}}
  .tag{{background:#1e3a5f;color:#93c5fd;padding:3px 10px;border-radius:12px;font-size:.8em;margin-right:6px}}
  .insight{{background:#1e293b;border-left:3px solid #6366f1;padding:10px 14px;margin-top:10px;font-size:.9em;color:#cbd5e1}}
  .muted{{color:#475569;font-size:.85em;margin-top:8px}}
  .error{{color:#f87171;font-size:.85em}}

  /* 수확 섹션 */
  .harvest-section{{background:#1e293b;border-radius:16px;padding:28px;margin-bottom:30px}}
  .harvest-section h2{{color:#fff;margin-bottom:20px;font-size:1.3em}}
  .platforms-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}}
  .platform-btn{{background:#0f172a;border:1px solid #334155;border-radius:12px;padding:16px;
                 text-decoration:none;display:flex;flex-direction:column;gap:4px;transition:.2s}}
  .platform-btn:hover{{border-color:#6366f1;transform:translateY(-2px)}}
  .platform-name{{color:#e2e8f0;font-weight:600;font-size:.95em}}
  .platform-note{{color:#64748b;font-size:.75em}}

  .updated{{text-align:center;color:#334155;font-size:.8em;padding:20px}}
</style>
</head>
<body>

<div class="top-bar">
  <h1>💰 AI Income Daily</h1>
  <div class="total">${total_est:.2f}</div>
  <div class="sub">이번 달 예상 수익 합산 · {now} 기준</div>
  <div style="margin-top:8px;font-size:1.1em;color:rgba(255,255,255,.9)">
    🚀 활성 수익 파이프라인 <strong>{total_active}개</strong> 자동 운영 중
  </div>
  <div style="margin-top:6px;font-size:.85em;color:rgba(255,255,255,.6)">
    매주 화요일 자동 확장 · 매주 월요일 전략 업데이트
  </div>
</div>

<div class="main">

  <!-- 수확 버튼 모음 -->
  <div class="harvest-section">
    <h2>🌾 수확하기 — 플랫폼별 정산 링크</h2>
    <div class="platforms-grid">
      {harvest_buttons}
    </div>
  </div>

  <!-- 수익 카드 -->
  <div class="grid">
    {_card("📺 YouTube 채널", yt_body, "#ff0000")}
    {_card("🍋 Lemon Squeezy 상품 판매", ls_body, "#fbbf24")}
    {_card("🛍️ 내 디지털 상품 목록", prod_body, "#10b981")}
    {_card("🧠 AI 전략 상태", strategy_body, "#6366f1")}
    {_card("🔥 전체 수익 파이프라인 현황", pipeline_body, "#f59e0b")}
  </div>

</div>

<div class="updated">마지막 업데이트: {now} · 매주 월요일 자동 갱신</div>

</body>
</html>"""


def run():
    from dotenv import load_dotenv
    load_dotenv()

    print("📊 수익 대시보드 생성 중...")

    yt       = fetch_youtube_stats()
    ls       = fetch_lemonsqueezy_stats()
    strategy = fetch_strategy_stats()

    print(f"  YouTube: 구독자 {yt.get('subscribers',0):,} / 예상 ${yt.get('est_monthly',0):.2f}")
    print(f"  Lemon Squeezy: 이달 ${ls.get('month_revenue',0):.2f} / 누적 ${ls.get('total_revenue',0):.2f}")
    print(f"  상품: {strategy.get('products_made',0)}개")

    DOCS_DIR.mkdir(exist_ok=True)
    html = build_dashboard(yt, ls, strategy)
    (DOCS_DIR / "dashboard.html").write_text(html, encoding="utf-8")

    print(f"\n✅ 대시보드 저장 완료")
    print(f"   → https://indiegyu.github.io/urban-chainsaw/dashboard.html")


if __name__ == "__main__":
    run()
