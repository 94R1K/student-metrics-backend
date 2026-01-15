from typing import Optional

from httpx import AsyncClient

from app.core.config import settings

_client: Optional[AsyncClient] = None


def get_clickhouse_client() -> AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = AsyncClient(
            base_url=settings.clickhouse_url,
            timeout=settings.clickhouse_timeout_seconds,
        )
    return _client


async def close_clickhouse_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
    _client = None
