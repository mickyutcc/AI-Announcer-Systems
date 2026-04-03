
import time
import sys
from gradio_client import Client

def test_auth():
    print("Connecting to Gradio app...")
    try:
        # Connect to local Gradio instance inside the container (localhost:7860)
        client = Client("http://localhost:7860")
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    username = f"testuser_{int(time.time())}"
    password = "password123"
    display_name = "Test User"
    email = "test@example.com"

    print(f"\n--- Testing Signup for {username} ---")
    try:
        # fn_index might be needed if api_name doesn't work perfectly in all versions, 
        # but let's try api_name first.
        # Note: api_name should be used without leading slash in some versions, or with slash.
        # Let's try "signup" first.
        result = client.predict(
            username, 
            password, 
            password, # confirm
            display_name, 
            email, 
            api_name="/signup"
        )
        print(f"Signup Result: {result}")
        # result is [msg, success_modal_update, form_col_update]
        # We expect msg to contain "Registration Successful" or similar (in Thai/English)
        if "Successful" in str(result) or "เรียบร้อย" in str(result) or "สำเร็จ" in str(result):
            print("✅ Signup PASSED")
        else:
            print("❌ Signup FAILED")
    except Exception as e:
        print(f"❌ Signup Error: {e}")

    print(f"\n--- Testing Login for {username} ---")
    try:
        result = client.predict(
            username, 
            password, 
            api_name="/login"
        )
        # result is [user_state, login_view_update, dashboard_view_update, welcome_msg]
        # Note: gr.State might not be fully serialized in client output, so check other fields too.
        print(f"Login Result: {result}")
        
        # Check if welcome message (last element) contains our username or "ยินดีต้อนรับ"
        # Or check if result string contains username
        if username in str(result) or "ยินดีต้อนรับ" in str(result):
            print("✅ Login PASSED")
        else:
            print("❌ Login FAILED")
            
    except Exception as e:
        print(f"❌ Login Error: {e}")

    print(f"\n--- Testing Invalid Login ---")
    try:
        result = client.predict(
            username, 
            "wrongpassword", 
            api_name="/login"
        )
        print(f"Invalid Login Result: {result}")
        
        if "Please enter" in str(result) or "ไม่ถูกต้อง" in str(result) or "Invalid" in str(result) or "None" in str(result[0]):
            print("✅ Invalid Login Handling PASSED")
        else:
            print("❌ Invalid Login Handling FAILED")
            
    except Exception as e:
        print(f"❌ Invalid Login Error: {e}")

if __name__ == "__main__":
    test_auth()
