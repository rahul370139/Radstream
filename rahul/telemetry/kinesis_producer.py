#!/usr/bin/env python3
"""
Kinesis Producer for RadStream Medical Imaging Pipeline
Helper functions for sending telemetry data to Kinesis streams
"""

import json
import boto3
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

class KinesisProducer:
    def __init__(self, stream_name: str = 'radstream-telemetry', region: str = 'us-east-1'):
        """Initialize Kinesis producer"""
        self.stream_name = stream_name
        self.region = region
        self.kinesis_client = boto3.client('kinesis', region_name=region)
        
        # Verify stream exists
        self._verify_stream()
    
    def _verify_stream(self) -> bool:
        """Verify that the Kinesis stream exists"""
        try:
            response = self.kinesis_client.describe_stream(StreamName=self.stream_name)
            status = response['StreamDescription']['StreamStatus']
            if status != 'ACTIVE':
                raise Exception(f"Stream {self.stream_name} is not active (status: {status})")
            print(f"Connected to Kinesis stream: {self.stream_name}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise Exception(f"Stream {self.stream_name} not found. Please create it first.")
            raise Exception(f"Error connecting to stream: {e}")
    
    def send_telemetry(self, event_data: Dict[str, Any], 
                      partition_key: Optional[str] = None) -> bool:
        """
        Send single telemetry event to Kinesis stream
        
        Args:
            event_data: Telemetry event data
            partition_key: Partition key for the record (defaults to studyId)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add metadata
            event_data.update({
                'event_id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'producer': 'kinesis_producer'
            })
            
            # Determine partition key
            if not partition_key:
                partition_key = event_data.get('studyId', 'default')
            
            # Send record
            response = self.kinesis_client.put_record(
                StreamName=self.stream_name,
                Data=json.dumps(event_data),
                PartitionKey=partition_key
            )
            
            print(f"Telemetry sent - SequenceNumber: {response['SequenceNumber']}")
            return True
            
        except Exception as e:
            print(f"Error sending telemetry: {e}")
            return False
    
    def send_batch_telemetry(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send multiple telemetry events in batch
        
        Args:
            events: List of telemetry events
            
        Returns:
            Dict with batch sending results
        """
        try:
            # Prepare batch records
            records = []
            for event in events:
                # Add metadata
                event.update({
                    'event_id': str(uuid.uuid4()),
                    'timestamp': datetime.utcnow().isoformat(),
                    'producer': 'kinesis_producer'
                })
                
                records.append({
                    'Data': json.dumps(event),
                    'PartitionKey': event.get('studyId', 'default')
                })
            
            # Send batch
            response = self.kinesis_client.put_records(
                StreamName=self.stream_name,
                Records=records
            )
            
            # Analyze results
            failed_count = response['FailedRecordCount']
            successful_count = len(records) - failed_count
            
            result = {
                'success': failed_count == 0,
                'successful_count': successful_count,
                'failed_count': failed_count,
                'total_count': len(records)
            }
            
            if failed_count > 0:
                result['failed_records'] = [
                    record for record in response.get('Records', [])
                    if 'ErrorCode' in record
                ]
            
            print(f"Batch telemetry sent - Success: {successful_count}, Failed: {failed_count}")
            return result
            
        except Exception as e:
            print(f"Error sending batch telemetry: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_count': len(events)
            }
    
    def send_pipeline_event(self, study_id: str, stage: str, status: str, 
                           latency_ms: int, **kwargs) -> bool:
        """
        Send standardized pipeline event
        
        Args:
            study_id: Study identifier
            stage: Pipeline stage (validate, preprocess, inference, etc.)
            status: Event status (success, failed, error)
            latency_ms: Processing latency in milliseconds
            **kwargs: Additional event data
            
        Returns:
            bool: True if successful, False otherwise
        """
        event_data = {
            'studyId': study_id,
            'stage': stage,
            'status': status,
            'latency_ms': latency_ms,
            **kwargs
        }
        
        return self.send_telemetry(event_data)
    
    def send_error_event(self, study_id: str, stage: str, error_code: str, 
                        error_message: str, **kwargs) -> bool:
        """
        Send error event
        
        Args:
            study_id: Study identifier
            stage: Pipeline stage where error occurred
            error_code: Error code
            error_message: Error message
            **kwargs: Additional error data
            
        Returns:
            bool: True if successful, False otherwise
        """
        event_data = {
            'studyId': study_id,
            'stage': stage,
            'status': 'error',
            'error_code': error_code,
            'error_message': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            **kwargs
        }
        
        return self.send_telemetry(event_data)
    
    def send_performance_metrics(self, study_id: str, metrics: Dict[str, Any]) -> bool:
        """
        Send performance metrics
        
        Args:
            study_id: Study identifier
            metrics: Performance metrics dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        event_data = {
            'studyId': study_id,
            'stage': 'performance_metrics',
            'status': 'success',
            'metrics': metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return self.send_telemetry(event_data)
    
    def get_stream_info(self) -> Dict[str, Any]:
        """Get information about the Kinesis stream"""
        try:
            response = self.kinesis_client.describe_stream(StreamName=self.stream_name)
            stream_info = response['StreamDescription']
            
            return {
                'stream_name': stream_info['StreamName'],
                'stream_status': stream_info['StreamStatus'],
                'shard_count': stream_info['ShardCount'],
                'retention_period': stream_info['RetentionPeriodHours'],
                'stream_arn': stream_info['StreamARN']
            }
        except Exception as e:
            print(f"Error getting stream info: {e}")
            return {}
    
    def list_shards(self) -> List[Dict[str, Any]]:
        """List all shards in the stream"""
        try:
            response = self.kinesis_client.list_shards(StreamName=self.stream_name)
            return response.get('Shards', [])
        except Exception as e:
            print(f"Error listing shards: {e}")
            return []

def create_telemetry_events(study_id: str, stages: List[str]) -> List[Dict[str, Any]]:
    """
    Create sample telemetry events for testing
    
    Args:
        study_id: Study identifier
        stages: List of pipeline stages
        
    Returns:
        List of telemetry events
    """
    events = []
    
    for i, stage in enumerate(stages):
        # Simulate processing time
        latency_ms = 100 + (i * 50) + (hash(study_id) % 100)
        
        event = {
            'studyId': study_id,
            'stage': stage,
            'status': 'success',
            'latency_ms': latency_ms,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add stage-specific data
        if stage == 'validate_metadata':
            event['validation_errors'] = 0
        elif stage == 'prepare_tensors':
            event['image_shape'] = [1, 3, 224, 224]
        elif stage == 'inference':
            event['model_version'] = '1.0.0'
            event['confidence'] = 0.95
        elif stage == 'store_results':
            event['results_size_bytes'] = 1024
        
        events.append(event)
    
    return events

def main():
    """Test the Kinesis producer"""
    print("Testing Kinesis Producer")
    print("=" * 25)
    
    # Initialize producer
    try:
        producer = KinesisProducer()
    except Exception as e:
        print(f"Failed to initialize producer: {e}")
        return
    
    # Test single event
    print("\n1. Testing single event...")
    success = producer.send_pipeline_event(
        study_id='TEST-001',
        stage='validate_metadata',
        status='success',
        latency_ms=150
    )
    print(f"Single event result: {'✅ Success' if success else '❌ Failed'}")
    
    # Test batch events
    print("\n2. Testing batch events...")
    test_events = create_telemetry_events('TEST-002', [
        'validate_metadata',
        'prepare_tensors',
        'inference',
        'store_results'
    ])
    
    batch_result = producer.send_batch_telemetry(test_events)
    print(f"Batch events result: {batch_result}")
    
    # Test error event
    print("\n3. Testing error event...")
    error_success = producer.send_error_event(
        study_id='TEST-003',
        stage='inference',
        error_code='MODEL_ERROR',
        error_message='Model inference failed'
    )
    print(f"Error event result: {'✅ Success' if error_success else '❌ Failed'}")
    
    # Get stream info
    print("\n4. Stream information:")
    stream_info = producer.get_stream_info()
    for key, value in stream_info.items():
        print(f"  {key}: {value}")
    
    print("\n🎉 Kinesis producer test completed!")

if __name__ == "__main__":
    main()
