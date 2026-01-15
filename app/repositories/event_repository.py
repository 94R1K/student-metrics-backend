import json
from typing import List, Sequence

from httpx import AsyncClient, BasicAuth, HTTPStatusError

from app.core.clickhouse import get_clickhouse_client
from app.core.config import settings
from app.schemas.events import EventIn


class EventRepository:
    """Репозиторий записи событий в ClickHouse через HTTP JSONEachRow."""

    def __init__(self, client_provider=get_clickhouse_client):
        self.client_provider = client_provider

    async def insert_batch(self, events: Sequence[EventIn]) -> None:
        if not events:
            return

        client: AsyncClient = self.client_provider()
        query = (
            f"INSERT INTO {settings.clickhouse_events_table} "
            "(id, user_id, course_id, module_id, event_type, timestamp, payload) "
            "FORMAT JSONEachRow"
        )

        body = "\n".join([event.json() for event in events])
        auth = (
            BasicAuth(settings.clickhouse_user, settings.clickhouse_password)
            if settings.clickhouse_password
            else None
        )
        response = await client.post(
            "/",
            params={"query": query, "database": settings.clickhouse_database},
            content=body,
            headers={"Content-Type": "application/json"},
            auth=auth,
        )
        try:
            response.raise_for_status()
        except HTTPStatusError as exc:
            detail = exc.response.text
            raise RuntimeError(f"ClickHouse insert failed: {detail}") from exc
