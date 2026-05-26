from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.user import CreateUser
from src.repositories.user_repository import UserRepository
from core.security import hash_password
from src.exceptions import UserAlreadyExistsError


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)

    async def register(self, user_data: CreateUser) -> None:
        if await self.get_user_by_email(user_data.email):
            raise UserAlreadyExistsError("email")
        if await self.get_user_by_username(user_data.username):
            raise UserAlreadyExistsError("username")
        hashed_password = hash_password(user_data.password)
        if await self.repo.create(user_data, hashed_password):
            return True

    async def get_user_by_email(self, email: str) -> User:
        return await self.repo.get_by_email(email)

    async def get_user_by_username(self, username: str) -> User:
        return await self.repo.get_by_username(username)
