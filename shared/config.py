"""환경 변수 기반 설정 모듈."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import BaseModel, Field, HttpUrl


def _comma_split(value: str) -> List[str]:
    return [chunk.strip() for chunk in value.split(",") if chunk.strip()]


class Settings(BaseModel):
    """에이전트 전반에서 공유할 런타임 설정."""

    agent_hosts: List[HttpUrl]
    poll_interval_seconds: float = Field(
        default=5.0,
        ge=0.5,
        description="포트폴리오 관리 에이전트가 각 분석 에이전트를 폴링하는 주기",
    )
    trading_ws_url: str = Field(
        default="ws://localhost:8765/ws/trade",
        description="거래 에이전트 WebSocket 엔드포인트",
    )
    request_timeout: float = Field(
        default=10.0,
        ge=1.0,
        description="HTTP 요청 타임아웃 (초)",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        description="분석 에이전트 호출 실패 시 재시도 횟수",
    )
    retry_backoff_seconds: float = Field(
        default=2.0,
        ge=0,
        description="재시도 사이 대기시간",
    )
    signal_threshold: float = Field(
        default=0.1,
        ge=0,
        description="주문 여부를 결정할 최소 신호 크기",
    )
    default_ticker: str = Field(
        default="SPY",
        min_length=1,
        description="샘플 구현에서 사용할 기본 티커",
    )

    @staticmethod
    def from_env() -> "Settings":
        """환경 변수에서 설정을 구성."""

        hosts_env = os.getenv("AGENT_HOSTS", "")
        agent_hosts = (
            _comma_split(hosts_env)
            if hosts_env
            else ["http://localhost:9001", "http://localhost:9002"]
        )

        return Settings(
            agent_hosts=agent_hosts,
            poll_interval_seconds=float(os.getenv("POLL_INTERVAL_SECONDS", 5.0)),
            trading_ws_url=os.getenv(
                "TRADING_WS_URL", "ws://localhost:8765/ws/trade"
            ),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", 10.0)),
            max_retries=int(os.getenv("REQUEST_MAX_RETRIES", 2)),
            retry_backoff_seconds=float(os.getenv("REQUEST_RETRY_BACKOFF", 2.0)),
            signal_threshold=float(os.getenv("SIGNAL_THRESHOLD", 0.1)),
            default_ticker=os.getenv("DEFAULT_TICKER", "SPY"),
        )


@lru_cache()
def get_settings() -> Settings:
    """Settings 싱글톤."""

    return Settings.from_env()

