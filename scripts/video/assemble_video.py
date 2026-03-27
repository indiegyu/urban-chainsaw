"""
Phase 3 – YouTube 자동화: 영상 조립
=====================================
ElevenLabs 음성 합성 + FFmpeg 기반 영상 조립

파이프라인:
  1. Groq → 스크립트 생성 (assemble_video.py 호출 전에 완료)
  2. ElevenLabs → 스크립트를 MP3 음성으로 변환
  3. Pexels API → 키워드에 맞는 무료 스톡 영상 다운로드
  4. FFmpeg → 영상 + 음성 + 자막 합병
  5. Ideogram → 썸네일 이미지 생성

무료 도구:
  - ElevenLabs 무료 티어 (10,000 chars/월)
  - Pexels API (무료, 무제한)
  - FFmpeg (오픈소스)
  - Ideogram.ai (무료 티어)

필수 환경변수:
  ELEVENLABS_API_KEY=...
  PEXELS_API_KEY=...       # https://www.pexels.com/api/ (무료 가입)
  IDEOGRAM_API_KEY=...
  GROQ_API_KEY=...
"""

import os
import json
import time
import subprocess
import tempfile
import requests
from pathlib import Path

# ── 설정 ─────────────────────────────────────────────────────────────────────
ELEVENLABS_API  = "https://api.elevenlabs.io/v1"
PEXELS_API      = "https://api.pexels.com/videos"
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
GROQ_API        = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL      = "llama-3.3-70b-versatile"

OUTPUT_DIR      = Path(__file__).parent / "output"
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel – 자연스러운 여성 목소리 (무료)
VIDEO_RESOLUTION    = "854x480"    # 480p - GitHub Actions 2-core에서 빠른 인코딩
TARGET_DURATION_SEC = 480  # 8분 = YouTube 광고 수익 최적


# ── 1. 스크립트 자동 생성 (Groq) ─────────────────────────────────────────────
def _groq_post(headers: dict, messages: list, temperature: float = 0.8) -> str:
    resp = requests.post(
        GROQ_API,
        headers=headers,
        json={"model": GROQ_MODEL, "messages": messages, "temperature": temperature},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _parse_json(text: str) -> dict:
    """마크다운 코드블록 제거 후 JSON 파싱."""
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def generate_script(topic: str, groq_api_key: str) -> dict:
    """8분 분량의 YouTube 스크립트를 생성합니다. (2-step: JSON 메타 + 스크립트 텍스트 분리)"""
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}

    # Step 1: JSON 메타데이터만 요청 (script 제외 → 개행문자 JSON 파싱 오류 방지)
    meta = _parse_json(_groq_post(headers, [
        {"role": "system", "content": (
            "You are a YouTube scriptwriter. Output ONLY valid JSON with these keys: "
            "title (max 70 chars), description (200 words), "
            "tags (list of 15 strings), keywords (list of 5 visual search words), "
            "thumbnail_text (short 3-5 word text for thumbnail). "
            "No markdown, no extra text, just JSON."
        )},
        {"role": "user", "content": f"Topic: {topic}"},
    ]))

    # Step 2: 스크립트 텍스트만 plain text로 요청
    script = _groq_post(headers, [
        {"role": "system", "content": (
            "You are a YouTube scriptwriter. Write a 1000-1200 word narration script "
            "for a faceless YouTube channel. No stage directions, no JSON, just the spoken text."
        )},
        {"role": "user", "content": f"Topic: {topic}"},
    ])

    meta["script"] = script
    return meta


