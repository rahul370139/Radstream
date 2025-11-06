#!/usr/bin/env python3
"""
EventBridge Setup Script for RadStream Medical Imaging Pipeline
Configures S3 event rules to trigger Step Functions workflow
"""

import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, List, Optional

class EventBridgeSetup:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize EventBridge setup with AWS region"""
        self.region = region
        self.eventbridge_client = boto3.client('events', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def create_rule(self, rule_name: str, event_pattern: Dict, targets: List[Dict]) -> bool:
        """Create an EventBridge rule with specified event pattern and targets"""
        try:
            # Check if rule already exists
            try:
                response = self.eventbridge_client.describe_rule(Name=rule_name)
                print(f"Rule {rule_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
            
            # Create the rule
            self.eventbridge_client.put_rule(
                Name=rule_name,
                EventPattern=json.dumps(event_pattern),
                State='ENABLED',
                Description=f'RadStream rule for {rule_name}'
            )
            print(f"Created EventBridge rule: {rule_name}")
            
            # Add targets to the rule
            if targets:
                self.eventbridge_client.put_targets(
                    Rule=rule_name,
                    Targets=targets
                )
                print(f"Added {len(targets)} target(s) to rule {rule_name}")
            
            return True
            
        except ClientError as e:
            print(f"Error creating rule {rule_name}: {e}")
            return False
    
    def create_s3_image_upload_rule(self, step_function_arn: str) -> bool:
        """Create EventBridge rule for S3 image uploads"""
        
        # Event pattern for S3 PutObject events
        event_pattern = {
            "source": ["aws.s3"],
            "detail-type": ["Object Created"],
            "detail": {
                "bucket": {
                    "name": [f"radstream-images-{self.account_id}"]
                },
                "object": {
                    "key": [
                        {
                            "prefix": "images/"
                        }
                    ]
                }
            }
        }
        
        # Target: Step Functions state machine
        targets = [
            {
                "Id": "1",
                "Arn": step_function_arn,
                "RoleArn": f"arn:aws:iam::{self.account_id}:role/EventBridgeStepFunctionsRole",
                "Input": {
                    "bucket": "$.detail.bucket.name",
                    "key": "$.detail.object.key",
                    "eventTime": "$.time",
                    "eventName": "$.detail-type"
                }
            }
        ]
        
        rule_name = "radstream-s3-image-upload"
        return self.create_rule(rule_name, event_pattern, targets)
    
    def create_s3_metadata_upload_rule(self, step_function_arn: str) -> bool:
        """Create EventBridge rule for S3 metadata JSON uploads"""
        
        # Event pattern for JSON metadata files
        event_pattern = {
            "source": ["aws.s3"],
            "detail-type": ["Object Created"],
            "detail": {
                "bucket": {
                    "name": [f"radstream-images-{self.account_id}"]
                },
                "object": {
                    "key": [
                        {
                            "suffix": ".json"
                        }
                    ]
                }
            }
        }
        
        # Target: Step Functions state machine
        targets = [
            {
                "Id": "1",
                "Arn": step_function_arn,
                "RoleArn": f"arn:aws:iam::{self.account_id}:role/EventBridgeStepFunctionsRole",
                "Input": {
                    "bucket": "$.detail.bucket.name",
                    "key": "$.detail.object.key",
                    "eventTime": "$.time",
                    "eventName": "$.detail-type",
                    "isMetadata": True
                }
            }
        ]
        
        rule_name = "radstream-s3-metadata-upload"
        return self.create_rule(rule_name, event_pattern, targets)
    
    def create_error_handling_rule(self, sns_topic_arn: Optional[str] = None) -> bool:
        """Create EventBridge rule for error handling and notifications"""
        
        # Event pattern for Step Functions failures
        event_pattern = {
            "source": ["aws.states"],
            "detail-type": ["Step Functions Execution Status Change"],
            "detail": {
                "status": ["FAILED", "ABORTED", "TIMED_OUT"],
                "stateMachineArn": [
                    f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:radstream-pipeline"
                ]
            }
        }
        
        targets = []
        
        # Add SNS target if provided
        if sns_topic_arn:
            targets.append({
                "Id": "1",
                "Arn": sns_topic_arn,
                "Input": {
                    "message": "RadStream pipeline execution failed",
                    "executionArn": "$.detail.executionArn",
                    "status": "$.detail.status",
                    "error": "$.detail.error"
                }
            })
        
        # Add CloudWatch Logs target for error logging
        targets.append({
            "Id": "2",
            "Arn": f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/events/radstream-errors",
            "Input": {
                "executionArn": "$.detail.executionArn",
                "status": "$.detail.status",
                "error": "$.detail.error",
                "timestamp": "$.time"
            }
        })
        
        rule_name = "radstream-error-handling"
        return self.create_rule(rule_name, event_pattern, targets)
    
    def create_telemetry_rule(self, kinesis_stream_arn: str) -> bool:
        """Create EventBridge rule for telemetry events"""
        
        # Event pattern for custom telemetry events
        event_pattern = {
            "source": ["radstream.telemetry"],
            "detail-type": ["Pipeline Stage Complete", "Inference Complete", "Error Occurred"]
        }
        
        targets = [
            {
                "Id": "1",
                "Arn": kinesis_stream_arn,
                "RoleArn": f"arn:aws:iam::{self.account_id}:role/EventBridgeKinesisRole",
                "Input": {
                    "studyId": "$.detail.studyId",
                    "stage": "$.detail.stage",
                    "latencyMs": "$.detail.latencyMs",
                    "timestamp": "$.time",
                    "errorCode": "$.detail.errorCode"
                }
            }
        ]
        
        rule_name = "radstream-telemetry"
        return self.create_rule(rule_name, event_pattern, targets)
    
    def list_rules(self) -> List[Dict]:
        """List all RadStream EventBridge rules"""
        try:
            response = self.eventbridge_client.list_rules(NamePrefix="radstream")
            return response.get('Rules', [])
        except ClientError as e:
            print(f"Error listing rules: {e}")
            return []
    
    def delete_rule(self, rule_name: str) -> bool:
        """Delete an EventBridge rule"""
        try:
            # Remove all targets first
            targets_response = self.eventbridge_client.list_targets_by_rule(Rule=rule_name)
            if targets_response.get('Targets'):
                target_ids = [target['Id'] for target in targets_response['Targets']]
                self.eventbridge_client.remove_targets(Rule=rule_name, Ids=target_ids)
                print(f"Removed {len(target_ids)} target(s) from rule {rule_name}")
            
            # Delete the rule
            self.eventbridge_client.delete_rule(Name=rule_name)
            print(f"Deleted rule: {rule_name}")
            return True
            
        except ClientError as e:
            print(f"Error deleting rule {rule_name}: {e}")
            return False
    
    def cleanup_rules(self, confirm: bool = False):
        """Delete all RadStream EventBridge rules"""
        if not confirm:
            print("This will delete ALL RadStream EventBridge rules. Set confirm=True to proceed.")
            return
        
        rules = self.list_rules()
        for rule in rules:
            rule_name = rule['Name']
            self.delete_rule(rule_name)

def create_iam_roles_template():
    """Create IAM roles template for EventBridge"""
    roles = {
        "EventBridgeStepFunctionsRole": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "states:StartExecution"
                    ],
                    "Resource": f"arn:aws:states:*:*:stateMachine:radstream-*"
                }
            ]
        },
        "EventBridgeKinesisRole": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "kinesis:PutRecord",
                        "kinesis:PutRecords"
                    ],
                    "Resource": f"arn:aws:kinesis:*:*:stream/radstream-*"
                }
            ]
        }
    }
    
    return roles

def main():
    """Main function to set up EventBridge infrastructure"""
    print("RadStream EventBridge Infrastructure Setup")
    print("=" * 45)
    
    # Initialize EventBridge setup
    eb_setup = EventBridgeSetup(region='us-east-1')
    
    # Note: These ARNs should be created by other setup scripts
    # For now, we'll use placeholder ARNs
    step_function_arn = f"arn:aws:states:us-east-1:{eb_setup.account_id}:stateMachine:radstream-pipeline"
    kinesis_stream_arn = f"arn:aws:kinesis:us-east-1:{eb_setup.account_id}:stream/radstream-telemetry"
    
    print("Creating EventBridge rules...")
    print("=" * 30)
    
    # Create rules
    rules_to_create = [
        ("S3 Image Upload Rule", lambda: eb_setup.create_s3_image_upload_rule(step_function_arn)),
        ("S3 Metadata Upload Rule", lambda: eb_setup.create_s3_metadata_upload_rule(step_function_arn)),
        ("Error Handling Rule", lambda: eb_setup.create_error_handling_rule()),
        ("Telemetry Rule", lambda: eb_setup.create_telemetry_rule(kinesis_stream_arn))
    ]
    
    results = {}
    
    for rule_name, create_func in rules_to_create:
        print(f"\nCreating {rule_name}...")
        success = create_func()
        results[rule_name] = success
        
        if success:
            print(f"✅ Successfully created {rule_name}")
        else:
            print(f"❌ Failed to create {rule_name}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"Successfully created: {successful}/{total} EventBridge rules")
    
    for rule_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {rule_name}: {status}")
    
    if successful == total:
        print("\n🎉 All EventBridge rules created successfully!")
        print("\nNext steps:")
        print("1. Create IAM roles for EventBridge (see iam_roles.json)")
        print("2. Set up Step Functions workflow (stepfunctions_setup.py)")
        print("3. Configure Kinesis stream (kinesis_setup.py)")
    else:
        print(f"\n⚠️  {total - successful} rules failed to create. Check AWS permissions and try again.")
    
    # Save IAM roles template
    roles_template = create_iam_roles_template()
    with open('eventbridge_iam_roles.json', 'w') as f:
        json.dump(roles_template, f, indent=2)
    print(f"\n📄 IAM roles template saved to: eventbridge_iam_roles.json")

if __name__ == "__main__":
    main()
