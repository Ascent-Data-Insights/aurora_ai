"""Integration tests for the LangGraph conversation flow."""

import pytest
from pydantic_ai.models.test import TestModel

from app.models.graph import SessionState
from app.models.scores import DimensionScore, RingScores
from app.services import chat_agent as chat_agent_module
from app.services.extractor_agent import extractor_agent
from app.services.flow_graph import run_flow


@pytest.fixture(autouse=True)
def _mock_models():
    """Mock both chat and extractor models for flow tests."""
    original_chat = chat_agent_module.chat_model
    chat_agent_module.chat_model = TestModel(custom_output_text="Flow test response")

    with extractor_agent.override(
        model=TestModel(custom_output_args=SessionState().model_dump())
    ):
        yield

    chat_agent_module.chat_model = original_chat


@pytest.mark.anyio
async def test_basic_flow():
    """A normal turn runs through route → chat → extract → detect_regression."""
    state = SessionState()
    result = await run_flow(state, messages=[], user_message="Hello")

    assert result["assistant_response"] == "Flow test response"
    assert result["regression_ring"] is None
    assert len(result["messages"]) > 0


@pytest.mark.anyio
async def test_first_message_flow():
    """Empty messages + empty user_message triggers first-message mode."""
    state = SessionState()
    result = await run_flow(state, messages=[], user_message="")

    assert result["assistant_response"] == "Flow test response"
    # Synthetic prompt should be stripped from messages
    for msg in result["messages"]:
        if msg.kind == "request":
            for part in msg.parts:
                if part.part_kind == "user-prompt" and isinstance(part.content, str):
                    assert part.content != "Begin the conversation."


@pytest.mark.anyio
async def test_regression_triggers_revisit():
    """When extractor produces a score regression, the graph loops back to chat."""
    # Start with existing scores
    initial_state = SessionState(
        scores=RingScores(
            value=DimensionScore(value=70, confidence=50),
            feasibility=DimensionScore(value=60, confidence=40),
            scalability=DimensionScore(value=50, confidence=30),
        )
    )

    # Extractor will return scores with a big drop in value
    regressed_state = SessionState(
        scores=RingScores(
            value=DimensionScore(value=40, confidence=50),  # -30 shift
            feasibility=DimensionScore(value=60, confidence=40),
            scalability=DimensionScore(value=50, confidence=30),
        )
    )

    original_chat = chat_agent_module.chat_model
    chat_agent_module.chat_model = TestModel(custom_output_text="Revisit response")

    with extractor_agent.override(
        model=TestModel(custom_output_args=regressed_state.model_dump())
    ):
        result = await run_flow(initial_state, messages=[], user_message="Some info")

    chat_agent_module.chat_model = original_chat

    # The graph loops once: first extract detects regression (initial→regressed),
    # second extract sees no change (regressed→regressed), so it stops at 1.
    assert result["revisit_count"] == 1


@pytest.mark.anyio
async def test_no_regression_no_revisit():
    """Stable scores don't trigger any revisits."""
    stable_state = SessionState(
        scores=RingScores(
            value=DimensionScore(value=70, confidence=50),
        )
    )

    with extractor_agent.override(
        model=TestModel(custom_output_args=stable_state.model_dump())
    ):
        result = await run_flow(stable_state, messages=[], user_message="Hello")

    assert result["revisit_count"] == 0
    assert result["regression_ring"] is None
