# SAM AI TEAM Runtime

This directory contains the 12 specialist HTTP workers and the coordinator. The code supports a local Windows runtime and a single-container staging layout.

## Local Windows runtime

- Python 3.12+ (standard library only)
- Ollama reachable at `http://127.0.0.1:11434`
- Default local model: `qwen2.5:3b`
- Start: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\\start.ps1`
- Stop: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\\stop.ps1`
- Health: `http://127.0.0.1:8787/health`

## Task queue and recovery

The coordinator writes each task to SQLite in WAL mode and maintains an atomic JSON archive under `tasks/`. It limits parallel worker calls, retries transient transport/HTTP failures with backoff, and resumes incomplete tasks after coordinator restart while preserving successful role outputs. This is a durable single-instance local queue, not a horizontally distributed job system.

Defaults can be changed with `SAM_MAX_PARALLEL`, `SAM_WORKER_TIMEOUT`, and `SAM_WORKER_RETRIES`. The queue database can be moved with `SAM_TASK_DB`.

## Coordinator API

- `GET /health`
- `GET /services`
- `POST /tasks` with JSON `{"task":"...","services":["ceo","research"],"context":"..."}`
- `GET /tasks/{id}`
- `POST /tasks/{id}/evidence` with JSON `{"path":"rendered-file.mp4"}`

Media evidence must point to a real file inside `SAM_MEDIA_DIR` (defaults to `services/runtime/deliverables`). The coordinator verifies existence, non-zero size, SHA-256, and file type. Video/audio metadata is checked with `ffprobe`; image files are checked against their file signatures. The independent acceptance module requires evidence for explicitly requested rendered media, checks video orientation/duration when specified, and rejects model-invented filenames.

The coordinator binds to localhost by default. If it is bound to a non-local interface, `SAM_API_TOKEN` is required. Workers are localhost-bound by default; set `SAM_WORKER_TOKEN` to authenticate coordinator-to-worker calls. Do not expose the API directly to the public internet.

## Worker/model quality

The local default remains Qwen 2.5 3B via Ollama. Prompts now distinguish written production assets (scripts, storyboards, copy) from rendered image/video/audio bytes and forbid fabricated file/execution claims. Ollama generation settings are configurable with `SAM_OLLAMA_TIMEOUT`; the local model itself has not been upgraded in this change.

## Automatic start after Windows sign-in

Run `install-startup.ps1` once in the current user session. It creates a shortcut in the current user's Startup folder without administrator rights or a permanent execution-policy change. The launcher waits for Ollama, avoids duplicate starts, starts the runtime, and verifies 12/12 workers. A full Windows reboot test is still required before claiming reboot persistence.

## Docker and cloud

The Compose file expects Ollama on the Docker host. The connected Windows PC did not have Docker installed, so the container configuration has not been locally container-tested. The Render staging blueprint remains manual and is not deployed.

## Remaining production gaps

- SQLite is suitable for one coordinator instance; multi-instance deployments need a shared durable queue/database and distributed worker leases.
- All 12 local workers share one Ollama model and host resource pool.
- GitHub and Notion connectors are available to the ChatGPT session but are not automatically exposed as credentials to the standalone Python workers. External SaaS integrations need explicit per-service adapters and least-privilege credentials.
- WorkOS management is unavailable until the connected WorkOS login is associated with a WorkOS dashboard account.
- Cloud deployment requires a suitable inference endpoint, durable task store, secret manager, TLS/reverse proxy, monitoring, and a reviewed cost plan. Render free web services sleep while idle and do not provide durable disks/background workers for a reliable always-on production fleet.

Never claim runtime acceptance from source tests alone. Require a live 12/12 health check, a completed 12-role task, a PASS quality verdict, actual evidence files where media was requested, and restart/reboot evidence.
