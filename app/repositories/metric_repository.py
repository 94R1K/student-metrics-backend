from datetime import datetime
from typing import Iterable, List, Sequence, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.metric import MetricName, MetricResult


class MetricRepository:
    def upsert_batch(
        self,
        db: Session,
        metric_name: MetricName,
        course_id: str,
        period_start,
        period_end,
        rows: Iterable[tuple[str, float]],
    ) -> None:
        """Сохраняет результаты метрики (user_id, value) с заменой существующих."""
        for user_id, value in rows:
            existing = (
                db.query(MetricResult)
                .filter(
                    and_(
                        MetricResult.metric_name == metric_name,
                        MetricResult.course_id == course_id,
                        MetricResult.user_id == user_id,
                        MetricResult.period_start == period_start,
                        MetricResult.period_end == period_end,
                    )
                )
                .first()
            )
            if existing:
                existing.value = value
                existing.calculated_at = datetime.utcnow()
            else:
                db.add(
                    MetricResult(
                        metric_name=metric_name,
                        user_id=user_id,
                        course_id=course_id,
                        value=value,
                        period_start=period_start,
                        period_end=period_end,
                    )
                )
        db.commit()

    def get_user_metrics(
        self,
        db: Session,
        user_id: str,
        course_id: str,
        period_start: datetime,
        period_end: datetime,
        metrics: Sequence[MetricName] | None = None,
    ) -> List[MetricResult]:
        query = db.query(MetricResult).filter(
            MetricResult.user_id == user_id,
            MetricResult.course_id == course_id,
            MetricResult.period_start == period_start,
            MetricResult.period_end == period_end,
        )
        if metrics:
            query = query.filter(MetricResult.metric_name.in_(metrics))
        return query.order_by(MetricResult.metric_name).all()

    def get_course_aggregates(
        self,
        db: Session,
        course_id: str,
        period_start: datetime,
        period_end: datetime,
        metrics: Sequence[MetricName] | None = None,
    ) -> List[Tuple[MetricName, float]]:
        query = (
            db.query(
                MetricResult.metric_name,
                func.avg(MetricResult.value).label("average_value"),
            )
            .filter(
                MetricResult.course_id == course_id,
                MetricResult.period_start == period_start,
                MetricResult.period_end == period_end,
            )
            .group_by(MetricResult.metric_name)
        )
        if metrics:
            query = query.filter(MetricResult.metric_name.in_(metrics))
        return [(row.metric_name, float(row.average_value)) for row in query.all()]
