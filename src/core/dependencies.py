from services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.core.db import get_db
from src.models.user import User
import jwt
from src.repositories.user_repository import UserRepository
from src.exceptions import UserNotFoundError, UserDisabledError
from src.services.token_blacklist import TokenBlackListService
from src.core.security import decode_access_token

security = HTTPBearer()

async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db = Depends(get_db)) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    token_blacklist = TokenBlackListService()
    if await token_blacklist.is_blacklisted(payload.get("jti")):
        raise HTTPException(status_code=401, detail="Invalid token")
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
         raise UserNotFoundError()
    if not user.is_active:
        raise UserDisabledError()
        
    return user
    


