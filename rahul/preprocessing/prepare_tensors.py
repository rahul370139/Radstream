#!/usr/bin/env python3
"""
Lambda function to prepare image tensors for RadStream medical imaging pipeline
Downloads images from S3, preprocesses them, and prepares for model inference
"""

import json
import boto3
import time
import base64
import os
from datetime import datetime
from typing import Dict, Any, Tuple
from botocore.exceptions import ClientError
from PIL import Image
import numpy as np
import io

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for image preprocessing
    
    Args:
        event: Event from previous step containing metadata and S3 info
        context: Lambda context object
        
    Returns:
        Dict containing preprocessed data and metadata
    """
    start_time = time.time()
    
    try:
        # Extract information from event
        bucket = event.get('bucket', '')
        key = event.get('key', '')
        metadata = event.get('metadata', {})
        study_id = metadata.get('study_id', 'unknown')
        
        print(f"Preprocessing image for study {study_id}: s3://{bucket}/{key}")
        
        # Download image from S3
        s3_client = boto3.client('s3')
        
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            image_data = response['Body'].read()
        except ClientError as e:
            return {
                'success': False,
                'error': f"Failed to download image from S3: {str(e)}",
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        
        # Preprocess the image
        preprocessing_result = preprocess_image(image_data, metadata)
        
        if not preprocessing_result['success']:
            return {
                'success': False,
                'error': preprocessing_result['error'],
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        
        # Prepare preprocessed data for next step
        preprocessed_data = {
            'study_id': study_id,
            'original_key': key,
            'preprocessed_image': preprocessing_result['preprocessed_image'],
            'image_shape': preprocessing_result['image_shape'],
            'normalization_params': preprocessing_result['normalization_params'],
            'metadata': metadata
        }
        
        # Calculate processing time
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Send telemetry
        send_telemetry({
            'studyId': study_id,
            'stage': 'prepare_tensors',
            'status': 'success',
            'latency_ms': latency_ms,
            'image_shape': preprocessing_result['image_shape'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
        print(f"Preprocessing completed in {latency_ms}ms for study {study_id}")
        
        return {
            'success': True,
            'preprocessedData': preprocessed_data,
            'latency_ms': latency_ms,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in preprocessing: {str(e)}"
        print(error_msg)
        
        # Send error telemetry
        send_telemetry({
            'studyId': event.get('metadata', {}).get('study_id', 'unknown'),
            'stage': 'prepare_tensors',
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

def preprocess_image(image_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preprocess image data for model inference
    
    Args:
        image_data: Raw image bytes
        metadata: Image metadata
        
    Returns:
        Dict with preprocessing result
    """
    try:
        # Load image from bytes
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Get original dimensions
        original_width, original_height = image.size
        print(f"Original image size: {original_width}x{original_height}")
        
        # Resize image to model input size (224x224 for most medical imaging models)
        target_size = (224, 224)
        image_resized = image.resize(target_size, Image.Resampling.LANCZOS)
        
        # Convert to numpy array
        image_array = np.array(image_resized, dtype=np.float32)
        
        # Normalize pixel values to [0, 1]
        image_normalized = image_array / 255.0
        
        # Apply medical imaging specific normalization if needed
        # For chest X-rays, we might want to apply window/level normalization
        if metadata.get('modality') == 'X-RAY' and metadata.get('body_part') == 'CHEST':
            image_normalized = apply_chest_xray_normalization(image_normalized)
        
        # Convert to the format expected by the model (CHW format for PyTorch)
        # From HWC to CHW
        image_tensor = np.transpose(image_normalized, (2, 0, 1))
        
        # Add batch dimension
        image_tensor = np.expand_dims(image_tensor, axis=0)
        
        # Convert to base64 for JSON serialization
        image_bytes = image_tensor.tobytes()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Calculate normalization parameters for potential denormalization
        normalization_params = {
            'mean': float(np.mean(image_normalized)),
            'std': float(np.std(image_normalized)),
            'min': float(np.min(image_normalized)),
            'max': float(np.max(image_normalized))
        }
        
        return {
            'success': True,
            'preprocessed_image': image_base64,
            'image_shape': image_tensor.shape,
            'normalization_params': normalization_params,
            'original_size': (original_width, original_height),
            'target_size': target_size
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Image preprocessing failed: {str(e)}"
        }

def apply_chest_xray_normalization(image: np.ndarray) -> np.ndarray:
    """
    Apply chest X-ray specific normalization
    
    Args:
        image: Normalized image array [0, 1]
        
    Returns:
        Normalized image array
    """
    # Chest X-ray window/level normalization
    # Typical values: window=1500, level=-600
    window = 1500
    level = -600
    
    # Convert back to Hounsfield units range
    image_hu = (image * 4095) - 1024
    
    # Apply window/level
    image_windowed = np.clip((image_hu - level + window/2) / window, 0, 1)
    
    return image_windowed

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

def test_preprocessing():
    """Test the preprocessing function with sample data"""
    
    # Create a sample image
    test_image = Image.new('RGB', (512, 512), color='white')
    
    # Convert to bytes
    img_buffer = io.BytesIO()
    test_image.save(img_buffer, format='JPEG')
    image_data = img_buffer.getvalue()
    
    # Test metadata
    metadata = {
        'study_id': 'TEST-001',
        'view': 'PA',
        'modality': 'X-RAY',
        'body_part': 'CHEST'
    }
    
    print("Testing image preprocessing...")
    result = preprocess_image(image_data, metadata)
    
    if result['success']:
        print(f"✅ Preprocessing successful")
        print(f"   Image shape: {result['image_shape']}")
        print(f"   Normalization params: {result['normalization_params']}")
    else:
        print(f"❌ Preprocessing failed: {result['error']}")

if __name__ == "__main__":
    test_preprocessing()
