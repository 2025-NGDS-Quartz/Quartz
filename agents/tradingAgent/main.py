"""
거래 에이전트 (Trading Agent)
- 실제 주식 거래 수행
- 포트폴리오 관리 에이전트와 WebSocket으로 연결
- 포트: 8005
"""
import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Set
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "agent": "trading-agent", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# 환경변수
HANSEC_APP_KEY = os.getenv("HANSEC_INVESTMENT_APP_KEY", "")
HANSEC_APP_SECRET = os.getenv("HANSEC_INVESTMENT_APP_SECRET_KEY", "")
HANSEC_CANO = os.getenv("HANSEC_INVESTMENT_CANO", "")
HANSEC_ACNT_PRDT_CD = os.getenv("HANSEC_INVESTMENT_ACNT_PRDT_CD", "01")
HANSEC_BASE_URL = "https://openapi.koreainvestment.com:9443"
AUTH_AGENT_URL = os.getenv("AUTH_AGENT_URL", "http://auth-agent:8006")

# TR_ID (실전투자)
TR_ID_BUY = "TTTC0012U"
TR_ID_SELL = "TTTC0011U"
TR_ID_MODIFY = "TTTC0013U"
TR_ID_PSBL_RVSECNCL = "TTTC0084R"


class OrderRequest(BaseModel):
    """주문 요청 모델"""
    request_id: str
    action: str  # buy, sell
    ticker: str
    qty: int
    order_type: str  # market, limit
    price: int = 0
    timestamp: str


class OrderResponse(BaseModel):
    """주문 응답 모델"""
    request_id: str
    status: str  # success, failed, pending
    order_no: Optional[str] = None
    message: str
    timestamp: str


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str


class TradingExecutor:
    """거래 실행 클래스"""
    
    def __init__(self):
        self._auth_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._pending_orders: Dict[str, Dict] = {}  # 미체결 주문 관리
    
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
        """API 요청 헤더 생성"""
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._auth_token}",
            "appkey": HANSEC_APP_KEY,
            "appsecret": HANSEC_APP_SECRET,
            "tr_id": tr_id,
            "custtype": "P"
        }
    
    async def execute_order(self, order: OrderRequest) -> OrderResponse:
        """주문 실행"""
        logger.info(f"Executing order: {order.action} {order.ticker} x {order.qty}")
        
        # 토큰 갱신
        try:
            await self._get_auth_token()
        except Exception as e:
            return OrderResponse(
                request_id=order.request_id,
                status="failed",
                message=f"Auth token error: {str(e)}",
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # 재시도 로직
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                if order.action.lower() == "buy":
                    result = await self._execute_buy(order)
                elif order.action.lower() == "sell":
                    result = await self._execute_sell(order)
                else:
                    return OrderResponse(
                        request_id=order.request_id,
                        status="failed",
                        message=f"Invalid action: {order.action}",
                        timestamp=datetime.utcnow().isoformat() + "Z"
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"Order execution error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    return OrderResponse(
                        request_id=order.request_id,
                        status="failed",
                        message=f"Order failed after {max_retries} attempts: {str(e)}",
                        timestamp=datetime.utcnow().isoformat() + "Z"
                    )
    
    async def _execute_buy(self, order: OrderRequest) -> OrderResponse:
        """매수 주문 실행"""
        url = f"{HANSEC_BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
        
        # 주문 구분 (00: 지정가, 01: 시장가)
        ord_dvsn = "01" if order.order_type == "market" else "00"
        ord_unpr = "0" if order.order_type == "market" else str(order.price)
        
        body = {
            "CANO": HANSEC_CANO,
            "ACNT_PRDT_CD": HANSEC_ACNT_PRDT_CD,
            "PDNO": order.ticker,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(order.qty),
            "ORD_UNPR": ord_unpr
        }
        
        headers = self._get_headers(TR_ID_BUY)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=body)
            data = response.json()
            
            if response.status_code == 200 and data.get("rt_cd") == "0":
                output = data.get("output", {})
                order_no = output.get("ODNO", "")
                
                # 미체결 주문 저장
                self._pending_orders[order_no] = {
                    "request_id": order.request_id,
                    "ticker": order.ticker,
                    "action": "buy",
                    "qty": order.qty,
                    "krx_fwdg_ord_orgno": output.get("KRX_FWDG_ORD_ORGNO", "")
                }
                
                logger.info(f"Buy order success: {order_no}")
                return OrderResponse(
                    request_id=order.request_id,
                    status="success",
                    order_no=order_no,
                    message=data.get("msg1", "주문 전송 완료"),
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
            else:
                error_msg = data.get("msg1", "Unknown error")
                logger.error(f"Buy order failed: {error_msg}")
                return OrderResponse(
                    request_id=order.request_id,
                    status="failed",
                    message=error_msg,
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
    
    async def _execute_sell(self, order: OrderRequest) -> OrderResponse:
        """매도 주문 실행"""
        url = f"{HANSEC_BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
        
        ord_dvsn = "01" if order.order_type == "market" else "00"
        ord_unpr = "0" if order.order_type == "market" else str(order.price)
        
        body = {
            "CANO": HANSEC_CANO,
            "ACNT_PRDT_CD": HANSEC_ACNT_PRDT_CD,
            "PDNO": order.ticker,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(order.qty),
            "ORD_UNPR": ord_unpr
        }
        
        headers = self._get_headers(TR_ID_SELL)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=body)
            data = response.json()
            
            if response.status_code == 200 and data.get("rt_cd") == "0":
                output = data.get("output", {})
                order_no = output.get("ODNO", "")
                
                self._pending_orders[order_no] = {
                    "request_id": order.request_id,
                    "ticker": order.ticker,
                    "action": "sell",
                    "qty": order.qty,
                    "krx_fwdg_ord_orgno": output.get("KRX_FWDG_ORD_ORGNO", "")
                }
                
                logger.info(f"Sell order success: {order_no}")
                return OrderResponse(
                    request_id=order.request_id,
                    status="success",
                    order_no=order_no,
                    message=data.get("msg1", "주문 전송 완료"),
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
            else:
                error_msg = data.get("msg1", "Unknown error")
                logger.error(f"Sell order failed: {error_msg}")
                return OrderResponse(
                    request_id=order.request_id,
                    status="failed",
                    message=error_msg,
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
    
    async def cancel_order(
        self, 
        order_no: str, 
        krx_fwdg_ord_orgno: str,
        qty: int,
        all_qty: bool = True
    ) -> Dict[str, Any]:
        """주문 취소"""
        await self._get_auth_token()
        
        url = f"{HANSEC_BASE_URL}/uapi/domestic-stock/v1/trading/order-rvsecncl"
        
        body = {
            "CANO": HANSEC_CANO,
            "ACNT_PRDT_CD": HANSEC_ACNT_PRDT_CD,
            "KRX_FWDG_ORD_ORGNO": krx_fwdg_ord_orgno,
            "ORGN_ODNO": order_no,
            "ORD_DVSN": "00",
            "RVSE_CNCL_DVSN_CD": "02",  # 02: 취소
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0",
            "QTY_ALL_ORD_YN": "Y" if all_qty else "N"
        }
        
        headers = self._get_headers(TR_ID_MODIFY)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=body)
            data = response.json()
            
            if response.status_code == 200 and data.get("rt_cd") == "0":
                logger.info(f"Order cancelled: {order_no}")
                return {"status": "success", "message": "주문 취소 완료"}
            else:
                error_msg = data.get("msg1", "Unknown error")
                logger.error(f"Cancel order failed: {error_msg}")
                return {"status": "failed", "message": error_msg}
    
    async def get_cancelable_orders(self) -> list:
        """정정취소 가능 주문 조회"""
        await self._get_auth_token()
        
        url = f"{HANSEC_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
        
        params = {
            "CANO": HANSEC_CANO,
            "ACNT_PRDT_CD": HANSEC_ACNT_PRDT_CD,
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
            "INQR_DVSN_1": "0",  # 주문
            "INQR_DVSN_2": "0"   # 전체
        }
        
        headers = self._get_headers(TR_ID_PSBL_RVSECNCL)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            data = response.json()
            
            if response.status_code == 200 and data.get("rt_cd") == "0":
                return data.get("output", [])
            else:
                logger.error(f"Failed to get cancelable orders: {data.get('msg1')}")
                return []


# 전역 거래 실행기
executor = TradingExecutor()

# WebSocket 연결 관리
connected_clients: Set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    logger.info("Trading Agent starting...")
    yield
    logger.info("Trading Agent shutting down...")


app = FastAPI(
    title="Trading Agent",
    description="거래 에이전트 - 실제 주식 매매 수행",
    version="1.0.0",
    lifespan=lifespan
)


async def send_ping(websocket: WebSocket):
    """30초마다 ping 전송"""
    try:
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat() + "Z"})
            except Exception:
                break
    except asyncio.CancelledError:
        pass


