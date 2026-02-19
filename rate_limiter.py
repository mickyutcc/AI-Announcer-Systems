import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# In-memory fallback store
_rate_store = {}

def _get_redis_client():
    # lazy import to avoid hard dependency
    try:
        from cache_helper import get_redis_client
        rc = get_redis_client()
        return rc
    except Exception as e:
        logger.debug("Redis client not available: %s", e)
        return None

def rate_limit(key_fn, max_calls: int, period_seconds: int):
    """
    key_fn: callable(*args, **kwargs)->str to produce unique key (e.g., user:{id} or ip:{ip})
    """
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                key = key_fn(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Rate limit key generation failed: {e}")
                return fn(*args, **kwargs)

            rc = _get_redis_client()
            if rc:
                # Redis implementation using INCR and EXPIRE atomically
                try:
                    cur = rc.incr(key)
                    if cur == 1:
                        rc.expire(key, period_seconds)
                    if int(cur) > max_calls:
                        logger.warning(f"Rate limit exceeded for {key}")
                        return {"status": "ERROR", "message": "Rate limit exceeded. Please try again later."}
                except Exception as e:
                    # If redis errors, fall back to in-memory
                    logger.exception("Redis rate limiter failed, falling back: %s", e)
                    _mem_rate_limit(key, max_calls, period_seconds)
            else:
                try:
                    _mem_rate_limit(key, max_calls, period_seconds)
                except Exception as e:
                     logger.warning(f"Rate limit exceeded (mem) for {key}")
                     return {"status": "ERROR", "message": "Rate limit exceeded. Please try again later."}
            return fn(*args, **kwargs)
        return wrapped
    return deco

def _mem_rate_limit(key: str, max_calls: int, period_seconds: int):
    now = int(time.time())
    calls, ts = _rate_store.get(key, (0, now))
    if now - ts > period_seconds:
        calls = 0
        ts = now
    if calls >= max_calls:
        raise Exception("Rate limit exceeded")
    _rate_store[key] = (calls + 1, ts)
