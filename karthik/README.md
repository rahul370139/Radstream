# Karthik Ramanathan - Security, Edge & Evaluation Lead

## 🎯 **Responsibilities**

- **Infrastructure Setup**: All AWS infrastructure (S3, EventBridge, Step Functions, Lambda, Kinesis)
- **Security**: IAM, WAF, GuardDuty, CloudTrail
- **Monitoring**: QuickSight dashboards, CloudWatch
- **Evaluation**: A/B testing, performance analysis
- **Compliance**: HIPAA, audit trails, data governance

## 📁 **My Components**

### Infrastructure (`infrastructure/`)
- `s3_setup.py` - Creates 4 S3 buckets with encryption
- `eventbridge_setup.py` - Configures EventBridge rules
- `stepfunctions_setup.py` - Creates Step Functions workflow
- `lambda_setup.py` - Deploys Lambda functions
- `kinesis_setup.py` - Sets up Kinesis streams and Firehose

### Security (`security/`)
- `iam_roles.json` - IAM roles and policies with least-privilege access

---

## 🚀 **STEP-BY-STEP SETUP GUIDE**

### **Week 1-2: Infrastructure & Security Foundation (CRITICAL PATH)**

#### **Day 1: Prerequisites & IAM Setup**

**Step 1: AWS Account Setup (30 minutes)**
1. Log into AWS Console
2. Create IAM user if needed (recommended over root account)
3. Create access key: IAM → Users → Security credentials → Create access key
4. Download and save credentials securely

**Step 2: Configure AWS CLI (15 minutes)**
```bash
aws configure
```
Enter:
- AWS Access Key ID: [your access key]
- AWS Secret Access Key: [your secret key]
- Default region name: `us-east-1`
- Default output format: `json`

**Test configuration:**
```bash
aws sts get-caller-identity
```
Should return your account ID and user ARN.

**Step 3: Install Python Dependencies (10 minutes)**
```bash
cd RadStream
pip install -r requirements.txt
```

**Step 4: Create IAM Roles (2-3 hours) - CRITICAL**
**Why**: All scripts need IAM permissions to create resources. This MUST be done first.

Go to: AWS IAM Console → Roles → Create Role

**Create Role 1: RadStreamLambdaExecutionRole**
1. Trust entity: AWS service → Lambda
2. Attach policies:
   - `AmazonS3ReadOnlyAccess` (for images bucket)
   - `AmazonS3FullAccess` (for results bucket)
   - `AmazonKinesisFullAccess` (for telemetry)
   - `CloudWatchLogsFullAccess`
3. Create role
4. Note the ARN for reference

**Create Role 2: RadStreamStepFunctionsExecutionRole**
1. Trust entity: AWS service → Step Functions
2. Attach policies:
   - `AWSLambda_FullAccess`
   - `AmazonS3FullAccess`
   - `AmazonEKSReadOnlyAccess`
   - `CloudWatchLogsFullAccess`
3. Create role

**Create Role 3: RadStreamEKSNodeGroupRole**
1. Trust entity: AWS service → EC2
2. Attach policies:
   - `AmazonEC2ContainerRegistryReadOnly`
   - `CloudWatchLogsFullAccess`
   - `AmazonS3ReadOnlyAccess`
3. Create role

**Create Role 4: RadStreamEventBridgeRole**
1. Trust entity: AWS service → EventBridge
2. Create inline policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "states:StartExecution",
      "Resource": "arn:aws:states:*:*:stateMachine:radstream-pipeline"
    }
  ]
}
```
3. Create role

**Create Role 5: RadStreamKinesisFirehoseRole**
1. Trust entity: AWS service → Firehose
2. Create inline policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:AbortMultipartUpload",
        "s3:GetBucketLocation",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::radstream-telemetry-*",
        "arn:aws:s3:::radstream-telemetry-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```
3. Create role

**Create Role 6: RadStreamGlueCrawlerRole**
1. Trust entity: AWS service → Glue
2. Attach policies:
   - `AWSGlueServiceRole`
   - `AmazonS3ReadOnlyAccess`
