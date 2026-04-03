import os
import sys
import time

import handlers


def run_test():
    print("🚀 Starting Full Loop Test Case (5 Loops)...")

    # 1. Initialize System
    print("Step 1: Initializing Handlers...")
    try:
        handlers.on_load()
        print("✅ Handlers initialized.")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # 2. Login as Admin (Default)
    print("Step 2: Authenticating as Test User...")

    test_user = f"test_user_{int(time.time())}"
    test_pass = "password123"

    print(f"Creating user: {test_user}")
    handlers.user_db.register_user(
        test_user, test_pass, "Test User", "test@example.com"
    )

    user_id, msg = handlers.user_db.login_user(test_user, test_pass)
    if not user_id:
        print(f"❌ Login failed: {msg}")
        return
    print(f"✅ Logged in as User ID: {user_id}")

    # Add credits for testing
    handlers.user_db.add_gg(user_id, 100, "test_init", "Test Credits")

    # Check initial balance
    initial_credits = handlers.get_credits(user_id)
    print(f"💰 Initial Balance: {initial_credits}")

    # 3. Run 5 Loops
    loops = 5
    success_count = 0

    for i in range(1, loops + 1):
        print("\n----------------------------------------")
        print(f"🔄 Loop {i}/{loops}: Generating Song...")

        prompt = f"Test Song {i} - Funky Beat"
        style = "Funk"
        lyrics = ""  # Easy mode doesn't use lyrics
        mode = "easy"

        start_time = time.time()

        try:
            # Call generation
            # generate_music(prompt, style, lyrics, mode, user_id)
            file_path, status_msg, audio_url = handlers.generate_music(
                prompt=prompt, style=style, lyrics=lyrics, mode=mode, user_id=user_id
            )

            duration = time.time() - start_time

            if file_path:
                print(f"✅ Loop {i} Success!")
                print(f"   - Time: {duration:.2f}s")
                print(f"   - File: {file_path}")
                print(f"   - URL: {audio_url}")
                print(f"   - Msg: {status_msg}")
                success_count += 1
            else:
                print(f"❌ Loop {i} Failed!")
                print(f"   - Time: {duration:.2f}s")
                print(f"   - Error: {status_msg}")

        except Exception as e:
            print(f"❌ Loop {i} Exception: {e}")
            import traceback

            traceback.print_exc()

        # Optional: Sleep briefly
        time.sleep(1)

    # 4. Final Report
    print("\n========================================")
    print("📊 Test Summary")
    print("========================================")
    print(f"Total Loops: {loops}")
    print(f"Success: {success_count}")
    print(f"Failed: {loops - success_count}")

    final_credits = handlers.get_credits(user_id)
    print(f"💰 Final Balance: {final_credits}")

    if success_count == loops:
        print("✅ PASSED: All loops completed successfully.")
    else:
        print("⚠️ WARNING: Some loops failed. Check logs.")


if __name__ == "__main__":
    # Ensure we are in the right directory for imports to work
    sys.path.append(os.getcwd())
    run_test()
