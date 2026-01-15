from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _sqlite_connect_args(url: str) -> dict:
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


engine = create_engine(
    settings.database_url,
    future=True,
    echo=False,
    connect_args=_sqlite_connect_args(settings.database_url),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
