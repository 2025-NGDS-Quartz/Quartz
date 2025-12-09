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

### 1.4 운영 환경: 실제 환경 (실전투자)
- **거래 가능 시간**: 평일 09:00~15:30 (한국 시간, KST)
- **시스템 시작**: 매일 08:30 (사전 준비), 종료: 16:00

---

## 2. 시스템 아키텍처

### 2.1 에이전트 간 연결
- **멀티에이전트 시스템 구조**: Quartz는 투자 의사결정 과정을 여러 단계로 분할하고, 각 단계를 전문화된 에이전트에 할당하는 멀티에이전트 아키텍처를 채택한다. 각 에이전트는 특정 업무에만 집중하여 전문성을 확보하고, 정보교환 시스템을 통해 하나의 유기적인 시스템을 구축한다.
- 에이전트 풀 내의 에이전트들을 통해 시장분석 데이터를 제공받고, 포트폴리오 관리 에이전트를 통해 시장 상황에 따라 현재 포트폴리오 내의 가용자금을 통해 거래 방식과 양을 산정(매도, 매수, 손절 및 익절)한다.
- 정보조사, 판단, 거래는 작은 동작으로 분할해 각각의 에이전트가 진행한다.

### 2.2 에이전트 서비스 포트 및 k3s 서비스명

| 에이전트 | 포트 | k3s Service 이름 | 내부 DNS |
|---------|------|------------------|----------|
| 거시경제 분석 | 8001 | macro-agent | macro-agent.quartz.svc.cluster.local |
| 거래종목 선택 | 8002 | ticker-selector | ticker-selector.quartz.svc.cluster.local |
| 기술분석 | 8003 | technical-agent | technical-agent.quartz.svc.cluster.local |
| 포트폴리오 관리 | 8004 | portfolio-manager | portfolio-manager.quartz.svc.cluster.local |
| 거래 | 8005 | trading-agent | trading-agent.quartz.svc.cluster.local |
| 인증관리 | 8006 | auth-agent | auth-agent.quartz.svc.cluster.local |

- 모든 에이전트는 `quartz` namespace에 배포
- 클러스터 내부 통신은 Service DNS 사용 (예: `http://auth-agent:8006/result/auth-token`)

### 2.3 배포 전략
- **Blue-Green 배포**: Argo Rollouts을 활용한 무중단 배포
- **헬스체크**: Kubernetes Liveness/Readiness/Startup Probes
- **자동 스케일링**: HPA(Horizontal Pod Autoscaler) 적용

### 2.4 공통 환경변수

모든 에이전트에서 공유하는 환경변수:

| 환경변수 | 설명 | 예시 |
|---------|------|------|
| `HANSEC_INVESTMENT_APP_KEY` | 한국투자증권 앱 키 | - |
| `HANSEC_INVESTMENT_APP_SECRET_KEY` | 한국투자증권 앱 시크릿 | - |
| `HANSEC_INVESTMENT_CANO` | 계좌번호 앞 8자리 | `12345678` |
| `HANSEC_INVESTMENT_ACNT_PRDT_CD` | 계좌상품코드 뒤 2자리 | `01` |
| `AWS_ACCESS_KEY_ID` | AWS 액세스 키 | - |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 키 | - |
| `AWS_REGION` | AWS 리전 | `ap-northeast-2` |
| `S3_BUCKET_NAME` | S3 버킷명 | `quartz-bucket` |
| `OPENAI_API_KEY` | OpenAI API 키 (GPT 호출용) | - |
| `GEMINI_API_KEY` | Gemini API 키 (거시경제 에이전트용) | - |

### 2.5 한국투자증권 API 기본 URL

| 환경 | Base URL |
|------|----------|
| 실전투자 | `https://openapi.koreainvestment.com:9443` |

### 2.6 공통 헬스체크 엔드포인트

모든 에이전트는 다음 엔드포인트를 제공:
- `GET /health/live` - Liveness probe (응답: `{"status": "ok"}`)
- `GET /health/ready` - Readiness probe (의존성 체크 포함)

---

## 3. 에이전트 상세 설계

### 3.0 에이전트 간 호출 관계, 전체 아키텍처

- 모든 에이전트는 k3s를 통해 한 인스턴스 내에서 동작. 각 인스턴스 별로 별도의 이미지로 빌드, 각 포드 간의 통신을 통해 작업이 이뤄짐
- 거시경제에이전트는 1시간에 한번씩 gemini search grounded api 를 사용해서 뉴스 감성분석 진행, 거시경제 보고서 작성 후 긍정적 관점의 보고서, 부정적 관점의 보고서를 각각 하나씩 S3 버킷에 올림. Report_Negative_{YYYYMMDDhhmmss}.md, Report_Positive_{YYYYMMDDhhmmss}.md 두가지
- 거래종목 선택 에이전트는 뉴스 감성 분석을 통해 거래할 후보 종목들을 선정해서 파일로 정리(파일은 백업없이 갱신, 요청이 들어오면 파일의 내용을 읽어서 반환)
- 포트폴리오 에이전트는 거래종목 선택 에이전트와 거시경제에이전트에게 각각 GET으로 거시경제 분위기와 종목을 받는다. (30분에 한번)
- 포트폴리오 에이전트는 받은 종목들의 ticker를 기술적 분석 에이전트와 기업분석 에이전트에 POST 요청으로 전달해서 각 종목 별 기술분석과 기업분석을 진행하고 결과를 반환받음
- 거시경제, 기술분석 및 기업분석을 통해 거래 여부를 결정하고 운용가능 자금을 분산해서 거래 에이전트에게 구매 명령(WebSocket) 전달 (보유 금액이 적으면 구매하지 않음)
- 포트폴리오에이전트는 위 작업과 별개로 (거래량을 보고있다가 거래량이 많을 때에는 5분, 거래량이 적을 때에는 10분에 한번씩) 현재 포트폴리오(보유주식과 운용가능자금)을 파악하고 보유주식들에 대해 매도 여부를 결정
  - 현재 보유주식들의 상승여력 분석(현재 수익률, 거시경제분석결과, 보유주식들에 대한 기술적 분석결과, 기업분석 결과 종합)
  - 매도, 보유여부 결정
- 각 에이전트는 거래할 때마다 인증 에이전트한테 auth 토큰 받아야 함



---


### 3.1 거시경제 분석 에이전트
- C++로 작성된 CLI 프로그램 (macroAnalysisAgent 폴더 내의 내용을 사용)
- 한국(ECOS), 미국(FRED), 글로벌(World Bank) 거시경제 데이터를 수집하여 Gemini 3 API + Google Search Grounding으로 보고서 생성, AWS S3에 업로드

- **아키텍처 구성**
  - `main.cpp`: 핵심 로직 (데이터 수집, 보고서 생성)
  - `S3Uploader.cpp/h`: AWS SDK를 통한 S3 업로드

