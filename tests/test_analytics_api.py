from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.main import create_app
from app.models.base import Base
from app.models.metric import MetricName, MetricResult
from app.routers.analytics import authorize_teacher_admin
from app.core.database import get_db


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    db = make_session()
    app = create_app()
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[authorize_teacher_admin] = lambda: {"role": "admin"}
    app.state._test_db = db  # type: ignore[attr-defined]
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    db.close()


def seed_metrics(db: Session, start: datetime, end: datetime):
    entries = [
        MetricResult(
            metric_name=MetricName.RETENTION,
            user_id="user-1",
            course_id="course-1",
            value=0.8,
            period_start=start,
            period_end=end,
        ),
        MetricResult(
            metric_name=MetricName.RETENTION,
            user_id="user-2",
            course_id="course-1",
            value=0.6,
            period_start=start,
            period_end=end,
        ),
        MetricResult(
            metric_name=MetricName.ENGAGEMENT,
            user_id="user-1",
            course_id="course-1",
            value=10.0,
            period_start=start,
            period_end=end,
        ),
    ]
    db.add_all(entries)
    db.commit()


def test_get_user_metrics_returns_filtered_results(client: TestClient):
    db_override: Session = client.app.state._test_db  # type: ignore[attr-defined]
    start = datetime.now(timezone.utc) - timedelta(days=7)
    end = datetime.now(timezone.utc)
    seed_metrics(db_override, start, end)

    resp = client.get(
        "/api/v1/metrics/user/user-1",
        params={
            "course_id": "course-1",
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    metric_names = {item["metric_name"] for item in data}
    assert metric_names == {MetricName.RETENTION.value, MetricName.ENGAGEMENT.value}


def test_get_course_analytics_returns_aggregates(client: TestClient):
    db_override: Session = client.app.state._test_db  # type: ignore[attr-defined]
    start = datetime.now(timezone.utc) - timedelta(days=7)
    end = datetime.now(timezone.utc)
    seed_metrics(db_override, start, end)

    resp = client.get(
        "/api/v1/analytics/course/course-1",
        params={
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    agg_map = {item["metric_name"]: item["average_value"] for item in data}
    assert agg_map[MetricName.RETENTION.value] == pytest.approx((0.8 + 0.6) / 2)
