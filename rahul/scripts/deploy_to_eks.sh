#!/bin/bash
# Script to deploy RadStream Triton to EKS

set -e  # Exit on error

echo "=========================================="
echo "RadStream EKS Deployment Script"
echo "=========================================="
echo ""

# Step 1: Check kubectl is configured
echo "Step 1: Checking kubectl configuration..."
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo "❌ ERROR: kubectl is not configured!"
    echo "   Run: aws eks update-kubeconfig --name radstream-cluster --region us-east-1"
    exit 1
fi
echo "✅ kubectl is configured"
echo ""

# Step 2: Create namespace if it doesn't exist
echo "Step 2: Creating namespace..."
if kubectl get namespace radstream > /dev/null 2>&1; then
    echo "✅ Namespace 'radstream' already exists"
else
    kubectl create namespace radstream
    echo "✅ Created namespace 'radstream'"
fi
echo ""

# Step 3: Verify image exists in ECR
echo "Step 3: Verifying image in ECR..."
ECR_URI="222634400500.dkr.ecr.us-east-1.amazonaws.com/radstream-triton"
IMAGE_TAG="cpu"

if aws ecr describe-images --repository-name radstream-triton --image-ids imageTag=${IMAGE_TAG} --region us-east-1 > /dev/null 2>&1; then
    echo "✅ Image ${ECR_URI}:${IMAGE_TAG} found in ECR"
else
    echo "❌ ERROR: Image ${ECR_URI}:${IMAGE_TAG} not found in ECR!"
    echo "   Please build and push the image first:"
    echo "   bash rahul/scripts/build_and_push_container.sh"
    exit 1
fi
echo ""

# Step 4: Deploy to EKS
echo "Step 4: Deploying to EKS..."
kubectl apply -f mukul/inference/deploy_manifest.yaml

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Deployment failed!"
    exit 1
fi
echo "✅ Deployment manifest applied"
echo ""

# Step 5: Wait for deployment
echo "Step 5: Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/radstream-triton -n radstream

if [ $? -ne 0 ]; then
    echo "⚠️  WARNING: Deployment may not be ready yet"
    echo "   Check status with: kubectl get pods -n radstream"
else
    echo "✅ Deployment is ready"
fi
echo ""

# Step 6: Get service endpoint
echo "Step 6: Getting service endpoint..."
echo "Waiting for LoadBalancer to be provisioned (this may take 2-5 minutes)..."
kubectl get svc radstream-triton-service -n radstream

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "To check status:"
echo "  kubectl get pods -n radstream"
echo "  kubectl get svc -n radstream"
echo ""
echo "To get LoadBalancer URL:"
echo "  kubectl get svc radstream-triton-service -n radstream -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'"
echo ""
echo "To view logs:"
echo "  kubectl logs -f deployment/radstream-triton -n radstream"
echo ""

