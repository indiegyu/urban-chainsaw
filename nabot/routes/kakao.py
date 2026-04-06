"""
카카오 i 오픈빌더 웹훅 핸들러.

오픈빌더에서 각 블록의 "스킬 서버"를 이 서버로 연결해야 합니다.
응답은 반드시 5초 내에 반환해야 합니다 (카카오 제한).

블록 ID 목록 (오픈빌더에서 맞게 설정):
- 메인 메뉴
- 키워드 추가 (term 파라미터)
- 키워드 추가 확인 (exact_match, exclude_words 파라미터)
- 키워드 목록 보기
- 키워드 삭제
- 지금 검색
- 플랜 업그레이드 안내
"""

import os
from fastapi import APIRouter, Request
from db import crud
from services.search import search_all
from services.notify import send_to_user

router = APIRouter(prefix="/kakao")

# 오픈빌더 블록 ID - 오픈빌더에서 블록 생성 후 .env에 설정
# 오픈빌더 > 블록 > 블록 상세 > 우측 상단 블록 ID 복사
BLOCK_MAIN = os.environ.get("BLOCK_MAIN", "BLOCK_MAIN")
BLOCK_ADD_KEYWORD = os.environ.get("BLOCK_ADD_KEYWORD", "BLOCK_ADD_KEYWORD")
BLOCK_LIST_KEYWORDS = os.environ.get("BLOCK_LIST_KEYWORDS", "BLOCK_LIST_KEYWORDS")
BLOCK_SEARCH_NOW = os.environ.get("BLOCK_SEARCH_NOW", "BLOCK_SEARCH_NOW")
BLOCK_UPGRADE = os.environ.get("BLOCK_UPGRADE", "BLOCK_UPGRADE")


# ---------- 응답 빌더 ----------

def simple_text(text: str, quick_replies: list[dict] | None = None) -> dict:
    resp: dict = {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": text}}],
        },
    }
    if quick_replies:
        resp["template"]["quickReplies"] = quick_replies
    return resp


def main_menu_replies() -> list[dict]:
    return [
        {"label": "키워드 추가", "action": "block", "blockId": BLOCK_ADD_KEYWORD},
        {"label": "내 키워드 목록", "action": "block", "blockId": BLOCK_LIST_KEYWORDS},
        {"label": "지금 검색해줘", "action": "block", "blockId": BLOCK_SEARCH_NOW},
        {"label": "플랜 업그레이드", "action": "block", "blockId": BLOCK_UPGRADE},
    ]


def back_to_menu(text: str) -> dict:
    return simple_text(text, quick_replies=main_menu_replies())


# ---------- 공통 파싱 ----------

def extract(body: dict) -> tuple[str, str, dict]:
    """user_key, utterance, action_params"""
    user_key = body["userRequest"]["user"]["id"]
    utterance = body["userRequest"]["utterance"].strip()
    params = body.get("action", {}).get("params", {})
    return user_key, utterance, params


# ---------- 엔드포인트 ----------

@router.post("/webhook/main")
async def webhook_main(request: Request):
    body = await request.json()
    user_key, _, _ = extract(body)
    crud.get_or_create_user(user_key)
    plan = crud.get_user_plan(user_key)
    count = crud.count_keywords(user_key)
    plan_labels = {"free": "무료", "standard": "스탠다드", "pro": "프로"}
    return back_to_menu(
        f"안녕하세요! 나봇 🔍\n나에 대한 인터넷 얘기를 잡아드려요.\n"
        f"현재 플랜: {plan_labels.get(plan, plan)} | 키워드: {count}개 등록됨"
    )


@router.post("/webhook/add-keyword")
async def webhook_add_keyword(request: Request):
    """
    오픈빌더에서 사용자가 키워드를 입력하면 호출.
    params: {term, exact_match, exclude_words}
      - exact_match: "true" | "false"
      - exclude_words: 쉼표 구분 문자열 (없으면 "")
    """
    body = await request.json()
    user_key, _, params = extract(body)
    crud.get_or_create_user(user_key)

    term = params.get("term", "").strip()
    if not term:
        return simple_text("키워드를 입력해주세요.")

    exact_match = params.get("exact_match", "true").lower() != "false"
    exclude_raw = params.get("exclude_words", "")
    exclude_words = [w.strip() for w in exclude_raw.split(",") if w.strip()]

    try:
        crud.add_keyword(user_key, term, exclude_words, exact_match)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("limit:"):
            _, limit, plan = msg.split(":")
            upgrade_msg = (
                f"키워드를 {limit}개까지 등록할 수 있어요 (현재 플랜: {plan}).\n"
                "더 많은 키워드를 등록하려면 업그레이드해주세요!"
            )
            return simple_text(
                upgrade_msg,
                quick_replies=[
                    {"label": "업그레이드", "action": "block", "blockId": BLOCK_UPGRADE},
                    {"label": "돌아가기", "action": "block", "blockId": BLOCK_MAIN},
                ],
            )
        return simple_text(f"오류가 발생했어요: {e}")

    match_label = "완전일치" if exact_match else "유사검색"
    excl_label = f"\n제외어: {', '.join(exclude_words)}" if exclude_words else ""
    return back_to_menu(
        f"✅ '{term}' 키워드가 등록됐어요!\n"
        f"검색 방식: {match_label}{excl_label}\n\n"
        "다음 정기 검색 때 결과를 알려드릴게요."
    )


