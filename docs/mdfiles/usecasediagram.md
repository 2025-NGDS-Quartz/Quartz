@startuml
left to right direction
skinparam packageStyle rectangle
skinparam shadowing false
skinparam actorStyle awesome

title Quartz - 멀티에이전트 자동투자 플랫폼 유즈케이스 다이어그램

' ===== 외부 액터 =====
actor "Scheduler\n(정기 트리거)" as SCH
actor "한국투자증권 API" as KIS
actor "AWS S3" as S3
actor "OpenAI GPT" as GPT
actor "Gemini API\n(+ Google Search)" as GEMINI
actor "거시경제 API\n(ECOS/FRED)" as MACRO_API
actor "뉴스 소스\n(네이버/한경/매경)" as NEWS


rectangle "Quartz Platform (k3s)" as QZ {

  ' ===== 인증 에이전트 (8006) =====
  package "인증 에이전트" as AUTH_PKG {
    usecase "OAuth 토큰 발급/갱신" as UC_TOKEN
    usecase "토큰 제공\n(GET /result/auth-token)" as UC_TOKEN_PROVIDE
  }

  ' ===== 거시경제 분석 에이전트 (8001) =====
  package "거시경제 분석 에이전트" as MACRO_PKG {
    usecase "거시경제 데이터 수집\n(ECOS/FRED/WorldBank)" as UC_MACRO_COLLECT
    usecase "긍정/부정 보고서 생성\n(Gemini + Search Grounding)" as UC_MACRO_REPORT
    usecase "보고서 S3 업로드\n(12시간 주기)" as UC_MACRO_UPLOAD
  }

  ' ===== 거래종목 선택 에이전트 (8002) =====
  package "거래종목 선택 에이전트" as TICKER_PKG {
    usecase "뉴스 크롤링\n(네이버/한경/매경)" as UC_NEWS_CRAWL
    usecase "종목 매칭 및\nGPT 감성 분석" as UC_SENTIMENT
    usecase "후보 종목 선정\n(POST /api/candidates)" as UC_CANDIDATES
  }

  ' ===== 기술분석 에이전트 (8003) =====
  package "기술분석 에이전트" as TECH_PKG {
    usecase "가격 데이터 조회\n(일/주/월봉)" as UC_PRICE_FETCH
    usecase "기술지표 계산\n(RSI/MACD/BB/피보나치)" as UC_TECH_CALC
    usecase "분석 결과 제공\n(POST /result/analysis)" as UC_TECH_PROVIDE
  }

  ' ===== 포트폴리오 관리 에이전트 (8004) =====
  package "포트폴리오 관리 에이전트" as PM_PKG {
    usecase "포트폴리오 현황 조회\n(잔고/매수가능금액)" as UC_PORTFOLIO
    usecase "Universe 구성\n(보유종목 + 후보종목)" as UC_UNIVERSE
    usecase "GPT 의사결정\n(BUY/SELL/HOLD)" as UC_DECIDE
    usecase "규칙 기반 손절/익절\n(손실>5%, 수익>15%)" as UC_RULES
    usecase "거래 명령 전송\n(WebSocket)" as UC_ORDER_CMD
  }

  ' ===== 거래 에이전트 (8005) =====
  package "거래 에이전트" as TRADE_PKG {
    usecase "주문 명령 수신\n(WebSocket)" as UC_ORDER_RECV
    usecase "주문 실행\n(매수/매도)" as UC_ORDER_EXEC
    usecase "주문 정정/취소" as UC_ORDER_AMEND
    usecase "미체결 주문 관리\n(장 마감 전 취소)" as UC_ORDER_TRACK
  }

}


' ===== 스케줄러 트리거 =====
SCH --> UC_MACRO_COLLECT : 12시간 주기
SCH --> UC_NEWS_CRAWL : 12시간 주기
SCH --> UC_PORTFOLIO : 30분 주기\n(신규 매수)
SCH --> UC_RULES : 5~10분 주기\n(매도 재평가)


' ===== 거시경제 에이전트 연동 =====
UC_MACRO_COLLECT --> MACRO_API
UC_MACRO_COLLECT ..> UC_MACRO_REPORT : <<include>>
UC_MACRO_REPORT --> GEMINI
UC_MACRO_REPORT ..> UC_MACRO_UPLOAD : <<include>>
UC_MACRO_UPLOAD --> S3


' ===== 거래종목 선택 에이전트 연동 =====
UC_NEWS_CRAWL --> NEWS
UC_NEWS_CRAWL ..> UC_SENTIMENT : <<include>>
UC_SENTIMENT --> GPT
UC_SENTIMENT ..> UC_CANDIDATES : <<include>>
UC_CANDIDATES --> S3


' ===== 기술분석 에이전트 연동 =====
UC_PRICE_FETCH --> KIS
UC_PRICE_FETCH ..> UC_TECH_CALC : <<include>>
UC_TECH_CALC ..> UC_TECH_PROVIDE : <<include>>
UC_TECH_PROVIDE --> S3


' ===== 포트폴리오 관리 에이전트 흐름 =====
UC_PORTFOLIO --> KIS
UC_PORTFOLIO ..> UC_UNIVERSE : <<include>>
UC_UNIVERSE ..> UC_MACRO_UPLOAD : 거시경제\n보고서 조회
UC_UNIVERSE ..> UC_CANDIDATES : 후보 종목\n조회
UC_UNIVERSE ..> UC_TECH_PROVIDE : 기술분석\n요청
UC_UNIVERSE ..> UC_DECIDE : <<include>>
UC_DECIDE --> GPT
UC_DECIDE ..> UC_RULES : <<include>>
UC_RULES ..> UC_ORDER_CMD : <<include>>
UC_ORDER_CMD --> S3 : 의사결정\n로그 저장


' ===== 거래 에이전트 흐름 =====
UC_ORDER_CMD ..> UC_ORDER_RECV : WebSocket
UC_ORDER_RECV ..> UC_ORDER_EXEC : <<include>>
UC_ORDER_EXEC ..> UC_TOKEN_PROVIDE : 토큰 요청
UC_TOKEN_PROVIDE ..> UC_TOKEN : <<include>>
UC_TOKEN --> KIS
UC_ORDER_EXEC --> KIS
UC_ORDER_EXEC ..> UC_ORDER_AMEND : <<extend>>
UC_ORDER_EXEC ..> UC_ORDER_TRACK : <<extend>>
UC_ORDER_AMEND --> KIS
UC_ORDER_TRACK --> KIS

@enduml