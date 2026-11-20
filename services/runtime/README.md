# SAM AI TEAM Runtime

This directory contains the current Windows-tested 12-worker runtime and its Docker Compose packaging.

## Local Windows runtime
- Python 3.12+ (standard library only)
- Ollama reachable at http://127.0.0.1:11434
- Default model: qwen2.5:3b
- Start: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\\start.ps1`
- Stop: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\\stop.ps1`
- Health: http://127.0.0.1:8787/health

## Automatic start after Windows sign-in
Run `install-startup.ps1` once in the current user session. It creates a shortcut in the current user's Startup folder without administrator rights or a permanent execution-policy change. The launcher waits for Ollama, avoids duplicate starts, starts the runtime, and verifies 12/12 workers. Logs are written to `logs/`.

## Coordinator API
- `GET /health`
- `GET /services`
- `POST /tasks` with JSON `{"task":"...","services":["ceo","research"],"context":"..."}`
- `GET /tasks/{id}`

The coordinator binds to localhost by default. A non-local bind is rejected unless `SAM_API_TOKEN` is configured. Do not expose it directly to the public internet.

## Docker
The Compose file expects Ollama on the Docker host and requires `SAM_API_TOKEN`. The connected Windows PC did not have Docker installed, so the container configuration has not been locally container-tested.

## Known production gaps
- Task records are JSON files, not a transactional queue/database; in-flight tasks are not recovered after a process crash.
- All 12 workers share one Ollama model and host resource pool.
- External SaaS integrations (search/design/video/social publishing) are not authenticated or wired into these Python workers.
- Cloud deployment requires a suitable inference endpoint, durable task store, secret manager, TLS/reverse proxy, monitoring, and a reviewed cost plan.
- Render free web services sleep after 15 minutes idle, and free background workers/persistent disks are not included; this is not a suitable always-on 12-worker deployment without a paid architecture.

Never claim runtime acceptance from source tests alone. Require a live 12/12 health check, a completed test task, output-quality review, and restart/reboot evidence.
