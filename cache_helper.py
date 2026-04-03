import os
import logging
import time
import json
from typing import Any, Optional, cast

try:
    import redis
except ImportError:
    redis = None

from config import REDIS_URL

logger = logging.getLogger(__name__)

def get_redis_client():
    if redis is None:
        return None
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.error(f"Failed to create Redis client: {e}")
        return None

class CacheInterface:
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError

class RedisCache(CacheInterface):
    def __init__(self, url: str):
        if redis is None:
            raise RuntimeError("redis package is not installed")
        self.client = redis.from_url(url, decode_responses=True)
        try:
            self.client.ping()
            logger.info(f"Connected to Redis at {url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def get(self, key: str) -> Optional[Any]:
        try:
            val = cast(Optional[str], self.client.get(key))
            if val:
                try:
                    return json.loads(val)
                except json.JSONDecodeError:
                    return val
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            if isinstance(value, (dict, list)):
                val_str = json.dumps(value)
            else:
                val_str = str(value)
            
            if ttl:
                return bool(self.client.setex(key, ttl, val_str))
            else:
                return bool(self.client.set(key, val_str))
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

class InMemoryCache(CacheInterface):
    def __init__(self):
        self._store: dict[str, tuple[Any, Optional[float]]] = {}
        logger.info("Initialized In-Memory Cache")

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if item is None:
            return None
        
        val, expiry = item
        if expiry and time.time() > expiry:
            del self._store[key]
            return None
        
        return val

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        expiry = time.time() + ttl if ttl else None
        self._store[key] = (value, expiry)
        return True

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

def get_cache() -> CacheInterface:
    if REDIS_URL and redis:
        try:
            return RedisCache(REDIS_URL)
        except Exception:
            logger.warning("Failed to initialize RedisCache, falling back to InMemoryCache")
            return InMemoryCache()
    else:
        return InMemoryCache()

# Singleton
cache = get_cache()
