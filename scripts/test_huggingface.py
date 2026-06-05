# Test script for HuggingFace model integration via vLLM
import os
from openai import OpenAI

# --- Configuration ---
# This should match the model loaded by the vLLM server
# Example: google/gemma-2b-it is a good small model for testing
MODEL_ID = os.environ.get("VLLM_MODEL_ID", "google/gemma-2b-it")
API_BASE_URL = "http://localhost:8000/v1"
API_KEY = "dummy-key" # vLLM doesn't require a real key

def run_vllm_test():
    """
    Connects to the vLLM OpenAI-compatible server and runs a test prompt.
    """
    print("--- HuggingFace (vLLM) Integration Test ---")
    print(f"Targeting model: {MODEL_ID}")
    print(f"API Endpoint: {API_BASE_URL}")

    # --- Instructions for the user ---
    print("\n--- Prerequisites ---")
    print("1. Ensure the user-playground container is running.")
    print("2. Start the vLLM server inside the container with the target model:")
    print("   python3 -m vllm.entrypoints.openai.api_server \\")
    print(f"     --model {MODEL_ID} \\")
    print("     --port 8000")
    print("---------------------\n")

    try:
        # Initialize the OpenAI client
        client = OpenAI(
            base_url=API_BASE_URL,
            api_key=API_KEY,
        )

        # --- Run a test prompt ---
        print("Sending a test prompt to the vLLM server...")
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "user", "content": "What is the difference between a llama and an alpaca?"}
            ],
            max_tokens=150,
            temperature=0.7,
        )

        # --- Print the response ---
        print("\n--- Model Response ---")
        print(response.choices[0].message.content)
        print("----------------------\n")
        print("✅ Test successful!")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please ensure the vLLM server is running and accessible at the specified URL.")

if __name__ == "__main__":
    run_vllm_test()