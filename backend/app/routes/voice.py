"""WebSocket endpoint for voice chat: text in → Claude → Cartesia TTS → audio out."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.graph import SessionState
from app.services.chat_agent import build_chat_agent
from app.services.extractor_agent import extractor_agent
from app.services.phase import get_phase_guidance
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

            # Build phase-aware agent
            state = session_store.get_state(session_id) or SessionState()
            phase, guidance = get_phase_guidance(state)
            agent = build_chat_agent(guidance)

            # Queue for piping Claude text chunks to TTS
            text_queue: asyncio.Queue[str | None] = asyncio.Queue()

            async def text_chunk_iter():
                """Async iterator that drains the text queue."""
                while True:
                    chunk = await text_queue.get()
                    if chunk is None:
                        return
                    yield chunk

            async def run_llm():
                """Stream Claude's response and push text chunks to the queue."""
                assistant_response = ""
                try:
                    async with agent.run_stream(
                        message,
                        message_history=message_history,
                        model_settings={"anthropic_cache_instructions": True},
                    ) as stream:
                        async for chunk in stream.stream_text(delta=True):
                            assistant_response += chunk
                            await text_queue.put(chunk)

                        session_store.set(session_id, stream.all_messages())
                finally:
                    await text_queue.put(None)  # Signal end of text

                return assistant_response

            async def run_tts():
                """Stream TTS audio chunks back to the client."""
                async for audio_chunk in stream_tts(text_chunk_iter()):
                    await ws.send_bytes(audio_chunk)

            # Run LLM and TTS concurrently
            llm_task = asyncio.create_task(run_llm())
            tts_task = asyncio.create_task(run_tts())

            assistant_response = await llm_task
            await tts_task

            # Send text response too (for display)
            await ws.send_text(json.dumps({
                "type": "transcript",
                "content": assistant_response,
            }))

            # Run extractor (non-blocking for audio, but we await for state update)
            try:
                extractor_input = (
                    f"Current state:\n{state.model_dump_json(indent=2)}\n\n"
                    f"Current phase: {phase.value}\n\n"
                    f"Latest user message:\n{message}\n\n"
                    f"Latest assistant response:\n{assistant_response}"
                )
                result = await extractor_agent.run(
                    extractor_input,
                    model_settings={"anthropic_cache_instructions": True},
                )
                new_state = result.output
                session_store.set_state(session_id, new_state)

                await ws.send_text(json.dumps({
                    "type": "scores",
                    **new_state.scores.model_dump(),
                }))
            except Exception:
                logger.exception("Extractor agent failed")

            await ws.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception:
        logger.exception("Voice WebSocket error")