# ── 2. 음성 합성 (ElevenLabs) ────────────────────────────────────────────────
def synthesize_voice(text: str, api_key: str, output_path: Path) -> Path:
    """스크립트 텍스트를 MP3 음성으로 변환합니다.
    ElevenLabs → gTTS(완전 무료) 순으로 시도합니다."""
    # ElevenLabs 시도 (유료 플랜 or 개인 IP에서 사용)
    if api_key and not api_key.startswith("sk_c978"):  # 테스트 키는 서버 IP 차단됨
        if len(text) > 9500:
            text = text[:9500]
        try:
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }
            payload = {
                "text": text,
                "model_id": "eleven_flash_v2_5",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            }
            resp = requests.post(
                f"{ELEVENLABS_API}/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            if resp.content[:3] == b'ID3' or resp.content[:2] in [b'\xff\xfb', b'\xff\xf3']:
                output_path.write_bytes(resp.content)
                print(f"  ✓ ElevenLabs voice: {output_path.name}")
                return output_path
        except Exception as e:
            print(f"  ⚠ ElevenLabs failed ({e}), using gTTS...")

    # gTTS 폴백 (완전 무료, 서버 IP 무관하게 작동)
    return _gtts_synthesize(text, output_path)


def _gtts_synthesize(text: str, output_path: Path) -> Path:
    """gTTS로 음성 합성 (완전 무료, 무제한)."""
    from gtts import gTTS
    mp3_path = output_path.with_suffix(".mp3")
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(str(mp3_path))
    print(f"  ✓ gTTS voice: {mp3_path.name}")
    return mp3_path


# ── 3. 스톡 영상 다운로드 (Pexels) ──────────────────────────────────────────
def download_stock_videos(keywords: list[str], api_key: str, output_dir: Path,
                           count_per_keyword: int = 2) -> list[Path]:
    """Pexels에서 무료 스톡 영상을 다운로드합니다."""
    headers = {"Authorization": api_key}
    video_paths = []

    for keyword in keywords:
        params = {"query": keyword, "per_page": count_per_keyword, "orientation": "landscape"}
        resp = requests.get(f"{PEXELS_API}/search", headers=headers, params=params, timeout=15)
        resp.raise_for_status()

        for video in resp.json().get("videos", []):
            # HD 화질 파일 선택
            hd_files = [f for f in video["video_files"] if f.get("quality") == "hd"]
            if not hd_files:
                hd_files = video["video_files"][:1]
            if not hd_files:
                continue

            file_url  = hd_files[0]["link"]
            safe_name = keyword.replace(" ", "_")[:20]
            vid_path  = output_dir / f"stock_{safe_name}_{video['id']}.mp4"

            if not vid_path.exists():
                vid_resp = requests.get(file_url, timeout=60, stream=True)
                vid_resp.raise_for_status()
                with open(vid_path, "wb") as f:
                    for chunk in vid_resp.iter_content(chunk_size=8192):
                        f.write(chunk)

            video_paths.append(vid_path)
            print(f"  ✓ Stock video: {vid_path.name}")

    return video_paths


# ── 4. 영상 조립 (FFmpeg) ────────────────────────────────────────────────────
def assemble_video(video_paths: list[Path], audio_path: Path,
                   output_path: Path) -> Path:
    """FFmpeg으로 스톡 영상들을 이어붙이고 음성을 합성합니다."""
    if not video_paths:
        raise ValueError("No stock videos to assemble.")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as concat_file:
        for vp in video_paths:
            concat_file.write(f"file '{vp.resolve()}'\n")
        concat_path = concat_file.name

    try:
        # Step 1: 스톡 영상 빠르게 연결 (재인코딩 없이 copy 모드)
        # 다른 해상도 파일이 있을 수 있으므로 먼저 첫 번째를 기준으로 스케일
        merged_path = output_path.parent / "merged_raw.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_path,
            "-c:v", "libx264", "-crf", "32", "-preset", "ultrafast",
            "-vf", f"scale={VIDEO_RESOLUTION},setsar=1,fps=24",
            "-c:a", "copy", "-an",
            "-threads", "0",
            str(merged_path)
        ], check=True, capture_output=True, timeout=1800)

        # Step 2: merged 영상 루프 + 음성 합성
        subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(merged_path),
            "-i", str(audio_path),
            "-c:v", "copy",          # 영상은 copy (이미 인코딩됨)
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-map", "0:v:0", "-map", "1:a:0",
            str(output_path)
        ], check=True, capture_output=True, timeout=300)

        print(f"  ✓ Video assembled: {output_path.name}")
        return output_path

    finally:
        Path(concat_path).unlink(missing_ok=True)
        merged_path.unlink(missing_ok=True)


# ── 5. 썸네일 생성 (PIL – 완전 로컬, 외부 API 불필요) ───────────────────────
def generate_thumbnail(prompt: str, api_key: str, output_path: Path) -> Path:
    """PIL로 YouTube 최적화 썸네일(1280×720)을 생성합니다 (외부 API 불필요)."""
    import textwrap
    from PIL import Image, ImageDraw, ImageFont

    title = prompt[:80]
    img  = Image.new("RGB", (1280, 720), color=(26, 26, 46))
    draw = ImageDraw.Draw(img)

    # 사이드 바 강조
    draw.rectangle([0, 0, 18, 720], fill=(233, 69, 96))
    draw.rectangle([1262, 0, 1280, 720], fill=(233, 69, 96))
    draw.rectangle([0, 0, 1280, 12], fill=(233, 69, 96))
    draw.rectangle([0, 708, 1280, 720], fill=(233, 69, 96))

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 88)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except Exception:
        font_big = font_sub = ImageFont.load_default()

    lines = textwrap.wrap(title.upper(), width=22)
    y = 720 // 2 - len(lines) * 100 // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_big)
        x = (1280 - (bbox[2] - bbox[0])) // 2
        draw.text((x + 3, y + 3), line, font=font_big, fill=(233, 69, 96))  # 그림자
        draw.text((x, y), line, font=font_big, fill=(255, 255, 255))
        y += 105

    output_path = output_path.with_suffix(".jpg")
    img.save(str(output_path), "JPEG", quality=95)
    print(f"  ✓ Thumbnail: {output_path.name}")
    return output_path


# ── 메인 실행 ────────────────────────────────────────────────────────────────
def run(topic: str):
    from dotenv import load_dotenv
    load_dotenv()
    groq_key       = os.environ["GROQ_API_KEY"]
    elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
    pexels_key     = os.environ["PEXELS_API_KEY"]

    from datetime import datetime
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir = OUTPUT_DIR / ts
    dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎬 Producing video: '{topic}'")

    # 1. 스크립트
    print("\n[1/5] Generating script...")
    meta = generate_script(topic, groq_key)
    (dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    # 2. 음성 합성
    print("\n[2/5] Synthesizing voice...")
    audio_path = synthesize_voice(meta["script"], elevenlabs_key, dir / "voice.mp3")

    # 3. 스톡 영상
    print("\n[3/5] Downloading stock footage...")
    video_paths = download_stock_videos(meta["keywords"], pexels_key, dir)

    # 4. 영상 조립
    print("\n[4/5] Assembling video...")
    final_video = assemble_video(video_paths, audio_path, dir / "final.mp4")

    # 5. 썸네일 (Pollinations.ai – 무료)
    print("\n[5/5] Generating thumbnail...")
    thumbnail = generate_thumbnail(meta["thumbnail_prompt"], "", dir / "thumbnail.jpg")

    print(f"\n✅ Video ready: {dir}")
    print(f"   Title: {meta['title']}")
    return {"dir": str(dir), "meta": meta, "video": str(final_video), "thumbnail": str(thumbnail)}


if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "10 AI tools that will change your life in 2026"
    run(topic)
