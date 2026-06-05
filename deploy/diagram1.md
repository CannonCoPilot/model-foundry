```markdown
--- 
marp: true
theme: default
class: lead
paginate: false
---

# AI8 Deployment — Config & Scripts Interaction
Single slide: deployment config / dockerfiles / scripts interaction diagram

---

## Deployment flow (visual)
```mermaid
flowchart LR
  %% REPO / HOST FILES
  subgraph Repo["Repository (/mnt/ai8_arch) - Source files"]
    direction TB
    env[".env.template"]
    compose["docker-compose.yaml / docker-compose-vllm.yaml"]
    deploysh["deploy/deploy.sh\nsetup_directories.sh"]
    config["config/litellm_config.yaml"]
    dockerfiles["dockerfiles/\n(Dockerfile.embeddings,\nDockerfile.vllm,\nDockerfile.playground, ...)"]
    scripts["scripts/\n(init-postgres.sh,\ninit-pgvector.sh,\nollama_preload.sh,\nollama_lazy_load.sh,\nembedding_service.py, ... )"]
    monitoring["monitoring/\n(prometheus.yml,\n grafana/dashboards, exporters)"]
    docs["docs/ README/quickstart/etc."]
    models_dir["models/ (shared model storage)"]
    data_dir["data/ (persistent volumes)"]
  end

  %% DEPLOYMENT ORCHESTRATION
  deploysh -->|calls| compose_cmd["docker compose --profile <phase> up -d\n(builds & starts services)"]
  compose_cmd --> DockerEngine["Docker Engine (host)"]

  %% DOCKER BUILD / IMAGES
  DockerEngine -->|reads| dockerfiles
  DockerEngine -->|reads| compose
  compose -->|mounts| models_dir
  compose -->|mounts| data_dir
  compose -->|injects env| env

  %% CONTAINERS / SERVICES
  subgraph Containers["Containers / Services (runtime)"]
    direction TB
    lite["LiteLLM API Gateway\n(container: litellm)\nreads: config/litellm_config.yaml"]
    postgres["Postgres\n(uses init-postgres.sh via /docker-entrypoint-initdb.d)"]
    pgvector["pgvector (Postgres+pgvector)\n(init-pgvector.sh)"]
    qdrant["Qdrant (vector DB)"]
    chroma["Chroma (vector store)"]
    mongo["MongoDB (documents)"]
    redis["Redis (cache)"]
    prom["Prometheus\n(reads monitoring/prometheus.yml)"]
    grafana["Grafana\n(provisioned dashboards)"]
    gpu_exporter["NVIDIA GPU Exporter\n(mounts nvidia libs from host)"]
    embeddings["Embeddings Service\n(runs embedding_service.py)\nmay start Ollama inside container"]
    ollama_primary["Ollama Primary\n(preload script ollama_preload.sh)\npersistent model(s) -> VRAM"]
    ollama_secondary["Ollama Secondary\n(lazy load ollama_lazy_load.sh)\non-demand models"]
    vllm_secondary["vLLM Services\n(HF models, on-demand)"]
    openwebui["OpenWebUI (chat)"]
    n8n["n8n (workflows)"]
    playground["Playground Container\n(dev tools, start-vllm, Ollama CLI)"]
  end

  %% ROUTING & DEPENDENCIES
  DockerEngine --> Containers

  %% CONFIG FLOWS
  config --> lite
  scripts --> postgres
  scripts --> pgvector
  scripts --> ollama_primary
  scripts --> ollama_secondary
  scripts --> embeddings
  dockerfiles --> embeddings
  dockerfiles --> ollama_primary
  dockerfiles --> ollama_secondary
  dockerfiles --> vllm_secondary
  dockerfiles --> playground

  %% STORAGE / MODEL FLOW
  ollama_primary -->|writes/reads| models_dir
  ollama_secondary -->|writes/reads| models_dir
  vllm_secondary -->|cache/read| models_dir
  embeddings -->|writes/reads| models_dir
  embeddings -->|calls| ollama_primary
  embeddings -->|calls| vllm_secondary

  %% DATABASES / DATA LAYER
  lite -->|logs requests| postgres
  lite -->|routes inference to| ollama_primary
  lite -->|routes inference to| ollama_secondary
  lite -->|routes inference to| vllm_secondary
  lite -->|calls embeddings| embeddings

  qdrant -->|stores vectors| data_dir
  chroma -->|stores vectors| data_dir
  pgvector -->|stores vectors| postgres

  mongo -->|stores metadata| data_dir
  redis -->|caching & rate limit| lite
  n8n -->|uses| lite
  openwebui -->|uses| lite

  %% MONITORING / OBSERVABILITY
  gpu_exporter --> prom
  lite --> prom
  embeddings --> prom
  ollama_primary --> prom
  ollama_secondary --> prom
  vllm_secondary --> prom
  postgres --> prom
  qdrant --> prom
  mongo --> prom
  redis --> prom

  prom --> grafana
  grafana -->|provisioned dashboards| monitoring

  %% EXTERNAL ACCESS
  openwebui -->|port 5151| Users["Users / Apps"]
  lite -->|port 4000| Users
  grafana -->|port 3000| Ops["Ops / SRE"]
  n8n -->|port 5678| Automation

  %% DEPLOYMENT PHASES (annotation)
  classDef phase fill:#f9f,stroke:#333,stroke-width:1px;
  phase1(["Phase 1: Foundation\nPrometheus, Grafana, Postgres, LiteLLM"]):::phase
  phase2(["Phase 2: Data Layer\nQdrant, MongoDB, Redis, pgvector"]):::phase
  phase3(["Phase 3: Models\nEmbeddings, Ollama/vLLM Primary & Secondary"]):::phase
  phase4(["Phase 4: UIs\nOpenWebUI, n8n, Playground"]):::phase

  compose_cmd --> phase1
  compose_cmd --> phase2
  compose_cmd --> phase3
  compose_cmd --> phase4
