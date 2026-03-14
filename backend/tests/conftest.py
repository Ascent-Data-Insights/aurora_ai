import pytest
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.db import get_db
from app.main import app
from app.models.db import Message, Session  # noqa: F401
from app.models.graph import SessionState
from app.services import chat_agent as chat_agent_module
from app.services.extractor_agent import extractor_agent

# In-memory SQLite for tests
_test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    async with _test_session_factory() as session:
        yield session


async def _init_tables():
    async with _test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def _drop_tables():
    async with _test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


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
    app.dependency_overrides[get_db] = _override_get_db
    await _init_tables()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
    await _drop_tables()


@pytest.fixture
async def db():
    await _init_tables()
    async with _test_session_factory() as session:
        yield session
    await _drop_tables()
