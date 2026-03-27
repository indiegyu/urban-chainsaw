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

SITE_NAME = "AI Income Automation Blog"
SITE_TAGLINE = "Daily AI Tips, Side Hustles & Make Money Online"


def build_index(posts: list) -> str:
    cards = ""
    for p in posts[:30]:  # 최신 30개
        cards += f"""
    <article class="card">
      <h2><a href="{p['file']}">{p['title']}</a></h2>
      <p class="meta">{p['date']} · {p['word_count']} words</p>
      <p>{p['desc']}</p>
      <div class="tags">{''.join(f'<span class="tag">{t}</span>' for t in p['tags'])}</div>
    </article>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{SITE_TAGLINE}">
<title>{SITE_NAME}</title>
<style>
:root {{ --primary:#0f172a; --accent:#6366f1; --text:#334155; --bg:#f8fafc; --card:#fff; }}
* {{ box-sizing:border-box; margin:0; padding:0 }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--text); line-height:1.7 }}
header {{ background:var(--primary); color:#fff; padding:2rem; text-align:center }}
header h1 {{ font-size:2rem; font-weight:800 }}
header p {{ opacity:.7; margin-top:.5rem }}
.container {{ max-width:900px; margin:2rem auto; padding:0 1rem }}
.card {{ background:var(--card); border-radius:12px; padding:1.5rem; margin-bottom:1.5rem; box-shadow:0 1px 3px rgba(0,0,0,.08) }}
.card h2 {{ font-size:1.25rem; margin-bottom:.5rem }}
.card h2 a {{ color:var(--primary); text-decoration:none }}
.card h2 a:hover {{ color:var(--accent) }}
.meta {{ font-size:.8rem; color:#94a3b8; margin-bottom:.75rem }}
.tag {{ background:#e0e7ff; color:var(--accent); border-radius:4px; padding:.2rem .5rem; font-size:.75rem; margin-right:.3rem }}
footer {{ text-align:center; padding:2rem; color:#94a3b8; font-size:.85rem }}
.ads {{ margin:1.5rem 0 }}
</style>
</head>
<body>
<header>
  <h1>🤖 {SITE_NAME}</h1>
  <p>{SITE_TAGLINE}</p>
</header>
<div class="container">
  <div class="ads">{ADSENSE_SNIPPET}</div>
  {cards}
  <div class="ads">{ADSENSE_SNIPPET}</div>
</div>
<footer>
  <p>© {datetime.now().year} {SITE_NAME} · Powered by AI · <a href="privacy.html">Privacy Policy</a></p>
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
