import httpx
from src.core.config import settings
from uuid import uuid4
from src.core.redis import get_redis
from fastapi import HTTPException
from urllib.parse import urlencode


class GoogleOAuthService:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    

    async def get_auth_url(self, state) -> str:
        redis = await get_redis()
        await redis.setex(f"oauth:state:{state}", 600, "pending")
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID.get_secret_value(),
            "redirect_uri": settings.GOOGLE_REDIRECT_URI.get_secret_value(),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
    

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID.get_secret_value(),
                    "client_secret": settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI.get_secret_value(),
                    "grant_type": "authorization_code",
                }
            )
            if response.status_code != 200:
                error_data = response.json()
                error_description = error_data.get("error_description", "Unknown error")
                
                if response.status_code == 400:
                    raise HTTPException(400, f"Invalid request: {error_description}")
                elif response.status_code == 401:
                    raise HTTPException(401, "Invalid client credentials")
                elif response.status_code == 403:
                    raise HTTPException(403, "Access denied")
                elif response.status_code == 429:
                    raise HTTPException(429, "Too many requests to Google")
                else:
                    raise HTTPException(500, f"Google error: {error_description}")
            
            return response.json()
    
    
    async def get_user_info(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code != 200:
                if response.status_code == 401:
                    raise HTTPException(401, "Invalid or expired Google access token")
                elif response.status_code == 403:
                    raise HTTPException(403, "Insufficient permissions")
                else:
                    raise HTTPException(500, f"Failed to get user info: {response.status_code}")
            
            return response.json()
                
        
    async def verify_state(self, state:str) -> bool:
        redis = await get_redis()
        result = await redis.get(f"oauth:state:{state}")
        if result:
            await redis.delete(f"oauth:state:{state}")
            return True
        return False