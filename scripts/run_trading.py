"""실거래 에이전트 서버 실행 스크립트."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "agents.trading_agent:app",
        host="0.0.0.0",
        port=8765,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

