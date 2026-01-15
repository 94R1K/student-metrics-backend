import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SqlEnum, Float, String, UniqueConstraint

from app.models.base import Base


class MetricName(str, Enum):
    RETENTION = "retention"
    ENGAGEMENT = "engagement_score"
    COMPLETION = "completion_rate"
    TIME_ON_TASK = "time_on_task"
    ACTIVITY_INDEX = "activity_index"
    FOCUS_RATIO = "focus_ratio"


class MetricResult(Base):
    __tablename__ = "metric_results"
    __table_args__ = (
        UniqueConstraint(
            "metric_name",
            "user_id",
            "course_id",
            "module_id",
            "period_start",
            "period_end",
            name="uq_metric_scope",
        ),
    )

    id: str = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_name: MetricName = Column(
        SqlEnum(MetricName, name="metric_names", native_enum=False), nullable=False
    )
    user_id: str = Column(String, nullable=False, index=True)
    course_id: str = Column(String, nullable=False, index=True)
    module_id: Optional[str] = Column(String, nullable=True, index=True)
    value: float = Column(Float, nullable=False)
    period_start: datetime = Column(DateTime, nullable=False)
    period_end: datetime = Column(DateTime, nullable=False)
    calculated_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
