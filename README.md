# Strategic Intelligence Platform

AI-powered enterprise strategy tooling. Encodes proven C-suite decision-making frameworks into guided agentic flows, delivering management-consulting-grade analysis at a fraction of the cost.

## Concept

Enterprise leaders rely on expensive consulting engagements for decisions that are fundamentally repeatable — portfolio prioritization, vendor selection, operational investment calls. This platform takes battle-tested frameworks, encodes them into agentic workflows, and uses voice as the primary input to eliminate adoption friction.

The platform is built around **modules**, each targeting a specific leadership decision domain:

- **Portfolio Strategy** — evaluate and rank initiatives against Value, Feasibility, and Scalability. Score each initiative across dimensions, then rack-and-stack the full portfolio.
- **Vendor Management (to be built later)** — structured vendor evaluation built on real enterprise procurement frameworks.
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
- **Azure** — Todd's network skews Microsoft/enterprise. Azure AI Foundry consolidates LLM and transcription under one endpoint.

## Voice Pipeline

Audio input (mic, uploaded recording, future passive Teams integration) flows through Whisper transcription before any agent sees it. Agents only work with text.

This is the core adoption play — leaders talk through decisions naturally instead of filling out forms. The platform captures context from how they already operate.

## Project Structure

```
frontend/   React web app (React Native iOS in later phase)
backend/    FastAPI + agentic stack (LangGraph, PydanticAI, LlamaIndex)
infra/      Azure infrastructure-as-code and deployment config
```

See each directory's README for details.

## Cost Profile

| Stage | Est. Monthly Cost |
|---|---|
| Pre-client dev | ~$20–40 |
| Early production (5 clients) | ~$130–290 |
| Growth (20+ clients) | ~$500–1,000 |

Infrastructure costs are nearly fixed. LLM usage is the variable that scales with client activity — and scales proportionally to revenue. Key cost levers: prompt caching (10% of normal input price on cache hits) and model routing (Haiku for simple tasks, Sonnet for core work).
