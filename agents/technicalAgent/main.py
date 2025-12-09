"""
기술분석 에이전트 (Technical Analysis Agent)
- ticker를 받아 RSI, MACD, Bollinger-Band, 피보나치되돌림, MA 계산
- 일/주/월 단위 기술적 분석 제공
- 포트: 8003
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager

import httpx
import numpy as np
import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "agent": "technical-agent", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# 환경변수
HANSEC_APP_KEY = os.getenv("HANSEC_INVESTMENT_APP_KEY", "")
HANSEC_APP_SECRET = os.getenv("HANSEC_INVESTMENT_APP_SECRET_KEY", "")
HANSEC_BASE_URL = "https://openapi.koreainvestment.com:9443"
AUTH_AGENT_URL = os.getenv("AUTH_AGENT_URL", "http://auth-agent:8006")

# AWS S3 설정
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "quartz-bucket")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# 캐시 설정 (5분)
CACHE_TTL_SECONDS = 300


class AnalysisRequest(BaseModel):
    """분석 요청 모델"""
    ticker: str


class MAData(BaseModel):
    """이동평균선 데이터"""
    ma5: float
    ma10: float
    ma20: float


class MACDData(BaseModel):
    """MACD 데이터"""
    macd_line: float
    signal_line: float
    histogram: float
    signal: str  # bullish, bearish, neutral


class BollingerBandData(BaseModel):
    """볼린저밴드 데이터"""
    top: float
    middle: float
    bottom: float


class FibonacciData(BaseModel):
    """피보나치 되돌림 데이터"""
    trend: str  # up, down, sideway
    levels: Dict[str, float]


class PeriodAnalysis(BaseModel):
    """기간별 분석 데이터"""
    rsi: float
    ma: MAData
    macd: MACDData
    bollinger_band: BollingerBandData
    fibonacci_retracement: FibonacciData


class AnalysisResponse(BaseModel):
    """분석 응답 모델"""
    ticker: str
    current_price: int
    analysis_time: str
    day: PeriodAnalysis
    week: PeriodAnalysis
    month: PeriodAnalysis


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str


class TechnicalAnalyzer:
    """기술적 분석 수행 클래스"""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # ticker -> (data, timestamp)
        self._auth_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._s3_client = None
        
        # S3 클라이언트 초기화
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            try:
                self._s3_client = boto3.client(
                    's3',
                    region_name=AWS_REGION,
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                )
                logger.info("S3 client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")
    
    async def _upload_to_s3(self, ticker: str, data: Dict) -> bool:
        """분석 결과를 S3에 업로드"""
        if not self._s3_client:
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            key = f"technical-analysis/{ticker}_{timestamp}.json"
            
            import json
            body = json.dumps(data, ensure_ascii=False, indent=2)
            
            self._s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=key,
                Body=body.encode('utf-8'),
                ContentType='application/json'
            )
            logger.info(f"Uploaded analysis to S3: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False
    
    async def _get_auth_token(self) -> str:
        """인증 토큰 조회"""
        # 캐시된 토큰이 유효한지 확인
        if self._auth_token and self._token_expires:
            if datetime.now() < self._token_expires - timedelta(minutes=5):
                return self._auth_token
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{AUTH_AGENT_URL}/result/auth-token")
                if response.status_code == 200:
                    data = response.json()
                    self._auth_token = data["token"]
                    self._token_expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00").replace("+00:00", ""))
                    return self._auth_token
                else:
                    raise HTTPException(status_code=503, detail="Failed to get auth token")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to auth agent: {e}")
            raise HTTPException(status_code=503, detail="Auth agent unavailable")
    
    async def _fetch_price_data(
        self, 
        ticker: str, 
        period_code: str,  # D: 일, W: 주, M: 월
        count: int = 100
    ) -> List[Dict[str, Any]]:
        """한국투자증권 API에서 시세 데이터 조회"""
        token = await self._get_auth_token()
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        url = f"{HANSEC_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": HANSEC_APP_KEY,
            "appsecret": HANSEC_APP_SECRET,
            "tr_id": "FHKST03010100",
            "custtype": "P"
        }
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": period_code,
            "FID_ORG_ADJ_PRC": "0"  # 수정주가
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("rt_cd") == "0":
                        output1 = data.get("output1", {})
                        output2 = data.get("output2", [])
                        
                        # 현재가 정보
                        current_price = int(output1.get("stck_prpr", 0))
                        
                        # 시세 데이터 변환
                        price_data = []
                        for item in output2[:count]:
                            price_data.append({
                                "date": item.get("stck_bsop_date", ""),
                                "close": int(item.get("stck_clpr", 0)),
                                "open": int(item.get("stck_oprc", 0)),
                                "high": int(item.get("stck_hgpr", 0)),
                                "low": int(item.get("stck_lwpr", 0)),
                                "volume": int(item.get("acml_vol", 0))
                            })
                        
                        return price_data, current_price, output1
                    else:
                        logger.error(f"API error: {data.get('msg1', 'Unknown error')}")
                        raise HTTPException(status_code=500, detail=f"API error: {data.get('msg1')}")
                else:
                    logger.error(f"HTTP error: {response.status_code}")
                    raise HTTPException(status_code=response.status_code, detail="Failed to fetch price data")
                    
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(status_code=503, detail="Failed to connect to Korea Investment API")
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    def _calculate_macd(
        self, 
        prices: List[float], 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> Dict[str, Any]:
        """MACD 계산"""
        if len(prices) < slow:
            return {"macd_line": 0, "signal_line": 0, "histogram": 0, "signal": "neutral"}
        
        prices_arr = np.array(prices, dtype=float)
        
        # EMA 계산
        def ema(data, period):
            alpha = 2 / (period + 1)
            ema_values = [data[0]]
            for i in range(1, len(data)):
                ema_values.append(alpha * data[i] + (1 - alpha) * ema_values[-1])
            return np.array(ema_values)
        
        ema_fast = ema(prices_arr, fast)
        ema_slow = ema(prices_arr, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        # 시그널 판단
        if histogram[-1] > 0 and histogram[-2] <= 0:
            sig = "bullish"
        elif histogram[-1] < 0 and histogram[-2] >= 0:
            sig = "bearish"
        elif histogram[-1] > 0:
            sig = "bullish"
        elif histogram[-1] < 0:
            sig = "bearish"
        else:
            sig = "neutral"
        
        return {
            "macd_line": round(float(macd_line[-1]), 2),
            "signal_line": round(float(signal_line[-1]), 2),
            "histogram": round(float(histogram[-1]), 2),
            "signal": sig
        }
    
    def _calculate_bollinger_bands(
        self, 
        prices: List[float], 
        period: int = 20, 
        std_dev: float = 2
    ) -> Dict[str, float]:
        """볼린저밴드 계산"""
        if len(prices) < period:
            return {"top": 0, "middle": 0, "bottom": 0}
        
        prices_arr = np.array(prices[-period:], dtype=float)
        middle = np.mean(prices_arr)
        std = np.std(prices_arr)
        
        return {
            "top": round(float(middle + std_dev * std), 0),
            "middle": round(float(middle), 0),
            "bottom": round(float(middle - std_dev * std), 0)
        }
    
    def _calculate_ma(self, prices: List[float], periods: List[int] = [5, 10, 20]) -> Dict[str, float]:
        """이동평균선 계산"""
        result = {}
        for period in periods:
            if len(prices) >= period:
                result[f"ma{period}"] = round(float(np.mean(prices[-period:])), 0)
            else:
                result[f"ma{period}"] = 0
        return result
    
    def _calculate_fibonacci(
        self, 
        highs: List[float], 
        lows: List[float]
    ) -> Dict[str, Any]:
        """피보나치 되돌림 계산"""
        if not highs or not lows:
            return {"trend": "sideway", "levels": {}}
        
        high = max(highs)
        low = min(lows)
        diff = high - low
        
        # 추세 판단
        recent_high_idx = highs.index(max(highs[-10:] if len(highs) >= 10 else highs))
        recent_low_idx = lows.index(min(lows[-10:] if len(lows) >= 10 else lows))
        
        if recent_high_idx > recent_low_idx:
            trend = "up"
        elif recent_high_idx < recent_low_idx:
            trend = "down"
        else:
            trend = "sideway"
        
        # 피보나치 레벨 계산
        levels = {
            "level_0": round(float(low), 0),
            "level_236": round(float(low + diff * 0.236), 0),
            "level_382": round(float(low + diff * 0.382), 0),
            "level_500": round(float(low + diff * 0.5), 0),
            "level_618": round(float(low + diff * 0.618), 0),
            "level_786": round(float(low + diff * 0.786), 0),
            "level_100": round(float(high), 0)
        }
        
        return {"trend": trend, "levels": levels}
    
    def _analyze_period(
        self, 
        price_data: List[Dict], 
        period_name: str
    ) -> Dict[str, Any]:
        """특정 기간의 기술적 분석 수행"""
        closes = [d["close"] for d in price_data if d["close"] > 0]
        highs = [d["high"] for d in price_data if d["high"] > 0]
        lows = [d["low"] for d in price_data if d["low"] > 0]
        
        if not closes:
            return self._get_empty_analysis()
        
        # 최신 데이터가 먼저 오므로 역순으로 변환
        closes = closes[::-1]
        highs = highs[::-1]
        lows = lows[::-1]
        
        return {
            "rsi": self._calculate_rsi(closes),
            "ma": self._calculate_ma(closes),
            "macd": self._calculate_macd(closes),
            "bollinger_band": self._calculate_bollinger_bands(closes),
            "fibonacci_retracement": self._calculate_fibonacci(highs, lows)
        }
    
    def _get_empty_analysis(self) -> Dict[str, Any]:
        """빈 분석 결과"""
        return {
            "rsi": 50.0,
            "ma": {"ma5": 0, "ma10": 0, "ma20": 0},
            "macd": {"macd_line": 0, "signal_line": 0, "histogram": 0, "signal": "neutral"},
            "bollinger_band": {"top": 0, "middle": 0, "bottom": 0},
            "fibonacci_retracement": {"trend": "sideway", "levels": {}}
        }
    
    async def analyze(self, ticker: str) -> Dict[str, Any]:
        """종목 기술적 분석 수행"""
        # 캐시 확인
        cache_key = ticker
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < CACHE_TTL_SECONDS:
                logger.info(f"Returning cached analysis for {ticker}")
                return cached_data
        
        logger.info(f"Starting technical analysis for {ticker}")
        
        # 일/주/월 데이터 병렬 조회
        try:
            daily_data, current_price, _ = await self._fetch_price_data(ticker, "D", 100)
            weekly_data, _, _ = await self._fetch_price_data(ticker, "W", 50)
            monthly_data, _, _ = await self._fetch_price_data(ticker, "M", 50)
        except Exception as e:
            logger.error(f"Failed to fetch data for {ticker}: {e}")
            raise
        
        # 기술적 분석 수행
        day_analysis = self._analyze_period(daily_data, "day")
        week_analysis = self._analyze_period(weekly_data, "week")
        month_analysis = self._analyze_period(monthly_data, "month")
        
        result = {
            "ticker": ticker,
            "current_price": current_price,
            "analysis_time": datetime.utcnow().isoformat() + "Z",
            "day": day_analysis,
            "week": week_analysis,
            "month": month_analysis
        }
        
        # 캐시 저장
        self._cache[cache_key] = (result, datetime.now())
        
        # S3에 업로드 (비동기)
        asyncio.create_task(self._upload_to_s3_async(ticker, result))
        
        logger.info(f"Technical analysis completed for {ticker}")
        return result
    
    async def _upload_to_s3_async(self, ticker: str, data: Dict):
        """비동기 S3 업로드 (실패해도 무시)"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._upload_to_s3(ticker, data)
            )
        except Exception as e:
            logger.warning(f"S3 upload failed for {ticker}: {e}")


# 전역 분석기
analyzer = TechnicalAnalyzer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    logger.info("Technical Agent starting...")
    yield
    logger.info("Technical Agent shutting down...")


app = FastAPI(
    title="Technical Analysis Agent",
    description="기술적 분석 에이전트 - RSI, MACD, 볼린저밴드, 피보나치 분석",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/result/analysis")
async def analyze_ticker(request: AnalysisRequest):
    """종목 기술적 분석 API"""
    ticker = request.ticker.strip()
    
    if not ticker or len(ticker) != 6:
        raise HTTPException(status_code=400, detail="Invalid ticker format. Must be 6 digits.")
    
    try:
        result = await analyzer.analyze(ticker)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/health/live", response_model=HealthResponse)
async def liveness_probe():
    """Liveness probe"""
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=HealthResponse)
async def readiness_probe():
    """Readiness probe"""
    # 인증 에이전트 연결 확인
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{AUTH_AGENT_URL}/health/live")
            if response.status_code != 200:
                raise HTTPException(status_code=503, detail="Auth agent not ready")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth agent unavailable")
    
    return HealthResponse(status="ok")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

