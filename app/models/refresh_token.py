from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String

from app.models.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    jti: str = Column(String, primary_key=True)
    user_id: str = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    revoked: bool = Column(Boolean, default=False, nullable=False)
    expires_at: datetime = Column(DateTime, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
