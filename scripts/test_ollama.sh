#!/bin/bash
# Test script for Ollama integration in the user playground
set -euo pipefail

echo "--- Ollama Integration Test ---"

# 1. Pull a small model
echo "1. Pulling 'phi3:mini' model..."
ollama pull phi3:mini

# 2. Run a prompt
echo "2. Running a test prompt..."
ollama run phi3:mini "Explain the significance of the number 42 in one sentence."

# 3. Remove the model
echo "3. Cleaning up the model..."
ollama rm phi3:mini

echo "--- Test Complete ---"