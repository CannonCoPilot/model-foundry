#!/bin/bash
# Setup directory structure for ai8_arch
# Run from: /mnt/ai8_arch
# Organizes GPT-OSS and Qwen3-VL as primary, all others as secondary

set -euo pipefail

BASE_DIR="/mnt/ai8_arch"

# Check if we're in the right directory
if [ "$PWD" != "$BASE_DIR" ]; then
  echo "⚠️  Warning: Not in $BASE_DIR"
  echo "Current directory: $PWD"
  read -p "Continue anyway? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Exiting. Please cd to $BASE_DIR first."
    exit 1
  fi
fi

cd "$BASE_DIR"

echo "🔧 Setting up ai8_arch directory structure..."
echo "📍 Base directory: $BASE_DIR"
echo ""

# Create directory structure
echo "📁 Creating base directories..."
mkdir -p config
mkdir -p dockerfiles
mkdir -p scripts
mkdir -p monitoring/grafana/{dashboards,datasources}
mkdir -p n8n/workflows
mkdir -p data/{postgres,grafana,n8n,prometheus,openwebui/{data,themes}}
mkdir -p logs/{ollama,vllm,embeddings}

# Create model directories
echo "📁 Creating model storage directories..."
mkdir -p models/ollama/primary/{gpt_oss,qwen3_vl}
mkdir -p models/ollama/secondary
mkdir -p models/ollama/embeddings
mkdir -p models/ollama/playground
mkdir -p models/ollama/custom
mkdir -p models/huggingface/hub

echo "✅ Directory structure created"

# Check if models need to be migrated from /net/isilon
ISILON_PATH="/net/isilon/ifs/updates/models/ai8_arch/models"
if [ -d "$ISILON_PATH" ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📦 Detected existing models at: $ISILON_PATH"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Options:"
  echo "  1) Move models from Isilon to /mnt/ai8_arch (recommended if on same filesystem)"
  echo "  2) Copy models from Isilon to /mnt/ai8_arch (safe but slow, ~1.4TB)"
  echo "  3) Create symlinks from /mnt/ai8_arch to Isilon (fast but requires Isilon mount)"
  echo "  4) Skip migration (organize models already in /mnt/ai8_arch)"
  echo ""
  read -p "Choose option (1-4): " -n 1 -r
  echo
  
  MIGRATION_METHOD=$REPLY
else
  echo ""
  echo "ℹ️  No existing models found at $ISILON_PATH"
  echo "Will organize any models already in $BASE_DIR/models/"
  MIGRATION_METHOD="4"
fi

# Organize existing models
echo ""
echo "📦 Organizing models..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Function to migrate/organize models
organize_model() {
  local src=$1
  local dest=$2
  local model_name=$3
  local method=$4  # "move", "copy", "link", or "local"
  
  # Determine source path based on migration method
  if [ "$method" = "local" ]; then
    local src_path="$BASE_DIR/models/$src"
  else
    local src_path="$ISILON_PATH/$src"
  fi
  
  local dest_path="$BASE_DIR/$dest"
  
  if [ -d "$src_path" ]; then
    echo "  Processing: $model_name"
    
    case $method in
      "move")
        if [ ! -d "$dest_path" ]; then
          mv "$src_path" "$dest_path"
          echo "    ✓ Moved: $src_path → $dest_path"
        else
          echo "    ⚠ Already exists: $dest_path"
        fi
        ;;
      
      "copy")
        if [ ! -d "$dest_path" ]; then
          echo "    ⏳ Copying (this may take a while)..."
          cp -a "$src_path" "$dest_path"
          echo "    ✓ Copied: $src_path → $dest_path"
        else
          echo "    ⚠ Already exists: $dest_path"
        fi
        ;;
      
      "link")
        if [ ! -L "$dest_path" ] && [ ! -d "$dest_path" ]; then
          ln -s "$src_path" "$dest_path"
          echo "    ✓ Linked: $src_path → $dest_path"
        else
          echo "    ⚠ Already exists: $dest_path"
        fi
        ;;
      
      "local")
        if [ ! -d "$dest_path" ] && [ "$src_path" != "$dest_path" ]; then
          mv "$src_path" "$dest_path"
          echo "    ✓ Moved: $src_path → $dest_path"
        else
          echo "    ⚠ Already exists or same path: $dest_path"
        fi
        ;;
    esac
  else
    if [ "$method" != "local" ]; then
      echo "  ⚠ Not found: $src_path (will need to download)"
    fi
  fi
}

