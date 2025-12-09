# Macro Analysis Agent Dockerfile
# C++ 분석 프로그램 + Python API 서버

FROM ubuntu:22.04

# 타임존 선택 등의 멈춤현상 방지용
ENV DEBIAN_FRONTEND=noninteractive

# C++ 빌드 도구 및 의존성 설치
RUN apt-get update && apt-get install -y \
    g++ \
    cmake \
    git \
    libcurl4-openssl-dev \
    libssl-dev \
    nlohmann-json3-dev \
    zlib1g-dev \
    ca-certificates \
    tzdata \
    # Python 3.12 설치를 위한 PPA
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 한국 시간 적용
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# AWS SDK for C++ 빌드 및 설치
WORKDIR /tmp
RUN git clone --recurse-submodules https://github.com/aws/aws-sdk-cpp.git
WORKDIR /tmp/aws-sdk-cpp
RUN mkdir build && cd build && \
    cmake .. -DBUILD_ONLY="s3" \
             -DCMAKE_BUILD_TYPE=Release \
             -DBUILD_SHARED_LIBS=ON \
             -DENABLE_TESTING=OFF \
             -DAUTORUN_UNIT_TESTS=OFF && \
    make -j $(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/aws-sdk-cpp

ENV LD_LIBRARY_PATH=/usr/local/lib

WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt

# C++ 소스 코드 복사 및 빌드
COPY agents/macroAnalysisAgent/main.cpp .
COPY agents/macroAnalysisAgent/S3Uploader.cpp .
COPY agents/macroAnalysisAgent/S3Uploader.h .

RUN g++ main.cpp S3Uploader.cpp -o macro_analysis \
    -L/usr/local/lib \
    -lcurl -laws-cpp-sdk-s3 -laws-cpp-sdk-core \
    -lssl -lcrypto -lz -lpthread \
    -Wl,-rpath,/usr/local/lib

# Python API 서버 복사
COPY agents/macroAnalysisAgent/api_server.py .

# 포트 노출 (architecture.md: macro-agent 8001)
EXPOSE 8001

# Python API 서버 실행 (C++ 프로그램은 API 서버에서 주기적으로 호출)
CMD ["python3.12", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8001"]

