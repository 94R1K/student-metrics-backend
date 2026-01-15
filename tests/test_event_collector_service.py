import pytest

from app.schemas.events import EventIn
from app.services.event_collector import EventCollectorService


class FailingRepo:
    async def insert_batch(self, events):
        raise RuntimeError("db down")


class MemoryRepo:
    def __init__(self):
        self.saved = []

    async def insert_batch(self, events):
        self.saved.extend(events)


@pytest.mark.anyio
async def test_event_collector_success():
    repo = MemoryRepo()
    service = EventCollectorService(repository=repo)
    event = EventIn(
        user_id="7f7b2b28-0d85-4701-a6c1-0d2a4b5b3e18",
        course_id="c8f6d0f7-3868-41a8-9c1b-bd93fa2c0bcb",
        module_id="2d2f8c71-4a3d-4b1e-8cf8-474c84e0a940",
        event_type="page_view",
        timestamp="2024-01-01T00:00:00Z",
        payload={"path": "/"},
    )
    count = await service.ingest_events([event])
    assert count == 1
    assert len(repo.saved) == 1


@pytest.mark.anyio
async def test_event_collector_failure_raises():
    service = EventCollectorService(repository=FailingRepo())
    event = EventIn(
        user_id="7f7b2b28-0d85-4701-a6c1-0d2a4b5b3e18",
        course_id="c8f6d0f7-3868-41a8-9c1b-bd93fa2c0bcb",
        module_id="2d2f8c71-4a3d-4b1e-8cf8-474c84e0a940",
        event_type="page_view",
        timestamp="2024-01-01T00:00:00Z",
        payload={"path": "/"},
    )
    with pytest.raises(Exception):
        await service.ingest_events([event])
