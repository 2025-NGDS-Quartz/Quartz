# 실거래 에이전트 WebSocket 서버

from __future__ import annotations

import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from shared.models import ActionMessage, ResultStatus, TradeResult

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="Trading Agent", version="0.1.0")

MAX_NOTIONAL = 100_000.0
MIN_COST = 1.0


async def execute_order(order: ActionMessage) -> TradeResult:
    """모의 체결 로직."""

    if order.cost < MIN_COST:
        message = f"가격 {order.cost}는 허용치보다 낮습니다."
        suggested = order.model_copy(update={"cost": MIN_COST})
        return TradeResult(result=ResultStatus.FAIL, message=message, next_action=suggested)

    notional = order.cost * order.amount
    if notional > MAX_NOTIONAL:
        discount = round(order.cost * 0.95, 2)
        suggested = order.model_copy(
            update={"cost": discount, "amount": round(MAX_NOTIONAL / max(discount, MIN_COST), 4)}
        )
        message = f"주문 금액 {notional} > 한도 {MAX_NOTIONAL}"
        return TradeResult(result=ResultStatus.FAIL, message=message, next_action=suggested)

    message = f"주문 체결 완료 (notional={notional:.2f})"
    return TradeResult(result=ResultStatus.SUCCESS, message=message)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.websocket("/ws/trade")
async def trade_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("포트폴리오 관리 에이전트 연결")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                order = ActionMessage.model_validate_json(raw)
            except ValidationError as exc:
                logger.warning("주문 검증 실패: %s", exc)
                error = TradeResult(result=ResultStatus.FAIL, message="invalid payload")
                await websocket.send_text(error.model_dump_json())
                continue

            result = await execute_order(order)
            await websocket.send_text(result.model_dump_json())
    except WebSocketDisconnect:
        logger.info("포트폴리오 관리 에이전트 연결 종료")

