import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Хешируем пароль через bcrypt (passlib)."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def _create_token(data: Dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    to_encode.update({"exp": now + expires_delta, "iat": now, "type": token_type})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str, role: str) -> str:
    return _create_token(
        {"sub": subject, "role": role},
        timedelta(minutes=settings.access_token_expire_minutes),
        token_type="access",
    )


def create_refresh_token(subject: str, role: str) -> Tuple[str, str, datetime]:
    expires_delta = timedelta(minutes=settings.refresh_token_expire_minutes)
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + expires_delta
    token = jwt.encode(
        {"sub": subject, "role": role, "exp": expires_at, "iat": now, "type": "refresh", "jti": jti},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return token, jti, expires_at


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


bearer_scheme = HTTPBearer(auto_error=True)


def get_current_payload(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Dict[str, Any]:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload


def require_roles(roles: set[str]) -> Callable:
    def dependency(payload: Dict[str, Any] = Depends(get_current_payload)) -> Dict[str, Any]:
        role = payload.get("role")
        if role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        return payload

    return dependency
