# Rahul Sharma - Data & Serving Performance Lead

## 🎯 Responsibilities

- **Data Pipeline**: S3 buckets, EventBridge, Step Functions
- **Lambda Functions**: Preprocessing, validation, storage
- **Telemetry**: Kinesis streams, data lake, analytics
- **Performance**: Benchmarking, optimization, A/B testing

## 📁 My Components

### Preprocessing (`preprocessing/`)
- `validate_metadata.py` - JSON sidecar validation
- `prepare_tensors.py` - Image preprocessing and normalization
- `store_results.py` - Inference result storage
- `send_telemetry.py` - Centralized telemetry sending
- `requirements.txt` - Python dependencies

### Telemetry (`telemetry/`)
- `kinesis_producer.py` - Telemetry data streaming
- `glue_schema.py` - Data catalog setup
- `athena_queries.sql` - Analytics queries

### Scripts (`scripts/`)
- `upload_images.py` - Batch image upload and load testing
- `benchmark.py` - Performance measurement and reporting

## 🚀 Quick Start

1. **Set up AWS infrastructure**
   ```bash
   python ../shared/infrastructure/s3_setup.py
   python ../shared/infrastructure/eventbridge_setup.py
   python ../shared/infrastructure/stepfunctions_setup.py
   python ../shared/infrastructure/lambda_setup.py
   python ../shared/infrastructure/kinesis_setup.py
   ```

2. **Deploy Lambda functions**
   ```bash
   python preprocessing/validate_metadata.py
   python preprocessing/prepare_tensors.py
   python preprocessing/store_results.py
   python preprocessing/send_telemetry.py
   ```

3. **Set up telemetry**
   ```bash
   python telemetry/glue_schema.py
   ```

4. **Test the pipeline**
   ```bash
   python scripts/upload_images.py --num-images 10
   python scripts/benchmark.py --num-studies 5
   ```

## 📊 Performance Targets

- **End-to-end latency**: < 5 seconds (p95)
- **Throughput**: 10+ images/minute sustained
- **Cost per image**: < $0.002
- **Success rate**: > 99%

## 🔗 Dependencies

- **Depends on Mukul**: EKS cluster and endpoint (Week 2-3)
- **Depends on Karthik**: IAM policies and security setup (Week 1-2)
- **Provides to Mukul**: Model container requirements (Week 3)
- **Provides to Karthik**: Telemetry data for dashboards (Week 4-5)

## 📈 A/B Testing Scenarios

1. **S3 Standard vs S3 Express One Zone**
2. **Autoscaling on vs off**
3. **Different Lambda memory configurations**
4. **Batch size optimization**

## 🛠️ Development Workflow

1. Create feature branch: `git checkout -b feature/rahul-description`
2. Make changes and test locally
3. Push and create PR to `develop`
4. Request review from team members
5. Merge after approval

## 📞 Contact

- **Role**: Data & Serving Performance Lead
- **Focus**: Pipeline performance, data flow, analytics
