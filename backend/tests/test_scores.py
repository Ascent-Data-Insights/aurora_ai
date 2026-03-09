import pytest
from pydantic import ValidationError

from app.models.scores import DimensionScore, RingScores


def test_dimension_score_defaults():
    score = DimensionScore()
    assert score.value == 0
    assert score.confidence == 0


def test_dimension_score_valid_range():
    score = DimensionScore(value=80, confidence=60)
    assert score.value == 80
    assert score.confidence == 60


def test_dimension_score_rejects_out_of_range():
    with pytest.raises(ValidationError):
        DimensionScore(value=101, confidence=50)
    with pytest.raises(ValidationError):
        DimensionScore(value=50, confidence=-1)


def test_ring_scores_defaults():
    scores = RingScores()
    for dim in [scores.value, scores.feasibility, scores.scalability]:
        assert dim.value == 0
        assert dim.confidence == 0


def test_ring_scores_serialization():
    scores = RingScores(
        value=DimensionScore(value=70, confidence=40),
        feasibility=DimensionScore(value=50, confidence=25),
        scalability=DimensionScore(value=0, confidence=0),
    )
    data = scores.model_dump()
    assert data["value"]["value"] == 70
    assert data["feasibility"]["confidence"] == 25
    assert data["scalability"]["value"] == 0
