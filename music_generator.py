# -*- coding: utf-8 -*-
import os
import time

import requests

import app


def _sanitize_filename(name: str) -> str:
    return (
        "".join(c for c in name if c.isalnum() or c in (" ", "_", "-"))
        .strip()
        .replace(" ", "_")
        or "song"
    )


def _download(url: str, filename: str) -> str | None:
    try:
        resp = requests.get(url, timeout=app.REQUEST_TIMEOUT)
        if resp.status_code == 200:
            target_dir = app.ASSETS_DIR
            os.makedirs(target_dir, exist_ok=True)
            path = os.path.join(target_dir, filename)
            with open(path, "wb") as f:
                f.write(resp.content)
            return path
    except Exception:
        pass
    return None


# Default retry config for SUNO attempts
DEFAULT_SUNO_RETRIES = 1
DEFAULT_SUNO_BACKOFF_BASE = 2  # seconds, exponential backoff base


def generate_song(
    title: str,
    style: str,
    lyrics: str,
    mode: str = "easy",
    make_instrumental: bool = False,
    output_format: str = "mp3",
    dry_run: bool = False,
) -> dict:
    """
    Generate song wrapper.
    output_format: 'mp3' or 'wav'
    dry_run: if True, simulate request without calling API (supported backends only)
    """
    backend = (app.MUSIC_BACKEND or "suno").lower().strip()
    print(f"DEBUG: Using backend: {backend}")

    if backend == "udio":
        res = _generate_udio(title, style, lyrics, mode, make_instrumental)
        if not res.get("ok"):
            print(f"DEBUG: UDIO failed: {res.get('message')}")
        return res
    if backend == "suno":
        # Try SUNO with retries and fallback to FAL/Minimax if unreliable
        res = _suno_with_fallback(
            title,
            style,
            lyrics,
            mode,
            make_instrumental,
            output_format=output_format,
            dry_run=dry_run,
        )
        if not res.get("ok"):
            print(f"DEBUG: Final failure after SUNO attempts: {res.get('message')}")
        return res
    if backend in ("fal", "minimax"):
        res = _generate_fal_minimax(
            title,
            style,
            lyrics,
            mode,
            make_instrumental,
            output_format=output_format,
            dry_run=dry_run,
        )
        if not res.get("ok"):
            print(f"DEBUG: FAL/Minimax failed: {res.get('message')}")
        return res
    return _generate_goapi(title, style, lyrics, mode)


def _suno_with_fallback(
    title: str,
    style: str,
    lyrics: str,
    mode: str,
    make_instrumental: bool = False,
    output_format: str = "mp3",
    max_retries: int = DEFAULT_SUNO_RETRIES,
    dry_run: bool = False,
) -> dict:
    """
    Try SUNO generation with retries. If still failing, fallback to FAL/Minimax automatically.
    Returns the successful result dict or final failure dict.
    """
    if dry_run:
        print("DEBUG: Dry run for SUNO requested - skipping actual API calls.")
        # For dry-run, we might want to return what we WOULD send, or just success
        # Since we don't have a payload builder for Suno separated out, we'll return a mock success
        return {
            "ok": True,
            "dry_run": True,
            "backend": "suno",
            "message": "Dry run simulation",
        }

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"DEBUG: SUNO attempt {attempt}/{max_retries}")
            res = _generate_suno(title, style, lyrics, mode, make_instrumental)
            if res.get("ok"):
                # If SUNO returns success but the file is missing, treat as failure
                if res.get("file") or res.get("audio_url"):
                    return res
                else:
                    last_err = res.get("message") or "SUNO returned ok but no file/url"
                    print(
                        f"DEBUG: SUNO attempt returned ok but missing file: {last_err}"
                    )
            else:
                last_err = res.get("message") or "SUNO failed without message"
                print(f"DEBUG: SUNO attempt failed: {last_err}")
        except Exception as e:
            last_err = str(e)
            print(f"DEBUG: Exception during SUNO attempt: {last_err}")

        # exponential backoff before next attempt
        if attempt < max_retries:
            backoff = min(30, DEFAULT_SUNO_BACKOFF_BASE * (2 ** (attempt - 1)))
            print(f"DEBUG: Waiting {backoff}s before next SUNO attempt...")
            time.sleep(backoff)

    # If reached here, SUNO attempts exhausted — fallback to UDIO
    print("DEBUG: SUNO attempts exhausted, falling back to UDIO.")
    udio_res = _generate_udio(title, style, lyrics, mode, make_instrumental)
    if udio_res.get("ok"):
        print("DEBUG: UDIO fallback succeeded.")
        return udio_res

    print(
        f"DEBUG: UDIO fallback failed: {udio_res.get('message')}. Falling back to FAL/Minimax."
    )

    # Try to craft a SUNO-like hint for FAL to mimic Suno tonality/quality
    suno_style_hint = f"{style or ''} Suno-style Thai vocal timbre, natural expressive phrasing, clear Thai diction"
    # Merge hint into style parameter passed to FAL
    fal_style = f"{suno_style_hint}".strip()
    fal_res = _generate_fal_minimax(
        title, fal_style, lyrics, mode, make_instrumental, output_format=output_format
    )
    if fal_res.get("ok"):
        print("DEBUG: FAL fallback succeeded.")
        return fal_res

    # Both SUNO, UDIO and FAL failed — return last error (prefer fal message if present)
    final_msg = (
        fal_res.get("message")
        or udio_res.get("message")
        or last_err
        or "All backends (SUNO, UDIO, FAL) failed"
    )
    return {"ok": False, "message": final_msg}


