import math
import os
import time
import logging
from collections import deque
from datetime import datetime, timedelta
import requests
from fastapi import FastAPI, Request
from agents import Agent, Runner, function_tool

# LangSmith tracing
from langsmith import traceable
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
IFTTT_KEY = os.getenv("IFTTT_KEY")
IFTTT_AC_ON_EVENT = os.getenv("IFTTT_AC_ON_EVENT", "ac_on")
IFTTT_AC_OFF_EVENT = os.getenv("IFTTT_AC_OFF_EVENT", "ac_off")

# LangSmith configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "smart-ac-agent")

HOME = (float(os.getenv("HOME_LAT")), float(os.getenv("HOME_LON")))

EARTH_RADIUS_MI = 3958.8

# Location history tracking
HISTORY_RETENTION_MINUTES = 30  # Keep location history for 30 minutes
MIN_SAMPLES_FOR_TREND = 2  # Need at least 2 samples to determine trend
location_history = deque()

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

@traceable(name="determine_movement_trend")
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

@function_tool
def ac_on():
    """Turn AC on using IFTTT webhook."""
    logger.info("🔥 AC ON decision triggered")
    
    @traceable(name="ac_control_on")
    def execute_ac_on():
        if not IFTTT_KEY:
            logger.error("IFTTT key not configured")
            return {"error": "IFTTT key not configured", "status": "error"}
        
        try:
            response = requests.post(
                f"https://maker.ifttt.com/trigger/{IFTTT_AC_ON_EVENT}/with/key/{IFTTT_KEY}",
                json={"value1": "location_triggered"}
            )
            response.raise_for_status()
            logger.info("✅ AC turned on successfully via IFTTT")
            
            return {
                "status": "success",
                "message": "AC turned on via IFTTT",
                "ifttt_response_code": response.status_code,
                "ifttt_response": response.text,
                "action": "turn_ac_on",
                "trigger": "location_based_automation"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to turn on AC: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to turn on AC"
            }
    
    result = execute_ac_on()
    if result["status"] == "error" and "error" in result:
        return result["error"]
    return "AC turned on via IFTTT"

@function_tool
def ac_off():
    """Turn AC off using IFTTT webhook."""
    logger.info("❄️ AC OFF decision triggered")
    
    @traceable(name="ac_control_off")
    def execute_ac_off():
        if not IFTTT_KEY:
            logger.error("IFTTT key not configured")
            return {"error": "IFTTT key not configured", "status": "error"}
        
        try:
            response = requests.post(
                f"https://maker.ifttt.com/trigger/{IFTTT_AC_OFF_EVENT}/with/key/{IFTTT_KEY}",
                json={"value1": "location_triggered"}
            )
            response.raise_for_status()
            logger.info("✅ AC turned off successfully via IFTTT")
            
            return {
                "status": "success",
                "message": "AC turned off via IFTTT",
                "ifttt_response_code": response.status_code,
                "ifttt_response": response.text,
                "action": "turn_ac_off",
                "trigger": "location_based_automation"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to turn off AC: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to turn off AC"
            }
    
    result = execute_ac_off()
    if result["status"] == "error" and "error" in result:
        return result["error"]
    return "AC turned off via IFTTT"

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

app = FastAPI()
runner = Runner()

@app.post("/ping")
@traceable(name="location_ping")
async def ping(req: Request):
    payload = await req.json()
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
    
    # Predict what the agent should do for logging
    predicted_action = "no_action"
    if dist < 0.25:
        predicted_action = "no_action (already home)"
    elif 0.25 <= dist <= 2 and movement_trend == "approaching":
        predicted_action = "turn_ac_on (approaching home)"
    elif dist > 2 or movement_trend == "moving_away":
        predicted_action = "turn_ac_off (far from home or moving away)"
    elif movement_trend in ["unknown", "stationary"]:
        predicted_action = "no_action (conservative - unknown movement)"
    
    logger.info(f"🤖 Predicted action: {predicted_action}")
    
    # Run the agent with enhanced tracing
    @traceable(name="agent_decision")
    async def run_agent_decision():
        try:
            # This will trigger the agent's decision-making process
            agent_result = await runner.run(agent, str(obs))
            
            # Log the agent's decision
            logger.info(f"🤖 Agent decision completed")
            
            return {
                "agent_result": "Decision completed",
                "location_distance": dist,
                "movement_trend": movement_trend,
                "predicted_action": predicted_action,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Agent decision failed: {e}")
            raise e
    
    await run_agent_decision()
    
    return {"status": "ok", **obs}

@app.post("/test")
async def test_endpoint():
    """Test endpoint that simulates a location update without requiring coordinates from Home Assistant."""
    logger.info("🧪 Test endpoint called - simulating location update")
    
    # Simulate a location 1.5 miles from home, approaching
    test_lat, test_lon = 37.7749, -122.4194  # Example coordinates
    test_speed = 25
    
    # Create test payload
    test_payload = {
        "lat": test_lat,
        "lon": test_lon,
        "speed_mph": test_speed
    }
    
    # Process the same way as normal ping
    loc = (test_payload["lat"], test_payload["lon"])
    speed_mph = test_payload.get("speed_mph", 0)
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
    
    # Run the agent decision
    @traceable(name="test_agent_decision")
    async def run_test_agent_decision():
        try:
            agent_result = await runner.run(agent, str(obs))
            logger.info(f"🤖 Test agent decision completed")
            return {
                "agent_result": "Test decision completed",
                "location_distance": dist,
                "movement_trend": movement_trend,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"❌ Test agent decision failed: {e}")
            raise e
    
    await run_test_agent_decision()
    
    return {
        "status": "test_ok", 
        "message": "Test endpoint processed successfully",
        "simulated_location": {"lat": test_lat, "lon": test_lon},
        **obs
    }
