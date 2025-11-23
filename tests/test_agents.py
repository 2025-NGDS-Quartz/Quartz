import asyncio

import pytest

from agents.portfolio_manager import PortfolioManager
from agents.trading_agent import MAX_NOTIONAL, execute_order
from shared.config import Settings
from shared.models import ActionMessage, ActionType, AgentResult, ResultStatus


@pytest.fixture
def settings() -> Settings:
    return Settings(
        agent_hosts=["http://localhost:9001"],
        poll_interval_seconds=0.5,
        trading_ws_url="ws://localhost:0/ws/trade",
        request_timeout=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        signal_threshold=0.1,
        default_ticker="TEST",
    )


def test_aggregate_signals(settings: Settings) -> None:
    manager = PortfolioManager(settings=settings)
    sample = [
        AgentResult(timestamp="2024-01-01T00:00:00Z", summation=[0.5, 0.7]),
        AgentResult(timestamp="2024-01-01T00:00:01Z", summation=[-0.2]),
    ]
    aggregated = manager.aggregate_signals(sample)
    assert pytest.approx(aggregated["average_signal"]) == (0.5 + 0.7 - 0.2) / 3
    assert aggregated["sample_size"] == pytest.approx(3.0)


def test_decide_orders_positive_signal(settings: Settings) -> None:
    manager = PortfolioManager(settings=settings)
    order_list = manager.decide_orders({"average_signal": 1.0})
    assert len(order_list) == 1
    order = order_list[0]
    assert order.action == ActionType.BUY
    assert order.ticker == "TEST"


def test_decide_orders_small_signal(settings: Settings) -> None:
    manager = PortfolioManager(settings=settings)
    assert manager.decide_orders({"average_signal": 0.05}) == []


@pytest.mark.asyncio
async def test_execute_order_limits() -> None:
    order = ActionMessage(action=ActionType.BUY, ticker="X", cost=1.0, amount=MAX_NOTIONAL * 2)
    result = await execute_order(order)
    assert result.result == ResultStatus.FAIL
    assert result.next_action is not None


