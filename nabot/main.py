import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from db.models import init_db
from routes.kakao import router as kakao_router
from scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("nabot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작
    init_db()
    log.info("DB 초기화 완료")

    scheduler = create_scheduler()
    scheduler.start()
    log.info("스케줄러 시작")

    yield

    # 종료
    scheduler.shutdown(wait=False)
    log.info("스케줄러 종료")


app = FastAPI(title="나봇 (NaBot)", version="1.0.0", lifespan=lifespan)
app.include_router(kakao_router)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "service": "nabot"})


@app.get("/")
async def root():
    return JSONResponse({
        "service": "나봇 (NaBot)",
        "description": "키워드 언급 알림 서비스",
        "docs": "/docs",
    })
