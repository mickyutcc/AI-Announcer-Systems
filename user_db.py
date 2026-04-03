"""
ระบบสมาชิกและประวัติเพลง - MuseGenx1000
ใช้ SQLite เก็บข้อมูลผู้ใช้ + ประวัติการสร้างเพลง + ระบบเลเวลสมาชิก + ระบบเหรียญ GG
"""

import hashlib
import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

import config
import utils
from locales import t

DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "musegenx1000.db"))

# ===================== ระบบเหรียญ GG (GuiGit) =====================
# อัตราแลกเปลี่ยน: 1$ = 20 GG
# ค่าใช้จ่าย: 1 เพลง = 2 GG, 1 Instrumental = 1 GG
# เติมขั้นต่ำ: 10 GG

GG_RATE = config.GG_RATE
GG_COST_SONG = config.GG_COST_SONG
GG_COST_INST = config.GG_COST_INST
GG_TOPUP_MIN = config.GG_TOPUP_MIN

# ===================== ระบบเลเวลสมาชิก =====================
# เลเวล: free → basic → pro → admin
# แต่ละเลเวลมีสิทธิ์ใช้ฟีเจอร์ต่างกัน

LEVEL_CONFIG: dict[str, dict[str, Any]] = {
    "free": {
        "label": t("level_free_label"),
        "price_usd": 0,
        "gg_reward": config.GG_SIGNUP_BONUS,
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
        "description": t("level_free_desc"),
    },
    "basic": {
        "label": t("level_basic_label"),
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
        "description": t("level_basic_desc"),
    },
    "pro": {
        "label": t("level_pro_label"),
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
        "description": t("level_pro_desc"),
    },
    "admin": {
        "label": t("level_admin_label"),
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
        "description": t("level_admin_desc"),
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
            cost REAL,
            backend TEXT,
            request_id TEXT,
            credits_used REAL,
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS generation_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT,
            style TEXT,
            lyrics TEXT,
            mode TEXT,
            instrumental INTEGER DEFAULT 0,
            plan TEXT,
            cost REAL,
            backend TEXT,
            request_id TEXT,
            priority TEXT,
            status TEXT DEFAULT 'queued',
            eta_seconds INTEGER,
            audio_url TEXT,
            error_message TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS gg_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            tx_type TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'completed',
            proof_url TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT,
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
    # Migration: เพิ่มคอลัมน์ updated_at ใน gg_transactions
    try:
        conn.execute("SELECT updated_at FROM gg_transactions LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE gg_transactions ADD COLUMN updated_at TEXT")
        conn.commit()

    # Migration: เพิ่มคอลัมน์ membership_expiry ใน users
    try:
        conn.execute("SELECT membership_expiry FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN membership_expiry TEXT")
        conn.commit()
    try:
        conn.execute("SELECT cost FROM song_history LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE song_history ADD COLUMN cost REAL")
        conn.commit()
    try:
        conn.execute("SELECT backend FROM song_history LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE song_history ADD COLUMN backend TEXT")
        conn.commit()
    try:
        conn.execute("SELECT request_id FROM song_history LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE song_history ADD COLUMN request_id TEXT")
        conn.commit()
    try:
        conn.execute("SELECT credits_used FROM song_history LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE song_history ADD COLUMN credits_used REAL")
        conn.commit()

    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    """Hash password ด้วย SHA-256 + salt"""
    salt = "MuseGenx1000_salt_v1"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def register_user(
    username: str, password: str, display_name: str = "", email: str = ""
) -> tuple[bool, str]:
    """ลงทะเบียนผู้ใช้ใหม่ + ให้ GG ฟรีตามเลเวล Free"""
    if not username or not password:
        return False, t("err_missing_credentials")
    if len(username) < 3:
        return False, t("err_username_too_short")
    if len(password) < 4:
        return False, t("err_password_too_short")
    free_gg = LEVEL_CONFIG["free"]["gg_reward"]
    conn = _get_conn()
    try:
        # ตรวจว่าเป็นผู้ใช้คนแรกหรือไม่ - ถ้าใช่ ตั้งเป็น Admin อัตโนมัติ
        existing_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        is_first_user = existing_count == 0
        initial_level = "admin" if is_first_user else "free"
        initial_gg = 9999 if is_first_user else free_gg

        conn.execute(
            "INSERT INTO users (username, password_hash, display_name, email, level, gg_balance) VALUES (?, ?, ?, ?, ?, ?)",
            (
                username.strip(),
                _hash_password(password),
                display_name.strip() or username,
                email.strip(),
                initial_level,
                initial_gg,
            ),
        )
        conn.commit()
        # บันทึก transaction GG ฟรี
        user_id = conn.execute(
            "SELECT id FROM users WHERE username=?", (username.strip(),)
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO gg_transactions (user_id, amount, tx_type, description) VALUES (?, ?, ?, ?)",
            (
                user_id,
                initial_gg,
                "signup_bonus",
                f"🎁 GG ฟรีจากการสมัคร ({initial_level} level)",
            ),
        )
        conn.commit()
        if is_first_user:
            return (
                True,
                t("success_register_admin").format(gg=initial_gg),
            )
        return (
            True,
            t("success_register_user").format(name=display_name or username, gg=initial_gg),
        )
    except sqlite3.IntegrityError:
        return False, t("err_username_exists")
    finally:
        conn.close()


def login_user(username: str, password: str) -> tuple[int | None, str]:
    """ล็อกอิน คืน (user_id หรือ None, ข้อความ)"""
    print(f"DEBUG: login_user called with username='{username}', password='{password}'")
    if not username or not password:
        return None, t("err_missing_credentials")
    conn = _get_conn()
    hashed = _hash_password(password)
    print(f"DEBUG: hashed password: {hashed}")
    row = conn.execute(
        "SELECT id, display_name, password_hash FROM users WHERE username=?",
        (username.strip(),),
    ).fetchone()
    
    if row:
        print(f"DEBUG: Found user {username}, stored hash: {row['password_hash']}")
        if row['password_hash'] == hashed:
            conn.execute(
                "UPDATE users SET last_login=datetime('now','localtime') WHERE id=?",
                (row["id"],),
            )
            conn.commit()
            conn.close()
            return row["id"], f"✅ เข้าสู่ระบบสำเร็จ! สวัสดี {row['display_name']}"
        else:
            print("DEBUG: Password mismatch")
    else:
        print(f"DEBUG: User {username} not found")

    conn.close()
    return None, t("err_login_invalid")


def save_song(
    user_id: int,
    title: str,
    style: str,
    lyrics: str,
    audio_url: str,
    mode: str = "",
    status: str = "completed",
    cost: float | None = None,
    backend: str | None = None,
    request_id: str | None = None,
    credits_used: float | None = None,
):
    """บันทึกประวัติเพลงที่สร้าง"""
    if not user_id:
        return
    conn = _get_conn()
    conn.execute(
        "INSERT INTO song_history (user_id, title, style, lyrics, audio_url, mode, cost, backend, request_id, credits_used, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            title or "",
            style or "",
            lyrics or "",
            audio_url or "",
            mode or "",
            cost,
            backend,
            request_id,
            credits_used,
            status,
        ),
    )
    conn.commit()
    conn.close()


def get_song_history(user_id: int, limit: int = 50) -> list[dict]:
    """ดึงประวัติเพลงของผู้ใช้ คืนเป็น list of dict"""
    if not user_id:
        return []
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, title, style, lyrics, audio_url, mode, cost, backend, request_id, credits_used, status, created_at FROM song_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_stats(user_id: int) -> dict:
    """ดึงสถิติของผู้ใช้"""
    if not user_id:
        return {"total_songs": 0, "completed": 0, "failed": 0}
    conn = _get_conn()
    total = conn.execute(
        "SELECT COUNT(*) FROM song_history WHERE user_id=?", (user_id,)
    ).fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM song_history WHERE user_id=? AND status='completed'",
        (user_id,),
    ).fetchone()[0]
    failed = conn.execute(
        "SELECT COUNT(*) FROM song_history WHERE user_id=? AND status='failed'",
        (user_id,),
    ).fetchone()[0]
    conn.close()
    return {"total_songs": total, "completed": completed, "failed": failed}


