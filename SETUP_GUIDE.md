# RadStream Pipeline Setup Guide

## 🎯 Quick Start

This guide helps you **recreate the entire RadStream pipeline from scratch** after services have been deleted to save costs.

**Estimated Setup Time**: 2-3 hours  
**Estimated Cost**: ~$20-30/month (with minimal usage)

---

## 📋 Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured (`aws configure`)
3. **kubectl** installed and configured
4. **Docker** installed and running
5. **Python 3.9+** with virtual environment
6. **Git** (to clone repository)

---

## 🚀 Step-by-Step Setup

### **Phase 1: Environment Setup** (15 minutes)

#### 1.1 Clone Repository and Setup Virtual Environment

```bash
# Navigate to project directory
cd "/Users/rahul/Downloads/Code scripts/RadStream"

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

#### 1.2 Configure AWS Credentials

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Set region (if not in ~/.aws/config)
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
```

#### 1.3 Get AWS Account ID

```bash
# Get account ID (needed for bucket names)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"
```

---

### **Phase 2: S3 Buckets** (10 minutes)

#### 2.1 Create S3 Buckets

```bash
# Activate virtual environment first
source venv/bin/activate

# Run S3 setup script
python karthik/infrastructure/s3_setup.py
```

**Expected Output**:
- ✅ `radstream-images-{account-id}` - Raw images
- ✅ `radstream-results-{account-id}` - Inference results
- ✅ `radstream-telemetry-{account-id}` - Telemetry data
- ✅ `radstream-artifacts-{account-id}` - Preprocessed images

**Verification**:
```bash
aws s3 ls | grep radstream
```

---

### **Phase 3: Lambda Functions** (30 minutes)

#### 3.1 Deploy Lambda Functions

```bash
# Deploy all Lambda functions
python karthik/infrastructure/lambda_setup.py
```

**This creates**:
- ✅ `radstream-validate-metadata` - Validates JSON metadata
- ✅ `radstream-prepare-tensors` - Preprocesses images
- ✅ `radstream-invoke-triton` - Calls Triton inference
- ✅ `radstream-store-results` - Stores results in S3
- ✅ `radstream-send-telemetry` - Sends telemetry to Kinesis

**Verification**:
```bash
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `radstream`)].FunctionName'
```

#### 3.2 Update Triton Endpoint (After EKS Setup)

After deploying Triton to EKS (Phase 5), update the Lambda environment variable:

```bash
# Get Triton endpoint
TRITON_ENDPOINT=$(kubectl get svc radstream-triton-service -n radstream -o jsonpath='{.status.loadBalancer.ingress[0].hostname}:8000')

# Update Lambda environment variable
aws lambda update-function-configuration \
    --function-name radstream-invoke-triton \
    --environment Variables="{TRITON_ENDPOINT=http://$TRITON_ENDPOINT}"
```

---

### **Phase 4: Step Functions** (15 minutes)

#### 4.1 Deploy Step Functions State Machine

```bash
# Deploy state machine
python karthik/infrastructure/stepfunctions_setup.py
```

**This creates**:
- ✅ `radstream-pipeline` - Main pipeline state machine
- ✅ `radstream-error-handler` - Error handling state machine

**Verification**:
```bash
aws stepfunctions list-state-machines --query 'stateMachines[?starts_with(name, `radstream`)].name'
```

---

### **Phase 5: EventBridge** (10 minutes)

#### 5.1 Setup EventBridge Rule

```bash
# Create EventBridge rule for S3 → Step Functions
python karthik/infrastructure/eventbridge_setup.py
```

**This creates**:
- ✅ EventBridge rule: `radstream-s3-trigger`
- ✅ Triggers Step Functions on S3 `PutObject` events

**Verification**:
```bash
aws events list-rules --query 'Rules[?starts_with(Name, `radstream`)].Name'
```

---

### **Phase 6: Kinesis Data Stream** (5 minutes)

