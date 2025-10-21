#!/usr/bin/env python3
"""
Test Setup Script for RadStream Medical Imaging Pipeline
Tests the project setup without running git operations
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and print status"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - MISSING")
        return False

def check_directory_structure():
    """Check if the directory structure is correct"""
    print("🔍 Checking RadStream Project Structure...")
    print("=" * 50)
    
    base_path = Path(__file__).parent
    required_files = [
        # Main files
        (base_path / "README.md", "Main README"),
        (base_path / "requirements.txt", "Main requirements.txt"),
        (base_path / "CONTRIBUTING.md", "Contributing guidelines"),
        (base_path / ".gitignore", "Git ignore file"),
        
        # Shared infrastructure
        (base_path / "shared" / "infrastructure" / "s3_setup.py", "S3 setup script"),
        (base_path / "shared" / "infrastructure" / "eventbridge_setup.py", "EventBridge setup script"),
        (base_path / "shared" / "infrastructure" / "stepfunctions_setup.py", "Step Functions setup script"),
        (base_path / "shared" / "infrastructure" / "lambda_setup.py", "Lambda setup script"),
        (base_path / "shared" / "infrastructure" / "kinesis_setup.py", "Kinesis setup script"),
        (base_path / "shared" / "requirements.txt", "Shared requirements.txt"),
        
        # Shared documentation
        (base_path / "shared" / "docs" / "architecture.md", "Architecture documentation"),
        (base_path / "shared" / "docs" / "member_tasks.md", "Member tasks documentation"),
        (base_path / "shared" / "docs" / "evaluation_plan.md", "Evaluation plan documentation"),
        
        # Rahul's files
        (base_path / "rahul" / "README.md", "Rahul's README"),
        (base_path / "rahul" / "preprocessing" / "validate_metadata.py", "Validate metadata Lambda"),
        (base_path / "rahul" / "preprocessing" / "prepare_tensors.py", "Prepare tensors Lambda"),
        (base_path / "rahul" / "preprocessing" / "store_results.py", "Store results Lambda"),
        (base_path / "rahul" / "preprocessing" / "send_telemetry.py", "Send telemetry Lambda"),
        (base_path / "rahul" / "preprocessing" / "requirements.txt", "Preprocessing requirements"),
        (base_path / "rahul" / "telemetry" / "kinesis_producer.py", "Kinesis producer"),
        (base_path / "rahul" / "telemetry" / "glue_schema.py", "Glue schema setup"),
        (base_path / "rahul" / "telemetry" / "athena_queries.sql", "Athena queries"),
        (base_path / "rahul" / "scripts" / "upload_images.py", "Upload images script"),
        (base_path / "rahul" / "scripts" / "benchmark.py", "Benchmark script"),
        (base_path / "rahul" / "scripts" / "test_pipeline.py", "Test pipeline script"),
        
        # Mukul's files
        (base_path / "mukul" / "README.md", "Mukul's README"),
        (base_path / "mukul" / "inference" / "Dockerfile.triton", "Triton Dockerfile"),
        (base_path / "mukul" / "inference" / "model_config.pbtxt", "Model configuration"),
        (base_path / "mukul" / "inference" / "health_check.py", "Health check script"),
        (base_path / "mukul" / "inference" / "start_triton.sh", "Start Triton script"),
        (base_path / "mukul" / "inference" / "deploy_manifest.yaml", "Kubernetes deployment"),
        
        # Karthik's files
        (base_path / "karthik" / "README.md", "Karthik's README"),
        (base_path / "karthik" / "security" / "iam_roles.json", "IAM roles and policies"),
        
        # GitHub files
        (base_path / ".github" / "workflows" / "ci.yml", "CI/CD workflow"),
        (base_path / ".github" / "ISSUE_TEMPLATE" / "bug_report.md", "Bug report template"),
        (base_path / ".github" / "ISSUE_TEMPLATE" / "feature_request.md", "Feature request template"),
    ]
    
    found_files = 0
    total_files = len(required_files)
    
    for file_path, description in required_files:
        if check_file_exists(file_path, description):
            found_files += 1
    
    print("\n" + "=" * 50)
    print(f"📊 SUMMARY: {found_files}/{total_files} files found")
    
    if found_files == total_files:
        print("🎉 All required files are present!")
        return True
    else:
        print(f"⚠️  {total_files - found_files} files are missing")
        return False

def check_python_imports():
    """Check if Python files can be imported without errors"""
    print("\n🐍 Checking Python Import Dependencies...")
    print("=" * 50)
    
    try:
        import boto3
        print("✅ boto3 - AWS SDK")
    except ImportError:
        print("❌ boto3 - AWS SDK (install with: pip install boto3)")
    
    try:
        import json
        print("✅ json - Built-in module")
    except ImportError:
        print("❌ json - Built-in module")
    
    try:
        from PIL import Image
        print("✅ Pillow - Image processing")
    except ImportError:
        print("❌ Pillow - Image processing (install with: pip install Pillow)")
    
    try:
        import numpy
        print("✅ numpy - Numerical computing")
    except ImportError:
        print("❌ numpy - Numerical computing (install with: pip install numpy)")

def check_aws_cli():
    """Check if AWS CLI is configured"""
    print("\n☁️  Checking AWS CLI Configuration...")
    print("=" * 50)
    
    try:
        import subprocess
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            identity = json.loads(result.stdout)
            print(f"✅ AWS CLI configured for account: {identity.get('Account', 'Unknown')}")
            print(f"✅ User/Role: {identity.get('Arn', 'Unknown')}")
            return True
        else:
            print(f"❌ AWS CLI error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ AWS CLI not found (install with: pip install awscli)")
        return False
    except Exception as e:
        print(f"❌ AWS CLI error: {e}")
        return False

def check_docker():
    """Check if Docker is available"""
    print("\n🐳 Checking Docker...")
    print("=" * 50)
    
    try:
        import subprocess
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print(f"✅ Docker: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Docker error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Docker not found (install Docker Desktop)")
        return False
    except Exception as e:
        print(f"❌ Docker error: {e}")
        return False

def check_kubectl():
    """Check if kubectl is available"""
    print("\n☸️  Checking kubectl...")
    print("=" * 50)
    
    try:
        import subprocess
        result = subprocess.run(['kubectl', 'version', '--client'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print(f"✅ kubectl: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ kubectl error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ kubectl not found (install with: brew install kubectl)")
        return False
    except Exception as e:
        print(f"❌ kubectl error: {e}")
        return False

def main():
    """Main function"""
    print("🚀 RadStream Project Setup Test")
    print("=" * 50)
    print("This script checks if the project is properly set up")
    print("without running any git operations.\n")
    
    # Check directory structure
    structure_ok = check_directory_structure()
    
    # Check Python imports
    check_python_imports()
    
    # Check AWS CLI
    aws_ok = check_aws_cli()
    
    # Check Docker
    docker_ok = check_docker()
    
    # Check kubectl
    kubectl_ok = check_kubectl()
    
    # Final summary
    print("\n" + "=" * 50)
    print("🎯 FINAL SUMMARY")
    print("=" * 50)
    
    if structure_ok and aws_ok and docker_ok and kubectl_ok:
        print("🎉 All checks passed! Project is ready for development.")
        print("\nNext steps:")
        print("1. Run: python shared/infrastructure/s3_setup.py")
        print("2. Run: python rahul/scripts/upload_images.py --num-images 5")
        print("3. Check the README files for team-specific instructions")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Install missing Python packages: pip install -r requirements.txt")
        print("- Configure AWS CLI: aws configure")
        print("- Install Docker Desktop")
        print("- Install kubectl: brew install kubectl")

if __name__ == "__main__":
    main()
