"""
YouTube 채널 관리 스크립트
- 기존 영상 전부 비공개 처리
- 채널 타이틀/설명/키워드 수익화 최적화
- 채널 배너 이미지 생성 + 업로드
- 프로필 이미지 생성 (수동 업로드 안내)
- token.json 은 youtube (full) scope 필요
"""
import json, sys, io, requests
from pathlib import Path

TOKEN_PATH  = "token_yt.json"
ASSETS_DIR  = Path("scripts/video/channel_assets")
API_BASE    = "https://www.googleapis.com/youtube/v3"

CHANNEL_TITLE       = "AI Income Daily"
CHANNEL_DESCRIPTION = """\
🤖 AI & Automation | Make Money Online | Passive Income

I show you how to use AI tools to build multiple income streams — \
YouTube automation, affiliate marketing, print-on-demand, and more.

📌 New video every day — no face, no studio, 100% automated
🔔 Subscribe and turn on notifications to never miss a tip

━━━━━━━━━━━━━━━━━━━━━━━━
WHAT YOU'LL LEARN
━━━━━━━━━━━━━━━━━━━━━━━━
✅ AI tools that save you hours every day
✅ How to make money online with zero budget
✅ YouTube automation step-by-step
✅ Passive income strategies that actually work
✅ ChatGPT side hustle ideas for beginners

━━━━━━━━━━━━━━━━━━━━━━━━
TOPICS COVERED
━━━━━━━━━━━━━━━━━━━━━━━━
AI Tools · ChatGPT · Automation · Passive Income · Side Hustles
Print on Demand · Affiliate Marketing · YouTube Growth · Tech Tips

💼 Business: contact via YouTube Community tab"""

CHANNEL_KEYWORDS = (
    "AI tools,make money online,passive income,ChatGPT,automation,"
    "side hustle,YouTube automation,affiliate marketing,print on demand,"
    "AI tutorial,earn money,tech tips,artificial intelligence,productivity,"
    "faceless YouTube,digital income,online business"
)


# ── 인증 ─────────────────────────────────────────────────────────────────────
def get_access_token() -> str:
    tok = json.loads(Path(TOKEN_PATH).read_text())
    r = requests.post(tok["token_uri"], data={
        "client_id":     tok["client_id"],
        "client_secret": tok["client_secret"],
        "refresh_token": tok["refresh_token"],
        "grant_type":    "refresh_token",
    })
    if r.status_code == 200:
        tok["token"] = r.json()["access_token"]
        Path(TOKEN_PATH).write_text(json.dumps(tok, indent=2))
        return tok["token"]
    raise RuntimeError(f"Token refresh failed: {r.text}")

def get_headers() -> dict:
    return {"Authorization": f"Bearer {get_access_token()}", "Content-Type": "application/json"}


