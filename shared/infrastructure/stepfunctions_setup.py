#!/usr/bin/env python3
"""
Step Functions Setup Script for RadStream Medical Imaging Pipeline
Creates the orchestration workflow for the medical imaging inference pipeline
"""

import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, List, Optional

class StepFunctionsSetup:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize Step Functions setup with AWS region"""
        self.region = region
        self.sf_client = boto3.client('stepfunctions', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            print(f"Using AWS Account ID: {self.account_id}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def create_state_machine(self, name: str, definition: Dict, role_arn: str) -> bool:
        """Create a Step Functions state machine"""
        try:
            # Check if state machine already exists
            try:
                response = self.sf_client.describe_state_machine(
                    stateMachineArn=f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:{name}"
                )
                print(f"State machine {name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'StateMachineDoesNotExist':
                    raise
            
            # Create the state machine
            self.sf_client.create_state_machine(
                name=name,
                definition=json.dumps(definition, indent=2),
                roleArn=role_arn,
                type='STANDARD',
                loggingConfiguration={
                    'level': 'ALL',
                    'includeExecutionData': True,
                    'destinations': [
                        {
                            'cloudWatchLogsLogGroup': {
                                'logGroupArn': f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/stepfunctions/radstream-pipeline"
                            }
                        }
                    ]
                },
                tracingConfiguration={
                    'enabled': True
                }
            )
            print(f"Created state machine: {name}")
            return True
            
        except ClientError as e:
            print(f"Error creating state machine {name}: {e}")
            return False
    
    def get_radstream_pipeline_definition(self) -> Dict:
        """Get the ASL definition for the RadStream pipeline"""
        return {
            "Comment": "RadStream Medical Imaging Pipeline - Orchestrates image processing workflow",
            "StartAt": "ValidateInput",
            "States": {
                "ValidateInput": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:{}:function:radstream-validate-metadata".format(self.account_id),
                    "Next": "CheckValidationResult",
                    "Retry": [
                        {
                            "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandleValidationError",
                            "ResultPath": "$.error"
                        }
                    ],
                    "ResultPath": "$.validation"
                },
                "CheckValidationResult": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.validation.valid",
                            "BooleanEquals": True,
                            "Next": "PrepareImage"
                        }
                    ],
                    "Default": "HandleValidationError"
                },
                "PrepareImage": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:{}:function:radstream-prepare-tensors".format(self.account_id),
                    "Next": "InvokeInference",
                    "Retry": [
                        {
                            "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandlePreprocessingError",
                            "ResultPath": "$.error"
                        }
                    ],
                    "ResultPath": "$.preprocessing"
                },
                "InvokeInference": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::eks:runJob.sync",
                    "Parameters": {
                        "ClusterName": "radstream-cluster",
                        "JobDefinition": "radstream-inference-job",
                        "JobName": "radstream-inference-{}.{}".format("$.studyId", "$$.Execution.Name"),
                        "JobQueue": "radstream-queue",
                        "Parameters": {
                            "studyId": "$.studyId",
                            "bucket": "$.bucket",
                            "key": "$.key",
                            "preprocessedData": "$.preprocessing.preprocessedData"
                        }
                    },
                    "Next": "StoreResults",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "IntervalSeconds": 5,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandleInferenceError",
                            "ResultPath": "$.error"
                        }
                    ],
                    "ResultPath": "$.inference"
                },
                "StoreResults": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:{}:function:radstream-store-results".format(self.account_id),
                    "Next": "SendTelemetry",
                    "Retry": [
                        {
                            "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandleStorageError",
                            "ResultPath": "$.error"
                        }
                    ],
                    "ResultPath": "$.storage"
                },
                "SendTelemetry": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:{}:function:radstream-send-telemetry".format(self.account_id),
                    "Next": "PipelineComplete",
                    "Retry": [
                        {
                            "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
                            "IntervalSeconds": 1,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "PipelineComplete",
                            "ResultPath": "$.telemetryError"
                        }
                    ],
                    "ResultPath": "$.telemetry"
                },
                "PipelineComplete": {
                    "Type": "Succeed",
                    "Output": {
                        "studyId": "$.studyId",
                        "status": "completed",
                        "timestamp": "$$.State.EnteredTime",
                        "results": "$.storage.results",
                        "telemetry": "$.telemetry"
                    }
                },
                "HandleValidationError": {
                    "Type": "Fail",
                    "Cause": "Validation failed",
                    "Error": "ValidationError",
                    "Comment": "Input validation failed - check metadata format"
                },
                "HandlePreprocessingError": {
                    "Type": "Fail",
                    "Cause": "Image preprocessing failed",
                    "Error": "PreprocessingError",
                    "Comment": "Failed to preprocess image - check image format and size"
                },
                "HandleInferenceError": {
                    "Type": "Fail",
                    "Cause": "Model inference failed",
                    "Error": "InferenceError",
                    "Comment": "Failed to run inference - check EKS cluster and model"
                },
                "HandleStorageError": {
                    "Type": "Fail",
                    "Cause": "Result storage failed",
                    "Error": "StorageError",
                    "Comment": "Failed to store results - check S3 permissions"
                }
            }
        }
    
    def get_error_handling_definition(self) -> Dict:
        """Get the ASL definition for error handling workflow"""
        return {
            "Comment": "RadStream Error Handling Workflow - Processes failed pipeline executions",
            "StartAt": "AnalyzeError",
            "States": {
                "AnalyzeError": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:{}:function:radstream-analyze-error".format(self.account_id),
                    "Next": "DetermineAction",
                    "ResultPath": "$.errorAnalysis"
                },
                "DetermineAction": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.errorAnalysis.severity",
                            "StringEquals": "HIGH",
                            "Next": "SendAlert"
                        },
                        {
                            "Variable": "$.errorAnalysis.severity",
                            "StringEquals": "MEDIUM",
                            "Next": "LogError"
                        }
                    ],
                    "Default": "LogError"
                },
                "SendAlert": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::sns:publish",
                    "Parameters": {
                        "TopicArn": f"arn:aws:sns:{self.region}:{self.account_id}:radstream-alerts",
                        "Message": "High severity error in RadStream pipeline",
                        "Subject": "RadStream Pipeline Alert"
                    },
                    "Next": "LogError"
                },
                "LogError": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:{}:function:radstream-log-error".format(self.account_id),
                    "Next": "End"
                },
                "End": {
                    "Type": "Succeed"
                }
            }
        }
    
    def create_iam_role_definition(self) -> Dict:
        """Create IAM role definition for Step Functions"""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": [
                        f"arn:aws:lambda:{self.region}:{self.account_id}:function:radstream-*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "eks:DescribeCluster",
                        "eks:ListClusters"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "eks:RunJob"
                    ],
                    "Resource": [
                        f"arn:aws:eks:{self.region}:{self.account_id}:cluster/radstream-cluster",
                        f"arn:aws:eks:{self.region}:{self.account_id}:jobdefinition/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::radstream-*/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kinesis:PutRecord"
                    ],
                    "Resource": [
                        f"arn:aws:kinesis:{self.region}:{self.account_id}:stream/radstream-*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "sns:Publish"
                    ],
                    "Resource": [
                        f"arn:aws:sns:{self.region}:{self.account_id}:radstream-*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": [
                        f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/stepfunctions/*"
                    ]
                }
            ]
        }
    
    def list_state_machines(self) -> List[Dict]:
        """List all RadStream state machines"""
        try:
            response = self.sf_client.list_state_machines()
            radstream_machines = [
                machine for machine in response.get('stateMachines', [])
                if machine['name'].startswith('radstream-')
            ]
            return radstream_machines
        except ClientError as e:
            print(f"Error listing state machines: {e}")
            return []
    
    def delete_state_machine(self, name: str) -> bool:
        """Delete a state machine"""
        try:
            self.sf_client.delete_state_machine(
                stateMachineArn=f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:{name}"
            )
            print(f"Deleted state machine: {name}")
            return True
        except ClientError as e:
            print(f"Error deleting state machine {name}: {e}")
            return False
    
    def cleanup_state_machines(self, confirm: bool = False):
        """Delete all RadStream state machines"""
        if not confirm:
            print("This will delete ALL RadStream state machines. Set confirm=True to proceed.")
            return
        
        machines = self.list_state_machines()
        for machine in machines:
            machine_name = machine['name']
            self.delete_state_machine(machine_name)

def main():
    """Main function to set up Step Functions infrastructure"""
    print("RadStream Step Functions Infrastructure Setup")
    print("=" * 50)
    
    # Initialize Step Functions setup
    sf_setup = StepFunctionsSetup(region='us-east-1')
    
    # IAM role ARN (should be created separately)
    role_arn = f"arn:aws:iam::{sf_setup.account_id}:role/RadStreamStepFunctionsRole"
    
    print("Creating Step Functions state machines...")
    print("=" * 40)
    
    # Create main pipeline state machine
    pipeline_definition = sf_setup.get_radstream_pipeline_definition()
    pipeline_success = sf_setup.create_state_machine(
        "radstream-pipeline",
        pipeline_definition,
        role_arn
    )
    
    # Create error handling state machine
    error_definition = sf_setup.get_error_handling_definition()
    error_success = sf_setup.create_state_machine(
        "radstream-error-handler",
        error_definition,
        role_arn
    )
    
    # Print summary
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    
    results = {
        "Main Pipeline": pipeline_success,
        "Error Handler": error_success
    }
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"Successfully created: {successful}/{total} state machines")
    
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name}: {status}")
    
    if successful == total:
        print("\n🎉 All Step Functions state machines created successfully!")
        print("\nNext steps:")
        print("1. Create IAM role for Step Functions (see stepfunctions_iam_role.json)")
        print("2. Deploy Lambda functions (lambda_setup.py)")
        print("3. Set up EKS cluster and job definitions")
    else:
        print(f"\n⚠️  {total - successful} state machines failed to create. Check AWS permissions and try again.")
    
    # Save IAM role definition
    iam_role = sf_setup.create_iam_role_definition()
    with open('stepfunctions_iam_role.json', 'w') as f:
        json.dump(iam_role, f, indent=2)
    print(f"\n📄 IAM role definition saved to: stepfunctions_iam_role.json")
    
    # Save state machine definitions
    with open('radstream_pipeline_definition.json', 'w') as f:
        json.dump(pipeline_definition, f, indent=2)
    print(f"📄 Pipeline definition saved to: radstream_pipeline_definition.json")
    
    with open('radstream_error_handler_definition.json', 'w') as f:
        json.dump(error_definition, f, indent=2)
    print(f"📄 Error handler definition saved to: radstream_error_handler_definition.json")

if __name__ == "__main__":
    main()
