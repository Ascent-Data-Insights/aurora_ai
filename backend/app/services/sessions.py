import uuid

from pydantic_ai.messages import ModelMessage

from app.models.scores import RingScores


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, list[ModelMessage]] = {}
        self._scores: dict[str, RingScores] = {}

    def create(self) -> str:
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = []
        self._scores[session_id] = RingScores()
        return session_id

    def get(self, session_id: str) -> list[ModelMessage] | None:
        return self._sessions.get(session_id)

    def set(self, session_id: str, messages: list[ModelMessage]) -> None:
        self._sessions[session_id] = messages

    def get_scores(self, session_id: str) -> RingScores | None:
        return self._scores.get(session_id)

    def set_scores(self, session_id: str, scores: RingScores) -> None:
        self._scores[session_id] = scores


session_store = SessionStore()
