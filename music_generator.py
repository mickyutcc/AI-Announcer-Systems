import os
import time
import typing as t
import requests
import app


def _sanitize_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_") or "song"


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


def generate_song(
    title: str,
    style: str,
    lyrics: str,
    mode: str = "easy",
) -> dict:
    backend = app.MUSIC_BACKEND
    if backend == "suno":
        res = _generate_suno(title, style, lyrics)
        if not res.get("ok") and app.GOAPI_KEY:
            # fallback to GOAPI if SUNO server unavailable
            return _generate_goapi(title, style, lyrics)
        return res
    return _generate_goapi(title, style, lyrics)


def _generate_suno(title: str, style: str, lyrics: str) -> dict:
    server = app.SUNO_SERVER_URL
    cookie = app.SUNO_COOKIE
    if not cookie:
        return {"ok": False, "message": "SUNO_COOKIE ไม่ถูกตั้งค่าใน .env"}
    try:
        session = requests.Session()
        session.headers.update({"Cookie": cookie, "Accept": "application/json", "Content-Type": "application/json"})
        payload = {
            "prompt": lyrics or (title or "Untitled"),
            "tags": style or "",
            "title": title or "Untitled",
            "make_instrumental": False,
            "wait_audio": True
        }
        r = session.post(f"{server}/api/custom_generate", json=payload, timeout=app.SUNO_TIMEOUT)
        if r.status_code not in (200, 202):
            return {"ok": False, "message": f"SUNO generate status {r.status_code}: {r.text}"}
        data = r.json()
        items = data if isinstance(data, list) else [data]
        # try direct audio_url
        for item in items:
            au = item.get("audio_url")
            if au:
                fn = _sanitize_filename(title) + ".mp3"
                path = _download(au, fn)
                return {"ok": True, "audio_url": au, "file": path}
        # if not ready, fetch by ids
        ids = ",".join([x.get("id") for x in items if x.get("id")])
        if ids:
            pr = session.get(f"{server}/api/get?ids={ids}", timeout=app.SUNO_TIMEOUT)
            if pr.status_code == 200:
                pd = pr.json()
                for item in pd if isinstance(pd, list) else [pd]:
                    au = (item or {}).get("audio_url")
                    if au:
                        fn = _sanitize_filename(title) + ".mp3"
                        path = _download(au, fn)
                        return {"ok": True, "audio_url": au, "file": path}
        return {"ok": False, "message": "ไม่พบ audio_url จาก SUNO"}
    except Exception as e:
        return {"ok": False, "message": f"SUNO error: {e}"}


def _generate_goapi(title: str, style: str, lyrics: str) -> dict:
    key = app.GOAPI_KEY
    if not key:
        return {"ok": False, "message": "GOAPI_KEY ไม่ถูกตั้งค่าใน .env"}
    base = "https://api.goapi.ai/api/suno/v1/music"
    headers = {"X-API-Key": key, "Accept": "application/json", "Content-Type": "application/json"}
    payload = {
        "custom_mode": False,
        "input": {
            "gpt_description_prompt": f"{title} | {style}".strip(),
            "make_instrumental": False,
            "prompt": lyrics or "",
        },
    }
    try:
        r = requests.post(base, json=payload, headers=headers, timeout=app.REQUEST_TIMEOUT)
        if r.status_code not in (200, 202):
            return {"ok": False, "message": f"GOAPI generate status {r.status_code}"}
        data = r.json()
        task_id = data.get("task_id") or data.get("id") or (data.get("data") or {}).get("task_id")
        if not task_id:
            audio_url = data.get("audio_url") or data.get("url")
            if audio_url:
                fn = _sanitize_filename(title) + ".mp3"
                path = _download(audio_url, fn)
                return {"ok": True, "audio_url": audio_url, "file": path}
            return {"ok": False, "message": "ไม่พบ task_id หรือ audio_url จาก GOAPI"}
        deadline = time.time() + app.MAX_POLL_SECONDS
        while time.time() < deadline:
            pr = requests.get(f"{base}/{task_id}", headers=headers, timeout=app.REQUEST_TIMEOUT)
            if pr.status_code != 200:
                time.sleep(app.RETRY_DELAY)
                continue
            pd = pr.json()
            status = pd.get("status") or pd.get("state") or (pd.get("data") or {}).get("status")
            if status in ("completed", "success", "done"):
                audio_url = pd.get("audio_url") or (pd.get("data") or {}).get("audio_url") or (pd.get("result") or {}).get("audio_url")
                fn = _sanitize_filename(title) + ".mp3"
                path = _download(audio_url, fn) if audio_url else None
                return {"ok": True, "audio_url": audio_url, "file": path}
            if status in ("failed", "error"):
                return {"ok": False, "message": pd.get("error") or "GOAPI งานล้มเหลว"}
            time.sleep(2)
        return {"ok": False, "message": "GOAPI timeout"}
    except Exception as e:
        return {"ok": False, "message": f"GOAPI error: {e}"}
