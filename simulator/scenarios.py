from app.engine.engine import ContinuousAssuranceEngine
from app.models.session import SessionContext
from app.models.signals import SignalStatus

from app.providers.face import FaceProvider
from app.providers.behavior import BehaviorProvider
from app.providers.context import ContextProvider


def run_scenario(
    name: str,
    engine: ContinuousAssuranceEngine,
    session: SessionContext,
    face_score: float,
    behavior_score: float,
    context_score: float,
    face_status=SignalStatus.CONSISTENT,
    behavior_status=SignalStatus.CONSISTENT,
    context_status=SignalStatus.CONSISTENT,
):

    face = FaceProvider().generate(
        score=face_score,
        status=face_status,
    )

    behavior = BehaviorProvider().generate(
        score=behavior_score,
        status=behavior_status,
    )

    context = ContextProvider().generate(
        score=context_score,
        status=context_status,
    )

    result = engine.assess(
        session=session,
        signals=[
            face,
            behavior,
            context,
        ],
    )

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    print(f"Risk:          {result.risk_score}")
    print(f"Assurance:     {result.assurance_score}")
    print(f"Risk level:    {result.risk_level}")
    print(f"Decision:      {result.decision}")
    print(f"Anomaly streak:{result.anomaly_streak}")

    print("Reasons:")

    for reason in result.reason_codes:
        print(f"  - {reason}")


def main():

    engine = ContinuousAssuranceEngine()

    session = SessionContext(
        session_id="session-001",
        user_id="user-001",
        application_id="demo-web-app",
    )

    # Scenario 1
    run_scenario(
        "LEGITIMATE USER",
        engine,
        session,
        face_score=0.95,
        behavior_score=0.90,
        context_score=0.95,
    )

    # Scenario 2
    run_scenario(
        "BEHAVIORAL ANOMALY",
        engine,
        session,
        face_score=0.95,
        behavior_score=0.25,
        context_score=0.95,
    )

    # Scenario 3
    run_scenario(
        "STRONG IDENTITY MISMATCH",
        engine,
        session,
        face_score=0.10,
        behavior_score=0.10,
        context_score=0.80,
        face_status=SignalStatus.MISMATCH,
        behavior_status=SignalStatus.MISMATCH,
    )

    # Persistent anomaly
    print("\n")
    print("=" * 60)
    print("PERSISTENT ANOMALY TEST")
    print("=" * 60)

    for i in range(5):

        result = engine.assess(
            session=session,
            signals=[
                FaceProvider().generate(
                    score=0.10,
                    status=SignalStatus.MISMATCH,
                ),
                BehaviorProvider().generate(
                    score=0.15,
                    status=SignalStatus.MISMATCH,
                ),
                ContextProvider().generate(
                    score=0.80,
                ),
            ],
        )

        print(
            f"Observation {i + 1}: "
            f"risk={result.risk_score:.3f}, "
            f"decision={result.decision}, "
            f"streak={result.anomaly_streak}"
        )


if __name__ == "__main__":
    main()