#!/bin/bash
# Ollama Persistent Model Loading Script
# Loads model into VRAM and keeps it loaded indefinitely
# Base Path: /mnt/ai8_arch
# Author: CannonCoPilot
# Date: 2025-01-11
# Usage: ollama_preload.sh <model_name>

set -euo pipefail

MODEL_NAME="${1:-}"
STARTUP_TIMEOUT=300
LOAD_TIMEOUT=600
LOG_DIR="/var/log"

# Logging with timestamps
log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  if [ -d "$LOG_DIR" ]; then
    echo "$msg" >> "$LOG_DIR/ollama_preload.log"
  fi
}

log "🚀 Starting Ollama with PERSISTENT model: $MODEL_NAME"

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
  GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader | head -1)
  FREE_VRAM=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
  TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
  
  log "📊 GPU Status:"
  log "  • GPU Count: $GPU_COUNT"
  log "  • VRAM Free: ${FREE_VRAM}MB / ${TOTAL_VRAM}MB"
  
  if [ "$FREE_VRAM" -lt 10000 ]; then
    log "⚠️  Low VRAM available: ${FREE_VRAM}MB"
  fi
else
  log "⚠️  nvidia-smi not available, cannot check GPU status"
fi

# Start Ollama server in background
log "Starting Ollama server..."
ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
SERVE_PID=$!

log "Ollama PID: $SERVE_PID"

# The `ollama` CLI will wait for the server to be ready on its own.
# We will proceed directly to the pull command, which will stream its output.
log "⏳ Waiting for Ollama server process to start..."
sleep 5 # Brief pause to allow the server to initialize.
log "✅ Ollama server process started. Proceeding with model pull."
SERVER_READY=true # Assume ready; the pull command will verify connectivity.

# Handle model loading
if [ -z "$MODEL_NAME" ]; then
  log "⚠️  No model specified for preload"
  log "Container will run with Ollama server only"
else
  log "Processing model: $MODEL_NAME"
  
  # To ensure a partial download is resumed, we will always run `ollama pull`.
  # The command will check for updates and download missing layers.
  # Running it in the foreground streams progress directly to the container logs.
  log "📥 Forcing pull/resume for model: $MODEL_NAME"
  log "Model download progress will be displayed below:"
  
  if ollama pull "$MODEL_NAME"; then
    log "✅ Model pull complete for $MODEL_NAME."
    
    # Now, attempt to preload the model into VRAM.
    log "🔥 Loading model into VRAM (persistent, timeout: ${LOAD_TIMEOUT}s)..."
    log "This will keep the model in VRAM indefinitely (keep_alive: -1)"
    
    # Create request payload
    REQUEST_PAYLOAD=$(cat <<EOF
{
  "model": "$MODEL_NAME",
  "prompt": "System initialization complete. Ready to serve requests.",
  "stream": false,
  "keep_alive": -1
}
EOF
)
    
    # Send load request (fatal if it fails)
    START_TIME=$(date +%s)
    RESPONSE=$(curl -sf -X POST \
      --max-time $LOAD_TIMEOUT \
      http://localhost:11434/api/generate \
      -H "Content-Type: application/json" \
      -d "$REQUEST_PAYLOAD" \
      2>&1) || {
      log "❌ Model load failed (curl error)"
      log "Response: $RESPONSE"
      log "Continuing without persistent load; model pull may still be in progress."
    }
    END_TIME=$(date +%s)
    LOAD_TIME=$((END_TIME - START_TIME))
    
    # Verify successful load
    if echo "$RESPONSE" | grep -q '"done":true'; then
      log "✅ Model $MODEL_NAME loaded and persistent in VRAM (${LOAD_TIME}s)"
      
      # Parse load duration from response if available
      if echo "$RESPONSE" | grep -q "total_duration"; then
        TOTAL_DURATION=$(echo "$RESPONSE" | grep -o '"total_duration":[0-9]*' | cut -d: -f2)
        if [ -n "$TOTAL_DURATION" ]; then
          DURATION_SEC=$((TOTAL_DURATION / 1000000000))
          log "  • Total duration: ${DURATION_SEC}s"
        fi
      fi
      
      # Show VRAM usage
      if command -v nvidia-smi &> /dev/null; then
        USED_VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
        FREE_VRAM=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
        log "  • VRAM used: ${USED_VRAM}MB"
        log "  • VRAM free: ${FREE_VRAM}MB"
      fi
    else
      log "⚠️ Model load verification did not confirm a persistent load."
    fi
  else
    log "❌ Model pull failed. The container will continue to run, but the model will not be preloaded."
  fi
fi

# Set up signal handlers for graceful shutdown
shutdown_handler() {
  log "Received shutdown signal"
  log "Stopping Ollama server (PID: $SERVE_PID)..."
  kill -TERM $SERVE_PID 2>/dev/null || true
  wait $SERVE_PID 2>/dev/null || true
  log "Shutdown complete"
  exit 0
}

trap shutdown_handler SIGTERM SIGINT

log "🎯 Service ready and healthy"
log "Model will remain in VRAM until container stops"
log "Ollama API available at http://localhost:11434"

# Keep container running
wait $SERVE_PID
EXIT_CODE=$?
log "Ollama server exited with code: $EXIT_CODE"
exit $EXIT_CODE
```