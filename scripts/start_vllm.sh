#!/usr/bin/env bash
# scripts/start_vllm.sh
# Entrypoint to start vLLM openai-compatible server with sensible defaults.
# Usage: the container CMD/compose can append additional vllm args.

set -euo pipefail

# Default model (override in docker-compose command)
DEFAULT_MODEL="${VLLM_DEFAULT_MODEL:-Qwen/Qwen3-Omni-30B-A3B-Thinking}"

# Verify HF_TOKEN (fail fast if model is gated)
if [ -z "${HF_TOKEN:-}" ]; then
  echo "WARNING: HF_TOKEN is not set. If model is gated you will not be able to download it."
fi

# Export huggingface token for transformers/hf_hub
export HUGGINGFACE_HUB_TOKEN="${HF_TOKEN:-}"

# If no args provided, run server for DEFAULT_MODEL
if [ $# -eq 0 ]; then
  set -- \
    "--trust-remote-code" \
    "--model" "${DEFAULT_MODEL}" \
    "--port" "8000" \
    "--host" "0.0.0.0" \
    "--dtype" "float16" \
    "--gpu-memory-utilization" "0.90"
fi

echo "Starting vLLM with args: $*"
# Run vllm CLI (the installed package provides the CLI "vllm" entrypoint)
# The vllm package exposes python module; using python -m to be explicit:
python -m vllm.entrypoints.openai.api_server "$@"