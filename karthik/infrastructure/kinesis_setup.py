#!/usr/bin/env python3
"""
Kinesis Setup Script for RadStream Medical Imaging Pipeline
Creates Kinesis streams and Firehose delivery streams for telemetry data
"""

import boto3
import json
import time
from botocore.exceptions import ClientError
from typing import Dict, List, Optional

class KinesisSetup:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize Kinesis setup with AWS region"""
        self.region = region
        self.kinesis_client = boto3.client('kinesis', region_name=region)
        self.firehose_client = boto3.client('firehose', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def create_kinesis_stream(self, stream_name: str, shard_count: int = 1) -> bool:
        """Create a Kinesis Data Stream"""
        try:
            # Check if stream already exists
            try:
                response = self.kinesis_client.describe_stream(StreamName=stream_name)
                print(f"Stream {stream_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
            
            # Create the stream
            self.kinesis_client.create_stream(
                StreamName=stream_name,
                ShardCount=shard_count
            )
            
            print(f"Creating stream: {stream_name}")
            
            # Wait for stream to become active
            waiter = self.kinesis_client.get_waiter('stream_exists')
            waiter.wait(StreamName=stream_name)
            
            print(f"Stream {stream_name} is now active")
            return True
            
        except ClientError as e:
            print(f"Error creating stream {stream_name}: {e}")
            return False
    
    def create_firehose_delivery_stream(self, stream_name: str, s3_bucket: str, 
                                      role_arn: str) -> bool:
        """Create a Kinesis Data Firehose delivery stream"""
        try:
            # Check if delivery stream already exists
            try:
                response = self.firehose_client.describe_delivery_stream(
                    DeliveryStreamName=stream_name
                )
                print(f"Delivery stream {stream_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
            
            # Create the delivery stream
            self.firehose_client.create_delivery_stream(
                DeliveryStreamName=stream_name,
                DeliveryStreamType='DirectPut',
                S3DestinationConfiguration={
                    'RoleARN': role_arn,
                    'BucketARN': f'arn:aws:s3:::{s3_bucket}',
                    'Prefix': 'raw/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/',
                    'BufferingHints': {
                        'SizeInMBs': 5,
                        'IntervalInSeconds': 300
                    },
                    'CompressionFormat': 'GZIP',
                    'ErrorOutputPrefix': 'errors/',
                    'CloudWatchLoggingOptions': {
                        'Enabled': True,
                        'LogGroupName': f'/aws/kinesisfirehose/{stream_name}',
                        'LogStreamName': 'S3Delivery'
                    }
                }
            )
            
            print(f"Creating delivery stream: {stream_name}")
            
            # Wait for delivery stream to become active
            waiter = self.firehose_client.get_waiter('delivery_stream_exists')
            waiter.wait(DeliveryStreamName=stream_name)
            
            print(f"Delivery stream {stream_name} is now active")
            return True
            
        except ClientError as e:
            print(f"Error creating delivery stream {stream_name}: {e}")
            return False
    
    def create_firehose_role(self, role_name: str) -> str:
        """Create IAM role for Kinesis Data Firehose"""
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
                            "Service": "firehose.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description=f"Role for RadStream Kinesis Data Firehose: {role_name}"
            )
            
            role_arn = response['Role']['Arn']
            print(f"Created role: {role_name}")
            
            # Attach the policy
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:AbortMultipartUpload",
                            "s3:GetBucketLocation",
                            "s3:GetObject",
                            "s3:ListBucket",
                            "s3:ListBucketMultipartUploads",
                            "s3:PutObject"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::radstream-telemetry-{self.account_id}",
                            f"arn:aws:s3:::radstream-telemetry-{self.account_id}/*"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "kinesis:DescribeStream",
                            "kinesis:GetShardIterator",
                            "kinesis:GetRecords",
                            "kinesis:ListShards"
                        ],
                        "Resource": f"arn:aws:kinesis:{self.region}:{self.account_id}:stream/radstream-telemetry"
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "logs:PutLogEvents"
                        ],
                        "Resource": f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/kinesisfirehose/*"
                    }
                ]
            }
            
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{role_name}-policy",
                PolicyDocument=json.dumps(policy_document)
            )
            
            print(f"Attached policy to role: {role_name}")
            return role_arn
            
        except ClientError as e:
            print(f"Error creating role {role_name}: {e}")
            raise
    
    def setup_telemetry_pipeline(self) -> Dict[str, bool]:
        """Set up complete telemetry pipeline"""
        
        # Create Kinesis stream
        stream_name = 'radstream-telemetry'
        stream_success = self.create_kinesis_stream(stream_name, shard_count=1)
        
        # Create Firehose role
        firehose_role_name = 'RadStreamFirehoseRole'
        try:
            firehose_role_arn = self.create_firehose_role(firehose_role_name)
        except Exception as e:
            print(f"Failed to create Firehose role: {e}")
            return {'kinesis_stream': stream_success, 'firehose_stream': False}
        
        # Create Firehose delivery stream
        firehose_stream_name = 'radstream-telemetry-firehose'
        s3_bucket = f'radstream-telemetry-{self.account_id}'
        firehose_success = self.create_firehose_delivery_stream(
            firehose_stream_name, s3_bucket, firehose_role_arn
        )
        
        return {
            'kinesis_stream': stream_success,
            'firehose_stream': firehose_success
        }
    
    def list_streams(self) -> List[Dict]:
        """List all RadStream Kinesis streams"""
        try:
            response = self.kinesis_client.list_streams()
            radstream_streams = [
                stream for stream in response.get('StreamNames', [])
                if stream.startswith('radstream-')
            ]
            return radstream_streams
        except ClientError as e:
            print(f"Error listing streams: {e}")
            return []
    
    def list_delivery_streams(self) -> List[Dict]:
        """List all RadStream Firehose delivery streams"""
        try:
            response = self.firehose_client.list_delivery_streams()
            radstream_streams = [
                stream for stream in response.get('DeliveryStreamNames', [])
                if stream.startswith('radstream-')
            ]
            return radstream_streams
        except ClientError as e:
            print(f"Error listing delivery streams: {e}")
            return []
    
    def delete_stream(self, stream_name: str) -> bool:
        """Delete a Kinesis stream"""
        try:
            self.kinesis_client.delete_stream(StreamName=stream_name)
            print(f"Deleted stream: {stream_name}")
            return True
        except ClientError as e:
            print(f"Error deleting stream {stream_name}: {e}")
            return False
    
    def delete_delivery_stream(self, stream_name: str) -> bool:
        """Delete a Firehose delivery stream"""
        try:
            self.firehose_client.delete_delivery_stream(DeliveryStreamName=stream_name)
            print(f"Deleted delivery stream: {stream_name}")
            return True
        except ClientError as e:
            print(f"Error deleting delivery stream {stream_name}: {e}")
            return False
    
    def cleanup_streams(self, confirm: bool = False):
        """Delete all RadStream streams"""
        if not confirm:
            print("This will delete ALL RadStream streams. Set confirm=True to proceed.")
            return
        
        # Delete delivery streams first
        delivery_streams = self.list_delivery_streams()
        for stream in delivery_streams:
            self.delete_delivery_stream(stream)
        
        # Delete Kinesis streams
        streams = self.list_streams()
        for stream in streams:
            self.delete_stream(stream)

def main():
    """Main function to set up Kinesis infrastructure"""
    print("RadStream Kinesis Infrastructure Setup")
    print("=" * 40)
    
    # Initialize Kinesis setup
    kinesis_setup = KinesisSetup(region='us-east-1')
    
    print("Setting up telemetry pipeline...")
    print("=" * 35)
    
    # Set up complete telemetry pipeline
    results = kinesis_setup.setup_telemetry_pipeline()
    
    # Print summary
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"Successfully created: {successful}/{total} telemetry components")
    
    for component, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {component}: {status}")
    
    if successful == total:
        print("\n🎉 All telemetry components created successfully!")
        print("\nNext steps:")
        print("1. Test telemetry streaming (kinesis_producer.py)")
        print("2. Set up Glue Data Catalog (glue_schema.py)")
        print("3. Configure Athena queries (athena_queries.sql)")
    else:
        print(f"\n⚠️  {total - successful} components failed to create. Check AWS permissions and try again.")

if __name__ == "__main__":
    main()