def get_user_id(username: str) -> int | None:
    """ดึง user_id จาก username"""
    if not username:
        return None
    conn = _get_conn()
    row = conn.execute(
        "SELECT id FROM users WHERE username=?", (username.strip(),)
    ).fetchone()
    conn.close()
    return row["id"] if row else None


def get_user_info(user_id: int) -> dict | None:
    """ดึงข้อมูลผู้ใช้ (รวม level + gg_balance)"""
    if not user_id:
        return None
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, username, display_name, email, level, gg_balance, created_at, last_login, membership_expiry FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    info = dict(row)

    # Use effective level (checks expiry)
    effective_level = get_user_level(user_id)
    info["level"] = effective_level
    info["level_config"] = LEVEL_CONFIG.get(effective_level, LEVEL_CONFIG["free"])

    info["gg_balance"] = info.get("gg_balance") or 0
    return info


def delete_song(user_id: int, song_id: int) -> bool:
    """ลบเพลงจากประวัติ"""
    conn = _get_conn()
    cur = conn.execute(
        "DELETE FROM song_history WHERE id=? AND user_id=?", (song_id, user_id)
    )
    conn.commit()
    conn.close()
    rowcount_value = int(cur.rowcount or 0)
    return rowcount_value > 0


# ===================== ฟังก์ชันเลเวลสมาชิก =====================


