#!/usr/bin/env python3
"""Standalone test to turn on AC via IFTTT - no dependencies on agents module."""

import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get IFTTT key from environment variable
IFTTT_KEY = os.getenv("IFTTT_KEY")

def test_ac_on():
    """Test turning on the AC via IFTTT webhook."""
    if not IFTTT_KEY:
        print("❌ Error: IFTTT_KEY environment variable not set")
        print("Set it with: export IFTTT_KEY='your_key_here'")
        return
    
    print("🌡️  Turning on AC...")
    
    try:
        url = f"https://maker.ifttt.com/trigger/ac_on/with/key/{IFTTT_KEY}"
        response = requests.post(url)
        
        if response.status_code == 200:
            print("✅ AC turned on successfully!")
            print(f"Response: {response.text}")
        else:
            print(f"❌ Failed to turn on AC. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error turning on AC: {e}")

if __name__ == "__main__":
    test_ac_on() 