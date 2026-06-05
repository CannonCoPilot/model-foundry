#!/usr/bin/env python3
"""
AI8 Architecture - LangChain Example
Complete RAG pipeline
"""
from langchain_community.chat_models import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.prompts import PromptTemplate
from qdrant_client import QdrantClient

# Configuration
LITELLM_URL = "http://localhost:4000/v1"
LITELLM_KEY = "sk-llm-master-key-2025"
QDRANT_URL = "http://localhost:6333"

# Initialize LLM
llm = ChatOpenAI(
    base_url=LITELLM_URL,
    api_key=LITELLM_KEY,
    model="gpt-oss-120b",
    temperature=0.7
)

# Initialize embeddings
embeddings = OpenAIEmbeddings(
    base_url=LITELLM_URL,
    api_key=LITELLM_KEY,
    model="stella-embed"
)

# Initialize Qdrant client
qdrant_client = QdrantClient(url=QDRANT_URL)

# Load and split documents
loader = TextLoader("documents/sample.txt")
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = text_splitter.split_documents(documents)

# Create vector store
vector_store = Qdrant.from_documents(
    chunks,
    embeddings,
    url=QDRANT_URL,
    collection_name="my_documents"
)

# Create prompt template
template = """Use the following context to answer the question.
If you don't know the answer, say so - don't make things up.

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

# Query
question = "What is the main topic of the documents?"
result = qa_chain({"query": question})

print("Question:", question)
print("Answer:", result["result"])
print("\nSources:")
for doc in result["source_documents"]:
    print(f"- {doc.metadata.get('source', 'Unknown')}")