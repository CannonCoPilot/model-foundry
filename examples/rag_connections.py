"""
RAG Database Connection Examples
Base Path: /mnt/ai8_arch
"""

# ============================================================
# Example 1: Ollama LLM + Embeddings
# ============================================================
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings

# Point to your model containers
OLLAMA_BASE_URL = "http://localhost:11601"  # primary-gpt-oss
OLLAMA_EMBED_URL = "http://localhost:11610"  # embeddings-service

# Configure LLM (using primary GPT-OSS model)
llm = ChatOllama(
    base_url=OLLAMA_BASE_URL,
    model="gpt-oss:120b",
    temperature=0.7
)

# Configure embeddings (using embeddings service)
embeddings = OllamaEmbeddings(
    base_url=OLLAMA_EMBED_URL,
    model="nomic-embed-text:137m-v1.5-fp16"
)

# Alternative: Use different embedding models
embeddings_stella = OllamaEmbeddings(
    base_url=OLLAMA_EMBED_URL,
    model="stella"  # Uses alias from embedding service
)

# ============================================================
# Example 2: Qdrant Vector Store
# ============================================================
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient

# Connect to Qdrant container
QDRANT_URL = "http://localhost:6333"

client = QdrantClient(url=QDRANT_URL)

# Create vector store
vector_store = Qdrant(
    client=client,
    collection_name="my_rag_documents",
    embeddings=embeddings  # Use embeddings defined above
)

# Example: Add documents
from langchain.schema import Document

docs = [
    Document(page_content="First document text", metadata={"source": "doc1.txt"}),
    Document(page_content="Second document text", metadata={"source": "doc2.txt"})
]

vector_store.add_documents(docs)

# Example: Similarity search
results = vector_store.similarity_search("query text", k=5)

# ============================================================
# Example 3: pgvector (PostgreSQL) Vector Store
# ============================================================
from langchain_community.vectorstores import PGVector

# Connect to pgvector container
CONNECTION_STRING = "postgresql://llmuser:llmpassword@localhost:5433/vectors"

vector_store_pg = PGVector(
    embedding_function=embeddings,
    collection_name="my_rag_collection",
    connection_string=CONNECTION_STRING,
    pre_delete_collection=False  # Don't delete existing data
)

# Example: Add documents (same as Qdrant)
vector_store_pg.add_documents(docs)

# Example: Similarity search with score
results_with_scores = vector_store_pg.similarity_search_with_score(
    "query text", 
    k=5
)

for doc, score in results_with_scores:
    print(f"Score: {score}, Content: {doc.page_content[:100]}")

# ============================================================
# Example 4: MongoDB for Document Metadata
# ============================================================
from pymongo import MongoClient

# Connect to MongoDB container
MONGO_URI = "mongodb://admin:mongopassword@localhost:27017/"

mongo_client = MongoClient(MONGO_URI)
db = mongo_client['rag_documents']
collection = db['documents']

# Store document metadata
doc_metadata = {
    "document_id": "doc1",
    "filename": "example.pdf",
    "uploaded_at": "2025-10-11T04:21:17Z",
    "num_chunks": 42,
    "embedding_model": "stella",
    "vector_db": "qdrant",
    "collection_name": "my_rag_documents"
}

collection.insert_one(doc_metadata)

# Retrieve metadata
doc = collection.find_one({"document_id": "doc1"})
print(doc)

# ============================================================
# Example 5: Redis for Caching
# ============================================================
import redis
from langchain.cache import RedisCache
from langchain.globals import set_llm_cache

# Connect to Redis container
REDIS_URL = "redis://:redispassword@localhost:6379/0"

redis_client = redis.from_url(REDIS_URL)

# Set up LLM response caching
set_llm_cache(RedisCache(redis_client))

# Now LLM responses will be cached automatically
response = llm.invoke("What is the capital of France?")
# Second call with same prompt will be instant (cached)
response2 = llm.invoke("What is the capital of France?")

# Manual cache operations
redis_client.set("my_key", "my_value", ex=3600)  # Expire in 1 hour
value = redis_client.get("my_key")

# ============================================================
# Example 6: Complete RAG Chain
# ============================================================
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Create prompt template
template = """Use the following context to answer the question.
If you don't know the answer, say so - don't make up information.

Context: {context}

Question: {question}

Answer:"""

prompt = PromptTemplate(
    template=template,
    input_variables=["context", "question"]
)

# Create RAG chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
    chain_type_kwargs={"prompt": prompt},
    return_source_documents=True
)

# Query the RAG system
question = "What is quantum computing?"
result = qa_chain({"query": question})

print("Answer:", result["result"])
print("\nSources:")
for doc in result["source_documents"]:
    print(f"  - {doc.metadata.get('source', 'Unknown')}")

# ============================================================
# Example 7: Using LiteLLM Gateway (OpenAI-compatible)
# ============================================================
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Use LiteLLM gateway (routes to your models)
LITELLM_BASE_URL = "http://localhost:4000/v1"
LITELLM_API_KEY = "sk-llm-master-key-2025"  # From .env

llm_via_gateway = ChatOpenAI(
    base_url=LITELLM_BASE_URL,
    api_key=LITELLM_API_KEY,
    model="gpt-oss-120b",  # Model name from litellm_config.yaml
    temperature=0.7
)

embeddings_via_gateway = OpenAIEmbeddings(
    base_url=LITELLM_BASE_URL,
    api_key=LITELLM_API_KEY,
    model="nomic-embed"  # Embedding model from litellm_config.yaml
)

# Use these interchangeably with direct connections
response = llm_via_gateway.invoke("Hello, how are you?")

# ============================================================
# Example 8: Hybrid Search (Qdrant + pgvector)
# ============================================================
from langchain.retrievers import EnsembleRetriever

# Create retrievers from both vector stores
qdrant_retriever = vector_store.as_retriever(search_kwargs={"k": 5})
pgvector_retriever = vector_store_pg.as_retriever(search_kwargs={"k": 5})

# Combine with weighted ensemble
ensemble_retriever = EnsembleRetriever(
    retrievers=[qdrant_retriever, pgvector_retriever],
    weights=[0.5, 0.5]  # Equal weight
)

# Use in RAG chain
qa_chain_hybrid = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=ensemble_retriever
)
```