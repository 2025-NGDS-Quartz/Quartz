#!/bin/bash
# Quartz Docker 이미지 빌드 스크립트

set -e

REGISTRY=${REGISTRY:-"quartz"}
TAG=${TAG:-"latest"}
IMPORT_TO_K3S=${IMPORT_TO_K3S:-"true"}

echo "=============================================="
echo "  Quartz Docker 이미지 빌드"
echo "=============================================="
echo ""

# 이미지 목록
IMAGES=(
    "auth-agent:agents/authAgent/Dockerfile:."
    "macro-agent:agents/macroAnalysisAgent/Dockerfile:."
    "ticker-selector:agents/stockSelectionAgent/Dockerfile:."
    "technical-agent:agents/technicalAgent/Dockerfile:."
    "trading-agent:agents/tradingAgent/Dockerfile:."
    "portfolio-manager:agents/portfolioManager/Dockerfile:."
    "frontend:frontend/Dockerfile:frontend/"
    "api-proxy:frontend/api-proxy/Dockerfile:frontend/api-proxy/"
)

TOTAL=${#IMAGES[@]}
COUNT=0

for IMAGE_INFO in "${IMAGES[@]}"; do
    IFS=':' read -r NAME DOCKERFILE CONTEXT <<< "$IMAGE_INFO"
    COUNT=$((COUNT + 1))
    
    echo "[${COUNT}/${TOTAL}] Building ${NAME}..."
    docker build -f ${DOCKERFILE} -t ${REGISTRY}/${NAME}:${TAG} ${CONTEXT}
done

echo ""
echo "All images built successfully!"

# k3s에 이미지 import (k3s가 설치된 경우)
if [ "$IMPORT_TO_K3S" = "true" ] && command -v k3s &> /dev/null; then
    echo ""
    echo "=============================================="
    echo "  k3s containerd로 이미지 import"
    echo "=============================================="
    echo ""
    
    for IMAGE_INFO in "${IMAGES[@]}"; do
        IFS=':' read -r NAME DOCKERFILE CONTEXT <<< "$IMAGE_INFO"
        FULL_IMAGE="${REGISTRY}/${NAME}:${TAG}"
        
        echo "Importing ${FULL_IMAGE} to k3s..."
        docker save ${FULL_IMAGE} | sudo k3s ctr images import -
    done
    
    echo ""
    echo "All images imported to k3s!"
    echo ""
    echo "k3s 이미지 확인:"
    echo "  sudo k3s ctr images list | grep quartz"
else
    echo ""
    echo "=============================================="
    echo "  레지스트리에 푸시하려면:"
    echo "=============================================="
    echo ""
    for IMAGE_INFO in "${IMAGES[@]}"; do
        IFS=':' read -r NAME DOCKERFILE CONTEXT <<< "$IMAGE_INFO"
        echo "  docker push ${REGISTRY}/${NAME}:${TAG}"
    done
    echo ""
    echo "k3s에 로컬 이미지 import하려면:"
    echo "  IMPORT_TO_K3S=true ./scripts/build_images.sh"
fi

