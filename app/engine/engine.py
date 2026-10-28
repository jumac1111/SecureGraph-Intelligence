from app.config import AssuranceConfig

from app.engine.behavioral_signals import (
    BehavioralSignalsEngine,
)

from app.engine.behavior_verifier import (
    BehavioralVerifier,
)

from app.engine.fusion import (
    RiskFusionEngine,
)

from app.engine.identity_signals import (
    IdentitySignalsEngine,
)

from app.engine.policy import (
    PolicyEngine,
)

from app.models.decision import (
    AssuranceDecision,
)

from app.models.profile import (
    UserProfile,
)

from app.models.signals import (
    BehaviorObservation,
    IdentityEvidence,
    SignalResult,
)

from app.providers.context import (
    ContextProvider,
)

from app.providers.face import (
    FaceProvider,
)


class ContinuousAssuranceEngine:
    """
    Coordinates behavioral, identity, face, and context
    signal generation, verification, signal fusion,
    and policy evaluation.

    Architecture:

        observation + identity evidence
                    |
                    v
          signal generation
                    |
                    v
              verification
                    |
                    v
                  signals
                    |
                    v
                 fusion
                    |
                    v
             assurance result
                    |
                    v
                 policy
                    |
                    v
             policy decision
    """

    def __init__(
        self,
        assurance_config: AssuranceConfig | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:

        assurance_config = (
            assurance_config
            or AssuranceConfig()
        )

        # ==================================================
        # BEHAVIORAL SIGNALS
        # ==================================================

        self.behavioral_signals_engine = (
            BehavioralSignalsEngine()
        )

        # ==================================================
        # BEHAVIORAL VERIFIER
        # ==================================================

        self.behavior_verifier = (
            BehavioralVerifier()
        )

        # ==================================================
        # IDENTITY SIGNALS
        # ==================================================

        self.identity_signals_engine = (
            IdentitySignalsEngine()
        )

        # ==================================================
        # OTHER PROVIDERS
        # ==================================================

        self.face_provider = (
            FaceProvider()
        )

        self.context_provider = (
            ContextProvider()
        )

        # ==================================================
        # FUSION
        # ==================================================

        self.fusion_engine = (
            RiskFusionEngine(
                behavior_weight=(
                    assurance_config.behavior_weight
                ),
                identity_weight=(
                    assurance_config.identity_weight
                ),
                face_weight=(
                    assurance_config.face_weight
                ),
                context_weight=(
                    assurance_config.context_weight
                ),
            )
        )

        # ==================================================
        # POLICY
        # ==================================================

        self.policy_engine = (
            policy_engine
            or PolicyEngine()
        )

    def evaluate(
        self,
        profile: UserProfile,
        observation: BehaviorObservation,
        identity_evidence: IdentityEvidence | None = None,
        face_signal: SignalResult | None = None,
        context_signal: SignalResult | None = None,
    ) -> AssuranceDecision:
        """
        Evaluate the current assurance state.

        Behavioral evidence is verified against the learned
        behavioral profile.

        Identity evidence is independently converted into an
        identity assurance signal.

        Identity is deliberately not inferred from the claimed
        user ID. The identity signal must come from explicit
        verification evidence.
        """

        # ==================================================
        # 1. BEHAVIORAL SIGNAL PREPARATION
        # ==================================================

        observation = (
            self.behavioral_signals_engine.build_observation(
                typing_speed=observation.typing_speed,
                typing_interval_variance=(
                    observation.typing_interval_variance
                ),
                mouse_speed=observation.mouse_speed,
                click_interval=observation.click_interval,
                navigation_interval=(
                    observation.navigation_interval
                ),
            )
        )

        # ==================================================
        # 2. BEHAVIOR VERIFICATION
        # ==================================================

        behavior_signal = (
            self.behavior_verifier.verify_signal(
                profile,
                observation,
            )
        )

        # ==================================================
        # 3. IDENTITY
        # ==================================================

        if identity_evidence is None:
            identity_signal = (
                self.identity_signals_engine.evaluate(
                    IdentityEvidence()
                )
            )

        else:
            identity_signal = (
                self.identity_signals_engine.evaluate(
                    identity_evidence
                )
            )

        # ==================================================
        # 4. FACE
        # ==================================================

        if face_signal is None:

            face_signal = (
                self.face_provider.generate()
            )

        # ==================================================
        # 5. CONTEXT
        # ==================================================

        if context_signal is None:

            context_signal = (
                self.context_provider.generate()
            )

        # ==================================================
        # 6. FUSION
        # ==================================================

        assurance = (
            self.fusion_engine.fuse(
                behavior=behavior_signal,
                identity=identity_signal,
                face=face_signal,
                context=context_signal,
            )
        )

        # ==================================================
        # 7. POLICY
        # ==================================================

        return (
            self.policy_engine.evaluate(
                assurance
            )
        )