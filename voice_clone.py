import argparse
import hashlib
import http.server
import json
import logging
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import threading
import time
from typing import Any

import requests

try:
    from prometheus_client import Counter, Gauge, Histogram

    HAS_PROMETHEUS = True
except Exception:
    HAS_PROMETHEUS = False
from datetime import datetime

from config import ELEVENLABS_API_KEY

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_STABILITY = 0.4
DEFAULT_SIMILARITY = 0.1
DEFAULT_FALLBACK_TEXT = "ขณะนี้บริการเสียงไม่พร้อม กรุณาลองใหม่ภายหลัง"
CROSSFADE_MS = int(os.getenv("TTS_CROSSFADE_MS", "30"))
MAX_CHARS_PER_CHUNK = int(os.getenv("TTS_MAX_CHARS_PER_CHUNK", "400"))
CACHE_MAX_DAYS = int(os.getenv("TTS_CACHE_MAX_DAYS", "90"))
CACHE_MAX_GB = float(os.getenv("TTS_CACHE_MAX_GB", "20"))
CIRCUIT_FAILURE_THRESHOLD = int(os.getenv("TTS_CIRCUIT_FAILURE_THRESHOLD", "3"))
CIRCUIT_OPEN_SECONDS = int(os.getenv("TTS_CIRCUIT_OPEN_SECONDS", "60"))
TTS_MAX_RETRIES = int(os.getenv("TTS_MAX_RETRIES", "3"))
TTS_RATE_LIMIT_PER_MIN = int(os.getenv("TTS_RATE_LIMIT_PER_MIN", "30"))
TTS_CONCURRENCY_LIMIT = int(os.getenv("TTS_CONCURRENCY_LIMIT", "4"))
TTS_COST_PER_CHAR = float(os.getenv("TTS_COST_PER_CHAR", "0.00006"))
TTS_COST_ALERT_THRESHOLD = float(os.getenv("TTS_COST_ALERT_THRESHOLD", "10.0"))
TTS_CACHE_CLEANUP_INTERVAL_SECONDS = int(
    os.getenv("TTS_CACHE_CLEANUP_INTERVAL_SECONDS", "3600")
)
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "tts")

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

_cache_hit_count = 0
_cache_miss_count = 0
_circuit_failures = 0
_circuit_open_until = 0
_rate_limiters: dict[str, dict[str, float]] = {}
_rate_lock = threading.Lock()
_semaphore = threading.Semaphore(TTS_CONCURRENCY_LIMIT)
_cleanup_counter = 0
_cleanup_thread: threading.Thread | None = None


class _Noop:
    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        return None

    def observe(self, *args, **kwargs):
        return None

    def set(self, *args, **kwargs):
        return None


TTS_REQUESTS_TOTAL: Any
TTS_REQUEST_DURATION: Any
TTS_CACHE_HITS_TOTAL: Any
TTS_CACHE_MISSES_TOTAL: Any
TTS_CHARS_PROCESSED_TOTAL: Any
TTS_COST_ESTIMATED_TOTAL: Any
TTS_CURRENT_CACHE_BYTES: Any
TTS_ACTIVE_WORKERS: Any

if HAS_PROMETHEUS:
    TTS_REQUESTS_TOTAL = Counter(
        "tts_requests_total", "Total TTS requests", ["status", "voice", "model"]
    )
    TTS_REQUEST_DURATION = Histogram(
        "tts_request_duration_seconds",
        "TTS request duration",
        buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8, 16),
    )
    TTS_CACHE_HITS_TOTAL = Counter("tts_cache_hits_total", "TTS cache hits")
    TTS_CACHE_MISSES_TOTAL = Counter("tts_cache_misses_total", "TTS cache misses")
    TTS_CHARS_PROCESSED_TOTAL = Counter(
        "tts_chars_processed_total", "TTS chars processed"
    )
    TTS_COST_ESTIMATED_TOTAL = Counter(
        "tts_cost_estimated_total", "TTS estimated cost in USD"
    )
    TTS_CURRENT_CACHE_BYTES = Gauge(
        "tts_current_cache_bytes", "Current cache size in bytes"
    )
    TTS_ACTIVE_WORKERS = Gauge("tts_active_workers", "Active TTS worker count")
