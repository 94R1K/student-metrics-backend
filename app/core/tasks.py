import logging
import threading
import time
from typing import Optional

from sqlalchemy.orm import sessionmaker

from app.repositories.refresh_token_repository import RefreshTokenRepository

logger = logging.getLogger(__name__)
_cleanup_thread: Optional[threading.Thread] = None
_lock = threading.Lock()


def start_refresh_token_cleanup(
    session_factory: sessionmaker, repo: RefreshTokenRepository, interval_seconds: int
) -> Optional[threading.Thread]:
    """Запускает фоновый поток очистки истёкших refresh-токенов (idempotent)."""
    global _cleanup_thread

    if interval_seconds <= 0:
        return None

    with _lock:
        if _cleanup_thread and _cleanup_thread.is_alive():
            return _cleanup_thread

        def _worker():
            while True:
                try:
                    with session_factory() as db:
                        repo.purge_expired(db)
                except Exception as exc:  # pragma: no cover - логирующий guard
                    logger.warning("Failed to purge expired refresh tokens: %s", exc)
                time.sleep(interval_seconds)

        _cleanup_thread = threading.Thread(target=_worker, name="refresh-token-cleanup", daemon=True)
        _cleanup_thread.start()
        return _cleanup_thread
