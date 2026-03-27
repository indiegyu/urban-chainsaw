"""
YouTube 채널 관리 스크립트
- 기존 영상 전부 비공개 처리
- 채널 설명/키워드 수익화 최적화
- token.json 은 youtube (full) scope 필요
"""
import json, sys, requests
from pathlib import Path

TOKEN_PATH = "token_yt.json"

def get_access_token():
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

def get_headers():
    return {"Authorization": f"Bearer {get_access_token()}", "Content-Type": "application/json"}

def make_all_videos_private():
    """채널의 모든 영상을 비공개로 변경"""
    headers = get_headers()
    page_token = None
    total = 0

    while True:
        params = {"part": "id,snippet,status", "mine": "true", "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get("https://www.googleapis.com/youtube/v3/videos", headers=headers, params=params)
        r.raise_for_status()
        data = r.json()

        for video in data.get("items", []):
            vid_id = video["id"]
            title = video["snippet"]["title"]
            current = video["status"]["privacyStatus"]
            if current != "private":
                body = {
                    "id": vid_id,
                    "status": {"privacyStatus": "private"}
                }
                upd = requests.put(
                    "https://www.googleapis.com/youtube/v3/videos?part=status",
                    headers=headers, json=body
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

def optimize_channel():
    """채널 설명/키워드를 수익화 최적화로 업데이트"""
    headers = get_headers()

    # 채널 ID 가져오기
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/channels?part=id,snippet,brandingSettings&mine=true",
        headers=headers
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        print("채널 없음")
        return

    channel = items[0]
    channel_id = channel["id"]
    current_title = channel["snippet"].get("title", "")
    print(f"채널 ID: {channel_id}, 제목: {current_title}")

    description = """🤖 AI & Tech Tips | Productivity | Make Money Online

Discover the latest AI tools, productivity hacks, and strategies to earn more in the digital age.

📌 New videos every day!
🔔 Subscribe for daily AI tips that will transform your workflow

Topics: AI Tools, ChatGPT, Automation, Passive Income, Tech Reviews, Productivity

💼 Business inquiries: contact via YouTube"""

    keywords = "AI tools,artificial intelligence,make money online,passive income,productivity,ChatGPT,automation,tech tips,AI tutorial,earn money"

    body = {
        "id": channel_id,
        "brandingSettings": {
            "channel": {
                "description": description,
                "keywords": keywords,
                "defaultLanguage": "en",
                "country": "US",
            }
        }
    }

    upd = requests.put(
        "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings",
        headers=headers, json=body
    )
    if upd.status_code in (200, 204):
        print("✅ 채널 설명/키워드 업데이트 완료")
    else:
        print(f"✗ 채널 업데이트 실패: {upd.status_code} {upd.text[:300]}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "private":
        make_all_videos_private()
    elif cmd == "optimize":
        optimize_channel()
    else:
        print("=== 기존 영상 비공개 처리 ===")
        make_all_videos_private()
        print("\n=== 채널 최적화 ===")
        optimize_channel()
