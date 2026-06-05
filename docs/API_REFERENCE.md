# AI8 Architecture - API Reference

**Version:** 1.0.0  
**Last Updated:** 2025-01-11  
**Author:** CannonCoPilot

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [LiteLLM Gateway API](#litellm-gateway-api)
4. [Model-Specific APIs](#model-specific-apis)
5. [Embedding Service API](#embedding-service-api)
6. [Vector Database APIs](#vector-database-apis)
7. [Monitoring APIs](#monitoring-apis)
8. [Code Examples](#code-examples)

---

## Overview

AI8 Architecture exposes multiple API layers:

1. **LiteLLM Gateway** (Port 4000): Unified OpenAI-compatible API
2. **Direct Model APIs**: Native Ollama/vLLM endpoints
3. **Embedding Service** (Port 8010): Multi-model embeddings
4. **Vector Databases**: Qdrant (6333), pgvector (5433)
5. **Monitoring**: Prometheus (9090), Grafana (3000)

**Recommended**: Use LiteLLM Gateway for all production workloads.

---

## Authentication

### LiteLLM Gateway

**Bearer Token Authentication**:
```bash
# Set in .env file
LITELLM_MASTER_KEY=sk-your-secure-key-here

# Use in requests
curl -H "Authorization: Bearer sk-your-secure-key-here" \
  http://localhost:4000/v1/models
```

**Python Example**:
```python
import openai

openai.api_base = "http://localhost:4000/v1"
openai.api_key = "sk-your-secure-key-here"

response = openai.ChatCompletion.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Direct Model APIs

**Ollama** (No authentication by default):
```bash
curl http://localhost:11601/api/tags
```

**vLLM** (No authentication by default):
```bash
curl http://localhost:8001/v1/models
```

⚠️ **Security Note**: Direct APIs are exposed for development. In production, use LiteLLM or add reverse proxy with auth.

---

## LiteLLM Gateway API

**Base URL**: `http://localhost:4000`

**OpenAI Compatible**: Drop-in replacement for OpenAI API

### List Models

**Endpoint**: `GET /v1/models`

**Request**:
```bash
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://localhost:4000/v1/models
```

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-oss-120b",
      "object": "model",
      "created": 1704931200,
      "owned_by": "ai8-architecture"
    },
    {
      "id": "qwen3-omni",
      "object": "model",
      "created": 1704931200,
      "owned_by": "ai8-architecture"
    },
    {
      "id": "deepseek-v2",
      "object": "model",
      "created": 1704931200,
      "owned_by": "ai8-architecture"
    },
    {
      "id": "nomic-embed-text-v1.5",
      "object": "model",
      "created": 1704931200,
      "owned_by": "ai8-architecture"
    }
  ]
}
```

---

### Chat Completions

**Endpoint**: `POST /v1/chat/completions`

**Request**:
```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Model ID (from `/v1/models`) |
| `messages` | array | Yes | Conversation history |
| `temperature` | float | No | 0.0-2.0, default 0.7 |
| `max_tokens` | integer | No | Max tokens to generate |
| `stream` | boolean | No | Stream response (default: false) |
| `top_p` | float | No | Nucleus sampling (default: 1.0) |
| `frequency_penalty` | float | No | -2.0 to 2.0 (default: 0) |
| `presence_penalty` | float | No | -2.0 to 2.0 (default: 0) |

**Response**:
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-oss-120b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 10,
    "total_tokens": 30
  }
}
```

**Streaming Response**:
```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "stream": true
  }' \
  --no-buffer
```

**Streaming Response Format** (SSE):
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-oss-120b","choices":[{"delta":{"role":"assistant"},"index":0,"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-oss-120b","choices":[{"delta":{"content":"Once"},"index":0,"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-oss-120b","choices":[{"delta":{"content":" upon"},"index":0,"finish_reason":null}]}

...

data: [DONE]
```

---

### Text Completions

**Endpoint**: `POST /v1/completions`

**Request**:
```bash
curl -X POST http://localhost:4000/v1/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "prompt": "The quick brown fox",
    "max_tokens": 50,
    "temperature": 0.7
  }'
```

**Response**:
```json
{
  "id": "cmpl-abc123",
  "object": "text_completion",
  "created": 1677652288,
  "model": "gpt-oss-120b",
  "choices": [
    {
      "text": " jumps over the lazy dog. This pangram contains every letter of the English alphabet.",
      "index": 0,
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 4,
    "completion_tokens": 16,
    "total_tokens": 20
  }
}
```

---

### Embeddings

**Endpoint**: `POST /v1/embeddings`

**Request**:
```bash
curl -X POST http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed-text-v1.5",
    "input": "The quick brown fox jumps over the lazy dog"
  }'
```

