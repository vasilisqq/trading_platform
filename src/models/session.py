from src.core.db import Base
from sqlalchemy import Column, UUID, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship


class Session(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True)
    refresh_token_hash = Column(String, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),  nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="sessions")
