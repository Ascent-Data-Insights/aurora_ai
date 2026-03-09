import json

import pytest
from pydantic_ai.models.test import TestModel

from app.models.graph import SessionState
from app.models.scores import DimensionScore, RingScores
from app.services.extractor_agent import extractor_agent
from app.services.sessions import session_store


@pytest.mark.anyio
async def test_extractor_agent_returns_session_state():
    result = await extractor_agent.run("Evaluate this project")
    assert isinstance(result.output, SessionState)


@pytest.mark.anyio
async def test_extractor_agent_custom_output():
    custom = SessionState(
        scores=RingScores(
            value=DimensionScore(value=75, confidence=40),
            feasibility=DimensionScore(value=60, confidence=30),
            scalability=DimensionScore(value=0, confidence=5),
        )
    )
    with extractor_agent.override(
        model=TestModel(custom_output_args=custom.model_dump())
    ):
        result = await extractor_agent.run("Test input")
        assert result.output.scores.value.value == 75
        assert result.output.scores.feasibility.confidence == 30
        assert result.output.scores.scalability.confidence == 5


def test_session_store_initializes_state():
    session_id = session_store.create()
    state = session_store.get_state(session_id)
    assert state is not None
    assert state.scores.value.confidence == 0
    assert state.scores.feasibility.confidence == 0
    assert state.scores.scalability.confidence == 0


def test_session_store_updates_state():
    session_id = session_store.create()
    new_state = SessionState(
        scores=RingScores(
            value=DimensionScore(value=80, confidence=50),
            feasibility=DimensionScore(value=40, confidence=20),
            scalability=DimensionScore(value=0, confidence=0),
        )
    )
    session_store.set_state(session_id, new_state)
    stored = session_store.get_state(session_id)
    assert stored is not None
    assert stored.scores.value.value == 80
    assert stored.scores.feasibility.confidence == 20


def test_session_store_get_state_unknown_session():
    assert session_store.get_state("nonexistent") is None


@pytest.mark.anyio
async def test_stream_emits_scores_event(client):
    resp = await client.post(
        "/api/chat/stream", json={"message": "hello"}
    )
    assert resp.status_code == 200

    events = []
    for line in resp.text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    event_types = [e["type"] for e in events]
    assert "session" in event_types
    assert "scores" in event_types
    assert "done" in event_types

    # scores should come after deltas and before done
    scores_idx = event_types.index("scores")
    done_idx = event_types.index("done")
    assert scores_idx < done_idx

    # Verify scores event structure
    scores_event = events[scores_idx]
    assert "value" in scores_event
    assert "feasibility" in scores_event
    assert "scalability" in scores_event
    assert "confidence" in scores_event["value"]
    assert "value" in scores_event["value"]


@pytest.mark.anyio
async def test_state_persists_across_turns(client):
    # First turn
    resp1 = await client.post(
        "/api/chat/stream", json={"message": "first message"}
    )
    events1 = []
    for line in resp1.text.strip().split("\n"):
        if line.startswith("data: "):
            events1.append(json.loads(line[6:]))

    session_id = next(e["session_id"] for e in events1 if e["type"] == "session")

    # Verify state stored in session
    stored = session_store.get_state(session_id)
    assert stored is not None

    # Second turn — same session
    resp2 = await client.post(
        "/api/chat/stream",
        json={"message": "second message", "session_id": session_id},
    )
    events2 = []
    for line in resp2.text.strip().split("\n"):
        if line.startswith("data: "):
            events2.append(json.loads(line[6:]))

    assert any(e["type"] == "scores" for e in events2)
