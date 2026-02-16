"""
ระบบสมาชิกและประวัติเพลง — MuseGenx1000
ใช้ SQLite เก็บข้อมูลผู้ใช้ + ประวัติการสร้างเพลง + ระบบเลเวลสมาชิก + ระบบเหรียญ GG
"""
import sqlite3
import hashlib
import os
import time
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "musegenx1000.db")

# ===================== ระบบเหรียญ GG (GuiGit) =====================
# อัตราแลกเปลี่ยน: 1$ = 2 GG
# ค่าใช้จ่าย: 1 เพลง = 1 GG, 1 Instrumental = 1 GG
# เติมขั้นต่ำ: 10 GG ($5)

GG_RATE = 2          # 1$ = 2 GG
GG_COST_SONG = 1     # สร้างเพลง 1 เพลง = 1 GG
GG_COST_INST = 1     # สร้าง Instrumental 1 ชิ้น = 1 GG
GG_TOPUP_MIN = 10    # เติมขั้นต่ำ 10 GG

# ===================== ระบบเลเวลสมาชิก =====================
# เลเวล: free → basic → pro → admin
# แต่ละเลเวลมีสิทธิ์ใช้ฟีเจอร์ต่างกัน

LEVEL_CONFIG = {
    "free": {
        "label": "🆓 Free",
        "price_usd": 0,
        "gg_reward": 2,
        "allowed_modes": ["easy"],
        "features": {
            "easy_mode": True,
            "standard_mode": False,
            "advance_mode": False,
            "voice_clone": False,
            "llm_lyrics": False,
            "mix_master": False,
            "instrumental": True,
            "custom_tags": False,
        },
        "description": "โหมดง่ายเท่านั้น • ได้รับ 2 GG ฟรี",
    },
    "basic": {
        "label": "⭐ Basic",
        "price_usd": 20,
        "gg_reward": 40,
        "allowed_modes": ["easy", "standard"],
        "features": {
            "easy_mode": True,
            "standard_mode": True,
            "advance_mode": False,
            "voice_clone": False,
            "llm_lyrics": False,
            "mix_master": True,
            "instrumental": True,
            "custom_tags": True,
        },
        "description": "โหมดง่าย + มาตรฐาน • $20 → 40 GG • Mix & Master",
    },
    "pro": {
        "label": "💎 Pro",
        "price_usd": 45,
        "gg_reward": 90,
        "allowed_modes": ["easy", "standard", "advance"],
        "features": {
            "easy_mode": True,
            "standard_mode": True,
            "advance_mode": True,
            "voice_clone": True,
            "llm_lyrics": True,
            "mix_master": True,
            "instrumental": True,
            "custom_tags": True,
        },
        "description": "ทุกโหมด • $45 → 90 GG • Voice Clone • LLM Lyrics",
    },
    "admin": {
        "label": "👑 Admin",
        "price_usd": 0,
        "gg_reward": 0,
        "allowed_modes": ["easy", "standard", "advance"],
        "features": {
            "easy_mode": True,
            "standard_mode": True,
            "advance_mode": True,
            "voice_clone": True,
            "llm_lyrics": True,
            "mix_master": True,
            "instrumental": True,
            "custom_tags": True,
        },
        "description": "ทุกฟีเจอร์ • ไม่จำกัด GG • จัดการสมาชิก",
    },
}


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """สร้างตาราง users, song_history, gg_transactions ถ้ายังไม่มี + migration"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            email TEXT,
            level TEXT DEFAULT 'free',
            gg_balance REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            last_login TEXT
        );
        CREATE TABLE IF NOT EXISTS song_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            style TEXT,
            lyrics TEXT,
            audio_url TEXT,
            mode TEXT,
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS gg_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            tx_type TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    # Migration: เพิ่มคอลัมน์ level ถ้ายังไม่มี (สำหรับ DB เดิม)
    try:
        conn.execute("SELECT level FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN level TEXT DEFAULT 'free'")
        conn.commit()
    # Migration: เพิ่มคอลัมน์ gg_balance ถ้ายังไม่มี
    try:
        conn.execute("SELECT gg_balance FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN gg_balance REAL DEFAULT 0")
        conn.commit()
    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    """Hash password ด้วย SHA-256 + salt"""
    salt = "MuseGenx1000_salt_v1"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def register_user(username: str, password: str, display_name: str = "", email: str = "") -> tuple[bool, str]:
    """ลงทะเบียนผู้ใช้ใหม่ + ให้ GG ฟรีตามเลเวล Free"""
    if not username or not password:
        return False, "❌ กรุณากรอกชื่อผู้ใช้และรหัสผ่าน"
    if len(username) < 3:
        return False, "❌ ชื่อผู้ใช้ต้องมีอย่างน้อย 3 ตัวอักษร"
    if len(password) < 4:
        return False, "❌ รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร"
    free_gg = LEVEL_CONFIG["free"]["gg_reward"]
    conn = _get_conn()
    try:
        # ตรวจว่าเป็นผู้ใช้คนแรกหรือไม่ — ถ้าใช่ ตั้งเป็น Admin อัตโนมัติ
        existing_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        is_first_user = existing_count == 0
        initial_level = "admin" if is_first_user else "free"
        initial_gg = 9999 if is_first_user else free_gg

        conn.execute(
            "INSERT INTO users (username, password_hash, display_name, email, level, gg_balance) VALUES (?, ?, ?, ?, ?, ?)",
            (username.strip(), _hash_password(password), display_name.strip() or username, email.strip(), initial_level, initial_gg),
        )
        conn.commit()
        # บันทึก transaction GG ฟรี
        user_id = conn.execute("SELECT id FROM users WHERE username=?", (username.strip(),)).fetchone()["id"]
        conn.execute(
            "INSERT INTO gg_transactions (user_id, amount, tx_type, description) VALUES (?, ?, ?, ?)",
            (user_id, initial_gg, "signup_bonus", f"🎁 GG ฟรีจากการสมัคร ({initial_level} level)"),
        )
        conn.commit()
        if is_first_user:
            return True, f"✅ สมัครสำเร็จ! 👑 คุณเป็นผู้ใช้คนแรก — ได้รับสิทธิ์ Admin + {initial_gg} GG ฟรี! 🎉"
        return True, f"✅ สมัครสมาชิกสำเร็จ! ยินดีต้อนรับ {display_name or username} — ได้รับ {initial_gg} GG ฟรี! 🎉"
    except sqlite3.IntegrityError:
        return False, "❌ ชื่อผู้ใช้นี้ถูกใช้แล้ว กรุณาเลือกชื่ออื่น"
    finally:
        conn.close()


def login_user(username: str, password: str) -> tuple[int | None, str]:
    """ล็อกอิน คืน (user_id หรือ None, ข้อความ)"""
    if not username or not password:
        return None, "❌ กรุณากรอกชื่อผู้ใช้และรหัสผ่าน"
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, display_name FROM users WHERE username=? AND password_hash=?",
        (username.strip(), _hash_password(password)),
    ).fetchone()
    if row:
        conn.execute("UPDATE users SET last_login=datetime('now','localtime') WHERE id=?", (row["id"],))
        conn.commit()
        conn.close()
        return row["id"], f"✅ เข้าสู่ระบบสำเร็จ! สวัสดี {row['display_name']}"
    conn.close()
    return None, "❌ ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"


def save_song(user_id: int, title: str, style: str, lyrics: str, audio_url: str, mode: str = "", status: str = "completed"):
    """บันทึกประวัติเพลงที่สร้าง"""
    if not user_id:
        return
    conn = _get_conn()
    conn.execute(
        "INSERT INTO song_history (user_id, title, style, lyrics, audio_url, mode, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, title or "", style or "", lyrics or "", audio_url or "", mode or "", status),
    )
    conn.commit()
    conn.close()


def get_song_history(user_id: int, limit: int = 50) -> list[dict]:
    """ดึงประวัติเพลงของผู้ใช้ คืนเป็น list of dict"""
    if not user_id:
        return []
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, title, style, lyrics, audio_url, mode, status, created_at FROM song_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_stats(user_id: int) -> dict:
    """ดึงสถิติของผู้ใช้"""
    if not user_id:
        return {"total_songs": 0, "completed": 0, "failed": 0}
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM song_history WHERE user_id=?", (user_id,)).fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM song_history WHERE user_id=? AND status='completed'", (user_id,)).fetchone()[0]
    failed = conn.execute("SELECT COUNT(*) FROM song_history WHERE user_id=? AND status='failed'", (user_id,)).fetchone()[0]
    conn.close()
    return {"total_songs": total, "completed": completed, "failed": failed}


def get_user_info(user_id: int) -> dict | None:
    """ดึงข้อมูลผู้ใช้ (รวม level + gg_balance)"""
    if not user_id:
        return None
    conn = _get_conn()
    row = conn.execute("SELECT id, username, display_name, email, level, gg_balance, created_at, last_login FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    info = dict(row)
    # เพิ่ม level config เข้าไปด้วย
    lvl = info.get("level") or "free"
    info["level_config"] = LEVEL_CONFIG.get(lvl, LEVEL_CONFIG["free"])
    info["gg_balance"] = info.get("gg_balance") or 0
    return info


def delete_song(user_id: int, song_id: int) -> bool:
    """ลบเพลงจากประวัติ"""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM song_history WHERE id=? AND user_id=?", (song_id, user_id))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ===================== ฟังก์ชันเลเวลสมาชิก =====================

def get_user_level(user_id: int) -> str:
    """ดึงเลเวลของผู้ใช้"""
    if not user_id:
        return "free"
    conn = _get_conn()
    row = conn.execute("SELECT level FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return (row["level"] if row else "free") or "free"


def set_user_level(user_id: int, level: str) -> tuple[bool, str]:
    """กำหนดเลเวลให้ผู้ใช้ + ให้ GG ตามแพ็กเกจ"""
    if level not in LEVEL_CONFIG:
        return False, f"❌ เลเวล '{level}' ไม่ถูกต้อง (ใช้ได้: {', '.join(LEVEL_CONFIG.keys())})"
    conn = _get_conn()
    cur = conn.execute("UPDATE users SET level=? WHERE id=?", (level, user_id))
    conn.commit()
    conn.close()
    if cur.rowcount > 0:
        config = LEVEL_CONFIG[level]
        label = config["label"]
        gg_reward = config.get("gg_reward", 0)
        if gg_reward > 0:
            add_gg(user_id, gg_reward, "level_upgrade", f"🎁 GG จากอัพเกรดเป็น {label}")
            return True, f"✅ เปลี่ยนเลเวลเป็น {label} + ได้รับ {gg_reward} GG"
        return True, f"✅ เปลี่ยนเลเวลเป็น {label} สำเร็จ"
    return False, "❌ ไม่พบผู้ใช้นี้"


def get_daily_usage(user_id: int) -> int:
    """นับจำนวนเพลงที่สร้างวันนี้"""
    if not user_id:
        return 0
    today = date.today().isoformat()
    conn = _get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM song_history WHERE user_id=? AND date(created_at)=?",
        (user_id, today),
    ).fetchone()[0]
    conn.close()
    return count


def get_total_usage(user_id: int) -> int:
    """นับจำนวนเพลงทั้งหมดที่สร้าง (ตลอดชีพ)"""
    if not user_id:
        return 0
    conn = _get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM song_history WHERE user_id=?",
        (user_id,),
    ).fetchone()[0]
    conn.close()
    return count


# ===================== ฟังก์ชัน GG (GuiGit) =====================

def get_gg_balance(user_id: int) -> float:
    """ดึงยอด GG ของผู้ใช้"""
    if not user_id:
        return 0
    conn = _get_conn()
    row = conn.execute("SELECT gg_balance FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return (row["gg_balance"] if row else 0) or 0


def deduct_gg(user_id: int, amount: float, description: str = "") -> tuple[bool, str]:
    """หัก GG จากผู้ใช้ คืน (สำเร็จ?, ข้อความ)"""
    if not user_id:
        return False, "❌ ไม่พบ user_id"
    # Admin ไม่หัก GG
    level = get_user_level(user_id)
    if level == "admin":
        return True, "✅ Admin — ไม่หัก GG"
    conn = _get_conn()
    balance = conn.execute("SELECT gg_balance FROM users WHERE id=?", (user_id,)).fetchone()
    if not balance:
        conn.close()
        return False, "❌ ไม่พบผู้ใช้"
    current = balance["gg_balance"] or 0
    if current < amount:
        conn.close()
        return False, f"⚠️ GG ไม่เพียงพอ (มี {current:.0f} GG ต้องการ {amount:.0f} GG) — เติม GG เพื่อสร้างเพลงต่อ"
    new_balance = current - amount
    conn.execute("UPDATE users SET gg_balance=? WHERE id=?", (new_balance, user_id))
    conn.execute(
        "INSERT INTO gg_transactions (user_id, amount, tx_type, description) VALUES (?, ?, ?, ?)",
        (user_id, -amount, "deduct", description or f"หัก {amount:.0f} GG"),
    )
    conn.commit()
    conn.close()
    return True, f"✅ หัก {amount:.0f} GG (เหลือ {new_balance:.0f} GG)"


def add_gg(user_id: int, amount: float, tx_type: str = "topup", description: str = "") -> tuple[bool, str]:
    """เติม GG ให้ผู้ใช้ คืน (สำเร็จ?, ข้อความ)"""
    if not user_id:
        return False, "❌ ไม่พบ user_id"
    conn = _get_conn()
    balance = conn.execute("SELECT gg_balance FROM users WHERE id=?", (user_id,)).fetchone()
    if not balance:
        conn.close()
        return False, "❌ ไม่พบผู้ใช้"
    current = balance["gg_balance"] or 0
    new_balance = current + amount
    conn.execute("UPDATE users SET gg_balance=? WHERE id=?", (new_balance, user_id))
    conn.execute(
        "INSERT INTO gg_transactions (user_id, amount, tx_type, description) VALUES (?, ?, ?, ?)",
        (user_id, amount, tx_type, description or f"เติม {amount:.0f} GG"),
    )
    conn.commit()
    conn.close()
    return True, f"✅ เติม {amount:.0f} GG สำเร็จ (ยอดใหม่ {new_balance:.0f} GG)"


def topup_gg(user_id: int, gg_amount: float) -> tuple[bool, str]:
    """เติม GG ด้วยเงิน (ขั้นต่ำ 10 GG = $5)"""
    if not user_id:
        return False, "❌ กรุณาเข้าสู่ระบบก่อน"
    if gg_amount < GG_TOPUP_MIN:
        return False, f"❌ เติมขั้นต่ำ {GG_TOPUP_MIN} GG (= ${GG_TOPUP_MIN / GG_RATE:.0f})"
    usd_cost = gg_amount / GG_RATE
    return add_gg(user_id, gg_amount, "topup", f"💰 เติม {gg_amount:.0f} GG (${usd_cost:.2f})")


def get_gg_transactions(user_id: int, limit: int = 30) -> list[dict]:
    """ดึงประวัติ GG transaction"""
    if not user_id:
        return []
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, amount, tx_type, description, created_at FROM gg_transactions WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_gg_balance(user_id: int, cost: float = 1) -> tuple[bool, str]:
    """
    ตรวจสอบว่ามี GG เพียงพอสำหรับสร้างเพลงหรือไม่
    คืน (เพียงพอ?, ข้อความ)
    """
    if not user_id:
        return False, "❌ กรุณาเข้าสู่ระบบก่อนใช้งาน"
    # Admin ไม่จำกัด
    level = get_user_level(user_id)
    if level == "admin":
        return True, "✅ Admin — ไม่จำกัด GG"
    balance = get_gg_balance(user_id)
    if balance < cost:
        return False, f"⚠️ GG ไม่เพียงพอ (มี {balance:.0f} GG ต้องการ {cost:.0f} GG) — เติม GG ที่แท็บ 💰 เติม GG"
    return True, f"✅ มี {balance:.0f} GG (ใช้ {cost:.0f} GG)"


def check_permission(user_id: int, feature: str) -> tuple[bool, str]:
    """
    ตรวจสอบสิทธิ์การใช้ฟีเจอร์ตามเลเวล
    feature: easy_mode, standard_mode, advance_mode, voice_clone, llm_lyrics, mix_master, instrumental, custom_tags
    คืน (อนุญาต?, ข้อความ)
    """
    if not user_id:
        return False, "❌ กรุณาเข้าสู่ระบบก่อนใช้งาน"

    level = get_user_level(user_id)
    config = LEVEL_CONFIG.get(level, LEVEL_CONFIG["free"])

    # ตรวจสอบว่าเลเวลนี้มีฟีเจอร์นี้หรือไม่
    if not config["features"].get(feature, False):
        need_level = _min_level_for_feature(feature)
        need_label = LEVEL_CONFIG[need_level]["label"] if need_level else "?"
        return False, f"🔒 ฟีเจอร์นี้ต้องการเลเวล {need_label} ขึ้นไป (คุณเป็น {config['label']})"

    return True, "✅"


def check_daily_limit(user_id: int) -> tuple[bool, str]:
    """
    ตรวจสอบว่ามี GG เพียงพอสำหรับสร้างเพลง 1 เพลงหรือไม่
    (เปลี่ยนจากระบบ daily limit เป็นระบบ GG)
    คืน (สร้างได้?, ข้อความ)
    """
    return check_gg_balance(user_id, GG_COST_SONG)


def check_mode_permission(user_id: int, mode: str) -> tuple[bool, str]:
    """
    ตรวจสอบสิทธิ์การใช้โหมดตามเลเวล
    mode: easy, standard, advance
    คืน (อนุญาต?, ข้อความ)
    """
    mode_feature_map = {
        "easy": "easy_mode",
        "standard": "standard_mode",
        "advance": "advance_mode",
    }
    feature = mode_feature_map.get(mode, mode)
    return check_permission(user_id, feature)


def _min_level_for_feature(feature: str) -> str:
    """หาเลเวลต่ำสุดที่มีฟีเจอร์นี้"""
    for lvl in ["free", "basic", "pro", "admin"]:
        if LEVEL_CONFIG[lvl]["features"].get(feature, False):
            return lvl
    return "admin"


def get_level_info(level: str) -> dict:
    """ดึงข้อมูล config ของเลเวล"""
    return LEVEL_CONFIG.get(level, LEVEL_CONFIG["free"])


def get_all_levels() -> dict:
    """ดึงข้อมูลทุกเลเวล"""
    return LEVEL_CONFIG


def get_all_users(limit: int = 100) -> list[dict]:
    """ดึงข้อมูลผู้ใช้ทั้งหมด (สำหรับ admin)"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, username, display_name, email, level, gg_balance, created_at, last_login FROM users ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def build_level_badge(level: str) -> str:
    """สร้าง badge HTML สำหรับแสดงเลเวล"""
    config = LEVEL_CONFIG.get(level, LEVEL_CONFIG["free"])
    colors = {
        "free": "#6b7280",
        "basic": "#3b82f6",
        "pro": "#8b5cf6",
        "admin": "#f59e0b",
    }
    color = colors.get(level, "#6b7280")
    return f'<span style="padding:2px 10px;border-radius:8px;font-size:12px;font-weight:600;background:{color};color:#fff;">{config["label"]}</span>'


