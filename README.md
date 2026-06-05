<p align="center">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose"/>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11"/>
  <img src="https://img.shields.io/badge/LiteLLM-Gateway-FF6F00?style=for-the-badge" alt="LiteLLM"/>
  <img src="https://img.shields.io/badge/vLLM-Inference-4B0082?style=for-the-badge" alt="vLLM"/>
  <img src="https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white" alt="Prometheus"/>
  <img src="https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white" alt="Grafana"/>
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="MIT License"/>
</p>

# Model Foundry

**Containerized infrastructure for running open-source LLMs at production quality -- multi-model orchestration, GPU resource management, RAG pipelines, and full observability.**

---

## Production Infrastructure for Open-Source AI

Getting a single model to respond to a prompt takes an afternoon. Keeping a fleet of heterogeneous models running reliably -- with proper resource isolation, automatic failover, embedding pipelines, and monitoring -- is an infrastructure problem that most teams underestimate.

Model Foundry is the layer between bare-metal GPUs and production workloads. It solves three problems that appear the moment you move past single-model deployments:

**GPU memory is a finite, shared resource.** Primary models stay resident in VRAM with persistent allocation. Secondary models load on-demand and auto-evict after 600 seconds of idle time. The system enforces strict GPU pinning at the container level -- even-numbered GPUs for primary inference and embeddings, odd-numbered for secondary and experimental workloads.

**Heterogeneous backends need a unified API.** Ollama, vLLM, and HuggingFace TGI each serve different API formats. LiteLLM normalizes them behind a single OpenAI-compatible endpoint with automatic fallback chains -- if the primary model times out, the request silently routes to an alternative.

**Embeddings are not a static deployment.** The embedding service manages nine models across two backends (SentenceTransformers and Ollama) with LRU eviction and GPU memory cleanup. Models load and unload dynamically based on demand rather than sitting permanently in VRAM.

---

## Architecture

```
                       Clients / Applications
                                |
                  +-------------+-------------+
                  |                           |
           OpenWebUI :5151              n8n :5678
                  |                           |
                  +-------------+-------------+
                                |
                 +--------------+--------------+
                 |    LiteLLM Gateway :4000    |
                 |  Routing / Auth / Fallback  |
                 +--+--------+--------+-------+
                    |        |        |
         +----------+  +----+----+  ++----------+
         |              |         |  |           |
  +------+------+  +---+----+ +--+-+  +---------+--------+
  | Primary LLMs|  |  vLLM  | |Sec.|  |  Embedding Svc   |
  | (Ollama/TGI)|  | Qwen3  | |Mdls|  |  9 models, LRU   |
  | Persistent  |  | Omni   | |    |  |  HF + Ollama     |
  +------+------+  +---+----+ +--+-+  +---------+--------+
         |             |         |              |
  +------+-------------+---------+--------------+------+
  |                  GPU Resource Pool                  |
  |  Even GPUs: Primary + Embeddings (strict pinning)   |
  |  Odd GPUs:  Secondary + Playground (flexible pool)  |
  +--+-----------+-----------+-----------+----------+--+
     |           |           |           |          |
 +---+---+ +----+----+ +----+----+ +----+----+ +---+---+
 |Qdrant | |pgvector | |MongoDB  | | Redis   | |Postgres|
 |:6333  | |:5433    | |:27017   | | :6379   | |:5432   |
 +-------+ +---------+ +---------+ +---------+ +-------+

  Monitoring: Prometheus :9090 --> Grafana :3000
              GPU Exporter :9835
```

---

## Key Capabilities

