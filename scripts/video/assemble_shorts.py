"""
YouTube Shorts 자동 제작
=========================
- 세로 포맷 (1080×1920, 9:16)
- 60초 이내, 핵심 한 가지 팁
- #Shorts 해시태그 자동 삽입
- 알고리즘이 신규 채널에 적극 추천 → 구독자 최단 경로

기존 assemble_video.py와 동일한 3단계 구조:
  1. Groq → 60초 분량 스크립트 + 메타데이터
  2. gTTS / ElevenLabs → 음성
  3. PIL 세로 썸네일 + FFmpeg 이미지 루프
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

OUTPUT_DIR = Path(__file__).parent / "output_shorts"


def _groq_post(headers, messages, max_tokens=400) -> str:
    r = requests.post(GROQ_API, headers=headers,
                      json={"model": GROQ_MODEL, "messages": messages,
                            "temperature": 0.85, "max_tokens": max_tokens},
                      timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def generate_shorts_script(groq_key: str) -> dict:
    """트렌드 기반 60초 Shorts 스크립트 생성."""
    import re, sys
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}

    # 전략 파일에서 상위 토픽 로드
    strategy_path = Path(__file__).parent.parent / "strategy" / "content_strategy.json"
    top_topics = []
    try:
        s = json.loads(strategy_path.read_text())
        top_topics = s.get("top_performing_topics", [])
    except Exception:
        pass

    topic_hint = f"Use one of these proven topics: {', '.join(top_topics[:3])}" if top_topics else ""

    # 메타데이터
    meta_raw = _groq_post(headers, [
        {"role": "system", "content": (
            "Output ONLY valid JSON with:\n"
            "- title: YouTube Shorts title (max 60 chars). Include #Shorts. "
            "Must have shock/curiosity hook + number or $ amount. "
            "Example: 'This AI makes $500/day for FREE 🤯 #Shorts'\n"
            "- thumbnail_text: 3-5 word ALL-CAPS hook for vertical thumbnail. "
            "Example: 'EARN $500 TODAY' or 'FREE AI MONEY HACK'\n"
            "- tags: list of 12 strings including 'Shorts', 'AI', 'PassiveIncome'"
        )},
        {"role": "user", "content": f"Create a viral YouTube Short about AI income. {topic_hint}"},
    ], max_tokens=300)
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', meta_raw)
    if "```" in raw:
        raw = raw.split("```")[1].lstrip("json").strip()
    meta = json.loads(raw)

    # 스크립트 (150~180 words = ~55초)
    script = _groq_post(headers, [
        {"role": "system", "content": (
            "Write a 150-word YouTube Shorts script. Rules:\n"
            "1. FIRST SENTENCE: shocking hook that stops the scroll (stat, claim, or question)\n"
            "2. ONE specific AI tool or method — name it, explain it in 2 sentences\n"
            "3. Exact steps: what to do right now (2-3 steps max)\n"
            "4. End: 'Follow for more AI income tips every day'\n"
            "No headings, no brackets, pure spoken words only."
        )},
        {"role": "user", "content": f"Topic: {meta.get('title', 'AI income hack')}"},
    ], max_tokens=300)

    meta["script"]      = script
    meta["description"] = (
        f"{meta['title']}\n\n"
        "💰 Daily AI income tips — Subscribe for more!\n\n"
        "#Shorts #AIIncome #PassiveIncome #ChatGPT #MakeMoneyOnline #SideHustle #AITools"
    )
    return meta


def generate_thumbnail_vertical(text: str, output_path: Path) -> Path:
    """1080×1920 세로형 Shorts 썸네일."""
    import textwrap
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1080, 1920
    img  = Image.new("RGB", (W, H), color=(10, 10, 30))
    draw = ImageDraw.Draw(img)

    # 그라데이션 배경
    for y in range(H):
        r = int(10 + 40 * (y / H))
        g = int(10 + 20 * (y / H))
        b = int(30 + 60 * (y / H))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 강조 바
    draw.rectangle([0, 0, W, 12],    fill=(233, 69, 96))
    draw.rectangle([0, H-12, W, H],  fill=(233, 69, 96))

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_tag = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
    except Exception:
        font_big = font_sub = font_tag = ImageFont.load_default()

    # 메인 텍스트 (중앙 세로 배치)
    lines = textwrap.wrap(text.upper(), width=12)
    total_h = len(lines) * 135
    y = (H - total_h) // 2 - 80
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font_big)
        x  = (W - (bb[2] - bb[0])) // 2
        draw.text((x+4, y+4), line, font=font_big, fill=(180, 20, 50))
        draw.text((x, y),     line, font=font_big, fill=(255, 255, 255))
        y += 135

    # 하단 채널 태그
    tag = "AI Income Daily • #Shorts"
    tb  = draw.textbbox((0, 0), tag, font=font_tag)
    draw.text(((W - (tb[2]-tb[0])) // 2, H - 120), tag,
              font=font_tag, fill=(150, 150, 200))

    out = output_path.with_suffix(".jpg")
    img.save(str(out), "JPEG", quality=92)
    print(f"  ✓ Shorts thumbnail: {out.name}")
    return out


def assemble_shorts_video(thumbnail: Path, audio: Path, output: Path) -> Path:
    """세로 포맷 Shorts 영상 조립."""
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(thumbnail),
        "-i", str(audio),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        "-vf", "scale=1080:1920,format=yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        str(output),
    ], check=True, capture_output=True, timeout=180)
    print(f"  ✓ Shorts video: {output.name}")
    return output


def synthesize_voice(text: str, eleven_key: str, out: Path) -> Path:
    if eleven_key:
        try:
            r = requests.post(
                f"{ELEVENLABS_API}/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={"xi-api-key": eleven_key, "Accept": "audio/mpeg",
                         "Content-Type": "application/json"},
                json={"text": text[:1500], "model_id": "eleven_flash_v2_5",
                      "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
                timeout=60,
            )
            r.raise_for_status()
            if r.content[:3] == b'ID3' or r.content[:2] in [b'\xff\xfb', b'\xff\xf3']:
                out.write_bytes(r.content)
                print(f"  ✓ ElevenLabs voice")
                return out
        except Exception as e:
            print(f"  ⚠ ElevenLabs failed ({e}), using gTTS")
    from gtts import gTTS
    mp3 = out.with_suffix(".mp3")
    gTTS(text=text[:1500], lang="en", slow=False).save(str(mp3))
    print(f"  ✓ gTTS voice")
    return mp3


def run():
    from dotenv import load_dotenv
    from datetime import datetime
    load_dotenv()

    groq_key   = os.environ["GROQ_API_KEY"]
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "")

    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_DIR / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n🎬 [Shorts] Generating script...")
    meta = generate_shorts_script(groq_key)
    (out_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"  ✓ Title: {meta['title'][:60]}")

    print("\n🎙️  [Shorts] Synthesizing voice...")
    audio = synthesize_voice(meta["script"], eleven_key, out_dir / "audio.mp3")

    print("\n🖼️  [Shorts] Assembling vertical video...")
    thumb = generate_thumbnail_vertical(meta.get("thumbnail_text", "AI MONEY"), out_dir / "thumbnail.jpg")
    video = assemble_shorts_video(thumb, audio, out_dir / "final.mp4")

    size_mb = video.stat().st_size / 1024 / 1024
    print(f"\n✅ Shorts ready: {out_dir.name} ({size_mb:.1f} MB)")
    return {"dir": str(out_dir), "meta": meta, "video": str(video)}


if __name__ == "__main__":
    run()
