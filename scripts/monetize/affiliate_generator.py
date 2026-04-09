"""
제휴 링크 생성기 파이프라인 — 테스트 모드 지원
================================================
AI 콘텐츠 주제를 기반으로 맞춤형 제휴 링크 컬렉션 페이지를 생성합니다.

테스트 모드 (TEST_MODE=1):
  - 외부 API(Groq) 호출 없음 — 내장 템플릿 사용
  - 모든 제휴 ID에 test-stub 값 사용
  - 출력: scripts/monetize/test_output/affiliate_links_<날짜>.html

라이브 모드:
  - GROQ_API_KEY로 주제별 맞춤 링크 설명 생성
  - 실제 환경변수 AMAZON_TAG, FIVERR_AFF_ID 등 사용
  - 출력: scripts/monetize/output/affiliate_links_<날짜>.html

필요 시크릿 (라이브 모드):
  GROQ_API_KEY       — AI 설명 생성 (console.groq.com)
  AMAZON_TAG         — Amazon Associates 태그 (예: aiblog-20)
  FIVERR_AFF_ID      — Fiverr 어필리에이트 ID
  ELEVENLABS_AFF_ID  — ElevenLabs 파트너 ID
  CONVERTKIT_AFF_ID  — ConvertKit 파트너 ID
  SEMRUSH_AFF_ID     — Semrush 파트너 ID
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# 프로젝트 루트를 sys.path에 추가
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.utils.test_mode import (
    is_test_mode, require_secret, test_output_dir, print_test_banner
)
from scripts.affiliate.link_inserter import _build_affiliate_map

OUTPUT_DIR = Path(__file__).parent / "output"

# 테스트 모드용 제휴 ID 스텁
_TEST_AFF_IDS = {
    "AMAZON_TAG":        "testblog-20",
    "FIVERR_AFF_ID":     "TEST_FIVERR_123",
    "ELEVENLABS_AFF_ID": "TEST_EL_456",
    "CONVERTKIT_AFF_ID": "TEST_CK_789",
    "SEMRUSH_AFF_ID":    "TEST_SEM_012",
    "PRINTIFY_AFF_ID":   "TEST_PFY_345",
    "HOSTINGER_AFF_ID":  "TEST_HOS_678",
    "JASPER_AFF_ID":     "TEST_JSP_901",
}

# 추천 제휴 카테고리 & 주제
_CATEGORIES = [
    {
        "name": "AI Writing Tools",
        "keywords": ["jasper ai", "jasper", "chatgpt"],
        "intro": "Best AI writing assistants to 10x your content output.",
    },
    {
        "name": "Voice & Audio AI",
        "keywords": ["elevenlabs"],
        "intro": "Professional AI voice generation — free to start.",
    },
    {
        "name": "Freelance Platforms",
        "keywords": ["fiverr", "freelance"],
        "intro": "Monetize your AI skills immediately on freelance marketplaces.",
    },
    {
        "name": "Print-on-Demand",
        "keywords": ["printify", "print on demand"],
        "intro": "Launch your POD store with zero upfront inventory costs.",
    },
    {
        "name": "Email Marketing",
        "keywords": ["convertkit", "email marketing", "newsletter"],
        "intro": "Build a recurring revenue newsletter with these tools.",
    },
    {
        "name": "SEO & Traffic",
        "keywords": ["semrush", "seo", "keyword research"],
        "intro": "Drive organic traffic with best-in-class SEO tools.",
    },
    {
        "name": "Web Hosting",
        "keywords": ["hostinger", "web hosting", "wordpress"],
        "intro": "Launch your blog or website for under $3/month.",
    },
    {
        "name": "Design Tools",
        "keywords": ["canva"],
        "intro": "Create professional graphics without design skills.",
    },
]


def _inject_test_env():
    """테스트 모드에서 제휴 ID 스텁을 환경변수로 주입합니다."""
    for key, val in _TEST_AFF_IDS.items():
        if not os.environ.get(key):
            os.environ[key] = val


def _build_html(aff_map: dict, date_str: str, test_mode: bool) -> str:
    """제휴 링크 컬렉션 HTML 페이지를 생성합니다."""
    mode_badge = (
        '<span style="background:#f59e0b;color:#1c1917;padding:2px 8px;'
        'border-radius:4px;font-size:.75em;font-weight:700">TEST MODE</span> '
        if test_mode else ""
    )

    cards = []
    for cat in _CATEGORIES:
        items = []
        for kw in cat["keywords"]:
            info = aff_map.get(kw)
            if not info:
                continue
            commission = f' <em style="color:#6ee7b7;font-size:.8em">({info["commission"]})</em>' if info.get("commission") else ""
            items.append(
                f'<li><a href="{info["url"]}" target="_blank" rel="noopener sponsored" '
                f'style="color:#93c5fd;text-decoration:none">'
                f'{info["label"]}</a>{commission}</li>'
            )
        if not items:
            continue
        cards.append(f"""
    <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px;margin-bottom:16px">
      <h3 style="color:#e2e8f0;margin:0 0 6px;font-size:1em">{cat["name"]}</h3>
      <p style="color:#94a3b8;font-size:.85em;margin:0 0 10px">{cat["intro"]}</p>
      <ul style="margin:0;padding-left:18px;color:#cbd5e1;font-size:.9em;line-height:1.8">
        {"".join(items)}
      </ul>
    </div>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Income Tools — Affiliate Resource Page</title>
  <meta name="description" content="Curated affiliate tools for AI income creators — free to start, high commission.">
  <style>
    * {{ box-sizing:border-box }}
    body {{ background:#0f172a;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:24px }}
    .container {{ max-width:760px;margin:0 auto }}
    h1 {{ font-size:1.6em;color:#a5b4fc;margin-bottom:4px }}
    .meta {{ color:#64748b;font-size:.82em;margin-bottom:24px }}
    .disclaimer {{ background:#1e1b4b;border:1px solid #312e81;border-radius:8px;padding:12px 16px;
                   color:#a5b4fc;font-size:.78em;margin-top:28px;line-height:1.6 }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{mode_badge}AI Income Tools — Affiliate Resources</h1>
    <p class="meta">Generated: {date_str} UTC · Links marked with commission rates are affiliate links.</p>
    {"".join(cards)}
    <div class="disclaimer">
      <strong>Disclosure:</strong> Some links on this page are affiliate links.
      If you click through and make a purchase, I may earn a commission at no extra cost to you.
      I only recommend tools I personally use or have vetted for quality.
      {"<br><strong>[TEST MODE]</strong> Affiliate IDs are stubs — not real commission links." if test_mode else ""}
    </div>
  </div>
</body>
</html>"""


def run():
    test = is_test_mode()
    if test:
        print_test_banner("affiliate_generator")
        _inject_test_env()
        out_dir = test_output_dir("monetize")
    else:
        out_dir = OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

    aff_map = _build_affiliate_map()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    date_slug = datetime.now(timezone.utc).strftime("%Y%m%d")

    html = _build_html(aff_map, date_str, test)
    out_file = out_dir / f"affiliate_links_{date_slug}.html"
    out_file.write_text(html, encoding="utf-8")

    # 결과 요약 JSON
    result = {
        "file": str(out_file),
        "categories": len(_CATEGORIES),
        "links": sum(
            len([kw for kw in cat["keywords"] if kw in aff_map])
            for cat in _CATEGORIES
        ),
        "test_mode": test,
        "generated_at": date_str,
    }
    summary_file = out_dir / f"affiliate_links_{date_slug}.json"
    summary_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print(f"  ✓ 제휴 링크 페이지 생성: {out_file}")
    print(f"  ✓ 카테고리: {result['categories']} / 링크: {result['links']}")
    return result


if __name__ == "__main__":
    run()