- **데이터 소스**
  - **한국 ECOS API** (월별)
    - 기준금리 (722Y001/0101000)
    - 근원물가 (901Y010/DB) - 식료품 및 에너지 제외
    - 원-달러 환율 (731Y004/0000001/0000100)
    - 수출입 총괄 (901Y118/T002, T004)
    - 가계대출 (151Y005/11110A0) - 주택담보대출
  - **미국 FRED API** (월별, 선택적)
    - 연방기금금리 (FEDFUNDS)
    - 소비자물가지수 (CPIAUCSL)
  - **World Bank API** (연간)
    - 세계 GDP 성장률 (NY.GDP.MKTP.KD.ZG)
    - 세계 인플레이션 (FP.CPI.TOTL.ZG)
    - 미국 GDP 성장률 (NY.GDP.MKTP.KD.ZG)
    - 미국 인플레이션 (FP.CPI.TOTL.ZG)

- **보고서 생성**
  - 사용 모델: `gemini-3-pro-preview` + Google Search Grounding
  - 긍정 보고서: 성장 모멘텀, 정책 여력, 연착륙(soft-landing) 시나리오 강조
  - 부정 보고서: 인플레이션 리스크, 부채 부담, 외부 취약성, 경착륙(hard-landing) 시나리오 경고
  - 요약 보고서: 전체 보고서를 한국어 10문장 이내로 요약 (`_short` 접미사)
  - 기본값: 전체 보고서 `temperature: 0.4`, 요약 `temperature: 0.3`
  - thinkingConfig: `thinkingLevel: low`

- **보고서 구성**
  - 개요 (현재 세계/한국 거시환경 요약)
  - 한국 평가 (금리, 물가, 환율, 수출입, 가계부채)
  - 미국 및 주요국 평가 (금리, 물가, 성장)
  - 시나리오별 (낙관/기준/비관) 시장 영향과 자산별 (주식, 채권, 환율) 함의
  - 포트폴리오 관점에서의 시사점

- **프롬프트**
  - 긍정 보고서:
    ```
    You are an optimistic macroeconomist. Focus on growth opportunities, 
    resilience, and soft-landing scenarios.
    Use ONLY data trends provided below plus grounded information from Google Search.
    Combine Korean macro data (ECOS), US macro data (FRED), and global indicators (World Bank).
    Write a professional markdown report in Korean, including:
    - 개요 (현재 세계/한국 거시환경 요약)
    - 한국(금리, 물가, 환율, 수출입, 가계부채)에 대한 평가
    - 미국 및 주요국(금리, 물가, 성장)에 대한 평가
    - 시나리오별(낙관/기준/비관) 시장 영향과 자산별(주식, 채권, 환율) 함의
    - 포트폴리오 관점에서의 시사점
    [DATA]
    {CSV 데이터}
    ```
  - 부정 보고서:
    ```
    You are a risk-focused macro strategist. Focus on inflation risks, 
    debt overhang, external vulnerability, and hard-landing scenarios.
    (이하 동일 구조)
    ```
  - 긍정 요약:
    ```
    다음의 거시경제 긍정 보고서를 한국어로 10문장이내로 요약해줘.
    핵심 성장 모멘텀, 정책 여력, 리스크 완화 요인에 집중해.
    추가 설명 없이 요약문만 출력해.
    [Report]
    {전체 보고서}
    ```
  - 부정 요약:
    ```
    다음의 거시경제 리스크 보고서를 한국어로 10문장이내로 요약해줘.
    핵심 리스크, 취약 구간, 꼬리위험(tail risk)에 집중해.
    추가 설명 없이 요약문만 출력해.
    [Report]
    {전체 보고서}
    ```

- **S3 업로드**
  - 버킷: `quartz-bucket`
  - 리전: `ap-northeast-2`
  - 전체 보고서: `Report_Positive_{YYYYMMDD_hhmmss}.md`, `Report_Negative_{YYYYMMDD_hhmmss}.md`
  - 요약 보고서: `Report_Positive_{YYYYMMDD_hhmmss}_short.md`, `Report_Negative_{YYYYMMDD_hhmmss}_short.md` (10문장 이내)
  - **다른 에이전트에서는 `_short` 요약 버전을 사용**

- **환경 변수**
  - `ECOS_API_KEY`: ECOS API 키 (필수)
  - `GEMINI_API_KEY`: Gemini API 키 (필수)
  - `FRED_API_KEY`: FRED API 키 (선택, 없으면 미국 지표 생략)

- **의존성**
  - libcurl: HTTP 요청
  - nlohmann/json: JSON 파싱
  - AWS SDK for C++: S3 업로드


### 3.2 거래종목 선택 에이전트
- python 3.12에서 작동.
- 뉴스 크롤링 → 종목 매칭 → 감성 분석 → 종목별 집계 파이프라인을 통해 거래 후보 종목 선정
- (stockSelectionAgent 폴더 내의 내용을 사용)

- **실행 방법**
  - `python run.py`로 API 서버와 스케줄러 동시 실행
  - API 서버: http://localhost:8000
  - 스케줄러: 1시간마다 (매시 정각) 자동 실행

- **아키텍처 구성**
  - `news_crawler.py`: 멀티 소스 뉴스 크롤링 (네이버, 한경, 매경)
  - `stock_matcher.py`: 뉴스에서 종목 코드 매칭
  - `sentiment/sentiment_analyzer.py`: GPT 기반 감성 분석
  - `stock_aggregator.py`: 종목별 뉴스 집계 및 점수 계산
  - `news_pipeline.py`: 전체 파이프라인 통합
  - `scheduler.py`: 자동화 스케줄러 (APScheduler)
  - `api_server.py`: FastAPI 기반 REST API

- **API 엔드포인트**
  - `POST /api/candidates` - 거래 후보 종목 리스트 반환 (기본 5개, 중요도 기반 필터링)
    - request body: `top_n` (int, 선택, 기본값: 5, 최대: 10)
    - response:
      ```json
      {
        "timestamp": "2024-01-15T09:30:00",
        "total_stocks": 45,
        "statistics": {
          "high_priority": 5,
          "mid_priority": 15,
          "low_priority": 25
        },
        "top_candidates": [
          {
            "ticker": "005930",
            "name": "삼성전자",
            "sector": "전기전자",
            "avg_sentiment": 0.75,
            "news_count": 5,
            "positive_count": 4,
            "negative_count": 0,
            "neutral_count": 1,
            "positive_ratio": 0.8,
            "negative_ratio": 0.0,
            "neutral_ratio": 0.2,
            "priority": "HIGH",
            "market_cap_tier": "LARGE",
            "reasoning": "평균 감성 0.75(긍정적), 총 5개 뉴스, 긍정 4개, 부정 0개",
            "top_headlines": ["삼성전자, 3분기 영업이익 10조원 돌파"],
            "final_score": 0.725
          }
        ]
      }
      ```
  - `GET /api/statistics` - 전체 통계 정보
  - `GET /api/candidates/{ticker}` - 특정 종목 상세 정보
  - `GET /health` - 헬스체크

- **데이터 소스 및 분석 방법**
  - 뉴스 크롤링 소스: 네이버 금융, 한국경제, 매일경제
  - 1시간마다 크롤링 및 감성 분석 실행 (매시 정각)
  - 종목 매칭: 종목 사전 기반 + 정규식 패턴 매칭

