import requests
import os
from dotenv import load_dotenv

load_dotenv()

SUNO_COOKIE = os.getenv("SUNO_COOKIE", "")
SUNO_SERVER_URL = os.getenv("SUNO_SERVER_URL", "http://localhost:3000")

def test_cookie():
    """ทดสอบ Suno Cookie"""
    
    print("=" * 60)
    print("🍪 Testing Suno Cookie")
    print("=" * 60)
    
    if not SUNO_COOKIE:
        print("\n❌ SUNO_COOKIE not found in .env")
        return False
    
    print(f"\nCookie preview: {SUNO_COOKIE[:60]}...")
    print(f"Cookie length: {len(SUNO_COOKIE)} characters")
    
    # ตรวจสอบรูปแบบ
    if "__client=" not in SUNO_COOKIE:
        print("\n⚠️  Warning: Cookie should contain '__client='")
    
    # Test connection
    print("\n🔌 Testing connection to Suno API...")
    print(f"Server URL: {SUNO_SERVER_URL}")
    
    try:
        headers = {"Cookie": SUNO_COOKIE}
        response = requests.get(
            f"{SUNO_SERVER_URL}/api/get_limit",
            headers=headers,
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Cookie is VALID!")
            print(f"💰 Credits left: {data.get('credits_left')}")
            print(f"📊 Monthly limit: {data.get('monthly_limit')}")
            print(f"📈 Monthly usage: {data.get('monthly_usage')}")
            print(f"\n🎉 Ready to generate music!")
            return True
        elif response.status_code == 401:
            print(f"\n❌ Cookie is EXPIRED or INVALID (401)")
            print("Please get a new cookie from suno.com")
            return False
        elif response.status_code == 422:
            print(f"\n❌ Token validation failed (422)")
            print("Cookie format might be incorrect")
            print(f"Response: {response.text}")
            return False
        else:
            print(f"\n⚠️  Unexpected status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Cannot connect to Suno Server")
        print(f"Server URL: {SUNO_SERVER_URL}")
        print(f"\n💡 Make sure Suno Server is running:")
        print(f"   cd suno-api")
        print(f"   npm start")
        print(f"\nError: {e}")
        return False
    except requests.exceptions.Timeout:
        print(f"\n❌ Connection timeout")
        print(f"Suno Server might be slow or not responding")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}")
        print(f"Details: {e}")
        return False

if __name__ == "__main__":
    print("\n🚀 Starting Suno Cookie Test...\n")
    result = test_cookie()
    
    if result:
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - You can now generate music!")
        print("=" * 60)
        print("\nNext step: python3 generate_luk_thung.py")
    else:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED - Please fix the issues above")
        print("=" * 60)
    
    exit(0 if result else 1)