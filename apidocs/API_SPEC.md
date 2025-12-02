# Quartz 에이전트 API 스펙

이 문서는 Quartz 프로젝트에서 구현된 에이전트들의 API 명세를 정리합니다.

---

## 1. Technical Agent (기술분석 에이전트)

**파일**: `agents/technical_agent.py`  
**FastAPI 앱**: `Chart Technical Analysis Agent v0.1.0`

포트폴리오 에이전트 요청 시 전달된 티커 목록에 대해 기술 지표(RSI, MACD, Bollinger Band, 이동평균, 피보나치 되돌림)를 실시간으로 계산해 반환합니다.

### POST `/api/analyze`

티커 목록을 받아 각 티커에 대한 기술분석 결과를 반환합니다.

#### Request Body

```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL"]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `tickers` | `string[]` | ✅ | 분석할 티커 목록 (최소 1개) |

#### Response (200 OK)

```json
{
  "requested": ["AAPL", "MSFT", "GOOGL"],
  "results": [
    {
      "ticker": "AAPL",
      "status": "ok",
      "payload": {
        "timestamp": "2025-12-02T10:30:00+00:00",
        "ticker": "AAPL",
        "daily": {
          "cost": 189.95,
          "rsi": 55.123456,
          "macd": {
            "macd": 1.234567,
            "signal": 0.987654,
            "histogram": 0.246913,
            "fast": 14,
            "slow": 28,
            "signal_window": 9
          },
          "bollinger_band": {
            "upper": 195.5,
            "middle": 188.0,
            "lower": 180.5
          },
          "ma_av": {
            "ma20": [185.1, 185.5, ...],
            "ma60": [180.2, 180.8, ...],
            "ma120": [175.0, 175.5, ...]
          },
          "fibonacci_retracement": {
            "high": 200.0,
            "low": 150.0,
            "levels": {
              "0.0": 200.0,
              "0.236": 188.2,
              "0.382": 180.9,
              "0.5": 175.0,
              "0.618": 169.1,
              "0.786": 160.7,
              "1.0": 150.0
            }
          }
        },
        "weekly": { ... },
        "monthly": { ... },
        "summation": [0.102456, 0.234567, -0.056789]
      }
    },
    {
      "ticker": "MSFT",
      "status": "error",
      "detail": "데이터를 불러오지 못했습니다. ticker=MSFT"
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `requested` | `string[]` | 요청된 티커 목록 (중복/공백 제거됨) |
| `results` | `object[]` | 각 티커별 분석 결과 |
| `results[].ticker` | `string` | 티커 심볼 |
| `results[].status` | `"ok" \| "error"` | 분석 성공/실패 여부 |
| `results[].payload` | `object` | 성공 시 기술분석 결과 |
| `results[].detail` | `string` | 실패 시 오류 메시지 |

#### 타임프레임별 섹션 구조

| 필드 | 타입 | 설명 |
|------|------|------|
| `cost` | `float` | 최근 종가 |
| `rsi` | `float` | RSI 지표 (0~100) |
| `macd` | `object` | MACD 지표 (macd, signal, histogram, 파라미터) |
| `bollinger_band` | `object` | 볼린저 밴드 (upper, middle, lower) |
| `ma_av` | `object` | 이동평균 배열 (ma20, ma60, ma120) |
| `fibonacci_retracement` | `object` | 피보나치 되돌림 (daily, weekly만 포함) |
| `summation` | `float[]` | RSI 기반 정규화 신호 (-1 ~ 1) |

#### Error Responses

| 상태 코드 | 설명 |
|-----------|------|
| `422` | 유효한 티커가 없음 (`no valid tickers provided`) |

---

## 2. Trading Agent (거래 에이전트)

**파일**: `agents/trading_agent.py`  
**FastAPI 앱**: `Trading Agent v0.1.0`

포트폴리오 에이전트로부터 WebSocket을 통해 주문을 받아 모의 체결을 수행합니다.

### GET `/health`

서버 상태를 확인합니다.

#### Response (200 OK)

```json
{
  "status": "ok"
}
```

---

### WebSocket `/ws/trade`

포트폴리오 에이전트와 실시간 주문 처리를 위한 WebSocket 연결입니다.

#### 연결 흐름

1. 클라이언트가 `/ws/trade`에 WebSocket 연결
2. 서버가 연결 수락 후 대기
3. 클라이언트가 `ActionMessage` JSON을 텍스트로 전송
4. 서버가 `TradeResult` JSON을 텍스트로 응답
5. 반복 (연결 유지)

#### Request Message (`ActionMessage`)

```json
{
  "action": "buy",
  "ticker": "AAPL",
  "cost": 150.0,
  "amount": 10.0
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `action` | `"buy" \| "sell"` | ✅ | 매수/매도 |
| `ticker` | `string` | ✅ | 티커 심볼 |
| `cost` | `float` | ✅ | 주문 가격 (> 0) |
| `amount` | `float` | ✅ | 주문 수량 (> 0) |

#### Response Message (`TradeResult`)

**성공 시:**

```json
{
  "result": "success",
  "message": "주문 체결 완료 (notional=1500.00)",
  "next_action": null
}
```

**실패 시 (한도 초과):**

```json
{
  "result": "fail",
  "message": "주문 금액 150000 > 한도 100000",
  "next_action": {
    "action": "buy",
    "ticker": "AAPL",
    "cost": 142.5,
    "amount": 701.7544
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `result` | `"success" \| "fail"` | 체결 결과 |
| `message` | `string` | 결과 메시지 |
| `next_action` | `ActionMessage \| null` | 실패 시 제안하는 대안 주문 |

#### 체결 규칙

| 조건 | 결과 |
|------|------|
| `cost < 1.0` | 실패, `cost=1.0`으로 수정된 대안 제안 |
| `cost * amount > 100,000` | 실패, 5% 할인 가격 + 한도 내 수량으로 대안 제안 |
| 그 외 | 성공 |

---

## 3. Portfolio Manager (포트폴리오 관리 에이전트)

**파일**: `agents/portfolio_manager.py`

분석 에이전트들로부터 데이터를 수집하고, 신호를 집계해 거래 에이전트로 주문을 전달하는 클라이언트입니다. HTTP/WebSocket 서버를 제공하지 않고, 다른 에이전트들을 호출하는 역할을 합니다.

### 호출하는 API

#### 분석 에이전트 호출

- **Method**: `POST`
- **URL**: `{agent_host}/api/result`
- **Request Body**: `{}`
- **Expected Response**: `AgentResult`

```json
{
  "timestamp": "2025-12-02T10:30:00+00:00",
  "summation": [0.5, 0.7, -0.2]
}
```

#### 거래 에이전트 호출

- **Protocol**: WebSocket
- **URL**: `ws://{trading_host}/ws/trade`
- **Message Format**: `ActionMessage` ↔ `TradeResult`

### 동작 흐름

1. 설정된 분석 에이전트들(`agent_hosts`)에 병렬로 `/api/result` 요청
2. 응답받은 `summation` 배열들을 병합해 평균 신호 계산
3. 평균 신호가 임계값(`signal_threshold`)을 초과하면 매수/매도 주문 생성
4. 거래 에이전트 WebSocket으로 주문 전송
5. 실패 시 `next_action`이 있으면 대안 주문 재전송
6. `poll_interval_seconds` 간격으로 반복

---

## 공통 데이터 모델

**파일**: `shared/models.py`

### ActionType (Enum)

```
"buy" | "sell"
```

### ResultStatus (Enum)

```
"success" | "fail"
```

### AgentResult

분석 에이전트가 반환하는 결과입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| `timestamp` | `datetime` | 계산 시각 (ISO 8601) |
| `summation` | `float[]` | 정규화된 신호 배열 (최소 1개) |

### ActionMessage

포트폴리오 에이전트가 거래 에이전트로 전송하는 주문입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| `action` | `ActionType` | 매수/매도 |
| `ticker` | `string` | 티커 심볼 |
| `cost` | `float` | 주문 가격 (> 0) |
| `amount` | `float` | 주문 수량 (> 0) |

### TradeResult

거래 에이전트가 반환하는 체결 결과입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| `result` | `ResultStatus` | 체결 성공/실패 |
| `message` | `string` | 결과 메시지 |
| `next_action` | `ActionMessage?` | 실패 시 제안하는 대안 주문 |

---

## 환경 변수

### Technical Agent

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TECH_AGENT_TICKER` | `SPY` | 기본 티커 |
| `TECH_AGENT_MACD_FAST` | `14` | MACD 빠른 EMA 기간 |
| `TECH_AGENT_MACD_SLOW` | `28` | MACD 느린 EMA 기간 |
| `TECH_AGENT_MACD_SIGNAL` | `9` | MACD 시그널 EMA 기간 |
| `TECH_AGENT_RSI_WINDOW` | `14` | RSI 윈도우 |
| `TECH_AGENT_BOLL_WINDOW` | `20` | 볼린저 밴드 윈도우 |
| `TECH_AGENT_BOLL_STD` | `2.0` | 볼린저 밴드 표준편차 배수 |
| `TECH_AGENT_MA_TAIL` | `60` | 이동평균 tail 길이 |

### Portfolio Manager

`shared/config.py`의 `Settings` 클래스 참조.

| 변수 | 설명 |
|------|------|
| `agent_hosts` | 분석 에이전트 URL 목록 |
| `poll_interval_seconds` | 폴링 주기 |
| `trading_ws_url` | 거래 에이전트 WebSocket URL |
| `request_timeout` | HTTP 요청 타임아웃 |
| `max_retries` | 최대 재시도 횟수 |
| `retry_backoff_seconds` | 재시도 대기 시간 |
| `signal_threshold` | 매매 신호 임계값 |
| `default_ticker` | 기본 거래 티커 |