- **데이터 저장 구조**
  - 크롤링 뉴스: `data/news_raw/{날짜}_{시간}.json`
  - 처리된 뉴스: `data/processed/processed_{날짜}_{시간}.json`
  - 후보 종목: `data/stock_candidates.json`
  - 감성 캐시: `data/sentiment_cache.json`
  - 로그: `data/logs/`

- **후보 종목 파일 형식** (`data/stock_candidates.json`)
  ```json
  {
    "timestamp": "2024-01-15T09:30:00",
    "total_stocks": 45,
    "statistics": {
      "high_priority": 5,
      "mid_priority": 15,
      "low_priority": 25
    },
    "top_candidates": [...],  // 최대 5개, 중요도 순 정렬
    "all_stocks": {...}
  }
  ```

- **우선순위 결정 로직**
  - HIGH: 평균 감성 0.7 이상 + 뉴스 3개 이상
  - MID: 평균 감성 0.5 이상 + 뉴스 2개 이상
  - LOW: 그 외

- **시총 등급 (market_cap_tier)**
  - LARGE: 시총 10조원 이상 (대형주)
  - MID: 시총 1조~10조원 (중형주)
  - SMALL: 시총 1조원 미만 (소형주)

- **중요도 점수 계산 (final_score)** - 최대 5개 종목 선정
  - 시총 등급 가중치: 25% (LARGE=1.0, MID=0.6, SMALL=0.3)
  - 감성 분석 점수: 40%
  - 뉴스 언급 횟수: 25% (최대 10개 기준 정규화)
  - 우선순위: 10% (HIGH=1.0, MID=0.6, LOW=0.3)

- **감성 분석 프롬프트**
  ```markdown
  다음 뉴스 헤드라인들에 대해 감성 분석을 수행하세요.

  헤드라인 목록:
  [헤드라인 JSON 배열]

  각 헤드라인에 대해 다음 정보를 JSON 배열로 반환하세요:

  1. sentiment: "positive" (긍정), "negative" (부정), "neutral" (중립)
  2. score: 0.0~1.0 사이 점수 (0=매우 부정, 0.5=중립, 1.0=매우 긍정)
  3. confidence: 0.0~1.0 사이 신뢰도
  4. reasoning: 간단한 분석 이유 (20자 이내)

  분석 기준:
  - 실적 호조, 수익 증가, 성장 등 → 긍정
  - 실적 부진, 손실, 하락 등 → 부정
  - 단순 사실 전달, 중립적 표현 → 중립

  반드시 다음 형식의 JSON만 반환하세요:
  [
    {
      "headline": "원본 헤드라인",
      "sentiment": "positive",
      "score": 0.75,
      "confidence": 0.85,
      "reasoning": "분석 이유"
    },
    ...
  ]
  ```

- **GPT 호출 스펙**
  - 사용 모델명: `gpt-4o-mini`
  - 호출 주기: 1시간 (매시 정각)
  - 배치 사이즈: 20개 헤드라인씩
  - 기본값: `temperature: 0.3`, `max_tokens: 2000`
  - 캐싱: MD5 해시 기반 캐시로 중복 분석 방지

- **환경 변수**
  - `GPT_API_KEY`: OpenAI API 키 (필수)


### 3.3 기술분석 에이전트
- python 3.12에서 작동.
- ticker를 전달하면 ticker들의 7개 일, 10개 주, 10개 월 별 RSI, MACD, Bollinger-Band, 피보나치되돌림, MA값을 계산해서 현재가 데이터와 함께 aws S3 버킷(quartz-bucket)의 technical-analysis 폴더 내에 json 형식으로 업로드
- `/result/analysis` 로 api 요청 가능. 포트폴리오 관리 에이전트가 기술분석을 요청함
  - request (POST)
    - ```
      json
      {
        "ticker": "005930"
      }
      ```
  - response
    - ```
      json
      {
        "ticker": "005930",
        "current_price": 78100,
        "analysis_time": "2024-01-15T09:30:00Z",
        "day": {
          "rsi": 55.2,
          "ma": {
            "ma5": 77500,
            "ma10": 76800,
            "ma20": 75200
          },
          "macd": {
            "macd_line": 1250.5,
            "signal_line": 1100.2,
            "histogram": 150.3,
            "signal": "bullish"
          },
          "bollinger_band": {
            "top": 82000,
            "middle": 77000,
            "bottom": 72000
          },
          "fibonacci_retracement": {
            "trend": "up",
            "levels": {
              "level_0": 70000,
              "level_236": 72360,
              "level_382": 73820,
              "level_500": 75000,
              "level_618": 76180,
              "level_786": 77860,
              "level_100": 80000
            }
          }
        },
        "week": {
          "rsi": 48.5,
          "ma": { "ma5": 76000, "ma10": 74500, "ma20": 73000 },
          "macd": { "macd_line": 800.0, "signal_line": 750.0, "histogram": 50.0, "signal": "bullish" },
          "bollinger_band": { "top": 85000, "middle": 75000, "bottom": 65000 },
          "fibonacci_retracement": { "trend": "up", "levels": { "...": "..." } }
        },
        "month": {
          "rsi": 52.1,
          "ma": { "ma5": 74000, "ma10": 72000, "ma20": 70000 },
          "macd": { "macd_line": 500.0, "signal_line": 480.0, "histogram": 20.0, "signal": "neutral" },
          "bollinger_band": { "top": 90000, "middle": 75000, "bottom": 60000 },
          "fibonacci_retracement": { "trend": "sideway", "levels": { "...": "..." } }
        }
      }
      ```

- **데이터 소스: 한국투자증권 API**
  - **국내주식기간별시세(일/주/월/년)** (v1_국내주식-016)
    - URL: `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice`
    - Method: GET
    - TR_ID: `FHKST03010100` (실전/모의 동일)
  - **Request Query Parameters**:
    | Parameter | 설명 | 예시 |
    |-----------|------|------|
    | `FID_COND_MRKT_DIV_CODE` | 시장 구분 | J (KRX), NX (NXT) |
    | `FID_INPUT_ISCD` | 종목코드 | 005930 |
    | `FID_INPUT_DATE_1` | 조회 시작일 | 20240101 |
    | `FID_INPUT_DATE_2` | 조회 종료일 | 20240115 |
    | `FID_PERIOD_DIV_CODE` | 기간 구분 | D (일), W (주), M (월), Y (년) |
    | `FID_ORG_ADJ_PRC` | 수정주가 여부 | 0 (수정주가), 1 (원주가) |
  - **Response 주요 필드 (output2 배열)**:
    | 필드 | 설명 | 사용 용도 |
    |------|------|----------|
    | `stck_bsop_date` | 영업일자 | 날짜 기준 |
    | `stck_clpr` | 종가 | RSI, MACD, MA 계산 |
    | `stck_oprc` | 시가 | 캔들 차트 |
    | `stck_hgpr` | 고가 | 볼린저밴드, 피보나치 |
    | `stck_lwpr` | 저가 | 볼린저밴드, 피보나치 |
    | `acml_vol` | 거래량 | 거래량 분석 |
  - **output1 주요 필드 (현재가 정보)**:
    | 필드 | 설명 |
    |------|------|
    | `stck_prpr` | 현재가 |
    | `prdy_vrss` | 전일대비 |
    | `prdy_ctrt` | 전일대비율 |
    | `per` | PER |
    | `pbr` | PBR |
    | `eps` | EPS |
  - **지표 계산 로직**:
    ```python
    # 일봉 100개 조회 후 지표 계산
    daily_data = fetch_daily_chart(ticker, "D", 100)
    rsi_14 = calculate_rsi(daily_data['close'], period=14)
    macd = calculate_macd(daily_data['close'], fast=12, slow=26, signal=9)
    bb = calculate_bollinger(daily_data['close'], period=20, std_dev=2)
    fib = calculate_fibonacci(daily_data['high'], daily_data['low'])
    ```

