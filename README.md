# RadStream: Cloud-Native Medical Imaging Pipeline

A comprehensive cloud-native medical imaging inference pipeline built on AWS services to demonstrate the benefits of modern cloud infrastructure over traditional on-premises PACS systems.

## 🏥 Project Overview

RadStream processes medical images through a serverless workflow, performs AI inference using containerized models, and provides comprehensive telemetry and monitoring. The system showcases how cloud services can improve latency, scalability, reliability, security, and observability for medical imaging workflows.

### Key Features

- **Serverless Architecture**: AWS Lambda, Step Functions, EventBridge
- **Containerized Inference**: EKS with NVIDIA Triton Inference Server
- **Real-time Telemetry**: Kinesis Data Streams and Firehose
- **Data Lake Analytics**: S3, Glue, Athena, QuickSight
- **Security First**: Security Groups, GuardDuty, CloudTrail, IAM least-privilege (see [WAF_ALTERNATIVES.md](./WAF_ALTERNATIVES.md))
- **Cost Optimized**: Designed for minimal cost while demonstrating benefits

## 🏗️ Architecture

```
Medical Images → S3 → EventBridge → Step Functions → Lambda → Triton (EKS) → Lambda (CheXpert Mapping) → S3 Results → Kinesis → S3 Data Lake → Athena → QuickSight
```

### Current Pipeline Flow

1. **Image Upload**: Medical images uploaded to S3 with JSON metadata
2. **EventBridge Trigger**: S3 event triggers Step Functions state machine
3. **Validation**: Lambda validates metadata format
4. **Preprocessing**: Lambda preprocesses image (resize, normalize, convert to grayscale)
5. **Inference**: Lambda calls Triton Inference Server on EKS
   - Triton returns 18 TXR logits
   - Lambda maps to 14 CheXpert labels
6. **Storage**: Lambda stores results in S3
7. **Telemetry**: Lambda sends telemetry to Kinesis
8. **Analytics**: Kinesis → Firehose → S3 → Athena → QuickSight

### Core Components

1. **Data Ingestion**: S3 buckets for images, metadata, results, and telemetry
2. **Processing**: Lambda functions for validation, preprocessing, and storage
3. **Inference**: EKS cluster with Triton Inference Server for model serving
4. **Orchestration**: Step Functions for workflow management
5. **Telemetry**: Kinesis streams and Firehose for real-time monitoring
6. **Analytics**: Glue Data Catalog, Athena, and QuickSight for insights

## 🚀 Quick Start

> **📖 For detailed setup instructions, see [SETUP_GUIDE.md](./SETUP_GUIDE.md)**

### Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+ installed
- Docker installed (for model containers)
- kubectl installed (for EKS management)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/rahul370139/Radstream.git
   cd Radstream
   ```

2. **Set up Python virtual environment**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate virtual environment
   source venv/bin/activate
   # or
   source activate_venv.sh
   
   # Install dependencies
   pip install boto3 botocore requests numpy scipy torch torchvision torchxrayvision onnx onnxruntime
   ```

