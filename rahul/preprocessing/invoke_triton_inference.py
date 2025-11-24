"""
Lambda function to invoke Triton Inference Server and map TXR logits to CheXpert labels
"""
import json
import os
import time
import base64
import boto3
from typing import Dict, Any, List
import requests
import numpy as np
from scipy.special import expit as sigmoid

# Initialize AWS clients
s3_client = boto3.client('s3')
kinesis_client = boto3.client('kinesis')

# Triton endpoint from environment variable
TRITON_ENDPOINT = os.environ.get('TRITON_ENDPOINT', 'http://abb2c3656a2744f8191015f5b516d8fc-1489982899.us-east-1.elb.amazonaws.com:8000')
MODEL_NAME = os.environ.get('TRITON_MODEL_NAME', 'chexpert_classifier')
STUDY_ID = os.environ.get('STUDY_ID', '')

# CheXpert labels (13 findings, excluding "No Finding")
CHEXPERT13_LABELS = [
    "Enlarged Cardiomediastinum",
    "Cardiomegaly",
    "Lung Opacity",
    "Lung Lesion",
    "Edema",
    "Consolidation",
    "Pneumonia",
    "Atelectasis",
    "Pneumothorax",
    "Pleural Effusion",
    "Pleural Other",
    "Fracture",
    "Support Devices",
]

CHEXPERT14_LABELS = CHEXPERT13_LABELS + ["No Finding"]


def load_label_mapping() -> Dict[str, Any]:
    """Load label mapping from S3 or use default mapping"""
    try:
        # Try to load from S3 (if available)
        mapping_bucket = os.environ.get('MAPPING_BUCKET', '')
        mapping_key = os.environ.get('MAPPING_KEY', 'model_repo/chexpert_classifier/label_mapping.json')
        
        if mapping_bucket:
            response = s3_client.get_object(Bucket=mapping_bucket, Key=mapping_key)
            mapping = json.loads(response['Body'].read().decode('utf-8'))
            return mapping
    except Exception as e:
        print(f"Warning: Could not load mapping from S3: {e}")
    
    # Default mapping (from label_mapping.json structure)
    return {
        "chexpert_to_txr_index": {
            "Enlarged Cardiomediastinum": 17,
            "Cardiomegaly": 10,
            "Lung Opacity": 16,
            "Lung Lesion": 14,
            "Edema": 4,
            "Consolidation": 1,
            "Pneumonia": 8,
            "Atelectasis": 0,
            "Pneumothorax": 3,
            "Pleural Effusion": 7,
            "Fracture": 15
        },
        "chexpert13_labels": CHEXPERT13_LABELS
    }