```

---

## Deployment sequence (concise)
1. deploy.sh (or docker compose) reads `.env.template` and `docker-compose*.yaml`, then instructs Docker to build images from `dockerfiles/` and start containers with mounted volumes (`/mnt/ai8_arch/models`, `/mnt/ai8_arch/data`, `/mnt/ai8_arch/logs`).
2. DB init: Postgres runs `init-postgres.sh` (mounted in `/docker-entrypoint-initdb.d`) → schemas, extensions, initial DBs created. `pgvector` runs `init-pgvector.sh`.
3. LiteLLM reads `config/litellm_config.yaml` to register model aliases and routing; logs to Postgres.
4. Model services:
   - Ollama primary runs `ollama_preload.sh` to pull & preload persistent models into VRAM.
   - Ollama secondary runs `ollama_lazy_load.sh` (on‑demand load, auto‑unload).
   - vLLM services serve HF models (via docker‑compose‑vllm.yaml).
   - All use `models/` volume for persistence.
5. Embeddings service (`embedding_service.py`) interfaces with Ollama or HuggingFace models to produce embeddings, caches HF models under the shared cache.
6. Prometheus scrapes exporters and services; Grafana reads Prometheus and auto‑provisions dashboards (monitoring/grafana/*).
7. UIs (OpenWebUI, n8n, Playground) call LiteLLM (port 4000) and embedding service (port 8010) for RAG workflows.

---

## Text snippet (from thread)
I created a mermaid diagram and concise sequence showing how each class of file participates in the deployment lifecycle and where to find the key pieces in the repo. If you want, I can (a) export this diagram to PNG/SVG, (b) embed it into a single-slide PPTX, or (c) expand the diagram into a sequence diagram showing the runtime call order for a sample RAG request — tell me which option you prefer and I will generate it next.

---

## Convert to PPTX (one-line)
Install Marp CLI (if needed) and export:

1) Install:
- npm: npm install -g @marp-team/marp-cli
- or use npx without global install

2) Convert:
```bash
npx @marp-team/marp-cli AI8_deployment_single_slide.md --pptx -o ai8_deployment_slide.pptx
```

Notes:
- Marp will render the Mermaid diagram into the slide. If you prefer a PNG or SVG instead:
```bash
npx @marp-team/marp-cli AI8_deployment_single_slide.md -o ai8_deployment_slide.png
```

---
```