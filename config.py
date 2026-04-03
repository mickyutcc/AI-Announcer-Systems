"""
Configuration file for MuseGenx1000 AI Music Studio
Contains all constants, API keys, and settings
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ==================== VERSION ====================
APP_VERSION = "v1.0.3 Beta"
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@musegen.ai")

# ==================== EMAIL SETTINGS ====================
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_EMAIL)  # Default to SMTP_EMAIL if not set

# Aliases for compatibility
SMTP_HOST = SMTP_SERVER
SMTP_USER = SMTP_EMAIL
SMTP_PASS = SMTP_PASSWORD

# ==================== NOTIFICATION SETTINGS ====================
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# ==================== SECURITY SETTINGS ====================
AV_STRICT = os.getenv("AV_STRICT", "false").lower() == "true"

# ==================== STORAGE SETTINGS ====================
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local").lower()  # 'local' or 's3'
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", os.path.join(os.path.dirname(__file__), "assets"))
ASSETS_DIR = LOCAL_STORAGE_PATH  # Keep backward compatibility

# ==================== CACHE / REDIS ====================
REDIS_URL = os.getenv("REDIS_URL", "")  # e.g. redis://:pass@host:6379/0

# ==================== PAYMENTS (Future) ====================
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# ==================== BACKEND ====================
MUSIC_BACKEND = os.getenv("MUSIC_BACKEND", "udio").lower().strip()
if MUSIC_BACKEND not in ("udio", "suno", "fal", "minimax"):
    MUSIC_BACKEND = "udio"

# ==================== API KEYS ====================
GOAPI_KEY = os.getenv("GOAPI_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SUNO_COOKIE = os.getenv("SUNO_COOKIE", "")
TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_KEY", "")
FAL_KEY = os.getenv("FAL_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# ==================== API ENDPOINTS ====================
GENERATE_URL = os.getenv("GOAPI_GENERATE_URL", "https://api.goapi.ai/api/v1/task")
FETCH_URL = os.getenv("GOAPI_FETCH_URL", "https://api.goapi.ai/api/v1/task/")
SUNO_SERVER_URL = os.getenv("SUNO_SERVER_URL", "http://localhost:3000")

# ==================== TIMEOUTS ====================
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_POLL_SECONDS = int(os.getenv("MAX_POLL_SECONDS", "300"))
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))
SUNO_TIMEOUT = int(os.getenv("SUNO_TIMEOUT", "240"))

# ==================== RETRY SETTINGS ====================
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "10"))

# ==================== GG COINS ====================
GG_RATE = 20  # 1$ = 20 GG (Legacy)
GG_COST_SONG = 6  # Default cost (Full Song)
GG_COST_EASY = 6
GG_COST_STANDARD = 6
GG_COST_PRO = 6
GG_COST_INST = 3  # Instrumental (Standard & Pro only)
GG_COST_TTS = 2  # Text-to-Speech
GG_TOPUP_MIN = 10  # เติมขั้นต่ำ 10 GG
TOPUP_PACKAGES = [
    {"key": "small", "label": "เล็ก (Small)", "gg": 10, "price_thb": 30, "bonus_pct": 0.0},
    {"key": "starter", "label": "เริ่มต้น (Starter)", "gg": 30, "price_thb": 90, "bonus_pct": 0.0},
    {"key": "popular", "label": "ยอดนิยม (Popular)", "gg": 100, "price_thb": 300, "bonus_pct": 0.1},
    {"key": "value", "label": "คุ้มค่า (Value)", "gg": 500, "price_thb": 1400, "bonus_pct": 0.12},
    {"key": "power", "label": "จัดเต็ม (Power)", "gg": 1500, "price_thb": 3900, "bonus_pct": 0.15},
]
FIRST_TOPUP_BONUS_PCT = 0.1
GG_SIGNUP_BONUS = 9  # สมัครใหม่ได้ 9 GG (Easy Plan)

# ==================== PLANS ====================
PLANS = {
    "easy": {
        "name": "Easy Plan (เริ่มต้น)",
        "desc": "ฟรี 9 GG เติมเงินได้ตลอดเวลา",
        "price_thb": "เติมเงินตามจริง",
        "gg_amount": "เริ่มด้วย 9 GG",
    },
    "standard": {
        "name": "Standard Plan (มาตรฐาน)",
        "desc": "คุ้มค่าที่สุดสำหรับครีเอเตอร์",
        "price_thb": 300,
        "gg_amount": 2000,  # 1800 + 200 bonus
        "label": "2,000 GG (1800 + 200 Bonus)",
    },
    "pro": {
        "name": "Pro Plan (มืออาชีพ)",
        "desc": "เข้าถึงทุกฟีเจอร์ระดับสตูดิโอ",
        "price_thb": 900,
        "gg_amount": 6900,
        "label": "6,900 GG",
    },
}

# ==================== LANGUAGE TAGS ====================
LANGUAGE_TAGS = {
    "thai": [
        "Thai",
        "Thai vocals",
        "ภาษาไทย",
        "native Thai pronunciation",
        "native Thai voice",
        "native accent",
        "Bangkok accent",
        "clear Thai diction",
    ],
    "english": [
        "English",
        "English vocals",
        "native English pronunciation",
        "native English voice",
        "native accent",
    ],
    "japanese": [
        "Japanese",
        "Japanese vocals",
        "native Japanese pronunciation",
        "native Japanese voice",
        "native accent",
    ],
    "korean": [
        "Korean",
        "Korean vocals",
        "native Korean pronunciation",
        "native Korean voice",
        "native accent",
    ],
    "chinese": [
        "Chinese",
        "Chinese vocals",
        "native Chinese pronunciation",
        "native Chinese voice",
        "native accent",
    ],
    "isan": [
        "Isan",
        "Isan vocals",
        "Luk Thung",
        "native Isan pronunciation",
        "native Isan voice",
        "native accent",
    ],
}

# ==================== NEGATIVE TAGS ====================
NEGATIVE_TAGS_DEFAULT = (
    "instrumental,no vocals,bad audio,robotic,foreign accent,broken language"
)
NEGATIVE_TAGS_MODERN = (
    "retro,vintage,lo-fi,old school,noise,grain,1980s,1990s,low quality,muffled"
)
NEGATIVE_TAGS_ISAN = "Chinese,Asian accent,Gibberish,Distortion,Muffled,Noise,Grainy"

# ==================== AI MODELS ====================
AI_MODEL_MAP = ["auto", "v1", "v1.5", "v2"]
DEFAULT_AI_MODEL = "v2"

LLM_MODELS = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"]
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.8
DEFAULT_MAX_TOKENS = 2000

# ==================== LYRICS MODES ====================
LYRICS_MODES = [
    "default",
    "romantic",
    "sad",
    "funny",
    "energetic",
    "long",
    "hiphop",
    "indie",
    "electronic",
    "classical",
]

# ==================== GENRE & MOOD ====================
GENRES = [
    ("ป๊อป", "Pop"),
    ("ร็อก", "Rock"),
    ("ฮิปฮอป", "Hip Hop"),
    ("อาร์แอนด์บี", "R&B"),
    ("อิเล็กทรอนิกส์", "Electronic"),
    ("แดนซ์", "Dance"),
    ("อีดีเอ็ม", "EDM"),
    ("เฮาส์", "House"),
    ("แทรนซ์", "Trance"),
    ("เร็กเก", "Reggae"),
    ("คันทรี", "Country"),
    ("โฟล์ค", "Folk"),
    ("อินดี้", "Indie"),
    ("อะคูสติก", "Acoustic"),
    ("แจ๊ส", "Jazz"),
    ("บลูส์", "Blues"),
    ("คลาสสิก", "Classical"),
    ("ละติน", "Latin"),
    ("เคป๊อป", "K-Pop"),
    ("เจป๊อป", "J-Pop"),
    ("ไทยป๊อป", "Thai Pop"),
    ("เมทัล", "Metal"),
    ("พังค์", "Punk"),
    ("โซล", "Soul"),
    ("แอมเบียนต์", "Ambient"),
    ("โลไฟ", "Lo-Fi"),
    ("ฟังก์", "Funk"),
    ("ดิสโก้", "Disco"),
    ("ลูกทุ่ง", "Luk Thung"),
    ("หมอลำ", "Mor Lam"),
]

MOODS = [
    ("คึกคัก / พลังเต็มร้อย", "Energetic"),
    ("โรแมนติก", "Romantic"),
    ("เศร้าสร้อย", "Melancholic"),
    ("โหยหาอดีต", "Nostalgic"),
    ("สงบ", "Calm"),
    ("ขี้เล่น", "Playful"),
    ("ดุดัน", "Aggressive"),
    ("มีความสุข / สนุกสนาน", "Happy"),
    ("เศร้า", "Sad"),
    ("มีความหวัง", "Hopeful"),
    ("ชวนฝัน", "Dreamy"),
    ("ลึกลับ", "Mysterious"),
    ("ยิ่งใหญ่", "Epic"),
    ("อบอุ่น", "Warm"),
    ("โกรธเกรี้ยว", "Angry"),
    ("ไตร่ตรอง", "Reflective"),
    ("อ่อนโยน", "Tender"),
]

VOCALIST_TYPES = [
    ("ชาย", "Male"),
    ("หญิง", "Female"),
    ("คู่ (Duet)", "Duet"),
    ("ประสานเสียง (Choir)", "Choir"),
    ("เด็ก", "Child"),
    ("ผู้สูงอายุ", "Elderly"),
    ("หุ่นยนต์", "Robot"),
    ("ไม่ระบุเพศ", "Non-binary"),
    ("ไม่ระบุ", "Unspecified"),
]

# ==================== AUDIO LAB ====================
AUDIO_LAB_TASKS = [
    "ลดเสียงรบกวน (Noise Reduction)",
    "แยกเสียงร้อง (Vocal Separation - HQ)",
    "แยกเสียงร้อง (Vocal Isolation - Basic)",
    "ปรับเสียงให้ดังเท่ากัน (Normalize)",
    "ปรับเส้นเสียงให้คงที่ (Compressor)",
    "เพิ่มความใสของเสียง (Brightness)",
]

AUDIO_LAB_FOCUS = ["บาลานซ์", "ร้องเด่น", "ดนตรีเด่น"]

# ==================== PATHS ====================
STATIC_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO_PATH = os.path.join(STATIC_ASSETS_DIR, "logo.png")
PAYMENT_QR_PATH = os.path.join(STATIC_ASSETS_DIR, "payment_qr.png")

# ASSETS_DIR is used for dynamic storage (proofs, songs) by legacy code
ASSETS_DIR = LOCAL_STORAGE_PATH

# ==================== GRADIO SETTINGS ====================
GRADIO_SERVER_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
GRADIO_SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")


# ==================== STARTUP LOG ====================
def print_config():
    """Print configuration on startup"""
    print(f"[CONFIG] 🎵 Music Backend: {MUSIC_BACKEND.upper()}")
    print(
        f"[CONFIG] API Key: {GOAPI_KEY[:8]}..."
        if GOAPI_KEY
        else "[CONFIG] ❌ No GOAPI_KEY"
    )
    print(
        f"[CONFIG] OpenAI: {OPENAI_API_KEY[:8]}..."
        if OPENAI_API_KEY
        else "[CONFIG] ❌ No OPENAI_KEY"
    )
    print(f"[CONFIG] Version: {APP_VERSION}")
    print(f"[CONFIG] Support: {SUPPORT_EMAIL}")


if __name__ == "__main__":
    print_config()
