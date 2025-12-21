# Quartz 프로젝트 분석 보고서

> **과목**: 차세대 분산 시스템  
> **주제**: 멀티 에이전트 기반 자동매매 시스템의 환경 분리 및 k3s 배포 분석

---

## 1. 프로젝트 개요

### 1.1 시스템 목적
Quartz는 한국 주식시장에서 자동매매를 수행하는 **멀티 에이전트 기반 분산 시스템**입니다. 각 에이전트는 독립적인 역할을 담당하며, 서로 통신하여 최종 매매 결정을 수행합니다.

### 1.2 아키텍처 특징
- **마이크로서비스 아키텍처**: 6개의 독립적인 에이전트로 구성
- **컨테이너 기반 배포**: Docker + k3s (경량 Kubernetes)
- **다국어 시스템**: Python (주요), C++ (성능 크리티컬 분석)
- **비동기 통신**: REST API + WebSocket

---

## 2. 에이전트별 상세 분석

### 2.1 인증 에이전트 (Auth Agent)

| 항목 | 내용 |
|------|------|
| **포트** | 8006 |
| **언어** | Python (FastAPI) |
| **역할** | 한국투자증권 OAuth 토큰 관리 |

#### 핵심 기능
```
┌─────────────────────────────────────────────────────────────┐
│                    Auth Agent (8006)                        │
├─────────────────────────────────────────────────────────────┤
│  • 토큰 발급: 23시간 55분마다 자동 갱신                       │
│  • 토큰 제공: GET /result/auth-token                         │
│  • 상태 확인: GET /result/auth-token/status                  │
│  • 헬스체크: GET /health/live, /health/ready                 │
└─────────────────────────────────────────────────────────────┘
```

#### 동작 방식
1. 시작 시 한국투자증권 API로 OAuth 토큰 발급
2. 백그라운드 태스크로 23시간 55분마다 자동 갱신 (24시간 만료 전 갱신)
3. 다른 에이전트들이 `/result/auth-token` 호출하여 토큰 획득
4. 만료 5분 전 요청 시 즉시 갱신

#### 분산 시스템 관점
- **Single Point of Authentication**: 모든 에이전트가 중앙 인증 서비스 사용
- **Token Caching**: 반복 발급 방지로 API Rate Limit 회피
- **High Availability**: k8s readiness probe로 토큰 유효성 보장

---

### 2.2 거시경제 분석 에이전트 (Macro Analysis Agent)

| 항목 | 내용 |
|------|------|
| **포트** | 8001 |
| **언어** | C++ (분석) + Python (API 서버) |
| **역할** | 거시경제 데이터 수집 및 AI 보고서 생성 |

#### 핵심 기능
```
┌──────────────────────────────────────────────────────────────────┐
│                 Macro Analysis Agent (8001)                       │
├──────────────────────────────────────────────────────────────────┤
│  C++ 분석 프로그램:                                               │
│  • 데이터 수집: ECOS (한국), FRED (미국), World Bank (글로벌)      │
│  • AI 보고서: Gemini 3 Pro + Google Search Grounding               │
│  • 출력: 긍정/부정 관점의 마크다운 보고서 + 10문장 요약             │
│  • S3 업로드: macro-analysis/ 폴더에 저장                          │
├──────────────────────────────────────────────────────────────────┤
│  Python API 서버:                                                 │
│  • GET /result/analysis: 요약본 반환 (포트폴리오 에이전트용)        │
│  • GET /result/analysis/full: 원본 반환 (프론트엔드용)              │
│  • 12시간마다 C++ 분석 실행                                        │
└──────────────────────────────────────────────────────────────────┘
```

#### 수집 데이터
| 출처 | 지표 | 주기 |
|------|------|------|
| ECOS (한국은행) | 기준금리, 근원물가, 환율, 수출입, 가계대출 | 월별 |
| FRED (미국 연준) | 연방기금금리, CPI | 월별 |
| World Bank | 글로벌/미국 GDP 성장률, 인플레이션 | 연간 |

