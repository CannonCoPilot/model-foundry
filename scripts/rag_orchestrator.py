#!/usr/bin/env python3
"""
RAG Orchestration Service
Handles: Document Upload → Processing → Embedding → Storage → Retrieval → Generation
Base Path: /mnt/ai8_arch
"""
import os
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import hashlib
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Orchestration Service")

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBEDDING_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8010")
UNSTRUCTURED_URL = os.getenv("UNSTRUCTURED_URL", "http://localhost:8001")
LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")

CACHE_DIR = Path("/app/cache")
CACHE_DIR.mkdir(exist_ok=True)

# Qdrant client
qdrant_client = QdrantClient(url=QDRANT_URL)

# HTTP client with timeout
http_client = httpx.AsyncClient(timeout=300.0)

# Pydantic models
class DocumentUpload(BaseModel):
    collection_name: str = "default"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "stella"

class QueryRequest(BaseModel):
    query: str
    collection_name: str = "default"
    top_k: int = 5
    llm_model: str = "gpt-oss-120b"
    include_sources: bool = True

class QueryResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    query: str
    model_used: str

# Helper functions
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        
        if start >= text_len:
            break
    
    return chunks

async def parse_document(file_path: Path) -> str:
    """Parse document using Unstructured.io"""
    try:
        with open(file_path, "rb") as f:
            files = {"files": (file_path.name, f)}
            response = await http_client.post(
                f"{UNSTRUCTURED_URL}/general/v0/general",
                files=files
            )
            response.raise_for_status()
            
        # Extract text from response
        elements = response.json()
        text = "\n\n".join([elem.get("text", "") for elem in elements])
        return text
    except Exception as e:
        logger.error(f"Document parsing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing error: {str(e)}")

async def get_embeddings(texts: List[str], model: str = "stella") -> List[List[float]]:
    """Get embeddings from embedding service"""
    try:
        response = await http_client.post(
            f"{EMBEDDING_URL}/v1/embeddings",
            json={"model": model, "input": texts}
        )
        response.raise_for_status()
        return response.json()["embeddings"]
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")

async def query_llm(prompt: str, model: str, context: str) -> str:
    """Query LLM through LiteLLM gateway"""
    try:
        response = await http_client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant. Answer based on the provided context."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"}
                ],
                "temperature": 0.7
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM query failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

# Ensure collection exists
def ensure_collection(collection_name: str, vector_size: int = 1024):
    """Create collection if it doesn't exist"""
    collections = [c.name for c in qdrant_client.get_collections().collections]
    
    if collection_name not in collections:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        logger.info(f"Created collection: {collection_name}")

# API endpoints
@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "qdrant": QDRANT_URL,
        "embeddings": EMBEDDING_URL,
        "unstructured": UNSTRUCTURED_URL,
        "litellm": LITELLM_URL
    }

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection_name: str = "default",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    embedding_model: str = "stella"
):
    """Upload and process document into RAG system"""
    logger.info(f"Uploading document: {file.filename}")
    
    # Save uploaded file
    file_path = CACHE_DIR / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    try:
        # Parse document
        logger.info("Parsing document...")
        text = await parse_document(file_path)
        
        # Chunk text
        logger.info("Chunking text...")
        chunks = chunk_text(text, chunk_size, chunk_overlap)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Get embeddings
        logger.info("Generating embeddings...")
        embeddings = await get_embeddings(chunks, embedding_model)
        
        # Ensure collection exists
        ensure_collection(collection_name, vector_size=len(embeddings[0]))
        
        # Store in Qdrant
        logger.info("Storing in vector database...")
        points = [
            PointStruct(
                id=hashlib.md5(f"{file.filename}_{i}".encode()).hexdigest()[:16],
                vector=emb,
                payload={
                    "text": chunk,
                    "source": file.filename,
                    "chunk_index": i,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]
        
        qdrant_client.upsert(collection_name=collection_name, points=points)
        
        logger.info(f"Successfully processed {file.filename}")
        return {
            "status": "success",
            "filename": file.filename,
            "chunks": len(chunks),
            "collection": collection_name
        }
    
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        if file_path.exists():
            file_path.unlink()

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Query RAG system with retrieval and generation"""
    logger.info(f"Query: {request.query}")
    
    try:
        # Get query embedding
        query_embedding = (await get_embeddings([request.query], "stella"))[0]
        
        # Search vector database
        results = qdrant_client.search(
            collection_name=request.collection_name,
            query_vector=query_embedding,
            limit=request.top_k
        )
        
        if not results:
            return QueryResponse(
                answer="No relevant documents found.",
                sources=[],
                query=request.query,
                model_used=request.llm_model
            )
        
        # Prepare context
        context = "\n\n---\n\n".join([
            f"[Source: {r.payload['source']}, Chunk {r.payload['chunk_index']}]\n{r.payload['text']}"
            for r in results
        ])
        
        # Generate answer
        answer = await query_llm(request.query, request.llm_model, context)
        
        # Prepare sources
        sources = [
            {
                "source": r.payload["source"],
                "chunk_index": r.payload["chunk_index"],
                "score": r.score,
                "text": r.payload["text"][:200] + "..."
            }
            for r in results
        ] if request.include_sources else None
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            model_used=request.llm_model
        )
    
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections")
async def list_collections():
    """List all collections"""
    collections = qdrant_client.get_collections()
    return {
        "collections": [
            {
                "name": c.name,
                "points_count": qdrant_client.get_collection(c.name).points_count,
                "vector_size": qdrant_client.get_collection(c.name).config.params.vectors.size
            }
            for c in collections.collections
        ]
    }

@app.delete("/collection/{collection_name}")
async def delete_collection(collection_name: str):
    """Delete a collection"""
    try:
        qdrant_client.delete_collection(collection_name)
        return {"status": "deleted", "collection": collection_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```