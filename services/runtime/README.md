# SAM AI TEAM — 12 model-backed specialist workers

The runtime contains 12 independently runnable specialist HTTP workers and one coordinator. Each worker has its own role prompt and calls the configured model provider.

## Providers
- Ollama (default): local model server; default model `qwen2.5:3b`.
- OpenAI: configure `SAM_LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and `SAM_OPENAI_MODEL`.

## Local Windows host
The current connected PC has Ollama and the `qwen2.5:3b` model available. The local package in `Downloads/SAM-GOLD/SAM-AI-TEAM-SERVICES` runs 12 worker processes and the coordinator. Health reported 12/12 workers online and 12/12 with a configured model provider.

Start/stop:
`powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1`
`powershell -NoProfile -ExecutionPolicy Bypass -File .\stop.ps1`
This uses a process-scoped execution-policy override; it does not change system policy.

## Docker deployment
Docker is not installed on the connected PC, so cloud/container deployment has not been executed. On a Docker-capable host, copy `.env.example` to `.env`, set a long random `SAM_API_TOKEN`, ensure Ollama is reachable from containers, then run:
`docker compose up --build -d`
Coordinator: `http://localhost:8787`.
Submit tasks using `POST /tasks` and header `Authorization: Bearer $SAM_API_TOKEN`.

## API
- `GET /health`: coordinator, worker and model-provider readiness
- `GET /services`: specialist catalogue
- `POST /tasks`: dispatch a task to selected workers (omit services to use all)
- `GET /tasks/{id}`: retrieve the result (in-memory MVP storage)

## Security
The coordinator refuses non-loopback binding without `SAM_API_TOKEN`. Do not expose publicly without TLS/reverse proxy, rate limiting, persistent queue/storage, audit logs, backups and secrets management. Publishing, sending, purchasing, payments, deletion and account-permission changes remain approval-gated.
