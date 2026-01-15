from datetime import datetime, timedelta, timezone
from typing import Generator, List

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
import app.core.database as db_module
from app.core.database import get_db
from app.main import create_app
from app.models.base import Base
from app.models.metric import MetricName, MetricResult
from app.repositories.metric_repository import MetricRepository
from app.routers import metrics as metrics_router
from app.routers import analytics as analytics_router
from app.routers.events import get_collector_service
from app.schemas.events import EventIn
from app.services.event_collector import EventCollectorService
from app.services.analytics import AnalyticsService
from app.services.metrics import MetricsEngine


class MemoryEventRepo:
    def __init__(self, store: List[EventIn]):
        self.store = store

    async def insert_batch(self, events):
        self.store.extend(events)


class StubClickHouseRepo:
    def __init__(self, store: List[EventIn]):
        self.store = store

    async def fetch_metric(self, metric: MetricName, start, end, course_id: str):
        counts = {}
        for ev in self.store:
            if str(ev.course_id) != course_id:
                continue
            user_id = str(ev.user_id)
            counts[user_id] = counts.get(user_id, 0) + 1
        return [(u, float(v)) for u, v in counts.items()]


class MemoryMetricRepo:
    def __init__(self):
        self.rows = []

    def upsert_batch(self, db, metric_name, course_id, period_start, period_end, rows):
        for user_id, value in rows:
            existing = next(
                (
                    r
                    for r in self.rows
                    if r["metric_name"] == metric_name
                    and r["course_id"] == course_id
                    and r["user_id"] == user_id
                    and r["period_start"] == period_start
                    and r["period_end"] == period_end
                ),
                None,
            )
            if existing:
                existing["value"] = value
            else:
                self.rows.append(
                    {
                        "metric_name": metric_name,
                        "user_id": user_id,
                        "course_id": course_id,
                        "period_start": period_start,
                        "period_end": period_end,
                        "value": value,
                    }
                )

    def get_user_metrics(self, db, user_id, course_id, period_start, period_end, metrics=None):
        filtered = [
            r
            for r in self.rows
            if r["user_id"] == user_id
            and r["course_id"] == course_id
            and r["period_start"] == period_start
            and r["period_end"] == period_end
            and (not metrics or r["metric_name"] in metrics)
        ]
        return [MetricResult(**r) for r in filtered]

    def get_course_aggregates(self, db, course_id, period_start, period_end, metrics=None):
        filtered = [
            r
            for r in self.rows
            if r["course_id"] == course_id
            and r["period_start"] == period_start
            and r["period_end"] == period_end
            and (not metrics or r["metric_name"] in metrics)
        ]
        agg = {}
        for r in filtered:
            agg.setdefault(r["metric_name"], []).append(r["value"])
        return [(name, sum(vals) / len(vals)) for name, vals in agg.items()]


@pytest.fixture
def app_with_overrides() -> Generator:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_module.engine = engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db_module.SessionLocal = SessionLocal

    events_store: List[EventIn] = []
    collector = EventCollectorService(repository=MemoryEventRepo(events_store))

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_collector_service] = lambda: collector
    app.dependency_overrides[get_db] = override_get_db
    app.state.events_store = events_store  # type: ignore[attr-defined]

    # Monkeypatch metrics engine to use stub CH and shared in-memory metric repo
    original_engine = metrics_router.engine
    metric_repo = MemoryMetricRepo()
    metrics_router.engine = MetricsEngine(
        ch_repo=StubClickHouseRepo(events_store),
        metric_repo=metric_repo,
    )
    analytics_router.analytics_service = AnalyticsService(metric_repo=metric_repo)
    app.state.metric_repo = metric_repo  # type: ignore[attr-defined]

    try:
        yield app
    finally:
        metrics_router.engine = original_engine
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_full_flow_auth_events_metrics_analytics(app_with_overrides):
    app = app_with_overrides
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register admin and obtain token
        reg_resp = await client.post(
            "/auth/register",
            json={"email": "admin@test.com", "password": "secret123", "role": "admin"},
        )
        assert reg_resp.status_code == 201
        tokens = reg_resp.json()
        access_token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        # user was created in auth flow

        # Ingest events
        now = datetime.now(timezone.utc)
        events_payload = {
            "events": [
                {
                    "user_id": "6e0b6e98-2b94-4e81-9be6-efb92d2e02fb",
                    "course_id": "3e278dff-c8f1-4e4b-bf0a-1e058a4d9224",
                    "module_id": "f5b3d663-9467-4d7d-bbaa-32bf79773f11",
                    "event_type": "page_view",
                    "timestamp": (now - timedelta(days=1)).isoformat(),
                    "payload": {"path": "/intro"},
                },
                {
                    "user_id": "6e0b6e98-2b94-4e81-9be6-efb92d2e02fb",
                    "course_id": "3e278dff-c8f1-4e4b-bf0a-1e058a4d9224",
                    "module_id": "f5b3d663-9467-4d7d-bbaa-32bf79773f11",
                    "event_type": "task_start",
                    "timestamp": now.isoformat(),
                    "payload": {"task": "t1"},
                },
                {
                    "user_id": "1b3612e7-e9ce-4aa9-8eb5-87b3df7bd036",
                    "course_id": "3e278dff-c8f1-4e4b-bf0a-1e058a4d9224",
                    "module_id": "f5b3d663-9467-4d7d-bbaa-32bf79773f11",
                    "event_type": "page_view",
                    "timestamp": now.isoformat(),
                    "payload": {"path": "/intro"},
                },
            ]
        }
        ing_resp = await client.post("/api/v1/events", json=events_payload)
        assert ing_resp.status_code == 202
        assert len(app.state.events_store) == 3  # type: ignore[attr-defined]

        # Calculate metrics (stub CH uses ingested events)
        start = (now - timedelta(days=7)).isoformat()
        end = (now + timedelta(seconds=1)).isoformat()
        calc_resp = await client.post(
            "/api/v1/metrics/calculate",
            json={
                "course_id": "3e278dff-c8f1-4e4b-bf0a-1e058a4d9224",
                "period_start": start,
                "period_end": end,
            },
        )
        assert calc_resp.status_code == 202
        assert MetricName.RETENTION.value in calc_resp.json()["calculated"]
        # Data persisted in in-memory metric repo?
        assert len(app.state.metric_repo.rows) > 0  # type: ignore[attr-defined]

        # Fetch course analytics (requires admin role)
        analytics_resp = await client.get(
            "/api/v1/analytics/course/3e278dff-c8f1-4e4b-bf0a-1e058a4d9224",
            params={"period_start": start, "period_end": end},
            headers=headers,
        )
        assert analytics_resp.status_code == 200
        aggregates = {item["metric_name"]: item["average_value"] for item in analytics_resp.json()}
        # With stub: user1 has 2 events, user2 has 1 event -> average 1.5
        assert aggregates[MetricName.RETENTION.value] == pytest.approx(1.5)
