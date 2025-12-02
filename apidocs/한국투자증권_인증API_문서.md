# 한국투자증권 OpenAPI 인증 API 문서

## 1. 접근토큰발급 (인증-001)

### 사용목적
본인 계좌에 필요한 인증 절차로, 접근토큰을 발급받아 OpenAPI를 활용할 수 있습니다. 토큰 유효기간은 24시간이며, 6시간 이내 재호출 시 기존 토큰을 반환합니다.

### 호출방법

| 항목 | 값 |
|------|-----|
| Method | `POST` |
| 실전 URL | `https://openapi.koreainvestment.com:9443/oauth2/tokenP` |
| 모의 URL | `https://openapivts.koreainvestment.com:29443/oauth2/tokenP` |

**Request Body**
```json
{
  "grant_type": "client_credentials",
  "appkey": "발급받은_앱키",
  "appsecret": "발급받은_앱시크릿"
}
```

### Response 형식

```json
{
  "access_token": "eyJ0eXAiOi...",
  "access_token_token_expired": "2023-12-22 08:16:59",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

| 필드 | 설명 |
|------|------|
| access_token | API 호출 시 사용할 접근토큰 |
| token_type | 토큰 유형 (`Bearer`) |
| expires_in | 유효기간 (초) |
| access_token_token_expired | 유효기간 (일시) |

---

## 2. 접근토큰폐기 (인증-002)

### 사용목적
부여받은 접근토큰을 더 이상 활용하지 않을 때 사용합니다.

### 호출방법

| 항목 | 값 |
|------|-----|
| Method | `POST` |
| 실전 URL | `https://openapi.koreainvestment.com:9443/oauth2/revokeP` |
| 모의 URL | `https://openapivts.koreainvestment.com:29443/oauth2/revokeP` |

**Request Body**
```json
{
  "appkey": "발급받은_앱키",
  "appsecret": "발급받은_앱시크릿",
  "token": "폐기할_접근토큰"
}
```

### Response 형식

```json
{
  "code": 200,
  "message": "접근토큰 폐기에 성공하였습니다"
}
```

| 필드 | 설명 |
|------|------|
| code | HTTP 응답코드 |
| message | 응답메세지 |
