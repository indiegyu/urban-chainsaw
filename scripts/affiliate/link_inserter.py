"""
Affiliate 링크 삽입 유틸리티
==============================
HTML 본문에서 키워드를 감지하고 Affiliate 링크로 자동 교체합니다.

지원 Affiliate 프로그램 (모두 무료 가입):
  - Amazon Associates: https://affiliate-program.amazon.com
  - Fiverr: https://affiliates.fiverr.com (건당 $150-500)
  - Hostinger: https://www.hostinger.com/affiliates (건당 $100+)
  - ElevenLabs: https://elevenlabs.io/affiliates (30% 반복)
  - Jasper AI: https://www.jasper.ai/affiliates (30% 반복)
  - ConvertKit: https://partners.convertkit.com (30% 반복)
  - Semrush: https://www.semrush.com/company/media/partner (건당 $200)
  - Canva: Impact 통해 가입 (건당 $36)
  - Printify: https://printify.com/affiliate-program (건당 $15)

환경변수 설정:
  AMAZON_TAG        — Amazon Associates 태그 (예: aiblog-20)
  FIVERR_AFF_ID     — Fiverr affiliate bta= 값
  HOSTINGER_AFF_ID  — Hostinger 어필리에이트 ID
  ELEVENLABS_AFF_ID — ElevenLabs 파트너 ID
  JASPER_AFF_ID     — Jasper AI fpr= 값
  CONVERTKIT_AFF_ID — ConvertKit lmref= 값
  SEMRUSH_AFF_ID    — Semrush 파트너 ID
  PRINTIFY_AFF_ID   — Printify 어필리에이트 ID
"""

import re
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


def _url(base: str, param: str, env_key: str, fallback: str) -> str:
    """환경변수 ID가 있으면 어필리에이트 URL, 없으면 fallback URL 반환."""
    aff_id = os.environ.get(env_key, "").strip()
    if aff_id:
        return f"{base}{param}{aff_id}"
    return fallback


