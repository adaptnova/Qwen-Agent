#!/bin/bash
# Start Qwen3-30B-A3B-Thinking Server with 262K Context Window

echo "🚀 Starting Qwen3-30B-A3B-Thinking Server"
echo "=========================================="

# Kill any existing servers
echo "🛑 Stopping existing servers..."
pkill -f 'vllm.entrypoints.openai.api_server' || true
sleep 3

# Model configuration
MODEL_PATH="/data/models/Qwen3-30B-A3B-Thinking-2507-FP8"

echo "📋 Configuration:"
echo "🔥 Model: Qwen3-30B-A3B-Thinking-FP8 (MoE)"
echo "🔥 Context: 262,144 tokens (native maximum)"
echo "🔥 GPU Memory: 70% utilization"
echo "🔥 Architecture: FP8 quantized"

# Check if model exists
if [ ! -d "$MODEL_PATH" ]; then
    echo "❌ Model not found at: $MODEL_PATH"
    exit 1
fi

echo "✅ Model path verified"
echo "🚀 Starting vLLM server..."

# Start server with maximum configuration
python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --port 8000 \
    --host 0.0.0.0 \
    --trust-remote-code \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.7 \
    --max-model-len 262144 \
    --dtype auto \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --disable-log-stats \
    --served-model-name Qwen3-30B-A3B-Thinking

echo ""
echo "✅ If you see this, the server has stopped"
echo "🔍 Check if it started successfully with:"
echo "   curl http://localhost:8000/v1/models"