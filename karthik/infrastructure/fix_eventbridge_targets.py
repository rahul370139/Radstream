#!/usr/bin/env python3
"""
Fix EventBridge Rules - Add Missing Targets
This script fixes EventBridge rules that exist but have no targets configured
"""

import boto3
import json
from botocore.exceptions import ClientError

def create_eventbridge_role_if_needed(iam_client, account_id):
    """Create EventBridge role to invoke Step Functions if it doesn't exist"""
    role_name = "EventBridgeStepFunctionsRole"
    
    try:
        # Check if role exists
        iam_client.get_role(RoleName=role_name)
        print(f"✅ IAM role {role_name} already exists")
        return f"arn:aws:iam::{account_id}:role/{role_name}"
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            # Create the role
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "events.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "states:StartExecution"
                        ],
                        "Resource": f"arn:aws:states:*:{account_id}:stateMachine:radstream-*"
                    }
                ]
            }
            
            # Create role
            iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Allows EventBridge to start Step Functions executions"
            )
            
            # Attach inline policy
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="StepFunctionsInvokePolicy",
                PolicyDocument=json.dumps(policy_document)
            )
            
            print(f"✅ Created IAM role: {role_name}")
            return f"arn:aws:iam::{account_id}:role/{role_name}"
        else:
            raise

def fix_eventbridge_targets():
    """Fix EventBridge rules by adding missing targets"""
    region = 'us-east-1'
    events_client = boto3.client('events', region_name=region)
    iam_client = boto3.client('iam', region_name=region)
    sts_client = boto3.client('sts', region_name=region)
    
    # Get account ID
    account_id = sts_client.get_caller_identity()['Account']
    print(f"Using AWS Account ID: {account_id}\n")
    
    # Get Step Functions ARN
    stepfunctions_client = boto3.client('stepfunctions', region_name=region)
    state_machines = stepfunctions_client.list_state_machines()
    state_machine_arn = None
    
    for sm in state_machines['stateMachines']:
        if sm['name'] == 'radstream-pipeline':
            state_machine_arn = sm['stateMachineArn']
            break
    
    if not state_machine_arn:
        print("❌ Step Functions state machine 'radstream-pipeline' not found!")
        return False
    
    print(f"✅ Found Step Functions: {state_machine_arn}\n")
    
    # Create IAM role if needed
    role_arn = create_eventbridge_role_if_needed(iam_client, account_id)
    print()
    
    # Rules to fix
    rules_to_fix = [
        {
            'name': 'radstream-s3-image-upload',
            'target': {
                'Id': '1',
                'Arn': state_machine_arn,
                'RoleArn': role_arn,
                'InputTransformer': {
                    'InputPathsMap': {
                        'bucket': '$.detail.bucket.name',
                        'key': '$.detail.object.key',
                        'time': '$.time'
                    },
                    'InputTemplate': '{"bucket": "<bucket>", "key": "<key>", "study_id": "<key>", "eventTime": "<time>"}'
                }
            }
        },
        {
            'name': 'radstream-s3-metadata-upload',
            'target': {
                'Id': '1',
                'Arn': state_machine_arn,
                'RoleArn': role_arn,
                'InputTransformer': {
                    'InputPathsMap': {
                        'bucket': '$.detail.bucket.name',
                        'key': '$.detail.object.key',
                        'time': '$.time'
                    },
                    'InputTemplate': '{"bucket": "<bucket>", "key": "<key>", "study_id": "<key>", "eventTime": "<time>", "isMetadata": true}'
                }
            }
        }
    ]
    
    print("Fixing EventBridge rules...")
    print("=" * 50)
    
    for rule_config in rules_to_fix:
        rule_name = rule_config['name']
        target = rule_config['target']
        
        try:
            # Check current targets
            current_targets = events_client.list_targets_by_rule(Rule=rule_name)
            
            if current_targets.get('Targets'):
                print(f"⚠️  Rule {rule_name} already has {len(current_targets['Targets'])} target(s)")
                # Remove existing targets first
                target_ids = [t['Id'] for t in current_targets['Targets']]
                events_client.remove_targets(Rule=rule_name, Ids=target_ids)
                print(f"   Removed existing targets")
            
            # Add new target
            events_client.put_targets(
                Rule=rule_name,
                Targets=[target]
            )
            
            print(f"✅ Added target to rule: {rule_name}")
            print(f"   Target: Step Functions ({state_machine_arn})")
            
        except ClientError as e:
            print(f"❌ Error fixing rule {rule_name}: {e}")
            continue
    
    print("\n" + "=" * 50)
    print("✅ EventBridge targets configured!")
    print("\nNext steps:")
    print("1. Upload a test image to: s3://radstream-images-{}/images/your-image.jpg".format(account_id))
    print("2. Check Step Functions console for automatic execution")
    print("\nNote: Event pattern currently matches 'images/' prefix.")
    print("   For 'test/' prefix, update event pattern or upload to 'images/' folder")

if __name__ == "__main__":
    fix_eventbridge_targets()

