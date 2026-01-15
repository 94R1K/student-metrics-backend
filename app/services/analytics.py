from datetime import datetime
from typing import Iterable, List, Tuple

from sqlalchemy.orm import Session

from app.models.metric import MetricName, MetricResult
from app.repositories.metric_repository import MetricRepository


class AnalyticsService:
    """Возвращает агрегированные метрики без пересчёта."""

    def __init__(self, metric_repo: MetricRepository | None = None):
        self.metric_repo = metric_repo or MetricRepository()

    def get_user_metrics(
        self,
        db: Session,
        user_id: str,
        course_id: str,
        period_start: datetime,
        period_end: datetime,
        metrics: Iterable[MetricName] | None = None,
    ) -> List[MetricResult]:
        return self.metric_repo.get_user_metrics(
            db=db,
            user_id=user_id,
            course_id=course_id,
            period_start=period_start,
            period_end=period_end,
            metrics=list(metrics) if metrics else None,
        )

    def get_course_aggregates(
        self,
        db: Session,
        course_id: str,
        period_start: datetime,
        period_end: datetime,
        metrics: Iterable[MetricName] | None = None,
    ) -> List[Tuple[MetricName, float]]:
        return self.metric_repo.get_course_aggregates(
            db=db,
            course_id=course_id,
            period_start=period_start,
            period_end=period_end,
            metrics=list(metrics) if metrics else None,
        )
