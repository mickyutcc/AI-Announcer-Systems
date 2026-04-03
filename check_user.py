
import user_db
import sys

try:
    username = "admin_micky"
    conn = user_db._get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()

    if row:
        print(f"User '{username}' found.")
        print(f"ID: {row['id']}")
        print(f"Level: {row['level']}")
        print(f"Password Hash: {row['password_hash']}")
        
        # Verify password
        password = "admin_micky"
        hashed = user_db._hash_password(password)
        if row['password_hash'] == hashed:
             print("Password verification: SUCCESS")
        else:
             print(f"Password verification: FAILED (Expected {hashed}, Got {row['password_hash']})")
    else:
        print(f"User '{username}' NOT found.")

except Exception as e:
    print(f"Error: {e}")
