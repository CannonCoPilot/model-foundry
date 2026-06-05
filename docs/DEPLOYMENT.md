# AI8 Architecture - Deployment Guide

**Version:** 1.0.0  
**Last Updated:** 2025-01-11  
**Author:** CannonCoPilot

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Phase 1: Core Infrastructure](#phase-1-foundation)
4. [Phase 2: RAG & Automation](#phase-2-data-layer)
5. [Phase 3: Monitoring & User Access](#phase-3-model-services)
6. [](#phase-4-user-interfaces)
7. [Post-Deployment](#post-deployment)
8. [Maintenance](#maintenance)

---

## Prerequisites

### Hardware Requirements

**Minimum**:
- 8x NVIDIA GPUs (H100, A100, or similar)
- 640GB+ total VRAM
- 128GB+ system RAM
- 2TB+ SSD storage
- 10Gbps+ network

**Recommended**:
- 8x NVIDIA H100 80GB
- 256GB system RAM
- 5TB NVMe SSD
- 25Gbps network

### Software Requirements

**Operating System**:
```bash
# Ubuntu 22.04 LTS (recommended)
lsb_release -a
# Should show: Ubuntu 22.04.x LTS
```

**NVIDIA Drivers**:
```bash
# Version 530+ required for CUDA 12.1
nvidia-smi
# Should show: CUDA Version: 12.1+
```

**Docker**:
```bash
# Docker Engine 24.0+
docker --version
# Should show: Docker version 24.0.0+

# Docker Compose
docker compose version
# Should show: Docker Compose version v2.20.0+
```

**NVIDIA Container Toolkit**:
```bash
# Test GPU access in container
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
# Should display GPU info
```

### Network Requirements

**Internet Access**:
- HuggingFace Hub (huggingface.co)
- Docker Hub (hub.docker.com)
- GitHub Container Registry (ghcr.io)
- Ollama Registry (ollama.ai)

**Firewall Ports** (if external access needed):
```bash
# Essential
4000  # LiteLLM API
5151  # OpenWebUI
3000  # Grafana

# Optional
5678  # n8n
9090  # Prometheus
6333  # Qdrant
```

---

## Pre-Deployment Checklist

### 1. Prepare Base Directory

```bash
# Create base directory
sudo mkdir -p /mnt/ai8_arch
sudo chown $(id -u):$(id -g) /mnt/ai8_arch
cd /mnt/ai8_arch

# Clone repository
git clone https://github.com/CannonCoPilot/ai8-architecture.git .

# Verify structure
ls -la
# Should see: docker-compose.yaml, deploy.sh, etc.
```

### 2. Set Up Directory Structure

```bash
# Run setup script
bash setup_directories.sh

# Follow prompts for model migration (if applicable)
# Choose option based on your existing setup:
#   1: Move (fast, if same filesystem)
#   2: Copy (safe but slow)
#   3: Symlink (requires Isilon mount)
#   4: Skip (organize local files only)

# Verify structure
tree -L 2 /mnt/ai8_arch
```

### 3. Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit environment file
nano .env

# Required changes:
HF_TOKEN=hf_xxxxxxxxxxxxx          # Your HuggingFace token
POSTGRES_PASSWORD=secure_pass      # Strong password
LITELLM_MASTER_KEY=sk-secure-key   # API key (keep secret)
N8N_PASSWORD=n8n_pass              # n8n admin password
GRAFANA_ADMIN_PASSWORD=grafana_pass # Grafana admin password
MONGO_PASSWORD=mongo_pass          # MongoDB password
REDIS_PASSWORD=redis_pass          # Redis password

# Secure the file
chmod 600 .env

# Verify variables
source .env
echo "HF_TOKEN length: ${#HF_TOKEN}"  # Should be >20
echo "All required vars set: OK"
```

### 4. Verify GPU Access

```bash
# Check GPU count
nvidia-smi --query-gpu=count --format=csv,noheader
# Should output: 8

# Check CUDA version
nvidia-smi | grep "CUDA Version"
# Should show: CUDA Version: 12.1 or higher

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
# Should display GPU info in container

# Check GPU memory
nvidia-smi --query-gpu=memory.total --format=csv,noheader
# Should show: 81920 MiB (for H100 80GB) x8
```

### 5. Check Disk Space

```bash
# Check available space
df -h /mnt
# Need: 2TB+ available

# Check inode availability
df -i /mnt
# Ensure sufficient inodes for many small files
```

### 6. Validate Configuration Files

```bash
# Validate docker-compose
docker compose config > /dev/null
echo $?
# Should output: 0 (success)

# Check for syntax errors
docker compose config --quiet
# No output = success

# Validate specific service
docker compose config --services
# Should list all services
```

---

## Phase 1: Core Infrastructure

**Goal**: Deploy core infrastructure (monitoring, database, API gateway)

**Duration**: 15-20 minutes

**Services**:
- Prometheus (metrics)
- GPU Exporter (GPU monitoring)
- Grafana (dashboards)
- PostgreSQL (database)
- LiteLLM (API gateway)

### Step 1: Start Foundation Services

```bash
cd /mnt/ai8_arch

# Deploy Phase 1
./deploy.sh phase1

# Or manually:
docker compose --profile phase1 up -d

# Watch startup logs
docker compose logs -f

# Press Ctrl+C when services are ready
```

### Step 2: Verify Foundation Services

**Prometheus**:
```bash
# Check health
curl -sf http://localhost:9090/-/healthy
echo $?  # Should be 0

# Check targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'
# All should be "up"

# View in browser
firefox http://localhost:9090
```

**GPU Exporter**:
```bash
# Check metrics
curl -s http://localhost:9835/metrics | grep "nvidia_gpu"
# Should show GPU metrics

# Verify all GPUs visible
curl -s http://localhost:9835/metrics | grep "nvidia_gpu_info" | wc -l
# Should be 8 (one per GPU)
```

**PostgreSQL**:
```bash
# Test connection
docker exec llm-postgres pg_isready -U llmuser -d litellm
# Should output: accepting connections

# Check databases
docker exec llm-postgres psql -U llmuser -d litellm -c "\l"
# Should list: litellm, n8n

# Verify extensions
docker exec llm-postgres psql -U llmuser -d n8n -c "SELECT extname FROM pg_extension;"
# Should include: pg_trgm, btree_gin
```

**LiteLLM**:
```bash
# Check health
curl -sf http://localhost:4000/health
# Should return: {"status":"healthy"}

# Test authentication
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://localhost:4000/v1/models
# Should return model list (empty for now)
```

**Grafana**:
```bash
# Check health
curl -sf http://localhost:3000/api/health
# Should return: {"database":"ok"}

# Login to UI
firefox http://localhost:3000
# Username: admin
# Password: (from GRAFANA_ADMIN_PASSWORD in .env)

# Verify Prometheus datasource
# Navigate to: Configuration → Data Sources
# Should see: Prometheus (default, working)
```

### Step 3: Phase 1 Checkpoint

```bash
# Run tests
./test_deployment.sh | grep "PHASE 1"

# Should show:
# ✓ PASS Prometheus health
# ✓ PASS GPU Exporter metrics
# ✓ PASS Grafana health
# ✓ PASS PostgreSQL connection
# ✓ PASS LiteLLM health

# Check running services
docker compose --profile phase1 ps

# All services should show "Up (healthy)"
```

**Troubleshooting Phase 1**:

| Issue | Solution |
|-------|----------|
| Prometheus not starting | Check port 9090 availability: `sudo lsof -i :9090` |
| GPU Exporter no metrics | Verify nvidia-smi works: `nvidia-smi` |
| PostgreSQL init failed | Check logs: `docker logs llm-postgres` |
| LiteLLM connection error | Verify PostgreSQL is healthy first |
| Grafana datasource error | Wait 30s for Prometheus, then refresh |

---

## Phase 2: RAG & Automation

**Goal**: Deploy databases for RAG pipelines

**Duration**: 10-15 minutes

**Services**:
- Qdrant (vector database)
- pgvector (PostgreSQL vector extension)
- MongoDB (document store)
- Redis (cache)

### Step 1: Start Data Services

```bash
# Deploy Phase 2
./deploy.sh phase2

# Or manually:
docker compose --profile phase2 up -d

# Watch logs
docker compose logs -f qdrant pgvector mongodb redis
```

### Step 2: Verify Data Services

**Qdrant**:
```bash
# Check health
curl -sf http://localhost:6333/healthz
# Should return: {"status":"ok"}

# Check collections
curl -s http://localhost:6333/collections | jq
# Should show empty collections list

# View dashboard
firefox http://localhost:6333/dashboard

# Create test collection
curl -X PUT http://localhost:6333/collections/test \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 768, "distance": "Cosine"}}'
# Should return: {"result":true}

# Verify
curl -s http://localhost:6333/collections | jq '.result.collections[].name'
# Should show: "test"
```

**pgvector**:
```bash
# Test connection
docker exec llm-pgvector pg_isready -U llmuser -d vectors
# Should output: accepting connections

# Check vector extension
docker exec llm-pgvector psql -U llmuser -d vectors \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname='vector';"
# Should show: vector | 0.5.1 (or similar)

# Check tables
docker exec llm-pgvector psql -U llmuser -d vectors \
  -c "\dt"
# Should list: document_embeddings, documents

# Test vector operations
docker exec llm-pgvector psql -U llmuser -d vectors \
  -c "SELECT '[1,2,3]'::vector <-> '[4,5,6]'::vector as distance;"
# Should return a distance value
```

**MongoDB**:
```bash
# Test connection
docker exec llm-mongodb mongosh \
  -u admin -p "$MONGO_PASSWORD" \
  --eval "db.adminCommand('ping')"
# Should return: { ok: 1 }

# List databases
docker exec llm-mongodb mongosh \
  -u admin -p "$MONGO_PASSWORD" \
  --eval "show dbs"
# Should show: admin, config, rag_documents

# Create test document
docker exec llm-mongodb mongosh \
  -u admin -p "$MONGO_PASSWORD" \
  rag_documents \
  --eval 'db.test.insertOne({name: "test", timestamp: new Date()})'
# Should return: acknowledged: true
```

**Redis**:
```bash
# Test connection
docker exec llm-redis redis-cli -a "$REDIS_PASSWORD" ping
# Should return: PONG

# Set and get test key
docker exec llm-redis redis-cli -a "$REDIS_PASSWORD" SET test "hello"
docker exec llm-redis redis-cli -a "$REDIS_PASSWORD" GET test
# Should return: "hello"

# Check memory usage
docker exec llm-redis redis-cli -a "$REDIS_PASSWORD" INFO memory | grep used_memory_human
# Should show current memory usage
```

### Step 3: Phase 2 Checkpoint

```bash
# Run tests
./test_deployment.sh | grep "PHASE 2"

# Should show:
# ✓ PASS Qdrant health
# ✓ PASS pgvector connection
# ✓ PASS MongoDB connection
# ✓ PASS Redis connection

# Check all data services
docker compose --profile phase2 ps
```

**Integration Test**:
```bash
# Test complete RAG workflow (simplified)

# 1. Create embedding (mock data)
EMBEDDING="[$(python3 -c 'import random; print(",".join(str(random.random()) for _ in range(768)))'))]"

# 2. Store in Qdrant
curl -X PUT http://localhost:6333/collections/test/points \
  -H "Content-Type: application/json" \
  -d "{\"points\":[{\"id\":1,\"vector\":$EMBEDDING,\"payload\":{\"text\":\"test document\"}}]}"

# 3. Search Qdrant
curl -X POST http://localhost:6333/collections/test/points/search \
  -H "Content-Type: application/json" \
  -d "{\"vector\":$EMBEDDING,\"limit\":1}"
# Should return the test document

# 4. Store metadata in MongoDB
docker exec llm-mongodb mongosh \
  -u admin -p "$MONGO_PASSWORD" \
  rag_documents \
  --eval 'db.documents.insertOne({doc_id: 1, text: "test document"})'

# Success! RAG pipeline infrastructure is working
```

---

## Phase 3: Monitoring & User Access

**Goal**: Deploy LLMs and embedding services

**Duration**: 30-120 minutes (depends on model downloads)

**Services**:
- Embeddings (multi-model service)
- Primary GPT-OSS (120B persistent)
- Primary Qwen3-Omni
- Secondary DeepSeek-V2

**⚠️ IMPORTANT**: This phase involves large downloads (400GB+)

### Step 1: Build Custom Images

```bash
# Build embedding service (5-10 minutes)
docker compose build embeddings

# Build vLLM image (15-20 minutes, compiles CUDA kernels)
docker compose build primary_qwen3_vl

# Build playground (20-25 minutes)
docker compose build playground

# Verify images
docker images | grep -E "embeddings|vllm|playground"
```

### Step 2: Start Embedding Service

```bash
# Start embeddings
docker compose up -d embeddings

# Watch logs
docker logs -f embeddings-service

# Wait for "🎯 Embedding service ready"
# Press Ctrl+C when ready

# Test health
curl -sf http://localhost:8010/health | jq
# Should show available models

# Test embedding generation
curl -X POST http://localhost:8010/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic", "input": ["test text"]}'
# Should return embedding vector

# If models not preloaded, first request will be slow (5-30s)
# Subsequent requests will be fast (<200ms)
```

### Step 3: Start Primary Models

**GPT-OSS 120B**:
```bash
# Start service
docker compose up -d primary_gpt_oss

# THIS WILL:
# 1. Start Ollama server (~10s)
# 2. Check if model exists
# 3. Download if missing (~196GB, 30-60 minutes on fast connection)
# 4. Load into VRAM (~5 minutes)

# Monitor logs in real-time
docker logs -f primary-gpt-oss

# Look for:
# "✅ Ollama server ready"
# "📥 Pulling model: gpt-oss:120b" (if downloading)
# "✅ Model loaded and persistent in VRAM"

# Check progress
docker exec primary-gpt-oss ollama list
# Will show model once downloaded

# Test API
curl -sf http://localhost:11601/api/tags | jq
# Should list gpt-oss:120b

# Test generation
curl -X POST http://localhost:11601/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss:120b",
    "prompt": "What is 2+2?",
    "stream": false
  }' | jq '.response'
# Should return answer

# Check GPU usage
nvidia-smi
# GPUs 0,2 should show high memory usage (~60GB each)
```

**Qwen3-Omni**:
```bash
# Start service
docker compose up -d primary_qwen3_vl

# THIS WILL:
# 1. Start vLLM server (~10s)
# 2. Download model from HuggingFace (~238GB, 40-90 minutes)
# 3. Load into VRAM (~10-15 minutes)
# 4. Initialize tensor parallelism (~2 minutes)

# Monitor logs
docker logs -f primary-qwen3-vl

# Look for:
# "Loading safetensors checkpoint"
# "Loading model weights"
# "Adding prefix space to tokenizer"
# "Profiling memory"
# "Uvicorn running on http://0.0.0.0:8000"

# This is a LONG process, be patient!

# Check progress (in another terminal)
docker exec primary-qwen3-vl ls -lh /root/.cache/huggingface/hub/
# Will show downloaded files

# Once ready, test API
curl -sf http://localhost:8001/health
# Should return: {"status":"ok"}

curl -sf http://localhost:8001/v1/models | jq
# Should list qwen3-vl-235b

# Test generation
curl -X POST http://localhost:8001/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-vl-235b",
    "prompt": "Explain quantum computing in one sentence.",
    "max_tokens": 50
  }' | jq '.choices[0].text'

# Check GPU usage
nvidia-smi
# GPUs 4,6 should show high memory usage (~79GB each)
```

### Step 4: Start Secondary Models

**DeepSeek-V2**:
```bash
# Start service
docker compose up -d secondary_deepseek

# Monitor logs
docker logs -f secondary_deepseek

# Look for:
# "✅ Ollama server ready"
# "✅ Model already downloaded: deepseek-r1:671b-0528-q4_K_M"
# "⏸️  Model ready for on-demand loading"

# Model is downloaded but NOT loaded yet
# First request will trigger loading (10-30s)

# Test
curl -X POST http://localhost:11603/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1:671b-0528-q4_K_M",
    "prompt": "Hello",
    "stream": false
  }'

# First request: ~30s (loading)
# Subsequent requests: <1s

# Model will auto-unload after 600s idle
```

### Step 5: Register Models with LiteLLM

Models should auto-register, but verify:

```bash
# Check registered models
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://localhost:4000/v1/models | jq '.data[].id'

# Should show:
# "gpt-oss-120b"
# "qwen3-vl-235b"
# "deepseek-r1-671b"
# "nomic-embed"
# "stella-embed"

# If missing, restart LiteLLM
docker compose restart litellm

# Wait 30s, check again
```

### Step 6: Test via LiteLLM Gateway

```bash
# Test primary model
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "What is 2+2?"}]
  }' | jq '.choices[0].message.content'

