"""
Phase 1 – Print-on-Demand 리스팅 자동 생성
==========================================
generate_designs.py 가 만든 디자인 JSON을 읽어
Printify → Etsy 에 상품을 자동 등록합니다.

무료 조건:
  - Printify: 무료 가입, 판매 시 원가만 차감
  - Etsy:     리스팅당 $0.20 (첫 40개 무료 크레딧 사용 가능)

필수 환경변수:
  PRINTIFY_API_KEY=...
  ETSY_API_KEY=...
  ETSY_SHOP_ID=...
  PRINTIFY_SHOP_ID=...
"""

import os
import json
import time
import requests
from pathlib import Path

# ── 설정 ─────────────────────────────────────────────────────────────────────
PRINTIFY_BASE    = "https://api.printify.com/v1"
ETSY_BASE        = "https://openapi.etsy.com/v3"

# Printify 제품 블루프린트 ID (무료 공급사 기준)
# 티셔츠: 6 (Bella+Canvas 3001), 머그컵: 70 (Printify Mug 11oz)
BLUEPRINTS = {
    "tshirt": {"blueprint_id": 6,  "print_provider_id": 99, "variant_ids": [36809, 36810, 36811]},
    "mug":    {"blueprint_id": 70, "print_provider_id": 99, "variant_ids": [18109]},
}

# Etsy 판매 가격 (달러)
PRICES = {"tshirt": 24.99, "mug": 19.99}


# ── Printify ─────────────────────────────────────────────────────────────────
def upload_image_to_printify(image_path: str, api_key: str, shop_id: str) -> str:
    """이미지를 Printify에 업로드하고 image_id를 반환합니다."""
    headers = {"Authorization": f"Bearer {api_key}"}
    with open(image_path, "rb") as f:
        files = {"file": (Path(image_path).name, f, "image/png")}
        resp = requests.post(
            f"{PRINTIFY_BASE}/uploads/images.json",
            headers=headers,
            files=files,
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()["id"]


def create_printify_product(meta: dict, image_id: str, product_type: str,
                             api_key: str, shop_id: str) -> str:
    """Printify에 제품을 생성하고 product_id를 반환합니다."""
    bp = BLUEPRINTS[product_type]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "title": meta["title"],
        "description": meta["description"],
        "blueprint_id": bp["blueprint_id"],
        "print_provider_id": bp["print_provider_id"],
        "variants": [
            {"id": vid, "price": int(PRICES[product_type] * 100), "is_enabled": True}
            for vid in bp["variant_ids"]
        ],
        "print_areas": [
            {
                "variant_ids": bp["variant_ids"],
                "placeholders": [
                    {
                        "position": "front",
                        "images": [{"id": image_id, "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}],
                    }
                ],
            }
        ],
    }
    resp = requests.post(
        f"{PRINTIFY_BASE}/shops/{shop_id}/products.json",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def publish_to_etsy(printify_product_id: str, api_key: str, shop_id: str):
    """Printify → Etsy 자동 동기화 (Printify의 publish 기능 사용)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "title":       {"sync": True},
        "description": {"sync": True},
        "images":      {"sync": True},
        "variants":    {"sync": True},
        "tags":        {"sync": True},
        "keyFeatures": {"sync": True},
        "shipping_template": {"sync": True},
    }
    resp = requests.post(
        f"{PRINTIFY_BASE}/shops/{shop_id}/products/{printify_product_id}/publish.json",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()


# ── 메인 실행 ────────────────────────────────────────────────────────────────
def run(output_dir: str = "scripts/pod/output"):
    printify_key = os.environ["PRINTIFY_API_KEY"]
    printify_shop = os.environ["PRINTIFY_SHOP_ID"]
    etsy_shop    = os.environ["ETSY_SHOP_ID"]

    output_path = Path(output_dir)
    meta_files  = sorted(output_path.glob("*.json"))

    if not meta_files:
        print(f"No design JSON files found in {output_path}")
        return

    print(f"Found {len(meta_files)} designs to list...")

    for meta_file in meta_files:
        img_file = meta_file.with_suffix(".png")
        if not img_file.exists():
            print(f"  ✗ Image not found: {img_file.name}, skipping.")
            continue

        with open(meta_file) as f:
            meta = json.load(f)

        print(f"\nListing: {meta['title'][:60]}...")

        try:
            # 1. Printify에 이미지 업로드
            print("  → Uploading image to Printify...")
            image_id = upload_image_to_printify(str(img_file), printify_key, printify_shop)

            # 2. 티셔츠 + 머그컵 두 종류 동시 등록
            for product_type in ["tshirt", "mug"]:
                print(f"  → Creating {product_type} product...")
                product_id = create_printify_product(
                    meta, image_id, product_type, printify_key, printify_shop
                )
                print(f"  → Publishing to Etsy...")
                publish_to_etsy(product_id, printify_key, printify_shop)
                print(f"  ✓ {product_type} listed (Printify ID: {product_id})")
                time.sleep(1)

        except requests.HTTPError as e:
            print(f"  ✗ HTTP Error: {e.response.status_code} – {e.response.text[:200]}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print("\nAll designs processed.")


if __name__ == "__main__":
    import sys
    directory = sys.argv[1] if len(sys.argv) > 1 else "scripts/pod/output"
    run(directory)