# สร้างตารางอัตโนมัติเมื่อ import
init_db()


# ===================== CLI: ตั้ง Admin จาก Terminal =====================
if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "promote":
        target = sys.argv[2] if len(sys.argv) >= 3 else None
        if not target:
            print("❌ กรุณาระบุ username: python user_db.py promote <username>")
            sys.exit(1)
        conn = _get_conn()
        row = conn.execute("SELECT id, display_name, level FROM users WHERE username=?", (target.strip(),)).fetchone()
        if not row:
            print(f"❌ ไม่พบผู้ใช้ '{target}'")
            conn.close()
            sys.exit(1)
        conn.execute("UPDATE users SET level='admin', gg_balance=9999 WHERE id=?", (row["id"],))
        conn.commit()
        conn.close()
        print(f"✅ ตั้ง {row['display_name']} (@{target}) เป็น Admin สำเร็จ! 👑")
    elif len(sys.argv) >= 2 and sys.argv[1] == "list":
        conn = _get_conn()
        rows = conn.execute("SELECT username, display_name, level, gg_balance FROM users ORDER BY id").fetchall()
        conn.close()
        if not rows:
            print("💭 ยังไม่มีสมาชิก — สมัครคนแรกจะได้เป็น Admin อัตโนมัติ")
        else:
            print(f"👥 สมาชิกทั้งหมด {len(rows)} คน:")
            for r in rows:
                print(f"  @{r['username']:15s}  {r['display_name']:15s}  [{r['level']:5s}]  {r['gg_balance']:.0f} GG")
    else:
        print("วิธีใช้:")
        print("  python user_db.py promote <username>  — ตั้งผู้ใช้เป็น Admin")
        print("  python user_db.py list                — ดูรายชื่อสมาชิกทั้งหมด")
