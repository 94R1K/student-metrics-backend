from fastapi import APIRouter, Depends

from app.schemas.events import EventBatch, EventIngestResponse
from app.services.event_collector import EventCollectorService

router = APIRouter(prefix="/api/v1/events", tags=["events"])
collector_service = EventCollectorService()


def get_collector_service() -> EventCollectorService:
    return collector_service


@router.post("", response_model=EventIngestResponse, status_code=202)
async def ingest_events(
    batch: EventBatch,
    collector: EventCollectorService = Depends(get_collector_service),
) -> EventIngestResponse:
    accepted = await collector.ingest_events(list(batch.events))
    return EventIngestResponse(accepted=accepted)