3. Create role

**Reference**: See `security/iam_roles.json` for detailed policy definitions.

---

#### **Day 2: Run Infrastructure Scripts**

**Step 5: S3 Buckets Setup (30 minutes)**
```bash
python karthik/infrastructure/s3_setup.py
```

**Manual Verification**:
1. Go to S3 Console
2. Verify 4 buckets created:
   - `radstream-images-{account-id}`
   - `radstream-results-{account-id}`
   - `radstream-telemetry-{account-id}`
   - `radstream-artifacts-{account-id}`
3. Check each bucket:
   - Encryption: AES-256 enabled
   - Versioning: Enabled on images bucket
   - Public access: Blocked

**Step 6: EventBridge Rules Setup (20 minutes)**
```bash
python karthik/infrastructure/eventbridge_setup.py
```

**Manual Verification**:
1. Go to EventBridge Console → Rules
2. Verify rules created:
   - `radstream-s3-image-upload`
   - `radstream-s3-metadata-upload`
3. Check targets are correctly configured

**Step 7: Step Functions Setup (25 minutes)**
```bash
python karthik/infrastructure/stepfunctions_setup.py
```

**Manual Verification**:
1. Go to Step Functions Console
2. Verify state machine: `radstream-pipeline`
3. Test execution:
   - Click "Start execution"
   - Input: `{"study_id": "test-001", "s3_path": "s3://radstream-images-{account-id}/test.jpg"}`
   - Click "Start execution"
   - Monitor execution logs

**Step 8: Lambda Functions Deployment (45 minutes)**
```bash
python karthik/infrastructure/lambda_setup.py
```

**Manual Verification**:
1. Go to Lambda Console
2. Verify 4 functions created:
   - `radstream-validate-metadata`
   - `radstream-prepare-tensors`
   - `radstream-store-results`
   - `radstream-send-telemetry`
3. For each function:
   - Click on function name
   - Go to Configuration → Permissions
   - Verify IAM role attached
   - Go to Test tab
   - Create test event:
   ```json
   {
     "study_id": "test-001",
     "s3_path": "s3://radstream-images-{account-id}/test.jpg",
     "metadata": {
       "study_id": "test-001",
       "view": "PA",
       "timestamp": "2024-01-15T10:00:00Z"
     }
   }
   ```
   - Click "Test"
   - Check execution results and logs

**Step 9: Kinesis Streams Setup (25 minutes)**
```bash
python karthik/infrastructure/kinesis_setup.py
```

**Manual Verification**:
1. Go to Kinesis Console
2. Verify stream: `radstream-telemetry` (1 shard, Active)
3. Go to Firehose Console
4. Verify delivery stream: `radstream-telemetry-firehose`
5. Check S3 destination configured correctly

---

#### **Day 3: Security Services**

**Step 10: CloudTrail Setup (30 minutes)**
1. Go to CloudTrail Console → Create Trail
2. Trail name: `radstream-trail`
3. Apply trail to all accounts: Leave unchecked (single account)
4. S3 bucket: Create new or use existing
   - Bucket name: `radstream-telemetry-{account-id}-cloudtrail`
   - Enable CloudWatch Logs: Yes
   - Log file validation: Enabled
   - Encryption: S3 SSE
5. Click "Next" → "Create"
6. Verify trail is active

**Step 11: GuardDuty Setup (30 minutes)**
1. Go to GuardDuty Console
2. Click "Enable GuardDuty"
3. Choose region: `us-east-1`
4. Enable EKS Protection: Optional (costs extra)
5. Click "Enable GuardDuty"
6. Configure notifications:
   - Go to Settings → SNS
   - Create SNS topic: `guardduty-findings`
   - Subscribe your email
   - Set finding publishing frequency: 15 minutes

