from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import chat, voice

app = FastAPI(title="Portfolio Strategy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(voice.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
