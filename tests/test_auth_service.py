from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.user import UserRole
from app.schemas.auth import UserCreate, UserLogin
from app.services.auth import AuthService


def make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_auth_service_register_and_authenticate():
    db = make_session()
    service = AuthService()

    user_in = UserCreate(email="unit@example.com", password="secret123", role=UserRole.STUDENT)
    user, access, refresh = service.register_user(db, user_in)
    assert user.email == user_in.email
    assert user.hashed_password != user_in.password
    assert access and refresh

    creds = UserLogin(email=user_in.email, password=user_in.password)
    authed_user, access2, refresh2 = service.authenticate(db, creds)
    assert authed_user.id == user.id
    assert access2 and refresh2


def test_auth_service_refresh_invalid_token_raises():
    db = make_session()
    service = AuthService()
    with pytest.raises(Exception):
        service.refresh_tokens(db, "not-a-token")
