import sqlite3
import hashlib
import os

# Define database path (same as in user_db.py default)
DB_PATH = os.path.join(os.path.dirname(__file__), "musegenx1000.db")

def _hash_password(password: str) -> str:
    """Hash password using SHA-256 + salt (same as user_db.py)"""
    salt = "MuseGenx1000_salt_v1"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def init_db():
    print(f"Initializing database at: {DB_PATH}")
    
    # Ensure fresh start if file exists (though we deleted it externally)
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("Removed existing database file.")
        except OSError as e:
            print(f"Error removing database file: {e}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table with full schema (including migration fields)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            email TEXT,
            level TEXT DEFAULT 'free',
            gg_balance REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            last_login TEXT,
            membership_expiry TEXT
        );
    """)
    
    # Create song_history table
    cursor.execute("""
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
    """)
    
    # Create generation_jobs table
    cursor.execute("""
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
    """)
    
    # Create gg_transactions table
    cursor.execute("""
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

    # Create admin_twin user
    username = "admin_twin"
    password = "47711015"
    password_hash = _hash_password(password)
    display_name = "Admin Twin"
    email = "admin@musegenx1000.com"
    level = "admin"
    gg_balance = 99999.0
    
    try:
        cursor.execute("""
            INSERT INTO users (username, password_hash, display_name, email, level, gg_balance)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password_hash, display_name, email, level, gg_balance))
        print(f"User '{username}' created successfully.")
    except sqlite3.IntegrityError:
        print(f"User '{username}' already exists.")
        
    conn.commit()
    conn.close()
    print("Database initialization completed successfully.")

if __name__ == "__main__":
    init_db()
