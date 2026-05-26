from services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from src.core.db import get_db


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService()

