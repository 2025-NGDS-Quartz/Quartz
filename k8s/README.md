# Quartz k3s 배포 가이드

이 문서는 Quartz 에이전트들을 k3s 클러스터에 배포하는 방법을 설명합니다.

## 사전 요구사항

- k3s 클러스터가 설치되어 있어야 합니다.
- `kubectl`이 클러스터에 연결되어 있어야 합니다.
- Docker 또는 containerd로 이미지를 빌드할 수 있어야 합니다.

## 디렉터리 구조

```
docker/
├── Dockerfile.technical   # 기술분석 에이전트 이미지
├── Dockerfile.trading     # 거래 에이전트 이미지
└── Dockerfile.portfolio   # 포트폴리오 관리 에이전트 이미지

k8s/
├── kustomization.yaml     # Kustomize 설정
├── namespace.yaml         # quartz 네임스페이스
├── technical-agent.yaml   # 기술분석 에이전트 Deployment + Service
├── trading-agent.yaml     # 거래 에이전트 Deployment + Service
└── portfolio-manager.yaml # 포트폴리오 관리 에이전트 Deployment
```

## 1. 이미지 빌드

프로젝트 루트에서 각 에이전트 이미지를 빌드합니다.

```bash
# 기술분석 에이전트
docker build -f docker/Dockerfile.technical -t quartz/technical-agent:latest .

# 거래 에이전트
docker build -f docker/Dockerfile.trading -t quartz/trading-agent:latest .

# 포트폴리오 관리 에이전트
docker build -f docker/Dockerfile.portfolio -t quartz/portfolio-manager:latest .
```

### k3s에서 로컬 이미지 사용

k3s는 기본적으로 containerd를 사용합니다. 로컬에서 빌드한 이미지를 k3s에서 사용하려면:

**방법 1: 이미지 내보내기/가져오기**

```bash
# Docker에서 이미지 내보내기
docker save quartz/technical-agent:latest | sudo k3s ctr images import -

# 모든 이미지 한 번에
docker save quartz/technical-agent:latest quartz/trading-agent:latest quartz/portfolio-manager:latest | sudo k3s ctr images import -
```

**방법 2: 로컬 레지스트리 사용**

```bash
# 로컬 레지스트리 실행
docker run -d -p 5000:5000 --name registry registry:2

# 이미지 태그 및 푸시
docker tag quartz/technical-agent:latest localhost:5000/quartz/technical-agent:latest
docker push localhost:5000/quartz/technical-agent:latest

# k8s 매니페스트에서 이미지 경로 수정 필요
```

## 2. 클러스터에 배포

### Kustomize 사용 (권장)

```bash
kubectl apply -k k8s/
```

### 개별 배포

```bash
# 네임스페이스 생성
kubectl apply -f k8s/namespace.yaml

# 에이전트 배포
kubectl apply -f k8s/technical-agent.yaml -n quartz
kubectl apply -f k8s/trading-agent.yaml -n quartz
kubectl apply -f k8s/portfolio-manager.yaml -n quartz
```

## 3. 배포 확인

```bash
# 파드 상태 확인
kubectl get pods -n quartz

# 서비스 확인
kubectl get svc -n quartz

# 로그 확인
kubectl logs -f deployment/technical-agent -n quartz
kubectl logs -f deployment/trading-agent -n quartz
kubectl logs -f deployment/portfolio-manager -n quartz
```

## 4. 에이전트 간 통신

클러스터 내부에서 에이전트들은 Kubernetes DNS를 통해 서로 통신합니다.

| 에이전트 | 클러스터 내부 주소 |
|----------|-------------------|
| Technical Agent | `http://technical-agent:8000` |
| Trading Agent | `http://trading-agent:8000` (HTTP), `ws://trading-agent:8000/ws/trade` (WebSocket) |

Portfolio Manager는 환경 변수로 이 주소들을 설정받습니다:

```yaml
env:
  - name: AGENT_HOSTS
    value: "http://technical-agent:8000"
  - name: TRADING_WS_URL
    value: "ws://trading-agent:8000/ws/trade"
```

## 5. 환경 변수 커스터마이징

각 에이전트의 환경 변수는 해당 YAML 파일의 `env` 섹션에서 수정할 수 있습니다.

### Technical Agent 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TECH_AGENT_TICKER` | `SPY` | 기본 티커 |
| `TECH_AGENT_MACD_FAST` | `14` | MACD 빠른 EMA |
| `TECH_AGENT_MACD_SLOW` | `28` | MACD 느린 EMA |
| `TECH_AGENT_MACD_SIGNAL` | `9` | MACD 시그널 |
| `TECH_AGENT_RSI_WINDOW` | `14` | RSI 윈도우 |
| `TECH_AGENT_BOLL_WINDOW` | `20` | 볼린저 밴드 윈도우 |
| `TECH_AGENT_BOLL_STD` | `2.0` | 볼린저 밴드 표준편차 |
| `TECH_AGENT_MA_TAIL` | `60` | 이동평균 tail |

### Portfolio Manager 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `AGENT_HOSTS` | - | 분석 에이전트 URL (쉼표 구분) |
| `TRADING_WS_URL` | - | 거래 에이전트 WebSocket URL |
| `POLL_INTERVAL_SECONDS` | `300` | 폴링 주기 (초) |
| `REQUEST_TIMEOUT` | `30` | HTTP 타임아웃 (초) |
| `REQUEST_MAX_RETRIES` | `3` | 최대 재시도 횟수 |
| `SIGNAL_THRESHOLD` | `0.1` | 매매 신호 임계값 |
| `DEFAULT_TICKER` | `SPY` | 기본 거래 티커 |

## 6. 스케일링

```bash
# 기술분석 에이전트 레플리카 수 조정
kubectl scale deployment/technical-agent --replicas=3 -n quartz
```

## 7. 삭제

```bash
# 전체 삭제
kubectl delete -k k8s/

# 또는 네임스페이스 삭제 (모든 리소스 함께 삭제)
kubectl delete namespace quartz
```

## 트러블슈팅

### 파드가 시작되지 않는 경우

```bash
# 파드 상태 상세 확인
kubectl describe pod <pod-name> -n quartz

# 이벤트 확인
kubectl get events -n quartz --sort-by='.lastTimestamp'
```

### 이미지를 찾을 수 없는 경우

- `imagePullPolicy: IfNotPresent`가 설정되어 있는지 확인
- k3s에 이미지가 올바르게 import 되었는지 확인:
  ```bash
  sudo k3s ctr images list | grep quartz
  ```

### 에이전트 간 통신 실패

```bash
# DNS 확인
kubectl run -it --rm debug --image=busybox -n quartz -- nslookup technical-agent

# 연결 테스트
kubectl run -it --rm debug --image=curlimages/curl -n quartz -- curl http://technical-agent:8000/docs
```

