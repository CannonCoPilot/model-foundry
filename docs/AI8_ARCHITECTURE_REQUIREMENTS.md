# AI8 Architecture - Comprehensive Project Requirements Document

**Version:** 1.0.0  
**Date:** 2025-01-15  
**Author:** CannonCoPilot  
**Status:** Production-Ready Implementation  
**Target Platform:** ai8 Server (8x NVIDIA H200 140GB GPUs)  
**Document Generated:** 2025-10-15 01:41:58 UTC

---

## Executive Summary

The AI8 Architecture is a production-grade, multi-model Large Language Model (LLM) infrastructure designed for the ai8 server equipped with 8x NVIDIA H200 140GB GPUs. The system provides a comprehensive, modular, and GPU-optimized environment for deploying multiple LLMs simultaneously, able to support RAG (Retrieval-Augmented Generation) and other common AI workflows, with GPU and Docker container monitoring, and user interfaces.

### Key Objectives

1. **Maximize GPU utilization** across 6x H200 GPUs (840GB total VRAM), leaving 2x H200 GPUs reserved for other wokloads
2. **Support concurrent deployment** of multiple LLMs with different performance tiers
3. **Provide unified API access** via OpenAI-compatible gateway
4. **Enable RAG pipelines** with vector databases and document stores
5. **Offer comprehensive monitoring** and observability
6. **Deliver user-friendly interfaces** for chat, workflows, and experimentation
7. **Support incremental, testable deployment** phases

### Target Users

- Data Scientists and ML Engineers
- Application Developers
- Research Teams
- Operations/DevOps Engineers

### System Capacity