@router.post("/webhook/list-keywords")
async def webhook_list_keywords(request: Request):
    body = await request.json()
    user_key, _, _ = extract(body)
    crud.get_or_create_user(user_key)

    keywords = crud.list_keywords(user_key)
    if not keywords:
        return back_to_menu("등록된 키워드가 없어요. [키워드 추가]를 눌러 시작해보세요!")

    lines = [f"📋 등록된 키워드 ({len(keywords)}개)\n"]
    for kw in keywords:
        match_label = "완전일치" if kw["exact_match"] else "유사검색"
        excl = f" | 제외: {', '.join(kw['exclude_words'])}" if kw["exclude_words"] else ""
        lines.append(f"• [{kw['id']}] {kw['term']} ({match_label}{excl})")

    lines.append("\n키워드를 삭제하려면 ID를 알려주세요. (예: '삭제 3')")
    return back_to_menu("\n".join(lines))


@router.post("/webhook/delete-keyword")
async def webhook_delete_keyword(request: Request):
    """params: {keyword_id}"""
    body = await request.json()
    user_key, utterance, params = extract(body)

    keyword_id_str = params.get("keyword_id", "").strip()
    if not keyword_id_str:
        # 발화에서 파싱 시도 ("삭제 3" 형태)
        parts = utterance.replace("삭제", "").strip().split()
        keyword_id_str = parts[0] if parts else ""

    try:
        keyword_id = int(keyword_id_str)
    except ValueError:
        return simple_text("삭제할 키워드 번호를 알려주세요. (예: '삭제 3')")

    crud.delete_keyword(user_key, keyword_id)
    return back_to_menu(f"🗑️ 키워드 #{keyword_id}가 삭제됐어요.")


@router.post("/webhook/search-now")
async def webhook_search_now(request: Request):
    """사용자 요청으로 즉시 검색 실행."""
    body = await request.json()
    user_key, _, _ = extract(body)
    crud.get_or_create_user(user_key)

    keywords = crud.list_keywords(user_key)
    if not keywords:
        return back_to_menu("등록된 키워드가 없어요. 먼저 키워드를 추가해주세요!")

    plan = crud.get_user_plan(user_key)
    sources = _sources_for_plan(plan)

    total_new = 0
    for kw in keywords:
        results = search_all(kw["term"], kw["exclude_words"], kw["exact_match"], sources)
        new_results = [r for r in results if not crud.is_seen(r["url"], user_key)]
        for r in new_results:
            crud.mark_seen(r["url"], user_key)
        if new_results:
            send_to_user(user_key, kw["term"], new_results)
            total_new += len(new_results)

    if total_new == 0:
        return back_to_menu("🔍 검색 완료! 새로운 언급은 없었어요.")
    return back_to_menu(f"🔍 검색 완료! 총 {total_new}건의 새 언급을 알려드렸어요.")


@router.post("/webhook/upgrade")
async def webhook_upgrade(request: Request):
    return simple_text(
        "💎 나봇 업그레이드\n"
        "━━━━━━━━━━━━━━━━\n"
        "📦 스탠다드 (월 1,900원)\n"
        "  · 키워드 10개\n"
        "  · 1시간마다 알림\n"
        "  · Twitter 검색 포함\n"
        "  · 유사검색 옵션\n\n"
        "🚀 프로 (월 4,900원)\n"
        "  · 키워드 무제한\n"
        "  · 15~30분마다 알림\n"
        "  · 모든 소스\n"
        "  · 무제한 히스토리\n"
        "━━━━━━━━━━━━━━━━\n"
        "결제 링크는 아래 버튼을 눌러주세요.",
        quick_replies=[
            {"label": "스탠다드 결제", "action": "webLink",
             "webLinkUrl": "https://nabot.kr/pay/standard"},
            {"label": "프로 결제", "action": "webLink",
             "webLinkUrl": "https://nabot.kr/pay/pro"},
            {"label": "돌아가기", "action": "block", "blockId": BLOCK_MAIN},
        ],
    )


# ---------- 내부 트리거 (스케줄러용) ----------

@router.post("/internal/trigger-search")
async def trigger_search(request: Request):
    """스케줄러가 호출하는 내부 엔드포인트. X-Internal-Secret 헤더로 보호."""
    import os
    secret = os.environ.get("INTERNAL_SECRET", "")
    if secret:
        incoming = request.headers.get("X-Internal-Secret", "")
        if incoming != secret:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Forbidden")

    body = await request.json()
    plan_filter = body.get("plan")  # None = 전체
    return {"status": "triggered", "plan": plan_filter}


# ---------- helpers ----------

def _sources_for_plan(plan: str) -> list[str]:
    """
    무료: 네이버만 (Twitter API 쿼터 절약)
    스탠다드+: 네이버 + Google CSE + Twitter
    """
    if plan == "free":
        return ["naver"]
    return ["naver", "google", "twitter"]
