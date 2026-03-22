#!/bin/bash

# AWS ECS Deployment Script for Focus Tracker
# This script deploys the Focus Tracker system to AWS ECS

set -e

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="focus-tracker"
CLUSTER_NAME="focus-tracker-cluster"
SERVICE_NAME="focus-tracker-service"
TASK_FAMILY="focus-tracker-task"

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
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed. Please install it first."
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install it first."
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured. Please run 'aws configure'."
    fi
    
    log "Prerequisites check passed"
}

# Create ECR repository
create_ecr_repository() {
    log "Creating ECR repository..."
    
    if aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" --region "$AWS_REGION" 2>/dev/null; then
        log "ECR repository already exists"
    else
        aws ecr create-repository --repository-name "$ECR_REPOSITORY" --region "$AWS_REGION"
        log "ECR repository created"
    fi
}

# Build and push Docker image
build_and_push_image() {
    log "Building Docker image..."
    
    # Get ECR login password
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com"
    
    # Build image
    IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"
    ECR_IMAGE_URI="$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
    
    docker build -t "$ECR_REPOSITORY:$IMAGE_TAG" .
    docker tag "$ECR_REPOSITORY:$IMAGE_TAG" "$ECR_IMAGE_URI"
    
    log "Pushing Docker image to ECR..."
    docker push "$ECR_IMAGE_URI"
    
    # Store image URI for later use
    echo "$ECR_IMAGE_URI" > .ecr_image_uri
    log "Docker image pushed: $ECR_IMAGE_URI"
}

# Create ECS cluster
create_ecs_cluster() {
    log "Creating ECS cluster..."
    
    if aws ecs describe-clusters --clusters "$CLUSTER_NAME" --region "$AWS_REGION" 2>/dev/null | grep -q "$CLUSTER_NAME"; then
        log "ECS cluster already exists"
    else
        aws ecs create-cluster --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
        log "ECS cluster created"
    fi
}

# Create task definition
create_task_definition() {
    log "Creating ECS task definition..."
    
    ECR_IMAGE_URI=$(cat .ecr_image_uri)
    
    # Read task definition template and substitute variables
    cat > task-definition.json <<EOF
{
    "family": "$TASK_FAMILY",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "2048",
    "memory": "4096",
    "executionRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsTaskRole",
    "containerDefinitions": [
        {
            "name": "focus-tracker-api",
            "image": "$ECR_IMAGE_URI",
            "portMappings": [
                {
                    "containerPort": 8002,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {
                    "name": "REDIS_URL",
                    "value": "redis://your-redis-endpoint:6379/0"
                },
                {
                    "name": "CELERY_BROKER_URL",
                    "value": "redis://your-redis-endpoint:6379/0"
                },
                {
                    "name": "CELERY_RESULT_BACKEND",
                    "value": "redis://your-redis-endpoint:6379/0"
                },
                {
                    "name": "ENVIRONMENT",
                    "value": "production"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/focus-tracker",
                    "awslogs-region": "$AWS_REGION",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8002/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
    ]
}
EOF
    
    # Register task definition
    aws ecs register-task-definition --cli-input-json file://task-definition.json --region "$AWS_REGION"
    log "Task definition created"
}

# Create ECS service
create_ecs_service() {
    log "Creating ECS service..."
    
    # Get VPC and subnets
    VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --region "$AWS_REGION" --query "Vpcs[0].VpcId" --output text)
    SUBNETS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC_ID" --region "$AWS_REGION" --query "Subnets[?MapPublicIpOnLaunch].SubnetId" --output text | tr '\t' ',')
    
    # Get security group
    SG_ID=$(aws ec2 create-security-group --group-name "focus-tracker-sg" --description "Security group for Focus Tracker" --vpc-id "$VPC_ID" --region "$AWS_REGION" --query "GroupId" --output text 2>/dev/null || echo "")
    
    if [ -z "$SG_ID" ]; then
        SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values="focus-tracker-sg" --region "$AWS_REGION" --query "SecurityGroups[0].GroupId" --output text)
    fi
    
    # Add security group rules
    aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 8002 --cidr 0.0.0.0/0 --region "$AWS_REGION" || true
    
    # Create service
    if aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" --region "$AWS_REGION" 2>/dev/null | grep -q "$SERVICE_NAME"; then
        log "ECS service already exists, updating..."
        aws ecs update-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" --task-definition "$TASK_FAMILY" --desired-count 2 --region "$AWS_REGION"
    else
        aws ecs create-service \
            --cluster "$CLUSTER_NAME" \
            --service-name "$SERVICE_NAME" \
            --task-definition "$TASK_FAMILY" \
            --desired-count 2 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
            --region "$AWS_REGION"
        log "ECS service created"
    fi
}

# Create Application Load Balancer
create_load_balancer() {
    log "Creating Application Load Balancer..."
    
    # Create target group
    TG_ARN=$(aws elbv2 create-target-group \
        --name "focus-tracker-tg" \
        --protocol HTTP \
        --port 8002 \
        --vpc-id "$VPC_ID" \
        --target-type ip \
        --health-check-protocol HTTP \
        --health-check-port 8002 \
        --health-check-path /health \
        --region "$AWS_REGION" \
        --query "TargetGroups[0].TargetGroupArn" --output text)
    
    # Create load balancer
    LB_ARN=$(aws elbv2 create-load-balancer \
        --name "focus-tracker-lb" \
        --subnets $SUBNETS \
        --security-groups "$SG_ID" \
        --region "$AWS_REGION" \
        --query "LoadBalancers[0].LoadBalancerArn" --output text)
    
    # Wait for LB to be active
    aws elbv2 wait load-balancer-available --load-balancer-arns "$LB_ARN" --region "$AWS_REGION"
    
    # Create listener
    aws elbv2 create-listener \
        --load-balancer-arn "$LB_ARN" \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
        --region "$AWS_REGION"
    
    log "Load Balancer created"
    
    # Get LB DNS name
    LB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns "$LB_ARN" --region "$AWS_REGION" --query "LoadBalancers[0].DNSName" --output text)
    echo "Load Balancer DNS: $LB_DNS"
}

# Main deployment function
deploy() {
    log "Starting AWS ECS deployment..."
    
    check_prerequisites
    create_ecr_repository
    build_and_push_image
    create_ecs_cluster
    create_task_definition
    create_ecs_service
    create_load_balancer
    
    log "Deployment completed successfully!"
    log "Your application is now running on AWS ECS"
    log "Access it via the Load Balancer DNS name shown above"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    rm -f task-definition.json .ecr_image_uri
}

# Trap cleanup on exit
trap cleanup EXIT

# Run deployment
deploy "$@"
