#!/usr/bin/env python3
"""
Lambda function to store inference results for RadStream medical imaging pipeline
Stores model outputs and metadata to S3 results bucket
"""

import json
import os
import boto3
import time
from datetime import datetime
from typing import Dict, Any
from botocore.exceptions import ClientError

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for storing inference results
    
    Args:
        event: Event containing inference results and metadata
        context: Lambda context object
        
    Returns:
        Dict containing storage result and metadata
    """
    start_time = time.time()
    
    try:
        # Extract information from event
        study_id = event.get('studyId', 'unknown')
        inference_results = event.get('inference', {})
        metadata = event.get('metadata', {})
        
        print(f"Storing results for study {study_id}")
        
        # Prepare results data
        results_data = {
            'study_id': study_id,
            'timestamp': datetime.utcnow().isoformat(),
            'inference_results': inference_results,
            'metadata': metadata,
            'pipeline_version': '1.0.0'
        }
        
        # Store results in S3
        s3_client = boto3.client('s3')
        results_bucket = os.environ.get('RESULTS_BUCKET', f'radstream-results-{context.invoked_function_arn.split(":")[4]}')
        
        # Create results key
        results_key = f"results/{study_id}/{datetime.utcnow().strftime('%Y/%m/%d')}/{study_id}_results.json"
        
        try:
            s3_client.put_object(
                Bucket=results_bucket,
                Key=results_key,
                Body=json.dumps(results_data, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            print(f"Results stored: s3://{results_bucket}/{results_key}")
            
        except ClientError as e:
            return {
                'success': False,
                'error': f"Failed to store results in S3: {str(e)}",
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        
        # Calculate processing time
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Send telemetry
        send_telemetry({
            'studyId': study_id,
            'stage': 'store_results',
            'status': 'success',
            'latency_ms': latency_ms,
            'results_key': results_key,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        print(f"Results storage completed in {latency_ms}ms for study {study_id}")
        
        return {
            'success': True,
            'results': {
                'bucket': results_bucket,
                'key': results_key,
                'study_id': study_id
            },
            'latency_ms': latency_ms,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in results storage: {str(e)}"
        print(error_msg)
        
        # Send error telemetry
        send_telemetry({
            'studyId': event.get('studyId', 'unknown'),
            'stage': 'store_results',
            'status': 'error',
            'latency_ms': int((time.time() - start_time) * 1000),
            'error_code': 'UNEXPECTED_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {
            'success': False,
            'error': error_msg,
            'latency_ms': int((time.time() - start_time) * 1000)
        }

def send_telemetry(event_data: Dict[str, Any]) -> None:
    """
    Send telemetry data to Kinesis stream
    
    Args:
        event_data: Telemetry event data
    """
    try:
        kinesis_client = boto3.client('kinesis')
        
        # Get stream name from environment variable
        stream_name = os.environ.get('TELEMETRY_STREAM_NAME', 'radstream-telemetry')
        
        # Put record to Kinesis
        kinesis_client.put_record(
            StreamName=stream_name,
            Data=json.dumps(event_data),
            PartitionKey=event_data.get('studyId', 'default')
        )
        
    except Exception as e:
        print(f"Failed to send telemetry: {str(e)}")
        # Don't raise exception - telemetry failure shouldn't break the pipeline

if __name__ == "__main__":
    # Test function
    test_event = {
        'studyId': 'TEST-001',
        'inference': {
            'predictions': [
                {'class': 'normal', 'confidence': 0.95},
                {'class': 'pneumonia', 'confidence': 0.05}
            ],
            'model_version': '1.0.0'
        },
        'metadata': {
            'study_id': 'TEST-001',
            'view': 'PA',
            'timestamp': '2024-01-15T10:30:00Z'
        }
    }
    
    print("Testing store results function...")
    result = lambda_handler(test_event, None)
    print(f"Result: {json.dumps(result, indent=2)}")
