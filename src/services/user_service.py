from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.token import TokenResponse
from src.schemas.user import CreateUser, UserResponse
from src.repositories.user_repository import UserRepository
from core.security import hash_password, create_access_token, create_refresh_token
from src.exceptions import UserAlreadyExistsError, DataBaseError, TokenCreatingError


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)

    async def register(self, user_data: CreateUser) -> dict[str, str|User]:
        if await self.get_user_by_email(user_data.email):
            raise UserAlreadyExistsError("email")
        if await self.get_user_by_username(user_data.username):
            raise UserAlreadyExistsError("username")
        hashed_password = hash_password(user_data.password)
        user = await self.repo.create(user_data, hashed_password)
        if not user:
            raise DataBaseError("users")
        access_token = create_access_token(
            {"sub": str(user.id), "email": user.email}
        )
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user
        }
        
    async def get_user_by_email(self, email: str) -> User | None:
        return await self.repo.get_by_email(email)

    async def get_user_by_username(self, username: str) -> User | None:
        return await self.repo.get_by_username(username)
