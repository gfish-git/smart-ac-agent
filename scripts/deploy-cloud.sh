#!/bin/bash
# Cloud deployment script for Smart AC Agent

set -e

echo "🚀 Deploying Smart AC Agent to GCP Cloud..."

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    if [ ! -f .env ]; then
        log_error ".env file not found. Please create one based on .env.example"
        exit 1
    fi
}

# Load environment variables
load_env() {
    log_info "Loading environment variables..."
    set -a
    source .env
    set +a
    
    # Set deployment mode
    export DEPLOYMENT_MODE=cloud
    
    # Validate required variables
    if [ -z "$IFTTT_KEY" ] || [ "$IFTTT_KEY" = "your_ifttt_webhook_key_here" ]; then
        log_error "IFTTT_KEY not configured in .env"
        exit 1
    fi
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        log_error "OPENAI_API_KEY not configured in .env"
        exit 1
    fi
    
    if [ -z "$HOME_LAT" ] || [ -z "$HOME_LON" ]; then
        log_error "HOME_LAT and HOME_LON must be configured in .env"
        exit 1
    fi
}

# Setup directories
setup_directories() {
    log_info "Setting up directories..."
    
    mkdir -p homeassistant
    mkdir -p caddy
    mkdir -p monitoring
    mkdir -p logs
    
    # Create Caddy directories
    mkdir -p caddy/logs
    
    # Create monitoring directories
    mkdir -p monitoring/prometheus
    mkdir -p monitoring/grafana
}

# Test IFTTT connectivity
test_ifttt() {
    log_info "Testing IFTTT connectivity..."
    
    local test_event="${IFTTT_AC_ON_EVENT:-ac_on}"
    local url="https://maker.ifttt.com/trigger/${test_event}/with/key/${IFTTT_KEY}"
    
    if curl -s -f -X POST "$url" > /dev/null; then
        log_info "✅ IFTTT webhook test successful"
    else
        log_warn "⚠️  IFTTT webhook test failed. Please check your configuration"
    fi
}

# Deploy services
deploy_services() {
    log_info "Deploying services..."
    
    # Stop existing services
    docker-compose -f docker-compose.cloud.yml --profile cloud down 2>/dev/null || true
    
    # Build and start services
    docker-compose -f docker-compose.cloud.yml --profile cloud up -d --build
    
    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 30
}

# Health checks
health_checks() {
    log_info "Performing health checks..."
    
    # Check Home Assistant
    local ha_url="http://localhost:8123"
    if [ -n "$EXTERNAL_URL" ]; then
        ha_url="$EXTERNAL_URL"
    fi
    
    for i in {1..10}; do
        if curl -s -f "$ha_url/api/" > /dev/null; then
            log_info "✅ Home Assistant is healthy"
            break
        else
            log_warn "⏳ Home Assistant not ready, attempt $i/10"
            sleep 10
        fi
    done
    
    # Check AC Agent
    local agent_url="http://localhost:8000"
    if [ -n "$WEBHOOK_URL" ]; then
        agent_url="${WEBHOOK_URL%/ping}"
    fi
    
    for i in {1..5}; do
        if curl -s -f "$agent_url/ping" -X POST -H "Content-Type: application/json" -d '{"lat": 0, "lon": 0}' > /dev/null; then
            log_info "✅ AC Agent is healthy"
            break
        else
            log_warn "⏳ AC Agent not ready, attempt $i/5"
            sleep 5
        fi
    done
    
    # Check Caddy (if SSL is enabled)
    if [ -n "$DOMAIN" ]; then
        if curl -s -f "https://$DOMAIN/health" > /dev/null; then
            log_info "✅ Caddy reverse proxy is healthy"
        else
            log_warn "⚠️  Caddy reverse proxy health check failed"
        fi
    fi
}

# Display status
display_status() {
    log_info "Deployment Status:"
    docker-compose -f docker-compose.cloud.yml --profile cloud ps
    
    echo ""
    log_info "Service URLs:"
    if [ -n "$EXTERNAL_URL" ]; then
        echo "  🏠 Home Assistant: $EXTERNAL_URL"
    else
        echo "  🏠 Home Assistant: http://localhost:8123"
    fi
    
    if [ -n "$WEBHOOK_URL" ]; then
        echo "  🤖 AC Agent: ${WEBHOOK_URL%/ping}"
    else
        echo "  🤖 AC Agent: http://localhost:8000"
    fi
    
    if [ -n "$DOMAIN" ]; then
        echo "  📊 Monitoring: https://$DOMAIN:3000 (if enabled)"
    fi
    
    echo ""
    log_info "Next steps:"
    echo "  1. Configure Home Assistant at the URL above"
    echo "  2. Install the Home Assistant mobile app"
    echo "  3. Set up location tracking in the app"
    echo "  4. Configure the webhook automation (see SETUP.md)"
    echo "  5. Test the system with your location"
    
    echo ""
    log_info "Useful commands:"
    echo "  📋 View logs: docker-compose -f docker-compose.cloud.yml logs -f"
    echo "  🔄 Restart: docker-compose -f docker-compose.cloud.yml restart"
    echo "  ⬇️  Stop: docker-compose -f docker-compose.cloud.yml down"
    echo "  🔍 Status: docker-compose -f docker-compose.cloud.yml ps"
}

# Main deployment flow
main() {
    log_info "Starting cloud deployment..."
    
    check_prerequisites
    load_env
    setup_directories
    test_ifttt
    deploy_services
    health_checks
    display_status
    
    log_info "🎉 Cloud deployment completed successfully!"
}

# Run main function
main "$@" 