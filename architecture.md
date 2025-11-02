# Quartz - 멀티에이전트 자동투자 플랫폼 개발 설계 문서

## 1. 시스템 개요

### 1.1 프로젝트 정보
- **프로젝트명**: Quartz (멀티에이전트 자동투자 플랫폼)
- **팀**: 3팀 (강연욱, 정윤아, 이정빈)
- **목표**: Kubernetes 기반 멀티에이전트 아키텍처를 통한 완전 자동화 투자 파이프라인 구축

### 1.2 시스템 목표
거시경제, 기업가치, 기술분석을 통합한 멀티에이전트 자동투자 시스템을 구축하여, 각 에이전트가 전문 영역을 담당하고 포트폴리오 관리 에이전트에 보고함으로써 실시간 시장 상황에 대응하는 자동 투자를 수행한다.

### 1.3 핵심 해결 과제
- 백테스팅과 실거래 간 성능 격차 해소
- 실시간 시장 상황 및 비정형 이벤트 대응
- 시스템 안정성 및 장애 복구 자동화

---

## 2. 시스템 아키텍처

### 2.1 에이전트 간 연결
- **멀티에이전트 시스템 구조**: Quartz는 투자 의사결정 과정을 여러 단계로 분할하고, 각 단계를 전문화된 에이전트에 할당하는 멀티에이전트 아키텍처를 채택한다. 각 에이전트는 특정 업무에만 집중하여 전문성을 확보하고, 정보교환 시스템을 통해 하나의 유기적인 시스템을 구축한다.
- 에이전트 풀 내의 에이전트들을 통해 시장분석 데이터를 제공받고, 포트폴리오 관리 에이전트를 통해 시장 상황에 따라 현재 포트폴리오 내의 가용자금을 통해 거래 방식과 양을 산정(매도, 매수, 손절 및 익절)한다.
- 정보조사, 판단, 거래는 작은 동작으로 분할해 각각의 에이전트가 진행한다.

### 2.2 에이전트 풀
- **거시경제 분석 에이전트**: FRED/한국은행/IMF/OECD 등에서 지표 수집·정규화·Regime 분류(Risk-on/off 등) 후, 포트폴리오 관리 에이전트에 보고. 
- **거래 종목 선택 에이전트**: 기업 재무(OpenDART, Yahoo Finance 등에서 자료 수집), 실시간 뉴스 키워드, 헤드라인 수집을 통한 감성분석. 이를 통해 변동률이 클 투자 종목 또는 투자 가치가 있을 종목을 선택하고, 이를 포트폴리오 관리 에이전트에 보고. 
- **섹터 분석 에이전트**: 섹터 별 자료조사 및 시장 흐름 적합도를 산업 섹터 별 동향 분석을 통해 판단 후 포트폴리오 관리 에이전트에 보고.
- **차트 기술분석 에이전트**: Fibonacci Retracement(피보나치 되돌림), RSI, MACD, Bollinger Bands 등 기술 지표를 분석하여 종목 별로 기술 분석 결과를 포트폴리오 관리 에이전트에 보고.
- **거래 에이전트**: 브로커/거래소 API 연동(증권사 API)을 통해 실제 거래를 수행. 주문 라우팅·슬리피지/수수료 반영·포지션 동기화 작업을 진행 후, 포트폴리오 관리 에이전트에 결과 보고. 거래 자체도 포트폴리오 관리 에이전트에게서 명령을 받아 진행. 
- **포트폴리오 관리 에이전트**: 현재 자금 현황과 투자 종목 분석 결과, 거시경제 분석결과를 종합해 실제 거래 에이전트에 거래 명령을 전달. 

### 2.3 배포 전략
- **Blue-Green 배포**: Argo Rollouts을 활용한 무중단 배포
- **헬스체크**: Kubernetes Liveness/Readiness/Startup Probes
- **자동 스케일링**: HPA(Horizontal Pod Autoscaler) 적용

---

## 3. 에이전트 상세 설계

### 3.1 거시경제 분석 에이전트

