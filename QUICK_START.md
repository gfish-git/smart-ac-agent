# Quick Start Guide: Home Assistant + IFTTT AC Control

This is a condensed guide to get your smart AC system running quickly.

## ⚡ Prerequisites Checklist

- [ ] Docker installed
- [ ] IFTTT account with AC control applets already working
- [ ] IFTTT webhook key
- [ ] OpenAI API key
- [ ] Your home's GPS coordinates

## 🚀 5-Minute Setup

### 1. Configure Environment
```bash
# Create .env file
cat > .env << 'EOF'
IFTTT_KEY=your_ifttt_webhook_key_here
IFTTT_AC_ON_EVENT=ac_on
IFTTT_AC_OFF_EVENT=ac_off
HOME_LAT=40.7128
HOME_LON=-74.0060
OPENAI_API_KEY=your_openai_api_key_here
EOF

# Edit with your actual values
nano .env
```

### 2. Start Services
```bash
# Quick start script
./start.sh

# Or manually
docker-compose up -d
```

### 3. Configure Home Assistant
1. **Open** http://localhost:8123
2. **Complete** the onboarding wizard
3. **Set your home location** during setup
4. **Install mobile app** on your phone
5. **Enable location tracking** in the app

### 4. Add REST Command
Edit Home Assistant's `configuration.yaml`:
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

### 5. Create Automation
In Home Assistant UI:
1. **Settings** → **Automations & Scenes**
2. **Create Automation**
3. **Trigger**: State change on `device_tracker.your_phone` (latitude/longitude attributes)
4. **Action**: Call service `rest_command.update_ac_agent`

## 🧪 Testing

### Test Chain Components

1. **Test IFTTT directly:**
```bash
curl -X POST "https://maker.ifttt.com/trigger/ac_on/with/key/YOUR_IFTTT_KEY"
```

2. **Test AC Agent directly:**
```bash
curl -X POST http://localhost:8000/ping \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7500, "lon": -74.0500, "speed_mph": 25}'
```

3. **Test Home Assistant automation:**
   - Leave/return home with your phone
   - Check `Developer Tools` → `States` for your device tracker
   - Monitor logs: `docker-compose logs -f smart-ac-agent`

## 📱 Mobile App Setup

### iPhone (Home Assistant App)
1. Download "Home Assistant" from App Store
2. Add server: `http://YOUR_LOCAL_IP:8123`
3. Allow location permissions
4. Enable "Location tracking" in app settings

### Android (Home Assistant App)
1. Download "Home Assistant" from Play Store
2. Add server: `http://YOUR_LOCAL_IP:8123`
3. Allow location permissions
4. Configure location zones if needed

## 🔧 Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| Home Assistant won't start | Check port 8123 isn't in use |
| Mobile app won't connect | Use local IP, not localhost |
| Location not updating | Check app permissions & battery optimization |
| AC not responding | Verify IFTTT webhooks work directly |
| Automation not triggering | Check device tracker entity name |

## 📊 System Flow

```
📱 Phone Location → 🏠 Home Assistant → 🤖 AC Agent → 🔗 IFTTT → ❄️ AC Control
```

**Logic:**
- `< 0.25 mi` from home → Do nothing
- `0.25-2 mi` approaching → Turn AC on
- `> 2 mi` or leaving → Turn AC off

## 🎯 What's Next?

Once basic functionality works:
1. **Fine-tune** distance thresholds in `main.py`
2. **Add temperature sensors** for smarter control
3. **Create dashboards** to monitor the system
4. **Add notifications** when AC turns on/off
5. **Include other family members** with device trackers

## 🆘 Need Help?

- **Full documentation**: See `SETUP.md`
- **Configuration examples**: See `homeassistant-config-sample.yaml`
- **Logs**: `docker-compose logs -f`
- **Status**: `docker-compose ps`

The system prioritizes safety with intelligent cooldown logic and distance-based decisions! 