def get_user_level(user_id: int) -> str:
    """ดึงเลเวลของผู้ใช้ (ตรวจสอบวันหมดอายุ)"""
    if not user_id:
        return "free"
    conn = _get_conn()
    row = conn.execute(
        "SELECT level, membership_expiry FROM users WHERE id=?", (user_id,)
    ).fetchone()
    conn.close()

    if not row:
        return "free"

    level = row["level"]
    expiry_str = row["membership_expiry"]

    # Admin never expires
    if level == "admin":
        return "admin"

    if level in ["basic", "pro"] and expiry_str:
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expiry:
                return "free"  # Expired
        except Exception as e:
            print(f"Error parsing expiry: {e}")

    return level or "free"


def set_user_level(user_id: int, level: str) -> tuple[bool, str]:
    """กำหนดเลเวลให้ผู้ใช้ + ให้ GG ตามแพ็กเกจ"""
    if level not in LEVEL_CONFIG:
        return (
            False,
            f"❌ เลเวล '{level}' ไม่ถูกต้อง (ใช้ได้: {', '.join(LEVEL_CONFIG.keys())})",
        )
    conn = _get_conn()
    cur = conn.execute("UPDATE users SET level=? WHERE id=?", (level, user_id))
    conn.commit()
    conn.close()
    if cur.rowcount > 0:
        config = LEVEL_CONFIG[level]
        label = str(config.get("label", ""))
        gg_reward_value = config.get("gg_reward", 0)
        if isinstance(gg_reward_value, (int, float)):
            gg_reward = float(gg_reward_value)
        else:
            gg_reward = 0.0
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
    row = conn.execute(
        "SELECT COUNT(*) FROM song_history WHERE user_id=? AND date(created_at)=?",
        (user_id, today),
    ).fetchone()
    conn.close()
    count_value = row[0] if row else 0
    return int(count_value or 0)


