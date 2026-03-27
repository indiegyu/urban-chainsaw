"""
AI Tools 디렉토리 자동 생성
=============================
GitHub Pages에 SEO 최적화된 AI 툴 디렉토리 페이지를 자동 생성.
"best AI tools 2026" 같은 키워드로 Google 상위 노출 목표.

각 툴에 어필리에이트 링크 삽입 → 클릭당 수수료 자동 수익.
매주 새로운 툴 추가 → 점점 커지는 SEO 자산.

수익 구조:
  검색 유입 → 툴 추천 클릭 → 어필리에이트 수수료
            → YouTube 채널 유입 → 구독자 증가
            → Lemon Squeezy 상품 판매
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

GROQ_API   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
DOCS_DIR   = Path("docs")
STATE_FILE = Path("scripts/publish/.tools_state.json")


def _build_seed_tools() -> list:
    """환경변수 기반으로 어필리에이트 URL이 포함된 시드 툴 목록을 생성합니다."""
    pfy  = os.environ.get("PRINTIFY_AFF_ID", "").strip()
    fiv  = os.environ.get("FIVERR_AFF_ID", "").strip()
    hos  = os.environ.get("HOSTINGER_AFF_ID", "").strip()
    eleven = os.environ.get("ELEVENLABS_AFF_ID", "").strip()
    jsp  = os.environ.get("JASPER_AFF_ID", "").strip()
    ck   = os.environ.get("CONVERTKIT_AFF_ID", "").strip()
    sem  = os.environ.get("SEMRUSH_AFF_ID", "").strip()
    amz  = os.environ.get("AMAZON_TAG", "").strip()

    return [
        {"name": "Groq", "url": "https://groq.com",
         "category": "AI LLM", "free": True, "affiliate": False},
        {"name": "Canva", "url": "https://partner.canva.com/c/canva",
         "category": "Design", "free": True, "affiliate": True},
        {"name": "ElevenLabs",
         "url": f"https://elevenlabs.io/?from={eleven}" if eleven else "https://elevenlabs.io",
         "category": "AI Voice", "free": True, "affiliate": bool(eleven)},
        {"name": "Printify",
         "url": f"https://printify.com/app/register?referrer={pfy}" if pfy else "https://printify.com",
         "category": "Print on Demand", "free": True, "affiliate": bool(pfy)},
        {"name": "Fiverr",
         "url": f"https://go.fiverr.com/visit/?bta={fiv}&brand=fiverrcpa" if fiv else "https://fiverr.com",
         "category": "Freelance", "free": True, "affiliate": bool(fiv)},
        {"name": "Hostinger",
         "url": f"https://hostinger.com?REFERRALCODE={hos}" if hos else "https://hostinger.com",
         "category": "Web Hosting", "free": False, "affiliate": bool(hos)},
        {"name": "Jasper AI",
         "url": f"https://jasper.ai?fpr={jsp}" if jsp else "https://jasper.ai",
         "category": "AI Writing", "free": False, "affiliate": bool(jsp)},
        {"name": "ConvertKit",
         "url": f"https://partners.convertkit.com/?lmref={ck}" if ck else "https://convertkit.com",
         "category": "Email Marketing", "free": True, "affiliate": bool(ck)},
        {"name": "Semrush",
         "url": f"https://semrush.sjv.io/{sem}" if sem else "https://semrush.com",
         "category": "SEO Tools", "free": False, "affiliate": bool(sem)},
        {"name": "HuggingFace", "url": "https://huggingface.co",
         "category": "AI Models", "free": True, "affiliate": False},
        {"name": "GitHub Actions", "url": "https://github.com/features/actions",
         "category": "Automation", "free": True, "affiliate": False},
        {"name": "Perplexity AI", "url": "https://perplexity.ai",
         "category": "AI Search", "free": True, "affiliate": False},
        {"name": "Ideogram", "url": "https://ideogram.ai",
         "category": "AI Image", "free": True, "affiliate": False},
        {"name": "Suno AI", "url": "https://suno.com",
         "category": "AI Music", "free": True, "affiliate": False},
        {"name": "Beehiiv", "url": "https://beehiiv.com",
         "category": "Newsletter", "free": True, "affiliate": False},
    ]


def _groq(messages, groq_key, max_tokens=1000) -> str:
    r = requests.post(GROQ_API, headers={
        "Authorization": f"Bearer {groq_key}", "Content-Type": "application/json",
    }, json={"model": GROQ_MODEL, "messages": messages,
             "temperature": 0.6, "max_tokens": max_tokens}, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def generate_tool_descriptions(tools: list[dict], groq_key: str) -> list[dict]:
    """Groq으로 각 툴의 SEO 설명 + 수익화 use case를 생성합니다."""
    import re
    names = [t["name"] for t in tools if not t.get("description")]
    if not names:
        return tools

    raw = _groq([
        {"role": "system", "content": (
            "Output ONLY valid JSON array. For each tool in the list, output an object with:\n"
            "- name: tool name (exact)\n"
            "- description: 2-sentence SEO description, mention the primary use case for making money online\n"
            "- money_use_case: one specific way to earn money with this tool (start with $amount)\n"
            "- best_for: 3-word phrase (who benefits most)"
        )},
        {"role": "user", "content": f"Write descriptions for these AI tools: {', '.join(names)}"},
    ], groq_key, max_tokens=1500)
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    if "```" in raw:
        raw = raw.split("```")[1].lstrip("json").strip()

    desc_map = {d["name"]: d for d in json.loads(raw)}
    for tool in tools:
        if tool["name"] in desc_map:
            tool.update(desc_map[tool["name"]])
    return tools


def build_html(tools: list[dict], strategy: dict) -> str:
    """전체 디렉토리 페이지 HTML을 생성합니다."""
    categories = {}
    for t in tools:
        cat = t.get("category", "Other")
        categories.setdefault(cat, []).append(t)

    # 카테고리별 섹션 HTML
    sections = []
    for cat, cat_tools in sorted(categories.items()):
        cards = []
        for t in cat_tools:
            free_badge = '<span class="badge free">FREE</span>' if t.get("free") else ""
            money = t.get("money_use_case", "")
            best  = t.get("best_for", "")
            rel_attr = 'noopener sponsored' if t.get('affiliate') else 'noopener'
            cards.append(f"""
    <div class="tool-card">
      <div class="tool-header">
        <h3><a href="{t['url']}" target="_blank" rel="{rel_attr}">{t['name']}</a></h3>
        {free_badge}
      </div>
      <p class="tool-desc">{t.get('description', '')}</p>
      {f'<p class="money">💰 {money}</p>' if money else ''}
      {f'<p class="best-for">👤 Best for: {best}</p>' if best else ''}
      <a href="{t['url']}" class="btn" target="_blank" rel="{rel_attr}">Try Free →</a>
    </div>""")
        sections.append(f"""
  <section>
    <h2 id="{cat.lower().replace(' ','-')}">{cat}</h2>
    <div class="grid">{''.join(cards)}
    </div>
  </section>""")

    # 채널 상품 링크
    products = strategy.get("gumroad_products_created", [])[-3:]
    product_html = ""
    if products:
        items = "".join(
            f'<li><a href="{p["url"]}" target="_blank">{p["title"]}</a> — ${p.get("price_usd",9)}</li>'
            for p in products if p.get("url")
        )
        product_html = f"""
  <section class="products-cta">
    <h2>🛍️ My AI Income Products</h2>
    <ul>{items}</ul>
    <p>Instant digital download · 30-day guarantee</p>
  </section>"""

    nav_links = "".join(
        f'<a href="#{c.lower().replace(" ","-")}">{c}</a>'
        for c in sorted(categories.keys())
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Best free AI tools to make money online in 2026. Curated list with income use cases, updated weekly by AI Income Daily.">
<title>Best AI Tools to Make Money Online 2026 — AI Income Daily</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;line-height:1.7}}
  header{{background:linear-gradient(135deg,#1e293b,#0f172a);padding:60px 20px;text-align:center;border-bottom:3px solid #6366f1}}
  header h1{{font-size:2.4em;color:#fff;margin-bottom:.5em}}
  header p{{color:#94a3b8;font-size:1.1em}}
  nav{{background:#1e293b;padding:16px 20px;text-align:center;position:sticky;top:0;z-index:10;border-bottom:1px solid #334155}}
  nav a{{color:#818cf8;margin:0 12px;text-decoration:none;font-size:.9em}}
  main{{max-width:1100px;margin:0 auto;padding:40px 20px}}
  section{{margin-bottom:60px}}
  h2{{font-size:1.6em;color:#818cf8;margin-bottom:24px;padding-bottom:8px;border-bottom:1px solid #1e293b}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}}
  .tool-card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px;transition:.2s}}
  .tool-card:hover{{border-color:#6366f1;transform:translateY(-2px)}}
  .tool-header{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}
  .tool-header h3{{font-size:1.1em}}
  .tool-header a{{color:#e2e8f0;text-decoration:none}}
  .badge.free{{background:#10b981;color:#fff;font-size:.7em;padding:2px 8px;border-radius:10px}}
  .tool-desc{{color:#94a3b8;font-size:.9em;margin-bottom:10px}}
  .money{{color:#fbbf24;font-size:.85em;margin-bottom:6px}}
  .best-for{{color:#64748b;font-size:.8em;margin-bottom:14px}}
  .btn{{display:inline-block;background:#6366f1;color:#fff;padding:8px 18px;border-radius:8px;text-decoration:none;font-size:.85em}}
  .btn:hover{{background:#4f46e5}}
  .products-cta{{background:#1e293b;border:2px solid #6366f1;border-radius:16px;padding:32px;text-align:center}}
  .products-cta ul{{list-style:none;margin:16px 0;padding:0}}
  .products-cta li{{margin:8px 0}}
  .products-cta a{{color:#818cf8}}
  footer{{text-align:center;padding:40px 20px;color:#475569;border-top:1px solid #1e293b}}
  footer a{{color:#6366f1}}
</style>
</head>
<body>
<header>
  <h1>🤖 Best AI Tools to Make Money Online</h1>
  <p>Updated {datetime.now().strftime('%B %Y')} · {len(tools)} tools · All free to start</p>
  <p style="margin-top:1em"><a href="https://www.youtube.com/@psg9806" style="color:#6366f1">▶ Watch daily AI income tips on YouTube →</a></p>
</header>
<nav>{nav_links}</nav>
<main>
{''.join(sections)}
{product_html}
</main>
<footer>
  <p>Updated weekly by <a href="https://www.youtube.com/@psg9806">AI Income Daily</a> · Subscribe for daily tips</p>
  <p style="margin-top:.5em;font-size:.8em">Some links may be affiliate links. We only recommend tools we use.</p>
</footer>
</body>
</html>"""