- **지표 계산 파라미터**

| 지표 | 파라미터 |
|------|---------|
| RSI | period=14 |
| MACD | fast=12, slow=26, signal=9 |
| Bollinger Band | period=20, std_dev=2 |
| MA | periods=[5, 10, 20] |
| Fibonacci | 최근 고점/저점 기준 되돌림 레벨 계산 |

- **S3 저장 경로**: `s3://quartz-bucket/technical-analysis/{ticker}_{YYYYMMDDhhmmss}.json`
- **캐싱**: 동일 ticker에 대해 5분 이내 재요청 시 캐시된 결과 반환


### 3.4 포트폴리오 관리 에이전트
- python 3.12에서 작동.
- 현재 포트폴리오 확인 및 거래 에이전트와 websocket으로 이어져 거래 명령 전달

- **한국투자증권 API 사용**

  - **주식잔고조회** (v1_국내주식-006)
    - URL: `/uapi/domestic-stock/v1/trading/inquire-balance`
    - Method: GET
    - TR_ID: `TTTC8434R` (실전), `VTTC8434R` (모의)
    - Query Parameters:
      | Parameter | 값 | 설명 |
      |-----------|-----|------|
      | `CANO` | 계좌번호 앞8자리 | 필수 |
      | `ACNT_PRDT_CD` | 01 | 계좌상품코드 |
      | `AFHR_FLPR_YN` | N | 시간외단일가 여부 |
      | `INQR_DVSN` | 02 | 조회구분 (02=종목별) |
      | `UNPR_DVSN` | 01 | 단가구분 |
      | `FUND_STTL_ICLD_YN` | N | 펀드결제분포함여부 |
      | `FNCG_AMT_AUTO_RDPT_YN` | N | 융자금액자동상환여부 |
      | `PRCS_DVSN` | 00 | 처리구분 (00=전일매매포함) |
    - Response 주요 필드 (output1 - 보유종목 배열):
      | 필드 | 설명 | GPT 입력 매핑 |
      |------|------|--------------|
      | `pdno` | 종목코드 | `positions[i].ticker` |
      | `prdt_name` | 종목명 | `positions[i].name` |
      | `hldg_qty` | 보유수량 | `positions[i].shares` |
      | `pchs_avg_pric` | 매입평균가 | `positions[i].avg_price` |
      | `prpr` | 현재가 | `positions[i].current_price` |
      | `evlu_amt` | 평가금액 | `positions[i].eval_amount` |
      | `evlu_pfls_rt` | 평가손익율 | `positions[i].profit_loss_rate` |
    - Response 주요 필드 (output2 - 계좌요약):
      | 필드 | 설명 |
      |------|------|
      | `dnca_tot_amt` | 예수금총금액 |
      | `tot_evlu_amt` | 총평가금액 |
      | `scts_evlu_amt` | 유가평가금액 |
      | `evlu_pfls_smtl_amt` | 평가손익합계 |

  - **매수가능조회** (v1_국내주식-007)
    - URL: `/uapi/domestic-stock/v1/trading/inquire-psbl-order`
    - Method: GET
    - TR_ID: `TTTC8908R` (실전), `VTTC8908R` (모의)
    - Query Parameters:
      | Parameter | 설명 |
      |-----------|------|
      | `PDNO` | 종목코드 (6자리) |
      | `ORD_UNPR` | 주문단가 (시장가는 "0") |
      | `ORD_DVSN` | 01 (시장가) - 증거금율 반영됨 |
      | `CMA_EVLU_AMT_ICLD_YN` | N |
      | `OVRS_ICLD_YN` | N |
    - Response 주요 필드:
      | 필드 | 설명 | GPT 입력 매핑 |
      |------|------|--------------|
      | `ord_psbl_cash` | 주문가능현금 | `portfolio.cash_krw` |
      | `nrcvb_buy_amt` | 미수없는매수금액 | 실제 매수 가능 금액 |
      | `nrcvb_buy_qty` | 미수없는매수수량 | 해당 종목 매수 가능 수량 |

  - **매도가능수량조회** (국내주식-165) ⚠️ 실전만 지원
    - URL: `/uapi/domestic-stock/v1/trading/inquire-psbl-sell`
    - Method: GET
    - TR_ID: `TTTC8408R`
    - Query Parameters: `CANO`, `ACNT_PRDT_CD`, `PDNO`
    - Response 주요 필드:
      | 필드 | 설명 |
      |------|------|
      | `ord_psbl_qty` | 주문가능수량 (매도 가능) |
      | `cblc_qty` | 잔고수량 |
      | `evlu_pfls_rt` | 평가손익율 |

- **공통 Request Header**
  ```
  content-type: application/json; charset=utf-8
  authorization: Bearer {access_token}
  appkey: {HANSEC_INVESTMENT_APP_KEY}
  appsecret: {HANSEC_INVESTMENT_APP_SECRET_KEY}
  tr_id: {각 API별 TR_ID}
  custtype: P
  ```

- **포트폴리오 현황 수집 및 GPT 입력 가공**
  - **수집 주기**: GPT 호출 직전 (30분마다 또는 리밸런싱 시점)
  - **수집 순서**:
    1. 주식 잔고 조회 API 호출 → 보유 종목 리스트 획득
    2. 매수 가능 조회 API 호출 → 가용 현금(예수금) 확인
    3. 각 보유 종목의 현재가 조회 (주식현재가 API 또는 캐시된 가격 사용)
  - **API 응답 → GPT 입력 변환**:
    - 주식 잔고 조회 응답에서 추출:
      ```
      positions[i].ticker = output1.pdno (종목코드)
      positions[i].name = output1.prdt_name (종목명)
      positions[i].shares = output1.hldg_qty (보유수량)
      positions[i].avg_price = output1.pchs_avg_pric (매입평균가)
      positions[i].current_price = output1.prpr (현재가)
      ```
    - 매수 가능 조회 응답에서 추출:
      ```
      cash_krw = output.ord_psbl_cash (주문가능현금)
      ```
    - 비중 계산:
      ```
      total_value = cash_krw + sum(positions[i].current_price * positions[i].shares)
      positions[i].weight_in_portfolio = (positions[i].current_price * positions[i].shares) / total_value
      ```
  - **GPT 입력 JSON 구성 예시**:
    ```json
    {
      "portfolio": {
        "cash_krw": 5000000,
        "total_value": 25000000,
        "positions": [
          {
            "ticker": "005930",
            "name": "삼성전자",
            "shares": 100,
            "avg_price": 76000,
            "current_price": 78100,
            "eval_amount": 7810000,
            "profit_loss_rate": 0.0276,
            "weight_in_portfolio": 0.3124
          }
        ]
      }
    }
    ```
  - **캐싱 전략**:
    - 잔고 정보는 GPT 호출 직전 실시간 조회 (stale 데이터 방지)
    - 현재가는 최근 1분 이내 캐시 사용 가능 (체결 API 데이터 재활용)
  - **에러 처리**:
    - API 조회 실패 시: 마지막 성공 데이터 + `"data_stale": true` 플래그 추가
    - 보유 종목이 없는 경우: `positions: []`, `cash_krw`만 전달

