# Stock Selection Agent Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 설치 (크롤링용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치 (pip 업그레이드 포함)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY agents/stockSelectionAgent/ .

# 데이터 디렉토리 생성
RUN mkdir -p data/news_raw data/processed data/logs

# 포트 노출 (architecture.md: ticker-selector 8002)
EXPOSE 8002

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health/live || exit 1

# 실행 (API 서버 + 스케줄러)
CMD ["python", "run.py"]

