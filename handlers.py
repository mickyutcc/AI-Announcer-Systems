"""
Handlers for the Gradio UI
Connects UI events to backend logic (music_generator, user_db)
"""

import logging
import os
import re
import shutil
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr

import config
import music_generator
import user_db
import voice_clone
from config import ASSETS_DIR

# Default user for local usage
DEFAULT_USER = "admin"
DEFAULT_PASS = "admin"
logger = logging.getLogger(__name__)

STYLE_MAP = {
    "ลูกทุ่ง": "Luk Thung (Thai country): acoustic guitar, saw u, mellow flute, steady country rhythm, traditional Thai ornamentation",
    "หมอลำ": "Mor Lam style: khaen lead, rhythmic percussion, northeastern Thai feel, fast tempo",
    "Pop": "Contemporary pop: synth pads, modern drums, catchy chorus, polished production",
    "Rock": "Rock: electric guitars, driving drums, energetic, distorted riffs, powerful bass",
    "Hip-Hop": "Hip-Hop: boom bap beat, deep bass, rhythmic flow, urban vibe",
    "R&B": "R&B: smooth vocals, groovy bassline, soulful chords, slow jam",
    "Electronic": "Electronic: synthesizers, drum machines, digital textures, futuristic",
    "Dance": "Dance pop: upbeat tempo, four-on-the-floor kick, club atmosphere",
    "EDM": "EDM: big room drops, heavy sidechain, high energy, festival sound",
    "House": "House music: 4/4 beat, hi-hats, piano chords, deep groove",
    "Trance": "Trance: hypnotic arpeggios, building tension, ethereal pads, high BPM",
    "Reggae": "Reggae: offbeat skank guitar, deep dub bass, relaxed island rhythm",
    "Country": "Country: acoustic guitar, pedal steel, storytelling lyrics, warm tone",
    "Folk": "Folk: acoustic instruments, raw vocals, intimate atmosphere, minimal production",
    "Indie": "Indie pop/rock: jangling guitars, lo-fi aesthetic, alternative sound",
    "Acoustic": "Acoustic: unplugged instruments, natural sound, clean vocals",
    "Jazz": "Jazz: saxophone lead, double bass, swing rhythm, improvisational elements, complex chords",
    "Blues": "Blues: 12-bar structure, expressive guitar solos, soulful vocals, shuffle rhythm",
    "Classical": "Classical: piano, violin, orchestral arrangement, formal structure, dynamic range",
    "Latin": "Latin: reggaeton beat, spanish guitar, tropical percussion, danceable",
    "K-Pop": "K-Pop: high production value, catchy hooks, mix of pop/rap/dance, energetic",
    "J-Pop": "J-Pop: upbeat, anime opening style, complex chord progressions, bright melody",
    "Thai Pop": "Thai Pop: T-Pop style, modern production mixed with Thai melodic sensibility",
    "Metal": "Heavy Metal: distorted guitars, aggressive drums, double kick, intense energy",
    "Punk": "Punk Rock: fast tempo, power chords, raw energy, rebellious attitude",
    "Soul": "Soul: emotive vocals, brass section, gospel influence, grooving bass",
    "Ambient": "Ambient: atmospheric pads, drone sounds, relaxing, no beat, spacious",
    "Lo-fi": "Lo-fi Hip Hop: chill beats, vinyl crackle, nostalgic, study music",
    "Funk": "Funk: slap bass, syncopated rhythm, wah guitar, groovy brass",
    "Disco": "Disco: funky bassline, string hits, four-on-the-floor, dance floor vibe",
}

PARENTHESES_LINE_RE = re.compile(r"^\s*[\(\[\{].*[\)\]\}]\s*$", flags=re.MULTILINE)


