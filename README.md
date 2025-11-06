# RadStream: Cloud-Native Medical Imaging Pipeline

A comprehensive cloud-native medical imaging inference pipeline built on AWS services to demonstrate the benefits of modern cloud infrastructure over traditional on-premises PACS systems.

## 🏥 Project Overview

RadStream processes medical images through a serverless workflow, performs AI inference using containerized models, and provides comprehensive telemetry and monitoring. The system showcases how cloud services can improve latency, scalability, reliability, security, and observability for medical imaging workflows.

### Key Features

- **Serverless Architecture**: AWS Lambda, Step Functions, EventBridge
- **Containerized Inference**: EKS with NVIDIA Triton Inference Server
- **Real-time Telemetry**: Kinesis Data Streams and Firehose
- **Data Lake Analytics**: S3, Glue, Athena, QuickSight
- **Security First**: WAF, GuardDuty, CloudTrail, IAM least-privilege
- **Cost Optimized**: Designed for minimal cost while demonstrating benefits

## 🏗️ Architecture

```
Medical Images → S3 → EventBridge → Step Functions → Lambda → EKS → Kinesis → S3 Data Lake → Athena → QuickSight
```

### Core Components

1. **Data Ingestion**: S3 buckets for images, metadata, results, and telemetry
2. **Processing**: Lambda functions for validation, preprocessing, and storage
3. **Inference**: EKS cluster with Triton Inference Server for model serving
4. **Orchestration**: Step Functions for workflow management
5. **Telemetry**: Kinesis streams and Firehose for real-time monitoring
6. **Analytics**: Glue Data Catalog, Athena, and QuickSight for insights

## 🚀 Quick Start

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

2. **Install Python dependencies**
   ```bash
   pip install -r shared/requirements.txt
   ```

3. **Set up AWS infrastructure** (Karthik's responsibility)
   ```bash
   # Create S3 buckets
   python karthik/infrastructure/s3_setup.py
   
   # Set up EventBridge rules
   python karthik/infrastructure/eventbridge_setup.py
   
   # Create Step Functions workflow
   python karthik/infrastructure/stepfunctions_setup.py
   
   # Deploy Lambda functions
   python karthik/infrastructure/lambda_setup.py
   
   # Set up Kinesis streams
   python karthik/infrastructure/kinesis_setup.py
   
   # Create Glue schema (Rahul's responsibility)
   python rahul/telemetry/glue_schema.py
   ```

4. **Deploy EKS cluster** (Mukul's responsibility)
   ```bash
   # Create EKS cluster
   eksctl create cluster --name radstream-cluster --region us-east-1
   
   # Deploy model containers
   kubectl apply -f mukul/inference/deploy_manifest.yaml
   ```

5. **Test the pipeline**
   ```bash
   # Upload test images
   python rahul/scripts/upload_images.py --num-images 10
   
   # Run benchmark
   python rahul/scripts/benchmark.py --num-studies 5
   ```

## 📁 Project Structure

```
RadStream/
├── shared/                    # Common documentation
│   ├── docs/                 # All documentation
│   │   ├── architecture.md
│   │   ├── PROGRESS_REPORT.md
│   │   └── evaluation_plan.md
│   └── requirements.txt
├── rahul/                    # Rahul's implementations
│   ├── preprocessing/        # Lambda functions
│   │   ├── validate_metadata.py
│   │   ├── prepare_tensors.py
│   │   ├── store_results.py
│   │   ├── send_telemetry.py
│   │   └── requirements.txt
│   ├── telemetry/            # Monitoring & logging
│   │   ├── kinesis_producer.py
│   │   ├── glue_schema.py
│   │   └── athena_queries.sql
│   ├── scripts/              # Helper scripts
│   │   ├── upload_images.py
│   │   ├── benchmark.py
│   │   └── test_pipeline.py
│   └── README.md
├── mukul/                    # Mukul's implementations
│   ├── inference/            # EKS/model serving
│   │   ├── Dockerfile.triton
│   │   ├── model_config.pbtxt
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
├── .github/                  # GitHub workflows and templates
│   ├── workflows/
│   └── ISSUE_TEMPLATE/
├── CONTRIBUTING.md
├── PROGRESS_REPORT.md
└── README.md
```

## 👥 Team Responsibilities

### Rahul Sharma — Data & Serving Performance Lead
- S3 buckets and EventBridge setup
- Lambda functions development
- Step Functions workflow design
- Telemetry pipeline and data lake
- Performance benchmarking

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

### Target Performance
- **End-to-end latency**: < 5 seconds (p95)
- **Throughput**: 10+ images/minute sustained
- **Availability**: 99.9% uptime
- **Cost per image**: < $0.002

### Monitoring
- CloudWatch dashboards for real-time metrics
- X-Ray tracing for request flow analysis
- Custom metrics for business KPIs
- QuickSight for data visualization

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
# Upload test images
python rahul/scripts/upload_images.py --num-images 100 --batch-size 10

# Run performance benchmark
python rahul/scripts/benchmark.py --num-studies 50 --concurrent 5

# Test telemetry
python rahul/telemetry/kinesis_producer.py
```

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
- [Progress Report & Task Breakdown](shared/docs/PROGRESS_REPORT.md)
- [Evaluation Plan & A/B Testing](shared/docs/evaluation_plan.md)
- [Contributing Guidelines](CONTRIBUTING.md)

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