import pytest
from src.services.user_service import UserService
from src.services.email_verification import EmailVerification
from src.models.user import User
from unittest.mock import AsyncMock, MagicMock, patch
from src.schemas.user import CreateUser, UserLogin
from sqlalchemy.exc import IntegrityError
from src.exceptions import UserAlreadyExistsError, UserNotFoundError
from uuid import uuid4


class TestUserService:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_register_success(self, db_session):
        service = UserService(db_session)
        mock_user = User(
            id="test-uuid",
            email="new@test.com",
            username="newuser",
            hashed_password="hashed_pass"
        )
        service.repo.create = AsyncMock(return_value=mock_user)
        user_data = CreateUser(
            email="new@test.com",
            username="newuser",
            password="StrongPass123!"
        )
        result = await service.register(user_data)
        assert result is not None
        assert result == mock_user


    @pytest.mark.asyncio(loop_scope="session")
    async def test_duplicate_email(self, db_session):
        service = UserService(db_session)
        service.db.commit = AsyncMock(side_effect=IntegrityError("dup", {}, None))

        mock_user = User(
            id="test-uuid",
            email="new@test.com",
            username="newuser",
            hashed_password="hashed_pass"
        )
        service.repo.get_by_email_or_username = AsyncMock(return_value=mock_user)
        user_data = CreateUser(
            email="new@test.com",
            username="newuser",
            password="StrongPass123!"
        )
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            await service.register(user_data)
        
        assert "email" in str(exc_info.value)


    @pytest.mark.asyncio(loop_scope="session")
    async def test_wrong_password_login(self, db_session):
        service = UserService(db_session)
        user_mock = User(
            id="test-uuid",
            email="user@email.ru",
            username="newuser",
            hashed_password="hashed_pass"
        )
        service.repo.get_by_email = AsyncMock(return_value=user_mock)
        user = UserLogin(
            email="user@email.ru",
            password="StrongPassword1213!"
        )
        with patch("src.services.user_service.verify_password", return_value=False):
            with pytest.raises(UserNotFoundError):
                await service.login(user)


    @pytest.mark.asyncio(loop_scope="session")
    async def test_verify_email(self, db_session):
        service = UserService(db_session)
        test_uuid = str(uuid4())
        service.email_verification.verify_email_register = AsyncMock(return_value=test_uuid)
        test_user = User(
            id=test_uuid,
            email="user@email.ru",
            username="newuser",
            hashed_password="hashed_pass"
        )
        service.repo.get_by_id = AsyncMock(return_value=test_user)
        service.session_repo.create = AsyncMock()
        result = await service.verify_email("token")
        assert result is not None
        assert result["user"] == test_user

class TestEmailVerification:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_send_email_register(self, mock_redis, mock_resend):
        service = EmailVerification()
        email = "ertybasevk@gmail.com"
        user_id = uuid4()
        await service.send_email_register(email, user_id)
        mock_resend.assert_awaited_once()
        call_kwargs = mock_resend.call_args[0][0]
        assert call_kwargs["to"] == email
        assert call_kwargs["subject"] == "Email verification"
        assert call_kwargs["from"] == "onboarding@resend.dev"
        assert "confirm_url" in call_kwargs["template"]["variables"]
        
        # Проверяем, что URL содержит ожидаемый роутер
        generated_url = call_kwargs["template"]["variables"]["confirm_url"]
        assert "/auth/verify-email?token=" in generated_url

        # 2. Проверяем вызовы Redis
        # setex должен быть вызван 2 раза: один раз для токена, второй для rate-limit (300 сек)
        assert mock_redis.setex.await_count == 2
        
        # Проверяем, что rate-limit ключ был установлен правильно
        mock_redis.setex.assert_any_call(
            f"{service.rate_prefix}:{email}", 
            300, 
            "sent"
        )


class TestGoogleOauth:
    ...



    
