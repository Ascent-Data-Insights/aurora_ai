import asyncio
import logging

import aiohttp
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings

router = APIRouter(prefix="/api/stt", tags=["stt"])
log = logging.getLogger(__name__)

DEEPGRAM_WS = "wss://api.deepgram.com/v1/listen"


@router.websocket("/ws")
async def stt_proxy(ws: WebSocket, sample_rate: int = 16000) -> None:
    """Proxy mic audio from the browser to Deepgram and relay transcripts back."""
    await ws.accept()

    if not settings.deepgram_api_key:
        await ws.send_json({"type": "error", "message": "DEEPGRAM_API_KEY not configured"})
        await ws.close()
        return

    params = {
        "model": "nova-3",
        "interim_results": "true",
        "endpointing": "300",
        "vad_events": "true",
        "encoding": "linear16",
        "sample_rate": str(sample_rate),
        "channels": "1",
    }

    session = aiohttp.ClientSession()
    try:
        dg_ws = await session.ws_connect(
            DEEPGRAM_WS,
            params=params,
            headers={"Authorization": f"Token {settings.deepgram_api_key}"},
            timeout=aiohttp.ClientWSTimeout(ws_close=10),
        )
    except Exception as e:
        log.error("Failed to connect to Deepgram: %s: %s", type(e).__name__, e)
        await session.close()
        try:
            await ws.send_json({"type": "error", "message": "Failed to connect to Deepgram"})
            await ws.close()
        except Exception:
            pass
        return

    log.info("Deepgram STT connected (sample_rate=%d)", sample_rate)

    async def forward_audio() -> None:
        """Forward audio bytes from browser → Deepgram."""
        try:
            while True:
                data = await ws.receive_bytes()
                await dg_ws.send_bytes(data)
        except (WebSocketDisconnect, Exception):
            # Browser disconnected — tell Deepgram to close gracefully
            try:
                await dg_ws.send_str('{"type": "CloseStream"}')
            except Exception:
                pass

    async def forward_transcripts() -> None:
        """Forward transcription results from Deepgram → browser."""
        try:
            async for msg in dg_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        await ws.send_text(msg.data)
                    except Exception:
                        break
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except Exception:
            pass

    try:
        audio_task = asyncio.create_task(forward_audio())
        transcript_task = asyncio.create_task(forward_transcripts())
        _done, pending = await asyncio.wait(
            [audio_task, transcript_task], return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
    finally:
        await dg_ws.close()
        await session.close()
        log.info("Deepgram STT disconnected")