3. **Set up AWS infrastructure** (Karthik's responsibility)
   ```bash
   # Activate virtual environment first
   source venv/bin/activate
   
   # Create S3 buckets
   python3 karthik/infrastructure/s3_setup.py
   
   # Set up EventBridge rules
   python3 karthik/infrastructure/eventbridge_setup.py
   
   # Create Step Functions workflow
   python3 karthik/infrastructure/stepfunctions_setup.py
   
   # Deploy Lambda functions (includes Triton inference Lambda)
   python3 karthik/infrastructure/lambda_setup.py
   
   # Set up Kinesis streams
   python3 karthik/infrastructure/kinesis_setup.py
   ```

4. **Export ONNX Model** (Rahul's responsibility)
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   
   # Export TorchXRayVision model to ONNX
   python3 rahul/scripts/export_txr_to_onnx.py \
       --opset-version 12 \
       --output model_repo/chexpert_classifier/1/model.onnx \
       --model-repo model_repo \
       --model-name chexpert_classifier
   ```

5. **Deploy EKS cluster and Triton Inference Server** (Karthik's responsibility)
   ```bash
   # Create EKS cluster (if not exists)
   eksctl create cluster --name radstream-cluster --region us-east-1
   
   # Create CPU nodegroup (t3.medium for inference capacity)
   eksctl create nodegroup \
     --cluster radstream-cluster \
     --name cpu-ng \
     --node-type t3.medium \
     --nodes 1 --nodes-min 1 --nodes-max 1 \
     --managed
   
   # Build and push Triton CPU image
   bash rahul/scripts/build_and_push_container.sh
   
   # Deploy Triton to EKS
   kubectl apply -f mukul/inference/deploy_manifest.yaml
   
   # Verify deployment
   kubectl get pods -n radstream
   kubectl get svc -n radstream radstream-triton-service
   ```

6. **Test the end-to-end pipeline**
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   
   # Run end-to-end test with Triton inference
   python3 rahul/scripts/test_end_to_end_triton.py --study-id TEST-001 --auto-trigger
   
   # Or upload test images
   python3 rahul/scripts/upload_images.py --num-images 10
   ```

## 📁 Project Structure

```
RadStream/
├── shared/                    # Common documentation
│   ├── docs/                 # All documentation
│   │   ├── architecture.md
│   │   └── evaluation_plan.md
│   └── requirements.txt
├── rahul/                    # Rahul's implementations
│   ├── preprocessing/        # Lambda functions
│   │   ├── validate_metadata.py
│   │   ├── prepare_tensors.py
│   │   ├── store_results.py
│   │   ├── send_telemetry.py
│   │   ├── invoke_triton_inference.py  # NEW: Triton inference Lambda
│   │   ├── requirements.txt
│   │   └── requirements_triton.txt     # NEW: Triton Lambda dependencies
│   ├── scripts/              # Helper scripts
│   │   ├── export_txr_to_onnx.py       # NEW: ONNX model export
│   │   ├── build_and_push_container.sh # NEW: Container build script
│   │   ├── test_end_to_end_triton.py  # NEW: E2E test with Triton
│   │   ├── upload_images.py
│   │   └── benchmark.py
│   ├── AWS_STATUS_SUMMARY.md # Status tracking document
│   └── README.md
├── mukul/                    # Mukul's implementations
│   ├── inference/            # EKS/model serving
│   │   ├── Dockerfile.triton
│   │   ├── health_check.py
│   │   ├── start_triton.sh
│   │   └── deploy_manifest.yaml
│   └── README.md
├── karthik/                  # Karthik's implementations (Infrastructure & Security)
│   ├── infrastructure/       # AWS infrastructure setup scripts
│   │   ├── s3_setup.py      # S3 bucket creation & config
│   │   ├── lambda_setup.py  # Lambda deployment
│   │   ├── eventbridge_setup.py # Event rules
│   │   ├── stepfunctions_setup.py # Workflow orchestration
│   │   └── kinesis_setup.py # Telemetry streams
│   ├── security/             # Security & compliance
│   │   └── iam_roles.json
│   └── README.md
├── model_repo/               # NEW: ONNX model repository
│   └── chexpert_classifier/
│       ├── 1/
│       │   └── model.onnx
│       ├── config.pbtxt
│       └── label_mapping.json
├── venv/                     # NEW: Python virtual environment
├── activate_venv.sh          # NEW: Virtual environment activation script
├── TRITON_INTEGRATION_COMPLETE.md  # NEW: Integration documentation
├── .github/                  # GitHub workflows and templates
│   ├── workflows/
│   └── ISSUE_TEMPLATE/
├── CONTRIBUTING.md
└── README.md
```

## 👥 Team Responsibilities

### Rahul Sharma — Data & Serving Performance Lead
- ✅ S3 buckets and EventBridge setup
- ✅ Lambda functions development (5 functions including Triton inference)
- ✅ Step Functions workflow design and Triton integration
- ✅ ONNX model export and containerization
- ✅ Triton Inference Server deployment
- ✅ CheXpert label mapping implementation
- ✅ End-to-end pipeline testing (100% success rate)
- ✅ Performance benchmarking (10 images, P95=5.68s, 100% success)

### Mukul Rayana — Platform & Autoscaling Lead
- EKS cluster setup and management
- Container deployment and orchestration
- Horizontal Pod Autoscaler (HPA) configuration
- Performance monitoring and optimization

### Karthik Ramanathan — Security, Edge & Evaluation Lead
- IAM roles and security policies
- WAF, GuardDuty, and CloudTrail setup
- QuickSight dashboards and analytics
- A/B testing and evaluation
- Final reporting and documentation

## 🔧 Configuration

### Environment Variables

```bash
export AWS_REGION=us-east-1
export TELEMETRY_STREAM_NAME=radstream-telemetry
export RESULTS_BUCKET=radstream-results-{account-id}
export IMAGES_BUCKET=radstream-images-{account-id}
```

### AWS Services Configuration

1. **S3 Buckets**: 4 buckets with encryption and lifecycle policies
2. **Lambda Functions**: 4 functions with appropriate IAM roles
3. **Step Functions**: 2 state machines for pipeline and error handling
4. **EKS Cluster**: GPU-enabled nodes with autoscaling
5. **Kinesis**: 1 shard stream with Firehose delivery
6. **Glue**: Data catalog with partitioned tables
7. **Athena**: SQL queries for analytics

## 📊 Performance Metrics

### Current Status
- ✅ **Triton Inference**: Deployed and operational
- ✅ **Pipeline Integration**: Complete end-to-end flow tested and verified
- ✅ **Performance Testing**: Completed (10 images, 100% success, P95=5.68s)

### Target Performance
- **End-to-end latency**: < 5 seconds (p95) - Ready to test
- **Throughput**: 10+ images/minute sustained - Ready to test
- **Availability**: 99.9% uptime
- **Cost per image**: < $0.002

### Monitoring
- CloudWatch dashboards for real-time metrics
- Kinesis telemetry streaming operational
- Custom metrics for business KPIs
- QuickSight dashboards (pending Glue setup)

## 🔒 Security

### Security Features
- Encryption at rest (AES-256) and in transit (TLS 1.2+)
- IAM roles with least-privilege access
- WAF protection against common attacks
- GuardDuty for threat detection
- CloudTrail for API auditing

### Compliance
- HIPAA-eligible services
- Data retention policies
- Audit trails and logging
- Access controls and permissions

## 💰 Cost Optimization

### Cost-Effective Design
- Lambda functions with minimal memory allocation
- EKS nodes with right-sizing
- S3 lifecycle policies for data archiving
- Kinesis with single shard for small workloads

### Estimated Costs (8-week project)
- **EKS nodes**: ~$30-40/month
- **Kinesis**: ~$11/month
- **S3 storage**: ~$5-10/month
- **Lambda**: Free tier eligible
- **Total**: ~$50-80/month

## 🧪 Testing

### Test Scripts
```bash
# Activate virtual environment
source venv/bin/activate

# Test end-to-end pipeline with Triton inference
python3 rahul/scripts/test_end_to_end_triton.py --study-id TEST-001 --auto-trigger

# Upload test images
python3 rahul/scripts/upload_images.py --num-images 100 --batch-size 10

# Run performance benchmark
python3 rahul/scripts/benchmark.py --num-studies 50 --concurrent 5
```

### Current Test Status
- ✅ **Lambda Functions**: All 5 functions deployed and configured
- ✅ **Triton Inference**: Model loaded, inference tested successfully
- ✅ **Step Functions**: State machine updated with Triton integration
- ✅ **End-to-End Test**: Completed (100% success rate, 3 seconds execution)
- ✅ **Performance Benchmarking**: Completed (10 images, P95=5.68s processing time)

### A/B Testing Scenarios
1. **Storage Performance**: S3 Standard vs S3 Express One Zone
2. **Autoscaling**: HPA enabled vs disabled
3. **Security**: WAF enabled vs disabled
4. **Cost**: Cloud vs on-premises comparison

## 📈 Analytics and Reporting

### QuickSight Dashboards
- **Performance Dashboard**: Latency, throughput, error rates
- **Security Dashboard**: WAF blocks, GuardDuty findings
- **Cost Dashboard**: Service costs and utilization

### Athena Queries
- Performance metrics analysis
- A/B test comparisons
- Cost analysis and optimization
- Security event analysis

## 🚨 Troubleshooting

### Common Issues

1. **Lambda timeout errors**
   - Increase memory allocation
   - Optimize function code
   - Check S3 access permissions

2. **EKS pod failures**
   - Check resource limits
   - Verify image availability
   - Review pod logs

3. **Kinesis stream errors**
   - Check IAM permissions
   - Verify stream status
   - Monitor shard capacity

4. **Step Functions failures**
   - Check Lambda function status
   - Verify IAM roles
   - Review execution logs

### Debug Commands
```bash
# Check Lambda function logs
aws logs tail /aws/lambda/radstream-validate-metadata --follow

# Check EKS pod status
kubectl get pods -n radstream

# Check Kinesis stream status
aws kinesis describe-stream --stream-name radstream-telemetry

# Check Step Functions execution
aws stepfunctions list-executions --state-machine-arn <arn>
```

## 📚 Documentation

- [Architecture Documentation](shared/docs/architecture.md)
- [AWS Status Summary](rahul/AWS_STATUS_SUMMARY.md) - **Current project status and progress**
- [Setup Guide](SETUP_GUIDE.md) - **Comprehensive setup instructions for pipeline recreation**
- [WAF Alternatives](WAF_ALTERNATIVES.md) - **Cost-effective security solutions**
- [Evaluation Plan & A/B Testing](shared/docs/evaluation_plan.md)

## ✅ **Recent Accomplishments (November 24-25, 2025)**

1. ✅ **ONNX Model Export**: TorchXRayVision DenseNet121 exported to ONNX (IR version 7)
2. ✅ **Triton Deployment**: Triton Inference Server deployed on EKS, model loaded successfully
3. ✅ **Triton Lambda**: Created `radstream-invoke-triton` Lambda with CheXpert label mapping
4. ✅ **Step Functions Integration**: Updated state machine with Triton inference step
5. ✅ **Virtual Environment**: Set up Python 3.13.9 venv with all dependencies
6. ✅ **End-to-End Pipeline Test**: **COMPLETED** - Successfully tested on November 25, 2025
   - All 5 states completed successfully (3 seconds execution time)
   - Results stored in S3, CheXpert mapping verified
   - Issues resolved: IAM permissions, Step Functions 256KB limit, Lambda packaging
7. ✅ **Performance Benchmarking**: **COMPLETED** - November 25, 2025
   - Tested with 10 real chest X-ray images from `chexagent_chexpert_eval/test_samples`
   - **Success Rate**: 100% (10/10 tests passed)
   - **Performance Metrics**:
     - Processing Time: P50=5.40s, P95=5.68s, P99=5.68s
     - Total Time: P50=5.82s, P95=6.51s, P99=6.51s
     - Throughput: 0.17 studies/second
   - Report saved to `benchmark_real_images.csv`
8. ✅ **CloudWatch Dashboard**: Created `Radstream-Monitoring` dashboard (Karthik)
9. ✅ **Lambda Packaging**: Fixed with Linux-compatible wheels and self-contained packages
10. ✅ **Repository Cleanup**: Removed unused files, created setup guides
11. ✅ **WAF Alternatives**: Documented cost-effective security alternatives (Security Groups)
12. ✅ **Setup Automation**: Created comprehensive setup script and guide for easy pipeline recreation

## 🎯 **Next Steps**

### **Rahul Sharma** - ✅ **All Major Tasks Complete**
**Status**: All core pipeline tasks are complete! Remaining items are optional enhancements:
- **OPTIONAL**: Additional large-scale testing (20-50 images) if needed for final report
- **OPTIONAL**: Cost analysis documentation (for final evaluation report)

### **Karthik Ramanathan** - ⏳ **In Progress**
1. **HIGH PRIORITY**: Set up Glue & Athena for telemetry analytics (can proceed independently)
2. **MEDIUM**: Complete QuickSight dashboards (after Glue setup)
3. **MEDIUM**: Configure Security Groups (WAF alternative - see [WAF_ALTERNATIVES.md](./WAF_ALTERNATIVES.md))
4. **LOW**: GuardDuty and CloudTrail setup

### **Repository Cleanup** - ✅ **Completed**
- Removed unused test files and redundant scripts
- Created comprehensive setup guide for easy pipeline recreation
- Documented WAF alternatives for cost optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- AWS for providing cloud services
- NVIDIA for Triton Inference Server
- Open source community for tools and libraries
- Medical imaging community for datasets and models

## 📞 Support

For questions or support, please contact:
- **Rahul Sharma**: Data & Serving Performance
- **Mukul Rayana**: Platform & Autoscaling
- **Karthik Ramanathan**: Security & Evaluation

---

**Note**: This project is designed for educational and demonstration purposes. For production use, ensure proper security reviews, compliance validation, and performance testing.