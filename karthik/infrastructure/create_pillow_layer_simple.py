#!/usr/bin/env python3
"""
Create Pillow Lambda Layer - Simple Method
Uses pip to install Pillow in a Lambda-compatible way
"""

import boto3
import subprocess
import os
import zipfile
import tempfile
import shutil
from botocore.exceptions import ClientError

def create_pillow_layer():
    """Create Pillow layer using pip install for Lambda"""
    print("Creating Pillow Lambda Layer (Simple Method)")
    print("=" * 50)
    
    # Create temporary directory
    layer_dir = tempfile.mkdtemp()
    python_dir = os.path.join(layer_dir, "python")
    os.makedirs(python_dir, exist_ok=True)
    
    try:
        print("Installing Pillow for Lambda (this may take a few minutes)...")
        
        # Install Pillow using pip with --platform for Lambda's environment
        # Lambda uses Amazon Linux 2, which is similar to manylinux2014
        result = subprocess.run([
            'pip', 'install',
            '--platform', 'manylinux2014_x86_64',
            '--target', python_dir,
            '--implementation', 'cp',
            '--python-version', '3.9',
            '--only-binary=:all:',
            '--upgrade',
            'Pillow==10.0.0'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("⚠️  Platform-specific install failed, trying generic install...")
            # Fallback: install normally (may not work in Lambda, but worth trying)
            subprocess.run([
                'pip', 'install',
                '--target', python_dir,
                'Pillow==10.0.0'
            ], check=True)
        
        # Verify PIL is installed
        if not os.path.exists(os.path.join(python_dir, 'PIL')):
            print("❌ PIL not found after installation")
            return None
        
        print("✅ Pillow installed successfully")
        
        # Create zip file
        zip_path = os.path.join(layer_dir, "pillow-layer.zip")
        print("Creating zip file...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(python_dir):
                # Skip __pycache__ directories
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for file in files:
                    if not file.endswith('.pyc'):
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, layer_dir)
                        zip_file.write(file_path, arc_name)
        
        file_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
        print(f"✅ Layer zip created: {zip_path} ({file_size:.2f} MB)")
        
        return zip_path
        
    except Exception as e:
        print(f"❌ Error creating layer: {e}")
        import traceback
        traceback.print_exc()
        return None

def publish_layer(zip_path):
    """Publish layer to AWS Lambda"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("\nPublishing layer to AWS Lambda...")
    
    try:
        with open(zip_path, 'rb') as f:
            zip_data = f.read()
        
        response = lambda_client.publish_layer_version(
            LayerName='radstream-pillow-layer',
            Description='Pillow library for RadStream Lambda functions (Python 3.9)',
            Content={'ZipFile': zip_data},
            CompatibleRuntimes=['python3.9']
        )
        
        layer_arn = response['LayerVersionArn']
        print(f"✅ Layer published: {layer_arn}")
        return layer_arn
        
    except ClientError as e:
        print(f"❌ Error publishing layer: {e}")
        return None

def add_layer_to_function(layer_arn):
    """Add layer to prepare_tensors function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'radstream-prepare-tensors'
    
    try:
        # Get current layers
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_layers = response.get('Layers', [])
        layer_arns = [layer['Arn'] for layer in current_layers]
        
        if layer_arn in layer_arns:
            print(f"✅ Layer already attached to {function_name}")
            return True
        
        # Add new layer
        new_layers = layer_arns + [layer_arn]
        
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Layers=new_layers
        )
        
        print(f"✅ Added Pillow layer to {function_name}")
        return True
        
    except ClientError as e:
        print(f"❌ Error adding layer: {e}")
        return False

def main():
    """Main function"""
    print("Creating Pillow Lambda Layer")
    print("=" * 50)
    
    # Create layer
    zip_path = create_pillow_layer()
    if not zip_path:
        print("\n❌ Failed to create layer")
        print("\nAlternative: Use Docker method:")
        print("  python create_pillow_layer_docker.py")
        return 1
    
    # Publish layer
    layer_arn = publish_layer(zip_path)
    if not layer_arn:
        return 1
    
    # Add to function
    success = add_layer_to_function(layer_arn)
    
    if success:
        print("\n✅ Pillow layer setup complete!")
        print("\nNext steps:")
        print("1. Test prepare_tensors function:")
        print("   python rahul/preprocessing/test_lambda_with_s3.py")
        print("2. Verify it can process images from S3")
    else:
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