# Test vision model
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-vl-235b",
    "messages": [{"role": "user", "content": "Describe AI in one sentence."}]
  }' | jq '.choices[0].message.content'

# Test embeddings
curl -X POST http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed",
    "input": "test text"
  }' | jq '.data[0].embedding | length'
# Should return: 768 (embedding dimension)
```

### Step 7: Phase 3 Checkpoint

```bash
# Run tests
./test_deployment.sh | grep "PHASE 3"

# Should show:
# ✓ PASS Embeddings service health
# ✓ PASS GPT-OSS API
# ✓ PASS Qwen3-VL API (if loaded)
# ✓ PASS DeepSeek API
# ✓ PASS LiteLLM lists models

# Check GPU usage
nvidia-smi

# Should show:
# GPUs 0,2: High usage (GPT-OSS)
# GPUs 4,6: High usage (Qwen3-Omni)
# GPU 0: Some usage (embeddings)

# Check VRAM usage
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**Troubleshooting Phase 3**:

| Issue | Solution |
|-------|----------|
| Model download fails | Check HF_TOKEN, check internet, retry |
| OOM (out of memory) | Check no other processes using GPU |
| vLLM won't start | Check logs for CUDA errors, verify drivers |
| Slow inference | Check GPU utilization with nvidia-smi |
| LiteLLM can't reach model | Check docker network, restart litellm |

