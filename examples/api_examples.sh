#!/bin/bash
# AI8 Architecture - API Examples (Bash/cURL)

set -euo pipefail

# Configuration
BASE_URL="http://localhost:4000/v1"
API_KEY="sk-llm-master-key-2025"

# Helper function for API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=${3:-}
    
    if [ -n "$data" ]; then
        curl -s -X "$method" "$BASE_URL$endpoint" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$BASE_URL$endpoint" \
            -H "Authorization: Bearer $API_KEY"
    fi
}

# List available models
echo "=== Available Models ==="
api_call GET "/models" | jq -r '.data[].id'
echo ""

# Simple chat completion
echo "=== Chat Completion ==="
RESPONSE=$(api_call POST "/chat/completions" '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "max_tokens": 50
}')
echo "$RESPONSE" | jq -r '.choices[0].message.content'
echo ""

# Generate embeddings
echo "=== Generate Embeddings ==="
EMBEDDINGS=$(api_call POST "/embeddings" '{
    "model": "nomic-embed",
    "input": "Sample text for embedding"
}')
DIMENSIONS=$(echo "$EMBEDDINGS" | jq '.data[0].embedding | length')
echo "Embedding dimensions: $DIMENSIONS"
echo ""

# Streaming chat (shows raw SSE stream)
echo "=== Streaming Chat ==="
curl -s -X POST "$BASE_URL/chat/completions" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "gpt-oss-120b",
        "messages": [{"role": "user", "content": "Count to 5"}],
        "stream": true
    }' \
    --no-buffer | while read -r line; do
    if [[ $line == data:* ]]; then
        DATA="${line#data: }"
        if [ "$DATA" != "[DONE]" ]; then
            CONTENT=$(echo "$DATA" | jq -r '.choices[0].delta.content // empty')
            if [ -n "$CONTENT" ]; then
                echo -n "$CONTENT"
            fi
        fi
    fi
done
echo -e "\n"

# Complete RAG workflow
echo "=== RAG Workflow ==="

# 1. Generate embeddings for documents
DOCS=("Machine learning is a subset of AI" "Deep learning uses neural networks")
EMBEDDINGS=()

for DOC in "${DOCS[@]}"; do
    EMB=$(api_call POST "/embeddings" "{
        \"model\": \"stella-embed\",
        \"input\": \"$DOC\"
    }")
    EMBEDDINGS+=("$(echo "$EMB" | jq -r '.data[0].embedding')")
done

# 2. Store in Qdrant (using direct API)
QDRANT_URL="http://localhost:6333"

# Create collection
curl -s -X PUT "$QDRANT_URL/collections/test_rag" \
    -H "Content-Type: application/json" \
    -d '{
        "vectors": {"size": 1024, "distance": "Cosine"}
    }' > /dev/null

# Insert documents
for i in "${!DOCS[@]}"; do
    curl -s -X PUT "$QDRANT_URL/collections/test_rag/points" \
        -H "Content-Type: application/json" \
        -d "{
            \"points\": [{
                \"id\": $((i+1)),
                \"vector\": ${EMBEDDINGS[$i]},
                \"payload\": {\"text\": \"${DOCS[$i]}\"}
            }]
        }" > /dev/null
done

# 3. Query: Search + Generate
QUERY="What is deep learning?"

# Get query embedding
QUERY_EMB=$(api_call POST "/embeddings" "{
    \"model\": \"stella-embed\",
    \"input\": \"$QUERY\"
}" | jq -r '.data[0].embedding')

# Search Qdrant
SEARCH_RESULTS=$(curl -s -X POST "$QDRANT_URL/collections/test_rag/points/search" \
    -H "Content-Type: application/json" \
    -d "{
        \"vector\": $QUERY_EMB,
        \"limit\": 2,
        \"with_payload\": true
    }")

# Extract context
CONTEXT=$(echo "$SEARCH_RESULTS" | jq -r '.result[].payload.text' | tr '\n' ' ')

# Generate answer
ANSWER=$(api_call POST "/chat/completions" "{
    \"model\": \"gpt-oss-120b\",
    \"messages\": [{
        \"role\": \"system\",
        \"content\": \"Answer based on this context: $CONTEXT\"
    }, {
        \"role\": \"user\",
        \"content\": \"$QUERY\"
    }],
    \"max_tokens\": 100
}")

echo "Query: $QUERY"
echo "Context: $CONTEXT"
echo "Answer: $(echo "$ANSWER" | jq -r '.choices[0].message.content')"

echo ""
echo "=== All Examples Complete ==="