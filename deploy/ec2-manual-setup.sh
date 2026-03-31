#!/bin/bash

# EC2 Instance Setup Script
# Run this script manually on EC2 instance if automated setup fails

set -e

echo "🔧 Setting up Focus Tracker on EC2 instance..."

# Update system
sudo apt-get update -y

# Install Docker
echo "📦 Installing Docker..."
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ubuntu

# Install Docker Compose
echo "📦 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Create application directory
echo "📁 Creating application directory..."
sudo mkdir -p /opt/gaze-tracker
sudo chown ubuntu:ubuntu /opt/gaze-tracker

# Create subdirectories
mkdir -p /opt/gaze-tracker/{logs,data,model,streams/subtasks,streams/sessions}

# Install additional tools
echo "🛠️ Installing additional tools..."
sudo apt-get install -y git htop curl wget

# Configure firewall (if active)
echo "🔥 Configuring firewall..."
if sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 8002/tcp
    sudo ufw allow 5555/tcp
    sudo ufw reload
fi

# Create environment file template
echo "📝 Creating environment file template..."
cat > /opt/gaze-tracker/.env << 'EOF'
# Redis Configuration
REDIS_PASSWORD=your_secure_redis_password_here

# Flower Configuration
FLOWER_PASSWORD=your_secure_flower_password_here

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO

# AWS Configuration (if needed)
AWS_REGION=eu-north-1

# Performance Tuning for t3.micro
WORKER_CONCURRENCY=1
MAX_REALISTIC_FOCUS_SCORE=95.0
HIGH_FOCUS_THRESHOLD=85.0
FOCUS_BUFFER_SIZE=50
EOF

echo "✅ EC2 setup completed!"
echo ""
echo "📝 Next steps:"
echo "1. Edit /opt/gaze-tracker/.env with your passwords"
echo "2. Copy docker-compose.yml to /opt/gaze-tracker/"
echo "3. Run: cd /opt/gaze-tracker && docker-compose up -d"
echo ""
echo "🔧 Useful commands:"
echo "  Check Docker status: sudo systemctl status docker"
echo "  View logs: journalctl -u docker"
echo "  Test Docker: docker run hello-world"
