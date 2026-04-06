#!/usr/bin/env python3
"""
로컬 웹훅 테스트 스크립트.
서버가 실행 중인 상태에서 실행: uvicorn main:app --reload

사용법:
  python test_webhook.py            # 전체 시나리오 순서대로 실행
  python test_webhook.py add        # 키워드 추가만
  python test_webhook.py list       # 키워드 목록만
  python test_webhook.py search     # 즉시 검색만
"""

import sys
import json
import requests

BASE = "http://localhost:8000/kakao"
TEST_USER = "test_user_local_001"


def kakao_body(block_name: str, utterance: str, params: dict | None = None) -> dict:
    return {
        "intent": {"id": "test", "name": block_name},
        "userRequest": {
            "timezone": "Asia/Seoul",
            "block": {"id": "test_block", "name": block_name},
            "utterance": utterance,
            "lang": "ko",
            "user": {
                "id": TEST_USER,
                "type": "botUserKey",
                "properties": {},
            },
        },
        "bot": {"id": "test_bot", "name": "나봇"},
        "action": {
            "name": block_name,
            "clientExtra": None,
            "params": params or {},
            "id": "test_action",
            "detailParams": {},
        },
    }


def post(endpoint: str, body: dict) -> dict:
    resp = requests.post(f"{BASE}{endpoint}", json=body, timeout=10)
    resp.raise_for_status()
    return resp.json()


def print_response(label: str, data: dict):
    outputs = data.get("template", {}).get("outputs", [])
    text = outputs[0].get("simpleText", {}).get("text", "") if outputs else ""
    replies = data.get("template", {}).get("quickReplies", [])
    print(f"\n{'='*50}")
    print(f"[{label}]")
    print(f"{'='*50}")
    print(text)
    if replies:
        print("\n빠른답장:", [r["label"] for r in replies])


def test_main():
    data = post("/webhook/main", kakao_body("메인", "시작"))
    print_response("메인 메뉴", data)


def test_add_keyword_exact():
    body = kakao_body(
        "키워드추가",
        "소음발광",
        params={"term": "소음발광", "exact_match": "true", "exclude_words": ""},
    )
    data = post("/webhook/add-keyword", body)
    print_response("키워드 추가 (소음발광, 완전일치)", data)


def test_add_keyword_with_exclude():
    body = kakao_body(
        "키워드추가",
        "솜발",
        params={
            "term": "솜발",
            "exact_match": "true",
            "exclude_words": "고양이,냥이,발바닥,집사,펫",
        },
    )
    data = post("/webhook/add-keyword", body)
    print_response("키워드 추가 (솜발, 제외어: 고양이 등)", data)


def test_list_keywords():
    data = post("/webhook/list-keywords", kakao_body("목록", "내 키워드"))
    print_response("키워드 목록", data)


def test_search_now():
    data = post("/webhook/search-now", kakao_body("즉시검색", "지금 검색해줘"))
    print_response("즉시 검색", data)


def test_upgrade():
    data = post("/webhook/upgrade", kakao_body("업그레이드", "업그레이드"))
    print_response("업그레이드 안내", data)


def test_keyword_limit():
    """무료 플랜 2개 초과 시 업그레이드 안내 확인."""
    for i in range(3):
        body = kakao_body(
            "키워드추가",
            f"테스트키워드{i}",
            params={"term": f"테스트키워드{i}", "exact_match": "true", "exclude_words": ""},
        )
        data = post("/webhook/add-keyword", body)
        text = data.get("template", {}).get("outputs", [{}])[0].get("simpleText", {}).get("text", "")
        print(f"\n[키워드 {i+1}번째 추가] {text[:60]}...")


SCENARIOS = {
    "main": test_main,
    "add": test_add_keyword_exact,
    "add_exclude": test_add_keyword_with_exclude,
    "list": test_list_keywords,
    "search": test_search_now,
    "upgrade": test_upgrade,
    "limit": test_keyword_limit,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "all":
        print("전체 시나리오 실행...\n")
        test_main()
        test_add_keyword_exact()
        test_add_keyword_with_exclude()
        test_list_keywords()
        test_search_now()
        test_upgrade()
    elif cmd in SCENARIOS:
        SCENARIOS[cmd]()
    else:
        print(f"사용 가능한 명령: all, {', '.join(SCENARIOS.keys())}")
        sys.exit(1)
