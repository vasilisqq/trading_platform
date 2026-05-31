from uuid import UUID
from datetime import datetime, timezone
from src.core.redis import get_redis


class TokenBlackListService:
    def __init__(self):     
        self.prefix = "access:blacklist"

    async def blacklist_access_token(self, jti:str, exp:datetime) -> None:
        redis = await get_redis()
        now = datetime.now(timezone.utc)
        ttl_seconds = int((exp - now).total_seconds())
        if ttl_seconds > 0:
            await redis.setex(f"{self.prefix}:{jti}", ttl_seconds, "revoked")


    async def is_blacklisted(self, jti: str) -> bool:
        redis = await get_redis()
        return await redis.get(f"{self.prefix}:{jti}") is not None
