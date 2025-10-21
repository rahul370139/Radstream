#!/usr/bin/env python3
"""
Image Upload Script for RadStream Medical Imaging Pipeline
Uploads test images to S3 and generates metadata for testing the pipeline
"""

import boto3
import json
import os
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from PIL import Image
import uuid

class ImageUploader:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize image uploader"""
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get AWS account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
            self.images_bucket = f'radstream-images-{self.account_id}'
            print(f"Using AWS Account ID: {self.account_id}")
            print(f"Images bucket: {self.images_bucket}")
        except Exception as e:
            print(f"Error getting AWS account ID: {e}")
            raise
    
    def create_test_image(self, width: int = 512, height: int = 512, 
                         image_type: str = 'chest_xray') -> bytes:
        """
        Create a test image for upload
        
        Args:
            width: Image width
            height: Image height
            image_type: Type of test image to create
            
        Returns:
            bytes: Image data
        """
        # Create a test image
        if image_type == 'chest_xray':
            # Create a grayscale chest X-ray-like image
            image = Image.new('L', (width, height), color=128)
            # Add some "anatomical" features
            for i in range(height):
                for j in range(width):
                    # Add some variation to simulate X-ray
                    value = 128 + int(50 * (i / height - 0.5)) + int(30 * (j / width - 0.5))
                    value = max(0, min(255, value))
                    image.putpixel((j, i), value)
        else:
            # Create a simple test pattern
            image = Image.new('RGB', (width, height), color=(128, 128, 128))
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG', quality=85)
        return img_buffer.getvalue()
    
    def generate_metadata(self, study_id: str, image_type: str = 'chest_xray') -> Dict[str, Any]:
        """
        Generate metadata for a study
        
        Args:
            study_id: Study identifier
            image_type: Type of image
            
        Returns:
            Dict with metadata
        """
        metadata = {
            'study_id': study_id,
            'view': 'PA',
            'timestamp': datetime.utcnow().isoformat(),
            'patient_id': f'PAT-{uuid.uuid4().hex[:8].upper()}',
            'study_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'modality': 'X-RAY',
            'body_part': 'CHEST',
            'image_size': {
                'width': 512,
                'height': 512
            },
            'annotations': [],
            'pipeline_version': '1.0.0',
            'test_data': True
        }
        
        return metadata
    
    def upload_single_image(self, study_id: str, image_data: bytes, 
                           metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload a single image and its metadata to S3
        
        Args:
            study_id: Study identifier
            image_data: Image data
            metadata: Image metadata
            
        Returns:
            Dict with upload results
        """
        start_time = time.time()
        
        try:
            # Upload image
            image_key = f'images/{study_id}/{study_id}.jpg'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=image_key,
                Body=image_data,
                ContentType='image/jpeg',
                ServerSideEncryption='AES256'
            )
            
            # Upload metadata
            metadata_key = f'images/{study_id}/{study_id}.json'
            self.s3_client.put_object(
                Bucket=self.images_bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            upload_time = time.time() - start_time
            
            return {
                'success': True,
                'study_id': study_id,
                'image_key': image_key,
                'metadata_key': metadata_key,
                'upload_time': upload_time,
                'image_size': len(image_data)
            }
            
        except ClientError as e:
            return {
                'success': False,
                'study_id': study_id,
                'error': str(e),
                'upload_time': time.time() - start_time
            }
    
    def upload_batch_images(self, num_images: int, batch_size: int = 10, 
                           image_type: str = 'chest_xray') -> List[Dict[str, Any]]:
        """
        Upload a batch of test images
        
        Args:
            num_images: Total number of images to upload
            batch_size: Number of images to upload in parallel
            image_type: Type of test images
            
        Returns:
            List of upload results
        """
        results = []
        
        print(f"Uploading {num_images} test images...")
        print(f"Batch size: {batch_size}")
        print("=" * 50)
        
        for i in range(0, num_images, batch_size):
            batch_end = min(i + batch_size, num_images)
            batch_num = i // batch_size + 1
            
            print(f"Processing batch {batch_num} (images {i+1}-{batch_end})...")
            
            batch_results = []
            for j in range(i, batch_end):
                study_id = f'TEST-{j+1:06d}'
                
                # Create test image
                image_data = self.create_test_image(image_type=image_type)
                
                # Generate metadata
                metadata = self.generate_metadata(study_id, image_type)
                
                # Upload image and metadata
                result = self.upload_single_image(study_id, image_data, metadata)
                batch_results.append(result)
                
                if result['success']:
                    print(f"  ✅ {study_id}: {result['upload_time']:.2f}s")
                else:
                    print(f"  ❌ {study_id}: {result['error']}")
            
            results.extend(batch_results)
            
            # Brief pause between batches
            if batch_end < num_images:
                time.sleep(1)
        
        return results
    
    def generate_load_test_images(self, num_images: int, 
                                 concurrent_uploads: int = 5) -> List[Dict[str, Any]]:
        """
        Generate load test by uploading images concurrently
        
        Args:
            num_images: Number of images to upload
            concurrent_uploads: Number of concurrent uploads
            
        Returns:
            List of upload results
        """
        import concurrent.futures
        import threading
        
        results = []
        results_lock = threading.Lock()
        
        def upload_worker(study_id: str):
            """Worker function for concurrent uploads"""
            image_data = self.create_test_image()
            metadata = self.generate_metadata(study_id)
            result = self.upload_single_image(study_id, image_data, metadata)
            
            with results_lock:
                results.append(result)
            
            return result
        
        print(f"Starting load test with {num_images} images, {concurrent_uploads} concurrent uploads...")
        print("=" * 60)
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_uploads) as executor:
            # Submit all upload tasks
            futures = []
            for i in range(num_images):
                study_id = f'LOAD-{i+1:06d}'
                future = executor.submit(upload_worker, study_id)
                futures.append(future)
            
            # Wait for all uploads to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result['success']:
                        print(f"  ✅ {result['study_id']}: {result['upload_time']:.2f}s")
                    else:
                        print(f"  ❌ {result['study_id']}: {result['error']}")
                except Exception as e:
                    print(f"  ❌ Upload failed: {e}")
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful_uploads = sum(1 for r in results if r['success'])
        failed_uploads = len(results) - successful_uploads
        avg_upload_time = sum(r['upload_time'] for r in results if r['success']) / max(successful_uploads, 1)
        
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)
        print(f"Total images: {num_images}")
        print(f"Successful uploads: {successful_uploads}")
        print(f"Failed uploads: {failed_uploads}")
        print(f"Success rate: {successful_uploads/num_images*100:.1f}%")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average upload time: {avg_upload_time:.2f}s")
        print(f"Throughput: {num_images/total_time:.2f} images/second")
        
        return results
    
    def cleanup_test_images(self, prefix: str = 'TEST-') -> int:
        """
        Clean up test images from S3
        
        Args:
            prefix: Prefix of images to delete
            
        Returns:
            Number of objects deleted
        """
        try:
            # List objects with prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.images_bucket,
                Prefix=f'images/{prefix}'
            )
            
            objects_to_delete = []
            for obj in response.get('Contents', []):
                objects_to_delete.append({'Key': obj['Key']})
            
            if not objects_to_delete:
                print(f"No objects found with prefix: {prefix}")
                return 0
            
            # Delete objects in batches
            deleted_count = 0
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                
                response = self.s3_client.delete_objects(
                    Bucket=self.images_bucket,
                    Delete={
                        'Objects': batch
                    }
                )
                
                deleted_count += len(response.get('Deleted', []))
                print(f"Deleted {len(response.get('Deleted', []))} objects...")
            
            print(f"Total deleted: {deleted_count} objects")
            return deleted_count
            
        except ClientError as e:
            print(f"Error cleaning up images: {e}")
            return 0

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Upload test images to RadStream S3 bucket')
    parser.add_argument('--num-images', type=int, default=10, help='Number of images to upload')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for uploads')
    parser.add_argument('--load-test', action='store_true', help='Run load test with concurrent uploads')
    parser.add_argument('--concurrent', type=int, default=5, help='Number of concurrent uploads for load test')
    parser.add_argument('--cleanup', action='store_true', help='Clean up test images')
    parser.add_argument('--image-type', choices=['chest_xray', 'test_pattern'], default='chest_xray', help='Type of test image')
    
    args = parser.parse_args()
    
    # Initialize uploader
    uploader = ImageUploader()
    
    if args.cleanup:
        print("Cleaning up test images...")
        deleted_count = uploader.cleanup_test_images()
        print(f"Deleted {deleted_count} test images")
        return
    
    if args.load_test:
        # Run load test
        results = uploader.generate_load_test_images(args.num_images, args.concurrent)
    else:
        # Run normal batch upload
        results = uploader.upload_batch_images(args.num_images, args.batch_size, args.image_type)
    
    # Print summary
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print("\n" + "=" * 50)
    print("UPLOAD SUMMARY")
    print("=" * 50)
    print(f"Total images: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {successful/len(results)*100:.1f}%")
    
    if successful > 0:
        avg_time = sum(r['upload_time'] for r in results if r['success']) / successful
        print(f"Average upload time: {avg_time:.2f}s")
    
    print("\n🎉 Upload test completed!")

if __name__ == "__main__":
    import io
    main()
