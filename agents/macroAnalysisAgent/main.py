"""
거시경제 분석 에이전트 (Macro Analysis Agent)
- ECOS API: 한국 거시경제 데이터 (기준금리, 근원물가, 환율, 수출입, 가계대출)
- FRED API: 미국 거시경제 데이터 (연방기금금리, CPI)
- World Bank API: 글로벌 데이터 (GDP 성장률, 인플레이션)
- Gemini 3 Pro: 긍정/부정 보고서 생성 및 요약
- S3: 보고서 업로드
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

import httpx
import boto3
from botocore.exceptions import ClientError

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "agent": "macro-agent", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# 환경 변수
ECOS_API_KEY = os.getenv("ECOS_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "quartz-bucket")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# S3 폴더 경로
S3_FOLDER = "macro-analysis/"

# HTTP 요청 설정
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30.0


class S3Uploader:
    """S3 파일 업로더"""
    
    def __init__(self, region: str = "ap-northeast-2"):
        self.region = region
        self.client = None
        
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            try:
                self.client = boto3.client(
                    's3',
                    region_name=region,
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                )
                logger.info("S3 client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
        else:
            # 환경변수 없이 기본 자격 증명 사용 (EC2 IAM Role 등)
            try:
                self.client = boto3.client('s3', region_name=region)
                logger.info("S3 client initialized with default credentials")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
    
    def upload_file(self, bucket_name: str, key: str, content: str) -> bool:
        """S3에 파일 업로드"""
        if not self.client:
            logger.error("S3 client not initialized")
            return False
        
        try:
            self.client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType='text/markdown; charset=utf-8'
            )
            logger.info(f"[S3] Upload Success: {key}")
            return True
        except ClientError as e:
            logger.error(f"[S3] Upload Failed: {e}")
            return False


async def perform_request(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    post_data: Optional[str] = None,
    max_retries: int = MAX_RETRIES
) -> str:
    """HTTP 요청 수행 (GET/POST)"""
    
    for i in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=False) as client:
                if post_data:
                    response = await client.post(url, headers=headers, content=post_data)
                else:
                    response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f"[HTTP Error] Status Code: {response.status_code}")
                    logger.error(f"Response: {response.text[:500]}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Request failed (attempt {i+1}/{max_retries}): {e}")
            await asyncio.sleep(1)
    
    return ""


async def fetch_ecos_data(
    key: str,
    table: str,
    item: str,
    start: str,
    end: str
) -> List[Tuple[str, str]]:
    """
    ECOS API에서 한국 거시경제 데이터 수집
    
    Args:
        key: ECOS API 키
        table: 통계표 코드
        item: 통계항목 코드
        start: 시작 기간 (YYYYMM)
        end: 종료 기간 (YYYYMM)
    
    Returns:
        [(날짜, 값), ...] 형태의 리스트
    """
    url = f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/100/{table}/M/{start}/{end}/{item}"
    
    results: List[Tuple[str, str]] = []
    resp = await perform_request(url)
    
    if not resp:
        return results
    
    try:
        import json
        j = json.loads(resp)
        
        # ECOS 에러 체크
        if "RESULT" in j:
            logger.warning(f"ECOS API Error: {j.get('RESULT', {}).get('MESSAGE', 'Unknown error')}")
            return results
        
        if "StatisticSearch" in j and "row" in j["StatisticSearch"]:
            for row in j["StatisticSearch"]["row"]:
                date = row.get("TIME", "")
                val = row.get("DATA_VALUE", "")
                results.append((date, val))
                
    except Exception as e:
        logger.error(f"ECOS Parsing Error: {e}")
    
    # API 과부하 방지
    await asyncio.sleep(0.1)
    return results


async def fetch_fred_series(
    fred_key: str,
    series_id: str,
    start_date: str,
    end_date: str
) -> List[Tuple[str, str]]:
    """
    FRED API에서 미국 거시경제 데이터 수집
    
    Args:
        fred_key: FRED API 키
        series_id: 시리즈 ID (예: "FEDFUNDS", "CPIAUCSL")
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
    
    Returns:
        [(날짜, 값), ...] 형태의 리스트
    """
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}"
        f"&api_key={fred_key}"
        f"&file_type=json"
        f"&observation_start={start_date}"
        f"&observation_end={end_date}"
    )
    
    results: List[Tuple[str, str]] = []
    resp = await perform_request(url)
    
    if not resp:
        return results
    
    try:
        import json
        j = json.loads(resp)
        
        if "observations" in j and isinstance(j["observations"], list):
            for ob in j["observations"]:
                date = ob.get("date", "")
                value = ob.get("value", "")
                if date and value and value != ".":
                    results.append((date, value))
                    
    except Exception as e:
        logger.error(f"FRED Parsing Error: {e}")
    
    await asyncio.sleep(0.1)
    return results


async def fetch_world_bank_series(
    country: str,
    indicator: str,
    start_year: str,
    end_year: str
) -> List[Tuple[str, str]]:
    """
    World Bank API에서 글로벌 거시경제 데이터 수집
    
    Args:
        country: 국가 코드 (예: "WLD", "USA", "KOR")
        indicator: 지표 코드 (예: "NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG")
        start_year: 시작 연도 (YYYY)
        end_year: 종료 연도 (YYYY)
    
    Returns:
        [(연도, 값), ...] 형태의 리스트
    """
    url = (
        f"https://api.worldbank.org/v2/country/{country}"
        f"/indicator/{indicator}"
        f"?date={start_year}:{end_year}"
        f"&format=json&per_page=2000"
    )
    
    results: List[Tuple[str, str]] = []
    resp = await perform_request(url)
    
    if not resp:
        return results
    
    try:
        import json
        j = json.loads(resp)
        
        # 응답 구조: [meta, [{ "date": "2024", "value": 3.5, ... }, ...]]
        if len(j) >= 2 and isinstance(j[1], list):
            for row in j[1]:
                if row.get("value") is None:
                    continue
                
                year = row.get("date", "")
                if not year:
                    continue
                
                value = row.get("value")
                if isinstance(value, (int, float)):
                    value = str(value)
                
                results.append((year, value))
                
    except Exception as e:
        logger.error(f"World Bank Parsing Error: {e}")
    
    await asyncio.sleep(0.1)
    return results


async def generate_gemini_report(
    csv_data: str,
    report_type: str,
    api_key: str
) -> str:
    """
    Gemini를 사용하여 거시경제 보고서 생성
    
    Args:
        csv_data: CSV 형식의 데이터
        report_type: "positive" 또는 "negative"
        api_key: Gemini API 키
    
    Returns:
        생성된 보고서 (마크다운)
    """
    # Gemini 모델 (C++ 버전과 동일)
    gemini_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3-pro-preview:generateContent"
    )
    
    if report_type == "positive":
        role_instruction = (
            "You are an optimistic macroeconomist. "
            "Focus on growth opportunities, resilience, and soft-landing scenarios."
        )
    else:
        role_instruction = (
            "You are a risk-focused macro strategist. "
            "Focus on inflation risks, debt overhang, external vulnerability, "
            "and hard-landing scenarios."
        )
    
    prompt_text = (
        f"{role_instruction} "
        "Use ONLY data trends provided below plus grounded information from Google Search. "
        "Combine Korean macro data (ECOS), US macro data (FRED), and global indicators (World Bank). "
        "Write a professional markdown report in Korean, including:\n"
        "- 개요 (현재 세계/한국 거시환경 요약)\n"
        "- 한국(금리, 물가, 환율, 수출입, 가계부채)에 대한 평가\n"
        "- 미국 및 주요국(금리, 물가, 성장)에 대한 평가\n"
        "- 시나리오별(낙관/기준/비관) 시장 영향과 자산별(주식, 채권, 환율) 함의\n"
        "- 포트폴리오 관점에서의 시사점\n\n"
        f"[DATA]\n{csv_data}"
    )
    
    import json
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "thinkingConfig": {"thinkingLevel": "low"}
        },
        "tools": [
            {"google_search": {}}
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    resp = await perform_request(gemini_url, headers, json.dumps(payload))
    
    try:
        j = json.loads(resp)
        if "candidates" in j and len(j["candidates"]) > 0:
            c0 = j["candidates"][0]
            if "content" in c0 and "parts" in c0["content"]:
                parts = c0["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"]
    except Exception as e:
        logger.error(f"Gemini Parsing Error: {e}")
    
    return ""


async def summarize_report(
    full_report: str,
    report_type: str,
    api_key: str
) -> str:
    """
    Gemini를 사용하여 보고서 요약 생성 (10문장 이내)
    
    Args:
        full_report: 전체 보고서
        report_type: "positive" 또는 "negative"
        api_key: Gemini API 키
    
    Returns:
        요약된 보고서
    """
    # Gemini 모델 (C++ 버전과 동일)
    gemini_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3-pro-preview:generateContent"
    )
    
    if report_type == "positive":
        prompt_text = (
            "다음의 거시경제 긍정 보고서를 한국어로 10문장이내로 요약해줘. "
            "핵심 성장 모멘텀, 정책 여력, 리스크 완화 요인에 집중해. "
            f"추가 설명 없이 요약문만 출력해.\n\n[Report]\n{full_report}"
        )
    else:
        prompt_text = (
            "다음의 거시경제 리스크 보고서를 한국어로 10문장이내로 요약해줘. "
            "핵심 리스크, 취약 구간, 꼬리위험(tail risk)에 집중해. "
            f"추가 설명 없이 요약문만 출력해.\n\n[Report]\n{full_report}"
        )
    
    import json
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "thinkingConfig": {"thinkingLevel": "low"}
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    resp = await perform_request(gemini_url, headers, json.dumps(payload))
    
    try:
        j = json.loads(resp)
        if "candidates" in j and len(j["candidates"]) > 0:
            c0 = j["candidates"][0]
            if "content" in c0 and "parts" in c0["content"]:
                parts = c0["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"]
    except Exception as e:
        logger.error(f"Gemini Summarize Parsing Error: {e}")
    
    return ""


def get_current_timestamp() -> str:
    """현재 타임스탬프 반환 (YYYYMMDD_HHMMSS)"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


