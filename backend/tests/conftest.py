import pytest
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel

from app.main import app
from app.services.agent import agent
from app.services.sessions import session_store


@pytest.fixture(autouse=True)
def _clear_sessions():
    session_store._sessions.clear()
    yield
    session_store._sessions.clear()


@pytest.fixture(autouse=True)
def _mock_agent():
    with agent.override(model=TestModel(custom_output_text="Test response")):
        yield


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