def run():
    from dotenv import load_dotenv
    load_dotenv()
    groq_key = os.environ.get("GROQ_API_KEY", "")

    print("🗂️  AI Tools 디렉토리 빌드 중...")

    # 기존 상태 로드
    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    tools = state.get("tools", _build_seed_tools())

    # Groq으로 설명 생성 (없는 것만)
    if groq_key:
        tools = generate_tool_descriptions(tools, groq_key)
        print(f"  ✓ {len(tools)}개 툴 설명 생성")

    # strategy.json 로드 (상품 링크 포함)
    strategy = {}
    if Path("scripts/strategy/content_strategy.json").exists():
        strategy = json.loads(Path("scripts/strategy/content_strategy.json").read_text())

    # HTML 빌드
    DOCS_DIR.mkdir(exist_ok=True)
    html = build_html(tools, strategy)
    (DOCS_DIR / "ai-tools.html").write_text(html, encoding="utf-8")

    # 상태 저장
    state["tools"] = tools
    state["last_updated"] = datetime.now().isoformat()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    print(f"  ✅ docs/ai-tools.html 생성 완료 ({len(tools)} 툴)")
    print(f"     URL: https://indiegyu.github.io/urban-chainsaw/ai-tools.html")


if __name__ == "__main__":
    run()
