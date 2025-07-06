# Smart AC Agent 🏠🤖

A location-based smart air conditioning control system that automatically manages your AC based on your proximity to home using Home Assistant, IFTTT, and AI.

## 🌟 Features

- **Location-based automation**: Automatically turns AC on/off based on your distance from home
- **Smart distance logic**: 
  - `> 2 miles away` → Turn AC OFF
  - `0.25-2 miles approaching` → Turn AC ON  
  - `< 0.25 miles (home)` → No action
- **Cloud deployment ready**: Deploy to GCP or run locally
- **Home Assistant integration**: Excellent mobile app for location tracking
- **IFTTT compatibility**: Works with any AC system that supports IFTTT
- **AI-powered decisions**: Uses OpenAI for intelligent decision making
- **Easy migration**: Switch between cloud and local (Coral dev board) deployments

## 🏗️ Architecture

```
Phone Location → Home Assistant → AC Agent → IFTTT → Your AC
```

- **Home Assistant**: Tracks your phone's location via mobile app
- **AC Agent**: FastAPI service that makes smart decisions based on distance
- **IFTTT**: Triggers your AC control system
- **Docker**: Containerized deployment for easy setup

## 🚀 Quick Start

### Cloud Deployment (GCP)

1. **Clone and setup**:
   ```bash
   git clone <this-repo>
   cd smart-ac-agent
   cp env.example .env
   ```

2. **Configure environment**:
   ```bash
   # Edit .env with your values
   IFTTT_KEY=your_ifttt_webhook_key
   OPENAI_API_KEY=your_openai_api_key
   HOME_LAT=40.7128
   HOME_LON=-74.0060
   ```

3. **Deploy to GCP**:
   ```bash
   ./scripts/deploy-cloud.sh
   ```

### Local Deployment

1. **Run locally**:
   ```bash
   docker-compose up -d
   ```

2. **Access services**:
   - Home Assistant: http://localhost:8123
   - AC Agent: http://localhost:8000

## 📱 Setup Instructions

### 1. IFTTT Configuration

1. Create IFTTT applets:
   - **AC On**: Webhook trigger `ac_on` → Your AC control
   - **AC Off**: Webhook trigger `ac_off` → Your AC control
2. Get your webhook key from https://ifttt.com/maker_webhooks

### 2. Home Assistant Setup

1. Complete initial setup wizard
2. Install Home Assistant mobile app
3. Enable location permissions
4. Configure webhook automation (see `SETUP.md`)

### 3. Test the System

```bash
# Test AC Agent directly
curl -X POST http://your-server:8000/ping \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7500, "lon": -74.0500, "speed_mph": 25}'
```

## 📁 Project Structure

```
smart-ac-agent/
├── main.py                     # FastAPI AC Agent service
├── docker-compose.yml          # Local deployment
├── docker-compose.cloud.yml    # Cloud deployment with profiles
├── dockerfile                  # AC Agent container
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
├── scripts/
│   ├── deploy-cloud.sh         # Cloud deployment script
│   ├── migrate-to-local.sh     # Migration script
│   └── check-gcp-status.sh     # GCP status checker
├── caddy/
│   └── Caddyfile              # SSL reverse proxy config
├── homeassistant/
│   └── configuration.yaml     # HA automation config
├── docs/
│   ├── SETUP.md               # Detailed setup guide
│   ├── CLOUD_DESIGN.md        # Architecture documentation
│   └── GCP_DEPLOYMENT_GUIDE.md # GCP deployment guide
└── README.md                   # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DEPLOYMENT_MODE` | Deployment environment | `cloud` or `local` |
| `IFTTT_KEY` | IFTTT webhook key | `abc123def456` |
| `IFTTT_AC_ON_EVENT` | IFTTT AC on event name | `ac_on` |
| `IFTTT_AC_OFF_EVENT` | IFTTT AC off event name | `ac_off` |
| `HOME_LAT` | Home latitude | `40.7128` |
| `HOME_LON` | Home longitude | `-74.0060` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `EXTERNAL_URL` | External HA URL | `http://34.73.50.34:8123` |
| `WEBHOOK_URL` | AC Agent webhook URL | `http://34.73.50.34:8000/ping` |

### Docker Profiles

- **Cloud profile**: Includes Caddy reverse proxy for SSL
- **Local profile**: Simple local deployment
- **Monitoring profile**: Adds Prometheus/Grafana (optional)

## 🛠️ Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run AC Agent
uvicorn main:app --reload

# Run Home Assistant
docker run -d --name homeassistant \
  -p 8123:8123 \
  -v $(pwd)/homeassistant:/config \
  ghcr.io/home-assistant/home-assistant:stable
```

### Testing

```bash
# Run tests
python test_ac_standalone.py

# Test IFTTT connectivity
curl -X POST "https://maker.ifttt.com/trigger/ac_on/with/key/YOUR_KEY"
```

## 📊 Monitoring

### View Logs

```bash
# AC Agent logs
docker-compose logs -f smart-ac-agent

# Home Assistant logs  
docker-compose logs -f homeassistant

# All services
docker-compose logs -f
```

### Health Checks

- AC Agent: `http://your-server:8000/health`
- Home Assistant: `http://your-server:8123`

## 🔄 Migration

### Cloud to Local (Coral Dev Board)

```bash
./scripts/migrate-to-local.sh
```

This script:
- Backs up your configuration
- Switches to local profile
- Configures for Coral dev board deployment

## 🐛 Troubleshooting

### Common Issues

1. **AC Agent not starting**: Check OpenAI API key in `.env`
2. **IFTTT not triggering**: Verify webhook key and event names
3. **Location not updating**: Check Home Assistant mobile app permissions
4. **Automation not working**: Verify device tracker name in `configuration.yaml`

### Debug Commands

```bash
# Check service status
docker-compose ps

# Check AC Agent health
curl http://localhost:8000/health

# Test manual trigger
curl -X POST http://localhost:8000/ping \
  -H "Content-Type: application/json" \
  -d '{"lat": YOUR_LAT, "lon": YOUR_LON, "speed_mph": 0}'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Home Assistant team for excellent location tracking
- IFTTT for device integration
- OpenAI for AI decision making
- Docker for containerization

---

**🏠 Enjoy your smart, location-aware AC system!** 🌟 