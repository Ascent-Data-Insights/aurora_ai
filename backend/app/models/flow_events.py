"""Event types emitted by flow graph nodes for streaming consumers."""

from __future__ import annotations

from typing import Any

from langgraph.types import RunnableConfig


def emit(config: RunnableConfig, event: dict[str, Any]) -> None:
    """Push an event onto the queue in config, if one exists (no-op otherwise)."""
    queue = config.get("configurable", {}).get("event_queue")
    if queue is not None:
        queue.put_nowait(event)


def node_start(node: str) -> dict[str, str]:
    return {"type": "flow_node", "node": node, "status": "active"}


def node_done(node: str) -> dict[str, str]:
    return {"type": "flow_node", "node": node, "status": "done"}


def text_delta(content: str) -> dict[str, str]:
    return {"type": "delta", "content": content}


def message_start() -> dict[str, str]:
    return {"type": "message_start"}


def scores_event(scores_dict: dict[str, Any]) -> dict[str, Any]:
    return {"type": "scores", **scores_dict}


def regression_event(ring: str) -> dict[str, str]:
    return {"type": "regression", "ring": ring}


def debug_event(phase: str, guidance: str, state: dict[str, Any]) -> dict[str, Any]:
    return {"type": "debug", "phase": phase, "guidance": guidance, "state": state}


def done_event() -> dict[str, str]:
    return {"type": "done"}
