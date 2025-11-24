#!/usr/bin/env python3
"""
Health check script for RadStream Triton Inference Server
Checks if the server is healthy and ready to serve requests
"""

import requests
import json
import sys
import time
from typing import Dict, Any

def check_triton_health() -> bool:
    """
    Check if Triton server is healthy
    
    Returns:
        bool: True if healthy, False otherwise
    """
    try:
        # Check server health endpoint
        health_url = "http://localhost:8000/v2/health/ready"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ Triton server is healthy")
            return True
        else:
            print(f"❌ Triton server health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Triton server health check failed: {e}")
        return False

def check_model_loading() -> bool:
    """
    Check if models are loaded and ready
    
    Returns:
        bool: True if models are ready, False otherwise
    """
    try:
        # Check models endpoint
        models_url = "http://localhost:8000/v2/models"
        response = requests.get(models_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to get models: {response.status_code}")
            return False
        
        models_data = response.json()
        models = models_data.get('models', [])
        
        if not models:
            print("❌ No models loaded")
            return False
        
        # Check if expected model is loaded
        expected_model = 'chexpert_classifier'
        loaded_models = [model['name'] for model in models]
        
        if expected_model not in loaded_models:
            print(f"❌ Missing model: {expected_model}")
            print(f"   Loaded models: {loaded_models}")
            return False
        
        # Check if models are ready
        for model in models:
            if model.get('state') != 'READY':
                print(f"❌ Model {model['name']} is not ready (state: {model.get('state')})")
                return False
        
        print(f"✅ All models loaded and ready: {loaded_models}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to check models: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse models response: {e}")
        return False

def check_model_inference(model_name: str) -> bool:
    """
    Check if a specific model can perform inference
    
    Args:
        model_name: Name of the model to test
        
    Returns:
        bool: True if inference works, False otherwise
    """
    try:
        # Create test input data
        test_input = {
            "inputs": [
                {
                    "name": "input",
                    "shape": [1, 1, 224, 224],
                    "datatype": "FP32",
                    "data": [[0.0] * (1 * 224 * 224)]  # Dummy grayscale data
                }
            ]
        }
        
        # Send inference request
        inference_url = f"http://localhost:8000/v2/models/{model_name}/infer"
        response = requests.post(
            inference_url,
            data=json.dumps(test_input),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Model {model_name} inference test passed")
            return True
        else:
            print(f"❌ Model {model_name} inference test failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Model {model_name} inference test failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Model {model_name} inference test failed: {e}")
        return False

def get_server_metrics() -> Dict[str, Any]:
    """
    Get server metrics
    
    Returns:
        Dict with server metrics
    """
    try:
        metrics_url = "http://localhost:8000/v2/metrics"
        response = requests.get(metrics_url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get metrics: {response.status_code}")
            return {}
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get metrics: {e}")
        return {}

def main():
    """Main health check function"""
    print("RadStream Triton Server Health Check")
    print("=" * 40)
    
    # Wait a bit for server to start
    print("Waiting for server to start...")
    time.sleep(10)
    
    # Check server health
    health_ok = check_triton_health()
    if not health_ok:
        print("❌ Server health check failed")
        sys.exit(1)
    
    # Check model loading
    models_ok = check_model_loading()
    if not models_ok:
        print("❌ Model loading check failed")
        sys.exit(1)
    
    # Test inference for the model
    model_to_test = 'chexpert_classifier'
    inference_ok = check_model_inference(model_to_test)
    
    if not inference_ok:
        print("❌ Model inference tests failed")
        sys.exit(1)
    
    # Get and display metrics
    metrics = get_server_metrics()
    if metrics:
        print("\n📊 Server Metrics:")
        print(f"  GPU Utilization: {metrics.get('gpu_utilization', 'N/A')}%")
        print(f"  Memory Usage: {metrics.get('gpu_memory_used', 'N/A')} MB")
        print(f"  Request Count: {metrics.get('request_count', 'N/A')}")
    
    print("\n🎉 All health checks passed! Server is ready.")
    sys.exit(0)

if __name__ == "__main__":
    main()