---

## 

**Goal**: Deploy user-facing applications

**Duration**: 10-15 minutes

**Services**:
- OpenWebUI (chat interface)
- n8n (workflow automation)
- Playground (experimentation)

### Step 1: Start UI Services

```bash
# Deploy Phase 4
./deploy.sh phase4

# Or manually:
docker compose --profile phase4 up -d

# Watch logs
docker compose logs -f openwebui n8n playground
```

### Step 2: Configure OpenWebUI

```bash
# Wait for service to be ready
curl -sf http://localhost:5151
# Should return HTML

# Open in browser
firefox http://localhost:5151

# First-time setup:
# 1. Create admin account
#    Email: admin@example.com
#    Password: (choose secure password)
#    Name: Admin

# 2. Configure models
#    Settings → Connections
#    OpenAI API: http://litellm:4000/v1
#    API Key: (your LITELLM_MASTER_KEY)

# 3. Test chat
#    Select model: gpt-oss-120b
#    Send message: "Hello, how are you?"

# Should receive response from GPT-OSS
```

### Step 3: Configure n8n

```bash
# Access n8n
firefox http://localhost:5678

# Login
# Username: admin
# Password: (from N8N_PASSWORD in .env)

# Create test workflow:
# 1. Add "Webhook" node (trigger)
# 2. Add "HTTP Request" node
#    URL: http://litellm:4000/v1/chat/completions
#    Method: POST
#    Headers: Authorization: Bearer {LITELLM_MASTER_KEY}
#    Body:
#    {
#      "model": "gpt-oss-120b",
#      "messages": [{"role": "user", "content": "{{$json.message}}"}]
#    }
# 3. Add "Set" node (format response)
# 4. Save workflow

# Test webhook:
curl -X POST http://localhost:5678/webhook-test/your-webhook-id \
  -H "Content-Type: application/json" \
  -d '{"message": "What is AI?"}'

# Should return LLM response
```