# ── 채널 정보 가져오기 ────────────────────────────────────────────────────────
def get_channel(headers: dict) -> dict:
    r = requests.get(
        f"{API_BASE}/channels?part=id,snippet,brandingSettings&mine=true",
        headers=headers
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError("채널을 찾을 수 없습니다.")
    return items[0]


# ── 기존 영상 비공개 처리 ─────────────────────────────────────────────────────
def make_all_videos_private():
    headers  = get_headers()
    channel  = get_channel(headers)
    # 채널 업로드 플레이리스트 ID 가져오기
    ch_detail = requests.get(
        f"{API_BASE}/channels?part=contentDetails&id={channel['id']}",
        headers=headers
    )
    ch_detail.raise_for_status()
    uploads_playlist = (ch_detail.json()["items"][0]
                        ["contentDetails"]["relatedPlaylists"]["uploads"])
    print(f"  업로드 플레이리스트: {uploads_playlist}")

    page_token = None
    total = 0

    while True:
        params = {"part": "contentDetails", "playlistId": uploads_playlist, "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(f"{API_BASE}/playlistItems", headers=headers, params=params)
        r.raise_for_status()
        data = r.json()

        video_ids = [item["contentDetails"]["videoId"] for item in data.get("items", [])]
        if not video_ids:
            break

        # 상태 일괄 조회
        vid_resp = requests.get(f"{API_BASE}/videos", headers=headers, params={
            "part": "id,snippet,status", "id": ",".join(video_ids)
        })
        vid_resp.raise_for_status()

        for video in vid_resp.json().get("items", []):
            vid_id  = video["id"]
            title   = video["snippet"]["title"]
            current = video["status"]["privacyStatus"]
            if current != "private":
                upd = requests.put(
                    f"{API_BASE}/videos?part=status",
                    headers=headers,
                    json={"id": vid_id, "status": {"privacyStatus": "private"}}
                )
                if upd.status_code in (200, 204):
                    print(f"  ✓ 비공개: [{vid_id}] {title[:50]}")
                    total += 1
                else:
                    print(f"  ✗ 실패: [{vid_id}] {upd.status_code} {upd.text[:100]}")
            else:
                print(f"  - 이미 비공개: {title[:50]}")

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    print(f"\n✅ 총 {total}개 영상 비공개 처리 완료")


# ── 채널 배너 이미지 생성 (PIL) ───────────────────────────────────────────────
def generate_banner() -> Path:
    """2560×1440 채널 배너를 PIL로 생성합니다."""
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    W, H = 2560, 1440
    img  = Image.new("RGB", (W, H), color=(15, 23, 42))   # 다크 네이비
    draw = ImageDraw.Draw(img)

    # ── 배경 그라데이션 효과 (도형으로 근사) ──
    for i in range(0, W, 4):
        alpha = int(30 * (i / W))
        draw.rectangle([i, 0, i+4, H], fill=(30 + alpha//3, 30 + alpha//5, 80 + alpha//2))

    # ── 강조 바 ──
    draw.rectangle([0, 0, W, 16],    fill=(99, 102, 241))   # 상단 인디고
    draw.rectangle([0, H-16, W, H],  fill=(99, 102, 241))   # 하단 인디고
    draw.rectangle([0, 0, 16, H],    fill=(99, 102, 241))   # 좌측
    draw.rectangle([W-16, 0, W, H],  fill=(99, 102, 241))   # 우측

    # ── 장식 원 ──
    draw.ellipse([W//2 - 500, H//2 - 500, W//2 + 500, H//2 + 500],
                 outline=(99, 102, 241), width=3)
    draw.ellipse([W//2 - 350, H//2 - 350, W//2 + 350, H//2 + 350],
                 outline=(55, 65, 150), width=2)

    # ── 폰트 ──
    try:
        font_xl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 160)
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
        font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
    except Exception:
        font_xl = font_lg = font_md = font_sm = ImageFont.load_default()

    # ── 메인 타이틀 ──
    title = "AI INCOME DAILY"
    tb = draw.textbbox((0, 0), title, font=font_xl)
    tx = (W - (tb[2] - tb[0])) // 2
    # 그림자
    draw.text((tx + 6, H//2 - 180 + 6), title, font=font_xl, fill=(30, 30, 80))
    draw.text((tx, H//2 - 180),          title, font=font_xl, fill=(255, 255, 255))

    # ── 서브타이틀 ──
    sub = "AI Tools · Passive Income · Automation"
    sb = draw.textbbox((0, 0), sub, font=font_md)
    sx = (W - (sb[2] - sb[0])) // 2
    draw.text((sx, H//2 + 40), sub, font=font_md, fill=(148, 163, 184))

    # ── 태그라인 ──
    tag = "🔔  New Video Every Day  •  Subscribe Now"
    tgb = draw.textbbox((0, 0), tag, font=font_sm)
    tgx = (W - (tgb[2] - tgb[0])) // 2
    # 배경 캡슐
    draw.rounded_rectangle(
        [tgx - 30, H//2 + 160, tgx + (tgb[2]-tgb[0]) + 30, H//2 + 230],
        radius=20, fill=(99, 102, 241)
    )
    draw.text((tgx, H//2 + 165), tag, font=font_sm, fill=(255, 255, 255))

    # ── 작은 AI 아이콘 도트 패턴 (배경) ──
    for yi in range(8, H, 120):
        for xi in range(8, W, 120):
            if abs(xi - W//2) > 600 or abs(yi - H//2) > 400:
                draw.ellipse([xi, yi, xi+6, yi+6], fill=(40, 50, 100))

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    banner_path = ASSETS_DIR / "channel_banner.jpg"
    img.save(str(banner_path), "JPEG", quality=95)
    print(f"  ✓ 배너 생성: {banner_path} ({W}×{H})")
    return banner_path


# ── 채널 프로필 이미지 생성 (PIL) ─────────────────────────────────────────────
def generate_profile_image() -> Path:
    """800×800 프로필 이미지를 PIL로 생성합니다.
    YouTube API는 프로필 사진 직접 변경을 지원하지 않으므로
    파일을 저장 후 수동 업로드 안내를 출력합니다."""
    from PIL import Image, ImageDraw, ImageFont

    S = 800
    img  = Image.new("RGB", (S, S), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)

    # 그라데이션 배경 원
    for r in range(S//2, 0, -2):
        ratio = r / (S//2)
        color = (
            int(15  + (99  - 15)  * (1 - ratio)),
            int(23  + (102 - 23)  * (1 - ratio)),
            int(42  + (241 - 42)  * (1 - ratio)),
        )
        draw.ellipse([S//2-r, S//2-r, S//2+r, S//2+r], fill=color)

    # 테두리 원
    draw.ellipse([10, 10, S-10, S-10], outline=(255, 255, 255), width=8)
    draw.ellipse([20, 20, S-20, S-20], outline=(99, 102, 241), width=4)

    try:
        font_icon = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 280)
        font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        font_sub  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 52)
    except Exception:
        font_icon = font_text = font_sub = ImageFont.load_default()

    # 메인 텍스트: "AI"
    icon_text = "AI"
    ib = draw.textbbox((0, 0), icon_text, font=font_icon)
    ix = (S - (ib[2] - ib[0])) // 2
    # 글로우 효과
    for offset in [(4,4), (-4,4), (4,-4), (-4,-4)]:
        draw.text((ix+offset[0], S//2-160+offset[1]), icon_text,
                  font=font_icon, fill=(30, 30, 120))
    draw.text((ix, S//2 - 160), icon_text, font=font_icon, fill=(255, 255, 255))

    # 하단 채널명
    ch_text = "INCOME DAILY"
    cb = draw.textbbox((0, 0), ch_text, font=font_text)
    cx = (S - (cb[2] - cb[0])) // 2
    draw.text((cx, S//2 + 150), ch_text, font=font_text, fill=(148, 163, 184))

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    profile_path = ASSETS_DIR / "channel_profile.jpg"
    img.save(str(profile_path), "JPEG", quality=95)
    print(f"  ✓ 프로필 이미지 생성: {profile_path} ({S}×{S})")
    return profile_path


# ── 배너 업로드 (YouTube API) ─────────────────────────────────────────────────
def upload_banner(banner_path: Path, headers: dict, channel_id: str):
    """생성한 배너를 YouTube 채널에 업로드합니다."""
    token = headers["Authorization"].replace("Bearer ", "")

    # Step 1: 배너 이미지 업로드
    with open(banner_path, "rb") as f:
        image_data = f.read()

    upload_resp = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/channelBanners/insert"
        "?uploadType=media&part=id",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "image/jpeg",
            "Content-Length": str(len(image_data)),
        },
        data=image_data,
        timeout=60,
    )

    if upload_resp.status_code not in (200, 201):
        print(f"  ✗ 배너 업로드 실패: {upload_resp.status_code} {upload_resp.text[:300]}")
        return False

    banner_url = upload_resp.json().get("url", "")
    if not banner_url:
        print(f"  ✗ 배너 URL 없음: {upload_resp.text[:200]}")
        return False

    print(f"  ✓ 배너 업로드 완료 (url: {banner_url[:60]}...)")

    # Step 2: 채널 brandingSettings에 배너 URL 연결
    upd = requests.put(
        f"{API_BASE}/channels?part=brandingSettings",
        headers=headers,
        json={
            "id": channel_id,
            "brandingSettings": {
                "image": {"bannerExternalUrl": banner_url}
            }
        }
    )
    if upd.status_code in (200, 204):
        print("  ✓ 채널 배너 적용 완료")
        return True
    else:
        print(f"  ✗ 배너 적용 실패: {upd.status_code} {upd.text[:300]}")
        return False


# ── 채널 전체 최적화 ──────────────────────────────────────────────────────────
def optimize_channel():
    """타이틀·설명·키워드·배너를 수익화 최적화로 업데이트합니다."""
    headers = get_headers()
    channel = get_channel(headers)
    channel_id    = channel["id"]
    current_title = channel["snippet"].get("title", "")
    print(f"채널 ID: {channel_id}")
    print(f"현재 타이틀: {current_title}")

    # ── 1. 타이틀 + 설명 (snippet) ──
    snippet_payload = {
        "id": channel_id,
        "snippet": {
            "title":       CHANNEL_TITLE,
            "description": CHANNEL_DESCRIPTION,
            "country":     "US",
            "defaultLanguage": "en",
        }
    }
    snippet_upd = requests.put(
        f"{API_BASE}/channels?part=snippet",
        headers=headers,
        json=snippet_payload
    )
    print(f"  snippet update → HTTP {snippet_upd.status_code}")
    if snippet_upd.status_code in (200, 204):
        updated_title = snippet_upd.json().get("snippet", {}).get("title", "?")
        print(f"  ✓ 타이틀: '{current_title}' → '{updated_title}'")
        if updated_title != CHANNEL_TITLE:
            print(f"  ⚠ API 응답 타이틀이 목표와 다름 (Brand Account 제한일 수 있음)")
    else:
        print(f"  ✗ snippet 업데이트 실패: {snippet_upd.text[:400]}")
        print("  ℹ️  Brand Account는 YouTube Studio에서 직접 변경해야 합니다:")
        print("      studio.youtube.com → 맞춤설정 → 기본 정보 → 채널 이름")

    # ── 2. brandingSettings (설명·키워드·언어·국가) ──
    brand_upd = requests.put(
        f"{API_BASE}/channels?part=brandingSettings",
        headers=headers,
        json={
            "id": channel_id,
            "brandingSettings": {
                "channel": {
                    "title":           CHANNEL_TITLE,
                    "description":     CHANNEL_DESCRIPTION,
                    "keywords":        CHANNEL_KEYWORDS,
                    "defaultLanguage": "en",
                    "country":         "US",
                    "featuredChannelsUrls": [],
                    "showRelatedChannels":  True,
                }
            }
        }
    )
    print(f"  brandingSettings update → HTTP {brand_upd.status_code}")
    if brand_upd.status_code in (200, 204):
        print("  ✓ 채널 설명/키워드 업데이트 완료")
    else:
        print(f"  ✗ brandingSettings 실패: {brand_upd.text[:400]}")

    # ── 3. 변경 후 채널 상태 재확인 ──
    print("\n  📋 변경 후 채널 상태 확인...")
    verify = requests.get(
        f"{API_BASE}/channels?part=snippet,brandingSettings&id={channel_id}",
        headers=headers
    )
    if verify.status_code == 200:
        v = verify.json()["items"][0]
        actual_title = v["snippet"].get("title", "N/A")
        actual_desc  = v["snippet"].get("description", "")[:80]
        brand_title  = v.get("brandingSettings", {}).get("channel", {}).get("title", "N/A")
        print(f"  채널명 (snippet.title):              {actual_title}")
        print(f"  채널명 (brandingSettings.channel.title): {brand_title}")
        print(f"  설명 (앞 80자):                      {actual_desc}...")
        if actual_title == CHANNEL_TITLE:
            print("  ✅ 채널명 변경 성공!")
        else:
            print(f"  ⚠ 채널명이 '{CHANNEL_TITLE}'로 변경되지 않음 — 수동 변경 필요")
            print("     👉 studio.youtube.com → 맞춤설정 → 기본 정보 → 채널 이름 편집")

    # ── 4. 배너 이미지 생성 + 업로드 ──
    print("\n  📐 배너 이미지 생성 중...")
    banner_path = generate_banner()
    upload_banner(banner_path, headers, channel_id)

    # ── 5. 프로필 이미지 생성 (파일만 저장, 수동 업로드 필요) ──
    print("\n  👤 프로필 이미지 생성 중...")
    profile_path = generate_profile_image()
    print(f"""
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ℹ️  프로필 사진 수동 업로드 안내 (API 정책 제한)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. GitHub에서 이미지 다운로드:
     https://github.com/indiegyu/urban-chainsaw/raw/main/scripts/video/channel_assets/channel_profile.jpg

  2. YouTube Studio 접속:
     https://studio.youtube.com

  3. 왼쪽 메뉴 → 맞춤설정 → 기본 정보 탭
     → 프로필 사진 항목 → 사진 변경
     → 다운로드한 channel_profile.jpg 선택
     → 게시 클릭

  📁 로컬 파일 경로: {profile_path}
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "private":
        make_all_videos_private()
    elif cmd == "optimize":
        optimize_channel()
    elif cmd == "banner":
        headers = get_headers()
        channel = get_channel(headers)
        banner_path = generate_banner()
        upload_banner(banner_path, headers, channel["id"])
    elif cmd == "assets":
        generate_banner()
        generate_profile_image()
        print("\n✅ 이미지 파일만 생성 완료 (API 호출 없음)")
    else:
        print("=== 기존 영상 비공개 처리 ===")
        make_all_videos_private()
        print("\n=== 채널 최적화 ===")
        optimize_channel()
