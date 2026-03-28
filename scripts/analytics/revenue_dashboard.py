"""
수익 대시보드 — 메인 실행
==========================
KST 기준 · 실사용 파이프라인만 표시 · 7일 트렌드 · 건강도
"""

from pathlib import Path
from .dashboard_data import (
    fetch_youtube_stats, fetch_strategy_stats, count_local_outputs,
    fetch_pipeline_status, save_revenue_snapshot, get_revenue_trend,
    fetch_pipeline_health, now_kst_str,
)
from .dashboard_html import (
    card_youtube, card_content, card_trend, card_strategy,
    card_health, card_pipelines, ACTIVE_PIPELINES,
)

DOCS_DIR = Path("docs")

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#080e1a;color:#e2e8f0;min-height:100vh}
.header{background:linear-gradient(135deg,#1e1b4b 0%,#312e81 50%,#1e1b4b 100%);padding:32px 20px 26px;text-align:center;border-bottom:1px solid #2d2d6b}
.header h1{font-size:1.4em;font-weight:700;color:#a5b4fc;letter-spacing:.05em;margin-bottom:4px}
.header .amount{font-size:3.2em;font-weight:800;color:#fff;margin:6px 0;line-height:1}
.header .sub{color:#818cf8;font-size:.85em;margin-bottom:14px}
.header .pill{display:inline-block;background:rgba(99,102,241,.2);border:1px solid rgba(99,102,241,.4);border-radius:20px;padding:5px 16px;font-size:.82em;color:#a5b4fc}
.main{max-width:960px;margin:0 auto;padding:24px 16px}
.harvest{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:20px;margin-bottom:20px}
.harvest h2{font-size:.9em;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px}
.hgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.hlink{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:12px 14px;text-decoration:none;display:block;transition:.15s}
.hlink:hover{border-color:#6366f1;background:#1e2a45;transform:translateY(-1px)}
.hlink .hi{font-size:1.2em;display:block;margin-bottom:4px}
.hlink .hn{color:#e2e8f0;font-weight:600;font-size:.85em;display:block}
.hlink .hd{color:#475569;font-size:.72em;display:block;margin-top:2px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(440px,1fr));gap:14px}
.card{background:#0f172a;border:1px solid #1e293b;border-radius:12px;overflow:hidden}
.card-h{padding:12px 18px;border-bottom:1px solid #1e293b;display:flex;align-items:center;gap:8px}
.card-h .ct{font-size:.78em;color:#64748b;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.card-b{padding:18px}
.stats-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(85px,1fr));gap:8px;margin-bottom:12px}
.stat{background:#1e293b;border-radius:8px;padding:10px;text-align:center}
.stat-num{display:block;font-size:1.3em;font-weight:700;color:#fff}
.stat-label{font-size:.68em;color:#475569;margin-top:2px;display:block;line-height:1.2}
.badge{display:inline-block;padding:3px 10px;border-radius:16px;font-size:.78em;font-weight:500}
.badge.green{background:#052e16;color:#86efac;border:1px solid #166534}
.badge.yellow{background:#1c1400;color:#fbbf24;border:1px solid #92400e}
.btn-primary{background:#4f46e5;color:#fff;padding:7px 14px;border-radius:7px;text-decoration:none;font-size:.8em;font-weight:600;white-space:nowrap}
.btn-primary:hover{background:#4338ca}
.btn-secondary{background:#1e293b;color:#94a3b8;padding:7px 14px;border-radius:7px;text-decoration:none;font-size:.8em;border:1px solid #334155;white-space:nowrap}
.btn-secondary:hover{border-color:#6366f1;color:#e2e8f0}
.data-table{width:100%;border-collapse:collapse;font-size:.8em}
.data-table th{text-align:left;padding:7px 5px;color:#475569;border-bottom:1px solid #1e293b;font-weight:500}
.data-table td{padding:7px 5px;border-bottom:1px solid #0f172a}
.tag{background:#1e3a5f;color:#93c5fd;padding:2px 9px;border-radius:10px;font-size:.76em;margin-right:4px;margin-bottom:3px;display:inline-block}
.muted{color:#475569;font-size:.8em}
.error{color:#f87171;font-size:.8em}
.footer{text-align:center;color:#1e293b;font-size:.72em;padding:20px 0 36px}
"""


def build_dashboard(yt, strategy, outputs, pipe_status, rev_history, health):
    now = now_kst_str()
    est = yt.get("est_monthly", 0) if "error" not in yt else 0
    trend = get_revenue_trend(rev_history or {}, days=7)
    health_html, h_color = card_health(health or {})

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Income Daily — 수익 대시보드</title>
<meta http-equiv="refresh" content="3600">
<style>{CSS}</style>
</head>
<body>

<div class="header">
  <h1>AI INCOME DAILY</h1>
  <div class="amount">${est:.2f}</div>
  <div class="sub">이번 달 예상 수익 · {now} 기준</div>
  <span class="pill">자동 파이프라인 {len(ACTIVE_PIPELINES)}개 운영 중</span>
</div>

<div class="main">

  <div class="harvest">
    <h2>수확하기</h2>
    <div class="hgrid">
      <a href="https://studio.youtube.com" target="_blank" class="hlink">
        <span class="hi">🎬</span><span class="hn">YouTube Studio</span><span class="hd">수익 확인</span></a>
      <a href="https://adsense.google.com" target="_blank" class="hlink">
        <span class="hi">💵</span><span class="hn">AdSense</span><span class="hd">$100 이상 출금</span></a>
      <a href="https://kdp.amazon.com" target="_blank" class="hlink">
        <span class="hi">📚</span><span class="hn">Amazon KDP</span><span class="hd">이북 인세</span></a>
      <a href="https://github.com/indiegyu/urban-chainsaw/actions" target="_blank" class="hlink">
        <span class="hi">⚙️</span><span class="hn">GitHub Actions</span><span class="hd">워크플로 현황</span></a>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-h"><div class="dot" style="background:#ff0000"></div><span class="ct">YouTube 채널</span></div>
      <div class="card-b">{card_youtube(yt)}</div>
    </div>
    <div class="card">
      <div class="card-h"><div class="dot" style="background:#10b981"></div><span class="ct">콘텐츠 생산 현황</span></div>
      <div class="card-b">{card_content(outputs)}</div>
    </div>
    <div class="card">
      <div class="card-h"><div class="dot" style="background:#818cf8"></div><span class="ct">7일 추이</span></div>
      <div class="card-b">{card_trend(trend)}</div>
    </div>
    <div class="card">
      <div class="card-h"><div class="dot" style="background:#6366f1"></div><span class="ct">AI 전략</span></div>
      <div class="card-b">{card_strategy(strategy)}</div>
    </div>
    <div class="card">
      <div class="card-h"><div class="dot" style="background:{h_color}"></div><span class="ct">파이프라인 건강도</span></div>
      <div class="card-b">{health_html}</div>
    </div>
    <div class="card">
      <div class="card-h"><div class="dot" style="background:#f59e0b"></div><span class="ct">파이프라인 현황</span></div>
      <div class="card-b">{card_pipelines(pipe_status)}</div>
    </div>
  </div>
</div>

<div class="footer">마지막 업데이트: {now} · 매일 07:00 KST 자동 갱신</div>
</body>
</html>"""


def run():
    from dotenv import load_dotenv
    load_dotenv()

    print("📊 수익 대시보드 생성 중...")

    yt = fetch_youtube_stats()
    strategy = fetch_strategy_stats()
    outputs = count_local_outputs()
    pipe_status = fetch_pipeline_status()
    health = fetch_pipeline_health()
    rev_history = save_revenue_snapshot(yt, outputs)

    print(f"  YouTube: 구독자 {yt.get('subscribers', 0):,} / 예상 ${yt.get('est_monthly', 0):.2f}")
    print(f"  콘텐츠: 영상 {outputs['videos']} / 블로그 {outputs['blogs']} / POD {outputs['pods']} / 이북 {outputs.get('ebooks',0)}")
    print(f"  건강도: {health.get('rate', 100)}%")

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "dashboard.html").write_text(
        build_dashboard(yt, strategy, outputs, pipe_status, rev_history, health),
        encoding="utf-8"
    )

    print(f"\n✅ 대시보드 저장 완료 ({now_kst_str()})")


if __name__ == "__main__":
    run()
