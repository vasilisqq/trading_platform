from src.core.db import Base
from sqlalchemy import Column, String, DateTime, Boolean, UUID, func, true, false
from datetime import datetime
from sqlalchemy.orm import relationship, Mapped, mapped_column


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=false())

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
