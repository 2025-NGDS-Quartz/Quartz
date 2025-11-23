"""포트폴리오 관리 에이전트 실행 스크립트."""

import asyncio

from agents.portfolio_manager import PortfolioManager


def main() -> None:
    asyncio.run(PortfolioManager().run_forever())


if __name__ == "__main__":
    main()

