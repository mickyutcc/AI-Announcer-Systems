from voice_clone import generate_speech

if __name__ == "__main__":
    print("Testing Voice Clone...")
    test_text = "สวัสดีครับ นี่คือการทดสอบระบบเสียงภาษาไทยจาก ElevenLabs"
    result = generate_speech(test_text)
    if result.get("ok"):
        print(f"File created: {result['file']}")
        if result["file"].endswith(".wav"):
            print("✅ Output format is WAV")
        else:
            print(f"❌ Output format is NOT WAV (got {result['file']})")
    else:
        print(f"Error: {result.get('message')}")
