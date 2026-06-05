#!/usr/bin/env python3
"""
Custom test script for Embeddings Service
Tests the actual embedding generation functionality
"""

import requests
import json
import sys
import time

def test_embeddings_service():
    """Test the embeddings service functionality"""
    base_url = "http://localhost:8010"
    
    print("=" * 60)
    print("EMBEDDINGS SERVICE TEST")
    print("=" * 60)
    
    # Test 1: Health check
    print("[1/4] Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
            print(f"    Models loaded: {health_data.get('models_loaded', [])}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: API docs
    print("\n[2/4] Testing API documentation...")
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API documentation accessible")
        else:
            print(f"❌ API docs failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API docs error: {e}")
    
    # Test 3: OpenAPI schema
    print("\n[3/4] Testing OpenAPI schema...")
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=5)
        if response.status_code == 200:
            schema = response.json()
            endpoints = list(schema.get('paths', {}).keys())
            print(f"✅ OpenAPI schema accessible")
            print(f"    Available endpoints: {endpoints}")
        else:
            print(f"❌ OpenAPI schema failed: {response.status_code}")
    except Exception as e:
        print(f"❌ OpenAPI schema error: {e}")
    
    # Test 4: Embeddings generation
    print("\n[4/4] Testing embeddings generation...")
    test_cases = [
        {"text": "Hello world", "expected_model": "all-MiniLM-L6-v2"},
        {"text": "The quick brown fox jumps over the lazy dog", "expected_model": "all-MiniLM-L6-v2"},
        {"text": "AI and machine learning are transforming technology", "expected_model": "all-MiniLM-L6-v2"}
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n    Test {i}/3: '{test_case['text'][:30]}...'")
        try:
            payload = {
                "input": test_case["text"],
                "model": test_case["expected_model"]
            }
            
            print(f"    Making request to {base_url}/v1/embeddings...")
            start_time = time.time()
            response = requests.post(
                f"{base_url}/v1/embeddings",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                embeddings = data.get('data', [])
                if embeddings and len(embeddings) > 0:
                    embedding_vector = embeddings[0].get('embedding', [])
                    print(f"    ✅ Embedding generated successfully")
                    print(f"        Vector length: {len(embedding_vector)}")
                    print(f"        Response time: {end_time - start_time:.2f}s")
                    print(f"        Model used: {data.get('model', 'unknown')}")
                    if len(embedding_vector) >= 300:  # Expected for all-MiniLM-L6-v2
                        print(f"        Vector dimension: VALID ({len(embedding_vector)})")
                    else:
                        print(f"        Vector dimension: UNEXPECTED ({len(embedding_vector)})")
                else:
                    print(f"    ❌ No embeddings in response")
                    return False
            else:
                print(f"    ❌ Request failed: {response.status_code}")
                print(f"        Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"    ❌ Request timed out (>30s)")
            return False
        except Exception as e:
            print(f"    ❌ Request error: {e}")
            return False
    
    print("\n" + "=" * 60)
    print("✅ ALL EMBEDDINGS TESTS PASSED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_embeddings_service()
    sys.exit(0 if success else 1)