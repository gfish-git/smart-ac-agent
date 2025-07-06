#!/bin/bash
# Check GCP VM status and get Home Assistant URL

echo "🏠 Checking GCP VM 'home-assistant' status..."

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

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    log_error "Google Cloud CLI is not installed"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    log_error "Not authenticated with Google Cloud"
    echo "Run: gcloud auth login"
    exit 1
fi

# Get current project
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ]; then
    log_error "No Google Cloud project selected"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

log_info "Using project: $PROJECT"

# List all VMs to find the home-assistant one
log_info "Searching for 'home-assistant' VM..."
VM_INFO=$(gcloud compute instances list --filter="name:home-assistant" --format="table(name,zone,status,externalIP)" 2>/dev/null)

if [ -z "$VM_INFO" ] || [ "$VM_INFO" = "NAME  ZONE  STATUS  EXTERNAL_IP" ]; then
    log_error "No VM with 'home-assistant' in the name found"
    echo ""
    echo "Available VMs:"
    gcloud compute instances list --format="table(name,zone,status,externalIP)"
    echo ""
    echo "If your VM has a different name, you can:"
    echo "1. Rename it: gcloud compute instances rename OLD_NAME --new-name=home-assistant --zone=ZONE"
    echo "2. Or modify the search above to use your actual VM name"
    exit 1
fi

echo ""
log_info "Found VMs matching 'home-assistant':"
echo "$VM_INFO"

# Get the first matching VM details
VM_NAME=$(echo "$VM_INFO" | tail -n +2 | head -n 1 | awk '{print $1}')
VM_ZONE=$(echo "$VM_INFO" | tail -n +2 | head -n 1 | awk '{print $2}')
VM_STATUS=$(echo "$VM_INFO" | tail -n +2 | head -n 1 | awk '{print $3}')
VM_EXTERNAL_IP=$(echo "$VM_INFO" | tail -n +2 | head -n 1 | awk '{print $4}')

echo ""
log_info "VM Details:"
echo "  Name: $VM_NAME"
echo "  Zone: $VM_ZONE"
echo "  Status: $VM_STATUS"
echo "  External IP: $VM_EXTERNAL_IP"

# Check if VM is running
if [ "$VM_STATUS" != "RUNNING" ]; then
    log_warn "VM is not running (status: $VM_STATUS)"
    echo ""
    echo "To start the VM:"
    echo "  gcloud compute instances start $VM_NAME --zone=$VM_ZONE"
    echo ""
    read -p "Would you like to start the VM now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Starting VM..."
        gcloud compute instances start $VM_NAME --zone=$VM_ZONE
        log_info "Waiting for VM to start..."
        sleep 30
        # Get updated IP after start
        VM_EXTERNAL_IP=$(gcloud compute instances describe $VM_NAME --zone=$VM_ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
    else
        log_error "VM needs to be running to proceed"
        exit 1
    fi
fi

# Check if external IP exists
if [ -z "$VM_EXTERNAL_IP" ] || [ "$VM_EXTERNAL_IP" = "None" ]; then
    log_error "VM has no external IP address"
    echo ""
    echo "To add an external IP:"
    echo "  gcloud compute instances add-access-config $VM_NAME --zone=$VM_ZONE"
    exit 1
fi

echo ""
log_info "✅ VM is running with external IP: $VM_EXTERNAL_IP"

# Check firewall rules
log_info "Checking firewall rules..."
FIREWALL_8123=$(gcloud compute firewall-rules list --filter="name:*8123* OR (direction:INGRESS AND allowed.ports:8123)" --format="value(name)" 2>/dev/null)
FIREWALL_8000=$(gcloud compute firewall-rules list --filter="name:*8000* OR (direction:INGRESS AND allowed.ports:8000)" --format="value(name)" 2>/dev/null)

if [ -z "$FIREWALL_8123" ]; then
    log_warn "No firewall rule found for port 8123 (Home Assistant)"
    echo "Create one with:"
    echo "  gcloud compute firewall-rules create allow-home-assistant-8123 --allow tcp:8123 --source-ranges 0.0.0.0/0"
else
    log_info "✅ Firewall rule for port 8123: $FIREWALL_8123"
fi

if [ -z "$FIREWALL_8000" ]; then
    log_warn "No firewall rule found for port 8000 (AC Agent)"
    echo "Create one with:"
    echo "  gcloud compute firewall-rules create allow-ac-agent-8000 --allow tcp:8000 --source-ranges 0.0.0.0/0"
else
    log_info "✅ Firewall rule for port 8000: $FIREWALL_8000"
fi

# Test connectivity
echo ""
log_info "Testing connectivity to VM..."

# Test SSH
log_info "Testing SSH connection..."
if gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="echo 'SSH connection successful'" --quiet 2>/dev/null; then
    log_info "✅ SSH connection working"
else
    log_warn "⚠️  SSH connection failed - may need to set up SSH keys"
    echo "Run: gcloud compute ssh $VM_NAME --zone=$VM_ZONE"
fi

# Test HTTP ports
log_info "Testing HTTP connectivity..."
if curl -m 5 -s "http://$VM_EXTERNAL_IP:8123" > /dev/null 2>&1; then
    log_info "✅ Home Assistant port 8123 is accessible"
else
    log_warn "⚠️  Home Assistant port 8123 not responding (may not be installed yet)"
fi

if curl -m 5 -s "http://$VM_EXTERNAL_IP:8000" > /dev/null 2>&1; then
    log_info "✅ AC Agent port 8000 is accessible"
else
    log_warn "⚠️  AC Agent port 8000 not responding (may not be installed yet)"
fi

# Display URLs
echo ""
echo "🌐 Your Home Assistant URLs:"
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🏠 Home Assistant:  http://$VM_EXTERNAL_IP:8123"
echo "  🤖 AC Agent:        http://$VM_EXTERNAL_IP:8000"
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# SSH command
echo ""
echo "🔌 To connect to your VM:"
echo "  gcloud compute ssh $VM_NAME --zone=$VM_ZONE"

# Next steps
echo ""
echo "📋 Next steps to deploy your AC Agent:"
echo "  1. SSH into your VM (command above)"
echo "  2. Clone your project: git clone https://github.com/yourusername/ac-agent.git"
echo "  3. Configure .env file with the IP address: $VM_EXTERNAL_IP"
echo "  4. Run deployment script: ./scripts/deploy-cloud.sh"

echo ""
echo "💡 Pro tip: Save these URLs for easy access!"
echo "  Home Assistant: http://$VM_EXTERNAL_IP:8123"
echo "  AC Agent: http://$VM_EXTERNAL_IP:8000" 