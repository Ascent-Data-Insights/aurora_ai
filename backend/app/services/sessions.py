import uuid
from datetime import datetime, timezone

from pydantic_ai.messages import ModelMessage

from app.models.scores import RingScores


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, list[ModelMessage]] = {}
        self._scores: dict[str, RingScores] = {}
        self._created_at: dict[str, datetime] = {}

    def create(self) -> str:
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = []
        self._scores[session_id] = RingScores()
        self._created_at[session_id] = datetime.now(timezone.utc)
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

    def get_scores(self, session_id: str) -> RingScores | None:
        return self._scores.get(session_id)

    def set_scores(self, session_id: str, scores: RingScores) -> None:
        self._scores[session_id] = scores


session_store = SessionStore()
