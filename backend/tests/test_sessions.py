import pytest


@pytest.mark.anyio
async def test_create_session(client):
    resp = await client.post("/api/chat/sessions")
    assert resp.status_code == 200
    assert "session_id" in resp.json()


@pytest.mark.anyio
async def test_get_messages_empty_session(client):
    session_resp = await client.post("/api/chat/sessions")
    session_id = session_resp.json()["session_id"]

    resp = await client.get(f"/api/chat/sessions/{session_id}/messages")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_get_messages_invalid_session_returns_404(client):
    resp = await client.get("/api/chat/sessions/nonexistent/messages")
    assert resp.status_code == 404
