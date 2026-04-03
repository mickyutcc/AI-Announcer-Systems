content = r'''"""
Configuration file for MuseGenx1000 AI Music Studio
Contains all constants, API keys, and settings
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ==================== VERSION ====================
APP_VERSION = "v1.0.3 Beta"
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@musegen.ai")

# ==================== BACKEND ====================
MUSIC_BACKEND = os.getenv("MUSIC_BACKEND", "udio").lower().strip()
if MUSIC_BACKEND not in ("udio", "suno"):
    MUSIC_BACKEND = "udio"

# ==================== API KEYS ====================
GOAPI_KEY = os.getenv("GOAPI_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SUNO_COOKIE = os.getenv("SUNO_COOKIE", "")

# ==================== API ENDPOINTS ====================
GENERATE_URL = os.getenv("GOAPI_GENERATE_URL", "https://api.goapi.ai/api/v1/task")
FETCH_URL = os.getenv("GOAPI_FETCH_URL", "https://api.goapi.ai/api/v1/task/")
SUNO_SERVER_URL = os.getenv("SUNO_SERVER_URL", "http://localhost:3000")

# ==================== TIMEOUTS ====================
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_POLL_SECONDS = int(os.getenv("MAX_POLL_SECONDS", "300"))
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))
SUNO_TIMEOUT = int(os.getenv("SUNO_TIMEOUT", "120"))

# ==================== RETRY SETTINGS ====================
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "10"))

# ==================== GG COINS ====================
GG_RATE = 20  # 1$ = 20 GG
GG_COST_SONG = 6  # สร้าง 1 เพลง = 6 GG
GG_COST_INST = 3  # Instrumental = 3 GG
GG_TOPUP_MIN = 10  # เติมขั้นต่ำ 10 GG
GG_SIGNUP_BONUS = 9  # สมัครใหม่ได้ 9 GG

# ==================== LANGUAGE TAGS ====================
LANGUAGE_TAGS = {
    "thai": [
        "Thai", "Thai vocals", "ภาษาไทย",
        "native Thai pronunciation", "native Thai voice",
        "native accent", "Bangkok accent", "clear Thai diction"
    ],
    "english": [
        "English", "English vocals",
        "native English pronunciation", "native English voice", "native accent"
    ],
    "japanese": [
        "Japanese", "Japanese vocals",
        "native Japanese pronunciation", "native Japanese voice", "native accent"
    ],
    "korean": [
        "Korean", "Korean vocals",
        "native Korean pronunciation", "native Korean voice", "native accent"
    ],
    "chinese": [
        "Chinese", "Chinese vocals",
        "native Chinese pronunciation", "native Chinese voice", "native accent"
    ],
    "isan": [
        "Isan", "Isan vocals", "Luk Thung",
        "native Isan pronunciation", "native Isan voice", "native accent"
    ],
}

# ==================== NEGATIVE TAGS ====================
NEGATIVE_TAGS_DEFAULT = "instrumental,no vocals,bad audio,robotic,foreign accent,broken language"
NEGATIVE_TAGS_MODERN = (
    "retro,vintage,lo-fi,old school,noise,grain,1980s,1990s,low quality,muffled"
)
NEGATIVE_TAGS_ISAN = (
    "Chinese,Asian accent,Gibberish,Distortion,Muffled,Noise,Grainy"
)

# ==================== AI MODELS ====================
AI_MODEL_MAP = ["auto", "v1", "v1.5", "v2"]
DEFAULT_AI_MODEL = "v2"

LLM_MODELS = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"]
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.8
DEFAULT_MAX_TOKENS = 2000

# ==================== LYRICS MODES ====================
LYRICS_MODES = [
    "default", "romantic", "sad", "funny", "energetic",
    "long", "hiphop", "indie", "electronic", "classical"
]

# ==================== GENRE & MOOD ====================
GENRES = [
    "Pop", "Rock", "Hip-Hop", "R&B", "Electronic", "Dance", "EDM", "House",
    "Trance", "Reggae", "Country", "Folk", "Indie", "Acoustic", "Jazz",
    "Blues", "Classical", "Latin", "K-Pop", "J-Pop", "Thai Pop", "Metal",
    "Punk", "Soul", "Ambient", "Lo-fi", "Funk", "Disco",
    "ลูกทุ่ง", "หมอลำ"
]

MOODS = [
    "Energetic", "Romantic", "Melancholic", "Nostalgic", "Calm", "Playful",
    "Aggressive", "Happy", "Sad", "Hopeful", "Dreamy", "Mysterious",
    "Epic", "Warm", "Angry", "Reflective", "Tender"
]

VOCALIST_TYPES = [
    "Male", "Female", "Non-binary",
    "Transgender (M→F)", "Transgender (F→M)",
    "Androgynous", "Child", "Elderly", "Any"
]

# ==================== AUDIO LAB ====================
AUDIO_LAB_TASKS = [
    "ลดเสียงรบกวน (Noise Reduction)",
    "แยกเสียงร้อง (Vocal Separation - HQ)",
    "แยกเสียงร้อง (Vocal Isolation - Basic)",
    "ปรับเสียงให้ดังเท่ากัน (Normalize)",
    "ปรับเส้นเสียงให้คงที่ (Compressor)",
    "เพิ่มความใสของเสียง (Brightness)"
]

AUDIO_LAB_FOCUS = ["บาลานซ์", "ร้องเด่น", "ดนตรีเด่น"]

# ==================== PATHS ====================
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

# ==================== GRADIO SETTINGS ====================
GRADIO_SERVER_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
GRADIO_SERVER_NAME = "0.0.0.0"

# ==================== STARTUP LOG ====================
def print_config():
    """Print configuration on startup"""
    print(f"[CONFIG] 🎵 Music Backend: {MUSIC_BACKEND.upper()}")
    print(f"[CONFIG] API Key: {GOAPI_KEY[:8]}..." if GOAPI_KEY else "[CONFIG] ❌ No GOAPI_KEY")
    print(f"[CONFIG] OpenAI: {OPENAI_API_KEY[:8]}..." if OPENAI_API_KEY else "[CONFIG] ❌ No OPENAI_KEY")
    print(f"[CONFIG] Version: {APP_VERSION}")
    print(f"[CONFIG] Support: {SUPPORT_EMAIL}")

if __name__ == "__main__":
    print_config()
'''

with open("/Users/thanawin/Desktop/MuseGenx1000-Refactored/config.py", "w") as f:
    f.write(content)
