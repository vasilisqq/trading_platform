from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from src.models.user import User
from src.schemas.user import CreateUser, UserLogin
from uuid import uuid7
from uuid import UUID


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email).limit(1))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.username == username).limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, user_data: CreateUser, hashed_password: str) -> User:
        user = User(
            id=uuid7(),
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
        )
        self.db.add(user)
        return user
    
    async def get_by_email_or_username(self, email: str, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                or_(User.email == email, User.username == username)
            ).limit(1)
        )
        return result.scalar_one_or_none()


    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
