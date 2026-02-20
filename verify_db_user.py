import sqlite3
import user_db
import hashlib

def verify_user():
    print(f"Checking DB at: {user_db.DB_PATH}")
    conn = sqlite3.connect(user_db.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check all users
    cursor.execute("SELECT id, username, password_hash, level FROM users")
    users = cursor.fetchall()
    print(f"Found {len(users)} users:")
    for user in users:
        print(f"ID: {user['id']}, User: {user['username']}, Hash: {user['password_hash']}, Level: {user['level']}")
    
    conn.close()
    
    # Try login function directly
    username = "admin_twin"
    password = "47711015"
    print(f"\nTesting login for {username} with password {password}...")
    
    user_id, msg = user_db.login_user(username, password)
    print(f"Result: User ID: {user_id}, Msg: {msg}")

    # Manual hash check
    salt = "MuseGenx1000_salt_v1"
    computed_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    print(f"Computed hash for '{password}': {computed_hash}")

if __name__ == "__main__":
    verify_user()
