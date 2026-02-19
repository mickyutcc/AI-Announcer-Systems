"""
ClamAV scanning helpers.

Behavior:
- Try to use pyclamd (connect to clamd). If available and working, use it.
- Otherwise fall back to clamscan subprocess (requires clamscan installed).
- If neither available, returns status 'unavailable' (not error) so caller can decide to block or allow based on config.AV_STRICT.
"""
import tempfile
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def _scan_with_clamscan_bytes(data: bytes) -> dict:
    # write to temp file and run clamscan
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(data)
        tf.flush()
        tmpname = tf.name
    try:
        # clamscan exit 0 => no virus; exit 1 => virus found; exit >1 => error
        proc = subprocess.run(["clamscan", "--no-summary", tmpname], capture_output=True, text=True, timeout=30)
        out = proc.stdout + proc.stderr
        if proc.returncode == 0:
            return {"status": "clean", "detail": out}
        elif proc.returncode == 1:
            return {"status": "infected", "detail": out}
        else:
            return {"status": "error", "detail": out}
    except FileNotFoundError:
        return {"status": "unavailable", "detail": "clamscan not found"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
    finally:
        try:
            os.unlink(tmpname)
        except Exception:
            pass

def scan_bytes(data: bytes) -> dict:
    """
    Scan bytes and return dict:
      {"status": "clean"|"infected"|"error"|"unavailable", "detail": "..."}
    """
    # Try pyclamd first (if installed)
    try:
        import pyclamd
        try:
            cd = pyclamd.ClamdNetworkSocket()  # tries network socket (localhost:3310)
            res = cd.scan_stream(data)
            # res is None if clean, otherwise dict { 'stream': ('FOUND', 'Eicar-Test-Signature') }
            if res is None:
                return {"status": "clean", "detail": "pyclamd: clean"}
            else:
                return {"status": "infected", "detail": str(res)}
        except pyclamd.ConnectionError:
            # try unix socket
            try:
                cd = pyclamd.ClamdUnixSocket()
                res = cd.scan_stream(data)
                if res is None:
                    return {"status": "clean", "detail": "pyclamd unix: clean"}
                else:
                    return {"status": "infected", "detail": str(res)}
            except Exception:
                # fallback to clamscan
                pass
        except Exception as e:
            logger.exception("pyclamd error")
    except Exception:
        # pyclamd not installed
        pass

    # fallback to clamscan subprocess
    return _scan_with_clamscan_bytes(data)