def get_total_usage(user_id: int) -> int:
    """นับจำนวนเพลงทั้งหมดที่สร้าง (ตลอดชีพ)"""
    if not user_id:
        return 0
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) FROM song_history WHERE user_id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    count_value = row[0] if row else 0
    return int(count_value or 0)


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
        return True, "✅ Admin - ไม่หัก GG"
    conn = _get_conn()
    balance = conn.execute(
        "SELECT gg_balance FROM users WHERE id=?", (user_id,)
    ).fetchone()
    if not balance:
        conn.close()
        return False, "❌ ไม่พบผู้ใช้"
    current = balance["gg_balance"] or 0
    if current < amount:
        conn.close()
        return (
            False,
            f"⚠️ GG ไม่เพียงพอ (มี {current:.0f} GG ต้องการ {amount:.0f} GG) - เติม GG เพื่อสร้างเพลงต่อ",
        )
    new_balance = current - amount
    conn.execute("UPDATE users SET gg_balance=? WHERE id=?", (new_balance, user_id))
    conn.execute(
        "INSERT INTO gg_transactions (user_id, amount, tx_type, description) VALUES (?, ?, ?, ?)",
        (user_id, -amount, "deduct", description or f"หัก {amount:.0f} GG"),
    )
    conn.commit()
    conn.close()

    # Low balance warning
    if new_balance < 100:
        # Check if email is valid (simple check)
        # We need to get email first. We can do this async or just try-except
        try:
            u_conn = _get_conn()
            u_row = u_conn.execute(
                "SELECT email FROM users WHERE id=?", (user_id,)
            ).fetchone()
            u_conn.close()
            email = u_row["email"] if u_row else ""
            if email and "@" in email:
                utils.send_email(
                    email,
                    "⚠️ Low Credit Alert - MuseGenx1000",
                    f"Your balance is running low ({new_balance:.0f} GG). Please top up soon!",
                )
        except Exception as e:
            print(f"Failed to send low balance email: {e}")

    return True, f"✅ หัก {amount:.0f} GG (เหลือ {new_balance:.0f} GG)"


def add_gg(
    user_id: int, amount: float, tx_type: str = "topup", description: str = ""
) -> tuple[bool, str]:
    """เติม GG ให้ผู้ใช้ คืน (สำเร็จ?, ข้อความ)"""
    if not user_id:
        return False, "❌ ไม่พบ user_id"
    conn = _get_conn()
    balance = conn.execute(
        "SELECT gg_balance FROM users WHERE id=?", (user_id,)
    ).fetchone()
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


def validate_and_reserve(
    user_id: int, cost: float, description: str
) -> tuple[bool, str, float | None]:
    if not user_id:
        return False, "❌ ไม่พบ user_id", None
    level = get_user_level(user_id)
    if level == "admin":
        return True, "✅ Admin - ไม่หัก GG", get_gg_balance(user_id)
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT gg_balance FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not row:
            conn.rollback()
            return False, "❌ ไม่พบผู้ใช้", None
        current = row["gg_balance"] or 0
        if current < cost:
            conn.rollback()
            return (
                False,
                f"⚠️ GG ไม่เพียงพอ (มี {current:.0f} GG ต้องการ {cost:.0f} GG) - เติม GG ที่แท็บ 💰 เติม GG",
                current,
            )
        new_balance = current - cost
        conn.execute("UPDATE users SET gg_balance=? WHERE id=?", (new_balance, user_id))
        conn.execute(
            "INSERT INTO gg_transactions (user_id, amount, tx_type, description) VALUES (?, ?, ?, ?)",
            (user_id, -cost, "reserve", description or f"Reserve {cost:.0f} GG"),
        )
        conn.commit()
        return True, f"✅ Reserved {cost:.0f} GG", new_balance
    except Exception as e:
        conn.rollback()
        return False, f"❌ Reserve failed: {e}", None
    finally:
        conn.close()


