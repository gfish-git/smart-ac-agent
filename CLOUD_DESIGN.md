# Smart AC Agent Cloud Architecture Design

## Overview

This document outlines the architecture for deploying the Smart AC Agent system in Google Cloud Platform (GCP) with a seamless migration path to a local Coral dev board setup.

## Current Architecture Analysis

### Components
1. **Smart AC Agent** (FastAPI + OpenAI)
   - Location-based decision making using GPT-4o-mini
   - IFTTT webhook integration for AC control
   - Distance calculations using haversine formula
   - Configurable thresholds and behavior

2. **Home Assistant** 
   - Location tracking via mobile app
   - Automation engine for triggering AC agent
   - Local data storage and processing

3. **IFTTT Integration**
   - AC on/off webhook endpoints
   - Bridge to existing AC control hardware

4. **Docker Containers**
   - Containerized deployment for portability
   - Environment-based configuration
   - Multi-service orchestration

## Cloud Deployment Architecture (GCP)

### 1. Infrastructure Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                    GCP Cloud Load Balancer                      │
│                  (with SSL termination)                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                 GCP Compute Engine VM                           │
│                 (home-assistant)                                │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │ Home Assistant  │    │ Smart AC Agent  │                    │
│  │   Container     │    │   Container     │                    │
│  │   Port 8123     │    │   Port 8000     │                    │
│  └─────────────────┘    └─────────────────┘                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Docker Network                                 ││
│  │         (container communication)                           ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           Persistent Volume                                 ││
│  │     (Home Assistant config & data)                         ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      IFTTT Cloud                                │
│                  (AC Control Webhooks)                          │
└─────────────────────────────────────────────────────────────────┘
```

### 2. GCP VM Specifications

**Recommended Instance Type:** e2-standard-2
- 2 vCPUs, 8 GB RAM
- 20 GB SSD boot disk
- 50 GB additional SSD for Home Assistant data
- Ubuntu 22.04 LTS

**Network Configuration:**
- Static external IP address
- Firewall rules for ports 8123 (Home Assistant) and 8000 (AC Agent)
- Optional: Cloud NAT for outbound traffic

### 3. Security Configuration

**Firewall Rules:**
```bash
# Home Assistant access
gcloud compute firewall-rules create allow-home-assistant \
  --allow tcp:8123 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow Home Assistant access"

# AC Agent webhook access  
gcloud compute firewall-rules create allow-ac-agent \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow AC Agent webhook access"
```

**SSL/TLS Setup:**
- Use Caddy proxy for automatic SSL certificates
- Secure domain access (e.g., `homeassistant.yourdomain.com`)

## Migration-Ready Architecture

### 1. Configuration Management Strategy

**Environment-Based Configuration:**
```yaml
# .env file structure
# Cloud deployment
DEPLOYMENT_MODE=cloud
EXTERNAL_URL=https://homeassistant.yourdomain.com
WEBHOOK_URL=https://homeassistant.yourdomain.com:8000/ping

# Local deployment (Coral dev board)
DEPLOYMENT_MODE=local
EXTERNAL_URL=http://192.168.1.100:8123
WEBHOOK_URL=http://192.168.1.100:8000/ping

# Common configuration
IFTTT_KEY=your_ifttt_webhook_key
IFTTT_AC_ON_EVENT=ac_on
IFTTT_AC_OFF_EVENT=ac_off
HOME_LAT=40.7128
HOME_LON=-74.0060
OPENAI_API_KEY=your_openai_api_key
```

### 2. Hardware Abstraction Layer

**Docker Compose Profiles:**
```yaml
# docker-compose.yml
version: "3.9"

services:
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    profiles:
      - cloud
      - local
    volumes:
      - ./homeassistant:/config
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    ports:
      - "8123:8123"
    environment:
      - TZ=${TIMEZONE:-America/New_York}
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  smart-ac-agent:
    container_name: smart-ac-agent
    build: .
    profiles:
      - cloud
      - local
    ports:
      - "8000:8000"
    environment:
      - IFTTT_KEY=${IFTTT_KEY}
      - IFTTT_AC_ON_EVENT=${IFTTT_AC_ON_EVENT:-ac_on}
      - IFTTT_AC_OFF_EVENT=${IFTTT_AC_OFF_EVENT:-ac_off}
      - HOME_LAT=${HOME_LAT}
      - HOME_LON=${HOME_LON}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEPLOYMENT_MODE=${DEPLOYMENT_MODE:-cloud}
    depends_on:
      - homeassistant
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Cloud-only services
  caddy:
    container_name: caddy
    image: caddy:latest
    profiles:
      - cloud
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

  # Local-only services (for Coral dev board)
  coral-optimizer:
    container_name: coral-optimizer
    image: coral/optimization:latest
    profiles:
      - local
    devices:
      - /dev/apex_0:/dev/apex_0
    volumes:
      - ./coral:/coral
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

### 3. Data Synchronization Strategy

