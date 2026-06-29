import pytest
from src.repositories.user_repository import UserRepository
from src.repositories.session_repository import SessionRepository
from src.schemas.user import CreateUser
from src.core.security import hash_password
from datetime import datetime, timezone


class TestUserRepository:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_create_user(self, db_session):
        repo = UserRepository(db_session)
        user_data = CreateUser(
            email="test@mail.ru",
            username="test_user",
            password="StronGPassword123!"
        )
        hashed_password = hash_password(user_data.password)
        user = await repo.create(user_data, hashed_password)
        await db_session.commit()
        assert user.id is not None
        assert user.created_at is not None

    
    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_by_email(self, db_session):
        repo = UserRepository(db_session)
        user_data = CreateUser(
            email="test@mail.ru",
            username="test_user",
            password="StronGPassword123!"
        )
        hashed_password = hash_password(user_data.password)
        await repo.create(user_data, hashed_password)
        await db_session.commit()
        user = await repo.get_by_email(user_data.email)
        assert user is not None



class TestSessionRepository:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_by_token(self, db_session):
        repo = SessionRepository(db_session)
        user_repo = UserRepository(db_session)
        user_data = CreateUser(
            email="test@mail.ru",
            username="test_user",
            password="StronGPassword123!"
        )
        hashed_password = hash_password(user_data.password)
        user = await user_repo.create(user_data, hashed_password)
        await db_session.commit()
        await repo.create(user.id, "refresh_token", datetime.now(timezone.utc))
        await db_session.commit()
        session = await repo.get_by_token("refresh_token")
        assert session.user_id == user.id

