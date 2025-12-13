# Quartz Dashboard

Quartz 멀티에이전트 자동투자 플랫폼의 웹 프론트엔드 대시보드입니다.

## 기능

- **대시보드**: 에이전트 상태 모니터링, 포트폴리오 요약, 후보 종목 미리보기
- **포트폴리오**: 현재 보유 종목, 평가금액, 수익률 상세 조회
- **후보 종목**: 뉴스 감성 분석 기반 매수 후보 종목 리스트
- **기술 분석**: 종목별 RSI, MACD, 볼린저밴드, 피보나치 분석

## 기술 스택

- **Frontend**: React 18 + TypeScript + Vite
- **Styling**: TailwindCSS
- **Charts**: Recharts
- **State Management**: TanStack React Query
- **API Proxy**: FastAPI

## 개발 환경 실행

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

프론트엔드가 http://localhost:3000 에서 실행됩니다.

### API 프록시 (개발 시)

```bash
cd frontend/api-proxy
pip install -r requirements.txt
python main.py
```

API 프록시가 http://localhost:8080 에서 실행됩니다.

## Docker 빌드

```bash
# 프론트엔드
docker build -f frontend/Dockerfile -t quartz/frontend:latest frontend/

# API 프록시
docker build -f frontend/api-proxy/Dockerfile -t quartz/api-proxy:latest frontend/api-proxy/
```

## k3s 배포

프론트엔드와 API 프록시는 `k8s/frontend.yaml`에 정의되어 있습니다.

```bash
# 전체 서비스 배포 (프론트엔드 포함)
kubectl apply -k k8s/

# 프론트엔드만 배포
kubectl apply -f k8s/frontend.yaml
```

## 환경 변수

API 프록시는 다음 환경 변수를 사용합니다 (ConfigMap에서 제공):

- `AUTH_AGENT_URL`: 인증 에이전트 URL
- `MACRO_AGENT_URL`: 거시경제 분석 에이전트 URL
- `TICKER_SELECTOR_URL`: 거래종목 선택 에이전트 URL
- `TECHNICAL_AGENT_URL`: 기술분석 에이전트 URL
- `PORTFOLIO_MANAGER_URL`: 포트폴리오 관리 에이전트 URL
- `TRADING_AGENT_URL`: 거래 에이전트 URL

## 접속 방법

k3s에 배포 후 Ingress를 통해 접속할 수 있습니다.

```bash
# 포트 포워딩으로 로컬 테스트
kubectl port-forward svc/frontend 8080:80 -n quartz

# 브라우저에서 http://localhost:8080 접속
```

## 디렉토리 구조

```
frontend/
├── api-proxy/           # FastAPI 프록시 서버
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── public/              # 정적 파일
│   └── quartz.svg
├── src/
│   ├── api/            # API 클라이언트
│   ├── components/     # React 컴포넌트
│   ├── types/          # TypeScript 타입 정의
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── Dockerfile          # 프론트엔드 Docker 이미지
├── nginx.conf          # Nginx 설정
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## 주요 엔드포인트 (API 프록시)

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/api/health/agents` | GET | 모든 에이전트 헬스체크 |
| `/api/portfolio` | GET | 포트폴리오 현황 조회 |
| `/api/candidates` | POST | 후보 종목 조회 |
| `/api/technical-analysis` | POST | 기술적 분석 조회 |
| `/api/token-status` | GET | 인증 토큰 상태 |
| `/api/macro-summary` | GET | 거시경제 요약 |
| `/api/decision` | POST | 수동 매매 결정 트리거 |