# Determine migration method
case $MIGRATION_METHOD in
  1)
    METHOD="move"
    echo "Migration method: MOVE"
    ;;
  2)
    METHOD="copy"
    echo "Migration method: COPY (this will take time)"
    ;;
  3)
    METHOD="link"
    echo "Migration method: SYMLINK"
    ;;
  4)
    METHOD="local"
    echo "Migration method: ORGANIZE LOCAL FILES"
    ;;
  *)
    METHOD="local"
    echo "Invalid option, defaulting to: ORGANIZE LOCAL FILES"
    ;;
esac

echo ""
echo "PRIMARY MODELS (persistent in VRAM):"
echo "────────────────────────────────────"

# GPT-OSS: Will need to be downloaded (placeholder created)
echo "  📍 gpt-oss:120b"
echo "    ℹ Model needs to be downloaded"
echo "    → Placeholder: models/ollama/primary/gpt_oss/"

# Qwen3-VL: Will be downloaded via HuggingFace/vLLM
echo "  📍 Qwen3-VL-235B"
echo "    ℹ Model will be downloaded by vLLM on first start"
echo "    → Cache: models/huggingface/hub/"

echo ""
echo "SECONDARY MODELS (on-demand, 600s timeout):"
echo "────────────────────────────────────────────"

# DeepSeek R1 671B - Use existing model
organize_model "deepseek_models" \
               "models/ollama/secondary/deepseek_r1_671b" \
               "DeepSeek R1 671B (377GB)" \
               "$METHOD"

# DeepSeek R1 8B Qwen3 - Use existing model  
organize_model "deep_qwen_models" \
               "models/ollama/secondary/deepseek_r1_8b_qwen3" \
               "DeepSeek R1 8B Qwen3 (16GB)" \
               "$METHOD"

# Qwen3 235B - Use existing model
organize_model "qwen3_235b_models" \
               "models/ollama/secondary/qwen3_235b" \
               "Qwen3 235B (233GB)" \
               "$METHOD"

# Qwen3 32B - Use existing model
organize_model "qwen3_32b_models" \
               "models/ollama/secondary/qwen3_32b" \
               "Qwen3 32B (62GB)" \
               "$METHOD"

# Qwen2.5VL 72B - Use existing model
organize_model "qwen25vl_models" \
               "models/ollama/secondary/qwen25vl_72b" \
               "Qwen2.5VL 72B (137GB + 74GB)" \
               "$METHOD"

# Mistral Small 3.1 24B - Use existing model
organize_model "mistral_models" \
               "models/ollama/secondary/mistral_small3_24b" \
               "Mistral Small 3.1 24B (45GB)" \
               "$METHOD"

# Llama4 Scout 17B - Use existing model
organize_model "llama4_models" \
               "models/ollama/secondary/llama4_scout_17b" \
               "Llama4 Scout 17B (109GB)" \
               "$METHOD"

# Gemma3 27B - Use existing model
organize_model "gemma3_models" \
               "models/ollama/secondary/gemma3_27b" \
               "Gemma3 27B (52GB)" \
               "$METHOD"

# Phi4 Reasoning 14B - Use existing model
organize_model "phi4_models" \
               "models/ollama/secondary/phi4_reasoning_14b" \
               "Phi4 Reasoning 14B (28GB)" \
               "$METHOD"

# PaliGemma - Use existing model
organize_model "paligemma_models" \
               "models/ollama/secondary/paligemma" \
               "PaliGemma (5.5GB + 4.7GB)" \
               "$METHOD"

# Base models (contains deepseek-r1:1.5b and paligemma)
organize_model "base_models" \
               "models/ollama/secondary/base_small_models" \
               "Base Small Models (DeepSeek 1.5B)" \
               "$METHOD"

# Llava: Will need to be downloaded
echo "  📍 Llava 34B"
echo "    ℹ Model needs to be downloaded"
echo "    → Target: models/ollama/secondary/llava/"

