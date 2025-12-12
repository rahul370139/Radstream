#!/usr/bin/env python3
"""
RadStream Live Demo - Multi-User (5 Concurrent Uploads)
Run: python3 demo_multi.py
"""

import boto3
import json
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

s3 = boto3.client('s3', region_name='us-east-1')
stepfunctions = boto3.client('stepfunctions', region_name='us-east-1')

BUCKET = 'radstream-images-222634400500'
STATE_MACHINE_ARN = 'arn:aws:states:us-east-1:222634400500:stateMachine:radstream-pipeline'

# Use 5 different real CheXpert images
test_images = [
    'test_images/004d3e38-84225af7-d59a16ee-0274a458-f36c87de.jpg',
    'test_images/01992162-dbb2e95c-ce5ceb79-3d688f50-be27931d.jpg',
    'test_images/0a724aa6-684b4d9d-8913093e-be130c21-8d0f9402.jpg',
    'test_images/0a7bfe10-7a668c98-394c0cba-29ca79f9-70900154.jpg',
    'test_images/0ad6ca58-39588006-a407ebfc-4147070f-89caf5e4.jpg',
]

print("\n👥 MULTI-USER SCENARIO: 5 Doctors Uploading Simultaneously")
print("=" * 60)
print()

def doctor_upload(doctor_id, img_path):
    study_id = f"DOC{doctor_id}-{uuid.uuid4().hex[:6]}"
    s3_key = f"images/{study_id}.jpg"
    
    s3.upload_file(img_path, BUCKET, s3_key)
    s3.put_object(Bucket=BUCKET, Key=f"images/{study_id}.json", 
                  Body=json.dumps({"study_id": study_id, "view": "PA", "timestamp": datetime.now(timezone.utc).isoformat()}))
    
    start = time.time()
    response = stepfunctions.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=study_id,
        input=json.dumps({"bucket": BUCKET, "key": s3_key, "study_id": study_id})
    )
    
    while True:
        status = stepfunctions.describe_execution(executionArn=response['executionArn'])
        if status['status'] != 'RUNNING':
            break
        time.sleep(0.3)
    
    return doctor_id, status['status'], (time.time() - start)

print("📤 Starting 5 concurrent uploads...")
print()
batch_start = time.time()

successes = 0
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(doctor_upload, i+1, img) for i, img in enumerate(test_images)]
    for future in as_completed(futures):
        doc_id, status, latency = future.result()
        icon = "✅" if status == "SUCCEEDED" else "❌"
        if status == "SUCCEEDED":
            successes += 1
        print(f"   {icon} Doctor {doc_id}: {status} ({latency:.1f}s)")

batch_time = time.time() - batch_start
print()
print("=" * 60)
print(f"📊 Results:")
print(f"   Success Rate: {successes}/5 ({successes*20}%)")
print(f"   Total Batch Time: {batch_time:.1f}s")
print(f"   Throughput: {60*5/batch_time:.0f} images/min")
print()
print("💡 KEY: Cloud processes all 5 in PARALLEL!")