#### 분산 시스템 관점
- **이기종 언어 통합**: C++의 성능 + Python의 생산성 결합
- **비동기 데이터 파이프라인**: 수집 → 분석 → S3 → 캐시
- **Loosely Coupled**: S3를 중간 저장소로 사용하여 결합도 최소화

---

### 2.3 종목 선택 에이전트 (Stock Selection Agent)

| 항목 | 내용 |
|------|------|
| **포트** | 8002 |
| **언어** | Python (FastAPI) |
| **역할** | 뉴스 기반 종목 선정 |

#### 핵심 기능
```
┌──────────────────────────────────────────────────────────────────┐
│                Stock Selection Agent (8002)                       │
├──────────────────────────────────────────────────────────────────┤
│  뉴스 파이프라인:                                                 │
│  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐               │
│  │ 크롤링 │ → │종목매칭│ → │감성분석│ → │ 집계  │               │
│  └────────┘   └────────┘   └────────┘   └────────┘               │
│                                                                   │
│  • 크롤러: 네이버, 한국경제, 매일경제                             │
│  • 감성 분석: Gemini API (배치 처리)                              │
│  • 스케줄: 12시간마다 자동 실행 (00:00, 12:00)                     │
│  • API: POST /api/candidates                                      │
└──────────────────────────────────────────────────────────────────┘
```

#### 중요도 점수 산출
```python
final_score = (
    market_cap_tier * 0.25 +    # 시총 등급 (LARGE/MID/SMALL)
    sentiment_score * 0.40 +     # 감성 분석 점수
    news_count_norm * 0.25 +     # 뉴스 언급 횟수 (정규화)
    priority_score * 0.10        # 우선순위
)
```

#### 분산 시스템 관점
- **Event-Driven Processing**: 스케줄러 기반 배치 처리
- **Data Locality**: S3를 통한 데이터 공유
- **Fault Tolerance**: 로컬 파일 폴백 지원

---

### 2.4 기술분석 에이전트 (Technical Analysis Agent)

| 항목 | 내용 |
|------|------|
| **포트** | 8003 |
| **언어** | Python (FastAPI + NumPy) |
| **역할** | 기술적 지표 계산 |

#### 핵심 기능
```
┌──────────────────────────────────────────────────────────────────┐
│                Technical Agent (8003)                             │
├──────────────────────────────────────────────────────────────────┤
│  기술적 지표:                                                     │
│  • RSI (Relative Strength Index)                                  │
│  • MACD (Moving Average Convergence Divergence)                   │
│  • Bollinger Bands (20일, 2σ)                                     │
│  • Fibonacci Retracement                                          │
│  • MA (5, 10, 20일 이동평균)                                      │
├──────────────────────────────────────────────────────────────────┤
│  분석 주기: 일(Day), 주(Week), 월(Month)                          │
│  캐시: 5분 TTL (API 호출 최소화)                                   │
│  API: POST /result/analysis { "ticker": "005930" }                │
└──────────────────────────────────────────────────────────────────┘
```

#### 데이터 흐름
```
[한국투자증권 API] → [시세 데이터 조회] → [지표 계산] → [결과 캐싱] → [S3 백업]
                              ↑
                    [Auth Agent에서 토큰 획득]
```

#### 분산 시스템 관점
- **Caching Strategy**: 5분 TTL로 동일 요청 재사용
- **Dependency Injection**: Auth Agent 의존성 명시적 관리
- **Async I/O**: httpx + asyncio로 비동기 API 호출

---

### 2.5 포트폴리오 관리 에이전트 (Portfolio Manager Agent)

| 항목 | 내용 |
|------|------|
| **포트** | 8004 |
| **언어** | Python (FastAPI + OpenAI) |
| **역할** | 매매 의사결정 및 조율 |

