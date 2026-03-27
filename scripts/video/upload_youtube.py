"""
Phase 3 – YouTube 자동 업로드 (direct HTTP, no google-auth library)
===================================================================
token.json (access_token + refresh_token) 을 직접 읽어서
YouTube Data API v3 에 multipart/resumable upload 를 수행합니다.
"""

import os
import json
import time
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TOKEN_PATH       = os.environ.get("GOOGLE_TOKEN_PATH", "token.json")
CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")


# ── 토큰 관리 ─────────────────────────────────────────────────────────────────
def _load_token() -> dict:
    return json.loads(Path(TOKEN_PATH).read_text())


def _save_token(data: dict):
    Path(TOKEN_PATH).write_text(json.dumps(data, indent=2))


def get_access_token() -> str:
    """access_token 반환. 만료 시 refresh_token으로 갱신."""
    tok = _load_token()

    # 항상 refresh 시도 (expiry 필드 없어도 갱신해서 신선한 토큰 사용)
    if tok.get("refresh_token"):
        resp = requests.post(tok["token_uri"], data={
            "client_id":     tok["client_id"],
            "client_secret": tok["client_secret"],
            "refresh_token": tok["refresh_token"],
            "grant_type":    "refresh_token",
        })
        if resp.status_code == 200:
            new_data = resp.json()
            tok["token"] = new_data["access_token"]
            _save_token(tok)
            return tok["token"]
        else:
            print(f"  ⚠ Token refresh failed: {resp.text}")

    return tok["token"]


# ── 업로드 ────────────────────────────────────────────────────────────────────
def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list,
    thumbnail_path: str = None,
    privacy: str = "public",
    category_id: str = "22",
) -> str:
    access_token = get_access_token()
    headers_auth = {"Authorization": f"Bearer {access_token}"}

    video_file = Path(video_path)
    file_size  = video_file.stat().st_size

    metadata = {
        "snippet": {
            "title":           title[:100],
            "description":     description,
            "tags":            tags[:500] if isinstance(tags, list) else [],
            "categoryId":      category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus":            privacy,
            "selfDeclaredMadeForKids":  False,
        },
    }

    # ── 1. Resumable upload 세션 시작 ─────────────────────────────────────────
    init_resp = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers={
            **headers_auth,
            "Content-Type":           "application/json; charset=UTF-8",
            "X-Upload-Content-Type":  "video/mp4",
            "X-Upload-Content-Length": str(file_size),
        },
        data=json.dumps(metadata),
    )

    if init_resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to initiate upload: {init_resp.status_code} {init_resp.text}")

    upload_url = init_resp.headers["Location"]
    print(f"  Upload session: {upload_url[:60]}...")

    # ── 2. 청크 업로드 ─────────────────────────────────────────────────────────
    chunk_size  = 4 * 1024 * 1024  # 4MB
    offset      = 0
    video_id    = None
    retry       = 0

    print(f"  Uploading: {video_file.name} ({file_size / 1e6:.1f} MB)")

    with open(video_path, "rb") as f:
        while offset < file_size:
            chunk = f.read(chunk_size)
            end   = offset + len(chunk) - 1

            upload_resp = requests.put(
                upload_url,
                headers={
                    "Content-Range":  f"bytes {offset}-{end}/{file_size}",
                    "Content-Length": str(len(chunk)),
                },
                data=chunk,
            )

            if upload_resp.status_code in (200, 201):
                video_id = upload_resp.json()["id"]
                print(f"\n  ✓ Uploaded: https://youtu.be/{video_id}")
                break
            elif upload_resp.status_code == 308:  # Resume Incomplete
                range_header = upload_resp.headers.get("Range", "")
                if range_header:
                    offset = int(range_header.split("-")[1]) + 1
                else:
                    offset += len(chunk)
                progress = int(offset / file_size * 100)
                print(f"  Upload progress: {progress}%", end="\r")
                retry = 0
            elif upload_resp.status_code in (500, 502, 503, 504) and retry < 5:
                retry += 1
                wait = 2 ** retry
                print(f"\n  ⚠ HTTP {upload_resp.status_code}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"Upload chunk failed: {upload_resp.status_code} {upload_resp.text[:300]}")

    if not video_id:
        raise RuntimeError("Upload completed but no video_id received")

    # ── 3. 썸네일 업로드 ────────────────────────────────────────────────────────
    if thumbnail_path and Path(thumbnail_path).exists():
        access_token = get_access_token()
        thumb_resp = requests.post(
            f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
            f"?videoId={video_id}&uploadType=media",
            headers={
                "Authorization":  f"Bearer {access_token}",
                "Content-Type":   "image/jpeg",
            },
            data=Path(thumbnail_path).read_bytes(),
        )
        if thumb_resp.status_code in (200, 201):
            print("  ✓ Thumbnail uploaded")
        else:
            print(f"  ⚠ Thumbnail upload failed: {thumb_resp.status_code} {thumb_resp.text[:200]}")

    return video_id


# ── 메인 실행 ─────────────────────────────────────────────────────────────────
def run(video_dir: str):
    video_dir  = Path(video_dir)
    meta_file  = video_dir / "meta.json"
    video_file = video_dir / "final.mp4"
    thumb_file = video_dir / "thumbnail.jpg"

    if not video_file.exists():
        raise FileNotFoundError(f"Video not found: {video_file}")
    if not meta_file.exists():
        raise FileNotFoundError(f"Meta not found: {meta_file}")

    with open(meta_file) as f:
        meta = json.load(f)

    video_id = upload_video(
        video_path=str(video_file),
        title=meta["title"],
        description=meta["description"],
        tags=meta.get("tags", []),
        thumbnail_path=str(thumb_file) if thumb_file.exists() else None,
        privacy="public",
    )

    result = {"video_id": video_id, "url": f"https://youtu.be/{video_id}", "meta": meta}
    (video_dir / "upload_result.json").write_text(json.dumps(result, indent=2))
    print(f"\n🎉 Done! Watch at: https://youtu.be/{video_id}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_youtube.py <video_output_dir>")
        print("Example: python upload_youtube.py scripts/video/output/20260326_043753")
        sys.exit(1)
    run(sys.argv[1])
