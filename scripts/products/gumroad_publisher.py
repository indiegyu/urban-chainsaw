"""
Lemon Squeezy 자동 상품 등록
==============================
auto_product.py가 생성한 상품을 Lemon Squeezy API로 자동 등록합니다.
Gumroad보다 수수료 낮음 (5% vs 10%), API 완전 오픈.

필요 시크릿: LEMONSQUEEZY_API_KEY
  → app.lemonsqueezy.com → Settings → API → Generate API key
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

LS_API        = "https://api.lemonsqueezy.com/v1"
OUTPUT_DIR    = Path(__file__).parent / "output"
STRATEGY_PATH = Path(__file__).parent.parent / "strategy" / "content_strategy.json"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


def get_store_id(token: str) -> str:
    """계정의 첫 번째 스토어 ID를 자동으로 가져옵니다."""
    r = requests.get(f"{LS_API}/stores", headers=_headers(token), timeout=15)
    r.raise_for_status()
    stores = r.json().get("data", [])
    if not stores:
        raise RuntimeError("Lemon Squeezy 스토어가 없습니다. app.lemonsqueezy.com에서 스토어 먼저 생성하세요.")
    store_id = stores[0]["id"]
    store_name = stores[0]["attributes"].get("name", "")
    print(f"  ✓ 스토어: {store_name} (id={store_id})")
    return store_id


def create_product(store_id: str, title: str, description: str, token: str) -> str:
    """Lemon Squeezy 상품을 생성하고 product_id를 반환합니다."""
    payload = {"data": {
        "type": "products",
        "attributes": {"name": title, "description": description},
        "relationships": {"store": {"data": {"type": "stores", "id": str(store_id)}}},
    }}
    r = requests.post(f"{LS_API}/products", headers=_headers(token),
                      json=payload, timeout=20)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"상품 생성 실패: {r.status_code} {r.text[:300]}")
    product_id = r.json()["data"]["id"]
    print(f"  ✓ 상품 생성 (id={product_id})")
    return product_id


def create_variant(product_id: str, price_cents: int, token: str) -> str:
    """가격 변형(variant)을 생성하고 variant_id를 반환합니다."""
    payload = {"data": {
        "type": "variants",
        "attributes": {
            "name": "Default",
            "price": price_cents,
            "pay_what_you_want": False,
            "status": "published",
        },
        "relationships": {"product": {"data": {"type": "products", "id": str(product_id)}}},
    }}
    r = requests.post(f"{LS_API}/variants", headers=_headers(token),
                      json=payload, timeout=20)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Variant 생성 실패: {r.status_code} {r.text[:300]}")
    variant_id = r.json()["data"]["id"]
    print(f"  ✓ 가격 설정 (${price_cents//100}, variant id={variant_id})")
    return variant_id


def upload_file(variant_id: str, file_path: Path, token: str):
    """상품 파일을 variant에 첨부합니다."""
    if not file_path or not file_path.exists():
        print("  ⚠ 파일 없음 — 파일 첨부 스킵")
        return
    mime = "text/html" if file_path.suffix == ".html" else "text/plain"
    with open(file_path, "rb") as f:
        r = requests.post(
            f"{LS_API}/files",
            headers={"Authorization": f"Bearer {token}"},  # multipart: Content-Type 자동 설정
            data={"variant_id": variant_id},
            files={"file": (file_path.name, f, mime)},
            timeout=60,
        )
    if r.status_code in (200, 201):
        print(f"  ✓ 파일 첨부: {file_path.name}")
    else:
        print(f"  ⚠ 파일 첨부 실패: {r.status_code} {r.text[:200]}")


def get_product_url(product_id: str, token: str) -> str:
    """상품의 구매 URL을 가져옵니다."""
    try:
        r = requests.get(f"{LS_API}/products/{product_id}", headers=_headers(token), timeout=10)
        if r.status_code == 200:
            attrs = r.json()["data"]["attributes"]
            return attrs.get("buy_now_url") or attrs.get("url", "")
    except Exception:
        pass
    return ""


def build_description(product: dict) -> str:
    base = product.get("description") or product.get("subtitle", "")
    return (
        f"{base}\n\n"
        "✅ Instant digital download\n"
        "✅ Practical, actionable content\n"
        "✅ Based on real AI income strategies\n\n"
        "📌 From the AI Income Daily YouTube channel\n"
        "🔔 Free daily tips: youtube.com/@AIIncomeDaily\n\n"
        "30-day money-back guarantee."
    )


def record_product(product_info: dict):
    strategy = json.loads(STRATEGY_PATH.read_text())
    created = strategy.get("gumroad_products_created", [])  # 키 유지 (하위호환)
    created.append({
        "title":      product_info["title"],
        "url":        product_info.get("url", ""),
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "price_usd":  product_info.get("price_usd", 0),
        "platform":   "lemonsqueezy",
    })
    strategy["gumroad_products_created"] = created
    STRATEGY_PATH.write_text(json.dumps(strategy, indent=2, ensure_ascii=False))


def run():
    from dotenv import load_dotenv
    load_dotenv()

    token = os.environ.get("LEMONSQUEEZY_API_KEY", "")
    if not token:
        print("  ⚠ LEMONSQUEEZY_API_KEY 없음 — 등록 스킵")
        print("  → app.lemonsqueezy.com → Settings → API → Generate API key")
        print("  → GitHub Secrets에 LEMONSQUEEZY_API_KEY로 추가")
        return None

    # 가장 최근 생성된 상품 메타 찾기
    meta_files = sorted(OUTPUT_DIR.glob("*_meta.json"), reverse=True)
    if not meta_files:
        print("  ✗ 상품 메타 파일 없음 — auto_product.py 먼저 실행 필요")
        return None

    meta = json.loads(meta_files[0].read_text())
    title = meta["title"]
    price_cents = meta.get("price_usd", 17) * 100

    stem = meta_files[0].stem.replace("_meta", "")
    product_file = next(
        (OUTPUT_DIR / (stem + ext) for ext in [".html", ".txt"]
         if (OUTPUT_DIR / (stem + ext)).exists()), None
    )

    print(f"\n🛍️  Lemon Squeezy 등록: '{title}' (${meta.get('price_usd', 17)})")

    try:
        store_id   = get_store_id(token)
        desc       = build_description(meta)
        product_id = create_product(store_id, title, desc, token)
        variant_id = create_variant(product_id, price_cents, token)
        if product_file:
            upload_file(variant_id, product_file, token)
        url = get_product_url(product_id, token)

        result = {"title": title, "url": url, "price_usd": meta.get("price_usd", 17)}
        record_product(result)

        print(f"\n✅ 등록 완료!")
        print(f"   판매 링크: {url or '(app.lemonsqueezy.com에서 확인)'}")
        return result
    except Exception as e:
        print(f"  ✗ 등록 실패: {e}")
        return None


if __name__ == "__main__":
    run()
