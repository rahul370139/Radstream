#!/usr/bin/env python3
"""
Benchmark Script for RadStream Medical Imaging Pipeline
Measures end-to-end pipeline performance and generates performance reports
"""

import boto3
import json
import time
import csv
import argparse
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
import concurrent.futures
import threading

class RadStreamBenchmark:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize benchmark tool"""
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.stepfunctions_client = boto3.client('stepfunctions', region_name=region)
        self.athena_client = boto3.client('athena', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            self.images_bucket = f'radstream-images-{self.account_id}'
            self.results_bucket = f'radstream-results-{self.account_id}'
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def create_test_study(self, study_id: str) -> Dict[str, Any]:
        """
        Create a test study with image and metadata
        
        Args:
            study_id: Study identifier
            
        Returns:
            Dict with study information
        """
        from PIL import Image
        import io
        import uuid
        
        # Create test image
        image = Image.new('RGB', (512, 512), color=(128, 128, 128))
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG', quality=85)
        image_data = img_buffer.getvalue()
        
        # Create metadata
        metadata = {
            'study_id': study_id,
            'view': 'PA',
            'timestamp': datetime.utcnow().isoformat(),
            'patient_id': f'PAT-{uuid.uuid4().hex[:8].upper()}',
            'modality': 'X-RAY',
            'body_part': 'CHEST'
        }
        
        return {
            'study_id': study_id,
            'image_data': image_data,
            'metadata': metadata
        }
    
    def upload_study(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload a study to S3
        
        Args:
            study: Study data
            
        Returns:
            Dict with upload results
        """
        start_time = time.time()
        
        try:
            study_id = study['study_id']
            
            # Upload image
            image_key = f'images/{study_id}/{study_id}.jpg'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=image_key,
                Body=study['image_data'],
                ContentType='image/jpeg',
                ServerSideEncryption='AES256'
            )
            
            # Upload metadata
            metadata_key = f'images/{study_id}/{study_id}.json'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=metadata_key,
                Body=json.dumps(study['metadata'], indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            upload_time = time.time() - start_time
            
            return {
                'success': True,
                'study_id': study_id,
                'upload_time': upload_time,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'study_id': study['study_id'],
                'error': str(e),
                'upload_time': time.time() - start_time,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def wait_for_pipeline_completion(self, study_id: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for pipeline to complete processing
        
        Args:
            study_id: Study identifier
            timeout: Timeout in seconds
            
        Returns:
            Dict with completion results
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if results exist in S3
                results_key = f"results/{study_id}/"
                response = self.s3_client.list_objects_v2(
                    Bucket=self.results_bucket,
                    Prefix=results_key
                )
                
                if response.get('Contents'):
                    # Results found
                    processing_time = time.time() - start_time
                    return {
                        'success': True,
                        'study_id': study_id,
                        'processing_time': processing_time,
                        'results_found': True
                    }
                
                # Wait before checking again
                time.sleep(5)
                
            except Exception as e:
                return {
                    'success': False,
                    'study_id': study_id,
                    'error': str(e),
                    'processing_time': time.time() - start_time
                }
        
        # Timeout reached
        return {
            'success': False,
            'study_id': study_id,
            'error': 'Timeout waiting for pipeline completion',
            'processing_time': timeout
        }
    
    def run_single_benchmark(self, study_id: str) -> Dict[str, Any]:
        """
        Run a single benchmark test
        
        Args:
            study_id: Study identifier
            
        Returns:
            Dict with benchmark results
        """
        print(f"Running benchmark for study: {study_id}")
        
        # Create test study
        study = self.create_test_study(study_id)
        
        # Upload study
        upload_result = self.upload_study(study)
        if not upload_result['success']:
            return upload_result
        
        # Wait for pipeline completion
        completion_result = self.wait_for_pipeline_completion(study_id)
        
        # Combine results
        result = {
            'study_id': study_id,
            'upload_success': upload_result['success'],
            'upload_time': upload_result['upload_time'],
            'pipeline_success': completion_result['success'],
            'processing_time': completion_result.get('processing_time', 0),
            'total_time': upload_result['upload_time'] + completion_result.get('processing_time', 0),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if not upload_result['success']:
            result['error'] = upload_result['error']
        elif not completion_result['success']:
            result['error'] = completion_result['error']
        
        return result
    
    def run_concurrent_benchmark(self, num_studies: int, 
                                concurrent_limit: int = 5) -> List[Dict[str, Any]]:
        """
        Run concurrent benchmark tests
        
        Args:
            num_studies: Number of studies to test
            concurrent_limit: Maximum concurrent tests
            
        Returns:
            List of benchmark results
        """
        results = []
        results_lock = threading.Lock()
        
        def benchmark_worker(study_id: str):
            """Worker function for concurrent benchmarks"""
            result = self.run_single_benchmark(study_id)
            
            with results_lock:
                results.append(result)
            
            return result
        
        print(f"Running concurrent benchmark with {num_studies} studies, {concurrent_limit} concurrent...")
        print("=" * 60)
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_limit) as executor:
            # Submit all benchmark tasks
            futures = []
            for i in range(num_studies):
                study_id = f'BENCH-{i+1:06d}'
                future = executor.submit(benchmark_worker, study_id)
                futures.append(future)
            
            # Wait for all benchmarks to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    status = "✅" if result.get('pipeline_success', False) else "❌"
                    print(f"  {status} {result['study_id']}: {result.get('total_time', 0):.2f}s")
                except Exception as e:
                    print(f"  ❌ Benchmark failed: {e}")
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful = sum(1 for r in results if r.get('pipeline_success', False))
        failed = len(results) - successful
        
        if successful > 0:
            processing_times = [r['processing_time'] for r in results if r.get('pipeline_success', False)]
            total_times = [r['total_time'] for r in results if r.get('pipeline_success', False)]
            
            stats = {
                'total_studies': num_studies,
                'successful': successful,
                'failed': failed,
                'success_rate': successful / num_studies * 100,
                'total_time': total_time,
                'avg_processing_time': statistics.mean(processing_times),
                'p50_processing_time': statistics.median(processing_times),
                'p95_processing_time': sorted(processing_times)[int(len(processing_times) * 0.95)],
                'p99_processing_time': sorted(processing_times)[int(len(processing_times) * 0.99)],
                'avg_total_time': statistics.mean(total_times),
                'throughput': num_studies / total_time
            }
        else:
            stats = {
                'total_studies': num_studies,
                'successful': 0,
                'failed': num_studies,
                'success_rate': 0,
                'total_time': total_time,
                'throughput': 0
            }
        
        return results, stats
    
    def query_telemetry_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """
        Query telemetry metrics from Athena
        
        Args:
            start_time: Start time for query
            end_time: End time for query
            
        Returns:
            Dict with telemetry metrics
        """
        try:
            # Query for pipeline performance metrics
            query = f"""
            SELECT 
                stage,
                COUNT(*) as total_events,
                AVG(latency_ms) as avg_latency_ms,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as p50_latency_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) as failed_count
            FROM radstream_analytics.telemetry_events
            WHERE timestamp >= '{start_time.isoformat()}'
                AND timestamp <= '{end_time.isoformat()}'
            GROUP BY stage
            ORDER BY avg_latency_ms
            """
            
            # Execute query
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={
                    'Database': 'radstream_analytics'
                },
                ResultConfiguration={
                    'OutputLocation': f's3://radstream-telemetry-{self.account_id}/athena-results/'
                }
            )
            
            query_execution_id = response['QueryExecutionId']
            
            # Wait for query to complete
            while True:
                response = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
                status = response['QueryExecution']['Status']['State']
                
                if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    break
                
                time.sleep(2)
            
            if status == 'SUCCEEDED':
                # Get query results
                response = self.athena_client.get_query_results(QueryExecutionId=query_execution_id)
                
                # Parse results
                metrics = {}
                for row in response['ResultSet']['Rows'][1:]:  # Skip header
                    stage = row['Data'][0]['VarCharValue']
                    metrics[stage] = {
                        'total_events': int(row['Data'][1]['VarCharValue']),
                        'avg_latency_ms': float(row['Data'][2]['VarCharValue']),
                        'p50_latency_ms': float(row['Data'][3]['VarCharValue']),
                        'p95_latency_ms': float(row['Data'][4]['VarCharValue']),
                        'success_count': int(row['Data'][5]['VarCharValue']),
                        'failed_count': int(row['Data'][6]['VarCharValue'])
                    }
                
                return metrics
            else:
                print(f"Query failed with status: {status}")
                return {}
                
        except Exception as e:
            print(f"Error querying telemetry metrics: {e}")
            return {}
    
    def generate_report(self, results: List[Dict[str, Any]], 
                       stats: Dict[str, Any], output_file: str) -> None:
        """
        Generate benchmark report
        
        Args:
            results: Benchmark results
            stats: Statistics
            output_file: Output file path
        """
        # Generate CSV report
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['study_id', 'upload_success', 'upload_time', 'pipeline_success', 
                         'processing_time', 'total_time', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'study_id': result['study_id'],
                    'upload_success': result['upload_success'],
                    'upload_time': result['upload_time'],
                    'pipeline_success': result['pipeline_success'],
                    'processing_time': result.get('processing_time', 0),
                    'total_time': result.get('total_time', 0),
                    'timestamp': result['timestamp']
                })
        
        # Generate summary report
        summary_file = output_file.replace('.csv', '_summary.txt')
        with open(summary_file, 'w') as f:
            f.write("RadStream Pipeline Benchmark Report\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Test Date: {datetime.utcnow().isoformat()}\n")
            f.write(f"Total Studies: {stats['total_studies']}\n")
            f.write(f"Successful: {stats['successful']}\n")
            f.write(f"Failed: {stats['failed']}\n")
            f.write(f"Success Rate: {stats['success_rate']:.1f}%\n")
            f.write(f"Total Test Time: {stats['total_time']:.2f}s\n")
            f.write(f"Throughput: {stats['throughput']:.2f} studies/second\n\n")
            
            if 'avg_processing_time' in stats:
                f.write("Processing Time Statistics:\n")
                f.write(f"  Average: {stats['avg_processing_time']:.2f}s\n")
                f.write(f"  P50: {stats['p50_processing_time']:.2f}s\n")
                f.write(f"  P95: {stats['p95_processing_time']:.2f}s\n")
                f.write(f"  P99: {stats['p99_processing_time']:.2f}s\n")
        
        print(f"Report saved to: {output_file}")
        print(f"Summary saved to: {summary_file}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Benchmark RadStream pipeline performance')
    parser.add_argument('--num-studies', type=int, default=10, help='Number of studies to test')
    parser.add_argument('--concurrent', type=int, default=5, help='Number of concurrent tests')
    parser.add_argument('--output', type=str, default='benchmark_results.csv', help='Output file')
    parser.add_argument('--single', action='store_true', help='Run single study test')
    
    args = parser.parse_args()
    
    # Initialize benchmark tool
    benchmark = RadStreamBenchmark()
    
    if args.single:
        # Run single study test
        result = benchmark.run_single_benchmark('SINGLE-TEST-001')
        print(f"Single test result: {result}")
    else:
        # Run concurrent benchmark
        results, stats = benchmark.run_concurrent_benchmark(args.num_studies, args.concurrent)
        
        # Print summary
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        print(f"Total Studies: {stats['total_studies']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Total Time: {stats['total_time']:.2f}s")
        print(f"Throughput: {stats['throughput']:.2f} studies/second")
        
        if 'avg_processing_time' in stats:
            print(f"Avg Processing Time: {stats['avg_processing_time']:.2f}s")
            print(f"P95 Processing Time: {stats['p95_processing_time']:.2f}s")
        
        # Generate report
        benchmark.generate_report(results, stats, args.output)
    
    print("\n🎉 Benchmark completed!")

if __name__ == "__main__":
    main()
