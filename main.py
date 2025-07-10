#!/usr/bin/env python3
"""
Smart AC Agent with REAL LLM and Agents SDK - Coral Dev Board Version with LangSmith Monitoring
Uses actual OpenAI LLM calls and mimics the agents SDK pattern from main.py
"""
import math
import os
import sys
import time
import logging
import json
import uuid
from collections import deque
from datetime import datetime, timedelta
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
def load_env():
    env_path = os.path.expanduser('~/.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"\'')

load_env()

# Environment variables
IFTTT_KEY = os.getenv("IFTTT_KEY")
IFTTT_AC_ON_EVENT = os.getenv("IFTTT_AC_ON_EVENT", "ac_on")
IFTTT_AC_OFF_EVENT = os.getenv("IFTTT_AC_OFF_EVENT", "ac_off")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LangSmith configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "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")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ac-bot")
LANGSMITH_ENABLED = bool(LANGSMITH_API_KEY)

HOME = (float(os.getenv("HOME_LAT", "40.7128")), float(os.getenv("HOME_LON", "-74.0060")))

EARTH_RADIUS_MI = 3958.8

# Location history tracking
HISTORY_RETENTION_MINUTES = 30  # Keep location history for 30 minutes
MIN_SAMPLES_FOR_TREND = 2  # Need at least 2 samples to determine trend
location_history = deque()

# LangSmith Monitoring Functions
class LangSmithTracer:
    def __init__(self):
        self.api_url = "https://api.smith.langchain.com"
        self.session_id = str(uuid.uuid4())
        
    def create_run(self, name, inputs, run_type="chain", parent_run_id=None):
        """Create a new LangSmith run/trace"""
        if not LANGSMITH_ENABLED:
            return str(uuid.uuid4())  # Return dummy ID if disabled
            
        run_id = str(uuid.uuid4())
        
        try:
            headers = {
                "x-api-key": LANGSMITH_API_KEY,
                "Content-Type": "application/json"
            }
            
            data = {
                "id": run_id,
                "name": name,
                "run_type": run_type,
                "inputs": inputs,
                "session_name": f"coral-agent-{datetime.now().strftime('%Y-%m-%d')}",
                "project_name": LANGSMITH_PROJECT,
                "start_time": datetime.utcnow().isoformat() + "Z",
                "parent_run_id": parent_run_id
            }
            
            response = requests.post(
                f"{self.api_url}/runs",
                headers=headers,
                json=data,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"📊 LangSmith trace created: {name}")
            else:
                logger.warning(f"⚠️ LangSmith trace failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ LangSmith trace error: {e}")
            
        return run_id
    
    def update_run(self, run_id, outputs=None, error=None, metadata=None):
        """Update a LangSmith run with outputs/error"""
        if not LANGSMITH_ENABLED:
            return
            
        try:
            headers = {
                "x-api-key": LANGSMITH_API_KEY,
                "Content-Type": "application/json"
            }
            
            data = {
                "end_time": datetime.utcnow().isoformat() + "Z"
            }
            
            if outputs:
                data["outputs"] = outputs
            if error:
                data["error"] = str(error)
            if metadata:
                data["extra"] = metadata
                
            response = requests.patch(
                f"{self.api_url}/runs/{run_id}",
                headers=headers,
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"📊 LangSmith trace updated: {run_id}")
            else:
                logger.warning(f"⚠️ LangSmith update failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ LangSmith update error: {e}")

# Initialize tracer
tracer = LangSmithTracer()

