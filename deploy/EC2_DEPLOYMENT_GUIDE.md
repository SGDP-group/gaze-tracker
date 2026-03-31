# EC2 Deployment Guide for Focus Tracker

## Overview
This guide deploys the Focus Tracker system to your EC2 t3.micro instance in eu-north-1 using Docker containers.

## Prerequisites

### Local Machine
- AWS CLI installed and configured
- Docker installed
- SSH client
- PEM key file (`sgdp_focus_agent.pem`)

### EC2 Instance Requirements
Your instance is already configured with:
- **Instance Type**: t3.micro (1 vCPU, 1GB RAM)
- **Region**: eu-north-1
- **Public IP**: 13.60.232.154
- **Public DNS**: ec2-13-60-232-154.eu-north-1.compute.amazonaws.com

### Security Group Configuration
Ensure your EC2 security group allows inbound traffic on:
- **Port 22**: SSH (from your IP)
- **Port 8002**: API server (from 0.0.0.0/0)
- **Port 5555**: Flower monitoring (from your IP for security)
- **Port 6379**: Redis (from localhost only, secured with password)

## Quick Deployment

### 1. Make Scripts Executable
```bash
chmod +x deploy/ec2-deploy.sh
chmod +x deploy/ec2-manual-setup.sh
```

### 2. Run Automated Deployment
```bash
./deploy/ec2-deploy.sh deploy
```

This will:
- Build Docker images locally
- Push to AWS ECR
- Setup EC2 instance with Docker
- Deploy all services
- Run health checks

## Manual Deployment (if automated fails)

### 1. Setup EC2 Instance Manually
```bash
# Copy setup script to EC2
scp -i sgdp_focus_agent.pem deploy/ec2-manual-setup.sh ec2-user@ec2-13-60-232-154.eu-north-1.compute.amazonaws.com:/tmp/

# SSH and run setup
ssh -i sgdp_focus_agent.pem ec2-user@ec2-13-60-232-154.eu-north-1.compute.amazonaws.com
chmod +x /tmp/ec2-manual-setup.sh
/tmp/ec2-manual-setup.sh
```

### 2. Build and Push Images Locally
```bash
# Set environment
export AWS_REGION=eu-north-1
export DOCKER_REGISTRY="937991583559.dkr.ecr.eu-north-1.amazonaws.com"
export IMAGE_NAME="focus-tracker"
export IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $DOCKER_REGISTRY

# Build and push
docker build -t $IMAGE_NAME:$IMAGE_TAG .
docker tag $IMAGE_NAME:$IMAGE_TAG $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
docker tag $IMAGE_NAME:$IMAGE_TAG $DOCKER_REGISTRY/$IMAGE_NAME:latest
docker push $DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG
docker push $DOCKER_REGISTRY/$IMAGE_NAME:latest
```

### 3. Deploy to EC2
```bash
# Create environment file on EC2
ssh -i sgdp_focus_agent.pem ec2-user@ec2-13-60-232-154.eu-north-1.compute.amazonaws.com "cat > /opt/gaze-tracker/.env << 'EOF'
REDIS_PASSWORD=redis_secure_password_$(date +%s)
FLOWER_PASSWORD=flower_admin_$(date +%s)
DOCKER_REGISTRY=$DOCKER_REGISTRY
IMAGE_NAME=$IMAGE_NAME
IMAGE_TAG=$IMAGE_TAG
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF"

# Copy docker-compose file
scp -i sgdp_focus_agent.pem deploy/docker-compose.ec2.yml ec2-user@ec2-13-60-232-154.eu-north-1.compute.amazonaws.com:/opt/gaze-tracker/docker-compose.yml

# Start services
ssh -i sgdp_focus_agent.pem ec2-user@ec2-13-60-232-154.eu-north-1.compute.amazonaws.com "cd /opt/gaze-tracker && docker-compose up -d"
```

## Access Your Application

After deployment, your services will be available at:

- **🌐 API Server**: http://13.60.232.154:8002
- **📊 Flower Monitoring**: http://13.60.232.154:5555
- **📖 API Documentation**: http://13.60.232.154:8002/docs

### Health Check Endpoints
- API Health: http://13.60.232.154:8002/api/v1/health
- Focus Health: http://13.60.232.154:8002/api/v1/focus/health
- Stream Stats: http://13.60.232.154:8002/api/v1/stream/stats

## Management Commands

###SSH into EC2
```bash
ssh -i sgdp_focus_agent.pem ec2-user@ec2-13-60-232-154.eu-north-1.compute.amazonaws.com
```

