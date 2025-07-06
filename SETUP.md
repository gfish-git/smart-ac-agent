# Smart AC Agent Setup with Home Assistant + IFTTT

This guide sets up a hybrid system where:
- **Home Assistant** handles location tracking (excellent mobile app integration)
- **AC Agent** makes smart decisions based on location
- **IFTTT** controls your AC (using your existing setup)

## Prerequisites

- Docker and Docker Compose installed on your system
- An OpenAI API key
- IFTTT account with AC controls already set up
- IFTTT Webhook service enabled
- Phone with Home Assistant app for location tracking

## Step 1: Get Your IFTTT Webhook Key

1. Go to https://ifttt.com/maker_webhooks
2. Click "Settings" in the top right
3. Your webhook key is shown in the URL: `https://maker.ifttt.com/use/YOUR_KEY_HERE`
4. Copy this key

## Step 2: Set Up IFTTT Applets

Create two IFTTT applets (if you haven't already):

### AC On Applet
1. **If This**: Webhooks → Receive a web request
2. **Event Name**: `ac_on` (or whatever you prefer)
3. **Then That**: Your AC control service → Turn On

### AC Off Applet  
1. **If This**: Webhooks → Receive a web request
2. **Event Name**: `ac_off` (or whatever you prefer)
3. **Then That**: Your AC control service → Turn Off

## Step 3: Create Environment Variables

Create a `.env` file in the project root:

```env
# IFTTT Configuration
IFTTT_KEY=your_ifttt_webhook_key_here
IFTTT_AC_ON_EVENT=ac_on
IFTTT_AC_OFF_EVENT=ac_off

# Home Location (required for distance calculations)
HOME_LAT=40.7128
HOME_LON=-74.0060

# OpenAI API Key (required for the AI agent)
OPENAI_API_KEY=your_openai_api_key_here
```

## Step 4: Start the System

```bash
# Start both Home Assistant and AC Agent
docker-compose up -d

# Wait for Home Assistant to start (1-2 minutes)
# Check logs if needed
docker-compose logs -f homeassistant
```

## Step 5: Configure Home Assistant

### Initial Setup
1. **Access Home Assistant**: Open http://localhost:8123 in your browser
2. **Complete onboarding**: Create your account and set up your home location
3. **Set timezone**: Make sure it matches your location

### Set Up Mobile App
1. **Download the app**: Install "Home Assistant" from App Store/Play Store
2. **Connect to server**: Enter `http://YOUR_LOCAL_IP:8123`
3. **Enable location tracking**: Allow location permissions when prompted
4. **Configure device tracker**: Your phone will appear as a `device_tracker` entity

### Configure Webhooks for AC Agent
1. **Go to Settings** → **Automations & Scenes**
2. **Create new automation**
3. **Set up location-based automation**:

```yaml
# Example automation in Home Assistant
alias: "AC Control Based on Location"
description: "Send location updates to AC agent"
trigger:
  - platform: state
    entity_id: device_tracker.your_phone
    attribute: latitude
  - platform: state
    entity_id: device_tracker.your_phone
    attribute: longitude
mode: single
action:
  - service: rest_command.update_ac_agent
    data:
      lat: "{{ state_attr('device_tracker.your_phone', 'latitude') }}"
      lon: "{{ state_attr('device_tracker.your_phone', 'longitude') }}"
      speed: "{{ state_attr('device_tracker.your_phone', 'speed') | default(0) }}"
```

### Add REST Command
Add this to your Home Assistant `configuration.yaml`:

```yaml
rest_command:
  update_ac_agent:
    url: "http://localhost:8000/ping"
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

## Step 6: Test the Complete Setup

### Test IFTTT (Direct)
```bash
# Verify your IFTTT webhooks work
curl -X POST "https://maker.ifttt.com/trigger/ac_on/with/key/YOUR_IFTTT_KEY"
curl -X POST "https://maker.ifttt.com/trigger/ac_off/with/key/YOUR_IFTTT_KEY"
```

### Test AC Agent (Direct)
```bash
# Test the AC agent directly
curl -X POST http://localhost:8000/ping \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7500, "lon": -74.0500, "speed_mph": 25}'
```

### Test End-to-End
1. **Leave home** with your phone
2. **Check Home Assistant**: Go to Developer Tools → States, find your `device_tracker.your_phone`
3. **Trigger automation**: The automation should fire when your location changes
4. **Check AC agent logs**: `docker-compose logs -f smart-ac-agent`
5. **Verify AC control**: Your AC should respond based on distance logic

## How the System Works

**Complete Flow:**
1. **Your phone** → Reports location to Home Assistant
2. **Home Assistant** → Detects location changes, triggers automation
3. **Home Assistant automation** → Sends webhook to AC Agent with location data
4. **AC Agent** → Calculates distance, makes smart decision using AI
5. **AC Agent** → Triggers IFTTT webhook if needed
6. **IFTTT** → Controls your AC

**Smart Logic:**
- Distance < 0.25 mi → Do nothing (already home)
- Distance 0.25-2 mi, getting closer → Turn AC on
- Distance > 2 mi or getting farther → Turn AC off

## Advanced Home Assistant Configuration

### Fine-tune Location Tracking
In Home Assistant, you can adjust location tracking sensitivity:

```yaml
# configuration.yaml
device_tracker:
  - platform: composite
    name: your_phone_composite
    time_as: device_or_local
    entity_id:
      - device_tracker.your_phone
```

### Add More Triggers
You can add additional triggers like:
- Time-based (don't turn on AC at night)
- Weather-based (only when it's hot)
- Calendar-based (work schedule)

### Dashboard Integration
Create a dashboard card to monitor the system:

```yaml
# Dashboard card example
type: entities
entities:
  - entity: device_tracker.your_phone
    name: "Phone Location"
  - entity: sensor.distance_to_home  # If you create this sensor
    name: "Distance to Home"
```

## Troubleshooting

### Home Assistant Issues
- **Can't access**: Check that port 8123 isn't blocked
- **Mobile app won't connect**: Use your local IP address, not localhost
- **Location not updating**: Check app permissions and battery optimization

### AC Agent Issues
- **Not receiving webhooks**: Check the REST command configuration
- **IFTTT not triggering**: Verify webhook URLs and applet status
- **Distance calculations wrong**: Double-check your home coordinates

### Integration Issues
- **Automation not triggering**: Check Home Assistant logs for errors
- **Webhooks timing out**: Ensure AC agent is running and accessible

## Security & Privacy

- **Local processing**: All location processing happens locally on your network
- **Secure tokens**: Keep your `.env` file secure
- **Network isolation**: Consider VPN if accessing remotely
- **Data retention**: Home Assistant stores location history locally

## Next Steps

Once everything is working:
1. **Fine-tune the distance thresholds** in the AC agent logic
2. **Add more sensors** (temperature, humidity) for smarter decisions
3. **Create dashboards** in Home Assistant to monitor the system
4. **Set up notifications** when AC is turned on/off
5. **Add additional family members** with their own device trackers

This hybrid approach gives you the best of both worlds - Home Assistant's excellent location tracking and your existing IFTTT AC control! 