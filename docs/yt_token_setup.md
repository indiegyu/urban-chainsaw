# YouTube OAuth 토큰 설정 가이드

> 대상: `scripts/video/upload_youtube.py`, `scripts/analytics/dashboard_data.py` 에서 사용하는 `token.json` / `token_yt.json` 생성 방법

---

## 개요

YouTube Data API를 사용하려면 Google OAuth 2.0 인증이 필요합니다.
로컬 개발과 GitHub Actions(CI) 환경에서 방법이 다릅니다.

---

## 1단계 — Google Cloud Console 설정

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 프로젝트 생성 또는 기존 프로젝트 선택
3. **API 및 서비스 → 라이브러리** 에서 `YouTube Data API v3` 활성화
4. **API 및 서비스 → 사용자 인증 정보** 클릭
5. **+ 사용자 인증 정보 만들기 → OAuth 클라이언트 ID** 선택
   - 애플리케이션 유형: **데스크톱 앱**
   - 이름: `urban-chainsaw-local` (임의 지정)
6. 생성된 클라이언트의 **JSON 다운로드** → 파일명을 `credentials.json`으로 저장
7. 파일을 프로젝트 루트에 저장:
   ```
   urban-chainsaw/
   └── credentials.json   ← 여기에 저장 (절대 커밋하지 말 것!)
   ```

> `credentials.json`은 `.gitignore`에 포함되어 있습니다.

---

## 2단계 — 로컬에서 OAuth 인증 (최초 1회)

### 방법 A: 브라우저 인증 (권장)

```bash
cd ~/projects/urban-chainsaw

# 의존성 설치
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client

# 브라우저 인증 실행 (port 8080 열림)
python scripts/video/setup_youtube_auth.py
```

브라우저가 열리면 Google 계정으로 로그인 후 권한 허용 → 완료되면 `token.json`이 생성됩니다.

### 방법 B: make_token.py (환경변수 방식)

이미 `refresh_token`을 갖고 있는 경우:

```bash
export YOUTUBE_REFRESH_TOKEN="your_refresh_token_here"
export GOOGLE_CLIENT_ID="your_client_id"
export GOOGLE_CLIENT_SECRET="your_client_secret"

python scripts/video/make_token.py token.json
```

---

## 3단계 — GitHub Actions(CI) 설정

CI 환경에서는 브라우저 인증이 불가능하므로 `refresh_token`을 GitHub Secret에 저장합니다.

### 필요한 GitHub Secrets

| Secret 이름 | 설명 | 값 위치 |
|---|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 클라이언트 ID | `credentials.json` 의 `client_id` 필드 |
| `GOOGLE_CLIENT_SECRET` | OAuth 클라이언트 Secret | `credentials.json` 의 `client_secret` 필드 |
| `YOUTUBE_REFRESH_TOKEN` | 업로드 권한 refresh token | 로컬 `token.json` 의 `refresh_token` 필드 |
| `YT_FULL_REFRESH_TOKEN` | 채널 관리 전체 권한 token | 별도 인증 시 발급 |

### Secrets 등록 방법

```bash
# GitHub CLI로 등록
gh secret set GOOGLE_CLIENT_ID --body "your_client_id"
gh secret set GOOGLE_CLIENT_SECRET --body "your_client_secret"
gh secret set YOUTUBE_REFRESH_TOKEN --body "your_refresh_token"
```

또는 GitHub UI: `https://github.com/indiegyu/urban-chainsaw/settings/secrets/actions`

### 워크플로에서 token.json 생성

`.github/workflows/daily_youtube.yml` 등에서:

```yaml
- name: Create YouTube token
  run: python scripts/video/make_token.py token.json
  env:
    YOUTUBE_REFRESH_TOKEN: ${{ secrets.YOUTUBE_REFRESH_TOKEN }}
    GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
    GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
```

---

## 4단계 — 토큰 없이 대시보드 실행 (테스트 모드)

`token.json`이 없어도 대시보드가 깨지지 않도록 테스트 모드를 지원합니다:

```bash
YOUTUBE_TEST_MODE=true python -m scripts.analytics.revenue_dashboard
```

테스트 모드에서는 YouTube 카드에 더미 데이터(구독자 0, 조회수 0)가 표시됩니다.
실제 데이터가 필요하면 반드시 토큰을 설정하세요.

---

## 자주 발생하는 오류

### `token.json 없음` 오류

```
error: token.json 없음 — YouTube OAuth 토큰이 필요합니다.
```

**원인**: `token.json` 파일이 존재하지 않음
**해결**: 위 2단계 진행 또는 `YOUTUBE_TEST_MODE=true` 환경변수 설정

### `refresh_token` 만료

**원인**: refresh_token은 6개월 미사용 시 만료
**해결**: 로컬에서 재인증(`setup_youtube_auth.py`) 후 GitHub Secret 업데이트

### `invalid_client` 오류

**원인**: `client_id` 또는 `client_secret` 불일치
**해결**: `credentials.json`과 GitHub Secrets 값 재확인

---

## 파일 위치 요약

```
urban-chainsaw/
├── credentials.json          ← Google OAuth 클라이언트 정보 (로컬 전용, gitignore)
├── token.json                ← YouTube OAuth 토큰 (로컬 전용, gitignore)
└── scripts/video/
    ├── make_token.py         ← 환경변수 → token.json 생성
    ├── setup_youtube_auth.py ← 브라우저 OAuth 인증
    └── exchange_code.py      ← Authorization code → token 교환
```
