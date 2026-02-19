#!/usr/bin/env python3

import json

import requests

# Configuration
SERVER_URL = "http://localhost:3000"

print("=" * 60)
print("🎵 Simple Song Generation Test")
print("=" * 60)

print("\n🔌 Connecting to Suno API at http://localhost:3000...")

# First check credits
try:
    response = requests.get(f"{SERVER_URL}/api/get_limit")
    if response.status_code == 200:
        credits = response.json()
        print(f"💰 Credits left: {credits['credits_left']}")
        print(f"📊 Monthly limit: {credits['monthly_limit']}")
    else:
        print(f"❌ Credit check failed: {response.status_code}")
        exit(1)
except Exception as e:
    print(f"❌ Error checking credits: {e}")
    exit(1)

print("\n🎼 Testing simple generation (no CAPTCHA)...")

# Try a simple generation request that might not trigger CAPTCHA
payload = {
    "prompt": "test simple melody",
    "make_instrumental": False,
    "wait_audio": False,
}

try:
    print("📤 Sending simple request...")
    response = requests.post(
        f"{SERVER_URL}/api/generate", json=payload, timeout=30  # Shorter timeout
    )

    print(f"📥 Response status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("✅ Generation successful!")
        print(f"Result: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Generation failed: {response.text}")

except requests.exceptions.Timeout:
    print("❌ Request timeout - CAPTCHA might be triggered")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
