from datetime import datetime

from pydantic import BaseModel, EmailStr, constr

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    password: constr(min_length=6, max_length=128)  # type: ignore[var-annotated]


class UserLogin(BaseModel):
    email: EmailStr
    password: constr(min_length=1)  # type: ignore[var-annotated]


class UserOut(UserBase):
    id: str
    created_at: datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(Token):
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str
