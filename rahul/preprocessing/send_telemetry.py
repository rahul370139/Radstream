#!/usr/bin/env python3
"""
Lambda function to send telemetry data for RadStream medical imaging pipeline
Centralized telemetry sending function for pipeline events
"""

import json
import boto3
import time
import os
from datetime import datetime
from typing import Dict, Any
from botocore.exceptions import ClientError

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for sending telemetry data
    
    Args:
        event: Event containing telemetry data
        context: Lambda context object
        
    Returns:
        Dict containing telemetry sending result
    """
    start_time = time.time()
    
    try:
        # Extract telemetry data from event
        telemetry_data = event.get('telemetry', {})
        study_id = telemetry_data.get('studyId', 'unknown')
        
        print(f"Sending telemetry for study {study_id}")
        
        # Add additional metadata
        telemetry_data.update({
            'function_name': context.function_name if context else 'unknown',
            'function_version': context.function_version if context else 'unknown',
            'request_id': context.aws_request_id if context else 'unknown',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send telemetry to Kinesis
        success = send_to_kinesis(telemetry_data)
        
        if not success:
            return {
                'success': False,
                'error': 'Failed to send telemetry to Kinesis',
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        
        # Calculate processing time
        latency_ms = int((time.time() - start_time) * 1000)
        
        print(f"Telemetry sent successfully in {latency_ms}ms for study {study_id}")
        
        return {
            'success': True,
            'latency_ms': latency_ms,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in telemetry sending: {str(e)}"
        print(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'latency_ms': int((time.time() - start_time) * 1000)
        }

def send_to_kinesis(telemetry_data: Dict[str, Any]) -> bool:
    """
    Send telemetry data to Kinesis stream
    
    Args:
        telemetry_data: Telemetry event data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        kinesis_client = boto3.client('kinesis')
        
        # Get stream name from environment variable
        stream_name = os.environ.get('TELEMETRY_STREAM_NAME', 'radstream-telemetry')
        
        # Prepare the record
        record_data = json.dumps(telemetry_data)
        partition_key = telemetry_data.get('studyId', 'default')
        
        # Put record to Kinesis
        response = kinesis_client.put_record(
            StreamName=stream_name,
            Data=record_data,
            PartitionKey=partition_key
        )
        
        print(f"Telemetry sent to Kinesis - SequenceNumber: {response['SequenceNumber']}")
        return True
        
    except ClientError as e:
        print(f"Error sending telemetry to Kinesis: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error sending telemetry: {e}")
        return False

def send_batch_telemetry(telemetry_records: list) -> Dict[str, Any]:
    """
    Send multiple telemetry records in batch
    
    Args:
        telemetry_records: List of telemetry records
        
    Returns:
        Dict with batch sending results
    """
    try:
        kinesis_client = boto3.client('kinesis')
        stream_name = os.environ.get('TELEMETRY_STREAM_NAME', 'radstream-telemetry')
        
        # Prepare batch records
        records = []
        for i, telemetry_data in enumerate(telemetry_records):
            record_data = json.dumps(telemetry_data)
            partition_key = telemetry_data.get('studyId', f'record_{i}')
            
            records.append({
                'Data': record_data,
                'PartitionKey': partition_key
            })
        
        # Send batch to Kinesis
        response = kinesis_client.put_records(
            StreamName=stream_name,
            Records=records
        )
        
        # Check for failed records
        failed_count = response['FailedRecordCount']
        successful_count = len(records) - failed_count
        
        return {
            'success': failed_count == 0,
            'successful_count': successful_count,
            'failed_count': failed_count,
            'failed_records': response.get('Records', []) if failed_count > 0 else []
        }
        
    except Exception as e:
        print(f"Error sending batch telemetry: {e}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # Test function
    test_telemetry = {
        'studyId': 'TEST-001',
        'stage': 'test_telemetry',
        'status': 'success',
        'latency_ms': 100,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    print("Testing telemetry sending...")
    result = send_to_kinesis(test_telemetry)
    print(f"Result: {result}")
    
    # Test batch sending
    test_records = [
        {'studyId': 'TEST-001', 'stage': 'stage1', 'status': 'success'},
        {'studyId': 'TEST-002', 'stage': 'stage2', 'status': 'success'},
        {'studyId': 'TEST-003', 'stage': 'stage3', 'status': 'success'}
    ]
    
    print("\nTesting batch telemetry sending...")
    batch_result = send_batch_telemetry(test_records)
    print(f"Batch result: {json.dumps(batch_result, indent=2)}")
