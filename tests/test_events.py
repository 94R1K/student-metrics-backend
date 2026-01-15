from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.routers.events import get_collector_service
from app.services.event_collector import EventCollectorService


class StubEventRepo:
    def __init__(self):
        self.saved = []

    async def insert_batch(self, events):
        self.saved.extend(events)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    repo = StubEventRepo()
    collector = EventCollectorService(repository=repo)
    app = create_app()
    app.dependency_overrides[get_collector_service] = lambda: collector
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_ingest_events_batch_returns_count(client: TestClient):
    payload = {
        "events": [
            {
                "user_id": "6e0b6e98-2b94-4e81-9be6-efb92d2e02fb",
                "course_id": "3e278dff-c8f1-4e4b-bf0a-1e058a4d9224",
                "module_id": "f5b3d663-9467-4d7d-bbaa-32bf79773f11",
                "event_type": "page_view",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"path": "/intro"},
            }
        ]
    }
    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 202
    assert response.json()["accepted"] == 1


def test_ingest_events_empty_batch_fails_validation(client: TestClient):
    response = client.post("/api/v1/events", json={"events": []})
    assert response.status_code == 422
