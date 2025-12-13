"""
포트폴리오 관리 에이전트 (Portfolio Manager Agent)
- 다른 에이전트들과 통신하여 매매 결정
- GPT를 통한 투자 의사결정
- WebSocket으로 거래 에이전트에 주문 전달
- 포트: 8004
"""
import os
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from uuid import uuid4
import math

import httpx
import boto3
from botocore.exceptions import ClientError
from openai import AsyncOpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import websockets

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "agent": "portfolio-manager", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# 환경변수
HANSEC_APP_KEY = os.getenv("HANSEC_INVESTMENT_APP_KEY", "")
HANSEC_APP_SECRET = os.getenv("HANSEC_INVESTMENT_APP_SECRET_KEY", "")
HANSEC_CANO = os.getenv("HANSEC_INVESTMENT_CANO", "")
HANSEC_ACNT_PRDT_CD = os.getenv("HANSEC_INVESTMENT_ACNT_PRDT_CD", "01")
HANSEC_BASE_URL = "https://openapi.koreainvestment.com:9443"
GPT_API_KEY = os.getenv("GPT_API_KEY", "")

# 에이전트 URL
AUTH_AGENT_URL = os.getenv("AUTH_AGENT_URL", "http://auth-agent:8006")
MACRO_AGENT_URL = os.getenv("MACRO_AGENT_URL", "http://macro-agent:8001")
TICKER_SELECTOR_URL = os.getenv("TICKER_SELECTOR_URL", "http://ticker-selector:8002")
TECHNICAL_AGENT_URL = os.getenv("TECHNICAL_AGENT_URL", "http://technical-agent:8003")
TRADING_AGENT_WS_URL = os.getenv("TRADING_AGENT_WS_URL", "ws://trading-agent:8005/ws/orders")

# AWS S3 설정
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "quartz-bucket")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# 제약조건
MIN_ORDER_KRW = int(os.getenv("MIN_ORDER_KRW", "100000"))
MAX_SINGLE_TICKER_WEIGHT = float(os.getenv("MAX_SINGLE_TICKER_WEIGHT", "0.2"))
MAX_TURNOVER_RATIO = float(os.getenv("MAX_TURNOVER_RATIO", "0.3"))
MAX_BUY_CANDIDATES = int(os.getenv("MAX_BUY_CANDIDATES", "3"))
MAX_SELL_CANDIDATES = int(os.getenv("MAX_SELL_CANDIDATES", "3"))

# 손절/익절 기준
STOP_LOSS_RATE = -0.05  # -5%
TAKE_PROFIT_RATE = 0.15  # +15%

# TR_ID
TR_ID_BALANCE = "TTTC8434R"
TR_ID_PSBL_ORDER = "TTTC8908R"
TR_ID_PSBL_SELL = "TTTC8408R"
TR_ID_CCNL = "FHKST01010300"  # 주식현재가 체결

# 거래량 기준 (전일 대비 150% 이상이면 "많음")
VOLUME_HIGH_THRESHOLD = 1.5


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str


class PortfolioStatus(BaseModel):
    """포트폴리오 상태 모델"""
    cash_krw: int
    total_value: int
    positions: List[Dict[str, Any]]
    last_updated: str


