"""
플랜별 검색 주기:
  free     → 6시간 (일 4회)
  standard → 1시간
  pro      → 30분
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from db import crud
from db.crud import all_active_keywords
from services.search import search_all
from services.notify import send_to_user

log = logging.getLogger("nabot.scheduler")

# 플랜별 검색 주기 (분)
PLAN_INTERVALS: dict[str, int] = {
    "free": 360,       # 6시간
    "standard": 60,    # 1시간
    "pro": 30,         # 30분
}

# 플랜별 검색 소스
PLAN_SOURCES: dict[str, list[str]] = {
    "free": ["naver", "google"],
    "standard": ["naver", "google", "twitter"],
    "pro": ["naver", "google", "twitter"],
}


async def run_search_for_plan(plan: str):
    """특정 플랜 유저의 키워드를 검색하고 새 언급을 알림."""
    keywords = [kw for kw in all_active_keywords() if kw["plan"] == plan]
    if not keywords:
        return

    sources = PLAN_SOURCES[plan]
    log.info(f"[{plan}] {len(keywords)}개 키워드 검색 시작")

    # 유저별로 그룹화
    by_user: dict[str, list[dict]] = {}
    for kw in keywords:
        by_user.setdefault(kw["kakao_user_key"], []).append(kw)

    for user_key, user_keywords in by_user.items():
        for kw in user_keywords:
            try:
                results = search_all(kw["term"], kw["exclude_words"], kw["exact_match"], sources)
                new_results = [r for r in results if not crud.is_seen(r["url"], user_key)]
                if new_results:
                    for r in new_results:
                        crud.mark_seen(r["url"], user_key)
                    send_to_user(user_key, kw["term"], new_results)
                    log.info(f"  '{kw['term']}' → {user_key}: {len(new_results)}건 알림")
            except Exception as e:
                log.error(f"  '{kw['term']}' 검색 오류: {e}")

    crud.purge_old_seen(days=90)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    for plan, interval_minutes in PLAN_INTERVALS.items():
        scheduler.add_job(
            run_search_for_plan,
            trigger=IntervalTrigger(minutes=interval_minutes),
            args=[plan],
            id=f"search_{plan}",
            name=f"Search [{plan}] every {interval_minutes}min",
            replace_existing=True,
        )
        log.info(f"스케줄 등록: {plan} → {interval_minutes}분 간격")

    return scheduler
