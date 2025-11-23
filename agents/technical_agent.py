"""차트 기술분석 에이전트 FastAPI 앱."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf  # type: ignore[import-untyped]
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_PATH = PROJECT_ROOT / "shared" / "data" / "chart_signals.json"


@dataclass(frozen=True)
class TimeframeConfig:
    period: str
    interval: str
    include_fibonacci: bool = False


@dataclass(frozen=True)
class TechnicalAgentConfig:
    ticker: str = "SPY"
    interval_seconds: int = 300
    cache_path: Path = DEFAULT_CACHE_PATH
    macd_fast: int = 14
    macd_slow: int = 28
    macd_signal: int = 9
    rsi_window: int = 14
    bollinger_window: int = 20
    bollinger_std: float = 2.0
    ma_windows: List[int] = field(default_factory=lambda: [20, 60, 120])
    ma_tail: int = 60
    timeframes: Dict[str, TimeframeConfig] = field(
        default_factory=lambda: {
            "daily": TimeframeConfig(period="6mo", interval="1d", include_fibonacci=True),
            "weekly": TimeframeConfig(period="5y", interval="1wk", include_fibonacci=True),
            "monthly": TimeframeConfig(period="15y", interval="1mo", include_fibonacci=False),
        }
    )

    @classmethod
    def from_env(cls) -> "TechnicalAgentConfig":
        """환경 변수 기반 설정."""

        ticker = os.getenv("TECH_AGENT_TICKER", cls.ticker)
        interval_seconds = int(os.getenv("TECH_AGENT_INTERVAL_SECONDS", cls.interval_seconds))
        cache_path = Path(os.getenv("TECH_AGENT_CACHE_PATH", str(DEFAULT_CACHE_PATH)))
        macd_fast = int(os.getenv("TECH_AGENT_MACD_FAST", cls.macd_fast))
        macd_slow = int(os.getenv("TECH_AGENT_MACD_SLOW", cls.macd_slow))
        macd_signal = int(os.getenv("TECH_AGENT_MACD_SIGNAL", cls.macd_signal))
        rsi_window = int(os.getenv("TECH_AGENT_RSI_WINDOW", cls.rsi_window))
        bollinger_window = int(os.getenv("TECH_AGENT_BOLL_WINDOW", cls.bollinger_window))
        bollinger_std = float(os.getenv("TECH_AGENT_BOLL_STD", cls.bollinger_std))
        ma_tail = int(os.getenv("TECH_AGENT_MA_TAIL", cls.ma_tail))
        return cls(
            ticker=ticker,
            interval_seconds=interval_seconds,
            cache_path=cache_path,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            rsi_window=rsi_window,
            bollinger_window=bollinger_window,
            bollinger_std=bollinger_std,
            ma_tail=ma_tail,
        )


class IndicatorCache:
    """파일 기반 캐시."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def write(self, data: Dict[str, Any]) -> None:
        text = json.dumps(data, ensure_ascii=False, indent=2)

        async with self._lock:
            await asyncio.to_thread(self._write_atomic, text)

    async def read(self) -> Optional[Dict[str, Any]]:
        if not self.path.exists():
            return None
        async with self._lock:
            return await asyncio.to_thread(self._read_json)

    def _write_atomic(self, text: str) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(self.path)

    def _read_json(self) -> Dict[str, Any]:
        raw = self.path.read_text(encoding="utf-8")
        return json.loads(raw)


