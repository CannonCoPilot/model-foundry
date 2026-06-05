# AI8 Architecture - Quick Start

## Prerequisites Complete
✅ Directory structure set up
✅ Existing models organized
✅ GPU drivers installed
✅ Docker + Docker Compose installed

## Deployment Steps

### 1. Configure Environment
```bash
cd /mnt/ai8_arch

# Copy and edit environment file
cp .env.template .env
nano .env

# Required changes:
# - HF_TOKEN=your_token_here
# - POSTGRES_PASSWORD=secure_password
# - LITELLM_MASTER_KEY=sk-secure-key
# - Other passwords as needed

# Secure the file
chmod 600 .env
```

### 2. Deploy Phase by Phase

#### Option A: Deploy All at Once
```bash
./deploy.sh all
```

#### Option B: Deploy Incrementally
```bash
# Phase 1: Foundation (5-10 minutes)
./deploy.sh phase1

# Test Phase 1
./test_deployment.sh

# Phase 2: Data Layer (5 minutes)
docker compose --profile phase2 up -d
./test_deployment.sh

# Phase 3: Models (30+ minutes for downloads)
docker compose build embeddings primary_qwen3_vl playground
docker compose --profile phase3 up -d

# Phase 4: User Interfaces (5 minutes)
docker compose --profile phase4 up -d
```

### 3. Verify Deployment
```bash
./test_deployment.sh
```

### 4. Access Services
- **OpenWebUI**: http://localhost:5151
- **n8n**: http://localhost:5678
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **LiteLLM**: http://localhost:4000

## Common Commands

```bash
# View all services
docker compose ps

# View logs
docker compose logs -f
docker logs -f <container_name>

# Restart service
docker compose restart <service_name>

# Stop all
docker compose down

# Check GPU usage
nvidia-smi
watch -n 1 nvidia-smi
```

## Troubleshooting

### Container won't start
```bash
docker logs <container_name>
docker compose config
```

### Out of memory
```bash
docker system prune -a
nvidia-smi
```

### Model not loading
```bash
docker exec <container> ollama list
docker exec <container> curl http://localhost:11434/api/tags
```

## Next Steps
1. Create account in OpenWebUI
2. Test model generation
3. Configure n8n workflows
4. Set up monitoring dashboards
5. Write RAG scripts using database connections
```