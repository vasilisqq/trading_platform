import resend
from src.core.config import settings
from uuid import uuid4
from src.core.redis import get_redis
from uuid import UUID
from fastapi import HTTPException
from math import ceil
from typing import Any


class EmailVerification:
    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY.get_secret_value()
        self.prefix = "email:verification"
        self.rate_prefix = "rate_limit:send"
        self.rate_password_forgot_prefix = "rate_limit:password_forgot"
        self.password_forgot_prefix = "password_forgot:verification"

    async def _check_email(self, token:str, prefix:str) -> Any:
        redis = await get_redis()
        result = await redis.get(f"{prefix}:{token}")
        if result is not None:
            await self.delete_token(token, prefix)
        return result

    async def _send_email(self, email:str, prefix:str,
                          rate_prefix:str,var_set:Any, 
                          subject:str, template_id:str,
                          variable_name: str, router:str) -> None:
        available_seconds = await self.check_for_last_send(email, rate_prefix)
        if available_seconds:
            raise HTTPException(429, f"Too many requests")
        token = str(uuid4())
        redis = await get_redis()
        await resend.Emails.send_async({
        "from": "onboarding@resend.dev",
        "to": email,
        "subject": subject,
        "template": {
            "id": template_id,
            "variables" : {variable_name: f"{settings.PUBLIC_URL}/auth/{router}?token={token}"}
            }
        })
        await redis.setex(f"{prefix}:{token}", settings.EXPIRE_EMAIL_HOURS * 3600, str(var_set))
        await redis.setex(f"{rate_prefix}:{email}", 300, "sent")


    async def send_email_register(self, email:str, user_id:UUID) -> None:
        await self._send_email(
            email, self.prefix, self.rate_prefix,
            user_id, "Email verification", settings.TEMPLATE_ID,
            "verify_url", "verify-email"
        )

    async def send_email_new_password(self, email:str) -> None:
        await self._send_email(
            email, self.password_forgot_prefix, self.rate_password_forgot_prefix,
            email, "Check your email for changing password", settings.TEMPLATE_PASSWORD_ID,
            "reset_url", "reset-password"
        )

    async def verify_email_register(self, token:str) -> str|None:
        return await self._check_email(token, self.prefix)

    async def verify_email_password_changing(self, token:str) -> str|None:
        return await self._check_email(token, self.password_forgot_prefix)

    async def check_for_last_send(self, email:str, prefix:str) -> int:
        redis = await get_redis()
        expire_seconds = await redis.ttl(f"{prefix}:{email}")
        if expire_seconds < 0:
            return 0
        return expire_seconds

    async def delete_token(self, token:str, prefix:str) -> None:
        redis = await get_redis()
        await redis.delete(f"{prefix}:{token}")


    
        
