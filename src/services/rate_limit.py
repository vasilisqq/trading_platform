from src.core.redis import get_redis

class RateLimiter:
    def __init__(self, prefix: str = "rate_limit:login"):
        self.prefix = prefix

    async def too_many(self, key: str, limit: int) -> bool:      
        redis = await get_redis()
        v = await redis.get(f"{self.prefix}:{key}")
        return v is not None and int(v) >= limit

    async def incr(self, key: str, window: int) -> None:   
        redis = await get_redis()
        full = f"{self.prefix}:{key}"
        if await redis.incr(full) == 1:
            await redis.expire(full, window)