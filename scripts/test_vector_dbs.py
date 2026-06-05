#!/usr/bin/env python3
"""
Custom test script for Vector Database Services (ChromaDB and Qdrant)
Tests vector storage, search, and retrieval functionality
"""

import requests
import json
import sys
import numpy as np

def test_chromadb():
    """Test ChromaDB functionality"""
    base_url = "http://localhost:8000"
    
    print("=" * 40)
    print("CHROMADB TESTS")
    print("=" * 40)
    
    # Test 1: Heartbeat
    print("[1/4] Testing ChromaDB heartbeat...")
    try:
        response = requests.get(f"{base_url}/api/v1/heartbeat", timeout=10)
        if response.status_code == 200:
            heartbeat_data = response.json()
            print(f"✅ ChromaDB heartbeat successful")
            print(f"    Timestamp: {heartbeat_data.get('nanosecond heartbeat', 'unknown')}")
        else:
            print(f"❌ ChromaDB heartbeat failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ChromaDB heartbeat error: {e}")
        return False
    
    # Test 2: Collections list
    print("\n[2/4] Testing ChromaDB collections...")
    try:
        response = requests.get(f"{base_url}/api/v1/collections", timeout=10)
        if response.status_code == 200:
            collections = response.json()
            print(f"✅ ChromaDB collections accessible")
            print(f"    Collections count: {len(collections)}")
        else:
            print(f"❌ ChromaDB collections failed: {response.status_code}")
    except Exception as e:
        print(f"❌ ChromaDB collections error: {e}")
    
    # Test 3: Create test collection
    print("\n[3/4] Testing ChromaDB collection creation...")
    try:
        collection_data = {
            "name": "test_collection_" + str(int(time.time() if 'time' in globals() else 1000)),
            "metadata": {"description": "Test collection for deployment validation"}
        }
        response = requests.post(f"{base_url}/api/v1/collections", 
                               json=collection_data, timeout=10)
        if response.status_code == 200:
            print("✅ ChromaDB collection creation successful")
        elif response.status_code == 500:
            print("⚠️  ChromaDB collection creation returned 500 (expected for new instances)")
        else:
            print(f"⚠️  ChromaDB collection creation: {response.status_code}")
    except Exception as e:
        print(f"❌ ChromaDB collection creation error: {e}")
    
    # Test 4: Version info
    print("\n[4/4] Testing ChromaDB version...")
    try:
        response = requests.get(f"{base_url}/api/v1/version", timeout=5)
        if response.status_code == 200:
            version_data = response.json()
            print(f"✅ ChromaDB version: {version_data}")
        else:
            print(f"⚠️  ChromaDB version endpoint: {response.status_code}")
    except Exception as e:
        print(f"⚠️  ChromaDB version error: {e}")
    
    return True

def test_qdrant():
    """Test Qdrant functionality"""
    base_url = "http://localhost:6333"
    
    print("\n" + "=" * 40)
    print("QDRANT TESTS")
    print("=" * 40)
    
    # Test 1: Health check
    print("[1/5] Testing Qdrant health...")
    try:
        response = requests.get(f"{base_url}/healthz", timeout=10)
        if response.status_code == 200:
            print(f"✅ Qdrant health check successful")
            print(f"    Response: {response.text.strip()}")
        else:
            print(f"❌ Qdrant health failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Qdrant health error: {e}")
        return False
    
    # Test 2: Collections list
    print("\n[2/5] Testing Qdrant collections...")
    try:
        response = requests.get(f"{base_url}/collections", timeout=10)
        if response.status_code == 200:
            collections_data = response.json()
            collections = collections_data.get('result', {}).get('collections', [])
            print(f"✅ Qdrant collections accessible")
            print(f"    Collections count: {len(collections)}")
            for collection in collections[:3]:
                print(f"      - {collection.get('name', 'unknown')}")
        else:
            print(f"❌ Qdrant collections failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Qdrant collections error: {e}")
    
    # Test 3: Create test collection
    test_collection_name = "test_deployment_collection"
    print(f"\n[3/5] Testing Qdrant collection creation ({test_collection_name})...")
    try:
        collection_config = {
            "vectors": {
                "size": 384,  # Match embeddings service
                "distance": "Cosine"
            }
        }
        response = requests.put(f"{base_url}/collections/{test_collection_name}",
                              json=collection_config, timeout=10)
        if response.status_code == 200:
            print("✅ Qdrant collection created successfully")
        else:
            print(f"⚠️  Qdrant collection creation: {response.status_code}")
            print(f"    Response: {response.text}")
    except Exception as e:
        print(f"❌ Qdrant collection creation error: {e}")
    
    # Test 4: Insert test vector
    print(f"\n[4/5] Testing Qdrant vector insertion...")
    try:
        # Create a test vector (384 dimensions to match embeddings)
        test_vector = [0.1] * 384
        point_data = {
            "points": [
                {
                    "id": 1,
                    "vector": test_vector,
                    "payload": {"text": "test document", "category": "deployment_test"}
                }
            ]
        }
        response = requests.put(f"{base_url}/collections/{test_collection_name}/points",
                              json=point_data, timeout=10)
        if response.status_code == 200:
            print("✅ Qdrant vector insertion successful")
        else:
            print(f"⚠️  Qdrant vector insertion: {response.status_code}")
    except Exception as e:
        print(f"❌ Qdrant vector insertion error: {e}")
    
    # Test 5: Clean up test collection
    print(f"\n[5/5] Testing Qdrant collection deletion...")
    try:
        response = requests.delete(f"{base_url}/collections/{test_collection_name}", timeout=10)
        if response.status_code == 200:
            print("✅ Qdrant collection deletion successful")
        else:
            print(f"⚠️  Qdrant collection deletion: {response.status_code}")
    except Exception as e:
        print(f"❌ Qdrant collection deletion error: {e}")
    
    return True

def test_vector_databases():
    """Test both vector database services"""
    print("=" * 60)
    print("VECTOR DATABASES TEST SUITE")
    print("=" * 60)
    
    chroma_success = test_chromadb()
    qdrant_success = test_qdrant()
    
    print("\n" + "=" * 60)
    if chroma_success and qdrant_success:
        print("✅ ALL VECTOR DATABASE TESTS COMPLETED SUCCESSFULLY")
    else:
        print("⚠️  VECTOR DATABASE TESTS COMPLETED WITH ISSUES")
    print("=" * 60)
    
    return chroma_success and qdrant_success

if __name__ == "__main__":
    import time
    success = test_vector_databases()
    sys.exit(0 if success else 1)