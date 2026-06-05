#!/bin/bash
# Ollama On-Demand Model Loading Script
# Downloads model but loads into VRAM only on first request
# Unloads after timeout period (default: 600s)
# Base Path: /mnt/ai8_arch
# Author: CannonCoPilot
# Date: 2025-01-11
# Usage: ollama_lazy_load.sh <model_name>

set -euo pipefail

MODEL_NAME="${1:-}"
STARTUP_TIMEOUT=120
KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-600}"
LOG_DIR="/var/log"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  if [ -d "$LOG_DIR" ]; then
    echo "$msg" >> "$LOG_DIR/ollama_lazy_load.log"
  fi
}

log "🚀 Starting Ollama with ON-DEMAND model: $MODEL_NAME"
log "⏱️  Keep-alive timeout: ${KEEP_ALIVE}s (model unloads after inactivity)"

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
  GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader | head -1)
  FREE_VRAM=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
  log "📊 GPU: $GPU_COUNT available, ${FREE_VRAM}MB VRAM free"
else
  log "⚠️  nvidia-smi not available"
fi

# Start Ollama server
log "Starting Ollama server..."
ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
SERVE_PID=$!

log "Ollama PID: $SERVE_PID"

# Wait for server with timeout
log "⏳ Waiting for Ollama server..."
ELAPSED=0
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
  
  if ! kill -0 $SERVE_PID 2>/dev/null; then
    log "❌ Ollama server process died"
    if [ -f "$LOG_DIR/ollama.log" ]; then
      tail -n 20 "$LOG_DIR/ollama.log"
    fi
    exit 1
  fi
  
  if [ $ELAPSED -ge $STARTUP_TIMEOUT ]; then
    log "❌ Timeout waiting for Ollama"
    exit 1
  fi
done

log "✅ Ollama server ready (took ${ELAPSED}s)"

# Handle model downloading
if [ -z "$MODEL_NAME" ]; then
  log "⚠️  No default model specified"
  log "Models can be loaded via API on demand"
else
  log "Preparing model: $MODEL_NAME"
  
  # Check if model exists
  if ! ollama list 2>/dev/null | grep -qE "^${MODEL_NAME}(\s|:)"; then
    log "📥 Downloading model: $MODEL_NAME"
    log "This may take a while..."
    
    for attempt in {1..3}; do
      log "Download attempt $attempt/3..."
      if ollama pull "$MODEL_NAME" 2>&1 | tee -a "$LOG_DIR/ollama.log"; then
        log "✅ Model downloaded: $MODEL_NAME"
        break
      else
        if [ $attempt -lt 3 ]; then
          log "⚠️  Download attempt $attempt failed, retrying..."
          sleep 30
        else
          log "❌ Failed to download model"
          exit 1
        fi
      fi
    done
  else
    log "✅ Model already downloaded: $MODEL_NAME"
    
    # Check for updates
    log "Checking for updates..."
    if ollama pull "$MODEL_NAME" 2>&1 | grep -q "up to date"; then
      log "  ✓ Model is up to date"
    else
      log "  → Model updated"
    fi
  fi
  
  log "⏸️  Model ready for on-demand loading"
  log "💡 First request will:"
  log "   • Load model into VRAM (10-60 seconds)"
  log "   • Keep in VRAM for ${KEEP_ALIVE}s after last request"
  log "   • Auto-unload after ${KEEP_ALIVE}s of inactivity"
fi

# Graceful shutdown
shutdown_handler() {
  log "Received shutdown signal"
  log "Stopping Ollama server..."
  kill -TERM $SERVE_PID 2>/dev/null || true
  wait $SERVE_PID 2>/dev/null || true
  log "Shutdown complete"
  exit 0
}

trap shutdown_handler SIGTERM SIGINT

log "🎯 Service ready"
log "Ollama API available at http://localhost:11434"

wait $SERVE_PID
EXIT_CODE=$?
log "Ollama server exited with code: $EXIT_CODE"
exit $EXIT_CODE
```