# AWS Resources Status Summary

**Last Updated**: November 18, 2025, 01:15 UTC  
**Account**: 222634400500  
**Region**: us-east-1  
**Project**: RadStream - Cloud-Native Medical Imaging Inference & Telemetry

---

## 📊 **EXECUTIVE SUMMARY**

**Overall Progress**: Core infrastructure is fully deployed and tested. Model container has been built and pushed to ECR. The system is ready for EKS deployment and final integration.

**Infrastructure Status**: ✅ **19/19 Core Resources Deployed**  
**Lambda Functions**: ✅ **4/4 Deployed & Tested**  
**End-to-End Pipeline**: ✅ **Tested & Working** (without EKS inference)  
**Telemetry Pipeline**: ✅ **Operational**  
**Model Container**: ✅ **Built & Pushed to ECR**

---

## ✅ **WHAT HAS BEEN DONE SO FAR**

### **Infrastructure Components - Completed (19/19)**

| Component | Count | Status | Owner | Details |
|-----------|-------|--------|-------|---------|
| S3 Buckets | 4/4 | ✅ Complete | Rahul | All buckets created with encryption, versioning, EventBridge notifications |
| Lambda Functions | 4/4 | ✅ Complete | Rahul | All functions deployed, tested with real S3 data |
| Lambda Layers | 2/2 | ✅ Complete | Rahul | Pillow and NumPy layers created and attached |
| IAM Roles | 7/7 | ✅ Complete | Karthik | All roles created with least-privilege policies |
| EventBridge Rules | 3/3 | ✅ Complete | Karthik | Rules enabled with Step Functions targets configured |
| Step Functions | 1/1 | ✅ Complete | Karthik | State machine deployed and tested |
| Kinesis Streams | 1/1 | ✅ Complete | Karthik | Stream created and receiving telemetry data |
| EKS Cluster | 1/1 | ✅ Complete | Karthik | Cluster created and active |
| ECR Repository | 1/1 | ✅ Complete | Karthik | Repository created, container pushed |
| Model Container | 1/1 | ✅ Complete | Rahul | Container built and pushed to ECR (6.0 GB) |

### **Testing & Validation - Completed**

- ✅ **Lambda Function Testing**: All 4 functions tested individually with real S3 data
- ✅ **End-to-End Pipeline Testing**: Complete pipeline tested successfully (Study ID: E2E-606A81DB)
- ✅ **Performance Metrics**: Baseline performance established (~1.5s total pipeline latency without EKS)
- ✅ **Container Build**: Model container successfully built and pushed to ECR

### **Code & Scripts Created**

- ✅ **Infrastructure Scripts**: 8 setup scripts created and executed
- ✅ **Lambda Functions**: 4 Lambda functions implemented and deployed
- ✅ **Testing Scripts**: 3 comprehensive testing scripts created
- ✅ **Configuration Files**: IAM roles, requirements files, layer creation scripts
- ✅ **Container Build Script**: Automated build and push script created

### **Recent Accomplishments**

1. ✅ **EKS Cluster Created** (November 7, 2025, 21:07:30 UTC-0500)
   - Cluster name: `radstream-cluster`
   - Kubernetes version: 1.32
   - Nodegroup: `ng-9322b429` (t3.micro, 1 node)
   - Status: ACTIVE

2. ✅ **ECR Repository Created** (November 7, 2025, 21:28:23 UTC-0500)
   - Repository: `radstream-triton`
   - URI: `222634400500.dkr.ecr.us-east-1.amazonaws.com/radstream-triton`

3. ✅ **Model Container Built & Pushed** (November 7, 2025, 22:10:47 UTC-0500)
   - Image: `222634400500.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:latest`
   - Size: ~6.0 GB (6,401,512,473 bytes)
   - Digest: `sha256:9213ec7acbae269273d36860f08b5c77f5be40011a4716fef3fc489fdc9b42da`
   - Status: Ready for EKS deployment

---

## 🎯 **WHAT NEEDS TO BE DONE NEXT**

### **Phase 1: Fix EKS Capacity Bottleneck (t3.micro → t3.medium)** ⏳ **URGENT**

**Problem**: Current t3.micro nodegroup is too small; system pods consume all capacity, leaving no room for inference pods.

**Solution**: Replace with t3.medium (or t3.small) for CPU inference baseline.

**Owner**: Karthik  
**Timeline**: Week 2, Day 1  
**Priority**: URGENT - Blocks all inference deployment

**Tasks**:
1. Create new CPU nodegroup with t3.medium
2. Drain and delete old t3.micro nodegroup
3. Verify cluster stability and capacity

---

### **Phase 2: Deploy Triton ONNX Inference on EKS (CPU)** ⏳ **URGENT**

**Goal**: Deploy Triton Inference Server with ONNX model for CPU-based inference.

**Owner**: Karthik (deployment), Rahul (model preparation)  
**Timeline**: Week 2, Day 1-2  
**Priority**: URGENT - Required for pipeline completion

