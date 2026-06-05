import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch
from typing import List, Union, Dict, Optional
import requests
import json
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for GPU availability
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"✅ Embedding Service: Using device: {DEVICE}")

# Configuration
MAX_MODELS_IN_MEMORY = int(os.getenv("MAX_MODELS_IN_MEMORY", "3"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

# Model registry - tracks all available models
AVAILABLE_MODELS = {
    # HuggingFace SentenceTransformers models
    "nomic-embed-text": {"type": "huggingface", "model_name": "nomic-ai/nomic-embed-text-v1.5"},
    "mxbai-embed-large": {"type": "huggingface", "model_name": "mixedbread-ai/mxbai-embed-large-v1"},
    "stella-en": {"type": "huggingface", "model_name": "dunzhang/stella_en_1.5B_v5"},
    "all-MiniLM-L6-v2": {"type": "huggingface", "model_name": "sentence-transformers/all-MiniLM-L6-v2"},
    "jasper": {"type": "huggingface", "model_name": "NovaSearch/jasper_en_vision_language_v1"},
    
    # Ollama models (served by local Ollama instance)
    "qwen3-embedding": {"type": "ollama", "model_name": "qwen3-embedding:8b-q8_0"},
    "embeddinggemma": {"type": "ollama", "model_name": "embeddinggemma:300m-bf16"},
    "gemma2-embed": {"type": "ollama", "model_name": "gemma2:2b"},
    "qwen3-embed": {"type": "ollama", "model_name": "qwen2.5:3b"},
}

# Runtime model storage
LOADED_MODELS: Dict[str, SentenceTransformer] = {}
MODEL_LAST_USED: Dict[str, datetime] = {}

app = FastAPI(title="AI8 Unified Embedding Service", version="2.0.0")

class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str]]
    encoding_format: Optional[str] = "float"

class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: list
    model: str
    usage: dict

