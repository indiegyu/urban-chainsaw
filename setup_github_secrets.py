"""
GitHub Secrets 자동 설정 스크립트
===================================
로컬 credentials.json / token.json / token_yt.json 에서 값을 읽어
GitHub Secrets API로 자동 등록합니다.

사용법:
  pip install PyNaCl requests -q
  python3 setup_github_secrets.py <GITHUB_PERSONAL_ACCESS_TOKEN>

PAT 발급 방법:
  https://github.com/settings/tokens → Generate new token (classic)
  필요한 권한: repo (전체 체크)
"""

import sys, json, base64, requests
from pathlib import Path

OWNER = "indiegyu"
REPO  = "urban-chainsaw"

def get_public_key(token: str) -> tuple:
    r = requests.get(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/public-key",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    r.raise_for_status()
    d = r.json()
    return d["key_id"], d["key"]

def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    from nacl import encoding, public
    pk = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    box = public.SealedBox(pk)
    encrypted = box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

def set_secret(token: str, key_id: str, pub_key: str, name: str, value: str):
    encrypted = encrypt_secret(pub_key, value)
    r = requests.put(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/{name}",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
        json={"encrypted_value": encrypted, "key_id": key_id},
    )
    if r.status_code in (201, 204):
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}: {r.status_code} {r.text[:100]}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 setup_github_secrets.py <GITHUB_PAT>")
        print()
        print("PAT 발급: https://github.com/settings/tokens → classic → repo 전체 선택")
        sys.exit(1)

    token = sys.argv[1]

    # ── 로컬 파일에서 값 읽기 ──────────────────────────────────────
    base = Path(__file__).parent

    creds_file = base / "credentials.json"
    tok_file   = base / "token.json"
    tok_yt     = base / "token_yt.json"
    groq_env   = base / ".env"

    creds = json.loads(creds_file.read_text())
    app   = creds.get("installed") or creds.get("web") or {}
    tok   = json.loads(tok_file.read_text())
    tyt   = json.loads(tok_yt.read_text())

    secrets = {
        "GOOGLE_CLIENT_ID":      app.get("client_id", ""),
        "GOOGLE_CLIENT_SECRET":  app.get("client_secret", ""),
        "YOUTUBE_REFRESH_TOKEN": tok.get("refresh_token", ""),
        "YT_FULL_REFRESH_TOKEN": tyt.get("refresh_token", ""),
    }

    # .env 파일에서 GROQ_API_KEY 추가
    if groq_env.exists():
        for line in groq_env.read_text().splitlines():
            if line.startswith("GROQ_API_KEY="):
                secrets["GROQ_API_KEY"] = line.split("=", 1)[1].strip()

    # 비어있는 값 제거
    secrets = {k: v for k, v in secrets.items() if v}

    print(f"\n🔑 GitHub Secrets 설정: {OWNER}/{REPO}")
    print(f"   설정할 항목: {list(secrets.keys())}\n")

    try:
        import nacl
    except ImportError:
        print("Installing PyNaCl...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "PyNaCl", "-q"], check=True)

    key_id, pub_key = get_public_key(token)

    for name, value in secrets.items():
        set_secret(token, key_id, pub_key, name, value)

    print(f"\n✅ 완료! GitHub Actions에서 시크릿이 바로 사용 가능합니다.")

if __name__ == "__main__":
    main()
