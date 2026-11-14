"""
Notion 템플릿 자동 생성기
==========================
LLM(Gemini 무료 티어 우선)으로 Notion 템플릿을 자동 생성하고
Etsy/Lemon Squeezy에 디지털 상품으로 등록합니다.

수익: Notion 템플릿은 Etsy에서 $5-25에 판매, 월 수백 달러 가능
"""
import sys, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import complete as llm_complete, extract_json  # noqa: E402
from utils.health import fail  # noqa: E402

OUTPUT_DIR = Path(__file__).parent / "notion_templates"

TEMPLATE_IDEAS = [
    "AI Side Hustle Tracker — 월 수익 추적 + 태스크 관리",
    "YouTube Channel Planner — 콘텐츠 캘린더 + 성과 분석",
    "Passive Income Dashboard — 수익원별 추적 + 목표 설정",
    "AI Tools Directory — 카테고리별 AI 툴 정리 + 사용법",
    "Freelance Client CRM — 고객 관리 + 인보이스 추적",
]

def generate_template(topic: str) -> dict:
    prompt = f"""Create a detailed Notion template specification for: "{topic}"

Return JSON with:
{{
  "name": "template name",
  "description": "2-3 sentence description for Etsy listing",
  "pages": ["page1_name", "page2_name", ...],
  "databases": [
    {{"name": "db_name", "properties": ["prop1", "prop2", ...]}}
  ],
  "price_usd": 9,
  "tags": ["tag1", "tag2", ...]
}}"""

    try:
        content = llm_complete(
            [{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
            json_mode=True,
        )
        return extract_json(content)
    except Exception as e:
        print(f"  ⚠ LLM error: {e}")
    return {}

def run():
    OUTPUT_DIR.mkdir(exist_ok=True)
    import random
    topic = random.choice(TEMPLATE_IDEAS)
    print(f"📋 Notion 템플릿 생성: {topic}")

    template = generate_template(topic)
    if template:
        filename = OUTPUT_DIR / f"template_{datetime.now().strftime('%Y%m%d')}.json"
        filename.write_text(json.dumps(template, indent=2, ensure_ascii=False))
        print(f"  ✓ 저장: {filename.name}")
        print(f"  ✓ 가격: ${template.get('price_usd', 9)}")
    else:
        # 거짓 성공 방지: 템플릿을 못 만들면 워크플로를 실패시킵니다.
        fail("notion", f"Notion 템플릿 생성 실패: '{topic[:40]}'")

if __name__ == "__main__":
    run()
