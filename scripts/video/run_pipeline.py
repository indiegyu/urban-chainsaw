"""
YouTube 영상 파이프라인 통합 실행기
=====================================
assemble_video.py + upload_youtube.py 를 순서대로 실행합니다.
ElevenLabs 한도 초과 시 gTTS(완전 무료)로 자동 폴백합니다.

사용법:
  python scripts/video/run_pipeline.py "topic here"
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def run_pipeline(topic: str, upload: bool = False):
    print(f"\n🎬 Pipeline start: '{topic}'")
    print("=" * 60)

    # Step 1: 스크립트 생성 + 음성 + 영상 조립
    result = subprocess.run(
        [sys.executable, "scripts/video/assemble_video.py"] + topic.split(),
        cwd=Path(__file__).parent.parent.parent,
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        print("❌ Video assembly failed.")
        return

    # 최신 output 디렉토리 찾기
    output_base = Path(__file__).parent / "output"
    dirs = sorted(output_base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not dirs:
        print("❌ No output directory found.")
        return

    video_dir = dirs[0]
    print(f"\n✅ Video ready: {video_dir}")

    # Step 2: YouTube 업로드 (선택)
    if upload:
        print("\n📤 Uploading to YouTube...")
        subprocess.run(
            [sys.executable, "scripts/video/upload_youtube.py", str(video_dir)],
            cwd=Path(__file__).parent.parent.parent,
        )
    else:
        # 결과 요약
        meta_file = video_dir / "meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            print(f"\n📋 Video Summary:")
            print(f"   Title: {meta.get('title', 'N/A')}")
            print(f"   Tags: {', '.join(meta.get('tags', [])[:5])}...")
        print(f"\n💡 To upload: python scripts/video/upload_youtube.py {video_dir}")


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "10 ways to make money online in 2026"
    upload = "--upload" in sys.argv
    run_pipeline(topic, upload)
