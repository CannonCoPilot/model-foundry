#!/usr/bin/env python3
"""
AI8 Architecture - Python Requests Example
"""
import requests
import json

BASE_URL = "http://localhost:4000/v1"
API_KEY = "sk-llm-master-key-2025"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# List models
response = requests.get(f"{BASE_URL}/models", headers=headers)
models = response.json()
print("Available models:", [m["id"] for m in models["data"]])

# Chat completion
payload = {
    "model": "gpt-oss-120b",
    "messages": [
        {"role": "user", "content": "What is 2+2?"}
    ]
}

response = requests.post(
    f"{BASE_URL}/chat/completions",
    headers=headers,
    json=payload
)

result = response.json()
print("Response:", result["choices"][0]["message"]["content"])

# Streaming completion
payload["stream"] = True

response = requests.post(
    f"{BASE_URL}/chat/completions",
    headers=headers,
    json=payload,
    stream=True
)

print("Streaming response:")
for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith("data: "):
            data = line[6:]  # Remove "data: " prefix
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                content = chunk["choices"][0]["delta"].get("content", "")
                print(content, end="", flush=True)
            except json.JSONDecodeError:
                pass
print()