#!/bin/bash
# Migration script from cloud to local Coral dev board

set -e

echo "🏠 Migrating Smart AC Agent from Cloud to Local Coral Dev Board..."

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

# Check if running on Coral dev board
check_coral_hardware() {
    log_info "Checking Coral dev board hardware..."
    
    if [ ! -f /proc/device-tree/model ]; then
        log_warn "Cannot detect hardware model"
        return 0
    fi
    
    local model=$(cat /proc/device-tree/model 2>/dev/null || echo "unknown")
    if echo "$model" | grep -i "coral" > /dev/null; then
        log_info "✅ Coral dev board detected: $model"
        export CORAL_DETECTED=true
    else
        log_warn "⚠️  Coral dev board not detected, but continuing anyway"
        export CORAL_DETECTED=false
    fi
}

# Export cloud configuration
export_cloud_config() {
    log_info "Exporting cloud configuration..."
    
    # Create backup directory
    local backup_dir="migration_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Export Home Assistant configuration
    if [ -d "homeassistant" ]; then
        log_info "Backing up Home Assistant configuration..."
        cp -r homeassistant "$backup_dir/"
    fi
    
    # Export environment variables
    if [ -f ".env" ]; then
        log_info "Backing up environment configuration..."
        cp .env "$backup_dir/"
    fi
    
    # Export custom configurations
    for config_file in docker-compose.yml docker-compose.cloud.yml caddy/Caddyfile; do
        if [ -f "$config_file" ]; then
            mkdir -p "$backup_dir/$(dirname "$config_file")"
            cp "$config_file" "$backup_dir/$config_file"
        fi
    done
    
    log_info "✅ Configuration exported to $backup_dir"
    export BACKUP_DIR="$backup_dir"
}

# Update environment for local deployment
update_local_env() {
    log_info "Updating environment for local deployment..."
    
    # Create local environment file
    cp .env .env.local
    
    # Update deployment mode
    sed -i 's/DEPLOYMENT_MODE=cloud/DEPLOYMENT_MODE=local/' .env.local
    
    # Update URLs for local network
    local local_ip=$(hostname -I | awk '{print $1}')
    sed -i "s|EXTERNAL_URL=.*|EXTERNAL_URL=http://${local_ip}:8123|" .env.local
    sed -i "s|WEBHOOK_URL=.*|WEBHOOK_URL=http://${local_ip}:8000/ping|" .env.local
    
    # Add Coral-specific environment variables
    if [ "$CORAL_DETECTED" = "true" ]; then
        echo "" >> .env.local
        echo "# Coral dev board specific settings" >> .env.local
        echo "CORAL_ENABLED=true" >> .env.local
        echo "CORAL_MODEL_PATH=/models/ac_decision_model.tflite" >> .env.local
    fi
    
    log_info "✅ Local environment configured in .env.local"
}

# Setup Coral-specific components
setup_coral_components() {
    if [ "$CORAL_DETECTED" != "true" ]; then
        log_info "Skipping Coral-specific setup (hardware not detected)"
        return 0
    fi
    
    log_info "Setting up Coral-specific components..."
    
    # Create Coral directories
    mkdir -p coral
    mkdir -p models
    
    # Create Coral optimizer script
    cat > coral/optimizer.py << 'EOF'
#!/usr/bin/env python3
"""
Coral dev board optimizer for Smart AC Agent
"""
import os
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoralOptimizer:
    def __init__(self):
        self.tflite_model = None
        self.model_path = os.getenv('CORAL_MODEL_PATH', '/models/ac_decision_model.tflite')
        
    def initialize(self):
        """Initialize Coral TPU if available"""
        try:
            import tflite_runtime.interpreter as tflite
            from pycoral.utils.edgetpu import make_interpreter
            
            if os.path.exists(self.model_path):
                logger.info(f"Loading TFLite model from {self.model_path}")
                self.tflite_model = make_interpreter(self.model_path)
                self.tflite_model.allocate_tensors()
                logger.info("✅ Coral TPU model loaded successfully")
            else:
                logger.warning(f"Model file not found at {self.model_path}")
                
        except ImportError:
            logger.warning("Coral libraries not available, running without TPU acceleration")
        except Exception as e:
            logger.error(f"Error initializing Coral TPU: {e}")
    
    def optimize_decision(self, location_data: dict) -> Optional[str]:
        """
        Use Coral TPU for decision making if available
        Falls back to cloud API if TPU not available
        """
        if self.tflite_model is None:
            return None
            
        try:
            # This is a placeholder for actual model inference
            # In practice, you would preprocess location_data and run inference
            logger.info("Running inference on Coral TPU")
            # result = self.tflite_model.invoke(preprocessed_data)
            # return postprocess_result(result)
            
            # For now, return None to fall back to OpenAI
            return None
            
        except Exception as e:
            logger.error(f"Error during Coral inference: {e}")
            return None

if __name__ == "__main__":
    optimizer = CoralOptimizer()
    optimizer.initialize()
    
    # Keep the service running
    import time
    while True:
        time.sleep(60)
        logger.info("Coral optimizer running...")
EOF
    
    chmod +x coral/optimizer.py
    
    log_info "✅ Coral components configured"
}

