#!/bin/bash

# BountyGo Backend Deployment Script
# 生产环境部署脚本

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/bountygo}"
LOG_FILE="${LOG_FILE:-/var/log/bountygo-deploy.log}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message"
            ;;
    esac
    
    # Also log to file if LOG_FILE is set
    if [[ -n "$LOG_FILE" ]]; then
        echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    fi
}

# Error handler
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log "WARN" "Running as root. Consider using a non-root user for deployment."
    fi
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed. Please install Docker first."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error_exit "Docker daemon is not running. Please start Docker first."
    fi
    
    # Check environment file
    if [[ ! -f "$PROJECT_ROOT/.env.prod" ]]; then
        error_exit "Production environment file (.env.prod) not found."
    fi
    
    log "INFO" "Prerequisites check passed."
}

# Validate configuration
validate_config() {
    log "INFO" "Validating configuration..."
    
    cd "$PROJECT_ROOT"
    
    # Run configuration validation script
    if [[ -f "scripts/validate_config.py" ]]; then
        python scripts/validate_config.py --env production || error_exit "Configuration validation failed."
    else
        log "WARN" "Configuration validation script not found. Skipping validation."
    fi
    
    log "INFO" "Configuration validation passed."
}

# Create backup
create_backup() {
    log "INFO" "Creating backup..."
    
    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/backup_$backup_timestamp"
    
    # Create backup directory
    mkdir -p "$backup_path"
    
    # Backup database
    if docker-compose -f "$COMPOSE_FILE" ps db | grep -q "Up"; then
        log "INFO" "Backing up database..."
        docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U bountygo bountygo > "$backup_path/database.sql" || {
            log "WARN" "Database backup failed, but continuing deployment..."
        }
    fi
    
    # Backup Redis data
    if docker-compose -f "$COMPOSE_FILE" ps redis | grep -q "Up"; then
        log "INFO" "Backing up Redis data..."
        docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli BGSAVE || {
            log "WARN" "Redis backup failed, but continuing deployment..."
        }
    fi
    
    # Backup application logs
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        cp -r "$PROJECT_ROOT/logs" "$backup_path/" || {
            log "WARN" "Log backup failed, but continuing deployment..."
        }
    fi
    
    log "INFO" "Backup created at: $backup_path"
}

# Build images
build_images() {
    log "INFO" "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build production image
    docker-compose -f "$COMPOSE_FILE" build --no-cache app || error_exit "Failed to build application image."
    
    log "INFO" "Docker images built successfully."
}

# Run database migrations
run_migrations() {
    log "INFO" "Running database migrations..."
    
    cd "$PROJECT_ROOT"
    
    # Start database service if not running
    docker-compose -f "$COMPOSE_FILE" up -d db redis
    
    # Wait for database to be ready
    log "INFO" "Waiting for database to be ready..."
    timeout=60
    while ! docker-compose -f "$COMPOSE_FILE" exec -T db pg_isready -U bountygo -d bountygo; do
        sleep 2
        timeout=$((timeout - 2))
        if [[ $timeout -le 0 ]]; then
            error_exit "Database failed to start within timeout."
        fi
    done
    
    # Run migrations
    docker-compose -f "$COMPOSE_FILE" run --rm app alembic upgrade head || error_exit "Database migration failed."
    
    log "INFO" "Database migrations completed."
}

# Deploy application
deploy_application() {
    log "INFO" "Deploying application..."
    
    cd "$PROJECT_ROOT"
    
    # Stop existing services
    log "INFO" "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans
    
    # Start services
    log "INFO" "Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for application to be ready
    log "INFO" "Waiting for application to be ready..."
    timeout=120
    while ! curl -f http://localhost:8000/health &> /dev/null; do
        sleep 5
        timeout=$((timeout - 5))
        if [[ $timeout -le 0 ]]; then
            error_exit "Application failed to start within timeout."
        fi
    done
    
    log "INFO" "Application deployed successfully."
}

# Health check
health_check() {
    log "INFO" "Performing health check..."
    
    cd "$PROJECT_ROOT"
    
    # Check all services
    local services=("db" "redis" "app")
    
    for service in "${services[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            log "INFO" "Service $service is running."
        else
            error_exit "Service $service is not running."
        fi
    done
    
    # Check application endpoints
    local endpoints=("/health" "/api/v1/health")
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f "http://localhost:8000$endpoint" &> /dev/null; then
            log "INFO" "Endpoint $endpoint is responding."
        else
            log "WARN" "Endpoint $endpoint is not responding."
        fi
    done
    
    log "INFO" "Health check completed."
}

# Cleanup old images and containers
cleanup() {
    log "INFO" "Cleaning up old images and containers..."
    
    # Remove unused images
    docker image prune -f || log "WARN" "Failed to prune images."
    
    # Remove unused containers
    docker container prune -f || log "WARN" "Failed to prune containers."
    
    # Remove unused volumes (be careful with this)
    # docker volume prune -f || log "WARN" "Failed to prune volumes."
    
    log "INFO" "Cleanup completed."
}

# Show deployment status
show_status() {
    log "INFO" "Deployment Status:"
    echo "===================="
    
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    log "INFO" "Application URLs:"
    echo "  - Application: http://localhost:8000"
    echo "  - Health Check: http://localhost:8000/health"
    echo "  - API Documentation: http://localhost:8000/docs"
    
    echo ""
    log "INFO" "Useful Commands:"
    echo "  - View logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  - Stop services: docker-compose -f $COMPOSE_FILE down"
    echo "  - Restart services: docker-compose -f $COMPOSE_FILE restart"
}

# Rollback function
rollback() {
    log "INFO" "Rolling back deployment..."
    
    cd "$PROJECT_ROOT"
    
    # Stop current services
    docker-compose -f "$COMPOSE_FILE" down
    
    # Find latest backup
    local latest_backup=$(ls -t "$BACKUP_DIR" | head -n1)
    
    if [[ -n "$latest_backup" && -d "$BACKUP_DIR/$latest_backup" ]]; then
        log "INFO" "Restoring from backup: $latest_backup"
        
        # Restore database if backup exists
        if [[ -f "$BACKUP_DIR/$latest_backup/database.sql" ]]; then
            docker-compose -f "$COMPOSE_FILE" up -d db
            sleep 10
            docker-compose -f "$COMPOSE_FILE" exec -T db psql -U bountygo -d bountygo < "$BACKUP_DIR/$latest_backup/database.sql"
        fi
        
        log "INFO" "Rollback completed."
    else
        log "ERROR" "No backup found for rollback."
    fi
}

# Main deployment function
main() {
    local action="${1:-deploy}"
    
    log "INFO" "Starting BountyGo deployment process..."
    log "INFO" "Environment: $ENVIRONMENT"
    log "INFO" "Compose file: $COMPOSE_FILE"
    log "INFO" "Action: $action"
    
    case $action in
        "deploy")
            check_root
            check_prerequisites
            validate_config
            create_backup
            build_images
            run_migrations
            deploy_application
            health_check
            cleanup
            show_status
            log "INFO" "Deployment completed successfully!"
            ;;
        "rollback")
            rollback
            ;;
        "health")
            health_check
            ;;
        "status")
            show_status
            ;;
        "backup")
            create_backup
            ;;
        "cleanup")
            cleanup
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|health|status|backup|cleanup}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Full deployment process (default)"
            echo "  rollback - Rollback to previous version"
            echo "  health   - Perform health check"
            echo "  status   - Show deployment status"
            echo "  backup   - Create backup only"
            echo "  cleanup  - Cleanup old images and containers"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"