**Multiple Inputs**:
```bash
curl -X POST http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mxbai-embed-large-v1",
    "input": [
      "First document text",
      "Second document text",
      "Third document text"
    ]
  }'
```

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.0023, -0.009, 0.015, ...],  // 768 or 1024 dimensions
      "index": 0
    }
  ],
  "model": "nomic-embed-text-v1.5",
  "usage": {
    "prompt_tokens": 9,
    "total_tokens": 9
  }
}
```

---

## Model-Specific APIs

### Ollama API (Direct)

**Base URLs**:
- Primary GPT-OSS: `http://localhost:11601`
- Secondary DeepSeek: `http://localhost:11603`
- Playground: `http://localhost:11620`
- Embeddings (Ollama): `http://localhost:11610`

#### Generate Completion

**Endpoint**: `POST /api/generate`

**Request**:
```bash
curl -X POST http://localhost:11601/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "prompt": "Why is the sky blue?",
    "stream": false
  }'
```

**Parameters**:
```json
{
  "model": "string",           // Required
  "prompt": "string",          // Required
  "stream": false,             // Optional (default: true)
  "keep_alive": "5m",          // Optional (5m, 10m, -1 for permanent)
  "options": {                 // Optional
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "num_predict": 100
  }
}
```

**Response**:
```json
{
  "model": "gpt-oss-120b",
  "created_at": "2025-01-11T04:45:45.123Z",
  "response": "The sky appears blue because...",
  "done": true,
  "context": [1, 2, 3, ...],
  "total_duration": 5000000000,
  "load_duration": 1000000000,
  "prompt_eval_duration": 1000000000,
  "eval_duration": 3000000000,
  "eval_count": 50
}
```

#### Chat Completion

**Endpoint**: `POST /api/chat`

**Request**:
```bash
curl -X POST http://localhost:11601/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false
  }'
```

**Response**:
```json
{
  "model": "gpt-oss-120b",
  "created_at": "2025-01-11T04:45:45.123Z",
  "message": {
    "role": "assistant",
    "content": "Hello! How can I help you today?"
  },
  "done": true,
  "total_duration": 2000000000
}
```

#### List Models

**Endpoint**: `GET /api/tags`

```bash
curl http://localhost:11601/api/tags
```

**Response**:
```json
{
  "models": [
    {
      "name": "gpt-oss-120b",
      "modified_at": "2025-01-11T00:00:00.000Z",
      "size": 196000000000,
      "digest": "sha256:abc123...",
      "details": {
        "format": "gguf",
        "family": "llama",
        "parameter_size": "120B",
        "quantization_level": "Q4_K_M"
      }
    }
  ]
}
```

#### Show Model Info

**Endpoint**: `POST /api/show`

```bash
curl -X POST http://localhost:11601/api/show \
  -d '{"name": "gpt-oss-120b"}'
```

---

### vLLM API (Direct)

**Base URLs**:
- Primary Qwen3-VL: `http://localhost:8001`

#### List Models

**Endpoint**: `GET /v1/models`

```bash
curl http://localhost:8001/v1/models
```

#### Chat Completions

**Endpoint**: `POST /v1/chat/completions`

Same format as LiteLLM, but direct to vLLM:

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-omni",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

#### Completions

**Endpoint**: `POST /v1/completions`

```bash
curl -X POST http://localhost:8001/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-omni",
    "prompt": "Once upon a time",
    "max_tokens": 100
  }'
```

---

## Embedding Service API

**Base URL**: `http://localhost:8010`

### Health Check

**Endpoint**: `GET /health`

```bash
curl http://localhost:8010/health
```

**Response**:
```json
{
  "status": "healthy",
  "ollama": "healthy",
  "gpu_available": true,
  "gpu_count": 1,
  "available_models": ["nomic-embed-text-v1.5", "mxbai-embed-large-v1"],
  "loaded_hf_models": ["mixedbread-ai/mxbai-embed-large-v1"]
}
```

### List Models

**Endpoint**: `GET /models`

```bash
curl http://localhost:8010/models
```

**Response**:
```json
{
  "models": {
    "nomic": {
      "type": "ollama",
      "name": "nomic-embed-text-v1.5-text:137m-v1.5-fp16",
      "dimensions": 768,
      "max_tokens": 8192
    },
    "stella": {
      "type": "hf",
      "name": "mixedbread-ai/mxbai-embed-large-v1",
      "dimensions": 1024,
      "max_tokens": 512
    }
  }
}
```

### Generate Embeddings

**Endpoint**: `POST /v1/embeddings`

**Request**:
```bash
curl -X POST http://localhost:8010/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mxbai-embed-large-v1",
    "input": ["First text", "Second text"]
  }'
```

**Response**:
```json
{
  "model": "mxbai-embed-large-v1",
  "embeddings": [
    [0.023, -0.045, 0.067, ...],  // 1024 dimensions
    [0.012, -0.034, 0.056, ...]
  ],
  "dimensions": 1024,
  "num_texts": 2
}
```

