#!/usr/bin/env python3
"""
Create test metadata JSON files for test images
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def create_metadata_for_image(image_path: Path) -> dict:
    """Create metadata for a single image"""
    image_name = image_path.stem  # Get filename without extension
    
    # Extract study ID from filename (use first part of UUID)
    study_id = image_name.split('-')[0] if '-' in image_name else image_name
    
    metadata = {
        "study_id": f"STUDY-{study_id}",
        "view": "PA",  # Posteroanterior view
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "patient_id": f"PAT-{study_id[:8]}",
        "institution": "Test Hospital",
        "modality": "X-RAY",
        "body_part": "CHEST",
        "study_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "image_size": {
            "width": None,  # Will be filled after image processing
            "height": None
        }
    }
    
    return metadata

def main():
    """Create metadata files for all test images"""
    # Get test images directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    test_images_dir = project_root / "test_images"
    metadata_dir = project_root / "test_images" / "metadata"
    
    if not test_images_dir.exists():
        print(f"❌ Test images directory not found: {test_images_dir}")
        return 1
    
    # Create metadata directory
    metadata_dir.mkdir(exist_ok=True)
    
    # Find all images
    images = list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png"))
    
    if not images:
        print(f"❌ No images found in {test_images_dir}")
        return 1
    
    print(f"📸 Found {len(images)} image(s))")
    print(f"📁 Creating metadata files in: {metadata_dir}\n")
    
    created_files = []
    
    for img_path in images:
        metadata = create_metadata_for_image(img_path)
        metadata_file = metadata_dir / f"{img_path.stem}.json"
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        created_files.append(metadata_file)
        print(f"✅ Created: {metadata_file.name}")
        print(f"   Study ID: {metadata['study_id']}")
        print(f"   View: {metadata['view']}")
        print()
    
    print(f"✅ Created {len(created_files)} metadata file(s)")
    print(f"\n📝 Metadata files are ready for testing!")
    print(f"   Location: {metadata_dir}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

