"""Unit tests for score regression detection."""

from app.models.scores import DimensionScore, RingScores
from app.services.regression import detect_regression


def _scores(
    v_val: int = 0,
    v_conf: int = 0,
    f_val: int = 0,
    f_conf: int = 0,
    s_val: int = 0,
    s_conf: int = 0,
) -> RingScores:
    return RingScores(
        value=DimensionScore(value=v_val, confidence=v_conf),
        feasibility=DimensionScore(value=f_val, confidence=f_conf),
        scalability=DimensionScore(value=s_val, confidence=s_conf),
    )


def test_no_regression_when_scores_stable():
    prev = _scores(v_val=70, v_conf=40, f_val=60, f_conf=30, s_val=50, s_conf=20)
    curr = _scores(v_val=72, v_conf=42, f_val=58, f_conf=32, s_val=52, s_conf=22)
    assert detect_regression(prev, curr) is None


def test_no_regression_when_confidence_below_threshold():
    """Don't flag regressions for rings with < 10 prior confidence."""
    prev = _scores(v_val=70, v_conf=5)
    curr = _scores(v_val=30, v_conf=0)  # Big drop but prior was low
    assert detect_regression(prev, curr) is None


def test_confidence_drop_triggers_regression():
    prev = _scores(v_val=70, v_conf=50)
    curr = _scores(v_val=70, v_conf=38)  # Dropped 12 points (> 10)
    assert detect_regression(prev, curr) == "value"


def test_score_shift_triggers_regression():
    prev = _scores(f_val=70, f_conf=40)
    curr = _scores(f_val=50, f_conf=40)  # Shifted 20 points (> 15)
    assert detect_regression(prev, curr) == "feasibility"


def test_score_increase_also_triggers_regression():
    """A large upward score shift is also a regression (inconsistency)."""
    prev = _scores(s_val=30, s_conf=40)
    curr = _scores(s_val=55, s_conf=40)  # Shifted +25 points (> 15)
    assert detect_regression(prev, curr) == "scalability"


def test_returns_first_regressed_ring():
    """When multiple rings regress, returns the first (value > feasibility > scalability)."""
    prev = _scores(v_val=70, v_conf=50, f_val=60, f_conf=40)
    curr = _scores(v_val=50, v_conf=50, f_val=40, f_conf=40)
    assert detect_regression(prev, curr) == "value"


def test_confidence_drop_exactly_at_threshold():
    """Exactly 10 point drop should NOT trigger (need > 10)."""
    prev = _scores(v_val=70, v_conf=50)
    curr = _scores(v_val=70, v_conf=40)  # Dropped exactly 10
    assert detect_regression(prev, curr) is None


def test_score_shift_exactly_at_threshold():
    """Exactly 15 point shift should NOT trigger (need > 15)."""
    prev = _scores(v_val=70, v_conf=50)
    curr = _scores(v_val=55, v_conf=50)  # Shifted exactly 15
    assert detect_regression(prev, curr) is None


def test_empty_scores_no_regression():
    prev = RingScores()
    curr = RingScores()
    assert detect_regression(prev, curr) is None
