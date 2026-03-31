#!/bin/bash

# EC2 Deployment Script for Focus Tracker (Docker Hub Version)
# This script builds Docker images locally and deploys to EC2 using Docker Hub

set -e

# EC2 Configuration
EC2_USER="ubuntu"
EC2_HOST="ec2-13-60-84-246.eu-north-1.compute.amazonaws.com"
EC2_IP="13.60.84.246"
PEM_KEY="./sgdp.pem"
AWS_REGION="eu-north-1"

# Docker Hub Configuration - CHANGE THIS
DOCKER_HUB_USERNAME="lhgrandgtr"
IMAGE_NAME="focus-tracker"
IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"
PROJECT_NAME="gaze-tracker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; exit 1; }
info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"; }

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed"
    fi
    
    # Check SSH
    if ! command -v ssh &> /dev/null; then
        error "SSH is not installed"
    fi
    
    # Check PEM key
    if [ ! -f "$PEM_KEY" ]; then
        error "PEM key file not found: $PEM_KEY"
    fi
    
    # Test SSH
    if ! ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$EC2_USER@$EC2_HOST" "echo 'SSH OK'" 2>/dev/null; then
        error "Cannot connect to EC2 instance"
    fi
    
    # Check Docker Hub username
    if [ "$DOCKER_HUB_USERNAME" = "your_dockerhub_username" ]; then
        warn "Please update DOCKER_HUB_USERNAME in the script"
        read -p "Enter your Docker Hub username: " DOCKER_HUB_USERNAME
        sed -i "s/DOCKER_HUB_USERNAME=\"your_dockerhub_username\"/DOCKER_HUB_USERNAME=\"$DOCKER_HUB_USERNAME\"/" "$0"
    fi
    
    log "Prerequisites check passed"
}

# Login to Docker Hub
login_docker_hub() {
    log "Logging into Docker Hub..."
    
    if ! docker info | grep -q "Username"; then
        echo "Please enter your Docker Hub credentials:"
        docker login
    else
        log "Already logged into Docker Hub"
    fi
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    docker build -t "$IMAGE_NAME:$IMAGE_TAG" .
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$DOCKER_HUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    
    log "Docker image built: $DOCKER_HUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
}

# Push images to Docker Hub
push_images() {
    log "Pushing Docker images to Docker Hub..."
    
    docker push "$DOCKER_HUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$DOCKER_HUB_USERNAME/$IMAGE_NAME:latest"
    docker push "$DOCKER_HUB_USERNAME/$IMAGE_NAME:latest"
    
    log "Images pushed to Docker Hub successfully"
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

# Clean up disk space to make room for Docker images
sudo apt-get autoremove -y
sudo apt-get clean
sudo docker system prune -af || true

# Fix potential Docker installation conflicts
sudo apt-get remove -y docker docker-engine docker.io containerd runc || true

# Install Docker using official repository
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ubuntu

# Install Docker Compose (standalone)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create directories
sudo mkdir -p /opt/$PROJECT_NAME
sudo chown ubuntu:ubuntu /opt/$PROJECT_NAME
mkdir -p /opt/$PROJECT_NAME/{logs,data,model,streams/subtasks,streams/sessions}

# Install tools
sudo apt-get install -y git htop curl

echo "EC2 setup completed"
EOF

    # Execute setup
    scp -i "$PEM_KEY" -o StrictHostKeyChecking=no ec2-setup.sh "$EC2_USER@$EC2_HOST:/tmp/"
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "chmod +x /tmp/ec2-setup.sh && /tmp/ec2-setup.sh"
    
    log "EC2 setup completed"
}

