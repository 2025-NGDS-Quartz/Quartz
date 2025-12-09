# Portfolio Manager Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY agents/portfolioManager/ .

# 포트 노출
EXPOSE 8004

# 실행
CMD ["python", "main.py"]

