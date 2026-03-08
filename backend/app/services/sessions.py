import uuid

from pydantic_ai.messages import ModelMessage


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, list[ModelMessage]] = {}

    def create(self) -> str:
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = []
        return session_id

    def get(self, session_id: str) -> list[ModelMessage] | None:
        return self._sessions.get(session_id)

    def set(self, session_id: str, messages: list[ModelMessage]) -> None:
        self._sessions[session_id] = messages


session_store = SessionStore()
