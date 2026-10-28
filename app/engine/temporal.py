from collections import deque


class TemporalAnalyzer:

    def __init__(
        self,
        window_size: int = 5,
        anomaly_threshold: float = 0.30,
    ):
        self.window_size = window_size
        self.anomaly_threshold = anomaly_threshold

        self.history: dict[str, deque[float]] = {}
        self.anomaly_streaks: dict[str, int] = {}

    def update(
        self,
        session_id: str,
        risk_score: float,
    ) -> tuple[float, int]:

        if session_id not in self.history:
            self.history[session_id] = deque(
                maxlen=self.window_size
            )

        if session_id not in self.anomaly_streaks:
            self.anomaly_streaks[session_id] = 0

        history = self.history[session_id]

        history.append(risk_score)

        if risk_score >= self.anomaly_threshold:
            self.anomaly_streaks[session_id] += 1
        else:
            self.anomaly_streaks[session_id] = 0

        # More recent observations receive more weight.
        weights = range(1, len(history) + 1)

        weighted_sum = sum(
            risk * weight
            for risk, weight in zip(history, weights)
        )

        total_weight = sum(weights)

        temporal_risk = weighted_sum / total_weight

        return temporal_risk, self.anomaly_streaks[session_id]

    def clear(self, session_id: str):
        self.history.pop(session_id, None)
        self.anomaly_streaks.pop(session_id, None)