# GPT 프롬프트 (architecture.md에서 정의된 프롬프트)
GPT_SYSTEM_PROMPT = """# Role

You are the **Portfolio Management Agent** for an automated trading system in the Korean stock market.

Your job is to:
- Integrate macro view, technical analysis, and fundamental analysis,
- Consider the current portfolio (positions + cash),
- Decide for each ticker whether to **BUY**, **SELL**, or **HOLD**,
- Provide only a compact JSON output that can be parsed by the system.

You must **not** generate any natural language explanation outside the JSON.
All outputs must be in **valid JSON only**.

---

# Output format (JSON only)

Return a single JSON object with this exact structure and nothing else:

```json
{
  "meta": {
    "decision_time_utc": "YYYY-MM-DDTHH:MM:SSZ",
    "overall_comment": "max 2 sentences summarizing overall strategy"
  },
  "global_view": {
    "macro_bias": "bullish | bearish | neutral | uncertain",
    "risk_action": "increase_exposure | keep_exposure | reduce_exposure",
    "target_cash_ratio": 0.0
  },
  "ticker_decisions": [
    {
      "ticker": "005930",
      "action": "BUY | SELL | HOLD",
      "target_weight": 0.15,
      "priority": 1,
      "strength": 0.0,
      "reason": "max 2 sentences; do not restate all input data."
    }
  ]
}
```

# Decision rules & risk management

Apply these principles:

1. **Capital preservation first**: In bearish/uncertain macro, reduce positions and increase cash.
2. **Signal alignment**: Strong BUY needs 2+ positive signals (macro, technical, fundamental). Strong SELL needs bearish technical + weak fundamental.
3. **Concentration control**: Respect target_max_single_ticker_weight constraint.
4. **Turnover control**: Keep number of trades small.
5. **Safe defaults**: If input is incomplete or inconsistent, prefer HOLD and higher cash ratio.

Output must be **valid JSON**. Do **not** include any text outside the JSON.
"""