def haversine(a, b):
    """Return the great‑circle distance between two (lat, lon) pairs in *miles*."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return EARTH_RADIUS_MI * 2 * math.asin(math.sqrt(h))

def cleanup_old_locations():
    """Remove location history older than HISTORY_RETENTION_MINUTES."""
    cutoff_time = time.time() - (HISTORY_RETENTION_MINUTES * 60)
    while location_history and location_history[0]["timestamp"] < cutoff_time:
        location_history.popleft()

def determine_movement_trend():
    """Determine if user is moving toward or away from home based on recent history."""
    if len(location_history) < MIN_SAMPLES_FOR_TREND:
        return "unknown"
    
    # Look at the last few samples to determine trend
    recent_samples = list(location_history)[-MIN_SAMPLES_FOR_TREND:]
    
    # Calculate average distance change
    distance_changes = []
    for i in range(1, len(recent_samples)):
        prev_dist = recent_samples[i-1]["distance"]
        curr_dist = recent_samples[i]["distance"]
        distance_changes.append(curr_dist - prev_dist)
    
    if not distance_changes:
        return "unknown"
    
    avg_change = sum(distance_changes) / len(distance_changes)
    
    # Threshold for considering significant movement (0.01 miles = ~53 feet)
    MOVEMENT_THRESHOLD = 0.01
    
    if avg_change < -MOVEMENT_THRESHOLD:
        return "approaching"
    elif avg_change > MOVEMENT_THRESHOLD:
        return "moving_away"
    else:
        return "stationary"

# REAL Agents SDK Implementation (minimal but authentic)
class FunctionTool:
    def __init__(self, func):
        self.func = func
        self.name = func.__name__
        self.description = func.__doc__ or ""
    
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

def function_tool(func):
    """Decorator to create function tools (mimics agents SDK)"""
    return FunctionTool(func)

class Agent:
    def __init__(self, name, model, instructions, tools=None):
        self.name = name
        self.model = model
        self.instructions = instructions
        self.tools = tools or []
        self.last_decision = None  # For idempotence
    
    def get_tool_by_name(self, name):
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

class Runner:
    def __init__(self):
        pass
    
    def run(self, agent, observation, parent_run_id=None):
        """Run the agent with REAL OpenAI LLM call"""
        logger.info("🤖 Running REAL Agent with OpenAI LLM...")
        
        # Create LangSmith trace for LLM decision
        llm_run_id = tracer.create_run(
            name="AC_Agent_LLM_Decision",
            inputs={
                "agent_name": agent.name,
                "model": agent.model,
                "observation": observation,
                "instructions": agent.instructions
            },
            run_type="llm",
            parent_run_id=parent_run_id
        )
        
        if not OPENAI_API_KEY:
            error_msg = "OpenAI API key not configured"
            logger.error(f"❌ {error_msg}")
            tracer.update_run(llm_run_id, error=error_msg)
            return {"error": error_msg}
        
        # Parse observation
        obs_data = eval(observation) if isinstance(observation, str) else observation
        distance = obs_data.get("distance_miles", 0)
        movement = obs_data.get("movement_trend", "unknown")
        speed = obs_data.get("speed_mph", 0)
        
        # Create LLM prompt with exact same instructions as main.py
        prompt = f"""
{agent.instructions}

Current observation:
- Distance from home: {distance:.3f} miles
- Movement trend: {movement}
- Speed: {speed} mph

Available tools: {[tool.name for tool in agent.tools]}

