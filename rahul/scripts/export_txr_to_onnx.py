#!/usr/bin/env python3
"""
Export TorchXRayVision DenseNet121 model to ONNX format for Triton Inference Server.

This script:
1. Loads the pre-trained TorchXRayVision DenseNet121 model (CheXpert weights)
2. Exports it to ONNX format (raw 18 TorchXRayVision logits)
3. Validates the ONNX model with ONNX Runtime
4. Creates the model repository structure for Triton

Model Details:
- Architecture: DenseNet121 (TorchXRayVision)
- Input: Grayscale image (1, 224, 224) - normalized using xrv.datasets.normalize
- Output: Logits for 18 TorchXRayVision pathologies (CheXpert mapping handled downstream)
- Weights: densenet121-res224-chex (pre-trained on CheXpert)
- Mapping: 18 TXR pathologies → 14 CheXpert labels (matches chexagent_chexpert_eval project)
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

try:
    import torchxrayvision as xrv
except ImportError:
    print("ERROR: torchxrayvision is required. Install with: pip install torchxrayvision")
    sys.exit(1)

try:
    import onnxruntime as ort
except ImportError:
    print("WARNING: onnxruntime not installed. ONNX validation will be skipped.")
    print("Install with: pip install onnxruntime")
    ort = None

# CheXpert labels (14 labels: 13 findings + "No Finding")
# This matches chexagent_chexpert_eval project
CHEXPERT13 = [
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

def normalize_name(name: str) -> str:
    """Normalize label name for matching (lowercase, replace spaces with underscores)."""
    return name.lower().replace(" ", "_")


def build_label_mapping(txr_pathologies: list) -> dict:
    """
    Map TorchXRayVision pathologies to CheXpert labels.
    Based on the mapping logic from chexagent_chexpert_eval/src/inference/txr_infer.py
    """
    lookups = {normalize_name(p): p for p in txr_pathologies}
    
    # Synonyms when naming differs between TXR and CheXpert
    synonyms = {
        "pleural_effusion": ["effusion", "pleural_effusion"],
        "pleural_other": ["pleural_other", "pleural_thickening"],
        "support_devices": ["support_devices", "supportdevice", "devices"],
        "lung_lesion": ["lung_lesion", "lesion"],
        "no_finding": ["no_finding", "none"],
    }
    
    mapping = {}  # Maps CheXpert label -> TXR pathology index
    for idx, label in enumerate(CHEXPERT13):
        norm = normalize_name(label)
        candidates = [norm] + synonyms.get(norm, [])
        matched_idx = None
        for cand in candidates:
            if cand in lookups:
                # Find the index of the matched pathology
                matched_pathology = lookups[cand]
                matched_idx = txr_pathologies.index(matched_pathology)
                break
        if matched_idx is not None:
            mapping[label] = matched_idx
    
    return mapping


def load_txr_model(weights: str = "densenet121-res224-chex"):
    """
    Load TorchXRayVision DenseNet121 model.
    
    Args:
        weights: Model weights identifier (default: "densenet121-res224-chex")
    
    Returns:
        model: PyTorch model in eval mode
        pathologies: List of pathology names the model predicts
    """
    print(f"Loading TorchXRayVision model: {weights}")
    model = xrv.models.DenseNet(weights=weights)
    model.eval()
    print(f"✅ Model loaded successfully")
    print(f"   Pathologies: {len(model.pathologies)} labels")
    print(f"   Sample pathologies: {model.pathologies[:5]}...")
    return model, model.pathologies


class ExportableModel(torch.nn.Module):
    """Wrapper that bypasses TorchXRayVision's preprocessing checks and returns 18 logits."""

    def __init__(self, txr_model: torch.nn.Module):
        super().__init__()
        self.features = txr_model.features
        self.classifier = txr_model.classifier

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.features(x)
        pooled = features.mean(3).mean(2)  # global average pooling
        return self.classifier(pooled)  # (batch, 18)


