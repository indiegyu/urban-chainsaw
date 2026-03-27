"""
자동 수익 창출 스케줄러
=======================
이 서버에서 24시간 자동으로 4가지 파이프라인을 실행합니다.

사용법:
  python scripts/scheduler.py           # 포그라운드 실행
  nohup python scripts/scheduler.py &   # 백그라운드 실행 (서버 재시작 유지)

스케줄:
  - 매일 오전 8시: POD 디자인 5개 생성
  - 매일 오전 9시: YouTube 영상 1개 생성 (업로드는 OAuth 인증 후)
  - 매 6시간:      SEO 블로그 포스트 2개 생성
  - 매일 자정:     일일 리포트 생성
"""

import time
import schedule
import subprocess
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

Path("logs").mkdir(exist_ok=True)
Path("reports").mkdir(exist_ok=True)

STATS = {
    "pod_designs": 0,
    "blog_posts": 0,
    "videos": 0,
    "started_at": datetime.now().isoformat(),
}


def run_script(script: str, *args) -> bool:
    """서브스크립트를 실행하고 성공 여부를 반환합니다."""
    cmd = [sys.executable, script] + list(args)
    log.info(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if result.returncode == 0:
            log.info(f"✓ {script} succeeded")
            return True
        else:
            log.error(f"✗ {script} failed:\n{result.stderr[-500:]}")
            return False
    except subprocess.TimeoutExpired:
        log.error(f"✗ {script} timed out after 15 minutes")
        return False
    except Exception as e:
        log.error(f"✗ {script} error: {e}")
        return False


def job_pod():
    """매일 POD 디자인 5개 생성"""
    log.info("=== JOB: POD Design Generation ===")
    if run_script("scripts/pod/generate_designs.py", "5"):
        STATS["pod_designs"] += 5
        # 생성된 디자인 Printify에 등록 (API 키가 있을 때)
        run_script("scripts/pod/create_listing.py")


def job_blog():
    """매 6시간 SEO 블로그 포스트 2개 생성"""
    log.info("=== JOB: Blog Post Generation ===")
    for _ in range(2):
        if run_script("scripts/blog/generate_post.py"):
            STATS["blog_posts"] += 1
        time.sleep(5)


def job_youtube():
    """매일 YouTube 영상 1개 생성 (자동화 모드)"""
    log.info("=== JOB: YouTube Video Production ===")
    if run_script("scripts/video/assemble_video.py"):
        STATS["videos"] += 1
        # YouTube OAuth가 설정된 경우 자동 업로드
        video_dirs = sorted(Path("scripts/video/output").iterdir(),
                            key=lambda p: p.stat().st_mtime, reverse=True)
        if video_dirs:
            token_exists = Path("token.json").exists()
            if token_exists:
                run_script("scripts/video/upload_youtube.py", str(video_dirs[0]))
            else:
                log.warning("YouTube OAuth not set up. Run: python scripts/video/setup_youtube_auth.py")


def job_daily_report():
    """매일 자정 일일 리포트"""
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "stats": STATS,
        "pod_output_count": len(list(Path("scripts/pod/output").glob("*.png"))),
        "blog_output_count": len(list(Path("scripts/blog/output").glob("*.html"))),
        "video_output_count": len(list(Path("scripts/video/output").rglob("final.mp4"))),
    }
    report_path = Path("reports") / f"{report['date']}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    log.info(f"📊 Daily Report:\n{json.dumps(report, indent=2)}")


# ── 스케줄 등록 ──────────────────────────────────────────────────────────────
schedule.every().day.at("08:00").do(job_pod)
schedule.every().day.at("09:00").do(job_youtube)
schedule.every(6).hours.do(job_blog)
schedule.every().day.at("00:00").do(job_daily_report)


def main():
    log.info("🚀 Urban-Chainsaw Scheduler Started")
    log.info("Schedule:")
    log.info("  08:00 – POD design generation (5/day)")
    log.info("  09:00 – YouTube video production")
    log.info("  every 6h – Blog post generation")
    log.info("  00:00 – Daily report")

    # 시작 즉시 첫 실행
    log.info("Running initial jobs now...")
    job_pod()
    job_blog()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