else:
    TTS_REQUESTS_TOTAL = _Noop()
    TTS_REQUEST_DURATION = _Noop()
    TTS_CACHE_HITS_TOTAL = _Noop()
    TTS_CACHE_MISSES_TOTAL = _Noop()
    TTS_CHARS_PROCESSED_TOTAL = _Noop()
    TTS_COST_ESTIMATED_TOTAL = _Noop()
    TTS_CURRENT_CACHE_BYTES = _Noop()
    TTS_ACTIVE_WORKERS = _Noop()

# Try to import PyThaiNLP for normalization
# Set PyThaiNLP data directory to local workspace to avoid permission errors
os.environ["PYTHAINLP_DATA_DIR"] = os.path.join(os.getcwd(), "pythainlp-data")

try:
    from pythainlp.tokenize import sent_tokenize
    from pythainlp.util import normalize as thai_normalize

    HAS_PYTHAINLP = True
except ImportError:
    HAS_PYTHAINLP = False
    logger.warning(
        "PyThaiNLP not found. Install with `pip install pythainlp` for better Thai text processing."
    )


def normalize_text(text: str) -> str:
    """
    Normalize text for TTS processing.
    Handles numbers, dates, and abbreviations if PyThaiNLP is available.
    """
    if not text:
        return ""

    original_text = text

    # 1. Basic cleanup
    text = text.strip()

    # 2. Thai specific normalization
    if HAS_PYTHAINLP:
        try:
            # Normalize zero-width characters, etc.
            text = thai_normalize(text)
            # TODO: Add more advanced normalization like number to text if needed
            # For now, relying on PyThaiNLP's basic normalization and ElevenLab's own handling
        except Exception as e:
            logger.error(f"Error during Thai normalization: {e}")
            text = original_text

    # 3. Lexicon mapping (Simple example)
    lexicon = {
        "MuseGen": "มิวส์เจน",
        "AI": "เอไอ",
        "Gen": "เจน",
        "Version": "เวอร์ชัน",
        "Studio": "สตูดิโอ",
    }
    for k, v in lexicon.items():
        text = text.replace(k, v)

    return text


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _snippet(text: str, length: int = 30) -> str:
    return text[:length]


def _generate_wav_bytes(
    duration_sec: float = 0.4, sample_rate: int = 24000, freq: float = 440.0
) -> bytes:
    n_samples = int(duration_sec * sample_rate)
    samples = bytearray()
    for i in range(n_samples):
        value = int(0.2 * 32767 * math.sin(2 * math.pi * freq * i / sample_rate))
        samples.extend(struct.pack("<h", value))
    data_size = len(samples)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + samples


_MOCK_WAV = _generate_wav_bytes()


def _now_iso():
    return datetime.utcnow().isoformat() + "Z"


def _log_event(event: str, payload: dict):
    data = {"event": event, "ts": _now_iso()}
    data.update(payload or {})
    logger.info(json.dumps(data, ensure_ascii=False))


class _MockTTSHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        _ = self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(_MOCK_WAV)))
        self.end_headers()
        self.wfile.write(_MOCK_WAV)

    def do_GET(self):
        data = {"ok": True, "message": "mock tts server"}
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def start_mock_tts_server(port: int = 9000):
    server = http.server.ThreadingHTTPServer(("", port), _MockTTSHandler)
    logger.info(f"Mock TTS server running on http://localhost:{port}")
    server.serve_forever()


def _get_cache_paths(cache_key: str):
    wav_path = os.path.join(CACHE_DIR, f"{cache_key}.wav")
    meta_path = os.path.join(CACHE_DIR, f"{cache_key}.meta.json")
    return wav_path, meta_path


