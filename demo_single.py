#!/usr/bin/env python3
"""
RadStream Live Demo - Single Image Upload
Run: python3 demo_single.py
"""

import boto3
import json
import time
from datetime import datetime, timezone
import uuid

s3 = boto3.client('s3', region_name='us-east-1')
stepfunctions = boto3.client('stepfunctions', region_name='us-east-1')

BUCKET = 'radstream-images-222634400500'
STATE_MACHINE_ARN = 'arn:aws:states:us-east-1:222634400500:stateMachine:radstream-pipeline'

study_id = f"DEMO-{uuid.uuid4().hex[:8]}"
print(f"\n🏥 RadStream Live Demo")
print(f"=" * 50)
print(f"Study ID: {study_id}")
print()

img_path = 'test_images/004d3e38-84225af7-d59a16ee-0274a458-f36c87de.jpg'
s3_key = f"images/{study_id}.jpg"

print(f"📤 Uploading chest X-ray...")
s3.upload_file(img_path, BUCKET, s3_key)
s3.put_object(Bucket=BUCKET, Key=f"images/{study_id}.json", 
              Body=json.dumps({"study_id": study_id, "view": "PA", "timestamp": datetime.now(timezone.utc).isoformat()}))
print(f"   ✅ Uploaded to S3")
print()

print("🚀 Starting pipeline...")
response = stepfunctions.start_execution(
    stateMachineArn=STATE_MACHINE_ARN,
    name=study_id,
    input=json.dumps({"bucket": BUCKET, "key": s3_key, "study_id": study_id})
)
print()

print("⏳ Processing...")
start_time = time.time()
while True:
    status = stepfunctions.describe_execution(executionArn=response['executionArn'])
    if status['status'] != 'RUNNING':
        break
    time.sleep(0.5)

elapsed = time.time() - start_time
print(f"   Done in {elapsed:.1f}s")
print()

if status['status'] == 'SUCCEEDED' and 'output' in status:
    output = json.loads(status['output'])
    print("🎉 SUCCESS!")
    print("=" * 50)
    print("\n📊 Stage Results:")
    for stage in ['validation', 'preprocessing', 'inference', 'storage', 'telemetry']:
        if stage in output:
            success = output[stage].get('success', output[stage].get('valid', False))
            print(f"   {'✅' if success else '❌'} {stage.capitalize()}")
    
    if output.get('inference', {}).get('success'):
        preds = output['inference'].get('inference', {}).get('chexpert14_dict', {})
        if preds:
            print("\n🔬 ML Predictions (Top 5):")
            for label, prob in sorted(preds.items(), key=lambda x: -x[1])[:5]:
                print(f"   {label}: {prob:.1%}")
else:
    print(f"❌ Failed: {status['status']}")

