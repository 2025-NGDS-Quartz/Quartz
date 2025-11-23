# Technical Agent 문서

FastAPI 기반 `agents/technical_agent.py`는 포트폴리오 에이전트가 전달한 티커 목록을 실시간으로 분석하여 RSI, MACD, Bollinger Band, 이동평균, 피보나치 되돌림 등을 계산해 돌려주는 온디맨드 기술분석 서비스입니다.

## 구성 요소

- **설정 계층**
  - `TimeframeConfig`: 기간·인터벌·피보나치 여부를 묶는 불변 데이터 클래스.
  - `TechnicalAgentConfig`: 기본 티커, 지표 파라미터, 타임프레임 사전을 포함하며 `from_env()`로 환경 변수 덮어쓰기를 지원합니다.
- **IndicatorCalculator**
  - `yfinance`로 타임프레임별 시세를 다운로드해 모든 지표를 계산하고, `timestamp`, `ticker`, 타임프레임 섹션, RSI 기반 `summation` 배열을 생성합니다.
- **AnalyzeRequest**
  - `/api/analyze` 요청 본문을 검증하며, 공백·중복을 제거한 티커 리스트를 제공합니다.

## 요청 처리 흐름

1. `/api/analyze` POST 요청이 들어오면 `AnalyzeRequest`가 티커 목록을 정규화합니다.
2. 각 티커마다 `IndicatorCalculator.build_payload(ticker)`를 `asyncio.gather`로 병렬 실행합니다.
   - `yfinance.download()` → 데이터 정리 → `_rsi`/`_macd`/`_bollinger`/`_format_mas`/`_fibonacci` 수행.
   - `summation`은 일·주·월 타임프레임 RSI를 -1~1 사이로 정규화한 배열입니다.
3. 성공한 티커는 `status: "ok"`와 계산 결과를, 실패한 티커는 `status: "error"`와 오류 메시지를 개별적으로 반환합니다.

## FastAPI 엔드포인트

| 경로 | 메서드 | 설명 |
| ---- | ------ | ---- |
| `/api/analyze` | POST | `{"tickers": ["AAPL", "MSFT"]}`와 같이 요청하면 각 티커별 분석 결과 또는 오류를 `results` 배열로 응답합니다. |

## 환경 변수

| 변수 | 기본값 | 용도 |
| ---- | ------ | ---- |
| `TECH_AGENT_TICKER` | `SPY` | 요청에 티커가 없을 때 사용할 기본 티커 |
| `TECH_AGENT_MACD_FAST/SLOW/SIGNAL` | `14/28/9` | MACD 파라미터 |
| `TECH_AGENT_RSI_WINDOW` | `14` | RSI 윈도우 |
| `TECH_AGENT_BOLL_WINDOW` | `20` | 볼린저 밴드 기준 윈도우 |
| `TECH_AGENT_BOLL_STD` | `2.0` | 볼린저 밴드 표준편차 배수 |
| `TECH_AGENT_MA_WINDOWS`* | `[20, 60, 120]` | 이동평균 윈도우 리스트 (코드 수정 필요) |
| `TECH_AGENT_MA_TAIL` | `60` | 이동평균 tail 길이 |

`*` 현재는 코드 상에서 리스트를 직접 정의하고 있으므로, 필요 시 환경 변수 처리 로직을 확장해야 합니다.

## 로깅과 예외 처리

- 전역 `logging.basicConfig`가 INFO 레벨 로그를 남깁니다.
- `/api/analyze` 처리 도중 특정 티커에서 예외가 발생하면 해당 티커만 `status="error"`로 표시하고 나머지는 정상 응답합니다.
- `yfinance` 호출 실패나 빈 데이터는 `ValueError`로 전파되어 위와 같이 처리됩니다.

## 의존성

- `yfinance`, `pandas`, `numpy`, `fastapi`, `pydantic`이 필요합니다.
- 네트워크나 외부 API 속도에 따라 응답 시간이 달라질 수 있으므로 호출 측에서 타임아웃과 재시도 전략을 두는 것이 좋습니다.


