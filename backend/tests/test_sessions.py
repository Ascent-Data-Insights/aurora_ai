import pytest


@pytest.mark.anyio
async def test_list_sessions_empty(client):
    resp = await client.get("/api/chat/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_list_sessions(client):
    # Create two sessions
    resp1 = await client.post("/api/chat/sessions")
    resp2 = await client.post("/api/chat/sessions")
    sid1 = resp1.json()["session_id"]
    sid2 = resp2.json()["session_id"]

    resp = await client.get("/api/chat/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) == 2
    returned_ids = {s["session_id"] for s in sessions}
    assert returned_ids == {sid1, sid2}
    for s in sessions:
        assert "created_at" in s


@pytest.mark.anyio
async def test_create_session(client):
    resp = await client.post("/api/chat/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "first_message" in data
    assert data["first_message"] is not None


@pytest.mark.anyio
async def test_get_messages_after_session_creation(client):
    """Session creation generates a first message, so messages should contain it."""
    session_resp = await client.post("/api/chat/sessions")
    session_id = session_resp.json()["session_id"]

    resp = await client.get(f"/api/chat/sessions/{session_id}/messages")
    assert resp.status_code == 200
    messages = resp.json()
    # First message is the agent's greeting (no user message since synthetic prompt is stripped)
    assert len(messages) >= 1
    assert messages[0]["role"] == "assistant"


@pytest.mark.anyio
async def test_get_messages_invalid_session_returns_404(client):
    resp = await client.get("/api/chat/sessions/nonexistent/messages")
    assert resp.status_code == 404
