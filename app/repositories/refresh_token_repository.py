from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def create(self, db: Session, jti: str, user_id: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at)
        db.add(token)
        db.commit()
        db.refresh(token)
        return token

    def revoke(self, db: Session, jti: str) -> None:
        token = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if token:
            token.revoked = True
            db.add(token)
            db.commit()

    def get_active(self, db: Session, jti: str) -> Optional[RefreshToken]:
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.jti == jti,
                RefreshToken.revoked.is_(False),
            )
            .first()
        )

    def purge_expired(self, db: Session) -> int:
        """Удаляем истёкшие refresh-токены; возвращаем число удалённых записей."""
        deleted = (
            db.query(RefreshToken).filter(RefreshToken.expires_at < datetime.utcnow()).delete(synchronize_session=False)
        )
        db.commit()
        return deleted
