import os
import sqlite3
import hashlib
import user_db

# กำหนด Path ของ Database (ใช้ตัวเดียวกับใน user_db.py)
DB_PATH = user_db.DB_PATH

def hash_password(password: str) -> str:
    """ฟังก์ชัน Hash Password ให้ตรงกับระบบ (SHA-256 + Salt)"""
    # อ้างอิงจาก user_db._hash_password
    salt = "MuseGenx1000_salt_v1"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def reset_and_create_admin():
    print(f"กำลังดำเนินการลบฐานข้อมูลเก่าที่: {DB_PATH}")
    
    # 1. ลบไฟล์ Database เดิมทิ้ง (ถ้ามี)
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("✅ ลบไฟล์ฐานข้อมูลเดิมเรียบร้อยแล้ว")
        except Exception as e:
            print(f"❌ ไม่สามารถลบไฟล์ฐานข้อมูลได้: {e}")
            return
    else:
        print("ℹ️ ไม่พบไฟล์ฐานข้อมูลเดิม (จะสร้างใหม่)")

    # 2. สร้างตารางใหม่ (Init DB)
    print("กำลังสร้างตารางในฐานข้อมูลใหม่...")
    try:
        user_db.init_db()
        print("✅ สร้างตาราง (Schema) เรียบร้อยแล้ว")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการสร้างตาราง: {e}")
        return

    # 3. สร้าง User ใหม่ (Admin)
    username = "admin_twin"
    password_raw = "47711015"
    password_hash = hash_password(password_raw)
    display_name = "Admin Twin"
    email = "admin@musegen.ai"
    level = "admin"
    gg_balance = 99999  # ให้เหรียญเยอะๆ สำหรับ Admin

    print(f"กำลังสร้างผู้ใช้: {username} ...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (username, password_hash, display_name, email, level, gg_balance)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password_hash, display_name, email, level, gg_balance))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ สร้าง Admin User สำเร็จ!")
        print(f"   🆔 ID: {user_id}")
        print(f"   👤 Username: {username}")
        print(f"   🔑 Password: {password_raw}")
        print(f"   👑 Level: {level}")
        print(f"   💰 GG Balance: {gg_balance}")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการสร้าง User: {e}")

if __name__ == "__main__":
    reset_and_create_admin()
