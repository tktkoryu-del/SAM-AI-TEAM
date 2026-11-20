# Independent Specialist Runtime

SAM AI TEAM now has a deployable runtime design: 12 separately runnable HTTP workers and one coordinator.

## Services
CEO, COO, Research, Strategy, CTO, Design, Video, Content, Marketing, Platforms, Finance, Quality.

## Local runtime already validated
A Windows host package lives at `Downloads/SAM-GOLD/SAM-AI-TEAM-SERVICES`.
It runs 12 specialist Python processes and a coordinator on localhost. Health check returned 12/12 online and task dispatch succeeded.

## Deploy on independent servers
Use Docker Compose on a Docker-capable host:
`docker compose up --build -d`
Each specialist is a separate service/container in compose. Coordinator port 8787 is the API entry point.
Do not expose the coordinator publicly until authentication, TLS, rate limiting, persistent storage and secrets management are configured.

## Endpoints
- GET /health — service health
- GET /services — worker catalogue
- POST /tasks — dispatch a task
- GET /tasks/{id} — retrieve in-memory task result

## Integration status
Worker scaffolding and dispatch are implemented. AI reasoning/provider adapters still require configured credentials and integration-specific implementation. An HTTP 200 means task accepted by the local role worker, not that a model produced a substantive work product. Publishing, payment, deletion, outbound messaging and account permission changes remain approval-gated.
