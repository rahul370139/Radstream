#!/usr/bin/env python3
"""
Lambda function to validate metadata for RadStream medical imaging pipeline
Validates JSON sidecar files for required fields and format
"""

import json
import boto3
import time
from datetime import datetime
from typing import Dict, Any, List
from botocore.exceptions import ClientError

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for metadata validation
    
    Args:
        event: EventBridge event containing S3 object information
        context: Lambda context object
        
    Returns:
        Dict containing validation result and metadata
    """
    start_time = time.time()
    
    try:
        # Extract S3 information from event
        bucket = event.get('bucket', '')
        key = event.get('key', '')
        
        print(f"Validating metadata for: s3://{bucket}/{key}")
        
        # Download and parse JSON metadata
        s3_client = boto3.client('s3')
        
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            metadata_content = response['Body'].read().decode('utf-8')
            metadata = json.loads(metadata_content)
        except ClientError as e:
            return {
                'valid': False,
                'errors': [f"Failed to download metadata from S3: {str(e)}"],
                'studyId': None,
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'errors': [f"Invalid JSON format: {str(e)}"],
                'studyId': None,
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        
        # Validate required fields
        validation_result = validate_metadata_fields(metadata)
        
        # Calculate processing time
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Prepare response
        response = {
            'valid': validation_result['valid'],
            'errors': validation_result['errors'],
            'studyId': metadata.get('study_id') if validation_result['valid'] else None,
            'metadata': metadata if validation_result['valid'] else None,
            'latency_ms': latency_ms,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send telemetry if validation successful
        if validation_result['valid']:
            send_telemetry({
                'studyId': metadata['study_id'],
                'stage': 'validate_metadata',
                'status': 'success',
                'latency_ms': latency_ms,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            send_telemetry({
                'studyId': key,  # Use key as fallback
                'stage': 'validate_metadata',
                'status': 'failed',
                'latency_ms': latency_ms,
                'error_code': 'VALIDATION_ERROR',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        print(f"Validation completed in {latency_ms}ms - Valid: {validation_result['valid']}")
        return response
        
    except Exception as e:
        error_msg = f"Unexpected error in validation: {str(e)}"
        print(error_msg)
        
        # Send error telemetry
        send_telemetry({
            'studyId': event.get('key', 'unknown'),
            'stage': 'validate_metadata',
            'status': 'error',
            'latency_ms': int((time.time() - start_time) * 1000),
            'error_code': 'UNEXPECTED_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {
            'valid': False,
            'errors': [error_msg],
            'studyId': None,
            'latency_ms': int((time.time() - start_time) * 1000)
        }

def validate_metadata_fields(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate required fields in metadata JSON
    
    Args:
        metadata: Parsed JSON metadata
        
    Returns:
        Dict with validation result and errors
    """
    required_fields = {
        'study_id': str,
        'view': str,
        'timestamp': str
    }
    
    optional_fields = {
        'patient_id': str,
        'study_date': str,
        'modality': str,
        'body_part': str,
        'image_size': dict,
        'annotations': list
    }
    
    errors = []
    
    # Check required fields
    for field, expected_type in required_fields.items():
        if field not in metadata:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(metadata[field], expected_type):
            errors.append(f"Field '{field}' must be of type {expected_type.__name__}")
        elif field == 'study_id' and len(metadata[field].strip()) == 0:
            errors.append("Field 'study_id' cannot be empty")
        elif field == 'view' and metadata[field] not in ['PA', 'AP', 'LATERAL', 'OBLIQUE', 'OTHER']:
            errors.append(f"Field 'view' must be one of: PA, AP, LATERAL, OBLIQUE, OTHER")
        elif field == 'timestamp':
            # Validate timestamp format (ISO 8601)
            try:
                datetime.fromisoformat(metadata[field].replace('Z', '+00:00'))
            except ValueError:
                errors.append("Field 'timestamp' must be in ISO 8601 format")
    
    # Check optional fields if present
    for field, expected_type in optional_fields.items():
        if field in metadata and not isinstance(metadata[field], expected_type):
            errors.append(f"Optional field '{field}' must be of type {expected_type.__name__}")
    
    # Validate study_id format (alphanumeric with hyphens/underscores)
    if 'study_id' in metadata and validation_result['valid']:
        study_id = metadata['study_id']
        if not all(c.isalnum() or c in '-_' for c in study_id):
            errors.append("Field 'study_id' can only contain alphanumeric characters, hyphens, and underscores")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def send_telemetry(event_data: Dict[str, Any]) -> None:
    """
    Send telemetry data to Kinesis stream
    
    Args:
        event_data: Telemetry event data
    """
    try:
        kinesis_client = boto3.client('kinesis')
        
        # Get stream name from environment variable or use default
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

# Test function for local development
def test_validation():
    """Test the validation function with sample data"""
    
    # Valid metadata
    valid_metadata = {
        "study_id": "STUDY-001-2024",
        "view": "PA",
        "timestamp": "2024-01-15T10:30:00Z",
        "patient_id": "PAT-12345",
        "modality": "X-RAY",
        "body_part": "CHEST"
    }
    
    # Invalid metadata
    invalid_metadata = {
        "study_id": "",
        "view": "INVALID",
        "timestamp": "not-a-date"
    }
    
    print("Testing valid metadata:")
    result1 = validate_metadata_fields(valid_metadata)
    print(f"Valid: {result1['valid']}, Errors: {result1['errors']}")
    
    print("\nTesting invalid metadata:")
    result2 = validate_metadata_fields(invalid_metadata)
    print(f"Valid: {result2['valid']}, Errors: {result2['errors']}")

if __name__ == "__main__":
    test_validation()