def validate_topup_amount(amount_gg: int) -> tuple[bool, str]:
    if amount_gg is None:
        return False, "Amount missing"
    if not isinstance(amount_gg, int):
        return False, "Amount must be integer GG"
    if amount_gg < GG_TOPUP_MIN:
        return False, f"Minimum top-up is {GG_TOPUP_MIN} GG"
    return True, ""


def _get_topup_bonus_pct(amount_gg: int) -> float:
    for pack in config.TOPUP_PACKAGES:
        if int(pack.get("gg", 0)) == amount_gg:
            return float(pack.get("bonus_pct", 0.0) or 0.0)
    return 0.0


def _has_completed_topup(user_id: int) -> bool:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(1) AS cnt FROM gg_transactions WHERE user_id=? AND tx_type='topup' AND status='completed'",
            (user_id,),
        ).fetchone()
        return bool(row and row["cnt"])
    finally:
        conn.close()


def compute_topup_bonus(user_id: int, amount_gg: int) -> int:
    package_bonus_pct = _get_topup_bonus_pct(amount_gg)
    first_bonus_pct = (
        float(config.FIRST_TOPUP_BONUS_PCT)
        if not _has_completed_topup(user_id)
        else 0.0
    )
    bonus_pct = max(package_bonus_pct, first_bonus_pct)
    return int(round(amount_gg * bonus_pct))


def process_topup(
    user_id: int, amount_gg: int, payment_reference: str, method: str
) -> tuple[bool, str, float | None, int]:
    ok, msg = validate_topup_amount(amount_gg)
    if not ok:
        return False, msg, None, 0
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT gg_balance FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not row:
            conn.rollback()
            return False, "❌ ไม่พบผู้ใช้", None, 0
        bonus = compute_topup_bonus(user_id, amount_gg)
        total = amount_gg + bonus
        new_balance = (row["gg_balance"] or 0) + total
        conn.execute("UPDATE users SET gg_balance=? WHERE id=?", (new_balance, user_id))
        desc = f"Topup {amount_gg} GG (+{bonus} bonus) [{method}] {payment_reference}".strip()
        conn.execute(
            "INSERT INTO gg_transactions (user_id, amount, tx_type, description, status, created_at) VALUES (?, ?, ?, ?, 'completed', datetime('now','localtime'))",
            (user_id, total, "topup", desc),
        )
        conn.commit()
        return True, "Top-up successful", new_balance, bonus
    except Exception as e:
        conn.rollback()
        return False, f"Top-up failed: {e}", None, 0
    finally:
        conn.close()


def refund_gg(user_id: int, amount: float, description: str = "") -> tuple[bool, str]:
    if not user_id:
        return False, "❌ ไม่พบ user_id"
    level = get_user_level(user_id)
    if level == "admin":
        return True, "✅ Admin - ไม่ต้องคืน GG"
    return add_gg(user_id, amount, "refund", description or f"Refund {amount:.0f} GG")


def topup_gg(user_id: int, gg_amount: float) -> tuple[bool, str]:
    """เติม GG ด้วยเงิน (ขั้นต่ำ 10 GG = $5)"""
    if not user_id:
        return False, "❌ กรุณาเข้าสู่ระบบก่อน"
    if gg_amount < GG_TOPUP_MIN:
        return (
            False,
            f"❌ เติมขั้นต่ำ {GG_TOPUP_MIN} GG (= ${GG_TOPUP_MIN / GG_RATE:.0f})",
        )
    usd_cost = gg_amount / GG_RATE
    return add_gg(
        user_id, gg_amount, "topup", f"💰 เติม {gg_amount:.0f} GG (${usd_cost:.2f})"
    )


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


