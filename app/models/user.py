import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, String

from app.models.base import Base


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: str = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: str = Column(String, unique=True, nullable=False, index=True)
    hashed_password: str = Column(String, nullable=False)
    role: UserRole = Column(SqlEnum(UserRole, name="user_roles", native_enum=False), nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
