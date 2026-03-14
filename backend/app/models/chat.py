from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    first_message: str | None = None


class SessionSummary(BaseModel):
    session_id: str
    created_at: datetime


class MessageEntry(BaseModel):
    role: str
    content: str


class DocumentInfo(BaseModel):
    filename: str
    size: int
    ok: bool
    error: str | None = None
