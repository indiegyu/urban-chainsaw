"""
Amazon KDP 자동 이북 생성기
============================
Groq AI로 5,000~15,000자 분량의 전문 이북을 생성하고
HTML → PDF로 변환 후 KDP 업로드용으로 저장합니다.

Amazon KDP 수익:
  - $2.99~$9.99 가격대: 인세 70% ($2.09~$6.99/권)
  - Free Tier (KDP Select): 페이지당 $0.0045 (KENP)
  - 틈새 시장 공략 시 월 $300~$3,000 가능

초기 설정 (1회 수동):
  1. https://kdp.amazon.com 계정 생성
  2. 생성된 PDF를 업로드 + 표지 설정
  3. 가격 $2.99로 설정 → 자동 판매

무료 도구:
  - wkhtmltopdf (GitHub Actions에서 apt-get으로 설치)
  - Groq API (무료 티어)

필요한 환경변수:
  GROQ_API_KEY — Groq API 키
"""

import os, sys, json, re, time
import requests
from pathlib import Path
from datetime import datetime

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
OUTPUT_DIR = Path(__file__).parent / "output"

# KDP에서 잘 팔리는 틈새 주제들 (경쟁 낮고 수요 높은)
EBOOK_TOPICS = [
    {
        "title": "ChatGPT Side Hustles: 27 Ways to Make $500/Month with AI in 2026",
        "genre": "Business & Money",
        "audience": "beginners wanting to make money with AI",
        "chapters": [
            "Introduction: The AI Income Revolution",
            "Chapter 1: AI Writing & Content Creation",
            "Chapter 2: AI Automation Services",
            "Chapter 3: AI-Powered Freelancing",
            "Chapter 4: Selling AI Art & Designs",
            "Chapter 5: AI YouTube Channel",
            "Chapter 6: AI Coaching & Courses",
            "Chapter 7: Building AI Micro-SaaS Tools",
            "Conclusion: Your 30-Day Action Plan",
        ]
    },
    {
        "title": "Print on Demand Mastery: Build a $3,000/Month Passive Income Business",
        "genre": "Business & Money",
        "audience": "people wanting passive income with no upfront cost",
        "chapters": [
            "Introduction: Why Print on Demand in 2026",
            "Chapter 1: Choosing Your Niche",
            "Chapter 2: Design Strategies That Sell",
            "Chapter 3: Printify vs Printful vs Redbubble",
            "Chapter 4: Etsy SEO Mastery",
            "Chapter 5: Scaling to 500+ Products",
            "Chapter 6: Automating with AI Tools",
            "Conclusion: Your POD Launch Checklist",
        ]
    },
    {
        "title": "YouTube Automation Playbook: Make Money Without Showing Your Face",
        "genre": "Computers & Technology",
        "audience": "people wanting YouTube income without appearing on camera",
        "chapters": [
            "Introduction: Faceless YouTube Empire",
            "Chapter 1: Niche Selection Formula",
            "Chapter 2: AI Script Writing",
            "Chapter 3: Voice Synthesis & Video Assembly",
            "Chapter 4: Thumbnail Psychology",
            "Chapter 5: Upload & Optimize Strategy",
            "Chapter 6: Monetization Paths",
            "Conclusion: 90-Day Roadmap",
        ]
    },
    {
        "title": "Passive Income with Affiliate Marketing: The 2026 No-BS Guide",
        "genre": "Business & Money",
        "audience": "beginners to affiliate marketing",
        "chapters": [
            "Introduction: Why Affiliate Marketing Works",
            "Chapter 1: Choosing Profitable Programs",
            "Chapter 2: Content That Converts",
            "Chapter 3: SEO on Zero Budget",
            "Chapter 4: Email List Building",
            "Chapter 5: Scaling with Automation",
            "Chapter 6: Advanced Strategies",
            "Conclusion: Your First $1,000",
        ]
    },
]


def groq_request(messages: list, groq_key: str, max_tokens: int = 4000) -> str:
    resp = requests.post(GROQ_URL, headers={
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }, json={
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }, timeout=90)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def generate_chapter(title: str, chapter: str, audience: str, groq_key: str) -> str:
    content = groq_request([
        {"role": "system", "content": (
            f"You are a bestselling author writing an ebook titled '{title}'. "
            f"Target audience: {audience}. "
            "Write in a conversational, actionable style. "
            "Include: practical tips, numbered lists, real examples, and a mini action step at the end. "
            "Write 600-800 words in clean HTML (use <h2>, <p>, <ul><li>, <strong> tags). "
            "No fluff, no filler. Every sentence must provide value."
        )},
        {"role": "user", "content": f"Write the full content for: {chapter}"}
    ], groq_key, max_tokens=1500)
    return content


