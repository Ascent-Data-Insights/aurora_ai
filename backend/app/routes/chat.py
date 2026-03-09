import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse, MessageEntry, SessionResponse
from app.models.scores import RingScores
from app.services.chat_agent import chat_agent
from app.services.scoring_agent import scoring_agent
from app.services.sessions import session_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions", response_model=SessionResponse)
async def create_session() -> SessionResponse:
    session_id = session_store.create()
    return SessionResponse(session_id=session_id)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # Auto-create session if none provided
    session_id = request.session_id or session_store.create()

    message_history = session_store.get(session_id)
    if message_history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await chat_agent.run(request.message, message_history=message_history)

    # Save updated history
    session_store.set(session_id, result.all_messages())

    return ChatResponse(message=result.output, session_id=session_id)


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    session_id = request.session_id or session_store.create()

    message_history = session_store.get(session_id)
    if message_history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        # Send session_id as the first event
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        assistant_response = ""
        async with chat_agent.run_stream(
            request.message, message_history=message_history
        ) as stream:
            async for chunk in stream.stream_text(delta=True):
                assistant_response += chunk
                yield f"data: {json.dumps({'type': 'delta', 'content': chunk})}\n\n"

            # Save history after stream completes
            session_store.set(session_id, stream.all_messages())

        # Run scoring agent after chat completes
        try:
            current_scores = session_store.get_scores(session_id) or RingScores()
            scoring_input = (
                f"Current scores:\n{current_scores.model_dump_json()}\n\n"
                f"Latest user message:\n{request.message}\n\n"
                f"Latest assistant response:\n{assistant_response}"
            )
            result = await scoring_agent.run(scoring_input)
            session_store.set_scores(session_id, result.output)
            yield f"data: {json.dumps({'type': 'scores', **result.output.model_dump()})}\n\n"
        except Exception:
            logger.exception("Scoring agent failed")

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
