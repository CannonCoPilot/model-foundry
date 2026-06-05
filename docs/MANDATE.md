**Project Mandate: AI Model Serving Architecture Refactoring**

**1.0 Overview**

This document serves as the primary requirements and implementation plan for the refactoring of the AI model serving architecture, hereby designated `ai8_stack`. It supersedes all previous planning documentation. The core objective is to re-architect the system to comply with new server resource constraints, which mandate a maximum of two GPUs for perpetual use, with dynamic, load-based allocation for the remaining six GPUs. This initiative requires a comprehensive overhaul, including revising documentation, refactoring configuration files, redirecting container volumes, and managing model files.

**2.0 Core Architectural Constraints: GPU Usage Policy**

*   **Perpetual Use GPUs:** A maximum of two GPUs (specifically, GPU 6 and GPU 7) are designated for models in a persistent or semi-persistent state.
*   **Dynamic Use GPUs:** Two additional GPUs (GPU 4 and GPU 5) are reserved for incidental, on-demand use. Their allocation must be managed dynamically based on real-time system load.

**3.0 System Architecture & Service Requirements**

**3.1 Model Tiers & GPU Allocation**

The architecture will categorize models into two tiers with distinct serving strategies on the designated primary GPUs (6 and 7):

*   **Tier 1 (Persistent Services):** A set of smaller, frequently used models will be loaded into a persistent state on GPUs 6 and 7. The total VRAM footprint on each of these two GPUs should be balanced to be approximately equal (~10GB).
*   **Tier 2 (On-Demand Services):** Two large, high-memory-footprint models (`Qwen3-Omni-30B` and `gpt-oss-120b`) will be assigned to GPUs 6 and 7 respectively, but will not be perpetually loaded. They will be loaded into VRAM on the first user request (API call or chat message) and will remain active with a 2-hour inactivity timeout. This "wake-up" mechanism balances VRAM conservation with acceptable initial latency for a user's work session.

**3.2 Service Containerization Strategy**

*   **Dedicated LLM Services:** With the exception of embeddings and utility models, every language model will be deployed in its own dedicated container service.
*   **Consolidated Embeddings Service:** All embedding, reranking, and transcription models will be consolidated and served from a single container service.

**3.3 Dynamic GPU Load Balancing for Secondary Models**

Secondary models (as defined in the inventory) must be loaded onto available GPUs according to the following prioritized logic:
1.  If GPU 7 has no secondary model loaded, load the new model to GPU 7.
2.  Else, if GPU 6 has no secondary model loaded, load the new model to GPU 6.
3.  Else, if GPU 5 has a minimum of 90% free VRAM, load the new model to GPU 5.
4.  Else, if GPU 4 has a minimum of 90% free VRAM, load the new model to GPU 4.
5.	Else, load the new model into VRAM by spreading across all low-usage GPUs from 0-5, with allocation managed dynamically based on real-time system load.


**3.4 API Gateway**

*   A `litellm` gateway will be implemented as the central entry point for all model requests.
*   The gateway must be configured to route requests using the model `Alias` specified in the inventory table below.
*   The gateway will expose all necessary API endpoints for each configured model.

**4.0 Model Inventory & Configuration**

All models will be sourced from HuggingFace. Models are categorized as "Primary" (persistent, smaller models on GPUs 6/7) or "Secondary" (larger, on-demand models).

| Model                  | Alias        | Source                                                     | Tag                                      | Quant | Size (GB) | GPUs | Primary | Secondary |
| ---------------------- | ------------ | ---------------------------------------------------------- | ---------------------------------------- | ----- | --------- | ---- | :-----: | :-------: |
| Qwen3 4B               | Qwen3_4B     | `https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507`       | `Qwen/Qwen3-4B-Thinking-2507`            | BF16  | 8         | 1    |    x    |           |
| Jasper Vision          | Jasper       | `https://huggingface.co/NovaSearch/jasper_en_vision_language_v1` | `NovaSearch/jasper_en_vision_language_v1`| BF16  | 4         | 1    |    x    |           |
| Qwen3 Embed            | Qwen3_Embed  | `https://huggingface.co/Qwen/Qwen3-Embedding-0.6B`         | `Qwen/Qwen3-Embedding-0.6B`              | BF16  | 1         | 1    |    x    |           |
| BGE-M3 Embed           | BGE_Embed    | `https://huggingface.co/BAAI/bge-m3`                       | `BAAI/bge-m3`                            | BF16  | 5         | 1    |    x    |           |
| Qwen3 Rerank           | Qwen3_Rank   | `https://huggingface.co/Qwen/Qwen3-Reranker-0.6B`          | `Qwen/Qwen3-Reranker-0.6B`               | BF16  | 1         | 1    |    x    |           |
| BGE-M3 Rerank          | BGE_Rank     | `https://huggingface.co/BAAI/bge-reranker-v2-m3`           | `BAAI/bge-reranker-v2-m3`                | F32   | 2         | 1    |    x    |           |
| Parakeet v3            | Parakeet     | `https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3`       | `nvidia/parakeet-tdt-0.6b-v3`            | F16   | 3         | 1    |    x    |           |
| Qwen3-Omni             | Qwen3_Omni   | `https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct`  | `Qwen/Qwen3-Omni-30B-A3B-Instruct`       | BF16  | 70        | 1    |         |     x     |
| gpt-oss-120b           | GPT_OSS      | `https://huggingface.co/unsloth/gpt-oss-120b-GGUF`         | `unsloth/gpt-oss-120b-GGUF`              | Q8_K_XL | 65        | 1    |         |     x     |
| Llama 3.3 70b          | Llama3_70B   | `https://huggingface.co/unsloth/Llama-3.3-70B-Instruct-GGUF` | `unsloth/Llama-3.3-70B-Instruct-GGUF`      | Q8_K_XL | 80        | 1    |         |     x     |

