# Smart AC Agent - GCP Cloud Deployment Guide

## Quick Start for GCP Deployment

This guide will help you deploy your Smart AC Agent to your existing GCP VM named "home-assistant" with easy migration to your Coral dev board later.

## Prerequisites

✅ **You have:**
- GCP VM named "home-assistant" running
- IFTTT account with AC control applets
- OpenAI API key
- Home Assistant mobile app on your phone

## Step 1: Connect to Your GCP VM

```bash
# SSH into your GCP VM
gcloud compute ssh home-assistant --zone=YOUR_ZONE

# Or use SSH directly
ssh -i ~/.ssh/your-key user@your-vm-external-ip
```

## Step 2: Install Prerequisites on VM

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for Docker group changes
exit
# SSH back in
```

## Step 3: Clone and Configure Your Project

```bash
# Clone your project (or upload files)
git clone https://github.com/yourusername/ac-agent.git
cd ac-agent

# Copy environment template
cp env.example .env

# Edit configuration
nano .env
```

### Configure `.env` for Cloud Deployment

```env
# DEPLOYMENT CONFIGURATION
DEPLOYMENT_MODE=cloud

# Replace with your actual domain (or use IP if no domain)
EXTERNAL_URL=https://your-domain.com
WEBHOOK_URL=https://your-domain.com:8000/ping
DOMAIN=your-domain.com

# Your IFTTT configuration
IFTTT_KEY=your_actual_ifttt_key_here
IFTTT_AC_ON_EVENT=ac_on
IFTTT_AC_OFF_EVENT=ac_off

# Your home coordinates
HOME_LAT=40.7128
HOME_LON=-74.0060

# Your OpenAI API key
OPENAI_API_KEY=your_actual_openai_key_here

# Your timezone
TIMEZONE=America/New_York
```

## Step 4: Configure GCP Firewall

```bash
# Allow Home Assistant port
gcloud compute firewall-rules create allow-home-assistant-8123 \
  --allow tcp:8123 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow Home Assistant access"

# Allow AC Agent port
gcloud compute firewall-rules create allow-ac-agent-8000 \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow AC Agent webhook access"

# Allow HTTP/HTTPS for SSL
gcloud compute firewall-rules create allow-web-traffic \
  --allow tcp:80,tcp:443 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow HTTP/HTTPS traffic"
```

## Step 5: Deploy to Cloud

```bash
# Run the automated deployment script
./scripts/deploy-cloud.sh
```

The script will:
- ✅ Check prerequisites
- ✅ Test IFTTT connectivity
- ✅ Deploy containers with SSL
- ✅ Perform health checks
- ✅ Display service URLs

## Step 6: Configure Your Domain (Optional)

If you want to use a custom domain:

1. **Point your domain to your GCP VM's external IP**
2. **Update your .env file with your domain**
3. **Restart with SSL:**

```bash
# Stop services
docker-compose -f docker-compose.cloud.yml --profile cloud down

# Start with SSL enabled
docker-compose -f docker-compose.cloud.yml --profile cloud up -d
```

## Step 7: Set Up Home Assistant

1. **Access Home Assistant:** Open your configured URL
2. **Complete onboarding** and create account
3. **Set home location** in the onboarding process

## Step 8: Configure Mobile App

1. **Install** Home Assistant mobile app
2. **Connect** to your cloud URL
3. **Enable location tracking** in app settings

## Step 9: Set Up Automation

Add this to your Home Assistant `configuration.yaml`:

```yaml
rest_command:
  update_ac_agent:
    url: "https://your-domain.com:8000/ping"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: >
      {
        "lat": {{ lat }},
        "lon": {{ lon }},
        "speed_mph": {{ speed | default(0) }}
      }
```

Create automation in Home Assistant:

```yaml
alias: "AC Control Based on Location"
description: "Send location updates to AC agent"
trigger:
  - platform: state
    entity_id: device_tracker.your_phone_name
    attribute: latitude
  - platform: state
    entity_id: device_tracker.your_phone_name
    attribute: longitude
mode: single
action:
  - service: rest_command.update_ac_agent
    data:
      lat: "{{ state_attr('device_tracker.your_phone_name', 'latitude') }}"
      lon: "{{ state_attr('device_tracker.your_phone_name', 'longitude') }}"
      speed: "{{ state_attr('device_tracker.your_phone_name', 'speed') | default(0) }}"
```

## Step 10: Test the System

```bash
# Test AC Agent directly
curl -X POST https://your-domain.com:8000/ping \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7500, "lon": -74.0500, "speed_mph": 25}'

# Test IFTTT integration
curl -X POST "https://maker.ifttt.com/trigger/ac_on/with/key/YOUR_IFTTT_KEY"
```

## Migration to Coral Dev Board

When you're ready to migrate to your Coral dev board:

1. **Set up Coral dev board** with Docker
2. **Run migration script:**

```bash
# On your Coral dev board
git clone https://github.com/yourusername/ac-agent.git
cd ac-agent
./scripts/migrate-to-local.sh
```

The migration script will:
- ✅ Export your cloud configuration
- ✅ Stop cloud services
- ✅ Configure for local deployment
- ✅ Enable Coral TPU optimization
- ✅ Start local services
- ✅ Update mobile app configuration

## Monitoring and Maintenance

### View Logs
```bash
# All services
docker-compose -f docker-compose.cloud.yml logs -f

# Specific service
docker-compose -f docker-compose.cloud.yml logs -f smart-ac-agent
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.cloud.yml restart

# Restart specific service
docker-compose -f docker-compose.cloud.yml restart smart-ac-agent
```

### Update Configuration
```bash
# Edit environment
nano .env

# Restart to apply changes
docker-compose -f docker-compose.cloud.yml restart
```

## Troubleshooting

### Common Issues

**Home Assistant not accessible:**
- Check firewall rules
- Verify external IP
- Check container logs

**AC Agent not responding:**
- Verify IFTTT keys
- Check OpenAI API key
- Review agent logs

**Location not updating:**
- Check mobile app permissions
- Verify webhook URL in automation
- Test REST command manually

### Get Help

```bash
# Check container status
docker-compose -f docker-compose.cloud.yml ps

# View specific logs
docker-compose -f docker-compose.cloud.yml logs smart-ac-agent

# Test connectivity
curl -v https://your-domain.com:8123/api/
```

## Architecture Benefits

This design provides:

✅ **Cloud deployment** with SSL and automatic certificates
✅ **Easy migration** to local Coral dev board
✅ **Environment-based configuration** for different deployments
✅ **Docker profiles** for cloud vs local services
✅ **Monitoring and logging** built-in
✅ **Backup and restore** capabilities

Your system will work identically whether deployed in the cloud or locally, making the transition seamless when you're ready to move to your Coral dev board! 