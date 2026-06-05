#!/usr/bin/env python3
"""
Comprehensive API Test Suite for the gpt-oss Model via llm-gateway

This script validates the primary gpt-oss model by routing requests through the
LiteLLM gateway. It is designed to be run from any machine with network access
to the gateway, including a user's local machine.

Instructions:
1.  Ensure you have Python 3.6+ and the 'requests' library installed.
    (pip install requests)
2.  Set the following environment variables:
    - LITELLM_MASTER_KEY: The master key for the LiteLLM gateway.
    - LLM_GATEWAY_URL: The base URL of the LiteLLM gateway 
      (e.g., http://<your_server_ip>:4000).
"""

import os
import json
import requests
import time

# --- Configuration ---
API_KEY = os.environ.get("LITELLM_MASTER_KEY")
BASE_URL = os.environ.get("LLM_GATEWAY_URL", "http://localhost:4000")
MODEL_NAME = "gpt-oss"

# --- Helper Functions ---
def print_header(title):
    """Prints a formatted header for each test section."""
    print("\n" + "=" * 70)
    print(f"RUNNING TEST: {title}")
    print("=" * 70)

def print_status(message, success=True):
    """Prints a status message with a checkmark or cross."""
    print(f"  {'✅' if success else '❌'} {message}")

def make_request(method, endpoint, payload=None, stream=False):
    """Makes an authenticated request to the gateway."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}{endpoint}"
    
    try:
        response = requests.request(
            method, url, headers=headers, json=payload, stream=stream, timeout=300
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print_status(f"Request failed: {e}", success=False)
        if e.response is not None:
            print(f"    Response Body: {e.response.text}")
        return None

# --- Test Cases ---

def test_01_check_environment():
    """Verify that necessary environment variables are set."""
    print_header("Environment Variable Check")
    success = True
    if not API_KEY:
        print_status("LITELLM_MASTER_KEY is not set.", success=False)
        success = False
    else:
        print_status("LITELLM_MASTER_KEY is set.")
        
    if not BASE_URL:
        print_status("LLM_GATEWAY_URL is not set.", success=False)
        success = False
    else:
        print_status(f"LLM_GATEWAY_URL is set to: {BASE_URL}")
        
    return success

def test_02_gateway_health():
    """Test the health and connectivity of the llm-gateway."""
    print_header("Gateway Health Check")
    response = make_request("GET", "/health")
    if response and response.status_code == 200:
        print_status("Gateway is healthy and reachable.")
        return True
    print_status("Gateway health check failed.", success=False)
    return False

def test_03_model_availability():
    """Check if the gpt-oss model is listed as available by the gateway."""
    print_header("Model Availability")
    response = make_request("GET", "/v1/models")
    if not response:
        return False
        
    models = response.json().get("data", [])
    model_found = any(m["id"] == MODEL_NAME for m in models)
    
    if model_found:
        print_status(f"'{MODEL_NAME}' is listed as an available model.")
        return True
    else:
        print_status(f"'{MODEL_NAME}' not found in available models.", success=False)
        print("    Available models:", [m["id"] for m in models])
        return False

def test_04_standard_chat_completion():
    """Perform a standard, non-streaming chat completion."""
    print_header("Standard Chat Completion")
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": "Explain the importance of gravity in 50 words."}
        ]
    }
    
    start_time = time.time()
    response = make_request("POST", "/v1/chat/completions", payload)
    duration = time.time() - start_time
    
    if not response:
        return False
        
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    
    if content:
        print_status(f"Received a valid response in {duration:.2f}s.")
        print(f"    Response: {content[:100]}...")
        return True
    else:
        print_status("Response did not contain valid content.", success=False)
        print(f"    Full Response: {data}")
        return False

def test_05_streaming_chat_completion():
    """Perform a streaming chat completion and verify token flow."""
    print_header("Streaming Chat Completion")
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": "Write a short poem about space."}
        ],
        "stream": True
    }
    
    response = make_request("POST", "/v1/chat/completions", payload, stream=True)
    if not response:
        return False
        
    chunks_received = 0
    full_response = ""
    try:
        for chunk in response.iter_lines():
            if chunk:
                print(f"    RAW CHUNK: {chunk}") # <-- ADDED FOR DEBUGGING
                chunk_str = chunk.decode('utf-8').replace('data: ', '')
                if "[DONE]" in chunk_str:
                    break
                data = json.loads(chunk_str)
                delta = data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    full_response += content
                    chunks_received += 1
    except Exception as e:
        print_status(f"Error processing stream: {e}", success=False)
        return False

    if chunks_received > 1 and full_response:
        print_status(f"Successfully received {chunks_received} stream chunks.")
        print(f"    Full Response: {full_response[:100]}...")
        return True
    else:
        print_status("Streaming test failed to receive multiple chunks.", success=False)
        return False

def test_06_invalid_api_key():
    """Test that a request with an invalid API key is rejected."""
    print_header("Invalid API Key")
    headers = {
        "Authorization": "Bearer this-is-a-fake-key",
        "Content-Type": "application/json"
    }
    payload = {"model": MODEL_NAME, "messages": [{"role": "user", "content": "test"}]}
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", headers=headers, json=payload)
        if response.status_code == 401:
            print_status("Request was correctly rejected with 401 Unauthorized.")
            return True
        else:
            print_status(f"Request returned unexpected status {response.status_code}", success=False)
            return False
    except requests.exceptions.RequestException as e:
        print_status(f"Request failed as expected, but with an error: {e}", success=False)
        return False

# --- Main Execution ---
def main():
    """Run all tests and report a summary."""
    print("=" * 70)
    print("      STARTING GPT-OSS API TEST SUITE VIA LLM-GATEWAY")
    print("=" * 70)
    
    tests = [
        test_01_check_environment,
        test_02_gateway_health,
        test_03_model_availability,
        test_04_standard_chat_completion,
        test_05_streaming_chat_completion,
        test_06_invalid_api_key,
    ]
    
    results = {"passed": 0, "failed": 0}
    
    for test in tests:
        if test():
            results["passed"] += 1
        else:
            results["failed"] += 1
            # Stop on first failure for critical tests
            if test in [test_01_check_environment, test_02_gateway_health, test_03_model_availability]:
                print("\nCritical test failed. Aborting remaining tests.")
                break

    print("\n" + "=" * 70)
    print("                    TEST SUMMARY")
    print("=" * 70)
    print(f"  Tests Passed: {results['passed']}")
    print(f"  Tests Failed: {results['failed']}")
    print("=" * 70)
    
    if results["failed"] > 0:
        print("\nSome tests failed. Please review the output above.")
        exit(1)
    else:
        print("\nAll tests passed successfully!")
        exit(0)

if __name__ == "__main__":
    main()