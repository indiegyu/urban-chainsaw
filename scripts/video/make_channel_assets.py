"""
YouTube 채널 에셋 자동 생성
=============================
배너 (2048x1152), 프로필 사진 (800x800), 워터마크 (150x150) 생성
"""
from PIL import Image, ImageDraw, ImageFont
import math, os
from pathlib import Path

OUT = Path(__file__).parent / "channel_assets"
OUT.mkdir(exist_ok=True)

# ── 색상 팔레트 ─────────────────────────────────────────────────
BG       = (10, 10, 20)        # 거의 검정
DARK     = (15, 23, 42)        # 네이비
PURPLE   = (99, 102, 241)      # 인디고
PURPLE2  = (139, 92, 246)      # 바이올렛
CYAN     = (34, 211, 238)      # 시안
WHITE    = (255, 255, 255)
GRAY     = (148, 163, 184)
GOLD     = (251, 191, 36)

def draw_gradient_bg(draw, w, h, c1, c2):
    for y in range(h):
        t = y / h
        r = int(c1[0] + (c2[0]-c1[0])*t)
        g = int(c1[1] + (c2[1]-c1[1])*t)
        b = int(c1[2] + (c2[2]-c1[2])*t)
        draw.line([(0,y),(w,y)], fill=(r,g,b))

def draw_grid(draw, w, h, color=(30,40,70), spacing=80):
    for x in range(0, w, spacing):
        draw.line([(x,0),(x,h)], fill=color, width=1)
    for y in range(0, h, spacing):
        draw.line([(0,y),(w,y)], fill=color, width=1)

def draw_glow_circle(img, cx, cy, r, color, alpha=60):
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    for i in range(r, 0, -8):
        a = int(alpha * (i/r) ** 2)
        d.ellipse([cx-i, cy-i, cx+i, cy+i], fill=(*color, a))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"),
              (0, 0))