#### 핵심 기능
```
┌──────────────────────────────────────────────────────────────────┐
│              Portfolio Manager Agent (8004)                       │
├──────────────────────────────────────────────────────────────────┤
│  의사결정 루프 (30분마다, 장시간 09:00~15:30):                     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │         [거시경제]    [후보종목]    [기술분석]               │ │
│  │             ↓            ↓            ↓                      │ │
│  │         ┌────────────────────────────────────┐              │ │
│  │         │     GPT-4o-mini 의사결정 엔진      │              │ │
│  │         └────────────────────────────────────┘              │ │
│  │                         ↓                                    │ │
│  │         ┌────────────────────────────────────┐              │ │
│  │         │   BUY / SELL / HOLD 결정 + 비중    │              │ │
│  │         └────────────────────────────────────┘              │ │
│  │                         ↓                                    │ │
│  │         ┌────────────────────────────────────┐              │ │
│  │         │   WebSocket → Trading Agent        │              │ │
│  │         └────────────────────────────────────┘              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  리밸런싱 루프 (5~10분마다):                                      │
│  • 손절 체크: -5% 이하 시 자동 매도                               │
│  • 익절 체크: +15% 이상 시 자동 매도                              │
│  • 거래량 기반 주기 조정                                          │
└──────────────────────────────────────────────────────────────────┘
```

#### GPT 입력 구조
```json
{
  "now_utc": "2024-12-15T10:00:00Z",
  "macro": { "positive_summary": "...", "negative_summary": "...", "market_bias_hint": "bullish" },
  "portfolio": { "cash_krw": 1000000, "total_value": 5000000, "positions": [...] },
  "universe": [{ "ticker": "005930", "technical": {...}, "fundamental": {...} }],
  "constraints": { "max_buy_candidates": 3, "max_single_ticker_weight": 0.2 }
}
```

#### 분산 시스템 관점
- **Orchestrator Pattern**: 다른 에이전트들의 데이터를 수집·통합
- **Event-Driven + Scheduled**: 주기적 실행 + 조건 기반 트리거
- **WebSocket Communication**: 실시간 주문 전송

---

### 2.6 거래 에이전트 (Trading Agent)

| 항목 | 내용 |
|------|------|
| **포트** | 8005 |
| **언어** | Python (FastAPI + WebSocket) |
| **역할** | 실제 주식 매매 실행 |

#### 핵심 기능
```
┌──────────────────────────────────────────────────────────────────┐
│                   Trading Agent (8005)                            │
├──────────────────────────────────────────────────────────────────┤
│  WebSocket 서버:                                                  │
│  • ws://trading-agent:8005/ws/orders                              │
│  • 주문 수신 → 실행 → 결과 응답                                   │
│  • 30초마다 Ping/Pong으로 연결 유지                               │
├──────────────────────────────────────────────────────────────────┤
│  주문 실행:                                                       │
│  • 매수: TR_ID=TTTC0012U                                          │
│  • 매도: TR_ID=TTTC0011U                                          │
│  • 취소: TR_ID=TTTC0013U                                          │
│  • 최대 3회 재시도 (1초 간격)                                     │
├──────────────────────────────────────────────────────────────────┤
│  HTTP API (백업용):                                               │
│  • POST /api/order                                                │
│  • POST /api/cancel-order                                         │
│  • GET /api/cancelable-orders                                     │
└──────────────────────────────────────────────────────────────────┘
```

#### 주문 메시지 형식
```json
{
  "request_id": "uuid",
  "action": "buy",
  "ticker": "005930",
  "qty": 10,
  "order_type": "market",
  "price": 0,
  "timestamp": "2024-12-15T10:00:00Z"
}
```

#### 분산 시스템 관점
- **Dual Protocol**: WebSocket (실시간) + HTTP (백업)
- **Idempotency**: request_id로 중복 주문 방지
- **Retry Logic**: 네트워크 장애 대응

---

## 3. 환경 분리 및 k3s 배포 전략

### 3.1 네임스페이스 격리

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: quartz
  labels:
    name: quartz
