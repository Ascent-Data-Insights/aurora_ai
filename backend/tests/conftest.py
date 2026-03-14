import pytest
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel

from app.main import app
from app.models.graph import SessionState
from app.services import chat_agent as chat_agent_module
from app.services.extractor_agent import extractor_agent
from app.services.sessions import session_store


@pytest.fixture(autouse=True)
def _clear_sessions():
    session_store._sessions.clear()
    session_store._state.clear()
    session_store._documents.clear()
    yield
    session_store._sessions.clear()
    session_store._state.clear()
    session_store._documents.clear()


@pytest.fixture(autouse=True)
def _mock_chat_model():
    original = chat_agent_module.chat_model
    chat_agent_module.chat_model = TestModel(custom_output_text="Test response")
    yield
    chat_agent_module.chat_model = original


@pytest.fixture(autouse=True)
def _mock_extractor_agent():
    with extractor_agent.override(
        model=TestModel(custom_output_args=SessionState().model_dump())
    ):
        yield


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
