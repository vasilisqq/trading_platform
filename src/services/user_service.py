from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError 
from fastapi import HTTPException
from src.models.user import User
from src.schemas.user import CreateUser, UserLogin
from src.repositories.user_repository import UserRepository
from src.repositories.session_repository import SessionRepository
from src.core.security import (
    hash_password, create_access_token, 
    create_refresh_token, verify_password, 
    decode_refresh_token, decode_access_token,
    DUMMY_PASSWORD_HASH
    )
from src.exceptions import UserAlreadyExistsError, UserNotFoundError, UserDisabledError
from jwt import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timezone, timedelta
from src.core.config import settings
from src.services.token_blacklist import TokenBlackListService
from src.services.email_verification import EmailVerification
from src.services.google_oauth import GoogleOAuthService
from uuid import UUID, uuid7
from src.services.rate_limit import RateLimiter


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)
        self.session_repo = SessionRepository(db)
        self.token_blacklist = TokenBlackListService()
        self.email_verification = EmailVerification()
        self.google_oauth = GoogleOAuthService()
        self.rate_limiter = RateLimiter()


    async def register(self, user_data: CreateUser) -> None:
        hashed_password = hash_password(user_data.password)
        user = await self.repo.create(user_data, hashed_password)
        try:
            await self.db.commit()
            return user
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


    async def login(self, user_data: UserLogin, ip) -> dict[str, str|User]:
        if await self.rate_limiter.too_many(f"email:{user_data.email}", 5) or \
                        await self.rate_limiter.too_many(f"ip:{ip}", 20):
            raise HTTPException(429, "Too many login attempts, try later")
        user = await self.repo.get_by_email(user_data.email)
        if not user:
            verify_password(user_data.password, DUMMY_PASSWORD_HASH)
            await self.rate_limiter.incr(f"email:{user_data.email}", 900)
            await self.rate_limiter.incr(f"ip:{ip}", 900)
            raise UserNotFoundError()
        if not verify_password(user_data.password, user.hashed_password):
            await self.rate_limiter.incr(f"email:{user_data.email}", 900)
            await self.rate_limiter.incr(f"ip:{ip}", 900)
            raise UserNotFoundError()
        if not user.is_active:
            await self.rate_limiter.incr(f"email:{user_data.email}", 900)
            await self.rate_limiter.incr(f"ip:{ip}", 900)
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
        user_id = await self.email_verification.verify_email_register(token)
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
        user = await self.repo.get_by_email(email)
        if not user:
            raise UserNotFoundError()
        await self.repo.update_password(email, hash_password(password))
        await self.session_repo.delete_all_for_user(user.id)   # без except_hash — отозвать всё
        await self.db.commit()
        return {"message": "password was successfully changed"}
        
        
    async def oauth_login(self, google_id: str, email: str) -> dict:
        user = await self.repo.get_by_google_id(google_id)
        if user:
            if not user.is_active:
                raise UserDisabledError()
        else:
            user = await self.repo.get_by_email(email)
            if user:
                if not user.is_active:
                    raise UserDisabledError()
                user.google_id=google_id
                user.email_verified = True
            else:
                username = email.split("@")[0]
                user = User(
                    id=uuid7(),
                    username=username,
                    email=email,
                    google_id=google_id,
                    email_verified=True
                )
                self.db.add(user)
        tokens = await self._create_tokens(user)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = await self.repo.get_by_google_id(google_id)
            if existing:
                if not existing.is_active:
                    raise UserDisabledError()
                user = existing
            else:
                # Конфликт username
                user.username = f"{user.username}_{user.google_id[:6]}"
                self.db.add(user)
            tokens = await self._create_tokens(user)
            await self.db.commit()
        return tokens
    
    async def google_auth(self, code: str, state:str) -> dict:
        if not await self.google_oauth.verify_state(state):
            raise UserNotFoundError()
        tokens = await self.google_oauth.exchange_code(code)
        user_info = await self.google_oauth.get_user_info(tokens["access_token"])
        if "sub" not in user_info or "email" not in user_info:
            raise HTTPException(500, "Invalid response from Google")    
        return await self.oauth_login(
            google_id=user_info["sub"],
            email=user_info["email"]
        )

    async def change_password(self, user: User, old_password:str, new_password:str, excpt_hash:str = None):
        if not user.hashed_password: #Oauth
            raise HTTPException(400, "User has no password")
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(400, "Password is incorrect")
        await self.repo.update_password(user.email, hash_password(new_password))
        await self.session_repo.delete_all_for_user(user.id, excpt_hash)
        await self.db.commit()