```

모든 에이전트는 `quartz` 네임스페이스에 배포되어 다른 워크로드와 격리됩니다.

### 3.2 설정 관리 (ConfigMap + Secret)

#### ConfigMap (비민감 설정)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: quartz-config
  namespace: quartz
data:
  IS_PRODUCTION: "true"
  AWS_REGION: "ap-northeast-2"
  S3_BUCKET_NAME: "quartz-bucket"
  # 제약조건
  MIN_ORDER_KRW: "100000"
  MAX_SINGLE_TICKER_WEIGHT: "0.2"
  MAX_TURNOVER_RATIO: "0.3"
  # 에이전트 URL (k3s 내부 DNS)
  AUTH_AGENT_URL: "http://auth-agent:8006"
  MACRO_AGENT_URL: "http://macro-agent:8001"
  TICKER_SELECTOR_URL: "http://ticker-selector:8002"
  TECHNICAL_AGENT_URL: "http://technical-agent:8003"
  TRADING_AGENT_WS_URL: "ws://trading-agent:8005/ws/orders"
```

#### Secret (민감 정보)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: quartz-secrets
  namespace: quartz
type: Opaque
stringData:
  HANSEC_INVESTMENT_APP_KEY: "..."
  HANSEC_INVESTMENT_APP_SECRET_KEY: "..."
  HANSEC_INVESTMENT_CANO: "..."
  GPT_API_KEY: "..."
  GEMINI_API_KEY: "..."
  AWS_ACCESS_KEY_ID: "..."
  AWS_SECRET_ACCESS_KEY: "..."
```

### 3.3 서비스 디스커버리

k3s 내부 DNS를 통해 에이전트 간 통신:

```
┌─────────────────────────────────────────────────────────────────┐
│                     quartz namespace                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐   │
│  │ auth-agent   │      │ macro-agent  │      │ticker-selector│  │
│  │   :8006      │      │   :8001      │      │   :8002      │   │
│  └──────┬───────┘      └──────┬───────┘      └──────┬───────┘   │
│         │                     │                     │            │
│         └─────────────────────┼─────────────────────┘            │
│                               ↓                                  │
│                    ┌──────────────────┐                          │
│                    │ portfolio-manager │                         │
│                    │      :8004        │                         │
│                    └────────┬─────────┘                          │
│                             │ WebSocket                          │
│                             ↓                                    │
│                    ┌──────────────────┐                          │
│                    │  trading-agent   │                          │
│                    │     :8005        │                          │
│                    └──────────────────┘                          │
│                                                                  │
│  ┌──────────────┐                                                │
│  │technical-agent│                                               │
│  │   :8003      │                                                │
│  └──────────────┘                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 리소스 할당 및 프로브 설정

각 에이전트별 Deployment 예시 (Auth Agent):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-agent
  namespace: quartz
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: auth-agent
        image: quartz/auth-agent:latest
        ports:
        - containerPort: 8006
        envFrom:
        - configMapRef:
            name: quartz-config
        - secretRef:
            name: quartz-secrets
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
          limits:
            cpu: "200m"
            memory: "128Mi"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8006
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8006
          periodSeconds: 10
        startupProbe:
          httpGet:
            path: /health/live
            port: 8006
          failureThreshold: 30
```

#### 프로브 설계 전략
| 프로브 | 목적 | 체크 내용 |
|--------|------|-----------|
| **Liveness** | 프로세스 생존 확인 | HTTP 200 응답 |
| **Readiness** | 서비스 준비 완료 | 의존 서비스 연결 + 데이터 가용성 |
| **Startup** | 초기화 대기 | 토큰 발급 등 초기화 완료 |

### 3.5 Kustomize 배포

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: quartz

resources:
  - namespace.yaml
  - configmap.yaml
  - secret.yaml
  - auth-agent.yaml
  - macro-agent.yaml
  - ticker-selector.yaml
  - technical-agent.yaml
  - trading-agent.yaml
  - portfolio-manager.yaml
  - frontend.yaml

labels:
  - pairs:
      app.kubernetes.io/part-of: quartz
      app.kubernetes.io/managed-by: kustomize
```

