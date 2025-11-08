#!/usr/bin/env python3
"""
Add Pillow Lambda Layer to prepare_tensors function
Uses pre-built layer from Klayers (public Lambda layers)
"""

import boto3
import json
from botocore.exceptions import ClientError

# Pre-built Pillow layer ARNs for us-east-1 (from Klayers)
# These are public layers maintained by the community
# If these don't work, use create_pillow_layer_docker.py to build your own
PILLOW_LAYERS = {
    'python3.9': 'arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p39-Pillow:6',  # Updated version
    'python3.10': 'arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p310-Pillow:6',
    'python3.11': 'arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p311-Pillow:6',
    'python3.12': 'arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-Pillow:6'
}

# Alternative: Try to use AWS SAM CLI layer or build our own
# If public layers don't work, we'll create our own layer

def get_function_runtime(lambda_client, function_name):
    """Get the runtime of a Lambda function"""
    try:
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        return response['Runtime']
    except ClientError as e:
        print(f"Error getting function runtime: {e}")
        return None

def add_layer_to_function(lambda_client, function_name, layer_arn):
    """Add a layer to a Lambda function"""
    try:
        # Get current layers
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_layers = response.get('Layers', [])
        
        # Check if layer already attached
        layer_arns = [layer['Arn'] for layer in current_layers]
        if layer_arn in layer_arns:
            print(f"   ✅ Layer already attached to {function_name}")
            return True
        
        # Add new layer
        new_layers = layer_arns + [layer_arn]
        
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Layers=new_layers
        )
        
        print(f"   ✅ Added Pillow layer to {function_name}")
        return True
        
    except ClientError as e:
        print(f"   ❌ Error adding layer to {function_name}: {e}")
        return False

def main():
    """Add Pillow layer to prepare_tensors function"""
    print("Adding Pillow Lambda Layer")
    print("=" * 50)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Function that needs Pillow
    function_name = 'radstream-prepare-tensors'
    
    print(f"\nGetting runtime for {function_name}...")
    runtime = get_function_runtime(lambda_client, function_name)
    
    if not runtime:
        print("❌ Could not get function runtime")
        return 1
    
    print(f"   Runtime: {runtime}")
    
    # Get appropriate layer ARN
    layer_arn = PILLOW_LAYERS.get(runtime)
    
    if not layer_arn:
        print(f"❌ No Pillow layer available for runtime {runtime}")
        print(f"   Available runtimes: {list(PILLOW_LAYERS.keys())}")
        return 1
    
    print(f"\nUsing layer ARN: {layer_arn}")
    print(f"Adding layer to {function_name}...")
    
    success = add_layer_to_function(lambda_client, function_name, layer_arn)
    
    if success:
        print("\n✅ Pillow layer added successfully!")
        print("\nNext steps:")
        print("1. Test the prepare_tensors function:")
        print("   python rahul/preprocessing/test_lambda_with_s3.py")
        print("2. Verify it can process images from S3")
    else:
        print("\n❌ Failed to add layer")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