def try_font(size):
    """사용 가능한 폰트 로드"""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def try_font_regular(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ════════════════════════════════════════════════════════════════
# 1. 배너 이미지 (2048 x 1152)
# ════════════════════════════════════════════════════════════════
def make_banner():
    W, H = 2048, 1152
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # 그라디언트 배경
    draw_gradient_bg(draw, W, H, (8, 8, 25), (18, 12, 40))

    # 그리드
    draw_grid(draw, W, H, color=(25, 30, 60), spacing=80)

    # 글로우 효과 (왼쪽 중앙)
    draw_glow_circle(img, 350, H//2, 420, PURPLE, alpha=45)
    draw_glow_circle(img, 300, H//2 + 80, 200, PURPLE2, alpha=30)

    # 오른쪽 장식 원
    draw_glow_circle(img, W - 200, 200, 250, CYAN, alpha=20)

    draw = ImageDraw.Draw(img)

    # 왼쪽 세로 컬러 바
    for i, color in enumerate([PURPLE, PURPLE2, CYAN]):
        x = 80 + i * 18
        draw.rectangle([x, H//2 - 160, x+8, H//2 + 160], fill=(*color, 200))

    # 채널 이름
    font_main = try_font(130)
    font_sub  = try_font(58)
    font_tag  = try_font_regular(40)

    # 메인 타이틀
    title = "AI Income Daily"
    draw.text((160, H//2 - 160), title, font=font_main, fill=WHITE)

    # 서브타이틀
    sub = "Automate. Earn. Repeat."
    draw.text((168, H//2 + 20), sub, font=font_sub, fill=CYAN)

    # 태그라인
    tags = "AI Tools  ·  Passive Income  ·  YouTube Automation  ·  ChatGPT Side Hustles"
    draw.text((168, H//2 + 110), tags, font=font_tag, fill=GRAY)

    # 업로드 주기 배지
    badge_x, badge_y = 168, H//2 + 190
    badge_w, badge_h = 340, 56
    draw.rounded_rectangle([badge_x, badge_y, badge_x+badge_w, badge_y+badge_h],
                            radius=28, fill=PURPLE)
    font_badge = try_font(32)
    draw.text((badge_x + 20, badge_y + 10), "📅  New Video Every Day", font=font_badge, fill=WHITE)

    # 오른쪽 장식 — 수익 아이콘들
    font_icon = try_font(48)
    icons = [("💰", 1650, 350), ("🤖", 1780, 450), ("📈", 1700, 580),
             ("⚡", 1820, 680), ("🎯", 1620, 720)]
    for icon, ix, iy in icons:
        draw.text((ix, iy), icon, font=font_icon, fill=WHITE)

    # 하단 핸들
    font_handle = try_font_regular(36)
    draw.text((168, H - 100), "@psg9806  |  youtube.com/@psg9806", font=font_handle, fill=GRAY)

    path = OUT / "banner_2048x1152.png"
    img.save(path, "PNG", optimize=True)
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"✅ 배너 저장: {path.name}  ({size_mb:.2f} MB)")
    return path


# ════════════════════════════════════════════════════════════════
# 2. 프로필 사진 (800 x 800)
# ════════════════════════════════════════════════════════════════
def make_profile():
    W = H = 800
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # 원형 그라디언트 배경
    cx, cy = W//2, H//2
    for r in range(400, 0, -2):
        t = r / 400
        color = (
            int(PURPLE[0]*t + BG[0]*(1-t)),
            int(PURPLE[1]*t + BG[1]*(1-t)),
            int(PURPLE2[2]*t + BG[2]*(1-t)),
        )
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)

    # 테두리 링
    draw.ellipse([20, 20, W-20, H-20], outline=PURPLE, width=8)
    draw.ellipse([35, 35, W-35, H-35], outline=(*CYAN, 120), width=3)

    # 메인 이모지/아이콘 — 큰 $ 기호
    font_big = try_font(280)
    draw.text((W//2, H//2), "AI", font=font_big, fill=WHITE, anchor="mm")

    # 하단 텍스트
    font_sub = try_font(60)
    draw.text((W//2, H - 130), "INCOME", font=font_sub, fill=CYAN, anchor="mm")
    font_sub2 = try_font_regular(38)
    draw.text((W//2, H - 70), "DAILY", font=font_sub2, fill=GRAY, anchor="mm")

    path = OUT / "profile_800x800.png"
    img.save(path, "PNG", optimize=True)
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"✅ 프로필 저장: {path.name}  ({size_mb:.2f} MB)")
    return path


# ════════════════════════════════════════════════════════════════
# 3. 워터마크 (150 x 150)
# ════════════════════════════════════════════════════════════════
def make_watermark():
    W = H = 150
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 반투명 원형 배경
    draw.ellipse([0, 0, W-1, H-1], fill=(*PURPLE, 180))
    draw.ellipse([4, 4, W-5, H-5], outline=(*WHITE, 160), width=3)

    # "AI" 텍스트
    font = try_font(54)
    draw.text((W//2, H//2 - 10), "AI", font=font, fill=WHITE, anchor="mm")
    font2 = try_font_regular(22)
    draw.text((W//2, H//2 + 34), "INCOME", font=font2, fill=(*CYAN, 220), anchor="mm")

    path = OUT / "watermark_150x150.png"
    img.save(path, "PNG")
    size_kb = path.stat().st_size / 1024
    print(f"✅ 워터마크 저장: {path.name}  ({size_kb:.1f} KB)")
    return path


if __name__ == "__main__":
    print("🎨 YouTube 채널 에셋 생성 중...\n")
    make_banner()
    make_profile()
    make_watermark()
    print(f"\n📁 저장 위치: scripts/video/channel_assets/")
    print("─" * 50)
    print("업로드 방법:")
    print("  배너     → YouTube Studio → 맞춤설정 → 배너 이미지 → 업로드")
    print("  프로필   → YouTube Studio → 맞춤설정 → 프로필 사진 → 업로드")
    print("  워터마크 → YouTube Studio → 맞춤설정 → 동영상 워터마크 → 업로드")