배포 명령:
```bash
kubectl apply -k k8s/
```

---

## 4. 분산 시스템 특성 분석

### 4.1 일관성 (Consistency)

| 구성요소 | 일관성 모델 | 설명 |
|----------|-------------|------|
| 인증 토큰 | Strong Consistency | 단일 Auth Agent가 토큰 관리 |
| 시세 데이터 | Eventual Consistency | 5분 캐시 TTL |
| 후보 종목 | Eventual Consistency | S3를 통한 비동기 업데이트 |
| 주문 실행 | Strong Consistency | 동기 API 호출 |

### 4.2 가용성 (Availability)

```
┌──────────────────────────────────────────────────────────────┐
│                    장애 대응 전략                             │
├──────────────────────────────────────────────────────────────┤
│  Auth Agent 장애:                                             │
│  → 다른 에이전트들 readiness fail → 트래픽 차단               │
│  → k8s가 Pod 재시작                                           │
├──────────────────────────────────────────────────────────────┤
│  Macro Agent 장애:                                            │
│  → 캐시된 데이터 반환 (stale but available)                   │
│  → "uncertain" bias로 보수적 결정                             │
├──────────────────────────────────────────────────────────────┤
│  Technical Agent 장애:                                        │
│  → 해당 종목 분석 스킵                                        │
│  → 포트폴리오 결정 시 제외                                    │
├──────────────────────────────────────────────────────────────┤
│  Trading Agent 장애:                                          │
│  → WebSocket 재연결 시도                                      │
│  → HTTP API 백업 경로 사용                                    │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 분할 내성 (Partition Tolerance)

- **S3를 중간 저장소로 활용**: 에이전트 간 직접 통신 실패 시에도 S3를 통해 데이터 공유 가능
- **비동기 처리**: 실시간 통신 실패 시 다음 스케줄 주기에 재처리
- **Graceful Degradation**: 일부 데이터 누락 시에도 기본값으로 동작

### 4.4 CAP 정리 적용

```
           Consistency
              /\
             /  \
            /    \
           /  CA  \
          /________\
         /\        /\
        /  \  CP  /  \
       / AP \    /    \
      /______\  /______\
   Availability   Partition
                  Tolerance
