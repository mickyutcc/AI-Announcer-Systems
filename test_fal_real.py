import os
import sys
from unittest.mock import MagicMock


def main():
    mock_app = MagicMock()
    mock_app.FAL_KEY = os.getenv("FAL_KEY", "")
    mock_app.REQUEST_TIMEOUT = 30
    mock_app.MAX_POLL_SECONDS = 10
    mock_app.RETRY_DELAY = 2
    mock_app.ASSETS_DIR = "assets"
    sys.modules["app"] = mock_app

    from music_generator import _generate_fal_minimax

    print("Starting real FAL test...")
    res = _generate_fal_minimax(
        "test", "pop", "[Verse]\nTesting", "easy", dry_run=False
    )

    if res.get("ok"):
        print("SUCCESS: API call returned OK")
        if res.get("audio_url"):
            print(f"Audio URL: {res['audio_url']}")
        else:
            print(
                "Note: No audio_url yet (might be still processing or returned status only)"
            )
    else:
        print(f"FAILURE: {res.get('message')}")

    print("Result keys:", list(res.keys()))


if __name__ == "__main__":
    main()
