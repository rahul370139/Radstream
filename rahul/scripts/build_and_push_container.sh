#!/bin/bash
# Script to build and push RadStream Triton container to ECR

set -e  # Exit on error

ECR_URI="222634400500.dkr.ecr.us-east-1.amazonaws.com/radstream-triton"
REGION="us-east-1"
IMAGE_NAME="radstream-triton"
IMAGE_TAG="latest"

echo "=========================================="
echo "RadStream Container Build & Push Script"
echo "=========================================="
echo ""

# Step 1: Check Docker is running
echo "Step 1: Checking Docker daemon..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ ERROR: Docker daemon is not running!"
    echo "   Please start Docker Desktop and try again."
    exit 1
fi
echo "✅ Docker daemon is running"
echo ""

# Step 2: Login to ECR
echo "Step 2: Logging into ECR..."
aws ecr get-login-password --region ${REGION} | \
    docker login --username AWS --password-stdin ${ECR_URI}
echo "✅ Logged into ECR"
echo ""

# Step 3: Build Docker image
echo "Step 3: Building Docker image..."
echo "   Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "   Dockerfile: mukul/inference/Dockerfile.triton"
echo "   This may take 30-60 minutes depending on network speed..."
echo ""

cd "$(dirname "$0")/../.."  # Go to RadStream root directory

docker build \
    -t ${IMAGE_NAME}:${IMAGE_TAG} \
    -f mukul/inference/Dockerfile.triton \
    mukul/inference/

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Docker build failed!"
    exit 1
fi
echo "✅ Docker image built successfully"
echo ""

# Step 4: Tag image for ECR
echo "Step 4: Tagging image for ECR..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}
echo "✅ Image tagged: ${ECR_URI}:${IMAGE_TAG}"
echo ""

# Step 5: Push to ECR
echo "Step 5: Pushing image to ECR..."
echo "   This may take 10-30 minutes depending on image size and network speed..."
echo ""

docker push ${ECR_URI}:${IMAGE_TAG}

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Docker push failed!"
    exit 1
fi
echo "✅ Image pushed successfully to ECR"
echo ""

# Step 6: Verify image in ECR
echo "Step 6: Verifying image in ECR..."
aws ecr describe-images \
    --repository-name radstream-triton \
    --region ${REGION} \
    --image-ids imageTag=${IMAGE_TAG} \
    --query 'imageDetails[0].{Tags:imageTags, PushedAt:imagePushedAt, Size:imageSizeInBytes}' \
    --output table

echo ""
echo "=========================================="
echo "✅ SUCCESS: Container built and pushed!"
echo "=========================================="
echo ""
echo "ECR URI: ${ECR_URI}:${IMAGE_TAG}"
echo ""
echo "Next steps:"
echo "1. Mukul can now deploy this container to EKS"
echo "2. Update deploy_manifest.yaml with ECR URI: ${ECR_URI}:${IMAGE_TAG}"
echo "3. Deploy to EKS: kubectl apply -f mukul/inference/deploy_manifest.yaml"
echo ""

