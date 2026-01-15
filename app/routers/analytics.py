from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.metric import MetricName
from app.schemas.metrics import MetricAggregateOut, MetricResultOut
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/api/v1", tags=["analytics"])
analytics_service = AnalyticsService()
authorize_teacher_admin = require_roles({"teacher", "admin"})


@router.get("/metrics/user/{user_id}", response_model=list[MetricResultOut])
def get_user_metrics(
    user_id: str,
    course_id: str,
    period_start: datetime,
    period_end: datetime,
    metrics: Optional[list[MetricName]] = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(authorize_teacher_admin),
) -> list[MetricResultOut]:
    results = analytics_service.get_user_metrics(
        db=db,
        user_id=user_id,
        course_id=course_id,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
    )
    return results


@router.get("/analytics/course/{course_id}", response_model=list[MetricAggregateOut])
def get_course_analytics(
    course_id: str,
    period_start: datetime,
    period_end: datetime,
    metrics: Optional[list[MetricName]] = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(authorize_teacher_admin),
) -> list[MetricAggregateOut]:
    aggregates = analytics_service.get_course_aggregates(
        db=db,
        course_id=course_id,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
    )
    return [
        MetricAggregateOut(
            metric_name=metric_name,
            course_id=course_id,
            period_start=period_start,
            period_end=period_end,
            average_value=value,
        )
        for metric_name, value in aggregates
    ]