class IndicatorCalculator:
    """가격 데이터 다운로드 및 지표 계산."""

    def __init__(self, config: TechnicalAgentConfig) -> None:
        self.config = config

    async def build_payload(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self._build_payload_sync)

    def _build_payload_sync(self) -> Dict[str, Any]:
        sections: Dict[str, Dict[str, Any]] = {}
        for name, timeframe in self.config.timeframes.items():
            logger.info("지표 계산 시작: %s", name)
            data = self._download_history(timeframe)
            sections[name] = self._compute_section(data, timeframe)

        timestamp = datetime.now(timezone.utc).isoformat()
        payload: Dict[str, Any] = {
            "timestamp": timestamp,
            "ticker": self.config.ticker,
            **sections,
        }
        payload["summation"] = self._summarize_signals(sections)
        return payload

    def _download_history(self, timeframe: TimeframeConfig) -> pd.DataFrame:
        df = yf.download(
            self.config.ticker,
            period=timeframe.period,
            interval=timeframe.interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if df.empty:
            raise ValueError(f"데이터를 불러오지 못했습니다. ticker={self.config.ticker}")
        # 일관된 컬럼명을 위해 MultiIndex 제거
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        return df.dropna()

    def _compute_section(self, df: pd.DataFrame, timeframe: TimeframeConfig) -> Dict[str, Any]:
        close = df["Close"]
        highs = df["High"]
        lows = df["Low"]

        section: Dict[str, Any] = {
            "cost": self._safe_float(close.iloc[-1]),
            "rsi": self._safe_float(self._rsi(close)),
            "macd": self._format_macd(self._macd(close)),
            "bollinger_band": self._format_bollinger(self._bollinger(close)),
            "ma_av": self._format_mas(close),
        }
        if timeframe.include_fibonacci:
            section["fibonacci_retracement"] = self._fibonacci(highs, lows)
        return section

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

    def _macd(self, series: pd.Series) -> Dict[str, float]:
        fast = series.ewm(span=self.config.macd_fast, adjust=False).mean()
        slow = series.ewm(span=self.config.macd_slow, adjust=False).mean()
        macd_line = fast - slow
        signal_line = macd_line.ewm(span=self.config.macd_signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return {
            "macd": float(macd_line.iloc[-1]),
            "signal": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1]),
        }

    def _bollinger(self, series: pd.Series) -> Dict[str, float]:
        window = self.config.bollinger_window
        rolling = series.rolling(window=window, min_periods=window)
        middle = rolling.mean().iloc[-1]
        std = rolling.std().iloc[-1]
        upper = middle + self.config.bollinger_std * std
        lower = middle - self.config.bollinger_std * std
        return {"upper": upper, "middle": middle, "lower": lower}

    def _fibonacci(self, highs: pd.Series, lows: pd.Series) -> Dict[str, Any]:
        high = float(highs.max())
        low = float(lows.min())
        diff = high - low if high != low else 0.0
        levels = {
            "0.0": high,
            "0.236": high - diff * 0.236,
            "0.382": high - diff * 0.382,
            "0.5": high - diff * 0.5,
            "0.618": high - diff * 0.618,
            "0.786": high - diff * 0.786,
            "1.0": low,
        }
        return {
            "high": self._safe_float(high),
            "low": self._safe_float(low),
            "levels": {k: self._safe_float(v) for k, v in levels.items()},
        }

    def _format_mas(self, series: pd.Series) -> Dict[str, List[float]]:
        mas: Dict[str, List[float]] = {}
        for window in self.config.ma_windows:
            ma = series.rolling(window=window, min_periods=window).mean().dropna()
            tail = ma.tail(self.config.ma_tail)
            key = f"ma{window}"
            mas[key] = [self._safe_float(value) for value in tail.tolist()]
        return mas

    def _format_bollinger(self, band: Dict[str, float]) -> Dict[str, float]:
        return {key: self._safe_float(value) for key, value in band.items()}

    def _format_macd(self, macd: Dict[str, float]) -> Dict[str, float]:
        formatted = {key: self._safe_float(value) for key, value in macd.items()}
        formatted["fast"] = self.config.macd_fast
        formatted["slow"] = self.config.macd_slow
        formatted["signal_window"] = self.config.macd_signal
        return formatted

    def _safe_float(self, value: float) -> float:
        return round(float(value), 6)

    def _summarize_signals(self, sections: Dict[str, Dict[str, Any]]) -> List[float]:
        signals: List[float] = []
        for key in ("daily", "weekly", "monthly"):
            section = sections.get(key)
            if not section:
                continue
            rsi = section.get("rsi")
            if rsi is None:
                continue
            signals.append(self._normalize_signal(rsi))
        return signals or [0.0]

    def _normalize_signal(self, rsi_value: float) -> float:
        normalized = (rsi_value - 50.0) / 50.0
        return max(min(round(normalized, 6), 1.0), -1.0)


class IndicatorWorker:
    """5분 주기로 지표를 계산하고 캐시에 저장."""

    def __init__(self, calculator: IndicatorCalculator, cache: IndicatorCache, interval: int) -> None:
        self.calculator = calculator
        self.cache = cache
        self.interval = interval
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        await self._run_once()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
                break
            except asyncio.TimeoutError:
                await self._run_once()
                continue

    async def _run_once(self) -> None:
        try:
            payload = await self.calculator.build_payload()
            await self.cache.write(payload)
            logger.info("지표 계산 완료: %s", payload["timestamp"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("지표 계산 실패: %s", exc)


config = TechnicalAgentConfig.from_env()
cache = IndicatorCache(config.cache_path)
calculator = IndicatorCalculator(config)
worker = IndicatorWorker(calculator, cache, config.interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await worker.start()
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(
    title="Chart Technical Analysis Agent",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> JSONResponse:
    cached = await cache.read()
    return JSONResponse(
        {
            "status": "ok",
            "ticker": config.ticker,
            "last_updated": cached["timestamp"] if cached else None,
        }
    )


@app.post("/api/result")
async def api_result() -> JSONResponse:
    cached = await cache.read()
    if cached is None:
        raise HTTPException(status_code=503, detail="indicator cache empty")
    return JSONResponse(cached)


