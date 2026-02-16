import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

SUNO_SERVER_URL = os.getenv("SUNO_SERVER_URL", "http://localhost:3000")
SUNO_COOKIE = os.getenv("SUNO_COOKIE", "")
TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_KEY", "")

def generate_luk_thung():
    """Generate Luk Thung song"""
    
    print("=" * 60)
    print("🎵 Luk Thung Song Generator")
    print("=" * 60)
    
    if not SUNO_COOKIE:
        print("❌ Error: SUNO_COOKIE not configured")
        print("Please update .env file with your Suno Cookie")
        return None
    
    print(f"\n📋 Configuration:")
    print(f"Server URL: {SUNO_SERVER_URL}")
    print(f"Cookie: {SUNO_COOKIE[:50]}...")
    print(f"2Captcha: {'✓ Configured' if TWOCAPTCHA_KEY else '✗ Not set'}")
    
    # ตรวจสอบ credits
    print(f"\n🔌 Connecting to Suno API at {SUNO_SERVER_URL}...")
    
    try:
        headers = {"Cookie": SUNO_COOKIE}
        response = requests.get(
            f"{SUNO_SERVER_URL}/api/get_limit",
            headers=headers,
            timeout=10
        )
        print(f"Credits check: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"💰 Credits left: {data.get('credits_left')}")
            print(f"📊 Monthly limit: {data.get('monthly_limit')}")
        else:
            print(f"⚠️  Warning: {response.text}")
            
    except Exception as e:
        print(f"❌ Failed to check credits: {e}")
        return None
    
    # สร้างเพลง
    print("\n🎼 Generating Luk Thung song...")
    
    payload = {
        "prompt": "ลูกทุ่ง, หมอลำ, Thai folk, acoustic guitar, traditional Thai instruments, male vocals",
        "make_instrumental": False,
        "wait_audio": False,
        "custom_mode": True,
        "mv": "chirp-v3-5",
        "input": {
            "gpt_description_prompt": "เพลงลูกทุ่งไทยสไตล์อีสาน มีเสียงแคน พิณ กลอง เนื้อหาเ���ี่ยวกับชีวิตชาวนา ความรัก ความคิดถึงบ้านเกิด",
            "tags": "ลูกทุ่ง, หมอลำ, Thai folk, Isan, traditional, male vocals, acoustic"
        }
    }
    
    # เพิ่ม TWOCAPTCHA_KEY ถ้ามี
    if TWOCAPTCHA_KEY:
        payload["twocaptcha_key"] = TWOCAPTCHA_KEY
        print("🔑 Using 2Captcha for CAPTCHA solving")
    
    print(f"\n📤 Sending request...")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        headers = {
            "Cookie": SUNO_COOKIE,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{SUNO_SERVER_URL}/api/generate",
            json=payload,
            headers=headers,
            timeout=120
        )
        
        print(f"\n📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Song generated successfully!")
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # แสดง Song IDs
            if isinstance(data, list):
                for song in data:
                    song_id = song.get('id', 'N/A')
                    print(f"\n🎵 Song ID: {song_id}")
                    print(f"   Status: {song.get('status', 'N/A')}")
            
            return data
        elif response.status_code == 422:
            print(f"\n❌ Token validation failed (422)")
            print(f"Response: {response.text}")
            print(f"\n💡 Troubleshooting:")
            print(f"1. Check if SUNO_COOKIE in .env matches suno-api/.env")
            print(f"2. Make sure Suno Server is running with the same cookie")
            print(f"3. Try restarting Suno Server")
            return None
        else:
            print(f"\n❌ Generation failed!")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timeout")
        print(f"The server took too long to respond")
        return None
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}")
        print(f"Details: {e}")
        return None

if __name__ == "__main__":
    print("\n")
    result = generate_luk_thung()
    
    if result:
        print("\n" + "=" * 60)
        print("✅ SUCCESS - Song generation completed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED - Please check the errors above")
        print("=" * 60)