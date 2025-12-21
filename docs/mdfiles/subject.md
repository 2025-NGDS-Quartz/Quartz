# QuartzOpsBench: 운영형 금융 에이전트 평가 벤치마크

## 논문 가제
**QuartzOpsBench: Operational, Reproducible, and Secure Evaluation of Multi-Agent Financial Decision Pipelines**

---

## 왜 지금 좋은가

- **FinBen**이 "태스크 폭"을 넓힌 종합 벤치마크라면 (42 datasets/24 tasks) [NeurIPS Proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/file/5e8fd5d6b77c0236c7f02c9d0e8beb66-Paper-Datasets_and_Benchmarks.pdf)
- **InvestorBench**는 "금융 의사결정 환경 + 에이전트 성능(수익률/리스크 지표)"을 표준화하려는 흐름 [ACL Anthology](https://aclanthology.org/2024.findings-acl.802/)
- 최근엔 아예 **주문 레벨(슬리피지/지연/호가 미시구조)**까지 포함한 시뮬레이터(StockSim)도 나왔음 [Emergent Mind](https://www.emergentmind.com/papers/2501.00491)

**Quartz는 여기서 한 발 더 나가서** *"에이전트 파이프라인을 쿠버네티스/마이크로서비스로 운영했을 때"*의 성능을 논문으로 만들기 좋음.

---

## 벤치마크(오픈소스) 목표

### (A) 평가 대상
"모델 1개"가 아니라 **"에이전트 팀(거시/뉴스/TA/포트폴리오/주문)"**

### (B) 공개물(필수)

#### 1. quartzopsbench 실행 프레임워크
- 컨테이너 기반(도커)으로 재현 가능한 실행(seed/버전 고정)
- AgentBench처럼 "환경+평가 루프" 형태를 차용 [GitHub](https://github.com/THUDM/AgentBench)

#### 2. Episode Dataset (경량)
**"하루 1회 의사결정" 단위의 에피소드:**
- **입력 스냅샷**: 거시지표/뉴스 묶음/OHLCV/기술지표
- **출력**: 선정 종목/주문 계획/리스크 제한/근거
- **결과**: 백테스트 성과 + 실행 실패/지연/비용 로그

#### 3. Trace Schema
에이전트별 근거 링크/지표 값/프롬프트 버전/툴콜 로그를 표준 JSON으로 남기는 규격  
**(이게 논문 contribution이 됨)**

### (C) 평가 지표(핵심 차별점)

#### 1. 투자 성과 (InvestorBench류)
- 누적수익, Sharpe, MDD, 거래회전율 등 [ACL Anthology](https://aclanthology.org/2024.findings-acl.802/)

#### 2. 운영 지표 (Quartz만의 축)
- 결정을 내리기까지 **latency**
- **실패율/재시도율**
- **비용**(토큰/₩)
- **rate-limit 내성**

#### 3. 안전/정합성 지표
- **정책 위반**: 포지션 한도/손절 규칙 위반 등 빈도
- **"근거-결론 정합성"**: 근거가 없는 주장 비율

---

## 논문에서 주장할 "핵심 기여(Contribution)"

1. 금융 LLM 평가를 **'AgentOps/LLMOps' 관점**으로 확장  
   (성능+운영+안전)

2. **리플레이 가능한 멀티에이전트 트레이스 데이터셋** + 평가 스키마 공개

3. 단일 LLM vs 역할 분리 멀티에이전트 vs 규칙기반(베이스라인) 비교로,  
   **"구조적 설계가 성능/안정성에 주는 영향"**을 실증


## 최종 결과물
결과물로 LLM provider 만 교체하면 복잡한 의사결정과정인 "에이전트 간 정보 수집 및 공유를 통한 투자"의 벤치마크 결과를 만들어주는 오픈소스 벤치마크 측정 툴과, 이에 대한 연구 논문을 학회에 제출하는 것을 목표로 함.