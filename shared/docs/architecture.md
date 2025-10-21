# RadStream: Cloud-Native Medical Imaging Pipeline Architecture

## Overview

RadStream is a cloud-native medical imaging inference pipeline designed to demonstrate the benefits of modern AWS services over traditional on-premises PACS (Picture Archiving and Communication Systems). The system processes medical images through a serverless workflow, performs AI inference using containerized models, and provides comprehensive telemetry and monitoring.

## Architecture Principles

- **Cloud-First**: Built specifically for AWS cloud services, not just cloud-hosted
- **Serverless**: Leverages AWS Lambda, Step Functions, and managed services
- **Event-Driven**: Uses EventBridge for loose coupling between components
- **Observable**: Comprehensive telemetry and monitoring throughout
- **Secure**: Implements zero-trust security model with least-privilege access
- **Cost-Optimized**: Designed for minimal cost while demonstrating cloud benefits

## High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Medical       │    │   AWS S3        │    │   EventBridge   │
│   Images        │───▶│   (Images)      │───▶│   (Events)      │
│   (JPEG/PNG)    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Results       │◀───│   Step          │◀───│   Lambda        │
│   Storage       │    │   Functions     │    │   (Preprocess)  │
│   (S3)          │    │   (Orchestr.)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   EKS Cluster   │
                       │   (Triton       │
                       │   Inference)    │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Kinesis       │
                       │   (Telemetry)   │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   S3 Data Lake  │
                       │   (Analytics)   │
                       └─────────────────┘
```

## Component Details

### 1. Data Ingestion Layer

**S3 Buckets:**
- `radstream-images-{account-id}`: Raw medical images and metadata
- `radstream-results-{account-id}`: Inference results and reports
- `radstream-telemetry-{account-id}`: Telemetry data lake
- `radstream-artifacts-{account-id}`: Model artifacts and configs

**EventBridge Rules:**
- S3 PutObject events trigger Step Functions workflow
- Error handling and notification rules
- Custom telemetry event routing

### 2. Processing Layer

**Lambda Functions:**
- `radstream-validate-metadata`: Validates JSON sidecar files
- `radstream-prepare-tensors`: Image preprocessing and normalization
- `radstream-store-results`: Stores inference results
- `radstream-send-telemetry`: Centralized telemetry sending

**Step Functions Workflow:**
- Orchestrates end-to-end pipeline execution
- Handles error recovery and retries
- Manages state transitions between stages

### 3. Inference Layer

**EKS Cluster:**
- GPU-enabled nodes for model inference
- Horizontal Pod Autoscaler (HPA) for dynamic scaling
- NVIDIA Triton Inference Server for model serving

**Model Types:**
- Chest X-ray classification (5 classes)
- Object detection for anomalies
- Vision-language encoder for report generation

### 4. Telemetry Layer

**Kinesis Data Streams:**
- Real-time event streaming
- 1 shard for cost optimization
- 24-hour retention period

**Kinesis Data Firehose:**
- Delivers data to S3 data lake
- Automatic partitioning by date
- GZIP compression for storage efficiency

**AWS Glue Data Catalog:**
- Schema discovery and management
- Partitioned tables for efficient querying
- Integration with Athena for analytics

### 5. Analytics Layer

**Amazon Athena:**
- SQL queries on telemetry data
- Performance metrics analysis
- A/B testing comparisons

**Amazon QuickSight:**
- Real-time dashboards
- Performance monitoring
- Cost analysis visualization

## Security Architecture

### Network Security
- VPC with private subnets for EKS
- Security groups with least-privilege access
- VPC endpoints for S3, Kinesis, and Glue

### Data Security
- Encryption at rest (AES-256 for S3, KMS for Kinesis)
- Encryption in transit (TLS 1.2+)
- IAM roles with least-privilege policies

### Monitoring Security
- AWS CloudTrail for API auditing
- AWS GuardDuty for threat detection
- AWS WAF for application protection

## Performance Characteristics

### Latency Targets
- End-to-end processing: < 5 seconds (p95)
- Image upload: < 1 second
- Metadata validation: < 100ms
- Image preprocessing: < 500ms
- Model inference: < 2 seconds
- Result storage: < 200ms

### Throughput Targets
- Sustained: 10 studies/minute
- Burst: 50 studies/minute
- Autoscaling convergence: < 2 minutes

### Availability Targets
- System availability: 99.9%
- Data durability: 99.999999999%
- Recovery time objective: < 5 minutes

## Cost Optimization

### Resource Sizing
- Lambda: 512MB memory, 60s timeout
- EKS: t3.medium nodes (CPU), g4dn.xlarge (GPU when needed)
- Kinesis: 1 shard
- S3: Standard storage with lifecycle policies

### Cost Monitoring
- AWS Cost Explorer integration
- Cost per 1000 images tracking
- Resource utilization monitoring

## Scalability Design

### Horizontal Scaling
- EKS HPA based on CPU/memory utilization
- Lambda concurrency limits
- Kinesis shard scaling (if needed)

### Vertical Scaling
- Lambda memory optimization
- EKS node instance type selection
- Model batch size tuning

## Disaster Recovery

### Data Backup
- S3 cross-region replication (optional)
- EKS cluster backup
- Lambda function versioning

### Failover
- Multi-AZ deployment
- EKS node group across AZs
- S3 cross-region failover

## Compliance

### HIPAA Compliance
- Encryption at rest and in transit
- Access logging and auditing
- Data retention policies
- Business Associate Agreement (BAA) ready

### Data Governance
- Data classification and tagging
- Access controls and permissions
- Audit trails and monitoring
- Data retention and deletion

## Monitoring and Observability

### Metrics
- CloudWatch custom metrics
- Application performance metrics
- Infrastructure metrics
- Business metrics

### Logging
- Centralized logging with CloudWatch
- Structured logging format
- Log aggregation and analysis
- Error tracking and alerting

### Tracing
- AWS X-Ray for distributed tracing
- Request flow visualization
- Performance bottleneck identification
- Error root cause analysis

## Deployment Architecture

### Infrastructure as Code
- AWS CloudFormation templates
- Terraform configurations
- GitOps deployment pipeline

### CI/CD Pipeline
- GitHub Actions or AWS CodePipeline
- Automated testing
- Blue-green deployments
- Rollback capabilities

### Environment Management
- Development environment
- Staging environment
- Production environment
- Environment-specific configurations

## Future Enhancements

### Planned Features
- Multi-region deployment
- Edge computing integration
- Advanced ML model types
- Real-time collaboration features

### Scalability Improvements
- Auto-scaling based on queue depth
- Predictive scaling
- Cost-based scaling decisions
- Performance-based optimization

## Technology Stack

### AWS Services
- S3, Lambda, Step Functions, EventBridge
- EKS, ECR, CloudWatch, X-Ray
- Kinesis, Firehose, Glue, Athena
- IAM, CloudTrail, GuardDuty, WAF

### Open Source
- Kubernetes, Docker
- NVIDIA Triton Inference Server
- Python, boto3
- JSON, YAML

### Development Tools
- AWS CLI, kubectl
- Python, pip
- Git, GitHub
- VS Code, Jupyter

This architecture provides a robust, scalable, and cost-effective solution for medical imaging inference while demonstrating the clear benefits of cloud-native services over traditional on-premises systems.