- 거래 에이전트에게 websocket으로 다음 메시지 전달
  - ```
    json
    {
      "request_id": "uuid-v4 형식의 요청 식별자",
      "action": "buy 또는 sell",
      "ticker": "005930",
      "qty": 10,
      "order_type": "market 또는 limit",
      "price": 0,
      "timestamp": "2024-01-15T09:30:00Z"
    }
    ```
  - `order_type`: `market`(시장가) 시 `price`는 0, `limit`(지정가) 시 희망가격 입력
  - 거래 에이전트 응답 메시지:
    - ```
      json
      {
        "request_id": "요청 시 전달한 request_id",
        "status": "success 또는 failed 또는 pending",
        "order_no": "주문번호 (성공 시)",
        "message": "결과 메시지",
        "timestamp": "2024-01-15T09:30:01Z"
      }
      ```

- **거래량 판단 기준**
  - 거래량 조회: 한국투자증권 주식현재가 체결 API 사용
    - URL: `/uapi/domestic-stock/v1/quotations/inquire-ccnl`
    - TR_ID: `FHKST01010300`
  - 거래량 판단 로직:
    - 최근 10분간 체결량이 전일 동시간대 평균 대비 150% 이상: "거래량 많음" → 5분 주기
    - 그 외: "거래량 적음" → 10분 주기

- **주문 수량 계산 로직**
  - `target_weight`를 실제 주문 수량으로 변환:
    ```
    total_portfolio_value = cash_krw + sum(position.current_price * position.shares)
    target_amount = total_portfolio_value * target_weight
    current_amount = position.current_price * position.shares (보유 시) 또는 0
    order_amount = target_amount - current_amount
    order_qty = floor(order_amount / current_price)
    ```
  - 최소 주문 금액(`min_order_krw`) 미만 시 주문 생략
- 프롬프트
  - ```markdown
    # Role

    You are the **Portfolio Management Agent** for an automated trading system in the Korean stock market.

    Your job is to:
    - Integrate macro view, technical analysis, and fundamental analysis,
    - Consider the current portfolio (positions + cash),
    - Decide for each ticker whether to **BUY**, **SELL**, or **HOLD**,
    - Provide only a compact JSON output that can be parsed by the system.

    You must **not** generate any natural language explanation outside the JSON.
    All outputs must be in **valid JSON only**.

    ---

    # Input format

    You will receive a single JSON object with the following structure:

    ```json
    {
      "now_utc": "YYYY-MM-DDTHH:MM:SSZ",
      "macro": {
        "positive_summary": "max 10 sentences summarizing positive macro view (from _short report)",
        "negative_summary": "max 10 sentences summarizing negative macro view (from _short report)",
        "market_bias_hint": "bullish | bearish | neutral | uncertain"
      },
      "portfolio": {
        "cash_krw": 5000000,
        "total_value": 25000000,
        "data_stale": false,
        "positions": [
          {
            "ticker": "005930",
            "name": "삼성전자",
            "shares": 100,
            "avg_price": 76000,
            "current_price": 78100,
            "eval_amount": 7810000,
            "profit_loss_rate": 0.0276,
            "weight_in_portfolio": 0.3124
          }
        ]
      },
      "universe": [
        {
          "ticker": "005930",
          "name": "Samsung Electronics",
          "current_price": 78100,
          "technical": {
            "day": {
              "trend": "up | down | sideway",
              "rsi": 55.2,
              "macd_signal": "bullish | bearish | neutral",
              "bollinger_position": "upper | middle | lower",
              "fibonacci_zone": "deep_pullback | shallow_pullback | extension | none"
            },
            "week": {
              "trend": "up | down | sideway",
              "macd_signal": "bullish | bearish | neutral"
            },
            "month": {
              "trend": "up | down | sideway"
            }
          },
          "fundamental": {
            "valuation": "cheap | fair | expensive",
            "quality": "high | medium | low",
            "growth": "high | medium | low",
            "recent_events": "max 3 bullet-style sentences"
          },
          "is_in_portfolio": true
        }
      ],
      "constraints": {
        "max_buy_candidates": 3,
        "max_sell_candidates": 3,
        "min_order_krw": 100000,
        "max_turnover_ratio": 0.3,
        "target_max_single_ticker_weight": 0.2,
        "risk_mode": "normal | conservative | aggressive"
      }
    }
    ```

    **Notes:**
    - `portfolio`는 GPT 호출 직전 한국투자증권 API에서 실시간 조회한 데이터입니다.
      - `cash_krw`: 주문가능현금 (예수금)
      - `total_value`: 총 평가금액 (현금 + 보유종목 평가액 합계)
      - `data_stale`: API 조회 실패 시 true (이전 데이터 사용 중임을 표시)
      - `eval_amount`: 해당 종목의 평가금액 (current_price × shares)
      - `profit_loss_rate`: 수익률 ((current_price - avg_price) / avg_price)
      - `weight_in_portfolio`: 포트폴리오 내 비중 (eval_amount / total_value)
    - `universe`에는 현재 보유 중인 종목 + 신규 매수 후보 종목만 들어옵니다.
    - 각 분석 데이터는 이미 사전 가공된 요약 정보입니다.
    - 가격/수치는 예시이며, 실제 값이 들어옵니다.

    ---

    # Task

    Given the input JSON, you must:

    ## 1. Infer a global risk stance
    - Combine `macro.market_bias_hint`, technical/fundamental signals, and current portfolio concentration.
    - Decide whether overall exposure should be **increased**, **kept**, or **reduced**.

    ## 2. Decide per-ticker actions
    For each ticker in `universe`, choose one of:
    - `"BUY"` : increase or open a position
    - `"SELL"` : reduce or fully close a position
    - `"HOLD"` : no trade

    ## 3. Respect constraints
    - Do not suggest more than `constraints.max_buy_candidates` tickers with `"BUY"`.
    - Do not suggest more than `constraints.max_sell_candidates` tickers with `"SELL"`.
    - Avoid excessive churning: if `constraints.max_turnover_ratio` is low, prefer `"HOLD"` unless there is a strong reason.
    - If data is inconsistent or unclear, default to `"HOLD"`.

    ## 4. Suggest target exposure
    - You do not need to compute exact share quantities.
    - Instead, for each ticker you can suggest a `target_weight` (0.0–1.0) relative to total portfolio value (including cash).
    - The system will transform `target_weight` into actual order sizes.
    - For tickers you want to fully exit, use `"target_weight": 0.0`.
    - Ensure the sum of all `target_weight` is ≤ 1.0; any remainder is treated as cash.

    ## 5. Explain briefly
    - For each ticker, provide a very short rationale (max 2 sentences).
    - Focus only on the most important signals (macro direction, major technical / fundamental signals).

    ---

    # Output format (JSON only)

    Return a single JSON object with this exact structure and nothing else:

    ```json
    {
      "meta": {
        "decision_time_utc": "YYYY-MM-DDTHH:MM:SSZ",
        "overall_comment": "max 2 sentences summarizing overall strategy"
      },
      "global_view": {
        "macro_bias": "bullish | bearish | neutral | uncertain",
        "risk_action": "increase_exposure | keep_exposure | reduce_exposure",
        "target_cash_ratio": 0.0
      },
      "ticker_decisions": [
        {
          "ticker": "005930",
          "action": "BUY | SELL | HOLD",
          "target_weight": 0.15,
          "priority": 1,
          "strength": 0.0,
          "reason": "max 2 sentences; do not restate all input data."
        }
      ]
    }
    ```

    **Field semantics:**

    | Field | Description |
    |-------|-------------|
    | `meta.decision_time_utc` | Echo `now_utc` from the input. |
    | `global_view.macro_bias` | Your final interpretation of macro condition. |
    | `global_view.risk_action` | How the portfolio should adjust its overall exposure. |
    | `global_view.target_cash_ratio` | Desired cash ratio in the portfolio (0.0–1.0). This will be used as a hint; the system may adjust slightly. |
    | `ticker_decisions` | One entry per ticker in the input universe. |
    | `action` | `"BUY"`: Increase or open a position. `"SELL"`: Decrease or close the position. `"HOLD"`: No trade. |
    | `target_weight` | Target fraction of total portfolio value in this ticker. `0.0` means full exit. Sum of all `target_weight` values must be ≤ 1.0. |
    | `priority` | Integer ranking (1 = highest priority). |
    | `strength` | 0.0–1.0 confidence score (e.g. 0.2 = weak, 0.8 = strong). |
    | `reason` | Max 2 concise sentences. Do not copy long parts of the input; only summarize key signals. |

    ---

    # Decision rules & risk management

    Apply these principles:

    ## 1. Capital preservation first
    In clearly bearish or uncertain macro conditions, prefer:
    - Reducing positions with weak fundamentals and bearish technical signals.
    - Increasing `target_cash_ratio`.
    - Avoid aggressive new buys unless technical + fundamental + macro all support it.

    ## 2. Signal alignment
    - **Strong BUY candidates:** At least 2 of 3 agree (macro, technical, fundamental) in a positive direction.
    - **Strong SELL candidates:** Technical clearly bearish and fundamental weak or deteriorating, especially under bearish macro.
    - When signals conflict, be conservative and prefer `"HOLD"`.

    ## 3. Concentration control
    - Respect `constraints.target_max_single_ticker_weight`.
    - If a ticker is above that threshold and risk is not aggressive, bias to `"SELL"` or lower `target_weight`.

    ## 4. Turnover control
    - Keep number of trades small.
    - If a change in action is marginal, choose `"HOLD"` to reduce noise.

    ## 5. Safe defaults
    If the input is incomplete, inconsistent, or you are not confident:
    - Set `action` to `"HOLD"` and use a higher `target_cash_ratio`.
    - Explain briefly in `reason`.

    ---

    # Remember

    - Output must be **valid JSON**.
    - Do **not** include any text outside the JSON.
    - Do **not** invent new fields or keys that are not listed in the output schema.
    ```

