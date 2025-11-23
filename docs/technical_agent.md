# Technical Agent 문서

FastAPI 기반 `agents/technical_agent.py`는 주기적으로 차트 지표를 계산해 캐시에 저장하고, 이를 HTTP API로 노출하는 기술분석 에이전트입니다. 아래는 구성요소와 동작 흐름 요약입니다.

## 구성 요소

- **설정 계층**
  - `TimeframeConfig`: 기간·인터벌·피보나치 여부를 묶는 불변 데이터 클래스.
  - `TechnicalAgentConfig`: 티커, 계산 주기, 각종 지표 파라미터와 타임프레임 사전을 포함합니다. `from_env()`를 통해 환경 변수로 기본값을 덮어쓸 수 있습니다.
- **IndicatorCache**
  - `shared/data/chart_signals.json`(기본값)에 JSON을 원자적으로 기록/읽기 하는 비동기 파일 캐시.
  - 내부 `asyncio.Lock`으로 동시 접근을 직렬화하고, 파일 IO는 `asyncio.to_thread`로 넘겨 이벤트 루프를 막지 않습니다.
- **IndicatorCalculator**
  - `yfinance`로 타임프레임별 시세를 받아 RSI, MACD, Bollinger Band, 이동평균, 피보나치 되돌림(옵션)을 계산합니다.
  - 계산 결과는 `timestamp`, `ticker`, 각 타임프레임 섹션, RSI 기반 `summation` 배열로 구성됩니다.
- **IndicatorWorker**
  - `interval_seconds`(기본 300초)마다 `IndicatorCalculator.build_payload()`를 호출해 캐시에 저장하는 백그라운드 태스크.
  - 앱 수명 동안 `start()`/`stop()`으로 관리되며, 실패 시 예외 로그만 남기고 루프를 지속합니다.

## 동작 흐름

1. 애플리케이션 시작 시 `TechnicalAgentConfig.from_env()`로 설정을 읽고, 캐시·계산기·워커를 생성합니다.
2. FastAPI `lifespan` 컨텍스트가 열리면 `IndicatorWorker.start()`가 즉시 한 번 계산 후 주기 실행을 스케줄링합니다.
3. 각 주기:
   - `yfinance.download()`으로 데이터 수집 → 데이터프레임 정리.
   - 지표 계산 함수(`_rsi`, `_macd`, `_bollinger`, `_format_mas`, `_fibonacci`)를 호출해 섹션을 구성.
   - `summation`은 일/주/월 타임프레임의 RSI를 -1~1 범위로 정규화해 배열로 저장.
   - 결과를 캐시 파일에 JSON으로 기록.
4. 앱 종료 시 `IndicatorWorker.stop()`이 호출돼 백그라운드 태스크를 정리합니다.

## FastAPI 엔드포인트

| 경로 | 메서드 | 설명 |
| ---- | ------ | ---- |
| `/health` | GET | 캐시에서 최근 계산 시각을 읽어 `status`, `ticker`, `last_updated`를 반환합니다. |
| `/api/result` | POST | 캐시에 저장된 최신 지표 페이로드 전체를 반환합니다. 캐시가 비어 있으면 503을 발생시킵니다. |

두 엔드포인트 모두 `IndicatorCache.read()`를 통해 동일한 캐시 데이터를 공유하며, 동기화는 `IndicatorCache`가 보장합니다.

## 환경 변수

| 변수 | 기본값 | 용도 |
| ---- | ------ | ---- |
| `TECH_AGENT_TICKER` | `SPY` | 분석 대상 티커 |
| `TECH_AGENT_INTERVAL_SECONDS` | `300` | 지표 계산 주기(초) |
| `TECH_AGENT_CACHE_PATH` | `shared/data/chart_signals.json` | 캐시 파일 경로 |
| `TECH_AGENT_MACD_FAST/SLOW/SIGNAL` | `14/28/9` | MACD 파라미터 |
| `TECH_AGENT_RSI_WINDOW` | `14` | RSI 윈도우 |
| `TECH_AGENT_BOLL_WINDOW` | `20` | 볼린저 밴드 기준 윈도우 |
| `TECH_AGENT_BOLL_STD` | `2.0` | 볼린저 밴드 표준편차 배수 |
| `TECH_AGENT_MA_TAIL` | `60` | 이동평균 tail 길이 |

모든 환경 변수는 문자열로 주입된 뒤 `int`/`float`로 변환됩니다.

## 로깅과 예외 처리

- 전역 `logging.basicConfig`로 INFO 레벨 로그를 남깁니다.
- `IndicatorWorker._run_once`는 계산 실패 시 잡은 예외를 로그에 기록하고 루프를 계속 진행합니다.
- `/ws`와 같은 실시간 인터페이스는 없으며, 모든 응답은 캐시된 계산 결과를 그대로 반환합니다.

## 의존성

- `yfinance`, `pandas`, `numpy`가 필수이며, 네트워크 환경에 따라 다운로드 실패 시 예외가 발생할 수 있습니다.
- 파일 캐시는 로컬 파일 시스템에 쓰기 권한이 있어야 하며, 경로는 존재하지 않을 경우 자동 생성됩니다.


