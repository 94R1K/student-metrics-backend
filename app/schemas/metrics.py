from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.metric import MetricName


class MetricResultOut(BaseModel):
    metric_name: MetricName
    user_id: str
    course_id: str
    module_id: Optional[str] = None
    value: float
    period_start: datetime
    period_end: datetime
    calculated_at: datetime

    class Config:
        orm_mode = True


class MetricsCalculationRequest(BaseModel):
    course_id: str
    period_start: datetime
    period_end: datetime
    metrics: Optional[list[MetricName]] = None


class MetricsCalculationResponse(BaseModel):
    calculated: list[MetricName]


class MetricAggregateOut(BaseModel):
    metric_name: MetricName
    course_id: str
    period_start: datetime
    period_end: datetime
    average_value: float
