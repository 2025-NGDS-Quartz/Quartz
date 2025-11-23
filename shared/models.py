"""에이전트 간 교환되는 데이터 모델 정의."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class ResultStatus(str, Enum):
    SUCCESS = "success"
    FAIL = "fail"


class AgentResult(BaseModel):
    """각 분석 에이전트가 반환하는 `/api/result` 데이터."""

    timestamp: datetime
    summation: List[float] = Field(..., min_length=1)

    @field_validator("summation")
    @classmethod
    def validate_summation(cls, value: List[float]) -> List[float]:
        if not value:
            raise ValueError("summation must contain at least one value")
        return value


class ActionMessage(BaseModel):
    """포트폴리오 관리 에이전트가 거래 에이전트로 전송하는 주문."""

    action: ActionType
    ticker: str
    cost: float = Field(..., gt=0)
    amount: float = Field(..., gt=0)


class TradeResult(BaseModel):
    """거래 에이전트가 반환하는 체결 상태."""

    result: ResultStatus
    message: str = ""
    next_action: Optional[ActionMessage] = Field(
        default=None,
        description="실패 시 거래 에이전트가 제안하는 후속 주문",
    )


