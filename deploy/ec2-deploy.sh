#!/bin/bash

# EC2 Deployment Script for Focus Tracker
# This script builds Docker images locally and deploys to EC2

set -e

# EC2 Configuration
EC2_USER="ubuntu"  # Using Ubuntu AMI
EC2_HOST="ec2-13-60-232-154.eu-north-1.compute.amazonaws.com"
EC2_IP="13.60.232.154"
PEM_KEY="./sgdp_focus_agent.pem"
AWS_REGION="eu-north-1"

# Docker Configuration
DOCKER_REGISTRY="937991583559.dkr.ecr.eu-north-1.amazonaws.com"  # Your ECR registry
IMAGE_NAME="focus-tracker"
IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"
PROJECT_NAME="gaze-tracker"

# Application Configuration
REDIS_PASSWORD="redis_secure_password_$(date +%s)"
FLOWER_PASSWORD="flower_admin_$(date +%s)"
DOMAIN_NAME=""  # Leave empty for now, can add later

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed. Please install it first."
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install it first."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed. Please install it first."
    fi
    
    # Check SSH
    if ! command -v ssh &> /dev/null; then
        error "SSH is not installed. Please install it first."
    fi
    
    # Check PEM key exists
    if [ ! -f "$PEM_KEY" ]; then
        error "PEM key file not found: $PEM_KEY"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured. Please run 'aws configure'."
    fi
    
    # Test SSH connection
    if ! ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$EC2_USER@$EC2_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
        error "Cannot connect to EC2 instance via SSH. Check PEM key and security group."
    fi
    
    log "Prerequisites check passed"
}

# Setup ECR repository
setup_ecr() {
    log "Setting up ECR repository..."
    
    # Create ECR repository if it doesn't exist
    if ! aws ecr describe-repositories --repository-names "$IMAGE_NAME" --region "$AWS_REGION" 2>/dev/null; then
        aws ecr create-repository --repository-name "$IMAGE_NAME" --region "$AWS_REGION" --image-scanning-configuration scanOnPush=true
        log "ECR repository created: $IMAGE_NAME"
    else
        log "ECR repository already exists: $IMAGE_NAME"
    fi
    
    # Get ECR login password
    log "Logging into ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$DOCKER_REGISTRY"
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    # Build main application image
    docker build -t "$IMAGE_NAME:$IMAGE_TAG" .
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
    
    log "Docker image built: $IMAGE_NAME:$IMAGE_TAG"
}

# Push images to ECR
push_images() {
    log "Pushing Docker images to ECR..."
    
    docker push "$DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
    
    # Also tag as latest
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$DOCKER_REGISTRY/$IMAGE_NAME:latest"
    docker push "$DOCKER_REGISTRY/$IMAGE_NAME:latest"
    
    log "Images pushed to ECR successfully"
}

