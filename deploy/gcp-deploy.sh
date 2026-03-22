#!/bin/bash

# Google Cloud Run Deployment Script for Focus Tracker
# This script deploys the Focus Tracker system to Google Cloud Run

set -e

# Configuration
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="focus-tracker"
REDIS_INSTANCE="focus-tracker-redis"

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
    
    # Check gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        error "Google Cloud CLI is not installed. Please install it first."
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install it first."
    fi
    
    # Get project ID
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$PROJECT_ID" ]; then
            error "Google Cloud project ID not set. Please run 'gcloud config set project YOUR_PROJECT_ID'"
        fi
    fi
    
    log "Using project: $PROJECT_ID"
    log "Prerequisites check passed"
}

# Enable required APIs
enable_apis() {
    log "Enabling required Google Cloud APIs..."
    
    gcloud services enable run.googleapis.com --project="$PROJECT_ID"
    gcloud services enable cloudbuild.googleapis.com --project="$PROJECT_ID"
    gcloud services enable redis.googleapis.com --project="$PROJECT_ID"
    gcloud services enable artifactregistry.googleapis.com --project="$PROJECT_ID"
    
    log "APIs enabled"
}

# Create Redis instance
create_redis_instance() {
    log "Creating Redis instance..."
    
    if gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" --project="$PROJECT_ID" 2>/dev/null; then
        log "Redis instance already exists"
    else
        gcloud redis instances create "$REDIS_INSTANCE" \
            --region="$REGION" \
            --size=2 \
            --tier=standard \
            --redis-version=redis_6_x \
            --project="$PROJECT_ID"
        
        log "Redis instance created"
    fi
    
    # Wait for Redis instance to be ready
    log "Waiting for Redis instance to be ready..."
    gcloud redis instances wait "$REDIS_INSTANCE" --region="$REGION" --project="$PROJECT_ID"
    
    # Get Redis connection details
    REDIS_IP=$(gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" --project="$PROJECT_ID" --format="value(host)")
    REDIS_PORT=$(gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" --project="$PROJECT_ID" --format="value(port)")
    
    log "Redis instance ready at $REDIS_IP:$REDIS_PORT"
}

# Build and deploy Cloud Run service
deploy_cloud_run() {
    log "Building and deploying Cloud Run service..."
    
    # Configure Docker to use gcloud as credential helper
    gcloud auth configure-docker "$REGION-docker.pkg.dev"
    
    # Build and push image
    IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/focus-tracker/focus-tracker:latest"
    
    docker build -t "$IMAGE_NAME" .
    docker push "$IMAGE_NAME"
    
    # Deploy to Cloud Run
    gcloud run deploy "$SERVICE_NAME" \
        --image="$IMAGE_NAME" \
        --region="$REGION" \
        --platform=managed \
        --allow-unauthenticated \
        --memory=4Gi \
        --cpu=2 \
        --timeout=300 \
        --concurrency=10 \
        --max-instances=10 \
        --set-env-vars="REDIS_URL=redis://$REDIS_IP:$REDIS_PORT/0" \
        --set-env-vars="CELERY_BROKER_URL=redis://$REDIS_IP:$REDIS_PORT/0" \
        --set-env-vars="CELERY_RESULT_BACKEND=redis://$REDIS_IP:$REDIS_PORT/0" \
        --set-env-vars="ENVIRONMENT=production" \
        --set-env-vars="LOG_LEVEL=INFO" \
        --project="$PROJECT_ID"
    
    log "Cloud Run service deployed"
}

# Deploy Cloud Run service for batch workers
deploy_batch_workers() {
    log "Deploying batch worker service..."
    
    # Build worker image
    WORKER_IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/focus-tracker/batch-worker:latest"
    
    docker build -t "$WORKER_IMAGE_NAME" -f- . <<EOF
FROM $IMAGE_NAME
CMD ["uv", "run", "celery", "-A", "src.services.batch_worker", "worker", "--loglevel=INFO", "--queues=batch_processing", "--concurrency=2"]
EOF
    
    docker push "$WORKER_IMAGE_NAME"
    
    # Deploy batch worker service
    gcloud run deploy "$SERVICE_NAME-batch-worker" \
        --image="$WORKER_IMAGE_NAME" \
        --region="$REGION" \
        --platform=managed \
        --no-allow-unauthenticated \
        --memory=4Gi \
        --cpu=2 \
        --timeout=900 \
        --concurrency=1 \
        --max-instances=5 \
        --min-instances=1 \
        --set-env-vars="REDIS_URL=redis://$REDIS_IP:$REDIS_PORT/0" \
        --set-env-vars="CELERY_BROKER_URL=redis://$REDIS_IP:$REDIS_PORT/0" \
        --set-env-vars="CELERY_RESULT_BACKEND=redis://$REDIS_IP:$REDIS_PORT/0" \
        --set-env-vars="ENVIRONMENT=production" \
        --set-env-vars="LOG_LEVEL=INFO" \
        --project="$PROJECT_ID"
    
    log "Batch worker service deployed"
}

# Set up IAM permissions
setup_iam() {
    log "Setting up IAM permissions..."
    
    # Get service account
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
    SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
    
    # Grant necessary permissions
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/redis.client"
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/logging.logWriter"
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/monitoring.metricWriter"
    
    log "IAM permissions set up"
}

# Create firewall rules for Redis
create_firewall_rules() {
    log "Creating firewall rules for Redis access..."
    
    # Get network
    NETWORK=$(gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" --project="$PROJECT_ID" --format="value(authorizedNetwork)")
    
    if [ -z "$NETWORK" ]; then
        # Create a new network range
        NETWORK="10.0.0.0/24"
        gcloud redis instances update "$REDIS_INSTANCE" \
            --region="$REGION" \
            --authorized-network="$NETWORK" \
            --project="$PROJECT_ID"
    fi
    
    log "Firewall rules configured for network: $NETWORK"
}

# Get service URL
get_service_url() {
    log "Getting service URL..."
    
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)" \
        --project="$PROJECT_ID")
    
    log "Service URL: $SERVICE_URL"
    echo "Your Focus Tracker is now live at: $SERVICE_URL"
}

# Main deployment function
deploy() {
    log "Starting Google Cloud Run deployment..."
    
    check_prerequisites
    enable_apis
    create_redis_instance
    setup_iam
    create_firewall_rules
    deploy_cloud_run
    deploy_batch_workers
    get_service_url
    
    log "Deployment completed successfully!"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    docker system prune -f 2>/dev/null || true
}

# Trap cleanup on exit
trap cleanup EXIT

# Run deployment
deploy "$@"
