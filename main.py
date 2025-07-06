import math
import os
import requests
from fastapi import FastAPI, Request
from agents import Agent, Runner, function_tool

# Environment variables
IFTTT_KEY = os.getenv("IFTTT_KEY")
IFTTT_AC_ON_EVENT = os.getenv("IFTTT_AC_ON_EVENT", "ac_on")
IFTTT_AC_OFF_EVENT = os.getenv("IFTTT_AC_OFF_EVENT", "ac_off")

HOME = (float(os.getenv("HOME_LAT")), float(os.getenv("HOME_LON")))

EARTH_RADIUS_MI = 3958.8

def haversine(a, b):
    """Return the great‑circle distance between two (lat, lon) pairs in *miles*."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return EARTH_RADIUS_MI * 2 * math.asin(math.sqrt(h))

@function_tool
def ac_on():
    """Turn AC on using IFTTT webhook."""
    if not IFTTT_KEY:
        return "IFTTT key not configured"
    
    response = requests.post(
        f"https://maker.ifttt.com/trigger/{IFTTT_AC_ON_EVENT}/with/key/{IFTTT_KEY}",
        json={"value1": "location_triggered"}
    )
    response.raise_for_status()
    return "AC turned on via IFTTT"

@function_tool
def ac_off():
    """Turn AC off using IFTTT webhook."""
    if not IFTTT_KEY:
        return "IFTTT key not configured"
    
    response = requests.post(
        f"https://maker.ifttt.com/trigger/{IFTTT_AC_OFF_EVENT}/with/key/{IFTTT_KEY}",
        json={"value1": "location_triggered"}
    )
    response.raise_for_status()
    return "AC turned off via IFTTT"

agent = Agent(
    name="Smart‑AC",
    model="gpt‑4o‑mini",
    instructions="""
    Decide whether to call ac_on or ac_off.
    • If distance_to_home < 0.25 mi → do nothing (user's already home).
    • If 0.25 mi ≤ distance_to_home ≤ 2 mi and distance is shrinking → call ac_on exactly once.
    • If distance_to_home > 2 mi or growing → call ac_off once.
    Maintain idempotence: don't call the same action twice in a row.
    """,
    tools=[ac_on, ac_off],
)

app = FastAPI()
runner = Runner(agent)

@app.post("/ping")
async def ping(req: Request):
    payload = await req.json()
    loc = (payload["lat"], payload["lon"])
    speed_mph = payload.get("speed_mph", 0)
    dist = haversine(loc, HOME)
    obs = {"distance_miles": dist, "speed_mph": speed_mph}
    runner.run_sync(input=str(obs))  # blocking is fine for a webhook‑style endpoint
    return {"status": "ok", **obs}
