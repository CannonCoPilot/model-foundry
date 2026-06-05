#!/bin/bash
set -e  # Exit on error

# Access the build argument (which is available as an environment variable during the RUN command)
echo "Value of BUILD_MODEL inside the script: $BUILD_MODEL"

# Start the Ollama server in the background
echo "Starting Ollama server..."
ollama serve &
SERVE_PID=$!

# Wait for the server to start
echo "Waiting for Ollama server to be active..."
while ! ollama list | grep -q 'NAME'; do
  sleep 1
done

# Get the model name from environment variable or use default
MODEL_NAME="${BUILD_MODEL:-default_model}"

# Check if the model name is set
echo "Using model: ${MODEL_NAME}"

# Pull the model
echo "Pulling ${MODEL_NAME} model..."
ollama pull ${MODEL_NAME}
sleep 5

# Run the model and keep it alive
echo "Running ${MODEL_NAME} model..."
ollama run ${MODEL_NAME} &
MODEL_PID=$!

# Send a dummy prompt to load the model
sleep 5
echo "Sending test prompt to model..."
curl -s -X POST http://localhost:11434/api/generate -d "{\"model\": \"${MODEL_NAME}\", \"prompt\": \"test\", \"stream\": false}" > /dev/null

# Keep the container running
echo "Model is ready and running. Waiting for server process..."
wait $SERVE_PID