def _update_accessed_at(meta_path: str):
    try:
        if not os.path.exists(meta_path):
            return
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["accessed_at"] = _now_iso()
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _rate_limit_allow(user_key: str) -> bool:
    if TTS_RATE_LIMIT_PER_MIN <= 0:
        return True
    now = time.time()
    capacity = TTS_RATE_LIMIT_PER_MIN
    refill_rate = TTS_RATE_LIMIT_PER_MIN / 60.0
    with _rate_lock:
        state = _rate_limiters.get(user_key, {"tokens": capacity, "last": now})
        elapsed = now - state["last"]
        tokens = min(capacity, state["tokens"] + elapsed * refill_rate)
        if tokens < 1:
            _rate_limiters[user_key] = {"tokens": tokens, "last": now}
            return False
        state["tokens"] = tokens - 1
        state["last"] = now
        _rate_limiters[user_key] = state
        return True


def _circuit_allows() -> bool:
    return time.time() >= _circuit_open_until


def _circuit_record_success():
    global _circuit_failures
    _circuit_failures = 0


def _circuit_record_failure():
    global _circuit_failures, _circuit_open_until
    _circuit_failures += 1
    if _circuit_failures >= CIRCUIT_FAILURE_THRESHOLD:
        _circuit_open_until = time.time() + CIRCUIT_OPEN_SECONDS


def _cache_hit():
    global _cache_hit_count
    _cache_hit_count += 1
    TTS_CACHE_HITS_TOTAL.inc()


def _cache_miss():
    global _cache_miss_count
    _cache_miss_count += 1
    TTS_CACHE_MISSES_TOTAL.inc()


def get_cache_metrics():
    size_bytes = 0
    for root, _, files in os.walk(CACHE_DIR):
        for f in files:
            if f.endswith(".wav"):
                try:
                    size_bytes += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
    return {
        "cache_hit_count": _cache_hit_count,
        "cache_miss_count": _cache_miss_count,
        "cache_size_bytes": size_bytes,
    }


def _update_metrics_gauges():
    metrics = get_cache_metrics()
    TTS_CURRENT_CACHE_BYTES.set(metrics.get("cache_size_bytes", 0))
    active_workers = 0
    try:
        active_workers = max(TTS_CONCURRENCY_LIMIT - _semaphore._value, 0)
    except Exception:
        active_workers = 0
    TTS_ACTIVE_WORKERS.set(active_workers)


def _finalize_request_metrics(
    status: str, voice_id: str, model_id: str, request_start: float
):
    duration_seconds = time.time() - request_start
    TTS_REQUESTS_TOTAL.labels(status, voice_id, model_id).inc()
    TTS_REQUEST_DURATION.observe(duration_seconds)
    _update_metrics_gauges()
    return duration_seconds


def get_tts_metrics():
    cache_metrics = get_cache_metrics()
    active_workers = 0
    try:
        active_workers = max(TTS_CONCURRENCY_LIMIT - _semaphore._value, 0)
    except Exception:
        active_workers = 0
    return {**cache_metrics, "tts_active_workers": active_workers}


