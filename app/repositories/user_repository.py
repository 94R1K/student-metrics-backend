from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserRepository:
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get(self, db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def create(self, db: Session, email: str, hashed_password: str, role: UserRole) -> User:
        user = User(email=email, hashed_password=hashed_password, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
