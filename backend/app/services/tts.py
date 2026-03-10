"""Cartesia TTS service for streaming text-to-speech over WebSocket."""

import asyncio
import logging
from collections.abc import AsyncIterator

from cartesia import AsyncCartesia

from app.config import settings

logger = logging.getLogger(__name__)

VOICE_ID = "e07c00bc-4134-4eae-9ea4-1a55fb45746b"
MODEL_ID = "sonic-3"
OUTPUT_FORMAT = {
    "container": "raw",
    "encoding": "pcm_s16le",
    "sample_rate": 24000,
}

# How many words to buffer before the first TTS send (for natural phrasing)
INITIAL_BUFFER_WORDS = 10


async def stream_tts(text_chunks: AsyncIterator[str]) -> AsyncIterator[bytes]:
    """Stream text chunks through Cartesia and yield audio bytes.

    Pushes text to Cartesia as it arrives from the LLM, while concurrently
    yielding audio bytes as Cartesia generates them.
    """
    client = AsyncCartesia(api_key=settings.cartesia_api_key)

    try:
        async with client.tts.websocket_connect() as ws:
            ctx = ws.context(
                model_id=MODEL_ID,
                voice={"mode": "id", "id": VOICE_ID},
                output_format=OUTPUT_FORMAT,
                language="en",
            )

            async def push_text():
                """Buffer initial words, then stream remaining text to Cartesia."""
                buffer = ""
                word_count = 0
                started = False

                async for chunk in text_chunks:
                    buffer += chunk
                    word_count += len(chunk.split())

                    if not started and word_count >= INITIAL_BUFFER_WORDS:
                        await ctx.push(buffer)
                        buffer = ""
                        started = True
                    elif started and buffer:
                        await ctx.push(buffer)
                        buffer = ""

                # Flush remaining buffer
                if buffer:
                    await ctx.push(buffer)

                await ctx.no_more_inputs()

            # Run text pushing concurrently with audio receiving
            push_task = asyncio.create_task(push_text())

            try:
                async for response in ctx.receive():
                    if response.type == "chunk" and response.audio:
                        yield response.audio
            finally:
                await push_task
    finally:
        await client.close()
