"""
GitHub Pages 블로그 배포 스크립트
=================================
scripts/blog/output/ 의 HTML 파일들을 docs/ 폴더로 복사하고
index.html을 자동 생성합니다.

GitHub Pages (Settings → Pages → Source: Deploy from branch /docs)로
무료 호스팅 후 Google AdSense 코드 삽입.

AdSense 승인 요건:
  - 충분한 콘텐츠 (최소 20~30개 포스트 권장)
  - 커스텀 도메인 (.github.io 또는 커스텀)
  - Privacy Policy 페이지 필요

필요한 환경변수:
  ADSENSE_CLIENT_ID — ca-pub-XXXX (AdSense 승인 후 입력)
"""

import os, shutil, json, re
from pathlib import Path
from datetime import datetime

BLOG_OUTPUT = Path(__file__).parent.parent / "blog" / "output"
DOCS_DIR    = Path(__file__).parent.parent.parent / "docs"
ADSENSE_ID  = os.environ.get("ADSENSE_CLIENT_ID", "")  # ca-pub-XXXX

ADSENSE_SNIPPET = ""
if ADSENSE_ID:
    ADSENSE_SNIPPET = f"""
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_ID}"
     crossorigin="anonymous"></script>
<!-- auto ads -->
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="{ADSENSE_ID}"
     data-ad-slot="auto"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
"""

SITE_NAME    = "AI Income Daily"
SITE_TAGLINE = "Daily AI Side Hustles, Automation Tips & Make Money Online"
BEEHIIV_PUB  = os.environ.get("BEEHIIV_PUB_ID", "")
KOFI_USER    = os.environ.get("KOFI_USERNAME", "")
PAGES_URL    = os.environ.get("GITHUB_PAGES_URL", "https://indiegyu.github.io/urban-chainsaw").rstrip("/")


def _subscribe_form() -> str:
    """Beehiiv 이메일 구독 폼"""
    if not BEEHIIV_PUB:
        return ""
    return f"""
<div style="background:linear-gradient(135deg,#1e1b4b,#312e81);border-radius:14px;
            padding:30px 24px;margin:28px 0;text-align:center;color:#e2e8f0">
  <h2 style="font-size:1.2em;margin:0 0 8px;color:#a5b4fc">📧 무료 AI 수익 뉴스레터</h2>
  <p style="font-size:.88em;color:#94a3b8;margin:0 0 18px">매일 아침 실행 가능한 AI 수익화 팁 · 스팸 없음</p>
  <a href="https://www.beehiiv.com/subscribe/{BEEHIIV_PUB}" target="_blank" rel="noopener"
     style="background:#6366f1;color:#fff;padding:12px 28px;border-radius:8px;
            text-decoration:none;font-weight:700;font-size:.95em;display:inline-block">
    지금 무료 구독하기 →
  </a>
</div>"""


def _affiliate_box() -> str:
    """어필리에이트 추천 박스"""
    pfy = os.environ.get("PRINTIFY_AFF_ID", "")
    fiv = os.environ.get("FIVERR_AFF_ID", "")
    printify_url = f"https://printify.com/app/register?referrer={pfy}" if pfy else "https://printify.com"
    fiverr_url   = f"https://go.fiverr.com/visit/?bta={fiv}&brand=fiverrcpa" if fiv else "https://fiverr.com"
    return f"""
<div style="background:#fff;border:2px solid #e0e7ff;border-radius:12px;padding:22px;margin:28px 0;
            font-family:-apple-system,sans-serif">
  <h3 style="font-size:1em;color:#4f46e5;margin:0 0 14px">🔧 지금 바로 시작할 수 있는 무료 도구</h3>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px">
    <a href="{printify_url}" target="_blank" rel="noopener sponsored"
       style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;
              text-decoration:none;text-align:center;display:block">
      <div style="font-size:1.4em">🎨</div>
      <div style="font-weight:700;color:#166534;font-size:.88em;margin-top:4px">Printify</div>
      <div style="color:#4ade80;font-size:.75em">무료 POD 플랫폼</div>
    </a>
    <a href="{fiverr_url}" target="_blank" rel="noopener sponsored"
       style="background:#fefce8;border:1px solid #fde047;border-radius:8px;padding:12px;
              text-decoration:none;text-align:center;display:block">
      <div style="font-size:1.4em">💼</div>
      <div style="font-weight:700;color:#713f12;font-size:.88em;margin-top:4px">Fiverr</div>
      <div style="color:#ca8a04;font-size:.75em">AI 서비스 판매</div>
    </a>
    <a href="https://beehiiv.com" target="_blank" rel="noopener"
       style="background:#fdf4ff;border:1px solid #e879f9;border-radius:8px;padding:12px;
              text-decoration:none;text-align:center;display:block">
      <div style="font-size:1.4em">📧</div>
      <div style="font-weight:700;color:#701a75;font-size:.88em;margin-top:4px">Beehiiv</div>
      <div style="color:#d946ef;font-size:.75em">뉴스레터 플랫폼 무료</div>
    </a>
    <a href="https://elevenlabs.io" target="_blank" rel="noopener"
       style="background:#eff6ff;border:1px solid #93c5fd;border-radius:8px;padding:12px;
              text-decoration:none;text-align:center;display:block">
      <div style="font-size:1.4em">🎙</div>
      <div style="font-weight:700;color:#1e3a8a;font-size:.88em;margin-top:4px">ElevenLabs</div>
      <div style="color:#3b82f6;font-size:.75em">AI 보이스 무료</div>
    </a>
  </div>
</div>"""