def build_generation_payload(
    prompt_text: str,
    selected_styles: List[str],
    mood: List[str],
    lyrics_text: str,
    include_stage_directions_in_vocals: bool = False,
) -> Dict[str, Any]:
    style_instructions = []
    for s in selected_styles:
        inst = STYLE_MAP.get(s)
        if inst:
            style_instructions.append(inst)
        else:
            style_instructions.append(s)
    
    arrangement_instruction = " / ".join(style_instructions)
    if mood:
        arrangement_instruction += " | Mood: " + ", ".join(mood)
    
    lyrics_for_vocal = lyrics_text
    if not include_stage_directions_in_vocals and lyrics_text:
        lyrics_lines = []
        extracted_instructions = []
        
        for line in lyrics_text.splitlines():
            line_stripped = line.strip()
            # Check if line is wrapped in () or {} - Treat as performance instructions
            if (line_stripped.startswith("(") and line_stripped.endswith(")")) or \
               (line_stripped.startswith("{") and line_stripped.endswith("}")):
                content = line_stripped[1:-1].strip()
                if content:
                    extracted_instructions.append(content)
            # Check if line is wrapped in [] - Treat as structure tags (Verse, Chorus)
            elif line_stripped.startswith("[") and line_stripped.endswith("]"):
                # Keep structure tags for Suno/Udio
                lyrics_lines.append(line)
            else:
                # Normal lyrics
                lyrics_lines.append(line)
        
        lyrics_for_vocal = "\n".join(lyrics_lines)
        
        # Append extracted instructions to arrangement
        if extracted_instructions:
            arrangement_instruction += " | " + ", ".join(extracted_instructions)

    return {
        "prompt": prompt_text,
        "arrangement_instructions": arrangement_instruction,
        "lyrics": lyrics_for_vocal,
        "meta": {
            "selected_styles": selected_styles,
            "mood": mood,
            "original_lyrics": lyrics_text
        },
    }


def map_style_tokens(style_payload: str) -> str:
    tokens = [t.strip() for t in (style_payload or "").split(",") if t.strip()]
    mapped = [STYLE_MAP.get(t, t) for t in tokens]
    return ", ".join(mapped)


def on_load():
    """Called when app loads"""
    # Ensure default admin user exists
    user_db.register_user(DEFAULT_USER, DEFAULT_PASS, "Admin User", "admin@musegen.ai")
    user_id, _ = user_db.login_user(DEFAULT_USER, DEFAULT_PASS)
    if user_id:
        user_db.set_user_level(user_id, "admin")
        # Ensure enough credits
        user_db.add_gg(user_id, 1000, "system_init", "Initial credits")
    return "Ready"


def _get_plan_from_level(level: str) -> str:
    if level in ("pro", "admin"):
        return "pro"
    if level == "basic":
        return "standard"
    return "easy"


def _get_priority_from_plan(plan: str) -> str:
    if plan == "pro":
        return "high"
    if plan == "standard":
        return "medium"
    return "low"


def estimate_cost(mode: str, instrumental: bool) -> int:
    base = config.GG_COST_SONG
    inst = config.GG_COST_INST if instrumental else 0
    return int(base + inst)