# Deploy application
deploy_application() {
    log "Deploying application to EC2..."
    
    # Create docker-compose file
    cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: gaze_tracker_redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --port 6379 --requirepass \${REDIS_PASSWORD}
    networks:
      - gaze_tracker_network

  api:
    image: $DOCKER_HUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG
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
      - ./streams:/app/streams
    depends_on:
      - redis
    networks:
      - gaze_tracker_network

  batch_worker_1:
    image: $DOCKER_HUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG
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
      - ./streams:/app/streams
    depends_on:
      - redis
      - api
    command: uv run celery -A src.services.batch_worker worker --loglevel=INFO --queues=batch_processing --concurrency=1 --hostname=batch_worker_1
    networks:
      - gaze_tracker_network

  batch_worker_2:
    image: $DOCKER_HUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG
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
      - ./streams:/app/streams
    depends_on:
      - redis
      - api
    command: uv run celery -A src.services.batch_worker worker --loglevel=INFO --queues=batch_processing --concurrency=1 --hostname=batch_worker_2
    networks:
      - gaze_tracker_network

  flower:
    image: $DOCKER_HUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG
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

networks:
  gaze_tracker_network:
    driver: bridge
EOF

    # Copy and deploy
    scp -i "$PEM_KEY" -o StrictHostKeyChecking=no docker-compose.prod.yml "$EC2_USER@$EC2_HOST:/opt/$PROJECT_NAME/docker-compose.yml"
    
    # Generate passwords
    REDIS_PASSWORD="redis_$(date +%s)"
    FLOWER_PASSWORD="flower_$(date +%s)"
    
    # Start services
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/$PROJECT_NAME && REDIS_PASSWORD='$REDIS_PASSWORD' FLOWER_PASSWORD='$FLOWER_PASSWORD' docker-compose up -d"
    
    log "Application deployed successfully"
    
    # Save credentials
    echo "REDIS_PASSWORD='$REDIS_PASSWORD'" > deployment-credentials.env
    echo "FLOWER_PASSWORD='$FLOWER_PASSWORD'" >> deployment-credentials.env
    echo "IMAGE_TAG='$IMAGE_TAG'" >> deployment-credentials.env
}

# Health check
health_check() {
    log "Performing health checks..."
    sleep 30
    
    if curl -f "http://$EC2_HOST:8002/api/v1/health" &> /dev/null; then
        log "✅ API health check passed"
    else
        warn "❌ API health check failed"
    fi
    
    if curl -f "http://$EC2_HOST:5555" &> /dev/null; then
        log "✅ Flower is accessible"
    else
        warn "❌ Flower is not accessible"
    fi
}

# Show deployment info
show_deployment_info() {
    log "🎉 Deployment completed successfully!"
    echo ""
    echo "=== DEPLOYMENT INFORMATION ==="
    echo "🌐 API Endpoint: http://$EC2_HOST:8002"
    echo "📊 Flower Monitoring: http://$EC2_HOST:5555"
    echo "🔑 Flower Credentials: admin / $(grep FLOWER_PASSWORD deployment-credentials.env | cut -d'=' -f2)"
    echo "🔒 Redis Password: $(grep REDIS_PASSWORD deployment-credentials.env | cut -d'=' -f2)"
    echo "📝 Image Tag: $(grep IMAGE_TAG deployment-credentials.env | cut -d'=' -f2)"
    echo "🐳 Docker Hub: $DOCKER_HUB_USERNAME/$IMAGE_NAME:$(grep IMAGE_TAG deployment-credentials.env | cut -d'=' -f2)"
    echo ""
    echo "=== USEFUL COMMANDS ==="
    echo "🔍 Check logs: ssh -i $PEM_KEY $EC2_USER@$EC2_HOST 'cd /opt/$PROJECT_NAME && docker-compose logs -f'"
    echo "🔄 Restart services: ssh -i $PEM_KEY $EC2_USER@$EC2_HOST 'cd /opt/$PROJECT_NAME && docker-compose restart'"
    echo "🛑 Stop services: ssh -i $PEM_KEY $EC2_USER@$EC2_HOST 'cd /opt/$PROJECT_NAME && docker-compose down'"
    echo ""
}

# Cleanup
cleanup() {
    rm -f ec2-setup.sh docker-compose.prod.yml
}

trap cleanup EXIT

# Main deployment
deploy() {
    log "🚀 Starting EC2 deployment (Docker Hub)..."
    check_prerequisites
    login_docker_hub
    build_images
    push_images
    setup_ec2
    deploy_application
    health_check
    show_deployment_info
}

# Run deployment
deploy "$@"