def build_index(posts: list) -> str:
    cards = ""
    for i, p in enumerate(posts[:50]):  # 최신 50개
        cards += f"""
    <article class="card">
      <h2><a href="{p['file']}">{p['title']}</a></h2>
      <p class="meta">📅 {p['date']} · 📖 {p['word_count']} words</p>
      <p style="color:#475569;font-size:.9em;line-height:1.6">{p['desc']}</p>
      <div style="margin-top:10px">{''.join(f'<span class="tag">{t}</span>' for t in p['tags'][:4])}</div>
      <a href="{p['file']}" style="display:inline-block;margin-top:12px;color:#4f46e5;font-size:.85em;font-weight:600">읽기 →</a>
    </article>
    {ADSENSE_SNIPPET if i > 0 and i % 5 == 0 else ''}"""

    kofi_strip = (
        f'<a href="https://ko-fi.com/{KOFI_USER}" target="_blank" rel="noopener" '
        f'style="background:#ff5e5b;color:#fff;padding:8px 18px;border-radius:20px;'
        f'text-decoration:none;font-size:.82em;font-weight:700">☕ Buy me a coffee</a>'
        if KOFI_USER else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{SITE_TAGLINE}">
<meta property="og:title" content="{SITE_NAME}">
<meta property="og:description" content="{SITE_TAGLINE}">
<title>{SITE_NAME} — AI Side Hustles & Passive Income</title>
{('<!-- Google AdSense -->' + chr(10) + f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_ID}" crossorigin="anonymous"></script>') if ADSENSE_ID else ''}
<style>
:root {{ --primary:#0f172a; --accent:#6366f1; --text:#334155; --bg:#f1f5f9; --card:#fff; }}
* {{ box-sizing:border-box; margin:0; padding:0 }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--text); line-height:1.7 }}
/* 상단 고정 바 */
.top-bar {{ background:var(--primary); color:#94a3b8; font-size:.8em; padding:6px 16px;
            display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px }}
.top-bar a {{ color:#a5b4fc; text-decoration:none; font-weight:600 }}
/* 헤더 */
header {{ background:linear-gradient(135deg,#1e1b4b,#312e81); color:#fff; padding:40px 20px; text-align:center }}
header h1 {{ font-size:2.2rem; font-weight:800; margin-bottom:8px }}
header p {{ opacity:.8; font-size:1.05em; max-width:600px; margin:0 auto 20px }}
.cta-strip {{ display:flex; gap:10px; justify-content:center; flex-wrap:wrap }}
.cta-strip a {{ padding:10px 20px; border-radius:8px; text-decoration:none; font-weight:700; font-size:.88em }}
.btn-red {{ background:#ff0000; color:#fff }}
.btn-indigo {{ background:#6366f1; color:#fff }}
.btn-ko {{ background:#ff5e5b; color:#fff }}
/* 레이아웃 */
.wrap {{ max-width:960px; margin:0 auto; padding:24px 16px; display:grid;
          grid-template-columns:1fr 300px; gap:24px }}
@media(max-width:700px) {{ .wrap {{ grid-template-columns:1fr }} .sidebar {{ display:none }} }}
.card {{ background:var(--card); border-radius:12px; padding:20px; margin-bottom:16px;
          box-shadow:0 1px 3px rgba(0,0,0,.06); border:1px solid #e2e8f0 }}
.card h2 {{ font-size:1.15rem; margin-bottom:6px }}
.card h2 a {{ color:var(--primary); text-decoration:none }}
.card h2 a:hover {{ color:var(--accent) }}
.meta {{ font-size:.78rem; color:#94a3b8; margin-bottom:.6rem }}
.tag {{ background:#e0e7ff; color:var(--accent); border-radius:4px; padding:.15rem .45rem; font-size:.72rem; margin-right:.3rem }}
/* 사이드바 */
.sidebar-card {{ background:#fff; border-radius:12px; padding:18px; margin-bottom:16px;
                  border:1px solid #e2e8f0; font-size:.87em }}
.sidebar-card h3 {{ font-size:.95em; font-weight:700; margin-bottom:12px; color:#0f172a }}
.sidebar-tool {{ display:flex; align-items:center; gap:10px; padding:8px 0;
                  border-bottom:1px solid #f1f5f9; text-decoration:none; color:#334155 }}
.sidebar-tool:hover {{ color:var(--accent) }}
footer {{ text-align:center; padding:28px 16px; color:#94a3b8; font-size:.82rem; border-top:1px solid #e2e8f0; background:#fff }}
.ads {{ margin:16px 0; text-align:center }}
</style>
</head>
<body>

<!-- 상단 고정 바 -->
<div class="top-bar">
  <span>🤖 AI Income Daily — 매일 자동 생성되는 수익화 블로그</span>
  <span>
    <a href="https://www.youtube.com/@psg9806" target="_blank">▶ YouTube</a> &nbsp;|&nbsp;
    <a href="dashboard.html">📊 대시보드</a>
    {f'&nbsp;|&nbsp;<a href="https://ko-fi.com/{KOFI_USER}" target="_blank">☕ Ko-fi</a>' if KOFI_USER else ""}
  </span>
</div>

<!-- 헤더 -->
<header>
  <h1>🤖 {SITE_NAME}</h1>
  <p>{SITE_TAGLINE}</p>
  <div class="cta-strip">
    <a href="https://www.youtube.com/@psg9806" target="_blank" class="cta-strip a btn-red">▶ YouTube 구독</a>
    {f'<a href="https://www.beehiiv.com/subscribe/{BEEHIIV_PUB}" target="_blank" class="cta-strip a btn-indigo">📧 뉴스레터 구독</a>' if BEEHIIV_PUB else ""}
    {f'<a href="https://ko-fi.com/{KOFI_USER}" target="_blank" class="cta-strip a btn-ko">☕ 후원하기</a>' if KOFI_USER else ""}
    <a href="ai-tools.html" style="background:#1e293b;color:#94a3b8;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:700;font-size:.88em">🔧 AI Tools</a>
  </div>
</header>

<div class="ads">{ADSENSE_SNIPPET}</div>

<div class="wrap">
  <!-- 메인 포스트 목록 -->
  <main>
    {_subscribe_form()}
    {cards}
  </main>

  <!-- 사이드바 -->
  <aside class="sidebar">
    <div class="ads">{ADSENSE_SNIPPET}</div>

    <div class="sidebar-card">
      <h3>🚀 무료 AI 수익화 도구</h3>
      <a class="sidebar-tool" href="https://printify.com" target="_blank" rel="noopener">
        <span>🎨</span><span><strong>Printify</strong><br><small style="color:#64748b">POD 무료 시작</small></span>
      </a>
      <a class="sidebar-tool" href="https://elevenlabs.io" target="_blank" rel="noopener">
        <span>🎙</span><span><strong>ElevenLabs</strong><br><small style="color:#64748b">AI 보이스 무료</small></span>
      </a>
      <a class="sidebar-tool" href="https://beehiiv.com" target="_blank" rel="noopener">
        <span>📧</span><span><strong>Beehiiv</strong><br><small style="color:#64748b">뉴스레터 2500명 무료</small></span>
      </a>
      <a class="sidebar-tool" href="https://canva.com" target="_blank" rel="noopener">
        <span>🎨</span><span><strong>Canva</strong><br><small style="color:#64748b">무료 디자인 툴</small></span>
      </a>
      <a class="sidebar-tool" href="https://groq.com" target="_blank" rel="noopener">
        <span>⚡</span><span><strong>Groq AI</strong><br><small style="color:#64748b">가장 빠른 무료 LLM</small></span>
      </a>
      <a class="sidebar-tool" href="ai-tools.html" style="color:#6366f1;font-weight:700;font-size:.85em;display:block;margin-top:10px;text-align:center;text-decoration:none">모든 AI 도구 보기 →</a>
    </div>

    {f'''<div class="sidebar-card" style="background:linear-gradient(135deg,#1e1b4b,#312e81);border-color:#312e81">
      <h3 style="color:#a5b4fc">📧 무료 뉴스레터</h3>
      <p style="color:#94a3b8;font-size:.82em;line-height:1.6;margin-bottom:14px">매일 AI 수익화 팁 · 스팸 없음</p>
      <a href="https://www.beehiiv.com/subscribe/{BEEHIIV_PUB}" target="_blank" rel="noopener"
         style="display:block;background:#6366f1;color:#fff;padding:9px;border-radius:7px;
                text-decoration:none;font-weight:700;text-align:center;font-size:.85em">무료 구독 →</a>
    </div>''' if BEEHIIV_PUB else ""}

    {f'''<div class="sidebar-card" style="text-align:center">
      <h3 style="margin-bottom:12px">☕ 블로그 후원</h3>
      <a href="https://ko-fi.com/{KOFI_USER}" target="_blank" rel="noopener"
         style="display:inline-block;background:#ff5e5b;color:#fff;padding:9px 18px;
                border-radius:20px;text-decoration:none;font-weight:700;font-size:.85em">Ko-fi로 응원하기</a>
    </div>''' if KOFI_USER else ""}

    <div class="ads">{ADSENSE_SNIPPET}</div>
  </aside>
</div>

<div class="ads">{ADSENSE_SNIPPET}</div>

<footer>
  <p>© {datetime.now().year} {SITE_NAME} · Powered by AI · <a href="privacy.html">Privacy Policy</a> · <a href="dashboard.html">Revenue Dashboard</a></p>
  <p style="margin-top:8px">
    <a href="https://www.youtube.com/@psg9806" target="_blank" style="color:#6366f1">YouTube</a> &nbsp;|&nbsp;
    <a href="ai-tools.html" style="color:#6366f1">AI Tools Directory</a>
    {f'&nbsp;|&nbsp;<a href="https://ko-fi.com/{KOFI_USER}" target="_blank" style="color:#ff5e5b">Support Us ☕</a>' if KOFI_USER else ""}
  </p>
</footer>
</body>
</html>"""


def build_privacy() -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Privacy Policy - {SITE_NAME}</title>
<style>body{{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.7}}h1,h2{{color:#0f172a}}</style>
</head>
<body>
<h1>Privacy Policy</h1>
<p>Last updated: {datetime.now().strftime('%B %d, %Y')}</p>
<h2>Information We Collect</h2>
<p>This website uses Google AdSense to display advertisements. Google may use cookies to serve ads based on your prior visits to this website or other sites.</p>
<h2>Cookies</h2>
<p>We use cookies to improve your experience. Third-party vendors, including Google, use cookies to serve ads based on your past visits to this site.</p>
<h2>Opt Out</h2>
<p>You may opt out of personalized advertising by visiting <a href="https://www.google.com/settings/ads">Google Ads Settings</a>.</p>
<h2>Contact</h2>
<p>For privacy concerns, contact us via YouTube channel.</p>
</body>
</html>"""


def inject_adsense(html: str) -> str:
    """기존 HTML 파일에 AdSense 코드 삽입."""
    if not ADSENSE_ID or ADSENSE_SNIPPET in html:
        return html
    # </head> 바로 앞에 삽입
    ad_head = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_ID}" crossorigin="anonymous"></script>'
    html = html.replace('</head>', f'{ad_head}\n</head>', 1)
    # </body> 앞에 광고 블록 삽입
    html = html.replace('</body>', f'<div style="margin:2rem auto;max-width:800px">{ADSENSE_SNIPPET}</div>\n</body>', 1)
    return html


def run():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 블로그 포스트 복사 + AdSense 삽입
    posts = []
    json_files = sorted(BLOG_OUTPUT.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    for jf in json_files:
        html_f = jf.with_suffix(".html")
        if not html_f.exists():
            continue

        meta = json.loads(jf.read_text())
        html_content = html_f.read_text()

        if ADSENSE_ID:
            html_content = inject_adsense(html_content)

        dest = DOCS_DIR / html_f.name
        dest.write_text(html_content)

        posts.append({
            "file":       html_f.name,
            "title":      meta.get("title", "Untitled"),
            "desc":       meta.get("meta_description", "")[:160],
            "tags":       meta.get("tags", []),
            "word_count": meta.get("word_count", 0),
            "date":       jf.stem[:8] if len(jf.stem) >= 8 else "",
        })

    # index.html 생성
    index_html = build_index(posts)
    (DOCS_DIR / "index.html").write_text(index_html)

    # privacy.html 생성
    (DOCS_DIR / "privacy.html").write_text(build_privacy())

    # CNAME (커스텀 도메인 있으면)
    custom_domain = os.environ.get("BLOG_CUSTOM_DOMAIN", "")
    if custom_domain:
        (DOCS_DIR / "CNAME").write_text(custom_domain)

    print(f"✅ GitHub Pages 빌드 완료: {len(posts)}개 포스트 → docs/")
    print(f"   AdSense: {'활성화' if ADSENSE_ID else '비활성화 (ADSENSE_CLIENT_ID 필요)'}")


if __name__ == "__main__":
    run()
