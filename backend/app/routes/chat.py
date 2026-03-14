import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse, MessageEntry, SessionResponse, SessionSummary
from app.models.graph import SessionState
from app.services.flow_graph import run_flow, run_flow_streaming
from app.services.sessions import session_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions() -> list[SessionSummary]:
    return [
        SessionSummary(session_id=sid, created_at=created_at)
        for sid, created_at in session_store.list_all()
    ]


@router.post("/sessions", response_model=SessionResponse)
async def create_session() -> SessionResponse:
    session_id = session_store.create()

    # Generate agent-initiated first message
    state = session_store.get_state(session_id) or SessionState()
    result = await run_flow(state, messages=[], user_message="")
    session_store.set(session_id, result["messages"])
    session_store.set_state(session_id, result["session_state"])

    return SessionResponse(session_id=session_id, first_message=result["assistant_response"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or session_store.create()

    message_history = session_store.get(session_id)
    if message_history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session_store.get_state(session_id) or SessionState()
    result = await run_flow(state, messages=message_history, user_message=request.message)

    session_store.set(session_id, result["messages"])
    session_store.set_state(session_id, result["session_state"])

    return ChatResponse(message=result["assistant_response"], session_id=session_id)


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    session_id = request.session_id or session_store.create()

    message_history = session_store.get(session_id)
    if message_history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        state = session_store.get_state(session_id) or SessionState()
        queue: asyncio.Queue = asyncio.Queue()

        task = asyncio.create_task(
            run_flow_streaming(state, message_history, request.message, queue)
        )

        # Drain events from the graph and yield as SSE
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event["type"] == "done":
                break

        try:
            result = await task
        except Exception:
            logger.exception("Flow graph error during streaming")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Internal server error'})}\n\n"
            return

        session_store.set(session_id, result["messages"])
        session_store.set_state(session_id, result["session_state"])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageEntry])
async def get_messages(session_id: str) -> list[MessageEntry]:
    message_history = session_store.get(session_id)
    if message_history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    entries: list[MessageEntry] = []
    for msg in message_history:
        if msg.kind == "request":
            for part in msg.parts:
                if part.part_kind == "user-prompt" and isinstance(part.content, str):
                    entries.append(MessageEntry(role="user", content=part.content))
        elif msg.kind == "response":
            for part in msg.parts:
                if part.part_kind == "text":
                    entries.append(MessageEntry(role="assistant", content=part.content))
    return entries
