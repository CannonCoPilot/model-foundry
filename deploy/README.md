# AI8 Architecture - Multi-Model LLM Infrastructure

**Author:** CannonCoPilot  
**Created:** 2025-01-11  
**Version:** 1.0.0  
**License:** MIT

## Overview

AI8 Architecture is a comprehensive, production-ready infrastructure for deploying and managing multiple Large Language Models (LLMs), embedding services, vector databases, and RAG pipelines. Built on Docker Compose, it provides a modular, scalable, and GPU-optimized environment for AI workloads.

### Key Features

- **Multi-Model Support**: Run multiple LLMs simultaneously with intelligent GPU allocation
- **Tiered Model Management**: Persistent (always-loaded) and on-demand (lazy-loaded) models
- **Unified API Gateway**: LiteLLM provides OpenAI-compatible API for all models
- **RAG Infrastructure**: Vector databases (Qdrant, pgvector), document stores (MongoDB), caching (Redis)
- **Embedding Services**: Multiple embedding models (Ollama + HuggingFace)
- **Monitoring Stack**: Prometheus + Grafana with GPU metrics
- **User Interfaces**: OpenWebUI for chat, n8n for workflows
- **Developer Tools**: Interactive playground for model experimentation

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
│  OpenWebUI (5151) │ n8n (5678) │ Grafana (3000)            │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                  LiteLLM API Gateway (4000)                  │
│            OpenAI-compatible unified interface               │
└──────────────────┬──────────────────────────────────────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
┌─────▼────┐ ┌────▼─────┐ ┌───▼──────┐
│ Primary  │ │Secondary │ │Embeddings│
│  Models  │ │  Models  │ │ Service  │
└──────────┘ └──────────┘ └──────────┘
  GPUs 2-7     GPUs 2-7      GPU 2
      │            │            │
      └────────────┼────────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
┌─────▼────┐ ┌────▼─────┐ ┌───▼──────┐
│  Qdrant  │ │ pgvector │ │ MongoDB  │
│  Vector  │ │  Vector  │ │Document  │
│   DB     │ │    DB    │ │  Store   │
└──────────┘ └──────────┘ └──────────┘
```

## Quick Start

### Prerequisites

- Ubuntu 22.04+ (or compatible Linux)
- Docker 24+ with Docker Compose
- NVIDIA GPUs with 530+ drivers
- 2TB+ disk space
- HuggingFace account (for model downloads)

### Installation

```bash
# 1. Clone repository
cd /mnt
git clone https://github.com/CannonCoPilot/ai8-architecture.git ai8_arch
cd ai8_arch

# 2. Set up directory structure
bash setup_directories.sh

# 3. Configure environment
cp .env.template .env
nano .env  # Set HF_TOKEN and passwords

# 4. Deploy infrastructure
./deploy.sh all

# 5. Verify deployment
./test_deployment.sh
```

### Access Services

- **OpenWebUI**: http://localhost:5151 - Chat interface
- **n8n**: http://localhost:5678 - Workflow automation
- **Grafana**: http://localhost:3000 - Monitoring dashboards
- **LiteLLM**: http://localhost:4000 - API gateway
- **Qdrant**: http://localhost:6333/dashboard - Vector database

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System design and components
- [Deployment Guide](docs/DEPLOYMENT.md) - Detailed deployment instructions
- [RAG Setup](docs/RAG_SETUP.md) - RAG pipeline configuration
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [API Reference](docs/API_REFERENCE.md) - API endpoints and usage

## Project Structure

```
/mnt/ai8_arch/
├── docker-compose.yaml         # Main orchestration file
├── deploy.sh                   # Phased deployment script
├── test_deployment.sh          # Validation tests
├── .env                        # Environment configuration
│
├── config/                     # Service configurations
│   └── litellm_config.yaml    # Model routing config
│
├── dockerfiles/                # Custom Docker images
│   ├── Dockerfile.vllm
│   ├── Dockerfile.embeddings
│   └── Dockerfile.playground
│
├── scripts/                    # Initialization & utilities
│   ├── init-postgres.sh
│   ├── ollama_preload.sh
│   ├── embedding_service.py
│   └── ...
│
├── monitoring/                 # Prometheus & Grafana
│   ├── prometheus.yml
│   └── grafana/
│
├── models/                     # Model storage (1.4TB+)
│   ├── ollama/
│   │   ├── primary/
│   │   ├── secondary/
│   │   └── embeddings/
│   └── huggingface/
│
├── data/                       # Persistent data
│   ├── postgres/
│   ├── qdrant/
│   ├── mongodb/
│   └── ...
│
└── docs/                       # Documentation
```

## Model Inventory

### Primary Models (Always Loaded)
- **GPT-OSS 120B** - GPUs 2,3,4 - Port 11601
- **Qwen3-VL 235B** - GPUs 5,6,7 - Port 8001

### Secondary Models (On-Demand)
- **DeepSeek R1 671B** - GPUs 2-5 - Port 11603
- **Llava 34B** - GPU 3 - Port 11602
- **InternVL3.5 8B** - GPU 2 - Port 8002
- **GLM-4.6** - GPUs 4-7 - Port 8003

### Embedding Models
- **Nomic Embed** - 768 dims - GPU 2
- **Stella** - 1024 dims - GPU 2
- **Qwen3 Embed** - 1024 dims - GPU 2

## Development

### Building Images

```bash
# Build all custom images
docker compose build

# Build specific image
docker compose build embeddings
```

### Testing Changes

```bash
# Validate configuration
docker compose config

# Test specific service
docker compose up -d <service>
docker logs -f <service>

# Run tests
./test_deployment.sh
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request

## License

MIT License - See [LICENSE](LICENSE) file

## Support

- **Issues**: https://github.com/CannonCoPilot/ai8-architecture/issues
- **Discussions**: https://github.com/CannonCoPilot/ai8-architecture/discussions
- **Documentation**: https://github.com/CannonCoPilot/ai8-architecture/wiki

## Acknowledgments

- vLLM team for high-performance inference
- Ollama team for easy model management
- LangChain for RAG utilities
- Open-source LLM community

---

**Star this repository if you find it useful!**
```