#### 6.1 Create Kinesis Stream

```bash
# Create Kinesis stream for telemetry
python karthik/infrastructure/kinesis_setup.py
```

**This creates**:
- ✅ Kinesis stream: `radstream-telemetry` (1 shard)

**Verification**:
```bash
aws kinesis list-streams --query 'StreamNames[?contains(@, `radstream`)]'
```

---

### **Phase 7: EKS Cluster & Triton** (60-90 minutes)

#### 7.1 Create EKS Cluster

```bash
# Create EKS cluster (if not exists)
aws eks create-cluster \
    --name radstream-cluster \
    --version 1.32 \
    --role-arn arn:aws:iam::{account-id}:role/RadStreamEKSClusterRole \
    --resources-vpc-config subnetIds=subnet-xxx,subnet-yyy,securityGroupIds=sg-xxx

# Wait for cluster to be active (10-15 minutes)
aws eks wait cluster-active --name radstream-cluster

# Configure kubectl
aws eks update-kubeconfig --name radstream-cluster --region us-east-1
```

#### 7.2 Create Node Group

```bash
# Create node group (t3.medium instances)
aws eks create-nodegroup \
    --cluster-name radstream-cluster \
    --nodegroup-name radstream-nodes \
    --node-role arn:aws:iam::{account-id}:role/RadStreamEKSNodeRole \
    --instance-types t3.medium \
    --scaling-config minSize=1,maxSize=3,desiredSize=1 \
    --subnets subnet-xxx subnet-yyy

# Wait for node group to be active (5-10 minutes)
aws eks wait nodegroup-active --cluster-name radstream-cluster --nodegroup-name radstream-nodes
```

#### 7.3 Build and Push Triton Container

```bash
# Build and push container to ECR
bash rahul/scripts/build_and_push_container.sh
```

**This**:
- ✅ Builds Triton Docker image
- ✅ Pushes to ECR: `radstream-triton:cpu`

#### 7.4 Deploy Triton to EKS

```bash
# Deploy Triton to EKS
bash rahul/scripts/deploy_to_eks.sh
```

**This**:
- ✅ Creates namespace: `radstream`
- ✅ Deploys Triton deployment
- ✅ Creates LoadBalancer service
- ✅ Exposes Triton endpoint

**Get Triton Endpoint**:
```bash
# Wait for LoadBalancer (2-5 minutes)
kubectl get svc radstream-triton-service -n radstream

# Get endpoint
TRITON_ENDPOINT=$(kubectl get svc radstream-triton-service -n radstream -o jsonpath='{.status.loadBalancer.ingress[0].hostname}:8000')
echo "Triton Endpoint: http://$TRITON_ENDPOINT"
```

#### 7.5 Update Lambda with Triton Endpoint

```bash
# Update Lambda environment variable
aws lambda update-function-configuration \
    --function-name radstream-invoke-triton \
    --environment Variables="{TRITON_ENDPOINT=http://$TRITON_ENDPOINT}"
```

---

### **Phase 8: Security Configuration** (20 minutes)

#### 8.1 Configure Security Groups

**EKS Security Group**:
- Allow inbound: Port 8000 from Lambda security group
- Block all other inbound traffic

**Lambda Security Group** (if using VPC):
- Allow outbound: To EKS security group
- Allow outbound: To S3, Kinesis, CloudWatch

**Implementation**:
```bash
# Get security group IDs
EKS_SG=$(aws eks describe-cluster --name radstream-cluster --query 'cluster.resourcesVpcConfig.clusterSecurityGroupId' --output text)
LAMBDA_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=RadStreamLambdaSG" --query 'SecurityGroups[0].GroupId' --output text)

# Allow Lambda → EKS
aws ec2 authorize-security-group-ingress \
    --group-id $EKS_SG \
    --protocol tcp \
    --port 8000 \
    --source-group $LAMBDA_SG
```

