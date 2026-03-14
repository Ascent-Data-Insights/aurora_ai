"""LangGraph conversation flow — graph definition and run_flow() entry point."""

from __future__ import annotations

import asyncio
import logging

from langgraph.graph import END, StateGraph
from langgraph.types import RunnableConfig

from app.models.flow import FlowState
from app.models.flow_events import (
    debug_event,
    done_event,
    emit,
    message_start,
    node_done,
    node_start,
    regression_event,
    scores_event,
    text_delta,
)
from app.models.graph import SessionState
from app.models.scores import RingScores
from app.services.chat_agent import build_chat_agent
from app.services.extractor_agent import extractor_agent
from app.services.phase import Phase, get_phase_guidance
from app.services.regression import detect_regression

logger = logging.getLogger(__name__)

MAX_REVISITS = 2

_FIRST_MESSAGE_GUIDANCE = (
    "This is the very start of the conversation. Introduce yourself warmly and "
    "briefly explain that you help evaluate initiatives across Value, Feasibility, "
    "and Scalability. Then ask a natural opening question to learn about the user's "
    "organization."
)

_REGRESSION_GUIDANCE_TEMPLATE = (
    "IMPORTANT: New information has caused a significant shift in the {ring} "
    "assessment. Before continuing, ask a focused clarifying question about "
    "{ring} to resolve the inconsistency. Be natural — don't alarm the user, "
    "just explore the area that changed."
)


def _has_queue(config: RunnableConfig) -> bool:
    return config.get("configurable", {}).get("event_queue") is not None


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def route_node(state: FlowState, config: RunnableConfig) -> dict:
    """Determine phase and guidance. Detect first-message mode."""
    emit(config, node_start("route"))

    session_state = state["session_state"]
    phase, guidance = get_phase_guidance(session_state)

    emit(config, debug_event(phase.value, guidance, session_state.model_dump()))
    emit(config, node_done("route"))
    return {"current_phase": phase}


async def chat_node(state: FlowState, config: RunnableConfig) -> dict:
    """Run the chat agent with phase-aware or regression-override guidance."""
    emit(config, node_start("chat"))

    session_state = state["session_state"]
    messages = state["messages"]
    user_message = state["user_message"]
    regression_ring = state.get("regression_ring")

    is_first_message = not messages and not user_message

    # Build guidance
    if is_first_message:
        guidance = _FIRST_MESSAGE_GUIDANCE
    elif regression_ring:
        _phase, base_guidance = get_phase_guidance(session_state)
        guidance = (
            base_guidance + "\n\n"
            + _REGRESSION_GUIDANCE_TEMPLATE.format(ring=regression_ring)
        )
    else:
        _phase, guidance = get_phase_guidance(session_state)

    agent = build_chat_agent(guidance)
    prompt = user_message if user_message else "Begin the conversation."

    if _has_queue(config):
        # Streaming mode: emit text deltas
        emit(config, message_start())
        assistant_response = ""
        async with agent.run_stream(
            prompt,
            message_history=messages,
            model_settings={"anthropic_cache_instructions": True},
        ) as stream:
            async for chunk in stream.stream_text(delta=True):
                assistant_response += chunk
                emit(config, text_delta(chunk))
            new_messages = stream.all_messages()
    else:
        # Non-streaming mode
        result = await agent.run(
            prompt,
            message_history=messages,
            model_settings={"anthropic_cache_instructions": True},
        )
        new_messages = result.all_messages()
        assistant_response = result.output

    # For first message, strip the synthetic "Begin the conversation." user prompt
    if is_first_message:
        new_messages = _strip_synthetic_prompt(new_messages)

    emit(config, node_done("chat"))
    return {
        "messages": new_messages,
        "assistant_response": assistant_response,
        "regression_ring": None,  # Clear after addressing
    }


async def extract_node(state: FlowState, config: RunnableConfig) -> dict:
    """Snapshot scores, run extractor, update state."""
    emit(config, node_start("extract"))

    session_state = state["session_state"]
    phase = state["current_phase"]
    user_message = state["user_message"]
    assistant_response = state["assistant_response"]

    previous_scores = session_state.scores.model_copy(deep=True)

    extractor_input = (
        f"Current state:\n{session_state.model_dump_json(indent=2)}\n\n"
        f"Current phase: {phase.value}\n\n"
        f"Latest user message:\n{user_message}\n\n"
        f"Latest assistant response:\n{assistant_response}"
    )
    result = await extractor_agent.run(
        extractor_input,
        model_settings={"anthropic_cache_instructions": True},
    )

    new_state = result.output
    emit(config, scores_event(new_state.scores.model_dump()))
    emit(config, node_done("extract"))

    return {
        "session_state": new_state,
        "previous_scores": previous_scores,
    }


