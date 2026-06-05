#!/bin/bash
# Initialize pgvector extension for PostgreSQL
# Idempotent - safe to run multiple times
# Base Path: /mnt/ai8_arch

set -euo pipefail

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "🔧 Initializing pgvector database..."

# Verify environment
if [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_DB:-}" ]; then
  log "❌ ERROR: Required environment variables not set"
  exit 1
fi

log "Database: $POSTGRES_DB, User: $POSTGRES_USER"

# Enable vector extension (idempotent)
log "Enabling vector extension..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
    -- Enable vector extension
    CREATE EXTENSION IF NOT EXISTS vector;
    
    -- Verify extension
    SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
EOSQL

log "✅ Vector extension enabled"

# Create example schema (optional, for reference)
log "Creating example RAG schema..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
    -- Example: Document embeddings table
    CREATE TABLE IF NOT EXISTS document_embeddings (
        id SERIAL PRIMARY KEY,
        document_id VARCHAR(255) NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding vector(1024),  -- Adjust dimension based on your model
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(document_id, chunk_index)
    );
    
    -- Create index for vector similarity search (HNSW for performance)
    CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx 
    ON document_embeddings USING hnsw (embedding vector_cosine_ops);
    
    -- Standard indexes
    CREATE INDEX IF NOT EXISTS document_embeddings_doc_id_idx 
    ON document_embeddings(document_id);
    
    -- Example: Document metadata table
    CREATE TABLE IF NOT EXISTS documents (
        id VARCHAR(255) PRIMARY KEY,
        filename VARCHAR(500) NOT NULL,
        filetype VARCHAR(50),
        size_bytes BIGINT,
        upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB
    );
    
    -- Grant permissions
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $POSTGRES_USER;
EOSQL

log "✅ Example RAG schema created"

# Display table info
log "Database setup complete. Tables created:"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
    SELECT 
        tablename, 
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables 
    WHERE schemaname = 'public'
    ORDER BY tablename;
EOSQL

log "✅ pgvector initialization complete"
log "Connection string: postgresql://$POSTGRES_USER:****@localhost:5433/$POSTGRES_DB"
```