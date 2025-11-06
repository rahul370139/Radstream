# Rahul Sharma - Data & Serving Performance Lead

## 🎯 **Responsibilities**

- **Lambda Functions**: Preprocessing, validation, storage
- **Telemetry Pipeline**: Kinesis streams, data lake, analytics
- **Performance**: Benchmarking, optimization, A/B testing
- **Integration**: Step Functions workflow, EKS integration

## 📁 **My Components**

### Preprocessing (`preprocessing/`)
- `validate_metadata.py` - JSON sidecar validation Lambda
- `prepare_tensors.py` - Image preprocessing Lambda
- `store_results.py` - Inference result storage Lambda
- `send_telemetry.py` - Telemetry sending Lambda
- `requirements.txt` - Python dependencies

### Telemetry (`telemetry/`)
- `kinesis_producer.py` - Telemetry data streaming helper
- `glue_schema.py` - Glue Data Catalog setup script
- `athena_queries.sql` - 14 SQL queries for analytics

### Scripts (`scripts/`)
- `upload_images.py` - Batch image upload and load testing
- `benchmark.py` - Performance measurement and reporting
- `test_pipeline.py` - End-to-end pipeline testing

---

## 🚀 **STEP-BY-STEP SETUP GUIDE**

### **Week 1: Wait for Infrastructure (BLOCKED)**

**Status**: Waiting for Karthik to complete infrastructure setup

**Actions While Waiting**:
1. Review Lambda function code
2. Prepare test data (sample images and JSON metadata)
3. Review Step Functions workflow design
4. Coordinate with team on timeline

**Checkpoint**: Wait for Karthik's confirmation that infrastructure is ready.

---

### **Week 2: Lambda Functions & Step Functions Testing**

#### **Day 1: Lambda Function Testing**

**Step 1: Verify Infrastructure Ready (15 minutes)**
1. Confirm with Karthik that infrastructure is complete
2. Verify in AWS Console:
   - S3 buckets exist
   - Lambda functions deployed
   - IAM roles attached

**Step 2: Test Individual Lambda Functions (2 hours)**