# InternVL3.5: Will be downloaded via HuggingFace/vLLM
echo "  📍 InternVL3.5 8B"
echo "    ℹ Model will be downloaded by vLLM on first start"
echo "    → Cache: models/huggingface/hub/"

# GLM-4.6: Will be downloaded via HuggingFace/vLLM
echo "  📍 GLM-4.6"
echo "    ℹ Model will be downloaded by vLLM on first start"
echo "    → Cache: models/huggingface/hub/"

echo ""
echo "EMBEDDING MODELS:"
echo "─────────────────"

# Check if nomic-embed is in mistral_models (seen in manifest)
if [ "$METHOD" = "local" ]; then
  CHECK_PATH="$BASE_DIR/models/mistral_models"
else
  CHECK_PATH="$ISILON_PATH/mistral_models"
fi

if [ -d "$CHECK_PATH" ]; then
  echo "  ℹ️  Found nomic-embed-text in existing mistral_models"
  echo "    This will remain in secondary/mistral_small3_24b"
  echo "    New embeddings will be in models/ollama/embeddings/"
fi

echo "  📍 Nomic Embed Text 137M"
echo "    ℹ Model needs to be downloaded"
echo "    → Target: models/ollama/embeddings/"

echo "  📍 Qwen3 Embedding 8B"
echo "    ℹ Model needs to be downloaded"
echo "    → Target: models/ollama/embeddings/"

echo "  📍 EmbeddingGemma 300M"
echo "    ℹ Model needs to be downloaded"
echo "    → Target: models/ollama/embeddings/"

echo "  📍 Jasper (HuggingFace)"
echo "    ℹ Model will be downloaded on first use"
echo "    → Cache: models/huggingface/hub/"

echo "  📍 Stella (HuggingFace)"
echo "    ℹ Model will be downloaded on first use"
echo "    → Cache: models/huggingface/hub/"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Set permissions
echo ""
echo "🔒 Setting permissions..."
chmod -R 755 config dockerfiles scripts monitoring 2>/dev/null || true
chmod -R 777 data models logs 2>/dev/null || true
echo "✅ Permissions set"

# Create .gitignore
cat > .gitignore <<'EOF'
# Environment files
.env
*.env.local

# Data directories (too large for git)
data/
models/huggingface/
models/ollama/primary/
models/ollama/secondary/
models/ollama/embeddings/
models/ollama/playground/
models/ollama/custom/
logs/

# Backup files
*.bak
*.backup

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Docker
*.log
EOF

echo "✅ .gitignore created"

# Create README for models directory
cat > models/README.md <<EOF
# Model Storage Structure

