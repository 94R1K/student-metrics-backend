from fastapi import HTTPException, status

from app.repositories.event_repository import EventRepository
from app.schemas.events import EventIn


class EventCollectorService:
    def __init__(self, repository: EventRepository | None = None):
        self.repository = repository or EventRepository()

    async def ingest_events(self, events: list[EventIn]) -> int:
        try:
            await self.repository.insert_batch(events)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to ingest events",
            ) from exc
        return len(events)
