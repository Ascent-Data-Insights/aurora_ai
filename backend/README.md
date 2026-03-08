# Backend

FastAPI application with the agentic stack powering the Strategic Intelligence Platform.

## Stack

- **FastAPI** — Python API layer connecting the frontend to the agentic stack
- **LangGraph** — orchestration backbone. Defines agent execution flow as an explicit graph with durable session state via Postgres checkpointing. Handles human-in-the-loop patterns (collaborator input, approval gates).
- **PydanticAI** — individual agents at each graph node. Type-safe structured outputs (scores, assessments, summaries) with built-in validation. Each module has its own agent set.
- **LlamaIndex** — document ingestion pipeline. Parsing, chunking, embedding, and retrieval for uploaded files. Feeds context into agents via pgvector.
- **PostgreSQL + pgvector** — triple duty: operational data (orgs, users, sessions, initiatives, vendors), LangGraph session checkpoints, and vector embeddings for semantic search.
- **Azure Blob Storage** — raw file storage (uploaded PDFs, audio recordings pre-transcription)
- **Azure AI Foundry** — LLM calls (Claude Sonnet/Haiku) and Whisper transcription

## Voice / Transcription Flow

```
Audio input --> Azure AI Foundry (Whisper) --> transcript text --> LangGraph pipeline --> agents
```

Transcription happens before any agent processes content. Agents only work with text.

## Module Architecture

Each strategy module (portfolio strategy, vendor management, etc.) is implemented as:

1. A **LangGraph graph** defining the orchestration flow — what context to gather, in what order, when to score, when to ask follow-ups.
2. A set of **PydanticAI agents** handling focused tasks at each node — scoring an initiative, summarizing context, generating recommendations.
3. **Structured output schemas** (Pydantic models) for each agent's output, ensuring type safety and validation.

Cross-module context is shared via pgvector — outputs from one module are embedded and retrievable by others.

## Key Considerations

- **Auth and multi-tenancy** — enterprise clients require strict tenant isolation. Row-level security in Postgres or schema-per-tenant.
- **Model routing** — use Haiku for simple structured tasks (parsing, classification), Sonnet for core agent reasoning, Opus only for high-stakes final outputs. Matters for both cost and latency in the voice pipeline.
- **Prompt caching** — repeated context (system prompts, module frameworks) should hit cache for 90% input cost reduction.
- **Auditability** — every LangGraph state transition is logged. Enterprise clients will ask how a recommendation was reached.
