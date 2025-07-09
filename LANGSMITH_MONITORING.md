# LangSmith Monitoring for Smart AC Agent

## 🔍 Why LangSmith for Your Smart AC Agent?

LangSmith is perfect for monitoring your smart AC agent because it:
- **Traces every decision** your agent makes
- **Monitors OpenAI API costs** and usage
- **Tracks performance** and response times
- **Provides real-time dashboards** for your agent's behavior
- **Alerts you** when things go wrong

## 🚀 Quick Setup (5 minutes)

### 1. Sign up for LangSmith
1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Create an account (free tier available)
3. Create a new project called "smart-ac-agent"

### 2. Get Your API Key
1. Go to Settings → API Keys
2. Create a new API key
3. Copy the key

### 3. Add to Your Environment
Add these to your `.env` file:

```env
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=smart-ac-agent
```

### 4. Restart Your Agent
```bash
docker-compose down && docker-compose up -d --build
```

## 📊 What You'll See in LangSmith

### **Real-time Monitoring:**
- Every location ping from your phone
- Distance calculations and movement trend detection
- AI agent decisions (turn AC on/off or do nothing)
- IFTTT webhook calls and responses

### **Example Trace:**
```
📍 Location Ping
├── 📏 Distance: 1.5 miles from home
├── 🏃 Movement: approaching
├── 🤖 AI Decision: Turn AC ON
└── 🔗 IFTTT: AC turned on successfully
```

### **Cost Tracking:**
- OpenAI API usage per decision
- Daily/weekly/monthly cost breakdown
- Token usage patterns

### **Performance Metrics:**
- Response time for each decision
- Success/failure rates
- Error tracking and alerts

## 🔧 Advanced Configuration

### Custom Metadata
The traces include rich metadata:
- **Location data**: lat/lon, distance, speed
- **Movement trends**: approaching/moving_away/stationary
- **History samples**: Number of location points used
- **Agent decisions**: What action was taken and why

### Error Monitoring
LangSmith automatically captures:
- OpenAI API errors
- IFTTT webhook failures
- Distance calculation issues
- Agent decision failures

### Performance Optimization
Use LangSmith to:
- Identify slow API calls
- Optimize your agent's instructions
- Monitor token usage efficiency
- Track decision accuracy

## 📱 Mobile Dashboard

LangSmith provides a mobile-friendly dashboard so you can:
- Monitor your AC agent from anywhere
- Get push notifications for errors
- See real-time location tracking
- View cost summaries

## 🚨 Alerts & Notifications

Set up alerts for:
- **High API costs** (e.g., >$5/day)
- **Failed AC control** (IFTTT errors)
- **Agent errors** (OpenAI API failures)
- **Unusual patterns** (too many AC toggles)

## 📈 Example Queries

In LangSmith, you can query:
- `"How many times did the AC turn on today?"`
- `"What's my average OpenAI cost per decision?"`
- `"Show me all failed IFTTT calls this week"`
- `"When was the last time I approached home?"`

## 🔄 Alternative Monitoring Options

If you don't want to use LangSmith:

### **Option 1: Built-in Logging**
Simple logging to files (already included):
```bash
docker-compose logs -f smart-ac-agent
```

### **Option 2: Prometheus + Grafana**
Use the existing monitoring stack:
- Metrics collection with Prometheus
- Dashboards with Grafana
- Custom alerts

### **Option 3: Webhook Notifications**
Send notifications to Slack/Discord:
- AC state changes
- Error alerts
- Daily summaries

## 🛠️ Troubleshooting

### Common Issues:
- **No traces appearing**: Check LANGSMITH_API_KEY is set
- **"Project not found"**: Ensure LANGSMITH_PROJECT matches your project name
- **Authentication errors**: Verify API key is valid

### Debug Mode:
Add to `.env`:
```env
LANGSMITH_TRACING=true
LANGSMITH_DEBUG=true
```

## 📞 Support

- **LangSmith Docs**: [docs.smith.langchain.com](https://docs.smith.langchain.com)
- **GitHub Issues**: Report issues with the smart AC agent
- **Community**: LangSmith Discord/Slack channels 