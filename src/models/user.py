from src.core.db import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, UUID

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False)
    hashed_password = Column(String, nullable=False)
