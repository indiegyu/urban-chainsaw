"""
Etsy 디지털 상품 자동 등록
============================
Lemon Squeezy와 동일한 상품을 Etsy에도 동시 등록.
Etsy 활성 구매자 9000만 명 — 검색 기반 수동 유입.

필요 시크릿:
  ETSY_API_KEY      — etsy.com/developers → Create App → API Key
  ETSY_ACCESS_TOKEN — OAuth2 액세스 토큰 (아래 안내 참조)
  ETSY_SHOP_ID      — 본인 Etsy 샵 ID (URL: etsy.com/shop/YOURSHOP)

OAuth 토큰 발급:
  1. etsy.com/developers → Create App
  2. Scopes: listings_w, listings_r
  3. Authorization URL로 접속 → 토큰 발급
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

ETSY_API      = "https://openapi.etsy.com/v3/application"
OUTPUT_DIR    = Path(__file__).parent / "output"
STRATEGY_PATH = Path(__file__).parent.parent / "strategy" / "content_strategy.json"
STATE_FILE    = Path(__file__).parent / ".etsy_listed.json"


def _headers(api_key: str, token: str) -> dict:
    return {
        "x-api-key": api_key,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"listed": []}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def create_listing(shop_id: str, api_key: str, token: str,
                   title: str, description: str, price: float,
                   tags: list[str]) -> dict:
    """Etsy 디지털 상품 드래프트 등록."""
    payload = {
        "quantity":         999,
        "title":            title[:140],
        "description":      description,
        "price":            price,
        "who_made":         "i_did",
        "when_made":        "made_to_order",
        "taxonomy_id":      2078,    # Digital Downloads > Other Digital Files
        "type":             "download",
        "is_digital":       True,
        "should_auto_renew": True,
        "tags":             tags[:13],
        "materials":        ["digital download", "PDF", "AI-generated"],
        "state":            "active",
    }
    r = requests.post(
        f"{ETSY_API}/shops/{shop_id}/listings",
        headers=_headers(api_key, token),
        json=payload,
        timeout=20,
    )
    if r.status_code in (200, 201):
        return r.json()
    raise RuntimeError(f"Etsy 등록 실패: {r.status_code} {r.text[:300]}")


def build_etsy_description(product: dict) -> str:
    base = product.get("description") or product.get("subtitle", "")
    return (
        f"✨ {product['title']}\n\n"
        f"{base}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "WHAT YOU GET:\n"
        "✅ Instant digital download\n"
        "✅ Practical, step-by-step content\n"
        "✅ Based on real AI income strategies\n"
        "✅ Beginner-friendly\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 From AI Income Daily — Subscribe on YouTube for free daily tips!\n"
        "🔔 youtube.com/@AIIncomeDaily\n\n"
        "30-day satisfaction guarantee."
    )


def run():
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.environ.get("ETSY_API_KEY", "")
    token   = os.environ.get("ETSY_ACCESS_TOKEN", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")

    if not all([api_key, token, shop_id]):
        missing = [k for k, v in {
            "ETSY_API_KEY": api_key,
            "ETSY_ACCESS_TOKEN": token,
            "ETSY_SHOP_ID": shop_id,
        }.items() if not v]
        print(f"  ⚠ Etsy 시크릿 없음 ({', '.join(missing)}) — 스킵")
        print("  → etsy.com/developers 에서 앱 생성 후 GitHub Secrets 추가")
        return

    # 최근 생성된 상품 메타 로드
    meta_files = sorted(OUTPUT_DIR.glob("*_meta.json"), reverse=True)
    if not meta_files:
        print("  ✗ 상품 메타 없음 — auto_product.py 먼저 실행 필요")
        return

    state = _load_state()

    listed = 0
    for meta_file in meta_files[:3]:   # 최근 3개 상품 순회
        meta  = json.loads(meta_file.read_text())
        title = meta["title"]

        if title in state["listed"]:
            print(f"  - 이미 등록됨: {title[:50]}")
            continue

        print(f"\n🛒 Etsy 등록: '{title}' (${meta.get('price_usd', 17)})")
        tags = [
            "AI tools", "passive income", "digital download", "ChatGPT",
            "make money online", "side hustle", "AI income", "prompt pack",
            "automation", "online business", "PDF guide", "2026",
        ]
        try:
            result = create_listing(
                shop_id, api_key, token, title,
                build_etsy_description(meta),
                float(meta.get("price_usd", 17)),
                tags,
            )
            listing_id  = result.get("listing_id", "")
            listing_url = f"https://www.etsy.com/listing/{listing_id}" if listing_id else ""
            print(f"  ✓ 등록 완료: {listing_url}")

            state["listed"].append(title)
            if listing_url:
                # strategy.json에도 Etsy URL 기록
                try:
                    strategy = json.loads(STRATEGY_PATH.read_text())
                    for p in strategy.get("gumroad_products_created", []):
                        if p.get("title") == title:
                            p["etsy_url"] = listing_url
                    STRATEGY_PATH.write_text(json.dumps(strategy, indent=2, ensure_ascii=False))
                except Exception:
                    pass
            listed += 1
        except Exception as e:
            print(f"  ✗ 실패: {e}")

    _save_state(state)
    print(f"\n✅ Etsy: {listed}개 상품 등록 완료")


if __name__ == "__main__":
    run()