def _build_affiliate_map() -> dict:
    """환경변수 기반으로 실시간 어필리에이트 링크 맵 생성."""
    amz    = os.environ.get("AMAZON_TAG", "").strip()
    fiv    = os.environ.get("FIVERR_AFF_ID", "").strip()
    hos    = os.environ.get("HOSTINGER_AFF_ID", "").strip()
    eleven = os.environ.get("ELEVENLABS_AFF_ID", "").strip()
    jsp    = os.environ.get("JASPER_AFF_ID", "").strip()
    ck     = os.environ.get("CONVERTKIT_AFF_ID", "").strip()
    sem    = os.environ.get("SEMRUSH_AFF_ID", "").strip()
    pfy    = os.environ.get("PRINTIFY_AFF_ID", "").strip()

    return {
        # ── AI 도구 (블로그 주요 주제) ──────────────────────────────────────
        "elevenlabs":      {
            "url": f"https://elevenlabs.io/?from={eleven}" if eleven else "https://elevenlabs.io",
            "label": "ElevenLabs AI Voice", "commission": "30% recurring"},
        "jasper":          {
            "url": f"https://jasper.ai?fpr={jsp}" if jsp else "https://jasper.ai",
            "label": "Jasper AI", "commission": "30% recurring"},
        "jasper ai":       {
            "url": f"https://jasper.ai?fpr={jsp}" if jsp else "https://jasper.ai",
            "label": "Jasper AI", "commission": "30% recurring"},
        "canva":           {
            "url": "https://partner.canva.com/c/canva",
            "label": "Canva", "commission": "$36/sale"},
        "groq":            {
            "url": "https://groq.com",
            "label": "Groq AI", "commission": "free tool"},
        "chatgpt":         {
            "url": "https://openai.com/chatgpt",
            "label": "ChatGPT", "commission": "free tool"},
        "midjourney":      {
            "url": "https://midjourney.com",
            "label": "Midjourney", "commission": ""},
        "stable diffusion":{"url": "https://stability.ai", "label": "Stable Diffusion", "commission": ""},

        # ── 수익화 플랫폼 ────────────────────────────────────────────────────
        "fiverr":          {
            "url": f"https://go.fiverr.com/visit/?bta={fiv}&brand=fiverrcpa" if fiv else "https://fiverr.com",
            "label": "Fiverr", "commission": "$150-$500/sale"},
        "freelance":       {
            "url": f"https://go.fiverr.com/visit/?bta={fiv}&brand=fiverrcpa" if fiv else "https://fiverr.com",
            "label": "Fiverr", "commission": "$150-$500/sale"},
        "upwork":          {
            "url": "https://upwork.com",
            "label": "Upwork", "commission": ""},
        "print on demand": {
            "url": f"https://printify.com/app/register?referrer={pfy}" if pfy else "https://printify.com",
            "label": "Printify", "commission": "$15/signup"},
        "printify":        {
            "url": f"https://printify.com/app/register?referrer={pfy}" if pfy else "https://printify.com",
            "label": "Printify", "commission": "$15/signup"},
        "etsy":            {
            "url": "https://etsy.com/sell",
            "label": "Etsy", "commission": ""},
        "dropshipping":    {
            "url": "https://shopify.pxf.io/c/shopify",
            "label": "Shopify", "commission": "$58/sale"},
        "shopify":         {
            "url": "https://shopify.pxf.io/c/shopify",
            "label": "Shopify", "commission": "$58/sale"},

        # ── 이메일/뉴스레터 ─────────────────────────────────────────────────
        "email marketing": {
            "url": f"https://partners.convertkit.com/?lmref={ck}" if ck else "https://convertkit.com",
            "label": "ConvertKit", "commission": "30% recurring"},
        "convertkit":      {
            "url": f"https://partners.convertkit.com/?lmref={ck}" if ck else "https://convertkit.com",
            "label": "ConvertKit", "commission": "30% recurring"},
        "kit":             {
            "url": f"https://partners.convertkit.com/?lmref={ck}" if ck else "https://convertkit.com",
            "label": "ConvertKit", "commission": "30% recurring"},
        "newsletter":      {
            "url": "https://beehiiv.com",
            "label": "Beehiiv", "commission": "referral bonus"},

        # ── 호스팅/도메인 ────────────────────────────────────────────────────
        "web hosting":     {
            "url": f"https://hostinger.com?REFERRALCODE={hos}" if hos else "https://hostinger.com",
            "label": "Hostinger", "commission": "$100+/sale"},
        "hostinger":       {
            "url": f"https://hostinger.com?REFERRALCODE={hos}" if hos else "https://hostinger.com",
            "label": "Hostinger", "commission": "$100+/sale"},
        "wordpress":       {
            "url": f"https://hostinger.com?REFERRALCODE={hos}" if hos else "https://hostinger.com/wordpress-hosting",
            "label": "Hostinger WordPress", "commission": "$100+/sale"},
        "bluehost":        {
            "url": "https://www.bluehost.com/track/",
            "label": "Bluehost", "commission": "$65/sale"},

        # ── SEO 도구 ─────────────────────────────────────────────────────────
        "seo":             {
            "url": f"https://semrush.sjv.io/{sem}" if sem else "https://semrush.com",
            "label": "Semrush", "commission": "$200/sale"},
        "semrush":         {
            "url": f"https://semrush.sjv.io/{sem}" if sem else "https://semrush.com",
            "label": "Semrush", "commission": "$200/sale"},
        "ahrefs":          {
            "url": "https://ahrefs.com",
            "label": "Ahrefs", "commission": ""},
        "keyword research":{
            "url": f"https://semrush.sjv.io/{sem}" if sem else "https://semrush.com",
            "label": "Semrush", "commission": "$200/sale"},

        # ── Amazon (물리적 상품) ─────────────────────────────────────────────
        "laptop":          {
            "url": f"https://www.amazon.com/s?k=best+laptop+for+remote+work&tag={amz}" if amz else "https://amazon.com/s?k=best+laptop+remote+work",
            "label": "Amazon", "commission": "4%"},
        "microphone":      {
            "url": f"https://www.amazon.com/s?k=best+usb+microphone&tag={amz}" if amz else "https://amazon.com/s?k=usb+microphone",
            "label": "Amazon", "commission": "4%"},
        "ring light":      {
            "url": f"https://www.amazon.com/s?k=ring+light+for+youtube&tag={amz}" if amz else "https://amazon.com/s?k=ring+light",
            "label": "Amazon", "commission": "4%"},
        "webcam":          {
            "url": f"https://www.amazon.com/s?k=best+webcam&tag={amz}" if amz else "https://amazon.com/s?k=best+webcam",
            "label": "Amazon", "commission": "4%"},

        # ── 학습/강의 ────────────────────────────────────────────────────────
        "udemy":           {
            "url": "https://click.linksynergy.com/fs-bin/click?id=udemy",
            "label": "Udemy", "commission": "15%"},
        "coursera":        {
            "url": "https://imp.i384100.net/coursera",
            "label": "Coursera", "commission": "45%"},
        "skillshare":      {
            "url": "https://skillshare.eqcm.net/skillshare",
            "label": "Skillshare", "commission": "$7/trial"},
    }


AFFILIATE_MAP = _build_affiliate_map()


