# 핸드오프 문서 — urban-chainsaw

> 다른 세션/머신/에이전트로 작업을 넘길 때 이 문서 하나만 읽으면 되도록 작성됨.
> 최종 갱신: 2026-04-09 (세션 4 — 제휴 링크 파이프라인 추가 + 테스트 모드 인프라)

---

## 0. 30초 요약

- **레포**: `indiegyu/urban-chainsaw`
- **작업 브랜치**: `dev/auto-monetize-20260409-1202`
- **현재 수익**: $0 (YouTube 미수익화 상태 — 1000 구독자 필요)
- **파이프라인 갭**: 마지막 성공 실행 Run#31 (2026-03-27). 이후 12일 공백
- **남은 일**:
  - [ ] GitHub Secrets 추가 — 아래 표 참조 (필수: `LEMONSQUEEZY_API_KEY`, `HASHNODE_ACCESS_TOKEN`)
  - [ ] 제휴 ID Secrets 추가 (선택): `AMAZON_TAG`, `FIVERR_AFF_ID`, `ELEVENLABS_AFF_ID` 등
  - [ ] GitHub Actions가 `dev/auto-monetize-20260409-1202` 브랜치에서 실행 중인지 확인
  - [ ] `run_all.yml` 수동 dispatch → 전체 파이프라인 즉시 재가동

---

## 1. 환경 셋업

```bash
cd ~/projects/urban-chainsaw  # 또는 git clone https://github.com/indiegyu/urban-chainsaw.git
git fetch origin claude/research-income-automation-cUfDC
git checkout claude/research-income-automation-cUfDC
git pull
cat HANDOFF.md
```

---

## 2. 프로젝트 컨텍스트

`$0` 예산 AI 자동 수익 시스템. GitHub Actions 파이프라인이 매일 콘텐츠 생성.

### 활성 파이프라인 (출력 검증됨)

| 파이프라인 | 주기 (UTC) | 출력 |
|---|---|---|
| YouTube 영상 | 매일 09:00, 21:00 | `scripts/video/output/` |
| YouTube Shorts | 매일 15:00 | `.github/run_logs/last_shorts_run.txt` |
| 블로그 생성 | 매일 08:00, 16:00 | `scripts/blog/output/` |
| 블로그 발행 | 매일 08:30 (생성 후) | Hashnode + Medium (API 키 설정 시) |
| POD 디자인 | 매일 08:00 | `scripts/pod/output/` (커밋됨) |
| **제휴 링크 페이지** | **매일 10:00** | **`scripts/monetize/output/`** |
| KDP 이북 | 매주 일 07:00 | `scripts/ebook/output/` |
| Lemon Squeezy 상품 | 수·토 07:00 | `scripts/products/output/` |
| AI 전략 최적화 | 매주 월 06:00 | `content_strategy.json` |
| 대시보드 | 매일 22:00 | `docs/dashboard.html` |

---

## 3. 세션 4에서 추가한 기능 (2026-04-09)

### 제휴 링크 파이프라인 신규 추가

| 작업 | 내용 |
|---|---|
| `scripts/monetize/affiliate_generator.py` | 매일 제휴 링크 컬렉션 HTML 자동 생성 (8개 카테고리) |
| `scripts/utils/test_mode.py` | `TEST_MODE=1` 환경변수로 시크릿 없이 CI 실행 가능한 스텁 인프라 |
| `.github/workflows/daily_affiliate.yml` | 매일 10:00 UTC 자동 실행, 결과 커밋 |
| `run_all.yml` | `daily_affiliate.yml`을 콘텐츠 1단계에 포함 |

**제휴 Secrets (미설정 시 fallback URL 사용 — 크래시 없음):**
`AMAZON_TAG`, `FIVERR_AFF_ID`, `ELEVENLABS_AFF_ID`, `CONVERTKIT_AFF_ID`,
`SEMRUSH_AFF_ID`, `PRINTIFY_AFF_ID`, `HOSTINGER_AFF_ID`, `JASPER_AFF_ID`

---

## 3-prev. 세션 3에서 수정한 버그 (2026-04-09)

### 수익 = 0의 근본 원인 진단

| 원인 | 수정 여부 |
|---|---|
| `weekly_optimize.yml`: 대시보드 직접 실행 → 상대 임포트 깨짐 | ✅ `python -m scripts.analytics.revenue_dashboard`로 수정 |
| `daily_pod.yml`: 커밋 단계 없음 → CI 종료 시 디자인 파일 유실 | ✅ git commit 단계 추가 + `permissions: contents: write` 추가 |
| `run_all.yml`: `BRANCH: main` 하드코딩 → 작업 브랜치가 아닌 main에 dispatch | ✅ `${{ github.ref_name }}`으로 변경 |
| `daily_shorts.yml`: YAML 블록 내 `&& exit` 구문 오류 → Shorts 업로드 실패 무시 | ✅ `run: |` 블록으로 교정 |
| `daily_blog.yml`: 블로그 생성 후 외부 발행 없음 → 트래픽 0 | ✅ Hashnode + Medium 발행 단계 추가 |
| `.github/run_logs/` git 미추적 | ✅ `.gitkeep` 추가 |

### 수익 = 0의 남은 원인 (코드 외적 — 사용자 설정 필요)

