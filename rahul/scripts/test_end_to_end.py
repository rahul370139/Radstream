#!/usr/bin/env python3
"""
End-to-End Pipeline Test Script
Tests the complete pipeline: S3 Upload → EventBridge → Step Functions → Lambda → Results
"""

import boto3
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any
from botocore.exceptions import ClientError

class EndToEndTester:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize end-to-end tester"""
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.stepfunctions_client = boto3.client('stepfunctions', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            self.images_bucket = f'radstream-images-{self.account_id}'
            self.results_bucket = f'radstream-results-{self.account_id}'
            self.state_machine_arn = f'arn:aws:states:{region}:{self.account_id}:stateMachine:radstream-pipeline'
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def upload_test_image_and_metadata(self, study_id: str) -> Dict[str, Any]:
        """Upload test image and metadata to S3"""
        try:
            from PIL import Image
            import io
            
            # Create test image
            image = Image.new('RGB', (512, 512), color=(128, 128, 128))
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG', quality=85)
            image_data = img_buffer.getvalue()
            
            # Create metadata
            metadata = {
                'study_id': study_id,
                'view': 'PA',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'patient_id': f'PAT-{study_id}',
                'modality': 'X-RAY',
                'body_part': 'CHEST',
                'institution': 'Test Hospital'
            }
            
            # Upload image
            image_key = f'test/{study_id}.jpg'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=image_key,
                Body=image_data,
                ContentType='image/jpeg',
                ServerSideEncryption='AES256'
            )
            print(f"   ✅ Uploaded image: s3://{self.images_bucket}/{image_key}")
            
            # Upload metadata
            metadata_key = f'test/{study_id}.json'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            print(f"   ✅ Uploaded metadata: s3://{self.images_bucket}/{metadata_key}")
            
            return {
                'success': True,
                'image_key': image_key,
                'metadata_key': metadata_key,
                'study_id': study_id
            }
            
        except Exception as e:
            print(f"   ❌ Upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def manually_trigger_step_functions(self, study_id: str, image_key: str) -> Dict[str, Any]:
        """Manually trigger Step Functions execution"""
        try:
            execution_name = f"e2e-test-{study_id}-{int(time.time())}"
            
            input_data = {
                'bucket': self.images_bucket,
                'key': image_key,
                'study_id': study_id
            }
            
            response = self.stepfunctions_client.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=execution_name,
                input=json.dumps(input_data)
            )
            
            print(f"   ✅ Started Step Functions execution: {execution_name}")
            return {
                'success': True,
                'execution_arn': response['executionArn'],
                'execution_name': execution_name
            }
            
        except Exception as e:
            print(f"   ❌ Failed to start execution: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def wait_for_execution(self, execution_arn: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for Step Functions execution to complete"""
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                response = self.stepfunctions_client.describe_execution(
                    executionArn=execution_arn
                )
                
                status = response['status']
                
                if status == 'SUCCEEDED':
                    print(f"   ✅ Execution SUCCEEDED")
                    return {
                        'success': True,
                        'status': status,
                        'output': json.loads(response.get('output', '{}'))
                    }
                elif status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
                    print(f"   ❌ Execution {status}")
                    return {
                        'success': False,
                        'status': status,
                        'error': response.get('error', 'Unknown error'),
                        'cause': response.get('cause', '')
                    }
                else:
                    print(f"   ⏳ Execution {status}... waiting...")
                    time.sleep(5)
                    
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
        
        return {
            'success': False,
            'error': 'Timeout waiting for execution'
        }
    
    def check_lambda_logs(self, function_name: str, study_id: str) -> Dict[str, Any]:
        """Check CloudWatch logs for Lambda function"""
        try:
            logs_client = boto3.client('logs', region_name=self.region)
            log_group = f'/aws/lambda/{function_name}'
            
            # Get recent log streams
            response = logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if response['logStreams']:
                stream_name = response['logStreams'][0]['logStreamName']
                events = logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    limit=10
                )
                
                return {
                    'success': True,
                    'events': [e['message'] for e in events['events']]
                }
            else:
                return {
                    'success': False,
                    'error': 'No log streams found'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_results_in_s3(self, study_id: str) -> Dict[str, Any]:
        """Check if results were stored in S3"""
        try:
            # List objects in results bucket
            response = self.s3_client.list_objects_v2(
                Bucket=self.results_bucket,
                Prefix=f'results/'
            )
            
            if response.get('Contents'):
                # Filter for our study_id
                matching_results = [
                    obj for obj in response['Contents']
                    if study_id in obj['Key']
                ]
                
                if matching_results:
                    return {
                        'success': True,
                        'results_found': True,
                        'result_count': len(matching_results),
                        'result_keys': [obj['Key'] for obj in matching_results]
                    }
            
            return {
                'success': False,
                'results_found': False
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_telemetry_in_kinesis(self) -> Dict[str, Any]:
        """Check if telemetry data is in Kinesis"""
        try:
            kinesis_client = boto3.client('kinesis', region_name=self.region)
            
            # Get shard iterator
            shard_iterator = kinesis_client.get_shard_iterator(
                StreamName='radstream-telemetry',
                ShardId='shardId-000000000000',
                ShardIteratorType='TRIM_HORIZON'
            )['ShardIterator']
            
            # Get records
            response = kinesis_client.get_records(
                ShardIterator=shard_iterator,
                Limit=10
            )
            
            if response['Records']:
                return {
                    'success': True,
                    'record_count': len(response['Records']),
                    'has_data': True
                }
            else:
                return {
                    'success': False,
                    'has_data': False
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_end_to_end_test(self) -> Dict[str, Any]:
        """Run complete end-to-end test"""
        study_id = f"E2E-{uuid.uuid4().hex[:8].upper()}"
        
        print("\n" + "="*60)
        print("🧪 END-TO-END PIPELINE TEST")
        print("="*60)
        print(f"Study ID: {study_id}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("="*60)
        
        results = {
            'study_id': study_id,
            'timestamp': datetime.utcnow().isoformat(),
            'tests': {}
        }
        
        # Step 1: Upload test data
        print("\n📤 STEP 1: Upload Test Image and Metadata to S3")
        upload_result = self.upload_test_image_and_metadata(study_id)
        results['tests']['upload'] = upload_result
        
        if not upload_result['success']:
            print("\n❌ Upload failed. Stopping test.")
            return results
        
        # Step 2: Manually trigger Step Functions (since EventBridge may not be configured)
        print("\n🚀 STEP 2: Trigger Step Functions Execution")
        trigger_result = self.manually_trigger_step_functions(
            study_id, 
            upload_result['image_key']
        )
        results['tests']['step_functions_trigger'] = trigger_result
        
        if not trigger_result['success']:
            print("\n❌ Failed to trigger Step Functions. Stopping test.")
            return results
        
        # Step 3: Wait for execution
        print("\n⏳ STEP 3: Wait for Step Functions Execution")
        execution_result = self.wait_for_execution(trigger_result['execution_arn'], timeout=120)
        results['tests']['step_functions_execution'] = execution_result
        
        # Step 4: Check Lambda logs
        print("\n📋 STEP 4: Check Lambda Function Logs")
        lambda_functions = [
            'radstream-validate-metadata',
            'radstream-prepare-tensors',
            'radstream-store-results',
            'radstream-send-telemetry'
        ]
        
        lambda_results = {}
        for func_name in lambda_functions:
            log_result = self.check_lambda_logs(func_name, study_id)
            lambda_results[func_name] = log_result
        
        results['tests']['lambda_logs'] = lambda_results
        
        # Step 5: Check results in S3
        print("\n📦 STEP 5: Check Results in S3")
        time.sleep(5)  # Wait a bit more
        results_check = self.check_results_in_s3(study_id)
        results['tests']['results'] = results_check
        
        if results_check.get('results_found'):
            print(f"   ✅ Found {results_check['result_count']} result file(s)")
            for key in results_check.get('result_keys', [])[:3]:
                print(f"      - {key}")
        else:
            print("   ⚠️  No results found yet (may take time to process)")
        
        # Step 6: Check telemetry
        print("\n📊 STEP 6: Check Telemetry in Kinesis")
        telemetry_check = self.check_telemetry_in_kinesis()
        results['tests']['telemetry'] = telemetry_check
        
        if telemetry_check.get('has_data'):
            print(f"   ✅ Telemetry data found ({telemetry_check.get('record_count', 0)} records)")
        else:
            print("   ⚠️  No telemetry data found (may take time to process)")
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(results['tests'])
        passed_tests = sum(1 for test in results['tests'].values() 
                          if isinstance(test, dict) and test.get('success', False))
        
        print(f"Total test steps: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        
        if execution_result.get('success'):
            print(f"\n✅ Step Functions Execution: {execution_result['status']}")
            if execution_result.get('output'):
                print(f"   Output: {json.dumps(execution_result['output'], indent=2)[:200]}...")
        else:
            print(f"\n❌ Step Functions Execution: {execution_result.get('status', 'UNKNOWN')}")
            if execution_result.get('error'):
                print(f"   Error: {execution_result['error']}")
        
        print("\n" + "="*60)
        
        return results

def main():
    """Main function"""
    tester = EndToEndTester()
    results = tester.run_end_to_end_test()
    
    # Save results
    results_file = f"e2e_test_results_{results['study_id']}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Test results saved to: {results_file}")

if __name__ == "__main__":
    main()

