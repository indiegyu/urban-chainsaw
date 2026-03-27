"""
자율 수익 파이프라인 확장 엔진
================================
매주 실행되어 새로운 수익 스트림을 자동으로 활성화합니다.
사용자가 아무것도 하지 않아도 파이프라인이 계속 늘어납니다.

동작 방식:
  1. 현재 활성화된 수익 스트림 목록 확인
  2. 미활성 스트림 중 우선순위 높은 것 선택
  3. 해당 스트림의 워크플로 파일 + 스크립트 자동 생성
  4. Groq으로 현재 전략 기반 콘텐츠 최적화 실행
  5. content_strategy.json 업데이트 (수익 모델 추가)
"""

import os, json, sys, subprocess
from pathlib import Path
from datetime import datetime
import requests

GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL  = "llama-3.3-70b-versatile"
STRATEGY    = Path(__file__).parent.parent / "strategy" / "content_strategy.json"
WORKFLOWS   = Path(__file__).parent.parent.parent / ".github" / "workflows"
SCRIPTS_DIR = Path(__file__).parent.parent

# ── 수익 스트림 카탈로그 (우선순위 순) ──────────────────────────────────────────
# 각 항목: { id, name, needs_secret, secret_keys, script_path, workflow_file, revenue_type }
STREAM_CATALOG = [
    {
        "id": "hashnode",
        "name": "Hashnode 크로스포스팅",
        "needs_secret": True,
        "secret_keys": ["HASHNODE_ACCESS_TOKEN", "HASHNODE_PUBLICATION_ID"],
        "script_path": "scripts/publish/hashnode_publisher.py",
        "workflow_exists": True,  # daily_publish.yml에 이미 추가됨
        "revenue_type": "traffic → ad + affiliate",
        "est_monthly": "$50-200",
    },
    {
        "id": "kofi",
        "name": "Ko-fi 후원 버튼",
        "needs_secret": True,
        "secret_keys": ["KOFI_USERNAME"],
        "script_path": "scripts/monetize/kofi_injector.py",
        "workflow_exists": False,
        "revenue_type": "donations",
        "est_monthly": "$20-100",
    },
    {
        "id": "sellfy",
        "name": "Sellfy 디지털 상품",
        "needs_secret": True,
        "secret_keys": ["SELLFY_API_KEY"],
        "script_path": "scripts/products/sellfy_publisher.py",
        "workflow_exists": False,
        "revenue_type": "digital products",
        "est_monthly": "$100-500",
    },
    {
        "id": "substack",
        "name": "Substack 뉴스레터",
        "needs_secret": True,
        "secret_keys": ["SUBSTACK_API_KEY"],
        "script_path": "scripts/social/substack_poster.py",
        "workflow_exists": False,
        "revenue_type": "newsletter subscriptions",
        "est_monthly": "$50-300",
    },
    {
        "id": "affiliate_amazon",
        "name": "Amazon 어필리에이트 자동삽입",
        "needs_secret": True,
        "secret_keys": ["AMAZON_ASSOCIATE_TAG"],
        "script_path": "scripts/affiliate/link_inserter.py",
        "workflow_exists": True,  # blog pipeline에 포함됨
        "revenue_type": "affiliate commissions",
        "est_monthly": "$30-150",
    },
    {
        "id": "notion_templates",
        "name": "Notion 템플릿 자동 생성",
        "needs_secret": False,
        "secret_keys": [],
        "script_path": "scripts/products/notion_template_generator.py",
        "workflow_exists": False,
        "revenue_type": "digital products",
        "est_monthly": "$50-200",
    },
    {
        "id": "promptbase",
        "name": "PromptBase 프롬프트 판매",
        "needs_secret": True,
        "secret_keys": ["PROMPTBASE_EMAIL", "PROMPTBASE_PASSWORD"],
        "script_path": "scripts/products/promptbase_publisher.py",
        "workflow_exists": False,
        "revenue_type": "digital products",
        "est_monthly": "$30-100",
    },
    {
        "id": "tiktok",
        "name": "TikTok 자동 포스팅",
        "needs_secret": True,
        "secret_keys": ["TIKTOK_ACCESS_TOKEN", "TIKTOK_OPEN_ID"],
        "script_path": "scripts/social/tiktok_poster.py",
        "workflow_exists": False,
        "revenue_type": "creator fund + traffic",
        "est_monthly": "$50-500",
    },
    {
        "id": "instagram_reels",
        "name": "Instagram Reels 자동 업로드",
        "needs_secret": True,
        "secret_keys": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ID"],
        "script_path": "scripts/social/instagram_poster.py",
        "workflow_exists": False,
        "revenue_type": "traffic + affiliate",
        "est_monthly": "$50-200",
    },
    {
        "id": "github_sponsors",
        "name": "GitHub Sponsors 프로필 최적화",
        "needs_secret": False,
        "secret_keys": [],
        "script_path": "scripts/monetize/github_sponsors_setup.py",
        "workflow_exists": False,
        "revenue_type": "sponsorships",
        "est_monthly": "$50-500",
    },
]