**역할**: 거시경제 지표 수집 및 시장 레짐 분류

**주요 기능**:
- 경제 지표 수집
  - FRED API: 미국 금리, M2, RRP 등
  - IMF Data API: 국제 거시 데이터
  - OECD API: 국가별 고용·산업 지표
  - 한국은행 API: 국내 경제 지표
- ChatGPT API를 통한 지표 해석 및 시장 레짐 분류
  - Risk-on / Risk-off 판단
  - 경기 사이클 분석 (확장/침체)
  - 인플레이션/디플레이션 압력 평가

**데이터 파이프라인**:
```
외부 API → 데이터 수집 → 정규화 → ChatGPT 분석 → 포트폴리오 에이전트 전달
```

**기술 스택**:
- Python 3.12
- httpx (비동기 HTTP 클라이언트)
- numpy, pandas (데이터 정규화 및 벡터화 계산)
- OpenAI SDK (ChatGPT API)
- APScheduler (스케줄링)


---

### 3.2 거래 종목 선택 에이전트

**역할**: 투자 가치 있는 종목 선정 및 추천

**주요 기능**:
- 기업 재무 데이터 수집
  - OpenDART API: 국내 기업 재무제표
  - Yahoo Finance API: 글로벌 기업 데이터
- 실시간 뉴스 수집 및 감성 분석
  - 뉴스 헤드라인 크롤링
  - FinBERT를 통한 감성 분석 (긍정/부정/중립)
- ChatGPT API를 통한 종합 분석
  - 재무 건전성 평가
  - 뉴스 감성과 재무지표 통합 분석
  - 투자 가치 점수 산출

**분석 프로세스**:
```
재무제표 수집 → 뉴스 크롤링 → FinBERT 감성분석 → ChatGPT 종합분석 → 종목 추천 리스트 생성
```

**기술 스택**:
- Python 3.11+
- yfinance, dart-fss (데이터 수집)
- BeautifulSoup4 (뉴스 크롤링)
- OpenAI SDK

**배포 설정**:
```yaml
replicas: 3
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
schedule: "*/30 * * * *"  # 30분마다 실행
```

---

### 3.3 차트 기술분석 에이전트

**역할**: 기술적 지표 분석을 통한 매매 타이밍 제공

**주요 기능**:
- 기술 지표 계산
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands
  - Fibonacci Retracement
  - 이동평균선 (MA20, MA60, MA120)
- ChatGPT API를 통한 차트 패턴 해석
  - 지지/저항선 분석
  - 매매 신호 생성 (매수/매도/관망)
  - 리스크 레벨 평가

**분석 프로세스**:
```
실시간 시세 수집 → 기술지표 계산 → ChatGPT 패턴분석 → 매매신호 생성 → 신호 전달
```

**기술 스택**:
- Python 3.11+
- TA-Lib (기술 지표)
- pandas, numpy
- OpenAI SDK

**배포 설정**:
```yaml
replicas: 3
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
update_frequency: "1m"  # 1분마다 업데이트
```

---

### 3.4 거래 실행 에이전트

**역할**: 실제 주문 체결 및 포지션 관리

**주요 기능**:
- 증권사 API 연동
  - 한국투자증권, 키움증권, 이베스트투자증권 등
  - REST API 및 WebSocket 실시간 체결 수신
- 주문 라우팅
  - 시장가/지정가/조건부 주문 처리
  - 분할 매수/매도 로직
- 슬리피지 및 수수료 관리
  - 실제 체결가 추적
  - 수수료 자동 계산 및 반영
- 포지션 동기화
  - 실시간 보유 종목 확인
  - 손익 계산 및 기록

**거래 프로세스**:
```
포트폴리오 에이전트 명령 수신 → 주문 검증 → API 호출 → 체결 확인 → 결과 저장 및 보고
```

**기술 스택**:
- Python 3.11+
- 증권사 SDK
- asyncio (비동기 처리)
- PostgreSQL (거래 이력)

**배포 설정**:
```yaml
replicas: 2
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
high_availability: true
```

