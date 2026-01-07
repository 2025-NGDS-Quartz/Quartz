# Macro Analysis Agent Dockerfile
# Python 기반 거시경제 분석 에이전트

FROM python:3.12-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 한국 시간 적용
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY agents/macroAnalysisAgent/ .

# 포트 노출 (architecture.md: macro-agent 8001)
EXPOSE 8001

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health/live || exit 1

# Python API 서버 실행
CMD ["python", "api_server.py"]

