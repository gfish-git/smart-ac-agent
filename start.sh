#!/bin/bash

# Smart AC Agent Setup Script

echo "🏠 Smart AC Agent Setup (Home Assistant + IFTTT)"
echo "==============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating template..."
    cat > .env << 'EOF'
# IFTTT Configuration
IFTTT_KEY=your_ifttt_webhook_key_here
IFTTT_AC_ON_EVENT=ac_on
IFTTT_AC_OFF_EVENT=ac_off

# Home Location (required for distance calculations)
HOME_LAT=40.7128
HOME_LON=-74.0060

# OpenAI API Key (required for the AI agent)
OPENAI_API_KEY=your_openai_api_key_here
EOF
    echo "📝 Created .env file. Please edit it with your configuration before continuing."
    echo "   See SETUP.md for detailed instructions."
    exit 1
fi

# Check if required environment variables are set
source .env

if [ "$IFTTT_KEY" = "your_ifttt_webhook_key_here" ]; then
    echo "⚠️  Please update IFTTT_KEY in .env file"
    echo "   Get your key from https://ifttt.com/maker_webhooks"
    exit 1
fi

if [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo "⚠️  Please update OPENAI_API_KEY in .env file"
    exit 1
fi

echo "✅ Environment variables configured"

# Test IFTTT connection
echo "🔧 Testing IFTTT connection..."
if curl -s -X POST "https://maker.ifttt.com/trigger/${IFTTT_AC_ON_EVENT}/with/key/${IFTTT_KEY}" > /dev/null; then
    echo "✅ IFTTT webhook test successful"
else
    echo "⚠️  IFTTT webhook test failed. Please check your key and applet setup."
fi

# Create Home Assistant config directory
mkdir -p homeassistant

# Start Home Assistant first
echo "🏠 Starting Home Assistant..."
docker-compose up homeassistant -d

echo "⏳ Waiting for Home Assistant to start (30 seconds)..."
sleep 30

# Check if Home Assistant is running
if curl -s http://localhost:8123 > /dev/null; then
    echo "✅ Home Assistant is running at http://localhost:8123"
else
    echo "⚠️  Home Assistant may still be starting. Check logs with:"
    echo "   docker-compose logs -f homeassistant"
fi

# Start the AC agent
echo "🤖 Starting Smart AC Agent..."
docker-compose up smart-ac-agent -d

# Wait a moment for startup
sleep 5

# Check if the AC agent is running
if curl -s http://localhost:8000/ping -X POST -H "Content-Type: application/json" -d '{"lat": 0, "lon": 0}' > /dev/null; then
    echo "✅ Smart AC Agent is running at http://localhost:8000"
else
    echo "⚠️  Smart AC Agent may still be starting. Check logs with:"
    echo "   docker-compose logs -f smart-ac-agent"
fi

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps for Home Assistant + IFTTT setup:"
echo "1. Open http://localhost:8123 to configure Home Assistant"
echo "2. Complete the onboarding process"
echo "3. Install the Home Assistant mobile app on your phone"
echo "4. Enable location tracking in the mobile app"
echo "5. Add the REST command to configuration.yaml:"
echo "   rest_command:"
echo "     update_ac_agent:"
echo "       url: \"http://localhost:8000/ping\""
echo "       method: POST"
echo "       headers:"
echo "         Content-Type: \"application/json\""
echo "       payload: >"
echo "         {"
echo "           \"lat\": {{ lat }},"
echo "           \"lon\": {{ lon }},"
echo "           \"speed_mph\": {{ speed | default(0) }}"
echo "         }"
echo "6. Create an automation to call the REST command when your location changes"
echo "7. Make sure your IFTTT applets are enabled"
echo ""
echo "📚 See SETUP.md for detailed step-by-step instructions"
echo "🔍 Monitor with: docker-compose logs -f"
echo ""
echo "🧪 Test the AC agent directly:"
echo "curl -X POST http://localhost:8000/ping -H 'Content-Type: application/json' -d '{\"lat\": 40.7500, \"lon\": -74.0500, \"speed_mph\": 25}'" 