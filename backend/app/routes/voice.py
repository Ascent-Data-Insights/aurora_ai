"""WebSocket endpoint for voice chat: text in → Claude → Cartesia TTS → audio out."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.graph import SessionState
from app.services.flow_graph import run_flow_streaming
from app.services.sessions import session_store
from app.services.tts import stream_tts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.websocket("/ws")
async def voice_chat(ws: WebSocket):
    await ws.accept()

    try:
        while True:
            # Receive a JSON message with session_id and user text
            data = json.loads(await ws.receive_text())
            message = data.get("message", "")
            session_id = data.get("session_id")

            if not session_id:
                session_id = session_store.create()

            message_history = session_store.get(session_id)
            if message_history is None:
                session_id = session_store.create()
                message_history = session_store.get(session_id)

            # Send session info
            await ws.send_text(json.dumps({"type": "session", "session_id": session_id}))

            state = session_store.get_state(session_id) or SessionState()
            queue: asyncio.Queue = asyncio.Queue()
            text_queue: asyncio.Queue[str | None] = asyncio.Queue()

            flow_task = asyncio.create_task(
                run_flow_streaming(state, message_history, message, queue)
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
                    if evt_type in ("scores", "regression", "debug", "flow_node"):
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

            result = await flow_task
            await consume_task
            await tts_task

            session_store.set(session_id, result["messages"])
            session_store.set_state(session_id, result["session_state"])

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
