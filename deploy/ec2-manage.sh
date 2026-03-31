#!/bin/bash

# EC2 Management Script
# Utility script for managing Focus Tracker on EC2

set -e

# Configuration
EC2_USER="ubuntu"
EC2_HOST="ec2-13-60-84-246.eu-north-1.compute.amazonaws.com"
PEM_KEY="./sgdp.pem"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check SSH connection
check_ssh() {
    if ! ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$EC2_USER@$EC2_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
        error "Cannot connect to EC2 instance via SSH"
        exit 1
    fi
}

# Show status
show_status() {
    log "📊 Checking service status..."
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && docker-compose ps"
}

# Show logs
show_logs() {
    local service=${1:-}
    if [ -z "$service" ]; then
        log "📝 Showing all logs (Ctrl+C to exit)..."
        ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && docker-compose logs -f"
    else
        log "📝 Showing logs for $service (Ctrl+C to exit)..."
        ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && docker-compose logs -f $service"
    fi
}

# Restart services
restart_services() {
    local service=${1:-}
    if [ -z "$service" ]; then
        log "🔄 Restarting all services..."
        ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && docker-compose restart"
    else
        log "🔄 Restarting service: $service"
        ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && docker-compose restart $service"
    fi
}

# Stop services
stop_services() {
    log "🛑 Stopping all services..."
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && docker-compose down"
}

# Start services
start_services() {
    log "▶️ Starting all services..."
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && docker-compose up -d"
}

# Update services
update_services() {
    log "🔄 Updating services..."
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && docker-compose pull && docker-compose up -d"
}

# Show resource usage
show_resources() {
    log "📈 Checking resource usage..."
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "echo '=== Docker Container Stats ===' && docker stats --no-stream && echo '=== System Resources ===' && free -h && echo '=== Disk Usage ===' && df -h"
}

# Health check
health_check() {
    log "🏥 Running health checks..."
    
    # Check API
    if curl -f -s "http://$EC2_HOST:8002/api/v1/health" > /dev/null; then
        log "✅ API: Healthy"
    else
        warn "❌ API: Unhealthy"
    fi
    
    # Check Flower
    if curl -f -s "http://$EC2_HOST:5555" > /dev/null; then
        log "✅ Flower: Accessible"
    else
        warn "❌ Flower: Not accessible"
    fi
    
    # Check Redis (via SSH)
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "docker exec gaze_tracker_redis redis-cli ping" > /dev/null 2>&1 && log "✅ Redis: Healthy" || warn "❌ Redis: Unhealthy"
}

# Backup data
backup_data() {
    local backup_name="backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    log "💾 Creating backup: $backup_name"
    
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && tar -czf $backup_name data/ logs/ && echo 'Backup created: $backup_name'"
    
    # Download backup
    log "📥 Downloading backup..."
    scp -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST:/opt/gaze-tracker/$backup_name" "./backups/"
    
    if [ $? -eq 0 ]; then
        log "✅ Backup completed and downloaded"
    else
        error "❌ Backup failed"
    fi
}

# Show credentials
show_credentials() {
    warn "🔐 Showing sensitive information..."
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && echo '=== Environment Variables ===' && cat .env | grep -E '(PASSWORD|TOKEN|KEY)' || echo 'No .env file found'"
}

# Clean up old images and containers
cleanup() {
    log "🧹 Cleaning up Docker resources..."
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "cd /opt/gaze-tracker && docker-compose down && docker system prune -f && docker-compose up -d"
}

# Access shell
access_shell() {
    log "🐚 Opening SSH shell to EC2..."
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST"
}

# Access container shell
access_container() {
    local container=${1:-api}
    log "🐚 Opening shell to container: $container"
    ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "docker exec -it gaze_tracker_$container /bin/bash"
}

# Show menu
show_menu() {
    echo ""
    echo "🎯 Focus Tracker EC2 Management Menu"
    echo "=================================="
    echo "1) Show service status"
    echo "2) Show logs (all)"
    echo "3) Show logs (specific service)"
    echo "4) Restart services (all)"
    echo "5) Restart service (specific)"
    echo "6) Stop services"
    echo "7) Start services"
    echo "8) Update services"
    echo "9) Show resource usage"
    echo "10) Health check"
    echo "11) Backup data"
    echo "12) Show credentials"
    echo "13) Cleanup Docker"
    echo "14) Access SSH shell"
    echo "15) Access container shell"
    echo "0) Exit"
    echo ""
}

# Main function
main() {
    check_ssh
    
    if [ $# -eq 0 ]; then
        # Interactive mode
        while true; do
            show_menu
            read -p "Enter your choice [0-15]: " choice
            case $choice in
                1) show_status ;;
                2) show_logs ;;
                3) read -p "Enter service name: " service && show_logs "$service" ;;
                4) restart_services ;;
                5) read -p "Enter service name: " service && restart_services "$service" ;;
                6) stop_services ;;
                7) start_services ;;
                8) update_services ;;
                9) show_resources ;;
                10) health_check ;;
                11) 
                    mkdir -p backups
                    backup_data 
                    ;;
                12) show_credentials ;;
                13) cleanup ;;
                14) access_shell ;;
                15) 
                    read -p "Enter container name (api/batch_worker_1/batch_worker_2/flower/redis): " container
                    access_container "$container"
                    ;;
                0) log "👋 Goodbye!" && exit 0 ;;
                *) warn "Invalid choice. Please try again." ;;
            esac
            echo ""
        done
    else
        # Command line mode
        case $1 in
            "status") show_status ;;
            "logs") show_logs "${2:-}" ;;
            "restart") restart_services "${2:-}" ;;
            "stop") stop_services ;;
            "start") start_services ;;
            "update") update_services ;;
            "resources") show_resources ;;
            "health") health_check ;;
            "backup") 
                mkdir -p backups
                backup_data 
                ;;
            "credentials") show_credentials ;;
            "cleanup") cleanup ;;
            "shell") access_shell ;;
            "container") access_container "${2:-api}" ;;
            *) 
                echo "Usage: $0 {status|logs|restart|stop|start|update|resources|health|backup|credentials|cleanup|shell|container}"
                echo "  status     - Show service status"
                echo "  logs       - Show logs (optional: service name)"
                echo "  restart    - Restart services (optional: service name)"
                echo "  stop       - Stop all services"
                echo "  start      - Start all services"
                echo "  update     - Update and restart services"
                echo "  resources  - Show resource usage"
                echo "  health     - Run health checks"
                echo "  backup     - Backup data"
                echo "  credentials- Show credentials"
                echo "  cleanup    - Clean up Docker resources"
                echo "  shell      - Access SSH shell"
                echo "  container  - Access container shell (default: api)"
                exit 1
                ;;
        esac
    fi
}

# Run main function
main "$@"
