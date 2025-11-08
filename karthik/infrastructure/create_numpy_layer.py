#!/usr/bin/env python3
"""
Create NumPy Lambda Layer - Simple Method
Similar to Pillow layer creation
"""

import boto3
import subprocess
import os
import zipfile
import tempfile
import shutil
from botocore.exceptions import ClientError

def create_numpy_layer():
    """Create NumPy layer using pip install for Lambda"""
    print("Creating NumPy Lambda Layer")
    print("=" * 50)
    
    # Create temporary directory
    layer_dir = tempfile.mkdtemp()
    python_dir = os.path.join(layer_dir, "python")
    os.makedirs(python_dir, exist_ok=True)
    
    try:
        print("Installing NumPy for Lambda (this may take a few minutes)...")
        
        # Install NumPy using pip with --platform for Lambda's environment
        result = subprocess.run([
            'pip', 'install',
            '--platform', 'manylinux2014_x86_64',
            '--target', python_dir,
            '--implementation', 'cp',
            '--python-version', '3.9',
            '--only-binary=:all:',
            '--upgrade',
            'numpy==1.24.3'  # Use specific version that's known to work
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("⚠️  Platform-specific install failed, trying generic install...")
            # Fallback: install normally
            subprocess.run([
                'pip', 'install',
                '--target', python_dir,
                '--only-binary=:all:',
                'numpy==1.24.3'
            ], check=True)
        
        # Verify numpy is installed
        if not os.path.exists(os.path.join(python_dir, 'numpy')):
            print("❌ NumPy not found after installation")
            return None
        
        # Remove any setup.py files that might cause issues
        for root, dirs, files in os.walk(python_dir):
            if 'setup.py' in files:
                os.remove(os.path.join(root, 'setup.py'))
            # Remove test directories
            if 'tests' in dirs and 'numpy' in root:
                shutil.rmtree(os.path.join(root, 'tests'), ignore_errors=True)
        
        print("✅ NumPy installed successfully")
        
        # Create zip file
        zip_path = os.path.join(layer_dir, "numpy-layer.zip")
        print("Creating zip file...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(python_dir):
                # Skip __pycache__ directories
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for file in files:
                    if not file.endswith('.pyc') and file != 'setup.py':
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, layer_dir)
                        zip_file.write(file_path, arc_name)
        
        file_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
        print(f"✅ Layer zip created: {zip_path} ({file_size:.2f} MB)")
        
        # Keep the zip file - don't delete it in finally block
        # Move it to a persistent location
        persistent_zip = os.path.join(os.path.dirname(__file__), "numpy-layer.zip")
        shutil.move(zip_path, persistent_zip)
        print(f"✅ Moved layer zip to: {persistent_zip}")
        
        return persistent_zip
        
    except Exception as e:
        print(f"❌ Error creating layer: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Only clean up layer_dir if zip wasn't moved
        if os.path.exists(layer_dir) and not os.path.exists(os.path.join(os.path.dirname(__file__), "numpy-layer.zip")):
            shutil.rmtree(layer_dir, ignore_errors=True)

def publish_layer(zip_path):
    """Publish layer to AWS Lambda"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("\nPublishing layer to AWS Lambda...")
    
    try:
        with open(zip_path, 'rb') as f:
            zip_data = f.read()
        
        response = lambda_client.publish_layer_version(
            LayerName='radstream-numpy-layer',
            Description='NumPy library for RadStream Lambda functions (Python 3.9)',
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
        
        # Add both Pillow and NumPy layers
        if layer_arn not in layer_arns:
            layer_arns.append(layer_arn)
        
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Layers=layer_arns
        )
        
        print(f"✅ Added NumPy layer to {function_name}")
        return True
        
    except ClientError as e:
        print(f"❌ Error adding layer: {e}")
        return False

def main():
    """Main function"""
    print("Creating NumPy Lambda Layer")
    print("=" * 50)
    
    # Create layer
    zip_path = create_numpy_layer()
    if not zip_path:
        print("\n❌ Failed to create layer")
        return 1
    
    # Publish layer
    layer_arn = publish_layer(zip_path)
    if not layer_arn:
        return 1
    
    # Add to function
    success = add_layer_to_function(layer_arn)
    
    if success:
        print("\n✅ NumPy layer setup complete!")
        print("\nNext steps:")
        print("1. Update requirements_no_pillow.txt to remove numpy")
        print("2. Redeploy prepare_tensors function")
        print("3. Test: python rahul/preprocessing/test_lambda_with_s3.py")
    else:
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

