"""WebSocket endpoint for voice chat: text in -> Claude -> Cartesia TTS -> audio out."""

import asyncio
import json
import logging
import time
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db import async_session_factory
from app.models.graph import SessionState
from app.services.flow_graph import run_flow_streaming
from app.services import sessions
from app.services.sessions import build_document_context
from app.services.tts import stream_tts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Simple per-IP rate limiter for WebSocket messages
_ws_timestamps: dict[str, list[float]] = defaultdict(list)
_WS_RATE_LIMIT = 20  # max messages per minute


def _ws_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    timestamps = _ws_timestamps[ip]
    # Prune old entries
    _ws_timestamps[ip] = [t for t in timestamps if now - t < 60]
    if len(_ws_timestamps[ip]) >= _WS_RATE_LIMIT:
        return True
    _ws_timestamps[ip].append(now)
    return False


@router.websocket("/ws")
async def voice_chat(ws: WebSocket):
    await ws.accept()
    client_ip = ws.client.host if ws.client else "unknown"

    try:
        while True:
            # Receive a JSON message with session_id and user text
            raw = await ws.receive_text()

            if _ws_rate_limited(client_ip):
                await ws.send_text(json.dumps({"type": "error", "message": "Rate limit exceeded"}))
                continue
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                await ws.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            if not isinstance(data, dict):
                await ws.send_text(json.dumps({"type": "error", "message": "Expected JSON object"}))
                continue

            message = str(data.get("message", ""))
            session_id = data.get("session_id")

            async with async_session_factory() as db:
                if not session_id:
                    session_id = await sessions.create(db)

                message_history = await sessions.get(db, session_id)
                if message_history is None:
                    session_id = await sessions.create(db)
                    message_history = await sessions.get(db, session_id)

                # Send session info
                await ws.send_text(json.dumps({"type": "session", "session_id": session_id}))

                state = await sessions.get_state(db, session_id) or SessionState()
                doc_context = build_document_context(session_id)
                queue: asyncio.Queue = asyncio.Queue()
                text_queue: asyncio.Queue[str | None] = asyncio.Queue()

                flow_task = asyncio.create_task(
                    run_flow_streaming(state, message_history, message, queue, document_context=doc_context)
                )

                async def consume_events():
                    """Drain events from the flow graph, forwarding to WS and TTS."""
                    while True:
                        event = await queue.get()
                        evt_type = event["type"]

                        # Fork text deltas to the TTS queue
                        if evt_type == "delta":
                            await text_queue.put(event["content"])

                        # Forward relevant events to the WebSocket client
                        if evt_type in ("delta", "scores", "regression", "debug", "flow_node"):
                            await ws.send_text(json.dumps(event))

                        if evt_type == "done":
                            await text_queue.put(None)  # Signal TTS end
                            break

                async def run_tts():
                    """Stream TTS audio chunks back to the client."""
                    async def text_chunk_iter():
                        while True:
                            chunk = await text_queue.get()
                            if chunk is None:
                                return
                            yield chunk

                    async for audio_chunk in stream_tts(text_chunk_iter()):
                        await ws.send_bytes(audio_chunk)

                consume_task = asyncio.create_task(consume_events())
                tts_task = asyncio.create_task(run_tts())

                try:
                    result = await flow_task
                    await consume_task
                    await tts_task
                except Exception:
                    consume_task.cancel()
                    tts_task.cancel()
                    logger.exception("Flow graph error in voice WebSocket")
                    await ws.send_text(json.dumps({"type": "error", "message": "Internal server error"}))
                    continue

                await sessions.set(db, session_id, result["messages"])
                await sessions.set_state(db, session_id, result["session_state"])

                # Send transcript and done
                await ws.send_text(json.dumps({
                    "type": "transcript",
                    "content": result["assistant_response"],
                }))
                await ws.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception:
        logger.exception("Voice WebSocket error")
