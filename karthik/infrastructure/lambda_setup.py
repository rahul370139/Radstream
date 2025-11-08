#!/usr/bin/env python3
"""
Lambda Setup Script for RadStream Medical Imaging Pipeline
Deploys Lambda functions for preprocessing and other pipeline components
"""

import boto3
import json
import zipfile
import os
import tempfile
import time
from botocore.exceptions import ClientError
from typing import Dict, List, Optional

class LambdaSetup:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize Lambda setup with AWS region"""
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def create_lambda_role(self, role_name: str, policy_document: Dict) -> str:
        """Create IAM role for Lambda function"""
        try:
            # Check if role already exists
            try:
                response = self.iam_client.get_role(RoleName=role_name)
                role_arn = response['Role']['Arn']
                print(f"Role {role_name} already exists: {role_arn}")
                return role_arn
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise
            
            # Create the role
            assume_role_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description=f"Role for RadStream Lambda function: {role_name}"
            )
            
            role_arn = response['Role']['Arn']
            print(f"Created role: {role_name}")
            
            # Attach the policy
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{role_name}-policy",
                PolicyDocument=json.dumps(policy_document)
            )
            
            # Attach basic execution role
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            )
            
            print(f"Attached policies to role: {role_name}")
            return role_arn
            
        except ClientError as e:
            print(f"Error creating role {role_name}: {e}")
            raise
    
    def create_deployment_package(self, function_code_path: str, requirements_path: str) -> bytes:
        """Create deployment package for Lambda function with dependencies"""
        import subprocess
        import shutil
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Create temporary directory for building package
        build_dir = tempfile.mkdtemp()
        
        try:
            # Copy function code
            function_name = os.path.basename(function_code_path)
            shutil.copy(function_code_path, os.path.join(build_dir, function_name))
            
            # Install dependencies if requirements file exists
            if requirements_path and os.path.isfile(requirements_path):
                print(f"   Installing dependencies from {requirements_path}...")
                # Install dependencies to build directory
                # Use --no-deps for numpy to avoid source directory issues
                # Lambda runtime includes numpy, but we'll install it properly
                result = subprocess.run([
                    'pip', 'install', '-r', requirements_path,
                    '-t', build_dir,
                    '--quiet', '--disable-pip-version-check',
                    '--no-cache-dir',
                    '--only-binary=:all:'  # Force binary wheels, avoid source
                ], check=False, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"   Warning: pip install had issues: {result.stderr[:200]}")
                
                # Check and remove numpy source directories (but keep installed package)
                numpy_dir = os.path.join(build_dir, 'numpy')
                if os.path.exists(numpy_dir) and os.path.isdir(numpy_dir):
                    # Check if it's a source directory (has setup.py in root)
                    setup_py = os.path.join(numpy_dir, 'setup.py')
                    if os.path.exists(setup_py):
                        print(f"   ⚠️  Found numpy source directory, removing and reinstalling as binary...")
                        shutil.rmtree(numpy_dir, ignore_errors=True)
                        # Also remove any numpy egg-info
                        for item in os.listdir(build_dir):
                            if 'numpy' in item.lower() and 'egg-info' in item.lower():
                                shutil.rmtree(os.path.join(build_dir, item), ignore_errors=True)
                        
                        # Reinstall numpy as binary wheel only
                        subprocess.run([
                            'pip', 'install', 'numpy>=1.24.0',
                            '-t', build_dir,
                            '--only-binary=:all:',
                            '--no-cache-dir',
                            '--quiet', '--disable-pip-version-check'
                        ], check=False, capture_output=True)
                        print(f"   ✅ Reinstalled numpy as binary wheel")
                    
                    # Remove setup.py if it exists (even in installed package, it shouldn't be there)
                    if os.path.exists(setup_py):
                        print(f"   Removing setup.py from numpy directory")
                        os.remove(setup_py)
                
                # Also remove any setup.py files from numpy subdirectories
                for root, dirs, files in os.walk(build_dir):
                    if 'numpy' in root:
                        if 'setup.py' in files:
                            setup_path = os.path.join(root, 'setup.py')
                            print(f"   Removing setup.py from: {os.path.relpath(setup_path, build_dir)}")
                            os.remove(setup_path)
            
            # Create zip file with all files
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add all files from build directory
                for root, dirs, files in os.walk(build_dir):
                    # Filter out directories we don't want to traverse
                    dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.pytest_cache', '.eggs']]
                    
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, build_dir)
                        
                        # Skip problematic files but KEEP numpy installed package
                        skip_patterns = [
                            '__pycache__',
                            '.pyc',
                            '.pyo',
                            '.git',
                            '.pytest_cache',
                            '.eggs',
                            '*.egg-info/setup.py',  # Skip setup.py in egg-info
                            'numpy/distutils',  # Skip distutils (not needed)
                            'numpy/tests',  # Skip tests
                            'numpy/doc',  # Skip docs
                            'numpy/f2py',  # Skip f2py (not needed for basic numpy)
                        ]
                        
                        should_skip = False
                        for pattern in skip_patterns:
                            # Handle wildcard patterns
                            if '*' in pattern:
                                pattern_base = pattern.replace('*', '')
                                if pattern_base in arc_name:
                                    should_skip = True
                                    break
                            elif pattern in arc_name:
                                should_skip = True
                                break
                        
                        # IMPORTANT: Never include setup.py files - they indicate source directories
                        if file == 'setup.py' or arc_name.endswith('/setup.py'):
                            should_skip = True
                        
                        if not should_skip:
                            zip_file.write(file_path, arc_name)
            
            # Read the zip file
            with open(temp_path, 'rb') as f:
                zip_data = f.read()
            
            print(f"   Deployment package size: {len(zip_data) / 1024 / 1024:.2f} MB")
            return zip_data
            
        finally:
            # Clean up temp files
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)
    
    def deploy_lambda_function(self, function_name: str, function_code_path: str, 
                             requirements_path: str, role_arn: str, 
                             environment_vars: Optional[Dict] = None,
                             layers: Optional[List[str]] = None) -> bool:
        """Deploy a Lambda function"""
        try:
            # Create deployment package
            print(f"Creating deployment package for {function_name}...")
            zip_data = self.create_deployment_package(function_code_path, requirements_path)
            
            # Check if function already exists
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                print(f"Function {function_name} already exists, updating...")
                
                # Wait for any in-progress updates to complete
                max_wait = 300  # 5 minutes max
                wait_time = 0
                while wait_time < max_wait:
                    config = self.lambda_client.get_function_configuration(FunctionName=function_name)
                    status = config.get('LastUpdateStatus', '')
                    if status not in ['InProgress']:
                        break
                    print(f"   Waiting for previous update to complete... (status: {status})")
                    time.sleep(5)
                    wait_time += 5
                
                # Update function code
                try:
                    self.lambda_client.update_function_code(
                        FunctionName=function_name,
                        ZipFile=zip_data
                    )
                    print(f"   Code updated")
                except ClientError as e:
                    if 'ResourceConflictException' in str(e):
                        print(f"   Code update in progress, waiting...")
                        time.sleep(10)
                        # Retry once
                        self.lambda_client.update_function_code(
                            FunctionName=function_name,
                            ZipFile=zip_data
                        )
                    else:
                        raise
                
                # Update function configuration
                update_params = {
                    'FunctionName': function_name,
                    'Role': role_arn,
                    'Timeout': 60,
                    'MemorySize': 1024
                }
                
                if environment_vars:
                    update_params['Environment'] = {'Variables': environment_vars}
                
                if layers:
                    update_params['Layers'] = layers
                
                try:
                    self.lambda_client.update_function_configuration(**update_params)
                    print(f"   Configuration updated")
                except ClientError as e:
                    if 'ResourceConflictException' in str(e):
                        print(f"   Configuration update in progress, waiting...")
                        time.sleep(10)
                        # Retry once
                        self.lambda_client.update_function_configuration(**update_params)
                    else:
                        raise
                
                print(f"✅ Updated function: {function_name}")
                return True
                
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
                
                # Create new function
                create_params = {
                    'FunctionName': function_name,
                    'Runtime': 'python3.9',
                    'Role': role_arn,
                    'Handler': f"{os.path.splitext(os.path.basename(function_code_path))[0]}.lambda_handler",
                    'Code': {'ZipFile': zip_data},
                    'Description': f"RadStream Lambda function: {function_name}",
                    'Timeout': 60,
                    'MemorySize': 1024,
                    'Publish': True
                }
                
                if environment_vars:
                    create_params['Environment'] = {'Variables': environment_vars}
                
                if layers:
                    create_params['Layers'] = layers
                
                self.lambda_client.create_function(**create_params)
                print(f"Created function: {function_name}")
                return True
                
        except Exception as e:
            print(f"Error deploying function {function_name}: {e}")
            return False
    
    def create_lambda_functions(self) -> Dict[str, bool]:
        """Create all required Lambda functions for RadStream pipeline"""
        
        # Define function configurations
        functions = {
            'radstream-validate-metadata': {
                'code_path': '../../rahul/preprocessing/validate_metadata.py',
                'requirements_path': '../../rahul/preprocessing/requirements.txt',
                'role_name': 'RadStreamValidateMetadataRole',
                'environment_vars': {
                    'TELEMETRY_STREAM_NAME': 'radstream-telemetry'
                }
            },
            'radstream-prepare-tensors': {
                'code_path': '../../rahul/preprocessing/prepare_tensors.py',
                'requirements_path': '../../rahul/preprocessing/requirements_no_pillow.txt',  # Use version without Pillow (layer provides it)
                'role_name': 'RadStreamPrepareTensorsRole',
                'environment_vars': {
                    'TELEMETRY_STREAM_NAME': 'radstream-telemetry'
                },
                'layers': []  # Will be set after layer is created
            },
            'radstream-store-results': {
                'code_path': '../../rahul/preprocessing/store_results.py',
                'requirements_path': '../../rahul/preprocessing/requirements.txt',
                'role_name': 'RadStreamStoreResultsRole',
                'environment_vars': {
                    'RESULTS_BUCKET': f'radstream-results-{self.account_id}',
                    'TELEMETRY_STREAM_NAME': 'radstream-telemetry'
                }
            },
            'radstream-send-telemetry': {
                'code_path': '../../rahul/preprocessing/send_telemetry.py',
                'requirements_path': '../../rahul/preprocessing/requirements.txt',
                'role_name': 'RadStreamSendTelemetryRole',
                'environment_vars': {
                    'TELEMETRY_STREAM_NAME': 'radstream-telemetry'
                }
            }
        }
        
        # Create IAM roles first
        role_policies = {
            'RadStreamValidateMetadataRole': self.get_validate_metadata_policy(),
            'RadStreamPrepareTensorsRole': self.get_prepare_tensors_policy(),
            'RadStreamStoreResultsRole': self.get_store_results_policy(),
            'RadStreamSendTelemetryRole': self.get_send_telemetry_policy()
        }
        
        roles = {}
        for role_name, policy in role_policies.items():
            try:
                role_arn = self.create_lambda_role(role_name, policy)
                roles[role_name] = role_arn
            except Exception as e:
                print(f"Failed to create role {role_name}: {e}")
                return {}
        
        # Deploy Lambda functions
        results = {}
        
        for function_name, config in functions.items():
            print(f"\nDeploying {function_name}...")
            
            # Get absolute paths (relative to script location)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            code_path = os.path.abspath(os.path.join(script_dir, config['code_path']))
            requirements_path = os.path.abspath(os.path.join(script_dir, config['requirements_path'])) if config['requirements_path'] else None
            role_arn = roles[config['role_name']]
            
            # Verify paths exist
            if not os.path.exists(code_path):
                print(f"❌ Error: Code file not found: {code_path}")
                print(f"   Looking for: {config['code_path']}")
                results[function_name] = False
                continue
            
            # Get layer ARN for prepare_tensors
            layers = config.get('layers')
            if function_name == 'radstream-prepare-tensors' and not layers:
                # Get the Pillow layer ARN we created
                try:
                    layer_response = self.lambda_client.list_layer_versions(
                        LayerName='radstream-pillow-layer',
                        MaxItems=1
                    )
                    if layer_response['LayerVersions']:
                        layers = [layer_response['LayerVersions'][0]['LayerVersionArn']]
                except:
                    pass
            
            success = self.deploy_lambda_function(
                function_name=function_name,
                function_code_path=code_path,
                requirements_path=requirements_path,
                role_arn=role_arn,
                environment_vars=config.get('environment_vars'),
                layers=layers
            )
            
            results[function_name] = success
        
        return results
    
    def get_validate_metadata_policy(self) -> Dict:
        """Get IAM policy for validate metadata function"""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": f"arn:aws:s3:::radstream-images-{self.account_id}/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kinesis:PutRecord"
                    ],
                    "Resource": f"arn:aws:kinesis:{self.region}:{self.account_id}:stream/radstream-telemetry"
                }
            ]
        }
    
    def get_prepare_tensors_policy(self) -> Dict:
        """Get IAM policy for prepare tensors function"""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": f"arn:aws:s3:::radstream-images-{self.account_id}/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kinesis:PutRecord"
                    ],
                    "Resource": f"arn:aws:kinesis:{self.region}:{self.account_id}:stream/radstream-telemetry"
                }
            ]
        }
    
    def get_store_results_policy(self) -> Dict:
        """Get IAM policy for store results function"""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectAcl"
                    ],
                    "Resource": f"arn:aws:s3:::radstream-results-{self.account_id}/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kinesis:PutRecord"
                    ],
                    "Resource": f"arn:aws:kinesis:{self.region}:{self.account_id}:stream/radstream-telemetry"
                }
            ]
        }
    
    def get_send_telemetry_policy(self) -> Dict:
        """Get IAM policy for send telemetry function"""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "kinesis:PutRecord",
                        "kinesis:PutRecords"
                    ],
                    "Resource": f"arn:aws:kinesis:{self.region}:{self.account_id}:stream/radstream-telemetry"
                }
            ]
        }
    
    def list_functions(self) -> List[Dict]:
        """List all RadStream Lambda functions"""
        try:
            response = self.lambda_client.list_functions()
            radstream_functions = [
                func for func in response.get('Functions', [])
                if func['FunctionName'].startswith('radstream-')
            ]
            return radstream_functions
        except ClientError as e:
            print(f"Error listing functions: {e}")
            return []
    
    def delete_function(self, function_name: str) -> bool:
        """Delete a Lambda function"""
        try:
            self.lambda_client.delete_function(FunctionName=function_name)
            print(f"Deleted function: {function_name}")
            return True
        except ClientError as e:
            print(f"Error deleting function {function_name}: {e}")
            return False

def main():
    """Main function to set up Lambda infrastructure"""
    print("RadStream Lambda Infrastructure Setup")
    print("=" * 40)
    
    # Initialize Lambda setup
    lambda_setup = LambdaSetup(region='us-east-1')
    
    print("Creating Lambda functions...")
    print("=" * 30)
    
    # Create all functions
    results = lambda_setup.create_lambda_functions()
    
    # Print summary
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"Successfully created: {successful}/{total} Lambda functions")
    
    for function_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {function_name}: {status}")
    
    if successful == total:
        print("\n🎉 All Lambda functions created successfully!")
        print("\nNext steps:")
        print("1. Test Lambda functions individually")
        print("2. Set up Step Functions workflow (stepfunctions_setup.py)")
        print("3. Configure Kinesis stream (kinesis_setup.py)")
    else:
        print(f"\n⚠️  {total - successful} functions failed to create. Check AWS permissions and try again.")

if __name__ == "__main__":
    main()
