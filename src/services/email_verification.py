import resend
from src.core.config import settings
from uuid import uuid4
from src.core.redis import get_redis
from uuid import UUID
from fastapi import HTTPException


class EmailVerification:
    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY.get_secret_value()
        self.prefix = "email:verification"
        self.rate_prefix = "rate_limit:send"

    async def send_email(self, email_to:str, user_id:UUID):
        available_seconds = await self.check_for_last_send(email_to)
        if available_seconds:
            raise HTTPException(403, f"Please, wait {int(available_seconds/60)} minutes")
        token = str(uuid4())
        redis = await get_redis()
        await resend.Emails.send_async({
        "from": "onboarding@resend.dev",
        "to": email_to,
        "subject": "Email verification",
        "template": {
            "id": settings.TEMPLATE_ID,
            "variables" : {
                "verify_url": f"{settings.PUBLIC_URL}/auth/verify-email?token={token}"
                }
            }
        })
        await redis.setex(f"{self.prefix}:{token}", settings.EXPIRE_EMAIL_HOURS * 3600, str(user_id))
        await redis.setex(f"{self.rate_prefix}:{email_to}", 300, "sent")

    async def verify_email(self, token:str) -> str|None:
        redis = await get_redis()
        user_id = await redis.get(f"{self.prefix}:{token}")
        if user_id is not None:
            await self.delete_token(token)
        return user_id


    async def check_for_last_send(self, email:str) -> int:
        redis = await get_redis()
        expire_seconds = await redis.ttl(f"{self.rate_prefix}:{email}")
        if expire_seconds < 0:
            return 0
        return expire_seconds
             

    

    async def delete_token(self, token:str) -> None:
        redis = await get_redis()
        await redis.delete(f"{self.prefix}:{token}")