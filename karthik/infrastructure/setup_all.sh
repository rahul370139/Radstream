#!/bin/bash
# Comprehensive Setup Script for RadStream Pipeline
# This script automates the entire pipeline setup process

set -e  # Exit on error

echo "=========================================="
echo "RadStream Pipeline Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}✅ Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}✅ Installing dependencies...${NC}"
pip install -q -r requirements.txt

# Get AWS account ID
echo -e "${GREEN}✅ Getting AWS account ID...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Function to run setup script
run_setup() {
    local script_name=$1
    local description=$2
    
    echo -e "${YELLOW}📦 $description...${NC}"
    if python "$SCRIPT_DIR/$script_name"; then
        echo -e "${GREEN}✅ $description completed${NC}"
    else
        echo -e "${RED}❌ $description failed${NC}"
        exit 1
    fi
    echo ""
}

# Phase 1: S3 Buckets
echo "=========================================="
echo "Phase 1: S3 Buckets"
echo "=========================================="
run_setup "s3_setup.py" "Creating S3 buckets"

# Phase 2: Lambda Functions
echo "=========================================="
echo "Phase 2: Lambda Functions"
echo "=========================================="
run_setup "lambda_setup.py" "Deploying Lambda functions"

# Phase 3: Step Functions
echo "=========================================="
echo "Phase 3: Step Functions"
echo "=========================================="
run_setup "stepfunctions_setup.py" "Creating Step Functions state machine"

# Phase 4: EventBridge
echo "=========================================="
echo "Phase 4: EventBridge"
echo "=========================================="
run_setup "eventbridge_setup.py" "Setting up EventBridge rules"

# Phase 5: Kinesis
echo "=========================================="
echo "Phase 5: Kinesis Data Stream"
echo "=========================================="
run_setup "kinesis_setup.py" "Creating Kinesis stream"

echo "=========================================="
echo -e "${GREEN}✅ Infrastructure Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Set up EKS cluster (see SETUP_GUIDE.md)"
echo "2. Build and push Triton container:"
echo "   bash rahul/scripts/build_and_push_container.sh"
echo "3. Deploy Triton to EKS:"
echo "   bash rahul/scripts/deploy_to_eks.sh"
echo "4. Update Lambda with Triton endpoint"
echo "5. Run end-to-end test:"
echo "   python rahul/scripts/test_end_to_end_triton.py --study-id TEST-001 --auto-trigger"
echo ""