### Step 4: Test Playground

```bash
# Enter playground
docker exec -it user-playground bash

# Should see welcome message with instructions

# Test Ollama
ollama list
# Should show installed models

# Pull test model
ollama pull llama2:7b

# Run model
ollama run llama2:7b "What is 2+2?"

# Test vLLM
python3 -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-hf \
  --port 8000 &

# Wait for startup (~2 minutes)

# Test API
curl http://localhost:8000/v1/models

# Exit
exit
```

### Step 5: Phase 4 Checkpoint

```bash
# Run tests
./test_deployment.sh | grep "PHASE 4"

# Check all services
docker compose ps

# All should be "Up (healthy)"
```

---

## Post-Deployment

### 1. Complete System Test

```bash
# Run full test suite
./test_deployment.sh

# Should show all tests passing

# View summary
docker compose ps
docker compose stats --no-stream

# Check disk usage
du -sh /mnt/ai8_arch/*
```

### 2. Set Up Monitoring Dashboards

```bash
# Access Grafana
firefox http://localhost:3000

# Import GPU dashboard
# 1. Navigate to: Dashboards → Import
# 2. Upload: monitoring/grafana/dashboards/gpu-dashboard.json
# 3. Select datasource: Prometheus
# 4. Click Import

# View GPU metrics
# Should see:
# - GPU Utilization (%)
# - VRAM Usage
# - Temperature
# - Power Usage
```