**Tasks**:
1. Prepare Triton model repository structure (ONNX model + config)
2. Update Triton Docker image for CPU (use CPU base image)
3. Build and push CPU image to ECR
4. Deploy to EKS with appropriate resource limits for t3.medium

---

### **Phase 3: Expose Triton Endpoint for Step Functions** ⏳ **URGENT**

**Goal**: Create stable inference URL accessible from Step Functions workflow.

**Owner**: Karthik  
**Timeline**: Week 2, Day 2  
**Priority**: URGENT - Blocks Step Functions integration

**Tasks**:
1. Create LoadBalancer service for Triton
2. Get external ELB DNS endpoint
3. Test endpoint: `http://<elb-dns>/v2/models/onnx_model/infer`
4. Provide endpoint URL to Rahul

---

### **Phase 4: Wire Step Functions → EKS Inference** ⏳ **URGENT**

**Goal**: Update Step Functions state machine to call Triton inference endpoint.

**Owner**: Rahul  
**Timeline**: Week 2, Day 2-3  
**Priority**: URGENT - Completes pipeline integration  
**Dependency**: Triton endpoint URL from Karthik (Phase 3)

**Tasks**:
1. Extract EKS cluster CA and endpoint
2. Update Step Functions InvokeInference state with:
   - CertificateAuthority
   - Endpoint (Triton LoadBalancer URL)
   - Container image reference
   - Job environment variables
3. Update state machine definition
4. Test Step Functions execution

---

### **Phase 5: Verify Telemetry Pipeline** ⏳

**Goal**: Ensure real-time telemetry streaming is operational.

**Owner**: Karthik  
**Timeline**: Week 2, Day 3  
**Priority**: Medium

**Tasks**:
1. Verify Kinesis stream is active
2. Verify Firehose delivery stream is active
3. Confirm telemetry Lambda writes to Kinesis
4. Test telemetry flow: Lambda → Kinesis → Firehose → S3

---

### **Phase 6: Full End-to-End Demo Run** ⏳

**Goal**: Test complete pipeline from S3 upload to results storage.

**Owner**: Rahul (execution), Karthik (monitoring)  
**Timeline**: Week 2, Day 3-4  
**Priority**: High

**Tasks**:
1. Upload test image to S3 (triggers EventBridge)
2. Monitor Step Functions execution:
   - ValidateInput Lambda
   - PrepareImage Lambda
   - InvokeInference (EKS → Triton)
   - StoreResults Lambda
   - SendTelemetry Lambda
3. Verify outputs:
   - Results in S3 results bucket
   - Telemetry in S3 data lake
   - Check CloudWatch logs
4. Run Athena query on telemetry data (optional)

---

### **Phase 7: Cost Control & Cleanup** ⏳

**Goal**: Minimize costs after demo/testing.

**Owner**: Karthik  
**Timeline**: After demo completion  
**Priority**: Low (post-demo)

**Tasks**:
1. Scale nodegroup to 0 or delete cluster after demo
2. Stop/delete any GPU nodes if added
3. Delete Kinesis stream and Firehose after submission (if not needed)
4. Monitor and optimize ongoing costs

---

### **Additional Tasks (Week 3-4)**

8. **Glue & Athena Setup** ⏳ **HIGH PRIORITY**
   - Create Glue database and crawler for telemetry data
   - Set up Athena workgroup
   - Test queries on telemetry data
   - **Owner**: Karthik
   - **Can proceed independently**

9. **HPA Configuration** ⏳
   - Configure Horizontal Pod Autoscaler for EKS
   - Test autoscaling behavior
   - **Owner**: Karthik

10. **CloudWatch Container Insights** ⏳
    - Enable Container Insights for EKS monitoring
    - Configure metrics and dashboards
    - **Owner**: Karthik

11. **Performance Benchmarking** ⏳
    - Run comprehensive benchmarks with full pipeline
    - Measure p50, p95, p99 latencies
    - **Owner**: Rahul

12. **QuickSight Dashboards** ⏳
    - Set up QuickSight account
    - Connect to Athena data source
    - Create performance and security dashboards
    - **Owner**: Karthik

13. **CloudWatch Dashboards** ⏳
    - Create dashboards for Lambda, EKS, Kinesis metrics
    - Configure alarms
    - **Owner**: Karthik

14. **AWS WAF Configuration** ⏳
    - Create Web ACL with managed rules
    - Attach to LoadBalancer
    - **Owner**: Karthik
    - **Dependency**: LoadBalancer from Phase 3

15. **Security Testing** ⏳
    - Simulate attacks (SQL injection, XSS)
    - Verify WAF blocks
    - Test GuardDuty alerts
    - **Owner**: Karthik

16. **Load Testing** ⏳
    - Burst test: 50 images in 1 minute
    - Sustained test: 10 images/min for 30 minutes
    - Monitor autoscaling behavior
    - **Owner**: Karthik (coordination), Rahul (execution)

---

## 👤 **WHAT NEEDS TO BE DONE BY KARTHIK**

