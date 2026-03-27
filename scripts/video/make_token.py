"""환경변수에서 token.json / token_yt.json 생성 (GitHub Actions용)"""
import json, os, sys

out_file = sys.argv[1] if len(sys.argv) > 1 else "token.json"

refresh = os.environ.get("YOUTUBE_REFRESH_TOKEN") or os.environ.get("YT_REFRESH_TOKEN", "")
client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
scope = os.environ.get("YT_SCOPE", "https://www.googleapis.com/auth/youtube.upload")

if not refresh:
    print("ERROR: YOUTUBE_REFRESH_TOKEN or YT_REFRESH_TOKEN env var not set", flush=True)
    sys.exit(1)

data = {
    "token": "",
    "refresh_token": refresh,
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": client_id,
    "client_secret": client_secret,
    "scopes": [scope]
}
open(out_file, "w").write(json.dumps(data))
print(f"{out_file} created (scope: {scope})")
