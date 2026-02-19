import os
import sys
from unittest.mock import MagicMock


def main():
    mock_app = MagicMock()
    mock_app.FAL_KEY = os.getenv("FAL_KEY", "")
    mock_app.REQUEST_TIMEOUT = 30
    mock_app.ASSETS_DIR = "assets"
    mock_app.MUSIC_BACKEND = "fal"
    mock_app.SUNO_SERVER_URL = "http://localhost:3000"
    mock_app.SUNO_COOKIE = ""
    mock_app.SUNO_TIMEOUT = 30
    mock_app.DEFAULT_SUNO_RETRIES = 1
    mock_app.DEFAULT_SUNO_BACKOFF_BASE = 2
    mock_app.MAX_POLL_SECONDS = 120
    mock_app.RETRY_DELAY = 5
    mock_app.GOAPI_KEY = ""
    mock_app.GENERATE_URL = ""
    mock_app.FETCH_URL = ""
    mock_app.TWOCAPTCHA_KEY = ""

    sys.modules["app"] = mock_app

    import pprint

    from music_generator import _generate_fal_minimax, build_fal_payload

    u, h, p = build_fal_payload(
        "เทสลูกทุ่ง", "ลูกทุ่ง", "[Verse]\nเทสระบบ\n[Chorus]\nโอเค", "pro"
    )

    h_display = {
        k: ("<redacted>" if k.lower() == "authorization" else v) for k, v in h.items()
    }

    print("URL:", u)
    print("Headers (masked):")
    pprint.pprint(h_display)
    print("Prompt (first 300 chars):", p["prompt"][:300])
    print("Audio setting:", p["audio_setting"])

    print("\n-- dry_run via _generate_fal_minimax:")
    res = _generate_fal_minimax(
        "เทสลูกทุ่ง", "ลูกทุ่ง", "[Verse]\nเทสระบบ\n[Chorus]\nโอเค", "pro", dry_run=True
    )
    if "headers" in res and "Authorization" in res["headers"]:
        res["headers"]["Authorization"] = "<redacted>"
    print(res)


if __name__ == "__main__":
    main()
