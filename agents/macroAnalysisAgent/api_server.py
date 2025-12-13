"""
거시경제 분석 에이전트 API 서버
C++ 분석 프로그램의 결과를 S3에서 조회하여 제공
"""
import os
import logging
import subprocess
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "agent": "macro-agent", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Macro Analysis Agent API",
    description="거시경제 분석 에이전트 API - C++ 분석 결과를 S3에서 조회하여 제공",
    version="1.0.0"
)

# 환경 변수
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "quartz-bucket")

# S3 클라이언트
s3_client = boto3.client('s3', region_name=AWS_REGION)

# 분석 결과 캐시
_cache: Dict[str, Any] = {
    "positive_summary": None,
    "negative_summary": None,
    "market_bias_hint": "uncertain",
    "last_update": None
}


class MacroAnalysisResponse(BaseModel):
    """거시경제 분석 응답"""
    positive_summary: str
    negative_summary: str
    market_bias_hint: str
    last_update: Optional[str] = None


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    timestamp: str
    last_update: Optional[str] = None


def get_latest_report_key(prefix: str) -> Optional[str]:
    """S3에서 가장 최신 보고서 키 조회"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=100
        )
        
        if 'Contents' not in response:
            return None
        
        # 파일명으로 정렬 (타임스탬프가 포함되어 있으므로)
        files = sorted(
            [obj['Key'] for obj in response['Contents']],
            reverse=True
        )
        
        # _short 파일 찾기
        for f in files:
            if '_short.md' in f:
                return f
        
        return None
    except Exception as e:
        logger.error(f"Error listing S3 objects: {e}")
        return None


def read_s3_file(key: str) -> Optional[str]:
    """S3에서 파일 읽기"""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        content = response['Body'].read().decode('utf-8')
        return content
    except Exception as e:
        logger.error(f"Error reading S3 file {key}: {e}")
        return None


def determine_market_bias(positive: str, negative: str) -> str:
    """
    긍정/부정 요약을 기반으로 시장 편향 판단
    간단한 키워드 기반 분석
    """
    positive_keywords = ["성장", "회복", "상승", "개선", "완화", "호조", "확대", "증가"]
    negative_keywords = ["위험", "하락", "침체", "악화", "긴축", "부담", "위축", "감소"]
    
    pos_count = sum(1 for kw in positive_keywords if kw in positive)
    neg_count = sum(1 for kw in negative_keywords if kw in negative)
    
    # 비율 기반 판단
    total = pos_count + neg_count
    if total == 0:
        return "uncertain"
    
    pos_ratio = pos_count / total
    
    if pos_ratio > 0.6:
        return "bullish"
    elif pos_ratio < 0.4:
        return "bearish"
    else:
        return "neutral"


async def refresh_cache():
    """S3에서 최신 보고서를 읽어 캐시 갱신"""
    global _cache
    
    try:
        # 긍정 보고서 조회
        pos_key = get_latest_report_key("Report_Positive_")
        if pos_key:
            pos_content = read_s3_file(pos_key)
            if pos_content:
                _cache["positive_summary"] = pos_content
        
        # 부정 보고서 조회
        neg_key = get_latest_report_key("Report_Negative_")
        if neg_key:
            neg_content = read_s3_file(neg_key)
            if neg_content:
                _cache["negative_summary"] = neg_content
        
        # 시장 편향 결정
        if _cache["positive_summary"] and _cache["negative_summary"]:
            _cache["market_bias_hint"] = determine_market_bias(
                _cache["positive_summary"],
                _cache["negative_summary"]
            )
        
        _cache["last_update"] = datetime.utcnow().isoformat() + "Z"
        logger.info("Cache refreshed successfully")
        
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")


async def run_cpp_analysis():
    """C++ 분석 프로그램 실행"""
    try:
        logger.info("Starting C++ macro analysis...")
        
        # C++ 실행 파일 경로
        executable = "/app/macro_analysis"
        
        if not os.path.exists(executable):
            logger.warning(f"C++ executable not found at {executable}")
            return
        
        # 프로세스 실행
        process = await asyncio.create_subprocess_exec(
            executable,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # stdout 출력 (C++ 프로그램의 진행 상황)
        if stdout:
            stdout_text = stdout.decode('utf-8', errors='replace')
            for line in stdout_text.strip().split('\n'):
                if line.strip():
                    logger.info(f"[C++] {line}")
        
        # stderr 출력 (에러 메시지)
        if stderr:
            stderr_text = stderr.decode('utf-8', errors='replace')
            for line in stderr_text.strip().split('\n'):
                if line.strip():
                    logger.error(f"[C++ ERROR] {line}")
        
        if process.returncode == 0:
            logger.info("C++ macro analysis completed successfully")
        else:
            logger.error(f"C++ macro analysis failed with return code: {process.returncode}")
            
    except Exception as e:
        logger.error(f"Error running C++ analysis: {e}")


async def analysis_scheduler():
    """12시간마다 C++ 분석 실행 및 캐시 갱신"""
    while True:
        try:
            # C++ 분석 실행
            await run_cpp_analysis()
            
            # 잠시 대기 후 캐시 갱신 (S3 업로드 완료 대기)
            await asyncio.sleep(30)
            
            # 캐시 갱신
            await refresh_cache()
            
        except Exception as e:
            logger.error(f"Error in analysis scheduler: {e}")
        
        # 12시간 대기 (43200초)
        await asyncio.sleep(43200)


@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    logger.info("Macro Analysis Agent starting...")
    
    # 초기 캐시 로드
    await refresh_cache()
    
    # 백그라운드 스케줄러 시작
    asyncio.create_task(analysis_scheduler())
    
    logger.info("Macro Analysis Agent started")


@app.get("/health/live", tags=["Health"])
async def liveness_probe():
    """Kubernetes Liveness Probe"""
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
async def readiness_probe():
    """Kubernetes Readiness Probe"""
    # 캐시에 데이터가 있으면 준비 완료
    has_data = _cache["positive_summary"] is not None or _cache["negative_summary"] is not None
    
    return {
        "status": "ok",
        "data_available": has_data,
        "last_update": _cache["last_update"]
    }


@app.get("/result/analysis", response_model=MacroAnalysisResponse, tags=["Analysis"])
async def get_analysis():
    """
    거시경제 분석 결과 반환
    
    S3에 저장된 최신 보고서 요약(_short 버전)을 반환합니다.
    
    Returns:
        - positive_summary: 긍정적 관점의 요약 (10문장 이내)
        - negative_summary: 부정적 관점의 요약 (10문장 이내)
        - market_bias_hint: 시장 편향 (bullish/bearish/neutral/uncertain)
    """
    # 캐시가 비어있으면 갱신 시도
    if _cache["positive_summary"] is None and _cache["negative_summary"] is None:
        await refresh_cache()
    
    return MacroAnalysisResponse(
        positive_summary=_cache["positive_summary"] or "거시경제 긍정 보고서를 아직 사용할 수 없습니다.",
        negative_summary=_cache["negative_summary"] or "거시경제 부정 보고서를 아직 사용할 수 없습니다.",
        market_bias_hint=_cache["market_bias_hint"],
        last_update=_cache["last_update"]
    )


@app.post("/refresh", tags=["Admin"])
async def manual_refresh():
    """캐시 수동 갱신"""
    await refresh_cache()
    return {"status": "refreshed", "timestamp": datetime.utcnow().isoformat()}


@app.post("/run-analysis", tags=["Admin"])
async def trigger_analysis():
    """C++ 분석 수동 실행"""
    asyncio.create_task(run_cpp_analysis())
    return {"status": "started", "message": "Analysis job started in background"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

