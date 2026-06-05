#!/usr/bin/env python3
"""
Custom test script for LiteLLM Gateway Service
Tests the API gateway functionality and model access
"""

import requests
import json
import sys
import os

def test_litellm_gateway():
    """Test the LiteLLM gateway service functionality"""
    base_url = "http://localhost:4000"
    
    print("=" * 60)
    print("LITELLM GATEWAY SERVICE TEST")
    print("=" * 60)
    
    # Get master key from environment
    master_key = os.getenv('LITELLM_MASTER_KEY', 'default_master_key')
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Basic connectivity (root endpoint)
    print("[1/5] Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ Root endpoint accessible (Swagger UI)")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False
    
    # Test 2: Health endpoint
    print("\n[2/5] Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", headers=headers, timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print(f"    Response: {response.text}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 3: Models endpoint
    print("\n[3/5] Testing models endpoint...")
    try:
        response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=10)
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('data', [])
            print(f"✅ Models endpoint accessible")
            print(f"    Available models: {len(models)}")
            for model in models[:3]:  # Show first 3 models
                print(f"      - {model.get('id', 'unknown')}")
        else:
            print(f"❌ Models endpoint failed: {response.status_code}")
            print(f"    Response: {response.text}")
    except Exception as e:
        print(f"❌ Models endpoint error: {e}")
    
    # Test 4: API documentation
    print("\n[4/5] Testing API documentation...")
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API documentation accessible")
        else:
            print(f"❌ API docs failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API docs error: {e}")
    
    # Test 5: Database connectivity (if configured)
    print("\n[5/5] Testing database integration...")
    try:
        # Try to get key info which requires DB
        response = requests.get(f"{base_url}/key/info", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Database integration working")
        elif response.status_code == 401:
            print("⚠️  Database integration requires valid API key")
        else:
            print(f"⚠️  Database response: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Database test error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ LITELLM GATEWAY BASIC TESTS COMPLETED")
    print("=" * 60)
    print("Note: Full functionality requires:")
    print("  - Valid API keys for model access")
    print("  - Properly configured model endpoints")
    print("  - Database setup for key management")
    
    return True

if __name__ == "__main__":
    success = test_litellm_gateway()
    sys.exit(0 if success else 1)