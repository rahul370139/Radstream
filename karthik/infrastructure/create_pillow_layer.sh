#!/bin/bash
# Create Lambda Layer for Pillow
# This script builds Pillow for Lambda's Amazon Linux 2 environment

set -e

echo "Creating Pillow Lambda Layer..."
echo "=================================="

# Create layer directory structure
LAYER_DIR="pillow-layer"
PYTHON_DIR="$LAYER_DIR/python"

# Clean up if exists
rm -rf "$LAYER_DIR"
mkdir -p "$PYTHON_DIR"

echo "Installing Pillow for Lambda (Amazon Linux 2)..."
echo "This may take a few minutes..."

# Install Pillow and dependencies to the layer directory
# Using pip with --platform to target Lambda's environment
pip install \
    --platform manylinux2014_x86_64 \
    --target "$PYTHON_DIR" \
    --implementation cp \
    --python-version 3.10 \
    --only-binary=:all: \
    --upgrade \
    Pillow 2>&1 | grep -v "WARNING" || echo "Note: Some warnings are expected"

# Alternative: If the above doesn't work, use Docker to build for Lambda
if [ ! -d "$PYTHON_DIR/PIL" ]; then
    echo "Building Pillow using Docker (Lambda-compatible)..."
    
    # Create Dockerfile for building Pillow
    cat > Dockerfile.pillow << 'EOF'
FROM public.ecr.aws/lambda/python:3.10
RUN yum install -y gcc && \
    pip install --no-cache-dir Pillow
EOF
    
    # Build in Docker and copy out
    docker build -f Dockerfile.pillow -t pillow-builder .
    CONTAINER_ID=$(docker create pillow-builder)
    docker cp $CONTAINER_ID:/var/lang/lib/python3.10/site-packages/. "$PYTHON_DIR/"
    docker rm $CONTAINER_ID
    rm -f Dockerfile.pillow
fi

# Create zip file
echo "Creating layer zip file..."
cd "$LAYER_DIR"
zip -r ../pillow-layer.zip python/ -q
cd ..

# Get layer size
LAYER_SIZE=$(du -h pillow-layer.zip | cut -f1)
echo "✅ Layer created: pillow-layer.zip ($LAYER_SIZE)"

# Instructions
echo ""
echo "Next steps:"
echo "1. Upload layer to AWS:"
echo "   aws lambda publish-layer-version \\"
echo "     --layer-name pillow-layer \\"
echo "     --zip-file fileb://pillow-layer.zip \\"
echo "     --compatible-runtimes python3.10 python3.11 python3.12"
echo ""
echo "2. Attach layer to Lambda functions:"
echo "   Use the layer ARN in lambda_setup.py"

