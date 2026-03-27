"""
YouTube OAuth2 설정 (Copy-Paste 방식)
======================================
1. 이 스크립트가 인증 URL을 출력합니다
2. 휴대폰으로 URL 접속 → Google 로그인 → 허용
3. 리다이렉트된 URL (http://localhost/?code=XXX...)에서 code 값을 복사
4. 이 스크립트에 붙여넣으면 token.json 자동 생성
"""

import os
import json
import sys
import urllib.parse
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
TOKEN_PATH       = os.environ.get("GOOGLE_TOKEN_PATH", "token.json")
SCOPE            = "https://www.googleapis.com/auth/youtube.upload"


def main():
    creds_data = json.loads(Path(CREDENTIALS_PATH).read_text())
    installed  = creds_data.get("installed", creds_data.get("web", {}))
    client_id     = installed["client_id"]
    client_secret = installed["client_secret"]
    token_uri     = installed["token_uri"]
    redirect_uri  = "http://localhost"

    # ── 1. 인증 URL 생성 ──────────────────────────────────────────────────────
    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         SCOPE,
        "access_type":   "offline",
        "prompt":        "consent",   # refresh_token 강제 발급
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    print("""
╔══════════════════════════════════════════════════════════════╗
║           YouTube OAuth2 인증 (휴대폰으로 완료 가능)           ║
╚══════════════════════════════════════════════════════════════╝

📱 지금 휴대폰에서:

  1. 아래 URL 전체를 복사해서 브라우저에 붙여넣기:
""")
    print(f"     {auth_url}")
    print("""
  2. Google 계정(vyehrkddl@gmail.com)으로 로그인

  3. "urban-chainsaw이(가) YouTube 계정에 액세스하려고 합니다"
     → [허용] 클릭

  4. 브라우저가 "localhost에 연결할 수 없음" 에러 페이지로 이동합니다
     → 정상입니다! 주소창의 URL 전체를 복사하세요

     URL 예시:
     http://localhost/?code=4/0XXXXX...&scope=...

  5. 복사한 URL (또는 code= 이후 값)을 아래에 붙여넣으세요:
""")

    # ── 2. 코드 입력 ─────────────────────────────────────────────────────────
    raw = input("  붙여넣기 → ").strip()

    # URL 전체 또는 code 값만 입력 모두 처리
    if raw.startswith("http"):
        parsed = urllib.parse.urlparse(raw)
        code = urllib.parse.parse_qs(parsed.query).get("code", [None])[0]
    else:
        code = raw.split("code=")[-1].split("&")[0] if "code=" in raw else raw

    if not code:
        print("\n❌ 코드를 찾을 수 없습니다. URL 전체를 복사해서 다시 시도하세요.")
        sys.exit(1)

    # ── 3. 코드 → 토큰 교환 ──────────────────────────────────────────────────
    print("\n⏳ 토큰 교환 중...")
    resp = requests.post(token_uri, data={
        "code":          code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  redirect_uri,
        "grant_type":    "authorization_code",
    })

    if resp.status_code != 200:
        print(f"\n❌ 토큰 교환 실패: {resp.text}")
        sys.exit(1)

    token_data = resp.json()
    if "error" in token_data:
        print(f"\n❌ 오류: {token_data}")
        sys.exit(1)

    # google-auth 형식으로 저장
    token_json = {
        "token":         token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "token_uri":     token_uri,
        "client_id":     client_id,
        "client_secret": client_secret,
        "scopes":        [SCOPE],
        "expiry":        None,
    }
    Path(TOKEN_PATH).write_text(json.dumps(token_json, indent=2))

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    ✅ YouTube 인증 완료!                       ║
╚══════════════════════════════════════════════════════════════╝

  token.json 저장됨 → 이제 영상이 자동으로 YouTube에 업로드됩니다.

  테스트 업로드:
    python scripts/video/upload_youtube.py scripts/video/output/LATEST_DIR
""")


if __name__ == "__main__":
    main()