def cleanup_cache(
    max_age_days: int = CACHE_MAX_DAYS, max_total_gb: float = CACHE_MAX_GB
):
    max_age_seconds = max_age_days * 86400
    now = time.time()
    entries = []
    for f in os.listdir(CACHE_DIR):
        if f.endswith(".wav"):
            wav_path = os.path.join(CACHE_DIR, f)
            meta_path = wav_path.replace(".wav", ".meta.json")
            try:
                mtime = os.path.getmtime(wav_path)
                size = os.path.getsize(wav_path)
            except Exception:
                continue
            entries.append((wav_path, meta_path, mtime, size))
    for wav_path, meta_path, mtime, _ in entries:
        if now - mtime > max_age_seconds:
            try:
                os.remove(wav_path)
            except Exception:
                pass
            try:
                if os.path.exists(meta_path):
                    os.remove(meta_path)
            except Exception:
                pass
    max_total_bytes = int(max_total_gb * 1024 * 1024 * 1024)
    entries = []
    total_size = 0
    for f in os.listdir(CACHE_DIR):
        if f.endswith(".wav"):
            wav_path = os.path.join(CACHE_DIR, f)
            meta_path = wav_path.replace(".wav", ".meta.json")
            try:
                mtime = os.path.getmtime(wav_path)
                size = os.path.getsize(wav_path)
            except Exception:
                continue
            entries.append((wav_path, meta_path, mtime, size))
            total_size += size
    if total_size > max_total_bytes:
        entries.sort(key=lambda x: x[2])
        for wav_path, meta_path, _, size in entries:
            if total_size <= max_total_bytes:
                break
            try:
                os.remove(wav_path)
            except Exception:
                pass
            try:
                if os.path.exists(meta_path):
                    os.remove(meta_path)
            except Exception:
                pass
            total_size -= size


def start_cache_cleanup_worker(
    interval_seconds: int = TTS_CACHE_CLEANUP_INTERVAL_SECONDS,
):
    global _cleanup_thread
    if _cleanup_thread is not None and _cleanup_thread.is_alive():
        return

    def _worker():
        while True:
            try:
                cleanup_cache()
            except Exception:
                pass
            time.sleep(interval_seconds)

    _cleanup_thread = threading.Thread(target=_worker, daemon=True)
    _cleanup_thread.start()


def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> list[str]:
    """Split text into chunks suitable for TTS synthesis."""
    if not text:
        return []

    chunks = []

    # Use PyThaiNLP sentence tokenizer if available
    sentences = []
    if HAS_PYTHAINLP:
        try:
            sentences = sent_tokenize(text)
        except Exception as e:
            logger.warning(f"PyThaiNLP sent_tokenize failed: {e}")
            # Fallback to regex split below
            sentences = []

    if not sentences:
        # Fallback: split by newlines and basic punctuation
        import re

        # Split by newline or common sentence endings, keeping delimiters
        parts = re.split(r"([\n.!?]+)", text)
        sentences = []
        current = ""
        for p in parts:
            current += p
            if re.search(r"[\n.!?]$", p):
                sentences.append(current.strip())
                current = ""
        if current:
            sentences.append(current.strip())

    processed_sentences = []
    for s in sentences:
        words = s.split()
        if len(words) >= 12 and all(p not in s for p in [",", "，", "、", ";", "；"]):
            s = " ".join(words[:12]) + ", " + " ".join(words[12:])
        processed_sentences.append(s)

    current_chunk = ""
    for s in processed_sentences:
        s = s.strip()
        if not s:
            continue

        if len(current_chunk) + len(s) + 1 <= max_chars:
            current_chunk += " " + s if current_chunk else s
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = s

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def get_cache_key(text: str, voice_id: str, model_id: str, settings: dict) -> str:
    """Generate a unique cache key based on input parameters."""
    data = {
        "text": text,
        "voice_id": voice_id,
        "model_id": model_id,
        "settings": settings,
    }
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def convert_to_wav(input_path: str, output_path: str) -> str:
    try:
        if not shutil.which("ffmpeg"):
            logger.warning("ffmpeg not found, skipping conversion")
            return input_path

        cmd = [
            "ffmpeg",
            "-i",
            input_path,
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=7",
            "-ar",
            "24000",
            "-ac",
            "1",
            "-map_metadata",
            "-1",
            "-sample_fmt",
            "s16",
            "-y",
            "-v",
            "error",
            output_path,
        ]

        logger.info(f"Post-processing audio: {input_path} -> {output_path}")
        subprocess.run(cmd, check=True)
        return output_path

    except Exception as e:
        logger.error(f"Error converting audio: {e}")
        return input_path


