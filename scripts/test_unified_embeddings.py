#!/usr/bin/env python3
"""
Test script for the unified embedding service architecture
Tests all available embedding models through a single API endpoint
"""

import requests
import json
import time
import sys
from typing import List, Dict, Any

# Configuration
EMBEDDING_SERVICE_URL = "http://localhost:8010"
TEST_TEXTS = [
    "Hello, this is a test sentence for embedding generation.",
    "Machine learning and artificial intelligence are transforming technology.",
    "Vector databases store high-dimensional embeddings efficiently."
]

def test_health_check() -> bool:
    """Test if the embedding service is healthy."""
    try:
        response = requests.get(f"{EMBEDDING_SERVICE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   Available models: {data.get('available_models', [])}")
            print(f"   Loaded models: {data.get('loaded_models', [])}")
            print(f"   Device: {data.get('device', 'unknown')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_list_models() -> List[str]:
    """Test listing all available models."""
    try:
        response = requests.get(f"{EMBEDDING_SERVICE_URL}/v1/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            print(f"✅ Models endpoint working")
            print(f"   Found {len(models)} models:")
            
            available_models = []
            for model in models:
                model_id = model.get("id", "unknown")
                model_type = model.get("type", "unknown")
                loaded = model.get("loaded", False)
                status = "🟢 loaded" if loaded else "⚪ available"
                print(f"     • {model_id} ({model_type}) - {status}")
                available_models.append(model_id)
            
            return available_models
        else:
            print(f"❌ Models list failed: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Models list error: {e}")
        return []

def test_embedding_generation(model: str, texts: List[str]) -> bool:
    """Test embedding generation for a specific model."""
    try:
        payload = {
            "model": model,
            "input": texts
        }
        
        print(f"🧪 Testing embeddings for model: {model}")
        start_time = time.time()
        
        response = requests.post(
            f"{EMBEDDING_SERVICE_URL}/v1/embeddings",
            json=payload,
            timeout=60
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            embeddings = data.get("data", [])
            
            if len(embeddings) == len(texts):
                # Check embedding dimensions
                first_embedding = embeddings[0].get("embedding", [])
                embedding_dim = len(first_embedding)
                
                print(f"   ✅ Generated {len(embeddings)} embeddings")
                print(f"   📏 Embedding dimension: {embedding_dim}")
                print(f"   ⏱️  Time taken: {duration:.2f}s")
                print(f"   🔧 Usage: {data.get('usage', {})}")
                
                # Validate embedding values
                if embedding_dim > 0 and all(isinstance(val, (int, float)) for val in first_embedding[:10]):
                    print(f"   ✅ Embedding values are valid numbers")
                    return True
                else:
                    print(f"   ❌ Invalid embedding values")
                    return False
            else:
                print(f"   ❌ Expected {len(texts)} embeddings, got {len(embeddings)}")
                return False
        else:
            print(f"   ❌ Request failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_model_preloading() -> bool:
    """Test the model preloading functionality."""
    try:
        models_to_preload = ["nomic-embed-text", "all-MiniLM-L6-v2"]
        
        payload = models_to_preload
        
        print(f"🔄 Testing model preloading: {models_to_preload}")
        
        response = requests.post(
            f"{EMBEDDING_SERVICE_URL}/admin/preload",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", {})
            
            success_count = 0
            for model, result in results.items():
                if "successfully" in result.lower():
                    print(f"   ✅ {model}: {result}")
                    success_count += 1
                else:
                    print(f"   ⚠️  {model}: {result}")
            
            if success_count > 0:
                print(f"   ✅ Preloaded {success_count}/{len(models_to_preload)} models")
                return True
            else:
                print(f"   ❌ No models preloaded successfully")
                return False
        else:
            print(f"   ❌ Preload request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Preload error: {e}")
        return False

def test_model_unloading() -> bool:
    """Test the model unloading functionality."""
    try:
        model_to_unload = "all-MiniLM-L6-v2"
        
        print(f"🗑️  Testing model unloading: {model_to_unload}")
        
        response = requests.delete(
            f"{EMBEDDING_SERVICE_URL}/admin/unload/{model_to_unload}",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ {data.get('message', 'Model unloaded')}")
            return True
        elif response.status_code == 404:
            print(f"   ⚠️  Model was not loaded: {response.json().get('detail', 'Not found')}")
            return True  # This is actually OK
        else:
            print(f"   ❌ Unload failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Unload error: {e}")
        return False

def main():
    """Run comprehensive embedding service tests."""
    print("=" * 60)
    print("🧪 AI8 Unified Embedding Service Test Suite")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n1️⃣  Testing health endpoint...")
    if not test_health_check():
        print("❌ Service is not healthy. Exiting.")
        sys.exit(1)
    
    # Test 2: List models
    print("\n2️⃣  Testing models endpoint...")
    available_models = test_list_models()
    if not available_models:
        print("❌ No models available. Exiting.")
        sys.exit(1)
    
    # Test 3: Model preloading
    print("\n3️⃣  Testing model preloading...")
    test_model_preloading()
    
    # Wait a bit for models to load
    print("\n⏳ Waiting 10 seconds for models to fully load...")
    time.sleep(10)
    
    # Test 4: Embedding generation for each model
    print("\n4️⃣  Testing embedding generation...")
    successful_models = []
    failed_models = []
    
    for model in available_models:
        if test_embedding_generation(model, TEST_TEXTS):
            successful_models.append(model)
        else:
            failed_models.append(model)
        print()  # Add spacing
    
    # Test 5: Model unloading
    print("5️⃣  Testing model unloading...")
    test_model_unloading()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully tested models: {len(successful_models)}")
    for model in successful_models:
        print(f"   • {model}")
    
    if failed_models:
        print(f"\n❌ Failed models: {len(failed_models)}")
        for model in failed_models:
            print(f"   • {model}")
    
    success_rate = len(successful_models) / len(available_models) * 100
    print(f"\n📈 Success rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 Unified embedding service is working well!")
        sys.exit(0)
    else:
        print("⚠️  Some issues detected with the embedding service.")
        sys.exit(1)

if __name__ == "__main__":
    main()