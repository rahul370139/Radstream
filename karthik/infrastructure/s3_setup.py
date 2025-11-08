#!/usr/bin/env python3
"""
S3 Setup Script for RadStream Medical Imaging Pipeline
Creates 4 S3 buckets with proper configurations for the cloud-native pipeline
"""

import boto3
import json
import time
from botocore.exceptions import ClientError
from typing import Dict, List

class S3Setup:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize S3 setup with AWS region"""
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID for unique bucket naming
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def create_bucket(self, bucket_name: str, bucket_config: Dict) -> bool:
        """Create a single S3 bucket with specified configuration"""
        try:
            # Check if bucket already exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                print(f"Bucket {bucket_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise
            
            # Create bucket
            if self.region == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            
            print(f"Created bucket: {bucket_name}")
            
            # Wait for bucket to be ready
            time.sleep(2)
            
            # Apply bucket configuration
            self._configure_bucket(bucket_name, bucket_config)
            
            return True
            
        except ClientError as e:
            print(f"Error creating bucket {bucket_name}: {e}")
            return False
    
    def _configure_bucket(self, bucket_name: str, config: Dict):
        """Apply configuration to S3 bucket"""
        try:
            # Enable versioning
            if config.get('versioning', False):
                self.s3_client.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                print(f"Enabled versioning for {bucket_name}")
            
            # Set up encryption
            if config.get('encryption', False):
                self.s3_client.put_bucket_encryption(
                    Bucket=bucket_name,
                    ServerSideEncryptionConfiguration={
                        'Rules': [
                            {
                                'ApplyServerSideEncryptionByDefault': {
                                    'SSEAlgorithm': 'AES256'
                                }
                            }
                        ]
                    }
                )
                print(f"Enabled encryption for {bucket_name}")
            
            # Set up lifecycle policy
            if config.get('lifecycle_policy'):
                try:
                    self.s3_client.put_bucket_lifecycle_configuration(
                        Bucket=bucket_name,
                        LifecycleConfiguration=config['lifecycle_policy']
                    )
                    print(f"Applied lifecycle policy to {bucket_name}")
                except ClientError as e:
                    print(f"Warning: Could not apply lifecycle policy to {bucket_name}: {e}")
                    print("   Bucket created successfully, but lifecycle policy needs manual configuration")
            
            # Set up CORS if specified
            if config.get('cors_policy'):
                self.s3_client.put_bucket_cors(
                    Bucket=bucket_name,
                    CORSConfiguration=config['cors_policy']
                )
                print(f"Applied CORS policy to {bucket_name}")
            
            # Set up bucket policy
            if config.get('bucket_policy'):
                self.s3_client.put_bucket_policy(
                    Bucket=bucket_name,
                    Policy=json.dumps(config['bucket_policy'])
                )
                print(f"Applied bucket policy to {bucket_name}")
                
        except ClientError as e:
            print(f"Error configuring bucket {bucket_name}: {e}")
            raise
    
    def setup_event_notifications(self, bucket_name: str, eventbridge_role_arn: str):
        """Set up S3 event notifications for EventBridge"""
        try:
            # Configure EventBridge notification
            self.s3_client.put_bucket_notification_configuration(
                Bucket=bucket_name,
                NotificationConfiguration={
                    'EventBridgeConfiguration': {}
                }
            )
            print(f"Enabled EventBridge notifications for {bucket_name}")
            
        except ClientError as e:
            print(f"Error setting up EventBridge notifications for {bucket_name}: {e}")
            raise
    
    def create_all_buckets(self) -> Dict[str, bool]:
        """Create all required S3 buckets for RadStream pipeline"""
        
        # Define bucket configurations
        bucket_configs = {
            f'radstream-images-{self.account_id}': {
                'versioning': True,
                'encryption': True,
                'lifecycle_policy': {
                    'Rules': [
                        {
                            'ID': 'DeleteOldVersions',
                            'Status': 'Enabled',
                            'NoncurrentVersionExpiration': {
                                'NoncurrentDays': 30
                            }
                        }
                    ]
                },
                'cors_policy': {
                    'CORSRules': [
                        {
                            'AllowedHeaders': ['*'],
                            'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE'],
                            'AllowedOrigins': ['*'],
                            'ExposeHeaders': ['ETag']
                        }
                    ]
                }
            },
            f'radstream-results-{self.account_id}': {
                'versioning': True,
                'encryption': True,
                'lifecycle_policy': {
                    'Rules': [
                        {
                            'ID': 'DeleteOldResults',
                            'Status': 'Enabled',
                            'Expiration': {
                                'Days': 90
                            }
                        }
                    ]
                }
            },
            f'radstream-telemetry-{self.account_id}': {
                'versioning': False,
                'encryption': True,
                'lifecycle_policy': {
                    'Rules': [
                        {
                            'ID': 'TransitionToIA',
                            'Status': 'Enabled',
                            'Transitions': [
                                {
                                    'Days': 30,
                                    'StorageClass': 'STANDARD_IA'
                                }
                            ]
                        },
                        {
                            'ID': 'DeleteOldTelemetry',
                            'Status': 'Enabled',
                            'Expiration': {
                                'Days': 365
                            }
                        }
                    ]
                }
            },
            f'radstream-artifacts-{self.account_id}': {
                'versioning': False,
                'encryption': True,
                'lifecycle_policy': {
                    'Rules': [
                        {
                            'ID': 'TransitionToOneZoneIA',
                            'Status': 'Enabled',
                            'Transitions': [
                                {
                                    'Days': 0,
                                    'StorageClass': 'ONEZONE_IA'
                                }
                            ]
                        }
                    ]
                }
            }
        }
        
        results = {}
        
        print("Creating S3 buckets for RadStream pipeline...")
        print("=" * 50)
        
        for bucket_name, config in bucket_configs.items():
            print(f"\nCreating bucket: {bucket_name}")
            success = self.create_bucket(bucket_name, config)
            results[bucket_name] = success
            
            if success:
                print(f"✅ Successfully created and configured {bucket_name}")
            else:
                print(f"❌ Failed to create {bucket_name}")
        
        return results
    
    def list_buckets(self) -> List[str]:
        """List all RadStream buckets"""
        try:
            response = self.s3_client.list_buckets()
            radstream_buckets = [
                bucket['Name'] for bucket in response['Buckets']
                if bucket['Name'].startswith('radstream-')
            ]
            return radstream_buckets
        except ClientError as e:
            print(f"Error listing buckets: {e}")
            return []
    
    def cleanup_buckets(self, confirm: bool = False):
        """Delete all RadStream buckets (use with caution!)"""
        if not confirm:
            print("This will delete ALL RadStream buckets. Set confirm=True to proceed.")
            return
        
        buckets = self.list_buckets()
        for bucket_name in buckets:
            try:
                # Delete all objects first
                paginator = self.s3_client.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=bucket_name):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            self.s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
                
                # Delete bucket
                self.s3_client.delete_bucket(Bucket=bucket_name)
                print(f"Deleted bucket: {bucket_name}")
                
            except ClientError as e:
                print(f"Error deleting bucket {bucket_name}: {e}")

def main():
    """Main function to set up S3 infrastructure"""
    print("RadStream S3 Infrastructure Setup")
    print("=" * 40)
    
    # Initialize S3 setup
    s3_setup = S3Setup(region='us-east-1')
    
    # Create all buckets
    results = s3_setup.create_all_buckets()
    
    # Print summary
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"Successfully created: {successful}/{total} buckets")
    
    for bucket_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {bucket_name}: {status}")
    
    if successful == total:
        print("\n🎉 All S3 buckets created successfully!")
        print("\nNext steps:")
        print("1. Set up EventBridge rules (eventbridge_setup.py)")
        print("2. Create Step Functions workflow (stepfunctions_setup.py)")
        print("3. Deploy Lambda functions (lambda_setup.py)")
    else:
        print(f"\n⚠️  {total - successful} buckets failed to create. Check AWS permissions and try again.")

if __name__ == "__main__":
    main()
