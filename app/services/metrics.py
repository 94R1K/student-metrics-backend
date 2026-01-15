from datetime import datetime
from typing import Iterable, List

from sqlalchemy.orm import Session

from app.models.metric import MetricName
from app.repositories.metric_ch_repository import ClickHouseMetricRepository
from app.repositories.metric_repository import MetricRepository


class MetricsEngine:
    """Расчёт метрик на основе событий в ClickHouse с сохранением в PostgreSQL."""

    def __init__(
        self,
        ch_repo: ClickHouseMetricRepository | None = None,
        metric_repo: MetricRepository | None = None,
    ):
        self.ch_repo = ch_repo or ClickHouseMetricRepository()
        self.metric_repo = metric_repo or MetricRepository()

    async def calculate_for_course(
        self,
        db: Session,
        course_id: str,
        period_start: datetime,
        period_end: datetime,
        metrics: Iterable[MetricName] | None = None,
    ) -> List[MetricName]:
        metrics_to_calc = list(metrics or [
            MetricName.RETENTION,
            MetricName.ENGAGEMENT,
            MetricName.COMPLETION,
            MetricName.TIME_ON_TASK,
            MetricName.ACTIVITY_INDEX,
            MetricName.FOCUS_RATIO,
        ])

        for metric in metrics_to_calc:
            rows = await self.ch_repo.fetch_metric(metric, period_start, period_end, course_id)
            self.metric_repo.upsert_batch(
                db=db,
                metric_name=metric,
                course_id=course_id,
                period_start=period_start,
                period_end=period_end,
                rows=rows,
            )
        return metrics_to_calc