**5.0 Phased Implementation Plan**

Execute the following stages sequentially. Each stage must be fully functional and tested before proceeding to the next.  You may not proceed to the next numbered stage until so instructed by the principle user who is directing this work.

**Stage 0: Environment Setup**
*   Initialize and activate a Python 3.10+ virtual environment for the `ai8_stack` project.
*   Use `uv` for package management, with `pip3` as a fallback.
*	Review and revise all additional project planning documentation in `/rhome/nathanielc/ai8_stack/docs` to bring all details in line with the specifications of this document `/rhome/nathanielc/ai8_stack/docs/MANDATE.md`.

**Stage 1: Model & Documentation Management**
*   Create a dedicated subdirectory for each model within `/rhome/nathanielc/ai8_stack/models`, keeping in mind any necessary compatibility with pulling and storing model files from HuggingFace using llama.cpp, LM Studio, or vLLM package utilities.
*   Download all required model files to their respective subdirectories.
*   Update the `inventory.txt` and `README.md` files in the models directory to reflect the new inventory, file structure, model types and features and general overview of the model manager architecture.

**Stage 2: Persistent Service Deployment**
*   **2a. Primary Model Service:** Deploy the persistent Docker service for `Qwen3 4B` on either GPU 6 or 7.
*   **2b. Consolidated Utility Service:** Deploy a single, persistent Docker service for all embedding, reranking, vision, and transcription models (`Jasper Vision`, `Qwen3 Embed`, `BGE-M3 Embed`, `Qwen3 Rerank`, `BGE-M3 Rerank`, `Parakeet v3`). Allocate this across GPU 6 and 7 such that each and every model is allocated to a single one of the two GPUs, and so that the total memory footprint placed on each of GPUs 6 and 7 is approximately equal.

**Stage 3: On-Demand Secondary Service Deployment**
*   Deploy the following models as individual, on-demand services with a 3-hour inactivity timeout, configured to adhere to the dynamic GPU load balancing logic for GPUs 6 and 7:
    *   `Llama 3.3 70b`
    *   `gpt-oss-120b`
    *   `Qwen3-Omni`

**Stage 4: Model Playground Service**
*   Deploy a dedicated container service for a "Model Playground" environment.
*   This service will be exclusively powered by Ollama, allowing users to pull and run any available Ollama model via API calls.
*	This service will be spread across GPUs 4 and 5, and will have an inactivity timeout of 1 hour, and its data stored in volumes will not persist beyond model timeout or the restarting of the container service.

**Stage 5: API Gateway Implementation & Testing**
*   Deploy and configure the `litellm` gateway to manage access to all services implemented in Stages 2 and 3.
*   Develop a comprehensive test suite with a dedicated script for each model. These scripts must validate API endpoints and functionality, serving as a full regression test set.

**Stage 6: Monitoring Stack**
*   Deploy the monitoring stack using CPU-allocated container services.
*   Configure, test, and deploy each component sequentially:
    *   **6a.** Prometheus
    *   **6b.** NVIDIA GPU Exporter (may need to be a GPU-allocated service. If so, load on GPU 5)
    *   **6c.** Grafana
    *   **6d.** PostgreSQL (for utilities and monitoring data)

**Stage 7: Data Layer Services**
*   Deploy the following databases, each in its own dedicated container service: `Qdrant`, `Chroma`, `MongoDB`, `Redis`.
*   Configure persistent, resilient volumes for each database to prevent data loss on container restarts.
*   Update model service configurations to include connections/pointers to these data services as required.

**Stage 8: User Interface - OpenWebUI**
*   Deploy `OpenWebUI` in its own container service.
*   Configure persistent volumes for OpenWebUI data storage.
*   Configure volumes to point to the primary (`Qwen3 4B`) and secondary (`Llama 3.3 70b`, `gpt-oss-120b`, `Qwen3-Omni`) model services.
*   Post-deployment, manually configure model connections and user accounts within the OpenWebUI admin interface.

**Stage 9: Workflow Automation - n8n**
*   Deploy `n8n` in its own container service, exposing its browser-based GUI for remote user access.
*   Ensure the `n8n` service can discover and interact with all currently running model services (including the consolidated embeddings service).
*   Investigate and implement a solution for persistent, user-based workspaces and storage within the Docker volume architecture.
*   **Validation:** Create and successfully execute a simple agentic workflow within the `n8n` GUI that utilizes the models served by the `ai8_stack` architecture.  This will be delivered to the principle user as a workflow file that can be uploaded into the user's workspace for further testing and experimentation.

**6.0 Core Design & Accessibility Principles**

*   **Remote-First Access:** The entire architecture, including API endpoints, database interactions, and file retrieval, must be designed for seamless access by end-users from their local machines. Testing scripts and demos should primarily use Python or cURL to reflect this remote-first paradigm. The IP of the server to be used is 10.45.2.134, and no additional authentication is required to send and recieve API calls and responses.
*   **Documentation Fallback:** In cases where this document lacks sufficient detail, implementation strategies should be derived from existing planning documents located in `/rhome/nathanielc/ai8_stack/docs`.  Ensure that all additional documentation in the `/docks` folder has been revised and updated to be fully consistent with the new project requirements outlined here, and that all documents are fully internally consistent on points of design, stages of development and implementation, and final exit criteria for project completion.