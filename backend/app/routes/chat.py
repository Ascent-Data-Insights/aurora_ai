import asyncio
import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.chat import ChatRequest, ChatResponse, DocumentInfo, MessageEntry, SessionResponse, SessionSummary
from app.models.graph import SessionState
from app.rate_limit import limiter
from app.services.document_parser import parse_document
from app.services.flow_graph import run_flow, run_flow_streaming
from app.services import sessions
from app.services.sessions import UploadedDocument, _document_store, build_document_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[SessionSummary]:
    return [
        SessionSummary(session_id=sid, created_at=created_at)
        for sid, created_at in await sessions.list_all(db)
    ]


@router.post("/sessions", response_model=SessionResponse)
@limiter.limit("5/minute")
async def create_session(request: Request, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    session_id = await sessions.create(db)

    # Generate agent-initiated first message
    state = await sessions.get_state(db, session_id) or SessionState()
    result = await run_flow(state, messages=[], user_message="")
    await sessions.set(db, session_id, result["messages"])
    await sessions.set_state(db, session_id, result["session_state"])

    return SessionResponse(session_id=session_id, first_message=result["assistant_response"])


@router.post("/upload", response_model=list[DocumentInfo])
async def upload_documents(
    session_id: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentInfo]:
    """Upload Word, PowerPoint, or Excel files to a session."""
    if await sessions.get(db, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")

    results: list[DocumentInfo] = []
    for file in files:
        content = await file.read()
        filename = file.filename or "unknown"
        try:
            text = parse_document(filename, content)
            doc = UploadedDocument(filename=filename, text=text)
            _document_store.setdefault(session_id, []).append(doc)
            results.append(DocumentInfo(filename=filename, size=len(content), ok=True))
        except ValueError as e:
            results.append(DocumentInfo(filename=filename, size=len(content), ok=False, error=str(e)))

    return results


@router.post("", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    session_id = body.session_id or await sessions.create(db)

    message_history = await sessions.get(db, session_id)
    if message_history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    state = await sessions.get_state(db, session_id) or SessionState()
    doc_context = build_document_context(session_id)
    result = await run_flow(state, messages=message_history, user_message=body.message, document_context=doc_context)

    await sessions.set(db, session_id, result["messages"])
    await sessions.set_state(db, session_id, result["session_state"])

    return ChatResponse(message=result["assistant_response"], session_id=session_id)


@router.post("/stream")
@limiter.limit("20/minute")
async def chat_stream(request: Request, body: ChatRequest, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    session_id = body.session_id or await sessions.create(db)

    message_history = await sessions.get(db, session_id)
    if message_history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        state = await sessions.get_state(db, session_id) or SessionState()
        doc_context = build_document_context(session_id)
        queue: asyncio.Queue = asyncio.Queue()

        task = asyncio.create_task(
            run_flow_streaming(state, message_history, body.message, queue, document_context=doc_context)
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

        await sessions.set(db, session_id, result["messages"])
        await sessions.set_state(db, session_id, result["session_state"])

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
