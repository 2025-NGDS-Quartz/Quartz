#!/bin/bash
# Quartz k8s 배포 스크립트

set -e

echo "=============================================="
echo "  Quartz - 멀티에이전트 자동투자 플랫폼 배포"
echo "=============================================="
echo ""

# Kustomize 사용하여 배포
echo "[1/3] Deploying to Kubernetes..."
kubectl apply -k k8s/

echo ""
echo "[2/3] Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/part-of=quartz -n quartz --timeout=180s || {
    echo "Warning: Some pods may not be ready yet. Check status manually."
}

echo ""
echo "[3/3] Deployment complete!"
echo ""
echo "=============================================="
echo "  배포 상태 확인"
echo "=============================================="
echo ""
kubectl get pods -n quartz
echo ""
kubectl get svc -n quartz
echo ""

echo "=============================================="
echo "  프론트엔드 접속 방법"
echo "=============================================="
echo ""
echo "방법 1: 포트 포워딩 (로컬 테스트)"
echo "  kubectl port-forward svc/frontend 8080:80 -n quartz"
echo "  → 브라우저에서 http://localhost:8080 접속"
echo ""
echo "방법 2: Ingress 확인 (외부 접속)"
echo "  kubectl get ingress -n quartz"
echo ""
echo "=============================================="
echo "  유용한 명령어"
echo "=============================================="
echo ""
echo "로그 확인:"
echo "  kubectl logs -f deployment/portfolio-manager -n quartz"
echo "  kubectl logs -f deployment/frontend -n quartz"
echo "  kubectl logs -f deployment/api-proxy -n quartz"
echo ""
echo "Pod 상태 상세 확인:"
echo "  kubectl describe pod -l app=frontend -n quartz"
echo ""
echo "서비스 삭제:"
echo "  kubectl delete -k k8s/"
echo ""

