"""
Affiliate 링크 삽입 유틸리티
==============================
HTML 본문에서 키워드를 감지하고 해당 Affiliate 링크로 자동 교체합니다.
n8n 워크플로의 'Insert Affiliate Links' 노드에서 HTTP로 호출하거나
단독 실행 스크립트로 사용할 수 있습니다.

지원 Affiliate 프로그램:
  - Amazon Associates (최대 10% 커미션)
  - SaaS 제품 (20–50% 반복 커미션)
  - 호스팅 서비스 (건당 $50–$200)
"""

import re
import os
from typing import Optional
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# ── Affiliate 링크 매핑 테이블 ────────────────────────────────────────────────
# 키워드(소문자) → 링크 딕셔너리
# 실제 Affiliate 태그/링크로 교체해야 합니다
AFFILIATE_MAP: dict[str, dict] = {
    # Amazon Associates
    "laptop":        {"url": "https://amzn.to/YOURTAG", "program": "Amazon", "commission": "4%"},
    "headphones":    {"url": "https://amzn.to/YOURTAG", "program": "Amazon", "commission": "4%"},
    "keyboard":      {"url": "https://amzn.to/YOURTAG", "program": "Amazon", "commission": "4%"},
    "monitor":       {"url": "https://amzn.to/YOURTAG", "program": "Amazon", "commission": "4%"},
    "coffee maker":  {"url": "https://amzn.to/YOURTAG", "program": "Amazon", "commission": "8%"},
    "running shoes": {"url": "https://amzn.to/YOURTAG", "program": "Amazon", "commission": "4%"},

    # SaaS – Hosting (고수익)
    "web hosting":   {"url": "https://www.hostinger.com/affiliate", "program": "Hostinger", "commission": "$100/sale"},
    "vps":           {"url": "https://www.vultr.com/?ref=YOURID",   "program": "Vultr",     "commission": "$100/sale"},
    "domain":        {"url": "https://namecheap.pxf.io/YOURID",     "program": "Namecheap", "commission": "35%"},

    # SaaS – Productivity (반복 커미션)
    "email marketing": {"url": "https://convertkit.com/?lmref=YOURID",  "program": "ConvertKit",  "commission": "30% recurring"},
    "newsletter":      {"url": "https://beehiiv.com/partner/YOURID",    "program": "Beehiiv",     "commission": "50% 3개월"},
    "automation":      {"url": "https://n8n.io/affiliates/?ref=YOURID", "program": "n8n",         "commission": "30% 12개월"},
    "project management": {"url": "https://notion.so/affiliates",       "program": "Notion",      "commission": "$10/signup"},

    # SaaS – AI Tools
    "ai writing":    {"url": "https://jasper.ai/affiliate",             "program": "Jasper AI",   "commission": "30% recurring"},
    "seo tool":      {"url": "https://ahrefs.com/affiliates",           "program": "Ahrefs",      "commission": "$1.5/trial"},
    "video editing": {"url": "https://invideo.io/affiliate",            "program": "InVideo AI",  "commission": "50%"},
}

# ── 링크 삽입 로직 ─────────────────────────────────────────────────────────────
def insert_affiliate_links(html: str, max_per_post: int = 3) -> tuple[str, list[dict]]:
    """
    HTML 본문에서 키워드를 찾아 최대 max_per_post개의 Affiliate 링크를 삽입합니다.
    이미 <a> 태그 안에 있는 텍스트는 건드리지 않습니다.

    Returns:
        (수정된 html, 삽입된 링크 목록)
    """
    inserted = []
    html_lower = html.lower()

    # 이미 링크 처리된 구간 추적 (중복 삽입 방지)
    linked_spans: list[tuple[int, int]] = [
        (m.start(), m.end()) for m in re.finditer(r"<a\b[^>]*>.*?</a>", html, re.DOTALL | re.IGNORECASE)
    ]

    def is_already_linked(start: int, end: int) -> bool:
        return any(ls <= start and end <= le for ls, le in linked_spans)

    # 수익성 높은 키워드 우선 처리
    sorted_keywords = sorted(AFFILIATE_MAP.keys(), key=lambda k: len(k), reverse=True)

    for keyword in sorted_keywords:
        if len(inserted) >= max_per_post:
            break

        info = AFFILIATE_MAP[keyword]
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)

        for match in pattern.finditer(html):
            if is_already_linked(match.start(), match.end()):
                continue

            # 첫 번째 등장에만 링크 삽입
            original_text = match.group(0)
            link_html = (
                f'<a href="{info["url"]}" target="_blank" rel="noopener sponsored">'
                f'{original_text}</a>'
            )
            html = html[: match.start()] + link_html + html[match.end() :]
            inserted.append({"keyword": keyword, **info})

            # linked_spans 업데이트 (오프셋 이동)
            offset = len(link_html) - len(original_text)
            linked_spans = [(s + offset if s >= match.start() else s,
                             e + offset if e >= match.start() else e)
                            for s, e in linked_spans]
            linked_spans.append((match.start(), match.start() + len(link_html)))
            break  # 키워드당 한 번만 삽입

    return html, inserted


# ── 간이 HTTP 서버 (n8n에서 HTTP 노드로 호출 가능) ──────────────────────────
class AffiliateHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length))
        html   = body.get("html", "")
        limit  = body.get("max_links", 3)

        modified_html, links = insert_affiliate_links(html, limit)
        response = json.dumps({"html": modified_html, "inserted_links": links})

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response.encode())

    def log_message(self, *args):
        pass  # 로그 억제


def serve(port: int = 8765):
    server = HTTPServer(("0.0.0.0", port), AffiliateHandler)
    print(f"Affiliate link server running on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve(int(sys.argv[2]) if len(sys.argv) > 2 else 8765)
    else:
        # 테스트 실행
        sample_html = """
        <p>Looking for the best <strong>laptop</strong> for remote work?
        Check our guide on <em>web hosting</em> and <em>email marketing</em>
        automation tools. We also cover <em>seo tool</em> recommendations.</p>
        """
        result, links = insert_affiliate_links(sample_html)
        print("Modified HTML:")
        print(result)
        print(f"\nInserted {len(links)} affiliate links:")
        for link in links:
            print(f"  • {link['keyword']} → {link['program']} ({link['commission']})")
