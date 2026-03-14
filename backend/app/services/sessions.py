import uuid
from datetime import datetime, timezone

from pydantic_ai.messages import ModelMessage

from app.models.graph import SessionState


class UploadedDocument:
    """Lightweight container for parsed document text."""

    def __init__(self, filename: str, text: str) -> None:
        self.filename = filename
        self.text = text


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, list[ModelMessage]] = {}
        self._state: dict[str, SessionState] = {}
        self._created_at: dict[str, datetime] = {}
        self._documents: dict[str, list[UploadedDocument]] = {}

    def create(self) -> str:
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = []
        self._state[session_id] = SessionState()
        self._created_at[session_id] = datetime.now(timezone.utc)
        self._documents[session_id] = []
        return session_id

    def list_all(self) -> list[tuple[str, datetime]]:
        return [
            (sid, self._created_at[sid])
            for sid in self._sessions
        ]

    def get(self, session_id: str) -> list[ModelMessage] | None:
        return self._sessions.get(session_id)

    def set(self, session_id: str, messages: list[ModelMessage]) -> None:
        self._sessions[session_id] = messages

    def get_state(self, session_id: str) -> SessionState | None:
        return self._state.get(session_id)

    def set_state(self, session_id: str, state: SessionState) -> None:
        self._state[session_id] = state

    def add_document(self, session_id: str, doc: UploadedDocument) -> None:
        if session_id not in self._documents:
            self._documents[session_id] = []
        self._documents[session_id].append(doc)

    def get_documents(self, session_id: str) -> list[UploadedDocument]:
        return self._documents.get(session_id, [])


session_store = SessionStore()
