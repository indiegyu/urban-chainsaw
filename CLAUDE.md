# AI Income Daily — 프로젝트 메모

## 현재 작업 브랜치
`claude/research-income-automation-cUfDC`

## 프로젝트 개요
$0 예산으로 시작하는 AI 기반 자동 수익 시스템. GitHub Actions로 14개 파이프라인 운영.

## 실제 활성 파이프라인 (출력 확인됨)
| 파이프라인 | 주기 | 출력 위치 | 현황 |
|-----------|------|----------|------|
| YouTube 영상 | 매일 2회 (18:00, 06:00 KST) | scripts/video/output/ (4개) | Run #31 성공 |
| YouTube Shorts | 매일 1회 (00:00 KST) | last_shorts_run.txt | Run #2 성공 |
| 블로그 포스트 | 매일 2회 (17:00, 01:00 KST) | scripts/blog/output/ (12개) | 활성 |
| POD 디자인 | 매일 1회 (17:00 KST) | scripts/pod/output/ (26개) | 활성 |
| KDP 이북 | 매주 일 (16:00 KST) | scripts/ebook/output/ (1개) | 활성 (주간) |
| AI 전략 최적화 | 매주 월 | content_strategy.json | v2 |
| 대시보드 | 매일 (07:00 KST) | docs/dashboard.html | 활성 |

## 미사용/미작동 파이프라인 (대시보드에서 제거 대상)
- Dev.to 발행 → .devto_published.json 파일 없음
- Twitter/X → .twitter_posted.json 파일 없음
- Ko-fi → 추적 불가
- AI Tools 디렉토리 → 출력 확인 불가
- 파이프라인 자동확장 → 출력 없음
- Podcast RSS → 에피소드 0개 (빈 JSON)
- Lemon Squeezy → API 키 미설정
- Etsy → SHOP_ID 미등록

## 최근 커밋 (2026-03-28)
- `c177ed4` feat: 파이프라인 안정성 강화 + 콘텐츠 품질 개선 + 대시보드 고도화
  - scripts/utils/retry.py 신규 (재시도 + 헬스체크 + 에러 알림)
  - 영상/블로그 프롬프트 품질 대폭 개선
  - 대시보드에 7일 트렌드 + 건강도 카드 추가

## 현재 진행 중인 작업
**대시보드 전면 리팩토링** (scripts/analytics/revenue_dashboard.py):
- [ ] UTC → KST(한국시간) 전환
- [ ] 미사용 파이프라인 제거 (Dev.to, Twitter, Ko-fi, Podcast 등)
- [ ] 실사용 파이프라인 데이터 확장 (YouTube 영상별 상세, 블로그 포스트 목록 등)
- [ ] 수확 링크 정리 (실제 사용하는 것만)
- [ ] 이북 카운트 추가

## 새 세션 시작 시 필수 체크리스트
1. `cd ~/Desktop/vscode/urban-chainsaw` 가능한지 확인. 없으면 git clone부터.
2. `git branch --show-current`가 `claude/research-income-automation-cUfDC`인지 확인.
3. `git pull` 후 `git log --oneline -5`로 최신 상태 점검.

## 스코프 가드레일
- 이 레포와 무관한 작업(Peekaboo, DuckDNS, nginx, Cloudflare 등) 금지.
- 막혔을 때 "그럴듯한 다른 일"로 빠지지 말고 즉시 보고하고 멈출 것.
- `revenue_dashboard.py`는 반드시 `python -m scripts.analytics.revenue_dashboard` 로 실행.
- `--no-verify` 절대 금지. 훅 실패 시 원인 파악 먼저.

## 비밀 정보 마스킹
- API 키, 토큰, 비밀번호는 절대 메시지/로그/커밋에 평문으로 쓰지 말 것.
- 환경변수 이름만 언급할 것 (예: `${GROQ_API_KEY}`).

## 파일 작업 가드레일
- 파일 하나는 200줄 이내로 유지. 넘으면 분리.
- 큰 파일 한 번에 Write 금지 — 세션이 멈춤. Edit 또는 분리 작성.

## GitHub Pages 배포 구조
- `docs/` → `gh-pages` 브랜치 → GitHub Pages 서빙.
- `.github/workflows/deploy_pages.yml`이 자동 배포 담당.
- GitHub Settings → Pages → Source를 `gh-pages` 브랜치로 수동 1회 설정 필요.

## 핵심 파일 구조
```
scripts/
  utils/retry.py          — 재시도/헬스체크/알림 유틸
  video/assemble_video.py — YouTube 영상 생성
  video/upload_youtube.py — YouTube 업로드
  blog/generate_post.py   — 블로그 포스트 생성
  analytics/revenue_dashboard.py — 대시보드 생성 ← 현재 수정 중
  analytics/weekly_optimizer.py  — 주간 전략 최적화
  strategy/content_strategy.json — 전략 데이터
  research/trend_researcher.py   — 트렌드 연구
.github/workflows/
  daily_youtube.yml, daily_shorts.yml, daily_blog.yml,
  daily_pod.yml, daily_dashboard.yml, run_all.yml 등 14개
```