**Home Assistant Configuration Sync:**
```yaml
# Cloud backup strategy
backup:
  - source: /home/homeassistant/homeassistant/
    destination: gs://your-backup-bucket/homeassistant/
    schedule: "0 2 * * *"  # Daily at 2 AM
    retention: 30 days

# Migration data export
export:
  - entities: all
  - automations: all
  - configuration: all
  - historical_data: last_30_days
```

## Deployment Scripts

### 1. Cloud Deployment Script

```bash
#!/bin/bash
# deploy-cloud.sh

echo "🚀 Deploying Smart AC Agent to GCP..."

# Set deployment mode
export DEPLOYMENT_MODE=cloud

# Pull latest code
git pull origin main

# Build and start cloud services
docker-compose --profile cloud up -d --build

# Wait for services to start
sleep 30

# Test endpoints
curl -f https://homeassistant.yourdomain.com:8123/api/ || echo "⚠️ Home Assistant not ready"
curl -f https://homeassistant.yourdomain.com:8000/ping \
  -X POST -H "Content-Type: application/json" \
  -d '{"lat": 0, "lon": 0}' || echo "⚠️ AC Agent not ready"

echo "✅ Cloud deployment complete!"
```

### 2. Local Migration Script

```bash
#!/bin/bash
# migrate-to-local.sh

echo "🏠 Migrating Smart AC Agent to local Coral dev board..."

# Export cloud configuration
./scripts/export-cloud-config.sh

# Set deployment mode
export DEPLOYMENT_MODE=local

# Stop cloud services
docker-compose --profile cloud down

# Start local services
docker-compose --profile local up -d --build

# Import configuration
./scripts/import-local-config.sh

echo "✅ Local migration complete!"
```

## Coral Dev Board Optimization

### 1. Hardware-Specific Optimizations

**TensorFlow Lite Model (future enhancement):**
```python
# coral_optimizer.py
import tflite_runtime.interpreter as tflite
from pycoral.adapters.common import input_size
from pycoral.adapters.detect import get_objects
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter

class CoralOptimizedAgent:
    def __init__(self):
        self.interpreter = make_interpreter('models/ac_decision_model.tflite')
        self.interpreter.allocate_tensors()
    
    def make_decision(self, location_data):
        # Use Edge TPU for inference if available
        # Fallback to OpenAI API if needed
        pass
```

### 2. Resource Management

**Memory and CPU Optimization:**
```yaml
# Resource limits for Coral dev board
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '2.0'
    reservations:
      memory: 256M
      cpus: '1.0'
```

## Monitoring and Observability

### 1. Cloud Monitoring

**Prometheus + Grafana Stack:**
```yaml
# monitoring/docker-compose.yml
version: "3.9"

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  grafana_data:
```

### 2. Application Metrics

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
ac_decisions_total = Counter('ac_decisions_total', 'Total AC decisions made')
location_updates_total = Counter('location_updates_total', 'Total location updates')
distance_to_home = Gauge('distance_to_home_miles', 'Current distance to home in miles')
response_time = Histogram('response_time_seconds', 'Response time in seconds')

def track_decision(decision_type):
    ac_decisions_total.inc()
    
def track_location_update(distance):
    location_updates_total.inc()
    distance_to_home.set(distance)
```

## Migration Checklist

### Pre-Migration (Cloud → Local)
- [ ] Export Home Assistant configuration
- [ ] Backup historical data
- [ ] Test local hardware compatibility
- [ ] Verify network connectivity
- [ ] Prepare Coral dev board environment

### During Migration
- [ ] Stop cloud services gracefully
- [ ] Transfer configuration files
- [ ] Start local services
- [ ] Verify all integrations
- [ ] Test AC control functionality

### Post-Migration
- [ ] Update DNS/networking if needed
- [ ] Verify mobile app connectivity
- [ ] Test location tracking
- [ ] Monitor system performance
- [ ] Update monitoring dashboards

## Security Considerations

### Cloud Security
- Use private networks where possible
- Enable GCP Security Command Center
- Regular security patches and updates
- SSL/TLS for all communications
- API key rotation

### Local Security
- Network segmentation
- VPN access for remote management
- Regular firmware updates
- Physical security for Coral dev board
- Backup encryption

## Cost Optimization

### Cloud Costs
- Use preemptible instances for development
- Monitor resource usage
- Set up billing alerts
- Use committed use discounts

### Local Benefits
- No ongoing cloud compute costs
- Reduced latency
- Better privacy control
- Offline capability

## Future Enhancements

1. **Edge AI Integration**
   - TensorFlow Lite models for Coral TPU
   - Local inference for faster decisions
   - Reduced API dependencies

2. **Multi-Zone Support**
   - Support for multiple AC zones
   - Different temperature preferences
   - Time-based automation

3. **Advanced Automation**
   - Weather-based decisions
   - Calendar integration
   - Energy usage optimization

4. **Enhanced Security**
   - End-to-end encryption
   - Certificate-based authentication
   - Audit logging

This architecture provides a robust, scalable solution that can seamlessly migrate between cloud and local deployments while maintaining all functionality and data integrity. 