def detect_regression_node(state: FlowState, config: RunnableConfig) -> dict:
    """Compare previous and current scores; flag regression if found."""
    emit(config, node_start("detect_regression"))

    previous_scores = state["previous_scores"]
    current_scores = state["session_state"].scores
    revisit_count = state.get("revisit_count", 0)

    if revisit_count >= MAX_REVISITS:
        emit(config, node_done("detect_regression"))
        return {"regression_ring": None}

    ring = detect_regression(previous_scores, current_scores)
    if ring:
        logger.info("Regression detected in ring=%s (revisit %d)", ring, revisit_count + 1)
        emit(config, regression_event(ring))
        emit(config, node_done("detect_regression"))
        return {"regression_ring": ring, "revisit_count": revisit_count + 1}

    emit(config, node_done("detect_regression"))
    return {"regression_ring": None}


# ---------------------------------------------------------------------------
# Edge logic
# ---------------------------------------------------------------------------

def after_regression(state: FlowState) -> str:
    """Route after regression detection: loop back to chat or end."""
    if state.get("regression_ring"):
        return "chat"
    return END


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_flow_graph() -> StateGraph:
    """Build and compile the conversation flow graph."""
    graph = StateGraph(FlowState)

    graph.add_node("route", route_node)
    graph.add_node("chat", chat_node)
    graph.add_node("extract", extract_node)
    graph.add_node("detect_regression", detect_regression_node)

    graph.set_entry_point("route")
    graph.add_edge("route", "chat")
    graph.add_edge("chat", "extract")
    graph.add_edge("extract", "detect_regression")
    graph.add_conditional_edges("detect_regression", after_regression)

    return graph.compile()


# Module-level compiled graph
flow_graph = build_flow_graph()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _initial_state(
    session_state: SessionState,
    messages: list,
    user_message: str,
) -> FlowState:
    return {
        "session_state": session_state,
        "messages": messages,
        "current_phase": Phase.CONTEXT_GATHERING,
        "previous_scores": RingScores(),
        "user_message": user_message,
        "assistant_response": "",
        "regression_ring": None,
        "revisit_count": 0,
    }


async def run_flow(
    session_state: SessionState,
    messages: list,
    user_message: str,
) -> FlowState:
    """Run the full conversation flow graph and return the final state.

    This is the non-streaming entry point used by POST /api/chat and
    session creation (first message).
    """
    result = await flow_graph.ainvoke(_initial_state(session_state, messages, user_message))
    return result


async def run_flow_streaming(
    session_state: SessionState,
    messages: list,
    user_message: str,
    event_queue: asyncio.Queue,
) -> FlowState:
    """Run the conversation flow graph, emitting events to the queue.

    This is the streaming entry point used by SSE and WebSocket endpoints.
    Nodes push flow_node, delta, scores, regression, and debug events onto
    the queue as they execute. A done event is always emitted at the end.
    """
    config: RunnableConfig = {"configurable": {"event_queue": event_queue}}
    try:
        result = await flow_graph.ainvoke(
            _initial_state(session_state, messages, user_message),
            config=config,
        )
    finally:
        await event_queue.put(done_event())
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_synthetic_prompt(messages: list) -> list:
    """Remove the synthetic 'Begin the conversation.' user prompt from history."""
    cleaned = []
    for msg in messages:
        if msg.kind == "request":
            # Filter out parts that contain the synthetic prompt
            filtered_parts = [
                part for part in msg.parts
                if not (
                    part.part_kind == "user-prompt"
                    and isinstance(part.content, str)
                    and part.content == "Begin the conversation."
                )
            ]
            if filtered_parts:
                # Reconstruct message without synthetic parts
                from pydantic_ai.messages import ModelRequest
                cleaned.append(ModelRequest(parts=filtered_parts))
        else:
            cleaned.append(msg)
    return cleaned
