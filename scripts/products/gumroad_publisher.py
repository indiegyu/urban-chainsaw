"""
Gumroad 자동 상품 등록
=======================
auto_product.py가 생성한 상품을 Gumroad API로 자동 등록합니다.

필요 시크릿: GUMROAD_ACCESS_TOKEN
  → gumroad.com/settings/advanced → Generate Access Token
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

GUMROAD_API   = "https://api.gumroad.com/v2"
OUTPUT_DIR    = Path(__file__).parent / "output"
STRATEGY_PATH = Path(__file__).parent.parent / "strategy" / "content_strategy.json"


def create_gumroad_product(title: str, description: str, price_cents: int,
                            file_path: Path, token: str) -> dict:
    """Gumroad에 디지털 상품을 생성하고 파일을 첨부합니다."""

    # 1. 상품 생성
    r = requests.post(f"{GUMROAD_API}/products", data={
        "access_token": token,
        "name": title,
        "description": description,
        "price": price_cents,
        "published": "true",
        "custom_summary": description[:255],
    }, timeout=30)

    if r.status_code not in (200, 201):
        raise RuntimeError(f"Gumroad 상품 생성 실패: {r.status_code} {r.text[:300]}")

    product_data = r.json().get("product", {})
    product_id   = product_data.get("id", "")
    product_url  = product_data.get("short_url", "")
    print(f"  ✓ 상품 생성: {product_url}")

    # 2. 파일 첨부 (PDF/TXT)
    if file_path.exists():
        with open(file_path, "rb") as f:
            mime = "text/html" if file_path.suffix == ".html" else "text/plain"
            attach = requests.put(
                f"{GUMROAD_API}/products/{product_id}/files",
                data={"access_token": token},
                files={"file": (file_path.name, f, mime)},
                timeout=60,
            )
            if attach.status_code in (200, 201):
                print(f"  ✓ 파일 첨부: {file_path.name}")
            else:
                print(f"  ⚠ 파일 첨부 실패: {attach.status_code}")

    return {"id": product_id, "url": product_url, "title": title}


def build_description(product: dict) -> str:
    """Gumroad 상품 설명을 구성합니다."""
    base = product.get("description") or product.get("subtitle", "")
    return f"""{base}

━━━━━━━━━━━━━━━━━━━━━━━━
✅ Instant digital download
✅ Practical, actionable content
✅ Based on real AI income strategies

📌 From the AI Income Daily YouTube channel
🔔 Subscribe for free daily tips: youtube.com/@AIIncomeDaily
━━━━━━━━━━━━━━━━━━━━━━━━
30-day money-back guarantee — no questions asked."""


def record_product(product_info: dict):
    """생성된 상품을 strategy.json에 기록합니다."""
    strategy = json.loads(STRATEGY_PATH.read_text())
    created = strategy.get("gumroad_products_created", [])
    created.append({
        "title":      product_info["title"],
        "url":        product_info.get("url", ""),
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "price_usd":  product_info.get("price_usd", 0),
    })
    strategy["gumroad_products_created"] = created
    STRATEGY_PATH.write_text(json.dumps(strategy, indent=2, ensure_ascii=False))


def run():
    from dotenv import load_dotenv
    load_dotenv()

    token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
    if not token:
        print("  ⚠ GUMROAD_ACCESS_TOKEN 없음 — 등록 스킵")
        print("  → gumroad.com/settings/advanced 에서 토큰 발급 후 GitHub Secrets에 추가")
        return None

    # 가장 최근 생성된 상품 메타 찾기
    meta_files = sorted(OUTPUT_DIR.glob("*_meta.json"), reverse=True)
    if not meta_files:
        print("  ✗ 상품 메타 파일 없음 — auto_product.py 먼저 실행 필요")
        return None

    meta = json.loads(meta_files[0].read_text())
    title = meta["title"]
    price_cents = meta.get("price_usd", 17) * 100

    # 대응하는 상품 파일 찾기
    stem = meta_files[0].stem.replace("_meta", "")
    product_file = None
    for ext in [".html", ".txt"]:
        candidate = OUTPUT_DIR / (stem + ext)
        if candidate.exists():
            product_file = candidate
            break

    print(f"\n🛍️  Gumroad 등록: '{title}' (${meta.get('price_usd', 17)})")

    description = build_description(meta)

    try:
        result = create_gumroad_product(title, description, price_cents, product_file or Path(""), token)
        result["price_usd"] = meta.get("price_usd", 17)
        record_product(result)
        print(f"\n✅ Gumroad 등록 완료!")
        print(f"   판매 링크: {result.get('url', 'N/A')}")
        return result
    except Exception as e:
        print(f"  ✗ 등록 실패: {e}")
        return None


if __name__ == "__main__":
    run()