def insert_affiliate_links(html: str, max_per_post: int = 5) -> tuple:
    """
    HTML 본문에서 키워드를 찾아 최대 max_per_post개의 Affiliate 링크를 삽입합니다.
    이미 <a> 태그 안에 있는 텍스트는 건드리지 않습니다.
    """
    # 실시간으로 맵을 재빌드 (워크플로 실행 시 env var 반영)
    aff_map = _build_affiliate_map()
    inserted = []

    linked_spans = [
        (m.start(), m.end()) for m in re.finditer(r"<a\b[^>]*>.*?</a>", html, re.DOTALL | re.IGNORECASE)
    ]

    def is_already_linked(start: int, end: int) -> bool:
        return any(ls <= start and end <= le for ls, le in linked_spans)

    # 긴 키워드(구체적) 우선 처리
    sorted_keywords = sorted(aff_map.keys(), key=lambda k: len(k), reverse=True)

    for keyword in sorted_keywords:
        if len(inserted) >= max_per_post:
            break

        info = aff_map[keyword]
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)

        for match in pattern.finditer(html):
            if is_already_linked(match.start(), match.end()):
                continue

            original_text = match.group(0)
            title_attr = f' title="{info["label"]}"' if info.get("label") else ""
            link_html = (
                f'<a href="{info["url"]}" target="_blank" rel="noopener sponsored"{title_attr}>'
                f'{original_text}</a>'
            )
            html = html[: match.start()] + link_html + html[match.end():]
            inserted.append({"keyword": keyword, **info})

            offset = len(link_html) - len(original_text)
            linked_spans = [
                (s + offset if s >= match.start() else s,
                 e + offset if e >= match.start() else e)
                for s, e in linked_spans
            ]
            linked_spans.append((match.start(), match.start() + len(link_html)))
            break

    return html, inserted


def build_cta_box(beehiiv_pub_id: str = "", kofi_username: str = "") -> str:
    """포스트 하단에 삽입할 수익화 CTA 박스 HTML."""
    subscribe_btn = ""
    if beehiiv_pub_id:
        subscribe_btn = f'<a href="https://www.beehiiv.com/subscribe/{beehiiv_pub_id}" target="_blank" rel="noopener" style="display:inline-block;background:#6366f1;color:#fff;padding:11px 24px;border-radius:8px;text-decoration:none;font-weight:700;font-size:.9em;margin:4px">📧 뉴스레터 무료 구독</a>'
    kofi_btn = ""
    if kofi_username:
        kofi_btn = f'<a href="https://ko-fi.com/{kofi_username}" target="_blank" rel="noopener" style="display:inline-block;background:#ff5e5b;color:#fff;padding:11px 24px;border-radius:8px;text-decoration:none;font-weight:700;font-size:.9em;margin:4px">☕ 커피 한 잔 사주기</a>'

    return f"""
<div style="background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 100%);
            border:1px solid #312e81;border-radius:14px;padding:28px 24px;
            margin:40px 0;text-align:center;color:#e2e8f0">
  <div style="font-size:1.6em;margin-bottom:8px">🤖</div>
  <h3 style="color:#a5b4fc;font-size:1.15em;margin-bottom:8px;font-family:-apple-system,sans-serif">
    매일 AI 수익화 전략 무료로 받기
  </h3>
  <p style="color:#94a3b8;font-size:.88em;margin-bottom:18px;line-height:1.6">
    2,500명이 구독 중 · 매일 아침 실행 가능한 AI 수익 팁 하나씩
  </p>
  <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px">
    {subscribe_btn}
    {kofi_btn}
    <a href="https://www.youtube.com/@psg9806" target="_blank" rel="noopener"
       style="display:inline-block;background:#ff0000;color:#fff;padding:11px 24px;
              border-radius:8px;text-decoration:none;font-weight:700;font-size:.9em;margin:4px">
      ▶ YouTube 구독
    </a>
  </div>
</div>"""


# ── 간이 HTTP 서버 (n8n에서 HTTP 노드로 호출 가능) ──────────────────────────
class AffiliateHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length))
        html   = body.get("html", "")
        limit  = body.get("max_links", 5)
        modified_html, links = insert_affiliate_links(html, limit)
        response = json.dumps({"html": modified_html, "inserted_links": links})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response.encode())

    def log_message(self, *args):
        pass


def serve(port: int = 8765):
    server = HTTPServer(("0.0.0.0", port), AffiliateHandler)
    print(f"Affiliate link server running on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve(int(sys.argv[2]) if len(sys.argv) > 2 else 8765)
    else:
        sample_html = "<p>Use <strong>Fiverr</strong> to make money, then scale with <em>email marketing</em>. Try <em>Canva</em> for design and <em>Jasper AI</em> for writing.</p>"
        result, links = insert_affiliate_links(sample_html)
        print("Modified HTML:", result[:300])
        print(f"\nInserted {len(links)} affiliate links:")
        for link in links:
            print(f"  • {link['keyword']} → {link['label']} ({link['commission']})")
