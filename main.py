import argparse
import os
import sys
import app
import user_db
import music_generator

def cmd_generate(args):
    user_id, msg = user_db.login_user(args.username, args.password)
    if not user_id:
        print(msg)
        return
    ok_perm, perm_msg = user_db.check_mode_permission(user_id, args.mode)
    if not ok_perm:
        print(perm_msg)
        return
    ok_bal, bal_msg = user_db.check_gg_balance(user_id, app.GG_COST_SONG)
    if not ok_bal:
        print(bal_msg)
        return
    print("เริ่มสร้างเพลง…")
    res = music_generator.generate_song(args.title, args.style, args.lyrics, args.mode)
    if not res.get("ok"):
        print("❌ สร้างเพลงล้มเหลว:", res.get("message"))
        return
    audio_url = res.get("audio_url") or ""
    file_path = res.get("file") or ""
    user_db.save_song(user_id, args.title, args.style, args.lyrics, audio_url, args.mode, status="completed")
    user_db.deduct_gg(user_id, app.GG_COST_SONG, f"สร้างเพลง: {args.title}")
    print("✅ สร้างเพลงสำเร็จ!")
    if audio_url:
        print("URL:", audio_url)
    if file_path:
        print("ไฟล์ถูกบันทึกที่:", file_path)

def cmd_config(_args):
    app.print_config()


def cmd_env(_args):
    print("GOAPI_KEY:", "set" if os.getenv("GOAPI_KEY") else "missing")
    print("SUNO_COOKIE:", "set" if os.getenv("SUNO_COOKIE") else "missing")
    print("MUSIC_BACKEND:", os.getenv("MUSIC_BACKEND", "udio"))


def cmd_users_list(_args):
    users = user_db.get_all_users()
    if not users:
        print("ยังไม่มีสมาชิก — สมัครคนแรกจะได้เป็น Admin อัตโนมัติ")
        return
    print(f"สมาชิกทั้งหมด {len(users)} คน:")
    for u in users:
        print(f"@{u['username']:15s}  {u['display_name']:15s}  [{u['level']:5s}]  {int(u['gg_balance']):4d} GG")


def cmd_users_register(args):
    ok, msg = user_db.register_user(args.username, args.password, args.display_name or "", args.email or "")
    print(msg)


def cmd_users_promote(args):
    conn = user_db._get_conn()
    row = conn.execute("SELECT id, display_name, level FROM users WHERE username=?", (args.username.strip(),)).fetchone()
    if not row:
        conn.close()
        print(f"ไม่พบผู้ใช้ '{args.username}'")
        return
    user_id = row["id"]
    conn.close()
    ok, msg = user_db.set_user_level(user_id, "admin")
    print(msg)
    user_db.add_gg(user_id, 9999, "admin_grant", "ตั้งเป็น Admin พร้อมเครดิต GG")


def main():
    parser = argparse.ArgumentParser(prog="MuseGenx1000")
    sub = parser.add_subparsers(dest="cmd")

    p_config = sub.add_parser("config")
    p_config.set_defaults(func=cmd_config)

    p_env = sub.add_parser("env")
    p_env.set_defaults(func=cmd_env)

    p_list = sub.add_parser("users:list")
    p_list.set_defaults(func=cmd_users_list)

    p_reg = sub.add_parser("users:register")
    p_reg.add_argument("--username", required=True)
    p_reg.add_argument("--password", required=True)
    p_reg.add_argument("--display-name")
    p_reg.add_argument("--email")
    p_reg.set_defaults(func=cmd_users_register)

    p_promote = sub.add_parser("users:promote")
    p_promote.add_argument("username")
    p_promote.set_defaults(func=cmd_users_promote)

    p_gen = sub.add_parser("generate")
    p_gen.add_argument("--username", required=True)
    p_gen.add_argument("--password", required=True)
    p_gen.add_argument("--title", required=True)
    p_gen.add_argument("--style", default="")
    p_gen.add_argument("--lyrics", default="")
    p_gen.add_argument("--mode", default="easy")
    p_gen.set_defaults(func=cmd_generate)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
