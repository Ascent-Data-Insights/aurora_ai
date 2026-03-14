"""Score regression detection — pure functions for comparing ring scores."""

from __future__ import annotations

from app.models.scores import RingScores

# Only flag regressions for rings where prior confidence was at least this level
_MIN_CONFIDENCE_FOR_REGRESSION = 10

# Confidence drop threshold (percentage points)
_CONFIDENCE_DROP_THRESHOLD = 10

# Score shift threshold (percentage points)
_SCORE_SHIFT_THRESHOLD = 15


def detect_regression(
    previous: RingScores,
    current: RingScores,
) -> str | None:
    """Compare previous and current scores; return the regressed ring name or None.

    A ring is flagged if:
    - The previous confidence was >= 10, AND
    - Confidence dropped by >10 points OR score shifted by >15 points

    Returns the first regressed ring found (value > feasibility > scalability),
    or None if no regression detected.
    """
    rings = [
        ("value", previous.value, current.value),
        ("feasibility", previous.feasibility, current.feasibility),
        ("scalability", previous.scalability, current.scalability),
    ]

    for ring_name, prev, curr in rings:
        if prev.confidence < _MIN_CONFIDENCE_FOR_REGRESSION:
            continue

        confidence_dropped = prev.confidence - curr.confidence > _CONFIDENCE_DROP_THRESHOLD
        score_shifted = abs(prev.value - curr.value) > _SCORE_SHIFT_THRESHOLD

        if confidence_dropped or score_shifted:
            return ring_name

    return None
