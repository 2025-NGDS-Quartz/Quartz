"""차트 기술분석 에이전트 실행 스크립트."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "agents.technical_agent:app",
        host="0.0.0.0",
        port=9003,
        reload=False,
        factory=False,
    )


if __name__ == "__main__":
    main()