def export_to_onnx(
    model: torch.nn.Module,
    txr_pathologies: list,
    output_path: Path,
    input_shape: tuple = (1, 1, 224, 224),
    opset_version: int = 12,
):
    """
    Export PyTorch model to ONNX format with CheXpert label mapping.
    
    Args:
        model: TorchXRayVision DenseNet model in eval mode
        txr_pathologies: List of TXR pathology names (18 labels)
        output_path: Path to save ONNX model
        input_shape: Input tensor shape (batch, channels, height, width)
        opset_version: ONNX opset version
    """
    print(f"\nExporting model to ONNX...")
    print(f"   Input shape: {input_shape}")
    print(f"   Opset version: {opset_version}")
    print(f"   TXR pathologies: {len(txr_pathologies)} labels")
    
    # Build label mapping from TXR pathologies to CheXpert labels
    print("   Building CheXpert label mapping for downstream post-processing...")
    label_mapping = build_label_mapping(txr_pathologies)
    print(f"   ✅ Mapped {len(label_mapping)} CheXpert findings from TXR pathologies")
    missing = [label for label in CHEXPERT13 if label not in label_mapping]
    if missing:
        print(f"   ⚠️  Warning: {len(missing)} CheXpert labels not found in TXR model: {missing}")
    
    # Create dummy input matching preprocessing
    # TorchXRayVision expects: (batch, 1, 224, 224) - grayscale
    dummy_input = torch.randn(*input_shape)
    
    # Create simple exportable model (18 TXR outputs, mapping handled later)
    print("   Creating exportable wrapper (no label mapping inside the graph)...")
    chexpert_model = ExportableModel(model)
    chexpert_model.eval()
    
    # Test forward pass
    with torch.no_grad():
        test_output = chexpert_model(dummy_input)
        print(f"   ✅ Test forward pass: input {dummy_input.shape} → output {test_output.shape} (18 TXR pathologies)")
        assert test_output.shape[1] == 18, f"Expected 18 outputs, got {test_output.shape[1]}"
    
    # Export model to ONNX
    # Note: Using fixed batch size for export; Triton will handle dynamic batching via config
    print("   Exporting to ONNX (this may take a minute)...")
    torch.onnx.export(
        chexpert_model,
        dummy_input,
        str(output_path),
        input_names=["input"],
        output_names=["output"],
        opset_version=opset_version,
        do_constant_folding=True,
        export_params=True,
        verbose=False,
        dynamic_axes={
            "input": {0: "batch_size"},
            "output": {0: "batch_size"},
        },
    )
    
    print(f"✅ ONNX model exported to: {output_path}")
    print(f"   File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    print("   Output: 18 TorchXRayVision pathologies (apply sigmoid + mapping in Triton client)")
    return label_mapping


def validate_onnx(onnx_path: Path, input_shape: tuple = (1, 1, 224, 224)):
    """
    Validate ONNX model using ONNX Runtime.
    
    Args:
        onnx_path: Path to ONNX model
        input_shape: Input tensor shape
    """
    if ort is None:
        print("⚠️  Skipping ONNX validation (onnxruntime not installed)")
        return
    
    print(f"\nValidating ONNX model...")
    
    try:
        # Create inference session
        sess = ort.InferenceSession(str(onnx_path))
        
        # Get input/output details
        input_name = sess.get_inputs()[0].name
        output_name = sess.get_outputs()[0].name
        input_shape_onnx = sess.get_inputs()[0].shape
        output_shape_onnx = sess.get_outputs()[0].shape
        
        print(f"   Input name: {input_name}")
        print(f"   Input shape: {input_shape_onnx}")
        print(f"   Output name: {output_name}")
        print(f"   Output shape: {output_shape_onnx}")
        
        # Run inference with dummy data
        dummy_input = np.random.randn(*input_shape).astype(np.float32)
        outputs = sess.run([output_name], {input_name: dummy_input})
        
        output = outputs[0]
        print(f"   Output shape: {output.shape}")
        print(f"   Output range: [{output.min():.4f}, {output.max():.4f}]")
        print(f"   Output mean: {output.mean():.4f}")
        
        print(f"✅ ONNX model validation successful!")
        
    except Exception as e:
        print(f"❌ ONNX validation failed: {e}")
        raise


def create_triton_model_repo(
    onnx_path: Path,
    repo_path: Path,
    model_name: str = "chexpert_classifier",
    num_labels: int = 18,  # 18 TorchXRayVision pathologies
    label_mapping: dict = None,
    txr_pathologies: list = None,
):
    """
    Create Triton model repository structure.
    
    Structure:
    model_repo/
      chexpert_classifier/
        1/
          model.onnx
        config.pbtxt
    """
    print(f"\nCreating Triton model repository...")
    
    # Create directory structure
    model_dir = repo_path / model_name / "1"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy ONNX model
    import shutil
    target_onnx = model_dir / "model.onnx"
    shutil.copy2(onnx_path, target_onnx)
    print(f"   Copied ONNX model to: {target_onnx}")
    
    # Create config.pbtxt
    config_path = repo_path / model_name / "config.pbtxt"
    config_content = f"""name: "{model_name}"
platform: "onnxruntime_onnx"
max_batch_size: 8
input [
  {{
    name: "input"
    data_type: TYPE_FP32
    dims: [ 1, 224, 224 ]  # Grayscale: 1 channel, 224x224
  }}
]
output [
  {{
    name: "output"
    data_type: TYPE_FP32
    dims: [ {num_labels} ]  # 18 TorchXRayVision pathologies
  }}
]
dynamic_batching {{
  max_queue_delay_microseconds: 10000
  preferred_batch_size: [ 1, 2, 4 ]
}}
instance_group [
  {{
    count: 1
    kind: KIND_CPU
  }}
]
"""
    
    config_path.write_text(config_content)
    print(f"   Created config.pbtxt: {config_path}")
    if label_mapping:
        mapping_path = repo_path / model_name / "label_mapping.json"
        payload = {
            "txr_pathologies": txr_pathologies or [],
            "chexpert13_labels": CHEXPERT13,
            "chexpert_to_txr_index": label_mapping,
            "notes": "Apply sigmoid to ONNX outputs, gather logits using mapping above, then derive 'No Finding' downstream.",
        }
        mapping_path.write_text(json.dumps(payload, indent=2))
        print(f"   Saved label mapping for post-processing: {mapping_path}")
    
    print(f"✅ Triton model repository created at: {repo_path / model_name}")
    print(f"\nModel repository structure:")
    print(f"  {repo_path / model_name}/")
    print(f"    ├── 1/")
    print(f"    │   └── model.onnx")
    print(f"    └── config.pbtxt")


def main():
    parser = argparse.ArgumentParser(
        description="Export TorchXRayVision DenseNet121 to ONNX for Triton"
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="densenet121-res224-chex",
        help="TorchXRayVision model weights (default: densenet121-res224-chex)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="model.onnx",
        help="Output ONNX file path (default: model.onnx)",
    )
    parser.add_argument(
        "--model-repo",
        type=str,
        default="model_repo",
        help="Triton model repository directory (default: model_repo)",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="chexpert_classifier",
        help="Triton model name (default: chexpert_classifier)",
    )
    parser.add_argument(
        "--opset-version",
        type=int,
        default=12,
        help="ONNX opset version (default: 12)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip ONNX Runtime validation",
    )
    args = parser.parse_args()
    
    # Convert to Path objects
    output_path = Path(args.output)
    model_repo_path = Path(args.model_repo)
    
    print("=" * 60)
    print("TorchXRayVision → ONNX Export for Triton Inference Server")
    print("=" * 60)
    
    # Step 1: Load model
    model, pathologies = load_txr_model(args.weights)
    
    # Step 2: Export to ONNX (CheXpert mapping handled downstream)
    label_mapping = export_to_onnx(
        model=model,
        txr_pathologies=pathologies,
        output_path=output_path,
        input_shape=(1, 1, 224, 224),  # Grayscale: 1 channel
        opset_version=args.opset_version,
    )
    
    # Step 3: Validate ONNX model
    if not args.skip_validation:
        validate_onnx(output_path, input_shape=(1, 1, 224, 224))
    
    # Step 4: Create Triton model repository
    create_triton_model_repo(
        onnx_path=output_path,
        repo_path=model_repo_path,
        model_name=args.model_name,
        num_labels=18,
        label_mapping=label_mapping,
        txr_pathologies=pathologies,
    )
    
    print("\n" + "=" * 60)
    print("✅ Export Complete!")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"1. Copy model repository to Docker image:")
    print(f"   COPY {model_repo_path / args.model_name} /models/{args.model_name}")
    print(f"2. Update Triton Dockerfile to use this model")
    print(f"3. Test with Triton Inference Server")
    print(f"\nModel repository location: {model_repo_path.absolute() / args.model_name}")


if __name__ == "__main__":
    main()