# Setup EC2 instance
setup_ec2() {
    log "Setting up EC2 instance..."
    
    # Create setup script for EC2
    cat > ec2-setup.sh << EOF
#!/bin/bash
set -e

# Update system
sudo apt-get update -y

# Install Docker
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
sudo mkdir -p /opt/$PROJECT_NAME
sudo chown ubuntu:ubuntu /opt/$PROJECT_NAME

# Create logs directory
mkdir -p /opt/$PROJECT_NAME/logs
mkdir -p /opt/$PROJECT_NAME/data
mkdir -p /opt/$PROJECT_NAME/model

# Install additional tools
sudo apt-get install -y git htop curl

# Create docker-compose override for production
cat > /opt/$PROJECT_NAME/docker-compose.override.yml << 'EOV'
version: '3.8'

services:
  # Override Redis for production with password
  redis:
    command: redis-server --appendonly yes --port 6379 --requirepass $REDIS_PASSWORD
    ports:
      - "127.0.0.1:6379:6379"  # Only accessible from localhost

  # Override API for production
  api:
    image: $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
    environment:
      - REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0
      - CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/0
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - REDIS_PASSWORD=$REDIS_PASSWORD
    deploy:
      resources:
        limits:
          memory: 512M  # Suitable for t3.micro
        reservations:
          memory: 256M

  # Override batch workers for production
  batch_worker_1:
    image: $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
    environment:
      - REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0
      - CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/0
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - REDIS_PASSWORD=$REDIS_PASSWORD
      - WORKER_NAME=batch_worker_1
      - WORKER_CONCURRENCY=1
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  batch_worker_2:
    image: $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
    environment:
      - REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0
      - CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/0
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - REDIS_PASSWORD=$REDIS_PASSWORD
      - WORKER_NAME=batch_worker_2
      - WORKER_CONCURRENCY=1
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  # Override Flower for production
  flower:
    image: $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
    environment:
      - REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0
      - CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/0
      - REDIS_PASSWORD=$REDIS_PASSWORD
    command: uv run celery -A src.services.celery_app flower --port=5555 --broker=redis://:$REDIS_PASSWORD@redis:6379/0 --basic_auth=admin:$FLOWER_PASSWORD

  # Disable nginx and redis-commander for now (can be enabled later)
  nginx:
    profiles: []
  redis-commander:
    profiles: []
EOV

echo "EC2 setup completed"
EOF

    # Copy and execute setup script
    scp -i "$PEM_KEY" -o StrictHostKeyChecking=no ec2-setup.sh "$EC2_USER@$EC2_HOST:/tmp/ec2-setup.sh"
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "chmod +x /tmp/ec2-setup.sh && /tmp/ec2-setup.sh"
    
    log "EC2 instance setup completed"
}

# Deploy application
deploy_application() {
    log "Deploying application to EC2..."
    
    # Create production docker-compose file
    cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: gaze_tracker_redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - gaze_tracker_network

  api:
    image: $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
    container_name: gaze_tracker_api
    restart: unless-stopped
    ports:
      - "8002:8002"
    environment:
      - REDIS_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - REDIS_PASSWORD=\${REDIS_PASSWORD}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./model:/app/model
      - batch_worker_pids:/app/.celery_pids
      - temp_frames:/tmp/test_session_frames
    depends_on:
      - redis
    networks:
      - gaze_tracker_network

  batch_worker_1:
    image: $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
    container_name: gaze_tracker_batch_worker_1
    restart: unless-stopped
    environment:
      - REDIS_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - REDIS_PASSWORD=\${REDIS_PASSWORD}
      - WORKER_NAME=batch_worker_1
      - WORKER_CONCURRENCY=1
    volumes:
      - ./logs:/app/logs
      - ./model:/app/model
      - batch_worker_pids:/app/.celery_pids
      - temp_frames:/tmp/test_session_frames
    depends_on:
      - redis
      - api
    command: uv run celery -A src.services.batch_worker worker --loglevel=INFO --queues=batch_processing --concurrency=1 --hostname=batch_worker_1 --logfile=/app/logs/batch_worker_1.log --pidfile=/app/.celery_pids/batch_worker_1.pid
    networks:
      - gaze_tracker_network

  batch_worker_2:
    image: $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
    container_name: gaze_tracker_batch_worker_2
    restart: unless-stopped
    environment:
      - REDIS_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - REDIS_PASSWORD=\${REDIS_PASSWORD}
      - WORKER_NAME=batch_worker_2
      - WORKER_CONCURRENCY=1
    volumes:
      - ./logs:/app/logs
      - ./model:/app/model
      - batch_worker_pids:/app/.celery_pids
      - temp_frames:/tmp/test_session_frames
    depends_on:
      - redis
      - api
    command: uv run celery -A src.services.batch_worker worker --loglevel=INFO --queues=batch_processing --concurrency=1 --hostname=batch_worker_2 --logfile=/app/logs/batch_worker_2.log --pidfile=/app/.celery_pids/batch_worker_2.pid
    networks:
      - gaze_tracker_network

  flower:
    image: $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
    container_name: gaze_tracker_flower
    restart: unless-stopped
    ports:
      - "5555:5555"
    environment:
      - REDIS_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:\${REDIS_PASSWORD}@redis:6379/0
      - REDIS_PASSWORD=\${REDIS_PASSWORD}
    depends_on:
      - redis
    command: uv run celery -A src.services.celery_app flower --port=5555 --broker=redis://:\${REDIS_PASSWORD}@redis:6379/0 --basic_auth=admin:\${FLOWER_PASSWORD}
    networks:
      - gaze_tracker_network

volumes:
  redis_data:
    driver: local
  batch_worker_pids:
    driver: local
  temp_frames:
    driver: local

networks:
  gaze_tracker_network:
    driver: bridge
EOF

    # Copy files to EC2
    scp -i "$PEM_KEY" -o StrictHostKeyChecking=no docker-compose.prod.yml "$EC2_USER@$EC2_HOST:/opt/$PROJECT_NAME/docker-compose.yml"
    
    # Start services on EC2
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/$PROJECT_NAME && REDIS_PASSWORD='$REDIS_PASSWORD' FLOWER_PASSWORD='$FLOWER_PASSWORD' DOCKER_REGISTRY='$DOCKER_REGISTRY' IMAGE_NAME='$IMAGE_NAME' IMAGE_TAG='$IMAGE_TAG' docker-compose up -d"
    
    log "Application deployed and started on EC2"
}

