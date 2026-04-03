import os
import sys
from unittest.mock import MagicMock


def main():
    mock_app = MagicMock()
    mock_app.FAL_KEY = os.getenv("FAL_KEY", "")
    mock_app.REQUEST_TIMEOUT = 30
    mock_app.MAX_POLL_SECONDS = 120
    mock_app.RETRY_DELAY = 5
    mock_app.ASSETS_DIR = "assets"
    sys.modules["app"] = mock_app

    from music_generator import _generate_fal_minimax

    print("Starting real FAL test (valid prompt)...")
    res = _generate_fal_minimax(
        "Testing Song",
        "Pop Style music",
        "[Verse]\nTesting the system with a longer prompt.",
        "easy",
        dry_run=False,
    )

    if res.get("ok"):
        print("SUCCESS: API call returned OK")
        if res.get("audio_url"):
            print(f"Audio URL: {res['audio_url']}")
    else:
        print(f"FAILURE: {res.get('message')}")


if __name__ == "__main__":
    main()