- GPT 호출 스펙
  - 사용 모델명: `gpt-5.1-mini` (또는 비용/품질에 따라 조정)
  - 호출 주기
    - 신규 매수/리밸런싱: 30분마다
    - 매도 재평가: 거래량 조건에 따라 30분마다 또는 규칙 기반 + GPT 혼합
  - 기본값: `temperature: 0.2`, `top_p: 0.9`, `max_tokens: 2048`

- 비용 최적화 전략
  - **입력 크기(토큰) 줄이기**
    - 거시경제 보고서를 그대로 넣지 않고, 사전에 3~6문장 요약 후 `positive_summary`, `negative_summary`만 전달
    - 기술/기업 분석도 원천 데이터 대신 `trend`, `signal` 같은 범주형/숫자형 지표만 전달
  - **티커 수 제한**
    - 한 번 호출에 최대 5개 티커만 전달
    - 포트폴리오 에이전트가 사전 필터링(유동성, 거래대금, 알파 기대치 등) 후 GPT에 전달
  - **호출 주기 제어**
    - 빠른 매도(손절/익절)는 규칙 기반 로직으로 먼저 처리
    - 큰 방향 전환 판단 때만 GPT 호출
  - **모델 구성**
    - 기술/기업 분석 요약용으로는 저렴한 모델 사용
    - 최종 포트폴리오 의사결정은 중간급 모델 1회 호출
  - **응답 길이 제한**
    - 프롬프트에 "reason은 최대 2문장"처럼 명시하여 토큰 절약

- 실패/예외 처리
  - GPT 응답 JSON 파싱 실패 시: 3번 재시도 후 실패하면 "전부 HOLD, 신규매수 없음" 기본 전략 적용
  - 응답 값이 제약조건 위반 시(예: `target_weight` 합 > 1.0): 로컬에서 정규화(normalize) 처리

- 리스크 파라미터
  - `target_max_single_ticker_weight`: 0.2 (기본값)
  - `max_turnover_ratio`: 0.3 (기본값)
  - `min_order_krw`: 100,000원 (기본값)
  - 위 값들은 환경변수 또는 ConfigMap으로 관리

- 로그 및 모니터링
  - GPT 입력/출력 JSON을 S3 `quartz-bucket/portfolio-decisions/` 폴더에 저장
  - 파일명 형식: `decision_{YYYYMMDDhhmmss}.json`
  - 대규모 매수/매도 시 INFO 레벨 로그 + Slack 알림 연동

- 언어/포맷 규칙
  - 프롬프트와 JSON 키는 **영어**로 통일
  - 소수점은 항상 `.` 사용 (콤마 불가)
  - 퍼센트 대신 0.0~1.0 스케일 사용



### 3.5 거래 에이전트
- python 3.12에서 작동.
- 실제 거래 수행
- 포트폴리오 관리 에이전트와 WebSocket으로 연결되어 주문 명령 수신

- **WebSocket 서버 설정**
  - 경로: `ws://trading-agent:8005/ws/orders`
  - 연결 유지: ping/pong 30초 간격
  - 재연결: 연결 끊김 시 포트폴리오 에이전트가 5초 후 재연결 시도 (최대 3회)

