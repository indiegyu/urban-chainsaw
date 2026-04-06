"""
카카오 친구톡 (FriendTalk) / 채널 메시지 발송.

카카오 비즈 메시지 API를 사용하기 위해서는:
1. 카카오 개발자센터에서 앱 생성
2. 카카오톡 채널 연결 (비즈 채널 인증 필요)
3. 친구톡 발송 API: https://developers.kakao.com/docs/latest/ko/message/rest-api

개발/테스트 시에는 KAKAO_NOTIFY_MODE=log 로 설정하면
실제 발송 없이 콘솔 출력만 함.
"""

import os
import json
import requests

TIMEOUT = 15


def _build_message(term: str, mentions: list[dict]) -> str:
    lines = [f"🔔 '{term}' 언급 발견! ({len(mentions)}건)", "━" * 16]
    for m in mentions[:5]:  # 최대 5건
        source_icon = {"Twitter": "📱", "네이버 뉴스": "📰", "네이버 블로그": "📝", "Google Alerts": "🔍"}.get(
            m["source"], "🌐"
        )
        lines.append(f"{source_icon} {m['source']} · {m['title'][:30]}")
        if m["snippet"]:
            lines.append(f'"{m["snippet"][:60]}..."')
        lines.append(f"→ {m['url']}")
        lines.append("")
    if len(mentions) > 5:
        lines.append(f"외 {len(mentions) - 5}건 더 있어요.")
    lines.append("━" * 16)
    lines.append("나봇 | 더 빠른 알림 → 업그레이드")
    return "\n".join(lines)


def send_to_user(kakao_user_key: str, term: str, mentions: list[dict]):
    """단일 유저에게 언급 알림 발송."""
    if not mentions:
        return

    message_text = _build_message(term, mentions)
    mode = os.environ.get("KAKAO_NOTIFY_MODE", "api")

    if mode == "log":
        print(f"\n[NOTIFY LOG] to={kakao_user_key}")
        print(message_text)
        return

    access_token = os.environ.get("KAKAO_ADMIN_KEY", "")
    if not access_token:
        print("  [Notify] KAKAO_ADMIN_KEY 없음")
        return

    # 카카오 친구톡 텍스트 메시지 발송
    # 실제 API 엔드포인트는 카카오 비즈 메시지 계약 후 제공됨
    # https://developers.kakao.com/docs/latest/ko/message/rest-api#send-friend
    try:
        resp = requests.post(
            "https://kapi.kakao.com/v1/api/talk/friends/message/send",
            headers={
                "Authorization": f"KakaoAK {access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "receiver_uuids": json.dumps([kakao_user_key]),
                "template_object": json.dumps({
                    "object_type": "text",
                    "text": message_text,
                    "link": {"web_url": "https://nabot.kr"},
                }),
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        print(f"  [Notify] 발송 완료 → {kakao_user_key} ({len(mentions)}건)")
    except Exception as e:
        print(f"  [Notify] 발송 실패 ({kakao_user_key}): {e}")
