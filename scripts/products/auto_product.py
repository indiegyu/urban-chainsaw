"""
AI 디지털 상품 자동 생성
==========================
content_strategy.json의 product_ideas를 읽어서
LLM(Gemini 무료 티어 우선)으로 PDF 전자책 / 프롬프트팩 콘텐츠를 자동 생성합니다.

생성 상품:
  - PDF 가이드 (HTML → PDF 변환)
  - ChatGPT 프롬프트팩 (텍스트 파일)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import complete as llm_complete, extract_json  # noqa: E402
from utils.site import channel_line  # noqa: E402

STRATEGY_PATH = Path(__file__).parent.parent / "strategy" / "content_strategy.json"
OUTPUT_DIR    = Path(__file__).parent / "output"


def _llm(messages: list, max_tokens: int = 3000, json_mode: bool = False) -> str:
    return llm_complete(
        messages, max_tokens=max_tokens, temperature=0.7, json_mode=json_mode
    )


def generate_pdf_guide(topic: str) -> dict:
    """PDF 전자책 콘텐츠를 HTML로 생성합니다."""
    print(f"  📄 PDF 가이드 생성: '{topic[:50]}'")

    # 1. 목차 + 메타
    import re
    meta_raw = _llm([
        {"role": "system", "content": (
            "Output ONLY valid JSON with: "
            "title (catchy product title, max 60 chars), "
            "subtitle (one-line value prop), "
            "price_usd (integer, 9 or 17 or 27), "
            "chapters (list of 6-8 chapter title strings), "
            "target_buyer (one sentence who this is for)"
        )},
        {"role": "user", "content": f"Digital PDF guide about: {topic}"},
    ], max_tokens=400, json_mode=True)
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', meta_raw)
    try:
        meta = json.loads(raw)
    except json.JSONDecodeError:
        meta = extract_json(raw)

    # 2. 본문 (챕터별)
    chapters_html = []
    for ch in meta.get("chapters", [])[:6]:
        content = _llm([
            {"role": "system", "content": (
                "Write a 300-word chapter for a practical digital guide. "
                "Use HTML: <h2> for title, <p> for paragraphs, <ul><li> for bullet points. "
                "Be specific, actionable, include real examples and numbers."
            )},
            {"role": "user", "content": f"Chapter: {ch}\nGuide topic: {topic}"},
        ], max_tokens=600)
        chapters_html.append(content)

    # 3. HTML 조립
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Georgia, serif; max-width: 680px; margin: 40px auto; padding: 0 30px; color: #1a1a2e; line-height: 1.8; }}
  h1   {{ font-size: 2.2em; color: #1a1a2e; margin-bottom: 0.3em; }}
  h2   {{ font-size: 1.4em; color: #e94560; margin-top: 2.5em; border-left: 4px solid #e94560; padding-left: 12px; }}
  p    {{ margin: 0.8em 0; }}
  ul   {{ padding-left: 1.4em; }}
  li   {{ margin: 0.4em 0; }}
  .cover   {{ text-align: center; padding: 60px 0; border-bottom: 2px solid #e94560; margin-bottom: 40px; }}
  .subtitle {{ font-size: 1.2em; color: #666; margin-top: 0.5em; }}
  .badge    {{ display: inline-block; background: #e94560; color: white; padding: 6px 18px; border-radius: 20px; font-size: 0.85em; margin-top: 1em; }}
  .footer   {{ text-align: center; margin-top: 60px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 0.85em; }}
</style>
</head>
<body>
<div class="cover">
  <h1>{meta['title']}</h1>
  <p class="subtitle">{meta.get('subtitle', '')}</p>
  <span class="badge">AI Income Daily</span>
  <p style="color:#999; font-size:0.85em; margin-top:1.5em;">© {datetime.now().year} AI Income Daily · All rights reserved</p>
</div>

<h2>Who This Guide Is For</h2>
<p>{meta.get('target_buyer', 'Anyone who wants to make money online using AI tools.')}</p>

{''.join(chapters_html)}

<div class="footer">
  <p>Get more free AI income tips from <strong>AI Income Daily</strong></p>
  <p>{channel_line("Subscribe for a new strategy every day →")}</p>
</div>
</body>
</html>"""

    return {
        "title": meta["title"],
        "subtitle": meta.get("subtitle", ""),
        "price_usd": meta.get("price_usd", 17),
        "html": full_html,
        "type": "pdf_guide",
        "topic": topic,
    }


