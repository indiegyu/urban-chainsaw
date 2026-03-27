# urban-chainsaw

$0 예산으로 시작하는 완전 자동화 수익 시스템.
4가지 수익원을 하나의 코드베이스로 운영합니다.

---

## 수익원 구조

```
urban-chainsaw/
├── Phase 1 │ Print-on-Demand   → Etsy + Amazon Merch  ($0 시작)
├── Phase 2 │ AI 블로그 + Affiliate → Ghost + n8n       ($0 시작)
├── Phase 3 │ YouTube 자동화     → AdSense + Affiliate  ($0 시작)
└── Phase 4 │ Micro-SaaS        → AutoContent Pro       ($0 시작)
```

---

## 빠른 시작

### 1. 환경변수 설정
```bash
cp .env.example .env
# .env 파일을 열어 API 키 입력
```

필요한 무료 API 키:

| 서비스 | 용도 | 가입 |
|--------|------|------|
| Groq | AI 텍스트 생성 (무료) | console.groq.com |
| Ideogram.ai | AI 이미지 생성 (무료 25/일) | ideogram.ai |
| ElevenLabs | 음성 합성 (무료 10K chars/월) | elevenlabs.io |
| Pexels | 스톡 영상 (완전 무료) | pexels.com/api |
| Printify | POD 플랫폼 (무료) | printify.com |

### 2. Phase 1: POD 즉시 시작 (가장 빠른 수익)
```bash
pip install -r requirements.txt

# 디자인 5개 생성 + Etsy 자동 등록
python scripts/pod/generate_designs.py 5
python scripts/pod/create_listing.py
```

또는 GitHub Actions `daily_pod.yml`이 매일 자동 실행합니다.

### 3. Phase 2: n8n 콘텐츠 파이프라인
```bash
# Docker로 n8n + Ghost 실행 (완전 무료)
docker compose up -d

# n8n 접속: http://localhost:5678
# workflows/content_pipeline.json 을 n8n에서 import
```

### 4. Phase 3: YouTube 자동화
```bash
# Google OAuth 최초 인증 (1회만)
python scripts/video/assemble_video.py "10 best AI tools in 2026"
python scripts/video/upload_youtube.py scripts/video/output/LATEST_DIR
```

GitHub Actions `daily_youtube.yml`이 매일 오전 9시(UTC) 자동 실행합니다.

### 5. Phase 4: Micro-SaaS 로컬 개발
```bash
cd saas
npm install
npm run dev   # http://localhost:3000
```

---

## 디렉토리 구조

```
urban-chainsaw/
├── scripts/
│   ├── pod/
│   │   ├── generate_designs.py   # Ideogram → POD 디자인 생성
│   │   └── create_listing.py     # Printify → Etsy 자동 리스팅
│   ├── affiliate/
│   │   └── link_inserter.py      # HTML에 Affiliate 링크 자동 삽입
│   └── video/
│       ├── assemble_video.py     # ElevenLabs + Pexels + FFmpeg 영상 조립
│       └── upload_youtube.py     # YouTube Data API v3 자동 업로드
├── workflows/
│   ├── content_pipeline.json     # n8n: 블로그 + Affiliate 자동화
│   └── youtube_pipeline.json     # n8n: YouTube 일일 자동화
├── saas/
│   ├── app/api/
│   │   ├── generate/route.ts     # 콘텐츠 생성 API
│   │   └── webhooks/stripe/      # Stripe 결제 웹훅
│   └── lib/pipeline.ts           # 핵심 파이프라인 로직
├── docker-compose.yml            # n8n + Ghost + PostgreSQL + Redis
├── requirements.txt              # Python 의존성
└── .env.example                  # 환경변수 템플릿
```

---

## 현실적 수익 예측 ($0 예산 기준)

| 기간 | 마일스톤 | 예상 월 수익 |
|------|----------|-------------|
| Week 1~2 | POD 상품 50개 자동 등록 | $0~$50 |
| Month 1 | 블로그 30개 포스팅 자동 발행 | $0~$100 |
| Month 2 | YouTube 채널 20개 영상 업로드 | $0~$200 |
| Month 3 | Affiliate 수익 시작 | $100~$500 |
| Month 6 | 모든 스트림 복합 수익 | $500~$3,000 |
| Year 1 | SaaS + 복합 수익 | $1,000~$10,000 |

> **주의**: "완전 자동"이나 초기 설정과 주 1~2시간 품질 검수는 필요합니다.
> YouTube 커뮤니티 가이드, Amazon Associates ToS 등 플랫폼 정책을 반드시 준수하세요.

---

## Affiliate 프로그램 가입 (수동, 1회)

수익 창출을 위해 아래 프로그램에 직접 가입해야 합니다:

- Amazon Associates: affiliate-program.amazon.com
- Hostinger Affiliate: hostinger.com/affiliates ($100/판매)
- ConvertKit: partners.convertkit.com (30% 반복)
- n8n: n8n.io/affiliates (30% 12개월)
- Beehiiv: beehiiv.com/partner (50% 3개월)