- **한국투자증권 API 사용**
  - **주식주문(현금)** (v1_국내주식-001)
    - URL: `/uapi/domestic-stock/v1/trading/order-cash`
    - Method: POST
    - TR_ID (실전): 매수 `TTTC0012U`, 매도 `TTTC0011U`
    - TR_ID (모의): 매수 `VTTC0012U`, 매도 `VTTC0011U`
    - Request Body:
      | 필드 | 설명 | 예시 |
      |------|------|------|
      | `CANO` | 계좌번호 앞 8자리 | 12345678 |
      | `ACNT_PRDT_CD` | 계좌상품코드 | 01 |
      | `PDNO` | 종목코드 (6자리) | 005930 |
      | `ORD_DVSN` | 주문구분 | 00(지정가), 01(시장가) |
      | `ORD_QTY` | 주문수량 (문자열) | "10" |
      | `ORD_UNPR` | 주문단가 (시장가는 "0") | "78000" |
    - Response 성공 시:
      ```json
      {
        "rt_cd": "0",
        "output": {
          "KRX_FWDG_ORD_ORGNO": "06010",
          "ODNO": "0001569157",
          "ORD_TMD": "155211"
        }
      }
      ```
    - `ODNO` (주문번호)는 정정/취소 시 필요하므로 저장

  - **주식주문(정정취소)** (v1_국내주식-003)
    - URL: `/uapi/domestic-stock/v1/trading/order-rvsecncl`
    - Method: POST
    - TR_ID (실전): `TTTC0013U`, (모의): `VTTC0013U`
    - Request Body:
      | 필드 | 설명 |
      |------|------|
      | `KRX_FWDG_ORD_ORGNO` | 원주문의 거래소코드 |
      | `ORGN_ODNO` | 원주문번호 |
      | `RVSE_CNCL_DVSN_CD` | 01(정정), 02(취소) |
      | `ORD_QTY` | 정정/취소 수량 |
      | `QTY_ALL_ORD_YN` | Y(전량), N(일부) |

  - **주식정정취소가능주문조회** (v1_국내주식-004) ⚠️ 실전만 지원
    - URL: `/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl`
    - Method: GET
    - TR_ID: `TTTC0084R`
    - **반드시 정정/취소 전 호출하여 `psbl_qty` (가능수량) 확인**
    - Response 주요 필드:
      | 필드 | 설명 |
      |------|------|
      | `odno` | 주문번호 |
      | `ord_qty` | 주문수량 |
      | `tot_ccld_qty` | 체결수량 |
      | `psbl_qty` | 정정/취소 가능수량 |
      | `sll_buy_dvsn_cd` | 01(매도), 02(매수) |

- **주문 실행 흐름**
  1. WebSocket으로 주문 명령 수신
  2. 인증 에이전트에서 토큰 조회 (`GET http://auth-agent:8006/result/auth-token`)
  3. 매수 시: 매수가능금액 확인 → 주문 실행
  4. 매도 시: 매도가능수량 확인 → 주문 실행
  5. 주문 결과를 WebSocket으로 응답
  6. 주문 실패 시 3회 재시도 (1초 간격)

- **주문 요청 Body 형식**
  - ```
    json
    {
      "CANO": "계좌번호 앞 8자리 (환경변수에서)",
      "ACNT_PRDT_CD": "계좌상품코드 뒤 2자리 (환경변수에서)",
      "PDNO": "종목코드 6자리",
      "ORD_DVSN": "00(지정가) 또는 01(시장가)",
      "ORD_QTY": "주문수량 (문자열)",
      "ORD_UNPR": "주문단가 (시장가는 0)"
    }
    ```

- **주문 상태 추적**
  - 주문 체결 확인: 일별주문체결조회 API 사용
    - URL: `/uapi/domestic-stock/v1/trading/inquire-daily-ccld`
    - TR_ID: `TTTC0081R` (실전), `VTTC0081R` (모의)
  - 미체결 주문은 장 마감 전 자동 취소 처리 (14:50)

- **에러 처리**
  - 토큰 만료: 인증 에이전트에 재요청
  - 주문 거부: 에러 코드별 처리 후 포트폴리오 에이전트에 실패 응답
  - 네트워크 오류: 3회 재시도 후 실패 처리



### 3.6 인증관리 에이전트
- python 3.12에서 작동.
- 한국투자증권 OAuth 토큰을 관리하여 다른 에이전트들에게 제공

- **한국투자증권 API: 접근토큰발급(P)** (인증-001)
  - URL: `/oauth2/tokenP`
  - Method: POST
  - 실전 Domain: `https://openapi.koreainvestment.com:9443`
  - **토큰 유효기간**: 24시간 (1일 1회 발급 원칙)
  - **갱신발급주기**: 6시간 이내 재호출 시 기존 토큰 반환
  - Request Body:
    ```json
    {
      "grant_type": "client_credentials",
      "appkey": "{HANSEC_INVESTMENT_APP_KEY}",
      "appsecret": "{HANSEC_INVESTMENT_APP_SECRET_KEY}"
    }
    ```
  - Response:
    ```json
    {
      "access_token": "eyJ0eXAi...",
      "access_token_token_expired": "2024-01-16 08:16:59",
      "token_type": "Bearer",
      "expires_in": 86400
    }
    ```
  - **Response 필드 활용**:
    | 필드 | 설명 | 사용 방법 |
    |------|------|----------|
    | `access_token` | OAuth 토큰 | 다른 API 호출 시 `Authorization: Bearer {token}` |
    | `access_token_token_expired` | 만료 일시 | 토큰 갱신 시점 판단 |
    | `expires_in` | 유효기간(초) | 86400초 = 24시간 |

- **토큰 관리 로직**
  - 시작 시 토큰 발급 → 메모리에 캐싱
  - 23시간 55분 주기로 갱신 (만료 5분 전)
  - `/result/auth-token` API로 다른 에이전트에게 제공
  - Response:
    ```json
    {
      "token": "받은 auth 토큰",
      "token_type": "Bearer",
      "expires_at": "2024-01-16T08:16:59Z"
    }
    ```

- **환경 변수**
  - `HANSEC_INVESTMENT_APP_KEY`: 앱키
  - `HANSEC_INVESTMENT_APP_SECRET_KEY`: 앱시크릿키
  - ⚠️ 절대 노출되지 않도록 주의

- **에러 처리**
  - 토큰 발급 실패 시: 1분 후 재시도 (최대 5회)
  - 만료 전 갱신 실패 시: 경고 로그 + Slack 알림

- **기존 토큰 발급 요청 Body** (참고용)
  - ```
    json
    {
      "grant_type": "client_credentials",
      "appkey": "환경변수에서 로드",
      "appsecret": "환경변수에서 로드"
    }
    ```

- **동작 방식**
  1. 에이전트 시작 시 즉시 토큰 발급 시도
  2. 발급 성공: 메모리에 토큰 저장, 만료 시간 기록
  3. 발급 실패: 30초 후 재시도 (최대 5회), 모두 실패 시 에이전트 종료 (k8s가 재시작)
  4. 23시간 55분마다 토큰 갱신 (토큰 유효기간 24시간보다 5분 일찍 갱신)
  5. 다른 에이전트가 토큰 요청 시 만료까지 5분 미만 남았으면 즉시 갱신 후 반환

