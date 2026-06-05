#!/bin/sh
set -e

echo "INFO: Entrypoint script started."

# 1. Check if OLLAMA_MODEL_TO_PULL environment variable is set
if [ -z "$OLLAMA_MODEL_TO_PULL" ]; then
  echo "ERROR: OLLAMA_MODEL_TO_PULL environment variable is not set. This variable is required." >&2
  exit 1
else
  echo "INFO: OLLAMA_MODEL_TO_PULL is set to: '$OLLAMA_MODEL_TO_PULL'"
fi

# 2. Pull the specified model
echo "INFO: Attempting to pull model '$OLLAMA_MODEL_TO_PULL'..."
if ollama pull "$OLLAMA_MODEL_TO_PULL"; then
  echo "INFO: Model '$OLLAMA_MODEL_TO_PULL' pulled successfully."
else
  echo "ERROR: Failed to pull model '$OLLAMA_MODEL_TO_PULL'. Please check the model name and availability." >&2
  exit 1
fi

# Set OLLAMA_HOST to allow connections from other containers/hosts if not already set.
# Ollama by default might listen on 127.0.0.1, 0.0.0.0 makes it listen on all interfaces.
export OLLAMA_HOST=${OLLAMA_HOST:-"0.0.0.0"}
echo "INFO: OLLAMA_HOST is configured to: '$OLLAMA_HOST'"

# 3. Start ollama in serving mode
echo "INFO: Starting Ollama server..."
exec ollama serve