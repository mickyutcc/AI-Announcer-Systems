import sqlite3
import hashlib
import os
import sys

# Try to import user_db to get the DB path and hash function
# If that fails, we fallback to defaults (assuming we are in the project root)
try:
    import user_db
    DB_PATH = user_db.DB_PATH
    def hash_password(p):
        return user_db._hash_password(p)
except ImportError:
    print("Could not import user_db, using local fallback logic.")
    DB_PATH = "musegenx1000.db"
    def hash_password(password: str) -> str:
        salt = "MuseGenx1000_salt_v1"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def force_create_admin():
    username = "admin_twin"
    password = "47711015"
    display_name = "Admin Twin"
    
    print(f"Target DB: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    
    hashed = hash_password(password)
    
    if row:
        print(f"User '{username}' found (ID: {row[0]}). Updating...")
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, level = 'admin', gg_balance = 99999, display_name = ?
            WHERE username = ?
        """, (hashed, display_name, username))
        print("Updated password, level=admin, and balance=99999.")
    else:
        print(f"User '{username}' not found. Creating new admin...")
        cursor.execute("""
            INSERT INTO users (username, password_hash, display_name, email, level, gg_balance, created_at)
            VALUES (?, ?, ?, 'admin@musegen.local', 'admin', 99999, CURRENT_TIMESTAMP)
        """, (username, hashed, display_name))
        print("Created new admin user.")
        
    conn.commit()
    conn.close()
    print("Done! You can now login with:")
    print(f"User: {username}")
    print(f"Pass: {password}")

if __name__ == "__main__":
    force_create_admin()