def concat_wavs_with_crossfade(wav_files: list[str], output_path: str) -> str:
    if not shutil.which("ffmpeg"):
        logger.warning("ffmpeg not found, skipping concat")
        return wav_files[0]
    if len(wav_files) == 1:
        return wav_files[0]
    inputs = []
    for f in wav_files:
        inputs.extend(["-i", f])
    d = max(CROSSFADE_MS / 1000.0, 0.01)
    filters = []
    last_label = "0:a"
    for i in range(1, len(wav_files)):
        out_label = f"a{i}"
        filters.append(
            f"[{last_label}][{i}:a]acrossfade=d={d}:c1=tri:c2=tri[{out_label}]"
        )
        last_label = out_label
    filter_complex = (
        ";".join(filters) + f";[{last_label}]loudnorm=I=-16:TP=-1.5:LRA=7[aout]"
    )
    cmd = [
        "ffmpeg",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[aout]",
        "-ar",
        "24000",
        "-ac",
        "1",
        "-map_metadata",
        "-1",
        "-sample_fmt",
        "s16",
        "-y",
        "-v",
        "error",
        output_path,
    ]
    subprocess.run(cmd, check=True)
    return output_path


def generate_speech_segment(
    text: str,
    voice_id: str,
    model_id: str,
    voice_settings: dict,
    use_cache: bool = True,
    origin_user_id=None,
) -> dict:
    cache_key = get_cache_key(text, voice_id, model_id, voice_settings)
    wav_path, meta_path = _get_cache_paths(cache_key)
    text_hash = _text_hash(text)
    snippet = _snippet(text)
    if use_cache and os.path.exists(wav_path):
        _log_event(
            "tts_cache_hit",
            {"text_hash": text_hash, "voice_id": voice_id, "cached": True},
        )
        _update_accessed_at(meta_path)
        try:
            os.utime(wav_path, None)
        except Exception:
            pass
        return {"ok": True, "file": wav_path, "cached": True, "cache_key": cache_key}
    if not _circuit_allows():
        return {"ok": False, "message": "Circuit open"}
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {"text": text, "model_id": model_id, "voice_settings": voice_settings}
    for attempt in range(1, TTS_MAX_RETRIES + 1):
        try:
            with _semaphore:
                start_time = time.time()
                response = requests.post(url, json=payload, headers=headers, timeout=60)
            latency = time.time() - start_time
            status = response.status_code
            if status == 200:
                tmp_mp3 = os.path.join(CACHE_DIR, f"{cache_key}.tmp.mp3")
                with open(tmp_mp3, "wb") as f:
                    f.write(response.content)
                final_wav = convert_to_wav(tmp_mp3, wav_path)
                try:
                    os.remove(tmp_mp3)
                except Exception:
                    pass
                size_bytes = 0
                try:
                    size_bytes = os.path.getsize(final_wav)
                except Exception:
                    pass
                now_iso = _now_iso()
                metadata = {
                    "hash": cache_key,
                    "snippet": snippet,
                    "created_at": now_iso,
                    "accessed_at": now_iso,
                    "voice_id": voice_id,
                    "model_id": model_id,
                    "stability": voice_settings.get("stability"),
                    "similarity_boost": voice_settings.get("similarity_boost"),
                    "char_count": len(text),
                    "origin": origin_user_id or "anon",
                    "size_bytes": size_bytes,
                    "text_hash": text_hash,
                    "cached": False,
                    "cost_estimated": len(text) * TTS_COST_PER_CHAR,
                }
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                _circuit_record_success()
                _log_event(
                    "tts_segment_success",
                    {
                        "status": status,
                        "latency": latency,
                        "text_hash": text_hash,
                        "voice_id": voice_id,
                    },
                )
                return {
                    "ok": True,
                    "file": final_wav,
                    "cached": False,
                    "cache_key": cache_key,
                }
            if status == 429 or status >= 500:
                _circuit_record_failure()
                _log_event(
                    "tts_segment_retry",
                    {
                        "status": status,
                        "attempt": attempt,
                        "text_hash": text_hash,
                        "voice_id": voice_id,
                    },
                )
                jitter = random.uniform(0, 0.5)
                time.sleep((2 ** (attempt - 1)) + jitter)
                continue
            _log_event(
                "tts_segment_error",
                {"status": status, "text_hash": text_hash, "voice_id": voice_id},
            )
            return {
                "ok": False,
                "message": f"API Error {status}",
                "status_code": status,
            }
        except requests.exceptions.Timeout:
            _circuit_record_failure()
            _log_event(
                "tts_segment_retry",
                {
                    "reason": "timeout",
                    "attempt": attempt,
                    "text_hash": text_hash,
                    "voice_id": voice_id,
                },
            )
            jitter = random.uniform(0, 0.5)
            time.sleep((2 ** (attempt - 1)) + jitter)
            continue
        except requests.exceptions.RequestException as e:
            _circuit_record_failure()
            jitter = random.uniform(0, 0.5)
            time.sleep((2 ** (attempt - 1)) + jitter)
            _log_event(
                "tts_segment_error",
                {"error": str(e), "text_hash": text_hash, "voice_id": voice_id},
            )
    return {"ok": False, "message": "API unavailable"}


