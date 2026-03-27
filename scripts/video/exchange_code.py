"""
YouTube OAuth2 코드 교환 (커맨드라인용)
  python scripts/video/exchange_code.py "http://localhost/?code=4/0XXX..."
또는
  python scripts/video/exchange_code.py "4/0XXX..."
"""
import json, sys, requests, urllib.parse
from pathlib import Path
from dotenv import load_dotenv; load_dotenv()

creds  = json.loads(Path("credentials.json").read_text())["installed"]
raw    = sys.argv[1] if len(sys.argv) > 1 else input("코드 또는 리다이렉트 URL 붙여넣기: ").strip()
code   = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query).get("code", [raw])[0].split("&")[0]

resp   = requests.post(creds["token_uri"], data={
    "code": code, "client_id": creds["client_id"],
    "client_secret": creds["client_secret"],
    "redirect_uri": "http://localhost", "grant_type": "authorization_code",
})
data   = resp.json()
if "error" in data:
    print(f"❌ {data}"); sys.exit(1)

Path("token.json").write_text(json.dumps({
    "token": data["access_token"], "refresh_token": data.get("refresh_token",""),
    "token_uri": creds["token_uri"], "client_id": creds["client_id"],
    "client_secret": creds["client_secret"],
    "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
}, indent=2))
print("✅ token.json 저장 완료! YouTube 자동 업로드 준비됩니다.")