**Step 12: VPC & Security Groups (2 hours)**
1. Go to VPC Console
2. Create VPC (or use default):
   - Name: `radstream-vpc`
   - CIDR: `10.0.0.0/16`
   - Create subnets:
     - Public subnet: `10.0.1.0/24` (us-east-1a)
     - Public subnet: `10.0.2.0/24` (us-east-1b)
     - Private subnet: `10.0.3.0/24` (us-east-1a)
     - Private subnet: `10.0.4.0/24` (us-east-1b)
3. Create Internet Gateway and attach to VPC
4. Create Security Groups:
   
   **Security Group 1: radstream-eks-sg**
   - Type: Custom TCP
   - Port: 443
   - Source: ALB security group (create ALB sg first)
   
   **Security Group 2: radstream-alb-sg**
   - Type: HTTPS
   - Port: 443
   - Source: 0.0.0.0/0 (or specific IP ranges)
   
   **Security Group 3: radstream-lambda-sg**
   - Type: All outbound
   - Destination: S3, Kinesis endpoints

5. Configure route tables for public/private subnets

---

#### **Day 4: Verification & Checkpoint**

**Step 13: Comprehensive Verification (2 hours)**
1. **S3 Verification**:
   - Upload test file to images bucket
   - Verify encryption, versioning working

2. **EventBridge Verification**:
   - Upload image to S3
   - Check EventBridge → Rules → Metrics
   - Verify rule triggered

3. **Step Functions Verification**:
   - Start execution manually
   - Monitor execution logs
   - Verify all states executed

4. **Lambda Verification**:
   - Test each function individually
   - Check CloudWatch logs
   - Verify IAM permissions working

5. **Kinesis Verification**:
   - Send test record to Kinesis stream
   - Verify data in Firehose
   - Check S3 destination for data

**CHECKPOINT 1: Infrastructure Foundation Complete**
- [ ] All 6 IAM roles created and verified
- [ ] All 5 infrastructure scripts executed successfully
- [ ] All resources verified in AWS Console
- [ ] CloudTrail enabled and logging
- [ ] GuardDuty enabled and monitoring
- [ ] VPC and Security Groups configured
- [ ] Ready for Mukul and Rahul to start

**Notify Team**: Send confirmation email/Slack message that infrastructure is ready.

---

### **Week 3-4: Monitoring & Dashboards**

#### **Day 1: CloudWatch Dashboards**

**Step 14: Create Operational Dashboard (2 hours)**
1. Go to CloudWatch Console → Dashboards → Create dashboard
2. Name: `radstream-operational`
3. Add widgets:
   - Lambda: Duration, Error count, Invocations
   - Step Functions: Executions succeeded, Executions failed
   - Kinesis: IncomingRecords, GetRecords.IteratorAgeMilliseconds
   - Custom metrics: End-to-end latency, Throughput
4. Set up alarms:
   - Lambda errors > 5 in 5 minutes
   - Step Functions failures
   - Kinesis iterator age > 1 minute

#### **Day 2: X-Ray Tracing**

**Step 15: Enable X-Ray (1 hour)**
1. Go to X-Ray Console
2. Enable for Lambda functions:
   - Go to each Lambda → Configuration → Tracing
   - Enable Active tracing
3. Enable for Step Functions:
   - Go to Step Functions → Configuration → Logging
   - Enable X-Ray tracing
4. Configure sampling rules:
   - Sample rate: 1% (for cost optimization)
5. View service map after first execution

#### **Day 3-4: QuickSight Setup**

**Step 16: QuickSight Account (30 minutes)**
1. Go to QuickSight Console
2. Sign up (if first time)
3. Choose: Free tier (1 user, 1GB SPICE)
4. Select region: `us-east-1`

**Step 17: Connect to Athena (30 minutes)**
1. In QuickSight, go to Data sources → New data source
2. Select: Athena
3. Data source name: `radstream-athena`
4. Workgroup: `radstream-analytics` (created by Rahul)
5. Test connection

**Step 18: Create Datasets (1 hour)**
1. Create dataset from `radstream_analytics.telemetry_events`
2. Import data to SPICE
3. Create calculated fields:
   - Average latency
   - Error rate
   - Throughput

