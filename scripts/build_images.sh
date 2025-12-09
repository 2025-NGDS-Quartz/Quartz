#!/bin/bash
# Quartz Docker 이미지 빌드 스크립트

set -e

REGISTRY=${REGISTRY:-"quartz"}
TAG=${TAG:-"latest"}

echo "Building Quartz agent images..."

# Auth Agent
echo "Building auth-agent..."
docker build -f agents/authAgent/Dockerfile -t ${REGISTRY}/auth-agent:${TAG} .

# Macro Agent (C++ + Python)
echo "Building macro-agent..."
docker build -f agents/macroAnalysisAgent/Dockerfile -t ${REGISTRY}/macro-agent:${TAG} .

# Ticker Selector
echo "Building ticker-selector..."
docker build -f agents/stockSelectionAgent/Dockerfile -t ${REGISTRY}/ticker-selector:${TAG} .

# Technical Agent
echo "Building technical-agent..."
docker build -f agents/technicalAgent/Dockerfile -t ${REGISTRY}/technical-agent:${TAG} .

# Trading Agent
echo "Building trading-agent..."
docker build -f agents/tradingAgent/Dockerfile -t ${REGISTRY}/trading-agent:${TAG} .

# Portfolio Manager
echo "Building portfolio-manager..."
docker build -f agents/portfolioManager/Dockerfile -t ${REGISTRY}/portfolio-manager:${TAG} .

echo "All images built successfully!"
echo ""
echo "To push images to registry:"
echo "  docker push ${REGISTRY}/auth-agent:${TAG}"
echo "  docker push ${REGISTRY}/macro-agent:${TAG}"
echo "  docker push ${REGISTRY}/ticker-selector:${TAG}"
echo "  docker push ${REGISTRY}/technical-agent:${TAG}"
echo "  docker push ${REGISTRY}/trading-agent:${TAG}"
echo "  docker push ${REGISTRY}/portfolio-manager:${TAG}"

