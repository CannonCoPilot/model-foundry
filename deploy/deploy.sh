#!/bin/bash
# AI8 Architecture - Unified Deployment Script
# Base Path: /mnt/ai8_arch
# User: CannonCoPilot
# Date: 2025-01-11
# Revised: 2025-10-21

set -euo pipefail

# Function to handle errors and ensure cleanup
handle_error() {
    local exit_code=$?
    local line_no=$1
    log_error "An error occurred with exit code $exit_code on line $line_no."
    log_error "Failing command: '$BASH_COMMAND'"
    log_warning "Tearing down services to prevent orphaned containers."
    $COMPOSE_CMD --env-file .env -f deploy/docker-compose.yaml down > /dev/null || true
    log_error "Deployment failed."
    exit $exit_code
}

# Trap errors to the handle_error function
trap 'handle_error $LINENO' ERR

# Determine the absolute path of the directory containing this script
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
# The project root is one level up from the deploy directory
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Change to the project root directory to ensure all paths are relative to it
cd "$PROJECT_ROOT"

COMPOSE_CMD="docker compose"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Checkpoint function
checkpoint() {
    local phase=$1
    local description=$2
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "CHECKPOINT: $phase - $description"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Verify prerequisites
verify_prerequisites() {
    checkpoint "PRE-FLIGHT" "Verifying Prerequisites"
    
    # Check Docker
    if ! command -v docker > /dev/null; then
        log_error "Docker not installed"
        exit 1
    fi
    log_success "Docker installed: $(docker --version)"
    
    # Check Docker Compose
    if ! docker compose version > /dev/null; then
        log_error "Docker Compose not available"
        exit 1
    fi
    log_success "Docker Compose available: $(docker compose version)"
    
    # Check NVIDIA
    if ! command -v nvidia-smi > /dev/null; then
        log_error "nvidia-smi not found"
        exit 1
    fi
    log_success "NVIDIA driver installed"
    
    # Check GPU count
    GPU_COUNT=$(nvidia-smi -L | wc -l)
    if [ "$GPU_COUNT" -lt 8 ]; then
        log_warning "Expected 8 GPUs, found $GPU_COUNT"
    else
        log_success "Found $GPU_COUNT GPUs"
    fi
    
    # Check base directory
    if [ ! -d "/mnt/ai8_arch" ]; then
        log_error "/mnt/ai8_arch does not exist"
        exit 1
    fi
    log_success "Base directory exists: /mnt/ai8_arch"
    
    # Check .env file
    if [ ! -f "deploy/.env" ]; then
        log_error "deploy/.env file not found"
        log_info "Ensure the .env file is located in the /mnt/ai8_arch/deploy/ directory."
        exit 1
    fi
    log_success ".env file exists in deploy/ directory"
    
    # Source .env
    set -a
    source deploy/.env
    set +a
    
    # Check required variables
    REQUIRED_VARS=("HF_TOKEN" "POSTGRES_USER" "POSTGRES_PASSWORD" "LITELLM_MASTER_KEY" "REDIS_PASSWORD" "MONGO_PASSWORD")
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required variable $var not set in .env"
            exit 1
        fi
    done
    log_success "Required environment variables set"
    
    # Check disk space
    AVAILABLE_GB=$(df -BG /mnt/ai8_arch/models | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$AVAILABLE_GB" -lt 500 ]; then
        log_warning "Low disk space: ${AVAILABLE_GB}GB available (recommend 1TB+)"
    else
        log_success "Sufficient disk space: ${AVAILABLE_GB}GB available"
    fi
    
    echo ""
}

# Deploy all services
deploy_all() {
    checkpoint "DEPLOY" "Deploying All Services"
    
    log_info "Verifying execution context..."
    pwd
    ls -la
    log_info "Forcing image build and starting all services..."
    $COMPOSE_CMD --env-file deploy/.env --project-directory . -f deploy/docker-compose.yaml up -d --build
    
    log_success "All services started."
    log_warning "It may take several minutes for all services to become healthy."
    log_info "Use 'docker ps' or '$0 status' to check the status of the containers."
    log_info "Use '$0 logs <service_name>' to view logs for a specific service."
}

# Build all custom images
build_images() {
    checkpoint "BUILD" "Building Custom Docker Images"
    log_info "Building embeddings image..."
    $COMPOSE_CMD --env-file deploy/.env --project-directory . -f deploy/docker-compose.yaml build embeddings
    log_info "Building vLLM image (this takes 15-20 minutes)..."
    $COMPOSE_CMD --env-file deploy/.env --project-directory . -f deploy/docker-compose.yaml build secondary_qwen3_omni
    log_success "All custom images built successfully"
}

# Show usage information
usage() {
    echo "Usage: $0 [COMMAND]"
    echo "Commands:"
    echo "  deploy     - Deploy all services."
    echo "  build      - Build all custom Docker images."
    echo "  down       - Stop and remove all services."
    echo "  status     - Show the status of all services."
    echo "  logs [service...] - Tail logs for specified services (or all)."
    echo "  playground - Start the interactive user playground."
}

# Main deployment function
main() {
    COMMAND="${1:-deploy}"

    case $COMMAND in
        deploy)
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "AI8 Architecture - Unified Deployment"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            
            verify_prerequisites
            deploy_all
            
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            log_success "Deployment Complete!"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            
            log_info "Full System Status:"
            $COMPOSE_CMD --env-file deploy/.env --project-directory . -f deploy/docker-compose.yaml ps
            
            echo ""
            log_info "Useful Commands:"
            echo "  • View all logs:       $0 logs"
            echo "  • View specific logs:  $0 logs <service_name>"
            echo "  • Stop all:            $0 down"
            echo "  • Check GPU usage:     nvidia-smi"
            echo "  • Access playground:   $0 playground"
            echo ""
            ;;
        build)
            build_images
            ;;
        down)
            log_info "Stopping and removing all services..."
            $COMPOSE_CMD --env-file deploy/.env --project-directory . -f deploy/docker-compose.yaml down
            log_success "All services stopped."
            ;;
        status)
            log_info "Current status of all services:"
            $COMPOSE_CMD --env-file deploy/.env --project-directory . -f deploy/docker-compose.yaml ps
            ;;
        logs)
            shift # Remove 'logs' command
            log_info "Tailing logs for: ${*:-all services}"
            $COMPOSE_CMD --env-file deploy/.env --project-directory . -f deploy/docker-compose.yaml logs -f "$@"
            ;;
        playground)
            log_info "Attaching to the user playground container..."
            log_warning "Press Ctrl+P, Ctrl+Q to detach."
            docker attach user-playground
            ;;
        *)
            log_error "Invalid command: $COMMAND"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"