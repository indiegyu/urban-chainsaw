"""
Notion 템플릿 자동 생성기
==========================
Groq AI로 Notion 템플릿을 자동 생성하고
Etsy/Lemon Squeezy에 디지털 상품으로 등록합니다.

수익: Notion 템플릿은 Etsy에서 $5-25에 판매, 월 수백 달러 가능
"""
import os, json, requests
from pathlib import Path
from datetime import datetime

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
OUTPUT_DIR = Path(__file__).parent / "notion_templates"

TEMPLATE_IDEAS = [
    "AI Side Hustle Tracker — 월 수익 추적 + 태스크 관리",
    "YouTube Channel Planner — 콘텐츠 캘린더 + 성과 분석",
    "Passive Income Dashboard — 수익원별 추적 + 목표 설정",
    "AI Tools Directory — 카테고리별 AI 툴 정리 + 사용법",
    "Freelance Client CRM — 고객 관리 + 인보이스 추적",
]

def generate_template(topic: str, groq_key: str) -> dict:
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
        resp = requests.post(GROQ_URL,
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 1000},
            timeout=30)
        content = resp.json()["choices"][0]["message"]["content"]
        import re
        m = re.search(r"\{[\s\S]+\}", content)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        print(f"  ⚠ Groq error: {e}")
    return {}

def run():
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        print("⚠ GROQ_API_KEY 미설정")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    import random
    topic = random.choice(TEMPLATE_IDEAS)
    print(f"📋 Notion 템플릿 생성: {topic}")

    template = generate_template(topic, groq_key)
    if template:
        filename = OUTPUT_DIR / f"template_{datetime.now().strftime('%Y%m%d')}.json"
        filename.write_text(json.dumps(template, indent=2, ensure_ascii=False))
        print(f"  ✓ 저장: {filename.name}")
        print(f"  ✓ 가격: ${template.get('price_usd', 9)}")

if __name__ == "__main__":
    run()
