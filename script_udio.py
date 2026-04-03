import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

GOAPI_KEY = os.getenv(
    "GOAPI_KEY", "825fe0611d1c03f000af60764f73c337db1a270a140a09510e2a0fdb81a82ad"
)
GOAPI_GENERATE_URL = os.getenv("GOAPI_GENERATE_URL", "https://api.piapi.ai/api/v1/task")
GOAPI_FETCH_URL = os.getenv("GOAPI_FETCH_URL", "https://api.piapi.ai/api/v1/task/")


def test_udio():
    """ทดสอบ Udio API"""

    print("=" * 60)
    print("🎵 Testing Udio API (GoAPI)")
    print("=" * 60)

    if not GOAPI_KEY:
        print("\n❌ GOAPI_KEY not found in .env")
        return False

    print(f"\nAPI Key: {GOAPI_KEY[:20]}...")

    # ทดสอบสร้างเพลง
    print("\n🎼 Generating test song...")

    url = GOAPI_GENERATE_URL
    fetch_url = GOAPI_FETCH_URL
    if not fetch_url.endswith("/"):
        fetch_url = fetch_url + "/"

    headers = {"x-api-key": GOAPI_KEY, "Content-Type": "application/json"}

    payload = {
        "model": "music-u",
        "task_type": "generate_music",
        "input": {
            "gpt_description_prompt": "ลูกทุ่งไทย Thai folk acoustic guitar traditional",
            "negative_tags": "",
            "lyrics_type": "user",
            "seed": -1,
            "lyrics": "[Verse 1]\nดอกไม้ที่บาน\nในสวนของเรา\n[Chorus]\nรักเธอนะ\nจะรักเธอตลอดไป",
        },
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        print(f"\n📥 Response status: {response.status_code}")

        if response.status_code in (200, 202):
            data = response.json()
            data_obj = data.get("data") if isinstance(data, dict) else None
            task_id = (
                (data_obj or {}).get("task_id")
                or (data or {}).get("task_id")
                or (data or {}).get("id")
            )
            if not task_id:
                print("\n✅ Udio API is working!")
                print(f"Response: {data}")
                return True
            print(f"\n🧩 Task ID: {task_id}")
            deadline = time.time() + 300
            while time.time() < deadline:
                pr = requests.get(f"{fetch_url}{task_id}", headers=headers, timeout=30)
                if pr.status_code != 200:
                    time.sleep(5)
                    continue
                pd = pr.json()
                data_pd = pd.get("data") if isinstance(pd, dict) else None
                status = (
                    (data_pd or {}).get("status") or pd.get("status") or pd.get("state")
                )
                if status in ("completed", "success", "done", "succeeded", "Completed"):
                    print("\n✅ Udio API is working!")
                    print(f"Response: {pd}")
                    return True
                if status in ("failed", "error"):
                    print("\n❌ Task failed")
                    print(f"Response: {pd}")
                    return False
                time.sleep(5)
            print("\n⚠️  Timeout")
            return False
        elif response.status_code == 401:
            print("\n❌ Invalid API Key")
            print("Please check your GOAPI_KEY in .env")
            return False
        else:
            print(f"\n⚠️  Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    test_udio()
