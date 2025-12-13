"""
Quartz Frontend API Proxy Server
- 프론트엔드와 각 에이전트 사이의 프록시 역할
- k3s 클러스터 내부 에이전트들과 통신
- 포트: 8080
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "agent": "api-proxy", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# 에이전트 URL (k3s 내부 DNS)
AUTH_AGENT_URL = os.getenv("AUTH_AGENT_URL", "http://auth-agent:8006")
MACRO_AGENT_URL = os.getenv("MACRO_AGENT_URL", "http://macro-agent:8001")
TICKER_SELECTOR_URL = os.getenv("TICKER_SELECTOR_URL", "http://ticker-selector:8002")
TECHNICAL_AGENT_URL = os.getenv("TECHNICAL_AGENT_URL", "http://technical-agent:8003")
PORTFOLIO_MANAGER_URL = os.getenv("PORTFOLIO_MANAGER_URL", "http://portfolio-manager:8004")
TRADING_AGENT_URL = os.getenv("TRADING_AGENT_URL", "http://trading-agent:8005")

# 에이전트 정보
AGENTS = [
    {"name": "인증관리", "port": 8006, "serviceName": "auth-agent", "url": AUTH_AGENT_URL},
    {"name": "거시경제분석", "port": 8001, "serviceName": "macro-agent", "url": MACRO_AGENT_URL},
    {"name": "거래종목선택", "port": 8002, "serviceName": "ticker-selector", "url": TICKER_SELECTOR_URL},
    {"name": "기술분석", "port": 8003, "serviceName": "technical-agent", "url": TECHNICAL_AGENT_URL},
    {"name": "포트폴리오관리", "port": 8004, "serviceName": "portfolio-manager", "url": PORTFOLIO_MANAGER_URL},
    {"name": "거래", "port": 8005, "serviceName": "trading-agent", "url": TRADING_AGENT_URL},
]

app = FastAPI(
    title="Quartz API Proxy",
    description="프론트엔드용 API 프록시 서버",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 데이터 모델 ====================

class AgentHealth(BaseModel):
    name: str
    port: int
    serviceName: str
    live: bool
    ready: bool
    lastCheck: str


class Position(BaseModel):
    ticker: str
    name: str
    shares: int
    avg_price: float
    current_price: int
    eval_amount: int
    profit_loss_rate: float
    weight_in_portfolio: float


class Portfolio(BaseModel):
    cash_krw: int
    total_value: int
    positions: List[Position]
    last_updated: str


class CandidatesRequest(BaseModel):
    top_n: int = 5


class TechnicalRequest(BaseModel):
    ticker: str


class TokenStatus(BaseModel):
    is_valid: bool
    expires_at: Optional[str]
    remaining_seconds: int


# ==================== 헬스체크 ====================

@app.get("/api/health/agents", response_model=List[AgentHealth])
async def check_all_agents_health():
    """모든 에이전트의 헬스체크"""
    results = []
    
    async def check_agent(agent: dict) -> AgentHealth:
        live = False
        ready = False
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Liveness check
                try:
                    response = await client.get(f"{agent['url']}/health/live")
                    live = response.status_code == 200
                except:
                    pass
                
                # Readiness check
                try:
                    response = await client.get(f"{agent['url']}/health/ready")
                    ready = response.status_code == 200
                except:
                    pass
        except Exception as e:
            logger.warning(f"Health check failed for {agent['serviceName']}: {e}")
        
        return AgentHealth(
            name=agent["name"],
            port=agent["port"],
            serviceName=agent["serviceName"],
            live=live,
            ready=ready,
            lastCheck=datetime.utcnow().isoformat() + "Z"
        )
    
    # 병렬로 헬스체크 수행
    tasks = [check_agent(agent) for agent in AGENTS]
    results = await asyncio.gather(*tasks)
    
    return results


# ==================== 포트폴리오 ====================

@app.get("/api/portfolio", response_model=Portfolio)
async def get_portfolio():
    """포트폴리오 현황 조회"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{PORTFOLIO_MANAGER_URL}/api/portfolio")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Portfolio API error: {response.status_code}")
                raise HTTPException(status_code=response.status_code, detail="포트폴리오 조회 실패")
    except httpx.RequestError as e:
        logger.error(f"Portfolio request error: {e}")
        raise HTTPException(status_code=503, detail="포트폴리오 관리 에이전트 연결 실패")


# ==================== 종목 후보 ====================

@app.post("/api/candidates")
async def get_candidates(request: CandidatesRequest):
    """후보 종목 조회"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TICKER_SELECTOR_URL}/api/candidates",
                json={"top_n": request.top_n}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # 데이터가 없어도 빈 응답 반환
                logger.warning(f"Candidates API returned {response.status_code}")
                return {
                    "timestamp": datetime.now().isoformat(),
                    "total_stocks": 0,
                    "statistics": {"high_priority": 0, "mid_priority": 0, "low_priority": 0},
                    "top_candidates": []
                }
    except httpx.RequestError as e:
        logger.error(f"Candidates request error: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "total_stocks": 0,
            "statistics": {"high_priority": 0, "mid_priority": 0, "low_priority": 0},
            "top_candidates": []
        }


# ==================== 기술적 분석 ====================

@app.post("/api/technical-analysis")
async def get_technical_analysis(request: TechnicalRequest):
    """기술적 분석 조회"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{TECHNICAL_AGENT_URL}/result/analysis",
                json={"ticker": request.ticker}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Technical analysis API error: {response.status_code}")
                raise HTTPException(status_code=response.status_code, detail="기술 분석 조회 실패")
    except httpx.RequestError as e:
        logger.error(f"Technical analysis request error: {e}")
        raise HTTPException(status_code=503, detail="기술분석 에이전트 연결 실패")


# ==================== 토큰 상태 ====================

@app.get("/api/token-status", response_model=TokenStatus)
async def get_token_status():
    """인증 토큰 상태 조회"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{AUTH_AGENT_URL}/result/auth-token/status")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Token status API returned {response.status_code}")
                return TokenStatus(is_valid=False, expires_at=None, remaining_seconds=0)
    except httpx.RequestError as e:
        logger.error(f"Token status request error: {e}")
        return TokenStatus(is_valid=False, expires_at=None, remaining_seconds=0)


# ==================== 거시경제 요약 ====================

@app.get("/api/macro-summary")
async def get_macro_summary():
    """거시경제 요약 조회"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{MACRO_AGENT_URL}/result/analysis")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Macro summary API returned {response.status_code}")
                return {
                    "positive_summary": "거시경제 데이터 없음",
                    "negative_summary": "거시경제 데이터 없음",
                    "market_bias_hint": "uncertain"
                }
    except httpx.RequestError as e:
        logger.error(f"Macro summary request error: {e}")
        return {
            "positive_summary": "거시경제 데이터 조회 실패",
            "negative_summary": "거시경제 데이터 조회 실패",
            "market_bias_hint": "uncertain"
        }


# ==================== 매매 결정 ====================

@app.post("/api/decision")
async def trigger_decision():
    """수동 매매 결정 트리거"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{PORTFOLIO_MANAGER_URL}/api/decision")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Decision API error: {response.status_code}")
                raise HTTPException(status_code=response.status_code, detail="매매 결정 실패")
    except httpx.RequestError as e:
        logger.error(f"Decision request error: {e}")
        raise HTTPException(status_code=503, detail="포트폴리오 관리 에이전트 연결 실패")


# ==================== 서버 헬스체크 ====================

@app.get("/health/live")
async def liveness_probe():
    """Liveness probe"""
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness_probe():
    """Readiness probe"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