**에러 핸들링**:
- 재시도 로직 (exponential backoff)
- 주문 실패 시 포트폴리오 에이전트에 즉시 보고
- Dead Letter Queue 활용

---

### 3.5 포트폴리오 관리 에이전트 (Master Agent)

**역할**: 모든 에이전트 결과 통합 및 최종 의사결정

**주요 기능**:
- 에이전트 결과 수집 및 통합
  - 거시경제 상황
  - 종목 추천 리스트
  - 기술적 매매 신호
  - 현재 포지션 상태
- ChatGPT API를 통한 최종 의사결정
  - 각 에이전트 분석 결과 종합
  - 리스크 관리 및 포지션 사이징
  - 매매 전략 수립
- 거래 명령 발행
  - 매수/매도 주문 생성
  - 거래 에이전트에 명령 전달
- 성과 모니터링
  - 실시간 수익률 추적
  - 리스크 메트릭 계산

**의사결정 프로세스**:
```
각 에이전트 결과 수집 → ChatGPT 통합분석 → 포트폴리오 최적화 → 거래 명령 생성 → 실행 지시
```

**기술 스택**:
- Python 3.11+
- FastAPI (내부 API)
- OpenAI SDK (GPT-4 권장)
- Redis (에이전트 간 통신)

**배포 설정**:
```yaml
replicas: 2
resources:
  requests:
    memory: "1Gi"
    cpu: "1000m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
high_availability: true
```

---

## 4. 데이터 아키텍처

### 4.1 데이터베이스 설계

**PostgreSQL (주 데이터베이스)**:
```sql
-- 거래 이력
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE,
    ticker VARCHAR(20),
    side VARCHAR(10), -- BUY/SELL
    quantity INTEGER,
    price DECIMAL(10, 2),
    executed_at TIMESTAMP,
    agent_reason TEXT,
    profit_loss DECIMAL(10, 2)
);

-- 포지션
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE,
    quantity INTEGER,
    avg_price DECIMAL(10, 2),
    current_price DECIMAL(10, 2),
    unrealized_pnl DECIMAL(10, 2),
    updated_at TIMESTAMP
);

-- 에이전트 분석 결과
CREATE TABLE agent_reports (
    id SERIAL PRIMARY KEY,
    agent_type VARCHAR(50),
    report_data JSONB,
    created_at TIMESTAMP
);
```

**TimescaleDB (시계열 데이터)**:
```sql
-- 시세 데이터
CREATE TABLE market_data (
    time TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(20),
    open DECIMAL(10, 2),
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    close DECIMAL(10, 2),
    volume BIGINT
);
SELECT create_hypertable('market_data', 'time');

-- 포트폴리오 가치 추적
CREATE TABLE portfolio_value (
    time TIMESTAMPTZ NOT NULL,
    total_value DECIMAL(15, 2),
    cash DECIMAL(15, 2),
    positions_value DECIMAL(15, 2)
);
SELECT create_hypertable('portfolio_value', 'time');
```

**Redis (캐시 및 실시간 데이터)**:
- Key patterns:
  - `market:{ticker}:price` - 실시간 가격
  - `agent:{type}:latest` - 최신 분석 결과
  - `signal:{ticker}` - 매매 신호
  - `macro:regime` - 거시경제 레짐

### 4.2 메시지 큐 설계

**RabbitMQ/Redis Pub-Sub**:
- Exchanges:
  - `agent.reports` - 에이전트 보고서
  - `trading.commands` - 거래 명령
  - `trading.results` - 거래 결과
  - `alerts` - 알림 및 경고

---

## 5. API 설계

### 5.1 내부 API (에이전트 간 통신)

**포트폴리오 관리 에이전트 API**:
```
POST /api/v1/reports/macro
POST /api/v1/reports/stock-selection
POST /api/v1/reports/technical-analysis
GET  /api/v1/portfolio/current
GET  /api/v1/portfolio/performance
```