@app.websocket("/ws/orders")
async def websocket_orders(websocket: WebSocket):
    """WebSocket 주문 엔드포인트"""
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info("Portfolio manager connected via WebSocket")
    
    # Ping 태스크 시작
    ping_task = asyncio.create_task(send_ping(websocket))
    
    try:
        while True:
            # 주문 메시지 수신
            data = await websocket.receive_text()
            
            # Pong 응답 처리
            try:
                msg = json.loads(data)
                if msg.get("type") == "pong":
                    continue
            except:
                pass
            
            try:
                order_data = json.loads(data)
                order = OrderRequest(**order_data)
                
                logger.info(f"Received order: {order.request_id}")
                
                # 주문 실행
                result = await executor.execute_order(order)
                
                # 결과 전송
                await websocket.send_text(result.model_dump_json())
                
            except json.JSONDecodeError:
                error_response = OrderResponse(
                    request_id="unknown",
                    status="failed",
                    message="Invalid JSON format",
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
                await websocket.send_text(error_response.model_dump_json())
            except Exception as e:
                logger.error(f"Order processing error: {e}")
                error_response = OrderResponse(
                    request_id=order_data.get("request_id", "unknown"),
                    status="failed",
                    message=str(e),
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
                await websocket.send_text(error_response.model_dump_json())
                
    except WebSocketDisconnect:
        logger.info("Portfolio manager disconnected")
    finally:
        ping_task.cancel()
        connected_clients.discard(websocket)


@app.post("/api/order", response_model=OrderResponse)
async def execute_order_http(order: OrderRequest):
    """HTTP 주문 API (테스트/백업용)"""
    result = await executor.execute_order(order)
    return result


@app.get("/api/cancelable-orders")
async def get_cancelable_orders():
    """정정취소 가능 주문 조회 API"""
    orders = await executor.get_cancelable_orders()
    return {"orders": orders}


@app.post("/api/cancel-order")
async def cancel_order(order_no: str, krx_fwdg_ord_orgno: str, qty: int, all_qty: bool = True):
    """주문 취소 API"""
    result = await executor.cancel_order(order_no, krx_fwdg_ord_orgno, qty, all_qty)
    return result


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
    uvicorn.run(app, host="0.0.0.0", port=8005)

