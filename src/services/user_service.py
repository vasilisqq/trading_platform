from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError 
from fastapi import HTTPException
from src.models.user import User
from src.schemas.user import CreateUser, UserLogin
from src.repositories.user_repository import UserRepository
from src.repositories.session_repository import SessionRepository
from core.security import hash_password, create_access_token, create_refresh_token, verify_password, decode_refresh_token, decode_access_token
from src.exceptions import UserAlreadyExistsError, UserNotFoundError, UserDisabledError
from jwt import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timezone, timedelta
from src.core.config import settings
from src.services.token_blacklist import TokenBlackListService
from src.services.email_verification import EmailVerification
from uuid import UUID


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)
        self.session_repo = SessionRepository(db)
        self.token_blacklist = TokenBlackListService()
        self.email_verification = EmailVerification()


    async def register(self, user_data: CreateUser) -> None:
        hashed_password = hash_password(user_data.password)
        user = await self.repo.create(user_data, hashed_password)
        try:
            await self.db.commit()
            await self.email_verification.send_email_register(user.email, user.id)
        except IntegrityError:
            await self.db.rollback()
            existing = await self.repo.get_by_email_or_username(
                user_data.email,
                user_data.username
            )
            if existing.email == user_data.email:
                raise UserAlreadyExistsError("email")
            if existing.username == user_data.username:
                raise UserAlreadyExistsError("username")
            raise


    async def login(self, user_data: UserLogin) -> dict[str, str|User]:
        user = await self.repo.get_by_email(user_data.email)
        if not user or not verify_password(user_data.password, user.hashed_password):
            raise UserNotFoundError()
        if not user.is_active:
            raise UserDisabledError()
        if not user.email_verified:
            await self.email_verification.send_email_register(user.email, user.id)
            raise HTTPException(403, "Check your email for verification")
        tokens = await self._create_tokens(user)
        await self.db.commit()
        return tokens

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.repo.get_by_email(email)

    async def get_user_by_username(self, username: str) -> User | None:
        return await self.repo.get_by_username(username)
    
    async def refresh(self, refresh_token:str) -> dict:
        try:
            decode_refresh_token(refresh_token)
        except (ExpiredSignatureError, InvalidTokenError):
            raise UserNotFoundError()
        
        session = await self.session_repo.get_by_token(refresh_token)
        if not session:
            raise UserNotFoundError()
        
        await self.session_repo.delete(session)
        
        user = await self.repo.get_by_id(session.user_id)
        if not user:
            raise UserNotFoundError()
        if not user.is_active:
            raise UserDisabledError()
        
        tokens = await self._create_tokens(user)
        await self.db.commit()
        return tokens
        
    async def logout(self, refresh_token:str, access_token:str) -> None:
        await self.session_repo.delete_by_hash(refresh_token)
        await self.db.commit()
        try:
            payload = decode_access_token(access_token, verify_exp=False)
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            await self.token_blacklist.blacklist_access_token(payload["jti"], exp)
        except InvalidTokenError:
            pass


    async def _create_tokens(self, user: User):
        access_token = create_access_token(
                {"sub": str(user.id), "email": user.email, "username": user.username}
            )
        refresh_token = create_refresh_token({"sub": str(user.id)})
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.session_repo.create(user.id, refresh_token, expires_at)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user
        }


    async def verify_email(self, token:str) -> dict[str, str|User]:
        user_id = await self.email_verification.verify_email(token)
        if not user_id:
            raise HTTPException(400, "Invalid or expired token")
        user = await self.repo.get_by_id(UUID(user_id))
        if not user:
            raise UserNotFoundError()
        user.email_verified = True
        tokens = await self._create_tokens(user)
        await self.db.commit()
        return tokens
    
    async def forgot_password(self, email:str) -> None:
        if await self.repo.get_by_email(email):
            await self.email_verification.send_email_new_password(email)

    
    async def reset_password(self, token:str, password:str) -> dict[str, str]:
        email = await self.email_verification.verify_email_password_changing(token)
        if not email:
            raise HTTPException(400, "Invalid or expired token")
        hashed_password = hash_password(password)
        await self.repo.update_password(email, hashed_password)
        try:
            await self.db.commit()
            return {"message": "password was successfuly changed"}
        except:
            raise UserNotFoundError()