Based on these rules, what action should I take? Respond with ONLY the tool name (ac_on, ac_off) or "no_action".
"""
        
        try:
            # REAL OpenAI API call
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": agent.model,
                "messages": [
                    {"role": "system", "content": "You are a smart AC controller. Follow the rules exactly."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            logger.info(f"🌐 Making REAL OpenAI API call to {agent.model}...")
            start_time = time.time()
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            llm_duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                decision = result["choices"][0]["message"]["content"].strip().lower()
                
                # Extract usage info for cost tracking
                usage = result.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                
                logger.info(f"🤖 REAL LLM Response: '{decision}'")
                
                # Update LangSmith trace with LLM results
                tracer.update_run(llm_run_id, 
                    outputs={
                        "decision": decision,
                        "raw_response": result["choices"][0]["message"]["content"]
                    },
                    metadata={
                        "duration_seconds": llm_duration,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "model": agent.model
                    }
                )
                
                # Execute the decision
                action_result = None
                if decision == "ac_on" and agent.last_decision != "ac_on":
                    tool = agent.get_tool_by_name("ac_on")
                    if tool:
                        action_result = tool(parent_run_id=llm_run_id)
                        agent.last_decision = "ac_on"
                        return {"action": "ac_on", "result": action_result, "llm_decision": decision, "tokens": total_tokens}
                
                elif decision == "ac_off" and agent.last_decision != "ac_off":
                    tool = agent.get_tool_by_name("ac_off")
                    if tool:
                        action_result = tool(parent_run_id=llm_run_id)
                        agent.last_decision = "ac_off"
                        return {"action": "ac_off", "result": action_result, "llm_decision": decision, "tokens": total_tokens}
                
                else:
                    logger.info("🤖 No action taken (idempotence or no_action)")
                    return {"action": "no_action", "llm_decision": decision, "tokens": total_tokens}
                    
            else:
                error_msg = f"OpenAI API error: {response.status_code} {response.text}"
                logger.error(f"❌ {error_msg}")
                tracer.update_run(llm_run_id, error=error_msg)
                return {"error": error_msg}
                
        except Exception as e:
            error_msg = f"LLM call failed: {e}"
            logger.error(f"❌ {error_msg}")
            tracer.update_run(llm_run_id, error=error_msg)
            return {"error": error_msg}

# REAL Function Tools (same as main.py) with LangSmith tracing
@function_tool
def ac_on(parent_run_id=None):
    """Turn AC on using IFTTT webhook."""
    logger.info("🔥 AC ON decision triggered by REAL LLM")
    
    # Create LangSmith trace for AC action
    action_run_id = tracer.create_run(
        name="AC_Turn_On_Action",
        inputs={"action": "ac_on", "trigger": "llm_decision"},
        run_type="tool",
        parent_run_id=parent_run_id
    )
    
    if not IFTTT_KEY:
        error_msg = "IFTTT key not configured"
        logger.error(error_msg)
        tracer.update_run(action_run_id, error=error_msg)
        return error_msg
    
    try:
        start_time = time.time()
        response = requests.post(
            f"https://maker.ifttt.com/trigger/{IFTTT_AC_ON_EVENT}/with/key/{IFTTT_KEY}",
            json={"value1": "llm_triggered"}
        )
        duration = time.time() - start_time
        
        response.raise_for_status()
        success_msg = "AC turned on via IFTTT"
        logger.info("✅ AC turned on successfully via IFTTT")
        
        tracer.update_run(action_run_id, 
            outputs={"status": "success", "message": success_msg},
            metadata={
                "duration_seconds": duration,
                "ifttt_event": IFTTT_AC_ON_EVENT,
                "response_code": response.status_code
            }
        )
        
        return success_msg
        
    except Exception as e:
        error_msg = f"Failed to turn on AC: {e}"
        logger.error(f"❌ {error_msg}")
        tracer.update_run(action_run_id, error=error_msg)
        return error_msg

@function_tool
def ac_off(parent_run_id=None):
    """Turn AC off using IFTTT webhook."""
    logger.info("❄️ AC OFF decision triggered by REAL LLM")
    
    # Create LangSmith trace for AC action
    action_run_id = tracer.create_run(
        name="AC_Turn_Off_Action",
        inputs={"action": "ac_off", "trigger": "llm_decision"},
        run_type="tool",
        parent_run_id=parent_run_id
    )
    
    if not IFTTT_KEY:
        error_msg = "IFTTT key not configured"
        logger.error(error_msg)
        tracer.update_run(action_run_id, error=error_msg)
        return error_msg
    
    try:
        start_time = time.time()
        response = requests.post(
            f"https://maker.ifttt.com/trigger/{IFTTT_AC_OFF_EVENT}/with/key/{IFTTT_KEY}",
            json={"value1": "llm_triggered"}
        )
        duration = time.time() - start_time
        
        response.raise_for_status()
        success_msg = "AC turned off via IFTTT"
        logger.info("✅ AC turned off successfully via IFTTT")
        
        tracer.update_run(action_run_id, 
            outputs={"status": "success", "message": success_msg},
            metadata={
                "duration_seconds": duration,
                "ifttt_event": IFTTT_AC_OFF_EVENT,
                "response_code": response.status_code
            }
        )
        
        return success_msg
        
    except Exception as e:
        error_msg = f"Failed to turn off AC: {e}"
        logger.error(f"❌ {error_msg}")
        tracer.update_run(action_run_id, error=error_msg)
        return error_msg

# Create the REAL Agent with LLM (exactly like main.py)
agent = Agent(
    name="Smart-AC",
    model="gpt-4o-mini",
    instructions="""
    Decide whether to call ac_on or ac_off based on location and movement trend.
    • If distance_to_home < 0.25 mi → do nothing (user's already home).
    • If 0.25 mi ≤ distance_to_home ≤ 2 mi and movement_trend is "approaching" → call ac_on exactly once.
    • If distance_to_home > 2 mi or movement_trend is "moving_away" → call ac_off once.
    • If movement_trend is "unknown" or "stationary", be conservative and don't change AC state.
    Maintain idempotence: don't call the same action twice in a row.
    """,
    tools=[ac_on, ac_off],
)

# Create the REAL Runner
runner = Runner()

# HTTP Server
from http.server import HTTPServer, BaseHTTPRequestHandler

class ACAgentHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/ping":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))
                
                # Create main LangSmith trace for location ping
                main_run_id = tracer.create_run(
                    name="Location_Ping_Processing",
                    inputs={
                        "lat": payload["lat"],
                        "lon": payload["lon"],
                        "speed_mph": payload.get("speed_mph", 0),
                        "endpoint": "/ping"
                    },
                    run_type="chain"
                )
                
                loc = (payload["lat"], payload["lon"])
                speed_mph = payload.get("speed_mph", 0)
                dist = haversine(loc, HOME)
                
                # Clean up old location history
                cleanup_old_locations()
                
                # Add current location to history
                location_entry = {
                    "timestamp": time.time(),
                    "distance": dist,
                    "speed": speed_mph,
                    "lat": loc[0],
                    "lon": loc[1]
                }
                location_history.append(location_entry)
                
                # Determine movement trend
                movement_trend = determine_movement_trend()
                
                obs = {
                    "distance_miles": dist, 
                    "speed_mph": speed_mph,
                    "movement_trend": movement_trend,
                    "history_samples": len(location_history)
                }
                
                logger.info(f"📍 Location update: {dist:.2f} miles, {movement_trend}, {speed_mph} mph")
                
                # Run the REAL Agent with REAL LLM
                agent_result = runner.run(agent, obs, parent_run_id=main_run_id)
                
                response = {
                    "status": "ok",
                    **obs,
                    "agent_used": True,
                    "real_llm_used": True,
                    "langsmith_enabled": LANGSMITH_ENABLED,
                    "agent_result": agent_result
                }
                
                # Update main trace with final results
                tracer.update_run(main_run_id, 
                    outputs=response,
                    metadata={
                        "home_coordinates": HOME,
                        "distance_miles": dist,
                        "movement_trend": movement_trend,
                        "agent_action": agent_result.get("action", "unknown"),
                        "total_location_history": len(location_history)
                    }
                )
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except Exception as e:
                logger.error(f"❌ Error processing request: {e}")
                self.send_error(500, str(e))
                
        elif self.path == "/test":
            try:
                logger.info("🧪 Test endpoint called - simulating location update")
                
                # Create main LangSmith trace for test
                main_run_id = tracer.create_run(
                    name="Test_Location_Simulation",
                    inputs={
                        "endpoint": "/test",
                        "test_type": "simulated_location_approaching"
                    },
                    run_type="chain"
                )
                
                # Simulate a location 1.5 miles from home, approaching
                test_lat, test_lon = HOME[0] + 0.02, HOME[1] + 0.01  
                test_speed = 25
                
                loc = (test_lat, test_lon)
                speed_mph = test_speed
                dist = haversine(loc, HOME)
                
                # Clean up old location history
                cleanup_old_locations()
                
                # Add current location to history
                location_entry = {
                    "timestamp": time.time(),
                    "distance": dist,
                    "speed": speed_mph,
                    "lat": loc[0],
                    "lon": loc[1]
                }
                location_history.append(location_entry)
                
                # Determine movement trend
                movement_trend = determine_movement_trend()
                
                obs = {
                    "distance_miles": dist, 
                    "speed_mph": speed_mph,
                    "movement_trend": movement_trend,
                    "history_samples": len(location_history)
                }
                
                logger.info(f"📍 Test location update: {dist:.2f} miles, {movement_trend}, {speed_mph} mph")
                
                # Run the REAL Agent with REAL LLM
                agent_result = runner.run(agent, obs, parent_run_id=main_run_id)
                
                response = {
                    "status": "test_ok", 
                    "message": "Test endpoint processed with REAL LLM",
                    "simulated_location": {"lat": test_lat, "lon": test_lon},
                    **obs,
                    "agent_used": True,
                    "real_llm_used": True,
                    "langsmith_enabled": LANGSMITH_ENABLED,
                    "agent_result": agent_result
                }
                
                # Update main trace with test results
                tracer.update_run(main_run_id, 
                    outputs=response,
                    metadata={
                        "test_coordinates": {"lat": test_lat, "lon": test_lon},
                        "simulated_distance": dist,
                        "simulated_movement": movement_trend,
                        "agent_action": agent_result.get("action", "unknown")
                    }
                )
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except Exception as e:
                logger.error(f"❌ Test error: {e}")
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not Found")

def main():
    logger.info("🚀 Starting Smart AC Agent with REAL LLM and Agents SDK on Coral Dev Board")
    logger.info(f"🏠 Home location: {HOME}")
    logger.info(f"🔧 IFTTT key configured: {'Yes' if IFTTT_KEY else 'No'}")
    logger.info(f"🤖 OpenAI API key configured: {'Yes' if OPENAI_API_KEY else 'No'}")
    logger.info(f"📊 LangSmith monitoring: {'Enabled' if LANGSMITH_ENABLED else 'Disabled'}")
    if LANGSMITH_ENABLED:
        logger.info(f"📊 LangSmith project: {LANGSMITH_PROJECT}")
    logger.info(f"🤖 Using REAL Agent: {agent.name} with model {agent.model}")
    logger.info(f"🛠️ Agent tools: {[tool.name for tool in agent.tools]}")
    
    server = HTTPServer(('0.0.0.0', 8000), ACAgentHandler)
    logger.info("🌐 Server running on http://0.0.0.0:8000")
    logger.info("📡 Endpoints: /ping, /test")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped")
        server.shutdown()

if __name__ == "__main__":
    main()