**Base Path**: \`$BASE_DIR/models/\`

## Directory Layout

\`\`\`
models/
├── ollama/
│   ├── primary/          # Persistent models (always in VRAM)
│   │   ├── gpt_oss/      # GPT-OSS 120B (~196GB)
│   │   └── qwen3_vl/     # Not used (vLLM loads from HF cache)
│   │
│   ├── secondary/        # On-demand models (600s timeout)
│   │   ├── deepseek_r1_671b/           # 377GB
│   │   ├── deepseek_r1_8b_qwen3/       # 16GB
│   │   ├── qwen3_235b/                 # 233GB
│   │   ├── qwen3_32b/                  # 62GB
│   │   ├── qwen25vl_72b/               # 211GB
│   │   ├── mistral_small3_24b/         # 45GB
│   │   ├── llama4_scout_17b/           # 109GB
│   │   ├── gemma3_27b/                 # 52GB
│   │   ├── phi4_reasoning_14b/         # 28GB
│   │   ├── paligemma/                  # 10GB
│   │   ├── base_small_models/          # 5GB
│   │   └── llava/                      # To be downloaded
│   │
│   ├── embeddings/       # Embedding models (300s timeout)
│   │   ├── nomic/        # To be downloaded
│   │   ├── qwen3_embed/  # To be downloaded
│   │   └── gemma_embed/  # To be downloaded
│   │
│   ├── playground/       # User testing (60s timeout)
│   └── custom/           # User custom models
│
└── huggingface/         # HuggingFace model cache
    └── hub/             # vLLM downloads models here
        ├── models--Qwen--Qwen3-VL-235B-A22B-Thinking-FP8/
        ├── models--OpenGVLab--InternVL3_5-8B/
        ├── models--zai-org--GLM-4.6-FP8/
        ├── models--NovaSearch--jasper_en_vision_language_v1/
        └── models--NovaSearch--stella_en_1.5B_v5/
\`\`\`

## Model Status

### Primary Models (Persistent VRAM)
- ⬇️ **GPT-OSS 120B**: Needs to be downloaded
- ⬇️ **Qwen3-VL 235B**: Downloaded by vLLM on first start

### Secondary Models (On-Demand)
EOF

# Add status for each secondary model based on what exists
for model_dir in models/ollama/secondary/*; do
  if [ -d "$model_dir" ]; then
    model_name=$(basename "$model_dir")
    echo "- ✅ **${model_name}**: Organized from existing files" >> models/README.md
  fi
done

cat >> models/README.md <<'EOF'
- ⬇️ **Llava 34B**: Needs to be downloaded (~37GB)
- ⬇️ **InternVL3.5 8B**: Downloaded by vLLM on first start (~6GB)
- ⬇️ **GLM-4.6**: Downloaded by vLLM on first start (~355GB)

### Embedding Models
- ⬇️ **Nomic Embed Text**: Needs to be downloaded (~1GB)
- ⬇️ **Qwen3 Embedding**: Needs to be downloaded (~15GB)
- ⬇️ **EmbeddingGemma**: Needs to be downloaded (~1GB)
- ⬇️ **Jasper (HF)**: Downloaded on first use (~4GB)
- ⬇️ **Stella (HF)**: Downloaded on first use (~5GB)

## Total Storage

**Currently Organized**: Check actual disk usage
**After Full Download**: ~1.8TB estimated
- Primary: ~196GB (GPT-OSS)
- Secondary: ~900GB (existing) + ~400GB (new downloads)
- HuggingFace Cache: ~250GB (vision models)
- Embeddings: ~26GB

## Download Commands

### Primary Models
```bash
# GPT-OSS 120B (Ollama)
docker exec primary-gpt-oss ollama pull gpt-oss:120b

# Qwen3-VL 235B (vLLM - downloads automatically on first start)
# No manual download needed
```

### Secondary Models
```bash
# Llava 34B (Ollama)
docker exec secondary-llava ollama pull llava:34b-v1.6-q8_0

# Other secondary models download automatically via vLLM
```

### Embedding Models
```bash
# Ollama embeddings
docker exec embeddings-service ollama pull nomic-embed-text:137m-v1.5-fp16
docker exec embeddings-service ollama pull qwen3-embedding:8b-q8_0
docker exec embeddings-service ollama pull embeddinggemma:300m-bf16

