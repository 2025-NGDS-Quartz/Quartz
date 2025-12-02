# 한국투자증권 국내주식 시세 API

## 1. 국내주식기간별시세 (일/주/월/년)

### 사용목적
특정 종목의 일/주/월/년 단위 OHLCV 차트 데이터 조회 (최대 100건)

### 호출방법
```
GET /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
```

| 구분 | 값 |
|------|-----|
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |
| TR_ID | `FHKST03010100` |

**Request Query Parameters**

| Parameter | 설명 | 필수 |
|-----------|------|------|
| FID_COND_MRKT_DIV_CODE | 시장구분 (J:KRX, NX:NXT, UN:통합) | Y |
| FID_INPUT_ISCD | 종목코드 (예: 005930) | Y |
| FID_INPUT_DATE_1 | 조회 시작일자 (YYYYMMDD) | Y |
| FID_INPUT_DATE_2 | 조회 종료일자 (YYYYMMDD) | Y |
| FID_PERIOD_DIV_CODE | 기간구분 (D:일봉, W:주봉, M:월봉, Y:년봉) | Y |
| FID_ORG_ADJ_PRC | 수정주가 여부 (0:수정주가, 1:원주가) | Y |

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "MCA00000",
  "output1": {
    "stck_prpr": "112000",      // 현재가
    "prdy_vrss": "1000",        // 전일대비
    "prdy_ctrt": "0.90",        // 전일대비율
    "hts_kor_isnm": "SK하이닉스" // 종목명
  },
  "output2": [
    {
      "stck_bsop_date": "20220509", // 영업일자
      "stck_oprc": "107000",        // 시가
      "stck_hgpr": "109000",        // 고가
      "stck_lwpr": "106500",        // 저가
      "stck_clpr": "107500",        // 종가
      "acml_vol": "2203472",        // 거래량
      "acml_tr_pbmn": "237914727500" // 거래대금
    }
  ]
}
```

---

## 2. 주식현재가 일자별

### 사용목적
특정 종목의 최근 일별/주별/월별 시세 조회 (최근 30일/주/월 제한)

### 호출방법
```
GET /uapi/domestic-stock/v1/quotations/inquire-daily-price
```

| 구분 | 값 |
|------|-----|
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |
| TR_ID | `FHKST01010400` |

**Request Query Parameters**

| Parameter | 설명 | 필수 |
|-----------|------|------|
| FID_COND_MRKT_DIV_CODE | 시장구분 (J:KRX, NX:NXT, UN:통합) | Y |
| FID_INPUT_ISCD | 종목코드 (예: 005930) | Y |
| FID_PERIOD_DIV_CODE | 기간구분 (D:일, W:주, M:월) | Y |
| FID_ORG_ADJ_PRC | 수정주가 반영 (0:미반영, 1:반영) | Y |

### Response 형식
```json
{
  "rt_cd": "0",
  "msg_cd": "MCA00000",
  "msg1": "정상처리 되었습니다!",
  "output": [
    {
      "stck_bsop_date": "20220111",  // 영업일자
      "stck_oprc": "125500",         // 시가
      "stck_hgpr": "128500",         // 고가
      "stck_lwpr": "124500",         // 저가
      "stck_clpr": "128000",         // 종가
      "acml_vol": "3908418",         // 거래량
      "prdy_vrss": "3500",           // 전일대비
      "prdy_vrss_sign": "2",         // 대비부호
      "prdy_ctrt": "2.81",           // 전일대비율
      "hts_frgn_ehrt": "49.39",      // 외국인소진율
      "frgn_ntby_qty": "0"           // 외국인순매수
    }
  ]
}
```

---

## 공통 Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| content-type | `application/json; charset=utf-8` | Y |
| authorization | Bearer {access_token} | Y |
| appkey | 발급받은 앱키 | Y |
| appsecret | 발급받은 앱시크릿 | Y |
| tr_id | 거래 ID | Y |
| custtype | 고객타입 (P:개인, B:법인) | Y |
