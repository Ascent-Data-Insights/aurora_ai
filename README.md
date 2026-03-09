# Strategic Intelligence Platform

AI-powered enterprise strategy tooling. Encodes proven C-suite decision-making frameworks into guided agentic flows, delivering management-consulting-grade analysis at a fraction of the cost.

## Concept

Enterprise leaders rely on expensive consulting engagements for decisions that are fundamentally repeatable — portfolio prioritization, vendor selection, operational investment calls. This platform takes battle-tested frameworks, encodes them into agentic workflows, and uses voice as the primary input to eliminate adoption friction.

The platform is built around **modules**, each targeting a specific leadership decision domain:

- **Portfolio Strategy**: evaluate and rank initiatives against Value, Feasibility, and Scalability. Score each initiative across dimensions, then rack-and-stack the full portfolio.
- **Vendor Management (to be built later)**:  structured vendor evaluation built on real enterprise procurement frameworks.
- Additional modules planned (~8 total), with cross-module context sharing so outputs from one module inform others.

This repo focuses **entirely** on Portfolio Strategy.

## Architecture

```
React (web) / React Native (iOS)
        |
    FastAPI (Python)
        |
    LangGraph (orchestration + session state)
        |--- PydanticAI agents (per module)
        |--- LlamaIndex (document ingestion)
        |
    PostgreSQL + pgvector          (Azure Database for PostgreSQL)
    Azure Blob Storage             (raw files, audio recordings)
    Azure AI Foundry               (LLMs + Whisper transcription)
```

**Key design decisions:**

- **LangGraph over pure PydanticAI orchestration** — execution flow is defined explicitly in code, not decided by the LLM at inference time. Every state transition is auditable, which matters for enterprise clients asking "how did you reach this recommendation."
- **pgvector over a dedicated vector DB** — avoids operational complexity, supports transactional joins between structured data and embeddings, sufficient at this scale.

## Project Structure

```
frontend/   React web app (React Native iOS in later phase)
backend/    FastAPI + agentic stack (LangGraph, PydanticAI, LlamaIndex)
infra/      Azure infrastructure-as-code and deployment config
```

## Setup

### Prerequisites

- Python >= 3.11
- Node.js
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### 1. Backend `.env`

Create `backend/.env`:

```
API_KEY=<your-anthropic-api-key>
MODEL_HEAVY="claude-sonnet-4-20250514"
MODEL_LIGHT="claude-haiku-4-5-20251001"
```

| Variable | Required | Description |
|---|---|---|
| `API_KEY` | Yes | Anthropic API key |
| `MODEL_HEAVY` | No | Model for complex reasoning (defaults to `claude-sonnet-4-6`) |
| `MODEL_LIGHT` | No | Model for simple structured tasks (defaults to `claude-haiku-4-5-20251001`) |

### 2. Frontend `.env`

Create `frontend/.env`:

```
VITE_DEBUG=true
```

| Variable | Required | Description |
|---|---|---|
| `VITE_DEBUG` | No | Enables debug panel in the UI |

### 3. Run the Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Runs on `http://localhost:8000`. Verify with `curl http://localhost:8000/api/health`.

### 4. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:3000`.