### 3. Configure Alerts (Optional)

```bash
# Edit Grafana alert rules
# Navigate to: Alerting → Alert rules

# Example: High GPU Temperature
# Condition: nvidia_gpu_temperature_celsius > 85
# Action: Log to console (or email/Slack if configured)
```

### 4. Document Your Setup

```bash
# Create site-specific README
cat > /mnt/ai8_arch/SITE_README.md <<EOF
# AI8 Architecture - Site Configuration

## Server Details
- Hostname: $(hostname)
- IP Address: $(hostname -I | awk '{print $1}')
- GPU Count: $(nvidia-smi --query-gpu=count --format=csv,noheader)
- Total VRAM: $(nvidia-smi --query-gpu=memory.total --format=csv,noheader | awk '{sum+=$1} END {print sum/1024 "GB"}')

## Deployment Date
- $(date)

## Deployed Models
$(docker compose ps --services | grep -E "primary|secondary|embeddings")

## Access URLs
- OpenWebUI: http://$(hostname -I | awk '{print $1}'):5151
- LiteLLM API: http://$(hostname -I | awk '{print $1}'):4000
- Grafana: http://$(hostname -I | awk '{print $1}'):3000

## Credentials
- LiteLLM Master Key: (in .env)
- Grafana Admin: admin / (in .env)
- n8n Admin: admin / (in .env)

## Maintenance Schedule
- Model updates: Monthly
- Log rotation: Weekly (automated)
- Backup: (configure as needed)

## Contact
- Admin: $(whoami)@$(hostname)
- Emergency: (add contact info)
EOF

# Secure the file
chmod 600 /mnt/ai8_arch/SITE_README.md
```

