# 한국투자증권 해외주식 API 문서

## 공통 정보

| 항목 | 값 |
|------|-----|
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |

---

## 1. 해외주식 주문 (v1_해외주식-001)

### 사용 목적
해외주식 매수/매도 주문을 실행합니다. 미국, 일본, 홍콩, 상해, 심천, 베트남 거래소 지원.

### 호출 방법

| 항목 | 값 |
|------|-----|
| Method | `POST` |
| URL | `/uapi/overseas-stock/v1/trading/order` |
| 실전 TR_ID | `TTTT1002U` (미국매수), `TTTT1006U` (미국매도) 등 |
| 모의 TR_ID | `VTTT1002U` (미국매수), `VTTT1001U` (미국매도) 등 |

**Request Body**
```json
{
  "CANO": "810XXXXX",
  "ACNT_PRDT_CD": "01",
  "OVRS_EXCG_CD": "NASD",
  "PDNO": "AAPL",
  "ORD_QTY": "1",
  "OVRS_ORD_UNPR": "145.00",
  "ORD_SVR_DVSN_CD": "0",
  "ORD_DVSN": "00"
}
```

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "APBK0013",
  "msg1": "주문 전송 완료 되었습니다.",
  "output": {
    "KRX_FWDG_ORD_ORGNO": "01790",
    "ODNO": "0000004336",
    "ORD_TMD": "160524"
  }
}
```

---

## 2. 해외주식 정정취소주문 (v1_해외주식-003)

### 사용 목적
접수된 해외주식 주문을 정정하거나 취소합니다.

### 호출 방법

| 항목 | 값 |
|------|-----|
| Method | `POST` |
| URL | `/uapi/overseas-stock/v1/trading/order-rvsecncl` |
| 실전 TR_ID | `TTTT1004U` (미국), `TTTS1003U` (홍콩) 등 |
| 모의 TR_ID | `VTTT1004U` (미국), `VTTS1003U` (홍콩) 등 |

**Request Body**
```json
{
  "CANO": "810XXXXX",
  "ACNT_PRDT_CD": "01",
  "OVRS_EXCG_CD": "NYSE",
  "PDNO": "BA",
  "ORGN_ODNO": "30135009",
  "RVSE_CNCL_DVSN_CD": "01",
  "ORD_QTY": "1",
  "OVRS_ORD_UNPR": "226.00"
}
```

> `RVSE_CNCL_DVSN_CD`: 01=정정, 02=취소 / 취소 시 `OVRS_ORD_UNPR`은 "0"

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "APBK0013",
  "msg1": "주문 전송 완료 되었습니다.",
  "output": {
    "KRX_FWDG_ORD_ORGNO": "01790",
    "ODNO": "0000004338",
    "ORD_TMD": "160710"
  }
}
```

---

## 3. 해외주식 잔고 (v1_해외주식-006)

### 사용 목적
해외주식 보유 잔고를 조회합니다. 종목별 평가손익, 수익률, 현재가 등 확인.

### 호출 방법

| 항목 | 값 |
|------|-----|
| Method | `GET` |
| URL | `/uapi/overseas-stock/v1/trading/inquire-balance` |
| 실전 TR_ID | `TTTS3012R` |
| 모의 TR_ID | `VTTS3012R` |

**Query Parameters**
```
CANO=810XXXXX
ACNT_PRDT_CD=01
OVRS_EXCG_CD=NASD
TR_CRCY_CD=USD
CTX_AREA_FK200=
CTX_AREA_NK200=
```

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "KIOK0510",
  "msg1": "조회가 완료되었습니다",
  "output1": [
    {
      "ovrs_pdno": "TSLA",
      "ovrs_item_name": "테슬라",
      "frcr_evlu_pfls_amt": "-3547254.185235",
      "evlu_pfls_rt": "-81.75",
      "pchs_avg_pric": "5832.2148",
      "ovrs_cblc_qty": "744",
      "ord_psbl_qty": "744",
      "now_pric2": "1064.400000",
      "tr_crcy_cd": "USD",
      "ovrs_excg_cd": "NASD"
    }
  ],
  "output2": {
    "frcr_pchs_amt1": "4339167.78523",
    "ovrs_tot_pfls": "-3547254.18524",
    "tot_pftrt": "-81.74964327"
  }
}
```

---

## 4. 해외주식 기간손익 (v1_해외주식-032)

### 사용 목적
특정 기간 동안의 해외주식 매매 손익을 조회합니다. (실전 전용, 모의투자 미지원)

### 호출 방법

| 항목 | 값 |
|------|-----|
| Method | `GET` |
| URL | `/uapi/overseas-stock/v1/trading/inquire-period-profit` |
| 실전 TR_ID | `TTTS3039R` |
| 모의 TR_ID | 미지원 |

**Query Parameters**
```
CANO=810XXXXX
ACNT_PRDT_CD=01
OVRS_EXCG_CD=NASD
NATN_CD=
CRCY_CD=USD
PDNO=
INQR_STRT_DT=20240101
INQR_END_DT=20241231
WCRC_FRCR_DVSN_CD=01
CTX_AREA_FK200=
CTX_AREA_NK200=
```

> `WCRC_FRCR_DVSN_CD`: 01=외화, 02=원화

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "...",
  "msg1": "...",
  "Output1": [
    {
      "trad_day": "20240315",
      "ovrs_pdno": "AAPL",
      "ovrs_item_name": "애플",
      "slcl_qty": "10",
      "pchs_avg_pric": "150.00",
      "frcr_pchs_amt1": "1500.00",
      "avg_sll_unpr": "180.00",
      "frcr_sll_amt_smtl1": "1800.00",
      "ovrs_rlzt_pfls_amt": "300.00",
      "pftrt": "20.00"
    }
  ],
  "Output2": {
    "stck_sll_amt_smtl": "...",
    "stck_buy_amt_smtl": "...",
    "ovrs_rlzt_pfls_tot_amt": "...",
    "tot_pftrt": "..."
  }
}
```

---

## 공통 Header 필수 항목

| Header | 설명 |
|--------|------|
| `authorization` | `Bearer {access_token}` |
| `appkey` | 발급받은 앱키 |
| `appsecret` | 발급받은 앱시크릿 |
| `tr_id` | 거래 ID (API별 상이) |
| `content-type` | `application/json; charset=utf-8` |

---

## 거래소 코드

| 코드 | 거래소 |
|------|--------|
| NASD | 나스닥 |
| NYSE | 뉴욕 |
| AMEX | 아멕스 |
| SEHK | 홍콩 |
| SHAA | 중국상해 |
| SZAA | 중국심천 |
| TKSE | 일본 |
| HASE | 베트남 하노이 |
| VNSE | 베트남 호치민 |
