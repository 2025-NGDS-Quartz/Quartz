"""
인증관리 에이전트 (Auth Agent)
- 한국투자증권 OAuth 토큰 관리
- 다른 에이전트들에게 토큰 제공
- 포트: 8006
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "agent": "auth-agent", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# 환경변수
HANSEC_APP_KEY = os.getenv("HANSEC_INVESTMENT_APP_KEY", "")
HANSEC_APP_SECRET = os.getenv("HANSEC_INVESTMENT_APP_SECRET_KEY", "")
HANSEC_BASE_URL = "https://openapi.koreainvestment.com:9443"

# 토큰 갱신 주기 (23시간 55분 = 86100초)
TOKEN_REFRESH_INTERVAL = 86100


class TokenResponse(BaseModel):
    """토큰 응답 모델"""
    token: str
    token_type: str
    expires_at: str


class TokenStatusResponse(BaseModel):
    """토큰 상태 응답 모델"""
    is_valid: bool
    expires_at: Optional[str]
    remaining_seconds: int


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str


class AuthTokenManager:
    """OAuth 토큰 관리 클래스"""
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.token_type: str = "Bearer"
        self.expires_at: Optional[datetime] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """토큰 초기화 및 발급"""
        success = await self._issue_token()
        if success:
            # 백그라운드 갱신 태스크 시작
            self._refresh_task = asyncio.create_task(self._auto_refresh_loop())
            logger.info("Token manager initialized successfully")
        return success
    
    async def shutdown(self):
        """종료 처리"""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
    
    async def _issue_token(self) -> bool:
        """토큰 발급"""
        if not HANSEC_APP_KEY or not HANSEC_APP_SECRET:
            logger.error("Missing HANSEC_INVESTMENT_APP_KEY or HANSEC_INVESTMENT_APP_SECRET_KEY")
            return False
        
        url = f"{HANSEC_BASE_URL}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": HANSEC_APP_KEY,
            "appsecret": HANSEC_APP_SECRET
        }
        
        retry_count = 0
        max_retries = 5
        retry_delay = 30  # 초
        
        while retry_count < max_retries:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        async with self._lock:
                            self.access_token = data.get("access_token")
                            self.token_type = data.get("token_type", "Bearer")
                            
                            # 만료 시간 파싱 (형식: "2024-01-16 08:16:59")
                            # 한국투자증권 API는 KST(한국 시간)으로 반환
                            expires_str = data.get("access_token_token_expired", "")
                            if expires_str:
                                # KST로 파싱 후 UTC로 변환하여 저장
                                kst = ZoneInfo("Asia/Seoul")
                                expires_naive = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
                                expires_kst = expires_naive.replace(tzinfo=kst)
                                self.expires_at = expires_kst.astimezone(timezone.utc)
                            else:
                                # expires_in 사용 (초 단위)
                                expires_in = data.get("expires_in", 86400)
                                self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                        
                        logger.info(f"Token issued successfully, expires at: {self.expires_at}")
                        return True
                    else:
                        logger.error(f"Token issue failed: {response.status_code} - {response.text}")
                        
            except Exception as e:
                logger.error(f"Token issue error: {str(e)}")
            
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying token issue in {retry_delay} seconds... ({retry_count}/{max_retries})")
                await asyncio.sleep(retry_delay)
        
        logger.error("Failed to issue token after maximum retries")
        return False
    
    async def _auto_refresh_loop(self):
        """자동 토큰 갱신 루프"""
        while True:
            try:
                await asyncio.sleep(TOKEN_REFRESH_INTERVAL)
                logger.info("Starting scheduled token refresh")
                await self._issue_token()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto refresh error: {str(e)}")
    
    async def get_token(self, auto_issue: bool = True) -> Optional[dict]:
        """
        토큰 조회
        - 토큰이 없으면 발급 시도 (auto_issue=True일 때)
        - 만료 5분 전이면 즉시 갱신
        """
        # 토큰이 없으면 발급 시도
        if not self.access_token and auto_issue:
            logger.info("No token available, attempting to issue...")
            await self._issue_token()
        
        async with self._lock:
            if not self.access_token:
                return None
            
            # 만료 5분 전 체크
            if self.expires_at:
                now_utc = datetime.now(timezone.utc)
                remaining = (self.expires_at - now_utc).total_seconds()
                if remaining < 300:  # 5분 미만
                    logger.info("Token expiring soon, refreshing...")
        
        # 5분 미만이면 갱신
        now_utc = datetime.now(timezone.utc)
        if self.expires_at and (self.expires_at - now_utc).total_seconds() < 300:
            await self._issue_token()
        
        async with self._lock:
            if not self.access_token:
                return None
            return {
                "token": self.access_token,
                "token_type": self.token_type,
                "expires_at": self.expires_at.isoformat() if self.expires_at else None
            }
    
    def get_status(self) -> dict:
        """토큰 상태 조회"""
        is_valid = self.access_token is not None
        remaining = 0
        
        if self.expires_at:
            # UTC 기준으로 남은 시간 계산
            now_utc = datetime.now(timezone.utc)
            remaining = max(0, int((self.expires_at - now_utc).total_seconds()))
            if remaining == 0:
                is_valid = False
        
        return {
            "is_valid": is_valid,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "remaining_seconds": remaining
        }


# 전역 토큰 매니저
token_manager = AuthTokenManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    # 시작 시 토큰 발급
    success = await token_manager.initialize()
    if not success:
        logger.error("Failed to initialize token manager")
        # k8s가 재시작할 수 있도록 예외 발생하지 않음
    
    yield
    
    # 종료 시 정리
    await token_manager.shutdown()


app = FastAPI(
    title="Auth Agent",
    description="한국투자증권 OAuth 토큰 관리 에이전트",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/result/auth-token", response_model=TokenResponse)
async def get_auth_token():
    """인증 토큰 조회 API"""
    token_data = await token_manager.get_token()
    
    if not token_data:
        raise HTTPException(
            status_code=503,
            detail="Token not available. Please retry later."
        )
    
    return TokenResponse(
        token=token_data["token"],
        token_type=token_data["token_type"],
        expires_at=token_data["expires_at"]
    )


@app.get("/result/auth-token/status", response_model=TokenStatusResponse)
async def get_token_status():
    """토큰 상태 조회 API"""
    status = token_manager.get_status()
    return TokenStatusResponse(**status)


@app.get("/health/live", response_model=HealthResponse)
async def liveness_probe():
    """Liveness probe - 프로세스 생존 여부"""
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=HealthResponse)
async def readiness_probe():
    """
    Readiness probe - 서비스 준비 여부
    토큰이 없으면 발급 시도 후 결과 반환
    """
    status = token_manager.get_status()
    
    # 토큰이 없거나 만료됐으면 발급 시도
    if not status["is_valid"]:
        logger.info("Readiness check: token not valid, attempting to issue...")
        token_data = await token_manager.get_token(auto_issue=True)
        
        if token_data is None:
            # 발급 실패 - 하지만 503 대신 상태 반환 (k8s가 재시도하도록)
            logger.warning("Readiness check: token issue failed")
            raise HTTPException(status_code=503, detail="Token not available - issue failed")
    
    return HealthResponse(status="ok")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)

