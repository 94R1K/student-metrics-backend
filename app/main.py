from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.clickhouse import close_clickhouse_client
from app.core.database import SessionLocal, engine
from app.core.tasks import start_refresh_token_cleanup
import app.models  # noqa: F401
from app.models.base import Base
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.routers import auth as auth_router
from app.routers import events as events_router
from app.routers import metrics as metrics_router
from app.routers import analytics as analytics_router

_refresh_repo = RefreshTokenRepository()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_refresh_token_cleanup(
        session_factory=SessionLocal,
        repo=_refresh_repo,
        interval_seconds=settings.refresh_cleanup_interval_seconds,
    )
    try:
        yield
    finally:
        await close_clickhouse_client()


def create_app() -> FastAPI:
    application = FastAPI(title="Student Metrics API", lifespan=lifespan)
    application.include_router(auth_router.router)
    application.include_router(events_router.router)
    application.include_router(metrics_router.router)
    application.include_router(analytics_router.router)
    return application


app = create_app()
