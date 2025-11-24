# ONNX Model Export Guide

## Overview

This guide explains how to export the TorchXRayVision DenseNet121 model to ONNX format for use with Triton Inference Server in the RadStream pipeline.

## Model Source

We're using the **TorchXRayVision DenseNet121** model from the `chexagent_chexpert_eval` project:
- **Architecture**: DenseNet121
- **Pre-trained weights**: `densenet121-res224-chex` (trained on CheXpert dataset)
- **Input**: Grayscale chest X-ray images (1 channel, 224x224)
- **Output**: Logits for 13 CheXpert labels (binary classification probabilities)

## Why This Model?

1. ✅ **Already in use**: Proven to work in `chexagent_chexpert_eval` project
2. ✅ **Pre-trained**: No need for training, just export
3. ✅ **Suitable for ONNX**: Standard CNN architecture, easy to export
4. ✅ **Medical imaging**: Specifically designed for chest X-ray analysis
5. ✅ **Lightweight**: DenseNet121 is efficient for CPU inference

## Export Process

### Step 1: Install Dependencies

```bash
cd "/Users/rahul/Downloads/Code scripts/RadStream"
source venv/bin/activate  # or create new venv
pip install torch torchvision torchxrayvision onnx onnxruntime
```

### Step 2: Run Export Script

```bash
python rahul/scripts/export_txr_to_onnx.py \
    --weights densenet121-res224-chex \
    --output model.onnx \
    --model-repo model_repo \
    --model-name chexpert_classifier
```

This will:
1. Load the TorchXRayVision DenseNet121 model
2. Export it to ONNX format
3. Validate the ONNX model with ONNX Runtime
4. Create Triton model repository structure

### Step 3: Verify Output

The script creates:
```
model_repo/
  chexpert_classifier/
    1/
      model.onnx          # Exported ONNX model
    config.pbtxt          # Triton configuration
```

### Step 4: Test ONNX Model (Optional)

```python
import onnxruntime as ort
import numpy as np

# Load ONNX model
sess = ort.InferenceSession("model.onnx")

# Create dummy input (grayscale: 1 channel, 224x224)
dummy_input = np.random.randn(1, 1, 224, 224).astype(np.float32)

# Run inference
outputs = sess.run(None, {"input": dummy_input})
print(f"Output shape: {outputs[0].shape}")  # Should be (1, 13)
print(f"Output range: [{outputs[0].min():.4f}, {outputs[0].max():.4f}]")
```

## Model Details

### Input Format
- **Shape**: `(batch_size, 1, 224, 224)` - Grayscale image
- **Data type**: `float32`
- **Normalization**: Images should be normalized using `xrv.datasets.normalize(arr, 255.0)`
- **Preprocessing**: 
  - Convert to grayscale: `Image.convert("L")`
  - Resize to 224x224: `Image.resize((224, 224), Image.BILINEAR)`
  - Normalize: `xrv.datasets.normalize(np.array(img), 255.0)`

### Output Format
- **Shape**: `(batch_size, 13)` - 13 CheXpert labels
- **Data type**: `float32`
- **Values**: Logits (use sigmoid to get probabilities)
- **Labels**:
  1. Enlarged Cardiomediastinum
  2. Cardiomegaly
  3. Lung Opacity
  4. Lung Lesion
  5. Edema
  6. Consolidation
  7. Pneumonia
  8. Atelectasis
  9. Pneumothorax
  10. Pleural Effusion
  11. Pleural Other
  12. Fracture
  13. Support Devices

## Integration with RadStream Pipeline

### Update Lambda Function (`prepare_tensors.py`)

The Lambda function should preprocess images to match the model's expected input:
- Resize to 224x224
- Convert to grayscale
- Normalize using TorchXRayVision normalization

### Update Step Functions

The Step Functions workflow will call Triton Inference Server with:
- Preprocessed image tensor (from Lambda)
- Model name: `chexpert_classifier`
- Get back 13 label probabilities

### Update Results Storage

Store inference results with label names and probabilities in S3.

## Troubleshooting

### Issue: Model export fails
- **Solution**: Ensure `torchxrayvision` is installed: `pip install torchxrayvision`
- Check PyTorch version compatibility

### Issue: ONNX validation fails
- **Solution**: Install `onnxruntime`: `pip install onnxruntime`
- Check ONNX opset version compatibility

### Issue: Model size is too large
- **Solution**: The model should be ~30-40 MB. If larger, check for unnecessary dependencies.

### Issue: Input shape mismatch
- **Solution**: Ensure input is grayscale (1 channel), not RGB (3 channels)
- Verify preprocessing matches TorchXRayVision normalization

## Next Steps

1. ✅ Export model to ONNX (this script)
2. ⏳ Update Dockerfile to include model in Triton image
3. ⏳ Test model with Triton Inference Server locally
4. ⏳ Update Step Functions to call Triton endpoint
5. ⏳ Test end-to-end pipeline

## References

- TorchXRayVision: https://github.com/mlmed/torchxrayvision
- ONNX Export: https://pytorch.org/docs/stable/onnx.html
- Triton ONNX Backend: https://github.com/triton-inference-server/onnxruntime_backend

