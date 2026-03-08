from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    session_id: str


class SessionResponse(BaseModel):
    session_id: str


class MessageEntry(BaseModel):
    role: str
    content: str