async def run_analysis() -> Dict[str, Any]:
    """
    거시경제 분석 실행
    
    Returns:
        분석 결과 딕셔너리 (성공 여부, 업로드된 파일 목록 등)
    """
    result = {
        "success": False,
        "uploaded_files": [],
        "errors": [],
        "timestamp": get_current_timestamp()
    }
    
    # 환경 변수 체크
    if not ECOS_API_KEY:
        error_msg = "환경 변수 ECOS_API_KEY가 설정되지 않았습니다."
        logger.error(f"[Error] {error_msg}")
        result["errors"].append(error_msg)
        return result
    
    if not GEMINI_API_KEY:
        error_msg = "환경 변수 GEMINI_API_KEY가 설정되지 않았습니다."
        logger.error(f"[Error] {error_msg}")
        result["errors"].append(error_msg)
        return result
    
    if not FRED_API_KEY:
        logger.warning("[Warning] FRED_API_KEY가 설정되지 않아 미국 지표는 생략됩니다.")
    
    # 기간 설정
    start_date = "202301"  # ECOS 월별
    end_date = "202512"
    
    # FRED: 월별 관측 커버용
    fred_start = "2023-01-01"
    fred_end = "2025-12-31"
    
    # World Bank: 연도
    wb_start_year = "2023"
    wb_end_year = "2025"
    
    logger.info("=== Fetching Macroeconomic Data (ECOS / FRED / World Bank) ===")
    
    # (1) 한국 ECOS 5개 지표
    rates = await fetch_ecos_data(ECOS_API_KEY, "722Y001", "0101000", start_date, end_date)
    logger.info(f"1. 기준금리: {len(rates)} months fetched.")
    
    cpis = await fetch_ecos_data(ECOS_API_KEY, "901Y010", "DB", start_date, end_date)
    logger.info(f"2. 근원물가: {len(cpis)} months fetched.")
    
    exchange = await fetch_ecos_data(ECOS_API_KEY, "731Y004", "0000001/0000100", start_date, end_date)
    logger.info(f"3. 원-달러 환율: {len(exchange)} months fetched.")
    
    exports = await fetch_ecos_data(ECOS_API_KEY, "901Y118", "T002", start_date, end_date)
    imports = await fetch_ecos_data(ECOS_API_KEY, "901Y118", "T004", start_date, end_date)
    logger.info(f"4. 수출입 총괄: {len(exports)} months fetched.")
    
    loans = await fetch_ecos_data(ECOS_API_KEY, "151Y005", "11110A0", start_date, end_date)
    logger.info(f"5. 가계대출: {len(loans)} months fetched.")
    
    min_len = min(
        len(rates), len(cpis), len(exchange),
        len(exports), len(imports), len(loans)
    )
    
    if min_len == 0:
        error_msg = "한국 ECOS 데이터를 가져오는데 실패했습니다. 키나 인터넷 연결을 확인하세요."
        logger.error(f"[Error] {error_msg}")
        result["errors"].append(error_msg)
        return result
    
    # (2) 미국 FRED (선택적)
    fedfunds: List[Tuple[str, str]] = []
    us_cpi: List[Tuple[str, str]] = []
    
    if FRED_API_KEY:
        fedfunds = await fetch_fred_series(FRED_API_KEY, "FEDFUNDS", fred_start, fred_end)
        us_cpi = await fetch_fred_series(FRED_API_KEY, "CPIAUCSL", fred_start, fred_end)
        logger.info(f"6. 미국 기준금리(FEDFUNDS): {len(fedfunds)} obs fetched.")
        logger.info(f"7. 미국 CPI(CPIAUCSL): {len(us_cpi)} obs fetched.")
    
    # (3) World Bank 글로벌/미국 연간 지표
    wld_gdp = await fetch_world_bank_series("WLD", "NY.GDP.MKTP.KD.ZG", wb_start_year, wb_end_year)
    wld_cpi = await fetch_world_bank_series("WLD", "FP.CPI.TOTL.ZG", wb_start_year, wb_end_year)
    usa_gdp = await fetch_world_bank_series("USA", "NY.GDP.MKTP.KD.ZG", wb_start_year, wb_end_year)
    usa_cpi = await fetch_world_bank_series("USA", "FP.CPI.TOTL.ZG", wb_start_year, wb_end_year)
    
    logger.info(f"8. World GDP 성장률: {len(wld_gdp)} yrs fetched.")
    logger.info(f"9. World CPI 인플레: {len(wld_cpi)} yrs fetched.")
    logger.info(f"10. USA GDP 성장률: {len(usa_gdp)} yrs fetched.")
    logger.info(f"11. USA CPI 인플레: {len(usa_cpi)} yrs fetched.")
    
    # ===== CSV 프롬프트 구성 =====
    csv_data = ""
    
    # 한국 월별 데이터
    csv_data += "### Korea monthly macro (ECOS)\n"
    csv_data += "Date, BaseRate(%), CoreCPI(2020=100), USD/KRW(Avg), Export(Mil$), Import(Mil$), MortgageLoan(Bil KRW)\n"
    
    for i in range(min_len):
        csv_data += f"{rates[i][0]}, {rates[i][1]}, {cpis[i][1]}, {exchange[i][1]}, {exports[i][1]}, {imports[i][1]}, {loans[i][1]}\n"
    
    # 미국 월별 데이터 (FRED) - 존재할 때만 추가
    if fedfunds and us_cpi:
        csv_data += "\n\n### US monthly macro (FRED)\n"
        csv_data += "Date, FedFundsRate(%), US_CPI_Index\n"
        
        fred_len = min(len(fedfunds), len(us_cpi))
        for i in range(fred_len):
            csv_data += f"{fedfunds[i][0]}, {fedfunds[i][1]}, {us_cpi[i][1]}\n"
    
    # World & US 연간 데이터 (World Bank)
    csv_data += "\n\n### World & US annual macro (World Bank)\n"
    csv_data += "Year, WLD_GDP_Growth(%), WLD_Inflation(%), USA_GDP_Growth(%), USA_Inflation(%)\n"
    
    wb_len = min(len(wld_gdp), len(wld_cpi), len(usa_gdp), len(usa_cpi))
    for i in range(wb_len):
        csv_data += f"{wld_gdp[i][0]}, {wld_gdp[i][1]}, {wld_cpi[i][1]}, {usa_gdp[i][1]}, {usa_cpi[i][1]}\n"
    
    # ===== Gemini 호출 및 S3 업로드 =====
    logger.info("\n=== Sending Data to Gemini (Grounded) ===")
    
    uploader = S3Uploader(AWS_REGION)
    timestamp = result["timestamp"]
    
    logger.info(f"   Timestamp: {timestamp}")
    
    # 긍정 보고서
    logger.info("   - Generating Positive Report...")
    pos_report = await generate_gemini_report(csv_data, "positive", GEMINI_API_KEY)
    
    if pos_report:
        fname = f"{S3_FOLDER}Report_Positive_{timestamp}.md"
        if uploader.upload_file(S3_BUCKET_NAME, fname, pos_report):
            logger.info(f"   [Success] Uploaded: {fname}")
            result["uploaded_files"].append(fname)
        
        logger.info("   - Generating Positive Summary...")
        pos_summary = await summarize_report(pos_report, "positive", GEMINI_API_KEY)
        
        if pos_summary:
            fname_short = f"{S3_FOLDER}Report_Positive_{timestamp}_short.md"
            if uploader.upload_file(S3_BUCKET_NAME, fname_short, pos_summary):
                logger.info(f"   [Success] Uploaded: {fname_short}")
                result["uploaded_files"].append(fname_short)
    
    # 부정 보고서
    logger.info("   - Generating Negative Report...")
    neg_report = await generate_gemini_report(csv_data, "negative", GEMINI_API_KEY)
    
    if neg_report:
        fname = f"{S3_FOLDER}Report_Negative_{timestamp}.md"
        if uploader.upload_file(S3_BUCKET_NAME, fname, neg_report):
            logger.info(f"   [Success] Uploaded: {fname}")
            result["uploaded_files"].append(fname)
        
        logger.info("   - Generating Negative Summary...")
        neg_summary = await summarize_report(neg_report, "negative", GEMINI_API_KEY)
        
        if neg_summary:
            fname_short = f"{S3_FOLDER}Report_Negative_{timestamp}_short.md"
            if uploader.upload_file(S3_BUCKET_NAME, fname_short, neg_summary):
                logger.info(f"   [Success] Uploaded: {fname_short}")
                result["uploaded_files"].append(fname_short)
    
    result["success"] = len(result["uploaded_files"]) > 0
    return result


if __name__ == "__main__":
    print("프로그램 시작")
    asyncio.run(run_analysis())
    print("프로그램 종료")

