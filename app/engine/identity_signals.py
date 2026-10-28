from __future__ import annotations

from app.models.signals import (
    IdentityEvidence,
    SignalResult,
    SignalStatus,
)


class IdentitySignalsEngine:
    """
    Converts identity verification evidence into a normalized
    assurance signal.

    Raw identity material is deliberately outside this engine.

    The engine supports two compatible input styles:

    1. IdentityEvidence:
       evaluate(evidence)

    2. Direct verification values:
       evaluate(
           verified=True,
           confidence=1.0,
           quality=1.0,
       )
    """

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        """
        Clamp a numeric value to the supported [0.0, 1.0] range.
        """

        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )

    def evaluate(
        self,
        evidence: IdentityEvidence | None = None,
        *,
        verified: bool | None = None,
        confidence: float | None = None,
        quality: float | None = None,
    ) -> SignalResult:
        """
        Evaluate identity verification evidence.

        Missing identity evidence is represented as unavailable
        rather than negative evidence.
        """

        # ======================================================
        # 1. DIRECT VALUE API
        # ======================================================

        if (
            verified is not None
            or confidence is not None
            or quality is not None
        ):

            # --------------------------------------------------
            # No identity verification result
            # --------------------------------------------------

            if verified is None:
                return SignalResult(
                    source="identity",
                    score=0.0,
                    confidence=0.0,
                    quality=0.0,
                    status=SignalStatus.UNAVAILABLE,
                )

            # --------------------------------------------------
            # Normalize supplied values
            # --------------------------------------------------

            normalized_confidence = self._clamp(
                0.0
                if confidence is None
                else confidence
            )

            normalized_quality = self._clamp(
                0.0
                if quality is None
                else quality
            )

            # --------------------------------------------------
            # Verified identity
            # --------------------------------------------------

            if verified:
                return SignalResult(
                    source="identity",
                    score=1.0,
                    confidence=normalized_confidence,
                    quality=normalized_quality,
                    status=SignalStatus.CONSISTENT,
                )

            # --------------------------------------------------
            # Identity mismatch
            # --------------------------------------------------

            return SignalResult(
                source="identity",
                score=0.0,
                confidence=normalized_confidence,
                quality=normalized_quality,
                status=SignalStatus.MISMATCH,
            )

        # ======================================================
        # 2. NO EVIDENCE OBJECT
        # ======================================================

        if evidence is None:
            return SignalResult(
                source="identity",
                score=0.0,
                confidence=0.0,
                quality=0.0,
                status=SignalStatus.UNAVAILABLE,
            )

        # ======================================================
        # 3. UNAVAILABLE EVIDENCE
        # ======================================================

        if evidence.status == SignalStatus.UNAVAILABLE:
            return SignalResult(
                source="identity",
                score=0.0,
                confidence=0.0,
                quality=0.0,
                status=SignalStatus.UNAVAILABLE,
                timestamp=evidence.timestamp,
            )

        # ======================================================
        # 4. NORMALIZE EVIDENCE
        # ======================================================

        normalized_confidence = self._clamp(
            evidence.verification_confidence
        )

        normalized_quality = self._clamp(
            evidence.verification_quality
        )

        normalized_score = self._clamp(
            evidence.verification_score
        )

        # ======================================================
        # 5. MISSING IDENTITY REFERENCES
        # ======================================================

        if (
            evidence.claimed_user_id is None
            or evidence.authenticated_user_id is None
        ):
            return SignalResult(
                source="identity",
                score=0.0,
                confidence=normalized_confidence,
                quality=normalized_quality,
                status=SignalStatus.UNCERTAIN,
                timestamp=evidence.timestamp,
            )

        # ======================================================
        # 6. IDENTITY MISMATCH
        # ======================================================

        if (
            evidence.claimed_user_id
            != evidence.authenticated_user_id
        ):
            return SignalResult(
                source="identity",
                score=0.0,
                confidence=normalized_confidence,
                quality=normalized_quality,
                status=SignalStatus.MISMATCH,
                timestamp=evidence.timestamp,
            )

        # ======================================================
        # 7. VERIFIED IDENTITY
        # ======================================================

        return SignalResult(
            source="identity",
            score=normalized_score,
            confidence=normalized_confidence,
            quality=normalized_quality,
            status=evidence.status,
            timestamp=evidence.timestamp,
        )