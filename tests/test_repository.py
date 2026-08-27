import pytest
from src.repositories.user_repository import UserRepository
from src.repositories.session_repository import SessionRepository
from src.schemas.user import CreateUser
from src.core.security import hash_password
from datetime import datetime, timezone


class TestUserRepository:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_create_user(self, create_user):
        user = await create_user()
        assert user.id is not None
        assert user.created_at is not None

    
    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_by_email(self, create_user, db_session):
        repo = UserRepository(db_session)
        user = await create_user()
        user = await repo.get_by_email(user.email)
        assert user is not None



class TestSessionRepository:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_by_token(self, db_session, create_user):
        repo = SessionRepository(db_session)
        user = await create_user()
        await repo.create(user.id, "refresh_token", datetime.now(timezone.utc))
        await db_session.commit()
        session = await repo.get_by_token("refresh_token")
        assert session.user_id == user.id

