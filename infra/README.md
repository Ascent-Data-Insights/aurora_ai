# Infrastructure

Azure infrastructure-as-code and deployment configuration for the Strategic Intelligence Platform.

## Azure Services

| Service | Purpose | Dev Tier |
|---|---|---|
| **Azure Static Web Apps** | Host React frontend | Free tier |
| **Azure Container Apps** | Run FastAPI backend | ~$0–5/mo |
| **Azure Database for PostgreSQL** | Operational data, LangGraph checkpoints, pgvector embeddings | Burstable, ~$12–15/mo |
| **Azure Blob Storage** | Raw files, audio recordings | ~$1/mo |
| **Azure AI Foundry** | LLM calls (Claude, GPT-4o) + Whisper transcription | Pay-per-use |

## Database

PostgreSQL with pgvector extension handles three workloads in a single instance:

1. **Operational tables** — orgs, users, sessions, initiatives, vendors, scores, etc.
2. **LangGraph checkpoints** — durable session state so users can pause/resume strategy sessions across days or weeks.
3. **Vector embeddings** — semantic search over documents, transcripts, and cross-module context.

Keeping everything in Postgres avoids a separate vector DB and enables joins between structured data and semantic search.

## Key Considerations

- **Tenant isolation** — data security is the #1 enterprise sales objection. Infrastructure must enforce strict separation between client data at the database level.
- **Secrets management** — API keys for Azure AI Foundry, database credentials, and any client-specific configuration need proper vault-based management.
- **Scaling path** — Postgres is the only meaningful fixed cost. LLM and transcription costs scale with usage (and proportionally with revenue). Container Apps scales to zero when idle.
- **Compliance** — passive voice recording in boardrooms has regulatory implications (consent laws vary by jurisdiction, GDPR for EU clients). Infrastructure choices should support data residency requirements.