---

## Vector Database APIs

### Qdrant API

**Base URL**: `http://localhost:6333`

**Documentation**: https://qdrant.tech/documentation/

#### Create Collection

```bash
curl -X PUT http://localhost:6333/collections/my_collection \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
```

#### Insert Points

```bash
curl -X PUT http://localhost:6333/collections/my_collection/points \
  -H "Content-Type: application/json" \
  -d '{
    "points": [
      {
        "id": 1,
        "vector": [0.1, 0.2, 0.3, ...],
        "payload": {"text": "First document", "category": "tech"}
      },
      {
        "id": 2,
        "vector": [0.4, 0.5, 0.6, ...],
        "payload": {"text": "Second document", "category": "science"}
      }
    ]
  }'
```

#### Search Similar Vectors

```bash
curl -X POST http://localhost:6333/collections/my_collection/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, 0.3, ...],
    "limit": 5,
    "with_payload": true,
    "with_vector": false
  }'
```

**Response**:
```json
{
  "result": [
    {
      "id": 1,
      "score": 0.95,
      "payload": {"text": "First document", "category": "tech"},
      "version": 0
    }
  ],
  "status": "ok",
  "time": 0.002
}
```

#### Filter Search

```bash
curl -X POST http://localhost:6333/collections/my_collection/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, 0.3, ...],
    "filter": {
      "must": [
        {"key": "category", "match": {"value": "tech"}}
      ]
    },
    "limit": 5
  }'
```

---

### pgvector (PostgreSQL)

**Connection**: `postgresql://llmuser:password@localhost:5433/vectors`

#### Search Similar Vectors

```sql
-- Using pgvector distance operators
SELECT 
  document_id,
  chunk_index,
  content,
  1 - (embedding <=> '[0.1, 0.2, 0.3, ...]'::vector) as similarity
FROM document_embeddings
ORDER BY embedding <=> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;
```

#### Using Helper Function

```sql
-- Function created during init
SELECT * FROM search_similar_embeddings(
  '[0.1, 0.2, 0.3, ...]'::vector(1024),
  0.7,  -- similarity threshold
  10    -- limit
);
```

#### Insert Embedding

```sql
INSERT INTO document_embeddings (document_id, chunk_index, content, embedding)
VALUES (
  'doc_123',
  0,
  'Document text content',
  '[0.1, 0.2, 0.3, ...]'::vector(1024)
);
```

---

## Monitoring APIs

### Prometheus

**Base URL**: `http://localhost:9090`

#### Query API

```bash
# Instant query
curl 'http://localhost:9090/api/v1/query?query=nvidia_gpu_duty_cycle'

# Range query
curl 'http://localhost:9090/api/v1/query_range?query=nvidia_gpu_duty_cycle&start=2025-01-11T00:00:00Z&end=2025-01-11T04:00:00Z&step=15s'

# Get all targets
curl 'http://localhost:9090/api/v1/targets'
```

#### Common Queries

```bash
# GPU utilization
nvidia_gpu_duty_cycle

# VRAM usage (%)
nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes * 100

# GPU temperature
nvidia_gpu_temperature_celsius

# LiteLLM request rate
rate(litellm_requests_total[5m])

# Average response time
histogram_quantile(0.95, rate(litellm_request_duration_seconds_bucket[5m]))
```

---

### Grafana

**Base URL**: `http://localhost:3000`

**Login**: admin / (from .env GRAFANA_ADMIN_PASSWORD)

#### API (with authentication)

```bash
# Get API key first (in Grafana UI)
API_KEY="your_grafana_api_key"

# List dashboards
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3000/api/dashboards/home

# Get dashboard
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3000/api/dashboards/uid/gpu-dashboard

# Create alert
curl -X POST http://localhost:3000/api/alerts \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

## Code Examples

### Python (OpenAI Library)

````python name=examples/python_openai.py
#!/usr/bin/env python3
"""
AI8 Architecture - Python OpenAI Client Example
"""
import openai

# Configure client
openai.api_base = "http://localhost:4000/v1"
openai.api_key = "sk-llm-master-key-2025"  # From .env

# Chat completion
response = openai.ChatCompletion.create(
    model="gpt-oss-120b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is quantum computing?"}
    ],
    temperature=0.7,
    max_tokens=200
)

print(response.choices[0].message.content)

# Streaming chat
stream = openai.ChatCompletion.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.get("content"):
        print(chunk.choices[0].delta.content, end="", flush=True)

# Embeddings
embeddings = openai.Embedding.create(
    model="nomic-embed-text-v1.5",
    input=["Text to embed", "Another text"]
)

print(f"Embedding dimensions: {len(embeddings.data[0].embedding)}")