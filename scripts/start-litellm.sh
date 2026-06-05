#!/bin/bash
set -e

# Start the LiteLLM proxy in the foreground
# Using exec allows the main process to receive signals from Docker
# Start the health check server in the background
python3 /app/healthz.py &

# Ensure the database schema is up-to-date before starting
echo "Cleaning up migrations directory..."
rm -rf /app/migrations/__pycache__
echo "Running database migrations..."
npx prisma migrate deploy
echo "Migrations complete."

# Start the LiteLLM proxy in the foreground
# Using exec allows the main process to receive signals from Docker
exec litellm --config /app/config.yaml --port 4000 --num_workers 4