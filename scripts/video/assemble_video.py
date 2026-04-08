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

sys_path = str(Path(__file__).parent.parent)
if sys_path not in __import__('sys').path:
    __import__('sys').path.insert(0, sys_path)
from utils.retry import retry_api_call, notify_error, notify_success, PipelineHealthCheck


# ── 1. 스크립트 생성 (Groq) ──────────────────────────────────────────────────
def _groq_post(headers: dict, messages: list, temperature: float = 0.8,
               max_tokens: int = 4096) -> str:
    def _call():
        resp = requests.post(
            GROQ_API,
            headers=headers,
            json={"model": GROQ_MODEL, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    return retry_api_call(_call, max_retries=3)


def generate_script(topic: str, groq_api_key: str, seo_context: str = "") -> dict:
    """2-step 방식: JSON 메타 + plain text 스크립트 분리.
    seo_context: trend_researcher에서 수집한 SEO 힌트 (선택)."""
    import re
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}

    seo_hint = (f"\n\nSEO MARKET DATA (use to optimize title/tags/thumbnail):\n{seo_context}"
                if seo_context else "")

    # Step 1: JSON 메타데이터만 (script 없음 → 파싱 오류 방지)
    meta_raw = _groq_post(headers, [
        {"role": "system", "content": (
            "Output ONLY valid JSON (no markdown, no code blocks) with these exact keys:\n"
            "- title: YouTube title max 70 chars. MUST include a specific number (e.g. '7 tools', '$500/month') "
            "AND a clear benefit. Year 2026. Use PROVEN patterns like:\n"
            "  * 'I Found X AI Tools That Pay $Y/Month (Free)'\n"
            "  * 'X AI Side Hustles Nobody Talks About ($Y/Month)'\n"
            "  * 'Stop Doing X — Use AI to Make $Y Instead'\n"
            "  * 'How I Made $X With AI in Y Days (Step-by-Step)'\n"
            "- description: 300-word SEO description. Structure:\n"
            "  (1) First 2 lines = attention hook with a bold claim + emoji\n"
            "  (2) Paragraph with 5+ keyword variations (AI tools, passive income, side hustle, etc.)\n"
            "  (3) Timestamps section: list 5-7 key moments with timestamps (0:00, 1:30, etc.)\n"
            "  (4) End with clear CTA: 'Subscribe for daily AI income tips!'\n"
            "- tags: list of 20 strings. Mix strategy:\n"
            "  * 5 exact-match high-volume (make money online, AI tools 2026)\n"
            "  * 5 long-tail (how to make passive income with AI tools)\n"
            "  * 5 trending (ChatGPT side hustle, faceless YouTube)\n"
            "  * 5 competitor-adjacent (similar channel topics)\n"
            "- thumbnail_text: 3-4 word PUNCHY phrase. Rules:\n"
            "  * MUST have a $ amount OR large number\n"
            "  * Use power words: FREE, SECRET, QUIT, LAZY, INSANE\n"
            "  * Examples: '$500/DAY FREE' or 'QUIT YOUR JOB' or '7 AI SECRETS'"
        )},
        {"role": "user", "content": f"Topic: {topic}{seo_hint}"},
    ], max_tokens=800)
    meta_raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', meta_raw)
    if "```" in meta_raw:
        meta_raw = meta_raw.split("```")[1].lstrip("json").strip()
    meta = json.loads(meta_raw)

    # Step 2: 스크립트 plain text (고품질 내레이션)
    script = _groq_post(headers, [
        {"role": "system", "content": (
            "You are a top-tier YouTube scriptwriter for a faceless AI/passive income channel. "
            "Write a 900-1100 word spoken narration. STRUCTURE:\n\n"
            "HOOK (first 30 seconds, ~60 words):\n"
            "- Open with a SHOCKING stat, contrarian take, or personal result\n"
            "- Create urgency: 'Most people don't know this yet, but...'\n"
            "- Promise: exactly what the viewer will learn by watching\n\n"
            "BODY (5-7 tips/tools, ~800 words):\n"
            "- Each tip follows: Name → What it does (1 sentence) → "
            "Step-by-step how to profit from it (2-3 sentences) → "
            "Specific dollar amount or result ('creators report earning $X/month')\n"
            "- Use transition phrases between tips: 'But here's where it gets even better...'\n"
            "- Tip #3 or #4 should be the BEST one — 'This next one is the real game-changer'\n"
            "- Include mini-stories: 'One creator used this to go from zero to $2000 in 3 months'\n\n"
            "CLOSE (~100 words):\n"
            "- Summarize the top 3 takeaways in one sentence\n"
            "- Soft CTA: 'If this was helpful, that subscribe button is right there'\n"
            "- Tease next video: 'In my next video, I'll show you...'\n\n"
            "STYLE: Conversational, confident, slightly excited. "
            "Short sentences. Rhetorical questions. No filler words. "
            "No markdown, no headers — pure spoken text only."
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
    import sys

    load_dotenv()
    groq_key   = os.environ["GROQ_API_KEY"]
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "")

    health = PipelineHealthCheck()
    seo_context = ""

    if not topic:
        # ── 실시간 트렌드 연구로 최적 주제 자동 선정 ────────────────────────
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from research.trend_researcher import research as do_research
            print("\n[0/3] Researching trending topics...")
            result = do_research(groq_api_key=groq_key)
            topic = result["topic"]
            seo_context = result.get("seo_context", "")
            health.step_ok("트렌드 연구", f"주제: {topic[:50]}")
        except Exception as e:
            health.step_warn("트렌드 연구", str(e))
            fallback = [
                "7 AI tools that pay $500 per month in 2026",
                "How to make $3000/month with ChatGPT automation",
                "5 passive income streams using free AI tools",
                "Build a faceless YouTube channel with AI in 1 hour",
                "The $0 AI business that generates income while you sleep",
                "10 side hustles you can start with ChatGPT this week",
            ]
            topic = random.choice(fallback)

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_DIR / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎬 Producing video: '{topic}'")

    # 1. 스크립트 (SEO 컨텍스트 주입)
    print("\n[1/3] Generating script...")
    try:
        meta = generate_script(topic, groq_key, seo_context=seo_context)
        (out_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        health.step_ok("스크립트 생성", f"{meta['title'][:50]}")
        print(f"  ✓ Title:     {meta['title'][:65]}")
        print(f"  ✓ Tags:      {len(meta.get('tags', []))} tags")
        print(f"  ✓ Thumbnail: {meta.get('thumbnail_text', '')}")
    except Exception as e:
        health.step_fail("스크립트 생성", str(e))
        notify_error("youtube", f"Script generation failed: {e}")
        raise

    # 2. 음성 합성
    print("\n[2/3] Synthesizing voice...")
    try:
        audio_path = synthesize_voice(meta["script"], eleven_key, out_dir / "audio.mp3")
        health.step_ok("음성 합성", audio_path.name)
    except Exception as e:
        health.step_fail("음성 합성", str(e))
        notify_error("youtube", f"Voice synthesis failed: {e}")
        raise

    # 3. 썸네일 생성 + 영상 조립
    print("\n[3/3] Generating thumbnail & assembling video...")
    try:
        thumbnail = generate_thumbnail(
            meta.get("thumbnail_text", meta["title"][:30]),
            out_dir / "thumbnail.jpg"
        )
        final_video = assemble_video(thumbnail, audio_path, out_dir / "final.mp4")
        size_mb = final_video.stat().st_size / 1024 / 1024
        health.step_ok("영상 조립", f"{size_mb:.1f} MB")
    except Exception as e:
        health.step_fail("영상 조립", str(e))
        notify_error("youtube", f"Video assembly failed: {e}")
        raise

    print(f"\n✅ Video ready: {out_dir.name}")
    print(f"   Title:  {meta['title']}")
    print(f"   Size:   {size_mb:.1f} MB")
    print(f"   ⏱️ 소요시간: {health.duration_sec:.1f}초")

    notify_success("youtube", f"영상 생성 완료: {meta['title'][:50]}")
    health.write_github_summary("YouTube 영상")

    return {"dir": str(out_dir), "meta": meta,
            "video": str(final_video), "thumbnail": str(thumbnail)}


if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    run(topic)
