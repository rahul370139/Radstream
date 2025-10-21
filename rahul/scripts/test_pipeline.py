#!/usr/bin/env python3
"""
Pipeline Test Script for RadStream Medical Imaging Pipeline
Tests the end-to-end pipeline functionality
"""

import boto3
import json
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List
from botocore.exceptions import ClientError
import requests

class PipelineTester:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize pipeline tester"""
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.stepfunctions_client = boto3.client('stepfunctions', region_name=region)
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
    
    def create_test_image(self, width: int = 512, height: int = 512) -> bytes:
        """Create a test image for testing"""
        from PIL import Image
        import io
        
        # Create a simple test image
        image = Image.new('RGB', (width, height), color=(128, 128, 128))
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG', quality=85)
        return img_buffer.getvalue()
    
    def create_test_metadata(self, study_id: str) -> Dict[str, Any]:
        """Create test metadata for a study"""
        return {
            'study_id': study_id,
            'view': 'PA',
            'timestamp': datetime.utcnow().isoformat(),
            'patient_id': f'PAT-{study_id}',
            'modality': 'X-RAY',
            'body_part': 'CHEST'
        }
    
    def upload_test_study(self, study_id: str) -> Dict[str, Any]:
        """Upload a test study to S3"""
        try:
            # Create test data
            image_data = self.create_test_image()
            metadata = self.create_test_metadata(study_id)
            
            # Upload image
            image_key = f'images/{study_id}/{study_id}.jpg'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=image_key,
                Body=image_data,
                ContentType='image/jpeg',
                ServerSideEncryption='AES256'
            )
            
            # Upload metadata
            metadata_key = f'images/{study_id}/{study_id}.json'
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
    
    def check_step_functions_execution(self, study_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Check if Step Functions executed successfully"""
        try:
            # List recent executions
            response = self.stepfunctions_client.list_executions(
                stateMachineArn=f'arn:aws:states:{self.region}:{self.account_id}:stateMachine:radstream-pipeline',
                statusFilter='RUNNING',
                maxResults=10
            )
            
            # Look for execution with our study_id
            for execution in response.get('executions', []):
                if study_id in execution['name']:
                    return {
                        'success': True,
                        'execution_arn': execution['executionArn'],
                        'status': execution['status']
                    }
            
            return {
                'success': False,
                'error': 'No execution found for study_id'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_results(self, study_id: str) -> Dict[str, Any]:
        """Check if results were stored in S3"""
        try:
            # Look for results in S3
            response = self.s3_client.list_objects_v2(
                Bucket=self.results_bucket,
                Prefix=f'results/{study_id}/'
            )
            
            if response.get('Contents'):
                return {
                    'success': True,
                    'results_found': True,
                    'result_count': len(response['Contents'])
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
    
    def test_lambda_functions(self) -> Dict[str, Any]:
        """Test Lambda functions individually"""
        results = {}
        
        # Test validate_metadata function
        try:
            lambda_client = boto3.client('lambda', region_name=self.region)
            
            # Test with valid metadata
            test_event = {
                'bucket': self.images_bucket,
                'key': 'test/test.json',
                'metadata': {
                    'study_id': 'TEST-001',
                    'view': 'PA',
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            response = lambda_client.invoke(
                FunctionName='radstream-validate-metadata',
                InvocationType='RequestResponse',
                Payload=json.dumps(test_event)
            )
            
            result = json.loads(response['Payload'].read())
            results['validate_metadata'] = {
                'success': result.get('valid', False),
                'response': result
            }
            
        except Exception as e:
            results['validate_metadata'] = {
                'success': False,
                'error': str(e)
            }
        
        return results
    
    def test_eks_endpoint(self, endpoint_url: str) -> Dict[str, Any]:
        """Test EKS inference endpoint"""
        try:
            # Test health endpoint
            health_url = f"{endpoint_url}/v2/health/ready"
            response = requests.get(health_url, timeout=10)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'response': response.json()
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': f"Health check failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_comprehensive_test(self, study_id: str, eks_endpoint: str = None) -> Dict[str, Any]:
        """Run comprehensive pipeline test"""
        print(f"Running comprehensive test for study: {study_id}")
        print("=" * 50)
        
        results = {
            'study_id': study_id,
            'timestamp': datetime.utcnow().isoformat(),
            'tests': {}
        }
        
        # Test 1: Upload study
        print("1. Testing S3 upload...")
        upload_result = self.upload_test_study(study_id)
        results['tests']['upload'] = upload_result
        
        if not upload_result['success']:
            print(f"   ❌ Upload failed: {upload_result['error']}")
            return results
        
        print(f"   ✅ Upload successful: {upload_result['image_key']}")
        
        # Test 2: Check Step Functions execution
        print("2. Checking Step Functions execution...")
        time.sleep(5)  # Wait for EventBridge to trigger
        sf_result = self.check_step_functions_execution(study_id)
        results['tests']['step_functions'] = sf_result
        
        if sf_result['success']:
            print(f"   ✅ Step Functions execution found: {sf_result['status']}")
        else:
            print(f"   ❌ Step Functions execution not found: {sf_result['error']}")
        
        # Test 3: Check Lambda functions
        print("3. Testing Lambda functions...")
        lambda_results = self.test_lambda_functions()
        results['tests']['lambda_functions'] = lambda_results
        
        for func_name, result in lambda_results.items():
            if result['success']:
                print(f"   ✅ {func_name}: Working")
            else:
                print(f"   ❌ {func_name}: {result.get('error', 'Failed')}")
        
        # Test 4: Check EKS endpoint (if provided)
        if eks_endpoint:
            print("4. Testing EKS endpoint...")
            eks_result = self.test_eks_endpoint(eks_endpoint)
            results['tests']['eks_endpoint'] = eks_result
            
            if eks_result['success']:
                print(f"   ✅ EKS endpoint healthy: {eks_result['status_code']}")
            else:
                print(f"   ❌ EKS endpoint failed: {eks_result['error']}")
        
        # Test 5: Check results
        print("5. Checking results...")
        time.sleep(10)  # Wait for pipeline to complete
        results_check = self.check_results(study_id)
        results['tests']['results'] = results_check
        
        if results_check['success'] and results_check['results_found']:
            print(f"   ✅ Results found: {results_check['result_count']} files")
        else:
            print(f"   ❌ No results found: {results_check.get('error', 'No results')}")
        
        # Summary
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(results['tests'])
        passed_tests = sum(1 for test in results['tests'].values() if test.get('success', False))
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
        
        return results

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test RadStream pipeline')
    parser.add_argument('--study-id', type=str, default='TEST-001', help='Study ID for testing')
    parser.add_argument('--eks-endpoint', type=str, help='EKS endpoint URL for testing')
    parser.add_argument('--comprehensive', action='store_true', help='Run comprehensive test')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = PipelineTester()
    
    if args.comprehensive:
        # Run comprehensive test
        results = tester.run_comprehensive_test(args.study_id, args.eks_endpoint)
        
        # Save results
        results_file = f"test_results_{args.study_id}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nTest results saved to: {results_file}")
    else:
        # Run basic upload test
        result = tester.upload_test_study(args.study_id)
        if result['success']:
            print(f"✅ Basic test passed: {result['study_id']}")
        else:
            print(f"❌ Basic test failed: {result['error']}")

if __name__ == "__main__":
    main()
