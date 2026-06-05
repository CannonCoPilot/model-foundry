#!/bin/bash
# PostgreSQL Initialization Script
# Creates additional databases for multi-service setup
# IDEMPOTENT - Safe to run multiple times
# Base Path: /mnt/ai8_arch
# Author: CannonCoPilot
# Date: 2025-01-11

set -euo pipefail

# Logging function
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "🔧 PostgreSQL initialization starting..."

# Verify environment variables
if [ -z "${POSTGRES_USER:-}" ]; then
  log "❌ ERROR: POSTGRES_USER not set"
  exit 1
fi

if [ -z "${POSTGRES_DB:-}" ]; then
  log "❌ ERROR: POSTGRES_DB not set"
  exit 1
fi

log "Database: $POSTGRES_DB"
log "User: $POSTGRES_USER"

# Function to create database if not exists (idempotent)
create_database() {
  local dbname=$1
  local owner=${2:-$POSTGRES_USER}
  
  log "Ensuring database exists: $dbname"
  
  # Check if database exists
  EXISTS=$(psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$dbname'" || echo "0")
  
  if [ "$EXISTS" = "1" ]; then
    log "  ✓ Database $dbname already exists"
  else
    log "  → Creating database $dbname"
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
      CREATE DATABASE $dbname OWNER $owner;
EOSQL
    log "  ✓ Database $dbname created"
  fi
  
  # Always ensure permissions (idempotent)
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
    GRANT ALL PRIVILEGES ON DATABASE $dbname TO $owner;
EOSQL
}

# Function to setup extensions (idempotent)
setup_extensions() {
  local dbname=$1
  
  log "Setting up extensions in $dbname..."
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$dbname" <<-EOSQL
    -- Enable common extensions
    CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- Text search
    CREATE EXTENSION IF NOT EXISTS btree_gin;    -- Index optimization
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;  -- Query performance
EOSQL
  log "  ✓ Extensions ready in $dbname"
}

# Create databases
log "Creating/verifying databases..."

# n8n database
create_database "n8n"
setup_extensions "n8n"

# Optional: Add more databases as needed
# Uncomment if you add services requiring dedicated databases
# create_database "grafana"
# setup_extensions "grafana"

# Verify setup
log "Verifying database setup..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
  SELECT 
    datname as database,
    pg_size_pretty(pg_database_size(datname)) as size,
    (SELECT count(*) FROM pg_stat_activity WHERE datname = d.datname) as connections
  FROM pg_database d
  WHERE datname IN ('$POSTGRES_DB', 'n8n')
  ORDER BY datname;
EOSQL

log "✅ PostgreSQL initialization complete"
log "Available databases: $POSTGRES_DB, n8n"
log "Connection strings:"
log "  • Main:  postgresql://$POSTGRES_USER:****@localhost:5432/$POSTGRES_DB"
log "  • n8n:   postgresql://$POSTGRES_USER:****@localhost:5432/n8n"

exit 0
```