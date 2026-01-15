from datetime import datetime
from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate, UserLogin


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository | None = None,
        refresh_repo: RefreshTokenRepository | None = None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.refresh_repo = refresh_repo or RefreshTokenRepository()

    def register_user(self, db: Session, user_in: UserCreate) -> Tuple[User, str, str]:
        existing = self.user_repo.get_by_email(db, user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists",
            )

        hashed = hash_password(user_in.password)
        user = self.user_repo.create(
            db,
            email=user_in.email,
            hashed_password=hashed,
            role=user_in.role,
        )
        access = create_access_token(user.id, user.role.value)
        refresh, jti, expires_at = create_refresh_token(user.id, user.role.value)
        self.refresh_repo.create(db, jti=jti, user_id=user.id, expires_at=expires_at)
        return user, access, refresh

    def authenticate(self, db: Session, credentials: UserLogin) -> Tuple[User, str, str]:
        user = self.user_repo.get_by_email(db, credentials.email)
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        access = create_access_token(user.id, user.role.value)
        refresh, jti, expires_at = create_refresh_token(user.id, user.role.value)
        self.refresh_repo.create(db, jti=jti, user_id=user.id, expires_at=expires_at)
        return user, access, refresh

    def refresh_tokens(self, db: Session, refresh_token: str) -> Tuple[User, str, str]:
        # Очищаем истёкшие токены перед попыткой refresh
        self.refresh_repo.purge_expired(db)

        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        jti = payload.get("jti")
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        token_record = self.refresh_repo.get_active(db, jti)
        if not token_record or token_record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user = self.user_repo.get(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        self.refresh_repo.revoke(db, jti=jti)
        access = create_access_token(user.id, user.role.value)
        refresh, new_jti, expires_at = create_refresh_token(user.id, user.role.value)
        self.refresh_repo.create(db, jti=new_jti, user_id=user.id, expires_at=expires_at)
        return user, access, refresh
