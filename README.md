<p align="center">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose"/>
  <img src="https://img.shields.io/badge/NVIDIA-CUDA_12.1-76B900?style=for-the-badge&logo=nvidia&logoColor=white" alt="CUDA 12.1"/>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11"/>
  <img src="https://img.shields.io/badge/Prometheus-Grafana-E6522C?style=for-the-badge&logo=prometheus&logoColor=white" alt="Prometheus"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/LiteLLM-Gateway-FF6F00?style=for-the-badge" alt="LiteLLM"/>
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="MIT License"/>
</p>

# Model Foundry

**A production-ready containerized AI infrastructure stack -- multi-model orchestration, monitoring, and deployment automation for open-source LLMs.**

---

## What Makes This Interesting

This is not a wrapper around `ollama run`. Model Foundry is the infrastructure layer that sits between bare metal GPUs and production workloads -- the part most teams hand-wave past when they say "we'll just deploy the model."

- **Tiered model scheduling with cold-start management.** Primary models stay persistent in VRAM with `keep_alive: -1`. Secondary models load on-demand and auto-evict after 600s idle. The system handles the messy reality that you cannot keep everything loaded at once, even on high-end hardware.

- **Unified API gateway over heterogeneous inference backends.** Ollama and vLLM serve fundamentally different APIs. LiteLLM normalizes them behind a single OpenAI-compatible endpoint with automatic fallback chains -- if the primary 120B model times out, the request silently routes to the secondary.

- **Custom embedding service with LRU model management.** Nine embedding models across two backends (HuggingFace SentenceTransformers + Ollama), with GPU memory managed via an LRU eviction policy. Not a static deployment -- the service dynamically loads and unloads models based on demand.

- **Complete RAG orchestration pipeline.** Document upload, chunking, embedding, vector storage (Qdrant + pgvector), retrieval, and LLM generation -- all wired together as a single deployable service, not a notebook.

- **GPU allocation as policy, not afterthought.** Strict GPU pinning separates primary inference workloads from experimental playground traffic. The architecture enforces resource isolation at the container level.

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
                   +-+----------+----------+-----+
                     |          |          |
          +----------+    +----+----+    ++-----------+
          |               |         |     |           |
   +------+------+  +----+----+ +--+--+  |  +--------+--------+
   | Primary LLMs|  |Secondary| | vLLM|  |  |  Embedding Svc  |
   | (Ollama)    |  | (Ollama)| |     |  |  |  (FastAPI)      |
   | GPT-OSS     |  | DeepSk  | |Qwen3|  |  |  9 models       |
   | 120B        |  | Llava   | |Omni |  |  |  HF + Ollama    |
   +------+------+  +----+----+ +--+--+  |  +--------+--------+
          |               |        |      |           |
   +------+---------------+--------+------+-----------+------+
   |                   GPU Resource Pool                     |
   |   Even GPUs: Primary + Embeddings (strict pinning)      |
   |   Odd GPUs:  Secondary + Playground (flexible pool)     |
   +--+-------------+-------------+-------------+-----------+
      |             |             |             |
  +---+---+   +----+----+   +----+----+   +----+----+
  |Qdrant |   |pgvector |   |MongoDB  |   | Redis   |
  |:6333  |   |:5433    |   |:27017   |   | :6379   |
  +-------+   +---------+   +---------+   +---------+

   Monitoring: Prometheus :9090 --> Grafana :3000
               GPU Exporter :9835
```

---

## Key Features

| Capability | Implementation |
|---|---|
| **Multi-model routing** | LiteLLM gateway with model group aliases (`vision`, `text`, `embedding`), automatic retries, and configurable fallback chains |
| **Tiered GPU scheduling** | Primary models persistent in VRAM; secondary models lazy-loaded with 600s idle eviction; strict GPU pinning via `NVIDIA_VISIBLE_DEVICES` |
| **Embedding service** | FastAPI service managing 9 models (5 HuggingFace + 4 Ollama) with LRU eviction, GPU memory cleanup via `torch.cuda.empty_cache()`, and OpenAI-compatible API |
| **RAG pipeline** | End-to-end orchestrator: document upload, text chunking (configurable size/overlap), embedding generation, Qdrant vector storage, retrieval, and LLM-augmented generation |
| **Dual vector stores** | Qdrant (HNSW indexing, payload filtering) + pgvector (ACID compliance, SQL joins with relational data) |
| **Observability** | Prometheus scraping 8 targets at 15s intervals, Grafana dashboards for GPU utilization/temperature/VRAM, API latency, and model throughput |
| **Phased deployment** | 4-phase rollout (Foundation, Data Layer, Model Services, User Interfaces) with per-phase health checks and automated test suites |
| **MCP server** | Model Context Protocol server for integration with agentic coding tools (Roo Code, Cline, Aider) |
| **Playground sandbox** | Isolated container with Ollama + vLLM + Jupyter for experimentation, pinned to its own GPU |

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Inference** | Ollama, vLLM (custom fork for Qwen3-Omni), HuggingFace TGI |
| **API Gateway** | LiteLLM Proxy (OpenAI-compatible routing) |
| **Embeddings** | SentenceTransformers, Ollama embeddings, FastAPI |
| **Vector Storage** | Qdrant, pgvector (PostgreSQL extension) |
| **Data Storage** | PostgreSQL 15, MongoDB 7.0, Redis 7 |
| **Monitoring** | Prometheus 2.48, Grafana 10.2, NVIDIA GPU Exporter |
| **Orchestration** | Docker Compose, custom shell/Python automation |
| **Frameworks** | FastAPI, LangChain, httpx, PyTorch |
| **Workflow** | n8n, OpenWebUI |

---

## Project Metrics

| Metric | Count |
|---|---|
| Docker services defined | 18 |
| Custom Dockerfiles | 7 |
| Embedding models supported | 9 |
| Automation scripts | 21 |
| Test scripts | 9 |
| Documentation pages | 13 |
| Prometheus scrape targets | 8 |
| Exposed service ports | 19 |
| Total project files | 64 |

---

## Getting Started

**Prerequisites:** Docker Engine 24.0+, Docker Compose v2.20+, NVIDIA Container Toolkit, CUDA 12.1+ drivers.

```bash
# Clone the repository
git clone https://github.com/your-username/model-foundry.git
cd model-foundry

# Configure environment
cp .env.template .env
# Edit .env with your HuggingFace token and secure passwords

# Set up directory structure
bash deploy/setup_directories.sh

# Deploy in phases
bash deploy/deploy.sh phase1    # Foundation: monitoring, database, API gateway
bash deploy/deploy.sh phase2    # Data layer: Qdrant, pgvector, MongoDB, Redis
bash deploy/deploy.sh phase3    # Model services: LLMs + embeddings
bash deploy/deploy.sh phase4    # User interfaces: OpenWebUI, n8n, Playground

# Validate deployment
python3 deploy/test_deployment.py
```

All models are accessible through a single endpoint:

```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-oss-120b", "messages": [{"role": "user", "content": "Hello"}]}'
```

Full deployment guide: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | API reference: [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Architecture deep-dive: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center"><i>Model Foundry -- because the hard part of AI infrastructure is not choosing a model, it is keeping twelve of them running reliably at the same time.</i></p>
