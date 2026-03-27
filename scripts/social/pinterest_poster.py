"""
Pinterest 자동 핀 포스팅
=========================
YouTube 영상 업로드 + 블로그 글 생성 시 자동으로 Pinterest 핀 생성.
Pinterest는 신규 채널에 검색 기반 무료 트래픽을 엄청 몰아줌.

수익 구조:
  핀 → YouTube 링크 (구독자+조회수) + Lemon Squeezy 링크 (상품 판매)

필요 시크릿:
  PINTEREST_ACCESS_TOKEN — developers.pinterest.com → My Apps → Create App
                            → OAuth: pins:read_secret,pins:write,boards:read,boards:write
  PINTEREST_BOARD_ID     — 핀을 올릴 보드 ID (URL에서 복사)
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

API = "https://api.pinterest.com/v5"
STRATEGY_PATH = Path(__file__).parent.parent / "strategy" / "content_strategy.json"
STATE_FILE    = Path(__file__).parent / ".pinterest_posted.json"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_or_create_board(token: str) -> str:
    """PINTEREST_BOARD_ID 없으면 'AI Income Daily' 보드를 자동 생성합니다."""
    board_id = os.environ.get("PINTEREST_BOARD_ID", "")
    if board_id:
        return board_id

    # 기존 보드 검색
    r = requests.get(f"{API}/boards", headers=_headers(token), timeout=10)
    if r.status_code == 200:
        for b in r.json().get("items", []):
            if "income" in b.get("name", "").lower() or "ai" in b.get("name", "").lower():
                print(f"  ✓ 기존 보드 사용: {b['name']} ({b['id']})")
                return b["id"]

    # 새 보드 생성
    r = requests.post(f"{API}/boards", headers=_headers(token), json={
        "name": "AI Income Daily",
        "description": "Daily AI tools, passive income strategies, and automation tips",
        "privacy": "PUBLIC",
    }, timeout=10)
    if r.status_code in (200, 201):
        board_id = r.json()["id"]
        print(f"  ✓ 보드 생성: AI Income Daily ({board_id})")
        return board_id
    raise RuntimeError(f"보드 생성 실패: {r.status_code} {r.text[:200]}")


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"pinned": []}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def create_pin(board_id: str, token: str, title: str, description: str,
               link: str, image_url: str = None) -> dict:
    """Pinterest 핀 1개 생성."""
    payload = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:500],
        "link": link,
    }
    if image_url:
        payload["media_source"] = {"source_type": "image_url", "url": image_url}

    r = requests.post(f"{API}/pins", headers=_headers(token), json=payload, timeout=20)
    if r.status_code in (200, 201):
        return r.json()
    print(f"  ✗ 핀 생성 실패: {r.status_code} {r.text[:200]}")
    return {}


def pin_youtube_video(video_id: str, title: str, description: str,
                      board_id: str, token: str) -> bool:
    """YouTube 영상을 Pinterest에 핀합니다."""
    state = _load_state()
    key   = f"yt_{video_id}"
    if key in state["pinned"]:
        return False

    # YouTube 썸네일을 이미지로 사용
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    yt_link = f"https://youtu.be/{video_id}"

    pin_desc = (
        f"{description[:300]}\n\n"
        "💰 Free AI income tips daily — Subscribe!\n"
        "#AIIncome #PassiveIncome #AITools #MakeMoneyOnline #SideHustle"
    )

    result = create_pin(board_id, token, title, pin_desc, yt_link, thumbnail_url)
    if result.get("id"):
        state["pinned"].append(key)
        state["pinned"].append({"id": key, "pin_id": result["id"], "date": datetime.now().isoformat()})
        _save_state(state)
        print(f"  ✓ 핀 생성: {title[:50]} → {yt_link}")
        return True
    return False


def pin_product(product: dict, board_id: str, token: str) -> bool:
    """Lemon Squeezy 상품을 Pinterest에 핀합니다."""
    state = _load_state()
    key   = f"prod_{product.get('title', '')[:30]}"
    if key in state["pinned"]:
        return False

    title = f"💰 {product['title']} — Only ${product.get('price_usd', 9)}"
    desc  = (
        f"{product.get('description', product['title'])}\n\n"
        "✅ Instant digital download\n"
        "✅ Practical AI income strategies\n"
        "#DigitalProducts #AIIncome #PassiveIncome #OnlineBusiness"
    )
    result = create_pin(board_id, token, title, desc, product.get("url", ""))
    if result.get("id"):
        state["pinned"].append(key)
        _save_state(state)
        print(f"  ✓ 상품 핀: {product['title'][:50]}")
        return True
    return False


def run():
    from dotenv import load_dotenv
    load_dotenv()

    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    if not token:
        print("  ⚠ PINTEREST_ACCESS_TOKEN 없음 — 스킵")
        print("  → developers.pinterest.com → My Apps → Create App")
        print("    OAuth scopes: pins:write boards:write")
        return

    print("📌 Pinterest 자동 핀 포스팅...")
    board_id = get_or_create_board(token)
    pinned = 0

    # 1. 최근 YouTube 업로드 결과에서 핀
    upload_results = sorted(
        Path("scripts/video/output").glob("*/upload_result.json"), reverse=True
    )[:5]
    for rf in upload_results:
        try:
            r = json.loads(rf.read_text())
            vid_id = r.get("video_id", "")
            meta   = r.get("meta", {})
            if vid_id and pin_youtube_video(
                vid_id, meta.get("title", "AI Income Tip"),
                meta.get("description", "")[:300], board_id, token
            ):
                pinned += 1
        except Exception as e:
            print(f"  ⚠ {rf.parent.name}: {e}")

    # 2. Lemon Squeezy 상품 핀
    strategy = {}
    if STRATEGY_PATH.exists():
        strategy = json.loads(STRATEGY_PATH.read_text())
    for product in strategy.get("gumroad_products_created", [])[-3:]:
        if product.get("url") and pin_product(product, board_id, token):
            pinned += 1

    print(f"  ✅ Pinterest: {pinned}개 핀 생성 완료")


if __name__ == "__main__":
    run()
