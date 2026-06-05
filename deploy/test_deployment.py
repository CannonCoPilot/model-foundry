import os
import litellm

# Set the LiteLLM API base to the gateway endpoint
litellm.api_base = "http://localhost:4000"

# Define the models to test
models_to_test = [
    "gpt-oss-120b",
    "qwen3-omni",
    "embeddings"
]

def test_model(model_name):
    """Sends a test request to a model and prints the outcome."""
    try:
        print(f"Testing model: {model_name}...")
        response = litellm.completion(
            model=model_name,
            messages=[{"role": "user", "content": "Ping"}],
            stream=False
        )
        print(f"SUCCESS: {model_name} responded successfully.")
        return True
    except Exception as e:
        print(f"FAILURE: {model_name} failed with error: {e}")
        return False

if __name__ == "__main__":
    all_models_passed = True
    for model in models_to_test:
        if not test_model(model):
            all_models_passed = False
    
    if all_models_passed:
        print("\nAll models are responsive.")
    else:
        print("\nSome models failed to respond.")