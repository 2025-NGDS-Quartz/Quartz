from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class CandidatesResponse(BaseModel):
    """후보 종목 응답 모델"""
    timestamp: str
    total_stocks: int
    statistics: Dict
    top_candidates: List[StockCandidate]

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

def get_latest_candidates_file() -> Optional[Path]:
    """최신 stock_candidates.json 파일 찾기"""
    candidates_file = Path("data/stock_candidates.json")
    
    if candidates_file.exists():
        return candidates_file
    
    return None

def load_candidates_data() -> Dict:
    """후보 종목 데이터 로드"""
    file_path = get_latest_candidates_file()
    
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Stock candidates file not found. Please run the pipeline first."
        )
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded candidates from {file_path}")
        return data
    
    except Exception as e:
        logger.error(f"Error loading candidates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error loading candidates: {str(e)}"
        )

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
    """헬스체크"""
    file_path = get_latest_candidates_file()
    last_update = None
    
    if file_path and file_path.exists():
        last_update = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        last_update=last_update
    )

@app.post("/api/candidates", response_model=CandidatesResponse, tags=["Stock Selection"])
async def get_stock_candidates(top_n: int = 20):
    """
    거래 후보 종목 리스트 반환
    
    - **top_n**: 반환할 상위 종목 개수 (기본: 20)
    
    Returns:
        최신 거래 후보 종목 리스트
    """
    logger.info(f"Received request for top {top_n} candidates")
    
    try:
        # 데이터 로드
        data = load_candidates_data()
        
        # top_n만큼만 반환
        top_candidates = data['top_candidates'][:top_n]
        
        response = CandidatesResponse(
            timestamp=data['timestamp'],
            total_stocks=data['total_stocks'],
            statistics=data['statistics'],
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
    print("🚀 Stock Selection Agent API Server")
    print("="*60)
    print("📍 Server: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)