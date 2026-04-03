#!/usr/bin/env python3

import os

import requests
from dotenv import load_dotenv

load_dotenv()

SUNO_SERVER_URL = os.getenv("SUNO_SERVER_URL", "http://localhost:3000")
SUNO_COOKIE = os.getenv("SUNO_COOKIE", "")


def verify_token():
    """Verify if the authentication token is valid"""

    print("=" * 50)
    print("🔑 Suno API Token Verification")
    print("=" * 50)

    if not SUNO_COOKIE:
        print("❌ Error: SUNO_COOKIE not configured")
        print("Please add SUNO_COOKIE=your_cookie_value to your .env file")
        return False

    print(f"\n🔌 Testing connection to: {SUNO_SERVER_URL}")
    print(f"🔐 Using cookie: {SUNO_COOKIE[:30]}...")

    try:
        headers = {"Cookie": SUNO_COOKIE}

        # Test credit endpoint
        response = requests.get(
            f"{SUNO_SERVER_URL}/api/get_limit", headers=headers, timeout=10
        )

        print(f"\n📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Token is VALID!")
            print(f"💰 Credits left: {data.get('credits_left')}")
            print(f"📈 Monthly limit: {data.get('monthly_limit')}")
            return True
        else:
            print("❌ Token validation failed")
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


if __name__ == "__main__":
    verify_token()
