"""
사이트/채널 링크 설정
=====================
채널 URL은 저장소에 하드코딩하지 않고 GitHub Secrets의 `YOUTUBE_CHANNEL_URL`로만
받습니다. 값이 없으면 링크를 아예 만들지 않습니다.

이유: 기존 코드에 박혀 있던 `https://www.youtube.com/@psg9806`은 404(죽은 링크)이고,
상품 문구에 쓰던 `@AIIncomeDaily`는 실제로 다른 사람(Paulo)의 채널입니다.
둘 중 하나를 기본값으로 두면 사이트에 틀린 링크가 나가므로, 설정이 없을 때는
링크를 생략하는 쪽을 기본으로 합니다.

설정 방법:
    GitHub → Settings → Secrets and variables → Actions → New secret
    YOUTUBE_CHANNEL_URL = https://www.youtube.com/@실제채널핸들
"""

from __future__ import annotations

import os

_PLACEHOLDER_TOKENS = (
    "your_channel", "yourchannel", "your-channel", "your_channnel",
    "@your", "/@channel", "/@handle", "/@username", "example.com",
)


def channel_url() -> str:
    """설정된 채널 URL. 없거나 예시값이면 빈 문자열."""
    raw = (os.environ.get("YOUTUBE_CHANNEL_URL") or "").strip()
    if not raw:
        return ""
    lowered = raw.lower()
    if any(token in lowered for token in _PLACEHOLDER_TOKENS):
        return ""
    if lowered.rstrip("/").endswith(("@channel", "@handle", "@username")):
        return ""
    if not lowered.startswith(("http://", "https://")):
        raw = "https://www.youtube.com/@" + raw.lstrip("@")
    return raw


def youtube_link(label: str = "YouTube", style: str = "", class_name: str = "",
                 target: str = "_blank") -> str:
    """채널 URL이 설정돼 있을 때만 <a> 태그를 만듭니다."""
    url = channel_url()
    if not url:
        return ""
    attrs = [f'href="{url}"']
    if target:
        attrs.append(f'target="{target}"')
    if style:
        attrs.append(f'style="{style}"')
    if class_name:
        attrs.append(f'class="{class_name}"')
    return f'<a {" ".join(attrs)}>{label}</a>'


def channel_line(prefix: str = "Subscribe:") -> str:
    """상품/이북 본문용 한 줄 링크 (설정 없으면 빈 문자열)."""
    url = channel_url()
    if not url:
        return ""
    return f"{prefix} {url}"
