from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.repositories.user_repository import UserRepository


class UserService():
    def __init__(self, db:AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)


    async def get_user_by_email(self, email: str) -> User:
        return await self.repo.get_by_email(email)
    
    async def get_user_by_username(self, username: str) -> User:
        return await self.repo.get_by_username(username)
    




