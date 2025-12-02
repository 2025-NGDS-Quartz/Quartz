# 한국투자증권 국내주식 API 문서

## 1. 주식주문(현금) - v1_국내주식-001

### 사용목적
국내주식 현금 매수/매도 주문을 실행하는 API

### 호출방법

| 항목 | 값 |
|------|-----|
| Method | `POST` |
| 실전 URL | `https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/order-cash` |
| 모의 URL | `https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash` |
| 실전 TR_ID | 매도: `TTTC0011U` / 매수: `TTTC0012U` |
| 모의 TR_ID | 매도: `VTTC0011U` / 매수: `VTTC0012U` |

**Request Header**
```
content-type: application/json; charset=utf-8
authorization: Bearer {접근토큰}
appkey: {앱키}
appsecret: {앱시크릿키}
tr_id: {거래ID}
custtype: P (개인) / B (법인)
```

**Request Body**
```json
{
  "CANO": "종합계좌번호 (8자리)",
  "ACNT_PRDT_CD": "계좌상품코드 (2자리)",
  "PDNO": "종목코드 (6자리)",
  "ORD_DVSN": "주문구분 (00:지정가, 01:시장가 등)",
  "ORD_QTY": "주문수량",
  "ORD_UNPR": "주문단가 (시장가는 0)"
}
```

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "APBK0013",
  "msg1": "주문 전송 완료 되었습니다.",
  "output": {
    "KRX_FWDG_ORD_ORGNO": "거래소코드",
    "ODNO": "주문번호",
    "ORD_TMD": "주문시간"
  }
}
```

---

## 2. 주식주문(정정취소) - v1_국내주식-003

### 사용목적
기존 주문 건에 대해 정정 또는 취소를 수행하는 API (이미 체결된 건은 불가)

### 호출방법

| 항목 | 값 |
|------|-----|
| Method | `POST` |
| 실전 URL | `https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/order-rvsecncl` |
| 모의 URL | `https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-rvsecncl` |
| 실전 TR_ID | `TTTC0013U` |
| 모의 TR_ID | `VTTC0013U` |

**Request Header**
```
content-type: application/json; charset=utf-8
authorization: Bearer {접근토큰}
appkey: {앱키}
appsecret: {앱시크릿키}
tr_id: {거래ID}
custtype: P (개인) / B (법인)
```

**Request Body**
```json
{
  "CANO": "종합계좌번호",
  "ACNT_PRDT_CD": "계좌상품코드",
  "KRX_FWDG_ORD_ORGNO": "한국거래소전송주문조직번호",
  "ORGN_ODNO": "원주문번호",
  "ORD_DVSN": "주문구분",
  "RVSE_CNCL_DVSN_CD": "01 (정정) / 02 (취소)",
  "ORD_QTY": "주문수량",
  "ORD_UNPR": "주문단가",
  "QTY_ALL_ORD_YN": "Y (전량) / N (일부)"
}
```

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "APBK0013",
  "msg1": "주문 전송 완료 되었습니다.",
  "output": {
    "KRX_FWDG_ORD_ORGNO": "한국거래소전송주문조직번호",
    "ODNO": "주문번호",
    "ORD_TMD": "주문시각"
  }
}
```

---

## 3. 주식잔고조회 - v1_국내주식-006

### 사용목적
보유 주식의 잔고 현황을 조회하는 API (보유종목, 수량, 평가손익 등)

### 호출방법

| 항목 | 값 |
|------|-----|
| Method | `GET` |
| 실전 URL | `https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance` |
| 모의 URL | `https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-balance` |
| 실전 TR_ID | `TTTC8434R` |
| 모의 TR_ID | `VTTC8434R` |

**Request Header**
```
authorization: Bearer {접근토큰}
appkey: {앱키}
appsecret: {앱시크릿키}
tr_id: {거래ID}
tr_cont: 공백 (초기조회) / N (연속조회)
```

**Query Parameters**
```
CANO: 종합계좌번호 (8자리)
ACNT_PRDT_CD: 계좌상품코드 (2자리)
AFHR_FLPR_YN: N (기본) / Y (시간외단일가) / X (NXT)
INQR_DVSN: 01 (대출일별) / 02 (종목별)
UNPR_DVSN: 01 (기본값)
FUND_STTL_ICLD_YN: N / Y
FNCG_AMT_AUTO_RDPT_YN: N (기본값)
PRCS_DVSN: 00 (전일매매포함) / 01 (전일매매미포함)
CTX_AREA_FK100: 연속조회검색조건
CTX_AREA_NK100: 연속조회키
```

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "KIOK0510",
  "msg1": "조회가 완료되었습니다",
  "ctx_area_fk100": "연속조회검색조건",
  "ctx_area_nk100": "연속조회키",
  "output1": [
    {
      "pdno": "종목번호",
      "prdt_name": "종목명",
      "hldg_qty": "보유수량",
      "ord_psbl_qty": "주문가능수량",
      "pchs_avg_pric": "매입평균가격",
      "pchs_amt": "매입금액",
      "prpr": "현재가",
      "evlu_amt": "평가금액",
      "evlu_pfls_amt": "평가손익금액",
      "evlu_pfls_rt": "평가손익율"
    }
  ],
  "output2": [
    {
      "dnca_tot_amt": "예수금총금액",
      "tot_evlu_amt": "총평가금액",
      "nass_amt": "순자산금액",
      "pchs_amt_smtl_amt": "매입금액합계",
      "evlu_amt_smtl_amt": "평가금액합계",
      "evlu_pfls_smtl_amt": "평가손익합계"
    }
  ]
}
```

---

## 공통 참고사항

- **인증**: OAuth 2.0 기반, Access Token 필요 (개인 1일/법인 3개월 유효)
- **토큰 형식**: `Bearer {토큰값}` 형태로 authorization 헤더에 전달
- **거래소 구분**: KRX (한국거래소), NXT (넥스트레이드), SOR (Smart Order Routing)
- **연속조회**: Response Header의 `tr_cont`가 M이면 다음 데이터 존재

## 4. 주식정정취소가능주문조회 (v1_국내주식-004)

### 사용목적
주문 정정/취소 전 정정취소 가능한 주문과 수량을 조회하는 API. 정정취소 주문 실행 전 반드시 이 API로 `psbl_qty`(정정취소가능수량)를 확인해야 함.

### 호출방법

| 항목 | 값 |
|------|-----|
| Method | `GET` |
| URL | `/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl` |
| Domain | `https://openapi.koreainvestment.com:9443` |
| TR_ID | `TTTC0084R` (실전) / 모의투자 미지원 |

