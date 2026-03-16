"""Session and message persistence backed by PostgreSQL."""

import uuid
from datetime import datetime, timezone

from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

_message_adapter = TypeAdapter(ModelMessage)

from app.models.db import Message, Session
from app.models.graph import SessionState


class UploadedDocument:
    """Lightweight container for parsed document text."""

    def __init__(self, filename: str, text: str) -> None:
        self.filename = filename
        self.text = text


# In-memory document store (documents aren't persisted to DB yet)
_document_store: dict[str, list[UploadedDocument]] = {}


async def create(db: AsyncSession) -> str:
    session_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    db.add(Session(id=session_id, state_json={}, created_at=now, updated_at=now))
    await db.commit()
    return session_id


async def list_all(db: AsyncSession) -> list[tuple[str, datetime]]:
    result = await db.execute(select(Session).order_by(Session.created_at))
    return [(s.id, s.created_at) for s in result.scalars()]


async def get(db: AsyncSession, session_id: str) -> list[ModelMessage] | None:
    session = await db.get(Session, session_id)
    if session is None:
        return None
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.ordinal)
    )
    rows = result.scalars().all()
    return [_message_adapter.validate_python(row.message_json) for row in rows]


async def set(db: AsyncSession, session_id: str, messages: list[ModelMessage]) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(delete(Message).where(Message.session_id == session_id))
    for i, msg in enumerate(messages):
        db.add(Message(
            session_id=session_id,
            message_json=_message_adapter.dump_python(msg, mode="json"),
            ordinal=i,
            created_at=now,
        ))
    session = await db.get(Session, session_id)
    if session:
        session.updated_at = now
    await db.commit()


async def get_state(db: AsyncSession, session_id: str) -> SessionState | None:
    session = await db.get(Session, session_id)
    if session is None:
        return None
    if not session.state_json:
        return SessionState()
    return SessionState.model_validate(session.state_json)


async def set_state(db: AsyncSession, session_id: str, state: SessionState) -> None:
    session = await db.get(Session, session_id)
    if session:
        session.state_json = state.model_dump()
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()


def build_document_context(session_id: str) -> str:
    """Build a context string from all uploaded documents in a session."""
    docs = _document_store.get(session_id, [])
    if not docs:
        return ""

    parts = []
    for doc in docs:
        parts.append(f"--- Document: {doc.filename} ---\n{doc.text}")
    return (
        "The user has uploaded the following documents for context. "
        "Use this information to inform your responses.\n\n"
        + "\n\n".join(parts)
    )