def build_ebook_html(topic: dict, chapters_content: list) -> str:
    title = topic["title"]
    chapters_html = ""
    for i, (chapter_title, content) in enumerate(zip(topic["chapters"], chapters_content)):
        chapters_html += f"""
<div class="chapter" id="ch{i}">
  <h2>{chapter_title}</h2>
  {content}
</div>
<div class="page-break"></div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @page {{ margin: 2cm; }}
  body {{ font-family: Georgia, 'Times New Roman', serif; font-size: 11pt; line-height: 1.8; color: #1a1a1a; }}
  h1.book-title {{ font-size: 28pt; text-align: center; color: #0f172a; margin: 3cm 0 1cm 0; padding: 0; }}
  h1.subtitle {{ font-size: 14pt; text-align: center; color: #475569; font-weight: normal; }}
  .author {{ text-align: center; margin: 2cm 0; color: #94a3b8; }}
  .toc {{ margin: 2cm 0; padding: 1cm; background: #f8fafc; border-left: 4px solid #6366f1; }}
  .toc h2 {{ color: #0f172a; }}
  .toc ol {{ margin: 0.5cm 0; }}
  .chapter {{ margin: 1cm 0; }}
  h2 {{ font-size: 18pt; color: #1e3a5f; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.3cm; margin-top: 1.5cm; }}
  p {{ margin: 0.5cm 0; text-align: justify; }}
  ul, ol {{ margin: 0.3cm 0.5cm; }}
  li {{ margin: 0.2cm 0; }}
  strong {{ color: #0f172a; }}
  .action-step {{ background: #f0fdf4; border-left: 4px solid #22c55e; padding: 0.5cm; margin: 0.5cm 0; }}
  .page-break {{ page-break-after: always; }}
  .disclaimer {{ font-size: 9pt; color: #94a3b8; margin-top: 2cm; border-top: 1px solid #e2e8f0; padding-top: 0.5cm; }}
</style>
</head>
<body>

<div class="page-break" style="text-align:center; padding-top: 5cm;">
  <h1 class="book-title">{title}</h1>
  <h1 class="subtitle">A Practical Guide for 2026</h1>
  <div class="author">Published {datetime.now().year} · AI Income Automation</div>
</div>

<div class="toc">
  <h2>Table of Contents</h2>
  <ol>
    {''.join(f'<li>{ch}</li>' for ch in topic["chapters"])}
  </ol>
</div>
<div class="page-break"></div>

{chapters_html}

<div class="disclaimer">
  <p><strong>Disclaimer:</strong> Results vary based on individual effort and market conditions.
  Income figures mentioned are potential estimates, not guarantees.
  Always do your own research before starting any business.</p>
</div>

</body>
</html>"""


def html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    """wkhtmltopdf로 HTML → PDF 변환."""
    import subprocess
    try:
        result = subprocess.run([
            "wkhtmltopdf",
            "--page-size", "A5",
            "--margin-top", "20mm",
            "--margin-bottom", "20mm",
            "--margin-left", "20mm",
            "--margin-right", "20mm",
            "--encoding", "utf-8",
            "--enable-local-file-access",
            str(html_path),
            str(pdf_path),
        ], capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except FileNotFoundError:
        print("  ⚠ wkhtmltopdf not installed — saving HTML only")
        return False
    except Exception as e:
        print(f"  ⚠ PDF conversion failed: {e}")
        return False


def run(topic_idx: int = None):
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        print("GROQ_API_KEY not set")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 오늘 날짜 기준으로 주제 순환
    if topic_idx is None:
        topic_idx = datetime.now().timetuple().tm_yday % len(EBOOK_TOPICS)

    topic = EBOOK_TOPICS[topic_idx]
    print(f"\n📚 생성 중: '{topic['title']}'")
    print(f"   챕터 수: {len(topic['chapters'])}")

    chapters_content = []
    for i, chapter in enumerate(topic["chapters"]):
        print(f"  [{i+1}/{len(topic['chapters'])}] {chapter[:60]}...")
        content = generate_chapter(topic["title"], chapter, topic["audience"], groq_key)
        chapters_content.append(content)
        time.sleep(1)  # Rate limit

    html = build_ebook_html(topic, chapters_content)

    # 파일명 생성
    ts    = datetime.now().strftime("%Y%m%d")
    slug  = re.sub(r'[^a-z0-9]+', '-', topic["title"].lower())[:50]
    html_path = OUTPUT_DIR / f"{ts}_{slug}.html"
    pdf_path  = OUTPUT_DIR / f"{ts}_{slug}.pdf"

    html_path.write_text(html, encoding="utf-8")
    print(f"  ✓ HTML 저장: {html_path.name}")

    if html_to_pdf(html_path, pdf_path):
        size_mb = pdf_path.stat().st_size / 1024 / 1024
        print(f"  ✓ PDF 생성: {pdf_path.name} ({size_mb:.1f}MB)")
    else:
        print(f"  → HTML 파일을 수동으로 PDF 변환 후 KDP 업로드")

    # KDP 업로드 안내
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📖 Amazon KDP 업로드 안내
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  제목: {topic['title']}
  장르: {topic['genre']}
  추천 가격: $2.99 (인세 70% = $2.09/권)

  업로드 URL: https://kdp.amazon.com/en_US/title-setup/kindle/new

  1. 'Kindle eBook Content' 탭 → Manuscript 업로드
  2. 표지: Canva 무료로 제작 (1600x2560px)
  3. 가격: $2.99 설정 → 70% 로열티
  4. KDP Select 등록 시 페이지당 $0.0045 추가
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

    return {"html": str(html_path), "pdf": str(pdf_path) if pdf_path.exists() else None}


if __name__ == "__main__":
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run(idx)
