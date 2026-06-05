#!/bin/bash
# Reload configuration without destroying volumes
# Base Path: /mnt/ai8_arch

set -euo pipefail

cd /mnt/ai8_arch

echo "🔄 Reloading AI8 Architecture Configuration"
echo ""

# Validate docker-compose file
echo "1️⃣  Validating docker-compose.yaml..."
if ! docker compose config > /dev/null 2>&1; then
  echo "❌ Invalid docker-compose.yaml"
  docker compose config
  exit 1
fi
echo "  ✓ Configuration valid"

# Validate environment file
echo "2️⃣  Checking .env file..."
if [ ! -f .env ]; then
  echo "❌ Missing .env file"
  exit 1
fi

# Check required variables
source .env
REQUIRED_VARS=("HF_TOKEN" "POSTGRES_PASSWORD" "LITELLM_MASTER_KEY")
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "❌ Missing required variable: $var"
    exit 1
  fi
done
echo "  ✓ Environment variables set"

# Reload services that support hot-reload
echo "3️⃣  Reloading LiteLLM configuration..."
docker compose exec litellm kill -HUP 1 2>/dev/null || {
  echo "  ⚠️  LiteLLM not running or doesn't support HUP, restarting..."
  docker compose restart litellm
}
echo "  ✓ LiteLLM configuration reloaded"

# Restart services that need it (preserve volumes)
echo "4️⃣  Restarting services with new configuration..."
docker compose up -d --no-recreate

echo ""
echo "✅ Configuration reload complete"
echo ""
echo "📊 Service status:"
docker compose ps

echo ""
echo "💡 To apply changes requiring container recreation:"
echo "   docker compose up -d --force-recreate <service_name>"
echo ""
echo "💡 To completely rebuild images:"
echo "   docker compose build --no-cache <service_name>"
echo "   docker compose up -d <service_name>"
```