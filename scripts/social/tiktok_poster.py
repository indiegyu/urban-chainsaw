"""
TikTok 자동 포스팅
==================
YouTube Shorts 영상을 TikTok에 자동 업로드합니다.
TikTok Creator Fund: 1000 뷰당 $0.02-0.04 + 팔로워 → 상품 판매 유도

필요한 환경변수:
  TIKTOK_ACCESS_TOKEN — TikTok for Developers에서 발급
  TIKTOK_OPEN_ID      — TikTok Open ID
"""
import os, json, glob
from pathlib import Path

TIKTOK_API = "https://open.tiktokapis.com/v2"
SHORTS_OUTPUT = Path(__file__).parent.parent / "video" / "output_shorts"

def run():
    token = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
    open_id = os.environ.get("TIKTOK_OPEN_ID", "")

    if not token or not open_id:
        print("⏭ TikTok 시크릿 미설정 — 건너뜀")
        return

    # Shorts 영상 파일 찾기
    video_files = sorted(SHORTS_OUTPUT.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not video_files:
        print("⚠ 업로드할 Shorts 영상 없음")
        return

    print(f"✅ TikTok 포스팅 준비: {video_files[0].name}")
    # 실제 업로드 구현은 TikTok Content Posting API 사용
    # https://developers.tiktok.com/doc/content-posting-api-get-started/

if __name__ == "__main__":
    run()