def groq_call(prompt: str, groq_key: str) -> str:
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 2000, "temperature": 0.7},
            timeout=30,
        )
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[Groq error: {e}]"


def load_strategy() -> dict:
    if STRATEGY.exists():
        return json.loads(STRATEGY.read_text())
    return {}


def save_strategy(data: dict):
    STRATEGY.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_activated_streams(strategy: dict) -> list:
    return strategy.get("activated_streams", [])


def activate_stream(stream: dict, strategy: dict) -> bool:
    """새 수익 스트림 활성화 기록"""
    activated = strategy.setdefault("activated_streams", [])
    if stream["id"] in activated:
        return False
    activated.append(stream["id"])
    strategy.setdefault("income_streams", {})[stream["id"]] = {
        "name": stream["name"],
        "activated_at": datetime.utcnow().isoformat(),
        "revenue_type": stream["revenue_type"],
        "est_monthly": stream["est_monthly"],
        "status": "waiting_for_secrets" if stream["needs_secret"] else "active",
        "required_secrets": stream["secret_keys"],
    }
    return True


def generate_kofi_injector():
    """Ko-fi 후원 버튼 삽입 스크립트 생성"""
    script_path = SCRIPTS_DIR / "monetize" / "kofi_injector.py"
    script_path.parent.mkdir(exist_ok=True)
    script_path.write_text('''"""
Ko-fi 후원 버튼 자동 삽입
===========================
생성된 모든 HTML 파일에 Ko-fi 후원 버튼을 자동으로 삽입합니다.
"""
import os, re
from pathlib import Path

KOFI_USERNAME = os.environ.get("KOFI_USERNAME", "")
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
BLOG_OUTPUT = Path(__file__).parent.parent / "blog" / "output"

KOFI_WIDGET = """
<div style="text-align:center;margin:20px 0;padding:15px;background:#f8f9fa;border-radius:8px;">
  <a href="https://ko-fi.com/{username}" target="_blank"
     style="background:#FF5E5B;color:#fff;padding:10px 20px;border-radius:5px;text-decoration:none;font-weight:bold;">
    ☕ Buy Me a Coffee on Ko-fi
  </a>
  <p style="margin:8px 0 0;color:#666;font-size:14px;">
    이 콘텐츠가 도움이 됐다면 커피 한 잔 사주세요! 더 좋은 콘텐츠를 만드는 데 씁니다.
  </p>
</div>
"""

def inject_kofi(html: str, username: str) -> str:
    widget = KOFI_WIDGET.format(username=username)
    # </body> 직전에 삽입
    if "</body>" in html:
        return html.replace("</body>", widget + "</body>", 1)
    return html + widget

def run():
    username = KOFI_USERNAME
    if not username:
        print("⏭ KOFI_USERNAME 미설정 — 건너뜀")
        return

    count = 0
    for html_dir in [DOCS_DIR, BLOG_OUTPUT]:
        if not html_dir.exists():
            continue
        for html_file in html_dir.rglob("*.html"):
            try:
                content = html_file.read_text(encoding="utf-8")
                if f"ko-fi.com/{username}" not in content:
                    html_file.write_text(inject_kofi(content, username), encoding="utf-8")
                    count += 1
            except Exception as e:
                print(f"  ⚠ {html_file.name}: {e}")
    print(f"✅ Ko-fi 버튼 삽입: {count}개 파일")

if __name__ == "__main__":
    run()
''')
    print(f"  ✓ Ko-fi 인젝터 생성: {script_path}")


