#!/bin/bash
# Quartz k8s 배포 스크립트

set -e

echo "Deploying Quartz to Kubernetes..."

# Kustomize 사용
kubectl apply -k k8s/

echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/part-of=quartz -n quartz --timeout=120s

echo "Deployment complete!"
echo ""
echo "Check status:"
echo "  kubectl get pods -n quartz"
echo "  kubectl get svc -n quartz"

