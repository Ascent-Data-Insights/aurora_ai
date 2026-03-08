import pytest


@pytest.mark.anyio
async def test_chat_auto_creates_session(client):
    resp = await client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Test response"
    assert "session_id" in data


@pytest.mark.anyio
async def test_chat_with_explicit_session(client):
    # Create session first
    session_resp = await client.post("/api/chat/sessions")
    session_id = session_resp.json()["session_id"]

    resp = await client.post(
        "/api/chat", json={"message": "hello", "session_id": session_id}
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id


@pytest.mark.anyio
async def test_chat_invalid_session_returns_404(client):
    resp = await client.post(
        "/api/chat", json={"message": "hello", "session_id": "nonexistent"}
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_chat_missing_message_returns_422(client):
    resp = await client.post("/api/chat", json={})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_conversation_continuity(client):
    # First message
    resp1 = await client.post("/api/chat", json={"message": "first"})
    session_id = resp1.json()["session_id"]

    # Second message in same session
    resp2 = await client.post(
        "/api/chat", json={"message": "second", "session_id": session_id}
    )
    assert resp2.status_code == 200

    # History should have both exchanges
    history = await client.get(f"/api/chat/sessions/{session_id}/messages")
    messages = history.json()
    assert len(messages) == 4  # 2 user + 2 assistant
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "first"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "second"
    assert messages[3]["role"] == "assistant"
