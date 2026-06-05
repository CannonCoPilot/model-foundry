#!/bin/bash
# Unified Playground Startup Script
# Supports Ollama and vLLM for user experimentation
# Base Path: /mnt/ai8_arch

set -euo pipefail

LOG_DIR="/var/log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  if [ -d "$LOG_DIR" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_DIR/playground.log"
  fi
}

log "🎮 Starting User Playground Container"
log "📍 Base Path: /mnt/ai8_arch/models/ollama/playground/"

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
  GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader | head -1)
  GPU_INFO=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
  log "🎮 GPU: $GPU_COUNT x $GPU_INFO"
  
  # Show VRAM
  FREE_VRAM=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
  TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
  log "💾 VRAM: ${FREE_VRAM}MB free / ${TOTAL_VRAM}MB total"
else
  log "⚠️  No GPU detected"
fi

# Start Ollama server
start_ollama() {
  log "🚀 Starting Ollama server..."
  export OLLAMA_HOST=0.0.0.0
  ollama serve &
  OLLAMA_PID=$!
  
  log "⏳ Waiting for Ollama server (timeout: 60s)..."
  for i in {1..60}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
      log "✅ Ollama server ready on port 11434 (took ${i}s)"
      return 0
    fi
    
    if ! kill -0 $OLLAMA_PID 2>/dev/null; then
      log "❌ Ollama server process died"
      if [ -f "$LOG_DIR/ollama.log" ]; then
        cat "$LOG_DIR/ollama.log"
      fi
      return 1
    fi
    
    sleep 1
  done
  
  log "❌ Ollama server failed to start within 60s"
  return 1
}

if ! start_ollama; then
  log "🔥🔥🔥 Ollama failed to start. Exiting container. Check logs for details."
  exit 1
fi

# Print comprehensive usage guide
cat << 'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎮 USER PLAYGROUND - Interactive Model Experimentation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 Storage Locations:
   • Ollama models: /root/.ollama → /mnt/ai8_arch/models/ollama/playground/
   • HuggingFace:   /root/.cache/huggingface → /mnt/ai8_arch/models/huggingface/
   • Logs:          /var/log/ → /mnt/ai8_arch/logs/playground/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 OLLAMA USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Basic Commands:
  ollama pull <model>           # Download model
  ollama run <model>            # Interactive chat
  ollama list                   # List local models
  ollama ps                     # Show running models
  ollama rm <model>             # Remove model

Examples:
  # Small models (testing)
  ollama pull llama2:7b
  ollama run llama2:7b "Explain quantum computing"
  
  # Medium models
  ollama pull mistral:7b
  ollama pull phi3:14b
  
  # Vision models
  ollama pull llava:13b
  ollama run llava:13b "Describe this image" --image /path/to/image.jpg

API Usage:
  # Generate completion
  curl http://localhost:11434/api/generate -d '{
    "model": "llama2:7b",
    "prompt": "Why is the sky blue?",
    "stream": false
  }'
  
  # Chat completion
  curl http://localhost:11434/api/chat -d '{
    "model": "llama2:7b",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 VLLM USAGE (HuggingFace Models)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Start vLLM Server:
  # Basic usage
  python3 -m vllm.entrypoints.openai.api_server \
    --model <hf_model_id> \
    --port 8000 \
    --gpu-memory-utilization 0.9

  # With tensor parallelism (multi-GPU)
  python3 -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-13b-hf \
    --tensor-parallel-size 2 \
    --port 8000

Popular Models:
  # Chat models
  meta-llama/Llama-2-7b-chat-hf
  meta-llama/Llama-2-13b-chat-hf
  mistralai/Mistral-7B-Instruct-v0.2
  google/gemma-7b-it
  
  # Code models
  Salesforce/codegen-2B-multi
  bigcode/starcoder
  
  # Vision models
  liuhaotian/llava-v1.5-7b
  OpenGVLab/InternVL-Chat-V1-5

API Usage (OpenAI-compatible):
  # List models
  curl http://localhost:8000/v1/models
  
  # Chat completion
  curl http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model": "meta-llama/Llama-2-7b-chat-hf",
      "messages": [{"role": "user", "content": "Hello"}]
    }'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 PYTHON USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ollama Python Client:
  pip3 install ollama
  python3 << 'PYTHON'
import ollama
response = ollama.chat(
    model='llama2',
    messages=[{'role': 'user', 'content': 'Why is the sky blue?'}]
)
print(response['message']['content'])
PYTHON

OpenAI Client (for vLLM):
  pip3 install openai
  python3 << 'PYTHON'
from openai import OpenAI
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"
)
response = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-chat-hf",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
PYTHON

LangChain Integration:
  pip3 install langchain langchain-community
  python3 << 'PYTHON'
from langchain_community.llms import Ollama
llm = Ollama(model="llama2")
response = llm.invoke("Why is the sky blue?")
print(response)
PYTHON

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 TIPS & TRICKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Monitor Resources:
  nvidia-smi                    # GPU status
  watch -n 1 nvidia-smi         # Live GPU monitoring
  ollama ps                     # Running Ollama models
  df -h /root/.ollama           # Disk usage

View Logs:
  tail -f /var/log/ollama.log           # Ollama logs
  tail -f /var/log/playground.log       # Startup logs
  docker logs -f user-playground        # Container logs

Model Organization:
  # Create subfolders for different purposes
  mkdir -p /root/.ollama/experiments
  mkdir -p /root/.ollama/testing
  
  # Models auto-organize in standard Ollama structure

Quick Model Tests:
  # Download and test small model
  ollama pull llama2:7b && \
  echo "Test prompt" | ollama run llama2:7b
  
  # Benchmark inference speed
  time ollama run llama2:7b "Count to 10"

Cleanup:
  # Remove unused models
  ollama rm <model>
  
  # Clear Ollama cache
  rm -rf /root/.ollama/tmp/*
  
  # Clear HuggingFace cache (careful!)
  rm -rf /root/.cache/huggingface/hub/*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 EXTERNAL ACCESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From Host Machine:
  # Ollama API
  curl http://localhost:11620/api/tags
  
  # vLLM API (when started)
  curl http://localhost:8020/v1/models

From Other Containers:
  # Ollama
  http://user-playground:11434
  
  # vLLM
  http://user-playground:8000

Through LiteLLM Gateway:
  # Configure in litellm_config.yaml to route to playground
  # Then access via: http://localhost:4000/v1/...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 DOCUMENTATION LINKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • Ollama:       https://github.com/ollama/ollama
  • Ollama API:   https://github.com/ollama/ollama/blob/main/docs/api.md
  • vLLM:         https://docs.vllm.ai/
  • HuggingFace:  https://huggingface.co/models
  • LangChain:    https://python.langchain.com/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

log "🎯 Playground ready for experimentation"

# Set up signal handlers
trap 'log "Received shutdown signal"; exit 0' SIGTERM SIGINT

# Keep container running by waiting on the Ollama process
trap 'log "Received shutdown signal"; kill $OLLAMA_PID; wait $OLLAMA_PID; exit 0' SIGTERM SIGINT
wait $OLLAMA_PID