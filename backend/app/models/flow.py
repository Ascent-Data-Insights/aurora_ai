"""FlowState — the LangGraph graph state for conversation flow."""

from __future__ import annotations

from typing import TypedDict

from pydantic_ai.messages import ModelMessage

from app.models.graph import SessionState
from app.models.scores import RingScores
from app.services.phase import Phase


class FlowState(TypedDict):
    session_state: SessionState
    messages: list[ModelMessage]
    current_phase: Phase
    previous_scores: RingScores
    user_message: str  # "" for first-message
    assistant_response: str
    regression_ring: str | None
    revisit_count: int
    document_context: str
