from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


from config import settings


class Base(DeclarativeBase):
    """Базовый класс для всех ORM моделей"""
    pass


# Создание асинхронного движка для работы с БД
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии базы данных.

    Использование:
        async def my_route(db: AsyncSession = Depends(get_db)):
            # Работаем с базой

    Yields:
        AsyncSession: Асинхронная сессия для работы с БД
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()