def submit_generation(
    prompt: str,
    style: Any,
    lyrics: str,
    mode: str,
    instrumental: bool = False,
    user_id: Optional[int] = None,
    treat_parens_as_instr: bool = True,
) -> Tuple[
    Optional[str],
    str,
    Optional[int],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[int],
    Optional[float],
    Optional[dict],
]:
    if not user_id:
        user_id, msg = user_db.login_user(DEFAULT_USER, DEFAULT_PASS)
        if not user_id:
            return (
                None,
                f"Login failed: {msg}",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )

    info = user_db.get_user_info(user_id) or {}
    level = info.get("level") or "free"
    plan = _get_plan_from_level(level)

    if mode not in ("easy", "standard", "pro"):
        return None, "❌ Mode ไม่ถูกต้อง", None, None, None, None, None, None, None
    if plan == "easy" and mode != "easy":
        return (
            None,
            "🔒 โหมด Standard/Pro สำหรับสมาชิกที่อัปเกรดเท่านั้น",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
    if plan == "standard" and mode == "pro":
        return (
            None,
            "🔒 โหมด Pro สำหรับสมาชิก Pro เท่านั้น",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
    if instrumental and plan != "pro":
        return (
            None,
            "🔒 Instrumental ใช้ได้เฉพาะ Pro เท่านั้น",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

    style_raw = style or ""
    
    # Extract styles from list if it's a list (gradio dropdown multiselect)
    all_tokens = []
    if isinstance(style, list):
        all_tokens = style
        style_raw = ", ".join(style)
    elif isinstance(style, str):
        all_tokens = [s.strip() for s in style.split(",") if s.strip()]

    # Separate styles and moods
    selected_styles = []
    selected_moods = []
    
    for token in all_tokens:
        if token in config.MOODS:
            selected_moods.append(token)
        else:
            selected_styles.append(token)
    
    payload = build_generation_payload(
        prompt, 
        selected_styles, 
        selected_moods, 
        lyrics,
        include_stage_directions_in_vocals=not treat_parens_as_instr
    )
    style_mapped = payload["arrangement_instructions"]
    lyrics_sanitized = payload["lyrics"]

    logger.info(f"selected_styles: {selected_styles}")
    logger.info(f"arrangement_instructions: {style_mapped}")

    logger.info(
        "payload_built",
        extra={
            "user_id": user_id,
            "style_raw": style_raw,
            "style_mapped": style_mapped,
            "lyrics_original_len": len(lyrics) if lyrics else 0,
            "lyrics_sanitized_len": len(lyrics_sanitized) if lyrics_sanitized else 0,
        },
    )

    cost = estimate_cost(mode, instrumental)
    reserved = False
    ok_bal, bal_msg, current_balance = user_db.validate_and_reserve(
        user_id,
        cost,
        f"Reserve ({mode}{'/Inst' if instrumental else ''}): {prompt[:20]}",
    )
    if not ok_bal:
        meta = None
        if current_balance is not None and current_balance < cost:
            meta = {
                "ok": False,
                "reason": "insufficient_credits",
                "required": cost,
                "balance": current_balance,
                "min_topup": config.GG_TOPUP_MIN,
            }
            logger.info(
                "insufficient_credits",
                extra={
                    "user_id": user_id,
                    "required": cost,
                    "balance": current_balance,
                },
            )
        return (
            None,
            f"Insufficient credits: {bal_msg}",
            None,
            None,
            None,
            None,
            None,
            None,
            meta,
        )

    reserved = True
    priority = _get_priority_from_plan(plan)
    eta_seconds = 120 if mode == "easy" else 180
    job_id = user_db.create_generation_job(
        user_id,
        prompt,
        style_raw,
        lyrics,
        mode,
        instrumental,
        plan,
        cost,
        priority,
        eta_seconds,
    )
    if job_id:
        user_db.update_generation_job(job_id, "running")
        logger.info(
            "Job created",
            extra={"job_id": job_id, "user_id": user_id, "cost": cost},
        )

    try:
        import importlib

        importlib.reload(config)
        res = music_generator.generate_song(
            prompt,
            style_mapped,
            lyrics_sanitized,
            mode,
            make_instrumental=instrumental,
        )
        if not res.get("ok"):
            if job_id:
                user_db.update_generation_job(
                    job_id, "failed", error_message=res.get("message")
                )
            if reserved:
                user_db.refund_gg(
                    user_id,
                    cost,
                    f"Refund on failure ({mode}{'/Inst' if instrumental else ''})",
                )
            return (
                None,
                f"Error: {res.get('message')}",
                job_id,
                priority,
                None,
                None,
                eta_seconds,
                cost,
            None,
            )

        audio_url = res.get("audio_url")
        file_path = res.get("file")
        backend = res.get("backend")
        request_id = res.get("request_id")
        final_audio = file_path if file_path else audio_url

        user_db.save_song(
            user_id,
            prompt,
            style_raw,
            lyrics,
            audio_url or "",
            mode,
            status="completed",
            cost=cost,
            backend=backend,
            request_id=request_id,
            credits_used=cost,
        )
        if job_id:
            user_db.update_generation_job(
                job_id,
                "completed",
                backend=backend,
                request_id=request_id,
                audio_url=audio_url or "",
            )
        return (
            final_audio,
            "✅ Generation Successful!",
            job_id,
            priority,
            backend,
            request_id,
            eta_seconds,
            cost,
            None,
        )
    except Exception as e:
        if job_id:
            user_db.update_generation_job(job_id, "failed", error_message=str(e))
        logger.exception("Failed to create generation job")
        if reserved:
            user_db.refund_gg(
                user_id,
                cost,
                f"Refund on error ({mode}{'/Inst' if instrumental else ''})",
            )
        return (
            None,
            f"System Error: {str(e)}",
            job_id,
            priority,
            None,
            None,
            eta_seconds,
            cost,
            None,
        )


def generate_music(prompt, style, lyrics, mode, lyrics_mode="AI", user_id=None):
    instrumental = lyrics_mode == "Instrumental"
    audio, status, _, _, _, _, _, _, _ = submit_generation(
        prompt, style, lyrics, mode, instrumental, user_id=user_id
    )
    return audio, status, None


def process_topup_payment(
    user_id: int, amount_gg: int, method: str, payment_reference: str
) -> tuple[bool, str, float | None, int]:
    logger.info(
        "topup_initiated",
        extra={"user_id": user_id, "amount": amount_gg, "method": method},
    )
    ok, msg, new_balance, bonus = user_db.process_topup(
        user_id, amount_gg, payment_reference, method
    )
    if ok:
        logger.info(
            "topup_success",
            extra={
                "user_id": user_id,
                "amount": amount_gg,
                "bonus": bonus,
                "new_balance": new_balance,
            },
        )
    return ok, msg, new_balance, bonus


def get_history(user_id=None):
    """Get generation history for specific user"""
    if not user_id:
        user_id, _ = user_db.login_user(DEFAULT_USER, DEFAULT_PASS)

    if not user_id:
        return []

    conn = user_db._get_conn()
    cursor = conn.execute(
        "SELECT id, prompt, style, created_at, audio_url, cost, backend FROM generation_jobs WHERE user_id=? AND status='completed' ORDER BY id DESC LIMIT 20",
        (user_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        cursor = conn.execute(
            "SELECT title, style, created_at, audio_url, cost, backend FROM song_history WHERE user_id=? ORDER BY id DESC LIMIT 20",
            (user_id,),
        )
        rows = cursor.fetchall()
    conn.close()

    return [
        [
            r["id"],
            r["prompt"],
            r["style"],
            r["created_at"],
            r["audio_url"],
            r["cost"],
            r["backend"],
        ]
        for r in rows
    ] if rows and "id" in rows[0].keys() else [
        [
            r["title"],
            r["style"],
            r["created_at"],
            r["audio_url"],
            r["cost"],
            r["backend"],
        ]
        for r in rows
    ]


def get_credits(user_id=None):
    """Get current credits"""
    if not user_id:
        user_id, _ = user_db.login_user(DEFAULT_USER, DEFAULT_PASS)

    if not user_id:
        return "0 GG"

    conn = user_db._get_conn()
    row = conn.execute("SELECT gg_balance FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()

    return f"{int(row['gg_balance'])} GG" if row else "0 GG"


def get_user_info(user_id=None):
    if not user_id:
        user_id, _ = user_db.login_user(DEFAULT_USER, DEFAULT_PASS)

    if not user_id:
        return "Unknown user"

    info = user_db.get_user_info(user_id)
    if not info:
        return "Unknown user"

    name = info.get("display_name") or info.get("username")
    email = info.get("email") or "-"
    level = info.get("level") or "free"

    level_str = level.upper()
    expiry = info.get("membership_expiry")
    if expiry and level in ["basic", "pro"]:
        try:
            exp_date = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            days_left = (exp_date - now).days
            if days_left < 0:
                level_str += " (Expired)"
            else:
                level_str += f" ({days_left} days left)"
        except Exception:
            pass

    return f"{name} | {email} | {level_str}"


def submit_topup_request(
    user_id: int, amount: int, proof_file, method: str = ""
) -> tuple[bool, str, str]:
    ok, msg = user_db.validate_topup_amount(amount)
    if not ok:
        return False, msg, ""
    if not proof_file:
        return False, "❌ กรุณาอัปโหลดสลิปการโอนเงิน", ""
    proof_path = ""
    try:
        slips_dir = os.path.join(ASSETS_DIR, "slips")
        if not os.path.exists(slips_dir):
            os.makedirs(slips_dir)
        src_path = proof_file.name if hasattr(proof_file, "name") else proof_file
        filename = f"slip_{user_id}_{int(time.time())}_{os.path.basename(src_path)}"
        dest_path = os.path.join(slips_dir, filename)
        shutil.copy(src_path, dest_path)
        proof_path = dest_path
    except Exception as e:
        return False, f"❌ Error saving slip: {e}", ""
    success, msg = user_db.create_topup_request(user_id, amount, proof_path, method)
    return success, msg, proof_path


def on_topup_submit(amount, proof_file, request: gr.Request):
    user_id = None
    if request:
        username = request.username
        if username:
            user_id = user_db.get_user_id(username)
    if not user_id:
        user_id = 1
    try:
        amount_int = int(amount)
    except Exception:
        return "❌ จำนวนไม่ถูกต้อง"
    ok, msg, _ = submit_topup_request(user_id, amount_int, proof_file)
    return msg


def on_admin_refresh(request: gr.Request):
    """Refresh admin data"""
    if not request:
        return "N/A", [], [], "Please login"

    username = request.username
    if not username:
        return "N/A", [], [], "Please login"
    user_id = user_db.get_user_id(username)
    if not user_id:
        return "N/A", [], [], "Please login"

    profit = user_db.get_total_profit(user_id)
    topups = user_db.get_pending_topups(user_id)
    users = user_db.get_all_users_for_admin(user_id)

    return profit, topups, users, f"Updated at {time.strftime('%H:%M:%S')}"


def on_admin_update_user(target_id, new_level, new_balance, request: gr.Request):
    """Update user status"""
    if not request:
        return "❌ Please login"

    username = request.username
    if not username:
        return "❌ Please login"
    admin_id = user_db.get_user_id(username)
    if not admin_id:
        return "❌ Please login"

    success, msg = user_db.update_user_status(
        admin_id, target_id, new_level, new_balance
    )
    return msg


def approve_tx(tx_id):
    """Approve a top-up transaction"""
    user_id, _ = user_db.login_user(DEFAULT_USER, DEFAULT_PASS)
    if not user_id:
        return "❌ Please login first"
    try:
        tx_id = int(tx_id)
    except Exception:
        return "❌ Invalid ID"

    success, msg = user_db.approve_topup(user_id, tx_id)
    return msg


def reject_tx(tx_id):
    """Reject a top-up transaction"""
    user_id, _ = user_db.login_user(DEFAULT_USER, DEFAULT_PASS)
    if not user_id:
        return "❌ Please login first"
    try:
        tx_id = int(tx_id)
    except Exception:
        return "❌ Invalid ID"

    success, msg = user_db.reject_topup(user_id, tx_id)
    return msg


def generate_voice_clone(
    text, voice_id, model_id, stability, similarity, consent, user_state=None
):
    """Handle TTS generation request"""
    # Extract user_id from state
    user_id = None
    if isinstance(user_state, dict):
        raw_id = user_state.get("id")
        if isinstance(raw_id, int):
            user_id = raw_id

    # Fallback to default user if none provided (e.g. for testing)
    if not user_id:
        user_id, _ = user_db.login_user(DEFAULT_USER, DEFAULT_PASS)
    if not user_id:
        return None, "❌ Please login first"

    # Determine cost
    cost = config.GG_COST_TTS

    # Check balance
    ok_bal, bal_msg = user_db.check_gg_balance(user_id, cost)
    if not ok_bal:
        return None, f"Insufficient credits: {bal_msg}"

    # Generate
    try:
        res = voice_clone.generate_speech(
            text,
            voice_id,
            model_id,
            stability,
            similarity,
            True,
            origin_user_id=user_id,
            consent=consent,
        )

        if not res.get("ok"):
            return None, f"Error: {res.get('message')}"

        file_path = res.get("file")

        # Deduct credits
        user_db.deduct_gg(user_id, cost, f"Voice Clone: {text[:20]}...")

        # We could save to song_history with special style tag, or just return
        # For now, let's just return.
        # Optionally save to DB if user wants history tracking for voices.

        return file_path, "✅ Generation Successful!"

    except Exception as e:
        return None, f"System Error: {str(e)}"
