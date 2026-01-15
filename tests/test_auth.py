from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import create_app
from app.models.base import Base
from app.models.user import UserRole
import app.models  # noqa: F401


TEST_DATABASE_URL = "sqlite://"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def test_register_returns_tokens_and_user(client: TestClient):
    payload = {"email": "student@example.com", "password": "secret123", "role": UserRole.STUDENT.value}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == payload["email"]
    assert body["user"]["role"] == payload["role"]
    assert body["access_token"]
    assert body["refresh_token"]


def test_duplicate_register_is_rejected(client: TestClient):
    payload = {"email": "dup@example.com", "password": "secret123", "role": UserRole.TEACHER.value}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400
    assert second.json()["detail"] == "User already exists"


def test_login_returns_tokens(client: TestClient):
    payload = {"email": "login@example.com", "password": "secret123", "role": UserRole.ADMIN.value}
    client.post("/auth/register", json=payload)

    login_response = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["user"]["role"] == UserRole.ADMIN.value
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password_fails(client: TestClient):
    payload = {"email": "wrongpass@example.com", "password": "secret123", "role": UserRole.STUDENT.value}
    client.post("/auth/register", json=payload)

    response = client.post("/auth/login", json={"email": payload["email"], "password": "bad"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_refresh_returns_new_tokens(client: TestClient):
    payload = {"email": "refresh@example.com", "password": "secret123", "role": UserRole.TEACHER.value}
    register_resp = client.post("/auth/register", json=payload)
    refresh_token = register_resp.json()["refresh_token"]

    refresh_resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    refreshed = refresh_resp.json()
    assert refreshed["user"]["email"] == payload["email"]
    assert refreshed["access_token"]
    assert refreshed["refresh_token"]


def test_refresh_token_cannot_be_reused(client: TestClient):
    payload = {"email": "rotate@example.com", "password": "secret123", "role": UserRole.STUDENT.value}
    register_resp = client.post("/auth/register", json=payload)
    first_refresh = register_resp.json()["refresh_token"]

    first_rotation = client.post("/auth/refresh", json={"refresh_token": first_refresh})
    assert first_rotation.status_code == 200
    second_refresh = first_rotation.json()["refresh_token"]

    reuse_attempt = client.post("/auth/refresh", json={"refresh_token": first_refresh})
    assert reuse_attempt.status_code == 401
    assert reuse_attempt.json()["detail"] == "Invalid refresh token"

    # new refresh should still work
    second_rotation = client.post("/auth/refresh", json={"refresh_token": second_refresh})
    assert second_rotation.status_code == 200