def create_generation_job(
    user_id: int,
    prompt: str,
    style: str,
    lyrics: str,
    mode: str,
    instrumental: bool,
    plan: str,
    cost: float,
    priority: str,
    eta_seconds: int | None = None,
) -> int | None:
    if not user_id:
        return None
    conn = _get_conn()
    cur = conn.execute(
        """
        INSERT INTO generation_jobs (user_id, prompt, style, lyrics, mode, instrumental, plan, cost, priority, status, eta_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            prompt or "",
            style or "",
            lyrics or "",
            mode or "",
            1 if instrumental else 0,
            plan or "",
            cost,
            priority or "low",
            "queued",
            eta_seconds,
        ),
    )
    conn.commit()
    job_id = cur.lastrowid
    conn.close()
    return int(job_id) if job_id is not None else None


def update_generation_job(
    job_id: int,
    status: str,
    backend: str | None = None,
    request_id: str | None = None,
    audio_url: str | None = None,
    error_message: str | None = None,
):
    if not job_id:
        return
    conn = _get_conn()
    conn.execute(
        """
        UPDATE generation_jobs
        SET status=?, backend=?, request_id=?, audio_url=?, error_message=?, updated_at=datetime('now','localtime')
        WHERE id=?
        """,
        (status, backend, request_id, audio_url, error_message, job_id),
    )
    conn.commit()
    conn.close()


def get_generation_job(job_id: int) -> dict | None:
    if not job_id:
        return None
    conn = _get_conn()
    row = conn.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


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
        return True, "✅ Admin - ไม่จำกัด GG"
    balance = get_gg_balance(user_id)
    if balance < cost:
        return (
            False,
            f"⚠️ GG ไม่เพียงพอ (มี {balance:.0f} GG ต้องการ {cost:.0f} GG) - เติม GG ที่แท็บ 💰 เติม GG",
        )
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
    label = str(config.get("label", ""))
    features = config.get("features")
    if not isinstance(features, dict):
        features = {}

    # ตรวจสอบว่าเลเวลนี้มีฟีเจอร์นี้หรือไม่
    if not features.get(feature, False):
        need_level = _min_level_for_feature(feature)
        need_label = (
            str(LEVEL_CONFIG[need_level].get("label", "?")) if need_level else "?"
        )
        return (
            False,
            f"🔒 ฟีเจอร์นี้ต้องการเลเวล {need_label} ขึ้นไป (คุณเป็น {label})",
        )

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
        features = LEVEL_CONFIG[lvl].get("features")
        if isinstance(features, dict) and features.get(feature, False):
            return lvl
    return "admin"


def get_level_info(level: str) -> dict:
    """ดึงข้อมูล config ของเลเวล"""
    return LEVEL_CONFIG.get(level, LEVEL_CONFIG["free"])


def get_all_levels() -> dict:
    """ดึงข้อมูลทุกเลเวล"""
    return LEVEL_CONFIG


def get_all_users_as_dict(limit: int = 100) -> list[dict]:
    """ดึงข้อมูลผู้ใช้ทั้งหมด (คืนค่าเป็น dict)"""
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
        row = conn.execute(
            "SELECT id, display_name, level FROM users WHERE username=?",
            (target.strip(),),
        ).fetchone()
        if not row:
            print(f"❌ ไม่พบผู้ใช้ '{target}'")
            conn.close()
            sys.exit(1)
        conn.execute(
            "UPDATE users SET level='admin', gg_balance=9999 WHERE id=?", (row["id"],)
        )
        conn.commit()
        conn.close()
        print(f"✅ ตั้ง {row['display_name']} (@{target}) เป็น Admin สำเร็จ! 👑")
    elif len(sys.argv) >= 2 and sys.argv[1] == "list":
        conn = _get_conn()
        rows = conn.execute(
            "SELECT username, display_name, level, gg_balance FROM users ORDER BY id"
        ).fetchall()
        conn.close()
        if not rows:
            print("💭 ยังไม่มีสมาชิก - สมัครคนแรกจะได้เป็น Admin อัตโนมัติ")
        else:
            print(f"👥 สมาชิกทั้งหมด {len(rows)} คน:")
            for r in rows:
                print(
                    f"  @{r['username']:15s}  {r['display_name']:15s}  [{r['level']:5s}]  {r['gg_balance']:.0f} GG"
                )
    else:
        print("วิธีใช้:")
        print("  python user_db.py promote <username>  - ตั้งผู้ใช้เป็น Admin")
        print("  python user_db.py list                - ดูรายชื่อสมาชิกทั้งหมด")

# ===================== New Top Up & Admin Functions =====================


def create_topup_request(
    user_id: int, gg_amount: float, proof_url: str = "", method: str = ""
) -> tuple[bool, str]:
    """สร้างรายการขอเติมเงิน (Pending)"""
    if not user_id:
        return False, "❌ ไม่พบ user_id"
    if gg_amount < GG_TOPUP_MIN:
        return False, f"❌ เติมขั้นต่ำ {GG_TOPUP_MIN} GG"

    conn = _get_conn()
    desc_method = f" ({method})" if method else ""
    conn.execute(
        "INSERT INTO gg_transactions (user_id, amount, tx_type, description, status, proof_url, created_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'))",
        (
            user_id,
            gg_amount,
            "topup",
            f"รออนุมัติ: เติม {gg_amount:.0f} GG{desc_method}",
            "pending",
            proof_url,
        ),
    )
    conn.commit()
    conn.close()
    return True, f"✅ ส่งคำขอเติมเงิน {gg_amount:.0f} GG แล้ว กรุณารอแอดมินตรวจสอบ"


def approve_topup(admin_id: int, tx_id: int) -> tuple[bool, str]:
    """อนุมัติรายการเติมเงิน (Admin only)"""
    if get_user_level(admin_id) != "admin":
        return False, "❌ เฉพาะ Admin เท่านั้น"

    conn = _get_conn()
    tx = conn.execute(
        "SELECT user_id, amount, status FROM gg_transactions WHERE id=?", (tx_id,)
    ).fetchone()
    if not tx:
        conn.close()
        return False, "❌ ไม่พบรายการนี้"
    if tx["status"] != "pending":
        conn.close()
        return False, f"❌ รายการนี้สถานะเป็น {tx['status']} แล้ว"

    user_id = tx["user_id"]
    amount = tx["amount"]

    # Update balance
    conn.execute(
        "UPDATE users SET gg_balance = gg_balance + ? WHERE id=?", (amount, user_id)
    )

    # Update Membership Logic (30 days)
    new_level = None
    if amount == 2000:
        new_level = "basic"
    elif amount == 6900:
        new_level = "pro"

    if new_level:
        # Check current expiry
        current = conn.execute(
            "SELECT membership_expiry FROM users WHERE id=?", (user_id,)
        ).fetchone()
        current_expiry_str = current["membership_expiry"] if current else None

        now = datetime.now()
        new_expiry = now + timedelta(days=30)

        # If already has valid expiry, extend it? Or just reset?
        # Simple approach: Reset to now + 30 days
        # Advanced: if current_expiry > now, new_expiry = current_expiry + 30 days

        if current_expiry_str:
            try:
                current_expiry = datetime.strptime(
                    current_expiry_str, "%Y-%m-%d %H:%M:%S"
                )
                if current_expiry > now:
                    new_expiry = current_expiry + timedelta(days=30)
            except Exception:
                pass  # Invalid format, just use now + 30

        expiry_str = new_expiry.strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE users SET level=?, membership_expiry=? WHERE id=?",
            (new_level, expiry_str, user_id),
        )

    # Update tx status
    conn.execute(
        "UPDATE gg_transactions SET status='completed', updated_at=datetime('now','localtime') WHERE id=?",
        (tx_id,),
    )
    conn.commit()
    conn.close()

    msg_extra = ""
    if new_level:
        msg_extra = f" และอัปเกรดเป็น {new_level.upper()} (หมดอายุ {expiry_str})"

    return True, f"✅ อนุมัติยอด {amount:.0f} GG{msg_extra} เรียบร้อย"


def reject_topup(admin_id: int, tx_id: int) -> tuple[bool, str]:
    """ปฏิเสธรายการเติมเงิน"""
    if get_user_level(admin_id) != "admin":
        return False, "❌ เฉพาะ Admin เท่านั้น"

    conn = _get_conn()
    conn.execute(
        "UPDATE gg_transactions SET status='rejected', updated_at=datetime('now','localtime') WHERE id=?",
        (tx_id,),
    )
    conn.commit()
    conn.close()
    return True, "✅ ปฏิเสธรายการเรียบร้อย"


def get_pending_topups(admin_id: int) -> list[list]:
    """ดึงรายการรออนุมัติ (Admin only) - Format for Gradio Dataframe"""
    if get_user_level(admin_id) != "admin":
        return []
    conn = _get_conn()
    rows = conn.execute("""
        SELECT t.id, u.username, t.amount, t.description, t.created_at, t.proof_url 
        FROM gg_transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.status='pending' AND t.tx_type='topup'
        ORDER BY t.id DESC
    """).fetchall()
    conn.close()

    result = []
    for r in rows:
        proof_display = r["proof_url"]
        if proof_display and "assets/slips" in proof_display:
            # If it's a file path, show filename only
            proof_display = os.path.basename(proof_display)
        result.append(
            [r["id"], r["username"], r["amount"], r["created_at"], proof_display or "-"]
        )
    return result


def get_total_profit(admin_id: int) -> str:
    """คำนวณรายได้รวม (GG) จากรายการ Topup ที่สำเร็จ (Admin only)"""
    if get_user_level(admin_id) != "admin":
        return "N/A"
    conn = _get_conn()
    # Sum amount of completed topups
    row = conn.execute(
        "SELECT SUM(amount) FROM gg_transactions WHERE tx_type='topup' AND status='completed'"
    ).fetchone()
    total_gg = row[0] if row and row[0] else 0
    conn.close()
    return f"{total_gg:,.0f} GG"


def get_all_users_for_admin(admin_id: int) -> list:
    """ดึงรายชื่อสมาชิกทั้งหมด (Admin only) - Format for Gradio Dataframe"""
    if get_user_level(admin_id) != "admin":
        return []
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, username, email, level, gg_balance, created_at FROM users ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def update_user_status(
    admin_id: int, target_user_id: int, new_level: str, new_balance: float
) -> tuple[bool, str]:
    """แก้ไขสถานะและยอดเงินของสมาชิก (Admin only)"""
    if get_user_level(admin_id) != "admin":
        return False, "❌ Permission denied"

    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE users SET level = ?, gg_balance = ? WHERE id = ?",
            (new_level, new_balance, target_user_id),
        )
        conn.commit()
        return (
            True,
            f"✅ Updated User ID {target_user_id}: Level={new_level}, Balance={new_balance}",
        )
    except Exception as e:
        return False, f"❌ Update failed: {e}"
    finally:
        conn.close()


def delete_user(admin_id: int, target_user_id: int) -> tuple[bool, str]:
    """ลบผู้ใช้ (Admin only)"""
    if get_user_level(admin_id) != "admin":
        return False, "❌ Permission denied"

    conn = _get_conn()
    try:
        # Check if target is admin
        target = conn.execute("SELECT level FROM users WHERE id=?", (target_user_id,)).fetchone()
        if target and target["level"] == "admin":
            return False, "❌ Cannot delete another admin"

        conn.execute("DELETE FROM users WHERE id=?", (target_user_id,))
        # Optional: Delete related data? For now, keep history or delete cascade if needed.
        # But SQLite foreign keys might not be enabled by default or configured to cascade.
        # Let's just delete the user record.
        conn.commit()
        return True, f"✅ User ID {target_user_id} deleted successfully"
    except Exception as e:
        return False, f"❌ Delete failed: {e}"
    finally:
        conn.close()