**거래 에이전트 API**:
```
POST /api/v1/orders
GET  /api/v1/orders/{order_id}
GET  /api/v1/positions
```

### 5.2 외부 API 연동

**ChatGPT API 사용 패턴**:

1. **거시경제 분석**:
```python
prompt = f"""
다음 경제 지표를 분석하여 현재 시장 레짐을 판단해주세요:
- 금리: {interest_rate}
- 실업률: {unemployment}
- GDP 성장률: {gdp_growth}
- CPI: {cpi}

Risk-on/Risk-off 상태와 투자 전략을 제시해주세요.
"""
```

2. **종목 선택**:
```python
prompt = f"""
다음 기업의 투자 가치를 평가해주세요:
- 기업명: {company_name}
- PER: {per}, PBR: {pbr}, ROE: {roe}
- 최근 뉴스 감성: {sentiment_score}
- 재무 건전성: {financial_health}

투자 추천 여부와 이유를 설명해주세요.
"""
```

3. **기술 분석**:
```python
prompt = f"""
다음 기술 지표를 바탕으로 {ticker}의 매매 타이밍을 분석해주세요:
- RSI: {rsi}
- MACD: {macd}
- Bollinger Bands: 현재가가 {band_position}
- 피보나치: {fib_level}

매수/매도/관망 중 추천과 진입/손절 가격을 제시해주세요.
"""
```

4. **포트폴리오 최적화**:
```python
prompt = f"""
다음 정보를 종합하여 포트폴리오 조정 전략을 수립해주세요:
- 거시경제: {macro_analysis}
- 추천 종목: {recommended_stocks}
- 기술적 신호: {technical_signals}
- 현재 포지션: {current_positions}
- 가용 자금: {available_cash}

리스크 관리를 고려한 매매 계획을 수립해주세요.
"""
```

---

## 6. 프론트엔드 설계

### 6.1 기술 스택
- React 18+
- TypeScript
- Recharts (차트 라이브러리)
- TanStack Query (데이터 페칭)
- Zustand (상태 관리)
- Tailwind CSS (스타일링)

### 6.2 주요 화면 구성

**1. 대시보드 메인**:
- 실시간 포트폴리오 가치
- 당일/누적 수익률
- 보유 종목 비중 파이차트
- 최근 거래 내역

**2. 거시경제 분석 페이지**:
- 주요 경제 지표 시각화
- 현재 시장 레짐 상태
- 섹터별 추천 비중

**3. 종목 분석 페이지**:
- 추천 종목 리스트
- 각 종목별 분석 근거
- 뉴스 감성 분석 결과

**4. 기술 분석 페이지**:
- 실시간 차트 (캔들스틱)
- 기술 지표 오버레이
- 매매 신호 표시

**5. 거래 내역 페이지**:
- 주문 ID, 체결가/수량
- 재시도/오류 사유
- 필터링 및 검색

**6. 모니터링 페이지**:
- 에이전트 상태 (헬스체크)
- API 호출 성공률
- 시스템 리소스 사용량

---

## 7. DevOps 및 운영

### 7.1 Kubernetes 리소스 구성

**Namespace**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: quartz-trading
```

**ConfigMap (환경 설정)**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: quartz-config
  namespace: quartz-trading
data:
  REDIS_HOST: "redis-service"
  POSTGRES_HOST: "postgres-service"
  OPENAI_API_ENDPOINT: "https://api.openai.com/v1"
```

**Secret (API 키)**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: quartz-secrets
  namespace: quartz-trading
type: Opaque
data:
  OPENAI_API_KEY: <base64-encoded>
  BROKER_API_KEY: <base64-encoded>
  BROKER_API_SECRET: <base64-encoded>
```

### 7.2 Deployment 예시 (포트폴리오 에이전트)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: portfolio-agent
  namespace: quartz-trading
spec:
  replicas: 2
  selector:
    matchLabels:
      app: portfolio-agent
  template:
    metadata:
      labels:
        app: portfolio-agent
    spec:
      containers:
      - name: portfolio-agent
        image: quartz/portfolio-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: quartz-secrets
              key: OPENAI_API_KEY
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 5
```