### **Role**: Security, Edge & Evaluation Lead + Platform & Autoscaling Lead

### **✅ What Karthik Has Completed**

1. ✅ **Infrastructure Setup Scripts**
   - EventBridge, Step Functions, Kinesis setup scripts executed
   - IAM roles created (7 roles)
   - Security configurations in place

2. ✅ **EKS Cluster Setup**
   - Cluster `radstream-cluster` created successfully
   - Kubernetes version: 1.32
   - Nodegroup deployed

3. ✅ **ECR Repository Setup**
   - Repository `radstream-triton` created
   - Ready for container images

### **⏳ What Karthik Needs to Do Next**

#### **Phase 1: Fix EKS Capacity Bottleneck (This Week - URGENT)**

1. **Replace t3.micro Nodegroup with t3.medium** ⏳ **URGENT**
   - **Problem**: Current t3.micro is too small; system pods consume all capacity
   - **Solution**: Create new CPU nodegroup with t3.medium (or t3.small for cost savings)
   - **Actions**:
     ```bash
     # Create new nodegroup
     eksctl create nodegroup \
       --cluster radstream-cluster \
       --name cpu-ng \
       --node-type t3.medium \
       --nodes 1 --nodes-min 1 --nodes-max 1 \
       --managed
     
     # Drain old nodes
     kubectl cordon <old-node>
     kubectl drain <old-node> --ignore-daemonsets --delete-emptydir-data
     
     # Delete old nodegroup
     eksctl delete nodegroup \
       --cluster radstream-cluster \
       --name ng-9322b429
     ```
   - **Timeline**: Week 2, Day 1 (URGENT - blocks all inference deployment)
   - **Dependency**: None

#### **Phase 2: Deploy Triton ONNX Inference on EKS (CPU) (This Week - URGENT)**

2. **Prepare Triton Model Repository** ⏳ **URGENT**
   - **Task**: Set up ONNX model repository structure
   - **Structure**:
     ```
     model_repo/
       onnx_model/
         1/
           model.onnx
         config.pbtxt
     ```
   - **Actions**:
     - Get ONNX model from Rahul or use placeholder
     - Create model repository structure
     - Prepare `config.pbtxt` for ONNX model
   - **Timeline**: Week 2, Day 1
   - **Dependency**: ONNX model (coordinate with Rahul)

3. **Build and Push Triton CPU Image** ⏳ **URGENT**
   - **Task**: Create Triton Docker image with CPU base image
   - **Dockerfile**:
     ```dockerfile
     FROM nvcr.io/nvidia/tritonserver:24.01-py3
     COPY model_repo /models
     ENV MODEL_REPOSITORY=/models
     CMD ["tritonserver", "--model-repository=/models", "--log-verbose=1"]
     ```
   - **Actions**:
     ```bash
     docker build -t radstream-triton:cpu -f mukul/inference/Dockerfile.triton .
     docker tag radstream-triton:cpu 222634400500.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:cpu
     aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 222634400500.dkr.ecr.us-east-1.amazonaws.com
     docker push 222634400500.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:cpu
     ```
   - **Timeline**: Week 2, Day 1-2
   - **Dependency**: Model repository (Task 2)

