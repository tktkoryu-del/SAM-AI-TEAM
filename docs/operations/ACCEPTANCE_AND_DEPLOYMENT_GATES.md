# SAM AI TEAM — Acceptance & Deployment Gates

This branch adds a reproducible repository-level acceptance gate. It does not claim that local desktop processes, external integrations, or cloud deployments are active.

## Acceptance gate

Run locally:
```bash
python -m unittest discover -s tests -v
python scripts/acceptance_gate.py
```

The gate checks:
- All 12 specialist roles are declared exactly once.
- Each role has a non-empty prompt and a stable service key.
- Coordinator/runtime files are present before claiming runtime readiness.
- Required operational safeguards are present: approval-gating, health endpoint, task status retrieval, and persisted task results.
- Docker deployment files declare all expected worker services.
- No credentials are committed in example configuration.

## Runtime acceptance evidence

A runtime is considered accepted only when all of these are attached to the release record:
1. Health response showing coordinator online and 12/12 workers online.
2. One unique task ID dispatched to every intended worker.
3. Each worker returns a non-empty role-specific deliverable (not a plan or promise).
4. Quality worker reports defects and objectively checks the outputs.
5. Task record can be retrieved after coordinator restart.
6. A cold reboot test confirms workers restart automatically.
7. A remote health check confirms TLS and authentication if deployed beyond localhost.

A passing source-level test suite is not proof of runtime acceptance.

## Desktop restart

For Windows desktop operation, prefer a per-user Startup folder launcher where Task Scheduler registration is denied. The launcher must:
- wait for Ollama readiness;
- start coordinator and all workers;
- write logs to a bounded/rotated directory;
- avoid embedding API keys in scripts;
- expose only localhost unless an authenticated reverse proxy is configured.

Do not run elevated commands or change account permissions without explicit user authorization.

## Integrations

Each external integration must have:
- an adapter with a narrow interface;
- an explicit connection/health test;
- least-privilege credentials loaded from environment/secret store;
- dry-run mode;
- idempotency and audit logging;
- approval checks for publish, send, spend, delete, and permission mutations.

Never mark an integration connected solely because a tool name appears in documentation.

## Cloud deployment

Cloud deployment remains blocked until a target host/provider, cost ceiling, secrets mechanism, domain/TLS strategy, backup policy, and monitoring destination are explicitly selected and verified. No paid resources are provisioned by this repository change.