- **토큰 상태 확인 API**
  - `GET /result/auth-token/status`
  - response:
    - ```
      json
      {
        "is_valid": true,
        "expires_at": "2024-01-16T08:16:59Z",
        "remaining_seconds": 3600
      }
      ```

- **에러 처리**
  - 토큰 요청 시 토큰이 없거나 만료됨: HTTP 503 반환, 요청 에이전트가 재시도
  - 한국투자증권 API 오류: 에러 로그 기록 후 재시도


<!-- ### 3.7 기업분석 에이전트 (미구현)
- python 3.12에서 작동.
- ticker를 통해 해당 기업의 재무정보를 검색하고 해당 ticker 종목 구매의 적합성을 판단
  - 다음 API들을 사용
    - https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/finance/balance-sheet
    - https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/finance/financial-ratio
    - https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/finance/growth-ratio -->

---

## 4. 에러 처리 및 재시도 정책

### 4.1 공통 재시도 정책

| 에러 유형 | 재시도 횟수 | 재시도 간격 | 실패 시 동작 |
|----------|------------|------------|-------------|
| 네트워크 타임아웃 | 3회 | 1초, 2초, 4초 (지수 백오프) | 에러 로그 후 기본값 반환 |
| HTTP 5xx | 3회 | 2초 고정 | 에러 로그 후 기본값 반환 |
| HTTP 4xx | 재시도 안함 | - | 에러 로그 후 즉시 실패 처리 |
| 토큰 만료 (401) | 1회 | 토큰 재발급 후 즉시 | 인증 에이전트 헬스체크 |

### 4.2 에이전트별 기본값 (폴백)

| 에이전트 | 실패 시 기본 동작 |
|---------|-----------------|
| 거래종목 선택 | 빈 배열 `[]` 반환 (신규 매수 없음) |
| 기술분석 | 해당 ticker 분석 스킵 |
| 포트폴리오 관리 | 전부 HOLD, 신규매수 없음 |
| 거래 | 주문 실패로 처리, 포트폴리오에 알림 |
| 인증관리 | 에이전트 재시작 (k8s 자동) |

### 4.3 로깅 형식

모든 에이전트는 JSON 형식 로그 출력:
```
json
{
  "timestamp": "2024-01-15T09:30:00.123Z",
  "level": "INFO | WARN | ERROR",
  "agent": "에이전트명",
  "event": "이벤트명",
  "message": "상세 메시지",
  "data": { "추가 데이터": "..." }
}
```

---

## 5. Kubernetes 배포 설정

### 5.1 리소스 요구사항

| 에이전트 | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|------------|-----------|----------------|--------------|
| 거시경제 분석 | 100m | 500m | 128Mi | 512Mi |
| 거래종목 선택 | 100m | 300m | 128Mi | 256Mi |
| 기술분석 | 200m | 500m | 256Mi | 512Mi |
| 포트폴리오 관리 | 200m | 500m | 256Mi | 512Mi |
| 거래 | 100m | 300m | 128Mi | 256Mi |
| 인증관리 | 50m | 200m | 64Mi | 128Mi |

### 5.2 ConfigMap 구성

`quartz-config` ConfigMap:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: quartz-config
  namespace: quartz
data:
  IS_PRODUCTION: "false"
  AWS_REGION: "ap-northeast-2"
  S3_BUCKET_NAME: "quartz-bucket"
  MIN_ORDER_KRW: "100000"
  MAX_SINGLE_TICKER_WEIGHT: "0.2"
  MAX_TURNOVER_RATIO: "0.3"
  MAX_BUY_CANDIDATES: "3"
  MAX_SELL_CANDIDATES: "3"
```

### 5.3 Secret 구성

`quartz-secrets` Secret (base64 인코딩):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: quartz-secrets
  namespace: quartz
type: Opaque
data:
  HANSEC_INVESTMENT_APP_KEY: <base64>
  HANSEC_INVESTMENT_APP_SECRET_KEY: <base64>
  HANSEC_INVESTMENT_CANO: <base64>
  HANSEC_INVESTMENT_ACNT_PRDT_CD: <base64>
  AWS_ACCESS_KEY_ID: <base64>
  AWS_SECRET_ACCESS_KEY: <base64>
  OPENAI_API_KEY: <base64>
  GEMINI_API_KEY: <base64>
```

### 5.4 Probe 설정

모든 에이전트에 적용:
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 800X
  initialDelaySeconds: 10
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 800X
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /health/live
    port: 800X
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 30
```

---

## 6. 데이터 흐름 요약

### 6.1 신규 매수 흐름 (30분 주기)

```
1. [거시경제 에이전트] → S3에 보고서 업로드 (1시간 주기, 별도 동작)
2. [포트폴리오 관리] → GET /result/analysis → [거시경제 에이전트]
3. [포트폴리오 관리] → GET /result/tickers → [거래종목 선택 에이전트]
4. [포트폴리오 관리] → POST /result/analysis (각 ticker) → [기술분석 에이전트]
5. [포트폴리오 관리] → GPT 호출 (매수/매도/보유 결정)
6. [포트폴리오 관리] → WebSocket 주문 명령 → [거래 에이전트]
7. [거래 에이전트] → GET /result/auth-token → [인증 에이전트]
8. [거래 에이전트] → 한국투자증권 API 호출 (주문 실행)
9. [거래 에이전트] → WebSocket 주문 결과 → [포트폴리오 관리]
```

### 6.2 매도 재평가 흐름 (5~10분 주기)

```
1. [포트폴리오 관리] → 한국투자증권 API (잔고 조회)
2. [포트폴리오 관리] → 거래량 확인 (주기 결정)
3. [포트폴리오 관리] → POST /result/analysis (보유 종목) → [기술분석 에이전트]
4. [포트폴리오 관리] → 규칙 기반 손절/익절 체크
   - 손실률 > 5%: 즉시 매도 (GPT 호출 없이)
   - 수익률 > 15%: 즉시 매도 (GPT 호출 없이)
5. 규칙에 해당 안되면 → GPT 호출 (매도/보유 결정)
6. 매도 결정 시 → WebSocket 주문 명령 → [거래 에이전트]
```

---

## 7. 모니터링 및 알림

### 7.1 S3 저장 경로 요약

| 데이터 | S3 경로 | 보관 주기 |
|-------|--------|----------|
| 거시경제 보고서 | `macroeconomics/Report_{Positive\|Negative}_{timestamp}.md` | 7일 |
| 선정 종목 | `select-ticker/selected_tickers.json` | 갱신 (단일 파일) |
| 기술분석 결과 | `technical-analysis/{ticker}_{timestamp}.json` | 1일 |
| 포트폴리오 결정 | `portfolio-decisions/decision_{timestamp}.json` | 30일 |

### 7.2 알림 조건 (INFO 레벨 로그)

- 대규모 매수: 총 포트폴리오의 10% 이상 단일 주문
- 대규모 매도: 보유 수량의 50% 이상 매도
- 손절 발동: 규칙 기반 손절 실행
- 연속 실패: 동일 에이전트 3회 연속 에러