**Request Parameters**
```
CANO: 계좌번호 앞 8자리
ACNT_PRDT_CD: 계좌번호 뒤 2자리
CTX_AREA_FK100: 연속조회키 (최초 공란)
CTX_AREA_NK100: 연속조회키 (최초 공란)
INQR_DVSN_1: 0(주문) / 1(종목)
INQR_DVSN_2: 0(전체) / 1(매도) / 2(매수)
```

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "KIOK0510",
  "msg1": "조회가 완료되었습니다",
  "output": [
    {
      "odno": "주문번호",
      "pdno": "종목번호",
      "prdt_name": "종목명",
      "ord_qty": "주문수량",
      "ord_unpr": "주문단가",
      "psbl_qty": "정정취소가능수량",
      "sll_buy_dvsn_cd": "01(매도)/02(매수)",
      "ord_dvsn_cd": "주문구분코드"
    }
  ]
}
```

---

## 5. 주식일별주문체결조회 (v1_국내주식-005)

### 사용목적
특정 기간 동안의 주문 및 체결 내역을 일별로 조회하는 API. 주문 히스토리 확인, 체결 여부 추적에 사용.

### 호출방법

| 항목 | 값 |
|------|-----|
| Method | `GET` |
| URL | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` |
| Domain | `https://openapi.koreainvestment.com:9443` (실전) |
| | `https://openapivts.koreainvestment.com:29443` (모의) |
| TR_ID (3개월 이내) | `TTTC0081R` (실전) / `VTTC0081R` (모의) |
| TR_ID (3개월 이전) | `CTSC9215R` (실전) / `VTSC9215R` (모의) |

**Request Parameters**
```
CANO: 계좌번호 앞 8자리
ACNT_PRDT_CD: 계좌번호 뒤 2자리
INQR_STRT_DT: 조회시작일자 (YYYYMMDD)
INQR_END_DT: 조회종료일자 (YYYYMMDD)
SLL_BUY_DVSN_CD: 00(전체) / 01(매도) / 02(매수)
CCLD_DVSN: 00(전체) / 01(체결) / 02(미체결)
INQR_DVSN: 00(역순) / 01(정순)
PDNO: 종목번호 (선택)
CTX_AREA_FK100, CTX_AREA_NK100: 연속조회키
```

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "KIOK0510",
  "output1": [
    {
      "ord_dt": "주문일자",
      "odno": "주문번호",
      "pdno": "종목번호",
      "prdt_name": "종목명",
      "ord_qty": "주문수량",
      "ord_unpr": "주문단가",
      "tot_ccld_qty": "총체결수량",
      "tot_ccld_amt": "총체결금액",
      "avg_prvs": "평균가",
      "sll_buy_dvsn_cd": "매도매수구분",
      "cncl_yn": "취소여부",
      "rmn_qty": "잔여수량"
    }
  ],
  "output2": {
    "tot_ord_qty": "총주문수량",
    "tot_ccld_qty": "총체결수량",
    "tot_ccld_amt": "총체결금액"
  }
}
```

---

## 6. 매도가능수량조회 (국내주식-165)

### 사용목적
특정 종목의 매도 가능 수량을 조회하는 API. 매도 주문 전 실제 매도 가능한 수량(`ord_psbl_qty`) 확인에 사용.

### 호출방법

| 항목 | 값 |
|------|-----|
| Method | `GET` |
| URL | `/uapi/domestic-stock/v1/trading/inquire-psbl-sell` |
| Domain | `https://openapi.koreainvestment.com:9443` |
| TR_ID | `TTTC8408R` (실전) / 모의투자 미지원 |

**Request Parameters**
```
CANO: 계좌번호 앞 8자리
ACNT_PRDT_CD: 계좌번호 뒤 2자리
PDNO: 종목번호 (ex: 005930)
```

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "KIOK0420",
  "msg1": "정상적으로 조회되었습니다",
  "output": {
    "pdno": "종목번호",
    "prdt_name": "종목명",
    "buy_qty": "매수수량",
    "sll_qty": "매도수량",
    "cblc_qty": "잔고수량",
    "ord_psbl_qty": "주문가능수량",
    "pchs_avg_pric": "매입평균가격",
    "now_pric": "현재가",
    "evlu_amt": "평가금액",
    "evlu_pfls_amt": "평가손익금액",
    "evlu_pfls_rt": "평가손익율"
  }
}
```

---

## 공통 Request Header

모든 API 호출 시 필요한 헤더:

```
content-type: application/json; charset=utf-8
authorization: Bearer {access_token}
appkey: {발급받은 appkey}
appsecret: {발급받은 appsecret}
tr_id: {각 API별 TR_ID}
custtype: P(개인) / B(법인)
```