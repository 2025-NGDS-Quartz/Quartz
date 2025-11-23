# 포트폴리오 관리 에이전트

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List, Optional

import httpx
import websockets
from websockets import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed

from shared.config import Settings, get_settings
from shared.models import ActionMessage, ActionType, AgentResult, ResultStatus, TradeResult

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


class PortfolioManager:
    """분석 에이전트 데이터를 집계하고 거래 에이전트로 주문을 전달."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._ws: Optional[WebSocketClientProtocol] = None
        self._ws_lock = asyncio.Lock()

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.settings.request_timeout)
        return self._http_client

    async def _fetch_agent_result(self, host: str) -> Optional[AgentResult]:
        client = await self._get_http_client()
        url = host.rstrip("/") + "/api/result"
        attempt = 0
        while attempt <= self.settings.max_retries:
            try:
                response = await client.post(url, json={})
                response.raise_for_status()
                payload = response.json()
                return AgentResult.model_validate(payload)
            except Exception as exc:  # noqa: BLE001 - 로깅 후 재시도
                attempt += 1
                if attempt > self.settings.max_retries:
                    logger.warning("에이전트 %s 호출 실패: %s", host, exc)
                    return None
                await asyncio.sleep(self.settings.retry_backoff_seconds)

    async def collect_agent_results(self) -> List[AgentResult]:
        tasks = [self._fetch_agent_result(host) for host in self.settings.agent_hosts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        parsed: List[AgentResult] = []
        for idx, host in enumerate(self.settings.agent_hosts):
            result = results[idx]
            if isinstance(result, Exception):
                logger.error("에이전트 %s 호출 중 예외: %s", host, result)
                continue
            if result is None:
                continue
            parsed.append(result)
        return parsed

    @staticmethod
    def aggregate_signals(results: List[AgentResult]) -> Dict[str, float]:
        if not results:
            return {}
        merged: List[float] = []
        for item in results:
            merged.extend(item.summation)
        total = sum(merged)
        avg = total / len(merged)
        return {
            "sample_size": float(len(merged)),
            "average_signal": avg,
            "total_signal": total,
        }

    def decide_orders(self, aggregated: Dict[str, float]) -> List[ActionMessage]:
        if not aggregated:
            return []
        avg_signal = aggregated.get("average_signal")
        if avg_signal is None:
            return []
        threshold = self.settings.signal_threshold

        if avg_signal > threshold:
            action = ActionType.BUY
        elif avg_signal < -threshold:
            action = ActionType.SELL
        else:
            return []

        strength = abs(avg_signal)
        cost = round(100 + strength * 10, 2)
        amount = round(max(1.0, strength * 10), 2)
        order = ActionMessage(
            action=action,
            ticker=self.settings.default_ticker,
            cost=cost,
            amount=amount,
        )
        return [order]

    async def _ensure_ws(self) -> WebSocketClientProtocol:
        if self._ws and not self._ws.closed:
            return self._ws

        if self._ws is not None:
            await self._ws.close()
            self._ws = None

        logger.info("거래 에이전트 WebSocket 연결 시도: %s", self.settings.trading_ws_url)
        self._ws = await websockets.connect(self.settings.trading_ws_url)
        return self._ws

    async def send_order(self, order: ActionMessage) -> Optional[TradeResult]:
        async with self._ws_lock:
            ws = await self._ensure_ws()
            payload = order.model_dump_json()
            try:
                await ws.send(payload)
                response_raw = await ws.recv()
                data = json.loads(response_raw)
                return TradeResult.model_validate(data)
            except ConnectionClosed:
                logger.warning("WebSocket 연결이 끊어졌습니다. 재연결을 시도합니다.")
                self._ws = None
                return await self.send_order(order)
            except Exception as exc:  # noqa: BLE001
                logger.error("주문 전송 실패: %s", exc)
                return None

    async def dispatch_orders(self, orders: List[ActionMessage]) -> None:
        for order in orders:
            result = await self.send_order(order)
            if result is None:
                continue
            if result.result == ResultStatus.SUCCESS:
                logger.info("주문 성공: %s", order)
                continue
            logger.warning("주문 실패: %s | 사유: %s", order, result.message)
            if result.next_action:
                logger.info("대안 주문 실행: %s", result.next_action)
                await self.send_order(result.next_action)

    async def run_once(self) -> None:
        results = await self.collect_agent_results()
        aggregated = self.aggregate_signals(results)
        orders = self.decide_orders(aggregated)
        await self.dispatch_orders(orders)

    async def run_forever(self) -> None:
        logger.info("포트폴리오 관리 에이전트 시작")
        try:
            while True:
                await self.run_once()
                await asyncio.sleep(self.settings.poll_interval_seconds)
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
        if self._ws is not None:
            await self._ws.close()
            self._ws = None


async def main() -> None:
    manager = PortfolioManager()
    await manager.run_forever()


if __name__ == "__main__":
    asyncio.run(main())

