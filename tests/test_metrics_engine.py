from datetime import datetime, timedelta, timezone
from typing import Generator, Iterable, List, Tuple

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.models.metric import MetricName, MetricResult
from app.repositories.metric_repository import MetricRepository
from app.services.metrics import MetricsEngine


class StubCHRepo:
    def __init__(self):
        self.calls: List[Tuple[MetricName, str]] = []

    async def fetch_metric(
        self,
        metric: MetricName,
        start: datetime,
        end: datetime,
        course_id: str,
    ) -> List[Tuple[str, float]]:
        self.calls.append((metric, course_id))
        return [("1111-2222", 0.5), ("3333-4444", 0.9)]


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.anyio
async def test_metrics_engine_stores_results(db_session: Session):
    ch_repo = StubCHRepo()
    metric_repo = MetricRepository()
    engine = MetricsEngine(ch_repo=ch_repo, metric_repo=metric_repo)

    start = datetime.now(timezone.utc) - timedelta(days=7)
    end = datetime.now(timezone.utc)
    course_id = "course-1"

    calculated = await engine.calculate_for_course(
        db=db_session,
        course_id=course_id,
        period_start=start,
        period_end=end,
        metrics=[MetricName.RETENTION, MetricName.COMPLETION],
    )

    assert set(calculated) == {MetricName.RETENTION, MetricName.COMPLETION}
    saved = db_session.query(MetricResult).all()
    assert len(saved) == 4  # 2 metrics * 2 users
    assert all(r.course_id == course_id for r in saved)
    assert ch_repo.calls[0][0] == MetricName.RETENTION
