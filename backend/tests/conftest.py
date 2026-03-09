import pytest
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel

from app.main import app
from app.models.scores import RingScores
from app.services.agent import agent
from app.services.scoring_agent import scoring_agent
from app.services.sessions import session_store


@pytest.fixture(autouse=True)
def _clear_sessions():
    session_store._sessions.clear()
    session_store._scores.clear()
    yield
    session_store._sessions.clear()
    session_store._scores.clear()


@pytest.fixture(autouse=True)
def _mock_agent():
    with agent.override(model=TestModel(custom_output_text="Test response")):
        yield


@pytest.fixture(autouse=True)
def _mock_scoring_agent():
    with scoring_agent.override(model=TestModel(custom_output_args=RingScores().model_dump())):
        yield


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