class PortfolioManager:
    """포트폴리오 관리 클래스"""
    
    def __init__(self):
        self._auth_token: Optional[str] = None
        self._portfolio_cache: Optional[Dict] = None
        self._portfolio_cache_time: Optional[datetime] = None
        self._ws_connection: Optional[websockets.WebSocketClientProtocol] = None
        self._decision_task: Optional[asyncio.Task] = None
        self._rebalance_task: Optional[asyncio.Task] = None
        self._openai_client = AsyncOpenAI(api_key=GPT_API_KEY) if GPT_API_KEY else None
        self._s3_client = None
        self._high_volume_mode = False  # 거래량 높음 모드
        
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
    
    async def initialize(self):
        """초기화"""
        logger.info("Initializing Portfolio Manager...")
        # 스케줄러 태스크 시작
        self._decision_task = asyncio.create_task(self._decision_loop())
        self._rebalance_task = asyncio.create_task(self._rebalance_loop())
    
    async def shutdown(self):
        """종료 처리"""
        if self._decision_task:
            self._decision_task.cancel()
        if self._rebalance_task:
            self._rebalance_task.cancel()
        if self._ws_connection:
            await self._ws_connection.close()
    
    async def _get_auth_token(self) -> str:
        """인증 토큰 조회"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{AUTH_AGENT_URL}/result/auth-token")
                if response.status_code == 200:
                    data = response.json()
                    self._auth_token = data["token"]
                    return self._auth_token
                else:
                    raise Exception("Failed to get auth token")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to auth agent: {e}")
            raise
    
    def _get_headers(self, tr_id: str) -> Dict[str, str]:
        """API 요청 헤더"""
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._auth_token}",
            "appkey": HANSEC_APP_KEY,
            "appsecret": HANSEC_APP_SECRET,
            "tr_id": tr_id,
            "custtype": "P"
        }
    
    async def get_portfolio(self) -> Dict[str, Any]:
        """포트폴리오 현황 조회"""
        await self._get_auth_token()
        
        # 주식잔고조회
        url = f"{HANSEC_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"
        params = {
            "CANO": HANSEC_CANO,
            "ACNT_PRDT_CD": HANSEC_ACNT_PRDT_CD,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",  # 오프라인여부 (공란: 기본값)
            "INQR_DVSN": "02",  # 종목별
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",  # 전일매매포함
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        
        headers = self._get_headers(TR_ID_BALANCE)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                data = response.json()
                
                if data.get("rt_cd") != "0":
                    logger.error(f"Balance query failed: {data.get('msg1')}")
                    raise Exception(f"Balance query failed: {data.get('msg1')}")
                
                output1 = data.get("output1", [])
                output2 = data.get("output2", [{}])[0] if data.get("output2") else {}
                
                # 포지션 파싱
                positions = []
                for item in output1:
                    hldg_qty = int(item.get("hldg_qty", 0))
                    if hldg_qty <= 0:
                        continue
                    
                    pchs_avg_pric = float(item.get("pchs_avg_pric", 0))
                    prpr = int(item.get("prpr", 0))
                    evlu_amt = int(item.get("evlu_amt", 0))
                    evlu_pfls_rt = float(item.get("evlu_pfls_rt", 0)) / 100  # 퍼센트를 비율로 변환
                    
                    positions.append({
                        "ticker": item.get("pdno", ""),
                        "name": item.get("prdt_name", ""),
                        "shares": hldg_qty,
                        "avg_price": pchs_avg_pric,
                        "current_price": prpr,
                        "eval_amount": evlu_amt,
                        "profit_loss_rate": evlu_pfls_rt
                    })
                
                # 예수금
                cash_krw = int(output2.get("dnca_tot_amt", 0))
                total_value = int(output2.get("tot_evlu_amt", 0))
                
                # 비중 계산
                for pos in positions:
                    pos["weight_in_portfolio"] = pos["eval_amount"] / total_value if total_value > 0 else 0
                
                portfolio = {
                    "cash_krw": cash_krw,
                    "total_value": total_value,
                    "data_stale": False,
                    "positions": positions
                }
                
                self._portfolio_cache = portfolio
                self._portfolio_cache_time = datetime.now()
                
                return portfolio
                
        except Exception as e:
            logger.error(f"Failed to get portfolio: {e}")
            if self._portfolio_cache:
                self._portfolio_cache["data_stale"] = True
                return self._portfolio_cache
            raise
    
    async def get_buyable_amount(self, ticker: str = "") -> Dict[str, Any]:
        """매수가능금액 조회"""
        await self._get_auth_token()
        
        url = f"{HANSEC_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        params = {
            "CANO": HANSEC_CANO,
            "ACNT_PRDT_CD": HANSEC_ACNT_PRDT_CD,
            "PDNO": ticker if ticker else "",
            "ORD_UNPR": "0",
            "ORD_DVSN": "01",  # 시장가
            "CMA_EVLU_AMT_ICLD_YN": "N",
            "OVRS_ICLD_YN": "N"
        }
        
        headers = self._get_headers(TR_ID_PSBL_ORDER)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            data = response.json()
            
            if data.get("rt_cd") == "0":
                output = data.get("output", {})
                return {
                    "ord_psbl_cash": int(output.get("ord_psbl_cash", 0)),
                    "nrcvb_buy_amt": int(output.get("nrcvb_buy_amt", 0)),
                    "nrcvb_buy_qty": int(output.get("nrcvb_buy_qty", 0))
                }
            else:
                logger.error(f"Buyable amount query failed: {data.get('msg1')}")
                return {"ord_psbl_cash": 0, "nrcvb_buy_amt": 0, "nrcvb_buy_qty": 0}
    
    async def get_sellable_qty(self, ticker: str) -> int:
        """매도가능수량 조회"""
        await self._get_auth_token()
        
        url = f"{HANSEC_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-sell"
        params = {
            "CANO": HANSEC_CANO,
            "ACNT_PRDT_CD": HANSEC_ACNT_PRDT_CD,
            "PDNO": ticker
        }
        
        headers = self._get_headers(TR_ID_PSBL_SELL)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            data = response.json()
            
            if data.get("rt_cd") == "0":
                output = data.get("output", {})
                return int(output.get("ord_psbl_qty", 0))
            else:
                logger.error(f"Sellable qty query failed: {data.get('msg1')}")
                return 0
    
    async def _save_decision_to_s3(self, gpt_input: Dict, gpt_output: Dict):
        """GPT 결정 결과를 S3에 저장"""
        if not self._s3_client:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            key = f"portfolio-decisions/decision_{timestamp}.json"
            
            data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "input": gpt_input,
                "output": gpt_output
            }
            
            body = json.dumps(data, ensure_ascii=False, indent=2)
            
            self._s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=key,
                Body=body.encode('utf-8'),
                ContentType='application/json'
            )
            logger.info(f"Saved decision to S3: {key}")
        except ClientError as e:
            logger.error(f"Failed to save decision to S3: {e}")
    
    async def _check_volume_level(self) -> bool:
        """거래량 수준 확인 (높으면 True)"""
        # 코스피 대표 종목(삼성전자)의 거래량으로 시장 전체 거래량 추정
        try:
            await self._get_auth_token()
            
            url = f"{HANSEC_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-ccnl"
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": "005930"  # 삼성전자
            }
            
            headers = self._get_headers(TR_ID_CCNL)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("rt_cd") == "0":
                        output1 = data.get("output1", {})
                        acml_vol = int(output1.get("acml_vol", 0))  # 누적 거래량
                        prdy_vol = int(output1.get("prdy_vol", 1))  # 전일 거래량
                        
                        if prdy_vol > 0:
                            volume_ratio = acml_vol / prdy_vol
                            is_high = volume_ratio >= VOLUME_HIGH_THRESHOLD
                            logger.info(f"Volume ratio: {volume_ratio:.2f} (high: {is_high})")
                            return is_high
        except Exception as e:
            logger.warning(f"Failed to check volume level: {e}")
        
        return False
    
    async def get_macro_summary(self) -> Dict[str, str]:
        """거시경제 보고서 요약 조회"""
        try:
            # S3에서 최신 _short 보고서 조회 (실제 구현에서는 boto3 사용)
            # 여기서는 간소화된 버전 - 거시경제 에이전트 API 호출
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{MACRO_AGENT_URL}/result/analysis")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "positive_summary": data.get("positive_summary", ""),
                        "negative_summary": data.get("negative_summary", ""),
                        "market_bias_hint": data.get("market_bias_hint", "uncertain")
                    }
        except Exception as e:
            logger.warning(f"Failed to get macro summary: {e}")
        
        return {
            "positive_summary": "거시경제 데이터 없음",
            "negative_summary": "거시경제 데이터 없음",
            "market_bias_hint": "uncertain"
        }
    
    async def get_candidate_tickers(self, top_n: int = 5) -> List[Dict]:
        """후보 종목 조회"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{TICKER_SELECTOR_URL}/api/candidates",
                    json={"top_n": top_n}
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("top_candidates", [])
        except Exception as e:
            logger.warning(f"Failed to get candidate tickers: {e}")
        
        return []
    
    async def get_technical_analysis(self, ticker: str) -> Dict[str, Any]:
        """기술적 분석 조회"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{TECHNICAL_AGENT_URL}/result/analysis",
                    json={"ticker": ticker}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Failed to get technical analysis for {ticker}: {e}")
        
        return {}
    
    async def _send_order_via_websocket(self, order: Dict) -> Dict:
        """WebSocket으로 주문 전송"""
        try:
            async with websockets.connect(TRADING_AGENT_WS_URL) as ws:
                await ws.send(json.dumps(order))
                response = await asyncio.wait_for(ws.recv(), timeout=30.0)
                return json.loads(response)
        except Exception as e:
            logger.error(f"WebSocket order failed: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def execute_decision(self, decision: Dict) -> List[Dict]:
        """매매 결정 실행"""
        results = []
        portfolio = await self.get_portfolio()
        
        for ticker_decision in decision.get("ticker_decisions", []):
            ticker = ticker_decision.get("ticker")
            action = ticker_decision.get("action", "HOLD").upper()
            target_weight = ticker_decision.get("target_weight", 0)
            
            if action == "HOLD":
                continue
            
            # 현재 포지션 확인
            current_position = next(
                (p for p in portfolio["positions"] if p["ticker"] == ticker),
                None
            )
            
            if action == "BUY":
                # 매수 수량 계산
                target_amount = portfolio["total_value"] * target_weight
                current_amount = current_position["eval_amount"] if current_position else 0
                order_amount = target_amount - current_amount
                
                if order_amount < MIN_ORDER_KRW:
                    continue
                
                # 기술 분석에서 현재가 조회
                tech = await self.get_technical_analysis(ticker)
                current_price = tech.get("current_price", 0)
                if current_price <= 0:
                    continue
                
                order_qty = int(order_amount / current_price)
                if order_qty <= 0:
                    continue
                
                order = {
                    "request_id": str(uuid4()),
                    "action": "buy",
                    "ticker": ticker,
                    "qty": order_qty,
                    "order_type": "market",
                    "price": 0,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                
                result = await self._send_order_via_websocket(order)
                results.append({"ticker": ticker, "action": "BUY", "result": result})
                
            elif action == "SELL":
                if not current_position:
                    continue
                
                if target_weight == 0:
                    # 전량 매도
                    sell_qty = await self.get_sellable_qty(ticker)
                else:
                    # 일부 매도
                    target_amount = portfolio["total_value"] * target_weight
                    current_amount = current_position["eval_amount"]
                    sell_amount = current_amount - target_amount
                    sell_qty = int(sell_amount / current_position["current_price"])
                
                if sell_qty <= 0:
                    continue
                
                order = {
                    "request_id": str(uuid4()),
                    "action": "sell",
                    "ticker": ticker,
                    "qty": sell_qty,
                    "order_type": "market",
                    "price": 0,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                
                result = await self._send_order_via_websocket(order)
                results.append({"ticker": ticker, "action": "SELL", "result": result})
        
        return results
    
    async def _check_stop_loss_take_profit(self) -> List[Dict]:
        """손절/익절 체크"""
        portfolio = await self.get_portfolio()
        orders = []
        
        for position in portfolio["positions"]:
            profit_rate = position["profit_loss_rate"]
            
            # 손절: -5% 이하
            if profit_rate <= STOP_LOSS_RATE:
                logger.info(f"Stop loss triggered for {position['ticker']}: {profit_rate:.2%}")
                sell_qty = await self.get_sellable_qty(position["ticker"])
                if sell_qty > 0:
                    order = {
                        "request_id": str(uuid4()),
                        "action": "sell",
                        "ticker": position["ticker"],
                        "qty": sell_qty,
                        "order_type": "market",
                        "price": 0,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    result = await self._send_order_via_websocket(order)
                    orders.append({"ticker": position["ticker"], "action": "STOP_LOSS", "result": result})
            
            # 익절: +15% 이상
            elif profit_rate >= TAKE_PROFIT_RATE:
                logger.info(f"Take profit triggered for {position['ticker']}: {profit_rate:.2%}")
                sell_qty = await self.get_sellable_qty(position["ticker"])
                if sell_qty > 0:
                    order = {
                        "request_id": str(uuid4()),
                        "action": "sell",
                        "ticker": position["ticker"],
                        "qty": sell_qty,
                        "order_type": "market",
                        "price": 0,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    result = await self._send_order_via_websocket(order)
                    orders.append({"ticker": position["ticker"], "action": "TAKE_PROFIT", "result": result})
        
        return orders
    
    async def make_decision(self) -> Dict[str, Any]:
        """GPT를 통한 매매 결정"""
        if not self._openai_client:
            logger.warning("OpenAI client not configured")
            return {"ticker_decisions": []}
        
        # 데이터 수집
        try:
            portfolio = await self.get_portfolio()
        except Exception as e:
            logger.error(f"Failed to get portfolio: {e}")
            return {"ticker_decisions": []}  # 포트폴리오 조회 실패 시 결정 불가
        
        macro = await self.get_macro_summary()
        candidates = await self.get_candidate_tickers(5)
        
        # universe 구성 (현재 보유 종목 + 후보 종목)
        universe = []
        processed_tickers = set()
        
        # 보유 종목 추가 (기술분석 실패해도 포트폴리오 데이터로 추가)
        for pos in portfolio["positions"]:
            tech = await self.get_technical_analysis(pos["ticker"])
            universe.append({
                "ticker": pos["ticker"],
                "name": pos["name"],
                "current_price": pos["current_price"],
                "technical": self._simplify_technical(tech) if tech else self._get_empty_technical(),
                "fundamental": {"valuation": "fair", "quality": "medium", "growth": "medium"},
                "is_in_portfolio": True
            })
            processed_tickers.add(pos["ticker"])
        
        # 후보 종목 추가 (기술분석 실패 시 해당 종목 스킵)
        for candidate in candidates[:5]:
            ticker = candidate.get("ticker", "")
            if ticker in processed_tickers:
                continue
            
            tech = await self.get_technical_analysis(ticker)
            
            # 기술분석 실패 또는 현재가 없으면 스킵
            if not tech or tech.get("current_price", 0) <= 0:
                logger.warning(f"Skipping candidate {ticker}: no technical data or price")
                continue
            
            universe.append({
                "ticker": ticker,
                "name": candidate.get("name", ""),
                "current_price": tech.get("current_price", 0),
                "technical": self._simplify_technical(tech),
                "fundamental": {
                    "valuation": "fair",
                    "quality": "medium",
                    "growth": "medium",
                    "recent_events": candidate.get("top_headlines", [])[:3]
                },
                "is_in_portfolio": False
            })
            processed_tickers.add(ticker)
        
        # universe가 비어있으면 기본 결정 반환 (모두 HOLD)
        if not universe:
            logger.warning("Universe is empty, returning default HOLD decision")
            return {
                "meta": {
                    "decision_time_utc": datetime.utcnow().isoformat() + "Z",
                    "overall_comment": "No stocks to analyze. Holding current positions."
                },
                "global_view": {
                    "macro_bias": macro.get("market_bias_hint", "uncertain"),
                    "risk_action": "keep_exposure",
                    "target_cash_ratio": 0.5
                },
                "ticker_decisions": []
            }
        
        # GPT 입력 구성
        gpt_input = {
            "now_utc": datetime.utcnow().isoformat() + "Z",
            "macro": macro,
            "portfolio": portfolio,
            "universe": universe,
            "constraints": {
                "max_buy_candidates": MAX_BUY_CANDIDATES,
                "max_sell_candidates": MAX_SELL_CANDIDATES,
                "min_order_krw": MIN_ORDER_KRW,
                "max_turnover_ratio": MAX_TURNOVER_RATIO,
                "target_max_single_ticker_weight": MAX_SINGLE_TICKER_WEIGHT,
                "risk_mode": "normal"
            }
        }
        
        # GPT 호출
        try:
            response = await self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": GPT_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(gpt_input, ensure_ascii=False)}
                ],
                temperature=0.2,
                max_tokens=2048
            )
            
            content = response.choices[0].message.content
            
            # JSON 파싱 시도
            try:
                # ```json ... ``` 형식 처리
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                decision = json.loads(content.strip())
                logger.info(f"GPT decision: {decision.get('meta', {}).get('overall_comment', '')}")
                
                # S3에 결정 결과 저장 (비동기)
                asyncio.create_task(self._save_decision_to_s3(gpt_input, decision))
                
                return decision
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GPT response: {e}")
                return {"ticker_decisions": []}
                
        except Exception as e:
            logger.error(f"GPT call failed: {e}")
            return {"ticker_decisions": []}
    
    def _get_empty_technical(self) -> Dict:
        """빈 기술분석 데이터 (기본값)"""
        return {
            "day": {
                "trend": "sideway",
                "rsi": 50,
                "macd_signal": "neutral",
                "bollinger_position": "middle",
                "fibonacci_zone": "none"
            },
            "week": {
                "trend": "sideway",
                "macd_signal": "neutral"
            },
            "month": {
                "trend": "sideway"
            }
        }
    
    def _simplify_technical(self, tech: Dict) -> Dict:
        """기술적 분석 데이터 단순화"""
        if not tech:
            return self._get_empty_technical()
        
        day = tech.get("day", {})
        week = tech.get("week", {})
        month = tech.get("month", {})
        
        def get_trend(period_data):
            fib = period_data.get("fibonacci_retracement", {})
            return fib.get("trend", "sideway")
        
        def get_bb_position(period_data, current_price):
            bb = period_data.get("bollinger_band", {})
            top = bb.get("top", 0)
            bottom = bb.get("bottom", 0)
            if current_price >= top:
                return "upper"
            elif current_price <= bottom:
                return "lower"
            return "middle"
        
        current_price = tech.get("current_price", 0)
        
        return {
            "day": {
                "trend": get_trend(day),
                "rsi": day.get("rsi", 50),
                "macd_signal": day.get("macd", {}).get("signal", "neutral"),
                "bollinger_position": get_bb_position(day, current_price),
                "fibonacci_zone": "none"
            },
            "week": {
                "trend": get_trend(week),
                "macd_signal": week.get("macd", {}).get("signal", "neutral")
            },
            "month": {
                "trend": get_trend(month)
            }
        }
    
    async def _decision_loop(self):
        """매매 결정 루프 (30분마다)"""
        while True:
            try:
                # 장시간 체크 (09:00~15:30)
                now = datetime.now()
                hour = now.hour
                minute = now.minute
                
                if 9 <= hour < 15 or (hour == 15 and minute <= 30):
                    logger.info("Starting decision cycle...")
                    decision = await self.make_decision()
                    if decision.get("ticker_decisions"):
                        results = await self.execute_decision(decision)
                        logger.info(f"Decision executed: {len(results)} orders")
                else:
                    logger.info("Market closed, skipping decision cycle")
                
            except Exception as e:
                logger.error(f"Decision loop error: {e}")
            
            await asyncio.sleep(1800)  # 30분
    
    async def _rebalance_loop(self):
        """리밸런싱 루프 (거래량에 따라 5~10분마다)"""
        while True:
            try:
                now = datetime.now()
                hour = now.hour
                minute = now.minute
                
                if 9 <= hour < 15 or (hour == 15 and minute <= 30):
                    # 거래량 수준 확인
                    self._high_volume_mode = await self._check_volume_level()
                    
                    # 손절/익절 체크
                    stop_orders = await self._check_stop_loss_take_profit()
                    if stop_orders:
                        logger.info(f"Stop/Take profit orders: {len(stop_orders)}")
                
            except Exception as e:
                logger.error(f"Rebalance loop error: {e}")
            
            # 거래량 높으면 5분, 낮으면 10분
            sleep_time = 300 if self._high_volume_mode else 600
            logger.info(f"Rebalance loop sleeping for {sleep_time}s (high_volume: {self._high_volume_mode})")
            await asyncio.sleep(sleep_time)


# 전역 포트폴리오 매니저
portfolio_manager = PortfolioManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    logger.info("Portfolio Manager starting...")
    await portfolio_manager.initialize()
    yield
    logger.info("Portfolio Manager shutting down...")
    await portfolio_manager.shutdown()


app = FastAPI(
    title="Portfolio Manager Agent",
    description="포트폴리오 관리 에이전트 - 매매 의사결정 및 실행",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/api/portfolio", response_model=PortfolioStatus)
async def get_portfolio():
    """포트폴리오 현황 조회"""
    try:
        portfolio = await portfolio_manager.get_portfolio()
        return PortfolioStatus(
            cash_krw=portfolio["cash_krw"],
            total_value=portfolio["total_value"],
            positions=portfolio["positions"],
            last_updated=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/decision")
async def trigger_decision():
    """수동 매매 결정 트리거"""
    try:
        decision = await portfolio_manager.make_decision()
        results = await portfolio_manager.execute_decision(decision)
        return {
            "decision": decision,
            "execution_results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/buyable")
async def get_buyable_amount(ticker: str = ""):
    """매수가능금액 조회"""
    try:
        result = await portfolio_manager.get_buyable_amount(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health/live", response_model=HealthResponse)
async def liveness_probe():
    """Liveness probe"""
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=HealthResponse)
async def readiness_probe():
    """Readiness probe"""
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
    uvicorn.run(app, host="0.0.0.0", port=8004)

