# Quartz k8s 배포 가이드

## 사전 요구사항

- k3s 또는 Kubernetes 클러스터
- kubectl 설치 및 클러스터 연결
- Docker 이미지 빌드 환경

## 배포 순서

### 1. Docker 이미지 빌드

프로젝트 루트 디렉토리에서 실행:

```bash
# 빌드 스크립트 사용 (권장)
./scripts/build_images.sh

# 또는 개별 빌드

# Auth Agent
docker build -f agents/authAgent/Dockerfile -t quartz/auth-agent:latest .

# Macro Agent (C++ + Python, 빌드 시간 오래 걸림)
docker build -f agents/macroAnalysisAgent/Dockerfile -t quartz/macro-agent:latest .

# Ticker Selector
docker build -f agents/stockSelectionAgent/Dockerfile -t quartz/ticker-selector:latest .

# Technical Agent
docker build -f agents/technicalAgent/Dockerfile -t quartz/technical-agent:latest .

# Trading Agent
docker build -f agents/tradingAgent/Dockerfile -t quartz/trading-agent:latest .

# Portfolio Manager
docker build -f agents/portfolioManager/Dockerfile -t quartz/portfolio-manager:latest .
```

### 2. Secret 설정

`k8s/secret.yaml` 파일의 값을 실제 값으로 대체:

```bash
# base64 인코딩
echo -n "your_app_key" | base64
echo -n "your_app_secret" | base64
# ... 나머지 값들도 동일하게
```

### 3. k8s 배포

```bash
# Kustomize를 사용한 배포 (권장)
kubectl apply -k k8s/

# 또는 개별 배포
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/auth-agent.yaml
kubectl apply -f k8s/macro-agent.yaml
kubectl apply -f k8s/ticker-selector.yaml
kubectl apply -f k8s/technical-agent.yaml
kubectl apply -f k8s/trading-agent.yaml
kubectl apply -f k8s/portfolio-manager.yaml
```

### 4. 배포 확인

```bash
# Pod 상태 확인
kubectl get pods -n quartz

# Service 확인
kubectl get svc -n quartz

# 로그 확인
kubectl logs -f deployment/auth-agent -n quartz
kubectl logs -f deployment/macro-agent -n quartz
kubectl logs -f deployment/ticker-selector -n quartz
kubectl logs -f deployment/technical-agent -n quartz
kubectl logs -f deployment/trading-agent -n quartz
kubectl logs -f deployment/portfolio-manager -n quartz
```

## 에이전트 서비스 정보

| 에이전트 | 포트 | k3s Service | 내부 DNS |
|---------|------|-------------|----------|
| 거시경제 분석 | 8001 | macro-agent | macro-agent.quartz.svc.cluster.local |
| 거래종목 선택 | 8002 | ticker-selector | ticker-selector.quartz.svc.cluster.local |
| 기술분석 | 8003 | technical-agent | technical-agent.quartz.svc.cluster.local |
| 포트폴리오 관리 | 8004 | portfolio-manager | portfolio-manager.quartz.svc.cluster.local |
| 거래 | 8005 | trading-agent | trading-agent.quartz.svc.cluster.local |
| 인증관리 | 8006 | auth-agent | auth-agent.quartz.svc.cluster.local |

## API 엔드포인트

### 거시경제 분석 에이전트 (포트 8001)
- `GET /result/analysis` - 거시경제 분석 결과 (S3에서 조회)
- `POST /refresh` - 캐시 수동 갱신
- `POST /run-analysis` - C++ 분석 수동 실행
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

### 거래종목 선택 에이전트 (포트 8002)
- `POST /api/candidates` - 후보 종목 리스트 조회
- `GET /api/statistics` - 전체 통계
- `GET /api/candidates/{ticker}` - 특정 종목 상세
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

### 기술분석 에이전트 (포트 8003)
- `POST /result/analysis` - 종목 기술적 분석
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

### 포트폴리오 관리 에이전트 (포트 8004)
- `GET /api/portfolio` - 포트폴리오 현황 조회
- `POST /api/decision` - 수동 매매 결정 트리거
- `GET /api/buyable` - 매수가능금액 조회
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

### 거래 에이전트 (포트 8005)
- `WebSocket /ws/orders` - 주문 WebSocket
- `POST /api/order` - HTTP 주문 (테스트용)
- `GET /api/cancelable-orders` - 정정취소 가능 주문 조회
- `POST /api/cancel-order` - 주문 취소
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

### 인증관리 에이전트 (포트 8006)
- `GET /result/auth-token` - 인증 토큰 조회
- `GET /result/auth-token/status` - 토큰 상태 확인
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

## 트러블슈팅

### Pod이 시작되지 않는 경우
```bash
kubectl describe pod <pod-name> -n quartz
kubectl logs <pod-name> -n quartz
```

### 토큰 발급 실패
- Secret의 HANSEC_INVESTMENT_APP_KEY와 HANSEC_INVESTMENT_APP_SECRET_KEY가 올바르게 설정되었는지 확인
- 한국투자증권 API 서버 접근 가능 여부 확인

### 에이전트 간 통신 오류
- Service가 올바르게 생성되었는지 확인
- Pod간 네트워크 정책 확인