4. **Deploy Triton to EKS** ⏳ **URGENT**
   - **Task**: Deploy Triton container to EKS with appropriate resource limits
   - **Actions**:
     - Update `mukul/inference/deploy_manifest.yaml`:
       - Image: `222634400500.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:cpu`
       - Resources for t3.medium:
         ```yaml
         resources:
           requests:
             cpu: "500m"
             memory: "1Gi"
           limits:
             cpu: "1"
             memory: "2Gi"
         ```
     - Configure kubectl: `aws eks update-kubeconfig --name radstream-cluster --region us-east-1`
     - Create namespace: `kubectl create namespace radstream`
     - Deploy: `kubectl apply -f mukul/inference/deploy_manifest.yaml`
     - Verify: `kubectl get pods -n radstream`
   - **Timeline**: Week 2, Day 2 (URGENT - blocks Rahul's integration)
   - **Dependency**: CPU image in ECR (Task 3)

#### **Phase 3: Expose Triton Endpoint (This Week - URGENT)**

5. **Create LoadBalancer Service** ⏳ **URGENT**
   - **Task**: Expose Triton service with stable external endpoint
   - **Service YAML**:
     ```yaml
     apiVersion: v1
     kind: Service
     metadata:
       name: triton-svc
       namespace: radstream
     spec:
       type: LoadBalancer
       selector:
         app: triton
       ports:
       - port: 80
         targetPort: 8000
     ```
   - **Actions**:
     - Create `triton_service.yaml`
     - Apply: `kubectl apply -f triton_service.yaml`
     - Get endpoint: `kubectl get svc triton-svc -n radstream`
     - Test: `http://<elb-dns>/v2/models/onnx_model/infer`
     - **Provide to Rahul**: External ELB DNS endpoint
   - **Timeline**: Week 2, Day 2 (URGENT - blocks Rahul's integration)
   - **Dependency**: Triton deployment (Task 4)

3. **Set Up AWS Glue & Athena** ⏳ **HIGH PRIORITY**
   - **Task**: Create Glue database and crawler for telemetry data
   - **Script**: `rahul/telemetry/glue_schema.py` (exists, needs execution)
   - **Actions**:
     - Create Glue database: `radstream_analytics`
     - Run crawler on telemetry S3 bucket: `radstream-telemetry-222634400500`
     - Create Athena workgroup: `radstream-analytics`
     - Configure query result location: `s3://radstream-telemetry-222634400500/athena-results/`
     - Test queries from `rahul/telemetry/athena_queries.sql`
   - **Timeline**: Week 2-3
   - **Dependency**: None (can proceed now)

#### **Week 2-3 Tasks**

4. **Configure Horizontal Pod Autoscaler (HPA)** ⏳
   - **Task**: Set up HPA for automatic scaling
   - **Actions**:
     - Set up HPA based on CPU/memory metrics
     - Configure min/max replicas (suggest: min=1, max=3 for t3.micro)
     - Test autoscaling behavior: `kubectl get hpa -n radstream --watch`
   - **Timeline**: Week 2-3
   - **Dependency**: Triton deployment (Task 1)

5. **Set Up CloudWatch Container Insights** ⏳
   - **Task**: Enable Container Insights for EKS monitoring
   - **Actions**:
     - Go to: CloudWatch Console → Container Insights
     - Enable Container Insights for EKS cluster
     - Verify metrics are flowing to CloudWatch
     - Configure custom metrics
   - **Timeline**: Week 3
   - **Dependency**: EKS cluster (✅ Done)

6. **Create Application Load Balancer (ALB)** ⏳
   - **Task**: Set up ALB for EKS service
   - **Actions**:
     - Set up ALB for EKS service
     - Configure health checks
     - Set up SSL/TLS certificates
     - Get ALB ARN for WAF attachment
   - **Timeline**: Week 3-4
   - **Dependency**: Triton deployment (Task 1)

#### **Week 3-4 Tasks**

7. **Create QuickSight Dashboards** ⏳
   - **Task**: Set up QuickSight and create performance dashboards
   - **Actions**:
     - Set up QuickSight account (free tier)
     - Connect to Athena as data source
     - Create Performance Dashboard:
       - Average latency over time (by pipeline stage)
       - Throughput (studies/hour) per day
       - p95 latency, error rate %
     - Create Security Dashboard (after WAF/GuardDuty setup)
   - **Timeline**: Week 3-4
   - **Dependency**: Glue & Athena setup (Task 3)

8. **Set Up CloudWatch Dashboards** ⏳
   - **Task**: Create CloudWatch dashboards for monitoring
   - **Actions**:
     - Go to: CloudWatch Console → Dashboards → Create
     - Lambda metrics: duration, error count, throttles
     - Step Functions: execution success rate, duration
     - Kinesis metrics: incoming records, delivery errors
     - EKS pod metrics: CPU, memory, request rate
   - **Timeline**: Week 3-4
   - **Dependency**: None (can proceed now)

9. **Configure AWS WAF** ⏳
   - **Task**: Create WAF Web ACL and attach to ALB
   - **Actions**:
     - Go to: WAF Console → Create Web ACL
     - Name: `radstream-waf`
     - Add managed rules: CommonRuleSet, KnownBadInputsRuleSet
     - Attach to Application Load Balancer (created in Task 6)
     - Monitor blocked requests in CloudWatch
   - **Timeline**: Week 4-5
   - **Dependency**: ALB from Task 6

10. **Network Security Setup** ⏳
    - **Task**: Review and configure network security
    - **Actions**:
      - Review VPC security groups
      - Configure EKS node security groups
      - Set up VPC endpoints (if needed for cost optimization)
    - **Timeline**: Week 4-5
    - **Dependency**: EKS cluster (✅ Done)

#### **Week 4-5 Tasks**

11. **Security Testing** ⏳
    - **Task**: Perform security testing and validation
    - **Actions**:
      - Simulate malicious requests (SQL injection, XSS)
      - Verify WAF blocks attacks
      - Test GuardDuty alert generation
      - Document security findings
    - **Timeline**: Week 5-6
    - **Dependency**: WAF setup (Task 9)

12. **Load Testing Coordination** ⏳
    - **Task**: Coordinate and monitor load testing
    - **Actions**:
      - Coordinate with Rahul for load tests
      - Burst test: 50 images in 1 minute
      - Sustained test: 10 images/min for 30 minutes
      - Monitor autoscaling behavior in EKS
      - Measure convergence time
    - **Timeline**: Week 5-6
    - **Dependency**: EKS deployment (Task 1)

13. **Performance Tuning (EKS)** ⏳
    - **Task**: Optimize EKS deployment
    - **Actions**:
      - Optimize resource requests/limits
      - Tune HPA parameters
      - Test under various loads
    - **Timeline**: Week 5-6
    - **Dependency**: HPA setup (Task 4)

14. **Implement Rolling Update Strategy** ⏳
    - **Task**: Configure deployment strategy for zero-downtime updates
    - **Actions**:
      - Configure deployment strategy
      - Test zero-downtime updates
      - Document rollback procedures
    - **Timeline**: Week 3-4
    - **Dependency**: Triton deployment (Task 1)

### **📊 Karthik's Current Status Summary**

**Completed**: ✅
- Infrastructure setup scripts created and executed (EventBridge, Step Functions, Kinesis)
- IAM roles and security configurations in place
- EventBridge rules configured and operational
- Step Functions state machine deployed
- Kinesis stream created and operational
- EKS cluster created successfully
- ECR repository created

**In Progress**: ⏳
- Preparing to deploy Triton Inference Server to EKS
- Security review and verification
- Preparing for Glue and Athena setup

**Pending**: ⏳
- **URGENT**: Deploy container to EKS (blocks Rahul's integration)
- **URGENT**: Provide EKS endpoint URL to Rahul
- **HIGH PRIORITY**: AWS Glue Data Catalog setup (can proceed now)
- Configure HPA and monitoring
- CloudWatch Container Insights
- Application Load Balancer (ALB)
- QuickSight dashboard creation
- AWS WAF configuration
- GuardDuty and CloudTrail verification

---

## 👤 **WHAT NEEDS TO BE DONE BY RAHUL**

### **Role**: Data & Serving Performance Lead

### **✅ What Rahul Has Completed**

1. ✅ **S3 Buckets Setup**
   - All 4 buckets created with encryption, versioning, EventBridge notifications
   - Buckets: images, results, telemetry, artifacts

2. ✅ **Lambda Functions Development & Deployment**
   - All 4 functions deployed and tested with real S3 data
   - Functions: validate_metadata, prepare_tensors, store_results, send_telemetry

3. ✅ **Lambda Layers Creation**
   - Pillow layer (3.16 MB) and NumPy layer (15.07 MB) created
   - Layers attached to prepare_tensors function

4. ✅ **Testing Infrastructure**
   - Test scripts created and executed
   - End-to-end pipeline tested successfully
   - Performance metrics established

5. ✅ **Model Container Build & Push**
   - Docker image built and pushed to ECR
   - Image size: ~6.0 GB
   - Ready for EKS deployment

### **⏳ What Rahul Needs to Do Next**

#### **Immediate Next Steps (This Week)**

1. **Wait for EKS Endpoint URL** ⏳
   - **Status**: Container is ready in ECR, waiting for Karthik to deploy to EKS
   - **Action**: Monitor for EKS endpoint URL from Karthik
   - **Timeline**: Week 2-3
   - **Dependency**: Karthik's EKS deployment

2. **Update Step Functions for EKS Integration** ⏳
   - **Task**: Modify Step Functions definition to include EKS API call
   - **Location**: `karthik/infrastructure/stepfunctions_setup.py`
   - **Actions**:
     - Add "RunInference" state that calls EKS endpoint
     - Update state machine definition
     - Test integration
   - **Dependency**: EKS endpoint URL from Karthik
   - **Timeline**: Week 2-3 (after receiving endpoint)

3. **Test EKS Inference Integration** ⏳
   - **Task**: Test complete pipeline with EKS inference step
   - **Actions**:
     - Run end-to-end test with real inference
     - Verify inference results
     - Check telemetry data
   - **Dependency**: EKS deployment complete
   - **Timeline**: Week 3

#### **Phase 5: Verify Telemetry Pipeline (This Week)**

6. **Verify Kinesis and Firehose** ⏳
   - **Task**: Ensure telemetry streaming is operational
   - **Actions**:
     ```bash
     aws kinesis describe-stream --stream-name radstream-telemetry
     aws firehose describe-delivery-stream --delivery-stream-name radstream-telemetry-firehose
     ```
   - **Timeline**: Week 2, Day 3
   - **Dependency**: None

7. **Test Telemetry Flow** ⏳
   - **Task**: Confirm telemetry Lambda writes to Kinesis
   - **Actions**:
     - Check `radstream-send-telemetry` Lambda logs
     - Run test put to Kinesis
     - Verify data flows: Lambda → Kinesis → Firehose → S3
   - **Timeline**: Week 2, Day 3
   - **Dependency**: None

#### **Week 3-4 Tasks**

8. **Performance Benchmarking** ⏳
   - **Task**: Run comprehensive benchmarks with full pipeline
   - **Script**: `rahul/scripts/benchmark.py`
   - **Actions**:
     - Run benchmarks with test images
     - Measure end-to-end latency
     - Calculate p50, p95, p99 latencies
     - Document baseline performance metrics
   - **Timeline**: Week 3-4
   - **Dependency**: EKS integration complete

5. **AWS Glue Data Catalog Setup** ⏳
   - **Task**: Set up Glue database for telemetry queries
   - **Script**: `rahul/telemetry/glue_schema.py`
   - **Actions**:
     - Create database and crawler
     - Run crawler on telemetry S3 bucket
     - Verify data is queryable
   - **Timeline**: Week 4 (can proceed independently)

6. **Optimize Model Serving** ⏳
   - **Task**: Configure batch processing and dynamic batching
   - **Actions**:
     - Update `model_config.pbtxt` with optimal settings
     - Test different batch sizes
     - Measure performance improvements
   - **Timeline**: Week 4

#### **Week 4-5 Tasks**

7. **Performance Optimization (Lambda)** ⏳
   - **Task**: Optimize Lambda functions
   - **Actions**:
     - Adjust memory allocation (512-1024 MB)
     - Set timeout (30-60 seconds)
     - Test different configurations
     - Optimize code for better performance
   - **Timeline**: Week 5-6

8. **A/B Testing Execution** ⏳
   - **Task**: Test S3 Standard vs S3 Express
   - **Actions**:
     - Test different configurations
     - Measure performance differences
     - Document findings
   - **Timeline**: Week 5-6
   - **Dependency**: Coordinate with Karthik

9. **Load Testing Execution** ⏳
   - **Task**: Execute load tests
   - **Actions**:
     - Burst test: 50 images in 1 minute
     - Sustained test: 10 images/min for 30 minutes
     - Monitor Lambda and Step Functions performance
   - **Timeline**: Week 5-6
   - **Dependency**: Coordinate with Karthik

#### **Week 8 Tasks**

10. **Technical Documentation** ⏳
    - **Task**: Document performance findings
    - **Actions**:
      - Document performance findings
      - Create technical reports
      - Prepare presentation data
    - **Timeline**: Week 8

### **📊 Rahul's Current Status Summary**

**Completed**: ✅
- All Lambda functions deployed and tested
- Lambda layers created and attached
- End-to-end pipeline tested successfully (without EKS)
- Testing infrastructure in place
- Model container built and pushed to ECR
- S3 buckets created and configured

**In Progress**: ⏳
- Waiting for Karthik's EKS deployment and endpoint URL
- Ready to integrate EKS inference into Step Functions

**Pending**: ⏳
- Update Step Functions to call EKS API (waiting for endpoint URL)
- Performance benchmarking with full pipeline
- AWS Glue Data Catalog setup (can proceed independently)
- Performance optimization
- Load testing execution

---

## 📋 **DEPENDENCIES & COORDINATION**

### **Karthik → Rahul**

**What Karthik Needs to Provide**:
1. ⏳ **EKS Endpoint URL** (URGENT)
   - **Status**: Waiting for Triton deployment
   - **Purpose**: Rahul needs this for Step Functions integration
   - **Timeline**: Week 2 (URGENT)

2. ⏳ **Service Endpoint URL** (URGENT)
   - **Status**: Waiting for Triton deployment
   - **Purpose**: Rahul needs this for inference API calls
   - **Timeline**: Week 2 (URGENT)

**What Rahul Has Provided to Karthik**:
1. ✅ **Model Container Image in ECR**: `222634400500.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:latest`
   - **Status**: ✅ Built and pushed successfully
   - **Image Size**: ~6.0 GB
   - **Purpose**: Karthik can now deploy this container to EKS cluster

2. ✅ **Model Configuration** (`model_config.pbtxt`)
   - **Status**: ✅ Available in `mukul/inference/model_config.pbtxt`
   - **Purpose**: Karthik needs this for Triton Inference Server configuration

### **Rahul → Karthik**

**What Rahul Has Provided**:
1. ✅ **S3 Telemetry Bucket Name**: `radstream-telemetry-222634400500`
   - **Purpose**: Karthik uses this for Kinesis Firehose destination and Glue crawler

**What Rahul Is Waiting For**:
1. ⏳ **Glue Database Access** (after Karthik sets up Glue Data Catalog)
   - **Purpose**: Rahul will query telemetry data using Athena
   - **Timeline**: Week 3-4

### **Karthik → All**

**What Karthik Will Provide**:
1. ⏳ **QuickSight Dashboard Access** (after dashboard creation)
2. ⏳ **Security Review Findings** (after security testing)
3. ⏳ **Performance Metrics and Cost Analysis** (after evaluation)

---

## 📊 **PROGRESS TRACKING**

| Component | Status | Owner | Blocked On | Notes |
|-----------|--------|-------|------------|-------|
| S3 Buckets | ✅ Complete | Rahul | - | All 4 buckets created with encryption |
| Lambda Functions | ✅ Complete | Rahul | - | All 4 functions deployed and tested |
| Lambda Layers | ✅ Complete | Rahul | - | Pillow and NumPy layers created and attached |
| IAM Roles | ✅ Complete | Karthik | - | All 7 roles created with proper permissions |
| EventBridge | ✅ Complete | Karthik | - | 3 rules enabled with targets configured |
| Step Functions | ✅ Complete | Karthik | - | State machine deployed and tested |
| Kinesis Streams | ✅ Complete | Karthik | - | Stream created and receiving data |
| EKS Cluster | ✅ Complete | Karthik | - | Cluster created, ready for deployment |
| ECR Repository | ✅ Complete | Karthik | - | Repository created, container pushed |
| Model Container | ✅ Complete | Rahul | - | Built and pushed to ECR (6.0 GB) |
| EKS Deployment | ⏳ **In Progress** | Karthik | - | **URGENT**: Container ready, needs deployment |
| EKS Endpoint | ⏳ **Pending** | Karthik | EKS Deployment | **URGENT**: Needed for Step Functions integration |
| Glue Data Catalog | ⏳ Pending | Karthik | - | Ready to set up (HIGH PRIORITY) |
| QuickSight Dashboards | ⏳ Pending | Karthik | Glue + Athena | Waiting for Glue setup |
| WAF Configuration | ⏳ Pending | Karthik | ALB | Waiting for ALB creation |
| End-to-End Testing | ✅ Tested | Rahul | - | Manual trigger tested (without EKS) |

---

## 🎯 **SUCCESS CRITERIA STATUS**

| Criteria | Target | Current Status | Notes |
|----------|--------|----------------|-------|
| End-to-end pipeline latency | < 5 seconds (p95) | ✅ In Progress | Current: ~1.5s (without EKS inference) |
| Autoscaling reduces latency spike | 30%+ during burst | ⏳ Pending | Waiting for EKS and HPA setup |
| WAF blocks attacks | 100% of simulated attacks | ⏳ Pending | Waiting for WAF and ALB setup |
| GuardDuty generates findings | For suspicious activity | ⏳ Pending | Waiting for GuardDuty setup |
| QuickSight dashboard | Shows real-time metrics | ⏳ Pending | Waiting for Glue and Athena setup |
| Cost per 1000 images | < $2 | ⏳ Pending | Will measure after full pipeline is operational |

---

## 📝 **HOW TO ACCESS AWS RESOURCES**

### **Lambda Functions**
- **Console**: https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions
- **Search for**: Functions starting with `radstream-`
- **Region**: Must be `us-east-1`

### **Step Functions**
- **Console**: https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines
- **State Machine**: `radstream-pipeline`
- **View Executions**: Click on state machine → "Executions" tab

### **S3 Buckets**
- **Console**: https://s3.console.aws.amazon.com/s3/buckets?region=us-east-1
- **Search for**: Buckets starting with `radstream-`

### **EventBridge Rules**
- **Console**: https://console.aws.amazon.com/events/home?region=us-east-1#/rules
- **Search for**: Rules starting with `radstream-`

### **Kinesis Streams**
- **Console**: https://console.aws.amazon.com/kinesis/home?region=us-east-1#/streams
- **Stream Name**: `radstream-telemetry`

### **EKS Cluster**
- **Console**: https://console.aws.amazon.com/eks/home?region=us-east-1#/clusters
- **Cluster Name**: `radstream-cluster`

### **ECR Repository**
- **Console**: https://console.aws.amazon.com/ecr/repositories?region=us-east-1
- **Repository Name**: `radstream-triton`

---

## 🚀 **SUMMARY**

**What Has Been Accomplished**:
- ✅ Complete infrastructure setup (S3, Lambda, EventBridge, Step Functions, Kinesis)
- ✅ All Lambda functions deployed, tested, and operational
- ✅ Custom Lambda layers created for Pillow and NumPy
- ✅ End-to-end pipeline tested successfully (manual trigger, without EKS)
- ✅ Telemetry pipeline operational and receiving data
- ✅ IAM roles and security configurations in place
- ✅ 11 major issues identified and resolved during setup
- ✅ EKS cluster created
- ✅ ECR repository created
- ✅ Model container built and pushed to ECR

**What's Next**:
- ⏳ **URGENT**: Karthik - Deploy container to EKS and provide endpoint URL (blocks Rahul)
- ⏳ **HIGH PRIORITY**: Karthik - Set up Glue and Athena (can proceed independently)
- ⏳ Rahul - Integrate EKS inference into Step Functions (after receiving endpoint)
- ⏳ Karthik - Create QuickSight dashboards (after Glue setup)
- ⏳ All - Complete end-to-end testing with full pipeline

**Current State**: 
- ✅ Core infrastructure is complete and tested
- ✅ EKS cluster and ECR repository created
- ✅ Model container built and pushed to ECR
- ✅ System is ready for EKS deployment
- ⏳ **URGENT**: Waiting for Karthik to deploy container to EKS and provide endpoint URL
- ⏳ Waiting for EKS endpoint URL to complete Step Functions integration
- All team members can proceed with their respective tasks based on the dependencies outlined above.

---

**Last Updated**: November 18, 2025, 01:15 UTC  
**Document Maintained By**: Rahul Sharma

---

## 📋 **DETAILED PHASE BREAKDOWN**

### **Phase 1: Fix EKS Capacity Bottleneck**

**Current Issue**: t3.micro nodegroup (ng-9322b429) is too small. System pods (kube-proxy, vpc-cni, coredns) consume all capacity, leaving no room for Triton inference pods.

**Solution**: Replace with t3.medium nodegroup for CPU inference baseline.

**Cost Comparison**:
- t3.micro: $0.0104/hour (~$7.50/month) - **Too small**
- t3.small: $0.0208/hour (~$15/month) - **Minimum viable**
- t3.medium: $0.0416/hour (~$30/month) - **Recommended for stability**

**Commands**:
```bash
# 1. Create new nodegroup
eksctl create nodegroup \
  --cluster radstream-cluster \
  --region us-east-1 \
  --name cpu-ng \
  --node-type t3.medium \
  --nodes 1 \
  --nodes-min 1 \
  --nodes-max 1 \
  --managed

# 2. Wait for nodes to be ready
kubectl get nodes

# 3. Cordon old node (prevent new pods)
kubectl cordon <old-node-name>

# 4. Drain old node
kubectl drain <old-node-name> --ignore-daemonsets --delete-emptydir-data

# 5. Delete old nodegroup
eksctl delete nodegroup \
  --cluster radstream-cluster \
  --region us-east-1 \
  --name ng-9322b429
```

---

### **Phase 2: Deploy Triton ONNX Inference on EKS (CPU)**

**Model Repository Structure**:
```
model_repo/
  onnx_model/
    1/
      model.onnx
    config.pbtxt
```

**Triton config.pbtxt Example**:
```protobuf
name: "onnx_model"
platform: "onnxruntime_onnx"
max_batch_size: 8
input [
  {
    name: "input"
    data_type: TYPE_FP32
    dims: [ 3, 224, 224 ]
  }
]
output [
  {
    name: "output"
    data_type: TYPE_FP32
    dims: [ 1000 ]
  }
]
dynamic_batching {
  max_queue_delay_microseconds: 10000
}
```

**Dockerfile for CPU**:
```dockerfile
FROM nvcr.io/nvidia/tritonserver:24.01-py3

# Copy model repository
COPY model_repo /models

# Set environment
ENV MODEL_REPOSITORY=/models

# Expose ports
EXPOSE 8000 8001 8002

# Start Triton
CMD ["tritonserver", "--model-repository=/models", "--log-verbose=1"]
```

**Deployment Resource Limits** (for t3.medium):
```yaml
resources:
  requests:
    cpu: "500m"      # 0.5 CPU cores
    memory: "1Gi"    # 1 GB RAM
  limits:
    cpu: "1"         # 1 CPU core max
    memory: "2Gi"    # 2 GB RAM max
```

---

### **Phase 3: Expose Triton Endpoint**

**LoadBalancer Service YAML** (`mukul/inference/triton_service.yaml`):
```yaml
apiVersion: v1
kind: Service
metadata:
  name: triton-svc
  namespace: radstream
spec:
  type: LoadBalancer
  selector:
    app: triton
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
```

**After deployment, get endpoint**:
```bash
kubectl get svc triton-svc -n radstream
# Copy EXTERNAL-IP or EXTERNAL-DNS
```

**Test endpoint**:
```bash
curl http://<elb-dns>/v2/models/onnx_model/infer
```

---

### **Phase 4: Wire Step Functions → EKS Inference**

**Extract EKS Details**:
```bash
# Get cluster CA
CLUSTER_CA=$(aws eks describe-cluster \
  --name radstream-cluster \
  --region us-east-1 \
  --query 'cluster.certificateAuthority.data' \
  --output text)

# Get cluster endpoint
CLUSTER_ENDPOINT=$(aws eks describe-cluster \
  --name radstream-cluster \
  --region us-east-1 \
  --query 'cluster.endpoint' \
  --output text)
```

**Step Functions State Update**:
- Update `InvokeInference` state to call Triton LoadBalancer endpoint
- Use HTTP request to Triton REST API: `POST http://<elb-dns>/v2/models/onnx_model/infer`
- Pass preprocessed image data and study_id

---

### **Phase 7: Cost Control After Demo**

**To minimize costs**:
```bash
# Option 1: Scale nodegroup to 0 (keeps cluster, stops nodes)
eksctl scale nodegroup \
  --cluster radstream-cluster \
  --name cpu-ng \
  --nodes 0

# Option 2: Delete nodegroup (saves node costs, cluster still costs)
eksctl delete nodegroup \
  --cluster radstream-cluster \
  --name cpu-ng

# Option 3: Delete entire cluster (saves all EKS costs)
eksctl delete cluster --name radstream-cluster

# Delete Kinesis stream (if not needed)
aws kinesis delete-stream --stream-name radstream-telemetry

# Delete Firehose (if not needed)
aws firehose delete-delivery-stream --delivery-stream-name radstream-telemetry-firehose
```

**Cost Notes**:
- EKS control plane: $0.10/hour (~$72/month) - runs 24/7 while cluster exists
- t3.medium node: $0.0416/hour (~$30/month) - only when running
- LoadBalancer: ~$0.0225/hour (~$16/month) - only when service exists
- **Biggest saver**: Delete cluster after demo

