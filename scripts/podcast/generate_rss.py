"""
팟캐스트 RSS 피드 자동 생성기
==============================
YouTube 파이프라인이 생성한 오디오 파일(mp3/wav)을 읽어
Podcast RSS 2.0 피드를 생성합니다.

생성된 feed.xml을 GitHub Pages (docs/podcast/feed.xml)에 배포하면
Spotify, Apple Podcasts, Google Podcasts에 무료 등록 가능.

수익화 경로:
  - Spotify: 스트리밍당 $0.003~$0.005
  - 팟캐스트 스폰서십: 1000 다운로드당 $18~$50 (CPM)
  - Anchor.fm (무료): 광고 자동 삽입 (Spotify Audience Network)

Spotify 등록: https://podcasters.spotify.com/ → RSS URL 제출

필요한 환경변수:
  PODCAST_TITLE       — 팟캐스트 제목
  PODCAST_DESCRIPTION — 팟캐스트 설명
  GITHUB_PAGES_URL    — https://USERNAME.github.io/urban-chainsaw
"""

import os, json, re
from pathlib import Path
from datetime import datetime, timezone
from xml.sax.saxutils import escape

VIDEO_OUTPUT  = Path(__file__).parent.parent / "video" / "output"
DOCS_PODCAST  = Path(__file__).parent.parent.parent / "docs" / "podcast"
PODCAST_LOG   = Path(__file__).parent / ".podcast_episodes.json"

PODCAST_TITLE = os.environ.get("PODCAST_TITLE", "AI Income Automation Daily")
PODCAST_DESC  = os.environ.get("PODCAST_DESCRIPTION",
    "Daily AI tips, side hustles, and strategies to earn more in the digital age. "
    "New episode every day!")
PODCAST_AUTHOR = os.environ.get("PODCAST_AUTHOR", "AI Income Bot")
PODCAST_EMAIL  = os.environ.get("PODCAST_EMAIL", "podcast@example.com")
PODCAST_LANG   = "en"
PODCAST_CAT    = "Business"
PAGES_URL      = os.environ.get("GITHUB_PAGES_URL", "").rstrip("/")


def load_episodes() -> list:
    if PODCAST_LOG.exists():
        return json.loads(PODCAST_LOG.read_text()).get("episodes", [])
    return []


def save_episodes(episodes: list):
    PODCAST_LOG.parent.mkdir(parents=True, exist_ok=True)
    PODCAST_LOG.write_text(json.dumps({"episodes": episodes}, indent=2))


def scan_new_audio() -> list:
    """video/output/*/ 디렉토리에서 audio.mp3/wav 파일을 스캔합니다."""
    new_episodes = []
    for run_dir in sorted(VIDEO_OUTPUT.glob("*/"), key=lambda p: p.stat().st_mtime, reverse=True):
        audio = None
        for ext in ("audio.mp3", "audio.wav", "voice.mp3", "voice.wav"):
            candidate = run_dir / ext
            if candidate.exists():
                audio = candidate
                break
        if not audio:
            continue

        # 메타데이터 읽기
        meta_file = run_dir / "metadata.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
        else:
            meta = {"title": run_dir.name, "description": ""}

        size = audio.stat().st_size
        mtime = datetime.fromtimestamp(audio.stat().st_mtime, tz=timezone.utc)

        new_episodes.append({
            "id":          run_dir.name,
            "title":       meta.get("title", run_dir.name),
            "description": meta.get("description", meta.get("script_preview", ""))[:500],
            "audio_file":  audio.name,
            "audio_path":  str(audio),
            "size":        size,
            "duration":    meta.get("duration_seconds", 300),
            "pub_date":    mtime.strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "run_dir":     run_dir.name,
        })

    return new_episodes


def format_duration(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def build_rss(episodes: list) -> str:
    if not PAGES_URL:
        print("  ⚠ GITHUB_PAGES_URL not set — using placeholder URL")
        base = "https://example.github.io/urban-chainsaw"
    else:
        base = PAGES_URL

    items = ""
    for ep in episodes[:50]:  # 최신 50화
        audio_url = f"{base}/podcast/audio/{ep['run_dir']}/{ep['audio_file']}"
        items += f"""
  <item>
    <title>{escape(ep['title'])}</title>
    <description><![CDATA[{ep['description']}]]></description>
    <enclosure url="{audio_url}" length="{ep['size']}" type="audio/mpeg"/>
    <guid isPermaLink="false">{ep['id']}</guid>
    <pubDate>{ep['pub_date']}</pubDate>
    <itunes:duration>{format_duration(ep['duration'])}</itunes:duration>
    <itunes:explicit>no</itunes:explicit>
    <itunes:episodeType>full</itunes:episodeType>
  </item>"""

    feed_url = f"{base}/podcast/feed.xml"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{escape(PODCAST_TITLE)}</title>
  <link>{base}</link>
  <description>{escape(PODCAST_DESC)}</description>
  <language>{PODCAST_LANG}</language>
  <atom:link href="{feed_url}" rel="self" type="application/rss+xml"/>
  <itunes:author>{escape(PODCAST_AUTHOR)}</itunes:author>
  <itunes:email>{PODCAST_EMAIL}</itunes:email>
  <itunes:category text="{PODCAST_CAT}"/>
  <itunes:explicit>no</itunes:explicit>
  <itunes:type>episodic</itunes:type>
  <image>
    <url>{base}/podcast/cover.jpg</url>
    <title>{escape(PODCAST_TITLE)}</title>
    <link>{base}</link>
  </image>
  <itunes:image href="{base}/podcast/cover.jpg"/>
  {items}
</channel>
</rss>"""


def copy_audio_files(episodes: list):
    """오디오 파일을 docs/podcast/audio/ 로 복사합니다."""
    for ep in episodes:
        dest_dir = DOCS_PODCAST / "audio" / ep["run_dir"]
        dest_dir.mkdir(parents=True, exist_ok=True)
        src = Path(ep["audio_path"])
        dest = dest_dir / ep["audio_file"]
        if src.exists() and not dest.exists():
            import shutil
            shutil.copy2(src, dest)
            print(f"  📁 Copied: {ep['audio_file']} ({ep['size']//1024}KB)")


def run():
    DOCS_PODCAST.mkdir(parents=True, exist_ok=True)

    existing = {ep["id"] for ep in load_episodes()}
    all_eps = scan_new_audio()

    new_eps = [ep for ep in all_eps if ep["id"] not in existing]
    if new_eps:
        print(f"  + {len(new_eps)}개 새 에피소드 발견")
        copy_audio_files(new_eps)

    # 기존 에피소드 유지 + 신규 추가 (최신순)
    combined = new_eps + load_episodes()
    combined = combined[:100]  # 최대 100화 유지
    save_episodes(combined)

    # RSS 피드 생성
    rss = build_rss(combined)
    feed_path = DOCS_PODCAST / "feed.xml"
    feed_path.write_text(rss, encoding="utf-8")
    print(f"  ✓ RSS 피드 생성: {feed_path}")
    print(f"  ✓ 총 {len(combined)}화")

    if PAGES_URL:
        print(f"\n  📡 Spotify 등록 URL: {PAGES_URL}/podcast/feed.xml")
        print(f"  → https://podcasters.spotify.com/ 에서 RSS URL 제출")
    else:
        print("\n  ⚠ GITHUB_PAGES_URL을 설정하면 실제 피드 URL이 출력됩니다")

    print("\n✅ 팟캐스트 RSS 업데이트 완료")


if __name__ == "__main__":
    run()