**Test 1: validate_metadata Lambda**
1. Go to Lambda Console → `radstream-validate-metadata`
2. Go to Test tab
3. Create test event:
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
4. Click "Test"
5. Verify response:
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Metadata validated successfully\"}",
  "status": "SUCCESS"
}
```
6. Check CloudWatch logs for any errors

**Test 2: prepare_tensors Lambda**
1. Upload a test image to S3 first:
```bash
aws s3 cp test-image.jpg s3://radstream-images-{account-id}/test.jpg
```
2. Go to Lambda Console → `radstream-prepare-tensors`
3. Create test event:
```json
{
  "s3_path": "s3://radstream-images-{account-id}/test.jpg",
  "metadata": {
    "study_id": "test-001",
    "view": "PA",
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```
4. Click "Test"
5. Verify response includes `tensor_shape` and `preprocessed_data_ref`
6. Check CloudWatch logs

**Test 3: store_results Lambda**
1. Go to Lambda Console → `radstream-store-results`
2. Create test event:
```json
{
  "s3_path": "s3://radstream-images-{account-id}/test.jpg",
  "metadata": {
    "study_id": "test-001",
    "view": "PA"
  },
  "inference_results": {
    "findings": "Normal chest X-ray",
    "confidence": 0.95
  }
}
```
3. Click "Test"
4. Verify response includes `results_s3_path`
5. Check S3 results bucket for stored results

**Test 4: send_telemetry Lambda**
1. Go to Lambda Console → `radstream-send-telemetry`
2. Create test event:
```json
{
  "study_id": "test-001",
  "s3_path": "s3://radstream-images-{account-id}/test.jpg",
  "status": "SUCCESS",
  "processing_time_ms": 150.5
}
```
3. Click "Test"
4. Verify response includes success status
5. Check Kinesis stream for telemetry record

**Step 3: Optimize Lambda Configuration (1 hour)**
1. For each Lambda function:
   - Go to Configuration → General configuration
   - Adjust memory: Start with 512 MB, increase if timeout
   - Adjust timeout: 30-60 seconds
   - Test with different configurations
2. Monitor:
   - Duration (should be < 5 seconds)
   - Memory used (should be < 80% of allocated)
   - Errors (should be 0)

---

#### **Day 2: Step Functions Integration**

**Step 4: Test Step Functions Workflow (2 hours)**
1. Go to Step Functions Console → `radstream-pipeline`
2. Click "Start execution"
3. Input:
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
4. Click "Start execution"
5. Monitor execution:
   - Watch each state transition
   - Check for errors
   - Verify all states execute successfully
6. Review execution output
7. Check CloudWatch logs for each Lambda invocation

**Step 5: Test Error Handling (1 hour)**
1. Test with invalid metadata:
```json
{
  "study_id": "test-002",
  "s3_path": "s3://radstream-images-{account-id}/test.jpg",
  "metadata": {
    "study_id": "test-002"
    // Missing required fields
  }
}
```
2. Verify error handling:
   - Check Catch block executes
   - Verify error logged
   - Check error notification

**Step 6: Wait for EKS Endpoint (Coordination)**
1. Coordinate with Mukul for EKS endpoint URL
2. Update Step Functions workflow with EKS endpoint:
   - Go to Step Functions → Edit state machine
   - Update "RunInference" state with EKS endpoint
   - Save changes
3. Test EKS integration:
   - Create test event with EKS endpoint
   - Verify inference call succeeds

---

### **Week 3: Telemetry & Analytics Setup**

#### **Day 1: Glue Data Catalog**

**Step 7: Create Glue Database and Tables (45 minutes)**
```bash
python rahul/telemetry/glue_schema.py
```

**Manual Verification**:
1. Go to Glue Console → Databases
2. Verify database: `radstream_analytics`
3. Go to Tables
4. Verify tables:
   - `telemetry_events`
   - `performance_metrics`
5. Check table schemas match expected format

**Step 8: Run Glue Crawler (30 minutes)**
1. Go to Glue Console → Crawlers
2. If crawler not created, create one:
   - Name: `radstream-telemetry-crawler`
   - Data source: S3 path `s3://radstream-telemetry-{account-id}/raw_telemetry/`
   - IAM role: `RadStreamGlueCrawlerRole`
   - Database: `radstream_analytics`
3. Run crawler
4. Verify crawler completes successfully
5. Check table schemas updated

---

#### **Day 2: Athena Setup**

**Step 9: Configure Athena (1 hour)**
1. Go to Athena Console
2. Create workgroup:
   - Name: `radstream-analytics`
   - Description: "RadStream telemetry analytics"
3. Configure query result location:
   - S3 path: `s3://radstream-telemetry-{account-id}/athena-results/`
4. Test connection:
   - Select database: `radstream_analytics`
   - Run test query:
   ```sql
   SELECT COUNT(*) FROM telemetry_events LIMIT 10;
   ```

**Step 10: Test Athena Queries (1 hour)**
1. Open `rahul/telemetry/athena_queries.sql`
2. Test each query:
   - Query 1: Total events count
   - Query 2: Average processing time
   - Query 3: Events by component
   - Query 4: Daily average inference latency
   - Query 5: Top 5 slowest processing times
   - Query 6: Error events over time
   - Query 7: Distribution of event types
3. Verify queries return expected results
4. Note query execution times and costs

---

#### **Day 3: Telemetry Testing**

**Step 11: Test Kinesis Producer (30 minutes)**
```bash
python rahul/telemetry/kinesis_producer.py
```

**Manual Verification**:
1. Go to Kinesis Console → Streams → `radstream-telemetry`
2. Check "Monitoring" tab for incoming records
3. Go to Firehose Console → `radstream-telemetry-firehose`
4. Check "Monitoring" tab for delivery records
5. Wait 5-10 minutes for Firehose buffer
6. Check S3 bucket: `radstream-telemetry-{account-id}/raw_telemetry/`
7. Verify data files exist

**Step 12: Verify Data Flow (30 minutes)**
1. Upload test image to S3
2. Trigger Step Functions workflow
3. Monitor telemetry flow:
   - Check Kinesis stream for records
   - Check Firehose delivery
   - Check S3 destination
   - Query Athena for telemetry events
4. Verify end-to-end data flow working

---

### **Week 3-4: End-to-End Testing**

#### **Day 1: Pipeline Testing**

**Step 13: Comprehensive Pipeline Test (2-3 hours)**
```bash
python rahul/scripts/test_pipeline.py --comprehensive --study-id TEST-001
```

**Manual Verification**:
1. **Upload Test Image**:
   ```bash
   aws s3 cp test-image.jpg s3://radstream-images-{account-id}/test/TEST-001.jpg
   ```

2. **Monitor Step Functions**:
   - Go to Step Functions Console
   - Watch execution in real-time
   - Verify all states execute

3. **Check Lambda Logs**:
   - Go to CloudWatch Logs
   - Check each Lambda function's logs
   - Verify no errors

4. **Verify EKS Inference**:
   - Check EKS pod logs (coordinate with Mukul)
   - Verify inference call succeeded

5. **Check Results**:
   - Go to S3 Console → `radstream-results-{account-id}`
   - Verify results file exists
   - Check result content

6. **Verify Telemetry**:
   - Query Athena for telemetry events
   - Verify events for TEST-001 study

**Step 14: Upload Script Testing (30 minutes)**
```bash
python rahul/scripts/upload_images.py --image_dir ./test-images --num-images 10
```

**Manual Verification**:
1. Verify images uploaded to S3
2. Verify JSON metadata files created
3. Verify Step Functions executions triggered
4. Check CloudWatch logs

---

### **Week 4-5: Performance Benchmarking**

#### **Day 1-2: Benchmarking**

**Step 15: Run Performance Benchmarks (2-3 hours)**
```bash
python rahul/scripts/benchmark.py \
  --image_dir ./test-images \
  --num-studies 50 \
  --concurrent 5
```

**What to Measure**:
1. **End-to-End Latency**:
   - p50, p95, p99 latencies
   - Average latency
   - Min/Max latency

2. **Throughput**:
   - Images processed per minute
   - Sustained throughput
   - Peak throughput

3. **Error Rate**:
   - Total errors
   - Error percentage
   - Error types

4. **Cost Metrics**:
   - Lambda invocation costs
   - Step Functions costs
   - S3 storage costs
   - Kinesis costs

**Step 16: Analyze Results (1 hour)**
1. Review benchmark output
2. Identify bottlenecks:
   - Long-running Lambda functions
   - Slow Step Functions transitions
   - S3 latency issues
   - Kinesis throughput limits
3. Document findings

---

### **Week 5-6: Optimization**

#### **Day 1-2: Performance Tuning**

**Step 17: Optimize Lambda Functions (2 hours)**
1. Based on benchmark results:
   - Increase memory for CPU-intensive functions
   - Optimize code for faster execution
   - Use Lambda layers for dependencies
   - Enable Lambda provisioned concurrency if needed
2. Re-test after optimization
3. Measure improvement

**Step 18: Optimize Step Functions (1 hour)**
1. Review workflow design
2. Optimize state transitions
3. Reduce unnecessary waits
4. Test optimized workflow

**Step 19: A/B Testing Execution (2-3 hours)**
1. **Test S3 Standard vs S3 Express**:
   - Upload same images to both
   - Measure read latency
   - Compare costs

2. **Test Different Lambda Configurations**:
   - Test with different memory sizes
   - Test with different timeout values
   - Measure performance impact

3. **Test Batch Size Optimization**:
   - Test different batch sizes
   - Measure throughput impact

4. Document all A/B test results

---

### **Week 8: Documentation**

**Step 20: Technical Documentation (4-5 hours)**
1. Document performance findings
2. Create technical reports:
   - Performance benchmarks
   - Optimization results
   - Cost analysis
   - A/B test comparisons
3. Prepare presentation data
4. Create diagrams:
   - Data flow diagram
   - Performance metrics charts
   - Cost breakdown charts

---

## 📊 **Performance Targets**

- **End-to-end latency**: < 5 seconds (p95)
- **Throughput**: 10+ images/minute sustained
- **Cost per image**: < $0.002
- **Success rate**: > 99%

## 🔗 **Dependencies**

- **Depends on Karthik**: Infrastructure setup (Week 1-2) - BLOCKS YOU
- **Depends on Mukul**: EKS endpoint URL (Week 2-3) - BLOCKS Step Functions integration
- **Provides to Karthik**: Telemetry data for dashboards (Week 4-5)
- **Provides to Mukul**: Model container requirements (Week 3)

## 📈 **A/B Testing Scenarios**

1. **S3 Standard vs S3 Express One Zone**
2. **Autoscaling on vs off** (coordinate with Mukul)
3. **Different Lambda memory configurations**
4. **Batch size optimization**

## 🛠️ **Development Workflow**

1. Create feature branch: `git checkout -b feature/rahul-description`
2. Make changes and test locally
3. Push and create PR to `develop`
4. Request review from team members
5. Merge after approval

## 📞 **Contact**

- **Role**: Data & Serving Performance Lead
- **Focus**: Pipeline performance, data flow, analytics

---

**Remember**: Wait for Karthik's infrastructure setup before starting. Once infrastructure is ready, you can proceed with Lambda testing! 🚀