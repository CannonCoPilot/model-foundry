# AI8 Architecture - System Design

**Version:** 1.0.0  
**Last Updated:** 2025-01-11  
**Author:** CannonCoPilot

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [Component Architecture](#component-architecture)
4. [GPU Allocation Strategy](#gpu-allocation-strategy)
5. [Network Architecture](#network-architecture)
6. [Data Flow](#data-flow)
7. [Scaling Strategy](#scaling-strategy)
8. [Security Considerations](#security-considerations)

---

## Overview

AI8 Architecture is designed as a modular, GPU-optimized infrastructure for running multiple LLMs with different performance characteristics and use cases. The system prioritizes:

- **Resource Efficiency**: Intelligent GPU sharing and memory management
- **High Availability**: Tiered model loading with fallback strategies
- **Developer Experience**: Unified API access and comprehensive tooling
- **Operational Excellence**: Monitoring, logging, and self-healing capabilities

### System Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Access Layer                      │
│  Port 5151  │  Port 5678  │  Port 3000  │  Port 4000            │
│  OpenWebUI  │     n8n     │   Grafana   │  LiteLLM API          │
└──────┬──────────────┬────────────┬──────────────┬────────────────┘
       │              │            │              │
       └──────────────┴────────────┴──────────────┘
                      │
       ┌──────────────▼────────────────────────┐
       │      LiteLLM Gateway (Port 4000)      │
       │  • Model routing & load balancing     │
       │  • API key authentication             │
       │  • Request/response transformation    │
       │  • Fallback handling                  │
       └──────────────┬────────────────────────┘
                      │
       ┌──────────────┼────────────────────────┐
       │              │                        │
┌──────▼──────┐ ┌────▼─────┐          ┌──────▼──────┐
│  Primary    │ │Secondary │          │ Embeddings  │
│  Models     │ │  Models  │          │  Service    │
│  (Tier 1)   │ │ (Tier 2) │          │             │
└──────┬──────┘ └────┬─────┘          └──────┬──────┘
       │             │                        │
       │             │                        │
┌──────▼─────────────▼────────────────────────▼──────┐
│               GPU Resource Pool (8x H200)           │
│  **Mandated Allocation:**                           │
│  GPU 0, 2, 4, 6: Primary & Embedding Models (Strict)│
│  GPU 1, 3, 5, 7: Secondary & Other Tasks (Flexible) │
└──────┬──────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│                 Storage & Data Layer                 │
│  PostgreSQL │ Qdrant │ MongoDB │ Redis               │
│  (Main DB)  │(Vector)│  (Docs) │ (Cache)             │
└─────────────────────────────────────────────────────┘
```

---

## Design Principles

### 1. Separation of Concerns

Each component has a single, well-defined responsibility:

- **LiteLLM**: API gateway and routing only
- **Model Services**: Inference only
- **Databases**: Storage and retrieval only
- **Monitoring**: Observability only

### 2. Resource Optimization

**GPU Sharing Strategy**:
```
Primary Models (Tier 1):
  - Always loaded in VRAM
  - Dedicated GPU allocation
  - Sub-100ms response time
  - Use: Production workloads

Secondary Models (Tier 2):
  - Loaded on-demand
  - Shared GPU pool
  - 10-30s first request (cold start)
  - Auto-unload after 600s idle
  - Use: Specialized tasks, batch processing
```

### 3. Fault Tolerance

**Multi-Level Redundancy**:
```yaml
Request Flow:
  1. LiteLLM receives request
  2. Routes to primary model
  3. If timeout/error → fallback to secondary
  4. If all fail → return error with context
```

**Health Monitoring**:
- Docker healthchecks every 30-60s
- Prometheus metrics every 15s
- Grafana alerts on anomalies
- Auto-restart on failure (unless-stopped)

### 4. Developer-First Design

**Single API Interface**:
- All models accessible via http://localhost:4000
- OpenAI-compatible format
- Model selection via `model` parameter
- Consistent error responses

**Easy Experimentation**:
- Playground container with all tools
- Interactive shell access
- Pre-installed libraries (LangChain, etc.)
- Example scripts and notebooks

---

## Component Architecture

### Core Services

#### 1. LiteLLM Gateway

**Purpose**: Unified API gateway for all LLM services

**Responsibilities**:
- Route requests to appropriate backend
- Transform between API formats
- Handle authentication (Bearer tokens)
- Implement retry logic and fallbacks
- Track usage metrics

**Configuration**: `config/litellm_config.yaml`

**Key Features**:
```yaml
- Latency-based routing
- Model group aliases (vision, reasoning, embeddings)
- Automatic fallbacks
- Database-backed model registry
- OpenAI API compatibility
```

**API Endpoints**:
- `/v1/chat/completions` - Chat completion
- `/v1/completions` - Text completion
- `/v1/embeddings` - Embedding generation
- `/v1/models` - List available models
- `/health` - Health check

#### 2. Primary Models (Tier 1)

**`gpt-oss-120b`** (Primary)
```yaml
- **Framework**: Ollama
- **GPU Allocation**: GPUs 0, 2 (Mandated)
- **Use Cases**: High-performance reasoning, complex instruction following.
```

**`qwen3-omni`** (Primary)
```yaml
- **Framework**: Ollama
- **GPU Allocation**: GPUs 4, 6 (Mandated)
- **Use Cases**: Advanced multimodal (vision-language) tasks.
```

**Loading Strategy**: `ollama_preload.sh`
```bash
# Starts Ollama server
# Pulls model if missing
# Loads into VRAM with keep_alive: -1
# Stays loaded until container stops
```

#### 3. Secondary Models (Tier 2)

**`deepseek-v2`** (Secondary)
```yaml
- **Framework**: Ollama
- **GPU Allocation**: Flexible (GPUs 1, 3, 5, 7)
- **Use Cases**: Specialized code generation and technical queries.
```

**`llava-v1.6-mistral-7b`** (Secondary)
```yaml
- **Framework**: Ollama
- **GPU Allocation**: Flexible (GPUs 1, 3, 5, 7)
- **Use Cases**: Vision-language tasks, image analysis.
```

**Loading Strategy**: `ollama_lazy_load.sh`
```bash
# Downloads model during startup
# Loads into VRAM on first request
# Auto-unloads after 600s idle
# Reloads on next request (~10-30s)
```

#### 4. Embedding Service

**Purpose**: Multi-model embedding generation

**Architecture**:
```python
FastAPI Service
├── **`nomic-embed-text-v1.5`**
│   - **Dimensions**: 768
│   - **Use Case**: High-performance text embedding.
└── **`mxbai-embed-large-v1`**
    - **Dimensions**: 1024
    - **Use Case**: State-of-the-art multilingual embedding.
```

**Model Caching**:
- HuggingFace models cached in memory (LRU)
- Ollama models loaded on-demand
- First request: ~5-30s (loading)
- Subsequent requests: ~50-200ms

**API Endpoints**:
- `/v1/embeddings` - Generate embeddings
- `/health` - Service health
- `/models` - List available models

#### 5. Vector Databases

**Qdrant**
```yaml
Purpose: Primary vector store for RAG
Port: 6333 (HTTP), 6334 (gRPC)
Features:
  - HNSW indexing
  - Collection management
  - Payload filtering
  - Hybrid search
Storage: /mnt/ai8_arch/data/qdrant
```

**pgvector**
```yaml
Purpose: SQL-based vector store
Port: 5433
Features:
  - PostgreSQL integration
  - ACID compliance
  - Join with relational data
  - Two index types (HNSW, IVFFlat)
Storage: /mnt/ai8_arch/data/pgvector
```

**Usage Pattern**:
```
Document Ingestion:
  1. Parse document → chunks
  2. Generate embeddings (embedding service)
  3. Store vectors (Qdrant or pgvector)
  4. Store metadata (MongoDB)

Query:
  1. Generate query embedding
  2. Search vector DB (top-k)
  3. Retrieve full documents
  4. Generate response (LLM)
```

#### 6. Monitoring Stack

**Prometheus** (Port 9090)
```yaml
Scrape Targets:
  - nvidia_gpu_exporter (GPU metrics)
  - litellm (API metrics)
  - embeddings (service metrics)
  - vllm services (inference metrics)
  - postgres, qdrant, redis (DB metrics)
  
Retention: 30 days
Scrape Interval: 15s
```

**Grafana** (Port 3000)
```yaml
Dashboards:
  - GPU Monitoring (utilization, temp, VRAM)
  - API Gateway (requests, latency, errors)
  - Model Performance (tokens/sec, queue depth)
  - Database Health (connections, query time)
  
Alerts:
  - GPU temperature > 85°C
  - VRAM usage > 95%
  - API error rate > 5%
  - Model response time > 10s
```

---

## GPU Allocation Strategy

### Physical Layout

```
Server: 8x NVIDIA H200 140GB
Total VRAM: 1120GB

**Mandated Allocation:**
- **GPUs 0, 2, 4, 6**: Reserved exclusively for Primary and Embedding models. This allocation is strict and non-negotiable.
- **GPUs 1, 3, 5, 7**: Flexible pool for Secondary models, playground experiments, and other tasks.
```

### Memory Allocation

**GPU 2-4 (GPT-OSS Primary)**:
```
Per GPU:
  GPT-OSS:        ~60GB (persistent)
  Available:      ~20GB (for secondaries)
  
Shared secondaries on demand:
  - Embeddings: ~5GB
  - InternVL: ~8GB
  - Small models: ~5-10GB
```

**GPU 5-7 (Qwen3-VL Primary)**:
```
Per GPU:
  Qwen3-VL:       ~79GB (persistent)
  Available:      ~1GB (minimal secondary use)
  
Note: Limited space for secondaries
Consider offloading to GPUs 2-4
```

### Scheduling Algorithm

**Priority Levels**:
```
P0: Monitoring (always)
P1: Primary models (persistent)
P2: Active secondary models (600s keepalive)
P3: New secondary model requests
P4: Playground experiments
```

**Load Balancing**:
```python
# Implemented by Ollama's OLLAMA_SCHED_SPREAD=1
# Distributes requests across available GPUs
# Prefers GPUs with more free VRAM
# Avoids overloading single GPU
```

**Conflict Resolution**:
```
If GPU full:
  1. Check other GPUs in allocation
  2. Evict idle secondary (>600s)
  3. Queue request (30s timeout)
  4. Return "Resource unavailable" error
```

---

## Network Architecture

### Docker Network

```yaml
Network: llm-network
Type: bridge
Subnet: 172.28.0.0/16
DNS: Docker internal DNS
```

**Benefits**:
- Service discovery by name
- Network isolation
- Port management

### Port Mapping

**External Ports** (accessible from host):
```
3000  → Grafana
4000  → LiteLLM API
5151  → OpenWebUI
5432  → PostgreSQL (main)
5433  → pgvector
5678  → n8n
6333  → Qdrant HTTP
6334  → Qdrant gRPC
6379  → Redis
8001  → Qwen3-VL (vLLM)
8010  → Embeddings API
9090  → Prometheus
9835  → GPU Exporter
11601 → GPT-OSS (Ollama)
11603 → DeepSeek (Ollama)
11610 → Embeddings (Ollama)
11620 → Playground (Ollama)
27017 → MongoDB
```

**Internal Ports** (container-to-container):
```
All services accessible by name:
  http://litellm:4000
  http://postgres:5432
  http://qdrant:6333
  etc.
```

### Service Communication

**Example: RAG Query Flow**
```
1. User → OpenWebUI (5151)
   ↓
2. OpenWebUI → LiteLLM (4000)
   ↓
3. LiteLLM → Embeddings (8010) [get query embedding]
   ↓
4. Embeddings → Qdrant (6333) [vector search]
   ↓
5. Qdrant → Returns chunks
   ↓
6. LiteLLM → Primary Model (11601) [generate response]
   ↓
7. Response → User
```

---

## Data Flow

### Model Inference Path

```
HTTP Request
    ↓
┌───────────────────────────────────┐
│  LiteLLM Gateway (Port 4000)      │
│  • Validates API key              │
│  • Selects model based on name    │
│  • Transforms request format      │
└───────────┬───────────────────────┘
            ↓
    ┌───────┴────────┐
    │  Model Router  │
    └───────┬────────┘
            ↓
    ┌───────┴────────────────────────┐
    │  Is primary model?             │
    ├────────────────────────────────┤
    │ YES → Send to primary          │
    │ NO  → Check secondary status   │
    └────────────────────────────────┘
            ↓
┌───────────▼─────────────────────────┐
│  Model Service (Ollama or vLLM)    │
│  • Loads model if not in VRAM      │
│  • Tokenizes input                 │
│  • Runs inference                  │
│  • Streams or returns completion   │
└───────────┬─────────────────────────┘
            ↓
┌───────────▼─────────────────────────┐
│  LiteLLM Gateway                    │
│  • Transforms response format       │
│  • Logs metrics to Prometheus      │
│  • Returns to client               │
└─────────────────────────────────────┘
```

### RAG Pipeline Data Flow

```
Document Upload:
  1. User uploads PDF/DOCX
  2. Parse with unstructured.io (or custom parser)
  3. Chunk text (1000 chars, 200 overlap)
  4. Generate embeddings (batch to embedding service)
  5. Store vectors in Qdrant
  6. Store metadata in MongoDB
  7. Return document ID

Query Processing:
  1. User submits query
  2. Generate query embedding
  3. Vector search (Qdrant, top-5)
  4. Fetch full chunks
  5. Build prompt with context
  6. Send to LLM (via LiteLLM)
  7. Stream response to user
```

### Monitoring Data Flow

```
Metrics Collection:
  GPU Exporter → Prometheus (15s interval)
  LiteLLM → Prometheus (on request)
  Services → Prometheus (health checks)
  
Data Retention:
  Prometheus: 30 days raw metrics
  Grafana: Real-time visualization
  
Alert Flow:
  Prometheus → Evaluates rules
  Alert Manager → (future: email/slack)
  Grafana → Visual indicators
```

---

## Scaling Strategy

### Vertical Scaling (Single Node)

**Current Capacity**:
- 8 GPUs
- 640GB VRAM
- ~10-20 concurrent users

**Optimization Opportunities**:
1. Quantization (FP16 → INT8)
   - 2x memory reduction
   - Minimal quality loss
   - Supported by vLLM

2. Batching
   - Process multiple requests together
   - Increases throughput
   - Managed by vLLM/Ollama

3. Model Pruning
   - Remove less-used secondary models
   - Add more frequently-used models

### Horizontal Scaling (Multi-Node)

**Approach 1: Model Sharding**
```yaml
Node 1:
  - Primary models (GPT-OSS, Qwen3-VL)
  - Embeddings
  
Node 2:
  - Secondary models (DeepSeek, Llava, etc.)
  - Playground

LiteLLM:
  - Routes to appropriate node
  - Handles failover
```

**Approach 2: Replica Sets**
```yaml
Node 1 & Node 2:
  - Same models on both
  - LiteLLM load balances
  - 2x capacity, high availability
```

### Database Scaling

**PostgreSQL**:
- Read replicas for analytics
- PgBouncer for connection pooling

**Qdrant**:
- Clustering (3+ nodes)
- Replication factor: 2
- Sharding by collection

**MongoDB**:
- Replica set (3 nodes)
- Sharding for large datasets

---

## Security Considerations

### Authentication & Authorization

**API Access**:
```yaml
LiteLLM:
  Authentication: Bearer token (LITELLM_MASTER_KEY)
  Rate Limiting: Per-key limits (configurable)
  IP Whitelisting: (future enhancement)

OpenWebUI:
  Authentication: Username/password
  Session Management: Cookie-based
  User Roles: Admin, User

n8n:
  Authentication: Basic auth
  API Keys: For external integrations
```

### Network Security

**Firewall Rules**:
```bash
# Only expose necessary ports
# Internal services: 172.28.0.0/16 only
# External services: Configure host firewall

iptables -A INPUT -p tcp --dport 4000 -j ACCEPT  # LiteLLM
iptables -A INPUT -p tcp --dport 5151 -j ACCEPT  # OpenWebUI
# ... etc
```

**Container Isolation**:
- Each service in separate container
- Non-root users (where possible)
- Read-only filesystem mounts (configs)

### Data Security

**Sensitive Data**:
```bash
# Environment variables
.env file: chmod 600 (not in git)

# Database credentials
Stored in .env, passed as env vars

# Model weights
Local storage, no external access
```

**Encryption**:
- TLS for external access (reverse proxy)
- Encrypted volumes for sensitive data (future)

### Audit & Compliance

**Logging**:
```yaml
Application Logs:
  Location: /mnt/ai8_arch/logs/
  Retention: 30 days
  Format: Structured (JSON)

Access Logs:
  LiteLLM: All API requests
  OpenWebUI: User actions
  n8n: Workflow executions
```

**Monitoring**:
- Real-time alerts on security events
- Failed authentication attempts
- Unusual API usage patterns

---

## Performance Characteristics

### Latency Targets

**Primary Models**:
```
Time to First Token (TTFT): <200ms
Tokens per Second: 50-100 tokens/s
Concurrent Requests: 4-8 per model
```

**Secondary Models**:
```
Cold Start: 10-30s (first request)
Warm Response: <500ms TTFT
Tokens per Second: 30-80 tokens/s
```

**Embeddings**:
```
Small batch (1-10 texts): 50-200ms
Medium batch (10-100 texts): 500ms-2s
Large batch (100+ texts): 2-10s
```

### Throughput

**Theoretical Maximum**:
```
Primary models: ~400 tokens/s aggregate
Secondary models: ~200 tokens/s (when loaded)
Embeddings: ~1000 embeddings/s
```

**Realistic Sustained**:
```
With 10 concurrent users:
  ~200 tokens/s aggregate
  ~500 embeddings/s
  ~50 requests/minute to secondaries
```

### Bottlenecks

1. **GPU Memory**: Limits number of concurrent models
2. **Model Loading**: Cold start penalty (10-30s)
3. **Network**: Internal bandwidth (not usually limiting)
4. **Disk I/O**: Model loading from disk

---

## Future Enhancements

### Short Term (1-3 months)
- [ ] Reverse proxy with TLS (Traefik/Nginx)
- [ ] Alert manager integration (email/Slack)
- [ ] Automated model updates
- [ ] Enhanced Grafana dashboards

### Medium Term (3-6 months)
- [ ] Multi-node deployment support
- [ ] Model fine-tuning pipeline
- [ ] Advanced RAG (hybrid search, re-ranking)
- [ ] User quotas and rate limiting

### Long Term (6+ months)
- [ ] Kubernetes deployment option
- [ ] Model marketplace integration
- [ ] Custom model training pipeline
- [ ] Multi-tenant isolation

---

## Conclusion

AI8 Architecture provides a robust, scalable foundation for production LLM deployments. The modular design allows for easy customization while maintaining operational excellence through comprehensive monitoring and automated management.

**Key Strengths**:
- ✅ Efficient GPU utilization
- ✅ Flexible model management
- ✅ Production-ready monitoring
- ✅ Developer-friendly tooling
- ✅ Comprehensive documentation

**Design Philosophy**:
> "Optimize for common cases, handle edge cases gracefully"

For questions or contributions, see [README.md](../README.md#support).
```