def generate_speech(
    text: str,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL_ID,
    stability: float = DEFAULT_STABILITY,
    similarity_boost: float = DEFAULT_SIMILARITY,
    use_cache: bool = True,
    origin_user_id=None,
    consent: bool = False,
) -> dict:
    request_start = time.time()
    if not ELEVENLABS_API_KEY:
        _finalize_request_metrics("error", voice_id, model_id, request_start)
        return {"ok": False, "message": "ELEVENLABS_API_KEY not found in configuration"}

    user_key = f"user:{origin_user_id}" if origin_user_id else "anon"
    if similarity_boost >= 0.3 and not consent:
        _finalize_request_metrics("rejected", voice_id, model_id, request_start)
        return {
            "ok": False,
            "message": "ต้องยืนยัน consent ก่อนใช้ similarity_boost สูง",
        }
    if not _rate_limit_allow(user_key):
        _finalize_request_metrics("rate_limited", voice_id, model_id, request_start)
        return {"ok": False, "message": "ขณะนี้คำขอมากเกินไป กรุณาลองใหม่ภายหลัง"}
    global _cleanup_counter
    _cleanup_counter += 1
    if _cleanup_counter % 20 == 0:
        cleanup_cache()

    processed_text = normalize_text(text)
    char_count = len(processed_text)
    cost_estimated = char_count * TTS_COST_PER_CHAR
    TTS_CHARS_PROCESSED_TOTAL.inc(char_count)
    if cost_estimated > 0:
        TTS_COST_ESTIMATED_TOTAL.inc(cost_estimated)
    voice_settings = {"stability": stability, "similarity_boost": similarity_boost}
    request_hash = get_cache_key(processed_text, voice_id, model_id, voice_settings)
    final_wav, final_meta = _get_cache_paths(request_hash)
    text_hash = _text_hash(processed_text)
    snippet = _snippet(processed_text)
    _log_event(
        "tts_request_start",
        {
            "request_hash": request_hash,
            "user_id": user_key,
            "snippet": snippet,
            "voice_id": voice_id,
            "model_id": model_id,
            "char_count": char_count,
        },
    )
    if TTS_COST_ALERT_THRESHOLD > 0 and cost_estimated > TTS_COST_ALERT_THRESHOLD:
        _log_event(
            "tts_cost_alert",
            {
                "request_hash": request_hash,
                "user_id": user_key,
                "voice_id": voice_id,
                "cost_estimated": cost_estimated,
            },
        )
    if use_cache and os.path.exists(final_wav):
        _cache_hit()
        _log_event(
            "tts_cache_hit",
            {
                "request_hash": request_hash,
                "user_id": user_key,
                "voice_id": voice_id,
                "cached": True,
            },
        )
        _update_accessed_at(final_meta)
        try:
            os.utime(final_wav, None)
        except Exception:
            pass
        latency_seconds = _finalize_request_metrics(
            "success", voice_id, model_id, request_start
        )
        _log_event(
            "tts_request",
            {
                "request_hash": request_hash,
                "user_id": user_key,
                "char_count": char_count,
                "latency_ms": int(latency_seconds * 1000),
                "cache_hit": True,
                "cost_estimated": cost_estimated,
                "status": "success",
                "voice_id": voice_id,
                "model_id": model_id,
            },
        )
        return {
            "ok": True,
            "file": final_wav,
            "message": "Loaded from cache",
            "cached": True,
        }
    if not _circuit_allows():
        fallback_processed = normalize_text(DEFAULT_FALLBACK_TEXT)
        fallback_hash = get_cache_key(
            fallback_processed, voice_id, model_id, voice_settings
        )
        fallback_wav, _ = _get_cache_paths(fallback_hash)
        if os.path.exists(fallback_wav):
            _cache_hit()
            latency_seconds = _finalize_request_metrics(
                "fallback", voice_id, model_id, request_start
            )
            _log_event(
                "tts_request",
                {
                    "request_hash": request_hash,
                    "user_id": user_key,
                    "char_count": char_count,
                    "latency_ms": int(latency_seconds * 1000),
                    "cache_hit": True,
                    "cost_estimated": cost_estimated,
                    "status": "fallback",
                    "voice_id": voice_id,
                    "model_id": model_id,
                },
            )
            return {
                "ok": True,
                "file": fallback_wav,
                "message": "Fallback audio",
                "cached": True,
            }
        _cache_miss()
        latency_seconds = _finalize_request_metrics(
            "error", voice_id, model_id, request_start
        )
        _log_event(
            "tts_request",
            {
                "request_hash": request_hash,
                "user_id": user_key,
                "char_count": char_count,
                "latency_ms": int(latency_seconds * 1000),
                "cache_hit": False,
                "cost_estimated": cost_estimated,
                "status": "error",
                "voice_id": voice_id,
                "model_id": model_id,
            },
        )
        return {"ok": False, "message": "Circuit open"}

    chunks = chunk_text(processed_text)
    if not chunks:
        _cache_miss()
        _finalize_request_metrics("error", voice_id, model_id, request_start)
        return {"ok": False, "message": "No text to synthesize"}

    segment_files = []

    for i, chunk in enumerate(chunks):
        logger.info(f"Generating chunk {i+1}/{len(chunks)}: {chunk[:30]}...")
        res = generate_speech_segment(
            chunk,
            voice_id,
            model_id,
            voice_settings,
            use_cache,
            origin_user_id=user_key,
        )
        if not res["ok"]:
            if use_cache and os.path.exists(final_wav):
                _cache_hit()
                _update_accessed_at(final_meta)
                latency_seconds = _finalize_request_metrics(
                    "success", voice_id, model_id, request_start
                )
                _log_event(
                    "tts_request",
                    {
                        "request_hash": request_hash,
                        "user_id": user_key,
                        "char_count": char_count,
                        "latency_ms": int(latency_seconds * 1000),
                        "cache_hit": True,
                        "cost_estimated": cost_estimated,
                        "status": "success",
                        "voice_id": voice_id,
                        "model_id": model_id,
                    },
                )
                return {
                    "ok": True,
                    "file": final_wav,
                    "message": "Loaded from cache",
                    "cached": True,
                }
            fallback_processed = normalize_text(DEFAULT_FALLBACK_TEXT)
            fallback_hash = get_cache_key(
                fallback_processed, voice_id, model_id, voice_settings
            )
            fallback_wav, _ = _get_cache_paths(fallback_hash)
            if os.path.exists(fallback_wav):
                _cache_hit()
                latency_seconds = _finalize_request_metrics(
                    "fallback", voice_id, model_id, request_start
                )
                _log_event(
                    "tts_request",
                    {
                        "request_hash": request_hash,
                        "user_id": user_key,
                        "char_count": char_count,
                        "latency_ms": int(latency_seconds * 1000),
                        "cache_hit": True,
                        "cost_estimated": cost_estimated,
                        "status": "fallback",
                        "voice_id": voice_id,
                        "model_id": model_id,
                    },
                )
                return {
                    "ok": True,
                    "file": fallback_wav,
                    "message": "Fallback audio",
                    "cached": True,
                }
            _cache_miss()
            latency_seconds = _finalize_request_metrics(
                "error", voice_id, model_id, request_start
            )
            _log_event(
                "tts_request",
                {
                    "request_hash": request_hash,
                    "user_id": user_key,
                    "char_count": char_count,
                    "latency_ms": int(latency_seconds * 1000),
                    "cache_hit": False,
                    "cost_estimated": cost_estimated,
                    "status": "error",
                    "voice_id": voice_id,
                    "model_id": model_id,
                },
            )
            return res
        segment_files.append(res["file"])

    if len(segment_files) == 1:
        if segment_files[0] != final_wav:
            try:
                shutil.copyfile(segment_files[0], final_wav)
            except Exception:
                final_wav = segment_files[0]
    else:
        try:
            final_wav = concat_wavs_with_crossfade(segment_files, final_wav)
        except Exception as e:
            logger.error(f"Error combining chunks: {e}")
            _cache_miss()
            _finalize_request_metrics("error", voice_id, model_id, request_start)
            return {"ok": False, "message": f"Error combining audio: {e}"}

    size_bytes = 0
    try:
        size_bytes = os.path.getsize(final_wav)
    except Exception:
        pass
    now_iso = _now_iso()
    metadata = {
        "hash": request_hash,
        "snippet": snippet,
        "created_at": now_iso,
        "accessed_at": now_iso,
        "voice_id": voice_id,
        "model_id": model_id,
        "stability": stability,
        "similarity_boost": similarity_boost,
        "char_count": char_count,
        "origin": user_key,
        "size_bytes": size_bytes,
        "text_hash": text_hash,
        "cached": False,
        "chunk_count": len(chunks),
        "consent": consent,
        "cost_estimated": cost_estimated,
    }
    with open(final_meta, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    _cache_miss()
    latency_seconds = _finalize_request_metrics(
        "success", voice_id, model_id, request_start
    )
    _log_event(
        "tts_request",
        {
            "request_hash": request_hash,
            "user_id": user_key,
            "char_count": char_count,
            "latency_ms": int(latency_seconds * 1000),
            "cache_hit": False,
            "cost_estimated": cost_estimated,
            "status": "success",
            "voice_id": voice_id,
            "model_id": model_id,
        },
    )
    return {
        "ok": True,
        "file": final_wav,
        "message": "Generated successfully",
        "chunks": len(chunks),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice clone utilities")
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument(
        "--cleanup-interval", type=int, default=TTS_CACHE_CLEANUP_INTERVAL_SECONDS
    )
    parser.add_argument("--start-cleanup-worker", action="store_true")
    parser.add_argument("--metrics", action="store_true")
    parser.add_argument("--mock-server", action="store_true")
    parser.add_argument("--mock-port", type=int, default=9000)
    args = parser.parse_args()
    if args.mock_server:
        start_mock_tts_server(args.mock_port)
        sys.exit(0)
    if args.cleanup:
        cleanup_cache()
    if args.start_cleanup_worker:
        start_cache_cleanup_worker(args.cleanup_interval)
        time.sleep(args.cleanup_interval)
    if args.metrics:
        print(json.dumps(get_tts_metrics(), ensure_ascii=False))
    if (
        not args.cleanup
        and not args.metrics
        and not args.start_cleanup_worker
        and not args.mock_server
    ):
        test_text = "สวัสดีครับ นี่คือการทดสอบระบบเสียง ElevenLabs ภาษาไทยครับ"
        result = generate_speech(test_text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
