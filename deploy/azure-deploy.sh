#!/bin/bash

# Azure Container Instances Deployment Script for Focus Tracker
# This script deploys the Focus Tracker system to Azure Container Instances

set -e

# Configuration
RESOURCE_GROUP="focus-tracker-rg"
LOCATION="eastus"
ACR_NAME="focustrackerregistry"
REDIS_NAME="focus-tracker-redis"
CONTAINER_GROUP_NAME="focus-tracker-app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        error "Azure CLI is not installed. Please install it first."
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install it first."
    fi
    
    # Check if logged in to Azure
    if ! az account show &> /dev/null; then
        error "Not logged in to Azure. Please run 'az login'."
    fi
    
    log "Prerequisites check passed"
}

# Create resource group
create_resource_group() {
    log "Creating resource group..."
    
    if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
        log "Resource group already exists"
    else
        az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
        log "Resource group created"
    fi
}

# Create Azure Container Registry
create_acr() {
    log "Creating Azure Container Registry..."
    
    if az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
        log "Container Registry already exists"
    else
        az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic
        log "Container Registry created"
    fi
    
    # Enable admin account for Docker login
    az acr update --name "$ACR_NAME" --admin-enabled true --resource-group "$RESOURCE_GROUP"
}

# Create Redis Cache
create_redis() {
    log "Creating Redis Cache..."
    
    if az redis show --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
        log "Redis Cache already exists"
    else
        az redis create \
            --name "$REDIS_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --location "$LOCATION" \
            --sku Basic \
            --vm-size C0 \
            --redis-version 6 \
            --enable-non-ssl-port true
        
        log "Redis Cache created"
    fi
    
    # Get Redis connection details
    REDIS_HOST=$(az redis show --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query "hostName" --output tsv)
    REDIS_PORT=$(az redis show --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query "port" --output tsv)
    REDIS_KEY=$(az redis list-keys --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query "primaryKey" --output tsv)
    
    log "Redis Cache ready at $REDIS_HOST:$REDIS_PORT"
}

# Build and push Docker image
build_and_push_image() {
    log "Building and pushing Docker image..."
    
    # Log in to ACR
    ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query "loginServer" --output tsv)
    az acr login --name "$ACR_NAME"
    
    # Build and push image
    IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"
    IMAGE_NAME="$ACR_LOGIN_SERVER/focus-tracker:$IMAGE_TAG"
    
    docker build -t "$IMAGE_NAME" .
    docker push "$IMAGE_NAME"
    
    # Store image name for later use
    echo "$IMAGE_NAME" > .acr_image_name
    log "Docker image pushed: $IMAGE_NAME"
}

# Create Container Instance Group
create_container_group() {
    log "Creating Container Instance Group..."
    
    IMAGE_NAME=$(cat .acr_image_name)
    REDIS_HOST=$(az redis show --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query "hostName" --output tsv)
    REDIS_PORT=$(az redis show --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query "port" --output tsv)
    REDIS_KEY=$(az redis list-keys --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query "primaryKey" --output tsv)
    
    # Create container group with API and Redis
    az container create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_GROUP_NAME" \
        --image "$IMAGE_NAME" \
        --dns-name-label "focus-tracker-$(date +%s)" \
        --ports 8002 \
        --cpu 2 \
        --memory 4 \
        --environment-variables \
            "REDIS_URL=redis://$REDIS_HOST:$REDIS_PORT/0" \
            "CELERY_BROKER_URL=redis://$REDIS_HOST:$REDIS_PORT/0" \
            "CELERY_RESULT_BACKEND=redis://$REDIS_HOST:$REDIS_PORT/0" \
            "ENVIRONMENT=production" \
            "LOG_LEVEL=INFO" \
        --secure-environment-variables \
            "REDIS_PASSWORD=$REDIS_KEY" \
        --command-line "uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8002"
    
    log "Container Instance Group created"
}

# Create separate container group for batch workers
create_batch_workers() {
    log "Creating batch workers container group..."
    
    IMAGE_NAME=$(cat .acr_image_name)
    REDIS_HOST=$(az redis show --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query "hostName" --output tsv)
    REDIS_PORT=$(az redis show --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query "port" --output tsv)
    REDIS_KEY=$(az redis list-keys --name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query "primaryKey" --output tsv)
    
    # Create container group for batch workers
    az container create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_GROUP_NAME-workers" \
        --image "$IMAGE_NAME" \
        --cpu 2 \
        --memory 4 \
        --restart-policy OnFailure \
        --environment-variables \
            "REDIS_URL=redis://$REDIS_HOST:$REDIS_PORT/0" \
            "CELERY_BROKER_URL=redis://$REDIS_HOST:$REDIS_PORT/0" \
            "CELERY_RESULT_BACKEND=redis://$REDIS_HOST:$REDIS_PORT/0" \
            "ENVIRONMENT=production" \
            "LOG_LEVEL=INFO" \
            "WORKER_CONCURRENCY=2" \
        --secure-environment-variables \
            "REDIS_PASSWORD=$REDIS_KEY" \
        --command-line "uv run celery -A src.services.batch_worker worker --loglevel=INFO --queues=batch_processing --concurrency=2"
    
    log "Batch workers container group created"
}

# Get application URL
get_app_url() {
    log "Getting application URL..."
    
    APP_URL=$(az container show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_GROUP_NAME" \
        --query "ipAddress.fqdn" \
        --output tsv)
    
    log "Application URL: http://$APP_URL:8002"
    echo "Your Focus Tracker is now live at: http://$APP_URL:8002"
}

# Set up monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Enable diagnostics
    az monitor diagnostic-settings create \
        --resource-group "$RESOURCE_GROUP" \
        --resource "$(az container show --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_GROUP_NAME" --query id --output tsv)" \
        --name "focus-tracker-diagnostics" \
        --logs '[{"category": "ContainerLogs", "enabled": true}]' \
        --metrics '[{"category": "AllMetrics", "enabled": true}]' \
        --storage-account "$(az storage account list --resource-group "$RESOURCE_GROUP" --query '[0].name' --output tsv 2>/dev/null || echo '')" || true
    
    log "Monitoring setup completed"
}

# Create storage account for logs
create_storage_account() {
    log "Creating storage account for logs..."
    
    STORAGE_ACCOUNT_NAME="focustrackerlogs$(date +%s | tail -c 8)"
    
    if az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
        log "Storage account already exists"
    else
        az storage account create \
            --name "$STORAGE_ACCOUNT_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --location "$LOCATION" \
            --sku Standard_LRS
        
        log "Storage account created"
    fi
}

# Main deployment function
deploy() {
    log "Starting Azure Container Instances deployment..."
    
    check_prerequisites
    create_resource_group
    create_storage_account
    create_acr
    create_redis
    build_and_push_image
    create_container_group
    create_batch_workers
    setup_monitoring
    get_app_url
    
    log "Deployment completed successfully!"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    rm -f .acr_image_name
}

# Trap cleanup on exit
trap cleanup EXIT

# Run deployment
deploy "$@"
