#!/bin/bash
# Quartz Docker 이미지 빌드 스크립트
# - 모든 에이전트 / 프론트엔드 / api-proxy 이미지를 quartz/<name>:latest 로 빌드
# - 필요 시 k3s containerd 로 바로 import

set -euo pipefail

REGISTRY=${REGISTRY:-"quartz"}
TAG=${TAG:-"latest"}
IMPORT_TO_K3S=${IMPORT_TO_K3S:-"true"}   # k3s 사용 시 true 유지
NO_CACHE=${NO_CACHE:-"false"}            # 캐시 삭제하려면 NO_CACHE=true

export DOCKER_BUILDKIT=1

echo "=============================================="
echo "  Quartz Docker 이미지 빌드"
echo "  REGISTRY=${REGISTRY}, TAG=${TAG}, NO_CACHE=${NO_CACHE}"
echo "=============================================="
echo ""

# 이미지 목록 (k8s/*.yaml 과 반드시 일치)
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
BUILD_OPTS=()
[ "${NO_CACHE}" = "true" ] && BUILD_OPTS+=(--no-cache --pull)

for IMAGE_INFO in "${IMAGES[@]}"; do
    IFS=':' read -r NAME DOCKERFILE CONTEXT <<< "${IMAGE_INFO}"
    COUNT=$((COUNT + 1))
    FULL_IMAGE="${REGISTRY}/${NAME}:${TAG}"

    echo "[${COUNT}/${TOTAL}] Building ${FULL_IMAGE} ..."
    docker build "${BUILD_OPTS[@]}" -f "${DOCKERFILE}" -t "${FULL_IMAGE}" "${CONTEXT}"
done

echo ""
echo "All images built successfully!"

# k3s에 이미지 import (k3s가 설치된 경우)
if [ "${IMPORT_TO_K3S}" = "true" ] && command -v k3s &> /dev/null; then
    echo ""
    echo "=============================================="
    echo "  k3s containerd로 이미지 import"
    echo "=============================================="
    echo ""
    
    for IMAGE_INFO in "${IMAGES[@]}"; do
        IFS=':' read -r NAME DOCKERFILE CONTEXT <<< "${IMAGE_INFO}"
        FULL_IMAGE="${REGISTRY}/${NAME}:${TAG}"
        
        echo "Importing ${FULL_IMAGE} to k3s..."
        docker save "${FULL_IMAGE}" | sudo k3s ctr images import -
    done
    
    echo ""
    echo "All images imported to k3s!"
    echo "k3s 이미지 확인: sudo k3s ctr images list | grep ${REGISTRY}"
else
    echo ""
    echo "=============================================="
    echo "  레지스트리에 푸시하려면:"
    echo "=============================================="
    echo ""
    for IMAGE_INFO in "${IMAGES[@]}"; do
        IFS=':' read -r NAME DOCKERFILE CONTEXT <<< "${IMAGE_INFO}"
        echo "  docker push ${REGISTRY}/${NAME}:${TAG}"
    done
    echo ""
    echo "k3s에 로컬 이미지 import하려면:"
    echo "  IMPORT_TO_K3S=true ./scripts/build_images.sh"
fi
