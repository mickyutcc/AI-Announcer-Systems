
import user_db
import sqlite3

def reset_password(username, new_password):
    conn = user_db._get_conn()
    row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        print(f"User '{username}' not found.")
        conn.close()
        return

    user_id = row['id']
    new_hash = user_db._hash_password(new_password)
    
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
    conn.commit()
    conn.close()
    print(f"Password for '{username}' reset successfully.")

if __name__ == "__main__":
    reset_password("admin_micky", "admin_micky")