async def ensure_ollama_model(model_name: str) -> bool:
    """Ensure Ollama model is available and loaded."""
    try:
        # Check if model exists
        response = requests.get(f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags")
        if response.status_code != 200:
            logger.warning(f"Cannot connect to Ollama at {OLLAMA_HOST}:{OLLAMA_PORT}")
            return False
            
        models = response.json().get("models", [])
        model_exists = any(model["name"].startswith(model_name.split(":")[0]) for model in models)
        
        if not model_exists:
            logger.info(f"Pulling Ollama model: {model_name}")
            pull_response = requests.post(
                f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/pull",
                json={"name": model_name}
            )
            if pull_response.status_code != 200:
                logger.error(f"Failed to pull model {model_name}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring Ollama model {model_name}: {e}")
        return False

async def get_ollama_embeddings(model_name: str, texts: List[str]) -> List[List[float]]:
    """Get embeddings from Ollama."""
    embeddings = []
    for text in texts:
        try:
            response = requests.post(
                f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/embeddings",
                json={"model": model_name, "prompt": text}
            )
            if response.status_code == 200:
                embedding = response.json().get("embedding", [])
                embeddings.append(embedding)
            else:
                logger.error(f"Ollama embedding failed for {model_name}: {response.text}")
                raise HTTPException(status_code=500, detail=f"Ollama embedding failed")
        except Exception as e:
            logger.error(f"Error getting Ollama embedding: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    return embeddings

async def load_huggingface_model(model_key: str, model_info: dict) -> SentenceTransformer:
    """Load a HuggingFace model, managing memory if needed."""
    
    # Check if we need to free memory
    if len(LOADED_MODELS) >= MAX_MODELS_IN_MEMORY:
        # Find least recently used model
        lru_model = min(MODEL_LAST_USED.items(), key=lambda x: x[1])[0]
        logger.info(f"Unloading LRU model: {lru_model}")
        del LOADED_MODELS[lru_model]
        del MODEL_LAST_USED[lru_model]
        torch.cuda.empty_cache()  # Free GPU memory
    
    # Load the model
    logger.info(f"Loading HuggingFace model: {model_info['model_name']}")
    cache_folder = os.getenv("SENTENCE_TRANSFORMERS_HOME")
    
    # Enable trust_remote_code for models that require it
    trust_remote_code = model_key in ["nomic-embed-text", "stella-en", "jasper"]
    
    model = SentenceTransformer(
        model_info["model_name"],
        device=DEVICE,
        cache_folder=cache_folder,
        trust_remote_code=trust_remote_code
    )
    
    LOADED_MODELS[model_key] = model
    MODEL_LAST_USED[model_key] = datetime.now()
    
    return model

async def get_huggingface_embeddings(model_key: str, model_info: dict, texts: List[str]) -> List[List[float]]:
    """Get embeddings from HuggingFace model."""
    
    # Check if model is already loaded
    if model_key not in LOADED_MODELS:
        await load_huggingface_model(model_key, model_info)
    
    # Update last used time
    MODEL_LAST_USED[model_key] = datetime.now()
    
    # Get embeddings
    model = LOADED_MODELS[model_key]
    embeddings = model.encode(texts, convert_to_tensor=True)
    
    return [emb.tolist() for emb in embeddings]

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "available_models": list(AVAILABLE_MODELS.keys()),
        "loaded_models": list(LOADED_MODELS.keys()),
        "device": DEVICE,
        "max_models_in_memory": MAX_MODELS_IN_MEMORY
    }

@app.get("/v1/models")
async def list_models():
    """List all available embedding models."""
    models = []
    for model_key, model_info in AVAILABLE_MODELS.items():
        models.append({
            "id": model_key,
            "object": "model",
            "type": model_info["type"],
            "model_name": model_info["model_name"],
            "loaded": model_key in LOADED_MODELS
        })
    return {"object": "list", "data": models}

@app.post("/v1/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    """Generate embeddings for given input using specified model."""
    
    if request.model not in AVAILABLE_MODELS:
        available = ", ".join(AVAILABLE_MODELS.keys())
        raise HTTPException(
            status_code=404, 
            detail=f"Model '{request.model}' not found. Available models: {available}"
        )
    
    model_info = AVAILABLE_MODELS[request.model]
    
    # Ensure input is a list
    texts = [request.input] if isinstance(request.input, str) else request.input
    
    try:
        # Route to appropriate embedding service
        if model_info["type"] == "ollama":
            await ensure_ollama_model(model_info["model_name"])
            embeddings = await get_ollama_embeddings(model_info["model_name"], texts)
        elif model_info["type"] == "huggingface":
            embeddings = await get_huggingface_embeddings(request.model, model_info, texts)
        else:
            raise HTTPException(status_code=500, detail=f"Unknown model type: {model_info['type']}")
        
        # Format response to be OpenAI compatible
        embedding_data = []
        total_tokens = sum(len(text.split()) for text in texts)
        
        for i, emb in enumerate(embeddings):
            embedding_data.append({
                "object": "embedding",
                "embedding": emb,
                "index": i
            })
        
        return EmbeddingResponse(
            data=embedding_data, 
            model=request.model,
            usage={
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens
            }
        )

    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/preload")
async def preload_models(models: List[str]):
    """Preload specific models into memory."""
    results = {}
    for model_key in models:
        if model_key not in AVAILABLE_MODELS:
            results[model_key] = "Model not found"
            continue
            
        model_info = AVAILABLE_MODELS[model_key]
        
        try:
            if model_info["type"] == "huggingface":
                await load_huggingface_model(model_key, model_info)
                results[model_key] = "Loaded successfully"
            elif model_info["type"] == "ollama":
                success = await ensure_ollama_model(model_info["model_name"])
                results[model_key] = "Prepared successfully" if success else "Failed to prepare"
        except Exception as e:
            results[model_key] = f"Error: {str(e)}"
    
    return {"results": results}

@app.delete("/admin/unload/{model_key}")
async def unload_model(model_key: str):
    """Unload a specific model from memory."""
    if model_key in LOADED_MODELS:
        del LOADED_MODELS[model_key]
        del MODEL_LAST_USED[model_key]
        torch.cuda.empty_cache()
        return {"message": f"Model {model_key} unloaded successfully"}
    else:
        raise HTTPException(status_code=404, detail=f"Model {model_key} not loaded")

# Preload default models on startup
@app.on_event("startup")
async def startup_event():
    """Preload specified models on startup."""
    preload_models_env = os.getenv("PRELOAD_MODELS", "nomic-embed-text,mxbai-embed-large")
    if preload_models_env:
        models_to_preload = [m.strip() for m in preload_models_env.split(",")]
        logger.info(f"Preloading models: {models_to_preload}")
        await preload_models(models_to_preload)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)