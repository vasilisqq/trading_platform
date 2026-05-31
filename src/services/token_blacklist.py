from uuid import UUID
from datetime import datetime, timezone
import redis.asyncio as redis


class TokenBlackListService:
    def __init__(self, redis: redis.Redis):
        self.redis = redis        
        self.prefix = "access:blacklist"

    async def blacklist_access_token(self, jti:str, exp:datetime) -> None:
        now = datetime.now(timezone.utc)
        ttl_seconds = int((exp - now).total_seconds())
        if ttl_seconds > 0:
            await self.redis.setex(f"{self.prefix}:{jti}", ttl_seconds, "revoked")


    async def is_blacklisted(self, jti: str) -> bool:
        return await self.redis.get(f"{self.prefix}:{jti}") is not None
