import redis
import json
import logging
from typing import Optional, Any
from src.config.settings import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Fail fast check
            self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        if not self.redis_client:
            return None
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        if not self.redis_client:
            return False
        try:
            self.redis_client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

# Global instance
cache = CacheService()
