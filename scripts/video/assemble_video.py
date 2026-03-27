"""
Phase 3 – YouTube 자동화: 영상 조립 (이미지+오디오 루프 방식)
=============================================================
Groq 스크립트 → gTTS 음성 → PIL 썸네일 → FFmpeg 이미지 루프 합병

파이프라인 (3단계, ~2분 내 완료):
  1. Groq → 스크립트 + 메타데이터 생성
  2. gTTS → 음성 합성 (ElevenLabs 없이도 작동)
  3. PIL 썸네일 + FFmpeg 이미지-오디오 루프 → final.mp4

핵심 설계:
  - 스톡 영상 다운로드 없음 → GitHub Actions 60분 내 완료
  - FFmpeg -loop 1 방식: 썸네일 이미지를 오디오 길이만큼 반복
  - 480p, ultrafast preset으로 인코딩 속도 최적화

필수 환경변수:
  GROQ_API_KEY=...
  ELEVENLABS_API_KEY=... (선택 – 없으면 gTTS 사용)
"""

import os
import json
import subprocess
import requests
from pathlib import Path

GROQ_API   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

ELEVENLABS_API      = "https://api.elevenlabs.io/v1"
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel

OUTPUT_DIR       = Path(__file__).parent / "output"
VIDEO_RESOLUTION = "854x480"   # 480p – 빠른 인코딩


# ── 1. 스크립트 생성 (Groq) ──────────────────────────────────────────────────
def _groq_post(headers: dict, messages: list, temperature: float = 0.8,
               max_tokens: int = 4096) -> str:
    resp = requests.post(
        GROQ_API,
        headers=headers,
        json={"model": GROQ_MODEL, "messages": messages,
              "temperature": temperature, "max_tokens": max_tokens},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def generate_script(topic: str, groq_api_key: str) -> dict:
    """2-step 방식: JSON 메타 + plain text 스크립트 분리."""
    import re
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}

    # Step 1: JSON 메타데이터만 (script 없음 → 파싱 오류 방지)
    meta_raw = _groq_post(headers, [
        {"role": "system", "content": (
            "Output ONLY valid JSON (no markdown, no code blocks) with keys: "
            "title (max 70 chars), description (200 words), "
            "tags (list of 15 strings), thumbnail_text (3-5 word phrase)."
        )},
        {"role": "user", "content": f"Topic: {topic}"},
    ], max_tokens=500)
    meta_raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', meta_raw)
    if "```" in meta_raw:
        meta_raw = meta_raw.split("```")[1].lstrip("json").strip()
    meta = json.loads(meta_raw)

    # Step 2: 스크립트 plain text
    script = _groq_post(headers, [
        {"role": "system", "content": (
            "Write a 900-1100 word spoken narration for a faceless YouTube channel. "
            "Engaging, conversational, no stage directions, no JSON, just the spoken text."
        )},
        {"role": "user", "content": f"Topic: {topic}"},
    ], max_tokens=2000)
    meta["script"] = script
    return meta


# ── 2. 음성 합성 (ElevenLabs → gTTS 폴백) ───────────────────────────────────
def synthesize_voice(text: str, api_key: str, output_path: Path) -> Path:
    if api_key:
        try:
            chunk = text[:9500]
            resp = requests.post(
                f"{ELEVENLABS_API}/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={"xi-api-key": api_key, "Accept": "audio/mpeg",
                         "Content-Type": "application/json"},
                json={"text": chunk, "model_id": "eleven_flash_v2_5",
                      "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
                timeout=120,
            )
            resp.raise_for_status()
            if resp.content[:3] == b'ID3' or resp.content[:2] in [b'\xff\xfb', b'\xff\xf3']:
                output_path.write_bytes(resp.content)
                print(f"  ✓ ElevenLabs voice: {output_path.name}")
                return output_path
        except Exception as e:
            print(f"  ⚠ ElevenLabs failed ({e}), using gTTS...")

    return _gtts_synthesize(text, output_path)


def _gtts_synthesize(text: str, output_path: Path) -> Path:
    from gtts import gTTS
    mp3_path = output_path.with_suffix(".mp3")
    gTTS(text=text[:5000], lang="en", slow=False).save(str(mp3_path))
    print(f"  ✓ gTTS voice: {mp3_path.name}")
    return mp3_path