def generate_notion_template_generator():
    """Notion 템플릿 자동 생성 스크립트"""
    script_path = SCRIPTS_DIR / "products" / "notion_template_generator.py"
    if script_path.exists():
        return
    script_path.write_text('''"""
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
        m = re.search(r"\\{[\\s\\S]+\\}", content)
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
''')
    print(f"  ✓ Notion 템플릿 생성기 생성: {script_path}")


def generate_tiktok_poster():
    """TikTok 자동 포스팅 스크립트 생성"""
    script_path = SCRIPTS_DIR / "social" / "tiktok_poster.py"
    if script_path.exists():
        return
    script_path.write_text('''"""
TikTok 자동 포스팅
==================
YouTube Shorts 영상을 TikTok에 자동 업로드합니다.
TikTok Creator Fund: 1000 뷰당 $0.02-0.04 + 팔로워 → 상품 판매 유도

필요한 환경변수:
  TIKTOK_ACCESS_TOKEN — TikTok for Developers에서 발급
  TIKTOK_OPEN_ID      — TikTok Open ID
"""
import os, json, glob
from pathlib import Path

TIKTOK_API = "https://open.tiktokapis.com/v2"
SHORTS_OUTPUT = Path(__file__).parent.parent / "video" / "output_shorts"

def run():
    token = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
    open_id = os.environ.get("TIKTOK_OPEN_ID", "")

    if not token or not open_id:
        print("⏭ TikTok 시크릿 미설정 — 건너뜀")
        return

    # Shorts 영상 파일 찾기
    video_files = sorted(SHORTS_OUTPUT.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not video_files:
        print("⚠ 업로드할 Shorts 영상 없음")
        return

    print(f"✅ TikTok 포스팅 준비: {video_files[0].name}")
    # 실제 업로드 구현은 TikTok Content Posting API 사용
    # https://developers.tiktok.com/doc/content-posting-api-get-started/

if __name__ == "__main__":
    run()
''')
    print(f"  ✓ TikTok 포스터 생성: {script_path}")


def update_strategy_with_expansion(strategy: dict, groq_key: str):
    """Groq으로 현재 전략 분석 후 수익 모델 개선 제안"""
    topics = strategy.get("top_performing_topics", [])
    weekly_stats = strategy.get("weekly_stats", {})
    activated = strategy.get("activated_streams", [])

    prompt = f"""You are a revenue optimization AI for an automated income system.

Current status:
- Top topics: {topics}
- Weekly stats: {weekly_stats}
- Active income streams: {activated}
- Total streams: YouTube, Blog, Lemon Squeezy digital products, Dev.to, Medium, Pinterest, Patreon, POD/Printify, KDP ebooks, Hashnode, Ko-fi

Based on the top performing topics and current performance, suggest:
1. 3 new content angles that will maximize YouTube CPM (focus on high-CPM topics: finance, AI tools, make money)
2. 2 new digital product ideas for Lemon Squeezy (specific titles + prices)
3. 1 new income stream we haven't tried yet

Keep suggestions specific, actionable, and focused on maximum revenue.
Return as JSON: {{"content_angles": [], "product_ideas": [], "new_stream": ""}}"""

    response = groq_call(prompt, groq_key)
    try:
        import re
        m = re.search(r"\{[\s\S]+\}", response)
        if m:
            suggestions = json.loads(m.group(0))
            # 콘텐츠 각도 추가
            existing_formats = strategy.get("top_performing_formats", [])
            for angle in suggestions.get("content_angles", []):
                if angle not in existing_formats:
                    existing_formats.insert(0, angle)
            strategy["top_performing_formats"] = existing_formats[:10]
            # 상품 아이디어 추가
            existing_products = strategy.get("product_ideas", [])
            for idea in suggestions.get("product_ideas", []):
                if idea not in existing_products:
                    existing_products.append(idea)
            strategy["product_ideas"] = existing_products[:10]
            # 새 수익 모델 기록
            new_stream = suggestions.get("new_stream", "")
            if new_stream:
                strategy.setdefault("groq_suggested_streams", []).append({
                    "suggestion": new_stream,
                    "date": datetime.utcnow().isoformat()
                })
            print(f"  ✓ Groq 전략 업데이트 완료")
    except Exception as e:
        print(f"  ⚠ 전략 파싱 실패: {e}")


