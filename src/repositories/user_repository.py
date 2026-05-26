from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email==email).limit(1)
        )
        return await result.scalar_one_or_none()
    

    async def get_by_username(self, username: str) -> User:
        result = self.db.execute(
            select(User).where(User.username==username).limit(1)
        )
        return result.scalar_one_or_none()
    