# ── 3. 썸네일 생성 (PIL) ─────────────────────────────────────────────────────
def generate_thumbnail(text: str, output_path: Path) -> Path:
    import textwrap
    from PIL import Image, ImageDraw, ImageFont

    img  = Image.new("RGB", (1280, 720), color=(26, 26, 46))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, 18, 720],   fill=(233, 69, 96))
    draw.rectangle([1262, 0, 1280, 720], fill=(233, 69, 96))
    draw.rectangle([0, 0, 1280, 12],  fill=(233, 69, 96))
    draw.rectangle([0, 708, 1280, 720], fill=(233, 69, 96))

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 88)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except Exception:
        font_big = font_sub = ImageFont.load_default()

    lines = textwrap.wrap(text.upper(), width=22)
    y = 720 // 2 - len(lines) * 100 // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_big)
        x = (1280 - (bbox[2] - bbox[0])) // 2
        draw.text((x + 3, y + 3), line, font=font_big, fill=(233, 69, 96))
        draw.text((x, y),         line, font=font_big, fill=(255, 255, 255))
        y += 105

    # 하단 채널 태그
    tag = "AI Income Daily"
    tb = draw.textbbox((0, 0), tag, font=font_sub)
    draw.text(((1280 - (tb[2] - tb[0])) // 2, 640), tag,
              font=font_sub, fill=(150, 150, 200))

    out = output_path.with_suffix(".jpg")
    img.save(str(out), "JPEG", quality=95)
    print(f"  ✓ Thumbnail: {out.name}")
    return out


# ── 4. 이미지+오디오 루프로 영상 조립 (FFmpeg) ──────────────────────────────
def assemble_video(thumbnail_path: Path, audio_path: Path, output_path: Path) -> Path:
    """썸네일 이미지를 오디오 길이만큼 루프해서 영상을 만듭니다.
    스톡 영상 다운로드 없이 수 초 내에 완료됩니다."""
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(thumbnail_path),
        "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-vf", f"scale={VIDEO_RESOLUTION},format=yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        "-threads", "0",
        str(output_path),
    ], check=True, capture_output=True, timeout=300)
    print(f"  ✓ Video assembled: {output_path.name}")
    return output_path


# ── 메인 실행 ────────────────────────────────────────────────────────────────
def run(topic: str = None):
    from dotenv import load_dotenv
    from datetime import datetime
    import random

    load_dotenv()
    groq_key   = os.environ["GROQ_API_KEY"]
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "")

    if not topic:
        topics = [
            "5 AI tools that will make you $1000 per month",
            "How to build passive income with AI automation in 2026",
            "10 side hustles you can start with ChatGPT today",
            "YouTube automation: how to make money without showing your face",
            "AI print on demand business: $0 to $3000/month guide",
            "Passive income ideas that actually work in 2026",
            "How I automated my income with GitHub Actions and AI",
            "Best free AI tools for making money online",
        ]
        topic = random.choice(topics)

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir = OUTPUT_DIR / ts
    dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎬 Producing video: '{topic}'")

    # 1. 스크립트
    print("\n[1/3] Generating script...")
    meta = generate_script(topic, groq_key)
    (dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"  ✓ Title: {meta['title'][:60]}")

    # 2. 음성 합성
    print("\n[2/3] Synthesizing voice...")
    audio_path = synthesize_voice(meta["script"], eleven_key, dir / "audio.mp3")

    # 3. 썸네일 생성 + 영상 조립
    print("\n[3/3] Generating thumbnail & assembling video...")
    thumbnail = generate_thumbnail(
        meta.get("thumbnail_text", meta["title"][:40]),
        dir / "thumbnail.jpg"
    )
    final_video = assemble_video(thumbnail, audio_path, dir / "final.mp4")

    size_mb = final_video.stat().st_size / 1024 / 1024
    print(f"\n✅ Video ready: {dir.name}")
    print(f"   Title: {meta['title']}")
    print(f"   Size:  {size_mb:.1f} MB")
    return {"dir": str(dir), "meta": meta,
            "video": str(final_video), "thumbnail": str(thumbnail)}


if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    run(topic)
