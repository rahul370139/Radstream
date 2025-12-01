#!/usr/bin/env python3
"""
End-to-end test script for RadStream pipeline with Triton inference
Tests the complete flow: S3 upload → Step Functions → Lambda → Triton → Results
"""
import boto3
import json
import time
import uuid
import argparse
from datetime import datetime, timezone
from typing import Dict, Any
from botocore.exceptions import ClientError
from PIL import Image
import io

class EndToEndTritonTester:
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.stepfunctions_client = boto3.client('stepfunctions', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            self.images_bucket = f'radstream-images-{self.account_id}'
            self.results_bucket = f'radstream-results-{self.account_id}'
            self.step_function_arn = f'arn:aws:states:{self.region}:{self.account_id}:stateMachine:radstream-pipeline'
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def create_test_image(self, width: int = 224, height: int = 224) -> bytes:
        """Create a test grayscale image"""
        image = Image.new('L', (width, height), color=128)  # Grayscale
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        return img_buffer.getvalue()
    
    def create_test_metadata(self, study_id: str) -> Dict[str, Any]:
        """Create test metadata JSON"""
        # Use proper ISO 8601 format with Z suffix (not +00:00Z)
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        return {
            'study_id': study_id,
            'view': 'PA',
            'timestamp': timestamp,
            'patient_id': f'PAT-{study_id}',
            'modality': 'X-RAY',
            'body_part': 'CHEST'
        }
    
    def upload_test_study(self, study_id: str, prefix: str = 'images/') -> Dict[str, Any]:
        """Upload test image and metadata to S3"""
        try:
            image_data = self.create_test_image()
            metadata = self.create_test_metadata(study_id)
            
            image_key = f'{prefix}{study_id}.png'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=image_key,
                Body=image_data,
                ContentType='image/png',
                ServerSideEncryption='AES256'
            )
            
            metadata_key = f'{prefix}{study_id}.json'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            return {
                'success': True,
                'study_id': study_id,
                'image_key': image_key,
                'metadata_key': metadata_key
            }
        except Exception as e:
            return {
                'success': False,
                'study_id': study_id,
                'error': str(e)
            }
    
    def wait_for_execution(self, execution_arn: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for Step Functions execution to complete"""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            response = self.stepfunctions_client.describe_execution(executionArn=execution_arn)
            status = response['status']
            if status != 'RUNNING':
                output = {}
                if 'output' in response:
                    try:
                        output = json.loads(response['output'])
                    except:
                        output = {'raw': response.get('output', '')}
                
                return {
                    'success': status == 'SUCCEEDED',
                    'status': status,
                    'output': output
                }
            print(f"   ⏳ Execution RUNNING... waiting...")
            time.sleep(5)
        
        return {
            'success': False,
            'status': 'TIMED_OUT',
            'error': 'Execution timed out'
        }
    
    def check_results_in_s3(self, study_id: str) -> Dict[str, Any]:
        """Check if results were stored in S3"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.results_bucket,
                Prefix=f'results/{study_id}/'
            )
            if response.get('Contents'):
                return {
                    'success': True,
                    'results_found': True,
                    'result_count': len(response['Contents']),
                    'files': [obj['Key'] for obj in response['Contents']]
                }
            else:
                return {
                    'success': False,
                    'results_found': False
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_test(self, study_id: str = None, auto_trigger: bool = True) -> Dict[str, Any]:
        """Run end-to-end test"""
        if not study_id:
            study_id = f'E2E-TRITON-{uuid.uuid4().hex[:8].upper()}'
        
        print("\n" + "=" * 60)
        print("🧪 END-TO-END TRITON PIPELINE TEST")
        print("=" * 60)
        print(f"Study ID: {study_id}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60 + "\n")
        
        results = {
            'study_id': study_id,
            'timestamp': datetime.now().isoformat(),
            'steps': []
        }
        
        # Step 1: Upload test study
        print("📤 STEP 1: Upload Test Study to S3")
        upload_result = self.upload_test_study(study_id, prefix='images/')
        results['steps'].append({'name': 'S3 Upload', 'result': upload_result})
        if upload_result['success']:
            print(f"   ✅ Uploaded image: s3://{self.images_bucket}/{upload_result['image_key']}")
            print(f"   ✅ Uploaded metadata: s3://{self.images_bucket}/{upload_result['metadata_key']}")
        else:
            print(f"   ❌ Upload failed: {upload_result.get('error')}")
            return results
        
        # Step 2: Wait for EventBridge to trigger Step Functions (or trigger manually)
        print("\n🚀 STEP 2: Step Functions Execution")
        if auto_trigger:
            print("   Waiting for EventBridge to trigger Step Functions...")
            # Poll for execution
            execution_arn = None
            poll_start = time.time()
            while (time.time() - poll_start) < 60:
                list_response = self.stepfunctions_client.list_executions(
                    stateMachineArn=self.step_function_arn,
                    statusFilter='RUNNING',
                    maxResults=10
                )
                for exec_sum in list_response.get('executions', []):
                    if study_id in exec_sum['name']:
                        execution_arn = exec_sum['executionArn']
                        break
                if execution_arn:
                    break
                time.sleep(5)
            
            if not execution_arn:
                print("   ⚠️  Auto-triggered execution not found, checking recent executions...")
                list_response = self.stepfunctions_client.list_executions(
                    stateMachineArn=self.step_function_arn,
                    maxResults=5
                )
                for exec_sum in list_response.get('executions', []):
                    if study_id in exec_sum['name']:
                        execution_arn = exec_sum['executionArn']
                        break
        else:
            # Manual trigger
            input_data = {
                "Records": [{
                    "s3": {
                        "bucket": {"name": self.images_bucket},
                        "object": {"key": upload_result['image_key']}
                    }
                }]
            }
            execution_name = f"e2e-test-{study_id}-{int(time.time())}"
            response = self.stepfunctions_client.start_execution(
                stateMachineArn=self.step_function_arn,
                name=execution_name,
                input=json.dumps(input_data)
            )
            execution_arn = response['executionArn']
        
        if not execution_arn:
            print("   ❌ Could not find or create execution")
            return results
        
        print(f"   ✅ Execution ARN: {execution_arn}")
        
        # Step 3: Wait for completion
        print("\n⏳ STEP 3: Wait for Pipeline Completion")
        execution_result = self.wait_for_execution(execution_arn)
        results['steps'].append({'name': 'Execution', 'result': execution_result})
        
        if execution_result['success']:
            print(f"   ✅ Execution SUCCEEDED")
            print(f"   Output: {json.dumps(execution_result.get('output', {}), indent=2)}")
        else:
            print(f"   ❌ Execution {execution_result.get('status')}: {execution_result.get('error', 'N/A')}")
        
        # Step 4: Check results
        print("\n📦 STEP 4: Check Results in S3")
        s3_results = self.check_results_in_s3(study_id)
        results['steps'].append({'name': 'S3 Results', 'result': s3_results})
        if s3_results.get('results_found'):
            print(f"   ✅ Results found: {s3_results.get('result_count', 0)} files")
            for file_key in s3_results.get('files', [])[:3]:
                print(f"      - {file_key}")
        else:
            print(f"   ⚠️  No results found yet")
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Study ID: {study_id}")
        print(f"Execution Status: {execution_result.get('status', 'N/A')}")
        print(f"Results Found: {s3_results.get('results_found', False)}")
        print("=" * 60 + "\n")
        
        return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test RadStream Pipeline with Triton')
    parser.add_argument('--study-id', type=str, default=None, help='Study ID for test')
    parser.add_argument('--auto-trigger', action='store_true', help='Use EventBridge auto-trigger')
    args = parser.parse_args()
    
    tester = EndToEndTritonTester()
    tester.run_test(args.study_id, args.auto_trigger)