# Health check
health_check() {
    log "Performing health checks..."
    
    sleep 30  # Wait for services to start
    
    # Check API health
    if curl -f "http://$EC2_HOST:8002/api/v1/health" &> /dev/null; then
        log "✅ API health check passed"
    else
        warn "❌ API health check failed"
    fi
    
    # Check Flower
    if curl -f "http://$EC2_HOST:5555" &> /dev/null; then
        log "✅ Flower is accessible"
    else
        warn "❌ Flower is not accessible"
    fi
    
    log "Health checks completed"
}

# Show deployment info
show_deployment_info() {
    log "🎉 Deployment completed successfully!"
    echo ""
    echo "=== DEPLOYMENT INFORMATION ==="
    echo "🌐 API Endpoint: http://$EC2_HOST:8002"
    echo "📊 Flower Monitoring: http://$EC2_HOST:5555"
    echo "🔑 Flower Credentials: admin / $FLOWER_PASSWORD"
    echo "🔒 Redis Password: $REDIS_PASSWORD"
    echo "📝 Image Tag: $IMAGE_TAG"
    echo ""
    echo "=== USEFUL COMMANDS ==="
    echo "🔍 Check logs: ssh -i $PEM_KEY $EC2_USER@$EC2_HOST 'cd /opt/$PROJECT_NAME && docker-compose logs -f'"
    echo "🔄 Restart services: ssh -i $PEM_KEY $EC2_USER@$EC2_HOST 'cd /opt/$PROJECT_NAME && docker-compose restart'"
    echo "🛑 Stop services: ssh -i $PEM_KEY $EC2_USER@$EC2_HOST 'cd /opt/$PROJECT_NAME && docker-compose down'"
    echo "📊 Check status: ssh -i $PEM_KEY $EC2_USER@$EC2_HOST 'cd /opt/$PROJECT_NAME && docker-compose ps'"
    echo ""
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    rm -f ec2-setup.sh docker-compose.prod.yml
}

# Trap cleanup on exit
trap cleanup EXIT

# Main deployment function
deploy() {
    log "🚀 Starting EC2 deployment for Focus Tracker..."
    echo ""
    
    info "Deployment Configuration:"
    info "  EC2 Host: $EC2_HOST"
    info "  Region: $AWS_REGION"
    info "  Instance Type: t3.micro"
    info "  Image: $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
    echo ""
    
    check_prerequisites
    setup_ecr
    build_images
    push_images
    setup_ec2
    deploy_application
    health_check
    show_deployment_info
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "build-only")
        check_prerequisites
        setup_ecr
        build_images
        push_images
        log "Build and push completed. Use 'deploy' to deploy to EC2."
        ;;
    "setup-only")
        check_prerequisites
        setup_ec2
        log "EC2 setup completed. Use 'deploy' to deploy application."
        ;;
    "health")
        health_check
        ;;
    *)
        echo "Usage: $0 {deploy|build-only|setup-only|health}"
        echo "  deploy     - Full deployment (default)"
        echo "  build-only - Build and push images only"
        echo "  setup-only - Setup EC2 instance only"
        echo "  health     - Run health checks"
        exit 1
        ;;
esac