### 5. Backup Configuration

```bash
# Create backup script
cat > /mnt/ai8_arch/backup_config.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/mnt/ai8_arch/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup configurations
cp .env "$BACKUP_DIR/"
cp docker-compose.yaml "$BACKUP_DIR/"
cp -r config/ "$BACKUP_DIR/"
cp -r scripts/ "$BACKUP_DIR/"
cp -r monitoring/ "$BACKUP_DIR/"

# Backup database configs (not data)
docker exec llm-postgres pg_dumpall -U llmuser --roles-only > "$BACKUP_DIR/postgres_roles.sql"

echo "Backup saved to: $BACKUP_DIR"
EOF

chmod +x /mnt/ai8_arch/backup_config.sh

# Run backup
./backup_config.sh
```

---

## Maintenance

### Regular Maintenance Tasks

**Daily**:
```bash
# Check service health
docker compose ps
./test_deployment.sh

# Monitor GPU usage
nvidia-smi

# Check disk space
df -h /mnt
```

**Weekly**:
```bash
# Update images (if needed)
docker compose pull

# Clean up unused data
docker system prune -f

# Check logs for errors
docker compose logs --since 7d | grep -i error

# Verify backups
ls -lh /mnt/ai8_arch/backups/
```

**Monthly**:
```bash
# Update models
docker exec primary-gpt-oss ollama pull gpt-oss:120b

# Update system packages
sudo apt update && sudo apt upgrade

# Review and rotate logs
find /mnt/ai8_arch/logs -type f -mtime +30 -delete

# Full backup
./backup_config.sh
tar -czf /backup/ai8_arch_$(date +%Y%m%d).tar.gz /mnt/ai8_arch/backups/
```

