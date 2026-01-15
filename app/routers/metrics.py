from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.metrics import MetricsCalculationRequest, MetricsCalculationResponse
from app.services.metrics import MetricsEngine

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])
engine = MetricsEngine()


@router.post("/calculate", response_model=MetricsCalculationResponse, status_code=202)
async def calculate_metrics(
    payload: MetricsCalculationRequest,
    db: Session = Depends(get_db),
) -> MetricsCalculationResponse:
    calculated = await engine.calculate_for_course(
        db=db,
        course_id=payload.course_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        metrics=payload.metrics,
    )
    return MetricsCalculationResponse(calculated=calculated)
