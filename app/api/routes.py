from fastapi import APIRouter

from app.engine.engine import ContinuousAssuranceEngine
from app.models.decision import AssessmentDecision
from app.models.session import SessionContext
from app.models.signals import SignalResult


router = APIRouter()

engine = ContinuousAssuranceEngine()


@router.post(
    "/assess",
    response_model=AssessmentDecision,
)
def assess_session(
    session: SessionContext,
    signals: list[SignalResult],
):

    return engine.assess(
        session=session,
        signals=signals,
    )