### Updating Services

**Update LiteLLM Config**:
```bash
# Edit config
nano /mnt/ai8_arch/config/litellm_config.yaml

# Reload
./scripts/reload_config.sh

# Or restart
docker compose restart litellm
```

**Update Model in Service**:
```bash
# Example: Update secondary model
docker compose stop secondary_deepseek

# Edit docker-compose.yaml to change model name

# Restart
docker compose up -d secondary_deepseek

# Models download automatically if missing
```

**Scale Services**:
```bash
# Add more instances (future enhancement)
docker compose up -d --scale secondary_deepseek=2

# Note: Requires load balancer configuration
```

### Monitoring & Debugging

**View Logs**:
```bash
# All services
docker compose logs -f

# Specific service
docker logs -f primary-gpt-oss

# Tail last 100 lines
docker logs --tail 100 embeddings-service

# Since specific time
docker logs --since 2025-01-11T04:00:00 litellm
```

**Check Resource Usage**:
```bash
# Real-time stats
docker compose stats

# GPU usage
watch -n 1 nvidia-smi

# Disk I/O
iostat -x 1

# Network
iftop
```

**Debug Container Issues**:
```bash
# Enter container
docker exec -it <container> bash

# Check environment
docker exec <container> env

# View processes
docker exec <container> ps aux

# Check network
docker exec <container> ping litellm

# View container config
docker inspect <container>
```

---

## Rollback Procedures

### Rollback to Previous Configuration

```bash
# Stop services
docker compose down

# Restore from backup
BACKUP_DATE="20250111_040000"  # Change to your backup
cp /mnt/ai8_arch/backups/$BACKUP_DATE/.env .env
cp /mnt/ai8_arch/backups/$BACKUP_DATE/docker-compose.yaml docker-compose.yaml
cp -r /mnt/ai8_arch/backups/$BACKUP_DATE/config/* config/

# Restart
docker compose up -d
```

### Rollback Specific Service

```bash
# Stop service
docker compose stop <service>

# Pull previous image version
docker pull <image>:<previous-tag>

# Update docker-compose.yaml to use previous tag

# Restart
docker compose up -d <service>
```

---

## Disaster Recovery

### Complete System Rebuild

```bash
# 1. Stop all services
docker compose down -v  # WARNING: Deletes volumes!

# 2. Restore configurations
cp -r /backup/ai8_arch/latest/* /mnt/ai8_arch/

# 3. Rebuild images
docker compose build

# 4. Deploy phase by phase
./deploy.sh phase1
./deploy.sh phase2
./deploy.sh phase3
./deploy.sh phase4

# 5. Verify
./test_deployment.sh
```

### Data Recovery

**PostgreSQL**:
```bash
# Restore database
cat backup/postgres_dump.sql | docker exec -i llm-postgres psql -U llmuser -d litellm
```

**Qdrant**:
```bash
# Stop service
docker compose stop qdrant

# Restore data
sudo rm -rf /mnt/ai8_arch/data/qdrant/*
sudo tar -xzf backup/qdrant_data.tar.gz -C /mnt/ai8_arch/data/qdrant/

# Restart
docker compose up -d qdrant
```

**MongoDB**:
```bash
# Restore database
docker exec -i llm-mongodb mongorestore --archive < backup/mongodb_dump.archive
```

---

## Next Steps

After successful deployment:

1. ✅ Complete [Post-Deployment](#post-deployment) checklist
2. ✅ Set up [Monitoring](#monitoring--debugging)
3. ✅ Configure [Alerts](#configure-alerts-optional)
4. ✅ Read [RAG_SETUP.md](RAG_SETUP.md) for building RAG pipelines
5. ✅ Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
6. ✅ Explore [API_REFERENCE.md](API_REFERENCE.md) for API usage

**Questions?** See [README.md](../README.md#support) for support channels.
```