import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.chat import ChatRequest, ChatResponse, MessageEntry, SessionResponse, SessionSummary
from app.models.graph import SessionState
from app.services.chat_agent import build_chat_agent
from app.services.extractor_agent import extractor_agent
from app.services.phase import get_phase_guidance
from app.services import sessions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[SessionSummary]:
    return [
        SessionSummary(session_id=sid, created_at=created_at)
        for sid, created_at in await sessions.list_all(db)
    ]


@router.post("/sessions", response_model=SessionResponse)
async def create_session(db: AsyncSession = Depends(get_db)) -> SessionResponse:
    session_id = await sessions.create(db)
    return SessionResponse(session_id=session_id)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    session_id = request.session_id or await sessions.create(db)

    message_history = await sessions.get(db, session_id)
    if message_history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build phase-aware chat agent
    state = await sessions.get_state(db, session_id) or SessionState()
    _phase, guidance = get_phase_guidance(state)
    agent = build_chat_agent(guidance)

    result = await agent.run(
        request.message,
        message_history=message_history,
        model_settings={"anthropic_cache_instructions": True},
    )
    await sessions.set(db, session_id, result.all_messages())

    return ChatResponse(message=result.output, session_id=session_id)


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    session_id = request.session_id or await sessions.create(db)

    message_history = await sessions.get(db, session_id)
    if message_history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        # Build phase-aware chat agent
        state = await sessions.get_state(db, session_id) or SessionState()
        phase, guidance = get_phase_guidance(state)
        agent = build_chat_agent(guidance)

        # Emit debug info: phase + state before this turn
        yield f"data: {json.dumps({'type': 'debug', 'phase': phase.value, 'guidance': guidance, 'state': state.model_dump()})}\n\n"

        assistant_response = ""
        async with agent.run_stream(
            request.message,
            message_history=message_history,
            model_settings={"anthropic_cache_instructions": True},
        ) as stream:
            async for chunk in stream.stream_text(delta=True):
                assistant_response += chunk
                yield f"data: {json.dumps({'type': 'delta', 'content': chunk})}\n\n"

            await sessions.set(db, session_id, stream.all_messages())

        # Run extractor agent after chat completes
        try:
            extractor_input = (
                f"Current state:\n{state.model_dump_json(indent=2)}\n\n"
                f"Current phase: {phase.value}\n\n"
                f"Latest user message:\n{request.message}\n\n"
                f"Latest assistant response:\n{assistant_response}"
            )
            result = await extractor_agent.run(
                extractor_input,
                model_settings={"anthropic_cache_instructions": True},
            )
            new_state = result.output
            await sessions.set_state(db, session_id, new_state)

            # Emit scores for the frontend (same shape as before)
            yield f"data: {json.dumps({'type': 'scores', **new_state.scores.model_dump()})}\n\n"

            # Emit updated debug info after extraction
            new_phase, new_guidance = get_phase_guidance(new_state)
            yield f"data: {json.dumps({'type': 'debug', 'phase': new_phase.value, 'guidance': new_guidance, 'state': new_state.model_dump()})}\n\n"
        except Exception:
            logger.exception("Extractor agent failed")

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageEntry])
async def get_messages(session_id: str, db: AsyncSession = Depends(get_db)) -> list[MessageEntry]:
    message_history = await sessions.get(db, session_id)
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
