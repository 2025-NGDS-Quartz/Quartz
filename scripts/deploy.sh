#!/bin/bash
# Quartz k8s 배포 스크립트

set -euo pipefail

NAMESPACE=quartz

echo "=============================================="
echo "  Quartz - 멀티에이전트 자동투자 플랫폼 배포"
echo "=============================================="
echo ""

echo "[1/3] Deploying with kustomize..."
kubectl apply -k k8s/

echo ""
echo "[2/3] Waiting for pods to be ready..."
# kustomization.yaml 에서 app.kubernetes.io/part-of=quartz 라벨을 달고 있음
kubectl wait --for=condition=ready pod -l app.kubernetes.io/part-of=quartz -n ${NAMESPACE} --timeout=300s || {
    echo "Warning: Some pods may not be ready yet. Check status manually."
}

echo ""
echo "[3/3] Deployment status"
kubectl get pods -n ${NAMESPACE}
echo ""
kubectl get svc -n ${NAMESPACE}
echo ""

echo "=============================================="
echo "  유용한 명령어"
echo "=============================================="
echo "로그 확인:"
echo "  kubectl logs -f deployment/frontend -n ${NAMESPACE}"
echo "  kubectl logs -f deployment/api-proxy -n ${NAMESPACE}"
echo "  kubectl logs -f deployment/macro-agent -n ${NAMESPACE}"
echo ""
echo "Pod 상태 상세 확인:" 
echo "  kubectl describe pod -l app=frontend -n ${NAMESPACE}"
echo ""
echo "프론트엔드 접속 (NodePort 30080):"
echo "  kubectl get svc frontend -n ${NAMESPACE}"
echo "  curl http://<node-ip>:30080"
echo ""
echo "전체 삭제:" 
echo "  kubectl delete -k k8s/"
echo ""