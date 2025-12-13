import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "agent": "ticker-selector", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# AWS S3 설정
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "quartz-bucket")
S3_CANDIDATES_KEY = "select-ticker/stock_candidates.json"

# S3 클라이언트 (지연 초기화)
_s3_client = None

def get_s3_client():
    """S3 클라이언트 반환 (싱글톤)"""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3', region_name=AWS_REGION)
    return _s3_client

app = FastAPI(
    title="Stock Selection Agent API",
    description="거래 종목 선택 에이전트 API",
    version="1.0.0"
)

# ==================== 데이터 모델 ====================

class StockCandidate(BaseModel):
    """종목 후보 모델"""
    ticker: str
    name: str
    sector: str
    avg_sentiment: float
    news_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    priority: str
    reasoning: str
    top_headlines: List[str]
    final_score: Optional[float] = None
    market_cap_tier: Optional[str] = None  # 시총 등급 (LARGE/MID/SMALL)

class CandidatesResponse(BaseModel):
    """후보 종목 응답 모델"""
    timestamp: str
    total_stocks: int
    statistics: Dict
    top_candidates: List[StockCandidate]

class CandidatesRequest(BaseModel):
    """후보 종목 요청 모델"""
    top_n: int = 5


class MacroReportRequest(BaseModel):
    """거시경제 보고서 요청 모델 (향후 확장)"""
    report_content: str
    timestamp: str

class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    timestamp: str
    last_update: Optional[str] = None

# ==================== 유틸리티 함수 ====================

def load_candidates_from_s3() -> Optional[Dict]:
    """S3에서 후보 종목 데이터 로드"""
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=S3_CANDIDATES_KEY)
        content = response['Body'].read().decode('utf-8')
        data = json.loads(content)
        logger.info(f"Loaded candidates from S3: s3://{S3_BUCKET_NAME}/{S3_CANDIDATES_KEY}")
        return data
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"S3 key not found: {S3_CANDIDATES_KEY}")
            return None
        logger.error(f"S3 load error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading from S3: {e}")
        return None


def load_candidates_from_local() -> Optional[Dict]:
    """로컬 파일에서 후보 종목 데이터 로드 (폴백용)"""
    candidates_file = Path("data/stock_candidates.json")
    
    if not candidates_file.exists():
        return None
    
    try:
        with open(candidates_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded candidates from local: {candidates_file}")
        return data
    except Exception as e:
        logger.error(f"Error loading from local: {e}")
        return None


def load_candidates_data(raise_on_missing: bool = True) -> Optional[Dict]:
    """후보 종목 데이터 로드 (S3 우선, 로컬 폴백)"""
    # 1. S3에서 먼저 시도
    data = load_candidates_from_s3()
    
    # 2. S3 실패 시 로컬 폴백
    if data is None:
        logger.info("Falling back to local file...")
        data = load_candidates_from_local()
    
    # 3. 둘 다 실패
    if data is None:
        if raise_on_missing:
            raise HTTPException(
                status_code=404,
                detail="Stock candidates not found. Please run the pipeline first."
            )
        return None
    
    return data


def get_empty_candidates_response() -> Dict:
    """빈 후보 종목 응답"""
    return {
        "timestamp": datetime.now().isoformat(),
        "total_stocks": 0,
        "statistics": {
            "high_priority": 0,
            "mid_priority": 0,
            "low_priority": 0
        },
        "top_candidates": []
    }


def check_data_available() -> bool:
    """데이터 가용성 확인 (S3 또는 로컬)"""
    # S3 확인
    try:
        s3_client = get_s3_client()
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=S3_CANDIDATES_KEY)
        return True
    except:
        pass
    
    # 로컬 확인
    return Path("data/stock_candidates.json").exists()

# ==================== API 엔드포인트 ====================

