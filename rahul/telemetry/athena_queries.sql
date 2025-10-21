-- RadStream Medical Imaging Pipeline - Athena Queries
-- SQL queries for analyzing telemetry data and performance metrics

-- =====================================================
-- BASIC TELEMETRY ANALYSIS
-- =====================================================

-- 1. Overall pipeline performance summary
SELECT 
    stage,
    COUNT(*) as total_events,
    AVG(latency_ms) as avg_latency_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as p50_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency_ms,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
GROUP BY stage
ORDER BY avg_latency_ms;

-- 2. Hourly throughput analysis
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as total_events,
    COUNT(DISTINCT study_id) as unique_studies,
    AVG(latency_ms) as avg_latency_ms
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour;

-- 3. Error analysis by stage
SELECT 
    stage,
    error_code,
    COUNT(*) as error_count,
    AVG(latency_ms) as avg_latency_before_error
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND status IN ('failed', 'error')
GROUP BY stage, error_code
ORDER BY error_count DESC;

-- =====================================================
-- PERFORMANCE METRICS ANALYSIS
-- =====================================================

-- 4. Resource utilization trends
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(cpu_usage) as avg_cpu_usage,
    AVG(memory_usage) as avg_memory_usage,
    AVG(gpu_usage) as avg_gpu_usage,
    AVG(throughput) as avg_throughput
FROM radstream_analytics.performance_metrics
WHERE year = '2024' AND month = '01' AND day = '15'
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour;

-- 5. Stage-wise performance comparison
SELECT 
    stage,
    AVG(latency_ms) as avg_latency,
    STDDEV(latency_ms) as latency_stddev,
    MIN(latency_ms) as min_latency,
    MAX(latency_ms) as max_latency,
    COUNT(*) as sample_count
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND status = 'success'
GROUP BY stage
ORDER BY avg_latency;

-- =====================================================
-- A/B TESTING QUERIES
-- =====================================================

-- 6. S3 Standard vs S3 Express One Zone comparison
-- (This would require additional metadata in the telemetry)
SELECT 
    CASE 
        WHEN metadata LIKE '%s3_standard%' THEN 'S3_Standard'
        WHEN metadata LIKE '%s3_express%' THEN 'S3_Express_OneZone'
        ELSE 'Unknown'
    END as storage_type,
    stage,
    AVG(latency_ms) as avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
    COUNT(*) as event_count
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND stage IN ('prepare_tensors', 'store_results')
GROUP BY 
    CASE 
        WHEN metadata LIKE '%s3_standard%' THEN 'S3_Standard'
        WHEN metadata LIKE '%s3_express%' THEN 'S3_Express_OneZone'
        ELSE 'Unknown'
    END, stage
ORDER BY storage_type, stage;

-- 7. Autoscaling on vs off comparison
-- (This would require additional metadata in the telemetry)
SELECT 
    CASE 
        WHEN metadata LIKE '%autoscaling_on%' THEN 'Autoscaling_On'
        WHEN metadata LIKE '%autoscaling_off%' THEN 'Autoscaling_Off'
        ELSE 'Unknown'
    END as autoscaling_mode,
    AVG(latency_ms) as avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
    COUNT(*) as event_count
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND stage = 'inference'
GROUP BY 
    CASE 
        WHEN metadata LIKE '%autoscaling_on%' THEN 'Autoscaling_On'
        WHEN metadata LIKE '%autoscaling_off%' THEN 'Autoscaling_Off'
        ELSE 'Unknown'
    END
ORDER BY autoscaling_mode;

-- =====================================================
-- COST ANALYSIS QUERIES
-- =====================================================

-- 8. Cost per 1000 images processed
-- (This would require cost data from AWS Cost Explorer or custom metrics)
SELECT 
    DATE_TRUNC('day', timestamp) as processing_date,
    COUNT(DISTINCT study_id) as unique_studies,
    COUNT(*) as total_events,
    -- Estimated cost calculation (would need actual AWS pricing)
    COUNT(DISTINCT study_id) * 0.002 as estimated_cost_usd
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01'
    AND stage = 'store_results'
GROUP BY DATE_TRUNC('day', timestamp)
ORDER BY processing_date;

-- 9. Resource efficiency metrics
SELECT 
    stage,
    AVG(cpu_usage) as avg_cpu_usage,
    AVG(memory_usage) as avg_memory_usage,
    AVG(gpu_usage) as avg_gpu_usage,
    AVG(latency_ms) as avg_latency_ms,
    -- Efficiency score (lower is better)
    (AVG(cpu_usage) + AVG(memory_usage) + AVG(gpu_usage)) / 3 as resource_efficiency_score
FROM radstream_analytics.performance_metrics
WHERE year = '2024' AND month = '01' AND day = '15'
GROUP BY stage
ORDER BY resource_efficiency_score;

-- =====================================================
-- SECURITY ANALYSIS QUERIES
-- =====================================================

-- 10. Security event analysis
-- (This would require integration with WAF and GuardDuty logs)
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as security_events,
    COUNT(DISTINCT study_id) as affected_studies
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND (error_code LIKE '%SECURITY%' OR error_code LIKE '%WAF%' OR error_code LIKE '%GUARDDUTY%')
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour;

-- =====================================================
-- DASHBOARD QUERIES
-- =====================================================

-- 11. Real-time dashboard metrics
SELECT 
    'Total Events' as metric_name,
    COUNT(*) as metric_value,
    'count' as metric_type
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'

UNION ALL

SELECT 
    'Success Rate' as metric_name,
    (SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as metric_value,
    'percentage' as metric_type
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'

UNION ALL

SELECT 
    'Avg Latency (ms)' as metric_name,
    AVG(latency_ms) as metric_value,
    'latency' as metric_type
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND status = 'success'

UNION ALL

SELECT 
    'P95 Latency (ms)' as metric_name,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as metric_value,
    'latency' as metric_type
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND status = 'success';

-- 12. Study-level performance summary
SELECT 
    study_id,
    MIN(timestamp) as start_time,
    MAX(timestamp) as end_time,
    MAX(timestamp) - MIN(timestamp) as total_processing_time,
    COUNT(*) as total_events,
    AVG(latency_ms) as avg_latency_ms,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_events,
    SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) as failed_events
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
GROUP BY study_id
ORDER BY total_processing_time DESC
LIMIT 100;

-- =====================================================
-- MAINTENANCE QUERIES
-- =====================================================

-- 13. Data quality check
SELECT 
    'Missing Study IDs' as check_name,
    COUNT(*) as issue_count
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND (study_id IS NULL OR study_id = '')

UNION ALL

SELECT 
    'Invalid Timestamps' as check_name,
    COUNT(*) as issue_count
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND timestamp IS NULL

UNION ALL

SELECT 
    'Negative Latencies' as check_name,
    COUNT(*) as issue_count
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'
    AND latency_ms < 0;

-- 14. Table statistics
SELECT 
    'telemetry_events' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT study_id) as unique_studies,
    MIN(timestamp) as earliest_timestamp,
    MAX(timestamp) as latest_timestamp
FROM radstream_analytics.telemetry_events
WHERE year = '2024' AND month = '01' AND day = '15'

UNION ALL

SELECT 
    'performance_metrics' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT study_id) as unique_studies,
    MIN(timestamp) as earliest_timestamp,
    MAX(timestamp) as latest_timestamp
FROM radstream_analytics.performance_metrics
WHERE year = '2024' AND month = '01' AND day = '15';