| 원인 | 해결 방법 |
|---|---|
| YouTube 미수익화 (구독자 < 1000) | 콘텐츠 지속 업로드 (현재 4개 영상) |
| Lemon Squeezy API 키 미설정 | `LEMONSQUEEZY_API_KEY` GitHub Secret 추가 |
| Hashnode 미연동 | `HASHNODE_ACCESS_TOKEN` + `HASHNODE_PUBLICATION_ID` 추가 |
| Medium 미연동 | `MEDIUM_TOKEN` GitHub Secret 추가 |
| AdSense 미승인 | 블로그 20~30개 포스트 후 신청 |

---

## 4. GitHub Secrets 체크리스트

### 필수 (수익 발생에 직결)

| Secret 이름 | 용도 | 발급처 |
|---|---|---|
| `GROQ_API_KEY` | 모든 AI 생성 | console.groq.com |
| `GOOGLE_CLIENT_ID` | YouTube API | Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | YouTube API | Google Cloud Console |
| `YOUTUBE_REFRESH_TOKEN` | YouTube 업로드 | OAuth 플로우 |
| `YT_FULL_REFRESH_TOKEN` | YouTube Shorts | OAuth 플로우 |

### 수익화에 필요 (미설정 시 워크플로 스킵 — 크래시 없음)

| Secret 이름 | 용도 | 발급처 |
|---|---|---|
| `LEMONSQUEEZY_API_KEY` | 디지털 상품 판매 | app.lemonsqueezy.com → Settings → API |
| `HASHNODE_ACCESS_TOKEN` | 블로그 자동 발행 | hashnode.com/settings/developer |
| `HASHNODE_PUBLICATION_ID` | Hashnode 블로그 ID | Hashnode 블로그 설정 |
| `MEDIUM_TOKEN` | Medium 발행 | medium.com/me/settings → Integration Token |
| `ADSENSE_CLIENT_ID` | Google AdSense 광고 | AdSense 계정 승인 후 |
| `BEEHIIV_API_KEY` | 뉴스레터 발송 | beehiiv.com → Settings → API |
| `BEEHIIV_PUB_ID` | Beehiiv Publication | Beehiiv 대시보드 |

---

## 5. 핵심 파일 구조

```
.github/workflows/
  daily_youtube.yml    — 영상 생성+업로드 (09:00, 21:00 UTC)
  daily_shorts.yml     — Shorts 생성+업로드 (15:00 UTC) [버그수정됨]
  daily_blog.yml       — 블로그 생성+Hashnode/Medium발행 [Hashnode추가됨]
  daily_pod.yml        — POD 디자인 생성+커밋 [커밋단계추가됨]
  daily_dashboard.yml  — 대시보드 갱신 (22:00 UTC)
  weekly_optimize.yml  — 주간 전략+대시보드 [명령수정됨]
  weekly_gumroad.yml   — Lemon Squeezy 상품 등록
  weekly_ebook.yml     — KDP 이북 생성
  run_all.yml          — 전체 파이프라인 수동 실행 [브랜치버그수정됨]

scripts/
  analytics/
    dashboard_data.py      — 데이터 레이어
    dashboard_html.py      — HTML 렌더링
    revenue_dashboard.py   — 컨트롤러
  publish/
    hashnode_publisher.py  — Hashnode 발행
    medium_publisher.py    — Medium 발행
    pages_deploy.py        — GitHub Pages 빌드
  products/
    auto_product.py        — Lemon Squeezy 상품 생성
    gumroad_publisher.py   — Lemon Squeezy 등록
```

---

## 6. 알려진 함정

| 함정 | 회피 |
|---|---|
| `revenue_dashboard.py`를 직접 실행 | 반드시 `python -m scripts.analytics.revenue_dashboard` |
| 큰 파일 한 번에 Write | 파일을 200줄 이내로 분리 |
| 기본 push가 실패하면 hook bypass | `--no-verify` 절대 금지 |
| 핸드오프에 절대경로 박기 | `~/projects/urban-chainsaw`로 통일 |
| `run_all.yml` 수동 dispatch 전 브랜치 확인 | `github.ref_name` 반드시 작업 브랜치여야 함 |

---

## 7. 즉시 해야 할 첫 번째 행동 (복붙용)

```bash
# 1. 레포 최신화
cd ~/projects/urban-chainsaw && git pull

# 2. 전체 파이프라인 즉시 실행 (GitHub UI → Actions → 🚀 전체 파이프라인 즉시 실행 → Run workflow)
# 또는 gh CLI:
gh workflow run run_all.yml --ref claude/research-income-automation-cUfDC

# 3. 실행 결과 확인
gh run list --limit 10
```

---

## 8. 수익화 로드맵

```
현재: $0
  ↓  콘텐츠 지속 업로드 + Hashnode/Medium 발행 (자동)
1개월: 블로그 트래픽 + Hashnode 광고 수익 시작
  ↓  Lemon Squeezy API 키 설정 → 디지털 상품 판매 시작
2개월: YouTube 1000 구독자 → AdSense 수익 시작
  ↓  AdSense 승인 (블로그 30개 포스트 후)
3개월: 다채널 수익 (YouTube AdSense + 블로그 AdSense + Hashnode + 디지털 상품)
```
