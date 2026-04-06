# 나봇 카카오톡 챗봇 설정 완전 가이드

> 이미 완료된 단계: 카카오 개발자센터 앱 생성 + 카카오톡 채널 연결 ✅

---

## 목차

1. [네이버 검색 API 발급](#1-네이버-검색-api-발급)
2. [카카오 i 오픈빌더 봇 생성](#2-카카오-i-오픈빌더-봇-생성)
3. [로컬 서버 실행](#3-로컬-서버-실행)
4. [ngrok으로 외부 접속 열기](#4-ngrok으로-외부-접속-열기)
5. [오픈빌더 스킬 서버 등록](#5-오픈빌더-스킬-서버-등록)
6. [오픈빌더 블록 구성 (7개)](#6-오픈빌더-블록-구성)
7. [블록 ID 확인 후 .env 설정](#7-블록-id-확인-후-env-설정)
8. [오픈빌더에서 바로 테스트](#8-오픈빌더에서-바로-테스트)
9. [카카오톡에서 실제 테스트](#9-카카오톡에서-실제-테스트)
10. [Fly.io 서버 배포 (실서비스)](#10-flyio-서버-배포-실서비스)

---

## 1. 네이버 검색 API 발급

> 소요 시간: 5분

1. **https://developers.naver.com** 접속 → 로그인
2. 상단 메뉴 **Application > 애플리케이션 등록** 클릭
3. 애플리케이션 이름: `나봇`
4. 사용 API에서 **검색** 체크
5. 비로그인 오픈 API 서비스 환경: **WEB 설정** → URL에 `https://nabot.kr` 입력 (임시값, 나중에 변경)
6. **등록하기** 클릭
7. 생성된 앱 클릭 → **Client ID**와 **Client Secret** 메모해두기

---

## 2. 카카오 i 오픈빌더 봇 생성

> 소요 시간: 3분

1. **https://i.kakao.com** 접속 (카카오 계정 로그인)
2. **오픈빌더 시작하기** 또는 **+ 봇 만들기** 클릭
3. 봇 이름: `나봇`
4. **카카오톡 채널 연결** → 아까 만든 채널 선택
5. **저장** 클릭

> 이제 오픈빌더 편집 화면이 열립니다.

---

## 3. 로컬 서버 실행

> 소요 시간: 2분

터미널에서:

```bash
cd nabot

# 의존성 설치 (최초 1회)
pip install -r requirements.txt

# .env 파일 만들기
cp .env.example .env
```

`.env` 파일을 열어서 방금 발급받은 네이버 키 입력:

```
NAVER_CLIENT_ID=발급받은_Client_ID
NAVER_CLIENT_SECRET=발급받은_Client_Secret
KAKAO_NOTIFY_MODE=log
INTERNAL_SECRET=nabot-test-secret-123
```

서버 실행:

```bash
uvicorn main:app --reload --port 8000
```

브라우저에서 **http://localhost:8000** 접속 → `{"service":"나봇 (NaBot)"...}` 보이면 성공.

---

## 4. ngrok으로 외부 접속 열기

> 카카오 오픈빌더가 우리 로컬 서버에 접근할 수 있도록 공개 URL을 만드는 과정입니다.
> 소요 시간: 3분

### ngrok 설치 (최초 1회)

```bash
# macOS
brew install ngrok

# Windows: https://ngrok.com/download 에서 설치

# 또는 pip
pip install pyngrok
```

### ngrok 실행

서버 실행 터미널은 그대로 두고, **새 터미널**에서:

```bash
ngrok http 8000
```

다음과 같은 화면이 나옵니다:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

**`https://abc123.ngrok-free.app`** 부분을 복사해둡니다.
(매번 실행마다 URL이 바뀝니다. 테스트할 때마다 오픈빌더에서 업데이트 필요)

---

## 5. 오픈빌더 스킬 서버 등록

> 소요 시간: 5분

오픈빌더 왼쪽 메뉴 **스킬** 클릭 → **+ 스킬 추가**

아래 6개의 스킬을 각각 추가합니다.
URL의 `https://abc123.ngrok-free.app` 부분은 본인 ngrok URL로 교체:

| 스킬 이름 | URL |
|----------|-----|
| `나봇_메인메뉴` | `https://abc123.ngrok-free.app/kakao/webhook/main` |
| `나봇_키워드추가` | `https://abc123.ngrok-free.app/kakao/webhook/add-keyword` |
| `나봇_키워드목록` | `https://abc123.ngrok-free.app/kakao/webhook/list-keywords` |
| `나봇_키워드삭제` | `https://abc123.ngrok-free.app/kakao/webhook/delete-keyword` |
| `나봇_즉시검색` | `https://abc123.ngrok-free.app/kakao/webhook/search-now` |
| `나봇_업그레이드` | `https://abc123.ngrok-free.app/kakao/webhook/upgrade` |

각 스킬마다:
1. 이름 입력
2. URL 입력
3. **저장** 클릭
4. **테스트** 버튼 눌러서 200 OK 확인

---

## 6. 오픈빌더 블록 구성

왼쪽 메뉴 **시나리오** 클릭. 기본 시나리오가 있습니다.

---

### 블록 1: 웰컴 블록 수정

> 이미 존재하는 블록입니다. 수정만 합니다.

오픈빌더에 기본으로 있는 **웰컴 블록** 클릭:

**봇 응답** 섹션:
- 응답 타입: **텍스트**
- 내용:
  ```
  안녕하세요! 나봇 🔍
  인터넷에서 나(우리 밴드, 브랜드 등)에 대한 얘기를 자동으로 찾아드려요.

  아래 버튼을 눌러 시작해보세요!
  ```

**버튼** 추가:
- 버튼명: `시작하기`
- 버튼 타입: `블록 연결`
- 연결 블록: `나봇_메인메뉴` (아래에서 만들 블록, 지금은 나중에 연결해도 됨)

---

### 블록 2: 나봇_메인메뉴

**+ 블록 추가** 클릭:

- 블록 이름: `나봇_메인메뉴`
- **발화** 추가: `시작`, `메뉴`, `처음으로`, `홈`, `처음`
- **봇 응답** → **스킬 데이터 사용** 선택 → `나봇_메인메뉴` 스킬 선택
- **저장**

---

### 블록 3: 나봇_키워드입력 (슬롯 수집 1단계)

- 블록 이름: `나봇_키워드입력`
- **발화** 추가: `키워드 추가`, `추가`, `등록`, `키워드 등록`
- **봇 응답** → **텍스트** 입력:
  ```
  모니터링할 키워드를 입력해주세요.
  예) 소음발광, 솜발, 우리밴드이름
  ```
- **파라미터** 섹션 → **+ 파라미터 추가**:
  - 파라미터명: `term`
  - 엔티티: `sys.constant`
  - 필수 여부: ✅ 필수
  - 재입력 안내: `키워드를 입력해주세요.`
- **다음 블록 연결**: `나봇_검색방식선택`
- **저장**

---

### 블록 4: 나봇_검색방식선택 (슬롯 수집 2단계)

- 블록 이름: `나봇_검색방식선택`
- **발화**: 없음 (이전 블록에서 자동 연결됨)
- **봇 응답** → **텍스트**:
  ```
  검색 방식을 선택해주세요.

  완전일치: "소음발광" 이 단어가 정확히 있는 경우만
  유사검색: 소음, 발광 등 관련 내용 포함
  ```
- **버튼** 2개 추가:
  - `완전일치 검색` → 버튼 타입: **블록 연결** (직접 다음 블록으로)
  - `유사검색 포함` → 버튼 타입: **블록 연결** (직접 다음 블록으로)

> ⚠️ exact_match 파라미터는 파라미터로 수집하는 대신, 버튼 클릭 시 발화값으로 처리합니다.
> 두 버튼 모두 `나봇_제외어입력` 블록으로 연결합니다.

실제로는 `exact_match` 파라미터를 서버에 전달하기 위해:
- **파라미터** 섹션 → `exact_match` 추가
  - 엔티티: `sys.constant`
  - 필수: ✅
  - `완전일치 검색` 버튼 클릭 시 값: `true`
  - `유사검색 포함` 버튼 클릭 시 값: `false`
- **다음 블록**: `나봇_제외어입력`
- **저장**

---

### 블록 5: 나봇_제외어입력 (슬롯 수집 3단계 + 스킬 호출)

- 블록 이름: `나봇_제외어입력`
- **봇 응답** → **텍스트**:
  ```
  제외할 단어가 있나요?
  쉼표로 구분해서 입력하거나 없으면 '없음'을 입력해주세요.

  예) 고양이,냥이,발바닥
  ```
- **파라미터**:
  - `exclude_words` (sys.constant, 필수, 재입력 안내: `입력해주세요.`)
- **봇 응답** → **스킬 데이터 사용** 선택 → `나봇_키워드추가` 스킬 선택
- **파라미터 전달 설정**에서 `term`, `exact_match`, `exclude_words` 모두 체크
- **저장**

---

### 블록 6: 나봇_키워드목록

- 블록 이름: `나봇_키워드목록`
- **발화**: `내 키워드`, `키워드 목록`, `등록된 키워드`, `목록`, `내가 등록한`
- **봇 응답** → **스킬 데이터 사용** → `나봇_키워드목록`
- **저장**

---

### 블록 7: 나봇_키워드삭제

- 블록 이름: `나봇_키워드삭제`
- **발화**: `삭제`, `키워드 삭제`, `지우기`
- **봇 응답** → **텍스트**:
  ```
  삭제할 키워드 번호를 입력해주세요.
  번호는 [내 키워드 목록]에서 확인할 수 있어요.
  예) 삭제 3
  ```
- **파라미터**: `keyword_id` (sys.number, 필수)
- **봇 응답** → **스킬 데이터 사용** → `나봇_키워드삭제`
- **저장**

---

### 블록 8: 나봇_즉시검색

- 블록 이름: `나봇_즉시검색`
- **발화**: `지금 검색`, `검색해줘`, `바로 검색`, `검색`, `지금 알려줘`
- **봇 응답** → **스킬 데이터 사용** → `나봇_즉시검색`
- **저장**

---

### 블록 9: 나봇_업그레이드

- 블록 이름: `나봇_업그레이드`
- **발화**: `업그레이드`, `유료`, `플랜`, `요금`, `구독`
- **봇 응답** → **스킬 데이터 사용** → `나봇_업그레이드`
- **저장**

---

## 7. 블록 ID 확인 후 .env 설정

각 블록을 클릭하면 화면 우측 상단에 **블록 ID**가 표시됩니다.
(형식: `65abc123def456789abcdef0` 같은 24자리 문자열)

각 블록의 ID를 확인해서 `.env` 파일에 입력:

```
BLOCK_MAIN=나봇_메인메뉴_블록ID
BLOCK_ADD_KEYWORD=나봇_제외어입력_블록ID
BLOCK_LIST_KEYWORDS=나봇_키워드목록_블록ID
BLOCK_SEARCH_NOW=나봇_즉시검색_블록ID
BLOCK_UPGRADE=나봇_업그레이드_블록ID
```

`.env` 수정 후 서버 재시작:
```bash
# Ctrl+C 로 서버 종료 후
uvicorn main:app --reload --port 8000
```

---

## 8. 오픈빌더에서 바로 테스트

### 스킬 직접 테스트

오픈빌더 **스킬** 메뉴 → 각 스킬 클릭 → **테스트** 탭:

**나봇_메인메뉴 테스트 payload:**
```json
{
  "intent": {"id": "test", "name": "메인"},
  "userRequest": {
    "timezone": "Asia/Seoul",
    "block": {"id": "test", "name": "메인"},
    "utterance": "시작",
    "lang": "ko",
    "user": {
      "id": "test_user_001",
      "type": "botUserKey",
      "properties": {}
    }
  },
  "bot": {"id": "test", "name": "나봇"},
  "action": {
    "name": "메인",
    "clientExtra": null,
    "params": {},
    "id": "test",
    "detailParams": {}
  }
}
```

**나봇_키워드추가 테스트 payload:**
```json
{
  "intent": {"id": "test", "name": "키워드추가"},
  "userRequest": {
    "timezone": "Asia/Seoul",
    "block": {"id": "test", "name": "키워드추가"},
    "utterance": "소음발광",
    "lang": "ko",
    "user": {
      "id": "test_user_001",
      "type": "botUserKey",
      "properties": {}
    }
  },
  "bot": {"id": "test", "name": "나봇"},
  "action": {
    "name": "키워드추가",
    "clientExtra": null,
    "params": {
      "term": "소음발광",
      "exact_match": "true",
      "exclude_words": ""
    },
    "id": "test",
    "detailParams": {}
  }
}
```

응답에 `✅ '소음발광' 키워드가 등록됐어요!` 텍스트가 오면 성공.

### 로컬 스크립트로 빠른 테스트

서버가 실행 중인 상태에서 또 다른 터미널:
```bash
cd nabot
python test_webhook.py all
```

---

## 9. 카카오톡에서 실제 테스트

### 오픈빌더에서 배포

1. 오픈빌더 상단 **배포** 버튼 클릭
2. **운영 채널에 배포** 선택
3. 배포 완료 확인

### 카카오톡에서 테스트

1. 카카오톡에서 본인이 만든 채널 검색
2. 채널 추가 (친구 추가)
3. 채팅방 열어서 아무 말이나 입력 → 웰컴 메시지 확인
4. `시작` 입력 → 메인 메뉴 버튼 확인
5. `키워드 추가` 입력 → 키워드 등록 플로우 확인
6. `소음발광` 입력 → `완전일치 검색` 선택 → `없음` 입력 → 등록 완료 확인

---

## 10. Fly.io 서버 배포 (실서비스)

> ngrok은 개발 테스트용. 실서비스에는 항상 켜진 서버가 필요합니다.

### Fly.io 설치 및 로그인

```bash
# macOS
brew install flyctl

# Windows
iwr https://fly.io/install.ps1 -useb | iex

# 로그인
fly auth login
```

### 앱 배포

```bash
cd nabot

# 최초 배포 설정
fly launch --name nabot --region nrt --no-deploy

# 볼륨 생성 (SQLite 데이터 영속성)
fly volumes create nabot_data --region nrt --size 1

# 환경변수 설정 (발급받은 키들로 교체)
fly secrets set \
  NAVER_CLIENT_ID="발급받은_ID" \
  NAVER_CLIENT_SECRET="발급받은_Secret" \
  KAKAO_ADMIN_KEY="카카오앱_Admin키" \
  KAKAO_NOTIFY_MODE="api" \
  INTERNAL_SECRET="랜덤문자열_여기에입력" \
  BLOCK_MAIN="블록ID" \
  BLOCK_ADD_KEYWORD="블록ID" \
  BLOCK_LIST_KEYWORDS="블록ID" \
  BLOCK_SEARCH_NOW="블록ID" \
  BLOCK_UPGRADE="블록ID"

# 배포
fly deploy

# 배포 확인
fly status
fly logs
```

배포 완료 후 URL: `https://nabot.fly.dev`

### 오픈빌더 스킬 URL 업데이트

오픈빌더 **스킬** 탭에서 각 스킬 URL을 ngrok URL → Fly.io URL로 변경:

```
https://abc123.ngrok-free.app/kakao/webhook/main
    ↓
https://nabot.fly.dev/kakao/webhook/main
```

6개 스킬 모두 변경 후 **오픈빌더 재배포**.

---

## 체크리스트

### 로컬 테스트 완료 기준
- [ ] `uvicorn main:app` 실행 시 서버 정상 시작
- [ ] `python test_webhook.py all` 전체 통과
- [ ] 오픈빌더 스킬 테스트에서 각 엔드포인트 200 OK
- [ ] 카카오톡에서 키워드 추가 → 목록 확인 → 즉시 검색 작동

### 실서비스 배포 완료 기준
- [ ] `fly deploy` 성공
- [ ] `fly logs`에서 에러 없음
- [ ] 오픈빌더 스킬 URL을 Fly.io URL로 교체
- [ ] 카카오톡에서 재테스트 통과
- [ ] 알림 발송 테스트 (KAKAO_NOTIFY_MODE=api 상태에서)

---

## 문제 해결

**Q: 오픈빌더 스킬 테스트에서 타임아웃 발생**
→ ngrok이 실행 중인지 확인. `ngrok http 8000` 다시 실행.

**Q: 키워드 추가 시 "오류가 발생했어요" 메시지**
→ 서버 터미널 로그 확인. 파라미터명이 정확한지 오픈빌더에서 확인.

**Q: 즉시 검색에서 결과 없음**
→ NAVER_CLIENT_ID/SECRET 환경변수 설정 확인. `python test_webhook.py search`로 서버 로그 확인.

**Q: Fly.io 배포 후 DB가 초기화됨**
→ 볼륨 마운트 확인: `fly volumes list`. fly.toml의 [mounts] 설정 확인.
