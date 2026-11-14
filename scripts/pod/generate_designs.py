"""
Phase 1 – Print-on-Demand Design Generator
===========================================
LLM(Gemini 무료 티어 우선)으로 문구를 생성하고 PIL로 직접 디자인합니다.
(외부 이미지 API 불필요 – 완전 무료)

Etsy 베스트셀러 1위 카테고리가 텍스트 기반 디자인입니다.
"funny quote tees", "motivational shirts" 등이 꾸준히 판매됩니다.

필수 환경변수:
  GEMINI_API_KEY=...  (무료 티어)

종료 코드:
  0 — 요청한 수량만큼 생성 (부분 성공은 경고 기록)
  1 — 하나도 생성하지 못함 (거짓 성공 방지)
"""

import sys
import json
import time
import random
import textwrap
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import complete as llm_complete, extract_json  # noqa: E402
from utils.health import fail, record, warn  # noqa: E402

# ── 설정 ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR   = Path(__file__).parent / "output"
CANVAS_SIZE  = (4500, 5400)   # Printify 티셔츠 권장 해상도 (300dpi)

# Etsy 수익성 높은 틈새 카테고리
NICHE_CATEGORIES = [
    "funny cat lover gift tshirt",
    "dog mom humor shirt",
    "nurse life funny quote",
    "teacher appreciation funny",
    "coffee addict morning humor",
    "fitness gym motivation",
    "book lover reading nerd",
    "introvert funny antisocial",
    "mental health awareness positive",
    "plant mom succulent humor",
    "work from home funny remote",
    "retirement funny gift idea",
]

# 색상 팔레트 (배경색, 텍스트색)
COLOR_PALETTES = [
    {"bg": "#FFFFFF", "text": "#1a1a2e", "accent": "#e94560"},
    {"bg": "#1a1a2e", "text": "#FFFFFF", "accent": "#e94560"},
    {"bg": "#f8f9fa", "text": "#212529", "accent": "#6c757d"},
    {"bg": "#2d6a4f", "text": "#FFFFFF", "accent": "#d8f3dc"},
    {"bg": "#ffd60a", "text": "#000814", "accent": "#001d3d"},
    {"bg": "#0077b6", "text": "#FFFFFF", "accent": "#caf0f8"},
    {"bg": "#6d2b2b", "text": "#FFFFFF", "accent": "#f5cac3"},
    {"bg": "#f4f1de", "text": "#3d405b", "accent": "#e07a5f"},
]


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ── LLM: 문구 + 메타데이터 생성 ─────────────────────────────────────────────
def generate_design_content(niche: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a print-on-demand copywriter. Create a witty, shareable design. "
                "Output valid JSON only (no markdown) with keys: "
                "'main_text' (bold main statement, max 40 chars), "
                "'sub_text' (optional secondary line, max 50 chars or empty string), "
                "'title' (Etsy listing title, 130 chars, SEO-rich with keywords), "
                "'tags' (list of 13 Etsy tags, each max 20 chars), "
                "'description' (3-sentence product description mentioning gift use cases)."
            ),
        },
        {
            "role": "user",
            "content": f"Create a best-selling POD design for: '{niche}'",
        },
    ]
    content = llm_complete(
        messages, max_tokens=1200, temperature=0.9, json_mode=True
    )
    return extract_json(content)


# ── PIL: 티셔츠 디자인 이미지 생성 ───────────────────────────────────────────
def create_design_image(main_text: str, sub_text: str, palette: dict) -> Image.Image:
    bg_rgb   = hex_to_rgb(palette["bg"])
    txt_rgb  = hex_to_rgb(palette["text"])
    acc_rgb  = hex_to_rgb(palette["accent"])

    img  = Image.new("RGB", CANVAS_SIZE, color=bg_rgb)
    draw = ImageDraw.Draw(img)

    W, H = CANVAS_SIZE

    # 폰트 크기 (시스템 기본 폰트 사용)
    try:
        # Linux 시스템 폰트 시도
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 380)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 200)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 장식 선
    line_y = H // 2 - 500
    draw.rectangle([W * 0.1, line_y, W * 0.9, line_y + 20], fill=acc_rgb)
    draw.rectangle([W * 0.1, H - line_y, W * 0.9, H - line_y + 20], fill=acc_rgb)

    # 메인 텍스트 (줄바꿈 처리)
    wrapped = textwrap.wrap(main_text.upper(), width=15)
    total_h = len(wrapped) * 420
    start_y = (H - total_h) // 2 - (150 if sub_text else 0)

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=font_large)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) // 2
        y = start_y + i * 420
        # 그림자 효과
        draw.text((x + 8, y + 8), line, font=font_large, fill=(*acc_rgb, 80))
        draw.text((x, y), line, font=font_large, fill=txt_rgb)

    # 서브 텍스트
    if sub_text:
        bbox = draw.textbbox((0, 0), sub_text, font=font_small)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) // 2
        y = start_y + total_h + 80
        draw.text((x, y), sub_text, font=font_small, fill=acc_rgb)

    return img


# ── 메인 실행 ────────────────────────────────────────────────────────────────
def run(count: int = 5):
    from dotenv import load_dotenv
    load_dotenv()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    niches   = random.sample(NICHE_CATEGORIES, min(count, len(NICHE_CATEGORIES)))
    results  = []
    failures = []

    for i, niche in enumerate(niches):
        print(f"[{i+1}/{count}] Generating: '{niche}'")
        try:
            meta    = generate_design_content(niche)
            palette = random.choice(COLOR_PALETTES)

            # 마크다운 기호 제거 (**, *, _, ` 등)
            import re
            clean = lambda s: re.sub(r"[\*\_\`\#]+", "", s).strip()
            img = create_design_image(
                main_text=clean(meta.get("main_text", niche.upper())),
                sub_text=clean(meta.get("sub_text", "")),
                palette=palette,
            )

            ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug      = niche.replace(" ", "_")[:30]
            img_path  = OUTPUT_DIR / f"{ts}_{slug}.png"
            meta_path = OUTPUT_DIR / f"{ts}_{slug}.json"

            img.save(str(img_path), "PNG", dpi=(300, 300))
            meta["palette"] = palette
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

            results.append({"niche": niche, "image": str(img_path), "meta": meta})
            print(f"  ✓ {img_path.name}  |  \"{meta['main_text']}\"")

            if i < count - 1:
                time.sleep(1)

        except Exception as exc:
            failures.append(f"{niche}: {exc}")
            print(f"  ✗ Failed: {exc}")

    print(f"\nDone. {len(results)}/{count} designs → {OUTPUT_DIR}")

    # 거짓 성공 방지: 하나도 못 만들었으면 워크플로를 실패시킵니다.
    if not results:
        fail(
            "pod",
            f"디자인을 하나도 생성하지 못했습니다 (0/{count}) — "
            + (failures[0] if failures else "원인 미상"),
            context={"requested": count, "failures": failures[:5]},
        )
    if len(results) < count:
        warn(
            "pod",
            f"{len(results)}/{count} 디자인만 생성됨",
            context={"failures": failures[:5]},
        )
    else:
        record("pod", "ok", f"{len(results)}개 디자인 생성")
    return results


if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run(count)
