# AI8 Architecture - Troubleshooting Guide

**Version:** 1.0.0  
**Last Updated:** 2025-01-11  
**Author:** CannonCoPilot

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Issues](#common-issues)
3. [Service-Specific Issues](#service-specific-issues)
4. [Performance Issues](#performance-issues)
5. [Recovery Procedures](#recovery-procedures)
6. [Debug Toolkit](#debug-toolkit)

---

## Quick Diagnostics

### Automated Health Check

```bash
cd /mnt/ai8_arch

# Run full test suite
./test_deployment.sh

# Check specific phase
./test_deployment.sh | grep "PHASE 1"

# View service status
docker compose ps

# Check GPU status
nvidia-smi

# View recent errors
docker compose logs --since 1h | grep -i error
```

### System Health Indicators

```bash
# Check all services are running
docker compose ps --filter "status=running" | wc -l
# Should match total services count

# Check for restarts (indicates crashes)
docker compose ps --format "table {{.Name}}\t{{.Status}}"
# Look for "Restarting" or recent "Up" times

# Check disk space
df -h /mnt | grep -v tmpfs
# Need >100GB free for operations

# Check memory
free -h
# Available should be >10GB

# Check GPU availability
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv
```

---

## Common Issues

### Issue: Container Won't Start

**Symptoms**:
- Container shows "Exited (1)" in `docker compose ps`
- Service immediately crashes after starting

**Diagnosis**:
```bash
# View container logs
docker logs <container_name>

# Check last 50 lines
docker logs --tail 50 <container_name>

# Follow logs in real-time
docker logs -f <container_name>
```

**Common Causes & Solutions**:

**1. Port Already in Use**
```bash
# Check what's using the port
sudo lsof -i :4000  # Replace with your port

# Solution: Stop conflicting service or change port
sudo systemctl stop <conflicting_service>
# OR edit docker-compose.yaml to use different port
```

**2. Missing Environment Variable**
```bash
# Check if .env file exists
ls -la .env

# Verify required variables
source .env
echo $HF_TOKEN
echo $POSTGRES_PASSWORD

# Solution: Add missing variables to .env
nano .env
```

**3. Permission Issues**
```bash
# Check directory permissions
ls -ld /mnt/ai8_arch/data/*

# Solution: Fix permissions
sudo chown -R $(id -u):$(id -g) /mnt/ai8_arch/data/
chmod -R 755 /mnt/ai8_arch/data/
```

**4. Docker Network Issues**
```bash
# Inspect network
docker network inspect llm-network

# Solution: Recreate network
docker compose down
docker network prune -f
docker compose up -d
```

---

### Issue: "CUDA Out of Memory" (OOM)

**Symptoms**:
- Container starts but crashes during model loading
- Logs show: "CUDA out of memory" or "RuntimeError: Out of memory"

**Diagnosis**:
```bash
# Check GPU memory usage
nvidia-smi

# Check which processes are using GPU
nvidia-smi pmon

# Check specific GPU details
nvidia-smi -q -d MEMORY -i 0  # GPU 0
```

**Solutions**:

**1. Stop Unnecessary Services**
```bash
# Stop secondary models
docker compose stop secondary_deepseek-v2 secondary_llava-v1.6-mistral-7b

# Free up GPU memory
docker compose restart primary_gpt_oss
```

**2. Reduce Model Size**
```bash
# Use quantized versions
# Edit docker-compose.yaml:
# Change: gpt-oss:120b
# To: gpt-oss:120b-q4_K_M  (smaller, quantized)

docker compose up -d primary_gpt_oss
```

**3. Adjust GPU Memory Utilization**
```bash
# Edit vLLM service in docker-compose.yaml
# Change: --gpu-memory-utilization 0.95
# To: --gpu-memory-utilization 0.85

docker compose up -d primary_qwen3_omni
```

**4. Increase GPU Allocation**
```bash
# If model needs more GPUs, edit docker-compose.yaml
# Change: device_ids: [\'0\',\'2\',\'4\',\'6\']
# To: device_ids: ['2','3','4','5']
```

---

### Issue: Slow Model Inference

**Symptoms**:
- Requests take >10 seconds
- Low tokens/second rate
- API timeouts

**Diagnosis**:
```bash
# Check GPU utilization
watch -n 1 nvidia-smi
# Should show 80-100% GPU Utilization during inference

# Check model status
curl http://localhost:11601/api/ps
# Shows running models

# Check LiteLLM metrics
curl http://localhost:4000/metrics | grep latency

# Test direct model endpoint
time curl -X POST http://localhost:11601/api/generate \
  -d '{"model":"gpt-oss:120b","prompt":"Hi","stream":false}'
```

**Common Causes & Solutions**:

**1. Model Not Loaded (Cold Start)**
```bash
# Secondary models load on first request (10-30s)
# This is expected behavior

# Solution: Use primary models for low-latency
# Or preload secondary model:
curl -X POST http://localhost:11603/api/generate \
  -d '{"model":"deepseek-v2","prompt":"warmup","keep_alive":600}'
```

**2. CPU Bottleneck**
```bash
# Check CPU usage
htop

# Solution: Reduce concurrent requests
# Edit litellm_config.yaml:
max_parallel_requests: 50  # Reduce from 100
```

**3. Disk I/O Bottleneck**
```bash
# Check disk I/O
iostat -x 1

# Solution: Move to faster storage (NVMe)
# Or increase system cache:
sudo sysctl -w vm.vfs_cache_pressure=50
```

**4. Network Latency**
```bash
# Test local network
ping litellm
# Should be <1ms

# Test from external
ping <server_ip>

# Solution: Use localhost URLs when on same machine
# Change: http://server_ip:4000
# To: http://localhost:4000
```

---

### Issue: Model Download Fails

**Symptoms**:
- "Failed to pull model" in logs
- Download stalls at XX%
- Connection timeout errors

**Diagnosis**:
```bash
# Check internet connectivity
ping huggingface.co
ping ollama.ai

# Check HuggingFace token
echo $HF_TOKEN
# Should be ~60 characters starting with "hf_"

# Test token manually
curl -H "Authorization: Bearer $HF_TOKEN" \
  https://huggingface.co/api/models/meta-llama/Llama-2-7b-hf
# Should return model info, not 401 error

# Check disk space
df -h /mnt
# Need >500GB for large models
```

**Solutions**:

**1. Invalid/Expired HuggingFace Token**
```bash
# Get new token from https://huggingface.co/settings/tokens
# Update .env
nano .env
# Set: HF_TOKEN=hf_your_new_token_here

# Restart service
docker compose restart primary_qwen3_omni
```

**2. Network Timeout**
```bash
# Increase timeout in Dockerfile.vllm or manually retry
docker compose restart primary_qwen3_omni

# Or download manually and mount:
# On host:
cd /mnt/ai8_arch/models/huggingface/hub
huggingface-cli download Qwen/Qwen3-omni

# Restart service
docker compose restart primary_qwen3_omni
```

**3. Disk Full During Download**
```bash
# Clean up space
docker system prune -a -f
rm -rf /mnt/ai8_arch/models/huggingface/hub/.locks

# Resume download
docker compose restart primary_qwen3_omni
```

**4. Ollama Download Issues**
```bash
# Enter container and retry manually
docker exec -it primary-gpt-oss bash
ollama pull gpt-oss:120b

# If fails, try different mirror (if available)
# Or download from Ollama library directly
```

---

### Issue: Database Connection Errors

**Symptoms**:
- "Connection refused" errors
- "Role does not exist"
- "Database does not exist"

**Diagnosis**:
```bash
# Check PostgreSQL is running
docker compose ps postgres
# Should show "Up (healthy)"

# Test connection
docker exec llm-postgres pg_isready -U llmuser -d litellm

# Check logs
docker logs llm-postgres | tail -50

# Try manual connection
docker exec -it llm-postgres psql -U llmuser -d litellm
# Should get psql prompt
```

**Solutions**:

**1. Database Not Ready**
```bash
# Wait for health check to pass
docker compose ps postgres
# Wait until "Up (healthy)"

# If stuck, restart
docker compose restart postgres
sleep 30
docker compose ps postgres
```

**2. Wrong Credentials**
```bash
# Check environment variables
docker exec postgres env | grep POSTGRES

# Verify against .env
source .env
echo $POSTGRES_USER
echo $POSTGRES_PASSWORD

# Update if mismatch
nano .env
docker compose up -d postgres
```

**3. Database Not Created**
```bash
# Check if init script ran
docker logs llm-postgres | grep "initialization"

# If not, volume has old data
# Backup and recreate:
docker compose down
sudo mv /mnt/ai8_arch/data/postgres /mnt/ai8_arch/data/postgres.bak
docker compose up -d postgres
```

**4. Connection String Issues**
```bash
# Verify connection string format
# Should be: postgresql://user:pass@host:port/database

# Test with psql
docker exec -it llm-postgres \
  psql "postgresql://llmuser:password@localhost:5432/litellm"

# Update in service config if wrong
```

---

### Issue: LiteLLM Can't Reach Models

**Symptoms**:
- "Connection refused" when calling models through LiteLLM
- LiteLLM health OK but `/v1/models` shows no models

**Diagnosis**:
```bash
# Check LiteLLM can reach backends
docker exec llm-gateway curl http://primary-gpt-oss:11434/api/tags
# Should return model list

# Check network connectivity
docker exec llm-gateway ping primary-gpt-oss
# Should respond

# Check model service health
curl http://localhost:11601/api/tags
# Should work from host
```

**Solutions**:

**1. Service Name Resolution**
```bash
# Verify all services in same network
docker network inspect llm-network

# Should list all services

# If service missing, restart it
docker compose restart <service>
```

**2. Wrong URL in Config**
```bash
# Check litellm_config.yaml
cat config/litellm_config.yaml | grep api_base

# Should use container names, not localhost:
# Correct: http://primary-gpt-oss:11434
# Wrong: http://localhost:11601

# Fix and reload
nano config/litellm_config.yaml
./scripts/reload_config.sh
```

**3. Model Service Not Ready**
```bash
# Check if model is loaded
curl http://localhost:11601/api/ps
# Should show running model

# Wait for model to load
docker logs -f primary-gpt-oss
# Look for "✅ Model loaded"
```

---

### Issue: High GPU Temperature

**Symptoms**:
- GPU temp >85°C
- Thermal throttling
- GPU fan at 100%

**Diagnosis**:
```bash
# Check GPU temperature
nvidia-smi --query-gpu=temperature.gpu --format=csv
# Should be <80°C under normal load

# Check fan speed
nvidia-smi --query-gpu=fan.speed --format=csv

# Monitor in real-time
watch -n 1 nvidia-smi
```

**Solutions**:

**1. Improve Airflow**
```bash
# Physical solutions:
# - Check server fans working
# - Clean dust from heatsinks
# - Ensure adequate rack spacing
# - Check room temperature (<25°C)
```

**2. Reduce GPU Load**
```bash
# Stop secondary models
docker compose stop secondary_deepseek-v2 secondary_llava-v1.6-mistral-7b

# Reduce concurrent requests
# Edit config/litellm_config.yaml:
max_parallel_requests: 20  # Reduce from 100
```

**3. Set Fan Speed (if supported)**
```bash
# Increase fan speed
sudo nvidia-smi -pl 250  # Reduce power limit (if needed)

# Or use nvidia-settings for manual fan control
```

**4. Alert on High Temp**
```bash
# In Grafana, create alert:
# nvidia_gpu_temperature_celsius > 85
# Action: Send notification, reduce load
```

---

## Service-Specific Issues

### Ollama Issues

**Issue: Model Keeps Unloading**
```bash
# Check keep_alive setting
docker exec <container> env | grep KEEP_ALIVE

# For persistent models, should be: -1
# For secondary models, default: 600 (10 minutes)

# Fix in docker-compose.yaml:
environment:
  - OLLAMA_KEEP_ALIVE=-1  # Never unload

docker compose up -d <service>
```

**Issue: "Model Not Found"**
```bash
# List available models
docker exec <container> ollama list

# If missing, pull it
docker exec <container> ollama pull <model_name>

# Check model name spelling
# Correct: gpt-oss:120b
# Wrong: gpt-oss:120B (case sensitive)
```

**Issue: Slow First Request**
```bash
# This is expected (cold start)
# Model loads into VRAM on first request

# To avoid, use persistent loading (primary models)
# Or pre-warm with dummy request:
curl -X POST http://localhost:11601/api/generate \
  -d '{"model":"gpt-oss:120b","prompt":"warmup","keep_alive":-1}'
```

---

### vLLM Issues

**Issue: "Model Not Supported"**
```bash
# Check vLLM logs
docker logs primary-qwen3-vl | grep -i "error"

# Some models require specific flags
# Add to docker-compose.yaml command:
--trust-remote-code  # For custom models
--max-model-len 4096  # Adjust context length
--dtype float16  # Or auto, bfloat16

docker compose up -d primary-qwen3_vl
```

**Issue: Tensor Parallelism Errors**
```bash
# Check GPU count matches tensor-parallel-size
nvidia-smi --query-gpu=count --format=csv
# Should be >= tensor-parallel-size value

# If mismatch, edit docker-compose.yaml:
--tensor-parallel-size 2  # Match available GPUs

docker compose up -d primary-qwen3_vl
```

**Issue: "PagedAttention Not Supported"**
```bash
# Some models don't support vLLM's optimizations
# Try with fallback:
# Add to command:
--enforce-eager  # Disable CUDA graphs

docker compose up -d primary-qwen3_vl
```

---

### Embedding Service Issues

**Issue: Wrong Embedding Dimensions**
```bash
# Check model dimensions
curl http://localhost:8010/models

# Common dimensions:
# nomic-embed-text-v1.5: 768
# mxbai-embed-large-v1: 1024

# If storing in vector DB, ensure dimension matches:
# Qdrant: {"vectors": {"size": 1024, ...}}
# pgvector: vector(1024)
```

**Issue: Embedding Service Slow**
```bash
# Check if HF models loaded
docker logs embeddings-service | grep "Loading HF model"

# First request loads model (5-30s)
# Subsequent requests should be fast (<200ms)

# Check GPU usage
nvidia-smi
# GPU 0 should show some usage

# If consistently slow, check batch size
# Edit scripts/embedding_service.py:
batch_size = 32  # Increase for better throughput
```

---

### Vector Database Issues

**Qdrant Issues**:

**Issue: Collection Not Found**
```bash
# List collections
curl http://localhost:6333/collections

# Create if missing
curl -X PUT http://localhost:6333/collections/my_collection \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 1024, "distance": "Cosine"}}'
```

**Issue: Search Returns Nothing**
```bash
# Check collection has points
curl http://localhost:6333/collections/my_collection

# Check vector dimension matches
# Query vector dimension must equal collection dimension

# Check distance metric
# Cosine: Best for normalized embeddings
# Euclidean: For absolute distances
```

**pgvector Issues**:

**Issue: Extension Not Found**
```bash
# Check extension enabled
docker exec llm-pgvector psql -U llmuser -d vectors \
  -c "SELECT extname FROM pg_extension WHERE extname='vector';"

# If missing, enable it
docker exec llm-pgvector psql -U llmuser -d vectors \
  -c "CREATE EXTENSION vector;"
```

**Issue: Index Not Being Used**
```bash
# Check if index exists
docker exec llm-pgvector psql -U llmuser -d vectors \
  -c "\d document_embeddings"

# Should show: document_embeddings_embedding_idx (hnsw)

# If missing, create it
docker exec llm-pgvector psql -U llmuser -d vectors \
  -c "CREATE INDEX ON document_embeddings USING hnsw (embedding vector_cosine_ops);"
```

---

## Performance Issues

### Optimization Checklist

**GPU Optimization**:
```bash
# 1. Check GPU utilization
nvidia-smi dmon -s u
# Target: >80% during inference

# 2. Enable CUDA graphs (vLLM)
# Already enabled by default

# 3. Use quantized models
# Q4_K_M: 4-bit quantization (~50% size reduction)
# Q8_0: 8-bit quantization (~25% size reduction)

# 4. Adjust batch sizes
# vLLM: --max-num-batched-tokens (increase for throughput)
# Ollama: OLLAMA_NUM_PARALLEL (default: 4)
```

**Memory Optimization**:
```bash
# 1. Use KV cache efficiently
# vLLM: --gpu-memory-utilization 0.90 (default: 0.90)

# 2. Reduce max sequence length
# vLLM: --max-model-len 4096 (if don't need longer)

# 3. Enable tensor parallelism
# vLLM: --tensor-parallel-size (spread across GPUs)
```

**Network Optimization**:
```bash
# 1. Use gRPC instead of HTTP (where supported)
# Qdrant: Port 6334 for gRPC

# 2. Enable HTTP/2
# LiteLLM: Already supports HTTP/2

# 3. Use connection pooling
# Redis: Connection pooling built-in
# PostgreSQL: Use PgBouncer (future enhancement)
```

---

## Recovery Procedures

### Service Recovery

**Quick Restart**:
```bash
# Restart single service
docker compose restart <service_name>

# Restart all services
docker compose restart

# Force recreate
docker compose up -d --force-recreate <service_name>
```

**Clean Restart**:
```bash
# Stop service
docker compose stop <service_name>

# Remove container
docker compose rm -f <service_name>

# Remove volumes (⚠️ DELETES DATA)
docker volume rm <volume_name>

# Recreate
docker compose up -d <service_name>
```

### Data Recovery

**Restore PostgreSQL**:
```bash
# Stop service
docker compose stop postgres

# Restore from backup
sudo rm -rf /mnt/ai8_arch/data/postgres/*
sudo tar -xzf /backup/postgres.tar.gz -C /mnt/ai8_arch/data/postgres/

# Restart
docker compose up -d postgres
```

**Restore Qdrant**:
```bash
docker compose stop qdrant
sudo rm -rf /mnt/ai8_arch/data/qdrant/*
sudo cp -r /backup/qdrant/* /mnt/ai8_arch/data/qdrant/
docker compose up -d qdrant
```

### Complete System Recovery

```bash
# 1. Stop all services
docker compose down

# 2. Backup current state
sudo tar -czf /backup/ai8_arch_$(date +%Y%m%d_%H%M%S).tar.gz \
  /mnt/ai8_arch/data /mnt/ai8_arch/.env

# 3. Reset to clean state
sudo rm -rf /mnt/ai8_arch/data/*
docker system prune -a -f

# 4. Deploy from scratch
./deploy.sh all

# 5. Restore data if needed
# (follow data recovery procedures above)
```

---

## Debug Toolkit

### Useful Commands

**Container Inspection**:
```bash
# View container details
docker inspect <container> | jq

# Check resource limits
docker inspect <container> | jq '.[0].HostConfig.Memory'

# View mounts
docker inspect <container> | jq '.[0].Mounts'

# Check environment
docker exec <container> env
```

**Network Debugging**:
```bash
# Test connectivity between containers
docker exec llm-gateway ping primary-gpt-oss

# Check DNS resolution
docker exec llm-gateway nslookup primary-gpt-oss

# View network details
docker network inspect llm-network

# Capture network traffic (if needed)
docker run --rm --net=container:<container> \
  nicolaka/netshoot tcpdump -i any -w /tmp/capture.pcap
```

**Performance Profiling**:
```bash
# CPU profiling
docker stats --no-stream <container>

# Memory profiling
docker exec <container> ps aux --sort=-%mem | head

# Disk I/O
docker exec <container> iostat -x 1

# GPU profiling
nvidia-smi pmon -s um -c 10
```

**Log Analysis**:
```bash
# Search logs for errors
docker logs <container> 2>&1 | grep -i "error\|exception\|fatal"

# Count errors per hour
docker logs <container> --since 24h | grep -i error | \
  awk '{print $1}' | uniq -c

# Filter by component
docker logs litellm | grep "model="

# Export logs
docker logs <container> > /tmp/container.log 2>&1
```

### Emergency Scripts

**Kill All GPU Processes**:
```bash
#!/bin/bash
# ⚠️ USE WITH CAUTION - Stops all GPU workloads

echo "Stopping all GPU processes..."
sudo nvidia-smi --gpu-reset

# Or selectively:
# sudo kill -9 $(nvidia-smi --query-compute-apps=pid --format=csv,noheader)

echo "GPU processes stopped"
nvidia-smi
```

**Force Clean Docker**:
```bash
#!/bin/bash
# ⚠️ NUCLEAR OPTION - Removes everything

echo "This will delete ALL Docker data. Continue? (yes/no)"
read -r response

if [ "$response" = "yes" ]; then
  docker compose down -v
  docker system prune -a -f --volumes
  docker network prune -f
  docker volume prune -f
  echo "Docker cleaned. Rebuild with: ./deploy.sh all"
fi
```

---

## Getting Help

### Information to Gather

When requesting help, include:

```bash
# 1. System information
uname -a
nvidia-smi --query-gpu=driver_version --format=csv,noheader
docker --version
docker compose version

# 2. Service status
docker compose ps

# 3. Recent logs
docker compose logs --tail 100 <service> > service.log

# 4. Resource usage
nvidia-smi > gpu_status.txt
df -h > disk_usage.txt
free -h > memory_usage.txt

# 5. Configuration
cat .env | sed 's/\(PASSWORD=\).*/\1***REDACTED***/' > env.txt
cat config/litellm_config.yaml > config.txt

# Attach these files when opening GitHub issue
```

### Support Channels

- **GitHub Issues**: https://github.com/CannonCoPilot/ai8-architecture/issues
- **Discussions**: https://github.com/CannonCoPilot/ai8-architecture/discussions
- **Documentation**: https://github.com/CannonCoPilot/ai8-architecture/wiki

---

**Remember**: Most issues are configuration-related. Check logs first!
```