| Capability | Implementation |
|---|---|
| **Multi-model routing** | LiteLLM gateway with model group aliases (`vision`, `text`, `embedding`), automatic retries, and configurable fallback chains |
| **Tiered GPU scheduling** | Primary models persistent in VRAM; secondary models lazy-loaded with 600s idle eviction; strict GPU pinning via `NVIDIA_VISIBLE_DEVICES` |
| **Embedding service** | FastAPI service managing 9 models (5 HuggingFace + 4 Ollama) with LRU eviction and `torch.cuda.empty_cache()` memory management |
| **RAG pipeline** | End-to-end orchestrator: document upload, configurable text chunking, embedding, Qdrant vector storage, retrieval, and LLM-augmented generation |
| **Dual vector stores** | Qdrant (HNSW indexing, payload filtering) + pgvector (ACID compliance, SQL joins with relational data) |
| **Observability** | Prometheus scraping 8 targets at 15s intervals; Grafana dashboards for GPU utilization, VRAM, API latency, and model throughput |
| **Phased deployment** | 4-phase rollout with per-phase health checks, error handling with automatic teardown, and automated validation |
| **MCP integration** | Model Context Protocol server for integration with AI coding tools |

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Inference** | Ollama, vLLM, HuggingFace TGI |
| **API Gateway** | LiteLLM Proxy (OpenAI-compatible routing) |
| **Embeddings** | SentenceTransformers, Ollama, FastAPI |
| **Vector Storage** | Qdrant, pgvector (PostgreSQL) |
| **Data** | PostgreSQL 15, MongoDB 7.0, Redis 7 |
| **Monitoring** | Prometheus 2.48, Grafana 10.2, NVIDIA GPU Exporter |
| **Orchestration** | Docker Compose, 7 custom Dockerfiles |
| **Frameworks** | FastAPI, LangChain, httpx, PyTorch |

---

## Usage

All models are accessible through a single OpenAI-compatible endpoint:

```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "Explain GPU memory management"}]
  }'
```

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000/v1", api_key="your-key")
response = client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Explain GPU memory management"}]
)
```

> [!TIP]
> Model group aliases (`vision`, `text`, `embedding`) route to the best available backend automatically, including fallback if the primary is unavailable.

<details>
<summary><strong>Getting Started</strong></summary>

### Prerequisites

- Docker Engine 24.0+ with Compose v2.20+
- NVIDIA Container Toolkit
- CUDA 12.1+ drivers
- 8x NVIDIA GPUs (H100/A100 or similar, 640GB+ total VRAM)
- 128GB+ system RAM

### Deployment

```bash
git clone https://github.com/nathanielcannon/model-foundry.git
cd model-foundry

# Configure environment
cp .env.template .env
# Edit .env: set HuggingFace token, database passwords, LiteLLM key

# Set up directory structure
bash deploy/setup_directories.sh

# Deploy in phases (each phase validates before proceeding)
bash deploy/deploy.sh phase1    # Monitoring, database, API gateway
bash deploy/deploy.sh phase2    # Qdrant, pgvector, MongoDB, Redis
bash deploy/deploy.sh phase3    # LLMs + embeddings
bash deploy/deploy.sh phase4    # OpenWebUI, n8n, Playground

# Validate full deployment
python3 deploy/test_deployment.py
```

</details>

<details>
<summary><strong>Project Structure</strong></summary>

```
model-foundry/
  config/                  # LiteLLM routing configuration
  deploy/                  # Docker Compose, deploy scripts, validation
  dockerfiles/             # 7 custom images (embeddings, litellm, mcp,
                           #   playground, primary_gpt_oss, rag, vllm)
  docs/                    # Architecture, deployment, API reference,
                           #   troubleshooting, roadmap
  examples/                # API usage (bash, Python, LangChain, RAG)
  monitoring/              # Prometheus scrape config
  scripts/                 # 23 management, test, and service scripts
```

| Metric | Count |
|---|---|
| Docker services defined | 18 |
| Custom Dockerfiles | 7 |
| Embedding models supported | 9 |
| Prometheus scrape targets | 8 |
| Automation and test scripts | 23 |
| Documentation pages | 13 |

</details>

---

## Documentation

| Document | Description |
|---|---|
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design, GPU allocation strategy, data flow diagrams, scaling approach |
| [`DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Hardware requirements, phased deployment procedure, post-deploy validation |
| [`API_REFERENCE.md`](docs/API_REFERENCE.md) | Endpoint catalog, authentication, code examples in bash/Python/LangChain |
| [`TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Common failure modes and diagnostic procedures |
| [`ROADMAP.md`](docs/ROADMAP.md) | Planned capabilities: TLS, multi-node, fine-tuning pipelines |

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center"><i>Model Foundry -- the infrastructure layer between bare-metal GPUs and production AI workloads.</i></p>