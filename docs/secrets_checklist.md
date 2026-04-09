# CI/CD Secrets 설정 체크리스트

> Repository: `indiegyu/urban-chainsaw`
> 설정 경로: GitHub → Settings → Secrets and variables → Actions → New repository secret

---

## 필수 Secrets (파이프라인 실행에 필요)

### AI / 콘텐츠 생성
| Secret 이름 | 설명 | 획득 방법 |
|---|---|---|
| `GROQ_API_KEY` | Groq LLM API — 블로그/요약/전략 생성 | [console.groq.com](https://console.groq.com) |

### 수익화 — Dev.to 블로그
| Secret 이름 | 설명 | 획득 방법 |
|---|---|---|
| `DEVTO_API_KEY` | Dev.to 포스트 자동 발행 | Dev.to Settings → Account → DEV Community API Keys |

### 수익화 — 뉴스레터
| Secret 이름 | 설명 | 획득 방법 |
|---|---|---|
| `BEEHIIV_API_KEY` | Beehiiv 뉴스레터 자동 발송 | Beehiiv Dashboard → Settings → API |
| `BEEHIIV_PUB_ID` | Beehiiv 퍼블리케이션 ID | 같은 위치에서 확인 (`pub_xxxxxxxx`) |

### 수익화 — 광고 (AdSense)
| Secret 이름 | 설명 | 획득 방법 |
|---|---|---|
| `ADSENSE_CLIENT_ID` | Google AdSense 퍼블리셔 ID | AdSense → 계정 → 계정 정보 (`ca-pub-xxxxxxxxxx` 형식) |
| `ADSENSE_API_KEY` | AdSense Reporting API | Google Cloud Console → APIs → AdSense |

#### AdSense 삽입 절차

1. [Google AdSense](https://adsense.google.com) 가입 및 사이트 등록 (`indiegyu.github.io/urban-chainsaw`)
2. 승인 완료 후 **계정 → 계정 정보**에서 퍼블리셔 ID 확인 (`ca-pub-XXXXXXXXXXXXXXXX`)
3. GitHub Secret 등록:
   ```bash
   gh secret set ADSENSE_CLIENT_ID --body "ca-pub-XXXXXXXXXXXXXXXX"
   ```
4. 다음 배포(`deploy_pages.yml`) 실행 시 `docs/*.html`의 `<!-- ADSENSE_CLIENT_ID -->` 플레이스홀더가 실제 AdSense 자동 광고 스크립트로 자동 치환됩니다.
5. Secret이 미설정이면 플레이스홀더는 그대로 유지되며 광고가 표시되지 않습니다 (사이트가 깨지지 않음).

> **플레이스홀더 위치**: `docs/index.html`, `docs/dashboard.html`, 대시보드 자동 생성 시 `revenue_dashboard.py` → `docs/dashboard.html`

### 수익화 — 제품/POD
| Secret 이름 | 설명 | 획득 방법 |
|---|---|---|
| `PRINTIFY_API_KEY` | Printify POD 상품 자동 생성 | Printify → My account → Connections → API access |
| `PRINTIFY_SHOP_ID` | Printify 스토어 ID | API 호출 또는 대시보드 URL에서 확인 |

### 수익화 — 디지털 제품
| Secret 이름 | 설명 | 획득 방법 |
|---|---|---|
| `GUMROAD_ACCESS_TOKEN` | Gumroad 제품/매출 API | Gumroad → Settings → Advanced → Application |

### 수익화 — GitHub Pages
| Secret 이름 | 설명 | 예시 값 |
|---|---|---|
| `GITHUB_PAGES_URL` | 배포된 Pages URL | `https://indiegyu.github.io/urban-chainsaw` |

### 제휴 마케팅 — Affiliate IDs
| Secret 이름 | 설명 | 획득 방법 |
|---|---|---|
| `AMAZON_TAG` | Amazon Associates 태그 | Associates Central → 계정 정보 |
| `FIVERR_AFF_ID` | Fiverr 제휴 ID | Fiverr Affiliates 대시보드 |
| `ELEVENLABS_AFF_ID` | ElevenLabs 제휴 ID | ElevenLabs Affiliates 프로그램 |
| `CONVERTKIT_AFF_ID` | ConvertKit(Kit) 제휴 ID | Kit Partner Program |
| `SEMRUSH_AFF_ID` | SEMrush 제휴 ID | SEMrush Affiliate Program |
| `PRINTIFY_AFF_ID` | Printify 제휴 ID | Printify Affiliate Program |
| `HOSTINGER_AFF_ID` | Hostinger 제휴 ID | Hostinger Affiliates |
| `JASPER_AFF_ID` | Jasper AI 제휴 ID | Jasper Partner Program |

### YouTube / Google OAuth
| Secret 이름 | 설명 | 획득 방법 |
|---|---|---|
| `GOOGLE_CLIENT_ID` | Google OAuth 클라이언트 ID | Google Cloud Console → Credentials |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 클라이언트 Secret | 같은 위치 |
| `YOUTUBE_REFRESH_TOKEN` | YouTube Data API refresh token | OAuth 인증 후 발급 |
| `YT_FULL_REFRESH_TOKEN` | YouTube Full scope refresh token | OAuth 인증 후 발급 (업로드 권한 포함) |

> **YouTube 토큰 상세 설정 방법**: [docs/yt_token_setup.md](yt_token_setup.md) 참고
>
> **토큰 없이 대시보드 실행**: `YOUTUBE_TEST_MODE=true python -m scripts.analytics.revenue_dashboard`

---

## 한국 결제 Secrets (향후 추가 예정)

| Secret 이름 | 설명 | 획득 방법 |
|---|---|---|
| `TOSS_CLIENT_KEY` | Toss Payments 클라이언트 키 | [developers.tosspayments.com](https://developers.tosspayments.com) |
| `TOSS_SECRET_KEY` | Toss Payments 시크릿 키 | Toss Payments 대시보드 |
| `KAKAO_APP_KEY` | Kakao Pay 앱 키 | [developers.kakao.com](https://developers.kakao.com) |
| `KAKAO_ADMIN_KEY` | Kakao Pay 어드민 키 | Kakao Developers → 내 애플리케이션 |
| `PAYPAL_CLIENT_ID` | PayPal REST API 클라이언트 ID | [developer.paypal.com](https://developer.paypal.com) |
| `PAYPAL_CLIENT_SECRET` | PayPal REST API Secret | PayPal Developer Dashboard |

---

## 설정 방법

```bash
# GitHub CLI로 일괄 설정 (권장)
gh secret set GROQ_API_KEY --body "your_key_here"
gh secret set DEVTO_API_KEY --body "your_key_here"
gh secret set BEEHIIV_API_KEY --body "your_key_here"
# ... 이하 동일
```

또는 GitHub UI: `https://github.com/indiegyu/urban-chainsaw/settings/secrets/actions`

---

## 현재 상태 (2026-04-09 기준)

- [x] `GROQ_API_KEY` — 설정 완료 (워크플로 실행 확인)
- [ ] `DEVTO_API_KEY` — 미설정
- [ ] `BEEHIIV_API_KEY` — 미설정
- [ ] `ADSENSE_CLIENT_ID` — 미설정
- [ ] `PRINTIFY_API_KEY` — 미설정
- [ ] `GUMROAD_ACCESS_TOKEN` — 미설정
- [ ] `AMAZON_TAG` — 미설정
- [ ] `GITHUB_PAGES_URL` — 미설정
- [ ] Toss/Kakao/PayPal — 향후 로드맵 참고