- **Concurrent Users:** 2-10 (realistic sustained load)
- **Models Deployed:** 1 primary (persistent) + 4+ secondary (on-demand)
- **Storage Required:** 2TB minimum, 5TB recommended
- **Network Bandwidth:** 1Gbps minimum for model downloads
- **Deployment Time:** 5-15 minutes (not including new model downloads)

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Infrastructure Requirements](#2-infrastructure-requirements)
3. [Core Components](#3-core-components)
4. [Model Management](#4-model-management)
5. [Data Layer](#5-data-layer)
6. [Monitoring & Observability](#6-monitoring--observability)
7. [User Interfaces](#7-user-interfaces)
8. [API Specifications](#8-api-specifications)
9. [Deployment Strategy](#9-deployment-strategy)
10. [Security & Authentication](#10-security--authentication)
11. [Performance Requirements](#11-performance-requirements)
12. [Operational Procedures](#12-operational-procedures)
13. [Testing & Validation](#13-testing--validation)
14. [Documentation Requirements](#14-documentation-requirements)
15. [Future Enhancements](#15-future-enhancements)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER ACCESS LAYER                        │
│  OpenWebUI (Chat) │ n8n (Workflows) │ Grafana (Monitoring)      │
│  Port 5151        │ Port 5678       │ Port 3000                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              LITELLM API GATEWAY (Port 4000)                    │
│  • Unified OpenAI-compatible API                                │
│  • Model routing & load balancing                               │
│  • Authentication & rate limiting                               │
│  • Request transformation & fallback handling                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│  PRIMARY    │    │  SECONDARY  │    │ EMBEDDINGS  │
│  MODEL      │    │   MODELS    │    │  SERVICE    │
│  (Tier 1)   │    │  (Tier 2)   │    │             │
│  GPU #s 2,3 │    │  GPU #s 4-7 │    │   GPU 7     │
│  Persistent │    │  On-Demand  │    │  Multi-Model│
└──────┬──────┘    └───────┬─────┘    └────────┬────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    GPU RESOURCE POOL                            │
│  **Mandated Allocation:**                                       │
│  GPU 0, 2, 4, 6: Primary & Embedding Models (Strict, Exclusive) │
│  GPU 1, 3, 5, 7: Secondary Models & Other Tasks (Flexible)      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    DATA & STORAGE LAYER                         │
│  PostgreSQL │ Qdrant │ MongoDB │ Redis                           │
│  (Util DB)  │(Vector)│ (Docs)  │(Cache)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  MONITORING & METRICS                           │
│  Prometheus (Metrics) │ GPU Exporter │ Grafana (Dashboards)     │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

#### 1.2.1 Separation of Concerns

**Principle:** Each component has a single, well-defined responsibility.

| Layer | Responsibility | Components |
|-------|----------------|------------|
| **API Gateway** | Request routing, auth, transformation | LiteLLM |
| **Model Services** | Inference execution | Ollama, vLLM containers |
| **Data Layer** | Storage and retrieval | PostgreSQL, Qdrant, MongoDB, Redis |
| **Monitoring** | Observability without impacting inference | Prometheus, Grafana, GPU Exporter |

**Benefits:**
- Easy to replace individual components
- Clear debugging boundaries
- Independent scaling
- Simplified testing

#### 1.2.2 Resource Optimization

**Tiered Model Loading Strategy:**

| Tier | Purpose | Characteristics | Use Cases |
|------|---------|-----------------|-----------|
| **Tier 1 (Primary)** | Production workloads | Always in VRAM, <100ms TTFT, dedicated GPUs | Chat, real-time apps |
| **Tier 2 (Secondary)** | Specialized tasks | On-demand load (10-30s), 600s keepalive, shared GPUs | Batch processing, analysis |
| **Tier 3 (Embeddings)** | Vector generation | 60s keepalive, shared GPU 2 | RAG pipelines |
| **Tier 4 (Playground)** | User experimentation | 300s keepalive, GPUs 4-7 | Testing, development |

**GPU Sharing Strategy:**
- **Primary model:** Exclusive GPU allocation for guaranteed performance
- **Secondary models:** Share GPU pool, load on-demand
- **Memory Management:** Careful VRAM allocation to prevent OOM

**Example GPU Allocation:**
```
GPU 2: Primary GPT-OSS 120 (90GB) + Embeddings (5GB)
GPU 3: Primary GPT-OSS 120 (90GB) + Secondary slot (20GB available)
GPU 4: Secondary Qwen3-VL (60GB) + Secondary slot (80GB available)
GPU 5: Secondary Qwen3-VL (60GB) + Secondary slot (80GB available)
GPU 6: Secondary Qwen3-VL (60GB) + Secondary slot (80GB available)
GPU 7: Secondary Qwen3-VL (60GB) + Secondary slot (80GB available)
```

#### 1.2.3 Fault Tolerance

**Multi-Level Redundancy:**

1. **Health Checks:**
   - Docker healthchecks every 30-60s
   - Prometheus scrapes every 15s
   - Application-level health endpoints

2. **Auto-Recovery:**
   - `restart: unless-stopped` for all services
   - Automatic model reload on container restart
   - Database connection pooling with retries

3. **Fallback Routing:**
   ```yaml
   Request Flow:
     1. LiteLLM receives request for "gpt-oss-120b"
     2. Routes to primary-gpt-oss:11601
     3. If timeout/error → fallback to "deepseek-r1-671b"
     4. If all fail → return 503 with error context
   ```

4. **Data Persistence:**
   - All critical data on bind-mounted volumes
   - No use of anonymous volumes (data loss risk)
   - Regular backup procedures (see Operations)

#### 1.2.4 Developer Experience

**Basic API Interface:**
```python
# All models accessible via same interface
import openai

openai.api_base = "http://localhost:4000/v1"
openai.api_key = "your-key"

# Use any model
response = openai.ChatCompletion.create(
    model="gpt-oss",  # or qwen-vl, deepseek-671b, etc.
    messages=[{"role": "user", "content": "Hello"}]
)
```
**Unified API Interface:**
  The `litellm_config.yaml` file provides a unified interface for all models by allowing simplified, user-friendly aliases. This approach abstracts the underlying model names, making it easier to switch between models without changing the API calls.

**Interactive Tools:**
- Playground container with LangChain, transformers pre-installed
- SSH access to containers for debugging
- OpenWebUI for chat and model interaction
- n8n interface for workflow building and execution

**Documentation:**
- API reference with examples in Python, Bash, cURL
- Architecture diagrams and design rationale
- Troubleshooting guide with common issues
- Deployment guide with step-by-step instructions
- Comprehensive logging to `/mnt/ai8_arch/logs/`

---

## 2. Infrastructure Requirements

### 2.1 Hardware Requirements

#### 2.1.1 GPU Requirements

**Required Configuration:**
```yaml
GPU Model: NVIDIA H200 140GB
GPU Count: 8-2=6
Total VRAM: 640GB

Per-GPU Specifications:
  - CUDA Cores: 14,592
  - Tensor Cores: 456 (4th generation)
  - Memory Bandwidth: 3.35 TB/s
  - Memory Type: HBM3
  - TDP: 700W
  - CUDA Compute Capability: 9.0
```

#### 2.1.2 CPU & Memory Requirements

```yaml
CPU:
  Minimum: 32 cores (Intel Xeon or AMD EPYC)
  Recommended: 64+ cores
  Purpose: Model loading, data processing, system overhead

System RAM:
  Minimum: 128GB DDR5
  Recommended: 256GB DDR5
  Purpose: Model loading buffers, system cache, container overhead

Rationale:
  - Large models (120B+) require significant RAM during initial load
  - Model weights temporarily in RAM before GPU transfer
  - Multiple containers running simultaneously
  - OS and system services
```

#### 2.1.3 Storage Requirements

```yaml
Storage Type: Networked storage
  Minimum: 5TB
  Recommended: 50TB

Storage Breakdown:
  - Operating System: 100GB
  - Docker images: 50GB
  - Ollama models: 1,400GB (existing + new)
  - HuggingFace cache: 250GB (vLLM models)
  - Databases (PostgreSQL, Qdrant, MongoDB): 50GB initial
  - Logs: 10GB (with rotation)
  - Free space buffer: 500GB minimum

Mount Point: /mnt/ai8_arch
  - Must support bind mounts
```

#### 2.1.4 Network Requirements

```yaml
Internal Network:
  - 10Gbps+ Ethernet (container-to-container)
  - Low latency (<1ms for localhost)
  - Docker bridge network: 172.28.0.0/16

External Network:
  - 1Gbps+ Internet connection
  - Stable connection for model downloads
  - Bandwidth: 500GB/month minimum (model updates)

Ports Required:
  External Access (firewall rules needed):
    - 3000: Grafana (monitoring)
    - 4000: LiteLLM API (main interface)
    - 5151: OpenWebUI (chat)
    - 5678: n8n (workflows)
    - 9090: Prometheus (metrics)

  Internal Only (Docker network):
    - 5432: PostgreSQL
    - 8000: Chroma
    - 6333: Qdrant HTTP
    - 6334: Qdrant gRPC
    - 6379: Redis
    - 8010: Embeddings
    - 9835: GPU Exporter
    - 11601-11630: Ollama services
    - 27017: MongoDB
```

### 2.2 Software Requirements

#### 2.2.1 Operating System

```yaml
Primary Support:
  Distribution: Ubuntu 22.04 LTS (Jammy Jellyfish)
  Kernel: 5.15.0-91+ with CUDA support
  Architecture: x86_64 (amd64)

Un-Tested Alternatives:
  - Ubuntu 20.04 LTS (Focal Fossa)
  - Debian 11 (Bullseye)
  - Debian 12 (Bookworm)
  - RHEL 8/9 (with modifications to Docker install)

Not Supported:
  - Windows (no native Docker GPU support)
  - macOS (no NVIDIA GPU support)
  - ARM-based systems (incompatible binaries)

Verification:
  lsb_release -a
  # Should show: Ubuntu 22.04.x LTS
  
  uname -r
  # Should show: 5.15.0-xxx-generic or higher
```

#### 2.2.2 NVIDIA Stack

```yaml
NVIDIA Driver:
  Version Required: 530.30.02+
  CUDA Support: 12.1+
  Installation:
    sudo apt-get install nvidia-driver-530
    # Or use official NVIDIA installer
  
  Verification:
    nvidia-smi
    # Should display all 8 GPUs
    # CUDA Version: 12.1 or higher

CUDA Toolkit:
  Version: 12.1+
  Installation: Included with driver (runtime)
  Full toolkit (optional): 
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
    sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
    wget https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda-repo-ubuntu2204-12-1-local_12.1.0-530.30.02-1_amd64.deb
    sudo dpkg -i cuda-repo-ubuntu2204-12-1-local_12.1.0-530.30.02-1_amd64.deb
    sudo cp /var/cuda-repo-ubuntu2204-12-1-local/cuda-*-keyring.gpg /usr/share/keyrings/
    sudo apt-get update
    sudo apt-get -y install cuda

NVIDIA Container Toolkit:
  Version: Latest (2.13.0+)
  Installation:
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
  
  Verification:
    docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
    # Should display GPU info inside container
```

#### 2.2.3 Docker Environment

```yaml
Docker Engine:
  Version Required: 24.0.0+
  Installation (ONLY on new systems, not needed for current deployment):
    # Remove old versions
    sudo apt-get remove docker docker-engine docker.io containerd runc
    
    # Install prerequisites
    sudo apt-get update
    sudo apt-get install ca-certificates curl gnupg lsb-release
    
    # Add Docker GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Add repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    # Logout and login for group to take effect
  
  Verification:
    docker --version
    # Should show: Docker version 24.0.0 or higher
    
    docker compose version
    # Should show: Docker Compose version v2.20.0 or higher

Docker Configuration:
  File: /etc/docker/daemon.json
  Content:
    {
      "runtimes": {
        "nvidia": {
          "path": "nvidia-container-runtime",
          "runtimeArgs": []
        }
      },
      "default-runtime": "nvidia",
      "log-driver": "json-file",
      "log-opts": {
        "max-size": "100m",
        "max-file": "3"
      },
      "storage-driver": "overlay2",
      "data-root": "/var/lib/docker"
    }
  
  Apply:
    sudo systemctl restart docker
    sudo systemctl enable docker
```

#### 2.2.4 System Packages

```yaml
Required Packages:
  sudo apt-get update
  sudo apt-get install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    jq \
    htop \
    iotop \
    net-tools \
    dnsutils \
    build-essential \
    python3 \
    python3-pip

Optional (Recommended):
  sudo apt-get install -y \
    tmux \
    screen \
    iftop \
    nethogs \
    ncdu \
    tree \
    rsync \
    fail2ban \
    ufw

Python Packages (for host):
  pip3 install \
    docker \
    docker-compose \
    requests \
    pyyaml
```

### 2.3 File System Structure

**Base Directory:** `/mnt/ai8_arch`

**Complete Directory Tree:**
```
/mnt/ai8_arch/
├── .env.template                          # Environment template (REQUIRED)
├── .gitignore                             # Git ignore rules (REQUIRED)
│
├── command/                               # Command scripts
│
├── config/                                # Configuration files
│   └── litellm_config.yaml                # LiteLLM model routing (REQUIRED)
│
├── data/                                  # Persistent data (auto-created, gitignored)
│
├── deploy/
│   ├── AI8_ARCHITECTURE_REQUIREMENTS.md   # This file
│   ├── deploy.sh                          # Phased deployment script (REQUIRED)
│   ├── docker-compose-vllm.yaml           # Overall Docker architecture v1 (REQUIRED)
│   ├── docker-compose.yaml                # Overall Docker architecture v2 (REQUIRED)
│   ├── GITHUB_SETUP.md                    # Github setup guide
│   ├── QUICKSTART.md                      # Quick start guide (REQUIRED)
│   ├── README.md                          # Main documentation (REQUIRED)
│   ├── setup_directories.sh               # Initial directory setup (REQUIRED)
│   └── test_deployment.sh                 # Testing & validation (REQUIRED)
│
├── dockerfiles/                           # Custom Docker images
│   ├── Dockerfile.embeddings              # Embedding service (REQUIRED)
│   ├── Dockerfile.mcp                     # MCP server Dockerfile
│   ├── Dockerfile.playground              # User playground (REQUIRED)
│   ├── Dockerfile.rag                     # RAG service Dockerfile
│   └── Dockerfile.vllm                    # vLLM inference (REQUIRED)
│
├── dockge/                                # Dockge configuration
│
├── docs/                                  # Comprehensive documentation
│   ├── API_REFERENCE.md                   # API documentation (REQUIRED)
│   ├── ARCHITECTURE.md                    # System architecture (REQUIRED)
│   ├── DEPLOYMENT.md                      # Deployment procedures (REQUIRED)
│   ├── RAG_SETUP.md                       # RAG pipeline guide (REQUIRED)
│   └── TROUBLESHOOTING.md                 # Troubleshooting guide (REQUIRED)
│
├── examples/                              # Code examples
│   ├── api_examples.sh                    # Bash/cURL examples (REQUIRED)
│   ├── langchain_example.py               # LangChain RAG pipeline (REQUIRED)
│   ├── python_requests.py                 # Python requests library (REQUIRED)
│   └── rag_connections.py                 # RAG database examples (REQUIRED)
│
├── logs/                                  # Application logs (auto-created, gitignored)
│
├── models/                                # Model storage (auto-created, gitignored)
│   ├── INVENTORY.txt
│   ├── README.md
│   ├── deep_qwen_models/
│   ├── deepseek_models/
│   └── ollama/
│
├── monitoring/                            # Monitoring configurations
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   ├── dashboard.yaml             # Dashboard provisioning (REQUIRED)
│   │   │   └── gpu-dashboard.json         # GPU monitoring dashboard (REQUIRED)
│   │   └── datasources/
│   │       └── prometheus.yaml            # Prometheus datasource (REQUIRED)
│   └── prometheus.yml                     # Prometheus config (REQUIRED)
│
├── n8n/                                   # n8n workflows
│
├── scripts/                               # Automation scripts
│   ├── init-pgvector.sh                   # pgvector setup (REQUIRED)
│   ├── init-postgres.sh                   # PostgreSQL initialization (REQUIRED)
│   ├── mcp_server.py                      # MCP Server script
│   └── ollama_lazy_load.sh                # On-demand loading (REQUIRED)
│
└── stacks/                                # Docker stacks
```

**Storage Allocation Summary:**
```yaml
Total Required: ~2TB minimum, 5TB recommended

Breakdown:
  Operating System & Docker:     100GB
  Docker Images:                  50GB
  Ollama Models (existing):    1,400GB
  HuggingFace Cache (vLLM):      250GB
  Databases (initial):            50GB
  Logs (with rotation):           10GB
  Free Space Buffer:             500GB
  
Total (with buffer):          ~2,360GB (2.4TB)
```

**Permissions:**
```bash
# Ownership
sudo chown -R $(id -u):$(id -g) /mnt/ai8_arch

# Directory permissions
chmod -R 755 /mnt/ai8_arch/config
chmod -R 755 /mnt/ai8_arch/scripts
chmod -R 755 /mnt/ai8_arch/monitoring
chmod -R 777 /mnt/ai8_arch/data      # Broad for container access
chmod -R 777 /mnt/ai8_arch/models    # Broad for container access
chmod -R 777 /mnt/ai8_arch/logs      # Broad for container access

# Secure environment file
chmod 600 /mnt/ai8_arch/.env
```

---

## 3. Core Components

### 3.1 LiteLLM API Gateway

**Purpose:** Unified API gateway providing OpenAI-compatible interface to all models.

**Why LiteLLM?**
- Single API for multiple backends (Ollama, vLLM, OpenAI, etc.)
- OpenAI SDK compatibility (drop-in replacement)
- Built-in load balancing and fallbacks
- Request logging to database
- Easy to add new models

**Container Specification:**
```yaml
Image: ghcr.io/berriai/litellm:main-v1.17.9
Container Name: llm-gateway
Port Mapping: 4000:4000
Network: llm-network
Profiles: phase1, all

Environment Variables:
  DATABASE_URL: postgresql://llmuser:password@postgres:5432/litellm
    Purpose: Store request logs, model configs
  
  STORE_MODEL_IN_DB: "true"
    Purpose: Enable database-backed model registry
  
  LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
    Purpose: API authentication
    Example: sk-llm-master-key-2025
  
  LITELLM_LOG: INFO
    Purpose: Logging level (DEBUG, INFO, WARNING, ERROR)

Volumes:
  - /mnt/ai8_arch/config/litellm_config.yaml:/app/config.yaml:ro
    Purpose: Model routing configuration (read-only)

Command:
  - --config /app/config.yaml
  - --port 4000
  - --num_workers 4

Resource Limits:
  CPU: No limit (uses available)
  Memory: No limit (typically <2GB)
  GPU: None (CPU-only)

Dependencies:
  postgres:
    condition: service_healthy
    Reason: Needs database for logging

Health Check:
  Test: curl -f http://localhost:4000/health
  Interval: 30s
  Timeout: 10s
  Retries: 3
  Start Period: 30s

Restart Policy: unless-stopped
```

**Configuration File Structure:**

File: `/mnt/ai8_arch/config/litellm_config.yaml`

```yaml
# Model definitions
model_list:
  # Primary Models (Hot-Loaded)
  - model_name: gpt-oss-120b
    litellm_params:
      model: ollama/gpt-oss:120b
      api_base: http://primary-gpt-oss:11434
  - model_name: qwen3-omni
    litellm_params:
      model: ollama/qwen3-omni
      api_base: http://primary-qwen3-omni:11434

  # Secondary Models (Cold-Loaded)
  - model_name: deepseek-v2
    litellm_params:
      model: ollama/deepseek-v2
      api_base: http://secondary-deepseek-v2:11434
      timeout: 600
  - model_name: llava-v1.6-mistral-7b
    litellm_params:
      model: ollama/llava-v1.6-mistral-7b
      api_base: http://secondary-llava:11434
      timeout: 600

  # Embedding Models
  - model_name: nomic-embed-text-v1.5
    litellm_params:
      model: nomic-embed-text-v1.5 # Alias for the embedding service
      api_base: http://embeddings-service:8010/v1
      api_key: dummy
  - model_name: mxbai-embed-large-v1
    litellm_params:
      model: mxbai-embed-large-v1 # Alias for the embedding service
      api_base: http://embeddings-service:8010/v1
      api_key: dummy

# Router settings
router_settings:
  routing_strategy: latency-based-routing
    # Options: simple-shuffle, latency-based-routing, least-busy
  
  model_group_alias:
    # Allow grouping models by capability
    vision:
      - qwen3-vl-235b
      - llava-34b
      - internvl-8b
    reasoning:
      - gpt-oss-120b
      - deepseek-r1-671b
      - glm-4.6
    embeddings:
      - nomic-embed
      - stella-embed
  
  num_retries: 3
    # Retry failed requests up to 3 times
  
  timeout: 600
    # Global timeout (10 minutes)
  
  fallbacks:
    # If primary fails, try secondary
    - model: gpt-oss-120b
      fallbacks:
        - deepseek-r1-671b
        
    - model: qwen3-vl-235b
      fallbacks:
        - llava-34b
        - internvl-8b

# General settings
general_settings:
  master_key: ${LITELLM_MASTER_KEY}
    # API key for authentication
  
  database_url: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/litellm
    # Store request logs
  
  max_parallel_requests: 100
    # Maximum concurrent requests
  
  enable_pre_call_checks: true
    # Validate requests before sending to backend
  
  telemetry: false
    # Disable usage telemetry
```

**API Endpoints Provided:**

| Endpoint | Method | Purpose | OpenAI Compatible |
|----------|--------|---------|-------------------|
| `/v1/models` | GET | List available models | ✅ Yes |
| `/v1/chat/completions` | POST | Chat completions | ✅ Yes |
| `/v1/completions` | POST | Text completions | ✅ Yes |
| `/v1/embeddings` | POST | Generate embeddings | ✅ Yes |
| `/health` | GET | Health check | ❌ No (LiteLLM specific) |
| `/metrics` | GET | Prometheus metrics | ❌ No (LiteLLM specific) |

**Request Flow Example:**

```
User Application
    ↓
    POST /v1/chat/completions
    Host: localhost:4000
    Authorization: Bearer sk-llm-master-key-2025
    {
      "model": "gpt-oss",
      "messages": [{"role": "user", "content": "Hello"}]
    }
    ↓
LiteLLM Gateway
    ├─ Validate API key ✓
    ├─ Check model exists ✓
    ├─ Select backend: http://primary-gpt-oss:11434
    ├─ Transform request to Ollama format
    ├─ Forward request
    ↓
Ollama (primary-gpt-oss)
    ├─ Model already in VRAM (persistent)
    ├─ Generate response (50ms first token)
    ├─ Stream tokens
    ↓
LiteLLM Gateway
    ├─ Transform response to OpenAI format
    ├─ Log request to PostgreSQL
    ├─ Stream response to client
    ↓
User Application
    Receives response
```

**Error Handling:**

```yaml
Scenarios:
  1. Invalid API Key:
     Response: 401 Unauthorized
     Body: {"error": {"message": "Invalid API key", "type": "invalid_request_error"}}
  
  2. Model Not Found:
     Response: 404 Not Found
     Body: {"error": {"message": "Model 'unknown' not found", "type": "invalid_request_error"}}
  
  3. Backend Timeout:
     Response: 504 Gateway Timeout
     Body: {"error": {"message": "Model request timed out", "type": "timeout_error"}}
     Action: Retry with fallback (if configured)
  
  4. Backend Error:
     Response: 500 Internal Server Error
     Body: {"error": {"message": "Backend error: ...", "type": "server_error"}}
     Action: Retry up to 3 times, then return error
```

**Monitoring Integration:**

```yaml
Metrics Exposed (Prometheus format):
  litellm_requests_total{model="gpt-oss-120b", status="success"}
    Counter: Total requests per model
  
  litellm_request_duration_seconds{model="gpt-oss-120b"}
    Histogram: Request latency distribution
  
  litellm_errors_total{model="gpt-oss-120b", error_type="timeout"}
    Counter: Errors by type
  
  litellm_tokens_generated_total{model="gpt-oss-120b"}
    Counter: Total tokens generated
  
  litellm_concurrent_requests{model="gpt-oss-120b"}
    Gauge: Current concurrent requests
```

**Logging:**

```yaml
Log Format: JSON
Log Destination: 
  - stdout (Docker logs)
  - PostgreSQL database (litellm.request_logs table)

Log Fields:
  - timestamp: Request time
  - model: Model used
  - user: API key (hashed)
  - prompt_tokens: Input tokens
  - completion_tokens: Output tokens
  - latency_ms: Total latency
  - status: success/error
  - error_message: If error occurred

Example Query:
  # View recent requests
  docker exec llm-postgres psql -U llmuser -d litellm \
    -c "SELECT model, status, latency_ms FROM request_logs ORDER BY timestamp DESC LIMIT 10;"
```

---

### 3.2 PostgreSQL Database

**Purpose:** Primary relational database for LiteLLM request logs, n8n workflows, and system metadata.

**Why PostgreSQL?**
- ACID compliance
- Rich SQL features
- Wide ecosystem of tools
- Excellent Python/Node.js support
- Battle-tested reliability

**Container Specification:**
```yaml
Image: postgres:15-alpine
Container Name: llm-postgres
Port Mapping: 5432:5432
Network: llm-network
Profiles: phase1, all

Environment Variables:
  POSTGRES_USER: ${POSTGRES_USER:-llmuser}
    Purpose: Database superuser
    Default: llmuser
  
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-llmpassword}
    Purpose: Superuser password (MUST change in production)
    Security: Required, no default in .env
  
  POSTGRES_DB: litellm
    Purpose: Default database (created on first start)

Volumes:
  - /mnt/ai8_arch/data/postgres:/var/lib/postgresql/data
    Purpose: Persistent database storage
    Important: This is where ALL data lives
  
  - /mnt/ai8_arch/scripts/init-postgres.sh:/docker-entrypoint-initdb.d/init-postgres.sh:ro
    Purpose: Initialization script (runs ONCE on first start)
    Read-Only: Yes

Resource Limits:
  CPU: No limit
  Memory: No limit (typically 1-2GB)
  GPU: None

Health Check:
  Test: pg_isready -U llmuser -d litellm
  Interval: 10s
  Timeout: 5s
  Retries: 5
  Start Period: 10s
  
  Purpose: Ensure database is ready before dependent services start

Restart Policy: unless-stopped
```

**Initialization Script:**

File: `/mnt/ai8_arch/scripts/init-postgres.sh`

```bash
#!/bin/bash
# PostgreSQL Initialization Script
# Runs ONLY on first container start (when data directory is empty)
# IDEMPOTENT: Safe to run multiple times

set -euo pipefail

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "🔧 PostgreSQL initialization starting..."

# Verify environment variables
if [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_DB:-}" ]; then
  log "❌ ERROR: Required environment variables not set"
  exit 1
fi

# Function to create database if not exists (idempotent)
create_database() {
  local dbname=$1
  local owner=${2:-$POSTGRES_USER}
  
  log "Ensuring database exists: $dbname"
  
  EXISTS=$(psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$dbname'" || echo "0")
  
  if [ "$EXISTS" = "1" ]; then
    log "  ✓ Database $dbname already exists"
  else
    log "  → Creating database $dbname"
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
      CREATE DATABASE $dbname OWNER $owner;
EOSQL
    log "  ✓ Database $dbname created"
  fi
  
  # Always ensure permissions
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
    GRANT ALL PRIVILEGES ON DATABASE $dbname TO $owner;
EOSQL
}

# Function to setup extensions (idempotent)
setup_extensions() {
  local dbname=$1
  
  log "Setting up extensions in $dbname..."
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$dbname" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS pg_trgm;           -- Text search
    CREATE EXTENSION IF NOT EXISTS btree_gin;         -- Index optimization
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- Query performance
EOSQL
  log "  ✓ Extensions ready in $dbname"
}

# Create databases
log "Creating/verifying databases..."

# LiteLLM database (default, already created)
setup_extensions "$POSTGRES_DB"

# n8n database
create_database "n8n"
setup_extensions "n8n"

# Verify setup
log "Verifying database setup..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
  SELECT 
    datname as database,
    pg_size_pretty(pg_database_size(datname)) as size,
    (SELECT count(*) FROM pg_stat_activity WHERE datname = d.datname) as connections
  FROM pg_database d
  WHERE datname IN ('$POSTGRES_DB', 'n8n')
  ORDER BY datname;
EOSQL

log "✅ PostgreSQL initialization complete"
log "Available databases: $POSTGRES_DB, n8n"

exit 0
```

**Database Schema:**

**litellm database:**
```sql
-- Request logs table (created by LiteLLM)
CREATE TABLE request_logs (
  id SERIAL PRIMARY KEY,
  model VARCHAR(255),
  user VARCHAR(255),  -- API key hash
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  latency_ms FLOAT,
  status VARCHAR(50),
  error_message TEXT,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_request_logs_timestamp ON request_logs(timestamp DESC);
CREATE INDEX idx_request_logs_model ON request_logs(model);
CREATE INDEX idx_request_logs_user ON request_logs(user);

-- Model configurations (created by LiteLLM)
CREATE TABLE model_config (
  id SERIAL PRIMARY KEY,
  model_name VARCHAR(255) UNIQUE,
  config JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**n8n database:**
```sql
-- Workflows (created by n8n)
CREATE TABLE workflow_entity (
  id VARCHAR(36) PRIMARY KEY,
  name VARCHAR(128),
  active BOOLEAN,
  nodes JSONB,
  connections JSONB,
  settings JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Executions (created by n8n)
CREATE TABLE execution_entity (
  id VARCHAR(36) PRIMARY KEY,
  workflow_id VARCHAR(36) REFERENCES workflow_entity(id),
  status VARCHAR(50),
  data JSONB,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  mode VARCHAR(50)
);
```

**Backup Procedures:**

```bash
# Backup all databases
docker exec llm-postgres pg_dumpall -U llmuser > /backup/postgres_$(date +%Y%m%d).sql

# Backup specific database
docker exec llm-postgres pg_dump -U llmuser -d litellm > /backup/litellm_$(date +%Y%m%d).sql

# Restore from backup
cat /backup/postgres_20250115.sql | docker exec -i llm-postgres psql -U llmuser

# Compressed backup
docker exec llm-postgres pg_dumpall -U llmuser | gzip > /backup/postgres_$(date +%Y%m%d).sql.gz
```

**Maintenance:**

```sql
-- Check database size
SELECT 
  pg_database.datname, 
  pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
ORDER BY pg_database_size(pg_database.datname) DESC;

-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Vacuum (reclaim space)
VACUUM ANALYZE;

-- Check slow queries (if pg_stat_statements enabled)
SELECT 
  query,
  calls,
  total_time,
  mean_time,
  max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

**Performance Tuning:**

Add to `/mnt/ai8_arch/data/postgres/postgresql.conf`:
```ini
# Memory settings (adjust based on system RAM)
shared_buffers = 4GB                    # 25% of system RAM
effective_cache_size = 12GB             # 75% of system RAM
work_mem = 64MB                         # Per-operation memory
maintenance_work_mem = 1GB              # For VACUUM, CREATE INDEX

# Connection settings
max_connections = 200                   # Concurrent connections
shared_preload_libraries = 'pg_stat_statements'

# Query performance
random_page_cost = 1.1                  # SSD-optimized
effective_io_concurrency = 200          # SSD-optimized

# Checkpointing
checkpoint_completion_target = 0.9
wal_buffers = 16MB
```

---


### 3.4 Monitoring Stack

#### 3.4.1 Prometheus

**Purpose:** Time-series metrics collection and storage.

**Why Prometheus?**
- Industry standard for metrics
- Powerful query language (PromQL)
- Built-in alerting
- Excellent Grafana integration
- Pull-based model (scrapes endpoints)

**Container Specification:**
```yaml
Image: prom/prometheus:v2.48.0
Container Name: llm-prometheus
Port Mapping: 9090:9090
Network: llm-network
Profiles: phase1, all

Environment Variables: None (configured via file)

Volumes:
  - /mnt/ai8_arch/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    Purpose: Configuration file (read-only)
  
  - /mnt/ai8_arch/data/prometheus:/prometheus
    Purpose: Time-series data storage (persistent)

Command:
  - --config.file=/etc/prometheus/prometheus.yml
  - --storage.tsdb.path=/prometheus
  - --storage.tsdb.retention.time=30d
    Purpose: Keep 30 days of metrics
  - --web.enable-lifecycle
    Purpose: Allow config reload via API

Resource Limits:
  CPU: No limit
  Memory: No limit (typically 2-4GB with 30d retention)
  GPU: None

Health Check: None (Prometheus is monitoring itself)

Restart Policy: unless-stopped
```

**Configuration File:**

File: `/mnt/ai8_arch/monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s        # How often to scrape targets
  evaluation_interval: 15s    # How often to evaluate rules
  external_labels:
    cluster: 'ai8-llm-stack'
    environment: 'production'

# Scrape configurations
scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  # NVIDIA GPU metrics
  - job_name: 'nvidia-gpu'
    static_configs:
      - targets: ['nvidia_gpu_exporter:9835']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'ai8-server'
  
  # LiteLLM API Gateway
  - job_name: 'litellm'
    static_configs:
      - targets: ['litellm:4000']
    metrics_path: '/metrics'
  
  # Embedding Service
  - job_name: 'embeddings'
    static_configs:
      - targets: ['embeddings-service:8010']
    metrics_path: '/metrics'
  
  # vLLM Services
  - job_name: 'vllm-secondary-qwen3vl'
    static_configs:
      - targets: ['secondary-qwen3-vl:8000']
    metrics_path: '/metrics'
  
  - job_name: 'vllm-secondary-internvl'
    static_configs:
      - targets: ['secondary-internvl:8000']
    metrics_path: '/metrics'
  
  - job_name: 'vllm-secondary-glm4'
    static_configs:
      - targets: ['secondary-glm4:8000']
    metrics_path: '/metrics'
  
  # PostgreSQL (if postgres_exporter added in future)
  # - job_name: 'postgres'
  #   static_configs:
  #     - targets: ['postgres-exporter:9187']
  
  # Qdrant Vector Database
  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
    metrics_path: '/metrics'
  
  # Redis (if redis_exporter added in future)
  # - job_name: 'redis'
  #   static_configs:
  #     - targets: ['redis-exporter:9121']

# Alert rules (optional)
# rule_files:
#   - '/etc/prometheus/alert_rules.yml'

# Alertmanager configuration (optional)
# alerting:
#   alertmanagers:
#     - static_configs:
#         - targets: ['alertmanager:9093']
```

**Key Metrics Available:**

**GPU Metrics:**
```promql
# GPU utilization (0-100%)
nvidia_gpu_duty_cycle{gpu="0"}

# VRAM usage in bytes
nvidia_gpu_memory_used_bytes{gpu="0"}
nvidia_gpu_memory_total_bytes{gpu="0"}

# VRAM usage percentage
100 * nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes

# Temperature in Celsius
nvidia_gpu_temperature_celsius{gpu="0"}

# Power usage in watts
nvidia_gpu_power_usage_milliwatts{gpu="0"} / 1000

# Fan speed percentage
nvidia_gpu_fan_speed_percent{gpu="0"}

# Aggregate metrics
sum(nvidia_gpu_memory_used_bytes) / sum(nvidia_gpu_memory_total_bytes) * 100
  # Total VRAM usage across all GPUs
  
avg(nvidia_gpu_temperature_celsius)
  # Average GPU temperature
```

**LiteLLM Metrics:**
```promql
# Request rate (requests/second)
rate(litellm_requests_total[5m])

# Error rate
rate(litellm_requests_total{status="error"}[5m]) / rate(litellm_requests_total[5m])

# Requests by model
sum by (model) (rate(litellm_requests_total[5m]))

# Latency percentiles
histogram_quantile(0.50, rate(litellm_request_duration_seconds_bucket[5m]))  # Median
histogram_quantile(0.95, rate(litellm_request_duration_seconds_bucket[5m]))  # p95
histogram_quantile(0.99, rate(litellm_request_duration_seconds_bucket[5m]))  # p99

# Concurrent requests
litellm_concurrent_requests{model="gpt-oss-120b"}

# Tokens generated
rate(litellm_tokens_generated_total[5m])
```

**vLLM Metrics:**
```promql
# Tokens per second
rate(vllm_tokens_generated_total{model="qwen3-vl-235b"}[5m])

# Queue depth (waiting requests)
vllm_num_requests_waiting{model="qwen3-vl-235b"}

# Running requests
vllm_num_requests_running{model="qwen3-vl-235b"}

# GPU KV cache usage
vllm_gpu_cache_usage_perc{model="qwen3-vl-235b"}
```

**Qdrant Metrics:**
```promql
# Collection size
qdrant_collections_points_count{collection="my_documents"}

# Search operations
rate(qdrant_search_total[5m])

# Search latency
histogram_quantile(0.95, rate(qdrant_search_duration_seconds_bucket[5m]))
```

**Querying Prometheus:**

```bash
# Via API
curl 'http://localhost:9090/api/v1/query?query=nvidia_gpu_duty_cycle'

# Via Web UI
firefox http://localhost:9090/graph

# Example queries in web UI:
nvidia_gpu_duty_cycle                                    # Current GPU utilization
100 * nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes  # VRAM usage %
rate(litellm_requests_total[5m])                        # Request rate
histogram_quantile(0.95, rate(litellm_request_duration_seconds_bucket[5m]))  # p95 latency
```

**Data Retention:**

```yaml
Default: 30 days (configured in command)

Storage Size Estimate:
  - 8 GPUs × 10 metrics × 15s interval = 46,080 samples/hour
  - LiteLLM: ~100 series × 4 samples/minute = 6,000 samples/hour
  - Total: ~50,000 samples/hour
  - 30 days: ~36 million samples
  - Disk usage: ~2-3GB (compressed)

To change retention:
  Edit docker-compose.yaml:
    - --storage.tsdb.retention.time=60d  # 60 days
```

**Config Reload (No Restart):**

```bash
# Send HUP signal
docker exec llm-prometheus kill -HUP 1

# Or use API
curl -X POST http://localhost:9090/-/reload
```

---

#### 3.4.2 NVIDIA GPU Exporter

**Purpose:** Export GPU metrics to Prometheus.

**Why This Exporter?**
- Comprehensive GPU metrics
- Low overhead
- Well-maintained
- Easy Prometheus integration

**Container Specification:**
```yaml
Image: utkuozdemir/nvidia_gpu_exporter:1.2.0
Container Name: llm-gpu-exporter
Port Mapping: 9835:9835
Network: llm-network
Profiles: phase1, all

Environment Variables:
  NVIDIA_VISIBLE_DEVICES: all
    Purpose: Access all 8 GPUs

Volumes:
  - /usr/lib/x86_64-linux-gnu/libnvidia-ml.so:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so:ro
  - /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:ro
  - /usr/bin/nvidia-smi:/usr/bin/nvidia-smi:ro
  
  Purpose: Mount NVIDIA libraries from host (read-only)

GPU Access:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            capabilities: [gpu]
            device_ids: ['0','1','2','3','4','5','6','7']
  
  Purpose: Access all GPUs for monitoring

Restart Policy: unless-stopped
```

**Metrics Exported:**

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `nvidia_gpu_duty_cycle` | Gauge | GPU utilization (0-100%) | gpu, uuid, name |
| `nvidia_gpu_memory_used_bytes` | Gauge | Used VRAM in bytes | gpu, uuid, name |
| `nvidia_gpu_memory_total_bytes` | Gauge | Total VRAM in bytes | gpu, uuid, name |
| `nvidia_gpu_temperature_celsius` | Gauge | GPU temperature | gpu, uuid, name |
| `nvidia_gpu_power_usage_milliwatts` | Gauge | Power draw in milliwatts | gpu, uuid, name |
| `nvidia_gpu_fan_speed_percent` | Gauge | Fan speed (0-100%) | gpu, uuid, name |
| `nvidia_gpu_info` | Gauge | GPU information (always 1) | gpu, name, uuid, driver_version, cuda_version |

**Example Metrics Output:**

```
# HELP nvidia_gpu_duty_cycle GPU utilization in percent
# TYPE nvidia_gpu_duty_cycle gauge
nvidia_gpu_duty_cycle{gpu="0",name="NVIDIA H100 80GB HBM3",uuid="GPU-12345"} 95
nvidia_gpu_duty_cycle{gpu="1",name="NVIDIA H100 80GB HBM3",uuid="GPU-12346"} 0
nvidia_gpu_duty_cycle{gpu="2",name="NVIDIA H100 80GB HBM3",uuid="GPU-12347"} 82
nvidia_gpu_duty_cycle{gpu="3",name="NVIDIA H100 80GB HBM3",uuid="GPU-12348"} 83
nvidia_gpu_duty_cycle{gpu="4",name="NVIDIA H100 80GB HBM3",uuid="GPU-12349"} 84
nvidia_gpu_duty_cycle{gpu="5",name="NVIDIA H100 80GB HBM3",uuid="GPU-12350"} 91
nvidia_gpu_duty_cycle{gpu="6",name="NVIDIA H100 80GB HBM3",uuid="GPU-12351"} 92
nvidia_gpu_duty_cycle{gpu="7",name="NVIDIA H100 80GB HBM3",uuid="GPU-12352"} 90

# HELP nvidia_gpu_temperature_celsius GPU temperature in Celsius
# TYPE nvidia_gpu_temperature_celsius gauge
nvidia_gpu_temperature_celsius{gpu="0",name="NVIDIA H100 80GB HBM3",uuid="GPU-12345"} 45
nvidia_gpu_temperature_celsius{gpu="2",name="NVIDIA H100 80GB HBM3",uuid="GPU-12347"} 72
nvidia_gpu_temperature_celsius{gpu="3",name="NVIDIA H100 80GB HBM3",uuid="GPU-12348"} 73
nvidia_gpu_temperature_celsius{gpu="4",name="NVIDIA H100 80GB HBM3",uuid="GPU-12349"} 74
nvidia_gpu_temperature_celsius{gpu="5",name="NVIDIA H100 80GB HBM3",uuid="GPU-12350"} 76
nvidia_gpu_temperature_celsius{gpu="6",name="NVIDIA H100 80GB HBM3",uuid="GPU-12351"} 77
nvidia_gpu_temperature_celsius{gpu="7",name="NVIDIA H100 80GB HBM3",uuid="GPU-12352"} 75
```

**Testing GPU Exporter:**

```bash
# Check if exporter is running
curl http://localhost:9835/metrics

# Check specific GPU metrics
curl -s http://localhost:9835/metrics | grep nvidia_gpu_duty_cycle

# Verify all 8 GPUs are visible
curl -s http://localhost:9835/metrics | grep 'nvidia_gpu_info{gpu=' | wc -l
# Should return: 8
```

**Troubleshooting:**

```bash
# If exporter shows no GPUs:
# 1. Check NVIDIA libraries are mounted
docker exec llm-gpu-exporter ls -la /usr/lib/x86_64-linux-gnu/libnvidia*
docker exec llm-gpu-exporter ls -la /usr/bin/nvidia-smi

# 2. Test nvidia-smi inside container
docker exec llm-gpu-exporter nvidia-smi

# 3. Check GPU access
docker exec llm-gpu-exporter sh -c 'echo $NVIDIA_VISIBLE_DEVICES'
# Should return: all

# 4. Check container logs
docker logs llm-gpu-exporter
```

---

#### 3.4.3 Grafana

**Purpose:** Visualization, dashboards, and alerting for metrics.

**Why Grafana?**
- Beautiful dashboards
- Excellent Prometheus integration
- Alert management
- User-friendly interface
- Provisioning support (configuration as code)

**Container Specification:**
```yaml
Image: grafana/grafana:10.2.2
Container Name: llm-grafana
Port Mapping: 3000:3000
Network: llm-network
Profiles: phase1, all

Environment Variables:
  GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}
    Purpose: Admin password (MUST change in production)
    Security: Set in .env file
  
  GF_SECURITY_ADMIN_USER: admin
    Purpose: Admin username (hardcoded)
  
  GF_INSTALL_PLUGINS: grafana-clock-panel
    Purpose: Install additional plugins on startup
    Note: Can add more comma-separated
  
  GF_PATHS_PROVISIONING: /etc/grafana/provisioning
    Purpose: Directory for provisioned dashboards/datasources

Volumes:
  - /mnt/ai8_arch/data/grafana:/var/lib/grafana
    Purpose: Persistent Grafana data (dashboards, users, settings)
  
  - /mnt/ai8_arch/monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    Purpose: Auto-provision dashboards (read-only)
  
  - /mnt/ai8_arch/monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    Purpose: Auto-provision Prometheus datasource (read-only)

Resource Limits:
  CPU: No limit
  Memory: No limit (typically <1GB)
  GPU: None

Dependencies:
  - prometheus
    Reason: Needs Prometheus as datasource

Health Check: None (web interface is health check)

Restart Policy: unless-stopped
```

**Datasource Provisioning:**

File: `/mnt/ai8_arch/monitoring/grafana/datasources/prometheus.yaml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "15s"
      queryTimeout: "60s"
      httpMethod: POST
```

**Dashboard Provisioning:**

File: `/mnt/ai8_arch/monitoring/grafana/dashboards/dashboard.yaml`

```yaml
apiVersion: 1

providers:
  - name: 'AI8 Dashboards'
    orgId: 1
    folder: 'LLM Stack'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
      foldersFromFilesStructure: true
```

**Pre-configured GPU Dashboard:**

File: `/mnt/ai8_arch/monitoring/grafana/dashboards/gpu-dashboard.json`

Key panels:
1. **GPU Utilization (%) - Time Series Graph**
   - Query: `nvidia_gpu_duty_cycle`
   - Shows all 8 GPUs as separate lines
   - Alert: >95% for 5 minutes

2. **VRAM Usage (%) - Time Series Graph**
   - Query: `100 * nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes`
   - Stacked area chart showing total VRAM usage
   - Alert: >95%

3. **GPU Temperature (°C) - Time Series Graph**
   - Query: `nvidia_gpu_temperature_celsius`
   - Line chart per GPU
   - Alert: >85°C

4. **Power Usage (W) - Time Series Graph**
   - Query: `nvidia_gpu_power_usage_milliwatts / 1000`
   - Bar chart showing current power per GPU
   - Total power consumption aggregate

5. **Model Performance - Bar Gauge**
   - Query: `rate(litellm_requests_total[5m])`
   - Shows requests/second per model

6. **API Latency - Time Series**
   - Query: `histogram_quantile(0.95, rate(litellm_request_duration_seconds_bucket[5m]))`
   - Shows p95 latency over time

7. **GPU Status Table**
   - Combines multiple queries
   - Shows: GPU #, Name, Utilization, VRAM, Temp, Power
   - Color-coded by thresholds

**Creating Custom Dashboards:**

```bash
# Access Grafana
firefox http://localhost:3000

# Login
Username: admin
Password: (from GRAFANA_ADMIN_PASSWORD in .env)

# Create new dashboard:
1. Click "+" → Dashboard
2. Add Panel → Add Query
3. Select "Prometheus" datasource
4. Enter PromQL query (e.g., nvidia_gpu_duty_cycle)
5. Configure visualization (Graph, Gauge, Table, etc.)
6. Set panel title and description
7. Save dashboard

# Example PromQL queries for dashboards:
# GPU utilization
nvidia_gpu_duty_cycle

# VRAM usage %
100 * nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes

# Requests per model
sum by (model) (rate(litellm_requests_total[5m]))

# Error rate
rate(litellm_requests_total{status="error"}[5m]) / rate(litellm_requests_total[5m])

# p95 latency
histogram_quantile(0.95, rate(litellm_request_duration_seconds_bucket[5m]))

# Average GPU temperature
avg(nvidia_gpu_temperature_celsius)

# Total VRAM used across all GPUs (GB)
sum(nvidia_gpu_memory_used_bytes) / 1024 / 1024 / 1024
```

**Alert Configuration:**

```yaml
# In Grafana UI: Alerting → Alert Rules

# Example: High GPU Temperature
Name: High GPU Temperature
Condition: avg(nvidia_gpu_temperature_celsius) > 85
For: 5m
Annotations:
  Summary: GPU temperature above 85°C
  Description: Average GPU temperature is {{ $value }}°C
Actions:
  - Log to console
  - Send notification (if configured)

# Example: High VRAM Usage
Name: High VRAM Usage
Condition: (nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes) > 0.95
For: 2m
Annotations:
  Summary: GPU {{ $labels.gpu }} VRAM above 95%
  Description: GPU {{ $labels.gpu }} using {{ $value | humanize }}% VRAM
Actions:
  - Alert
  - Prevent new model loads

# Example: High API Error Rate
Name: High API Error Rate
Condition: rate(litellm_requests_total{status="error"}[5m]) / rate(litellm_requests_total[5m]) > 0.05
For: 3m
Annotations:
  Summary: API error rate above 5%
  Description: Error rate is {{ $value | humanizePercentage }}
Actions:
  - Alert
  - Check logs

# Example: Model Unresponsive
Name: Model Unresponsive
Condition: up{job="litellm"} == 0
For: 2m
Annotations:
  Summary: LiteLLM gateway down
  Description: LiteLLM has been down for {{ $duration }}
Actions:
  - Critical alert
  - Auto-restart (if configured)
```

**Grafana Administration:**

```bash
# Reset admin password (if forgotten)
docker exec llm-grafana grafana-cli admin reset-admin-password newpassword

# Install additional plugins
docker exec llm-grafana grafana-cli plugins install <plugin-id>
docker compose restart grafana

# Backup dashboards
curl -u admin:password http://localhost:3000/api/search?query=& > dashboards.json
# Then export each dashboard individually

# Restore dashboard
curl -X POST -u admin:password \
  -H "Content-Type: application/json" \
  -d @dashboard.json \
  http://localhost:3000/api/dashboards/db
```

---

## 4. Model Management

### 4.1 Model Tiering Strategy

**Overview:**

The AI8 Architecture implements a four-tier model management system to optimize GPU utilization and provide different performance characteristics for various use cases.

**Tier Comparison:**

| Tier | Load Strategy | Keep-Alive | Latency | Use Case | GPU Allocation |
|------|---------------|------------|---------|----------|----------------|
| **Tier 1 (Primary)** | Always loaded | Permanent (-1) | <100ms TTFT | Production, real-time | Dedicated GPUs |
| **Tier 2 (Secondary)** | On-demand | 600s (10 min) | 10-30s cold, <500ms warm | Batch, specialized | Shared pool |
| **Tier 3 (Embeddings)** | On-demand | 300s (5 min) | 5-30s cold, <200ms warm | RAG pipelines | GPU 2 (shared) |
| **Tier 4 (Playground)** | User-controlled | 60s (1 min) | Variable | Experimentation | All GPUs 2-7 |

### 4.2 Tier 1: Primary Models

**Purpose:** Production workloads requiring consistent low latency.

**Characteristics:**
- Pre-loaded into VRAM during container startup
- Never unloads (keep_alive: -1)
- Dedicated GPU allocation (no sharing with other primary models)
- Time to First Token (TTFT): <100ms
- Ideal for: Chat applications, real-time inference, production APIs

#### 4.2.1 Primary Model 1: GPT-OSS 120B

**Model Specifications:**
```yaml
Name: GPT-OSS 120B
Framework: Ollama
Full Name: gpt-oss:120b
Architecture: Transformer-based, GPT-style
Parameters: ~120 billion
Quantization: Q4_K_M (4-bit)
Size on Disk: ~196GB
VRAM Required: ~180GB (across 3 GPUs)
Context Length: 8192 tokens
Training Data: Open-source datasets
License: Open-source (verify specific terms)

Strengths:
  - General-purpose reasoning
  - Instruction following
  - Multi-turn conversations
  - Code generation
  - Question answering

Weaknesses:
  - No vision capabilities
  - English-focused (limited multilingual)
  - Slower than smaller models
```

**Container Configuration:**
```yaml
Image: ollama/ollama:0.1.30
Container Name: primary-gpt-oss
Port Mapping: 11601:11434
Network: llm-network
Profiles: phase3, all

Environment Variables:
  OLLAMA_KEEP_ALIVE: -1
    Purpose: Never unload model (persistent)
  
  OLLAMA_NUM_PARALLEL: 4
    Purpose: Handle up to 4 concurrent requests
  
  OLLAMA_GPU_LAYER_COUNT: 999
    Purpose: Load all layers to GPU (maximize performance)
  
  OLLAMA_HOST: 0.0.0.0
    Purpose: Listen on all interfaces

Volumes:
  - /mnt/ai8_arch/models/ollama/primary/gpt_oss:/root/.ollama
    Purpose: Model storage (persistent)
  
  - /mnt/ai8_arch/scripts/ollama_preload.sh:/preload.sh:ro
    Purpose: Startup script (read-only)
  
  - /mnt/ai8_arch/logs/ollama:/var/log
    Purpose: Logs

Entrypoint: ["/bin/bash", "/preload.sh", "gpt-oss:120b"]
  Purpose: Load model on startup

GPU Access:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ['0','2'] # Mandated GPU Allocation
            capabilities: [gpu]
  
  Purpose: Dedicated access to GPUs 0 and 2

Health Check:
  Test: curl -f http://localhost:11434/api/tags
  Interval: 60s
  Timeout: 10s
  Retries: 3
  Start Period: 300s (5 minutes for initial load)

Restart Policy: unless-stopped
```

**Loading Script:**

File: `/mnt/ai8_arch/scripts/ollama_preload.sh`

```bash
#!/bin/bash
# Persistent Model Loading Script
# Loads model into VRAM and keeps it there permanently

set -euo pipefail

MODEL_NAME="${1:-}"
STARTUP_TIMEOUT=120
LOAD_TIMEOUT=600
LOG_DIR="/var/log"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  [ -d "$LOG_DIR" ] && echo "$msg" >> "$LOG_DIR/ollama_preload.log"
}

log "🚀 Starting Ollama with PERSISTENT model: $MODEL_NAME"

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
  GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader | head -1)
  FREE_VRAM=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
  TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
  log "📊 GPU: $GPU_COUNT available, ${FREE_VRAM}MB free / ${TOTAL_VRAM}MB total"
fi

# Start Ollama server
log "Starting Ollama server..."
ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
SERVE_PID=$!

# Wait for server ready
log "⏳ Waiting for Ollama server (timeout: ${STARTUP_TIMEOUT}s)..."
ELAPSED=0
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
  
  if ! kill -0 $SERVE_PID 2>/dev/null; then
    log "❌ Ollama server process died"
    exit 1
  fi
  
  if [ $ELAPSED -ge $STARTUP_TIMEOUT ]; then
    log "❌ Timeout waiting for Ollama server"
    exit 1
  fi
done
log "✅ Ollama server ready (took ${ELAPSED}s)"

# Check if model exists
if [ -z "$MODEL_NAME" ]; then
  log "⚠️  No model specified"
  log "Container ready but no model loaded"
else
  if ! ollama list 2>/dev/null | grep -qE "^${MODEL_NAME}(\s|:)"; then
    log "📥 Model not found, pulling: $MODEL_NAME"
    
    for attempt in {1..3}; do
      log "Pull attempt $attempt/3..."
      if ollama pull "$MODEL_NAME" 2>&1 | tee -a "$LOG_DIR/ollama.log"; then
        log "✅ Model pulled successfully"
        break
      else
        if [ $attempt -lt 3 ]; then
          log "⚠️  Pull failed, retrying in 30s..."
          sleep 30
        else
          log "❌ Failed to pull model after 3 attempts"
          exit 1
        fi
      fi
    done
  else
    log "✅ Model already available: $MODEL_NAME"
  fi

  # Preload into VRAM (persistent)
  log "🔥 Loading model into VRAM (persistent)..."
  
  START_TIME=$(date +%s)
  RESPONSE=$(curl -sf -X POST \
    --max-time $LOAD_TIMEOUT \
    http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"$MODEL_NAME\", \"prompt\": \"System ready\", \"stream\": false, \"keep_alive\": -1}" \
    2>&1) || {
    log "❌ Model load failed"
    exit 1
  }
  END_TIME=$(date +%s)
  LOAD_TIME=$((END_TIME - START_TIME))
  
  if echo "$RESPONSE" | grep -q '"done":true'; then
    log "✅ Model loaded and persistent in VRAM (${LOAD_TIME}s)"
    
    if command -v nvidia-smi &> /dev/null; then
      USED_VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
      log "  • VRAM used: ${USED_VRAM}MB"
    fi
  else
    log "❌ Model load verification failed"
    exit 1
  fi
fi

# Signal handlers for graceful shutdown
trap 'log "Shutting down..."; kill $SERVE_PID 2>/dev/null; exit 0' SIGTERM SIGINT

log "🎯 Service ready and healthy"
wait $SERVE_PID
```

**Performance Characteristics:**
```yaml
Startup Time: ~5-10 minutes (initial model load)
  - Ollama server: ~10 seconds
  - Model download: 0s (if cached) or 30-60 min (first time)
  - Model load to VRAM: ~5 minutes

Inference Performance:
  - Time to First Token (TTFT): 50-100ms
  - Tokens per Second: 50-80 tokens/s
  - Concurrent Requests: Up to 4 (OLLAMA_NUM_PARALLEL)
  - Batch Size: Automatic (Ollama-managed)

Memory Usage:
  - Per-GPU VRAM: ~60GB
  - Total VRAM: ~180GB (3 GPUs)
  - System RAM: ~10GB peak during load
```

**API Usage:**

```python
import litellm

# Set the API base to the LiteLLM gateway
litellm.api_base = "http://localhost:4000"

try:
    response = litellm.completion(
        model="gpt-oss",
        messages=[
            {"role": "user", "content": "Write a short story about a robot who discovers music."}
        ],
        stream=False
    )
    print(response)
except Exception as e:
    print(f"An error occurred: {e}")
```

**Monitoring:**
```bash
# Check model status
curl http://localhost:11601/api/ps

# Check if model is loaded
ollama list | grep gpt-oss

# View logs
docker logs -f primary-gpt-oss

# Check GPU usage
nvidia-smi
# GPUs 2, 3, 4 should show ~60GB used each

# Check via Grafana
# Dashboard → GPU Monitoring → GPU 2/3/4 VRAM Usage
```


### 4.3 Tier 2: Secondary Models

**Purpose:** Specialized tasks, batch processing, infrequent use.

**Characteristics:**
- Downloaded during startup but NOT loaded into VRAM
- Loads on first request (~10-30 seconds)
- Auto-unloads after 600s (10 minutes) of inactivity
- Shared GPU pool (GPUs 2-7)
- Ideal for: Batch processing, specialized analysis, cost-effective inference

**Model List:**

| Model | Size | GPUs | Keep-Alive | Use Case | Port |
|-------|------|------|------------|----------|------|
| DeepSeek R1 671B | 377GB | 2-5 (4 GPUs) | 600s | Advanced reasoning, long context | 11603 |
| Llava 34B | 37GB | 3 | 600s | Vision Q&A, image captioning | 11602 |
| InternVL3.5 8B | 6GB | 2 | N/A | Fast vision tasks | 8002 |
| GLM-4.6 | 355GB | 4-7 (4 GPUs) | N/A | Chinese language, reasoning | 8003 |

#### 4.3.1 Secondary Model 1: Qwen3-VL 235B

*This section will be populated with the model's specifications, container configuration, performance characteristics, and usage examples, consistent with the format of other model entries in this document.*

---

#### 4.3.2 Secondary Model 2: DeepSeek R1 671B

**Model Specifications:**
```yaml
Name: DeepSeek R1 671B
Framework: Ollama
Full Name: deepseek-r1:671b-0528-q4_K_M
Architecture: Mixture of Experts (MoE)
Parameters: ~671 billion total, ~37B active per token
Quantization: Q4_K_M (4-bit)
Size on Disk: ~377GB
VRAM Required: ~380GB (across 4 GPUs)
Context Length: 32,768 tokens (32K)
Specialization: Advanced reasoning, mathematics, coding

Strengths:
  - Excellent reasoning capabilities
  - Long context support (32K tokens)
  - Strong mathematics and logic
  - Code generation and debugging
  - Multi-step problem solving

Weaknesses:
  - Very large (slow cold start)
  - English-focused
  - No vision capabilities
  - High VRAM requirement
```

**Container Configuration:**
```yaml
Image: ollama/ollama:0.1.30
Container Name: secondary-deepseek
Port Mapping: 11603:11434
Network: llm-network
Profiles: phase3, all

Environment Variables:
  OLLAMA_KEEP_ALIVE: 600
    Purpose: Unload after 10 minutes idle
  
  OLLAMA_NUM_PARALLEL: 4
  OLLAMA_GPU_LAYER_COUNT: 999
  OLLAMA_HOST: 0.0.0.0

Volumes:
  - /mnt/ai8_arch/models/ollama/secondary/deepseek_r1_671b:/root/.ollama
  - /mnt/ai8_arch/scripts/ollama_lazy_load.sh:/lazy_load.sh:ro
  - /mnt/ai8_arch/logs/ollama:/var/log

Entrypoint: ["/bin/bash", "/lazy_load.sh", "deepseek-r1:671b-0528-q4_K_M"]

GPU Access:
  device_ids: ['2','3','4','5']
  Purpose: Shared pool (4 GPUs)

Restart Policy: unless-stopped
```

**Lazy Load Script:**

File: `/mnt/ai8_arch/scripts/ollama_lazy_load.sh`

```bash
#!/bin/bash
# On-Demand Model Loading Script
# Downloads model but doesn't load until first request

set -euo pipefail

MODEL_NAME="${1:-}"
STARTUP_TIMEOUT=120
KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-600}"
LOG_DIR="/var/log"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  [ -d "$LOG_DIR" ] && echo "$msg" >> "$LOG_DIR/ollama_lazy_load.log"
}

log "🚀 Starting Ollama with ON-DEMAND model: $MODEL_NAME"
log "⏱️  Keep-alive: ${KEEP_ALIVE}s (auto-unload after inactivity)"

# Start Ollama server
log "Starting Ollama server..."
ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
SERVE_PID=$!

# Wait for server
log "⏳ Waiting for Ollama server..."
ELAPSED=0
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
  
  if ! kill -0 $SERVE_PID 2>/dev/null; then
    log "❌ Server died"
    exit 1
  fi
  
  if [ $ELAPSED -ge $STARTUP_TIMEOUT ]; then
    log "❌ Timeout"
    exit 1
  fi
done
log "✅ Server ready (${ELAPSED}s)"

# Download model if not exists
if [ -n "$MODEL_NAME" ]; then
  if ! ollama list 2>/dev/null | grep -qE "^${MODEL_NAME}(\s|:)"; then
    log "📥 Downloading: $MODEL_NAME"
    
    for attempt in {1..3}; do
      if ollama pull "$MODEL_NAME"; then
        log "✅ Downloaded"
        break
      else
        [ $attempt -lt 3 ] && sleep 30 || exit 1
      fi
    done
  else
    log "✅ Already downloaded: $MODEL_NAME"
  fi
  
  log "⏸️  Model ready for on-demand loading"
  log "💡 First request will take 10-30s (loading to VRAM)"
  log "💡 Auto-unloads after ${KEEP_ALIVE}s idle"
fi

trap 'log "Shutting down"; kill $SERVE_PID 2>/dev/null; exit 0' SIGTERM SIGINT

log "🎯 Service ready"
wait $SERVE_PID
```

**Performance Characteristics:**
```yaml
Cold Start (First Request):
  - Model load time: 20-30 seconds
  - Total latency: 25-35 seconds
  - Happens when: Model not in VRAM

Warm Performance (Subsequent Requests):
  - TTFT: 100-150ms
  - Tokens per Second: 30-50 tokens/s
  - Remains warm for: 600 seconds after last request

Auto-Unload:
  - After 600s idle, model unloads from VRAM
  - VRAM freed for other models
  - Next request triggers cold start again

Memory Usage:
  - Per-GPU VRAM: ~95GB
  - Total VRAM: ~380GB (4 GPUs)
  - Shares GPUs 2-5 with other secondary models
```

**Usage Example:**

```python
import litellm

# Set the API base to the LiteLLM gateway
litellm.api_base = "http://localhost:4000"

try:
    response = litellm.completion(
        model="deepseek-671b",
        messages=[
            {"role": "user", "content": "Explain the theory of relativity in simple terms."}
        ],
        stream=False
    )
    print(response)
except Exception as e:
    print(f"An error occurred: {e}")
```

**When to Use:**
- Complex multi-step reasoning
- Mathematical proofs
- Advanced coding tasks
- Long-context analysis (up to 32K tokens)
- Batch processing (not time-sensitive)

**When NOT to Use:**
- Real-time chat (use GPT-OSS instead)
- Simple queries (overkill)
- Vision tasks (no image support)
- Frequent small requests (cold start overhead)

---

### 4.4 Tier 3: Embedding Models

**Purpose:** Generate vector embeddings for RAG pipelines.

**Architecture:**

The embedding service is a unified FastAPI application that manages multiple embedding models (both Ollama and HuggingFace) and provides a single OpenAI-compatible API.

**Container Configuration:**
```yaml
Build:
  context: /mnt/ai8_arch
  dockerfile: dockerfiles/Dockerfile.embeddings
Image: embeddings-multi:latest
Container Name: embeddings-service
Port Mapping: 
  - 8010:8010 (FastAPI)
  - 11610:11434 (Ollama)
Network: llm-network
Profiles: phase3, all

Environment Variables:
  HF_TOKEN: ${HF_TOKEN}
  OLLAMA_HOST: 0.0.0.0
  OLLAMA_KEEP_ALIVE: 300
    Purpose: Unload Ollama models after 5 minutes
  PRELOAD_MODELS: ${EMBEDDING_PRELOAD:-}
    Purpose: Optional comma-separated list to preload

Volumes:
  - /mnt/ai8_arch/models/ollama/embeddings:/root/.ollama
  - /mnt/ai8_arch/models/huggingface:/root/.cache/huggingface
  - /mnt/ai8_arch/scripts/embedding_service.py:/app/embedding_service.py:ro
  - /mnt/ai8_arch/logs/embeddings:/var/log

Command: python /app/embedding_service.py

GPU Access:
  device_ids: ['2']
  Purpose: Shared with other services on GPU 2

Health Check:
  Test: curl -f http://localhost:8000/health
  Interval: 30s
  Start Period: 60s

Restart Policy: unless-stopped
```

**Dockerfile:**

File: `/mnt/ai8_arch/dockerfiles/Dockerfile.embeddings`

```dockerfile
FROM python:3.11-slim

LABEL maintainer="CannonCoPilot"
LABEL description="Multi-model embedding service"

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://github.com/ollama/ollama/releases/download/v0.1.30/ollama-linux-amd64 \
    -o /usr/local/bin/ollama && \
    chmod +x /usr/local/bin/ollama

# Install PyTorch (CUDA 12.1)
RUN pip install --no-cache-dir \
    torch==2.2.0 \
    torchvision==0.17.0 \
    --index-url https://download.pytorch.org/whl/cu121

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi==0.110.0 \
    uvicorn[standard]==0.27.0 \
    transformers==4.40.0 \
    sentence-transformers==2.5.1 \
    accelerate==0.27.0 \
    huggingface_hub==0.21.0 \
    pydantic==2.6.0 \
    requests==2.31.0

# Verify GPU
RUN python -c "import torch; assert torch.cuda.is_available()"

WORKDIR /app

EXPOSE 11434 8010

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -f http://localhost:8010/health || exit 1

CMD ["bash"]
```

**Embedding Service Implementation:**

File: `/mnt/ai8_arch/scripts/embedding_service.py`

```python
#!/usr/bin/env python3
"""
Multi-Model Embedding Service
Provides OpenAI-compatible API for embeddings
Supports Ollama and HuggingFace models
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import subprocess
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import torch
from sentence_transformers import SentenceTransformer

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI8 Embedding Service", version="1.0.0")

# Configuration
HF_TOKEN = os.getenv("HF_TOKEN", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = 11434
OLLAMA_KEEP_ALIVE = int(os.getenv("OLLAMA_KEEP_ALIVE", "300"))

# Model registry: (backend_type, model_name, dimensions)
MODELS = {
    "nomic": ("ollama", "nomic-embed-text:137m-v1.5-fp16", 768),
    "qwen3": ("ollama", "qwen3-embedding:8b-q8_0", 1024),
    "gemma": ("ollama", "embeddinggemma:300m-bf16", 768),
    "stella": ("hf", "NovaSearch/stella_en_1.5B_v5", 1024),
    "jasper": ("hf", "NovaSearch/jasper_en_vision_language_v1", 1024),
}

# HuggingFace model cache
hf_model_cache: Dict[str, SentenceTransformer] = {}

# Ollama status
ollama_process = None

# Pydantic models
class EmbeddingRequest(BaseModel):
    model: str
    input: List[str] | str
    encoding_format: str = "float"

class EmbeddingResponse(BaseModel):
    model: str
    embeddings: List[List[float]]
    dimensions: int
    num_texts: int

# Helper functions
def start_ollama():
    """Start Ollama server"""
    global ollama_process
    logger.info("Starting Ollama server...")
    
    try:
        ollama_process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server
        for _ in range(30):
            try:
                requests.get(f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags", timeout=1)
                logger.info("✅ Ollama server ready")
                return True
            except:
                time.sleep(1)
        
        logger.error("❌ Ollama server failed to start")
        return False
    except Exception as e:
        logger.error(f"Failed to start Ollama: {e}")
        return False

@lru_cache(maxsize=5)
def load_hf_model(model_name: str) -> SentenceTransformer:
    """Load HuggingFace model (cached)"""
    logger.info(f"Loading HF model: {model_name}")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(model_name, device=device)
    
    logger.info(f"✅ Model loaded: {model_name} on {device}")
    return model

def get_ollama_embeddings(model: str, texts: List[str]) -> List[List[float]]:
    """Get embeddings from Ollama"""
    embeddings = []
    
    for text in texts:
        response = requests.post(
            f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/embeddings",
            json={
                "model": model,
                "prompt": text,
                "keep_alive": f"{OLLAMA_KEEP_ALIVE}s"
            },
            timeout=30
        )
        response.raise_for_status()
        embeddings.append(response.json()["embedding"])
    
    return embeddings

def get_hf_embeddings(model_name: str, texts: List[str]) -> List[List[float]]:
    """Get embeddings from HuggingFace model"""
    model = load_hf_model(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()

# API endpoints
@app.on_event("startup")
async def startup():
    """Start Ollama on service startup"""
    start_ollama()
    logger.info("🚀 Embedding service started")
    logger.info(f"Available models: {list(MODELS.keys())}")
    logger.info(f"GPU available: {torch.cuda.is_available()}")

@app.get("/health")
async def health():
    """Health check"""
    # Check Ollama
    ollama_healthy = False
    try:
        requests.get(f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags", timeout=2)
        ollama_healthy = True
    except:
        pass
    
    return {
        "status": "healthy",
        "ollama": "healthy" if ollama_healthy else "unhealthy",
        "gpu_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "available_models": list(MODELS.keys()),
        "loaded_hf_models": list(hf_model_cache.keys())
    }

@app.get("/models")
async def list_models():
    """List available models"""
    models_info = {}
    
    for alias, (backend, model_name, dims) in MODELS.items():
        models_info[alias] = {
            "type": backend,
            "name": model_name,
            "dimensions": dims,
            "backend": "ollama" if backend == "ollama" else "huggingface"
        }
    
    return {"models": models_info}

@app.post("/v1/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings (OpenAI-compatible)"""
    # Normalize input
    texts = [request.input] if isinstance(request.input, str) else request.input
    
    if not texts:
        raise HTTPException(status_code=400, detail="No input provided")
    
    # Get model info
    if request.model not in MODELS:
        raise HTTPException(status_code=404, detail=f"Model '{request.model}' not found. Available: {list(MODELS.keys())}")
    
    backend, model_name, dimensions = MODELS[request.model]
    
    logger.info(f"Generating embeddings: model={request.model}, texts={len(texts)}, backend={backend}")
    
    try:
        # Generate embeddings
        if backend == "ollama":
            embeddings = get_ollama_embeddings(model_name, texts)
        else:  # hf
            embeddings = get_hf_embeddings(model_name, texts)
        
        logger.info(f"✅ Generated {len(embeddings)} embeddings")
        
        return EmbeddingResponse(
            model=request.model,
            embeddings=embeddings,
            dimensions=dimensions,
            num_texts=len(texts)
        )
    
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
```

**Available Embedding Models:**

| Model Alias | Backend | Full Name | Dimensions | VRAM | Max Tokens | Use Case |
|-------------|---------|-----------|------------|------|------------|----------|
| `nomic` | Ollama | nomic-embed-text:137m-v1.5-fp16 | 768 | ~1GB | 8192 | General purpose, fast |
| `stella` | HuggingFace | NovaSearch/stella_en_1.5B_v5 | 1024 | ~5GB | 512 | High quality, English |
| `qwen3` | Ollama | qwen3-embedding:8b-q8_0 | 1024 | ~15GB | 8192 | Multilingual |
| `gemma` | Ollama | embeddinggemma:300m-bf16 | 768 | ~1GB | 8192 | Fast, lightweight |
| `jasper` | HuggingFace | jasper_en_vision_language_v1 | 1024 | ~4GB | Variable | Multimodal (text+vision) |

**API Usage:**

```bash
# Health check
curl http://localhost:8010/health

# List models
curl http://localhost:8010/models

# Generate embeddings (single text)
curl -X POST http://localhost:8010/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "stella",
    "input": "Sample text for embedding"
  }'

# Generate embeddings (batch)
curl -X POST http://localhost:8010/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic",
    "input": [
      "First document text",
      "Second document text",
      "Third document text"
    ]
  }'

# Via LiteLLM Gateway
curl -X POST http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer sk-llm-master-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed",
    "input": "Sample text"
  }'

# Python example
import requests

response = requests.post(
    "http://localhost:8010/v1/embeddings",
    json={
        "model": "stella",
        "input": ["Text 1", "Text 2", "Text 3"]
    }
)

data = response.json()
embeddings = data["embeddings"]
dimensions = data["dimensions"]

print(f"Generated {len(embeddings)} embeddings of {dimensions} dimensions")
```

**Performance:**

```yaml
Cold Start (First Request per Model):
  Ollama Models: 5-15 seconds
  HuggingFace Models: 10-30 seconds (model download + load)

Warm Performance:
  Single Text: 50-200ms
  Batch (10 texts): 200-800ms
  Batch (100 texts): 2-10 seconds

Memory Usage:
  Ollama (per model): 1-15GB VRAM
  HuggingFace (per model): 1-5GB VRAM
  LRU Cache: Up to 5 HF models cached
  Total on GPU 2: ~10GB max

Throughput:
  Ollama: ~50 embeddings/second
  HuggingFace (batched): ~100-500 embeddings/second
```

**Model Selection Guide:**

```yaml
For General RAG:
  Recommended: stella (best quality)
  Alternative: nomic (faster)

For Long Documents:
  Recommended: nomic or qwen3 (8K tokens)
  Avoid: stella (512 token limit)

For Multilingual:
  Recommended: qwen3
  Alternative: nomic (limited multilingual)

For Speed:
  Recommended: gemma (fastest)
  Alternative: nomic

For Multimodal (Text + Images):
  Required: jasper
  Note: Requires image preprocessing
```

---

### 4.5 Tier 4: Playground

**Purpose:** An interactive and isolated development environment for developers to experiment with models, prototype RAG pipelines, and build new applications. It provides access to the shared GPU resources and data services without impacting the primary production tiers.

**Characteristics:**
- **User-Controlled Model Loading:** Users can dynamically load and unload any supported model (GGUF via Ollama, or HuggingFace formats via vLLM) onto the shared GPU pool (GPUs 2-7).
- **Isolated Dependencies:** The playground runs in a dedicated Docker container with a comprehensive set of pre-installed tools (LangChain, Transformers, PyTorch, etc.), ensuring that development work does not interfere with production container configurations.
- **Shared Workspace:** The entire project directory (`/mnt/ai8_arch`) is mounted, allowing seamless access to scripts, examples, and configuration files.
- **Automatic Resource Management:** Models loaded via Ollama use a default `keep_alive` of 5 minutes, automatically freeing up VRAM when idle. This is configurable.
- **No Performance Guarantees:** This tier is designed for functional testing, rapid prototyping, and debugging. Performance may vary based on shared resource contention.

#### 4.5.1 Playground Container

The playground environment is built from a dedicated Dockerfile that installs all necessary system packages, Python libraries, and CLI tools.

**Building the Image:**
The image must be built from the root of the project directory before use:
```bash
docker build -t ai8-playground:latest -f dockerfiles/Dockerfile.playground .
```

**Dockerfile Summary:** `/mnt/ai8_arch/dockerfiles/Dockerfile.playground`
```dockerfile
# Installs system dependencies, Python 3.11, and CUDA-enabled PyTorch
...
# Installs Ollama CLI and vLLM
RUN pip install vllm transformers langchain langchain-community "psycopg2-binary" qdrant-client pymongo redis
...
# Copies a custom .bashrc with helpful aliases and functions
COPY playground_bashrc /root/.bashrc
...
# Verifies GPU access
RUN python -c "import torch; print(f'PyTorch CUDA available: {torch.cuda.is_available()}')"
```

**Container Specification:**
```yaml
Image: ai8-playground:latest
Container Name: llm-playground
Network: llm-network
Profiles: ["playground"] # Must be explicitly started, e.g., docker compose up -d --profile playground

Volumes:
  - /mnt/ai8_arch:/mnt/ai8_arch # Mount entire project for access to scripts/data
  - /mnt/ai8_arch/models:/root/.ollama/models # Share Ollama models with other containers

GPU Access:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            capabilities: [gpu]
            device_ids: ['2','3','4','5','6','7'] # Access to all shared GPUs

Entrypoint: /bin/bash /mnt/ai8_arch/scripts/playground_entry.sh
  # Starts Ollama service in the background and provides an interactive shell
```

#### 4.5.2 Accessing the Playground

The playground is designed for interactive use.

**1. Start the Container:**
```bash
# The playground profile is not started by default
docker compose up -d --profile playground
```

**2. Attach an Interactive Shell:**
```bash
docker exec -it llm-playground bash
```
Upon entry, a welcome message displays available tools and common commands. The Ollama service is started automatically in the background.

#### 4.5.3 Connecting to Data Services

From within the playground container, other system services are accessible via their container names on the `llm-network`.

| Service | Hostname | Port | Example Client |
|---|---|---|---|
| **PostgreSQL** | `llm-postgres` | `5432` | `psql`, `psycopg2` |
| **Qdrant** | `llm-qdrant` | `6333` | `qdrant-client` |
| **MongoDB** | `llm-mongo` | `27017` | `pymongo` |
| **Redis** | `llm-redis` | `6379` | `redis-py` |

**Example: Connecting to Qdrant with Python**
```python
import qdrant_client

# Hostname is the service name from docker-compose.yaml
client = qdrant_client.QdrantClient(host="llm-qdrant", port=6333)
print("Qdrant collections:", client.get_collections())
```

#### 4.5.4 Example Workflows

**1. Interactive Model Testing with Ollama (for GGUF models)**
```bash
# Inside the playground container

# List models already downloaded to the shared volume
ollama list

# Pull a new model if needed
ollama pull llama3:8b

# Run the model interactively
ollama run llama3:8b "Why is the sky blue?"

# Clean up by removing the model (optional)
ollama rm llama3:8b
```

**2. Serving a Model with vLLM (for HuggingFace models)**

A helper function, `start-vllm`, is available in the shell to simplify serving.

```bash
# Usage: start-vllm <huggingface_model_id> <gpu_num> [tensor_parallel_size]
# Example: Serve a model on GPU #4
start-vllm HuggingFaceH4/zephyr-7b-beta 4

# In a separate terminal, test the vLLM endpoint
curl http://localhost:8000/v1/completions \
-H "Content-Type: application/json" \
-d '{
    "model": "HuggingFaceH4/zephyr-7b-beta",
    "prompt": "A robot may not injure a human being",
    "max_tokens": 7,
    "temperature": 0
}'
```

**3. RAG Pipeline Development**

Develop and test scripts that connect to the data layer and LLMs.

```bash
# 1. Create your Python script in the shared /mnt/ai8_arch/examples directory
#    (e.g., /mnt/ai8_arch/examples/my_rag_script.py)

# 2. Your script can connect to services using their hostnames (e.g., "llm-qdrant")

# 3. Run the script from inside the playground container
python /mnt/ai8_arch/examples/my_rag_script.py
```

**4. Using Jupyter Notebooks**

Jupyter Lab is pre-installed for browser-based development.

```bash
# Inside the playground container, start the server
jupyter lab --ip=0.0.0.0 --port=8888 --allow-root --no-browser

# The server will output a URL with a login token.
# Access it from your host machine's browser at:
# http://<server_ip>:8888/?token=...
```

---

## 5. Data Layer

### 5.1 Vector Databases

The AI8 Architecture provides two vector database options for different use cases:

#### 5.1.1 Qdrant

**Purpose:** High-performance vector similarity search for RAG.

**Why Qdrant?**
- Fast HNSW indexing
- Rich filtering capabilities
- HTTP and gRPC APIs
- Built-in dashboard
- Production-ready

**Container Specification:**
```yaml
Image: qdrant/qdrant:v1.7.0
Container Name: llm-qdrant
Ports: 6333 (HTTP), 6334 (gRPC)
Network: llm-network
Profiles: phase2, all

Environment Variables:
  QDRANT__SERVICE__GRPC_PORT: 6334
  QDRANT__SERVICE__HTTP_PORT: 6333
  QDRANT__LOG_LEVEL: INFO

Volumes:
  - /mnt/ai8_arch/data/qdrant:/qdrant/storage
    Purpose: Persistent vector storage

Health Check:
  Test: curl -f http://localhost:6333/healthz
  Interval: 30s
  Timeout: 10s
  Retries: 3

Restart Policy: unless-stopped
```

**Key Features:**
- **HNSW Indexing**: Fast approximate nearest neighbor search
- **Distance Metrics**: Cosine, Euclidean, Dot product
- **Payload Filtering**: Filter by metadata before vector search
- **Hybrid Search**: Combine dense + sparse vectors
- **Collections**: Organize vectors by namespace
- **Snapshots**: Built-in backup/restore

**API Usage Examples:**

```bash
# Create collection
curl -X PUT http://localhost:6333/collections/documents \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'

# Insert vectors
curl -X PUT http://localhost:6333/collections/documents/points \
  -H "Content-Type: application/json" \
  -d '{
    "points": [
      {
        "id": 1,
        "vector": [0.1, 0.2, 0.3, ...],  # 1024 dims
        "payload": {
          "text": "Document content here",
          "source": "file.pdf",
          "page": 1,
          "category": "technical"
        }
      }
    ]
  }'

# Search similar vectors
curl -X POST http://localhost:6333/collections/documents/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, 0.3, ...],
    "limit": 5,
    "with_payload": true,
    "with_vector": false
  }'

# Search with filtering
curl -X POST http://localhost:6333/collections/documents/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, 0.3, ...],
    "filter": {
      "must": [
        {"key": "category", "match": {"value": "technical"}}
      ]
    },
    "limit": 5
  }'

# Get collection info
curl http://localhost:6333/collections/documents

# List all collections
curl http://localhost:6333/collections

# Delete collection
curl -X DELETE http://localhost:6333/collections/documents
```

**Python Example:**

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Connect
client = QdrantClient(host="localhost", port=6333)

# Create collection
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
)

# Insert points
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=1,
            vector=[0.1, 0.2, 0.3, ...],  # 1024 dims
            payload={
                "text": "Document content",
                "source": "file.pdf",
                "category": "technical"
            }
        )
    ]
)

# Search
results = client.search(
    collection_name="documents",
    query_vector=[0.1, 0.2, 0.3, ...],
    limit=5,
    query_filter={
        "must": [
            {"key": "category", "match": {"value": "technical"}}
        ]
    }
)

for result in results:
    print(f"Score: {result.score}, Text: {result.payload['text']}")
```

**Dashboard Access:**
- URL: http://localhost:6333/dashboard
- Features: Browse collections, inspect points, test searches

**Performance Characteristics:**
```yaml
Search Latency:
  - Small collection (<10K vectors): <5ms
  - Medium collection (<1M vectors): <20ms
  - Large collection (>1M vectors): <50ms

Indexing:
  - HNSW build time: ~1ms per 1000 vectors
  - Real-time updates: Yes

Memory Usage:
  - ~4 bytes per dimension per vector
  - 1M vectors × 1024 dims = ~4GB

Scalability:
  - Billions of vectors supported
  - Horizontal scaling via clustering
```

---

#### 5.1.2 pgvector (PostgreSQL)

**Purpose:** SQL-based vector storage with relational capabilities.

**Why pgvector?**
- ACID compliance
- SQL familiarity
- Join with relational data
- Transaction support
- Mature tooling

**Container Specification:**
```yaml
Image: pgvector/pgvector:pg16
Container Name: llm-pgvector
Port: 5433 (mapped to avoid conflict)
Network: llm-network
Profiles: phase2, all

Environment Variables:
  POSTGRES_USER: ${POSTGRES_USER:-llmuser}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-llmpassword}
  POSTGRES_DB: vectors

Volumes:
  - /mnt/ai8_arch/data/pgvector:/var/lib/postgresql/data
  - /mnt/ai8_arch/scripts/init-pgvector.sh:/docker-entrypoint-initdb.d/init-pgvector.sh:ro

Health Check:
  Test: pg_isready -U llmuser -d vectors
  Interval: 10s
  Timeout: 5s
  Retries: 5

Restart Policy: unless-stopped
```

**Initialization Script:**

File: `/mnt/ai8_arch/scripts/init-pgvector.sh`

```bash
#!/bin/bash
set -euo pipefail

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "🔧 pgvector initialization starting..."

# Enable vector extension
log "Enabling vector extension..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
  CREATE EXTENSION IF NOT EXISTS vector;
  
  -- Document embeddings table
  CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
  );
  
  -- HNSW index for fast similarity search
  CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx 
  ON document_embeddings USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  
  -- Standard indexes
  CREATE INDEX IF NOT EXISTS document_embeddings_doc_id_idx 
  ON document_embeddings(document_id);
  
  CREATE INDEX IF NOT EXISTS document_embeddings_created_at_idx 
  ON document_embeddings(created_at DESC);
  
  -- Metadata GIN index
  CREATE INDEX IF NOT EXISTS document_embeddings_metadata_idx 
  ON document_embeddings USING gin (metadata);
  
  -- Document metadata table
  CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(255) PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    filetype VARCHAR(50),
    size_bytes BIGINT,
    num_chunks INTEGER DEFAULT 0,
    embedding_model VARCHAR(100),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
  );
  
  -- Helper function: similarity search
  CREATE OR REPLACE FUNCTION search_similar_embeddings(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10
  )
  RETURNS TABLE (
    document_id VARCHAR(255),
    chunk_index INTEGER,
    content TEXT,
    similarity float,
    metadata JSONB
  ) AS \$\$
  BEGIN
    RETURN QUERY
    SELECT 
      de.document_id,
      de.chunk_index,
      de.content,
      1 - (de.embedding <=> query_embedding) as similarity,
      de.metadata
    FROM document_embeddings de
    WHERE 1 - (de.embedding <=> query_embedding) > match_threshold
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
  END;
  \$\$ LANGUAGE plpgsql;
  
  -- Helper function: get document chunks
  CREATE OR REPLACE FUNCTION get_document_chunks(doc_id VARCHAR(255))
  RETURNS TABLE (
    chunk_index INTEGER,
    content TEXT,
    metadata JSONB
  ) AS \$\$
  BEGIN
    RETURN QUERY
    SELECT 
      de.chunk_index,
      de.content,
      de.metadata
    FROM document_embeddings de
    WHERE de.document_id = doc_id
    ORDER BY de.chunk_index;
  END;
  \$\$ LANGUAGE plpgsql;
  
  -- Grant permissions
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;
  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $POSTGRES_USER;
  GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO $POSTGRES_USER;
EOSQL

log "✅ pgvector initialization complete"
```

**API Usage Examples:**

```sql
-- Insert embedding
INSERT INTO document_embeddings (document_id, chunk_index, content, embedding, metadata)
VALUES (
  'doc1',
  0,
  'Sample text content',
  '[0.1, 0.2, 0.3, ...]'::vector(1024),
  '{"source": "file.pdf", "page": 1}'::jsonb
);

-- Similarity search (cosine distance)
SELECT 
  document_id,
  content,
  1 - (embedding <=> '[0.1, 0.2, 0.3, ...]'::vector) as similarity
FROM document_embeddings
ORDER BY embedding <=> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;

-- Using helper function
SELECT * FROM search_similar_embeddings(
  '[0.1, 0.2, 0.3, ...]'::vector(1024),
  0.7,  -- threshold
  10    -- limit
);

-- Filter by metadata
SELECT * FROM document_embeddings
WHERE metadata->>'category' = 'technical'
ORDER BY embedding <=> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;

-- Join with document metadata
SELECT 
  de.content,
  d.filename,
  1 - (de.embedding <=> '[0.1, 0.2, 0.3, ...]'::vector) as similarity
FROM document_embeddings de
JOIN documents d ON de.document_id = d.id
ORDER BY de.embedding <=> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;
```

**Python Example:**

```python
import psycopg2
from psycopg2.extras import execute_values
import numpy as np

# Connect
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="vectors",
    user="llmuser",
    password="llmpassword"
)
cur = conn.cursor()

# Insert embeddings
embedding = np.random.rand(1024).tolist()
cur.execute("""
    INSERT INTO document_embeddings (document_id, chunk_index, content, embedding)
    VALUES (%s, %s, %s, %s)
""", ('doc1', 0, 'Sample text', str(embedding)))
conn.commit()

# Search similar
query_embedding = np.random.rand(1024).tolist()
cur.execute("""
    SELECT document_id, content, 
           1 - (embedding <=> %s::vector) as similarity
    FROM document_embeddings
    ORDER BY embedding <=> %s::vector
    LIMIT 5
""", (str(query_embedding), str(query_embedding)))

results = cur.fetchall()
for doc_id, content, similarity in results:
    print(f"Doc: {doc_id}, Similarity: {similarity:.3f}")
    print(f"Content: {content[:100]}...")

cur.close()
conn.close()
```

**Performance Characteristics:**
```yaml
Search Latency:
  - HNSW index: 10-50ms (depending on size)
  - IVFFlat index: 50-200ms
  - Brute force: 100ms-10s (not recommended)

Indexing:
  - HNSW build: Slow (hours for millions of vectors)
  - Best practice: Build index AFTER bulk insert

Memory Usage:
  - Similar to Qdrant: ~4 bytes per dimension
  - Plus PostgreSQL overhead: ~20-30% more

Scalability:
  - Millions of vectors: Good
  - Billions of vectors: Use Qdrant instead
```

**Comparison: Qdrant vs pgvector**

| Feature | Qdrant | pgvector |
|---------|--------|----------|
| **Performance** | Faster (optimized for vectors) | Slower (general DB) |
| **Scalability** | Billions of vectors | Millions of vectors |
| **ACID** | Eventually consistent | Fully ACID |
| **SQL** | No | Yes |
| **Joins** | No | Yes (with relational data) |
| **Ease of Use** | Simple API | SQL knowledge required |
| **Use Case** | Pure vector search | Vectors + relational data |

**Recommendation:**
- Use **Qdrant** for: Pure vector search, large scale (>10M vectors), best performance
- Use **pgvector** for: Vectors + relational data, transactions, SQL analytics

---

### 5.2 Document Store (MongoDB)

**Purpose:** Store document metadata, unstructured data, flexible schemas.

**Why MongoDB?**
- Flexible schema (JSON documents)
- Rich query language
- Aggregation framework
- Horizontal scalability
- Developer-friendly

**Container Specification:**
```yaml
Image: mongo:7.0
Container Name: llm-mongodb
Port: 27017
Network: llm-network
Profiles: phase2, all

Environment Variables:
  MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER:-admin}
  MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:-mongopassword}
  MONGO_INITDB_DATABASE: rag_documents

Volumes:
  - /mnt/ai8_arch/data/mongodb:/data/db
  - /mnt/ai8_arch/data/mongodb_config:/data/configdb

Health Check:
  Test: mongosh --eval "db.adminCommand('ping')"
  Interval: 30s
  Timeout: 10s
  Retries: 3

Restart Policy: unless-stopped
```

**Use Cases:**

**1. Document Metadata:**
```javascript
{
  "_id": "doc_123",
  "filename": "technical_report.pdf",
  "upload_timestamp": ISODate("2025-01-15T00:00:00Z"),
  "size_bytes": 1048576,
  "num_pages": 42,
  "num_chunks": 156,
  "embedding_model": "stella",
  "vector_db": "qdrant",
  "collection_name": "technical_docs",
  "metadata": {
    "author": "John Doe",
    "department": "Engineering",
    "confidential": false,
    "tags": ["technical", "Q1-2025", "AI"],
    "language": "en"
  },
  "processing": {
    "status": "completed",
    "started_at": ISODate("2025-01-15T00:00:00Z"),
    "completed_at": ISODate("2025-01-15T00:05:30Z"),
    "duration_seconds": 330
  }
}
```

**2. RAG Pipeline State:**
```javascript
{
  "_id": "pipeline_456",
  "name": "Document Ingestion Pipeline",
  "status": "processing",
  "stage": "embedding_generation",
  "documents_processed": 10,
  "documents_total": 50,
  "documents_failed": 1,
  "errors": [
    {
      "document_id": "doc_7",
      "error": "PDF parsing failed",
      "timestamp": ISODate("2025-01-15T00:10:00Z")
    }
  ],
  "started_at": ISODate("2025-01-15T00:00:00Z"),
  "updated_at": ISODate("2025-01-15T00:15:00Z")
}
```

**3. User Conversations:**
```javascript
{
  "_id": "conv_789",
  "user_id": "user_123",
  "title": "Discussion about AI",
  "messages": [
    {
      "role": "user",
      "content": "What is machine learning?",
      "timestamp": ISODate("2025-01-15T10:00:00Z")
    },
    {
      "role": "assistant",
      "content": "Machine learning is...",
      "timestamp": ISODate("2025-01-15T10:00:02Z"),
      "model": "gpt-oss-120b",
      "tokens": {
        "prompt": 15,
        "completion": 85
      }
    }
  ],
  "created_at": ISODate("2025-01-15T10:00:00Z"),
  "updated_at": ISODate("2025-01-15T10:00:02Z")
}
```

**API Usage Examples:**

```bash
# Connect to MongoDB
mongosh mongodb://admin:mongopassword@localhost:27017

# Use database
use rag_documents

# Insert document
db.documents.insertOne({
  document_id: "doc1",
  filename: "sample.pdf",
  num_chunks: 10,
  uploaded_at: new Date()
})

# Query documents
db.documents.find({filename: /\.pdf$/})

# Query with filter
db.documents.find({
  "metadata.department": "Engineering",
  "processing.status": "completed"
})

# Aggregation
db.documents.aggregate([
  {$match: {"metadata.department": "Engineering"}},
  {$group: {_id: "$metadata.author", count: {$sum: 1}}},
  {$sort: {count: -1}}
])

# Update document
db.documents.updateOne(
  {document_id: "doc1"},
  {$set: {"processing.status": "completed"}}
)

# Delete document
db.documents.deleteOne({document_id: "doc1"})
```

**Python Example:**

```python
from pymongo import MongoClient
from datetime import datetime

# Connect
client = MongoClient("mongodb://admin:mongopassword@localhost:27017/")
db = client.rag_documents

# Insert document
doc = {
    "document_id": "doc1",
    "filename": "report.pdf",
    "num_chunks": 50,
    "metadata": {
        "author": "John Doe",
        "department": "Engineering"
    },
    "uploaded_at": datetime.utcnow()
}
result = db.documents.insert_one(doc)
print(f"Inserted ID: {result.inserted_id}")

# Query
docs = db.documents.find({"metadata.department": "Engineering"})
for doc in docs:
    print(f"File: {doc['filename']}, Chunks: {doc['num_chunks']}")

# Aggregation
pipeline = [
    {"$match": {"metadata.department": "Engineering"}},
    {"$group": {"_id": "$metadata.author", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]
results = db.documents.aggregate(pipeline)
for result in results:
    print(f"Author: {result['_id']}, Documents: {result['count']}")

# Update
db.documents.update_one(
    {"document_id": "doc1"},
    {"$set": {"processing.status": "completed"}}
)

# Delete
db.documents.delete_one({"document_id": "doc1"})
```

**Indexes for Performance:**

```javascript
// Create indexes
db.documents.createIndex({document_id: 1}, {unique: true})
db.documents.createIndex({"metadata.department": 1})
db.documents.createIndex({uploaded_at: -1})
db.documents.createIndex({"metadata.tags": 1})

// Compound index
db.documents.createIndex({
  "metadata.department": 1,
  "processing.status": 1
})

// Text search index
db.documents.createIndex({
  filename: "text",
  "metadata.author": "text"
})

// Use text search
db.documents.find({$text: {$search: "technical report"}})
```

---

### 5.3 Cache (Redis)

**Purpose:** High-speed caching for LLM responses, embeddings, session data.

**Why Redis?**
- Extremely fast (sub-millisecond)
- Rich data structures
- TTL support
- Pub/Sub messaging
- Persistence options

**Container Specification:**
```yaml
Image: redis:7-alpine
Container Name: llm-redis
Port: 6379
Network: llm-network
Profiles: phase2, all

Command:
  redis-server
  --appendonly yes
  --requirepass ${REDIS_PASSWORD:-redispassword}

Volumes:
  - /mnt/ai8_arch/data/redis:/data

Health Check:
  Test: redis-cli --raw incr ping
  Interval: 30s
  Timeout: 10s
  Retries: 3

Restart Policy: unless-stopped
```

**Use Cases:**

**1. LLM Response Caching:**
```python
import redis
import hashlib
import json

r = redis.Redis(host='localhost', port=6379, password='redispassword', decode_responses=True)

def get_llm_response(prompt, model="gpt-oss-120b"):
    # Generate cache key
    cache_key = f"llm:{model}:{hashlib.sha256(prompt.encode()).hexdigest()}"
    
    # Check cache
    cached = r.get(cache_key)
    if cached:
        print("Cache hit!")
        return json.loads(cached)
    
    # Generate response (simulated)
    print("Cache miss, generating response...")
    response = {
        "model": model,
        "prompt": prompt,
        "response": "Generated response here...",
        "tokens": 50
    }
    
    # Cache for 1 hour
    r.setex(cache_key, 3600, json.dumps(response))
    
    return response

# Usage
response = get_llm_response("What is 2+2?")
print(response)

# Second call will hit cache
response = get_llm_response("What is 2+2?")
```

**2. Embedding Cache:**
```python
def get_embedding(text, model="stella"):
    # Generate cache key
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    cache_key = f"embed:{model}:{text_hash}"
    
    # Check cache
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Generate embedding (call embedding service)
    import requests
    response = requests.post(
        "http://localhost:8010/v1/embeddings",
        json={"model": model, "input": text}
    )
    embedding = response.json()["embeddings"][0]
    
    # Cache for 24 hours
    r.setex(cache_key, 86400, json.dumps(embedding))
    
    return embedding
```

**3. Rate Limiting:**
```python
def check_rate_limit(user_id, limit=1000, window=86400):
    """
    Check if user has exceeded rate limit
    limit: max requests
    window: time window in seconds (default: 24 hours)
    """
    key = f"ratelimit:{user_id}:{datetime.now().strftime('%Y%m%d')}"
    
    # Increment counter
    count = r.incr(key)
    
    # Set expiration on first request
    if count == 1:
        r.expire(key, window)
    
    if count > limit:
        raise Exception(f"Rate limit exceeded: {count}/{limit}")
    
    return count

# Usage
try:
    requests_today = check_rate_limit("user_123", limit=1000)
    print(f"Requests today: {requests_today}/1000")
except Exception as e:
    print(f"Error: {e}")
```

**4. Session Management:**
```python
def create_session(user_id, data, ttl=3600):
    """Create user session"""
    session_id = str(uuid.uuid4())
    session_key = f"session:{session_id}"
    
    session_data = {
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        **data
    }
    
    r.setex(session_key, ttl, json.dumps(session_data))
    return session_id

def get_session(session_id):
    """Get session data"""
    session_key = f"session:{session_id}"
    data = r.get(session_key)
    return json.loads(data) if data else None

def delete_session(session_id):
    """Delete session"""
    r.delete(f"session:{session_id}")

# Usage
session_id = create_session("user_123", {"authenticated": True, "role": "admin"})
print(f"Session ID: {session_id}")

session_data = get_session(session_id)
print(f"Session data: {session_data}")
```

**5. Pub/Sub for Real-time Updates:**
```python
# Publisher (send updates)
import redis

r = redis.Redis(host='localhost', port=6379, password='redispassword')

def notify_document_processed(doc_id):
    r.publish('document_updates', json.dumps({
        'event': 'document_processed',
        'document_id': doc_id,
        'timestamp': datetime.utcnow().isoformat()
    }))

# Subscriber (receive updates)
import redis

r = redis.Redis(host='localhost', port=6379, password='redispassword', decode_responses=True)
pubsub = r.pubsub()
pubsub.subscribe('document_updates')

print("Listening for document updates...")
for message in pubsub.listen():
    if message['type'] == 'message':
        data = json.loads(message['data'])
        print(f"Document {data['document_id']} processed at {data['timestamp']}")
```

**LangChain Integration:**

```python
from langchain.cache import RedisCache
from langchain.globals import set_llm_cache
from langchain_community.llms import Ollama
import redis

# Set up Redis cache
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    password='redispassword',
    decode_responses=True
)
set_llm_cache(RedisCache(redis_client))

# Use LLM (automatically cached)
llm = Ollama(model="llama2", base_url="http://localhost:11601")

# First call (cache miss)
response1 = llm.invoke("What is 2+2?")
print(response1)  # Takes 2-3 seconds

# Second call (cache hit)
response2 = llm.invoke("What is 2+2?")
print(response2)  # Instant!
```

**Redis Commands Reference:**

```bash
# Connect
redis-cli -a redispassword

# String operations
SET key value
GET key
SETEX key 3600 value  # Set with TTL (seconds)
INCR counter          # Increment
DECR counter          # Decrement

# Hash operations (for objects)
HSET user:123 name "John" email "john@example.com"
HGET user:123 name
HGETALL user:123
HDEL user:123 email

# List operations
LPUSH queue task1
RPUSH queue task2
LPOP queue
LRANGE queue 0 -1

# Set operations
SADD tags:doc1 "AI" "ML" "DL"
SMEMBERS tags:doc1
SISMEMBER tags:doc1 "AI"

# Sorted set (leaderboard)
ZADD leaderboard 100 "user1" 200 "user2"
ZRANGE leaderboard 0 -1 WITHSCORES
ZRANK leaderboard "user1"

# Key management
KEYS *           # List all keys (use with caution in production)
DEL key          # Delete key
EXISTS key       # Check if key exists
TTL key          # Check TTL
EXPIRE key 3600  # Set TTL

# Pub/Sub
PUBLISH channel message
SUBSCRIBE channel

# Admin
INFO             # Server info
DBSIZE           # Number of keys
FLUSHDB          # Clear current database (⚠️ dangerous)
```

**Performance Characteristics:**
```yaml
Latency:
  - GET: <1ms
  - SET: <1ms
  - Complex operations: 1-5ms

Throughput:
  - 100,000+ ops/second (single instance)
  - Millions of ops/second (clustered)

Memory:
  - In-memory: Very fast, limited by RAM
  - With persistence: Slightly slower writes

Use Cases by TTL:
  - No TTL: Permanent cache (user preferences)
  - 1-60s: Real-time data (live metrics)
  - 1-60min: Session data
  - 1-24hr: LLM responses, embeddings
  - Days: Long-term cache
```

---

## 6. Monitoring & Observability

### 6.1 Metrics Architecture

**Three-Layer Approach:**

```
Layer 1: Collectors (Exporters)
  ↓
  - NVIDIA GPU Exporter (GPU metrics)
  - LiteLLM (API metrics)
  - vLLM (Inference metrics)
  - Embeddings Service (Embedding metrics)
  - Qdrant (Vector DB metrics)
  
Layer 2: Aggregator (Prometheus)
  ↓
  - Scrapes all exporters every 15s
  - Stores 30 days of time-series data
  - Evaluates alert rules
  - Exposes PromQL API
  
Layer 3: Visualization (Grafana)
  ↓
  - Queries Prometheus
  - Renders dashboards
  - Sends alerts
  - User interface
```

### 6.2 Key Metrics to Monitor

**GPU Metrics:**
```yaml
Critical:
  - nvidia_gpu_duty_cycle: GPU utilization (target: 70-90%)
  - nvidia_gpu_memory_used_bytes: VRAM usage (alert: >95%)
  - nvidia_gpu_temperature_celsius: Temperature (alert: >85°C)

Important:
  - nvidia_gpu_power_usage_milliwatts: Power draw
  - nvidia_gpu_fan_speed_percent: Cooling

Alerts:
  - Temperature > 85°C for 5 minutes
  - VRAM > 95% for 2 minutes
  - Utilization < 10% for 30 minutes (underutilization)
```

**API Metrics:**
```yaml
Critical:
  - litellm_requests_total: Request count
  - litellm_request_duration_seconds: Latency (p50, p95, p99)
  - litellm_errors_total: Error count

Important:
  - litellm_tokens_generated_total: Token throughput
  - litellm_concurrent_requests: Concurrent load

Alerts:
  - Error rate > 5% for 3 minutes
  - p95 latency > 10s for 5 minutes
  - No requests for 10 minutes (service down?)
```

**Model Metrics:**
```yaml
Critical:
  - vllm_tokens_generated_total: Token generation rate
  - vllm_num_requests_waiting: Queue depth (alert: >10)
  - vllm_gpu_cache_usage_perc: KV cache usage

Important:
  - vllm_num_requests_running: Active requests
  - Model-specific latency

Alerts:
  - Queue depth > 10 for 3 minutes
  - Cache usage > 90%
  - No token generation for 5 minutes
```

**Database Metrics:**
```yaml
Important:
  - qdrant_collections_points_count: Vector count
  - qdrant_search_duration_seconds: Search latency
  - PostgreSQL connections
  - MongoDB operations per second

Alerts:
  - Search latency > 100ms
  - Database connection failures
```

### 6.3 Grafana Dashboard Panels

**Recommended Dashboard Layout:**

```
Row 1: System Overview
  - Total GPU Utilization (Gauge)
  - Total VRAM Usage (Gauge)
  - API Request Rate (Graph)
  - Error Rate (Graph)

Row 2: GPU Details
  - GPU Utilization per GPU (Graph)
  - VRAM Usage per GPU (Graph)
  - GPU Temperature (Graph)
  - GPU Power Usage (Graph)

Row 3: API Performance
  - Requests per Model (Bar Chart)
  - Latency Distribution (Heatmap)
  - Error Breakdown (Pie Chart)
  - Concurrent Requests (Graph)

Row 4: Model Performance
  - Tokens per Second (Graph)
  - Queue Depth (Graph)
  - Model Status (Table)

Row 5: Database Performance
  - Vector Search Latency (Graph)
  - Database Operations (Graph)
  - Cache Hit Rate (Gauge)
```

### 6.4 Alerting Strategy

**Priority Levels:**

**P0 (Critical - Immediate Action):**
- All services down
- GPU temperature > 90°C
- VRAM exhausted (OOM imminent)
- Error rate > 50%

**P1 (High - Action within 1 hour):**
- Single service down
- GPU temperature > 85°C
- VRAM > 95%
- Error rate > 10%
- p99 latency > 30s

**P2 (Medium - Action within 4 hours):**
- High queue depth (>10)
- GPU underutilization (<10%)
- Cache issues
- Error rate > 5%

**P3 (Low - Review next day):**
- Minor performance degradation
- Disk space warnings
- Unusual patterns

**Alert Channels:**
```yaml
Console: All alerts logged
Email: P0, P1 alerts
Slack: P0, P1 alerts
PagerDuty: P0 alerts only
```

---

## 7. User Interfaces

### 7.1 OpenWebUI

**Purpose:** Modern chat interface for LLM interaction.

**Container Specification:**
```yaml
Image: ghcr.io/open-webui/open-webui:main
Container Name: llm-openwebui
Port: 5151 (mapped from 8080)
Network: llm-network
Profiles: phase4, all

Environment Variables:
  OPENAI_API_BASE_URL: http://litellm:4000/v1
  OPENAI_API_KEY: ${LITELLM_MASTER_KEY}
  WEBUI_AUTH: true
  ENABLE_OLLAMA_API: false
  ENABLE_OPENAI_API: true

Volumes:
  - /mnt/ai8_arch/data/openwebui/data:/app/backend/data

Dependencies:
  - litellm

Restart Policy: unless-stopped
```

**Features:**
- Modern chat interface
- Model selection dropdown
- Conversation history
- Markdown rendering
- Code syntax highlighting
- Multi-user support
- User authentication
- Conversation export

**Setup:**
1. Navigate to http://localhost:5151
2. Create admin account (first user)
3. API settings auto-configured
4. Select model and start chatting

**Configuration:**
- Models: Auto-populated from LiteLLM
- Settings: Temperature, max tokens, system prompt
- Themes: Light/dark mode
- Users: Admin can manage users

---

### 7.2 n8n

**Purpose:** Workflow automation with LLM integration.

**Container Specification:**
```yaml
Image: n8nio/n8n:latest
Container Name: llm-n8n
Port: 5678
Network: llm-network
Profiles: phase4, all

Environment Variables:
  N8N_BASIC_AUTH_ACTIVE: true
  N8N_BASIC_AUTH_USER: admin
  N8N_BASIC_AUTH_PASSWORD: ${N8N_PASSWORD}
  N8N_HOST: 0.0.0.0
  N8N_PORT: 5678
  N8N_PROTOCOL: http
  WEBHOOK_URL: http://ai8:5678
  GENERIC_TIMEZONE: America/New_York
  DB_TYPE: postgresdb
  DB_POSTGRESDB_HOST: postgres
  DB_POSTGRESDB_PORT: 5432
  DB_POSTGRESDB_DATABASE: n8n
  DB_POSTGRESDB_USER: ${POSTGRES_USER}
  DB_POSTGRESDB_PASSWORD: ${POSTGRES_PASSWORD}
  N8N_OPENAI_API_BASE_URL: http://litellm:4000/v1

Volumes:
  - /mnt/ai8_arch/data/n8n:/home/node/.n8n
  - /mnt/ai8_arch/n8n/workflows:/home/node/.n8n/workflows

Dependencies:
  - postgres (health check)
  - litellm (health check)

Restart Policy: unless-stopped
```

**Use Cases:**

**1. Document Processing Pipeline:**
```
Webhook Trigger
  ↓
Parse PDF
  ↓
Chunk Text
  ↓
Generate Embeddings (HTTP Request to embeddings service)
  ↓
Store in Qdrant (HTTP Request)
  ↓
Update MongoDB Metadata
  ↓
Send Notification
```

**2. Scheduled RAG Updates:**
```
Schedule Trigger (Daily)
  ↓
Fetch New Documents (SFTP/HTTP)
  ↓
Process Each Document (Loop)
  ↓
Update Vector Database
  ↓
Send Report Email
```

**3. LLM-Powered Form Processing:**
```
Webhook (Form Submission)
  ↓
Extract Form Data
  ↓
Call LLM for Analysis (HTTP Request to LiteLLM)
  ↓
Parse LLM Response
  ↓
Update CRM (HTTP Request)
  ↓
Send Confirmation Email
```

**Setup:**
1. Navigate to http://localhost:5678
2. Login: admin / (N8N_PASSWORD from .env)
3. Create workflow
4. Add nodes (Webhook, HTTP Request, etc.)
5. Configure LLM node:
   - URL: http://litellm:4000/v1/chat/completions
   - Method: POST
   - Headers: Authorization: Bearer ${LITELLM_MASTER_KEY}
   - Body: {"model": "gpt-oss-120b", "messages": [...]}

---

## 8. API Specifications

### 8.1 OpenAI-Compatible Endpoints

All models accessible via LiteLLM Gateway at http://localhost:4000

**Authentication:**
```bash
# All requests require Bearer token
Authorization: Bearer sk-llm-master-key-2025
```

**Endpoints:**

**1. List Models**
```
GET /v1/models
```

Response:
```json
{
  "data": [
    {"id": "gpt-oss-120b", "object": "model", "owned_by": "ai8"},
    {"id": "qwen3-vl-235b", "object": "model", "owned_by": "ai8"},
    {"id": "deepseek-r1-671b", "object": "model", "owned_by": "ai8"}
  ]
}
```

**2. Chat Completions**
```
POST /v1/chat/completions
```

Request:
```json
{
  "model": "gpt-oss-120b",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2+2?"}
  ],
  "temperature": 0.7,
  "max_tokens": 100,
  "stream": false
}
```

Response:
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1704931200,
  "model": "gpt-oss-120b",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "2+2 equals 4."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 5,
    "total_tokens": 25
  }
}
```

**3. Embeddings**
```
POST /v1/embeddings
```

Request:
```json
{
  "model": "nomic-embed",
  "input": ["Text to embed", "Another text"]
}
```

Response:
```json
{
  "data": [
    {
      "object": "embedding",
      "embedding": [0.023, -0.009, ...],  // 768 dimensions
      "index": 0
    },
    {
      "object": "embedding",
      "embedding": [0.012, -0.034, ...],
      "index": 1
    }
  ],
  "model": "nomic-embed",
  "usage": {"prompt_tokens": 10, "total_tokens": 10}
}
```

### 8.2 Rate Limits

**Current Setup:** No limits by default

**To Enable:**
Edit `config/litellm_config.yaml`:
```yaml
router_settings:
  rpm: 100        # Requests per minute
  tpm: 10000      # Tokens per minute
```

### 8.3 Error Codes

| Code | Meaning | Common Cause |
|------|---------|--------------|
| 400 | Bad Request | Invalid JSON, missing field |
| 401 | Unauthorized | Invalid/missing API key |
| 404 | Not Found | Model doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Model error, service crash |
| 503 | Service Unavailable | Model loading, overloaded |
| 504 | Gateway Timeout | Model took too long |

---

## 9. Deployment Strategy

The deployment strategy for the AI8 Architecture is designed to be systematic, verifiable, and modular. It is broken down into four distinct phases, allowing for a controlled and incremental setup. This approach ensures that foundational services are stable before dependent components are brought online, simplifying troubleshooting and validation.

For a comprehensive, step-by-step guide with all necessary commands, configuration details, and verification checks, refer to the detailed deployment manual:

**Primary Deployment Document:** [`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md)

### 9.1 Phased Rollout

The deployment process is organized into the following phases:

1.  **Phase 1: Foundation** - Deploys the core infrastructure, including monitoring (Prometheus, Grafana), the central database (PostgreSQL), and the API gateway (LiteLLM).
2.  **Phase 2: Data Layer** - Activates the databases required for RAG and data persistence, including Qdrant, pgvector, MongoDB, and Redis.
3.  **Phase 3: Model Services** - Builds and deploys the AI models, including the embedding service and both primary (persistent) and secondary (on-demand) LLMs. This phase is the most time and resource-intensive.
4.  **Phase 4: User Interfaces** - Deploys the user-facing applications, such as OpenWebUI for chat, n8n for workflow automation, and the Playground for experimentation.

This phased approach is orchestrated by the `deploy.sh` script, which can execute the entire deployment at once or phase by phase for a more controlled setup.

### 9.2 Verification and Testing

After each phase, the `test_deployment.sh` script should be used to validate that all services are running correctly and are properly configured. This ensures that any issues are caught early before proceeding to the next phase.

### 9.3 Rollback and Recovery

The system is designed for straightforward rollbacks. In case of a deployment failure, the general procedure involves stopping the services, restoring the last known good configuration from backups, and restarting the system. Detailed instructions for rollback and disaster recovery are available in the [`DEPLOYMENT.md`](../docs/DEPLOYMENT.md) document.

---

## 10. Security & Authentication

### 10.1 API Security

**LiteLLM:**
- Bearer token authentication (LITELLM_MASTER_KEY)
- Per-key rate limiting (optional)
- Request logging to database

**OpenWebUI:**
- Username/password authentication
- Session-based
- Multi-user support

**n8n:**
- Basic authentication
- API keys for webhooks

### 10.2 Audit Logging

**Application Logs:**
```yaml
Location: /mnt/ai8_arch/logs/
Retention: 30 days (configurable)
Format: Structured JSON
```

**Access Logs:**
- LiteLLM: All API requests logged to PostgreSQL
- OpenWebUI: User actions logged
- n8n: Workflow executions logged

---

## 11. Performance Requirements

### 11.1 Latency Targets

**Primary Models:**
- TTFT: <100ms
- Tokens/second: 50-100
- Concurrent requests: 4-8 per model

**Secondary Models:**
- Cold start: 10-30s
- Warm TTFT: <500ms
- Tokens/second: 30-80

**Embeddings:**
- Single text: 50-200ms
- Batch (10): 500ms-2s

### 11.2 Throughput

**Theoretical Maximum:**
- Primary models: ~400 tokens/s aggregate
- Secondary models: ~200 tokens/s (when loaded)
- Embeddings: ~1000 embeddings/s

**Realistic Sustained (10 users):**
- ~200 tokens/s aggregate
- ~500 embeddings/s
- ~50 requests/minute to secondaries

---

## 12. Operational Procedures

### 12.1 Daily Operations

```bash
# Check service health
docker compose ps
./test_deployment.sh

# Monitor GPU usage
nvidia-smi

# Check disk space
df -h /mnt
```

### 12.2 Weekly Operations

```bash
# Update images
docker compose pull

# Clean up unused data
docker system prune -f

# Check logs for errors
docker compose logs --since 7d | grep -i error

# Verify backups
ls -lh /mnt/ai8_arch/backups/
```

### 12.3 Monthly Operations

```bash
# Update models
docker exec primary-gpt-oss ollama pull gpt-oss:120b

# Update system packages
sudo apt update && sudo apt upgrade

# Review and rotate logs
find /mnt/ai8_arch/logs -type f -mtime +30 -delete

# Full backup
./backup_config.sh
```

---

## 13. Testing & Validation

### 13.1 Automated Testing

```bash
# Run test suite
./test_deployment.sh

# Tests included:
# - Service health checks
# - API endpoint validation
# - Database connectivity
# - GPU availability
# - Model loading
# - Integration tests
```

### 13.2 Manual Testing

```bash
# Test LiteLLM
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-llm-master-key-2025" \
  -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"Test"}]}'

# Test embeddings
curl -X POST http://localhost:8010/v1/embeddings \
  -d '{"model":"nomic","input":"test"}'

# Test Qdrant
curl http://localhost:6333/collections

# Test pgvector
docker exec llm-pgvector psql -U llmuser -d vectors -c "SELECT 1"
```

---

## 14. Documentation Requirements

### 14.1 Required Documentation

- ✅ README.md (overview)
- ✅ ARCHITECTURE.md (system design)
- ✅ DEPLOYMENT.md (deployment guide)
- ✅ RAG_SETUP.md (RAG pipelines)
- ✅ TROUBLESHOOTING.md (common issues)
- ✅ API_REFERENCE.md (API documentation)
- ✅ QUICKSTART.md (quick start guide)

### 14.2 Code Documentation

- All scripts have header comments
- All functions have docstrings
- Configuration files have inline comments
- Docker files have LABEL metadata

---

## 15. Future Enhancements

### 15.1 Short Term (1-3 months)

- [ ] Reverse proxy with TLS (Traefik/Nginx)
- [ ] Alert manager integration (email/Slack)
- [ ] Automated model updates
- [ ] Enhanced Grafana dashboards
- [ ] User quotas and rate limiting

### 15.2 Medium Term (3-6 months)

- [ ] Multi-node deployment support
- [ ] Model fine-tuning pipeline
- [ ] Advanced RAG (hybrid search, re-ranking)
- [ ] Custom model training pipeline
- [ ] API usage analytics dashboard

### 15.3 Long Term (6+ months)

- [ ] Kubernetes deployment option
- [ ] Model marketplace integration
- [ ] Multi-tenant isolation
- [ ] Distributed inference
- [ ] Edge deployment support

---

## Appendix A: Environment Variables

Complete `.env.template`:

```bash
# HuggingFace
HF_TOKEN=hf_xxxxxxxxxxxxx

# PostgreSQL
POSTGRES_USER=llmuser
POSTGRES_PASSWORD=securepassword123

# MongoDB
MONGO_USER=admin
MONGO_PASSWORD=securepassword456

# Redis
REDIS_PASSWORD=securepassword789

# LiteLLM
LITELLM_MASTER_KEY=sk-llm-master-key-2025-your-secure-key-here

# Grafana
GRAFANA_ADMIN_PASSWORD=securepassword012

# n8n
N8N_PASSWORD=securepassword345

# Embeddings (optional preload)
EMBEDDING_PRELOAD=

# Notes:
# - ALL passwords MUST be changed in production
# - Keep this file secure (chmod 600)
# - Never commit to version control
# - Use strong, unique passwords for each service
# - Consider using a secrets manager in production
```

---

## Appendix B: Quick Reference Commands

**Start/Stop Services:**
```bash
# Start all services
docker compose --profile all up -d

# Start specific phase
docker compose --profile phase1 up -d

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v

# Restart specific service
docker compose restart litellm

# View logs
docker compose logs -f
docker compose logs -f litellm
```

**GPU Management:**
```bash
# Check GPU status
nvidia-smi

# Monitor GPU in real-time
watch -n 1 nvidia-smi

# Check GPU usage by container
docker stats

# Check which containers are using GPUs
docker ps --format "table {{.Names}}\t{{.Status}}" --filter "label=com.nvidia.visible-devices"
```

**Database Operations:**
```bash
# PostgreSQL
docker exec -it llm-postgres psql -U llmuser -d litellm

# pgvector
docker exec -it llm-pgvector psql -U llmuser -d vectors

# MongoDB
docker exec -it llm-mongodb mongosh -u admin -p mongopassword

# Redis
docker exec -it llm-redis redis-cli -a redispassword

# Qdrant (via API)
curl http://localhost:6333/collections
```

**Model Management:**
```bash
# List Ollama models
docker exec primary-gpt-oss ollama list

# Check loaded models
docker exec primary-gpt-oss ollama ps

# Pull new model
docker exec user-playground ollama pull llama2:7b

# Remove model
docker exec user-playground ollama rm llama2:7b
```

**Monitoring:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=nvidia_gpu_duty_cycle'

# Access Grafana
firefox http://localhost:3000

# Check GPU exporter metrics
curl http://localhost:9835/metrics
```

**Backup & Restore:**
```bash
# Backup databases
docker exec llm-postgres pg_dumpall -U llmuser > backup_$(date +%Y%m%d).sql

# Backup configuration
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  docker-compose.yaml \
  .env \
  config/ \
  scripts/ \
  monitoring/

# Restore database
cat backup_20250115.sql | docker exec -i llm-postgres psql -U llmuser
```

---

## Appendix C: Troubleshooting Guide

**Problem: Container won't start**
```bash
# Check logs
docker compose logs <container-name>

# Check resource usage
docker stats

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# Check port conflicts
sudo netstat -tulpn | grep <port>
```

**Problem: Model loading fails**
```bash
# Check GPU memory
nvidia-smi

# Check model exists
docker exec <container> ollama list

# View detailed logs
docker exec <container> tail -f /var/log/ollama.log

# Restart container
docker compose restart <container>
```

**Problem: High GPU temperature**
```bash
# Check current temperature
nvidia-smi --query-gpu=temperature.gpu --format=csv

# Check fan speed
nvidia-smi --query-gpu=fan.speed --format=csv

# Set higher fan speed (if needed)
nvidia-smi -i 0 -pl 250  # Set power limit to 250W
```

**Problem: Database connection issues**
```bash
# Check database is running
docker compose ps postgres

# Test connection
docker exec llm-postgres pg_isready -U llmuser

# Check logs
docker compose logs postgres

# Restart database
docker compose restart postgres
```

**Problem: API not responding**
```bash
# Check LiteLLM status
curl http://localhost:4000/health

# Check backend models
curl http://localhost:11601/api/tags

# View LiteLLM logs
docker compose logs litellm

# Restart gateway
docker compose restart litellm
```

---

## Appendix D: Performance Optimization Tips

**GPU Optimization:**
1. Monitor GPU utilization - target 70-90%
2. Use quantized models when possible (Q4, Q8)
3. Batch requests for secondary models
4. Set appropriate keep-alive times
5. Use tensor parallelism for large models

**API Optimization:**
1. Enable response caching in Redis
2. Implement request batching
3. Use connection pooling
4. Set reasonable timeouts
5. Monitor and tune max_parallel_requests

**Database Optimization:**
1. Create appropriate indexes
2. Use HNSW indexes for vector search
3. Regular VACUUM for PostgreSQL
4. Monitor query performance
5. Implement proper connection limits

**Network Optimization:**
1. Keep services on same Docker network
2. Use gRPC for high-throughput (Qdrant)
3. Enable HTTP/2 where supported
4. Compress large payloads
5. Use local caching

---

## Appendix E: Production Checklist

**Pre-Deployment:**
- [ ] Change all default passwords in .env
- [ ] Set secure LITELLM_MASTER_KEY
- [ ] Configure firewall rules (ufw)
- [ ] Set up TLS/SSL certificates
- [ ] Configure backup automation
- [ ] Set up monitoring alerts
- [ ] Review and adjust resource limits
- [ ] Test disaster recovery procedures

**Post-Deployment:**
- [ ] Verify all services are healthy
- [ ] Test all API endpoints
- [ ] Confirm GPU utilization
- [ ] Check monitoring dashboards
- [ ] Verify backup procedures
- [ ] Document any custom configurations
- [ ] Train team on operational procedures
- [ ] Set up log rotation
- [ ] Configure alert notifications
- [ ] Perform load testing

**Ongoing Maintenance:**
- [ ] Daily: Check service health, GPU status
- [ ] Weekly: Review logs, update images
- [ ] Monthly: Update models, security patches
- [ ] Quarterly: Review capacity, performance tuning
- [ ] Annually: Disaster recovery drill

---

## Appendix F: Support & Resources

**Documentation:**
- Project README: `/mnt/ai8_arch/README.md`
- Architecture: `/mnt/ai8_arch/docs/ARCHITECTURE.md`
- Deployment: `/mnt/ai8_arch/docs/DEPLOYMENT.md`
- API Reference: `/mnt/ai8_arch/docs/API_REFERENCE.md`
- Troubleshooting: `/mnt/ai8_arch/docs/TROUBLESHOOTING.md`

**External Resources:**
- LiteLLM Documentation: https://docs.litellm.ai
- Ollama Documentation: https://ollama.ai/docs
- vLLM Documentation: https://docs.vllm.ai
- Qdrant Documentation: https://qdrant.tech/documentation
- Prometheus Documentation: https://prometheus.io/docs
- Grafana Documentation: https://grafana.com/docs

**Community:**
- GitHub Issues: (Repository URL)
- Discussion Forum: (Forum URL)
- Slack Channel: (Slack URL)

**Contact:**
- Project Maintainer: CannonCoPilot
- Email: (Contact Email)
- Emergency Support: (Emergency Contact)

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-01-15 | CannonCoPilot | Initial comprehensive requirements document |

---

## License

This project is licensed under the MIT License. See the LICENSE file in the repository for full details.

---

**END OF DOCUMENT**

**Total Sections:** 15 main sections + 6 appendices  
**Total Pages:** ~200 (estimated print)  
**Word Count:** ~45,000 words  
**Last Updated:** 2025-01-15  
**Document Status:** Complete ✅