### 7.3 Service 및 Ingress

```yaml
apiVersion: v1
kind: Service
metadata:
  name: portfolio-agent-service
  namespace: quartz-trading
spec:
  selector:
    app: portfolio-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: quartz-ingress
  namespace: quartz-trading
spec:
  rules:
  - host: quartz.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: portfolio-agent-service
            port:
              number: 80
```

### 7.4 Argo Rollouts (Blue-Green 배포)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: portfolio-agent-rollout
  namespace: quartz-trading
spec:
  replicas: 2
  strategy:
    blueGreen:
      activeService: portfolio-agent-active
      previewService: portfolio-agent-preview
      autoPromotionEnabled: false
      scaleDownDelaySeconds: 30
  selector:
    matchLabels:
      app: portfolio-agent
  template:
    metadata:
      labels:
        app: portfolio-agent
    spec:
      containers:
      - name: portfolio-agent
        image: quartz/portfolio-agent:latest
        # ... (동일한 컨테이너 설정)
```

### 7.5 모니터링 및 로깅

**Prometheus + Grafana**:
- 에이전트별 CPU/메모리 사용량
- API 응답 시간
- 주문 성공/실패율
- 데이터 수집 지연 시간

**ELK Stack (Elasticsearch + Logstash + Kibana)**:
- 모든 에이전트 로그 집중화
- 거래 이력 검색
- 에러 트래킹

**알림 설정**:
- 에이전트 다운 감지
- API 호출 실패율 임계치 초과
- 주문 체결 실패
- 비정상적인 손실 발생

---

## 8. 성능 지표 및 평가

### 8.1 정량적 지표

**거래 성과**:
- 체결 성공률: 95% 이상 목표
- 실 수익률: 벤치마크(KOSPI/S&P500) 대비 초과 수익
- 샤프 비율: 1.5 이상 목표
- 최대 낙폭(MDD): 15% 이내

**운영 지표**:
- 주문 성공률: 98% 이상
- 에이전트 가용성: 99.9% (three nines)
- 데이터 지연: 평균 5초 이내
- API 응답 시간: P95 < 500ms

### 8.2 평가 방법

**백테스팅**:
- 과거 3년 데이터로 전략 검증
- Walk-forward 분석

**페이퍼 트레이딩**:
- 최소 3개월 모의 거래
- 실거래 환경과 동일한 조건

**실거래 단계적 확대**:
- Phase 1: 소액 자금 (100만원)
- Phase 2: 중액 자금 (1000만원)
- Phase 3: 본격 운영

---

## 9. 리스크 관리

### 9.1 기술적 리스크

**장애 대응**:
- 에이전트 자동 재시작 (Kubernetes probes)
- 데이터베이스 레플리케이션
- 주기적 백업 (일 1회)

**API 장애**:
- Circuit breaker 패턴 적용
- Fallback 로직 구현
- Rate limiting 준수

### 9.2 거래 리스크

**손실 제한**:
- 종목당 최대 손실률 설정 (5%)
- 일일 최대 손실률 제한 (2%)
- 긴급 중단 메커니즘

**포지션 관리**:
- 단일 종목 최대 비중 제한 (20%)
- 섹터 분산 투자
- 현금 비중 유지 (최소 10%)

---


## 11. 참고 자료

### 논문 및 기술 문서
- FinBERT: Financial Sentiment Analysis with Pre-trained Language Models
- Kubernetes Documentation: Configure Liveness, Readiness and Startup Probes
- Argo Rollouts: Progressive Delivery for Kubernetes

### API 문서
- OpenAI API Documentation
- FRED API: https://fred.stlouisfed.org/docs/api/
- IMF Data API: https://datahelp.imf.org/knowledgebase/articles/667681
- OECD API: https://data.oecd.org/api/
- 한국은행 경제통계시스템 API
- OpenDART API: https://opendart.fss.or.kr/

### 증권사 API
- 한국투자증권 Open API