### Docker Management (on EC2)
```bash
# View running containers
cd /opt/gaze-tracker && docker-compose ps

# View logs
cd /opt/gaze-tracker && docker-compose logs -f

# View specific service logs
cd /opt/gaze-tracker && docker-compose logs -f api
cd /opt/gaze-tracker && docker-compose logs -f batch_worker_1

# Restart services
cd /opt/gaze-tracker && docker-compose restart

# Stop all services
cd /opt/gaze-tracker && docker-compose down

# Update and restart
cd /opt/gaze-tracker && docker-compose pull && docker-compose up -d
```

### Monitoring
```bash
# Check system resources
htop
df -h

# Check Docker logs
sudo journalctl -u docker

# Check container resource usage
docker stats
```

## Performance Tuning for t3.micro

The deployment is optimized for t3.micro constraints:

### Resource Limits
- **API Server**: 512MB RAM, 0.5 CPU
- **Batch Workers**: 256MB RAM, 0.25 CPU each
- **Flower**: 128MB RAM, 0.25 CPU
- **Redis**: Minimal footprint with password protection

### Application Settings
- Worker concurrency: 1 (per worker)
- Focus buffer size: 50 (reduced from 100)
- Max realistic focus score: 95.0
- High focus threshold: 85.0

## Security Considerations

### Redis Security
- Password protected with auto-generated password
- Only accessible from localhost
- Not exposed to public internet

### Flower Security
- Basic authentication with auto-generated password
- Consider restricting access to your IP only

### API Security
- Uses port 8002 (non-standard)
- Consider adding API key authentication for production
- Monitor logs for unauthorized access

## Troubleshooting

### Common Issues

1. **Out of Memory on t3.micro**
   ```bash
   # Check memory usage
   free -h
   docker stats
   
   # Reduce worker concurrency if needed
   # Edit docker-compose.ec2.yml and set WORKER_CONCURRENCY=0
   ```

2. **Docker Build Fails**
   ```bash
   # Ensure enough disk space
   df -h
   
   # Clean Docker cache
   docker system prune -a
   ```

3. **Services Not Starting**
   ```bash
   # Check logs
   cd /opt/gaze-tracker && docker-compose logs
   
   # Check Docker daemon
   sudo systemctl status docker
   ```

4. **Cannot Access Services**
   ```bash
   # Check security group rules
   # Ensure ports 8002 and 5555 are open
   
   # Check if services are running
   cd /opt/gaze-tracker && docker-compose ps
   ```

### Performance Monitoring

```bash
# Monitor resource usage
watch -n 2 'free -h && echo "---" && df -h'

# Monitor Docker containers
watch -n 2 'docker stats --no-stream'

# Monitor application logs
cd /opt/gaze-tracker && docker-compose logs -f
```

## Scaling Considerations

### When to Upgrade from t3.micro
- Consistent high memory usage (>80%)
- Slow batch processing
- Frequent OOM errors

### Recommended Upgrade Path
- **t3.small**: Better for moderate load
- **t3.medium**: Good for production with multiple users
- **t3.large**: High-load production

### Scaling Configuration
For larger instances, update `docker-compose.ec2.yml`:
- Increase memory limits
- Add more batch workers
- Enable Nginx reverse proxy
- Add SSL termination

## Backup and Recovery

### Data Backup
```bash
# Backup application data
ssh -i sgdp_focus_agent.pem ec2-user@ec2-13-60-232-154.eu-north-1.compute.amazonaws.com "cd /opt/gaze-tracker && tar -czf backup-$(date +%Y%m%d).tar.gz data/ logs/"

# Download backup
scp -i sgdp_focus_agent.pem ec2-user@ec2-13-60-232-154.eu-north-1.compute.amazonaws.com:/opt/gaze-tracker/backup-*.tar.gz ./
```

### Recovery
```bash
# Upload backup to new instance
scp -i sgdp_focus_agent.pem backup-*.tar.gz ec2-user@new-instance:/opt/gaze-tracker/

# Restore on new instance
ssh -i sgdp_focus_agent.pem ec2-user@new-instance "cd /opt/gaze-tracker && tar -xzf backup-*.tar.gz"
```

## Next Steps

1. **Monitor Performance**: Use Flower and system monitoring
2. **Set Up Alerts**: Configure CloudWatch alerts for critical metrics
3. **Add SSL**: Set up Nginx with Let's Encrypt for HTTPS
4. **Database Backup**: Configure automated backups
5. **Log Aggregation**: Set up centralized logging

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Verify resources: `free -h` and `df -h`
3. Test connectivity: `curl http://localhost:8002/api/v1/health`
4. Review this guide and troubleshooting section
