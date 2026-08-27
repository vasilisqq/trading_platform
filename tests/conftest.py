import os
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from unittest.mock import AsyncMock, patch, MagicMock
import respx
from httpx import Response
from alembic.config import Config
from alembic import command
from src.schemas.user import CreateUser
from src.core.security import hash_password
from src.repositories.user_repository import UserRepository


# ВАЖНО: устанавливаем .env.test ДО импорта модулей проекта
os.environ["ENV_FILE"] = ".env.test"

from src.core.config import settings
from src.core.db import Base, get_db
from src.core.dependencies import get_google_oauth
from src.services.google_oauth import GoogleOAuthService

# Создаём тестовый engine (не используем глобальный из src.core.db)
TEST_DATABASE_URL = settings.DATABASE_URL.get_secret_value()
test_engine = create_async_engine(TEST_DATABASE_URL, future=True)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

# Импортируем app ПОСЛЕ создания engine
from src.main import app


# ═══════════════════════════════════════════════════════
# ФИКСТУРА 1: Миграции Alembic
# ═══════════════════════════════════════════════════════
@pytest_asyncio.fixture(loop_scope="session", autouse=True)
async def setup_database():
    """
    Выполняет Alembic миграции в тестовую БД.
    Гарантирует, что схема БД точно совпадает с продакшеном.
    """
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")

    # Очищаем таблицы перед тестами
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE users CASCADE"))

    yield


# ═══════════════════════════════════════════════════════
# ФИКСТУРА 3: Сессия БД с откатом транзакции
# ═══════════════════════════════════════════════════════
@pytest_asyncio.fixture
async def db_session():
    """
    Создаёт сессию БД внутри транзакции соединения.

    Ключевой момент: используем engine.connect() + begin() +
    AsyncSession с join_transaction_mode="create_savepoint".

    Это позволяет endpoint'ам делать commit(), но на самом деле
    коммитится только SAVEPOINT. После теста внешняя транзакция
    откатывается — данные не сохраняются в БД.
    """
    async with test_engine.connect() as connection:
        # Начинаем внешнюю транзакцию
        trans = await connection.begin()

        # Создаём сессию, привязанную к соединению
        # join_transaction_mode="create_savepoint" означает, что
        # commit() внутри сессии создаст SAVEPOINT, а не закоммитит
        # внешнюю транзакцию
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )

        yield session

        await session.close()
        await trans.rollback()


# ═══════════════════════════════════════════════════════
# ФИКСТУРА 4: HTTP клиент для тестов API
# ═══════════════════════════════════════════════════════
@pytest_asyncio.fixture
async def client(db_session):
    """
    Создаёт HTTP клиент, который отправляет запросы
    напрямую в FastAPI приложение (без реального сервера).

    Подменяет зависимость get_db, чтобы endpoint'ы
    использовали тестовую сессию (с откатом).
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════
# ФИКСТУРА 5: Мок Redis
# ═══════════════════════════════════════════════════════
@pytest.fixture
def mock_redis():
    """
    Мокает Redis. Все вызовы get_redis() внутри теста
    будут возвращать фейковый Redis вместо реального.

    Нужен для:
    - TokenBlackListService (чёрный список токенов)
    - EmailVerification (хранение токенов подтверждения)
    - GoogleOAuth (хранение oauth state)
    """
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.setex = AsyncMock(return_value=True)
    fake_redis.delete = AsyncMock(return_value=True)
    fake_redis.ttl = AsyncMock(return_value=-1)

    with patch("src.core.redis.get_redis", return_value=fake_redis):
        with patch("src.core.redis.redis_client", fake_redis):
            yield fake_redis


# ═══════════════════════════════════════════════════════
# ФИКСТУРА 6: Мок отправки email (Resend)
# ═══════════════════════════════════════════════════════
@pytest.fixture
def mock_resend():
    """
    Мокает отправку email. Реальные письма не отправляются.
    Проверяем, что метод вызвался через mock.assert_called().
    """
    with patch(
        "src.services.email_verification.resend.Emails.send_async",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = {"id": "test-email-id"}
        yield mock


# ═══════════════════════════════════════════════════════
# ФИКСТУРА 7: Мок Google OAuth (для endpoint /auth/google)
# ═══════════════════════════════════════════════════════
@pytest_asyncio.fixture(loop_scope="session")
async def mock_google_oauth():
    """
    Мокает GoogleOAuthService для endpoint /auth/google.
    Этот endpoint использует Depends(get_google_oauth).
    """
    mock = AsyncMock(spec=GoogleOAuthService)
    mock.get_auth_url.return_value = "https://accounts.google.com/fake-auth"

    original = app.dependency_overrides.get(get_google_oauth)
    app.dependency_overrides[get_google_oauth] = lambda: mock

    yield mock

    if original:
        app.dependency_overrides[get_google_oauth] = original
    else:
        app.dependency_overrides.pop(get_google_oauth, None)


# ═══════════════════════════════════════════════════════
# ФИКСТУРА 8: Мок HTTP запросов к Google API
# ═══════════════════════════════════════════════════════
@pytest.fixture
def mock_google_http():
    """
    Мокает HTTP запросы к Google (httpx).
    Используется в GoogleOAuthService.exchange_code()
    и get_user_info() при callback.
    """
    with respx.mock:
        # Мокаем обмен кода на токен
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=Response(
                200, json={"access_token": "fake-google-token", "token_type": "Bearer"}
            )
        )

        # Мокаем получение данных пользователя
        respx.get("https://www.googleapis.com/oauth2/v3/userinfo").mock(
            return_value=Response(
                200,
                json={
                    "sub": "123456789",
                    "email": "google@test.com",
                    "name": "Google User",
                },
            )
        )

        yield

@pytest_asyncio.fixture
async def create_user(db_session):
    async def _make(**overrides):
        data = {
            "email": "test@mail.ru", 
            "username":"test_user", 
            "password":"StronGPassword123!"
        }
        data.update(overrides) 
        user_data = CreateUser(**data)
        hashed_password = hash_password(user_data.password)
        repo = UserRepository(db_session)
        user = await repo.create(user_data, hashed_password)
        await db_session.commit()
        return user
    return _make

@pytest_asyncio.fixture
async def verify_user(create_user, db_session):
    user = await create_user()
    user.email_verified = True
    await db_session.commit()
    return user
