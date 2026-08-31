from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
import hashlib
from src.models.session import Session
from sqlalchemy import select, delete


class SessionRepository:
    def __init__(self, db:AsyncSession):
        self.db = db

    def _hash_token(self, refresh_token:str) -> str:
        return hashlib.sha256(refresh_token.encode()).hexdigest()
        

    async def create(self, user_id:UUID, refresh_token:str, expires_at: datetime) -> None:
        token_hash = self._hash_token(refresh_token)
        session = Session(
            user_id=user_id,
            refresh_token_hash=token_hash,
            expires_at=expires_at
        )
        self.db.add(session)


    async def get_by_token(self, refresh_token:str) -> Session | None:
        token_hash = self._hash_token(refresh_token)
        result = await self.db.execute(
            select(Session).where(Session.refresh_token_hash == token_hash)
        )
        return result.scalar_one_or_none()
    
    async def delete(self, session:Session) -> None:
        await self.db.delete(session)

    async def delete_by_hash(self, refresh_token:str) -> None:
        token_hash = self._hash_token(refresh_token)
        await self.db.execute(
            delete(Session).where(Session.refresh_token_hash == token_hash)
        )