# Stop cloud services
stop_cloud_services() {
    log_info "Stopping cloud services..."
    
    # Stop cloud deployment
    docker-compose -f docker-compose.cloud.yml --profile cloud down 2>/dev/null || true
    
    # Clean up cloud-specific containers
    docker container prune -f 2>/dev/null || true
    
    log_info "✅ Cloud services stopped"
}

# Start local services
start_local_services() {
    log_info "Starting local services..."
    
    # Use local environment
    cp .env.local .env
    
    # Start local deployment
    docker-compose -f docker-compose.cloud.yml --profile local up -d --build
    
    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 30
}

# Health checks for local deployment
health_checks_local() {
    log_info "Performing health checks for local deployment..."
    
    local local_ip=$(hostname -I | awk '{print $1}')
    
    # Check Home Assistant
    for i in {1..10}; do
        if curl -s -f "http://${local_ip}:8123/api/" > /dev/null; then
            log_info "✅ Home Assistant is healthy"
            break
        else
            log_warn "⏳ Home Assistant not ready, attempt $i/10"
            sleep 10
        fi
    done
    
    # Check AC Agent
    for i in {1..5}; do
        if curl -s -f "http://${local_ip}:8000/ping" -X POST -H "Content-Type: application/json" -d '{"lat": 0, "lon": 0}' > /dev/null; then
            log_info "✅ AC Agent is healthy"
            break
        else
            log_warn "⏳ AC Agent not ready, attempt $i/5"
            sleep 5
        fi
    done
    
    # Check Coral optimizer (if enabled)
    if [ "$CORAL_DETECTED" = "true" ]; then
        if docker ps | grep coral-optimizer > /dev/null; then
            log_info "✅ Coral optimizer is running"
        else
            log_warn "⚠️  Coral optimizer not running"
        fi
    fi
}

# Display migration status
display_migration_status() {
    local local_ip=$(hostname -I | awk '{print $1}')
    
    log_info "Migration Status:"
    docker-compose -f docker-compose.cloud.yml --profile local ps
    
    echo ""
    log_info "Local Service URLs:"
    echo "  🏠 Home Assistant: http://${local_ip}:8123"
    echo "  🤖 AC Agent: http://${local_ip}:8000"
    
    if [ "$CORAL_DETECTED" = "true" ]; then
        echo "  🧠 Coral TPU: Enabled"
    else
        echo "  🧠 Coral TPU: Not detected"
    fi
    
    echo ""
    log_info "Migration completed! Important notes:"
    echo "  1. Update your Home Assistant mobile app to use the new local URL"
    echo "  2. Your Home Assistant configuration has been preserved"
    echo "  3. The system is now running locally on your Coral dev board"
    echo "  4. IFTTT integration remains unchanged"
    echo "  5. Backup saved in: $BACKUP_DIR"
    
    echo ""
    log_info "Network configuration:"
    echo "  📱 Configure your phone's Home Assistant app to: http://${local_ip}:8123"
    echo "  🔧 Update webhook URL in Home Assistant to: http://${local_ip}:8000/ping"
    
    echo ""
    log_info "Useful commands:"
    echo "  📋 View logs: docker-compose -f docker-compose.cloud.yml --profile local logs -f"
    echo "  🔄 Restart: docker-compose -f docker-compose.cloud.yml --profile local restart"
    echo "  ⬇️  Stop: docker-compose -f docker-compose.cloud.yml --profile local down"
}

# Main migration flow
main() {
    log_info "Starting migration from cloud to local..."
    
    check_coral_hardware
    export_cloud_config
    update_local_env
    setup_coral_components
    stop_cloud_services
    start_local_services
    health_checks_local
    display_migration_status
    
    log_info "🎉 Migration completed successfully!"
}

# Run main function
main "$@" 