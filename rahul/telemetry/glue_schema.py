#!/usr/bin/env python3
"""
Glue Schema Setup Script for RadStream Medical Imaging Pipeline
Creates Glue Data Catalog database and tables for telemetry analysis
"""

import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, List, Optional

class GlueSchemaSetup:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize Glue setup with AWS region"""
        self.region = region
        self.glue_client = boto3.client('glue', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def create_database(self, database_name: str) -> bool:
        """Create Glue database"""
        try:
            # Check if database already exists
            try:
                response = self.glue_client.get_database(Name=database_name)
                print(f"Database {database_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'EntityNotFoundException':
                    raise
            
            # Create the database
            self.glue_client.create_database(
                DatabaseInput={
                    'Name': database_name,
                    'Description': 'RadStream medical imaging pipeline telemetry database',
                    'LocationUri': f's3://radstream-telemetry-{self.account_id}/',
                    'Parameters': {
                        'classification': 'json',
                        'typeOfData': 'telemetry'
                    }
                }
            )
            print(f"Created database: {database_name}")
            return True
            
        except ClientError as e:
            print(f"Error creating database {database_name}: {e}")
            return False
    
    def create_telemetry_table(self, database_name: str, table_name: str, 
                             s3_location: str) -> bool:
        """Create telemetry events table"""
        try:
            # Check if table already exists
            try:
                response = self.glue_client.get_table(
                    DatabaseName=database_name,
                    Name=table_name
                )
                print(f"Table {table_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'EntityNotFoundException':
                    raise
            
            # Create the table
            table_input = {
                'Name': table_name,
                'Description': 'RadStream pipeline telemetry events',
                'StorageDescriptor': {
                    'Columns': [
                        {'Name': 'study_id', 'Type': 'string', 'Comment': 'Study identifier'},
                        {'Name': 'stage', 'Type': 'string', 'Comment': 'Pipeline stage'},
                        {'Name': 'status', 'Type': 'string', 'Comment': 'Event status'},
                        {'Name': 'latency_ms', 'Type': 'int', 'Comment': 'Processing latency in milliseconds'},
                        {'Name': 'timestamp', 'Type': 'timestamp', 'Comment': 'Event timestamp'},
                        {'Name': 'error_code', 'Type': 'string', 'Comment': 'Error code if applicable'},
                        {'Name': 'error_message', 'Type': 'string', 'Comment': 'Error message if applicable'},
                        {'Name': 'event_id', 'Type': 'string', 'Comment': 'Unique event identifier'},
                        {'Name': 'producer', 'Type': 'string', 'Comment': 'Event producer'},
                        {'Name': 'metadata', 'Type': 'string', 'Comment': 'Additional metadata as JSON string'}
                    ],
                    'Location': s3_location,
                    'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                    'SerdeInfo': {
                        'SerializationLibrary': 'org.openx.data.jsonserde.JsonSerDe',
                        'Parameters': {
                            'serialization.format': '1'
                        }
                    }
                },
                'PartitionKeys': [
                    {'Name': 'year', 'Type': 'string'},
                    {'Name': 'month', 'Type': 'string'},
                    {'Name': 'day', 'Type': 'string'}
                ],
                'TableType': 'EXTERNAL_TABLE',
                'Parameters': {
                    'classification': 'json',
                    'typeOfData': 'telemetry'
                }
            }
            
            self.glue_client.create_table(
                DatabaseName=database_name,
                TableInput=table_input
            )
            print(f"Created table: {table_name}")
            return True
            
        except ClientError as e:
            print(f"Error creating table {table_name}: {e}")
            return False
    
    def create_performance_metrics_table(self, database_name: str, table_name: str,
                                       s3_location: str) -> bool:
        """Create performance metrics table"""
        try:
            # Check if table already exists
            try:
                response = self.glue_client.get_table(
                    DatabaseName=database_name,
                    Name=table_name
                )
                print(f"Table {table_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'EntityNotFoundException':
                    raise
            
            # Create the table
            table_input = {
                'Name': table_name,
                'Description': 'RadStream pipeline performance metrics',
                'StorageDescriptor': {
                    'Columns': [
                        {'Name': 'study_id', 'Type': 'string', 'Comment': 'Study identifier'},
                        {'Name': 'stage', 'Type': 'string', 'Comment': 'Pipeline stage'},
                        {'Name': 'latency_ms', 'Type': 'int', 'Comment': 'Processing latency'},
                        {'Name': 'cpu_usage', 'Type': 'double', 'Comment': 'CPU usage percentage'},
                        {'Name': 'memory_usage', 'Type': 'double', 'Comment': 'Memory usage percentage'},
                        {'Name': 'gpu_usage', 'Type': 'double', 'Comment': 'GPU usage percentage'},
                        {'Name': 'throughput', 'Type': 'double', 'Comment': 'Throughput (requests/second)'},
                        {'Name': 'timestamp', 'Type': 'timestamp', 'Comment': 'Metric timestamp'},
                        {'Name': 'event_id', 'Type': 'string', 'Comment': 'Unique event identifier'}
                    ],
                    'Location': s3_location,
                    'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                    'SerdeInfo': {
                        'SerializationLibrary': 'org.openx.data.jsonserde.JsonSerDe',
                        'Parameters': {
                            'serialization.format': '1'
                        }
                    }
                },
                'PartitionKeys': [
                    {'Name': 'year', 'Type': 'string'},
                    {'Name': 'month', 'Type': 'string'},
                    {'Name': 'day', 'Type': 'string'}
                ],
                'TableType': 'EXTERNAL_TABLE',
                'Parameters': {
                    'classification': 'json',
                    'typeOfData': 'performance_metrics'
                }
            }
            
            self.glue_client.create_table(
                DatabaseName=database_name,
                Name=table_name,
                TableInput=table_input
            )
            print(f"Created table: {table_name}")
            return True
            
        except ClientError as e:
            print(f"Error creating table {table_name}: {e}")
            return False
    
    def create_crawler(self, crawler_name: str, database_name: str, 
                      s3_paths: List[str]) -> bool:
        """Create Glue crawler for automatic schema discovery"""
        try:
            # Check if crawler already exists
            try:
                response = self.glue_client.get_crawler(Name=crawler_name)
                print(f"Crawler {crawler_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'EntityNotFoundException':
                    raise
            
            # Create IAM role for crawler
            role_name = f"{crawler_name}-role"
            role_arn = self.create_crawler_role(role_name)
            
            # Create the crawler
            self.glue_client.create_crawler(
                Name=crawler_name,
                Role=role_arn,
                DatabaseName=database_name,
                Description='RadStream telemetry data crawler',
                Targets={
                    'S3Targets': [
                        {'Path': path} for path in s3_paths
                    ]
                },
                SchemaChangePolicy={
                    'UpdateBehavior': 'UPDATE_IN_DATABASE',
                    'DeleteBehavior': 'LOG'
                },
                RecrawlPolicy={
                    'RecrawlBehavior': 'CRAWL_EVERYTHING'
                }
            )
            print(f"Created crawler: {crawler_name}")
            return True
            
        except ClientError as e:
            print(f"Error creating crawler {crawler_name}: {e}")
            return False
    
    def create_crawler_role(self, role_name: str) -> str:
        """Create IAM role for Glue crawler"""
        iam_client = boto3.client('iam', region_name=self.region)
        
        try:
            # Check if role already exists
            try:
                response = iam_client.get_role(RoleName=role_name)
                return response['Role']['Arn']
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
                            "Service": "glue.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            response = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description=f"Role for RadStream Glue crawler: {role_name}"
            )
            
            role_arn = response['Role']['Arn']
            
            # Attach AWS managed policy
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
            )
            
            # Attach custom policy for S3 access
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:ListBucket"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::radstream-telemetry-{self.account_id}",
                            f"arn:aws:s3:::radstream-telemetry-{self.account_id}/*"
                        ]
                    }
                ]
            }
            
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{role_name}-s3-policy",
                PolicyDocument=json.dumps(policy_document)
            )
            
            print(f"Created crawler role: {role_name}")
            return role_arn
            
        except ClientError as e:
            print(f"Error creating crawler role {role_name}: {e}")
            raise
    
    def setup_complete_schema(self) -> Dict[str, bool]:
        """Set up complete Glue schema for RadStream"""
        database_name = 'radstream_analytics'
        s3_base_location = f's3://radstream-telemetry-{self.account_id}/'
        
        results = {}
        
        # Create database
        results['database'] = self.create_database(database_name)
        
        # Create tables
        results['telemetry_table'] = self.create_telemetry_table(
            database_name, 'telemetry_events', 
            f'{s3_base_location}raw/'
        )
        
        results['performance_table'] = self.create_performance_metrics_table(
            database_name, 'performance_metrics',
            f'{s3_base_location}performance/'
        )
        
        # Create crawler
        results['crawler'] = self.create_crawler(
            'radstream-telemetry-crawler',
            database_name,
            [f'{s3_base_location}raw/', f'{s3_base_location}performance/']
        )
        
        return results
    
    def list_databases(self) -> List[str]:
        """List all RadStream databases"""
        try:
            response = self.glue_client.get_databases()
            radstream_dbs = [
                db['Name'] for db in response.get('DatabaseList', [])
                if db['Name'].startswith('radstream')
            ]
            return radstream_dbs
        except ClientError as e:
            print(f"Error listing databases: {e}")
            return []
    
    def list_tables(self, database_name: str) -> List[str]:
        """List all tables in a database"""
        try:
            response = self.glue_client.get_tables(DatabaseName=database_name)
            return [table['Name'] for table in response.get('TableList', [])]
        except ClientError as e:
            print(f"Error listing tables: {e}")
            return []

def main():
    """Main function to set up Glue schema"""
    print("RadStream Glue Schema Setup")
    print("=" * 30)
    
    # Initialize Glue setup
    glue_setup = GlueSchemaSetup(region='us-east-1')
    
    print("Setting up Glue schema...")
    print("=" * 25)
    
    # Set up complete schema
    results = glue_setup.setup_complete_schema()
    
    # Print summary
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"Successfully created: {successful}/{total} Glue components")
    
    for component, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {component}: {status}")
    
    if successful == total:
        print("\n🎉 All Glue components created successfully!")
        print("\nNext steps:")
        print("1. Run the crawler to discover data")
        print("2. Test Athena queries (athena_queries.sql)")
        print("3. Set up QuickSight dashboards")
    else:
        print(f"\n⚠️  {total - successful} components failed to create. Check AWS permissions and try again.")

if __name__ == "__main__":
    main()
