# Infrastructure

## Architecture

- **Frontend**: Netlify (static site hosting)
- **Backend**: Hetzner VM (`demos-server`, `178.156.214.239`)
- **Database**: PostgreSQL on the Hetzner VM
- **Reverse proxy / TLS**: Caddy (auto-provisions Let's Encrypt certs)
- **DNS**: Netlify DNS (both `ascentdi.com` and `ascentdatainsights.com` zones)

## Domains

| Domain | Points to | Purpose |
|---|---|---|
| `aurora-api.ascentdi.com` | Hetzner VM (Caddy → port 8001) | Backend API |
| `aurora.ascentdi.com` | Netlify (`adi-aurora-demo`) | Frontend |

## Hetzner VM Setup

The backend runs as a systemd service from a git clone of this repo.

### Services on the VM

| Service | Port | Description |
|---|---|---|
| `routing-demo` | 8000 | Routing demo backend (separate project) |
| `aurora` | 8001 | This project's backend |
| `caddy` | 80/443 | Reverse proxy with auto-TLS |
| `postgresql` | 5432 | Database |

### Key files on the VM

```
/root/aurora/                    # git clone of this repo
/root/aurora/backend/.env        # environment variables (not in git)
/etc/systemd/system/aurora.service
/etc/caddy/Caddyfile
```

### Systemd service (`aurora.service`)

```ini
[Unit]
Description=Aurora Portfolio Manager Backend
After=network.target postgresql.service

[Service]
Type=simple
WorkingDirectory=/root/aurora/backend
ExecStartPre=/root/.local/bin/uv run alembic upgrade head
ExecStart=/root/.local/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Caddy config

```
routing-api.ascentdatainsights.com, routing-api.ascentdi.com {
     reverse_proxy localhost:8000
}

aurora-api.ascentdi.com {
     reverse_proxy localhost:8001
}
```

### Backend environment variables (`/root/aurora/backend/.env`)

```
ANTHROPIC_API_KEY=<your key>
CARTESIA_API_KEY=<your key>       # optional, for voice chat TTS
DEEPGRAM_API_KEY=<your key>       # optional, for speech-to-text
DATABASE_URL=postgresql+asyncpg://aurora:aurora@localhost:5432/aurora
CORS_ORIGINS=["https://aurora.ascentdi.com"]
```

### Deploying backend updates

```bash
ssh root@178.156.214.239
cd /root/aurora
git pull
cd backend && uv sync --frozen --no-dev
systemctl restart aurora
```

### GitHub access

The VM has a read-only SSH deploy key registered on the `Ascent-Data-Insights/aurora_ai` repo (titled `hetzner-demos-server`).

## Netlify Frontend

The frontend is deployed as its own Netlify site (`adi-aurora-demo`), linked to the `Ascent-Data-Insights/aurora_ai` GitHub repo. Pushes to `main` auto-deploy. Build settings are in `frontend/netlify.toml`.

### Environment variables (set in Netlify build)

| Variable | Value | Purpose |
|---|---|---|
| `VITE_API_BASE` | `https://aurora-api.ascentdi.com` | Backend HTTP API base URL |
| `VITE_WS_BASE` | `wss://aurora-api.ascentdi.com` | Backend WebSocket base URL |

### Database

PostgreSQL 16 on the VM, database `aurora`, user `aurora`. Migrations are run automatically on service start via `alembic upgrade head`.

## DNS Records (Netlify DNS, `ascentdi.com` zone)

| Record | Type | Value |
|---|---|---|
| `aurora-api.ascentdi.com` | A | `178.156.214.239` |
| `aurora.ascentdi.com` | NETLIFY | `adi-aurora-demo.netlify.app` |
| `routing-api.ascentdi.com` | A | `178.156.214.239` |
| `demos.ascentdi.com` | NETLIFY | `adi-routing-demo.netlify.app` |