def map_txr_to_chexpert(txr_logits: np.ndarray, label_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map 18 TXR logits to 14 CheXpert labels (13 findings + "No Finding")
    
    Args:
        txr_logits: Array of shape (batch, 18) with TXR logits
        label_mapping: Mapping dictionary with chexpert_to_txr_index
        
    Returns:
        Dictionary with CheXpert14 probabilities and labels
    """
    batch_size = txr_logits.shape[0]
    
    # Apply sigmoid to get probabilities
    txr_probs = sigmoid(txr_logits)  # Shape: (batch, 18)
    
    # Get mapping
    chexpert_to_txr = label_mapping.get("chexpert_to_txr_index", {})
    chexpert13_labels = label_mapping.get("chexpert13_labels", CHEXPERT13_LABELS)
    
    # Initialize CheXpert13 probabilities
    chexpert13_probs = np.zeros((batch_size, len(chexpert13_labels)), dtype=np.float32)
    
    # Map TXR probabilities to CheXpert13
    for i, label in enumerate(chexpert13_labels):
        if label in chexpert_to_txr:
            txr_idx = chexpert_to_txr[label]
            chexpert13_probs[:, i] = txr_probs[:, txr_idx]
        # If label not found in mapping, keep as 0 (low probability)
    
    # Derive "No Finding" probability: 1 - max(other 13 probabilities)
    max_other_prob = np.max(chexpert13_probs, axis=1, keepdims=True)
    no_finding_prob = np.clip(1.0 - max_other_prob, 0.0, 1.0)
    
    # Concatenate: 13 findings + "No Finding" = 14 labels
    chexpert14_probs = np.concatenate([chexpert13_probs, no_finding_prob], axis=1)
    
    # Convert to dictionary format
    result = {
        "probabilities": chexpert14_probs[0].tolist(),  # For batch_size=1
        "labels": CHEXPERT14_LABELS,
        "probabilities_dict": {
            label: float(prob) for label, prob in zip(CHEXPERT14_LABELS, chexpert14_probs[0])
        }
    }
    
    return result


def invoke_triton_inference(preprocessed_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke Triton Inference Server with preprocessed image
    
    Args:
        preprocessed_image: Dictionary with 'preprocessed_image' (base64) and 'image_shape'
        
    Returns:
        Dictionary with inference results
    """
    # Decode base64 image
    image_base64 = preprocessed_image.get('preprocessed_image', '')
    image_shape = preprocessed_image.get('image_shape', [1, 1, 224, 224])
    
    if not image_base64:
        raise ValueError("Missing preprocessed_image in input")
    
    # Decode base64 to numpy array
    image_bytes = base64.b64decode(image_base64)
    image_array = np.frombuffer(image_bytes, dtype=np.float32)
    
    # Reshape to expected shape (batch, channels, height, width)
    if len(image_shape) == 4:
        image_array = image_array.reshape(image_shape)
    else:
        # Default shape if not provided
        image_array = image_array.reshape(1, 1, 224, 224)
    
    # Prepare Triton inference request
    inference_request = {
        "inputs": [
            {
                "name": "input",
                "shape": list(image_array.shape),
                "datatype": "FP32",
                "data": image_array.flatten().tolist()
            }
        ],
        "outputs": [{"name": "output"}]
    }
    
    # Call Triton endpoint
    inference_url = f"{TRITON_ENDPOINT}/v2/models/{MODEL_NAME}/infer"
    
    start_time = time.time()
    try:
        response = requests.post(
            inference_url,
            json=inference_request,
            timeout=30
        )
        inference_time = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code != 200:
            raise Exception(f"Triton inference failed: {response.status_code} - {response.text}")
        
        result = response.json()
        output_data = result["outputs"][0]["data"]
        
        # Convert to numpy array
        txr_logits = np.array(output_data, dtype=np.float32).reshape(1, -1)  # Shape: (1, 18)
        
        return {
            "success": True,
            "txr_logits": txr_logits.tolist(),
            "inference_time_ms": inference_time
        }
        
    except Exception as e:
        inference_time = (time.time() - start_time) * 1000
        return {
            "success": False,
            "error": str(e),
            "inference_time_ms": inference_time
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Triton inference with CheXpert mapping
    
    Expected event structure:
    {
        "study_id": "...",
        "preprocessing": {
            "preprocessed_image": "base64...",
            "image_shape": [1, 1, 224, 224],
            ...
        }
    }
    """
    try:
        start_time = time.time()
        
        # Extract study_id and preprocessing results
        study_id = event.get('study_id') or event.get('validation', {}).get('study_id', 'UNKNOWN')
        preprocessing = event.get('preprocessing', {})
        
        if not preprocessing:
            return {
                "success": False,
                "error": "Missing preprocessing results",
                "study_id": study_id
            }
        
        # Invoke Triton inference
        inference_result = invoke_triton_inference(preprocessing)
        
        if not inference_result.get("success"):
            return {
                "success": False,
                "error": inference_result.get("error", "Inference failed"),
                "study_id": study_id,
                "inference_time_ms": inference_result.get("inference_time_ms", 0)
            }
        
        # Load label mapping
        label_mapping = load_label_mapping()
        
        # Map TXR logits to CheXpert labels
        txr_logits = np.array(inference_result["txr_logits"], dtype=np.float32)
        chexpert_result = map_txr_to_chexpert(txr_logits, label_mapping)
        
        total_time = (time.time() - start_time) * 1000
        
        # Send telemetry
        try:
            telemetry_event = {
                "studyId": study_id,
                "stage": "inference",
                "latencyMs": total_time,
                "inferenceTimeMs": inference_result.get("inference_time_ms", 0),
                "timestamp": time.time() * 1000,
                "model": MODEL_NAME,
                "success": True
            }
            
            kinesis_client.put_record(
                StreamName=os.environ.get('KINESIS_STREAM', 'radstream-telemetry'),
                Data=json.dumps(telemetry_event),
                PartitionKey=study_id
            )
        except Exception as e:
            print(f"Warning: Failed to send telemetry: {e}")
        
        return {
            "success": True,
            "study_id": study_id,
            "inference": {
                "txr_logits": inference_result["txr_logits"],
                "chexpert14_probabilities": chexpert_result["probabilities"],
                "chexpert14_labels": chexpert_result["labels"],
                "chexpert14_dict": chexpert_result["probabilities_dict"]
            },
            "timing": {
                "total_time_ms": total_time,
                "inference_time_ms": inference_result.get("inference_time_ms", 0),
                "mapping_time_ms": total_time - inference_result.get("inference_time_ms", 0)
            }
        }
        
    except Exception as e:
        error_time = (time.time() - start_time) * 1000 if 'start_time' in locals() else 0
        
        # Send error telemetry
        try:
            telemetry_event = {
                "studyId": study_id if 'study_id' in locals() else 'UNKNOWN',
                "stage": "inference",
                "latencyMs": error_time,
                "timestamp": time.time() * 1000,
                "errorCode": "INFERENCE_ERROR",
                "errorMessage": str(e),
                "success": False
            }
            
            kinesis_client.put_record(
                StreamName=os.environ.get('KINESIS_STREAM', 'radstream-telemetry'),
                Data=json.dumps(telemetry_event),
                PartitionKey=study_id if 'study_id' in locals() else 'ERROR'
            )
        except:
            pass
        
        return {
            "success": False,
            "error": str(e),
            "study_id": study_id if 'study_id' in locals() else 'UNKNOWN',
            "timing": {
                "total_time_ms": error_time
            }
        }