#### 8.2 Review IAM Roles

Verify all IAM roles have least-privilege permissions:
- Lambda roles: Only necessary S3, Kinesis, CloudWatch permissions
- EKS roles: Only ECR pull, CloudWatch logs
- Step Functions role: Only Lambda invoke

---

### **Phase 9: Testing** (15 minutes)

#### 9.1 End-to-End Test

```bash
# Run end-to-end test
python rahul/scripts/test_end_to_end_triton.py --study-id TEST-001 --auto-trigger
```

**Expected Output**:
- ✅ Step Functions execution succeeds
- ✅ Results stored in S3: `radstream-results-{account-id}/results/TEST-001/`
- ✅ CloudWatch logs show success

#### 9.2 Benchmark Test

```bash
# Run benchmark with real images
python rahul/scripts/benchmark_real_images.py --num-studies 10
```

**Expected Output**:
- ✅ 100% success rate
- ✅ P95 latency < 6 seconds
- ✅ Results saved to `benchmark_real_images.csv`

---

## 🔧 Troubleshooting

### **Issue: Lambda can't find dependencies**

**Solution**:
```bash
# Redeploy Lambda with correct packaging
python karthik/infrastructure/lambda_setup.py
```

### **Issue: Triton endpoint not accessible**

**Solution**:
```bash
# Check Triton pod status
kubectl get pods -n radstream

# Check service
kubectl get svc -n radstream

# Check logs
kubectl logs -f deployment/radstream-triton -n radstream
```

### **Issue: Step Functions execution fails**

**Solution**:
```bash
# Check Step Functions execution
aws stepfunctions describe-execution --execution-arn <execution-arn>

# Check CloudWatch logs for each Lambda
aws logs tail /aws/lambda/radstream-validate-metadata --follow
```

### **Issue: S3 bucket not found**

**Solution**:
```bash
# Recreate S3 buckets
python karthik/infrastructure/s3_setup.py
```

---

## 💰 Cost Optimization Tips

1. **EKS Node Group**: Use `t3.medium` (not GPU) - ~$30/month
2. **Node Count**: Keep `desiredSize=1` when not testing
3. **S3 Lifecycle**: Delete objects after 30 days
4. **Kinesis**: 1 shard is sufficient (~$11/month)
5. **Lambda**: Free tier: 1M requests/month
6. **Step Functions**: Free tier: 4,000 state transitions/month

**Total Estimated Cost**: ~$20-30/month (with minimal usage)

---

## 📊 Verification Checklist

- [ ] S3 buckets created (4 buckets)
- [ ] Lambda functions deployed (5 functions)
- [ ] Step Functions state machine created
- [ ] EventBridge rule created
- [ ] Kinesis stream created
- [ ] EKS cluster active
- [ ] Triton deployed and accessible
- [ ] Security groups configured
- [ ] End-to-end test passes
- [ ] Benchmark test passes

---

## 🚀 Next Steps

1. **Monitor Costs**: Set up AWS Cost Alerts
2. **Scale Testing**: Run larger benchmarks if needed
3. **Security Review**: Review IAM roles and security groups
4. **Documentation**: Update team documentation

---

## 📚 Additional Resources

- [AWS Lambda Setup](https://docs.aws.amazon.com/lambda/)
- [EKS Setup Guide](https://docs.aws.amazon.com/eks/)
- [Triton Inference Server](https://github.com/triton-inference-server/server)
- [WAF Alternatives](./WAF_ALTERNATIVES.md)

---

## 🆘 Support

If you encounter issues:
1. Check CloudWatch Logs for each service
2. Review IAM permissions
3. Verify network connectivity (Security Groups)
4. Check service quotas/limits

**Common Issues**:
- IAM permissions: Check role policies
- Network: Check security groups
- Dependencies: Check Lambda layers/packages
- Endpoints: Verify Triton endpoint is accessible