def _generate_suno_lyrics(
    session: requests.Session, server: str, prompt: str
) -> str | None:
    try:
        r = session.post(
            f"{server}/api/generate_lyrics",
            json={"prompt": prompt},
            timeout=app.SUNO_TIMEOUT,
        )
        if r.status_code not in (200, 202):
            return None
        data = r.json()
        text = None
        if isinstance(data, dict):
            text = data.get("text") or data.get("lyrics") or data.get("lyric")
        if isinstance(text, str) and text.strip():
            return text
    except Exception:
        return None
    return None


def _generate_suno(
    title: str, style: str, lyrics: str, mode: str, make_instrumental: bool = False
) -> dict:
    server = app.SUNO_SERVER_URL
    cookie = app.SUNO_COOKIE
    if not cookie:
        return {"ok": False, "message": "SUNO_COOKIE ไม่ถูกตั้งค่าใน .env"}
    try:
        session = requests.Session()
        session.headers.update(
            {
                "Cookie": cookie,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        is_easy = (mode or "").lower() == "easy"
        if is_easy:
            # Try to inject a Suno-style hint into tags if Thai is detected
            tags = style or ""
            if any("\u0e00" <= c <= "\u0e7f" for c in (title + style + (lyrics or ""))):
                tags = f"{tags} Suno-style Thai vocals".strip()
            payload = {
                "prompt": title or "Untitled",
                "tags": tags,
                "make_instrumental": False,  # Easy mode always vocal
                "wait_audio": False,
            }
            if app.TWOCAPTCHA_KEY:
                payload["twocaptcha_key"] = app.TWOCAPTCHA_KEY
            r = session.post(
                f"{server}/api/generate", json=payload, timeout=app.SUNO_TIMEOUT
            )
        else:
            # Standard / Pro
            if not make_instrumental and not (lyrics or "").strip():
                # Only generate lyrics if NOT instrumental and no lyrics provided
                prompt = " | ".join([p for p in [title, style] if p]) or "Untitled"
                generated_lyrics = _generate_suno_lyrics(session, server, prompt)
                if generated_lyrics:
                    lyrics = generated_lyrics

            tags = style or ""
            if any("\u0e00" <= c <= "\u0e7f" for c in (title + style + (lyrics or ""))):
                tags = f"{tags} Suno-style Thai vocals".strip()

            payload = {
                "prompt": (
                    "" if make_instrumental else (lyrics or (title or "Untitled"))
                ),
                "tags": tags,
                "title": title or "Untitled",
                "make_instrumental": make_instrumental,
                "wait_audio": False,
            }
            if app.TWOCAPTCHA_KEY:
                payload["twocaptcha_key"] = app.TWOCAPTCHA_KEY
            r = session.post(
                f"{server}/api/custom_generate", json=payload, timeout=app.SUNO_TIMEOUT
            )
        if r.status_code not in (200, 202):
            return {
                "ok": False,
                "message": f"SUNO generate status {r.status_code}: {r.text}",
            }
        data = r.json()
        items_list: list[dict] = []
        if isinstance(data, dict):
            clips = data.get("clips")
            data_items = data.get("data")
            if isinstance(clips, list):
                items_list = [i for i in clips if isinstance(i, dict)]
            elif isinstance(data_items, list):
                items_list = [i for i in data_items if isinstance(i, dict)]
        elif isinstance(data, list):
            items_list = [i for i in data if isinstance(i, dict)]
        elif isinstance(data, dict):
            items_list = [data]
        # try direct audio_url
        for item in items_list:
            au = item.get("audio_url")
            if au:
                fn = _sanitize_filename(title) + ".mp3"
                path = _download(au, fn)
                req_id = item.get("id") if isinstance(item, dict) else None
                return {
                    "ok": True,
                    "audio_url": au,
                    "file": path,
                    "backend": "suno",
                    "request_id": req_id,
                }
        # if not ready, fetch by ids (poll until ready)
        ids_list = [str(x.get("id")) for x in items_list if x.get("id")]
        ids = ",".join(ids_list)
        if ids:
            deadline = time.time() + app.MAX_POLL_SECONDS
            while time.time() < deadline:
                pr = session.get(
                    f"{server}/api/get?ids={ids}", timeout=app.SUNO_TIMEOUT
                )
                if pr.status_code == 200:
                    pd = pr.json()
                    for item in pd if isinstance(pd, list) else [pd]:
                        au = (item or {}).get("audio_url")
                        if au:
                            fn = _sanitize_filename(title) + ".mp3"
                            path = _download(au, fn)
                            req_id = item.get("id") if isinstance(item, dict) else None
                            return {
                                "ok": True,
                                "audio_url": au,
                                "file": path,
                                "backend": "suno",
                                "request_id": req_id or ids,
                            }
                time.sleep(5)
        return {
            "ok": False,
            "message": "ไม่พบ audio_url จาก SUNO (รอแล้วแต่ยังไม่พร้อม)",
        }
    except Exception as e:
        return {"ok": False, "message": f"SUNO error: {e}"}


def _extract_audio_url(obj):
    if isinstance(obj, dict):
        for key in (
            "audio_url",
            "audioUrl",
            "url",
            "audio",
            "mp3_url",
            "mp3Url",
            "song_path",
            "file_url",
            "output_url",
            "result_url",
        ):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                return val
        for key in ("data", "result", "audio", "output", "songs"):
            found = _extract_audio_url(obj.get(key))
            if found:
                return found
    if isinstance(obj, list):
        for item in obj:
            found = _extract_audio_url(item)
            if found:
                return found
    return None


def _generate_udio(
    title: str, style: str, lyrics: str, mode: str, make_instrumental: bool = False
) -> dict:
    key = app.GOAPI_KEY
    if not key:
        return {"ok": False, "message": "GOAPI_KEY ไม่ถูกตั้งค่าใน .env"}
    generate_url = app.GENERATE_URL
    fetch_url = app.FETCH_URL
    if not generate_url or not fetch_url:
        return {
            "ok": False,
            "message": "GOAPI_GENERATE_URL หรือ GOAPI_FETCH_URL ไม่ถูกตั้งค่า",
        }
    if not fetch_url.endswith("/"):
        fetch_url = fetch_url + "/"
    headers = {"x-api-key": key, "Content-Type": "application/json"}

    print(f"DEBUG: UDIO Request to {generate_url}")

    gpt_description_prompt = " | ".join([p for p in [title, style] if p]).strip()
    if make_instrumental:
        lyrics_type = "instrumental"
    elif (lyrics or "").strip():
        lyrics_type = "user"
    else:
        lyrics_type = "generate"

    # Auto-inject Thai tags if title/lyrics contain Thai
    is_thai = False
    if any("\u0e00" <= c <= "\u0e7f" for c in (title + style + lyrics)):
        is_thai = True

        # Enhanced Genre Handling for Luk Thung / Mor Lam
        style_lower = style.lower()
        if "luk thung" in style_lower or "ลูกทุ่ง" in style_lower:
            gpt_description_prompt += ", Luk Thung, Thai country folk, emotional vocals, vibrato, heavy bass, clear Thai pronunciation, male vocals, rustic timbre, age 30-50, Thai-only, native luk-thung accent"
            gpt_description_prompt += (
                ", instrumentation: acoustic guitar, tambourine, khaen, phin, bass"
            )
        elif (
            "mor lam" in style_lower
            or "mo lam" in style_lower
            or "หมอลำ" in style_lower
        ):
            gpt_description_prompt += ", Mor Lam, Isan folk, fast paced, Khaen mouth organ, Phin guitar, fun, energetic, northeastern Thai style, male vocals, rustic timbre, age 30-50, Thai-only, native Isan accent"
            gpt_description_prompt += (
                ", instrumentation: phin, khaen, khlui, electric guitar, tambourine"
            )

        if "thai" not in gpt_description_prompt.lower():
            gpt_description_prompt += (
                ", Thai vocals, native Thai pronunciation, clear Thai diction"
            )

    # Add negative tags to prevent foreign accents
    # User requested: prioritized list, combined <= 100 chars
    negative_candidates = ["instrumental", "no vocals"]
    if is_thai:
        # Prioritize: foreign/western/chinese accents and broken thai
        negative_candidates.extend(
            [
                "foreign accent",
                "western accent",
                "Chinese vocals",
                "Chinese accent",
                "English accent",
                "broken Thai",
                "incomprehensible",
                "no English words",
                "no western pop arrangement",
            ]
        )

        # Ensure 'Thai language' is explicitly mentioned if not already
        if "thai language" not in gpt_description_prompt.lower():
            gpt_description_prompt += ", Thai language"

    def _build_neg_tags(candidates, limit=100):
        selected = []
        current_len = 0
        for tag in candidates:
            tag_len = len(tag)
            # comma + space = 2 chars, except first item
            added_len = tag_len + 2 if selected else tag_len
            if current_len + added_len <= limit:
                selected.append(tag)
                current_len += added_len
        return ", ".join(selected)

    negative_tags = _build_neg_tags(negative_candidates)

    input_payload = {
        "gpt_description_prompt": gpt_description_prompt or "Untitled",
        "negative_tags": negative_tags,
        "lyrics_type": lyrics_type,
        "seed": -1,
    }

    # Auto-adjust lyrics for better Thai pronunciation
    final_lyrics = lyrics or ""
    if lyrics_type == "user" and is_thai:
        # Clean lyrics: Remove English/Chinese to enforce "Thai-only" and "no code-switching"
        import re

        # Remove English (A-Za-z)
        final_lyrics = re.sub(r"[a-zA-Z]", "", final_lyrics)
        # Remove CJK (Chinese range)
        final_lyrics = re.sub(r"[\u4e00-\u9fff]", "", final_lyrics)
        # Clean up double spaces
        final_lyrics = re.sub(r"\s+", " ", final_lyrics).strip()

        # Udio sometimes handles Thai better with spaces between phrases
        # This is a simple heuristic
        pass

    if lyrics_type == "user":
        input_payload["lyrics"] = final_lyrics
    payload = {
        "model": "music-u",
        "task_type": "generate_music",
        "input": input_payload,
    }
    try:
        # Retry loop for specific errors (like negative tags length)
        r = None
        for attempt in range(2):  # Try 0, then 1 (retry)
            r = requests.post(
                generate_url, json=payload, headers=headers, timeout=app.REQUEST_TIMEOUT
            )
            print(f"DEBUG: UDIO Response {r.status_code}: {r.text[:200]}")

            if r.status_code != 200:
                # Check for negative tags error
                if "negative tags cannot exceed" in r.text and attempt == 0:
                    print(
                        "DEBUG: Udio negative tags too long, truncating and retrying..."
                    )
                    # Truncate aggressively to 90 chars
                    input_payload["negative_tags"] = _build_neg_tags(
                        negative_candidates, limit=90
                    )
                    payload["input"] = input_payload
                    continue
                return {
                    "ok": False,
                    "message": f"UDIO generate status {r.status_code}: {r.text}",
                    "backend": "udio",
                }
            break  # Success

        if r is None:
            return {
                "ok": False,
                "message": "UDIO ไม่ได้รับ response",
                "backend": "udio",
            }
        data = r.json()
        data_obj = data.get("data") if isinstance(data, dict) else None
        task_id = (
            (data_obj or {}).get("task_id")
            or (data or {}).get("task_id")
            or (data or {}).get("id")
        )
        if not task_id:
            audio_url = _extract_audio_url(data)
            if audio_url:
                fn = _sanitize_filename(title) + ".mp3"
                path = _download(audio_url, fn)
                return {
                    "ok": True,
                    "audio_url": audio_url,
                    "file": path,
                    "backend": "udio",
                }
            return {
                "ok": False,
                "message": "ไม่พบ task_id หรือ audio_url จาก UDIO",
                "backend": "udio",
            }
        deadline = time.time() + app.MAX_POLL_SECONDS
        while time.time() < deadline:
            pr = requests.get(
                f"{fetch_url}{task_id}", headers=headers, timeout=app.REQUEST_TIMEOUT
            )
            if pr.status_code != 200:
                print(f"DEBUG: Poll {task_id} status {pr.status_code}")
                time.sleep(app.RETRY_DELAY)
                continue
            pd = pr.json()
            data_pd = pd.get("data") if isinstance(pd, dict) else None
            status = (
                (data_pd or {}).get("status") or pd.get("status") or pd.get("state")
            )
            print(f"DEBUG: Poll {task_id} -> {status}")

            if isinstance(status, str) and status.lower() in (
                "completed",
                "success",
                "done",
                "succeeded",
                "completed",
            ):
                audio_url = _extract_audio_url((data_pd or {}).get("output") or pd)
                if not audio_url:
                    print(f"DEBUG: Success but no audio_url found in: {pd}")
                    return {
                        "ok": False,
                        "message": "API แจ้งว่าเสร็จแล้ว แต่ไม่พบไฟล์เสียง",
                        "backend": "udio",
                        "request_id": task_id,
                    }

                print(f"DEBUG: Found audio_url: {audio_url}")
                fn = _sanitize_filename(title) + ".mp3"
                path = _download(audio_url, fn) if audio_url else None
                return {
                    "ok": True,
                    "audio_url": audio_url,
                    "file": path,
                    "backend": "udio",
                    "request_id": task_id,
                }
            if isinstance(status, str) and status.lower() in ("failed", "error"):
                err = (data_pd or {}).get("error") or pd.get("error")
                if isinstance(err, dict):
                    err = err.get("message") or err.get("raw_message") or str(err)
                if not err:
                    output = (data_pd or {}).get("output") or {}
                    songs = output.get("songs") if isinstance(output, dict) else None
                    if isinstance(songs, list) and songs:
                        err = songs[0].get("error_detail") or songs[0].get("error_type")

                print(f"DEBUG: Failed detail: {pd}")
                return {
                    "ok": False,
                    "message": err or "UDIO งานล้มเหลว",
                    "backend": "udio",
                    "request_id": task_id,
                }
            time.sleep(2)
        return {
            "ok": False,
            "message": "UDIO timeout",
            "backend": "udio",
            "request_id": task_id,
        }
    except Exception as e:
        return {"ok": False, "message": f"UDIO error: {e}", "backend": "udio"}


def _generate_goapi(title: str, style: str, lyrics: str, mode: str) -> dict:
    key = app.GOAPI_KEY
    if not key:
        return {"ok": False, "message": "GOAPI_KEY ไม่ถูกตั้งค่าใน .env"}
    base = "https://api.goapi.ai/api/suno/v1/music"
    headers = {
        "X-API-Key": key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    is_easy = (mode or "").lower() == "easy"
    payload = {
        "custom_mode": False if is_easy else True,
        "input": {
            "gpt_description_prompt": f"{title} | {style}".strip(),
            "make_instrumental": False,
            "prompt": "" if is_easy else (lyrics or ""),
        },
    }
    try:
        r = requests.post(
            base, json=payload, headers=headers, timeout=app.REQUEST_TIMEOUT
        )
        if r.status_code not in (200, 202):
            return {
                "ok": False,
                "message": f"GOAPI generate status {r.status_code}",
                "backend": "goapi",
            }
        data = r.json()
        task_id = (
            data.get("task_id")
            or data.get("id")
            or (data.get("data") or {}).get("task_id")
        )
        if not task_id:
            audio_url = data.get("audio_url") or data.get("url")
            if audio_url:
                fn = _sanitize_filename(title) + ".mp3"
                path = _download(audio_url, fn)
                return {
                    "ok": True,
                    "audio_url": audio_url,
                    "file": path,
                    "backend": "goapi",
                }
            return {
                "ok": False,
                "message": "ไม่พบ task_id หรือ audio_url จาก GOAPI",
                "backend": "goapi",
            }
        deadline = time.time() + app.MAX_POLL_SECONDS
        while time.time() < deadline:
            pr = requests.get(
                f"{base}/{task_id}", headers=headers, timeout=app.REQUEST_TIMEOUT
            )
            if pr.status_code != 200:
                time.sleep(app.RETRY_DELAY)
                continue
            pd = pr.json()
            status = (
                pd.get("status")
                or pd.get("state")
                or (pd.get("data") or {}).get("status")
            )
            if status in ("completed", "success", "done"):
                audio_url = (
                    pd.get("audio_url")
                    or (pd.get("data") or {}).get("audio_url")
                    or (pd.get("result") or {}).get("audio_url")
                )
                fn = _sanitize_filename(title) + ".mp3"
                path = _download(audio_url, fn) if audio_url else None
                return {
                    "ok": True,
                    "audio_url": audio_url,
                    "file": path,
                    "backend": "goapi",
                    "request_id": task_id,
                }
            if status in ("failed", "error"):
                return {
                    "ok": False,
                    "message": pd.get("error") or "GOAPI งานล้มเหลว",
                    "backend": "goapi",
                    "request_id": task_id,
                }
            time.sleep(2)
        return {
            "ok": False,
            "message": "GOAPI timeout",
            "backend": "goapi",
            "request_id": task_id,
        }
    except Exception as e:
        return {"ok": False, "message": f"GOAPI error: {e}", "backend": "goapi"}


# -----------------------
# New helper: build_fal_payload for dry-run/debug
# -----------------------
def build_fal_payload(
    title: str,
    style: str,
    lyrics: str,
    mode: str,
    make_instrumental: bool = False,
    output_format: str = "mp3",
) -> tuple:
    """
    Build and return (url, headers, payload) for Fal Minimax request without sending it.
    Use this for debugging / simulation.
    """
    key = app.FAL_KEY or ""
    url = "https://queue.fal.run/fal-ai/minimax-music/v2"
    lk = (key or "").strip()
    auth_value = lk
    if lk and not lk.lower().startswith(("bearer ", "key ")):
        auth_value = f"Key {lk}"
    headers = {
        "Authorization": auth_value,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    raw_text = f"{title} {style} {lyrics or ''}".strip()
    style_prompt = f"{style} {title}".strip()
    if not style_prompt:
        style_prompt = "Pop song"

    lyrics_content = lyrics
    lower_raw = raw_text.lower()
    is_thai = any("\u0e00" <= c <= "\u0e7f" for c in raw_text)
    wants_thai = is_thai or ("thai" in lower_raw) or ("ไทย" in raw_text)
    wants_lukthung = any(
        k in lower_raw
        for k in ["luk thung", "luk-thung", "molam", "mor lam", "isan", "thai folk"]
    ) or any(k in raw_text for k in ["ลูกทุ่ง", "หมอลำ", "อีสาน"])
    avoid_lukthung = any(
        k in lower_raw
        for k in ["not luk thung", "no luk thung", "not molam", "no molam", "not isan"]
    ) or any(k in raw_text for k in ["ไม่ใช่ลูกทุ่ง", "ไม่ใช่หมอลำ", "ไม่ใช่อีสาน"])
    wants_chinese = any(
        k in lower_raw
        for k in [
            "chinese vocals",
            "native chinese",
            "mandarin vocals",
            "cantonese vocals",
            "chinese accent",
            "สำเนียงจีน",
            "คนจีนร้อง",
        ]
    )
    avoid_chinese = any(
        k in lower_raw
        for k in [
            "not chinese",
            "no chinese",
            "not mandarin",
            "no mandarin",
            "not cantonese",
            "no cantonese",
            "no pinyin",
            "no chinese accent",
        ]
    ) or any(
        k in raw_text
        for k in ["ไม่ใช่จีน", "ไม่เอาจีน", "ไม่ใช่ภาษาจีน", "ไม่เอาสำเนียงจีน"]
    )

    THAI_FILTER = (
        "no chinese instruments, no guzheng, no erhu, no pipa, "
        "no mandarin-style vocals, no cantonese-style vocals, "
        "no beijing opera style, avoid pentatonic-chinese ornamentation"
    )

    if wants_thai and wants_chinese:
        style_prompt = f"{style_prompt}, Thai lyrics, Chinese-sounding vocal timbre, singing Thai language"
        if lyrics_content:
            lyrics_content = f"ภาษาไทย (ร้องโดยน้ำเสียงจีน)\n{lyrics_content}"
    elif wants_lukthung and not avoid_lukthung:
        base_thai_prompt = "Thai vocals, native Thai pronunciation, clear Thai diction, no foreign accent"
        luk_thung_style = "Authentic Thai Luk Thung / Mor Lam style, rural vibe, acoustic guitar, phin-like plucked instrument, kleun/khlui flute, light drums, soft strings"
        luk_thung_vocal = "Professional Thai singer, natural Luk Thung ornamentation, moderate vibrato, small slides on long vowels, Isan phrasing when requested"
        style_prompt = f"{style_prompt}, {luk_thung_style}, {luk_thung_vocal}, {base_thai_prompt}, {THAI_FILTER}"
        if lyrics_content:
            lyrics_content = f"ภาษาไทย สำเนียงลูกทุ่ง/หมอลำ\n{lyrics_content}"
    elif wants_thai or (avoid_chinese and not wants_chinese):
        base_thai_prompt = "Thai vocals, native Thai pronunciation, clear Thai diction, no foreign accent"
        style_prompt = f"{style_prompt}, {base_thai_prompt}, {THAI_FILTER}"
        if lyrics_content:
            lyrics_content = f"ภาษาไทย สำเนียงไทย\n{lyrics_content}"
    else:
        if is_thai:
            style_prompt = f"{style_prompt}, Thai language, native Thai pronunciation, {THAI_FILTER}"

    if avoid_lukthung:
        style_prompt = f"{style_prompt}, not lukthung, not molam, not isan"

    if make_instrumental:
        style_prompt += ", instrumental, no vocals"
        lyrics_content = "[Instrumental]"
    elif not lyrics_content:
        lyrics_content = f"[Verse]\n{title}\n[Chorus]\n{title}"

    fmt = (output_format or "mp3").lower()
    audio_setting: dict = {"sample_rate": 44100, "channels": 2}
    if fmt == "wav" or fmt == "wave":
        audio_setting.update(
            {"format": "wav", "bits_per_sample": 16, "sample_rate": 48000}
        )
    else:
        audio_setting.update({"format": "mp3", "bitrate": 256000, "sample_rate": 44100})

    pronunciation_controls = {
        "pronunciation_strictness": "high",
        "preserve_accent": False,
        "dialect_target": (
            "native_isan"
            if any(
                k in lower_raw
                for k in ["is an", "isan", "อีสาน", "หมอลำ", "mor lam", "molam"]
            )
            else "native_thai"
        ),
    }

    payload = {
        "prompt": style_prompt[:800],
        "lyrics_prompt": (lyrics_content or "")[:8000],
        "audio_setting": audio_setting,
        "pronunciation": pronunciation_controls,
        "generation_options": {
            "mix_vocals_with_instrumental": True,
            "duration_limit_seconds": 300,
        },
    }

    return url, headers, payload


def _process_fal_submit_response(r, title, request_payload, request_headers) -> dict:
    data = r.json()
    print(f"DEBUG: FAL submit response: {data}")
    request_id = data.get("request_id") or data.get("id") or data.get("requestId")

    if not request_id:
        # maybe immediate result returned
        audio_url = _extract_audio_url(data)
        if audio_url:
            fmt = request_payload.get("audio_setting", {}).get("format")
            fn_ext = ".wav" if fmt == "wav" else ".mp3"
            fn = _sanitize_filename(title) + fn_ext
            path = _download(audio_url, fn)
            return {"ok": True, "audio_url": audio_url, "file": path, "backend": "fal"}
        return {"ok": False, "message": "ไม่พบ request_id จาก FAL", "backend": "fal"}

    # build a status URL if not provided
    status_url = (
        data.get("status_url")
        or f"https://queue.fal.run/fal-ai/minimax-music/v2/requests/{request_id}/status"
    )
    if isinstance(status_url, str):
        status_url = status_url.replace("`", "").strip()

    deadline = time.time() + app.MAX_POLL_SECONDS
    while time.time() < deadline:
        try:
            sr = requests.get(
                status_url, headers=request_headers, timeout=app.REQUEST_TIMEOUT
            )
        except Exception as e:
            print(f"DEBUG: Failed to fetch status_url {status_url}: {e}")
            time.sleep(app.RETRY_DELAY)
            continue

        if sr.status_code == 200:
            sdata = sr.json()
            status = sdata.get("status") or sdata.get("state") or ""
            print(f"DEBUG: FAL Status: {status}")
            if isinstance(status, str) and status.lower() in (
                "completed",
                "succeeded",
                "success",
            ):
                # try multiple possible result endpoints to find the audio url
                response_url = sdata.get("response_url") or ""
                if isinstance(response_url, str):
                    response_url = response_url.replace("`", "").strip()
                audio_url = None

                result_urls = []
                if response_url:
                    result_urls.append(response_url)
                    if not response_url.endswith("/result"):
                        result_urls.append(response_url.rstrip("/") + "/result")
                base_result = f"https://queue.fal.run/fal-ai/minimax-music/v2/requests/{request_id}"
                result_urls.append(base_result)
                result_urls.append(base_result + "/result")
                # dedupe while preserving order
                deduped = []
                seen = set()
                for url in result_urls:
                    if url in seen:
                        continue
                    seen.add(url)
                    deduped.append(url)
                result_urls = deduped

                for result_url in result_urls:
                    try:
                        rr = requests.get(
                            result_url,
                            headers=request_headers,
                            timeout=app.REQUEST_TIMEOUT,
                        )
                        if rr.status_code == 200:
                            rdata = rr.json()
                            print(
                                f"DEBUG: FAL result endpoint returned keys: {list(rdata.keys())}"
                            )
                            audio_url = _extract_audio_url(rdata)
                            if audio_url:
                                break
                        else:
                            print(
                                f"DEBUG: FAL result_url status {rr.status_code}: {rr.text[:200]}"
                            )
                    except Exception as e:
                        print(f"DEBUG: Failed to fetch result_url {result_url}: {e}")

                # fallback: check status payload itself
                if not audio_url:
                    audio_url = _extract_audio_url(sdata)

                if audio_url:
                    ext = (
                        ".wav"
                        if request_payload.get("audio_setting", {}).get("format")
                        == "wav"
                        else ".mp3"
                    )
                    fn = _sanitize_filename(title) + ext
                    path = _download(audio_url, fn)
                    return {
                        "ok": True,
                        "audio_url": audio_url,
                        "file": path,
                        "backend": "fal",
                        "request_id": request_id,
                    }

                return {
                    "ok": False,
                    "message": "FAL เสร็จแล้ว แต่ไม่พบไฟล์เสียง (ตรวจสอบผลลัพธ์เพิ่มเติม)",
                    "backend": "fal",
                    "request_id": request_id,
                }

            if isinstance(status, str) and status.lower() in ("failed", "error"):
                err = sdata.get("error") or sdata.get("message") or ""
                print(f"DEBUG: FAL failed detail: {sdata}")
                return {
                    "ok": False,
                    "message": f"FAL งานล้มเหลว: {err or 'Unknown error'}",
                    "backend": "fal",
                    "request_id": request_id,
                }

        time.sleep(2)

    return {
        "ok": False,
        "message": "FAL timeout",
        "backend": "fal",
        "request_id": request_id,
    }


def _generate_fal_minimax(
    title: str,
    style: str,
    lyrics: str,
    mode: str,
    make_instrumental: bool = False,
    output_format: str = "mp3",
    dry_run: bool = False,
) -> dict:
    """
    Generate using Fal / Minimax queue endpoint.
    output_format: 'mp3' or 'wav'
    dry_run: if True, do not send network request; return (url, headers, payload) for inspection.
    """
    # ... [keep earlier build_fal_payload usage unchanged] ...
    key = app.FAL_KEY or ""
    if not key and not dry_run:
        return {
            "ok": False,
            "message": "FAL_KEY ไม่ถูกตั้งค่าใน .env",
            "backend": "fal",
        }

    request_url, request_headers, request_payload = build_fal_payload(
        title, style, lyrics, mode, make_instrumental, output_format=output_format
    )

    if dry_run:
        safe_headers = dict(request_headers)
        if "Authorization" in safe_headers and safe_headers["Authorization"]:
            safe_headers["Authorization"] = "<redacted>"
        return {
            "ok": True,
            "dry_run": True,
            "url": request_url,
            "headers": safe_headers,
            "payload": request_payload,
            "backend": "fal",
        }

    # Prepare actual auth header - try preferred form(s)
    lk = (key or "").strip()

    # Prefer "Key <token>" if no prefix present; if token already contains a prefix, use as-is
    primary_auth = lk
    if not lk.lower().startswith(("key ", "bearer ")):
        primary_auth = f"Key {lk}"

    # Build candidates list: Primary first, then fallbacks
    candidates = [primary_auth]
    # Ensure Key variant is in list (if not already primary)
    if f"Key {lk}" not in candidates:
        candidates.append(f"Key {lk}")
    # Always include Bearer as fallback
    if f"Bearer {lk}" not in candidates:
        candidates.append(f"Bearer {lk}")

    # Dedupe preserving order
    candidates = list(dict.fromkeys(candidates))

    last_resp = None
    tried_headers = []

    for auth_candidate in candidates:
        headers = dict(request_headers)
        headers["Authorization"] = auth_candidate
        tried_headers.append(auth_candidate)
        try:
            print(
                f"DEBUG: FAL/Minimax v2 Request to {request_url} with auth starting '{auth_candidate[:10]}...'"
            )
            r = requests.post(
                request_url,
                json=request_payload,
                headers=headers,
                timeout=app.REQUEST_TIMEOUT,
            )
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            req_header_id = r.headers.get("x-fal-request-id") or r.headers.get(
                "X-Fal-Request-Id"
            )
            print(
                f"DEBUG: FAL response at {ts} status {r.status_code} request_id_header {req_header_id or 'n/a'}"
            )
        except Exception as e:
            last_resp = {
                "ok": False,
                "message": f"FAL request error with auth {auth_candidate}: {e}",
                "backend": "fal",
            }
            continue

        if r.status_code in (200, 201, 202):
            # proceed with normal flow using this headers
            return _process_fal_submit_response(r, title, request_payload, headers)
        elif r.status_code == 401:
            # try next candidate
            last_resp = {
                "ok": False,
                "message": f"FAL auth {auth_candidate} returned 401",
                "backend": "fal",
            }
            print(
                f"DEBUG: FAL auth attempt with '{auth_candidate[:6]}...' returned 401, trying next candidate if any."
            )
            continue
        else:
            # other error: surface it
            try:
                text = r.text
            except Exception:
                text = "<no-body>"
            return {
                "ok": False,
                "message": f"FAL generate status {r.status_code}: {text}",
                "backend": "fal",
            }

    # If all candidates failed
    if last_resp:
        return last_resp
    return {
        "ok": False,
        "message": f"FAL authentication failed with tried headers: {tried_headers}. Please verify FAL_KEY environment variable and token format.",
        "backend": "fal",
    }
