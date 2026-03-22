# 🚀 Focus Tracker Cloud Deployment Guide

This guide provides comprehensive instructions for deploying the Focus Tracker system to major cloud providers with full batch processing capabilities.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Options](#deployment-options)
3. [AWS ECS Deployment](#aws-ecs-deployment)
4. [Google Cloud Run Deployment](#google-cloud-run-deployment)
5. [Azure Container Instances Deployment](#azure-container-instances-deployment)
6. [Docker Compose (Local/Single VM)](#docker-compose-local-single-vm)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### Required Tools
- **Docker** (v20.10+)
- **Docker Compose** (v2.0+)
- **Cloud CLI**:
  - AWS: `aws-cli`
  - Google Cloud: `gcloud`
  - Azure: `azure-cli`

### System Requirements
- **Minimum**: 4 CPU cores, 8GB RAM, 50GB storage
- **Recommended**: 8 CPU cores, 16GB RAM, 100GB storage
- **Network**: Internet connectivity for container registry access

### Authentication Setup
```bash
# AWS
aws configure

# Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Azure
az login
```

## 🌩️ Deployment Options

### 1. AWS ECS (Recommended for Production)
- **Pros**: Scalable, managed, load balancing, auto-scaling
- **Cons**: More complex setup, higher cost
- **Best for**: Production workloads with variable traffic

### 2. Google Cloud Run (Recommended for Simplicity)
- **Pros**: Serverless, auto-scaling, pay-per-use, simple
- **Cons**: Cold starts, limited customization
- **Best for**: Small to medium workloads, cost optimization

### 3. Azure Container Instances (Recommended for Hybrid)
- **Pros**: Simple, fast deployment, integrated with Azure
- **Cons**: Limited scalability, higher per-unit cost
- **Best for**: Azure environments, quick deployments

### 4. Docker Compose (Development/Testing)
- **Pros**: Simple, local development, full control
- **Cons**: Manual scaling, single-server limitation
- **Best for**: Development, testing, single-server deployments

## 🟰 AWS ECS Deployment

### Quick Start
```bash
# Make the script executable
chmod +x deploy/aws-deploy.sh

# Run deployment
./deploy/aws-deploy.sh
```

### Detailed Steps

1. **Prerequisites Setup**
   ```bash
   # Install AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   
   # Configure credentials
   aws configure
   ```

2. **IAM Roles Required**
   - `ecsTaskExecutionRole`: For ECS task execution
   - `ecsTaskRole`: For application permissions
   - CloudWatch Logs permissions
   - ECR pull permissions

3. **Network Configuration**
   - VPC with public subnets
   - Security groups for API (port 8002) and Redis
   - Application Load Balancer for external access

4. **Redis Setup**
   ```bash
   # Create ElastiCache Redis cluster
   aws elasticache create-replication-group \
     --replication-group-id focus-tracker-redis \
     --description "Focus Tracker Redis" \
     --num-cache-clusters 2 \
     --cache-node-type cache.t3.micro \
     --engine redis \
     --engine-version 6.x
   ```

5. **Environment Variables**
   - `REDIS_URL`: Redis connection string
   - `CELERY_BROKER_URL`: Celery broker URL
   - `CELERY_RESULT_BACKEND`: Celery result backend
   - `ENVIRONMENT=production`

### Post-Deployment
```bash
# Check service status
aws ecs describe-services --cluster focus-tracker-cluster --services focus-tracker-service

# View logs
aws logs tail /ecs/focus-tracker --follow

# Access application
curl http://your-load-balancer-dns/health
```

## 🟡 Google Cloud Run Deployment

### Quick Start
```bash
# Make the script executable
chmod +x deploy/gcp-deploy.sh

# Run deployment
./gcp-deploy.sh
```

### Detailed Steps

1. **Project Setup**
   ```bash
   # Create new project (optional)
   gcloud projects create focus-tracker-prod
   
   # Set project
   gcloud config set project focus-tracker-prod
   ```

2. **Enable APIs**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable redis.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   ```

3. **Redis Configuration**
   ```bash
   # Create Memorystore Redis instance
   gcloud redis instances create focus-tracker-redis \
     --region=us-central1 \
     --size=2 \
     --tier=standard
   ```

4. **Artifact Registry**
   ```bash
   # Create repository
   gcloud artifacts repositories create focus-tracker \
     --repository-format=docker \
     --location=us-central1
   ```

5. **Deployment Configuration**
   - Memory: 4Gi per instance
   - CPU: 2 vCPU per instance
   - Concurrency: 10 requests
   - Timeout: 300s (5 minutes)

### Post-Deployment
```bash
# Get service URL
gcloud run services describe focus-tracker --region=us-central1

# View logs
gcloud logs tail "projects/PROJECT_ID/logs/run.googleapis.com%2Fstdout"

# Scale service
gcloud run services update focus-tracker --region=us-central1 --max-instances=10
```

## 🔵 Azure Container Instances Deployment

### Quick Start
```bash
# Make the script executable
chmod +x deploy/azure-deploy.sh

# Run deployment
./azure-deploy.sh
```

### Detailed Steps

1. **Resource Group**
   ```bash
   az group create --name focus-tracker-rg --location eastus
   ```

2. **Container Registry**
   ```bash
   az acr create --resource-group focus-tracker-rg --name focustrackerregistry --sku Basic
   ```

3. **Redis Cache**
   ```bash
   az redis create \
     --name focus-tracker-redis \
     --resource-group focus-tracker-rg \
     --location eastus \
     --sku Basic \
     --vm-size C0
   ```

4. **Container Configuration**
   - CPU: 2 cores
   - Memory: 4GB
   - Ports: 8002 (API)
   - Restart policy: Always

### Post-Deployment
```bash
# Get container IP
az container show --resource-group focus-tracker-rg --name focus-tracker-app

# View logs
az container logs --resource-group focus-tracker-rg --name focus-tracker-app

# Restart container
az container restart --resource-group focus-tracker-rg --name focus-tracker-app
```

## 🐳 Docker Compose (Local/Single VM)

### Development Setup
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Setup
```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale batch_worker_1=3 --scale batch_worker_2=3

# Update services
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Configuration Files
- `docker-compose.yml`: Development configuration
- `docker-compose.prod.yml`: Production configuration
- `nginx.conf`: Nginx reverse proxy configuration
- `redis.conf`: Redis production configuration

## 📊 Monitoring and Maintenance

### Health Checks
```bash
# API Health
curl http://localhost:8002/health

# Redis Health
redis-cli -h localhost -p 6380 ping

# Worker Status
curl http://localhost:5555  # Flower dashboard
```

### Log Management
```bash
# View API logs
docker-compose logs api

# View worker logs
docker-compose logs batch_worker_1

# View Redis logs
docker-compose logs redis
```

### Performance Monitoring
- **Flower**: Celery task monitoring (port 5555)
- **Redis Commander**: Redis GUI (port 8081)
- **Application logs**: Structured JSON logging
- **Cloud monitoring**: AWS CloudWatch, GCP Cloud Monitoring, Azure Monitor

### Backup and Recovery
```bash
# Redis backup
redis-cli --rdb /backup/redis-$(date +%Y%m%d).rdb

# Application data backup
tar -czf backup-$(date +%Y%m%d).tar.gz data/ logs/

# Restore
docker-compose down
tar -xzf backup-$(date +%Y%m%d).tar.gz
docker-compose up -d
```

## 🔧 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis status
   docker-compose ps redis
   
   # Test connection
   redis-cli -h localhost -p 6380 ping
   
   # View Redis logs
   docker-compose logs redis
   ```

2. **Batch Workers Not Processing**
   ```bash
   # Check worker status
   curl http://localhost:5555
   
   # Restart workers
   docker-compose restart batch_worker_1 batch_worker_2
   
   # Check queue
   redis-cli -h localhost -p 6380 llen celery
   ```

3. **API Not Responding**
   ```bash
   # Check API logs
   docker-compose logs api
   
   # Restart API
   docker-compose restart api
   
   # Check port
   netstat -tlnp | grep 8002
   ```

4. **Memory Issues**
   ```bash
   # Check memory usage
   docker stats
   
   # Clear Redis memory
   redis-cli -h localhost -p 6380 flushall
   
   # Restart services
   docker-compose restart
   ```

### Performance Optimization

1. **Redis Optimization**
   - Enable AOF persistence
   - Configure maxmemory policy
   - Use Redis Cluster for high load

2. **Worker Optimization**
   - Adjust concurrency based on CPU cores
   - Monitor task queue length
   - Scale workers horizontally

3. **API Optimization**
   - Enable gzip compression
   - Use connection pooling
   - Implement rate limiting

### Security Considerations

1. **Network Security**
   - Use VPC/private networks
   - Implement firewalls
   - Enable SSL/TLS

2. **Authentication**
   - Configure API keys
   - Use IAM roles
   - Enable RBAC

3. **Data Protection**
   - Encrypt sensitive data
   - Use secure Redis configuration
   - Regular security updates

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Google Cloud Run Documentation](https://cloud.google.com/run)
- [Azure Container Instances Documentation](https://docs.microsoft.com/en-us/azure/container-instances/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)

## 🆘 Support

For deployment issues:
1. Check the troubleshooting section above
2. Review service logs
3. Verify cloud provider configurations
4. Check network connectivity
5. Validate environment variables

For additional support, create an issue in the project repository with:
- Deployment method used
- Error messages/logs
- Configuration details
- Environment information