@app.get("/", tags=["Root"])
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Stock Selection Agent API",
        "version": "1.0.0",
        "endpoints": {
            "candidates": "/api/candidates",
            "health": "/health",
            "statistics": "/api/statistics",
            "docs": "/docs"
        }
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """헬스체크 (레거시)"""
    data_available = check_data_available()
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        last_update=None
    )


@app.get("/health/live", tags=["Health"])
async def liveness_probe():
    """Kubernetes Liveness Probe"""
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
async def readiness_probe():
    """Kubernetes Readiness Probe - 데이터 가용성 확인 (S3 또는 로컬)"""
    data_available = check_data_available()
    
    # 후보 파일이 없어도 서비스는 준비됨 (파이프라인이 실행되면 생성됨)
    return {
        "status": "ok",
        "data_available": data_available,
        "storage": "s3" if data_available else "none"
    }

@app.post("/api/candidates", response_model=CandidatesResponse, tags=["Stock Selection"])
async def get_stock_candidates(request: CandidatesRequest = CandidatesRequest()):
    """
    거래 후보 종목 리스트 반환 (중요도 기반)
    
    Request Body:
    - **top_n**: 반환할 상위 종목 개수 (기본: 5, 최대: 10)
    
    중요도 점수 기준:
    - 시총 등급 (LARGE/MID/SMALL): 25%
    - 감성 분석 점수: 40%
    - 뉴스 언급 횟수: 25%
    - 우선순위: 10%
    
    Returns:
        최신 거래 후보 종목 리스트 (중요도 순)
        데이터가 없으면 빈 리스트 반환
    """
    # 최대 10개로 제한
    top_n = min(request.top_n, 10)
    logger.info(f"Received request for top {top_n} candidates (importance-based)")
    
    try:
        # 데이터 로드 (없으면 None 반환)
        data = load_candidates_data(raise_on_missing=False)
        
        # 데이터가 없으면 빈 응답 반환
        if data is None:
            logger.warning("No candidates data available, returning empty response")
            empty_response = get_empty_candidates_response()
            return CandidatesResponse(**empty_response)
        
        # top_n만큼만 반환
        top_candidates = data.get('top_candidates', [])[:top_n]
        
        response = CandidatesResponse(
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            total_stocks=data.get('total_stocks', 0),
            statistics=data.get('statistics', {"high_priority": 0, "mid_priority": 0, "low_priority": 0}),
            top_candidates=top_candidates
        )
        
        logger.info(f"Returning {len(top_candidates)} candidates")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/statistics", tags=["Statistics"])
async def get_statistics():
    """
    전체 통계 정보 반환
    """
    try:
        data = load_candidates_data()
        
        return {
            "timestamp": data['timestamp'],
            "total_stocks": data['total_stocks'],
            "statistics": data['statistics'],
            "candidate_count": len(data['top_candidates'])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/candidates/{ticker}", tags=["Stock Selection"])
async def get_stock_by_ticker(ticker: str):
    """
    특정 종목의 상세 정보 반환
    
    - **ticker**: 종목 코드 (예: 005930)
    """
    try:
        data = load_candidates_data()
        
        # all_stocks에서 찾기
        all_stocks = data.get('all_stocks', {})
        
        if ticker not in all_stocks:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {ticker} not found"
            )
        
        return all_stocks[ticker]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/macro-report", tags=["Macro Economy"])
async def receive_macro_report(report: MacroReportRequest):
    """
    거시경제 보고서 수신 (향후 확장용)
    
    현재는 단순히 수신만 하고 로그에 기록
    """
    logger.info(f"Received macro report at {report.timestamp}")
    logger.info(f"Report content length: {len(report.report_content)} chars")
    
    # 향후: 거시경제 정보를 바탕으로 종목 선택 로직 개선
    
    return {
        "status": "received",
        "message": "Macro report received successfully",
        "timestamp": datetime.now().isoformat()
    }

# ==================== 시작 ====================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("Stock Selection Agent API Server")
    print("="*60)
    print("Server: http://localhost:8002")
    print("Docs: http://localhost:8002/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8002)