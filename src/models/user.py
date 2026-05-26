from src.core.db import Base
from sqlalchemy import Column, String, DateTime, Boolean, UUID, func



class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)
    hashed_password = Column(String, nullable=False)