# HuggingFace embeddings download automatically on first use
```

## Notes

- All models organized under /mnt/ai8_arch/models/
- Models are in logical directories by tier (primary/secondary)
- Each secondary model has its own subdirectory for clarity
- HuggingFace models cache in `models/huggingface/hub/`
EOF

echo "✅ models/README.md created"

# Create model inventory
cat > models/INVENTORY.txt <<EOF
MODEL INVENTORY - ai8_arch
Generated: $(date)
Base Path: $BASE_DIR

PRIMARY MODELS (Persistent VRAM - GPUs 2-7)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status  Model Name                  Size      Location
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⬇️      GPT-OSS 120B               196GB     ollama/primary/gpt_oss/
⬇️      Qwen3-VL 235B              238GB     huggingface/hub/ (auto-download)

SECONDARY MODELS (On-Demand, 600s timeout)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status  Model Name                  Size      Location
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

# Add existing models to inventory
if [ -d "$BASE_DIR/models/ollama/secondary/deepseek_r1_671b" ]; then
  echo "✅      DeepSeek R1 671B           377GB     ollama/secondary/deepseek_r1_671b/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/deepseek_r1_8b_qwen3" ]; then
  echo "✅      DeepSeek R1 8B Qwen3       16GB      ollama/secondary/deepseek_r1_8b_qwen3/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/qwen3_235b" ]; then
  echo "✅      Qwen3 235B                 233GB     ollama/secondary/qwen3_235b/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/qwen3_32b" ]; then
  echo "✅      Qwen3 32B                  62GB      ollama/secondary/qwen3_32b/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/qwen25vl_72b" ]; then
  echo "✅      Qwen2.5VL 72B              211GB     ollama/secondary/qwen25vl_72b/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/mistral_small3_24b" ]; then
  echo "✅      Mistral Small 3.1 24B      45GB      ollama/secondary/mistral_small3_24b/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/llama4_scout_17b" ]; then
  echo "✅      Llama4 Scout 17B           109GB     ollama/secondary/llama4_scout_17b/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/gemma3_27b" ]; then
  echo "✅      Gemma3 27B                 52GB      ollama/secondary/gemma3_27b/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/phi4_reasoning_14b" ]; then
  echo "✅      Phi4 Reasoning 14B         28GB      ollama/secondary/phi4_reasoning_14b/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/paligemma" ]; then
  echo "✅      PaliGemma                  10GB      ollama/secondary/paligemma/" >> models/INVENTORY.txt
fi
if [ -d "$BASE_DIR/models/ollama/secondary/base_small_models" ]; then
  echo "✅      Base Small Models          5GB       ollama/secondary/base_small_models/" >> models/INVENTORY.txt
fi

cat >> models/INVENTORY.txt <<'EOF'
⬇️      Llava 34B                  37GB      ollama/secondary/llava/
⬇️      InternVL3.5 8B             6GB       huggingface/hub/ (auto-download)
⬇️      GLM-4.6                    355GB     huggingface/hub/ (auto-download)

EMBEDDING MODELS (300s timeout)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status  Model Name                  Size      Location
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⬇️      Nomic Embed Text           1GB       ollama/embeddings/
⬇️      Qwen3 Embedding            15GB      ollama/embeddings/
⬇️      EmbeddingGemma             1GB       ollama/embeddings/
⬇️      Jasper (HF)                4GB       huggingface/hub/ (auto-download)
⬇️      Stella (HF)                5GB       huggingface/hub/ (auto-download)

LEGEND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅  Available (organized from existing files)
⬇️  Needs to be downloaded

STORAGE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Check current usage: du -sh /mnt/ai8_arch/models/*
EOF

echo "✅ models/INVENTORY.txt created"

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 Directory Structure Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Base directory: $BASE_DIR"
echo ""
echo "📂 Configuration:"
echo "   config/                    - LiteLLM, model configs"
echo "   dockerfiles/               - Custom Docker images"
echo "   scripts/                   - Startup scripts"
echo "   monitoring/                - Prometheus, Grafana"
echo ""
echo "📂 Data (persistent):"
echo "   data/postgres/             - Database"
echo "   data/openwebui/            - Chat interface data"
echo "   data/n8n/                  - Workflows"
echo "   data/grafana/              - Dashboards"
echo "   data/prometheus/           - Metrics"
echo ""
echo "📂 Models:"
echo "   models/ollama/primary/     - 2 persistent models (VRAM)"
echo "   models/ollama/secondary/   - 11+ on-demand models (organized)"
echo "   models/ollama/embeddings/  - 5 embedding models"
echo "   models/ollama/playground/  - User testing"
echo "   models/ollama/custom/      - User custom models"
echo "   models/huggingface/        - HF model cache (~250GB)"
echo ""
echo "📂 Logs:"
echo "   logs/ollama/               - Ollama logs"
echo "   logs/vllm/                 - vLLM logs"
echo "   logs/embeddings/           - Embedding service logs"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Model Organization Complete"
echo "   📝 See models/README.md for details"
echo "   📋 See models/INVENTORY.txt for full list"
echo ""
echo "🎯 Next steps:"
echo "   1. Review models/README.md"
echo "   2. Review models/INVENTORY.txt"
echo "   3. Check disk usage: du -sh $BASE_DIR/models/*"
echo "   4. Create configuration files"
echo "   5. Create docker-compose-vllm.yaml"
echo "   6. Create .env with credentials"
echo ""
echo "💡 To migrate models from Isilon (if not done):"
echo "   Option 1 - Move: mv /net/isilon/ifs/updates/models/ai8_arch/models/* $BASE_DIR/models/ollama/secondary/"
echo "   Option 2 - Copy: cp -a /net/isilon/ifs/updates/models/ai8_arch/models/* $BASE_DIR/models/ollama/secondary/"
echo "   Option 3 - Link: ln -s /net/isilon/ifs/updates/models/ai8_arch/models/* $BASE_DIR/models/ollama/secondary/"
echo ""