**Step 19: Build Dashboards (2 hours)**
1. **Performance Dashboard**:
   - Line chart: Average latency over time
   - Bar chart: Throughput per hour
   - KPI: p95 latency, error rate
   
2. **Security Dashboard**:
   - WAF blocked requests count
   - GuardDuty findings by severity
   - CloudTrail API call trends
   
3. **Cost Dashboard**:
   - Service cost breakdown
   - Cost per 1000 images
   - Daily cost trends

---

### **Week 3-4: WAF Setup (After Mukul Creates ALB)**

**Step 20: WAF Configuration (1 hour)**
1. Go to WAF Console → Create Web ACL
2. Name: `radstream-waf`
3. Resource type: Application Load Balancer
4. Select ALB created by Mukul
5. Add managed rule sets:
   - AWSManagedRulesCommonRuleSet
   - AWSManagedRulesKnownBadInputsRuleSet
6. Set default action: Allow
7. Create Web ACL
8. Verify metrics in CloudWatch

---

### **Week 5-6: Evaluation & Testing**

#### **A/B Testing Setup**

**Step 21: Configure Test Environments (2 hours)**
1. Create separate S3 bucket for S3 Express One Zone testing
2. Configure HPA on/off scenarios (coordinate with Mukul)
3. Set up WAF on/off scenarios
4. Create test scripts for each scenario

#### **Security Testing**

**Step 22: Security Validation (3-4 hours)**
1. **SQL Injection Test**:
   ```bash
   # Simulate malicious request
   curl -X POST https://{alb-endpoint}/api/inference \
     -H "Content-Type: application/json" \
     -d '{"metadata": "'; DROP TABLE users; --"}'
   ```
   - Verify WAF blocks request
   - Check GuardDuty findings

2. **XSS Test**:
   ```bash
   curl -X POST https://{alb-endpoint}/api/inference \
     -d '{"metadata": "<script>alert(1)</script>"}'
   ```
   - Verify WAF blocks request

3. **Port Scanning Test**:
   ```bash
   nmap -p 443 {eks-endpoint}
   ```
   - Verify GuardDuty detects scan

4. **DoS Test**:
   - Use Apache Bench for load testing
   - Verify WAF rate limiting

#### **Load Testing Coordination**

**Step 23: Coordinate Load Tests (4-5 hours)**
1. Coordinate with Rahul for burst test: 50 images in 1 minute
2. Coordinate sustained test: 10 images/min for 30 minutes
3. Monitor autoscaling behavior (coordinate with Mukul)
4. Measure performance metrics
5. Document results

---

### **Week 7-8: Final Evaluation & Reporting**

#### **Compile Results**

**Step 24: Data Collection (4-5 hours)**
1. Export QuickSight charts to PDF/images
2. Export CloudWatch metrics to CSV
3. Collect Athena query results
4. Gather cost data from AWS Cost Explorer

**Step 25: Final Report (8-10 hours)**
1. Create comparison tables:
   - Performance: Before/after cloud optimizations
   - Cost: Cloud vs on-premises estimates
   - Security: Attacks blocked, findings summary
   - Scalability: Autoscaling impact
2. Write comprehensive evaluation report
3. Create presentation materials
4. Prepare demo scenarios

---

## 📊 **Performance Targets**

- **Attack Detection**: 100% of simulated attacks blocked
- **Compliance**: 100% HIPAA compliance
- **Audit Trail**: Complete API call logging
- **Response Time**: < 5 minutes to detect threats

## 🔗 **Dependencies**

- **Blocks**: Rahul and Mukul (they cannot start until infrastructure is ready)
- **Depends on**: None (starts first)
- **Provides to**: 
  - Rahul: Infrastructure access (Week 1-2)
  - Mukul: IAM roles and infrastructure (Week 1-2)
  - All: Security evaluation and final report (Week 7-8)

## 📞 **Contact**

- **Role**: Security, Edge & Evaluation Lead
- **Focus**: Infrastructure, security, monitoring, evaluation, compliance

---

**Remember**: You are on the CRITICAL PATH. All other work depends on your completion of infrastructure setup! 🚀