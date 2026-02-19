"""
Token-bucket rate limiter backed by Redis.
Each platform has its own bucket with configurable capacity and refill rate.
"""
import asyncio
import time
from dataclasses import dataclass

import redis.asyncio as aioredis

from config.settings import get_settings


@dataclass
class RateLimitConfig:
    platform: str
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int


PLATFORM_LIMITS: dict[str, RateLimitConfig] = {
    "twitter": RateLimitConfig("twitter", 15, 300, 1500),
    "tiktok": RateLimitConfig("tiktok", 10, 200, 1000),
    "linkedin": RateLimitConfig("linkedin", 10, 100, 500),
    "instagram": RateLimitConfig("instagram", 20, 200, 1000),
}


class RateLimiter:
    def __init__(self):
        self._settings = get_settings()
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self._settings.redis_url, decode_responses=True
            )
        return self._redis

    async def acquire(self, platform: str, endpoint: str = "default") -> None:
        """
        Block until a request slot is available for the given platform.
        Uses a sliding window in Redis.
        """
        config = PLATFORM_LIMITS.get(platform)
        if not config:
            return

        redis = await self._get_redis()
        key = f"ratelimit:{platform}:{endpoint}:minute"
        now = time.time()
        window_start = now - 60

        async with redis.pipeline() as pipe:
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            _, count = await pipe.execute()

        if count >= config.requests_per_minute:
            wait_time = 60 - (now - window_start)
            await asyncio.sleep(max(0, wait_time))

        async with redis.pipeline() as pipe:
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, 120)
            await pipe.execute()

    async def check_daily_limit(self, platform: str) -> bool:
        """Returns True if still under daily limit."""
        config = PLATFORM_LIMITS.get(platform)
        if not config:
            return True

        redis = await self._get_redis()
        key = f"ratelimit:{platform}:daily"
        count = await redis.get(key)
        return int(count or 0) < config.requests_per_day

    async def increment_daily(self, platform: str) -> None:
        redis = await self._get_redis()
        key = f"ratelimit:{platform}:daily"
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400)
        await pipe.execute()

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
