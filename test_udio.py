import requests
import os
from dotenv import load_dotenv

load_dotenv()

GOAPI_KEY = os.getenv("GOAPI_KEY","825fe0611d1c03f000af60764f73c337db1a270a140a09510e2a0fdb81a82ad")

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
    
    url = "https://api.goapi.ai/udio/v1/generate"
    
    headers = {
        "X-API-Key": GOAPI_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": "ลูกทุ่งไทย Thai folk acoustic guitar traditional",
        "lyrics": "[Verse 1]\nดอกไม้ที่บาน\nในสวนของเรา\n[Chorus]\nรักเธอนะ\nจะรักเธอตลอดไป",
        "tags": "ลูกทุ่ง, Thai folk, acoustic",
        "title": "Test Song"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Udio API is working!")
            print(f"Response: {data}")
            return True
        elif response.status_code == 401:
            print(f"\n❌ Invalid API Key")
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