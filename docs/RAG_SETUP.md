# RAG Pipeline Setup Guide

**Base Path**: `/mnt/ai8_arch`

## Available Database Services

### 1. Qdrant (Vector Database)
**Best for:** Fast similarity search, production RAG pipelines

**Connection:**
```python
from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")
```

**Features:**
- High-performance vector search
- Collections for different document sets
- Filtering and hybrid search
- REST API + gRPC

**Access:**
- HTTP API: `http://localhost:6333`
- gRPC: `http://localhost:6334`
- Dashboard: `http://localhost:6333/dashboard`

### 2. pgvector (PostgreSQL + Vector Extension)
**Best for:** SQL-based workflows, joining with relational data

**Connection:**
```python
CONNECTION_STRING = "postgresql://llmuser:password@localhost:5433/vectors"
```

**Features:**
- Native PostgreSQL integration
- ACID compliance
- Join vectors with structured data
- HNSW and IVFFlat indexes

**Access:**
- Port: `5433`
- Database: `vectors`
- Tables: `document_embeddings`, `documents`

### 3. MongoDB (Document Store)
**Best for:** Document metadata, unstructured data, flexible schemas

**Connection:**
```python
from pymongo import MongoClient
client = MongoClient("mongodb://admin:password@localhost:27017/")
```

**Features:**
- Flexible JSON documents
- Fast reads/writes
- GridFS for large files
- Aggregation pipelines

**Access:**
- Port: `27017`
- Database: `rag_documents`

### 4. Redis (Cache)
**Best for:** LLM response caching, session management, fast lookups

**Connection:**
```python
import redis
client = redis.from_url("redis://:password@localhost:6379/0")
```

**Features:**
- In-memory speed
- TTL support
- Pub/sub messaging
- LangChain cache integration

**Access:**
- Port: `6379`
- Password: From `.env`

## Recommended Architectures

### Small-Scale RAG (< 10k documents)
```
pgvector → Embeddings → LLM
```
- Single database for vectors and metadata
- Simple setup
- Good performance

### Medium-Scale RAG (10k - 1M documents)
```
Qdrant (vectors) + MongoDB (metadata) + Redis (cache) → Embeddings → LLM
```
- Separated concerns
- Better performance
- Scalable

### Large-Scale RAG (> 1M documents)
```
Qdrant (vectors) + pgvector (backup) + MongoDB (metadata) + Redis (cache) → Embeddings → LLM
```
- Hybrid search
- Redundancy
- Maximum performance

## Example Workflows

### 1. Document Ingestion
```python
# 1. Parse document (your code)
text = parse_pdf("document.pdf")

# 2. Chunk text
chunks = chunk_text(text, size=1000, overlap=200)

# 3. Generate embeddings
embeddings = embeddings_model.embed_documents(chunks)

# 4. Store in Qdrant
from qdrant_client.models import PointStruct
points = [
    PointStruct(id=i, vector=emb, payload={"text": chunk})
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
]
client.upsert(collection_name="docs", points=points)

# 5. Store metadata in MongoDB
mongo_db.documents.insert_one({
    "doc_id": "doc1",
    "filename": "document.pdf",
    "num_chunks": len(chunks),
    "uploaded": datetime.now()
})
```

### 2. RAG Query
```python
# 1. Get query embedding
query_embedding = embeddings_model.embed_query("What is AI?")

# 2. Search Qdrant
results = client.search(
    collection_name="docs",
    query_vector=query_embedding,
    limit=5
)

# 3. Prepare context
context = "\n\n".join([r.payload["text"] for r in results])

# 4. Query LLM
prompt = f"Context: {context}\n\nQuestion: What is AI?\n\nAnswer:"
response = llm.invoke(prompt)
```

## Testing Database Connections

```bash
# Test Qdrant
curl http://localhost:6333/healthz

# Test pgvector
psql -h localhost -p 5433 -U llmuser -d vectors -c "SELECT version();"

# Test MongoDB
mongosh --host localhost:27017 -u admin -p password --eval "db.adminCommand('ping')"

# Test Redis
redis-cli -h localhost -p 6379 -a password ping
```

## Backup and Maintenance

### Qdrant Backup
```bash
# Data stored in: /mnt/ai8_arch/data/qdrant/
tar -czf qdrant_backup.tar.gz /mnt/ai8_arch/data/qdrant/
```

### pgvector Backup
```bash
docker exec llm-pgvector pg_dump -U llmuser vectors > vectors_backup.sql
```

### MongoDB Backup
```bash
docker exec llm-mongodb mongodump --out=/data/backup
```

### Redis Backup
```bash
# Redis auto-saves to /mnt/ai8_arch/data/redis/
# Manual save:
docker exec llm-redis redis-cli -a password SAVE
```

## Performance Tuning

### Qdrant
- Use HNSW index for speed
- Adjust `m` and `ef_construct` parameters
- Enable quantization for large collections

### pgvector
- Use HNSW index: `CREATE INDEX ... USING hnsw`
- Tune `maintenance_work_mem` for index building
- Use `vector_cosine_ops` for cosine similarity

### MongoDB
- Create indexes on frequently queried fields
- Use projections to reduce data transfer
- Enable WiredTiger compression

### Redis
- Set appropriate `maxmemory` policy
- Use connection pooling
- Enable Redis persistence if needed
```