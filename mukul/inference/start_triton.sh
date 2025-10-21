#!/bin/bash
# RadStream Triton Server Startup Script

echo "Starting RadStream Triton Inference Server..."

# Set environment variables
export TRITON_MODEL_STORE=/models
export TRITON_SERVER_HTTP_PORT=8000
export TRITON_SERVER_GRPC_PORT=8001
export TRITON_SERVER_METRICS_PORT=8002

# Start Triton server
exec tritonserver \
    --model-store=${TRITON_MODEL_STORE} \
    --http-port=${TRITON_SERVER_HTTP_PORT} \
    --grpc-port=${TRITON_SERVER_GRPC_PORT} \
    --metrics-port=${TRITON_SERVER_METRICS_PORT} \
    --log-verbose=1 \
    --log-info=true \
    --log-warning=true \
    --log-error=true \
    --allow-http=true \
    --allow-grpc=true \
    --allow-metrics=true \
    --strict-model-config=false
