from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import AuthResponse, RefreshRequest, UserCreate, UserLogin
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()
TOKEN_TYPE = "bearer"


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> AuthResponse:
    user, access, refresh = auth_service.register_user(db, user_in)
    return AuthResponse(user=user, access_token=access, refresh_token=refresh, token_type=TOKEN_TYPE)


@router.post("/login", response_model=AuthResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> AuthResponse:
    user, access, refresh = auth_service.authenticate(db, credentials)
    return AuthResponse(user=user, access_token=access, refresh_token=refresh, token_type=TOKEN_TYPE)


@router.post("/refresh", response_model=AuthResponse)
def refresh_tokens(request: RefreshRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user, access, refresh = auth_service.refresh_tokens(db, request.refresh_token)
    return AuthResponse(user=user, access_token=access, refresh_token=refresh, token_type=TOKEN_TYPE)