```

**Quartz 시스템의 선택: AP (Availability + Partition Tolerance)**
- 주식 거래 시스템에서 가용성이 중요 (장 시간 내 거래 필수)
- 일시적 데이터 불일치보다 서비스 중단이 더 큰 리스크
- 최종적 일관성(Eventual Consistency)으로 수렴

---

## 5. 에이전트 간 통신 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           External Services                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │한국투자증권 │  │   AWS S3    │  │  OpenAI GPT │  │ Gemini API  │    │
│  │    API      │  │             │  │             │  │             │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
└─────────┼────────────────┼────────────────┼────────────────┼────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         quartz namespace (k3s)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌───────────┐                                                          │
│   │Auth Agent │◄──── 토큰 요청 ────┬────────┬────────┬────────┐         │
│   │   :8006   │                    │        │        │        │         │
│   └─────┬─────┘                    │        │        │        │         │
│         │                          │        │        │        │         │
│         │ 토큰                     │        │        │        │         │
│         ▼                          │        │        │        │         │
│   ┌───────────┐              ┌─────┴─────┐  │        │        │         │
│   │  Macro    │──S3 Upload──▶│           │  │        │        │         │
│   │  Agent    │              │   AWS S3  │  │        │        │         │
│   │   :8001   │◄─S3 Read────│           │  │        │        │         │
│   └─────┬─────┘              └─────┬─────┘  │        │        │         │
│         │                          ▲        │        │        │         │
│         │                          │        │        │        │         │
│   ┌───────────┐                    │        │        │        │         │
│   │  Ticker   │──S3 Upload─────────┘        │        │        │         │
│   │ Selector  │                             │        │        │         │
│   │   :8002   │                             │        │        │         │
│   └─────┬─────┘                             │        │        │         │
│         │                                   │        │        │         │
│         │     ┌───────────┐                 │        │        │         │
│         │     │ Technical │                 │        │        │         │
│         │     │  Agent    │─────────────────┘        │        │         │
│         │     │   :8003   │                          │        │         │
│         │     └─────┬─────┘                          │        │         │
│         │           │                                │        │         │
│         │           │ 기술분석                       │        │         │
│         │           │                                │        │         │
│         ▼           ▼                                │        │         │
│   ┌─────────────────────────────────────────────────┴────────┴───┐      │
│   │                   Portfolio Manager                           │      │
│   │                        :8004                                  │      │
│   │  ┌─────────────────────────────────────────────────────────┐ │      │
│   │  │  GPT 의사결정: macro + candidates + technical → 매매결정 │ │      │
│   │  └─────────────────────────────────────────────────────────┘ │      │
│   └─────────────────────────┬─────────────────────────────────────┘      │
│                             │                                            │
│                             │ WebSocket 주문                             │
│                             ▼                                            │
│   ┌─────────────────────────────────────────────────────────────┐       │
│   │                    Trading Agent                             │       │
│   │                        :8005                                 │       │
│   │  ┌─────────────────────────────────────────────────────────┐│       │
│   │  │  주문 실행: 한국투자증권 API → 매수/매도/취소            ││       │
│   │  └─────────────────────────────────────────────────────────┘│       │
│   └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 핵심 설계 패턴

### 6.1 사용된 분산 시스템 패턴

| 패턴 | 적용 위치 | 설명 |
|------|-----------|------|
| **Service Discovery** | k3s DNS | 내부 서비스명으로 자동 라우팅 |
| **Circuit Breaker** | HTTP 클라이언트 | 타임아웃 + 재시도 로직 |
| **Sidecar** | 각 에이전트 | 로깅, 모니터링 분리 가능 |
| **Event Sourcing** | S3 저장 | 분석 결과 이력 보관 |
| **CQRS** | 읽기/쓰기 분리 | 분석(조회) vs 거래(명령) 분리 |
| **Orchestrator** | Portfolio Manager | 다른 에이전트 조율 |
| **Gateway** | Frontend API Proxy | 외부 접근 통합 |

### 6.2 마이크로서비스 원칙 준수

1. **Single Responsibility**: 각 에이전트가 하나의 도메인 담당
2. **Loose Coupling**: REST/WebSocket + S3로 결합도 최소화
3. **High Cohesion**: 관련 기능이 동일 에이전트 내 응집
4. **Independently Deployable**: 각 에이전트 독립 배포 가능
5. **Decentralized Data**: 에이전트별 캐시 + 공유 S3

---

## 7. 결론

Quartz 프로젝트는 **차세대 분산 시스템**의 핵심 개념을 실제 금융 도메인에 적용한 사례입니다.

### 주요 특징
- **멀티 에이전트 아키텍처**: 6개의 독립적인 에이전트가 협력하여 복잡한 매매 의사결정 수행
- **k3s 기반 배포**: 경량 Kubernetes로 리소스 효율적인 컨테이너 오케스트레이션
- **환경 분리**: ConfigMap/Secret, Namespace로 설정과 보안 정보 분리
- **비동기 통신**: REST API + WebSocket + S3를 통한 유연한 통신 체계
- **장애 대응**: 프로브 설정, 재시도 로직, 폴백 메커니즘으로 가용성 확보

### 분산 시스템 학습 포인트
1. CAP 정리에서 AP 선택의 실제 구현
2. 서비스 디스커버리와 내부 DNS 활용
3. 이기종 언어(C++/Python) 통합
4. 이벤트 기반 + 스케줄 기반 하이브리드 처리
5. 컨테이너 오케스트레이션과 리소스 관리

---

*작성일: 2024년 12월*  
*Quartz v1.0.0*

