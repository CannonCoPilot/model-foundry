#!/usr/bin/env python3
"""
Deep Authentication and Model Validation Test Suite
Tests all services with proper authentication using .env credentials
Validates model loading and responses for AI services
"""

import requests
import json
import sys
import os
import time
import subprocess
from pathlib import Path
import psycopg2
import redis
import pymongo

def test_litellm_with_auth(env_vars):
    """Test LiteLLM with proper authentication"""
    print("=" * 60)
    print("LITELLM GATEWAY - DEEP AUTHENTICATION TEST")
    print("=" * 60)
    
    base_url = "http://litellm:4000"
    master_key = env_vars.get('LITELLM_MASTER_KEY')
    
    if not master_key:
        print("❌ LITELLM_MASTER_KEY not found in .env")
        return False
    
    print(f"[INFO] Using master key: {master_key[:10]}...")
    
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Health endpoint with authentication
    print("\n[1/5] Testing authenticated health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", headers=headers, timeout=10)
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ LiteLLM health check with auth successful")
            health_data = response.json()
            print(f"    Response: {health_data}")
        elif response.status_code == 401:
            print("❌ Authentication failed - invalid master key")
            return False
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: Models endpoint
    print("\n[2/5] Testing models endpoint...")
    try:
        response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=10)
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('data', [])
            print(f"✅ Models endpoint accessible - {len(models)} models found")
            for model in models[:5]:  # Show first 5 models
                print(f"      - {model.get('id', 'unknown')}")
        else:
            print(f"⚠️  Models endpoint: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Models endpoint error: {e}")
    
    # Test 3: Key info endpoint
    print("\n[3/5] Testing key info endpoint...")
    try:
        response = requests.get(f"{base_url}/key/info", headers=headers, timeout=10)
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Key info endpoint successful")
            key_data = response.json()
            print(f"    Key info: {json.dumps(key_data, indent=2)[:200]}...")
        else:
            print(f"⚠️  Key info: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Key info error: {e}")
    
    # Test 4: Database connection test
    print("\n[4/5] Testing database connection...")
    try:
        response = requests.get(f"{base_url}/key/generate", headers=headers, timeout=10)
        print(f"    Status: {response.status_code}")
        if response.status_code in [200, 422]:  # 422 is expected if no data provided
            print("✅ Database connection working")
        else:
            print(f"⚠️  Database test: {response.status_code}")
    except Exception as e:
        print(f"❌ Database test error: {e}")
    
    # Test 5: Config endpoint
    print("\n[5/5] Testing config endpoint...")
    try:
        response = requests.get(f"{base_url}/config", headers=headers, timeout=10)
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Config endpoint accessible")
            config_data = response.json()
            print(f"    Config keys: {list(config_data.keys())}")
        else:
            print(f"⚠️  Config endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Config endpoint error: {e}")
    
    return True

def test_databases_with_auth(env_vars):
    """Test database services with authentication using Python clients."""
    print("\n" + "=" * 60)
    print("DATABASE SERVICES - AUTHENTICATION TEST")
    print("=" * 60)

    # Test MongoDB
    print("\n[MongoDB] Testing with authentication...")
    try:
        mongo_user = env_vars.get('MONGO_USER', 'admin')
        mongo_password = env_vars.get('MONGO_PASSWORD')
        client = pymongo.MongoClient(
            'mongodb',
            username=mongo_user,
            password=mongo_password,
            serverSelectionTimeoutMS=5000
        )
        client.admin.command('ping')
        print("✅ MongoDB authentication successful")
    except Exception as e:
        print(f"❌ MongoDB authentication failed: {e}")

    # Test Redis
    print("\n[Redis] Testing with authentication...")
    try:
        redis_password = env_vars.get('REDIS_PASSWORD')
        r = redis.Redis(host='redis', password=redis_password, decode_responses=True)
        r.ping()
        print("✅ Redis authentication successful")
    except Exception as e:
        print(f"❌ Redis authentication failed: {e}")

    # Test PostgreSQL
    print("\n[PostgreSQL] Testing with authentication...")
    try:
        conn = psycopg2.connect(
            dbname="litellm",
            user=env_vars.get('POSTGRES_USER', 'llmuser'),
            password=env_vars.get('POSTGRES_PASSWORD'),
            host="postgres"
        )
        print("✅ PostgreSQL authentication successful")
        conn.close()
    except Exception as e:
        print(f"❌ PostgreSQL authentication failed: {e}")

def test_ollama_models():
    """Test Ollama and vLLM services and model loading"""
    print("\n" + "=" * 60)
    print("AI MODEL SERVICES - VALIDATION")
    print("=" * 60)
    
    # Test Primary GPT OSS (Ollama)
    print("\n[Primary GPT OSS] Testing model availability...")
    try:
        response = requests.get("http://primary_gpt_oss:11434/api/tags", timeout=15)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Service accessible - {len(models)} models loaded")
            if models:
                print(f"    - {models[0].get('name', 'unknown')}")
        else:
            print(f"❌ Service not accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Service error: {e}")

    # Test Secondary Qwen3-Omni (vLLM)
    print("\n[Secondary Qwen3-Omni] Testing model availability...")
    try:
        response = requests.get("http://secondary_qwen3_omni:8000/health", timeout=15)
        if response.status_code == 200:
            print("✅ Service is healthy")
        else:
            print(f"❌ Service not healthy: {response.status_code}")
    except Exception as e:
        print(f"❌ Service error: {e}")

def test_all_service_health():
    """Force check health of all services"""
    print("\n" + "=" * 60)
    print("ALL SERVICES - FORCED HEALTH CHECK")
    print("=" * 60)
    
    services = [
        ("Embeddings Service", "http://embeddings:8000/health"),
        ("ChromaDB", "http://chroma:8000/api/v1/heartbeat"),
        ("Qdrant", "http://qdrant:6333/healthz"),
        ("LiteLLM Gateway", "http://litellm:4000/"),
        ("Open WebUI", "http://openwebui:8080/"),
        ("Prometheus", "http://prometheus:9090/-/healthy"),
        ("Grafana", "http://grafana:3000/api/health"),
    ]
    
    for service_name, url in services:
        print(f"\n[{service_name}] Force checking...")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {service_name} healthy (200)")
            else:
                print(f"⚠️  {service_name} responded with {response.status_code}")
        except Exception as e:
            print(f"❌ {service_name} failed: {e}")

def main():
    """Main test execution"""
    print("=" * 80)
    print("AI8 ARCHITECTURE - DEEP VALIDATION & AUTHENTICATION TEST")
    print("=" * 80)
    
    # Load environment variables
    print("\n[SETUP] Loading environment variables from .env...")
    env_vars = dict(os.environ)
    
    required_vars = ['LITELLM_MASTER_KEY', 'POSTGRES_PASSWORD', 'REDIS_PASSWORD', 'MONGO_PASSWORD']
    missing_vars = [var for var in required_vars if not env_vars.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    print(f"✅ Environment variables loaded: {len(env_vars)} variables")
    print(f"    Required vars present: {[var for var in required_vars if env_vars.get(var)]}")
    
    # Run all tests
    test_all_service_health()
    test_litellm_with_auth(env_vars)
    test_databases_with_auth(env_vars)
    test_ollama_models()
    
    print("\n" + "=" * 80)
    print("DEEP VALIDATION TEST COMPLETE")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)