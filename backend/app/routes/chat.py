from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse, MessageEntry, SessionResponse
from app.services.agent import agent
from app.services.sessions import session_store

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

    result = await agent.run(request.message, message_history=message_history)

    # Save updated history
    session_store.set(session_id, result.all_messages())

    return ChatResponse(message=result.output, session_id=session_id)


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
