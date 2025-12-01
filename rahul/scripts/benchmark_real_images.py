#!/usr/bin/env python3
"""
Benchmark Script for RadStream Pipeline using Real Images
Tests end-to-end pipeline with real chest X-ray images from chexagent_chexpert_eval
"""

import boto3
import json
import time
import csv
import argparse
import statistics
import os
import glob
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
import concurrent.futures

class RealImageBenchmark:
    def __init__(self, region: str = 'us-east-1', image_dir: str = None):
        """Initialize benchmark tool with real images"""
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.stepfunctions_client = boto3.client('stepfunctions', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            self.images_bucket = f'radstream-images-{self.account_id}'
            self.results_bucket = f'radstream-results-{self.account_id}'
            self.step_function_arn = f'arn:aws:states:{self.region}:{self.account_id}:stateMachine:radstream-pipeline'
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
        
        # Find real images
        if image_dir:
            self.image_dir = Path(image_dir)
        else:
            # Try to find chexagent_chexpert_eval folder
            script_dir = Path(__file__).parent.parent.parent.parent
            possible_dirs = [
                script_dir / 'chexagent_chexpert_eval' / 'test_samples',
                script_dir.parent / 'chexagent_chexpert_eval' / 'test_samples',
                script_dir / 'chexagent_chexpert_eval' / 'data' / 'images',
                script_dir.parent / 'chexagent_chexpert_eval' / 'data' / 'images',
                Path('/Users/rahul/Downloads/Code scripts/chexagent_chexpert_eval/test_samples'),
                Path('/Users/rahul/Downloads/Code scripts/chexagent_chexpert_eval/data/images'),
            ]
            
            self.image_dir = None
            for dir_path in possible_dirs:
                if dir_path.exists() and dir_path.is_dir():
                    self.image_dir = dir_path
                    break
            
            if not self.image_dir:
                raise FileNotFoundError("Could not find chexagent_chexpert_eval/test_samples or data/images directory")
        
        print(f"Using image directory: {self.image_dir}")
        
        # Find all images
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        self.image_files = []
        for ext in image_extensions:
            self.image_files.extend(list(self.image_dir.glob(ext)))
        
        if not self.image_files:
            raise FileNotFoundError(f"No images found in {self.image_dir}")
        
        print(f"Found {len(self.image_files)} images")
    
    def create_metadata(self, study_id: str, image_path: Path) -> Dict[str, Any]:
        """Create metadata JSON for a study"""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        return {
            'study_id': study_id,
            'view': 'PA',  # Default view
            'timestamp': timestamp,
            'patient_id': f'PAT-{study_id}',
            'modality': 'X-RAY',
            'body_part': 'CHEST',
            'source_file': str(image_path.name)
        }
    
    def upload_study(self, study_id: str, image_path: Path) -> Dict[str, Any]:
        """Upload a single study (image + metadata) to S3"""
        start_time = time.time()
        
        try:
            # Read image file
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Create metadata
            metadata = self.create_metadata(study_id, image_path)
            
            # Determine file extension
            ext = image_path.suffix.lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                ext = '.png'  # Default to PNG
            
            # Upload image
            image_key = f'images/{study_id}{ext}'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=image_key,
                Body=image_data,
                ContentType=f'image/{ext[1:]}',
                ServerSideEncryption='AES256'
            )
            
            # Upload metadata
            metadata_key = f'images/{study_id}.json'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            upload_time = time.time() - start_time
            
            return {
                'success': True,
                'study_id': study_id,
                'image_key': image_key,
                'metadata_key': metadata_key,
                'upload_time': upload_time,
                'image_size': len(image_data)
            }
        except Exception as e:
            return {
                'success': False,
                'study_id': study_id,
                'error': str(e),
                'upload_time': time.time() - start_time
            }
    
    def wait_for_execution(self, study_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for Step Functions execution to complete"""
        start_time = time.time()
        upload_timestamp = time.time()
        
        # Poll for execution - EventBridge auto-triggers, so look for recent executions
        max_poll_time = 120  # Poll for 120 seconds to find execution
        poll_start = time.time()
        
        execution_arn = None
        last_checked_execution = None
        
        while (time.time() - poll_start) < max_poll_time:
            try:
                # List recent executions - check RUNNING first, then SUCCEEDED
                for status in ['RUNNING', 'SUCCEEDED', 'FAILED']:
                    response = self.stepfunctions_client.list_executions(
                        stateMachineArn=self.step_function_arn,
                        maxResults=100,  # Check more executions
                        statusFilter=status
                    )
                    
                    # Find execution that started after our upload
                    for exec_sum in response.get('executions', []):
                        exec_start = exec_sum['startDate'].timestamp()
                        time_diff = exec_start - upload_timestamp
                        
                        # Check if execution started within 60 seconds of upload
                        if -5 <= time_diff <= 60:  # Allow 5 seconds before (clock skew) and 60 after
                            # Check if it's likely our execution by checking input
                            try:
                                exec_details = self.stepfunctions_client.describe_execution(
                                    executionArn=exec_sum['executionArn']
                                )
                                input_data = json.loads(exec_details.get('input', '{}'))
                                input_str = json.dumps(input_data)
                                
                                # Check if input contains our study_id or image key
                                if study_id in input_str or f'images/{study_id}' in input_str:
                                    execution_arn = exec_sum['executionArn']
                                    break
                                # Also check if key matches our image file pattern
                                key = input_data.get('key', '')
                                if study_id in key:
                                    execution_arn = exec_sum['executionArn']
                                    break
                            except Exception as e:
                                # If we can't check input, use the most recent matching one
                                if not execution_arn and time_diff >= 0:
                                    execution_arn = exec_sum['executionArn']
                    
                    if execution_arn:
                        break
                
                if execution_arn:
                    break
                
                # If no execution found yet, wait a bit longer
                time.sleep(5)
            except Exception as e:
                print(f"   ⚠️  Error polling for execution: {e}")
                time.sleep(5)
        
        if not execution_arn:
            # Last attempt: get the most recent execution that started after upload
            try:
                response = self.stepfunctions_client.list_executions(
                    stateMachineArn=self.step_function_arn,
                    maxResults=5
                )
                for exec_sum in response.get('executions', []):
                    exec_start = exec_sum['startDate'].timestamp()
                    if 0 <= (exec_start - upload_timestamp) <= 90:
                        execution_arn = exec_sum['executionArn']
                        print(f"   ⚠️  Using most recent execution (may not be exact match)")
                        break
            except:
                pass
        
        if not execution_arn:
            return {
                'success': False,
                'error': 'Execution not found',
                'processing_time': time.time() - start_time
            }
        
        # Wait for completion
        while (time.time() - start_time) < timeout:
            try:
                exec_response = self.stepfunctions_client.describe_execution(executionArn=execution_arn)
                status = exec_response['status']
                
                if status != 'RUNNING':
                    processing_time = time.time() - start_time
                    return {
                        'success': status == 'SUCCEEDED',
                        'status': status,
                        'processing_time': processing_time,
                        'execution_arn': execution_arn
                    }
                
                time.sleep(3)
            except Exception as e:
                print(f"Error checking execution: {e}")
                time.sleep(3)
        
        return {
            'success': False,
            'error': 'Timeout waiting for execution',
            'processing_time': timeout
        }
    
    def check_results(self, study_id: str) -> bool:
        """Check if results exist in S3"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.results_bucket,
                Prefix=f'results/{study_id}/'
            )
            return len(response.get('Contents', [])) > 0
        except:
            return False
    
    def run_single_benchmark(self, study_id: str, image_path: Path) -> Dict[str, Any]:
        """Run benchmark for a single image"""
        print(f"\n📤 Testing: {image_path.name} (Study ID: {study_id})")
        
        # Upload study
        upload_result = self.upload_study(study_id, image_path)
        if not upload_result['success']:
            return {
                'study_id': study_id,
                'image_file': str(image_path.name),
                'success': False,
                'error': upload_result.get('error', 'Upload failed'),
                'upload_time': upload_result.get('upload_time', 0),
                'total_time': upload_result.get('upload_time', 0)
            }
        
        print(f"   ✅ Uploaded in {upload_result['upload_time']:.2f}s")
        
        # Wait for pipeline execution
        print(f"   ⏳ Waiting for pipeline execution...")
        execution_result = self.wait_for_execution(study_id)
        
        if execution_result['success']:
            print(f"   ✅ Pipeline completed in {execution_result['processing_time']:.2f}s")
            
            # Check results
            if self.check_results(study_id):
                print(f"   ✅ Results stored in S3")
            else:
                print(f"   ⚠️  Results not found in S3 yet")
        else:
            print(f"   ❌ Pipeline failed: {execution_result.get('error', 'Unknown error')}")
        
        total_time = upload_result['upload_time'] + execution_result.get('processing_time', 0)
        
        return {
            'study_id': study_id,
            'image_file': str(image_path.name),
            'image_size': upload_result.get('image_size', 0),
            'success': execution_result['success'],
            'upload_time': upload_result['upload_time'],
            'processing_time': execution_result.get('processing_time', 0),
            'total_time': total_time,
            'status': execution_result.get('status', 'UNKNOWN'),
            'error': execution_result.get('error')
        }
    
    def run_benchmark(self, num_images: int = 10, sequential: bool = True) -> List[Dict[str, Any]]:
        """Run benchmark with specified number of images"""
        # Select images
        selected_images = self.image_files[:num_images]
        
        print("=" * 70)
        print(f"🚀 RADSTREAM PIPELINE BENCHMARK")
        print("=" * 70)
        print(f"Images to test: {len(selected_images)}")
        print(f"Mode: {'Sequential' if sequential else 'Concurrent'}")
        print("=" * 70)
        
        results = []
        
        if sequential:
            # Run sequentially to minimize cost
            for i, image_path in enumerate(selected_images, 1):
                study_id = f'BENCH-{i:03d}-{int(time.time())}'
                result = self.run_single_benchmark(study_id, image_path)
                results.append(result)
                
                # Small delay between tests
                if i < len(selected_images):
                    time.sleep(2)
        else:
            # Run concurrently (use with caution for cost)
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for i, image_path in enumerate(selected_images, 1):
                    study_id = f'BENCH-{i:03d}-{int(time.time())}'
                    future = executor.submit(self.run_single_benchmark, study_id, image_path)
                    futures.append(future)
                
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
        
        return results
    
    def generate_report(self, results: List[Dict[str, Any]], output_file: str = 'benchmark_results.csv'):
        """Generate benchmark report"""
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]
        
        print("\n" + "=" * 70)
        print("📊 BENCHMARK RESULTS")
        print("=" * 70)
        print(f"Total Tests: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print(f"Success Rate: {len(successful)/len(results)*100:.1f}%")
        
        if successful:
            processing_times = [r['processing_time'] for r in successful]
            total_times = [r['total_time'] for r in successful]
            
            print(f"\n⏱️  Processing Time (Pipeline):")
            print(f"   Average: {statistics.mean(processing_times):.2f}s")
            print(f"   Median (p50): {statistics.median(processing_times):.2f}s")
            if len(processing_times) >= 2:
                sorted_times = sorted(processing_times)
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                print(f"   P95: {sorted_times[min(p95_idx, len(sorted_times)-1)]:.2f}s")
                print(f"   P99: {sorted_times[min(p99_idx, len(sorted_times)-1)]:.2f}s")
            
            print(f"\n⏱️  Total Time (Upload + Pipeline):")
            print(f"   Average: {statistics.mean(total_times):.2f}s")
            print(f"   Median (p50): {statistics.median(total_times):.2f}s")
            if len(total_times) >= 2:
                sorted_total = sorted(total_times)
                p95_idx = int(len(sorted_total) * 0.95)
                p99_idx = int(len(sorted_total) * 0.99)
                print(f"   P95: {sorted_total[min(p95_idx, len(sorted_total)-1)]:.2f}s")
                print(f"   P99: {sorted_total[min(p99_idx, len(sorted_total)-1)]:.2f}s")
            
            # Throughput
            total_time = sum(total_times)
            throughput = len(successful) / total_time if total_time > 0 else 0
            print(f"\n📈 Throughput: {throughput:.2f} studies/second")
            print(f"   ({len(successful)} studies in {total_time:.2f}s)")
        
        if failed:
            print(f"\n❌ Failed Tests:")
            for r in failed:
                print(f"   - {r['study_id']}: {r.get('error', 'Unknown error')}")
        
        # Save to CSV
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'study_id', 'image_file', 'image_size', 'success', 
                'upload_time', 'processing_time', 'total_time', 'status', 'error'
            ])
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        return {
            'total': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful)/len(results)*100 if results else 0,
            'avg_processing_time': statistics.mean(processing_times) if successful else 0,
            'p95_processing_time': sorted_times[min(p95_idx, len(sorted_times)-1)] if successful and len(processing_times) >= 2 else 0,
            'p99_processing_time': sorted_times[min(p99_idx, len(sorted_times)-1)] if successful and len(processing_times) >= 2 else 0,
        }

def main():
    parser = argparse.ArgumentParser(description='Benchmark RadStream pipeline with real images')
    parser.add_argument('--num-images', type=int, default=10, help='Number of images to test')
    parser.add_argument('--image-dir', type=str, help='Directory containing images')
    parser.add_argument('--output', type=str, default='benchmark_real_images.csv', help='Output CSV file')
    parser.add_argument('--concurrent', action='store_true', help='Run tests concurrently (increases cost)')
    
    args = parser.parse_args()
    
    try:
        benchmark = RealImageBenchmark(image_dir=args.image_dir)
        results = benchmark.run_benchmark(num_images=args.num_images, sequential=not args.concurrent)
        stats = benchmark.generate_report(results, args.output)
        
        print("\n🎉 Benchmark completed!")
        return stats
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()