def generate_prompt_pack(topic: str) -> dict:
    """ChatGPT 프롬프트팩을 생성합니다."""
    print(f"  📦 프롬프트팩 생성: '{topic[:50]}'")

    import re
    meta_raw = _llm([
        {"role": "system", "content": (
            "Output ONLY valid JSON with: "
            "title (prompt pack product title, max 60 chars), "
            "description (2-sentence sales description), "
            "price_usd (integer: 7 or 9 or 15)"
        )},
        {"role": "user", "content": f"ChatGPT prompt pack for: {topic}"},
    ], max_tokens=200, json_mode=True)
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', meta_raw)
    try:
        meta = json.loads(raw)
    except json.JSONDecodeError:
        meta = extract_json(raw)

    # 50개 프롬프트 생성
    prompts_raw = _llm([
        {"role": "system", "content": (
            "Write 50 specific, ready-to-use ChatGPT prompts. "
            "Format each as: [NUMBER]. [PROMPT TITLE]\nPrompt: [the actual prompt text]\n\n"
            "Make prompts actionable and focused on making money / saving time. "
            "Each prompt should be 1-3 sentences."
        )},
        {"role": "user", "content": f"Topic: {topic}\nCreate 50 premium ChatGPT prompts."},
    ], max_tokens=3000)

    content = f"""{meta['title']}
{'=' * 60}
{meta.get('description', '')}

© {datetime.now().year} AI Income Daily
{channel_line("Get more free tips:")}
{'=' * 60}

{prompts_raw}

{'=' * 60}
BONUS: Join AI Income Daily for daily strategies
{channel_line("Subscribe:")}
{'=' * 60}
"""

    return {
        "title": meta["title"],
        "description": meta.get("description", ""),
        "price_usd": meta.get("price_usd", 9),
        "content": content,
        "type": "prompt_pack",
        "topic": topic,
    }


def save_product(product: dict) -> Path:
    """상품 파일을 저장합니다."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = product["title"].lower().replace(" ", "_")[:40]

    if product["type"] == "pdf_guide":
        path = OUTPUT_DIR / f"{ts}_{slug}.html"
        path.write_text(product["html"], encoding="utf-8")
    else:
        path = OUTPUT_DIR / f"{ts}_{slug}.txt"
        path.write_text(product["content"], encoding="utf-8")

    meta_path = OUTPUT_DIR / f"{ts}_{slug}_meta.json"
    meta_path.write_text(json.dumps(
        {k: v for k, v in product.items() if k not in ("html", "content")},
        indent=2, ensure_ascii=False
    ))

    print(f"  ✓ 저장: {path.name}")
    return path


def run():
    from dotenv import load_dotenv
    load_dotenv()

    # 전략 파일에서 이번 주 상품 아이디어 선택
    strategy = json.loads(STRATEGY_PATH.read_text())
    already_created = [p.get("title", "") for p in strategy.get("gumroad_products_created", [])]
    ideas = [i for i in strategy.get("product_ideas", []) if i not in already_created]

    if not ideas:
        print("  ⚠ 새 상품 아이디어 없음 — 기본 아이디어 사용")
        ideas = ["50 ChatGPT prompts for making money online with AI tools"]

    topic = ideas[0]
    print(f"\n🛍️  이번 주 상품: '{topic}'")

    # 짝수 주 = PDF 가이드 / 홀수 주 = 프롬프트팩 (자동 교대)
    from datetime import date
    week_num = date.today().isocalendar()[1]
    if week_num % 2 == 0:
        product = generate_pdf_guide(topic)
    else:
        product = generate_prompt_pack(topic)

    path = save_product(product)

    print(f"\n✅ 상품 생성 완료")
    print(f"   제목:  {product['title']}")
    print(f"   가격:  ${product['price_usd']}")
    print(f"   파일:  {path.name}")

    return {"product": product, "path": str(path)}


if __name__ == "__main__":
    run()