def print_income_map(strategy: dict):
    """현재 수익 파이프라인 전체 맵 출력"""
    print("\n" + "="*60)
    print("💰 현재 수익 파이프라인 현황")
    print("="*60)

    streams = strategy.get("income_streams", {})
    activated = strategy.get("activated_streams", [])

    print(f"\n✅ 활성 스트림 ({len(activated)}개):")
    core = ["YouTube 영상 x2/일", "YouTube Shorts x1/일", "블로그 x2/일",
            "Lemon Squeezy 상품 x2/주", "KDP 이북 x1/주"]
    for s in core:
        print(f"  • {s}")
    for sid, info in streams.items():
        status = "🟢" if info.get("status") == "active" else "🟡"
        print(f"  {status} {info['name']} ({info.get('est_monthly', '?')})")

    print(f"\n⏳ 시크릿 등록 대기:")
    waiting = [s for s in STREAM_CATALOG if s["id"] not in activated]
    for s in waiting[:5]:
        secrets = ", ".join(s["secret_keys"]) if s["secret_keys"] else "없음"
        print(f"  • {s['name']} (필요: {secrets})")

    print("="*60)


def run():
    groq_key = os.environ.get("GROQ_API_KEY", "")
    strategy = load_strategy()

    print("🚀 수익 파이프라인 확장 엔진 시작...")

    # 1. Groq으로 전략 최적화
    if groq_key:
        print("\n📊 Groq 전략 분석 중...")
        update_strategy_with_expansion(strategy, groq_key)

    # 2. 미활성 스트림 중 다음 우선순위 활성화
    activated = get_activated_streams(strategy)
    newly_activated = []

    for stream in STREAM_CATALOG:
        if stream["id"] not in activated:
            # 시크릿 불필요하거나 스크립트가 이미 있으면 즉시 활성화
            if not stream["needs_secret"]:
                print(f"\n🆕 새 스트림 활성화: {stream['name']}")
                activate_stream(stream, strategy)
                newly_activated.append(stream)

                # 스크립트 자동 생성
                if stream["id"] == "notion_templates":
                    generate_notion_template_generator()
            else:
                # 시크릿 필요 → 활성화 기록 후 대기 상태로
                activate_stream(stream, strategy)
                newly_activated.append(stream)

                # 스크립트 자동 생성 (없는 경우)
                if stream["id"] == "kofi":
                    generate_kofi_injector()
                elif stream["id"] == "tiktok":
                    generate_tiktok_poster()

            if len(newly_activated) >= 3:
                break  # 한 번에 3개까지만

    # 3. 전략 파일 업데이트
    strategy["last_expansion"] = datetime.utcnow().isoformat()
    strategy["total_pipelines"] = len(activated) + len(newly_activated)
    save_strategy(strategy)

    # 4. 현황 출력
    print_income_map(strategy)

    if newly_activated:
        print(f"\n✅ 이번 주 {len(newly_activated)}개 스트림 추가됨:")
        for s in newly_activated:
            if s["needs_secret"]:
                print(f"  🟡 {s['name']} — 시크릿 등록 필요: {', '.join(s['secret_keys'])}")
            else:
                print(f"  🟢 {s['name']} — 즉시 활성화!")


if __name__ == "__main__":
    run()
