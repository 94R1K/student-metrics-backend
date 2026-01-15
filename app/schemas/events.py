import uuid
from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field, UUID4, conlist, constr


class EventIn(BaseModel):
    """Входящее событие с детерминированной схемой."""

    id: UUID4 = Field(default_factory=uuid.uuid4)
    user_id: UUID4
    course_id: UUID4
    module_id: UUID4
    event_type: constr(min_length=1, strip_whitespace=True)  # type: ignore[var-annotated]
    timestamp: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"


class EventBatch(BaseModel):
    events: conlist(EventIn, min_items=1)  # type: ignore[var-annotated]

    class Config:
        extra = "forbid"


class EventIngestResponse(BaseModel):
    accepted: int
