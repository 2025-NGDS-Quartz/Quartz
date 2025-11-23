# Technical Agent 지표 계산 상세

`agents/technical_agent.py`는 `/api/analyze` 요청을 처리할 때 각 티커에 대해 `IndicatorCalculator`를 통해 기술 지표를 생성합니다. 이 문서는 지표별 계산 과정을 코드 기반으로 설명합니다.

## 1. 데이터 준비

- `yfinance.download()`으로 타임프레임별 시세(High/Low/Close)를 가져옵니다. 멀티 인덱스 컬럼이 오면 1차컬럼만 추출하고, 결측치는 `dropna()`로 제거합니다.
- 데이터가 비어 있으면 `ValueError`를 발생시켜 호출자에게 실패 티커로 전달합니다.
- 모든 수치 결과는 `_safe_float()`에서 `round(value, 6)`을 거쳐 JSON 직렬화 오차를 줄입니다.

## 2. RSI (Relative Strength Index)

```
174:199:agents/technical_agent.py
    def _rsi(self, series: pd.Series) -> float:
        window = self.config.rsi_window
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=window, min_periods=window).mean()
        avg_loss = loss.rolling(window=window, min_periods=window).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
```

1. 종가 시리즈의 1차 차분(`delta`)을 계산합니다.
2. 양의 변화만 `gain`, 음의 변화 절댓값을 `loss`로 분리합니다.
3. 설정된 `rsi_window`(기본 14) 길이로 이동평균을 취해 `avg_gain`, `avg_loss`를 구합니다.
4. `RS = avg_gain / avg_loss` (0 분모는 NaN으로 대체) 후, `RSI = 100 - 100/(1+RS)` 공식을 적용합니다.
5. 가장 최근 값만 반환합니다.

## 3. MACD (Moving Average Convergence Divergence)

```
201:211:agents/technical_agent.py
    def _macd(self, series: pd.Series) -> Dict[str, float]:
        fast = series.ewm(span=self.config.macd_fast, adjust=False).mean()
        slow = series.ewm(span=self.config.macd_slow, adjust=False).mean()
        macd_line = fast - slow
        signal_line = macd_line.ewm(span=self.config.macd_signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return {"macd": ..., "signal": ..., "histogram": ...}
```

- `macd_fast`(기본 14)와 `macd_slow`(기본 28) EMA로 MACD 라인을 구성하고, `macd_signal`(기본 9) EMA로 시그널 라인을 만듭니다.
- 히스토그램은 `macd_line - signal_line`입니다.
- `_format_macd()`는 결과에 FAST/SLOW/Signal 윈도우 메타데이터를 함께 포함합니다.

## 4. Bollinger Band

```
213:220:agents/technical_agent.py
    def _bollinger(self, series: pd.Series) -> Dict[str, float]:
        window = self.config.bollinger_window
        rolling = series.rolling(window=window, min_periods=window)
        middle = rolling.mean().iloc[-1]
        std = rolling.std().iloc[-1]
        upper = middle + self.config.bollinger_std * std
        lower = middle - self.config.bollinger_std * std
```

- `bollinger_window`(기본 20) 길이의 이동평균과 표준편차를 사용합니다.
- 상단/하단 밴드는 `middle ± bollinger_std * std`로 계산합니다(기본 표준편차 배수 2.0).

## 5. 이동평균 묶음

```
241:248:agents/technical_agent.py
    def _format_mas(self, series: pd.Series) -> Dict[str, List[float]]:
        for window in self.config.ma_windows:
            ma = series.rolling(window=window, min_periods=window).mean().dropna()
            tail = ma.tail(self.config.ma_tail)
            key = f"ma{window}"
            mas[key] = [self._safe_float(value) for value in tail.tolist()]
```

- `ma_windows`(기본 [20, 60, 120]) 각각에 대해 단순 이동평균을 계산합니다.
- `ma_tail`(기본 60) 만큼의 최근 값만 리스트로 보관하여 시각화나 추세 비교에 사용할 수 있게 합니다.

## 6. 피보나치 되돌림

```
222:239:agents/technical_agent.py
    def _fibonacci(self, highs: pd.Series, lows: pd.Series) -> Dict[str, Any]:
        high = float(highs.max())
        low = float(lows.min())
        diff = high - low if high != low else 0.0
        levels = {
            "0.0": high,
            "0.236": high - diff * 0.236,
            ...
            "1.0": low,
        }
```

- 타임프레임 전체의 최고가/최저가를 사용해 구간 폭 `diff`를 계산합니다.
- 표준 비율(0.236, 0.382, 0.5, 0.618, 0.786)을 적용하여 레벨별 가격을 도출하고, high/low/levels를 반환합니다.
- `include_fibonacci=True`인 타임프레임(기본 daily, weekly)만 이 섹션이 포함됩니다.

## 7. Summation 정규화 점수

```
263:277:agents/technical_agent.py
    def _summarize_signals(self, sections: Dict[str, Dict[str, Any]]) -> List[float]:
        for key in ("daily", "weekly", "monthly"):
            ...
            signals.append(self._normalize_signal(rsi))
        return signals or [0.0]
```

- 일·주·월 타임프레임의 RSI를 수집해 `_normalize_signal(rsi)`을 적용합니다.
- 정규화 공식: `(rsi - 50) / 50` → `round(..., 6)` → `[-1.0, 1.0]`로 클램핑.
- 결과 배열은 포트폴리오 에이전트가 여러 기간의 편향을 단일 벡터로 활용할 수 있게 설계되었습니다.

## 8. 오류 처리 및 응답 구조

- 각 지표 계산에서 예외가 발생하면 `/api/analyze`는 해당 티커만 `status="error"`로 표시하고 오류 메시지를 포함합니다.
- 정상 계산 시 `payload`에는 `timestamp`, `ticker`, 타임프레임별 섹션(각각 `cost`, `rsi`, `macd`, `bollinger_band`, `ma_av`, 필요 시 `fibonacci_retracement`), 그리고 `summation`이 포함됩니다.

