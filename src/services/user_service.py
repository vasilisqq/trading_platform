from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.user import CreateUser, UserLogin
from src.repositories.user_repository import UserRepository
from core.security import hash_password, create_access_token, create_refresh_token, verify_password, decode_refresh_token
from src.exceptions import UserAlreadyExistsError, DataBaseError, UserNotFoundError, UserDisabledError
from jwt import ExpiredSignatureError, InvalidTokenError


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

    async def login(self, user_data: UserLogin) -> dict[str, str|User]:
        user = await self.repo.get_user(user_data.email)
        if not user or not verify_password(user_data.password, user.hashed_password):
            raise UserNotFoundError()
        if not user.is_active:
            raise UserDisabledError()
        access_token = create_access_token(
            {"sub": str(user.id), "email": user.email, "username": user.username}
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
    
    async def refresh(self, refresh_token:str) -> dict:
        try:
            payload = decode_refresh_token(refresh_token)
        except (ExpiredSignatureError, InvalidTokenError):
            raise UserNotFoundError()
        user_id = payload.get("sub")
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        if not user.is_active:
            raise UserDisabledError()

        access_token = create_access_token({"sub": str(user.id), "email": user.email, "username": user.username})
        new_refresh_token = create_refresh_token({"sub": str(user.id)})

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "user": user
        }


